from django.urls import path

from . import views

app_name = "programs"
urlpatterns = [
    path("", views.program_list, name="program_list"),
    path("create/", views.program_create, name="program_create"),
    path("select/", views.select_program, name="select_program"),
    path("switch/", views.switch_program, name="switch_program"),
    path("<int:program_id>/", views.program_detail, name="program_detail"),
    path("<int:program_id>/edit/", views.program_edit, name="program_edit"),
    path("<int:program_id>/roles/add/", views.program_add_role, name="program_add_role"),
    path("<int:program_id>/roles/<int:role_id>/remove/", views.program_remove_role, name="program_remove_role"),
]
