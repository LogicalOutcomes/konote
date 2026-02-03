"""Template context processors for terminology, features, and settings."""
from django.core.cache import cache


def terminology(request):
    """Inject terminology overrides into all templates."""
    from apps.admin_settings.models import TerminologyOverride

    terms = cache.get("terminology_overrides")
    if terms is None:
        terms = TerminologyOverride.get_all_terms()
        cache.set("terminology_overrides", terms, 300)  # 5 min cache
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
