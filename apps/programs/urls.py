from django.urls import path

from apps.portal.staff_views import (
    program_resource_deactivate,
    program_resource_edit,
    program_resources_manage,
)

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
    # Portal resource links
    path("<int:program_id>/resources/", program_resources_manage, name="program_resources"),
    path("<int:program_id>/resources/<int:resource_id>/edit/", program_resource_edit, name="program_resource_edit"),
    path("<int:program_id>/resources/<int:resource_id>/deactivate/", program_resource_deactivate, name="program_resource_deactivate"),
]
