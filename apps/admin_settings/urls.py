from django.urls import path

from . import views
from . import report_template_views
from . import setup_wizard_views

app_name = "admin_settings"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("terminology/", views.terminology, name="terminology"),
    path("terminology/reset/<str:term_key>/", views.terminology_reset, name="terminology_reset"),
    path("features/", views.features, name="features"),
    path("instance/", views.instance_settings, name="instance_settings"),
    path("messaging/", views.messaging_settings, name="messaging_settings"),
    path("diagnose-charts/", views.diagnose_charts, name="diagnose_charts"),
    path("demo-directory/", views.demo_directory, name="demo_directory"),
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
