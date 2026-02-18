"""URL configuration for event type management (mounted at /manage/event-types/)."""
from django.urls import path

from .views import event_type_create, event_type_edit, event_type_list

app_name = "event_types"
urlpatterns = [
    path("", event_type_list, name="event_type_list"),
    path("create/", event_type_create, name="event_type_create"),
    path("<int:type_id>/edit/", event_type_edit, name="event_type_edit"),
]
