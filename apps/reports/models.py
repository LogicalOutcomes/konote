"""Models for the reports app — partners, report templates, and secure exports."""
import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Partner — a reporting relationship (funder, board, network, etc.)
# ---------------------------------------------------------------------------

class Partner(models.Model):
    """
    A reporting relationship between the agency and an external entity.

    Partners include funders, boards, networks, regulators, accreditation
    bodies, and donors. Each partner may require one or more report
    templates with specific metrics, demographics, and schedules.

    The term "Partner" was chosen over "Stakeholder" (colonial connotations
    in the Canadian context) and "FundingSource" (too narrow — boards and
    networks are not funders).
    """

    PARTNER_TYPES = [
        ("funder", _("Funder")),
        ("network", _("Network / Collaboration")),
        ("board", _("Board of Directors")),
        ("regulator", _("Government / Regulator")),
        ("accreditation", _("Accreditation Body")),
        ("donor", _("Donor")),
        ("other", _("Other")),
    ]

    name = models.CharField(
        max_length=255,
        help_text=_("Partner name, e.g., 'United Way Greater Toronto'."),
    )
    name_fr = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("French name (optional)."),
    )
    partner_type = models.CharField(
        max_length=20,
        choices=PARTNER_TYPES,
        help_text=_("Type of reporting relationship."),
    )
    programs = models.ManyToManyField(
        "programs.Program",
        blank=True,
        related_name="partners",
        help_text=_(
            "Programs this partner funds or oversees. "
            "Leave empty for organisation-wide partners (e.g., board)."
        ),
    )
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    grant_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Grant or contribution agreement number (if applicable)."),
    )
    grant_period_start = models.DateField(null=True, blank=True)
    grant_period_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "partners"

    def __str__(self):
        return self.name

    @property
    def translated_name(self):
        from django.utils.translation import get_language

        if get_language() == "fr" and self.name_fr:
            return self.name_fr
        return self.name

    def get_programs(self):
        """Linked programs, or all active programs if none specified."""
        programs = self.programs.all()
        if programs.exists():
            return programs
        from apps.programs.models import Program

        return Program.objects.filter(status="active")


# ---------------------------------------------------------------------------
# Report Template — complete report definition linked to a partner
# ---------------------------------------------------------------------------

class ReportTemplate(models.Model):
    """
    A complete report definition for a specific partner.

    Defines what metrics to include, how to aggregate them, what
    demographic breakdowns to apply, and the reporting period. One
    partner may have multiple templates (e.g., quarterly + annual).

    Admins can also upload CSV files to define demographic breakdowns
    (the original workflow, preserved for backward compatibility).
    """

    PERIOD_TYPES = [
        ("monthly", _("Monthly")),
        ("quarterly", _("Quarterly")),
        ("semi_annual", _("Semi-annual")),
        ("annual", _("Annual")),
        ("custom", _("Custom")),
    ]

    PERIOD_ALIGNMENTS = [
        ("calendar", _("Calendar year (Jan-Dec)")),
        ("fiscal", _("Fiscal year (custom start month)")),
        ("grant", _("Grant period")),
    ]

    OUTPUT_FORMATS = [
        ("tabular", _("Tables and charts")),
        ("narrative", _("Narrative with data")),
        ("mixed", _("Mixed — narrative and tables")),
    ]

    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="report_templates",
        help_text=_("The partner this report template belongs to."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Template name, e.g., 'Quarterly Outcomes Report'."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the reporting requirements."),
    )
    programs = models.ManyToManyField(
        "programs.Program",
        blank=True,
        related_name="report_templates",
        help_text=_("Programs linked to this reporting template."),
    )
    source_csv = models.TextField(
        blank=True,
        help_text=_("Original uploaded CSV content, preserved for re-export and audit."),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_report_templates",
    )
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPES,
        default="annual",
        help_text=_("How often this report is produced."),
    )
    period_alignment = models.CharField(
        max_length=20,
        choices=PERIOD_ALIGNMENTS,
        default="fiscal",
        help_text=_("How the reporting period aligns with the calendar."),
    )
    fiscal_year_start_month = models.PositiveSmallIntegerField(
        default=4,
        help_text=_("1=Jan, 4=Apr (Ontario govt), 7=Jul, etc."),
    )
    output_format = models.CharField(
        max_length=20,
        choices=OUTPUT_FORMATS,
        default="mixed",
    )
    language = models.CharField(
        max_length=5,
        default="en",
        choices=[("en", _("English")), ("fr", _("French")), ("both", _("Bilingual"))],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "report_templates"

    def __str__(self):
        if self.partner:
            return f"{self.name} ({self.partner.name})"
        return self.name


# ---------------------------------------------------------------------------
# Report Section — structural section within a report template
# ---------------------------------------------------------------------------

class ReportSection(models.Model):
    """
    A structural section within a report template.

    Organises report content into logical blocks (metrics tables,
    demographic summaries, narrative sections, charts). Each section
    can contain ReportMetric entries or free-form content.
    """

    SECTION_TYPES = [
        ("metrics_table", _("Metrics Table")),
        ("demographic_summary", _("Demographic Summary")),
        ("narrative", _("Narrative / Written Section")),
        ("chart", _("Chart / Visualisation")),
        ("service_stats", _("Service Statistics")),
    ]

    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    title = models.CharField(max_length=255)
    title_fr = models.CharField(max_length=255, blank=True, default="")
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    instructions = models.TextField(
        blank=True,
        help_text=_("Guidance for narrative sections (what to write about)."),
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        db_table = "report_sections"

    def __str__(self):
        return f"{self.report_template.name} — {self.title}"

    @property
    def translated_title(self):
        from django.utils.translation import get_language

        if get_language() == "fr" and self.title_fr:
            return self.title_fr
        return self.title


# ---------------------------------------------------------------------------
# Report Metric — a metric included in a report with aggregation rules
# ---------------------------------------------------------------------------

class ReportMetric(models.Model):
    """
    A metric included in a report template with specific aggregation rules.

    The same underlying MetricDefinition (e.g., 'housing stability score')
    can appear in two templates with different aggregation: average in one,
    threshold count in another. The display label can also be overridden
    to match a specific partner's terminology.
    """

    AGGREGATION_TYPES = [
        ("count", _("Count of participants")),
        ("average", _("Average value")),
        ("average_change", _("Average change (intake to latest)")),
        ("percentage", _("Percentage of participants")),
        ("threshold_count", _("Count meeting threshold")),
        ("threshold_percentage", _("Percentage meeting threshold")),
        ("sum", _("Sum total")),
    ]

    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="report_metrics",
    )
    metric_definition = models.ForeignKey(
        "plans.MetricDefinition",
        on_delete=models.CASCADE,
        related_name="report_usages",
    )
    section = models.ForeignKey(
        ReportSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="metrics",
    )
    aggregation = models.CharField(
        max_length=25,
        choices=AGGREGATION_TYPES,
        help_text=_("How this metric should be aggregated in the report."),
    )
    threshold_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("For threshold-based aggregation: the target value."),
    )
    display_label = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Override label for this partner's terminology."),
    )
    display_label_fr = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    is_consortium_required = models.BooleanField(
        default=False,
        help_text=_("Whether this metric is required by a consortium standard schema."),
    )

    class Meta:
        ordering = ["sort_order"]
        db_table = "report_metrics"

    def __str__(self):
        label = self.display_label or self.metric_definition.name
        return f"{self.report_template.name} — {label} ({self.aggregation})"

    @property
    def translated_label(self):
        from django.utils.translation import get_language

        if get_language() == "fr":
            if self.display_label_fr:
                return self.display_label_fr
            return self.metric_definition.translated_name
        return self.display_label or self.metric_definition.name


class DemographicBreakdown(models.Model):
    """
    One demographic dimension within a report template.

    Each breakdown defines how to slice client data for a single
    demographic dimension (e.g., age groups, employment status).

    For age breakdowns, bins_json defines custom age ranges.
    For custom field breakdowns, merge_categories_json optionally
    maps the field's original options into funder-required categories.
    """

    SOURCE_TYPE_CHOICES = [
        ("age", _("Age (from date of birth)")),
        ("custom_field", _("Custom intake field")),
    ]

    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="breakdowns",
    )
    label = models.CharField(
        max_length=100,
        help_text=_("Display label, e.g., 'Age Group' or 'Employment Status'."),
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
    )
    custom_field = models.ForeignKey(
        "clients.CustomFieldDefinition",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_("The intake field to group by (only for custom_field source type)."),
    )
    bins_json = models.JSONField(
        default=list,
        blank=True,
        help_text=_(
            'For age breakdowns: list of {"min": int, "max": int, "label": str}. '
            'E.g., [{"min": 0, "max": 14, "label": "Child (0-14)"}]'
        ),
    )
    merge_categories_json = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "For custom field breakdowns: map target labels to lists of source labels. "
            'E.g., {"Employed": ["Employed full-time", "Employed part-time"]}'
        ),
    )
    keep_all_categories = models.BooleanField(
        default=False,
        help_text=_("Use the field's original categories without merging."),
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        db_table = "demographic_breakdowns"

    def __str__(self):
        return f"{self.report_template.name} — {self.label}"


class SecureExportLink(models.Model):
    """
    Time-limited download link for exports.

    Instead of streaming CSV/PDF directly to the browser, exports are saved
    to a temporary file and a secure link is created. The link expires after
    24 hours and can be revoked by admins at any time.

    File storage: Files are saved to SECURE_EXPORT_DIR (outside web root).
    On Railway, this is ephemeral /tmp — files disappear on deploy, which
    is acceptable for 24-hour links.
    """

    EXPORT_TYPE_CHOICES = [
        ("client_data", _("Participant Data")),
        ("metrics", _("Metric Report")),
        ("funder_report", _("Funder Report")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="export_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    # Download tracking
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    last_downloaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="downloaded_exports",
    )

    # What was exported
    export_type = models.CharField(max_length=50, choices=EXPORT_TYPE_CHOICES)
    filters_json = models.TextField(default="{}")
    client_count = models.PositiveIntegerField()
    includes_notes = models.BooleanField(default=False)
    recipient = models.CharField(max_length=200)
    filename = models.CharField(max_length=255, default="export.csv")

    # PII tracking — True when export contains individual client data
    # (record IDs, names, per-client metric rows, author names).
    # Used by download_export() to re-validate that the downloader still
    # has permission to access individual data (defense-in-depth).
    # DEFAULT=TRUE (deny by default): any export that forgets to set this
    # is treated as containing PII. Only explicitly aggregate exports
    # should set contains_pii=False.
    contains_pii = models.BooleanField(default=True)

    # Elevated export tracking (Phase 4 — fields added now for forward compat)
    is_elevated = models.BooleanField(default=False)
    admin_notified_at = models.DateTimeField(null=True, blank=True)

    # Manual revocation
    revoked = models.BooleanField(default=False)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="revoked_exports",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    # File location (not web-accessible)
    file_path = models.CharField(max_length=500)

    def is_valid(self):
        """Check if link is still usable (no I/O — checks DB state only)."""
        if self.revoked:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True

    @property
    def is_available(self):
        """Check if the export can be downloaded (delay period passed for elevated)."""
        if not self.is_elevated:
            return True
        delay = getattr(settings, "ELEVATED_EXPORT_DELAY_MINUTES", 10)
        return timezone.now() >= self.created_at + timedelta(minutes=delay)

    @property
    def available_at(self):
        """When this export becomes downloadable. None if already available."""
        if not self.is_elevated:
            return None
        delay = getattr(settings, "ELEVATED_EXPORT_DELAY_MINUTES", 10)
        return self.created_at + timedelta(minutes=delay)

    @property
    def file_exists(self):
        """Check if the export file is still on disk."""
        return self.file_path and os.path.exists(self.file_path)

    @property
    def status_display(self):
        """Human-readable status for admin views."""
        if self.revoked:
            return "Revoked"
        if timezone.now() > self.expires_at:
            return "Expired"
        if not self.file_exists:
            return "File Missing"
        if self.is_elevated and not self.is_available:
            return "Pending"
        return "Active"

    def __str__(self):
        return f"{self.export_type} by {self.created_by} ({self.status_display})"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["expires_at"]),
            models.Index(fields=["created_by", "created_at"]),
        ]


class InsightSummary(models.Model):
    """Cached AI-generated insight summary for Outcome Insights.

    Stores the validated AI response so the same summary can be revisited
    without re-calling the API. Users see the generation timestamp and
    can click "Regenerate" to refresh.
    """

    cache_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Format: insights:{program_id}:{date_from}:{date_to} or "
                  "insights:client:{client_id}:{date_from}:{date_to}",
    )
    summary_json = models.JSONField(
        help_text="Full validated AI response: summary, themes, cited_quotes, recommendations.",
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_insights",
    )

    class Meta:
        db_table = "insight_summaries"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Insight {self.cache_key} ({self.generated_at:%Y-%m-%d})"
