from django.urls import path

from . import views
from . import field_access_views
from . import partner_views
from . import report_template_views
from . import setup_wizard_views

from apps.auth_app import access_grant_views

app_name = "admin_settings"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("terminology/", views.terminology, name="terminology"),
    path("terminology/reset/<str:term_key>/", views.terminology_reset, name="terminology_reset"),
    path("features/", views.features, name="features"),
    path("features/<str:feature_key>/confirm/", views.feature_toggle_confirm, name="feature_toggle_confirm"),
    path("features/<str:feature_key>/toggle/", views.feature_toggle_action, name="feature_toggle_action"),
    path("instance/", views.instance_settings, name="instance_settings"),
    path("messaging/", views.messaging_settings, name="messaging_settings"),
    path("field-access/", field_access_views.field_access, name="field_access"),
    path("diagnose-charts/", views.diagnose_charts, name="diagnose_charts"),
    path("demo-directory/", views.demo_directory, name="demo_directory"),
    # Access grants admin (Tier 3 only)
    path("access-grants/", access_grant_views.access_grant_admin_list, name="access_grant_admin_list"),
    path("access-grant-reasons/", access_grant_views.access_grant_reasons_admin, name="access_grant_reasons"),
    # Partner management
    path("partners/", partner_views.partner_list, name="partner_list"),
    path("partners/create/", partner_views.partner_create, name="partner_create"),
    path("partners/<int:partner_id>/", partner_views.partner_detail, name="partner_detail"),
    path("partners/<int:partner_id>/edit/", partner_views.partner_edit, name="partner_edit"),
    path("partners/<int:partner_id>/programs/", partner_views.partner_edit_programs, name="partner_edit_programs"),
    path("partners/<int:partner_id>/delete/", partner_views.partner_delete, name="partner_delete"),
    # Report template management
    path("report-templates/", report_template_views.report_template_list, name="report_template_list"),
    path("report-templates/upload/", report_template_views.report_template_upload, name="report_template_upload"),
    path("report-templates/confirm/", report_template_views.report_template_confirm, name="report_template_confirm"),
    path("report-templates/sample.csv", report_template_views.report_template_sample_csv, name="report_template_sample_csv"),
    path("report-templates/<int:profile_id>/", report_template_views.report_template_detail, name="report_template_detail"),
    path("report-templates/<int:profile_id>/programs/", report_template_views.report_template_edit_programs, name="report_template_edit_programs"),
    path("report-templates/<int:profile_id>/delete/", report_template_views.report_template_delete, name="report_template_delete"),
    path("report-templates/<int:profile_id>/download/", report_template_views.report_template_download_csv, name="report_template_download_csv"),
    # Setup wizard -- specific routes before the <str:step> catch-all
    path("setup-wizard/", setup_wizard_views.setup_wizard, name="setup_wizard"),
    path("setup-wizard/complete/", setup_wizard_views.setup_wizard_complete, name="setup_wizard_complete"),
    path("setup-wizard/reset/", setup_wizard_views.setup_wizard_reset, name="setup_wizard_reset"),
    path("setup-wizard/<str:step>/", setup_wizard_views.setup_wizard, name="setup_wizard_step"),
]
