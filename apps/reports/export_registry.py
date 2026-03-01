"""
Export coverage registry for the agency data export command.

Every model in KoNote's apps must be either:
  - Exportable (included via auto-discovery)
  - Explicitly excluded (in EXPORT_EXCLUDE with a reason)

The Django system check (KoNote.W020) and CI test enforce this.
"""

from django.apps import apps

# KoNote app labels — must match INSTALLED_APPS
KONOTE_APPS = {
    "auth_app", "programs", "clients", "plans", "notes",
    "events", "admin_settings", "audit", "reports",
    "registration", "groups", "circles", "portal",
    "communications", "surveys", "field_collection",
}

# Models explicitly excluded from export, with reasons.
# Format: (app_label, model_name) tuples.
EXPORT_EXCLUDE = {
    # Ephemeral download links with expiry tokens — not agency data
    ("reports", "SecureExportLink"),
    # Cached / derived insight summaries — regenerated from source models
    ("reports", "InsightSummary"),
    # Infrastructure health-check pings — operational, not agency data
    ("communications", "SystemHealthCheck"),
    # ODK sync-run tracking — operational / ephemeral
    ("field_collection", "SyncRun"),
    # Short-lived tokens for staff-assisted portal login
    ("portal", "StaffAssistedLoginToken"),
    # Personal calendar-feed tokens — security-sensitive / ephemeral
    ("events", "CalendarFeedToken"),
}


def get_all_konote_models():
    """Return all models belonging to KoNote apps."""
    return {
        model for model in apps.get_models()
        if model._meta.app_label in KONOTE_APPS
    }


def get_excluded_models():
    """Return model classes that are explicitly excluded from export."""
    excluded = set()
    for app_label, model_name in EXPORT_EXCLUDE:
        try:
            excluded.add(apps.get_model(app_label, model_name))
        except LookupError:
            pass  # Model may have been removed
    return excluded


def get_exportable_models():
    """Return models that should be included in a full agency export."""
    return get_all_konote_models() - get_excluded_models()


def get_uncovered_models():
    """Return models that are neither exported nor explicitly excluded.

    This should always return an empty set. If it doesn't, a model
    was added without updating the export registry.
    """
    all_models = get_all_konote_models()
    excluded = get_excluded_models()
    exportable = get_exportable_models()
    return all_models - exportable - excluded
