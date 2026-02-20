from django.urls import path

from apps.portal.staff_views import (
    create_portal_invite,
    create_staff_portal_note,
    generate_staff_login_token,
    portal_manage,
    portal_reset_mfa,
    portal_revoke_access,
)

from . import erasure_views, views
from .dashboard_views import executive_dashboard


app_name = "clients"

urlpatterns = [
    path("executive/", executive_dashboard, name="executive_dashboard"),
    path("", views.client_list, name="client_list"),
    path("create/", views.client_create, name="client_create"),
    path("check-duplicate/", views.check_duplicate, name="check_duplicate"),
    path("search/", views.client_search, name="client_search"),
    path("<int:client_id>/", views.client_detail, name="client_detail"),
    path("<int:client_id>/edit/", views.client_edit, name="client_edit"),
    path("<int:client_id>/transfer/", views.client_transfer, name="client_transfer"),
    path("<int:client_id>/edit-contact/", views.client_contact_edit, name="client_contact_edit"),
    path("<int:client_id>/confirm-phone/", views.client_confirm_phone, name="client_confirm_phone"),
    path("<int:client_id>/custom-fields/", views.client_save_custom_fields, name="client_save_custom_fields"),
    path("<int:client_id>/custom-fields/display/", views.client_custom_fields_display, name="client_custom_fields_display"),
    path("<int:client_id>/custom-fields/edit/", views.client_custom_fields_edit, name="client_custom_fields_edit"),
    # Consent recording (PRIV1)
    path("<int:client_id>/consent/display/", views.client_consent_display, name="client_consent_display"),
    path("<int:client_id>/consent/edit/", views.client_consent_edit, name="client_consent_edit"),
    path("<int:client_id>/consent/", views.client_consent_save, name="client_consent_save"),
    # Custom field admin (FIELD1)
    path("admin/fields/", views.custom_field_admin, name="custom_field_admin"),
    path("admin/fields/groups/create/", views.custom_field_group_create, name="custom_field_group_create"),
    path("admin/fields/groups/<int:group_id>/edit/", views.custom_field_group_edit, name="custom_field_group_edit"),
    path("admin/fields/create/", views.custom_field_def_create, name="custom_field_def_create"),
    path("admin/fields/<int:field_id>/edit/", views.custom_field_def_edit, name="custom_field_def_edit"),
    # Erasure request (ERASE4)
    path("<int:client_id>/erase/", erasure_views.erasure_request_create, name="client_erasure_request"),
    # Portal staff note
    path("<int:client_id>/portal-note/", create_staff_portal_note, name="create_staff_portal_note"),
    # Portal management
    path("<int:client_id>/portal-invite/", create_portal_invite, name="create_portal_invite"),
    path("<int:client_id>/portal/", portal_manage, name="portal_manage"),
    path("<int:client_id>/portal/revoke/", portal_revoke_access, name="portal_revoke"),
    path("<int:client_id>/portal/reset-mfa/", portal_reset_mfa, name="portal_reset_mfa"),
    path("<int:client_id>/portal/staff-login/", generate_staff_login_token, name="portal_staff_login"),
]
