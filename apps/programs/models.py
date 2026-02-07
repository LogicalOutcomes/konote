"""Program and user-program role models."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Program(models.Model):
    """An organisational unit (e.g., housing, employment, youth services)."""

    SERVICE_MODEL_CHOICES = [
        ("individual", _("One-on-one")),
        ("group", _("Group sessions")),
        ("both", _("Both")),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True)
    colour_hex = models.CharField(max_length=7, default="#3B82F6")
    service_model = models.CharField(
        max_length=20,
        choices=SERVICE_MODEL_CHOICES,
        default="both",
        help_text=_(
            "How staff record their work in this program. "
            "One-on-one: individual notes and plans. "
            "Group sessions: attendance and session notes. "
            "Both: all of the above."
        ),
    )
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", "Active"), ("archived", "Archived")],
    )
    is_confidential = models.BooleanField(
        default=False,
        help_text=_(
            "Confidential programs are invisible to staff in other programs. "
            "Cannot be changed back to Standard without a formal Privacy Impact Assessment."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "programs"
        db_table = "programs"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserProgramRole(models.Model):
    """Links a user to a program with a specific role."""

    ROLE_CHOICES = [
        ("receptionist", _("Front Desk")),
        ("staff", _("Direct Service")),
        ("program_manager", _("Program Manager")),
        ("executive", _("Executive")),
    ]
    STATUS_CHOICES = [
        ("active", _("Active")),
        ("removed", _("Removed")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="program_roles"
    )
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="user_roles")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, default="active", choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "programs"
        db_table = "user_program_roles"
        unique_together = ["user", "program"]

    def __str__(self):
        return f"{self.user} → {self.program} ({self.role})"
