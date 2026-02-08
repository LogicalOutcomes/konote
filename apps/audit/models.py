"""Immutable audit log — stored in separate database."""
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """
    Append-only audit trail. The database user for this table
    should have INSERT-only permission (no UPDATE/DELETE).
    """

    ACTION_CHOICES = [
        ("create", _("Created")),
        ("update", _("Updated")),
        ("delete", _("Deleted")),
        ("login", _("Logged in")),
        ("login_failed", _("Login failed")),
        ("logout", _("Logged out")),
        ("export", _("Exported")),
        ("view", _("Viewed")),
        ("post", _("Created")),
        ("put", _("Updated")),
        ("patch", _("Updated")),
        ("access_denied", _("Access denied")),
        ("cancel", _("Cancelled")),
    ]

    # Human-readable labels for resource_type values
    RESOURCE_TYPE_LABELS = {
        "auth": _("Account"),
        "session": _("Account"),
        "clients": _("Client record"),
        "notes": _("Progress note"),
        "plans": _("Plan"),
        "events": _("Event"),
        "programs": _("Program"),
        "groups": _("Group"),
        "audit_log": _("Audit log"),
        "export": _("Export"),
        "erasure": _("Erasure request"),
        "registration": _("Registration"),
        "settings": _("Settings"),
    }

    @property
    def resource_type_display(self):
        """Return human-readable resource type label."""
        return self.RESOURCE_TYPE_LABELS.get(
            self.resource_type, self.resource_type.replace("_", " ").title()
        )

    event_timestamp = models.DateTimeField()
    user_id = models.IntegerField(null=True, blank=True)
    user_display = models.CharField(max_length=255, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100)
    resource_id = models.IntegerField(null=True, blank=True)
    program_id = models.IntegerField(null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    is_demo_context = models.BooleanField(
        default=False,
        help_text="True when the action was performed by a demo user.",
    )
    is_confidential_context = models.BooleanField(
        default=False,
        help_text="True when the action involved a confidential program.",
    )

    class Meta:
        app_label = "audit"
        db_table = "audit_log"
        ordering = ["-event_timestamp"]
        # Django-level protection — real protection is at PostgreSQL role level
        managed = True

    def __str__(self):
        return f"{self.event_timestamp} | {self.user_display} | {self.action} {self.resource_type}"
