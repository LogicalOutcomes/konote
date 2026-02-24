"""URL configuration for KoNote Web."""
import os

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
from django.views.static import serve

from apps.audit.views import program_audit_log
from apps.auth_app.views import switch_language
from apps.events.views import calendar_feed
from apps.portal.analytics_views import portal_analytics
from apps.surveys.public_views import public_survey_form, public_survey_thank_you
from konote.error_views import permission_denied_view
from konote.page_views import help_view, privacy_view

# Custom error handlers
handler403 = permission_denied_view

urlpatterns = [
    # Internationalization - language switching
    path("i18n/", include("django.conf.urls.i18n")),
    path("i18n/switch/", switch_language, name="switch_language"),
    path("auth/", include("apps.auth_app.urls")),
    path("participants/", include("apps.clients.urls")),
    path("programs/", include("apps.programs.urls")),
    # Redirects for old admin URLs (BEFORE app includes so they match first)
    path("plans/admin/metrics/<path:rest>", RedirectView.as_view(url="/manage/metrics/%(rest)s", permanent=True)),
    path("plans/admin/metrics/", RedirectView.as_view(url="/manage/metrics/", permanent=True)),
    path("plans/client/<path:rest>", RedirectView.as_view(url="/plans/participant/%(rest)s", permanent=True)),
    path("plans/", include("apps.plans.urls")),
    path("notes/client/<path:rest>", RedirectView.as_view(url="/notes/participant/%(rest)s", permanent=True)),
    path("notes/", include("apps.notes.urls")),
    path("events/admin/types/<path:rest>", RedirectView.as_view(url="/manage/event-types/%(rest)s", permanent=True)),
    path("events/admin/types/", RedirectView.as_view(url="/manage/event-types/", permanent=True)),
    path("events/client/<path:rest>", RedirectView.as_view(url="/events/participant/%(rest)s", permanent=True)),
    path("events/", include("apps.events.urls")),
    path("communications/client/<path:rest>", RedirectView.as_view(url="/communications/participant/%(rest)s", permanent=True)),
    path("communications/", include("apps.communications.urls")),
    path("calendar/<str:token>/feed.ics", calendar_feed, name="calendar_feed"),
    path("reports/client/<path:rest>", RedirectView.as_view(url="/reports/participant/%(rest)s", permanent=True)),
    path("reports/", include("apps.reports.urls")),
    path("groups/", include("apps.groups.urls")),
    path("surveys/", include("apps.surveys.urls")),
    # ── Public survey links (no login required) ──
    path("s/<str:token>/", public_survey_form, name="public_survey_form"),
    path("s/<str:token>/thanks/", public_survey_thank_you, name="public_survey_thank_you"),

    # ── /manage/ routes (PM + Admin accessible) ──
    path("manage/templates/", include("apps.plans.admin_urls")),
    path("manage/note-templates/", include("apps.notes.admin_urls")),
    path("manage/event-types/", include("apps.events.manage_urls")),
    path("manage/metrics/", include("apps.plans.metric_urls")),
    path("manage/users/", include("apps.auth_app.admin_urls")),
    path("manage/audit/", include("apps.audit.urls")),
    path("manage/suggestions/", include("apps.notes.suggestion_urls")),
    path("manage/surveys/", include("apps.surveys.manage_urls")),
    path("manage/portal-analytics/", portal_analytics, name="portal_analytics"),

    # ── /admin/ routes (Admin only) ──
    path("admin/settings/", include("apps.admin_settings.urls")),
    # Redirect /settings/ to /admin/settings/ for convenience
    path("settings/", login_required(RedirectView.as_view(url="/admin/settings/", permanent=False))),

    # ── Redirects from old /admin/ URLs to new /manage/ locations ──
    path("admin/templates/<path:rest>", RedirectView.as_view(url="/manage/templates/%(rest)s", permanent=True)),
    path("admin/templates/", RedirectView.as_view(url="/manage/templates/", permanent=True)),
    path("admin/settings/note-templates/<path:rest>", RedirectView.as_view(url="/manage/note-templates/%(rest)s", permanent=True)),
    path("admin/settings/note-templates/", RedirectView.as_view(url="/manage/note-templates/", permanent=True)),
    path("admin/users/<path:rest>", RedirectView.as_view(url="/manage/users/%(rest)s", permanent=True)),
    path("admin/users/", RedirectView.as_view(url="/manage/users/", permanent=True)),
    path("admin/audit/<path:rest>", RedirectView.as_view(url="/manage/audit/%(rest)s", permanent=True)),
    path("admin/audit/", RedirectView.as_view(url="/manage/audit/", permanent=True)),
    path("admin/suggestions/<path:rest>", RedirectView.as_view(url="/manage/suggestions/%(rest)s", permanent=True)),
    path("admin/suggestions/", RedirectView.as_view(url="/manage/suggestions/", permanent=True)),
    path("admin/registration/<path:rest>", RedirectView.as_view(url="/manage/registration/%(rest)s", permanent=True)),
    path("admin/registration/", RedirectView.as_view(url="/manage/registration/", permanent=True)),
    path("admin/submissions/<path:rest>", RedirectView.as_view(url="/manage/submissions/%(rest)s", permanent=True)),
    path("admin/submissions/", RedirectView.as_view(url="/manage/submissions/", permanent=True)),

    path("audit/program/<int:program_id>/", program_audit_log, name="program_audit_log"),
    path("erasure/", include("apps.clients.erasure_urls")),
    path("data-access/", include("apps.clients.data_access_urls")),
    path("merge/", include("apps.clients.merge_urls")),
    path("ai/", include("konote.ai_urls")),
    path("my/", include("apps.portal.urls")),
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
