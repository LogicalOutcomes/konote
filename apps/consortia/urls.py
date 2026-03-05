"""URL routing for consortium dashboard."""
from django.urls import path

from . import views

app_name = "consortia"

urlpatterns = [
    path(
        "<int:consortium_id>/dashboard/",
        views.dashboard,
        name="dashboard",
    ),
    path(
        "<int:consortium_id>/dashboard/data/",
        views.dashboard_data,
        name="dashboard_data",
    ),
    path(
        "<int:consortium_id>/dashboard/export/csv/",
        views.export_csv,
        name="export_csv",
    ),
]
