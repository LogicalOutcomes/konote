from django.urls import path

from . import views
from . import pdf_views
from . import insights_views

app_name = "reports"
urlpatterns = [
    # Outcome Insights
    path("insights/", insights_views.program_insights, name="program_insights"),
    path("client/<int:client_id>/insights/", insights_views.client_insights_partial, name="client_insights"),
    # Exports
    path("export/", views.export_form, name="export_form"),
    path("cmt-export/", views.cmt_export_form, name="cmt_export"),
    path("client-data-export/", views.client_data_export, name="client_data_export"),
    path("client/<int:client_id>/analysis/", views.client_analysis, name="client_analysis"),
    path("client/<int:client_id>/pdf/", pdf_views.client_progress_pdf, name="client_progress_pdf"),
    path("client/<int:client_id>/export/", pdf_views.client_export, name="client_export"),
    # Secure export links
    path("download/<uuid:link_id>/", views.download_export, name="download_export"),
    path("export-links/", views.manage_export_links, name="manage_export_links"),
    path("export-links/<uuid:link_id>/revoke/", views.revoke_export_link, name="revoke_export_link"),
]
