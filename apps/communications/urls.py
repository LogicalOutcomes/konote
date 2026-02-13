"""URL configuration for communications app."""
from django.urls import path

from .views import communication_log, email_unsubscribe, quick_log, send_reminder_preview

app_name = "communications"

urlpatterns = [
    path("client/<int:client_id>/quick-log/", quick_log, name="quick_log"),
    path("client/<int:client_id>/log/", communication_log, name="communication_log"),
    path(
        "client/<int:client_id>/meeting/<int:event_id>/send-reminder/",
        send_reminder_preview,
        name="send_reminder_preview",
    ),
    path("unsubscribe/<str:token>/", email_unsubscribe, name="email_unsubscribe"),
]
