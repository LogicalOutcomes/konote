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
    - is_executive_only: executive role with no other roles (dashboard only)
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {"has_program_roles": False, "is_admin_only": False, "is_executive_only": False}

    from apps.programs.models import UserProgramRole

    roles = set(
        UserProgramRole.objects.filter(user=request.user, status="active").values_list("role", flat=True)
    )
    has_roles = bool(roles)

    # Export access: admins and program managers can create reports
    has_export_access = request.user.is_admin or "program_manager" in roles

    return {
        "has_program_roles": has_roles,
        "is_admin_only": request.user.is_admin and not has_roles,
        "is_executive_only": UserProgramRole.is_executive_only(request.user, roles=roles),
        "has_export_access": has_export_access,
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


def pending_erasures(request):
    """Inject pending erasure request count for admin/PM nav badge.

    PMs see count for their programs; admins see all. Cached 1 minute.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {}

    from apps.programs.models import UserProgramRole

    is_pm = UserProgramRole.objects.filter(
        user=request.user, role="program_manager", status="active",
    ).exists()

    if not request.user.is_admin and not is_pm:
        return {}

    cache_key = f"pending_erasure_count_{request.user.pk}"
    count = cache.get(cache_key)
    if count is None:
        from apps.clients.models import ErasureRequest

        if request.user.is_admin:
            count = ErasureRequest.objects.filter(status="pending").count()
        else:
            # PM-scoped: count requests where at least one required program is theirs
            # Filters in Python — works on all DB backends (SQLite + PostgreSQL)
            pm_program_ids = list(
                UserProgramRole.objects.filter(
                    user=request.user, role="program_manager", status="active",
                ).values_list("program_id", flat=True)
            )
            pids_set = set(pm_program_ids)
            pending = ErasureRequest.objects.filter(status="pending")
            count = sum(
                1 for r in pending
                if pids_set & set(r.programs_required or [])
            )
        cache.set(cache_key, count, 60)  # 1 min cache
    return {"pending_erasure_count": count if count > 0 else None}


def active_program_context(request):
    """Inject active program context for the program switcher (CONF9).

    Only runs queries for authenticated users with multi-tier program access.
    Single-program and standard-only users get empty context (no switcher shown).
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {
            "show_program_switcher": False,
            "active_program_id": None,
            "active_program_name": "",
            "program_options": [],
            "active_service_model": None,
            "active_program_role": "",
            "active_program_role_display": "",
        }

    from apps.programs.context import (
        SESSION_KEY,
        get_switcher_options,
        needs_program_selector,
    )
    from apps.programs.models import Program, UserProgramRole

    # Use cached result from middleware when available (CONF9c).
    selector_needed = getattr(request, "_needs_program_selector", None)
    if selector_needed is None:
        selector_needed = needs_program_selector(request.user)

    if not selector_needed:
        # Check if user has exactly one program — use its service model + role
        single_program_sm = None
        single_role = ""
        single_role_display = ""
        user_roles = UserProgramRole.objects.filter(
            user=request.user, status="active", program__status="active",
        ).select_related("program")[:2]
        if len(user_roles) == 1:
            single_program_sm = user_roles[0].program.service_model
            single_role = user_roles[0].role
            single_role_display = user_roles[0].get_role_display()
        return {
            "show_program_switcher": False,
            "active_program_id": None,
            "active_program_name": "",
            "program_options": [],
            "active_service_model": single_program_sm,
            "active_program_role": single_role,
            "active_program_role_display": single_role_display,
        }

    options = get_switcher_options(request.user)
    value = request.session.get(SESSION_KEY)

    # Determine display name, service model, and role for the active selection
    active_name = ""
    active_service_model = None
    active_role = ""
    active_role_display = ""
    if value == "all_standard":
        from django.utils.translation import gettext as _

        active_name = _("All Standard Programs")
        # For "all standard", show the user's highest role across standard programs
        from apps.programs.context import get_user_program_tiers
        tiers = get_user_program_tiers(request.user)
        from apps.auth_app.constants import ROLE_RANK

        best = None
        for prog in tiers["standard"]:
            if best is None or ROLE_RANK.get(prog["role"], 0) > ROLE_RANK.get(
                best["role"], 0
            ):
                best = prog
        if best:
            active_role = best["role"]
            active_role_display = best["role_display"]
    elif value is not None:
        try:
            program = Program.objects.get(pk=int(value))
            active_name = program.name
            active_service_model = program.service_model
            role_obj = UserProgramRole.objects.filter(
                user=request.user, program=program, status="active",
            ).first()
            if role_obj:
                active_role = role_obj.role
                active_role_display = role_obj.get_role_display()
        except (Program.DoesNotExist, ValueError, TypeError):
            pass

    # Convert value to string for template comparison
    active_id = str(value) if value is not None else ""

    return {
        "show_program_switcher": True,
        "active_program_id": active_id,
        "active_program_name": active_name,
        "program_options": options,
        "active_service_model": active_service_model,
        "active_program_role": active_role,
        "active_program_role_display": active_role_display,
    }
