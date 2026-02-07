"""Events and alerts for client timelines."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class EventType(models.Model):
    """Categorises events (e.g., 'Intake', 'Discharge', 'Crisis')."""

    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True)
    colour_hex = models.CharField(max_length=7, default="#6B7280")
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

    class Meta:
        app_label = "events"
        db_table = "events"
        ordering = ["-start_timestamp"]

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
