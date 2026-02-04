"""Template context processors for terminology, features, and settings."""
from django.core.cache import cache
from django.utils.translation import get_language


def terminology(request):
    """Inject terminology overrides into all templates.

    Detects the current language from the request and returns terms
    in that language. Falls back to English if French translation
    is not available or if any error occurs.
    """
    from apps.admin_settings.models import TerminologyOverride

    try:
        # Get current language (returns 'en', 'fr', etc.)
        lang = get_language() or "en"
        lang_prefix = "fr" if lang.startswith("fr") else "en"
    except Exception:
        # If translation system fails, default to English
        lang_prefix = "en"

    cache_key = f"terminology_overrides_{lang_prefix}"

    terms = cache.get(cache_key)
    if terms is None:
        terms = TerminologyOverride.get_all_terms(lang=lang_prefix)
        cache.set(cache_key, terms, 300)  # 5 min cache
    return {"term": terms}


def features(request):
    """Inject feature toggles into all templates."""
    from apps.admin_settings.models import FeatureToggle

    flags = cache.get("feature_toggles")
    if flags is None:
        flags = FeatureToggle.get_all_flags()
        cache.set("feature_toggles", flags, 300)
    return {"features": flags}


def instance_settings(request):
    """Inject instance settings (branding, formats) into all templates."""
    from apps.admin_settings.models import InstanceSetting

    settings_dict = cache.get("instance_settings")
    if settings_dict is None:
        settings_dict = InstanceSetting.get_all()
        cache.set("instance_settings", settings_dict, 300)
    return {"site": settings_dict}


def user_roles(request):
    """Inject the user's role information into all templates.

    - has_program_roles: whether the user has any active program assignments
    - is_admin_only: admin with no program roles (cannot see client data)
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {"has_program_roles": False, "is_admin_only": False}

    from apps.programs.models import UserProgramRole

    has_roles = UserProgramRole.objects.filter(
        user=request.user, status="active"
    ).exists()
    return {
        "has_program_roles": has_roles,
        "is_admin_only": request.user.is_admin and not has_roles,
    }


def document_storage(request):
    """Inject document storage configuration into all templates.

    Provides:
    - document_storage.provider: 'none', 'sharepoint', or 'google_drive'
    - document_storage.provider_display: Human-readable provider name
    - document_storage.is_configured: Boolean for quick template checks
    """
    from apps.clients.helpers import get_document_storage_info
    return {"document_storage": get_document_storage_info()}


def pending_submissions(request):
    """Inject pending registration submissions count for admin badge.

    Only calculated for admin users to avoid unnecessary queries.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {}

    if not request.user.is_admin:
        return {}

    from apps.registration.models import RegistrationSubmission

    count = cache.get("pending_submissions_count")
    if count is None:
        count = RegistrationSubmission.objects.filter(status="pending").count()
        cache.set("pending_submissions_count", count, 60)  # 1 min cache
    return {"pending_submissions_count": count if count > 0 else None}
