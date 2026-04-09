"""User management views — admin and PM access.

Admins: full access to all users.
PMs with user.manage: PROGRAM: manage staff/receptionist in their own programs.
Invites and impersonation remain admin-only (separate views).
"""
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

from apps.programs.access import get_user_program_ids
from apps.programs.models import Program, UserProgramRole

from apps.auth_app.constants import MANAGEMENT_ROLES, ROLE_PROGRAM_MANAGER, ROLE_RECEPTIONIST, ROLE_STAFF
from konote.utils import get_client_ip
from .decorators import admin_required, requires_permission
from .forms import (
    EvaluationExportGrantForm,
    UserCreateForm,
    UserEditForm,
    UserProgramRoleForm,
)
from .models import EvaluationExportGrant, User

# Roles that PMs are NOT allowed to assign (no-elevation constraint).
# PMs with user.manage: PROGRAM can manage staff in their own program
# but cannot create PM/executive accounts or elevate front desk to staff.
_PM_BLOCKED_ROLE_ASSIGNMENTS = MANAGEMENT_ROLES


def _get_pm_program_ids(user):
    """Return set of program IDs where the user is an active PM."""
    return set(
        UserProgramRole.objects.filter(
            user=user, role=ROLE_PROGRAM_MANAGER, status="active",
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
                if existing_role == ROLE_RECEPTIONIST and role == ROLE_STAFF:
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


# ---------------------------------------------------------------------------
# EVAL-GOV1 — Evaluator Export Access grant management
# ---------------------------------------------------------------------------
#
# The governance model in tasks/eval-export-governance.md requires a
# two-person control: ED authorises an evaluation engagement and then
# the Admin records the grant in KoNote with a reason. These views are
# the only supported way to set `evaluation_export_granted` — the flag
# on User is now read-only in the Django admin and removed from the
# general user edit form.


@login_required
@admin_required
def eval_export_grant_list(request):
    """Show active evaluator-export grants and the revoke control.

    The table is the agency's audit view: who holds the permission,
    who granted it, when, and the reason. Revoked grants are not shown
    here — they live in the audit log.

    Admin-only: the DRR (evaluation-microdata-export.md) and governance
    doc (eval-export-governance.md) both specify that only system admins
    grant `report.evaluation_export`. A Program Manager with
    user.manage: PROGRAM should not see agency-wide grants.
    """
    # Join the most recent evaluation-microdata export per grantee so
    # the admin can see whether the permission is actually being used.
    # Use a correlated subquery annotation rather than loading every
    # SecureExportLink into memory — keeps the list view O(1) memory
    # even at large agencies with long export histories.
    from django.db.models import OuterRef, Subquery
    from apps.reports.models import SecureExportLink

    last_export_subquery = (
        SecureExportLink.objects
        .filter(
            export_type="evaluation_microdata",
            created_by_id=OuterRef("user_id"),
        )
        .order_by("-created_at")
        .values("created_at")[:1]
    )

    grants = (
        EvaluationExportGrant.objects
        .filter(active=True)
        .select_related("user", "granted_by")
        .annotate(last_export_at=Subquery(last_export_subquery))
        .order_by("user__display_name")
    )

    # Flag grants that haven't been used for 6+ months (or were never
    # used at all and are older than 6 months). The DRR rejected
    # automatic expiry — visibility is the agreed safeguard — so this
    # is the visibility.
    stale_cutoff = timezone.now() - timedelta(days=180)
    grant_rows = []
    for g in grants:
        reference_date = g.last_export_at or g.granted_at
        is_stale = reference_date < stale_cutoff
        grant_rows.append({
            "grant": g,
            "last_export_at": g.last_export_at,
            "is_stale": is_stale,
        })

    return render(request, "auth_app/eval_export_grant_list.html", {
        "grant_rows": grant_rows,
        "stale_days": 180,
    })


@login_required
@admin_required
def eval_export_grant_create(request):
    """Grant evaluator-export access to a user.

    The reason field is mandatory and logged to the audit DB so the
    grant is tied back to the ED's authorising decision. Attempting to
    grant a user who already has an active grant re-renders the form
    with a clear error — revoke the existing grant first.

    Admin-only (see eval_export_grant_list docstring for rationale).
    """
    users_with_active_grants = set(
        EvaluationExportGrant.objects
        .filter(active=True)
        .values_list("user_id", flat=True)
    )

    # Candidate users: active, not already holding an active grant.
    # Admins and non-admins alike can hold the permission (the panel
    # decided PMs are legitimate operators), but inactive accounts
    # should not be grantable.
    candidate_users = (
        User.objects
        .filter(is_active=True)
        .exclude(pk__in=users_with_active_grants)
        .order_by("display_name", "username")
    )

    initial_user_id = None
    form = EvaluationExportGrantForm()
    error = None

    if request.method == "POST":
        raw_user_id = request.POST.get("user_id") or ""
        raw_reason = request.POST.get("reason") or ""
        try:
            user_id = int(raw_user_id) if raw_user_id else 0
        except (TypeError, ValueError):
            user_id = 0
        initial_user_id = user_id
        form = EvaluationExportGrantForm(request.POST)

        target = User.objects.filter(pk=user_id, is_active=True).first()
        if not target:
            error = _("Please choose a user to grant this permission to.")
            _audit_eval_export_attempt_rejected(
                request,
                failure_reason="invalid_user",
                attempted_user_id=raw_user_id,
                raw_reason=raw_reason,
            )
        elif user_id in users_with_active_grants:
            error = _(
                "This user already has an active grant. Revoke the "
                "existing grant before issuing a new one."
            )
            _audit_eval_export_attempt_rejected(
                request,
                failure_reason="duplicate_active_grant",
                attempted_user_id=raw_user_id,
                raw_reason=raw_reason,
            )
        elif not form.is_valid():
            _audit_eval_export_attempt_rejected(
                request,
                failure_reason="reason_validation_failed",
                attempted_user_id=raw_user_id,
                raw_reason=raw_reason,
                form_errors=dict(form.errors),
            )
        else:
            reason = form.cleaned_data["reason"]
            # Wrap the create in a savepoint so an IntegrityError from
            # the partial unique constraint (concurrent grant for the
            # same user) doesn't poison the outer transaction. The view
            # check above catches the common case, but two admins
            # racing can slip past it — the DB constraint is the final
            # guarantee and we need to handle it gracefully.
            try:
                with transaction.atomic():
                    grant = EvaluationExportGrant.objects.create(
                        user=target,
                        granted_by=request.user,
                        reason=reason,
                    )
            except IntegrityError:
                error = _(
                    "This user already has an active grant. Revoke the "
                    "existing grant before issuing a new one."
                )
                _audit_eval_export_attempt_rejected(
                    request,
                    failure_reason="race_duplicate_active_grant",
                    attempted_user_id=raw_user_id,
                    raw_reason=raw_reason,
                )
            else:
                _audit_eval_export_grant(
                    request, grant, action="create", reason=reason,
                )
                messages.success(
                    request,
                    _("Evaluator export access granted to %(name)s.")
                    % {"name": target.display_name},
                )
                return redirect("admin_users:eval_export_grant_list")

    else:
        try:
            initial_user_id = int(request.GET.get("user_id") or 0) or None
        except (TypeError, ValueError):
            initial_user_id = None

    return render(request, "auth_app/eval_export_grant_form.html", {
        "form": form,
        "candidate_users": candidate_users,
        "initial_user_id": initial_user_id,
        "error": error,
    })


@login_required
@admin_required
def eval_export_grant_revoke(request, grant_id):
    """Revoke an active grant. POST only.

    Admin-only (see eval_export_grant_list docstring for rationale).
    """
    if request.method != "POST":
        return redirect("admin_users:eval_export_grant_list")

    grant = get_object_or_404(EvaluationExportGrant, pk=grant_id, active=True)
    grant.active = False
    grant.revoked_at = timezone.now()
    grant.revoked_by = request.user
    grant.save()

    _audit_eval_export_grant(
        request, grant, action="update", reason=grant.reason,
    )
    messages.success(
        request,
        _("Evaluator export access revoked for %(name)s.")
        % {"name": grant.user.display_name},
    )
    return redirect("admin_users:eval_export_grant_list")


def _audit_eval_export_attempt_rejected(
    request, failure_reason, attempted_user_id, raw_reason, form_errors=None,
):
    """Record a rejected grant-creation attempt in the audit DB.

    We log rejections as well as successes so a privacy officer can
    see whether anyone is probing the grant endpoint (e.g., repeated
    attempts with invalid users, or racing past the duplicate check).
    The rule of thumb: anything that hit the view and was turned away
    should leave a trace.

    ``failure_reason`` is a short code:
      - ``invalid_user``: target not found or inactive
      - ``duplicate_active_grant``: view-level check caught a duplicate
      - ``race_duplicate_active_grant``: DB IntegrityError caught a
        concurrent duplicate that slipped past the view check
      - ``reason_validation_failed``: the form rejected the reason
        (too short, placeholder, etc.)
    """
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.id,
            user_display=request.user.get_display_name(),
            ip_address=get_client_ip(request),
            action="access_denied",
            resource_type="evaluation_export_grant",
            resource_id=None,
            metadata={
                "outcome": "rejected",
                "failure_reason": failure_reason,
                "attempted_user_id": str(attempted_user_id)[:100],
                "raw_reason": (raw_reason or "")[:2000],
                "form_errors": form_errors or {},
            },
        )
    except Exception:
        logger.exception(
            "Failed to audit rejected evaluation_export_grant attempt "
            "by user %s (failure_reason=%s)",
            request.user.id, failure_reason,
        )


def _audit_eval_export_grant(request, grant, action, reason):
    """Record an evaluator-export grant create/revoke in the audit DB."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.id,
            user_display=request.user.get_display_name(),
            ip_address=get_client_ip(request),
            action=action,
            resource_type="evaluation_export_grant",
            resource_id=grant.pk,
            metadata={
                "grant_id": grant.pk,
                "target_user_id": grant.user_id,
                "target_user": grant.user.display_name,
                "granted_by_id": grant.granted_by_id,
                "granted_by_display": (
                    grant.granted_by.display_name if grant.granted_by else None
                ),
                "active": grant.active,
                "reason": reason,
                "revoked_at": (
                    grant.revoked_at.isoformat() if grant.revoked_at else None
                ),
                "revoked_by_id": grant.revoked_by_id,
            },
        )
    except Exception:
        logger.exception(
            "Failed to audit evaluation_export_grant %s for user %s",
            grant.pk, grant.user_id,
        )


def _audit_user_change(request, target_user, action_type, old_values, new_values):
    """Record user account creation or modification in audit log."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.id,
            user_display=request.user.get_display_name(),
            ip_address=get_client_ip(request),
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
            ip_address=get_client_ip(request),
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
            ip_address=get_client_ip(request),
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
