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
    name_fr = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("French name (displayed when language is French)"),
    )
    portal_display_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("Name shown in participant portal. Leave blank to use programme name."),
    )
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

    @property
    def translated_name(self):
        """Return French name when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.name_fr:
            return self.name_fr
        return self.name

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

    # Roles that grant access to individual client records
    CLIENT_ACCESS_ROLES = {"receptionist", "staff", "program_manager"}

    def __str__(self):
        return f"{self.user} → {self.program} ({self.role})"

    @classmethod
    def is_executive_only(cls, user, roles=None):
        """Check if user only has executive role (no client access roles).

        Returns True if the user has an active executive role but no roles
        that grant access to individual client records.

        Pass pre-fetched ``roles`` set to avoid an extra query when the
        caller has already loaded the user's roles.
        """
        if roles is None:
            roles = set(
                cls.objects.filter(user=user, status="active")
                .values_list("role", flat=True)
            )
        if not roles:
            return False
        if "executive" in roles:
            return not bool(roles & cls.CLIENT_ACCESS_ROLES)
        return False
