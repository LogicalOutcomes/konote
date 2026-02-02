"""URL configuration for KoNote Web."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.auth_app.urls")),
    path("clients/", include("apps.clients.urls")),
    path("programs/", include("apps.programs.urls")),
    path("plans/", include("apps.plans.urls")),
    path("admin/templates/", include("apps.plans.admin_urls")),
    path("notes/", include("apps.notes.urls")),
    path("events/", include("apps.events.urls")),
    path("reports/", include("apps.reports.urls")),
    path("admin/settings/", include("apps.admin_settings.urls")),
    path("admin/audit/", include("apps.audit.urls")),
    path("ai/", include("konote.ai_urls")),
    path("", include("apps.clients.urls_home")),
    path("django-admin/", admin.site.urls),
]
