from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "is_admin", "is_active", "is_demo", "created_at")
    list_filter = ("is_admin", "is_active", "is_staff", "is_demo")
    search_fields = ("username",)
    ordering = ("username",)
    readonly_fields = ("is_demo",)  # Security: is_demo set at creation only
    # Override fieldsets — encrypted email can't be edited via raw field
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Permissions", {"fields": ("is_admin", "is_active", "is_staff", "is_superuser", "evaluation_export_granted")}),
        ("Demo", {"fields": ("is_demo",)}),  # Read-only display
    )
    # Note: is_demo intentionally excluded from add_fieldsets — new users default to is_demo=False
    add_fieldsets = (
        (None, {"fields": ("username", "password1", "password2", "is_admin")}),
    )
