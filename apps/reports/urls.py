from django.urls import path
from django.views.generic import RedirectView

from . import cids_views
from . import views
from . import pdf_views
from . import insights_views
from . import oversight_views
from . import preview_views

app_name = "reports"
urlpatterns = [
    # Root redirect - /reports/ -> /reports/generate/
    path("", RedirectView.as_view(pattern_name="reports:generate_report", permanent=False), name="root"),
    # Legacy URL redirect (QA-R8-UX11)
    path("funder/", RedirectView.as_view(pattern_name="reports:funder_report", permanent=True)),
    # Outcome Insights
    path("insights/", insights_views.program_insights, name="program_insights"),
    path("participant/<int:client_id>/insights/", insights_views.client_insights_partial, name="client_insights"),
    # Template-driven report generation (DRR: reporting-architecture.md)
    path("generate/", views.generate_report_form, name="generate_report"),
    path("generate/preview/", preview_views.template_report_preview, name="template_report_preview"),
    path("generate/period-options/", views.template_period_options, name="template_period_options"),
    # Exports (ad-hoc + legacy funder report)
    path("export/", views.export_form, name="export_form"),
    path("export/preview/", preview_views.adhoc_report_preview, name="adhoc_report_preview"),
    path("export/template-autofill/", views.adhoc_template_autofill, name="adhoc_template_autofill"),
    path("funder-report/", views.funder_report_form, name="funder_report"),
    path("funder-report/preview/", views.funder_report_preview, name="funder_report_preview"),
    path("funder-report/approve/", views.funder_report_approve, name="funder_report_approve"),
    path("participant/<int:client_id>/analysis/", views.client_analysis, name="client_analysis"),
    path("participant/<int:client_id>/pdf/", pdf_views.client_progress_pdf, name="client_progress_pdf"),
    path("participant/<int:client_id>/export/", pdf_views.client_export, name="client_export"),
    # Team meeting view
    path("team-meeting/", views.team_meeting_view, name="team_meeting_view"),
    # Secure export links
    path("download/<uuid:link_id>/", views.download_export, name="download_export"),
    path("export-links/", views.manage_export_links, name="manage_export_links"),
    path("export-links/<uuid:link_id>/revoke/", views.revoke_export_link, name="revoke_export_link"),
    # Safety Oversight Reports
    path("oversight/", oversight_views.oversight_report_list, name="oversight_list"),
    path("oversight/generate/", oversight_views.oversight_report_generate, name="oversight_generate"),
    path("oversight/<int:report_id>/", oversight_views.oversight_report_detail, name="oversight_detail"),
    path("oversight/<int:report_id>/approve/", oversight_views.oversight_report_approve, name="oversight_approve"),
    path("oversight/<int:report_id>/pdf/", oversight_views.oversight_report_pdf, name="oversight_pdf"),
    # Sessions by Participant report (REP-SESS1)
    path("sessions/", views.session_report_form, name="session_report"),
    # Report Schedules
    path("schedules/", oversight_views.report_schedule_list, name="schedule_list"),
    path("schedules/create/", oversight_views.report_schedule_create, name="schedule_create"),
    path("schedules/<int:schedule_id>/edit/", oversight_views.report_schedule_edit, name="schedule_edit"),
    # CIDS compliance
    path("cids/", cids_views.cids_coverage_dashboard, name="cids_dashboard"),
    path("cids/<int:program_id>/status/", cids_views.cids_export_status, name="cids_export_status"),
    path("cids/export/", cids_views.cids_full_tier_export, name="cids_full_tier_export"),
]
