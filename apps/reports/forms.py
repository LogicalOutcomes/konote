"""Forms for the reports app — metric export filtering, CMT reports, and client data export."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program
from apps.plans.models import MetricDefinition
from apps.clients.models import ClientFile
from .demographics import get_demographic_field_choices
from .utils import get_fiscal_year_choices, get_fiscal_year_range, get_current_fiscal_year


# Recipient choices for audit logging — tracks who is receiving exported data
RECIPIENT_CHOICES = [
    ("", _("— Select recipient —")),
    ("self", _("Keeping for my records")),
    ("colleague", _("Sharing with colleague")),
    ("funder", _("Sharing with funder")),
    ("other", _("Other")),
]


class ExportRecipientMixin:
    """
    Mixin adding recipient tracking fields to export forms.

    Security requirement: All exports must document who is receiving
    the data. This creates accountability and enables audit review.
    """

    def add_recipient_fields(self):
        """Add recipient fields to the form. Call in __init__ after super()."""
        self.fields["recipient"] = forms.ChoiceField(
            choices=RECIPIENT_CHOICES,
            required=True,
            label=_("Who is receiving this data?"),
            help_text=_("Required for audit purposes."),
            error_messages={"required": _("Please select who will receive this export.")},
        )
        self.fields["recipient_detail"] = forms.CharField(
            required=False,
            max_length=200,
            label=_("Recipient details"),
            help_text=_("Name of colleague, funder, or other recipient."),
            widget=forms.TextInput(attrs={"placeholder": _("e.g., United Way, Jane Smith")}),
        )

    def get_recipient_display(self):
        """Return a formatted string describing the recipient for audit logs."""
        recipient = self.cleaned_data.get("recipient", "")
        detail = self.cleaned_data.get("recipient_detail", "").strip()

        if recipient == "self":
            return "Self (personal records)"
        elif recipient == "colleague":
            return f"Colleague: {detail}" if detail else "Colleague (unspecified)"
        elif recipient == "funder":
            return f"Funder: {detail}" if detail else "Funder (unspecified)"
        elif recipient == "other":
            return f"Other: {detail}" if detail else "Other (unspecified)"
        else:
            return "Not specified"


class MetricExportForm(ExportRecipientMixin, forms.Form):
    """Filter form for the aggregate metric CSV export."""

    program = forms.ModelChoiceField(
        queryset=Program.objects.filter(status="active"),
        required=True,
        label=_("Program"),
        empty_label=_("— Select a programme —"),
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
        label=_("Group by demographic"),
        help_text=_("Optionally break down results by age range or a custom field."),
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


class CMTExportForm(ExportRecipientMixin, forms.Form):
    """
    Form for United Way CMT (Community Monitoring Tool) export.

    This form is simpler than the full metric export form, as CMT reports
    have a fixed structure. Users select a programme and fiscal year,
    and the report is generated with all applicable data.
    """

    program = forms.ModelChoiceField(
        queryset=Program.objects.filter(status="active"),
        required=True,
        label=_("Programme"),
        empty_label=_("— Select a programme —"),
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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Scope program dropdown to programs the user can export from
        if user:
            from .utils import get_manageable_programs
            self.fields["program"].queryset = get_manageable_programs(user)
        # Build fiscal year choices dynamically
        # For CMT, we require a fiscal year selection (no custom date range)
        self.fields["fiscal_year"].choices = get_fiscal_year_choices()
        # Default to current fiscal year
        self.fields["fiscal_year"].initial = str(get_current_fiscal_year())
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


class ClientDataExportForm(ExportRecipientMixin, forms.Form):
    """
    Form for exporting all client data as CSV.

    This export is designed for data portability and migration, allowing
    agencies to extract all their client data in a standard format.
    """

    STATUS_CHOICES = [
        ("", _("— All statuses —")),
        ("active", _("Active only")),
        ("inactive", _("Inactive only")),
        ("discharged", _("Discharged only")),
    ]

    program = forms.ModelChoiceField(
        queryset=Program.objects.filter(status="active"),
        required=False,
        label=_("Programme"),
        empty_label=_("— All programmes —"),
        help_text=_("Leave blank to export participants from all programmes."),
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label=_("Participant status"),
        help_text=_("Filter by participant status, or export all."),
    )

    include_custom_fields = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Include custom fields"),
        help_text=_("Add custom field values as additional columns."),
    )

    include_enrolments = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Include programme enrolments"),
        help_text=_("Add programme enrolment history as additional columns."),
    )

    include_consent = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Include consent information"),
        help_text=_("Add consent and data retention fields."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add recipient tracking fields for audit purposes
        self.add_recipient_fields()


class IndividualClientExportForm(ExportRecipientMixin, forms.Form):
    """
    Form for exporting an individual client's complete data (PIPEDA compliance).

    Under PIPEDA, individuals have the right to access all personal information
    held about them. This form lets staff export everything for one client.
    """

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
