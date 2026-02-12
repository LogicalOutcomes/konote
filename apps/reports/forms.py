"""Forms for the reports app — metric export filtering, funder reports, and individual client export."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program
from apps.plans.models import MetricDefinition
from .demographics import get_demographic_field_choices
from .models import FunderProfile
from .utils import get_fiscal_year_choices, get_fiscal_year_range, get_current_fiscal_year


# --- Context-specific recipient choices ---
# Different export types have different legitimate audiences.
# Individual client data should NEVER be offered to funders.
# Funders need aggregate outcomes, not individual clinical records.

AGGREGATE_RECIPIENT_CHOICES = [
    ("", _("— Select recipient —")),
    ("self", _("Keeping for my records")),
    ("colleague", _("Sharing with colleague")),
    ("funder", _("Sharing with funder")),
    ("board", _("Sharing with board")),
    ("other", _("Other")),
]

CLINICAL_RECIPIENT_CHOICES = [
    ("", _("— Select recipient —")),
    ("self", _("Keeping for my records")),
    ("colleague", _("Sharing with colleague")),
    ("client", _("Client access request (PIPEDA)")),
    ("supervisor", _("Sharing with supervisor")),
    ("other", _("Other")),
]


class ExportRecipientMixin:
    """
    Mixin adding recipient tracking fields to export forms.

    Security requirement: All exports must document who is receiving
    the data. This creates accountability and enables audit review.

    Subclasses set recipient_choices to control which audiences are
    offered. Individual-level exports must NOT include "funder".
    """

    recipient_choices = AGGREGATE_RECIPIENT_CHOICES  # default; override per form
    recipient_placeholder = _("e.g., Community Foundation, Jane Smith")  # default; override per form

    def add_recipient_fields(self):
        """Add recipient fields to the form. Call in __init__ after super()."""
        self.fields["recipient"] = forms.ChoiceField(
            choices=self.recipient_choices,
            required=True,
            label=_("Who is receiving this data?"),
            help_text=_("Required for audit purposes."),
            error_messages={"required": _("Please select who will receive this export.")},
        )
        self.fields["recipient_detail"] = forms.CharField(
            required=False,
            max_length=200,
            label=_("Recipient details"),
            help_text=_("Name of recipient or organisation."),
            widget=forms.TextInput(attrs={"placeholder": self.recipient_placeholder}),
        )

    def get_recipient_display(self):
        """Return a formatted string describing the recipient for audit logs."""
        recipient = self.cleaned_data.get("recipient", "")
        detail = self.cleaned_data.get("recipient_detail", "").strip()

        labels = {
            "self": "Self (personal records)",
            "colleague": "Colleague",
            "funder": "Funder",
            "board": "Board",
            "client": "Client access request (PIPEDA)",
            "supervisor": "Supervisor",
        }
        base = labels.get(recipient, recipient.title() if recipient else "Not specified")
        if recipient == "self":
            return base
        if detail:
            return f"{base}: {detail}"
        return f"{base} (unspecified)" if recipient else "Not specified"


class MetricExportForm(ExportRecipientMixin, forms.Form):
    """Filter form for the aggregate metric CSV export."""

    recipient_choices = AGGREGATE_RECIPIENT_CHOICES

    program = forms.ModelChoiceField(
        queryset=Program.objects.filter(status="active"),
        required=True,
        label=_("Program"),
        empty_label=_("— Select a program —"),
    )

    # Fiscal year quick-select (optional — overrides manual dates when selected)
    fiscal_year = forms.ChoiceField(
        required=False,
        label=_("Fiscal Year (April-March)"),
        help_text=_("Select a fiscal year to auto-fill dates, or leave blank for custom range."),
    )

    metrics = forms.ModelMultipleChoiceField(
        queryset=MetricDefinition.objects.filter(is_enabled=True, status="active"),
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label=_("Metrics to include"),
    )
    date_from = forms.DateField(
        required=False,  # Made optional — fiscal_year can provide dates
        label=_("Date from"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        required=False,  # Made optional — fiscal_year can provide dates
        label=_("Date to"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    # Demographic grouping (optional)
    group_by = forms.ChoiceField(
        required=False,
        label=_("Legacy single-field grouping"),
        help_text=_("Ignored when a funder profile is selected above."),
    )

    # Funder profile — selects demographic breakdown configuration
    funder_profile = forms.ModelChoiceField(
        queryset=FunderProfile.objects.none(),
        required=False,
        empty_label=_("No funder profile"),
        label=_("Funder demographic profile"),
        help_text=_(
            "Select a funder profile to use their specific demographic categories. "
            "Leave blank to use the legacy single-field grouping above."
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Scope program dropdown to programs the user can export from
        if user:
            from .utils import get_manageable_programs
            self.fields["program"].queryset = get_manageable_programs(user)
        # Build fiscal year choices dynamically (includes blank option)
        fy_choices = [("", "— Custom date range —")] + get_fiscal_year_choices()
        self.fields["fiscal_year"].choices = fy_choices
        # Build demographic grouping choices dynamically
        self.fields["group_by"].choices = get_demographic_field_choices()
        # Scope funder profiles to programs the user can access
        if user:
            from .utils import get_manageable_programs
            accessible_programs = get_manageable_programs(user)
            self.fields["funder_profile"].queryset = (
                FunderProfile.objects.filter(
                    programs__in=accessible_programs
                ).distinct().order_by("name")
            )
        # Add recipient tracking fields for audit purposes
        self.add_recipient_fields()

    FORMAT_CHOICES = [
        ("csv", _("CSV (spreadsheet)")),
        ("pdf", _("PDF (printable report)")),
    ]

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial="csv",
        widget=forms.RadioSelect,
        label=_("Export format"),
    )

    include_achievement_rate = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Include achievement rate"),
        help_text=_("Calculate and include outcome achievement statistics in the export."),
    )

    def clean(self):
        cleaned = super().clean()
        fiscal_year = cleaned.get("fiscal_year")
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")

        # If fiscal year is selected, use those dates instead of manual entry
        if fiscal_year:
            try:
                fy_start_year = int(fiscal_year)
                date_from, date_to = get_fiscal_year_range(fy_start_year)
                cleaned["date_from"] = date_from
                cleaned["date_to"] = date_to
            except (ValueError, TypeError):
                raise forms.ValidationError(_("Invalid fiscal year selection."))
        else:
            # Manual date entry — both fields required
            if not date_from:
                self.add_error("date_from", _("This field is required when not using a fiscal year."))
            if not date_to:
                self.add_error("date_to", _("This field is required when not using a fiscal year."))

        # Validate date order (after potentially setting from fiscal year)
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(_("'Date from' must be before 'Date to'."))

        return cleaned


class FunderReportForm(ExportRecipientMixin, forms.Form):
    """
    Form for funder report export.

    This form is simpler than the full metric export form, as funder reports
    have a fixed structure. Users select a program and fiscal year,
    and the report is generated with all applicable data.
    """

    recipient_choices = AGGREGATE_RECIPIENT_CHOICES

    program = forms.ModelChoiceField(
        queryset=Program.objects.filter(status="active"),
        required=True,
        label=_("Program"),
        empty_label=_("— Select a program —"),
    )

    fiscal_year = forms.ChoiceField(
        required=True,
        label=_("Fiscal Year (April-March)"),
        help_text=_("Select the fiscal year to report on."),
    )

    FORMAT_CHOICES = [
        ("csv", _("CSV (spreadsheet)")),
        ("pdf", _("PDF (printable report)")),
    ]

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial="csv",
        widget=forms.RadioSelect,
        label=_("Export format"),
    )

    # Funder profile — selects demographic breakdown configuration
    funder_profile = forms.ModelChoiceField(
        queryset=FunderProfile.objects.none(),
        required=False,
        empty_label=_("Default age categories"),
        label=_("Funder demographic profile"),
        help_text=_(
            "Select a funder profile to use their specific demographic categories. "
            "Leave blank for the default Canadian nonprofit age groupings."
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Scope program dropdown to programs the user can export from
        if user:
            from .utils import get_manageable_programs
            self.fields["program"].queryset = get_manageable_programs(user)
        # Build fiscal year choices dynamically
        # Funder reports require a fiscal year selection (no custom date range)
        self.fields["fiscal_year"].choices = get_fiscal_year_choices()
        # Default to current fiscal year
        self.fields["fiscal_year"].initial = str(get_current_fiscal_year())
        # Scope funder profiles to programs the user can access
        if user:
            from .utils import get_manageable_programs
            accessible_programs = get_manageable_programs(user)
            self.fields["funder_profile"].queryset = (
                FunderProfile.objects.filter(
                    programs__in=accessible_programs
                ).distinct().order_by("name")
            )
        # Add recipient tracking fields for audit purposes
        self.add_recipient_fields()

    def clean(self):
        cleaned = super().clean()
        fiscal_year = cleaned.get("fiscal_year")

        if fiscal_year:
            try:
                fy_start_year = int(fiscal_year)
                date_from, date_to = get_fiscal_year_range(fy_start_year)
                cleaned["date_from"] = date_from
                cleaned["date_to"] = date_to
                # Create fiscal year label for display
                end_year_short = str(fy_start_year + 1)[-2:]
                cleaned["fiscal_year_label"] = f"FY {fy_start_year}-{end_year_short}"
            except (ValueError, TypeError):
                raise forms.ValidationError(_("Invalid fiscal year selection."))
        else:
            raise forms.ValidationError(_("Please select a fiscal year."))

        return cleaned


class IndividualClientExportForm(ExportRecipientMixin, forms.Form):
    """
    Form for exporting an individual client's complete data (PIPEDA compliance).

    Under PIPEDA, individuals have the right to access all personal information
    held about them. This form lets staff export everything for one client.

    Funders are NOT a valid recipient for individual client data.
    """

    recipient_choices = CLINICAL_RECIPIENT_CHOICES
    recipient_placeholder = _("e.g., Jane Smith, Clinical Supervisor")

    FORMAT_CHOICES = [
        ("pdf", _("PDF (printable report)")),
        ("csv", _("CSV (spreadsheet)")),
    ]

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial="pdf",
        widget=forms.RadioSelect,
        label=_("Export format"),
    )

    include_plans = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Include plan sections and targets"),
    )

    include_notes = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Include progress notes"),
    )

    include_metrics = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Include metric values"),
    )

    include_events = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Include events"),
    )

    include_custom_fields = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Include custom fields"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_recipient_fields()
