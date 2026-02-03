"""Program CRUD views — list visible to all users, management admin-only."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from apps.auth_app.models import User

from .forms import ProgramForm, UserProgramRoleForm
from .models import Program, UserProgramRole


def admin_required(view_func):
    """Decorator: 403 if user is not an admin."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            return HttpResponseForbidden("Access denied. Admin privileges required.")
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


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
            messages.success(request, "Program created.")
            return redirect("programs:program_list")
    else:
        form = ProgramForm()
    return render(request, "programs/form.html", {"form": form, "editing": False})


@login_required
@admin_required
def program_edit(request, program_id):
    program = get_object_or_404(Program, pk=program_id)
    if request.method == "POST":
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            form.save()
            messages.success(request, "Program updated.")
            return redirect("programs:program_detail", program_id=program.pk)
    else:
        form = ProgramForm(instance=program)
    return render(request, "programs/form.html", {"form": form, "editing": True, "program": program})


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

    return render(request, "programs/detail.html", {
        "program": program,
        "roles": roles,
        "role_form": role_form,
        "is_admin": request.user.is_admin,
        "user_has_access": user_has_access,
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
            messages.success(request, f"{user.display_name} role updated.")
        else:
            messages.success(request, f"{user.display_name} added.")
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
    messages.success(request, f"{role.user.display_name} removed.")
    roles = UserProgramRole.objects.filter(program_id=program_id).select_related("user").order_by("status", "user__display_name")
    return render(request, "programs/_role_list.html", {"roles": roles, "program": role.program, "is_admin": True})
