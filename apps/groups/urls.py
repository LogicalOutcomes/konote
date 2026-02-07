from django.urls import path

from . import views

app_name = "groups"
urlpatterns = [
    path("", views.group_list, name="group_list"),
    path("<int:group_id>/", views.group_detail, name="group_detail"),
    path("create/", views.group_create, name="group_create"),
    path("<int:group_id>/edit/", views.group_edit, name="group_edit"),
    path("<int:group_id>/session/", views.session_log, name="session_log"),
    path("<int:group_id>/member/add/", views.membership_add, name="membership_add"),
    path("member/<int:membership_id>/remove/", views.membership_remove, name="membership_remove"),
    path("<int:group_id>/milestone/", views.milestone_create, name="milestone_create"),
    path("milestone/<int:milestone_id>/edit/", views.milestone_edit, name="milestone_edit"),
    path("<int:group_id>/outcome/", views.outcome_create, name="outcome_create"),
    path("<int:group_id>/attendance/", views.attendance_report, name="attendance_report"),
]
