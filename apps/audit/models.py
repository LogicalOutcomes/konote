"""Immutable audit log — stored in separate database."""
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """
    Append-only audit trail. The database user for this table
    should have INSERT-only permission (no UPDATE/DELETE).
    """

    ACTION_CHOICES = [
        ("create", _("Create")),
        ("update", _("Update")),
        ("delete", _("Delete")),
        ("login", _("Login")),
        ("login_failed", _("Login Failed")),
        ("logout", _("Logout")),
        ("export", _("Export")),
        ("view", _("View")),
        ("post", _("POST")),
        ("put", _("PUT")),
        ("patch", _("PATCH")),
        ("access_denied", _("Access Denied")),
        ("cancel", _("Cancel")),
    ]

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
