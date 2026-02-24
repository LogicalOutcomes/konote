"""Django admin registration for Circle and CircleMembership."""
from django.contrib import admin

from .models import Circle, CircleMembership


class CircleMembershipInline(admin.TabularInline):
    model = CircleMembership
    extra = 0
    raw_id_fields = ("client_file",)
    fields = ("client_file", "get_member_name", "relationship_label", "is_primary_contact", "status")
    readonly_fields = ("get_member_name",)

    def get_member_name(self, obj):
        return obj.member_name
    get_member_name.short_description = "Member name"


@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = ("pk", "get_name", "status", "is_demo", "created_by", "created_at")
    list_filter = ("status", "is_demo")
    inlines = [CircleMembershipInline]
    raw_id_fields = ("created_by",)

    def get_name(self, obj):
        return obj.name
    get_name.short_description = "Name"


@admin.register(CircleMembership)
class CircleMembershipAdmin(admin.ModelAdmin):
    list_display = ("pk", "circle", "client_file", "get_member_name", "relationship_label", "is_primary_contact", "status")
    list_filter = ("status", "is_primary_contact")
    raw_id_fields = ("circle", "client_file")

    def get_member_name(self, obj):
        return obj.member_name
    get_member_name.short_description = "Member name"
