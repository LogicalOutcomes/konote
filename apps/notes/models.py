"""Progress notes and metric value recording."""
from django.conf import settings
from django.db import models


class ProgressNoteTemplate(models.Model):
    """Defines the structure of a full progress note."""

    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", "Active"), ("archived", "Archived")],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "notes"
        db_table = "progress_note_templates"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProgressNoteTemplateSection(models.Model):
    """A section within a progress note template."""

    SECTION_TYPE_CHOICES = [
        ("basic", "Basic Text"),
        ("plan", "Plan Targets"),
    ]

    template = models.ForeignKey(ProgressNoteTemplate, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=255)
    section_type = models.CharField(max_length=20, choices=SECTION_TYPE_CHOICES, default="basic")
    sort_order = models.IntegerField(default=0)

    class Meta:
        app_label = "notes"
        db_table = "progress_note_template_sections"
        ordering = ["sort_order"]


class ProgressNoteTemplateMetric(models.Model):
    """Links a metric to a template section."""

    template_section = models.ForeignKey(
        ProgressNoteTemplateSection, on_delete=models.CASCADE, related_name="metrics"
    )
    metric_def = models.ForeignKey("plans.MetricDefinition", on_delete=models.CASCADE)
    sort_order = models.IntegerField(default=0)

    class Meta:
        app_label = "notes"
        db_table = "progress_note_template_metrics"
        ordering = ["sort_order"]


class ProgressNote(models.Model):
    """A progress note recorded against a client."""

    NOTE_TYPE_CHOICES = [
        ("quick", "Quick Note"),
        ("full", "Full Note"),
    ]
    STATUS_CHOICES = [
        ("default", "Active"),
        ("cancelled", "Cancelled"),
    ]

    client_file = models.ForeignKey("clients.ClientFile", on_delete=models.CASCADE, related_name="progress_notes")
    note_type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES)
    status = models.CharField(max_length=20, default="default", choices=STATUS_CHOICES)
    status_reason = models.TextField(default="", blank=True)
    template = models.ForeignKey(ProgressNoteTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="authored_notes")
    author_program = models.ForeignKey(
        "programs.Program", on_delete=models.SET_NULL, null=True, blank=True
    )
    notes_text = models.TextField(default="", blank=True, help_text="Content for quick notes.")
    summary = models.TextField(default="", blank=True)
    backdate = models.DateTimeField(null=True, blank=True, help_text="Override date if note is for a past session.")
    begin_timestamp = models.DateTimeField(null=True, blank=True)
    follow_up_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional date to follow up on this note."
    )
    follow_up_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the follow-up was completed (new note recorded)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "notes"
        db_table = "progress_notes"
        ordering = ["-created_at"]

    def __str__(self):
        if self.created_at:
            return f"{self.get_note_type_display()} - {self.created_at:%Y-%m-%d}"
        return f"{self.get_note_type_display()} - (no date)"

    @property
    def effective_date(self):
        """The date this note is for (backdate if set, otherwise created_at)."""
        from django.utils import timezone
        return self.backdate or self.created_at or timezone.now()


class ProgressNoteTarget(models.Model):
    """Notes and metrics recorded for a specific plan target within a progress note."""

    progress_note = models.ForeignKey(ProgressNote, on_delete=models.CASCADE, related_name="target_entries")
    plan_target = models.ForeignKey("plans.PlanTarget", on_delete=models.CASCADE, related_name="note_entries")
    notes = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "notes"
        db_table = "progress_note_targets"


class MetricValue(models.Model):
    """A single metric measurement recorded in a progress note."""

    progress_note_target = models.ForeignKey(
        ProgressNoteTarget, on_delete=models.CASCADE, related_name="metric_values"
    )
    metric_def = models.ForeignKey("plans.MetricDefinition", on_delete=models.CASCADE)
    value = models.CharField(max_length=100, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "notes"
        db_table = "metric_values"
