"""Program context switcher — session-based active program for multi-tier staff.

CONF9: When a user has roles in both Standard and Confidential programs,
they must select which program context to work in. This module provides
the session logic for storing, validating, and querying the active program.
"""
from django.utils.translation import gettext_lazy as _

from .models import Program, UserProgramRole

SESSION_KEY = "active_program_id"


def get_user_program_tiers(user):
    """Return user's programs grouped by tier.

    Returns dict with 'standard' and 'confidential' lists.
    Each entry: {'id': int, 'name': str, 'role': str, 'role_display': str}
    Only includes active roles in active programs.
    """
    roles = (
        UserProgramRole.objects.filter(user=user, status="active", program__status="active")
        .select_related("program")
        .order_by("program__name")
    )
    tiers = {"standard": [], "confidential": []}
    for r in roles:
        entry = {
            "id": r.program_id,
            "name": r.program.name,
            "role": r.role,
            "role_display": r.get_role_display(),
        }
        if r.program.is_confidential:
            tiers["confidential"].append(entry)
        else:
            tiers["standard"].append(entry)
    return tiers


def needs_program_selector(user):
    """Return True if the user needs the program context switcher.

    Trigger: user has 2+ active programs where at least one is confidential.
    Standard-only multi-program users keep the current 'see all' behaviour.
    """
    programs = (
        UserProgramRole.objects.filter(user=user, status="active", program__status="active")
        .select_related("program")
    )
    has_confidential = False
    total = 0
    for r in programs:
        total += 1
        if r.program.is_confidential:
            has_confidential = True
    # Need selector if 2+ programs AND at least one is confidential
    return total >= 2 and has_confidential


def needs_program_selection(user, session):
    """Return True if selector is needed AND user hasn't made a valid selection yet."""
    if not needs_program_selector(user):
        return False
    value = session.get(SESSION_KEY)
    if value is None:
        return True
    # Validate that the stored selection is still valid
    return not _is_valid_selection(user, value)


def get_active_program_ids(user, session):
    """Return set of program IDs to filter client lists by.

    - Single int in session -> {that_id}
    - "all_standard" in session -> all user's standard program IDs
    - Not set + doesn't need selector -> all user's program IDs (backwards compatible)
    - Not set + needs selector -> empty set (forces selection page)
    """
    all_user_program_ids = set(
        UserProgramRole.objects.filter(user=user, status="active", program__status="active")
        .values_list("program_id", flat=True)
    )

    if not needs_program_selector(user):
        # No selector needed — return all programs (backwards compatible)
        return all_user_program_ids

    value = session.get(SESSION_KEY)
    if value is None:
        return set()  # Forces selection

    if value == "all_standard":
        return set(
            UserProgramRole.objects.filter(
                user=user, status="active", program__status="active",
                program__is_confidential=False,
            ).values_list("program_id", flat=True)
        )

    try:
        program_id = int(value)
    except (ValueError, TypeError):
        return set()

    if program_id in all_user_program_ids:
        return {program_id}
    return set()  # Invalid selection — force re-selection


def set_active_program(session, value):
    """Set the active program in session. Value is an int ID or 'all_standard'."""
    session[SESSION_KEY] = value


def clear_active_program(session):
    """Remove active program from session."""
    session.pop(SESSION_KEY, None)


def get_switcher_options(user):
    """Build the dropdown options list for the program switcher.

    Returns list of dicts: {'value': str, 'label': str}
    - "All Standard Programs" only if user has 2+ standard programs
    - Each program as individual option (program name + role)
    - Never labels programs as "Confidential"
    - Never offers "All Confidential" combined option
    """
    tiers = get_user_program_tiers(user)
    options = []

    # "All Standard Programs" option — only if 2+ standard programs
    if len(tiers["standard"]) >= 2:
        options.append({
            "value": "all_standard",
            "label": str(_("All Standard Programs")),
        })

    # Individual standard programs
    for prog in tiers["standard"]:
        options.append({
            "value": str(prog["id"]),
            "label": f"{prog['name']} — {prog['role_display']}",
        })

    # Individual confidential programs (never combined)
    for prog in tiers["confidential"]:
        options.append({
            "value": str(prog["id"]),
            "label": f"{prog['name']} — {prog['role_display']}",
        })

    return options


def _is_valid_selection(user, value):
    """Check if a session value is still valid for this user."""
    if value == "all_standard":
        # Valid if user still has at least one standard program
        return UserProgramRole.objects.filter(
            user=user, status="active", program__status="active",
            program__is_confidential=False,
        ).exists()

    try:
        program_id = int(value)
    except (ValueError, TypeError):
        return False

    return UserProgramRole.objects.filter(
        user=user, status="active", program_id=program_id,
        program__status="active",
    ).exists()
