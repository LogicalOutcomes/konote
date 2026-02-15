"""Forms for the reports app — metric export filtering, report templates, and individual client export."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program
from apps.plans.models import MetricDefinition
from .demographics import get_demographic_field_choices
from .models import ReportTemplate
from .utils import get_fiscal_year_choices, get_fiscal_year_range, get_current_fiscal_year, is_aggregate_only_user


class ExportRecipientMixin:
    """
    Mixin adding recipient tracking fields to export forms.

    Security requirement: All exports must document who is receiving
    the data. This creates accountability and enables audit review.

    Uses open text fields to avoid exposing inappropriate predefined
    audiences for sensitive exports.
    """

    def add_recipient_fields(self):
        """Add recipient fields to the form. Call in __init__ after super()."""
        self.fields["recipient"] = forms.CharField(
            required=True,
            label=_("Who is receiving this data?"),
            help_text=_("Required for audit purposes (name and organisation)."),
            max_length=200,
            widget=forms.TextInput(attrs={"placeholder": _("e.g., Jane Smith, Sunrise Community Services")}),
            error_messages={"required": _("Please enter who will receive this export.")},
        )
        self.fields["recipient_reason"] = forms.CharField(
            required=True,
            max_length=250,
            label=_("Reason"),
            help_text=_("Required for audit purposes."),
            widget=forms.TextInput(attrs={"placeholder": _("e.g., Board reporting, case conference, client request")}),
            error_messages={"required": _("Please enter the reason for this export.")},
        )

    def get_recipient_display(self):
        """Return a formatted string describing the recipient for audit logs."""
        recipient = (self.cleaned_data.get("recipient") or "").strip()
        reason = (self.cleaned_data.get("recipient_reason") or "").strip()
        if not recipient:
            recipient = "Not specified"
        if not reason:
            reason = "Not specified"
        return f"{recipient} | Reason: {reason}"

    def clean_recipient(self):
        """Validate recipient text for privacy-sensitive exports."""
        recipient = (self.cleaned_data.get("recipient") or "").strip()
        if not recipient:
            return recipient

        if getattr(self, "contains_client_identifying_data", False):
            lowered = recipient.lower()
            blocked_terms = ("funder", "funding", "foundation", "grant")
            if any(term in lowered for term in blocked_terms):
                raise forms.ValidationError(
                    _("For security, funders are not valid recipients for exports that include participant-identifying data.")
                )

        return recipient


class MetricExportForm(ExportRecipientMixin, forms.Form):
    """Filter form for the aggregate metric CSV export."""

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
        label=_("Grouping"),
        help_text=_("Used only when no reporting template is selected above."),
    )

    # Report template — selects demographic breakdown configuration
    report_template = forms.ModelChoiceField(
        queryset=ReportTemplate.objects.none(),
        required=False,
        empty_label=_("No reporting template"),
        label=_("Reporting template"),
        help_text=_(
            "Reporting templates define the demographic categories your funder requires "
            "(e.g., age groups, employment status). Select one to format your report "
            "to match a funder's requirements, or leave blank to use Grouping above."
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.contains_client_identifying_data = bool(user and not is_aggregate_only_user(user))
        # Scope program dropdown to programs the user can export from
        if user:
            from .utils import get_manageable_programs
            self.fields["program"].queryset = get_manageable_programs(user)
        # Build fiscal year choices dynamically (includes blank option)
        fy_choices = [("", "— Custom date range —")] + get_fiscal_year_choices()
        self.fields["fiscal_year"].choices = fy_choices
        # Build demographic grouping choices dynamically
        self.fields["group_by"].choices = get_demographic_field_choices()
        # Scope report templates to programs the user can access
        if user:
            from .utils import get_manageable_programs
            accessible_programs = get_manageable_programs(user)
            self.fields["report_template"].queryset = (
                ReportTemplate.objects.filter(
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
    Form for program outcome report template export.

    This form is simpler than the full metric export form, as funder reports
    have a fixed structure. Users select a program and fiscal year,
    and the report is generated with all applicable data.
    """

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

    # Report template — selects demographic breakdown configuration
    report_template = forms.ModelChoiceField(
        queryset=ReportTemplate.objects.none(),
        required=False,
        empty_label=_("Default age categories"),
        label=_("Reporting template"),
        help_text=_(
            "Reporting templates define the demographic categories your funder requires. "
            "Select one to match a specific funder's format, or leave blank for "
            "the default age groupings."
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.contains_client_identifying_data = False
        # Scope program dropdown to programs the user can export from
        if user:
            from .utils import get_manageable_programs
            self.fields["program"].queryset = get_manageable_programs(user)
        # Build fiscal year choices dynamically
        # Funder reports require a fiscal year selection (no custom date range)
        self.fields["fiscal_year"].choices = get_fiscal_year_choices()
        # Default to current fiscal year
        self.fields["fiscal_year"].initial = str(get_current_fiscal_year())
        # Scope report templates to programs the user can access
        if user:
            from .utils import get_manageable_programs
            accessible_programs = get_manageable_programs(user)
            self.fields["report_template"].queryset = (
                ReportTemplate.objects.filter(
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

        # Validate that the selected reporting template is linked to the
        # selected program.  Without this check an executive could pick
        # a template intended for a different program, producing a report
        # with empty or misleading breakdown sections.
        report_template = cleaned.get("report_template")
        program = cleaned.get("program")
        if report_template and program:
            if not report_template.programs.filter(pk=program.pk).exists():
                self.add_error(
                    "report_template",
                    _("This reporting template is not linked to the selected program. "
                      "Choose a different template or ask an administrator to "
                      "assign this template to the program."),
                )

        return cleaned


class IndividualClientExportForm(ExportRecipientMixin, forms.Form):
    """
    Form for exporting an individual client's complete data (PIPEDA compliance).

    Under PIPEDA, individuals have the right to access all personal information
    held about them. This form lets staff export everything for one client.

    Funders are NOT a valid recipient for individual client data.
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
        self.contains_client_identifying_data = True
        self.add_recipient_fields()
