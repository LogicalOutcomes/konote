from django.urls import path

from . import views

app_name = "plans"
urlpatterns = [
    # Plan view
    path("participant/<int:client_id>/", views.plan_view, name="plan_view"),
    # Section CRUD
    path("participant/<int:client_id>/sections/create/", views.section_create, name="section_create"),
    path("sections/<int:section_id>/edit/", views.section_edit, name="section_edit"),
    path("sections/<int:section_id>/status/", views.section_status, name="section_status"),
    # Combined goal creation
    path("participant/<int:client_id>/goals/create/", views.goal_create, name="goal_create"),
    path("participant/<int:client_id>/goals/suggestions/", views.goal_name_suggestions, name="goal_name_suggestions"),
    # Target CRUD
    path("sections/<int:section_id>/targets/create/", views.target_create, name="target_create"),
    path("targets/<int:target_id>/edit/", views.target_edit, name="target_edit"),
    path("targets/<int:target_id>/status/", views.target_status, name="target_status"),
    path("targets/<int:target_id>/metrics/", views.target_metrics, name="target_metrics"),
    path("targets/<int:target_id>/history/", views.target_history, name="target_history"),
]
