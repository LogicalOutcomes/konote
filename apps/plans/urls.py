from django.urls import path

from . import views

app_name = "plans"
urlpatterns = [
    # Plan view
    path("client/<int:client_id>/", views.plan_view, name="plan_view"),
    # Section CRUD
    path("client/<int:client_id>/sections/create/", views.section_create, name="section_create"),
    path("sections/<int:section_id>/edit/", views.section_edit, name="section_edit"),
    path("sections/<int:section_id>/status/", views.section_status, name="section_status"),
    # Target CRUD
    path("sections/<int:section_id>/targets/create/", views.target_create, name="target_create"),
    path("targets/<int:target_id>/edit/", views.target_edit, name="target_edit"),
    path("targets/<int:target_id>/status/", views.target_status, name="target_status"),
    path("targets/<int:target_id>/metrics/", views.target_metrics, name="target_metrics"),
    path("targets/<int:target_id>/history/", views.target_history, name="target_history"),
    # Metric library (admin)
    path("admin/metrics/", views.metric_library, name="metric_library"),
    path("admin/metrics/export/", views.metric_export, name="metric_export"),
    path("admin/metrics/create/", views.metric_create, name="metric_create"),
    path("admin/metrics/import/", views.metric_import, name="metric_import"),
    path("admin/metrics/<int:metric_id>/edit/", views.metric_edit, name="metric_edit"),
    path("admin/metrics/<int:metric_id>/toggle/", views.metric_toggle, name="metric_toggle"),
]
