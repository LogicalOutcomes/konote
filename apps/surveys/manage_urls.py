"""Survey management URL configuration."""
from django.urls import path

from . import views

app_name = "survey_manage"

urlpatterns = [
    path("", views.survey_list, name="survey_list"),
    path("new/", views.survey_create, name="survey_create"),
    path("<int:survey_id>/", views.survey_detail, name="survey_detail"),
    path("<int:survey_id>/edit/", views.survey_edit, name="survey_edit"),
    path("<int:survey_id>/questions/", views.survey_questions, name="survey_questions"),
    path("<int:survey_id>/status/", views.survey_status, name="survey_status"),
    path(
        "<int:survey_id>/responses/<int:response_id>/",
        views.survey_response_detail,
        name="survey_response_detail",
    ),
    path("<int:survey_id>/links/", views.survey_links, name="survey_links"),
    path("import/", views.csv_import, name="csv_import"),
]
