"""Role-based access decorators for views."""
import logging
from functools import wraps

from django.http import HttpResponseForbidden
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _

from apps.auth_app.constants import ROLE_RANK
from apps.auth_app.permissions import (
    ALL_PERMISSION_KEYS,
    ALLOW,
    DENY,
    GATED,
    PER_FIELD,
    SCOPED,
    can_access,
)

logger = logging.getLogger(__name__)


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


def _get_user_highest_role_any(user):
    """Return the user's highest role across all programs, INCLUDING executive.

    Unlike _get_user_highest_role, this includes executive roles.
    Used by requires_permission_global where the matrix itself decides
    what each role can do (executives may have ALLOW for some keys).
    """
    from apps.programs.models import UserProgramRole

    roles = set(
        UserProgramRole.objects.filter(
            user=user, status="active",
        ).values_list("role", flat=True)
    )
    if not roles:
        return None
    return max(roles, key=lambda r: ROLE_RANK.get(r, 0))


def minimum_role(min_role):
    """Decorator: require at least this program role to access the view.

    Uses request.user_program_role if set by ProgramAccessMiddleware
    (client-scoped routes). Falls back to the user's highest role across
    all programs for routes without a client_id in the URL.

    DEPRECATED: Use @requires_permission("key") instead. This decorator
    is kept for views not yet migrated to the permission matrix.
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


def _render_403(request, message):
    """Render 403 page with message. Shared by permission decorators."""
    response = TemplateResponse(
        request, "403.html", {"exception": message}, status=403,
    )
    response.render()
    return response


def _check_client_access_block(request, get_client_fn, args, kwargs):
    """Check ClientAccessBlock for DV safety. Returns 403 response or None.

    Fail closed: if we can't verify the block list, deny access.
    ClientAccessBlock exists for DV safety — never skip silently.
    """
    if get_client_fn is None:
        return None
    try:
        client = get_client_fn(request, *args, **kwargs)
        if client is not None:
            from apps.clients.models import ClientAccessBlock
            if ClientAccessBlock.objects.filter(
                user=request.user, client_file=client, is_active=True
            ).exists():
                return _render_403(request, _("Access to this client has been restricted."))
    except Exception:
        return _render_403(request, _("Unable to verify access permissions."))
    return None


def requires_permission(permission_key, get_program_fn=None, get_client_fn=None, allow_admin=False):
    """Decorator: check permission matrix for the user's role in the relevant program.

    Replaces @minimum_role and @program_role_required. Reads from
    permissions.py via can_access() — changes to the matrix immediately
    affect enforcement.

    Args:
        permission_key: key like "note.create" from PERMISSIONS matrix
        get_program_fn: function(request, *args, **kwargs) -> Program.
                        If None, uses user's highest role across all programs.
        get_client_fn: optional function for ClientAccessBlock check.
        allow_admin: if True, admin users (is_admin=True) bypass the matrix
                     check entirely. Use for report/export views where admins
                     need access even without a program role.

    Usage:
        @requires_permission("note.create", _get_program_from_client)
        def note_create(request, client_id):
            ...

        @requires_permission("client.create")  # no program — uses highest role
        def client_create(request):
            ...

        @requires_permission("report.funder_report", allow_admin=True)
        def funder_report_form(request):
            ...
    """
    # Validate at import time that the key exists in the matrix
    if permission_key not in ALL_PERMISSION_KEYS:
        raise ValueError(
            f"Unknown permission key '{permission_key}'. "
            f"Valid keys: {sorted(ALL_PERMISSION_KEYS)}"
        )

    # Safety: allow_admin must not be combined with client-scoped views,
    # because the bypass skips ClientAccessBlock (DV safety).  Catch misuse
    # at import time rather than in production.
    if allow_admin and get_client_fn is not None:
        raise ValueError(
            f"allow_admin=True cannot be used with get_client_fn (permission "
            f"'{permission_key}'). The admin bypass skips ClientAccessBlock "
            f"checks, which is unsafe for client-scoped views."
        )

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Admin bypass — admin is NOT a program role, so the matrix
            # has no entry for them. Views that should be accessible to
            # admins (e.g. report generation) opt in with allow_admin=True.
            # SAFETY: This skips ClientAccessBlock, so allow_admin must
            # never be used on client-scoped views (enforced above).
            if allow_admin and getattr(request.user, "is_admin", False):
                return view_func(request, *args, **kwargs)

            # --- Determine the user's role ---
            user_role = None

            if get_program_fn is not None:
                # Program-scoped: get role in the specific program
                from apps.programs.models import UserProgramRole
                try:
                    program = get_program_fn(request, *args, **kwargs)
                except Exception as e:
                    return _render_403(
                        request,
                        f"Unable to determine program for this resource: {str(e)}"
                    )

                # Check ClientAccessBlock (DV safety)
                block_response = _check_client_access_block(
                    request, get_client_fn, args, kwargs
                )
                if block_response is not None:
                    return block_response

                role_obj = UserProgramRole.objects.filter(
                    user=request.user,
                    program=program,
                    status="active"
                ).first()

                if not role_obj:
                    return _render_403(
                        request,
                        _("You do not have access to this program.")
                    )

                user_role = role_obj.role
                request.user_program_role = role_obj.role
            else:
                # No program in URL — use highest role across all programs
                # Check ClientAccessBlock if client function provided
                block_response = _check_client_access_block(
                    request, get_client_fn, args, kwargs
                )
                if block_response is not None:
                    return block_response

                user_role = _get_user_highest_role_any(request.user)
                if user_role is not None:
                    request.user_program_role = user_role

            if user_role is None:
                return _render_403(
                    request,
                    _("You do not have any program roles.")
                )

            # --- Check the matrix ---
            level = can_access(user_role, permission_key)

            if level == DENY:
                return _render_403(
                    request,
                    _("Access denied. Your role does not have permission for this action.")
                )

            if level in (ALLOW, SCOPED):
                return view_func(request, *args, **kwargs)

            if level == GATED:
                # Future: check for documented justification.
                # For now, treat as ALLOW with a log warning.
                logger.warning(
                    "GATED permission '%s' treated as ALLOW for user %s (role=%s). "
                    "Justification UI not yet implemented.",
                    permission_key, request.user.pk, user_role,
                )
                return view_func(request, *args, **kwargs)

            if level == PER_FIELD:
                # Future: delegate to field-level check.
                # For now, treat as ALLOW with a log warning.
                logger.warning(
                    "PER_FIELD permission '%s' treated as ALLOW for user %s (role=%s). "
                    "Field-level check not yet implemented.",
                    permission_key, request.user.pk, user_role,
                )
                return view_func(request, *args, **kwargs)

            # Unknown level — fail closed
            logger.error(
                "Unknown permission level '%s' for key '%s', role '%s'. Denying access.",
                level, permission_key, user_role,
            )
            return _render_403(
                request,
                _("Access denied. Unable to determine permission level.")
            )

        return wrapper
    return decorator


def requires_permission_global(permission_key):
    """Like requires_permission but always uses user's highest role across all programs.

    For views like group_list, insights, etc. that aren't scoped to a single
    client or program. The matrix itself decides what each role can do.

    Usage:
        @requires_permission_global("group.view_roster")
        def group_list(request):
            ...
    """
    return requires_permission(permission_key, get_program_fn=None, get_client_fn=None)


def program_role_required(min_role, get_program_fn, get_client_fn=None):
    """Decorator: check user's role in a SPECIFIC program, not across all programs.

    This fixes the security hole where a user with front desk role in Program A
    and staff in Program B could access Program A's clinical data because
    their highest role across all programs is "staff".

    DEPRECATED: Use @requires_permission("key", get_program_fn) instead.
    Kept for views not yet migrated to the permission matrix.

    Args:
        min_role: minimum role name (e.g., "staff")
        get_program_fn: function that extracts program from view args.
                        Example: lambda req, group_id: get_object_or_404(Group, pk=group_id).program
        get_client_fn: optional function that extracts client for access block check.
                       If provided, checks ClientAccessBlock before allowing access.

    Usage:
        @program_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def group_detail(request, group_id):
            ...
    """
    from apps.programs.models import UserProgramRole
    from django.shortcuts import get_object_or_404

    min_rank = ROLE_RANK.get(min_role, 0)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get the program for this resource
            try:
                program = get_program_fn(request, *args, **kwargs)
            except Exception as e:
                # If we can't determine the program, deny access
                return _render_403(
                    request,
                    f"Unable to determine program for this resource: {str(e)}"
                )

            # Optional: check negative access list (ClientAccessBlock)
            block_response = _check_client_access_block(
                request, get_client_fn, args, kwargs
            )
            if block_response is not None:
                return block_response

            # Get user's role in THIS program (not highest across all)
            role_obj = UserProgramRole.objects.filter(
                user=request.user,
                program=program,
                status="active"
            ).first()

            if not role_obj:
                return _render_403(
                    request,
                    _("You do not have access to this program.")
                )

            user_rank = ROLE_RANK.get(role_obj.role, 0)
            if user_rank < min_rank:
                message = _(
                    "Your role ({role}) in this program cannot access this resource. "
                    "Required: {min_role} or higher."
                ).format(role=role_obj.get_role_display(), min_role=min_role)
                return _render_403(request, message)

            # Store for use in view
            request.user_program_role = role_obj.role
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

