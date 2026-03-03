"""Admin registration for shared-schema tenant models."""
from django.contrib import admin

from .models import Agency, AgencyDomain, Consortium, TenantKey


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("name", "short_code", "schema_name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "short_code")
    readonly_fields = ("schema_name", "created_at", "updated_at")


@admin.register(AgencyDomain)
class AgencyDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)


@admin.register(TenantKey)
class TenantKeyAdmin(admin.ModelAdmin):
    list_display = ("tenant", "created_at", "rotated_at")
    readonly_fields = ("encrypted_key", "created_at", "rotated_at")


@admin.register(Consortium)
class ConsortiumAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
