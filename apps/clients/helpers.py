"""Helper functions for client-related operations."""
from urllib.parse import quote

from django.core.cache import cache


def get_document_folder_url(client):
    """Generate URL to client's document folder in external storage.

    Returns None if document storage is not configured.
    Uses cached settings for performance.

    Args:
        client: A ClientFile instance with a record_id attribute.

    Returns:
        str: The document folder URL with {record_id} replaced, or None.
    """
    from apps.admin_settings.models import InstanceSetting

    # Try cache first
    settings_dict = cache.get("instance_settings")
    if settings_dict is None:
        settings_dict = InstanceSetting.get_all()
        cache.set("instance_settings", settings_dict, 300)

    provider = settings_dict.get("document_storage_provider", "none")
    template = settings_dict.get("document_storage_url_template", "")

    if provider == "none" or not template:
        return None

    if not client.record_id:
        return None

    encoded_id = quote(client.record_id, safe="")
    return template.replace("{record_id}", encoded_id)


def get_document_storage_info():
    """Get document storage configuration for templates.

    Returns:
        dict: Contains 'provider', 'provider_display', and 'is_configured'.
    """
    from apps.admin_settings.models import InstanceSetting

    # Try cache first
    settings_dict = cache.get("instance_settings")
    if settings_dict is None:
        settings_dict = InstanceSetting.get_all()
        cache.set("instance_settings", settings_dict, 300)

    provider = settings_dict.get("document_storage_provider", "none")

    provider_display_map = {
        "none": "Not configured",
        "sharepoint": "SharePoint / OneDrive",
        "google_drive": "Google Drive",
    }

    return {
        "provider": provider,
        "provider_display": provider_display_map.get(provider, "Unknown"),
        "is_configured": provider != "none",
    }


def get_client_tab_counts(client):
    """Get counts for client tab badges.

    Args:
        client: A ClientFile instance.

    Returns:
        dict: Contains counts for notes, events, plan sections/targets.
    """
    from apps.notes.models import ProgressNote
    from apps.events.models import Event, Alert
    from apps.plans.models import PlanSection, PlanTarget

    notes_count = ProgressNote.objects.filter(
        client_file=client,
        status="default"
    ).count()

    events_count = Event.objects.filter(
        client_file=client,
        status="default"
    ).count()

    # Active alerts (shown prominently)
    alerts_count = Alert.objects.filter(
        client_file=client,
        status="default"
    ).count()

    # Active plan targets
    targets_count = PlanTarget.objects.filter(
        client_file=client,
        status="default"
    ).count()

    return {
        "notes_count": notes_count,
        "events_count": events_count + alerts_count,  # Combined for Events tab
        "targets_count": targets_count,
    }
