"""Admin registration for Communications app."""
from django.contrib import admin

from .models import Communication


@admin.register(Communication)
class CommunicationAdmin(admin.ModelAdmin):
    list_display = ["client_file", "channel", "direction", "method", "delivery_status", "created_at"]
    list_filter = ["channel", "direction", "method", "delivery_status"]
    search_fields = ["subject", "external_id"]
    readonly_fields = ["_content_encrypted", "created_at"]
    date_hierarchy = "created_at"
