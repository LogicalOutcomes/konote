"""URL configuration for communications app."""
from django.urls import path

from .views import communication_log, quick_log

app_name = "communications"

urlpatterns = [
    path("client/<int:client_id>/quick-log/", quick_log, name="quick_log"),
    path("client/<int:client_id>/log/", communication_log, name="communication_log"),
]
