from django.contrib import admin

from .models import Alert, Event, EventType, SRECategory


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "status")
    list_filter = ("status",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("client_file", "event_type", "title", "start_timestamp", "status", "is_sre")
    list_filter = ("event_type", "status", "is_sre")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("client_file", "status", "author", "created_at")
    list_filter = ("status",)


@admin.register(SRECategory)
class SRECategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fr", "severity", "is_active", "display_order")
    list_filter = ("severity", "is_active")
    ordering = ("display_order", "name")
