"""URL configuration for KoNote2 Web."""
import os

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

from apps.audit.views import program_audit_log
from apps.auth_app.views import switch_language
from konote.error_views import permission_denied_view
from konote.page_views import help_view, privacy_view

# Custom error handlers
handler403 = permission_denied_view

urlpatterns = [
    # Internationalization - language switching
    path("i18n/", include("django.conf.urls.i18n")),
    path("i18n/switch/", switch_language, name="switch_language"),
    path("auth/", include("apps.auth_app.urls")),
    path("clients/", include("apps.clients.urls")),
    path("programs/", include("apps.programs.urls")),
    path("plans/", include("apps.plans.urls")),
    path("admin/templates/", include("apps.plans.admin_urls")),
    path("notes/", include("apps.notes.urls")),
    path("events/", include("apps.events.urls")),
    path("reports/", include("apps.reports.urls")),
    path("groups/", include("apps.groups.urls")),
    path("admin/settings/note-templates/", include("apps.notes.admin_urls")),
    path("admin/settings/", include("apps.admin_settings.urls")),
    path("admin/users/", include("apps.auth_app.admin_urls")),
    path("admin/audit/", include("apps.audit.urls")),
    path("audit/program/<int:program_id>/", program_audit_log, name="program_audit_log"),
    path("erasure/", include("apps.clients.erasure_urls")),
    path("merge/", include("apps.clients.merge_urls")),
    path("ai/", include("konote.ai_urls")),
    path("", include("apps.registration.urls")),
    path("", include("apps.clients.urls_home")),
    path("privacy/", privacy_view, name="privacy"),
    path("help/", help_view, name="help"),
    path("django-admin/", admin.site.urls),
    # Service worker — served from root so its scope covers all pages
    path(
        "sw.js",
        serve,
        {"document_root": os.path.join(settings.BASE_DIR, "static"), "path": "sw.js"},
        name="service-worker",
    ),
]
