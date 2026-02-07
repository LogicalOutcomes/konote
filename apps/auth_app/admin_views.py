"""User management views — admin only."""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.programs.models import Program, UserProgramRole

from .forms import UserCreateForm, UserEditForm, UserProgramRoleForm
from .models import User


def admin_required(view_func):
    """Decorator: 403 if user is not an admin."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            return HttpResponseForbidden("Access denied. Admin privileges required.")
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@login_required
@admin_required
def user_list(request):
    users = User.objects.all().order_by("-is_admin", "display_name")
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
@admin_required
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("User created."))
            return redirect("auth_app:user_list")
    else:
        form = UserCreateForm()
    return render(request, "auth_app/user_form.html", {"form": form, "editing": False})


@login_required
@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("User updated."))
            return redirect("auth_app:user_list")
    else:
        form = UserEditForm(instance=user)
    return render(request, "auth_app/user_form.html", {
        "form": form, "editing": True, "edit_user": user,
    })


@login_required
@admin_required
def user_deactivate(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        if user == request.user:
            messages.error(request, _("You cannot deactivate your own account."))
        else:
            user.is_active = False
            user.save()
            messages.success(request, _("User '%(name)s' deactivated.") % {"name": user.display_name})
    return redirect("auth_app:user_list")


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
        return redirect("auth_app:user_list")

    # Additional check: target must be active
    if not target_user.is_active:
        messages.error(request, _("Cannot impersonate inactive users."))
        return redirect("auth_app:user_list")

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
@admin_required
def user_roles(request, user_id):
    """Manage a user's program role assignments."""
    edit_user = get_object_or_404(User, pk=user_id)
    roles = (
        UserProgramRole.objects.filter(user=edit_user, status="active")
        .select_related("program")
        .order_by("program__name")
    )

    form = UserProgramRoleForm()
    # Exclude programs the user is already assigned to
    assigned_program_ids = roles.values_list("program_id", flat=True)
    form.fields["program"].queryset = Program.objects.filter(
        status="active",
    ).exclude(pk__in=assigned_program_ids)

    return render(request, "auth_app/user_roles.html", {
        "edit_user": edit_user,
        "roles": roles,
        "form": form,
        "has_available_programs": form.fields["program"].queryset.exists(),
    })


@login_required
@admin_required
def user_role_add(request, user_id):
    """Add a program role assignment (POST only)."""
    edit_user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        form = UserProgramRoleForm(request.POST)
        if form.is_valid():
            program = form.cleaned_data["program"]
            role = form.cleaned_data["role"]
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
    return redirect("auth_app:user_roles", user_id=edit_user.pk)


@login_required
@admin_required
def user_role_remove(request, user_id, role_id):
    """Remove a program role assignment (POST only)."""
    edit_user = get_object_or_404(User, pk=user_id)
    role_obj = get_object_or_404(UserProgramRole, pk=role_id, user=edit_user)
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
    return redirect("auth_app:user_roles", user_id=edit_user.pk)


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
        pass  # Don't fail the action if audit logging fails


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
        # Don't fail the impersonation if audit logging fails
        pass
