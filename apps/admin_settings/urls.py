from django.urls import path

from . import views
from . import funder_profile_views

app_name = "admin_settings"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("terminology/", views.terminology, name="terminology"),
    path("terminology/reset/<str:term_key>/", views.terminology_reset, name="terminology_reset"),
    path("features/", views.features, name="features"),
    path("instance/", views.instance_settings, name="instance_settings"),
    path("diagnose-charts/", views.diagnose_charts, name="diagnose_charts"),
    path("demo-directory/", views.demo_directory, name="demo_directory"),
    # Funder profile management
    path("funder-profiles/", funder_profile_views.funder_profile_list, name="funder_profile_list"),
    path("funder-profiles/upload/", funder_profile_views.funder_profile_upload, name="funder_profile_upload"),
    path("funder-profiles/confirm/", funder_profile_views.funder_profile_confirm, name="funder_profile_confirm"),
    path("funder-profiles/sample.csv", funder_profile_views.funder_profile_sample_csv, name="funder_profile_sample_csv"),
    path("funder-profiles/<int:profile_id>/", funder_profile_views.funder_profile_detail, name="funder_profile_detail"),
    path("funder-profiles/<int:profile_id>/programs/", funder_profile_views.funder_profile_edit_programs, name="funder_profile_edit_programs"),
    path("funder-profiles/<int:profile_id>/delete/", funder_profile_views.funder_profile_delete, name="funder_profile_delete"),
    path("funder-profiles/<int:profile_id>/download/", funder_profile_views.funder_profile_download_csv, name="funder_profile_download_csv"),
]
