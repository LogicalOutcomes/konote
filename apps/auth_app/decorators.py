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
    """Return the user's highest client-access role across all programs.

    The executive role is excluded because it does not grant access to
    individual client data.  If the user only has executive roles, None
    is returned so that minimum_role checks will deny access.
    """
    from apps.programs.models import UserProgramRole

    roles = set(
        UserProgramRole.objects.filter(
            user=user, status="active",
        ).values_list("role", flat=True)
    )
    if not roles:
        return None
    # Only consider roles that grant client-level data access
    client_roles = roles & UserProgramRole.CLIENT_ACCESS_ROLES
    if not client_roles:
        return None
    return max(client_roles, key=lambda r: ROLE_RANK.get(r, 0))


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


def programme_role_required(min_role, get_programme_fn):
    """Decorator: check user's role in a SPECIFIC programme, not across all programmes.

    This fixes the security hole where a user with receptionist in Programme A
    and staff in Programme B could access Programme A's clinical data because
    their highest role across all programmes is "staff".

    Args:
        min_role: minimum role name (e.g., "staff")
        get_programme_fn: function that extracts programme from view args.
                          Example: lambda req, group_id: get_object_or_404(Group, pk=group_id).program

    Usage:
        @programme_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def group_detail(request, group_id):
            ...
    """
    from apps.programs.models import UserProgramRole
    from django.shortcuts import get_object_or_404

    min_rank = ROLE_RANK.get(min_role, 0)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get the programme for this resource
            try:
                programme = get_programme_fn(request, *args, **kwargs)
            except Exception as e:
                # If we can't determine the programme, deny access
                message = f"Unable to determine programme for this resource: {str(e)}"
                response = TemplateResponse(
                    request, "403.html", {"exception": message}, status=403,
                )
                response.render()
                return response

            # Get user's role in THIS programme (not highest across all)
            role_obj = UserProgramRole.objects.filter(
                user=request.user,
                program=programme,
                status="active"
            ).first()

            if not role_obj:
                message = _("You do not have access to this programme.")
                response = TemplateResponse(
                    request, "403.html", {"exception": message}, status=403,
                )
                response.render()
                return response

            user_rank = ROLE_RANK.get(role_obj.role, 0)
            if user_rank < min_rank:
                message = _(
                    "Your role ({role}) in this programme cannot access this resource. "
                    "Required: {min_role} or higher."
                ).format(role=role_obj.get_role_display(), min_role=min_role)
                response = TemplateResponse(
                    request, "403.html", {"exception": message}, status=403,
                )
                response.render()
                return response

            # Store for use in view
            request.user_programme_role = role_obj.role
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
