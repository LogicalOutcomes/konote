from django.urls import path

from apps.portal.staff_views import (
    program_resource_deactivate,
    program_resource_edit,
    program_resources_manage,
)

from . import evaluation_views, views

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
    # Evaluation frameworks (CIDS Full Tier)
    path("evaluation/", evaluation_views.framework_list, name="framework_list"),
    path("<int:program_id>/evaluation/create/", evaluation_views.framework_create, name="framework_create"),
    path("evaluation/<int:framework_id>/", evaluation_views.framework_detail, name="framework_detail"),
    path("evaluation/<int:framework_id>/edit/", evaluation_views.framework_edit, name="framework_edit"),
    path("evaluation/<int:framework_id>/attest/", evaluation_views.framework_attest, name="framework_attest"),
    path("evaluation/<int:framework_id>/components/add/", evaluation_views.component_add, name="component_add"),
    path("evaluation/<int:framework_id>/components/<int:component_id>/edit/", evaluation_views.component_edit, name="component_edit"),
    path("evaluation/<int:framework_id>/components/<int:component_id>/deactivate/", evaluation_views.component_deactivate, name="component_deactivate"),
    path("evaluation/<int:framework_id>/evidence/add/", evaluation_views.evidence_add, name="evidence_add"),
    path("evaluation/<int:framework_id>/evidence/<int:evidence_id>/delete/", evaluation_views.evidence_delete, name="evidence_delete"),
]
