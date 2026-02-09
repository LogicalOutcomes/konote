"""Program CRUD views — list visible to all users, management admin-only."""
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.auth_app.decorators import admin_required
from apps.auth_app.models import User

from .context import (
    get_switcher_options,
    get_user_program_tiers,
    needs_program_selector,
    set_active_program,
)
from apps.groups.models import Group

from .forms import CONFIDENTIAL_KEYWORDS, ProgramForm, UserProgramRoleForm
from .models import Program, UserProgramRole

logger = logging.getLogger(__name__)


@login_required
def program_list(request):
    """List all programs — everyone sees all programs with basic info."""
    programs = Program.objects.all()

    # Get programs where current user has an active role
    user_program_ids = set(
        UserProgramRole.objects.filter(
            user=request.user, status="active"
        ).values_list("program_id", flat=True)
    )

    # Build program data with manager info
    program_data = []
    for program in programs:
        # Get program manager (if any)
        manager_role = UserProgramRole.objects.filter(
            program=program, role="program_manager", status="active"
        ).select_related("user").first()
        manager_name = manager_role.user.display_name if manager_role else None

        user_count = UserProgramRole.objects.filter(program=program, status="active").count()
        program_data.append({
            "program": program,
            "user_count": user_count,
            "manager_name": manager_name,
            "user_has_access": program.pk in user_program_ids,
        })
    return render(request, "programs/list.html", {
        "program_data": program_data,
        "is_admin": request.user.is_admin,
    })


@login_required
@admin_required
def program_create(request):
    if request.method == "POST":
        form = ProgramForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Program created."))
            return redirect("programs:program_list")
    else:
        form = ProgramForm()
    return render(request, "programs/form.html", {
        "form": form,
        "editing": False,
        "suggest_confidential": True,
        "confidential_keywords_json": json.dumps(CONFIDENTIAL_KEYWORDS),
    })


@login_required
@admin_required
def program_edit(request, program_id):
    program = get_object_or_404(Program, pk=program_id)
    if request.method == "POST":
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            form.save()
            messages.success(request, _("Program updated."))
            return redirect("programs:program_detail", program_id=program.pk)
    else:
        form = ProgramForm(instance=program)
    return render(request, "programs/form.html", {
        "form": form,
        "editing": True,
        "program": program,
        "confidential_locked": program.is_confidential,
    })


@login_required
def program_detail(request, program_id):
    """View program details — admins see management UI, staff see read-only info."""
    program = get_object_or_404(Program, pk=program_id)

    # Check if user has access to this program
    user_has_access = UserProgramRole.objects.filter(
        user=request.user, program=program, status="active"
    ).exists()

    # Non-admins without access see a friendly message
    if not request.user.is_admin and not user_has_access:
        return render(request, "programs/no_access.html", {"program": program})

    roles = UserProgramRole.objects.filter(program=program).select_related("user").order_by("status", "user__display_name")
    role_form = UserProgramRoleForm(program=program) if request.user.is_admin else None

    # Get this user's role in the program (for template permission checks)
    user_program_role = UserProgramRole.objects.filter(
        user=request.user, program=program, status="active"
    ).values_list("role", flat=True).first()
    is_receptionist = user_program_role == "receptionist"

    # Groups linked to this program (for group/both service models)
    groups = None
    if program.service_model in ("group", "both"):
        from django.db.models import Q
        groups = (
            Group.objects.filter(program=program, status="active")
            .annotate(member_count=Count(
                "memberships", filter=Q(memberships__status="active"),
            ))
            .order_by("name")
        )

    return render(request, "programs/detail.html", {
        "program": program,
        "roles": roles,
        "role_form": role_form,
        "is_admin": request.user.is_admin,
        "is_receptionist": is_receptionist,
        "user_has_access": user_has_access,
        "groups": groups,
    })


@login_required
@admin_required
def program_add_role(request, program_id):
    """HTMX: add a user to a program."""
    program = get_object_or_404(Program, pk=program_id)
    form = UserProgramRoleForm(request.POST, program=program)
    if form.is_valid():
        user = form.cleaned_data["user"]
        role = form.cleaned_data["role"]
        obj, created = UserProgramRole.objects.update_or_create(
            user=user, program=program,
            defaults={"role": role, "status": "active"},
        )
        if not created:
            messages.success(request, _("%(name)s role updated.") % {"name": user.display_name})
        else:
            messages.success(request, _("%(name)s added.") % {"name": user.display_name})
    # Return full role list partial
    roles = UserProgramRole.objects.filter(program=program).select_related("user").order_by("status", "user__display_name")
    return render(request, "programs/_role_list.html", {"roles": roles, "program": program, "is_admin": True})


@login_required
@admin_required
def program_remove_role(request, program_id, role_id):
    """HTMX: remove a user from a program (set status to removed)."""
    role = get_object_or_404(UserProgramRole, pk=role_id, program_id=program_id)
    role.status = "removed"
    role.save()
    messages.success(request, _("%(name)s removed.") % {"name": role.user.display_name})
    roles = UserProgramRole.objects.filter(program_id=program_id).select_related("user").order_by("status", "user__display_name")
    return render(request, "programs/_role_list.html", {"roles": roles, "program": role.program, "is_admin": True})


# --- CONF9: Program context switcher views ---


@login_required
def select_program(request):
    """Full-page program selection for mixed-tier users.

    Shown on login (and by middleware) when a user has roles in both
    Standard and Confidential programs but hasn't chosen a context yet.
    """
    tiers = get_user_program_tiers(request.user)
    options = get_switcher_options(request.user)
    return render(request, "programs/select_program.html", {
        "standard_programs": tiers["standard"],
        "confidential_programs": tiers["confidential"],
        "options": options,
    })


@login_required
def switch_program(request):
    """POST: Set the active program in the user's session.

    Accepts form field 'program' with value:
    - A program ID (integer) for a specific program
    - "all_standard" to see all standard programs combined

    Validates that the user has an active role in the chosen program.
    Audit-logs switches to confidential programs.
    Redirects to 'next' param or home.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    value = request.POST.get("program", "").strip()
    next_url = request.POST.get("next", "/")

    # Validate next URL (prevent open redirect)
    from django.utils.http import url_has_allowed_host_and_scheme
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"

    if value == "all_standard":
        # Valid if user has at least one standard program
        has_standard = UserProgramRole.objects.filter(
            user=request.user, status="active",
            program__status="active", program__is_confidential=False,
        ).exists()
        if not has_standard:
            return HttpResponseForbidden(_("You do not have access to any standard programs."))
        set_active_program(request.session, "all_standard")
        messages.info(request, _("Now viewing: %(name)s") % {"name": _("All Standard Programs")})
        return redirect(next_url)

    # Single program ID
    try:
        program_id = int(value)
    except (ValueError, TypeError):
        return HttpResponseForbidden(_("Invalid program selection."))

    # Verify user has active role in this program
    try:
        role = UserProgramRole.objects.select_related("program").get(
            user=request.user, program_id=program_id, status="active",
            program__status="active",
        )
    except UserProgramRole.DoesNotExist:
        return HttpResponseForbidden(_("You do not have access to this program."))

    set_active_program(request.session, program_id)
    messages.info(request, _("Now viewing: %(name)s") % {"name": role.program.name})

    # Audit-log switches to confidential programs
    if role.program.is_confidential:
        _audit_program_switch(request, role.program)

    return redirect(next_url)


def _audit_program_switch(request, program):
    """Log a context switch to a confidential program in the audit trail."""
    try:
        from apps.audit.models import AuditLog
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.pk,
            user_display=request.user.display_name,
            ip_address=_get_client_ip(request),
            action="view",
            resource_type="program",
            resource_id=program.pk,
            program_id=program.pk,
            is_confidential_context=True,
            metadata={"context_switch": True, "program_name": program.name},
        )
    except Exception:
        logger.exception("Failed to audit program context switch for user %s", request.user.pk)


from konote.utils import get_client_ip as _get_client_ip
