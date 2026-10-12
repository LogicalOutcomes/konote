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

    # Cache the user's highest role on the request to avoid repeated DB
    # queries when multiple {% has_permission %} calls appear in one template
    highest_role = getattr(request, "_perm_tag_highest_role", None)
    if highest_role is None:
        from apps.programs.models import UserProgramRole

        roles = set(
            UserProgramRole.objects.filter(
                user=user, status="active",
            ).values_list("role", flat=True)
        )

        if not roles:
            request._perm_tag_highest_role = ""
            return False

        highest_role = max(roles, key=lambda r: ROLE_RANK.get(r, 0))
        request._perm_tag_highest_role = highest_role
    elif highest_role == "":
        return False

    level = can_access(highest_role, permission_key)
    if level != DENY:
        return True

    # Check per-user explicit grants for specific permissions.
    # Mirrors apps.reports.utils.can_create_evaluation_export — keep in sync.
    if permission_key == "report.evaluation_export":
        return getattr(user, "evaluation_export_granted", False)

    # LTE — strictly separate from evaluation_export. Mirrors
    # apps.reports.utils.can_create_lte_export — keep in sync. Admin
    # bypass does not apply; the grant is per-user.
    if permission_key == "report.evaluation_export_small_population":
        return getattr(user, "lte_export_granted", False)

    return False
