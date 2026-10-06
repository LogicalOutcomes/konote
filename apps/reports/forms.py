"""Forms for the reports app — metric export filtering, report templates, and individual client export."""
import calendar
from datetime import date

from django import forms
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext

from apps.programs.models import Program
from apps.plans.models import MetricDefinition
from .demographics import get_demographic_field_choices
from .models import Partner, ReportTemplate
from .utils import (
    get_fiscal_year_choices, get_fiscal_year_range, get_current_fiscal_year,
    get_quarter_choices, get_quarter_range,
    is_aggregate_only_user,
)


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


class ProgramSelectionMixin:
    """Shared logic for forms with a program dropdown that supports 'All Programs'.

    Provides:
    - ALL_PROGRAMS_VALUE sentinel constant
    - _setup_program_choices(user) to build the dropdown
    - clean_program() with RBAC validation
    - is_all_programs property
    - PDF format rejection when All Programs is selected
    """

    ALL_PROGRAMS_VALUE = "__all__"

    def _setup_program_choices(self, user):
        """Build program dropdown choices and store user for RBAC validation."""
        self._user = user
        if user:
            from .utils import get_manageable_programs
            programs = get_manageable_programs(user)
        else:
            programs = Program.objects.filter(status="active")
        program_choices = [("", _("\u2014 Select a program \u2014"))]
        if programs.count() > 1:
            program_choices.append(
                (self.ALL_PROGRAMS_VALUE, _("All Programs \u2014 Organisation Summary"))
            )
        for p in programs.order_by("name"):
            program_choices.append((str(p.pk), str(p)))
        self.fields["program"].choices = program_choices

    def clean_program(self):
        """Validate the program selection.

        Returns a Program instance for single-program exports, or None
        for the "All Programs" sentinel (organisation-wide summary).
        """
        value = self.cleaned_data.get("program", "")
        if value == self.ALL_PROGRAMS_VALUE:
            return None  # Sentinel: all accessible programs
        if not value:
            raise forms.ValidationError(_("Please select a program."))
        try:
            program = Program.objects.get(pk=int(value), status="active")
        except (Program.DoesNotExist, ValueError, TypeError):
            raise forms.ValidationError(_("Invalid program selection."))
        # RBAC: verify user has access to this program
        if self._user:
            from .utils import get_manageable_programs
            if not get_manageable_programs(self._user).filter(pk=program.pk).exists():
                raise forms.ValidationError(_("You do not have access to this program."))
        return program

    @property
    def is_all_programs(self):
        """Return True if the user selected the 'All Programs' option."""
        if hasattr(self, "cleaned_data"):
            return self.cleaned_data.get("program") is None
        return False

    def _validate_all_programs_format(self, cleaned):
        """Reject PDF format when All Programs is selected (CSV only)."""
        if cleaned.get("program") is None and cleaned.get("format") == "pdf":
            self.add_error(
                "format",
                _("PDF export is not available for All Programs. Please select CSV or HTML."),
            )


class MetricExportForm(ProgramSelectionMixin, ExportRecipientMixin, forms.Form):
    """Filter form for the aggregate metric CSV export."""

    # Sentinel value for "All Programs" in the ChoiceField
    ALL_PROGRAMS_VALUE = "__all__"

    program = forms.ChoiceField(
        required=True,
        label=_("Program"),
    )

    # Period quick-select (optional — overrides manual dates when selected)
    fiscal_year = forms.ChoiceField(
        required=False,
        label=_("Period"),
        help_text=_("Select a fiscal year or quarter to auto-fill dates, or leave blank for custom range."),
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
        empty_label=_("None — use grouping below"),
        label=_("Reporting template"),
        help_text=_(
            "Your admin sets these up to match a specific partner's reporting format "
            "(e.g., age brackets, employment categories). Pick one to format your "
            "export the way that partner expects. You can preview what each template "
            "includes below."
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.contains_client_identifying_data = bool(user and not is_aggregate_only_user(user))
        # Consortium-required metric IDs (locked checkboxes in template)
        self.consortium_locked_metrics = set()
        self.consortium_partner_name = ""
        # Store user for clean_program RBAC validation
        self._user = user
        # Build program choices: "All Programs" sentinel + individual programs
        if user:
            from .utils import get_manageable_programs
            programs = get_manageable_programs(user)
        else:
            programs = Program.objects.filter(status="active")
        program_choices = [("", _("\u2014 Select a program \u2014"))]
        # Only show "All Programs" when user has access to more than one program
        if programs.count() > 1:
            program_choices.append(
                (self.ALL_PROGRAMS_VALUE, _("All Programs \u2014 Organisation Summary"))
            )
        for p in programs.order_by("name"):
            program_choices.append((str(p.pk), str(p)))
        self.fields["program"].choices = program_choices
        # Build period choices: blank + fiscal years + quarters (as optgroups)
        period_choices = [
            ("", _("\u2014 Custom date range \u2014")),
            (_("Fiscal Years"), get_fiscal_year_choices()),
            (_("Quarters"), get_quarter_choices()),
        ]
        self.fields["fiscal_year"].choices = period_choices
        # Build demographic grouping choices dynamically
        self.fields["group_by"].choices = get_demographic_field_choices()
        # Scope report templates to programs the user can access (through partner)
        if user:
            from .utils import get_manageable_programs
            accessible_programs = get_manageable_programs(user)
            template_qs = (
                ReportTemplate.objects.filter(
                    partner__programs__in=accessible_programs
                ).distinct().order_by("name")
            )
            if template_qs.exists():
                self.fields["report_template"].queryset = template_qs
            else:
                del self.fields["report_template"]
        else:
            del self.fields["report_template"]
        # Build consortium-required metric IDs from POST data
        if self.data.get("report_template"):
            try:
                template_id = int(self.data["report_template"])
                from .models import ReportMetric as RM
                locked = RM.objects.filter(
                    report_template_id=template_id,
                    is_consortium_required=True,
                ).select_related("metric_definition", "report_template__partner")
                for rm in locked:
                    self.consortium_locked_metrics.add(rm.metric_definition_id)
                    if not self.consortium_partner_name:
                        self.consortium_partner_name = (
                            rm.report_template.partner.translated_name
                        )
            except (ValueError, TypeError):
                pass
        # Add recipient tracking fields for audit purposes
        self.add_recipient_fields()

    FORMAT_CHOICES = [
        ("csv", _("CSV (spreadsheet)")),
        ("pdf", _("PDF (printable report)")),
        ("html", _("HTML (shareable web page)")),
        ("cids_json", _("CIDS JSON-LD (Common Approach)")),
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

    def clean_program(self):
        """Validate the program selection.

        Returns a Program instance for single-program exports, or None
        for the "All Programs" sentinel (organisation-wide summary).
        """
        value = self.cleaned_data.get("program", "")
        if value == self.ALL_PROGRAMS_VALUE:
            return None  # Sentinel: all accessible programs
        if not value:
            raise forms.ValidationError(_("Please select a program."))
        try:
            program = Program.objects.get(pk=int(value), status="active")
        except (Program.DoesNotExist, ValueError, TypeError):
            raise forms.ValidationError(_("Invalid program selection."))
        # RBAC: verify user has access to this program
        if self._user:
            from .utils import get_manageable_programs
            if not get_manageable_programs(self._user).filter(pk=program.pk).exists():
                raise forms.ValidationError(_("You do not have access to this program."))
        return program

    @property
    def is_all_programs(self):
        """Return True if the user selected the 'All Programs' option."""
        if hasattr(self, "cleaned_data"):
            return self.cleaned_data.get("program") is None
        return False

    def clean(self):
        cleaned = super().clean()
        self._validate_all_programs_format(cleaned)
        fiscal_year = cleaned.get("fiscal_year")
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")

        # If a period preset is selected, use those dates instead of manual entry
        if fiscal_year:
            if fiscal_year.startswith("Q"):
                # Quarter preset, e.g. "Q1-2025"
                try:
                    q_str, fy_str = fiscal_year.split("-")
                    q_num = int(q_str[1:])
                    fy_start_year = int(fy_str)
                    date_from, date_to = get_quarter_range(q_num, fy_start_year)
                    cleaned["date_from"] = date_from
                    cleaned["date_to"] = date_to
                except (ValueError, IndexError, KeyError):
                    raise forms.ValidationError(_("Invalid quarter selection."))
            else:
                # Fiscal year preset
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

        # Ensure consortium-required metrics cannot be deselected
        if self.consortium_locked_metrics:
            selected = set(
                m.pk for m in cleaned.get("metrics", [])
            )
            missing = self.consortium_locked_metrics - selected
            if missing:
                # Force-add them back
                from apps.plans.models import MetricDefinition
                locked_defs = MetricDefinition.objects.filter(pk__in=missing)
                cleaned["metrics"] = list(cleaned.get("metrics", [])) + list(locked_defs)

        return cleaned


class FunderReportForm(ProgramSelectionMixin, ExportRecipientMixin, forms.Form):
    """
    Form for program outcome report template export.

    This form is simpler than the full metric export form, as funder reports
    have a fixed structure. Users select a program and fiscal year,
    and the report is generated with all applicable data.
    """

    # Sentinel value for "All Programs" in the ChoiceField
    ALL_PROGRAMS_VALUE = "__all__"

    program = forms.ChoiceField(
        required=True,
        label=_("Program"),
    )

    fiscal_year = forms.ChoiceField(
        required=True,
        label=_("Fiscal Year (April-March)"),
        help_text=_("Select the fiscal year to report on."),
    )

    FORMAT_CHOICES = [
        ("csv", _("CSV (spreadsheet)")),
        ("pdf", _("PDF (printable report)")),
        ("html", _("HTML (shareable web page)")),
        ("cids_json", _("CIDS JSON-LD (Common Approach)")),
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
        empty_label=_("None \u2014 use default age categories"),
        label=_("Reporting template"),
        help_text=_(
            "Your admin sets these up to match a specific partner's reporting format "
            "(e.g., age brackets, employment categories). Pick one to format your "
            "report the way that partner expects. You can preview what each template "
            "includes below."
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.contains_client_identifying_data = False
        # Store user for clean_program RBAC validation
        self._user = user
        # Build program choices: "All Programs" sentinel + individual programs
        if user:
            from .utils import get_manageable_programs
            programs = get_manageable_programs(user)
        else:
            programs = Program.objects.filter(status="active")
        program_choices = [("", _("\u2014 Select a program \u2014"))]
        # Only show "All Programs" when user has access to more than one program
        if programs.count() > 1:
            program_choices.append(
                (self.ALL_PROGRAMS_VALUE, _("All Programs \u2014 Organisation Summary"))
            )
        for p in programs.order_by("name"):
            program_choices.append((str(p.pk), str(p)))
        self.fields["program"].choices = program_choices
        # Build fiscal year choices dynamically
        # Funder reports require a fiscal year selection (no custom date range)
        self.fields["fiscal_year"].choices = get_fiscal_year_choices()
        # Default to current fiscal year
        self.fields["fiscal_year"].initial = str(get_current_fiscal_year())
        # Scope report templates to programs the user can access (through partner)
        if user:
            from .utils import get_manageable_programs
            accessible_programs = get_manageable_programs(user)
            template_qs = (
                ReportTemplate.objects.filter(
                    partner__programs__in=accessible_programs
                ).distinct().order_by("name")
            )
            if template_qs.exists():
                self.fields["report_template"].queryset = template_qs
            else:
                del self.fields["report_template"]
        else:
            del self.fields["report_template"]
        # Add recipient tracking fields for audit purposes
        self.add_recipient_fields()

    def clean_program(self):
        """Validate the program selection.

        Returns a Program instance for single-program reports, or None
        for the "All Programs" sentinel (organisation-wide summary).
        """
        value = self.cleaned_data.get("program", "")
        if value == self.ALL_PROGRAMS_VALUE:
            return None  # Sentinel: all accessible programs
        if not value:
            raise forms.ValidationError(_("Please select a program."))
        try:
            program = Program.objects.get(pk=int(value), status="active")
        except (Program.DoesNotExist, ValueError, TypeError):
            raise forms.ValidationError(_("Invalid program selection."))
        # RBAC: verify user has access to this program
        if self._user:
            from .utils import get_manageable_programs
            if not get_manageable_programs(self._user).filter(pk=program.pk).exists():
                raise forms.ValidationError(_("You do not have access to this program."))
        return program

    @property
    def is_all_programs(self):
        """Return True if the user selected the 'All Programs' option."""
        if hasattr(self, "cleaned_data"):
            return self.cleaned_data.get("program") is None
        return False

    def clean(self):
        cleaned = super().clean()
        self._validate_all_programs_format(cleaned)
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
        # selected program (through partner).  Without this check an
        # executive could pick a template intended for a different
        # program, producing a report with empty or misleading breakdown
        # sections.
        # Skip this validation for "All Programs" — templates apply across all.
        report_template = cleaned.get("report_template")
        program = cleaned.get("program")
        if report_template and program:
            partner = report_template.partner
            if not partner or not partner.programs.filter(pk=program.pk).exists():
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
        ("json", _("JSON (machine-readable)")),
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


class PartnerForm(forms.ModelForm):
    """Form for creating and editing reporting partners."""

    class Meta:
        model = Partner
        fields = [
            "name",
            "name_fr",
            "partner_type",
            "contact_name",
            "contact_email",
            "grant_number",
            "grant_period_start",
            "grant_period_end",
            "is_active",
            "notes",
        ]
        labels = {
            "name": _("Partner name"),
            "name_fr": _("Partner name (French)"),
            "partner_type": _("Type"),
            "contact_name": _("Contact name"),
            "contact_email": _("Contact email"),
            "grant_number": _("Grant / agreement number"),
            "grant_period_start": _("Grant period start"),
            "grant_period_end": _("Grant period end"),
            "is_active": _("Active"),
            "notes": _("Notes"),
        }
        widgets = {
            "grant_period_start": forms.DateInput(attrs={"type": "date"}),
            "grant_period_end": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].initial = True

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("grant_period_start")
        end = cleaned.get("grant_period_end")
        if start and end and start > end:
            raise forms.ValidationError(
                _("Grant period start must be before grant period end.")
            )
        return cleaned


# ---------------------------------------------------------------------------
# Template-driven report generation (DRR: reporting-architecture.md)
# ---------------------------------------------------------------------------


def _get_period_start_month(template):
    """Determine the year/period start month based on template alignment."""
    if template.period_alignment == "fiscal":
        return template.fiscal_year_start_month or 4  # Default: April
    elif template.period_alignment == "calendar":
        return 1
    elif template.period_alignment == "grant":
        partner = template.partner
        if partner and partner.grant_period_start:
            return partner.grant_period_start.month
        return template.fiscal_year_start_month or 4  # Fallback to fiscal
    return 4


def _fiscal_year_label(start_month, year, month):
    """Return e.g. 'FY2025-26' for fiscal years, or just '2026' for calendar."""
    if start_month == 1:
        return str(year)
    # Determine the fiscal year that contains this month
    if month >= start_month:
        fy_start = year
    else:
        fy_start = year - 1
    fy_end_short = str(fy_start + 1)[-2:]
    return f"FY{fy_start}-{fy_end_short}"


def build_period_choices(template):
    """
    Build (value, label) choices for the period dropdown.

    Value format: "YYYY-MM-DD|YYYY-MM-DD" (pipe-delimited start|end dates).
    Returns empty list for custom period_type (uses raw date inputs instead).
    """
    today = date.today()

    if template.period_type == "custom":
        return []

    start_month = _get_period_start_month(template)

    if template.period_type == "monthly":
        choices = []
        for i in range(12):
            m = today.month - i
            y = today.year
            while m < 1:
                m += 12
                y -= 1
            last_day = calendar.monthrange(y, m)[1]
            start = date(y, m, 1)
            end = date(y, m, last_day)
            label = date_format(start, "N Y")
            choices.append((f"{start}|{end}", label))
        return choices

    if template.period_type == "quarterly":
        return _build_quarter_choices(start_month, today, count=8)

    if template.period_type == "semi_annual":
        return _build_half_choices(start_month, today, count=4)

    if template.period_type == "annual":
        return _build_annual_choices(start_month, today, count=5)

    return []


def _build_quarter_choices(start_month, today, count=8):
    """Build quarterly period choices working backwards from today."""
    choices = []

    # Find which quarter we're currently in
    # Quarters are relative to start_month
    months_into_year = (today.month - start_month) % 12
    current_q = months_into_year // 3  # 0-indexed quarter
    # Start of current quarter
    q_month = start_month + current_q * 3
    q_year = today.year
    if today.month < start_month:
        q_year -= 1
    # Normalise month overflow
    while q_month > 12:
        q_month -= 12
        q_year += 1

    for _ in range(count):
        q_start = date(q_year, q_month, 1)
        # End is last day of the 3rd month of the quarter
        end_month = q_month + 2
        end_year = q_year
        while end_month > 12:
            end_month -= 12
            end_year += 1
        last_day = calendar.monthrange(end_year, end_month)[1]
        q_end = date(end_year, end_month, last_day)

        # Quarter number (1-4)
        q_num = ((q_month - start_month) % 12) // 3 + 1
        fy_label = _fiscal_year_label(start_month, q_year, q_month)

        # Month abbreviations for the quarter
        m1 = date_format(date(q_year, q_month, 1), "M")
        m3 = date_format(date(end_year, end_month, 1), "M")
        label = f"Q{q_num} {fy_label} ({m1}\u2013{m3})"

        choices.append((f"{q_start}|{q_end}", label))

        # Move back one quarter
        q_month -= 3
        if q_month < 1:
            q_month += 12
            q_year -= 1

    return choices


def _build_half_choices(start_month, today, count=4):
    """Build semi-annual period choices working backwards from today."""
    choices = []

    months_into_year = (today.month - start_month) % 12
    current_h = months_into_year // 6  # 0 or 1
    h_month = start_month + current_h * 6
    h_year = today.year
    if today.month < start_month:
        h_year -= 1
    while h_month > 12:
        h_month -= 12
        h_year += 1

    for _ in range(count):
        h_start = date(h_year, h_month, 1)
        end_month = h_month + 5
        end_year = h_year
        while end_month > 12:
            end_month -= 12
            end_year += 1
        last_day = calendar.monthrange(end_year, end_month)[1]
        h_end = date(end_year, end_month, last_day)

        h_num = ((h_month - start_month) % 12) // 6 + 1
        fy_label = _fiscal_year_label(start_month, h_year, h_month)
        m1 = date_format(date(h_year, h_month, 1), "M")
        m6 = date_format(date(end_year, end_month, 1), "M")
        label = f"H{h_num} {fy_label} ({m1}\u2013{m6})"

        choices.append((f"{h_start}|{h_end}", label))

        h_month -= 6
        if h_month < 1:
            h_month += 12
            h_year -= 1

    return choices


def _build_annual_choices(start_month, today, count=5):
    """Build annual period choices working backwards from today."""
    choices = []

    # Start from current year (fiscal year perspective)
    y = today.year
    if today.month < start_month:
        y -= 1

    for _ in range(count):
        y_start = date(y, start_month, 1)
        end_month = start_month - 1 if start_month > 1 else 12
        end_year = y + 1 if start_month > 1 else y
        last_day = calendar.monthrange(end_year, end_month)[1]
        y_end = date(end_year, end_month, last_day)

        fy_label = _fiscal_year_label(start_month, y, start_month)
        choices.append((f"{y_start}|{y_end}", fy_label))

        y -= 1

    return choices


def parse_period_value(value, template):
    """
    Parse a period dropdown value back to (date_from, date_to, label).

    Values are pipe-delimited: "YYYY-MM-DD|YYYY-MM-DD".
    """
    if not value or "|" not in value:
        raise ValueError(gettext("Invalid period selection."))
    parts = value.split("|")
    if len(parts) != 2:
        raise ValueError(gettext("Invalid period selection."))
    try:
        date_from = date.fromisoformat(parts[0])
        date_to = date.fromisoformat(parts[1])
    except (ValueError, TypeError):
        raise ValueError(gettext("Invalid period dates."))
    if date_from > date_to:
        raise ValueError(gettext("Period start must be before end."))
    # Find the matching label from choices
    choices = build_period_choices(template)
    label = f"{date_from} {gettext('to')} {date_to}"  # Fallback
    for choice_val, choice_label in choices:
        if choice_val == value:
            label = choice_label
            break
    return date_from, date_to, label


class TemplateExportForm(ExportRecipientMixin, forms.Form):
    """
    Template-driven report generation form.

    The user selects a report template and a period; the template defines
    which programs, metrics, demographics, and aggregation rules to use.
    No program dropdown, no metric checkboxes.

    Used at /reports/generate/ — accessible to executives, PMs, and admins.
    See tasks/design-rationale/reporting-architecture.md for full specification.
    """

    report_template = forms.ModelChoiceField(
        queryset=ReportTemplate.objects.none(),
        required=True,
        label=_("Which report?"),
        empty_label=_("\u2014 Select a report \u2014"),
    )

    period = forms.ChoiceField(
        required=False,
        label=_("Which period?"),
        choices=[],
    )

    # For custom period_type only
    date_from = forms.DateField(
        required=False,
        label=_("Date from"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        label=_("Date to"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    FORMAT_CHOICES = [
        ("csv", _("CSV (spreadsheet)")),
        ("pdf", _("PDF (printable report)")),
        ("html", _("HTML (shareable web page)")),
        ("cids_json", _("CIDS JSON-LD (Common Approach)")),
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
        self.contains_client_identifying_data = False  # Always aggregate

        # Scope templates to those linked to programs the user can access
        if user:
            from .utils import get_manageable_programs
            accessible_programs = get_manageable_programs(user)
            template_qs = (
                ReportTemplate.objects.filter(
                    is_active=True,
                    partner__programs__in=accessible_programs,
                )
                .select_related("partner")
                .distinct()
                .order_by("partner__name", "name")
            )
            self.fields["report_template"].queryset = template_qs
            self.fields["report_template"].label_from_instance = (
                lambda obj: (
                    obj.name
                    if obj.partner and obj.partner.translated_name in obj.name
                    else f"{obj.partner.translated_name} \u2014 {obj.name}"
                    if obj.partner
                    else obj.name
                )
            )

        # On POST, populate period choices from the submitted template
        # so Django validation can find the selected value in the choices list.
        template_id = None
        if args and args[0]:  # POST data
            template_id = args[0].get("report_template")

        if template_id:
            try:
                template_obj = ReportTemplate.objects.select_related("partner").get(
                    pk=template_id
                )
                self.fields["period"].choices = build_period_choices(template_obj)
                # Constrain format if template specifies
                if template_obj.output_format == "tabular":
                    self.fields["format"].choices = [
                        ("csv", _("CSV (spreadsheet)")),
                        ("cids_json", _("CIDS JSON-LD (Common Approach)")),
                    ]
                    self.fields["format"].initial = "csv"
                elif template_obj.output_format == "narrative":
                    self.fields["format"].choices = [
                        ("pdf", _("PDF (printable report)")),
                        ("cids_json", _("CIDS JSON-LD (Common Approach)")),
                    ]
                    self.fields["format"].initial = "pdf"
            except ReportTemplate.DoesNotExist:
                pass

        self.add_recipient_fields()

    def clean(self):
        cleaned = super().clean()
        template = cleaned.get("report_template")

        if not template:
            return cleaned

        if template.period_type == "custom":
            # Custom period uses raw date fields
            df = cleaned.get("date_from")
            dt = cleaned.get("date_to")
            if not df:
                self.add_error("date_from", _("This field is required for a custom date range."))
            if not dt:
                self.add_error("date_to", _("This field is required for a custom date range."))
            if df and dt and df > dt:
                raise forms.ValidationError(_("'Date from' must be before 'Date to'."))
            if df and dt:
                cleaned["period_label"] = f"{df} to {dt}"
        else:
            # Parse the selected period value to date_from / date_to
            period_val = cleaned.get("period")
            if not period_val:
                self.add_error("period", _("Please select a reporting period."))
                return cleaned
            try:
                df, dt, label = parse_period_value(period_val, template)
                cleaned["date_from"] = df
                cleaned["date_to"] = dt
                cleaned["period_label"] = label
            except ValueError as e:
                self.add_error("period", str(e))

        return cleaned


# ---------------------------------------------------------------------------
# Safety Oversight Report forms
# ---------------------------------------------------------------------------

class OversightReportForm(forms.Form):
    """Form for generating a safety oversight report."""

    period = forms.ChoiceField(
        label=_("Reporting Period"),
        choices=[],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["period"].choices = self._build_quarter_choices()

    @staticmethod
    def _build_quarter_choices():
        """Return (value, label) tuples for last 4 quarters."""
        import datetime

        today = datetime.date.today()
        choices = []
        # Start from the current quarter and go back 4
        year = today.year
        quarter = (today.month - 1) // 3 + 1

        for _ in range(4):
            label = f"Q{quarter} {year}"
            choices.append((label, label))
            quarter -= 1
            if quarter < 1:
                quarter = 4
                year -= 1

        return choices


class OversightApproveForm(forms.Form):
    """Attestation form for approving a safety oversight report."""

    narrative = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": _("Add management observations if applicable...")}),
        label=_("Management Observations"),
    )
    confirm = forms.BooleanField(
        required=True,
        label=_("I confirm this report has been reviewed and is ready to file."),
    )


class ReportScheduleForm(forms.ModelForm):
    """Form for creating or editing a report schedule."""

    class Meta:
        from .models import ReportSchedule

        model = ReportSchedule
        fields = [
            "name", "report_type", "frequency", "due_date",
            "reminder_days_before",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Wire up aria-describedby for fields with errors (after validation)
        for field_name in self.errors:
            if field_name in self.fields:
                widget = self.fields[field_name].widget
                widget.attrs["aria-invalid"] = "true"
                widget.attrs["aria-describedby"] = f"id_{field_name}_error"


# ---------------------------------------------------------------------------
# Sessions by Participant report form (REP-SESS1)
# ---------------------------------------------------------------------------

class SessionReportForm(ProgramSelectionMixin, ExportRecipientMixin, forms.Form):
    """Form for generating a Sessions by Participant report.

    Users select a program and date range. The report aggregates session
    data from ProgressNote records, grouped by participant.

    Accessible to program managers and admins.
    See tasks/session-reporting-research.md for requirements.
    """

    program = forms.ChoiceField(
        required=True,
        label=_("Program"),
    )

    fiscal_year = forms.ChoiceField(
        required=False,
        label=_("Period"),
        help_text=_("Select a fiscal year or quarter to auto-fill dates, or leave blank for custom range."),
    )

    date_from = forms.DateField(
        required=False,
        label=_("Date from"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        label=_("Date to"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.contains_client_identifying_data = True
        self._setup_program_choices(user)
        # Build period choices
        period_choices = [
            ("", _("\u2014 Custom date range \u2014")),
            (_("Fiscal Years"), get_fiscal_year_choices()),
            (_("Quarters"), get_quarter_choices()),
        ]
        self.fields["fiscal_year"].choices = period_choices
        # Add recipient tracking fields
        self.add_recipient_fields()

    def clean(self):
        cleaned = super().clean()
        fiscal_year = cleaned.get("fiscal_year")
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")

        # If a period preset is selected, use those dates
        if fiscal_year:
            if fiscal_year.startswith("Q"):
                try:
                    q_str, fy_str = fiscal_year.split("-")
                    q_num = int(q_str[1:])
                    fy_start_year = int(fy_str)
                    date_from, date_to = get_quarter_range(q_num, fy_start_year)
                    cleaned["date_from"] = date_from
                    cleaned["date_to"] = date_to
                except (ValueError, IndexError, KeyError):
                    raise forms.ValidationError(_("Invalid quarter selection."))
            else:
                try:
                    fy_start_year = int(fiscal_year)
                    date_from, date_to = get_fiscal_year_range(fy_start_year)
                    cleaned["date_from"] = date_from
                    cleaned["date_to"] = date_to
                except (ValueError, TypeError):
                    raise forms.ValidationError(_("Invalid fiscal year selection."))
        else:
            if not date_from:
                self.add_error("date_from", _("This field is required when not using a fiscal year."))
            if not date_to:
                self.add_error("date_to", _("This field is required when not using a fiscal year."))

        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(_("'Date from' must be before 'Date to'."))

        return cleaned


class FunderReportApprovalForm(forms.Form):
    """Form for the funder report preview/approval step (RPT-APPROVE1).

    Captures optional agency notes before the report is approved and exported.
    """

    agency_notes = forms.CharField(
        required=False,
        label=_("Agency Notes"),
        help_text=_(
            "Optional context notes to accompany this report. "
            "For example: explain outlier values or unusual patterns."
        ),
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": _("e.g., Q1 debt figures include a large legal settlement for one participant. This is accurate, not a data entry error."),
        }),
    )


# ---------------------------------------------------------------------------
# Evaluation Microdata Export (DRR: evaluation-microdata-export.md)
# ---------------------------------------------------------------------------


class EvaluationExportForm(ProgramSelectionMixin, forms.Form):
    """Form for generating de-identified evaluation microdata exports.

    Captures: program, reporting period, evaluator details (for audit),
    and quasi-identifier column selection.  All evaluator fields are
    required — they are stored in the immutable audit log, not in a
    separate model.

    Access is restricted to users with the report.evaluation_export
    permission (checked in the view, not the form).
    """

    program = forms.ChoiceField(
        required=True,
        label=_("Program"),
    )

    period_start = forms.DateField(
        required=True,
        label=_("Period start"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    period_end = forms.DateField(
        required=True,
        label=_("Period end"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    # Evaluator details — all required for audit trail
    evaluator_name = forms.CharField(
        max_length=200,
        label=_("Evaluator name"),
    )
    evaluator_email = forms.EmailField(
        label=_("Evaluator email"),
    )
    evaluator_organisation = forms.CharField(
        max_length=200,
        label=_("Evaluator organisation"),
    )
    evaluation_purpose = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        label=_("Evaluation purpose"),
        help_text=_("Describe the evaluation and how the data will be used."),
    )
    agreement_expiry = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Data sharing agreement expiry"),
        help_text=_("When does the data sharing agreement with this evaluator expire?"),
    )

    # Quasi-identifier column selection (checkboxes)
    include_age_group = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Age group"),
        help_text=_("5-year age bands (e.g., 25-29, 30-34)"),
    )
    include_gender = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Gender"),
    )
    include_ethnicity = forms.BooleanField(
        required=False,
        label=_("Ethnicity"),
    )
    include_geography = forms.BooleanField(
        required=False,
        label=_("Geography"),
        help_text=_("Urban / Rural (derived from postal code)"),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Use mixin's program setup but without "All Programs" option
        self._user = user
        if user:
            from .utils import get_manageable_programs
            programs = get_manageable_programs(user)
        else:
            programs = Program.objects.filter(status="active")
        program_choices = [("", _("\u2014 Select a program \u2014"))]
        for p in programs.order_by("name"):
            program_choices.append((str(p.pk), str(p)))
        self.fields["program"].choices = program_choices

        from apps.clients.models import CustomFieldGroup
        self._custom_qi_groups = list(
            CustomFieldGroup.objects.filter(
                is_evaluation_exportable=True,
                status="active",
            ).order_by("sort_order")
        )
        for group in self._custom_qi_groups:
            field_name = f"include_cfg_{group.pk}"
            self.fields[field_name] = forms.BooleanField(
                required=False,
                label=group.title,
                help_text=_("Custom field group"),
            )

    @property
    def custom_qi_fields(self):
        """Yield the dynamically-added custom field group BoundFields."""
        for group in self._custom_qi_groups:
            field_name = f"include_cfg_{group.pk}"
            yield self[field_name]

    def clean_program(self):
        """Override mixin: evaluation exports require a single program."""
        value = self.cleaned_data.get("program", "")
        if not value or value == self.ALL_PROGRAMS_VALUE:
            raise forms.ValidationError(_("Please select a program."))
        try:
            program = Program.objects.get(pk=int(value), status="active")
        except (Program.DoesNotExist, ValueError, TypeError):
            raise forms.ValidationError(_("Invalid program selection."))
        if self._user:
            from .utils import get_manageable_programs
            if not get_manageable_programs(self._user).filter(pk=program.pk).exists():
                raise forms.ValidationError(_("You do not have access to this program."))
        return program

    def clean(self):
        cleaned = super().clean()
        period_start = cleaned.get("period_start")
        period_end = cleaned.get("period_end")
        if period_start and period_end and period_start > period_end:
            raise forms.ValidationError(_("Period start must be before period end."))
        return cleaned

    def get_qi_columns(self):
        """Return the list of selected quasi-identifier column names.

        Includes both built-in QI columns (age, gender, ethnicity, geography)
        and custom field groups marked is_evaluation_exportable.
        """
        qi = []
        if self.cleaned_data.get("include_age_group"):
            qi.append("age_group")
        if self.cleaned_data.get("include_gender"):
            qi.append("gender")
        if self.cleaned_data.get("include_ethnicity"):
            qi.append("ethnicity")
        if self.cleaned_data.get("include_geography"):
            qi.append("geography")
        # Custom field groups — use the same sanitiser as the pipeline
        # so column names match between form and CSV output.
        from apps.reports.deidentify import DeidentificationPipeline
        for group in self._custom_qi_groups:
            field_name = f"include_cfg_{group.pk}"
            if self.cleaned_data.get(field_name):
                qi.append(DeidentificationPipeline._sanitise_metric_name(group.title))
        return qi

    def get_evaluator_info(self):
        """Return evaluator details as a dict for the pipeline."""
        return {
            "name": self.cleaned_data.get("evaluator_name", ""),
            "email": self.cleaned_data.get("evaluator_email", ""),
            "organisation": self.cleaned_data.get("evaluator_organisation", ""),
            "purpose": self.cleaned_data.get("evaluation_purpose", ""),
            "agreement_expiry": self.cleaned_data.get("agreement_expiry"),
        }


class LTEExportRequestForm(ProgramSelectionMixin, forms.Form):
    """Longitudinal Trajectory Export request form.

    Strict validation — every precondition is required. The form
    rejects any submission where REB, evaluator credentials, or
    (where applicable) community governance signoff are missing or
    invalid. See tasks/design-rationale/evaluation-microdata-export.md,
    "Preconditions Enforced by the Form" for the full list and
    rationale.

    Access is restricted to users with the
    report.evaluation_export_small_population permission AND the
    agency must have at least one designated privacy officer
    (checked in the view, not the form).
    """

    ACKNOWLEDGEMENT_TEXT = _(
        "I have read the re-identification risk notice and confirm "
        "this export is for program evaluation, not research. "
        "Research-grade data access (complete microdata, unfuzzed "
        "values, demographic detail) is handled through a separate "
        "workflow and is not available through this form."
    )

    program = forms.ChoiceField(
        required=True,
        label=_("Program"),
    )

    # Period
    period_start = forms.DateField(
        required=True,
        label=_("Period start"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    period_end = forms.DateField(
        required=True,
        label=_("Period end"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    # REB
    reb_name = forms.CharField(
        max_length=200,
        label=_("REB name"),
        help_text=_("Name of the Research Ethics Board that approved this evaluation."),
    )
    reb_approval_number = forms.CharField(
        min_length=5,
        max_length=100,
        label=_("REB approval number"),
    )
    reb_approval_date = forms.DateField(
        label=_("REB approval date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    # DSA — captured for audit, not an unlock
    data_sharing_agreement_expiry = forms.DateField(
        label=_("Data sharing agreement expiry"),
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text=_(
            "When does the data sharing agreement with this evaluator expire? "
            "A signed DSA is required but does not on its own unlock LTE access."
        ),
    )

    # Evaluator credentials — structured, not free text
    evaluator_name = forms.CharField(max_length=200, label=_("Evaluator name"))
    evaluator_email = forms.EmailField(label=_("Evaluator email"))
    evaluator_organisation = forms.CharField(
        max_length=200, label=_("Evaluator organisation"),
    )
    evaluator_degree = forms.CharField(
        max_length=300,
        label=_("Evaluator degree or certification"),
    )
    evaluator_years_experience = forms.IntegerField(
        min_value=0, max_value=60,
        label=_("Evaluator years of experience"),
    )
    evaluator_prior_programs = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        min_length=50,
        label=_("Prior programs evaluated"),
        help_text=_(
            "Describe at least two prior program evaluations this evaluator "
            "has conducted. Minimum 50 characters. This becomes part of the "
            "immutable audit record."
        ),
    )

    # Destruction window
    destruction_window_days = forms.TypedChoiceField(
        coerce=int,
        choices=[(30, _("30 days")), (60, _("60 days")), (90, _("90 days"))],
        label=_("Destruction attestation window"),
        help_text=_(
            "How long after download the evaluator has to destroy the file. "
            "KoNote sends a reminder at the end of the window."
        ),
    )

    # Purpose statement
    purpose_statement = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        min_length=30,
        label=_("Purpose statement"),
        help_text=_(
            "Plain-language description of the evaluation question. "
            "Printed in the CSV metadata header and in the audit record."
        ),
    )

    # Community governance (conditionally required — see clean())
    community_reviewer_name = forms.CharField(
        max_length=200, required=False,
        label=_("Community reviewer name"),
    )
    community_reviewer_affiliation = forms.CharField(
        max_length=300, required=False,
        label=_("Community reviewer affiliation"),
    )
    community_framework_description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label=_("Community review framework description"),
        help_text=_("Required when the program's community governance flag is 'Other'."),
    )
    community_signoff_date = forms.DateField(
        required=False,
        label=_("Community signoff date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    # Acknowledgement — must be True to submit
    acknowledgement_confirmed = forms.BooleanField(
        required=True,
        label=ACKNOWLEDGEMENT_TEXT,
        error_messages={
            "required": _(
                "You must confirm the re-identification risk acknowledgement "
                "to submit an LTE request."
            ),
        },
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._user = user
        if user:
            from .utils import get_manageable_programs
            programs = get_manageable_programs(user)
        else:
            programs = Program.objects.filter(status="active")
        program_choices = [("", _("\u2014 Select a program \u2014"))]
        for p in programs.order_by("name"):
            program_choices.append((str(p.pk), str(p)))
        self.fields["program"].choices = program_choices

    def clean_program(self):
        """LTE requires a single program — no All Programs option."""
        value = self.cleaned_data.get("program", "")
        if not value or value == self.ALL_PROGRAMS_VALUE:
            raise forms.ValidationError(_("Please select a program."))
        try:
            program = Program.objects.get(pk=int(value), status="active")
        except (Program.DoesNotExist, ValueError, TypeError):
            raise forms.ValidationError(_("Invalid program selection."))
        if self._user:
            from .utils import get_manageable_programs
            if not get_manageable_programs(self._user).filter(pk=program.pk).exists():
                raise forms.ValidationError(_("You do not have access to this program."))
        return program

    def clean(self):
        cleaned = super().clean()
        period_start = cleaned.get("period_start")
        period_end = cleaned.get("period_end")
        if period_start and period_end and period_start > period_end:
            self.add_error(
                "period_end",
                _("Period end must be on or after period start."),
            )

        # REB date sanity
        reb_date = cleaned.get("reb_approval_date")
        from datetime import date as _date
        if reb_date and reb_date > _date.today():
            self.add_error(
                "reb_approval_date",
                _("REB approval date cannot be in the future."),
            )

        # DSA expiry must be in the future — no point running an LTE
        # against a DSA that has already expired.
        dsa_expiry = cleaned.get("data_sharing_agreement_expiry")
        if dsa_expiry and dsa_expiry < _date.today():
            self.add_error(
                "data_sharing_agreement_expiry",
                _("Data sharing agreement has already expired."),
            )

        # Community governance conditional validation — the program's
        # community_governance_framework flag controls which fields
        # become required.
        program = cleaned.get("program")
        if program and getattr(program, "community_governance_framework", ""):
            framework = program.community_governance_framework
            required = [
                "community_reviewer_name",
                "community_reviewer_affiliation",
                "community_signoff_date",
            ]
            if framework == "other":
                required.append("community_framework_description")
            for field_name in required:
                if not cleaned.get(field_name):
                    self.add_error(
                        field_name,
                        _(
                            "Required for programs with a "
                            "community governance framework."
                        ),
                    )

            # Signoff date must not be in the future
            signoff = cleaned.get("community_signoff_date")
            if signoff and signoff > _date.today():
                self.add_error(
                    "community_signoff_date",
                    _("Community signoff date cannot be in the future."),
                )

        return cleaned

    def get_evaluator_info(self):
        """Return evaluator + preconditions dict for the LTE pipeline."""
        return {
            "name": self.cleaned_data.get("evaluator_name", ""),
            "email": self.cleaned_data.get("evaluator_email", ""),
            "organisation": self.cleaned_data.get("evaluator_organisation", ""),
            "degree": self.cleaned_data.get("evaluator_degree", ""),
            "years_experience": self.cleaned_data.get("evaluator_years_experience", 0),
            "prior_programs": self.cleaned_data.get("evaluator_prior_programs", ""),
            "purpose": self.cleaned_data.get("purpose_statement", ""),
            "reb_name": self.cleaned_data.get("reb_name", ""),
            "reb_approval_number": self.cleaned_data.get("reb_approval_number", ""),
            "reb_approval_date": self.cleaned_data.get("reb_approval_date"),
            "agreement_expiry": self.cleaned_data.get("data_sharing_agreement_expiry"),
            "destruction_window_days": self.cleaned_data.get("destruction_window_days"),
            "community_reviewer_name": self.cleaned_data.get("community_reviewer_name", ""),
            "community_reviewer_affiliation": self.cleaned_data.get(
                "community_reviewer_affiliation", "",
            ),
            "community_framework_description": self.cleaned_data.get(
                "community_framework_description", "",
            ),
            "community_signoff_date": self.cleaned_data.get("community_signoff_date"),
        }
