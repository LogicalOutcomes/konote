"""Communication log for tracking all client interactions."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


class Communication(models.Model):
    """A single communication event — logged manually or recorded by the system.

    Business rules:
    - direction: Was this outbound (staff->client) or inbound (client->staff)?
    - channel: How was it sent? (email, sms, phone, in_person, etc.)
    - method: Was it typed by staff (manual_log) or sent by the system (system_sent)?
    - Content is encrypted because it may contain clinical details.
    - delivery_status tracks what happened for system-sent messages.
    - delivery_status_display is plain language for staff ("Phone may not be in service").
    """

    DIRECTION_CHOICES = [
        ("outbound", _("Outbound")),
        ("inbound", _("Inbound")),
    ]

    CHANNEL_CHOICES = [
        ("email", _("Email")),
        ("sms", _("SMS")),
        ("phone", _("Phone Call")),
        ("in_person", _("In Person")),
        ("portal", _("Portal Message")),
        ("whatsapp", _("WhatsApp")),
    ]

    METHOD_CHOICES = [
        ("manual_log", _("Manual Log")),
        ("system_sent", _("System Sent")),
        ("system_received", _("System Received")),
    ]

    DELIVERY_STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("sent", _("Sent")),
        ("delivered", _("Delivered")),
        ("failed", _("Failed")),
        ("bounced", _("Bounced")),
        ("blocked", _("Blocked")),
    ]

    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        related_name="communications",
    )

    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    channel = models.CharField(max_length=15, choices=CHANNEL_CHOICES)
    method = models.CharField(max_length=15, choices=METHOD_CHOICES, default="manual_log")

    subject = models.CharField(max_length=255, blank=True, default="")

    # Encrypted content — may contain clinical details
    _content_encrypted = models.BinaryField(null=True, blank=True)

    # Delivery tracking (for system-sent messages)
    delivery_status = models.CharField(
        max_length=15,
        choices=DELIVERY_STATUS_CHOICES,
        default="sent",
        blank=True,
    )
    delivery_status_display = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Plain-language description of delivery result for staff display"),
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("External reference (e.g. Twilio SID)"),
    )

    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logged_communications",
    )
    author_program = models.ForeignKey(
        "programs.Program",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "communications"
        db_table = "communications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client_file", "-created_at"]),
            models.Index(fields=["delivery_status"]),
        ]

    def __str__(self):
        date_str = self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "(no date)"
        return f"{self.get_channel_display()} ({self.get_direction_display()}) — {date_str}"

    # Encrypted content accessor
    @property
    def content(self):
        return decrypt_field(self._content_encrypted)

    @content.setter
    def content(self, value):
        self._content_encrypted = encrypt_field(value)
