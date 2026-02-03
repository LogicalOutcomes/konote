from django.urls import path

from . import views

app_name = "events"
urlpatterns = [
    # Event type admin
    path("admin/types/", views.event_type_list, name="event_type_list"),
    path("admin/types/create/", views.event_type_create, name="event_type_create"),
    path("admin/types/<int:type_id>/edit/", views.event_type_edit, name="event_type_edit"),
    # Client events
    path("client/<int:client_id>/", views.event_list, name="event_list"),
    path("client/<int:client_id>/create/", views.event_create, name="event_create"),
    # Alerts
    path("client/<int:client_id>/alerts/create/", views.alert_create, name="alert_create"),
    path("alerts/<int:alert_id>/cancel/", views.alert_cancel, name="alert_cancel"),
]
