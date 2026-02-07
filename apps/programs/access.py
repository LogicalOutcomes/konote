"""Shared helpers for program-scoped data access.

All views that need to check program access or filter data by program
should import from here instead of duplicating the logic.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.clients.models import ClientFile, ClientProgramEnrolment

from .models import Program, UserProgramRole


def get_user_program_ids(user, active_program_ids=None):
    """Return set of program IDs the user has active roles in.

    If active_program_ids is provided (from CONF9 context switcher),
    narrows to those programs only.
    """
    if active_program_ids:
        return active_program_ids
    return set(
        UserProgramRole.objects.filter(user=user, status="active")
        .values_list("program_id", flat=True)
    )


def get_accessible_programs(user, active_program_ids=None):
    """Return Program queryset the user can access.

    Admins without program roles get no programs (they manage system config,
    not client data). If active_program_ids is provided (CONF9), narrows to
    those programs only.
    """
    if active_program_ids:
        return Program.objects.filter(pk__in=active_program_ids, status="active")
    if user.is_admin:
        admin_program_ids = UserProgramRole.objects.filter(
            user=user, status="active"
        ).values_list("program_id", flat=True)
        if admin_program_ids:
            return Program.objects.filter(pk__in=admin_program_ids, status="active")
        return Program.objects.none()
    return Program.objects.filter(
        pk__in=UserProgramRole.objects.filter(
            user=user, status="active"
        ).values_list("program_id", flat=True),
        status="active",
    )


def get_author_program(user, client):
    """Return the first program the user shares with this client, or None.

    Used when creating notes/events to tag them with the authoring program.
    """
    user_program_ids = set(
        UserProgramRole.objects.filter(user=user, status="active")
        .values_list("program_id", flat=True)
    )
    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client, status="enrolled"
        ).values_list("program_id", flat=True)
    )
    shared = user_program_ids & client_program_ids
    if shared:
        return Program.objects.filter(pk__in=shared).first()
    return None


def get_client_or_403(request, client_id):
    """Return client if user has access via program roles, otherwise None.

    Checks:
    1. Client exists (404 if not)
    2. Demo/real data separation (user.is_demo must match client.is_demo)
    3. Admin bypass — admins can access any client (for system administration)
    4. User shares at least one program with the client

    Note: this checks *access* to the client record. Data filtering (which
    programs' notes/events/plans you see) is handled separately in each view.

    All views should use this single canonical function instead of their
    own copies.
    """
    client = get_object_or_404(ClientFile, pk=client_id)
    user = request.user

    # Demo/real data separation
    if client.is_demo != user.is_demo:
        return None

    # Admins can access any client (for system administration)
    if user.is_admin:
        return client

    user_program_ids = set(
        UserProgramRole.objects.filter(user=user, status="active")
        .values_list("program_id", flat=True)
    )
    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client, status="enrolled"
        ).values_list("program_id", flat=True)
    )
    if user_program_ids & client_program_ids:
        return client
    return None


def build_program_display_context(user, active_program_ids=None):
    """Determine display mode for program grouping in templates.

    Returns dict with:
      show_program_ui: True if user has 2+ accessible programs (show badges/filters)
      show_grouping: True if user has 2+ accessible programs (show group headers)
      accessible_programs: QuerySet of Program objects
      user_program_ids: set of int
    """
    user_program_ids = get_user_program_ids(user, active_program_ids)
    accessible_programs = get_accessible_programs(user, active_program_ids)
    program_count = accessible_programs.count()

    return {
        "show_program_ui": program_count > 1,
        "show_grouping": program_count > 1,
        "accessible_programs": accessible_programs,
        "user_program_ids": user_program_ids,
    }


def program_filter_q(field_name="author_program_id", program_ids=None):
    """Return a Q object to filter by program OR null program.

    Items with a null program are visible to all users with client access.
    Items with a specific program are only visible to users in that program.
    """
    return Q(**{f"{field_name}__in": program_ids}) | Q(**{f"{field_name}__isnull": True})
