"""Template tags for permission checks.

Usage in templates:
    {% load permissions_tags %}
    {% has_permission "note.view" as can_view_notes %}
    {% if can_view_notes %}<a href="...">Notes</a>{% endif %}
"""
from django import template

from apps.auth_app.constants import ROLE_RANK
from apps.auth_app.permissions import DENY, can_access

register = template.Library()


@register.simple_tag(takes_context=True)
def has_permission(context, permission_key):
    """Check if the current user has a given permission.

    Returns True if the user's highest role has non-DENY access for this key.
    For users with roles in multiple programs, uses the highest role
    (most permissive) since template-level checks control UI visibility,
    not data access.

    Returns False for unauthenticated users.
    """
    request = context.get("request")
    if request is None:
        return False

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False

    from apps.programs.models import UserProgramRole

    roles = set(
        UserProgramRole.objects.filter(
            user=user, status="active",
        ).values_list("role", flat=True)
    )

    if not roles:
        return False

    # Use the highest role (most permissive) for UI visibility
    highest_role = max(roles, key=lambda r: ROLE_RANK.get(r, 0))
    level = can_access(highest_role, permission_key)
    return level != DENY
