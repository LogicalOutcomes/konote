"""Role-based access decorators for views."""
from functools import wraps

from django.http import HttpResponseForbidden
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _

from apps.auth_app.constants import ROLE_RANK


def admin_required(view_func):
    """Decorator: 403 if user is not an admin."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            return HttpResponseForbidden(_("Access denied. Admin privileges required."))
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_user_highest_role(user):
    """Return the user's highest role across all active program assignments."""
    from apps.programs.models import UserProgramRole

    roles = UserProgramRole.objects.filter(
        user=user, status="active",
    ).values_list("role", flat=True)
    if not roles:
        return None
    return max(roles, key=lambda r: ROLE_RANK.get(r, 0))


def minimum_role(min_role):
    """Decorator: require at least this program role to access the view.

    Uses request.user_program_role if set by ProgramAccessMiddleware
    (client-scoped routes). Falls back to the user's highest role across
    all programs for routes without a client_id in the URL.
    """
    min_rank = ROLE_RANK.get(min_role, 0)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_role = getattr(request, "user_program_role", None)
            if user_role is None:
                user_role = _get_user_highest_role(request.user)
            if user_role is None or ROLE_RANK.get(user_role, 0) < min_rank:
                message = "Access denied. You do not have the required role for this action."
                response = TemplateResponse(
                    request, "403.html", {"exception": message}, status=403,
                )
                response.render()
                return response
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
