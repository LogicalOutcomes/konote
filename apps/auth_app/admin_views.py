"""User management views — admin and PM access.

Admins: full access to all users.
PMs with user.manage: PROGRAM: manage staff/receptionist in their own programs.
Invites and impersonation remain admin-only (separate views).
"""
import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

from apps.programs.access import get_user_program_ids
from apps.programs.models import Program, UserProgramRole

from .decorators import admin_required, requires_permission
from .forms import UserCreateForm, UserEditForm, UserProgramRoleForm
from .models import User

# Roles that PMs are NOT allowed to assign (no-elevation constraint).
# PMs with user.manage: PROGRAM can manage staff in their own program
# but cannot create PM/executive accounts or elevate front desk to staff.
_PM_BLOCKED_ROLE_ASSIGNMENTS = {"program_manager", "executive"}


def _get_pm_program_ids(user):
    """Return set of program IDs where the user is an active PM."""
    return set(
        UserProgramRole.objects.filter(
            user=user, role="program_manager", status="active",
        ).values_list("program_id", flat=True)
    )


def _user_in_pm_programs(pm_user, target_user):
    """Check if the target user shares at least one program with the PM."""
    pm_programs = _get_pm_program_ids(pm_user)
    target_programs = set(
        UserProgramRole.objects.filter(
            user=target_user, status="active",
        ).values_list("program_id", flat=True)
    )
    return bool(pm_programs & target_programs)


@login_required
@requires_permission("user.manage", allow_admin=True)
def user_list(request):
    if request.user.is_admin:
        users = User.objects.all().order_by("-is_admin", "display_name")
    else:
        # PMs see only users who share a program with them
        pm_program_ids = _get_pm_program_ids(request.user)
        user_ids_in_programs = set(
            UserProgramRole.objects.filter(
                program_id__in=pm_program_ids, status="active",
            ).values_list("user_id", flat=True)
        )
        users = User.objects.filter(
            pk__in=user_ids_in_programs,
        ).order_by("-is_admin", "display_name")

    # Prefetch program roles for display
    user_roles = {}
    for role in UserProgramRole.objects.filter(
        status="active",
    ).select_related("program"):
        user_roles.setdefault(role.user_id, []).append(role)

    user_data = []
    for u in users:
        user_data.append({"user": u, "roles": user_roles.get(u.pk, [])})

    return render(request, "auth_app/user_list.html", {"user_data": user_data})


@login_required
@requires_permission("user.manage", allow_admin=True)
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST, requesting_user=request.user)
        if form.is_valid():
            new_user = form.save()
            _audit_user_change(
                request, new_user, "create",
                old_values={},
                new_values={"email": new_user.email, "is_admin": new_user.is_admin},
            )
            messages.success(request, _("User created."))
            return redirect("admin_users:user_list")
    else:
        form = UserCreateForm(requesting_user=request.user)
    return render(request, "auth_app/user_form.html", {"form": form, "editing": False})


@login_required
@requires_permission("user.manage", allow_admin=True)
def user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    # PMs can only edit users who share a program with them
    if not request.user.is_admin:
        if not _user_in_pm_programs(request.user, user):
            return HttpResponseForbidden(_("Access denied. You can only manage users in your programs."))

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user, requesting_user=request.user)
        if form.is_valid():
            old_values = {"email": user.email, "is_admin": user.is_admin, "is_active": user.is_active}
            form.save()
            _audit_user_change(
                request, user, "update",
                old_values=old_values,
                new_values={"email": user.email, "is_admin": user.is_admin, "is_active": user.is_active},
            )
            messages.success(request, _("User updated."))
            return redirect("admin_users:user_list")
    else:
        form = UserEditForm(instance=user, requesting_user=request.user)
    return render(request, "auth_app/user_form.html", {
        "form": form, "editing": True, "edit_user": user,
    })


@login_required
@requires_permission("user.manage", allow_admin=True)
def user_deactivate(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    # PMs can only deactivate users in their programs
    if not request.user.is_admin:
        if not _user_in_pm_programs(request.user, user):
            return HttpResponseForbidden(_("Access denied. You can only manage users in your programs."))

    if request.method == "POST":
        if user == request.user:
            messages.error(request, _("You cannot deactivate your own account."))
        elif user.is_admin and not request.user.is_admin:
            messages.error(request, _("Only administrators can deactivate admin accounts."))
        else:
            user.is_active = False
            user.save()
            _audit_user_change(
                request, user, "update",
                old_values={"is_active": True},
                new_values={"is_active": False},
            )
            messages.success(request, _("User '%(name)s' deactivated.") % {"name": user.display_name})
    return redirect("admin_users:user_list")


@login_required
@admin_required
def impersonate_user(request, user_id):
    """
    Allow admin to log in as a demo user for testing purposes.

    CRITICAL SECURITY: Only demo users (is_demo=True) can be impersonated.
    Real users cannot be impersonated regardless of admin privileges.
    """
    target_user = get_object_or_404(User, pk=user_id)

    # CRITICAL SECURITY CHECK: Only allow impersonation of demo users
    if not target_user.is_demo:
        messages.error(
            request,
            _("Cannot impersonate real users. Only demo accounts can be impersonated.")
        )
        return redirect("admin_users:user_list")

    # Additional check: target must be active
    if not target_user.is_active:
        messages.error(request, _("Cannot impersonate inactive users."))
        return redirect("admin_users:user_list")

    # Log the impersonation for audit trail
    _audit_impersonation(request, target_user)

    # Store original user info in session for potential "return to admin" feature
    original_user_id = request.user.id
    original_username = request.user.username

    # Perform logout then login as demo user
    logout(request)
    login(request, target_user)

    # Update last login timestamp
    target_user.last_login_at = timezone.now()
    target_user.save(update_fields=["last_login_at"])

    messages.success(
        request,
        _("You are now logged in as %(name)s (demo account). "
          "Impersonated by admin '%(admin)s'.") % {
            "name": target_user.get_display_name(),
            "admin": original_username,
        }
    )
    return redirect("/")


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------


@login_required
@requires_permission("user.manage", allow_admin=True)
def user_roles(request, user_id):
    """Manage a user's program role assignments."""
    edit_user = get_object_or_404(User, pk=user_id)

    # PMs can only manage roles for users in their programs
    if not request.user.is_admin:
        if not _user_in_pm_programs(request.user, edit_user):
            return HttpResponseForbidden(_("Access denied. You can only manage users in your programs."))

    roles = (
        UserProgramRole.objects.filter(user=edit_user, status="active")
        .select_related("program")
        .order_by("program__name")
    )

    form = UserProgramRoleForm()
    # Exclude programs the user is already assigned to
    assigned_program_ids = roles.values_list("program_id", flat=True)

    if request.user.is_admin:
        available_programs = Program.objects.filter(
            status="active",
        ).exclude(pk__in=assigned_program_ids)
    else:
        # PMs can only assign to their own programs
        pm_program_ids = _get_pm_program_ids(request.user)
        available_programs = Program.objects.filter(
            status="active", pk__in=pm_program_ids,
        ).exclude(pk__in=assigned_program_ids)

    form.fields["program"].queryset = available_programs

    # For non-admin users, restrict role choices (no PM/executive)
    if not request.user.is_admin:
        form.fields["role"].choices = [
            (value, label) for value, label in UserProgramRole.ROLE_CHOICES
            if value not in _PM_BLOCKED_ROLE_ASSIGNMENTS
        ]

    return render(request, "auth_app/user_roles.html", {
        "edit_user": edit_user,
        "roles": roles,
        "form": form,
        "has_available_programs": available_programs.exists(),
    })


@login_required
@requires_permission("user.manage", allow_admin=True)
def user_role_add(request, user_id):
    """Add a program role assignment (POST only).

    No-elevation constraint: non-admin users with user.manage: PROGRAM
    (program managers) cannot assign PM or executive roles, and cannot
    elevate front desk to staff.
    """
    edit_user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        form = UserProgramRoleForm(request.POST)
        if form.is_valid():
            program = form.cleaned_data["program"]
            role = form.cleaned_data["role"]

            # No-elevation constraint for non-admin users
            if not request.user.is_admin:
                # PMs can only assign roles in their own programs
                pm_program_ids = _get_pm_program_ids(request.user)
                if program.pk not in pm_program_ids:
                    messages.error(
                        request,
                        _("You can only assign roles in your own programs."),
                    )
                    return redirect("admin_users:user_roles", user_id=edit_user.pk)

                if role in _PM_BLOCKED_ROLE_ASSIGNMENTS:
                    messages.error(
                        request,
                        _("You cannot assign the %(role)s role. "
                          "Only administrators can assign manager or executive roles.")
                        % {"role": role},
                    )
                    return redirect("admin_users:user_roles", user_id=edit_user.pk)

                # PMs cannot change front desk to staff (grants clinical access)
                existing_role = UserProgramRole.objects.filter(
                    user=edit_user, program=program, status="active",
                ).values_list("role", flat=True).first()
                if existing_role == "receptionist" and role == "staff":
                    messages.error(
                        request,
                        _("Elevating front desk to staff grants clinical data access. "
                          "Only administrators can make this change."),
                    )
                    return redirect("admin_users:user_roles", user_id=edit_user.pk)

            obj, created = UserProgramRole.objects.get_or_create(
                user=edit_user,
                program=program,
                defaults={"role": role, "status": "active"},
            )
            if not created:
                # Reactivate if previously removed
                obj.role = role
                obj.status = "active"
                obj.save()
            messages.success(
                request,
                _("%(name)s assigned as %(role)s in %(program)s.")
                % {
                    "name": edit_user.display_name,
                    "role": obj.get_role_display(),
                    "program": program.name,
                },
            )
            _audit_role_change(request, edit_user, program, role, "add")
    return redirect("admin_users:user_roles", user_id=edit_user.pk)


@login_required
@requires_permission("user.manage", allow_admin=True)
def user_role_remove(request, user_id, role_id):
    """Remove a program role assignment (POST only)."""
    edit_user = get_object_or_404(User, pk=user_id)
    role_obj = get_object_or_404(UserProgramRole, pk=role_id, user=edit_user)

    # PMs can only remove roles in their own programs
    if not request.user.is_admin:
        pm_program_ids = _get_pm_program_ids(request.user)
        if role_obj.program_id not in pm_program_ids:
            return HttpResponseForbidden(_("Access denied. You can only manage roles in your programs."))

    if request.method == "POST":
        role_obj.status = "removed"
        role_obj.save()
        messages.success(
            request,
            _("Role removed from %(program)s.")
            % {"program": role_obj.program.name},
        )
        _audit_role_change(
            request, edit_user, role_obj.program, role_obj.role, "remove",
        )
    return redirect("admin_users:user_roles", user_id=edit_user.pk)


def _audit_user_change(request, target_user, action_type, old_values, new_values):
    """Record user account creation or modification in audit log."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.id,
            user_display=request.user.get_display_name(),
            ip_address=request.META.get("REMOTE_ADDR", ""),
            action=action_type,
            resource_type="user",
            resource_id=target_user.id,
            metadata={
                "target_user_id": target_user.id,
                "target_user": target_user.display_name,
                "old_values": old_values,
                "new_values": new_values,
            },
        )
    except Exception:
        logger.exception("Failed to audit user change for user %s", target_user.id)


def _audit_role_change(request, target_user, program, role, action_type):
    """Record role change in audit log."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.id,
            user_display=request.user.get_display_name(),
            ip_address=request.META.get("REMOTE_ADDR", ""),
            action="update",
            resource_type="user_program_role",
            resource_id=target_user.id,
            metadata={
                "target_user_id": target_user.id,
                "target_user": target_user.display_name,
                "program": program.name,
                "program_id": program.id,
                "role": role,
                "change": action_type,
            },
        )
    except Exception:
        logger.exception("Failed to audit role change for user %s", target_user.id)


def _audit_impersonation(request, target_user):
    """Record impersonation event in audit log."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.id,
            user_display=request.user.get_display_name(),
            ip_address=request.META.get("REMOTE_ADDR", ""),
            action="login",  # Using 'login' as closest match from ACTION_CHOICES
            resource_type="impersonation",
            resource_id=target_user.id,
            is_demo_context=True,  # Impersonation is always into a demo user
            metadata={
                "impersonated_user_id": target_user.id,
                "impersonated_username": target_user.username,
                "impersonated_display_name": target_user.get_display_name(),
                "admin_user_id": request.user.id,
                "admin_username": request.user.username,
            },
        )
    except Exception:
        logger.exception("Failed to audit impersonation of user %s", target_user.id)
