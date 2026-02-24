"""Access-control helpers for circles.

Circles have no program FK — visibility is derived from membership.
A user can see a circle if they can access at least one of its members.

DV safety: when ClientAccessBlock hides a member and fewer than 4
visible members remain, hide the entire circle (DRR risk registry).
"""
from apps.clients.models import ClientAccessBlock, ClientProgramEnrolment
from apps.programs.models import UserProgramRole

from .models import Circle, CircleMembership


def _get_accessible_client_ids(user):
    """Return set of ClientFile IDs this user can access through program roles."""
    user_program_ids = set(
        UserProgramRole.objects.filter(user=user, status="active")
        .values_list("program_id", flat=True)
    )
    return set(
        ClientProgramEnrolment.objects.filter(
            program_id__in=user_program_ids, status="enrolled"
        ).values_list("client_file_id", flat=True)
    )


def _get_blocked_client_ids(user):
    """Return set of ClientFile IDs the user is blocked from (DV safety)."""
    return set(
        ClientAccessBlock.objects.filter(user=user, is_active=True)
        .values_list("client_file_id", flat=True)
    )


def get_visible_circles(user):
    """Return Circle queryset visible to this user.

    Visibility rules:
    1. User can see a circle if at least one member's client_file is accessible
    2. Blocked clients (ClientAccessBlock) are excluded from member count
    3. If a block causes fewer than 4 visible members, hide the entire circle
       (DV safety — in a 2-person household, hiding one reveals the other by absence)
    4. Demo/real data separation via user.is_demo
    """
    # Get base circle queryset matching demo status
    if user.is_demo:
        base_circles = Circle.objects.demo().filter(status="active")
    else:
        base_circles = Circle.objects.real().filter(status="active")

    accessible_ids = _get_accessible_client_ids(user)
    blocked_ids = _get_blocked_client_ids(user)
    # Remove blocked clients from accessible set
    accessible_ids -= blocked_ids

    # Find circles where at least one active member is accessible
    visible_circle_ids = set(
        CircleMembership.objects.filter(
            circle__in=base_circles,
            client_file_id__in=accessible_ids,
            status="active",
        ).values_list("circle_id", flat=True)
    )

    if not blocked_ids or not visible_circle_ids:
        # No blocks — no DV small-circle hiding needed
        return base_circles.filter(pk__in=visible_circle_ids)

    # DV small-circle hiding: single query for all visible circles,
    # then group by circle_id in Python to check each one.
    from collections import defaultdict
    all_memberships = CircleMembership.objects.filter(
        circle_id__in=visible_circle_ids, status="active"
    ).values_list("circle_id", "client_file_id")

    circle_members = defaultdict(list)
    for cid, client_id in all_memberships:
        circle_members[cid].append(client_id)

    circles_to_hide = set()
    for circle_id in visible_circle_ids:
        member_ids = circle_members.get(circle_id, [])
        has_blocked = any(mid in blocked_ids for mid in member_ids if mid)
        if has_blocked:
            visible_count = sum(
                1 for mid in member_ids
                if mid is None or (mid in accessible_ids)
            )
            if visible_count < 4:
                circles_to_hide.add(circle_id)

    final_ids = visible_circle_ids - circles_to_hide
    return base_circles.filter(pk__in=final_ids)


def get_accessible_notes_for_circle(circle, user):
    """Return ProgressNotes tagged to this circle that the user can access.

    PHIPA: Only show notes where the user has access to note.client_file.
    Returns (accessible_notes, total_count) so the template can show
    "Showing X of Y" when some notes are hidden.
    """
    all_notes = circle.tagged_notes.filter(
        status="default",
    ).select_related("client_file", "author", "author_program").order_by("-created_at")

    total_count = all_notes.count()

    accessible_ids = _get_accessible_client_ids(user)
    blocked_ids = _get_blocked_client_ids(user)
    accessible_ids -= blocked_ids

    accessible_notes = [
        note for note in all_notes
        if note.client_file_id in accessible_ids
    ]

    return accessible_notes, total_count
