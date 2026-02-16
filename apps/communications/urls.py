"""URL configuration for communications app."""
from django.urls import path

from .views import (
    communication_log, compose_email, email_unsubscribe, quick_log,
    send_reminder_preview,
    leave_message, client_messages, mark_message_read, my_messages,
)

app_name = "communications"

urlpatterns = [
    path("client/<int:client_id>/quick-log/", quick_log, name="quick_log"),
    path("client/<int:client_id>/log/", communication_log, name="communication_log"),
    path("client/<int:client_id>/compose-email/", compose_email, name="compose_email"),
    path(
        "client/<int:client_id>/meeting/<int:event_id>/send-reminder/",
        send_reminder_preview,
        name="send_reminder_preview",
    ),
    path("unsubscribe/<str:token>/", email_unsubscribe, name="email_unsubscribe"),
    # Staff messages
    path("my-messages/", my_messages, name="my_messages"),
    path("client/<int:client_id>/leave-message/", leave_message, name="leave_message"),
    path("client/<int:client_id>/messages/", client_messages, name="client_messages"),
    path("client/<int:client_id>/message/<int:message_id>/read/", mark_message_read, name="mark_message_read"),
]
