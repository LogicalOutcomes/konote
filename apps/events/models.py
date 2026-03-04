"""Events and alerts for client timelines."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class SRECategory(models.Model):
    """Serious Reportable Event category — predefined list, configurable per agency.

    Canadian nonprofits in housing, mental health, addictions, and youth services
    must track and report critical incidents. Categories follow MCCSS, PHIPA,
    and OHSA requirements.
    """

    SEVERITY_CHOICES = [
        (1, _("Level 1 — Immediate")),
        (2, _("Level 2 — Within 24 hours")),
        (3, _("Level 3 — Within 7 days")),
    ]

    name = models.CharField(max_length=100)
    name_fr = models.CharField(max_length=100, blank=True, default="", help_text=_("French name"))
    description = models.TextField(blank=True)
    description_fr = models.TextField(blank=True, default="", help_text=_("French description"))
    severity = models.IntegerField(
        choices=SEVERITY_CHOICES,
        default=2,
    )
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "events"
        db_table = "sre_categories"
        ordering = ["display_order", "name"]
        verbose_name = _("SRE category")
        verbose_name_plural = _("SRE categories")

    def get_translated_name(self):
        """Return the French name if the active language is French and a translation exists."""
        from django.utils.translation import get_language
        if get_language() == "fr" and self.name_fr:
            return self.name_fr
        return self.name

    def get_translated_description(self):
        """Return the French description if the active language is French and a translation exists."""
        from django.utils.translation import get_language
        if get_language() == "fr" and self.description_fr:
            return self.description_fr
        return self.description

    def __str__(self):
        return self.get_translated_name()


class EventType(models.Model):
    """Categorises events (e.g., 'Intake', 'Discharge', 'Crisis')."""

    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True)
    colour_hex = models.CharField(max_length=7, default="#6B7280")
    owning_program = models.ForeignKey(
        "programs.Program", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="event_types",
        help_text="Program that owns this event type. Null = global (admin-created).",
    )
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", "Active"), ("archived", "Archived")],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "events"
        db_table = "event_types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Event(models.Model):
    """A significant event in a client's journey."""

    client_file = models.ForeignKey("clients.ClientFile", on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=255, default="", blank=True)
    description = models.TextField(default="", blank=True)
    start_timestamp = models.DateTimeField()
    end_timestamp = models.DateTimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False, help_text="If true, only the date is stored; time is ignored.")
    event_type = models.ForeignKey(EventType, on_delete=models.SET_NULL, null=True, blank=True)
    related_note = models.ForeignKey("notes.ProgressNote", on_delete=models.SET_NULL, null=True, blank=True)
    author_program = models.ForeignKey("programs.Program", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default="default")
    backdate = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Serious Reportable Event (SRE) fields ---
    is_sre = models.BooleanField(
        default=False,
        verbose_name=_("Serious Reportable Event"),
        help_text=_("Flag this event as a Serious Reportable Event (SRE)."),
    )
    sre_category = models.ForeignKey(
        SRECategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
        verbose_name=_("SRE category"),
    )
    sre_flagged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sre_flagged_events",
        verbose_name=_("Flagged by"),
    )
    sre_flagged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Flagged at"),
    )
    sre_notifications_sent = models.BooleanField(
        default=False,
        verbose_name=_("SRE notifications sent"),
    )

    class Meta:
        app_label = "events"
        db_table = "events"
        ordering = ["-start_timestamp"]

    def clean(self):
        """Validate SRE fields: category is required when flagged as SRE."""
        super().clean()
        if self.is_sre and not self.sre_category_id:
            raise ValidationError({
                "sre_category": _("An SRE category is required when flagging an event as a Serious Reportable Event."),
            })

    def __str__(self):
        # Use title if available, otherwise event type, otherwise generic
        label = self.title or (self.event_type.name if self.event_type else "Event")
        date_str = self.start_timestamp.strftime("%Y-%m-%d") if self.start_timestamp else "(no date)"
        return f"{label} - {date_str}"


class Alert(models.Model):
    """An alert attached to a client file (e.g., safety concerns)."""

    STATUS_CHOICES = [
        ("default", _("Active")),
        ("cancelled", _("Cancelled")),
    ]

    client_file = models.ForeignKey("clients.ClientFile", on_delete=models.CASCADE, related_name="alerts")
    content = models.TextField(default="", blank=True)
    status = models.CharField(max_length=20, default="default", choices=STATUS_CHOICES)
    status_reason = models.TextField(default="", blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    author_program = models.ForeignKey("programs.Program", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "events"
        db_table = "alerts"
        ordering = ["-created_at"]

    def __str__(self):
        date_str = self.created_at.strftime("%Y-%m-%d") if self.created_at else "(no date)"
        preview = self.content.strip()[:40] if self.content else ""
        if len(self.content.strip()) > 40:
            preview += "…"
        if preview:
            return f"Alert - {date_str}: {preview}"
        return f"Alert - {date_str}"


class AlertCancellationRecommendation(models.Model):
    """Staff recommendation to cancel an alert, requiring PM review.

    DV safety: two-person rule. Staff cannot unilaterally cancel safety alerts.
    Staff submits an assessment; PM reviews and approves (cancels alert) or
    rejects (adds note, alert stays active). Staff can re-recommend after
    rejection.
    """

    STATUS_CHOICES = [
        ("pending", _("Pending Review")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
    ]

    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name="cancellation_recommendations",
    )
    recommended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alert_cancel_recommendations",
    )
    assessment = models.TextField(
        help_text=_("Staff assessment of why this alert should be cancelled."),
    )
    status = models.CharField(
        max_length=20,
        default="pending",
        choices=STATUS_CHOICES,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alert_cancel_reviews",
    )
    review_note = models.TextField(
        default="",
        blank=True,
        help_text=_("PM note when approving or rejecting."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "events"
        db_table = "alert_cancellation_recommendations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Cancel recommendation for Alert #{self.alert_id} ({self.status})"


class Meeting(models.Model):
    """A scheduled meeting with a client — separate from Event to keep Event clean.

    OneToOneField to Event means every meeting IS an event on the timeline,
    but nullable meeting-specific fields (location, duration, reminder status)
    don't pollute the Event model.
    """

    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="meeting")
    location = models.CharField(max_length=255, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("scheduled", "Scheduled"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("no_show", "No Show"),
        ],
        default="scheduled",
    )
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="meetings"
    )
    reminder_sent = models.BooleanField(default=False)
    reminder_status = models.CharField(
        max_length=15,
        choices=[
            ("not_sent", "Not Sent"),
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("blocked", "Blocked"),
            ("no_consent", "No Consent"),
            ("no_phone", "No Phone"),
        ],
        default="not_sent",
    )
    reminder_status_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = "events"
        db_table = "meetings"
        ordering = ["-event__start_timestamp"]
        indexes = [
            models.Index(fields=["status", "reminder_sent"]),
        ]

    def __str__(self):
        date_str = self.event.start_timestamp.strftime("%Y-%m-%d %H:%M") if self.event.start_timestamp else "(no date)"
        return f"Meeting — {date_str}"


class CalendarFeedToken(models.Model):
    """Token-based auth for iCal calendar feeds. No login required — token IS the auth."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar_feed_token")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "events"
        db_table = "calendar_feed_tokens"

    def __str__(self):
        return f"Calendar feed for {self.user}"
