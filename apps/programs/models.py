"""Program and user-program role models."""
from django.conf import settings
from django.db import models


class Program(models.Model):
    """An organisational unit (e.g., housing, employment, youth services)."""

    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True)
    colour_hex = models.CharField(max_length=7, default="#3B82F6")
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", "Active"), ("archived", "Archived")],
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
        ("receptionist", "Receptionist"),
        ("staff", "Counsellor"),
        ("program_manager", "Program Manager"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("removed", "Removed"),
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
