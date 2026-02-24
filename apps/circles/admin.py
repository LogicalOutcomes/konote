"""Django admin registration for Circle and CircleMembership."""
from django.contrib import admin

from .models import Circle, CircleMembership


class CircleMembershipInline(admin.TabularInline):
    model = CircleMembership
    extra = 0
    raw_id_fields = ("client_file",)
    fields = ("client_file", "member_name", "relationship_label", "is_primary_contact", "status")


@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = ("pk", "status", "is_demo", "created_by", "created_at")
    list_filter = ("status", "is_demo")
    inlines = [CircleMembershipInline]
    raw_id_fields = ("created_by",)


@admin.register(CircleMembership)
class CircleMembershipAdmin(admin.ModelAdmin):
    list_display = ("pk", "circle", "client_file", "member_name", "relationship_label", "is_primary_contact", "status")
    list_filter = ("status", "is_primary_contact")
    raw_id_fields = ("circle", "client_file")
