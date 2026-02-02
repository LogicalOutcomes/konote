"""URL patterns for plan template administration."""
from django.urls import path

from . import admin_views

app_name = "plan_templates"
urlpatterns = [
    path("", admin_views.template_list, name="template_list"),
    path("create/", admin_views.template_create, name="template_create"),
    path("<int:template_id>/", admin_views.template_detail, name="template_detail"),
    path("<int:template_id>/edit/", admin_views.template_edit, name="template_edit"),
    path("<int:template_id>/sections/create/", admin_views.template_section_create, name="template_section_create"),
    path("sections/<int:section_id>/edit/", admin_views.template_section_edit, name="template_section_edit"),
    path("sections/<int:section_id>/delete/", admin_views.template_section_delete, name="template_section_delete"),
    path("sections/<int:section_id>/targets/create/", admin_views.template_target_create, name="template_target_create"),
    path("targets/<int:target_id>/edit/", admin_views.template_target_edit, name="template_target_edit"),
    path("targets/<int:target_id>/delete/", admin_views.template_target_delete, name="template_target_delete"),
    # Apply template to client
    path("apply/<int:client_id>/", admin_views.template_apply_list, name="template_apply_list"),
    path("apply/<int:client_id>/<int:template_id>/", admin_views.template_apply, name="template_apply"),
]
