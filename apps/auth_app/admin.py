from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "is_admin", "is_active", "is_demo", "created_at")
    list_filter = ("is_admin", "is_active", "is_staff", "is_demo")
    search_fields = ("username",)
    ordering = ("username",)
    # Security:
    # - is_demo is set at creation only
    # - evaluation_export_granted is a cached flag; editing it here would
    #   bypass the EvaluationExportGrant audit trail (EVAL-GOV1). Use the
    #   KoNote admin UI at /manage/users/evaluation-export/ instead.
    readonly_fields = ("is_demo", "evaluation_export_granted")
    # Override fieldsets — encrypted email can't be edited via raw field
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Permissions", {"fields": ("is_admin", "is_active", "is_staff", "is_superuser")}),
        ("Evaluation Export", {
            "fields": ("evaluation_export_granted",),
            "description": (
                "Read-only. Use the Evaluator Export Access admin page "
                "(/manage/users/evaluation-export/) to grant or revoke this "
                "permission — direct edits bypass the audit trail."
            ),
        }),
        ("Demo", {"fields": ("is_demo",)}),  # Read-only display
    )
    # Note: is_demo intentionally excluded from add_fieldsets — new users default to is_demo=False
    add_fieldsets = (
        (None, {"fields": ("username", "password1", "password2", "is_admin")}),
    )
