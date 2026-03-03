"""Admin registration for tenant-scoped consortia models."""
from django.contrib import admin

from .models import ConsortiumMembership, ProgramSharing, PublishedReport


@admin.register(ConsortiumMembership)
class ConsortiumMembershipAdmin(admin.ModelAdmin):
    list_display = ("consortium_id", "joined_at", "is_active")
    list_filter = ("is_active",)
    search_fields = ("consortium_id",)
    readonly_fields = ("joined_at",)


@admin.register(ProgramSharing)
class ProgramSharingAdmin(admin.ModelAdmin):
    list_display = ("program", "membership", "date_from", "date_to", "created_at")
    list_filter = ("date_to",)
    search_fields = ("program__name",)
    readonly_fields = ("created_at",)


@admin.register(PublishedReport)
class PublishedReportAdmin(admin.ModelAdmin):
    list_display = ("title", "membership", "period_start", "period_end", "published_by", "published_at")
    list_filter = ("period_start", "period_end")
    search_fields = ("title",)
    readonly_fields = ("published_at",)
