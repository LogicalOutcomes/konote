"""URL configuration for metric library management (mounted at /manage/metrics/)."""
from django.urls import path

from . import views

app_name = "metrics"
urlpatterns = [
    path("", views.metric_library, name="metric_library"),
    path("export/", views.metric_export, name="metric_export"),
    path("create/", views.metric_create, name="metric_create"),
    path("import/", views.metric_import, name="metric_import"),
    path("<int:metric_id>/edit/", views.metric_edit, name="metric_edit"),
    path("<int:metric_id>/toggle/", views.metric_toggle, name="metric_toggle"),
]
