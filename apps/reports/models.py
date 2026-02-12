"""Models for the reports app — secure export link tracking and funder profiles."""
import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Funder Profile — demographic breakdown configuration uploaded as CSV
# ---------------------------------------------------------------------------

class FunderProfile(models.Model):
    """
    A funder's reporting requirements for demographic breakdowns.

    Admins create profiles by uploading a CSV (typically generated with
    Claude's help from a funder's reporting template). Each profile
    defines one or more demographic breakdowns with custom age bins
    and/or category merges.

    Executives and PMs select a profile at export time (read-only) to
    produce reports matching that funder's required categorisations.
    """

    name = models.CharField(
        max_length=255,
        help_text=_("Funder name, e.g., 'United Way Greater Toronto'."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the reporting requirements, e.g., 'Annual Community Impact Report'."),
    )
    programs = models.ManyToManyField(
        "programs.Program",
        blank=True,
        related_name="funder_profiles",
        help_text=_("Programs that report to this funder."),
    )
    source_csv = models.TextField(
        blank=True,
        help_text=_("Original uploaded CSV content, preserved for re-export and audit."),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_funder_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "funder_profiles"

    def __str__(self):
        return self.name


class DemographicBreakdown(models.Model):
    """
    One demographic dimension within a funder profile.

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

    funder_profile = models.ForeignKey(
        FunderProfile,
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
        return f"{self.funder_profile.name} — {self.label}"


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
