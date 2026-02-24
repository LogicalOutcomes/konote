"""Offline field data collection configuration and sync tracking.

Manages per-program ODK Central integration settings and records
sync history for audit and troubleshooting.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProgramFieldConfig(models.Model):
    """Per-program configuration for offline field data collection.

    Each program can independently enable field collection and choose
    which forms are available and what PII tier to use.
    """

    TIER_CHOICES = [
        ("restricted", _("Restricted — ID only")),
        ("standard", _("Standard — ID + first name")),
        ("field", _("Field — ID + first name + last initial")),
        ("field_contact", _("Field+Contact — ID + name + last initial + phone")),
    ]

    PROFILE_CHOICES = [
        ("group", _("Group Programs — session attendance")),
        ("home_visiting", _("Home Visiting — visit notes")),
        ("circle", _("Circle Programs — visit notes + circle observations")),
        ("full_field", _("Full Field — all forms")),
    ]

    program = models.OneToOneField(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="field_config",
    )
    enabled = models.BooleanField(
        default=False,
        help_text=_("Enable offline field data collection for this program."),
    )
    data_tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default="standard",
        help_text=_(
            "Controls what participant data is available on field devices. "
            "Higher tiers expose more PII and require stricter device policies."
        ),
    )
    profile = models.CharField(
        max_length=20,
        choices=PROFILE_CHOICES,
        default="home_visiting",
        help_text=_("Determines which forms are available to field staff."),
    )

    # Form-level overrides (advanced — profile sets defaults)
    form_session_attendance = models.BooleanField(default=False)
    form_visit_note = models.BooleanField(default=True)
    form_circle_observation = models.BooleanField(default=False)

    # ODK Central identifiers (populated by sync command)
    odk_project_id = models.IntegerField(
        null=True, blank=True,
        help_text="ODK Central project ID. Set automatically by sync_odk.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "field_collection"
        db_table = "field_collection_program_config"
        verbose_name = _("field collection configuration")
        verbose_name_plural = _("field collection configurations")

    def __str__(self):
        status = "enabled" if self.enabled else "disabled"
        return f"{self.program.name} — field collection {status}"

    def save(self, *args, **kwargs):
        """Apply profile defaults to form toggles when profile changes."""
        profile_forms = {
            "group": {
                "form_session_attendance": True,
                "form_visit_note": False,
                "form_circle_observation": False,
            },
            "home_visiting": {
                "form_session_attendance": False,
                "form_visit_note": True,
                "form_circle_observation": False,
            },
            "circle": {
                "form_session_attendance": False,
                "form_visit_note": True,
                "form_circle_observation": True,
            },
            "full_field": {
                "form_session_attendance": True,
                "form_visit_note": True,
                "form_circle_observation": True,
            },
        }
        defaults = profile_forms.get(self.profile, {})
        for field, value in defaults.items():
            setattr(self, field, value)
        super().save(*args, **kwargs)

    @property
    def enabled_forms(self):
        """Return list of enabled form identifiers."""
        forms = []
        if self.form_session_attendance:
            forms.append("session_attendance")
        if self.form_visit_note:
            forms.append("visit_note")
        if self.form_circle_observation:
            forms.append("circle_observation")
        return forms

    @property
    def entity_fields_for_tier(self):
        """Return the participant fields to push based on data tier."""
        if self.data_tier == "restricted":
            return ["id"]
        elif self.data_tier == "standard":
            return ["id", "first_name"]
        elif self.data_tier == "field":
            return ["id", "first_name", "last_initial"]
        elif self.data_tier == "field_contact":
            return ["id", "first_name", "last_initial", "phone"]
        return ["id", "first_name"]


class SyncRun(models.Model):
    """Records each execution of the sync_odk management command.

    Used for audit, troubleshooting, and the admin sync dashboard.
    """

    DIRECTION_CHOICES = [
        ("push", _("Push (KoNote → ODK)")),
        ("pull", _("Pull (ODK → KoNote)")),
        ("both", _("Both directions")),
    ]

    STATUS_CHOICES = [
        ("running", _("Running")),
        ("success", _("Success")),
        ("partial", _("Partial — some errors")),
        ("failed", _("Failed")),
    ]

    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="running")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Push stats
    participants_pushed = models.IntegerField(default=0)
    groups_pushed = models.IntegerField(default=0)
    app_users_synced = models.IntegerField(default=0)

    # Pull stats
    attendance_records_created = models.IntegerField(default=0)
    notes_created = models.IntegerField(default=0)
    submissions_skipped = models.IntegerField(default=0)

    # Errors
    error_count = models.IntegerField(default=0)
    error_details = models.TextField(default="", blank=True)

    # Which programs were included
    programs_synced = models.TextField(
        default="", blank=True,
        help_text="Comma-separated program IDs included in this sync.",
    )

    class Meta:
        app_label = "field_collection"
        db_table = "field_collection_sync_runs"
        ordering = ["-started_at"]
        verbose_name = _("sync run")
        verbose_name_plural = _("sync runs")

    def __str__(self):
        return f"Sync {self.direction} — {self.started_at:%Y-%m-%d %H:%M} — {self.status}"
