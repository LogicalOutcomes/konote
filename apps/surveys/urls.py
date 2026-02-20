"""Survey URL configuration — participant-level routes."""
from django.urls import path

from . import views

app_name = "surveys"

urlpatterns = [
    path(
        "participant/<int:client_id>/",
        views.client_surveys,
        name="client_surveys",
    ),
    path(
        "participant/<int:client_id>/assign/",
        views.assign_survey,
        name="assign_survey",
    ),
    path(
        "participant/<int:client_id>/enter/<int:survey_id>/",
        views.staff_data_entry,
        name="staff_data_entry",
    ),
    path(
        "participant/<int:client_id>/response/<int:response_id>/",
        views.client_response_detail,
        name="client_response_detail",
    ),
    path(
        "assignment/<int:assignment_id>/approve/",
        views.approve_assignment,
        name="approve_assignment",
    ),
    path(
        "assignment/<int:assignment_id>/dismiss/",
        views.dismiss_assignment,
        name="dismiss_assignment",
    ),
]
