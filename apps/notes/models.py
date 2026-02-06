"""Progress notes and metric value recording."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


class ProgressNoteTemplate(models.Model):
    """Defines the structure of a full progress note."""

    INTERACTION_TYPE_CHOICES = [
        ("session", _("One-on-One Session")),
        ("group", _("Group Session")),
        ("phone", _("Phone Call")),
        ("collateral", _("Contact with Others")),
        ("home_visit", _("Home Visit")),
        ("admin", _("Admin / Paperwork")),
        ("other", _("Other")),
    ]

    name = models.CharField(max_length=255)
    default_interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPE_CHOICES,
        default="session",
        help_text="Pre-fills the interaction type when this template is selected.",
    )
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
    INTERACTION_TYPE_CHOICES = ProgressNoteTemplate.INTERACTION_TYPE_CHOICES
    STATUS_CHOICES = [
        ("default", "Active"),
        ("cancelled", "Cancelled"),
    ]

    client_file = models.ForeignKey("clients.ClientFile", on_delete=models.CASCADE, related_name="progress_notes")
    note_type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES)
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPE_CHOICES,
        default="session",
        db_index=True,
    )
    status = models.CharField(max_length=20, default="default", choices=STATUS_CHOICES)
    status_reason = models.TextField(default="", blank=True)
    template = models.ForeignKey(ProgressNoteTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="authored_notes")
    author_program = models.ForeignKey(
        "programs.Program", on_delete=models.SET_NULL, null=True, blank=True
    )
    # Encrypted clinical content fields
    _notes_text_encrypted = models.BinaryField(default=b"", blank=True)
    _summary_encrypted = models.BinaryField(default=b"", blank=True)
    _participant_reflection_encrypted = models.BinaryField(default=b"", blank=True)

    @property
    def notes_text(self):
        """Content for quick notes (decrypted)."""
        return decrypt_field(self._notes_text_encrypted)

    @notes_text.setter
    def notes_text(self, value):
        self._notes_text_encrypted = encrypt_field(value)

    @property
    def summary(self):
        """Summary of the session (decrypted)."""
        return decrypt_field(self._summary_encrypted)

    @summary.setter
    def summary(self, value):
        self._summary_encrypted = encrypt_field(value)

    @property
    def participant_reflection(self):
        """The participant's own words about what they're taking away (decrypted)."""
        return decrypt_field(self._participant_reflection_encrypted)

    @participant_reflection.setter
    def participant_reflection(self, value):
        self._participant_reflection_encrypted = encrypt_field(value)
    ENGAGEMENT_CHOICES = [
        ("", "---------"),
        ("disengaged", "Disengaged"),
        ("motions", "Going through the motions"),
        ("guarded", "Guarded but present"),
        ("engaged", "Engaged"),
        ("valuing", "Valuing the process"),
        ("no_interaction", "No individual interaction"),
    ]

    engagement_observation = models.CharField(
        max_length=20, choices=ENGAGEMENT_CHOICES, default="", blank=True,
    )
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
        # Build date portion
        if self.created_at:
            date_str = f"{self.created_at:%Y-%m-%d}"
        else:
            date_str = "(no date)"

        # Get preview text from summary or notes_text
        preview = ""
        if self.summary:
            preview = self.summary.strip()
        elif self.notes_text:
            preview = self.notes_text.strip()

        # Truncate preview to 40 characters
        if preview:
            if len(preview) > 40:
                preview = preview[:40].rstrip() + "…"
            return f"{self.get_interaction_type_display()} - {date_str}: {preview}"

        return f"{self.get_interaction_type_display()} - {date_str}"

    @property
    def effective_date(self):
        """The date this note is for (backdate if set, otherwise created_at)."""
        from django.utils import timezone
        return self.backdate or self.created_at or timezone.now()


class ProgressNoteTarget(models.Model):
    """Notes and metrics recorded for a specific plan target within a progress note."""

    PROGRESS_DESCRIPTOR_CHOICES = [
        ("", "---------"),
        ("harder", "Harder right now"),
        ("holding", "Holding steady"),
        ("shifting", "Something's shifting"),
        ("good_place", "In a good place"),
    ]

    progress_note = models.ForeignKey(ProgressNote, on_delete=models.CASCADE, related_name="target_entries")
    plan_target = models.ForeignKey("plans.PlanTarget", on_delete=models.CASCADE, related_name="note_entries")
    _notes_encrypted = models.BinaryField(default=b"", blank=True)
    _client_words_encrypted = models.BinaryField(default=b"", blank=True)
    progress_descriptor = models.CharField(
        max_length=20, choices=PROGRESS_DESCRIPTOR_CHOICES, default="", blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def notes(self):
        """Target-specific notes (decrypted)."""
        return decrypt_field(self._notes_encrypted)

    @notes.setter
    def notes(self, value):
        self._notes_encrypted = encrypt_field(value)

    @property
    def client_words(self):
        """What the client said about this goal today (decrypted)."""
        return decrypt_field(self._client_words_encrypted)

    @client_words.setter
    def client_words(self, value):
        self._client_words_encrypted = encrypt_field(value)

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
