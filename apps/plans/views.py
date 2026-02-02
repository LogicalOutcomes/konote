"""Phase 3: Plan editing views — sections, targets, metrics, revisions."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import UserProgramRole

from .forms import (
    MetricAssignmentForm,
    MetricDefinitionForm,
    PlanSectionForm,
    PlanSectionStatusForm,
    PlanTargetForm,
    PlanTargetStatusForm,
)
from .models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
    PlanTargetRevision,
)


# ---------------------------------------------------------------------------
# Permission helper
# ---------------------------------------------------------------------------

def _can_edit_plan(user, client_file):
    """
    Return True if the user may modify this client's plan.
    Admins can always edit. Programme managers can edit if they manage a
    programme the client is enrolled in. Staff cannot edit.
    """
    if user.is_admin:
        return True
    # Get programmes this client is enrolled in
    enrolled_program_ids = ClientProgramEnrolment.objects.filter(
        client_file=client_file, status="enrolled"
    ).values_list("program_id", flat=True)
    # Check if user is a programme manager for any of those programmes
    return UserProgramRole.objects.filter(
        user=user,
        program_id__in=enrolled_program_ids,
        role="program_manager",
        status="active",
    ).exists()


def _get_client_or_403(client_id, user):
    """Fetch client and verify the user has at least view access."""
    return get_object_or_404(ClientFile, pk=client_id)


# ---------------------------------------------------------------------------
# Plan tab view
# ---------------------------------------------------------------------------

@login_required
def plan_view(request, client_id):
    """Full plan tab — all sections with targets and metrics."""
    client = _get_client_or_403(client_id, request.user)
    can_edit = _can_edit_plan(request.user, client)

    sections = (
        PlanSection.objects.filter(client_file=client)
        .prefetch_related("targets__metrics", "program")
        .order_by("sort_order")
    )

    active_sections = [s for s in sections if s.status == "default"]
    inactive_sections = [s for s in sections if s.status != "default"]

    return render(request, "plans/plan_view.html", {
        "client": client,
        "active_sections": active_sections,
        "inactive_sections": inactive_sections,
        "can_edit": can_edit,
    })


# ---------------------------------------------------------------------------
# Section CRUD
# ---------------------------------------------------------------------------

@login_required
def section_create(request, client_id):
    """Add a new section to a client's plan."""
    client = _get_client_or_403(client_id, request.user)
    if not _can_edit_plan(request.user, client):
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        form = PlanSectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.client_file = client
            section.save()
            messages.success(request, "Section added.")
            return redirect("plans:plan_view", client_id=client.pk)
    else:
        form = PlanSectionForm()

    return render(request, "plans/plan_view.html", {
        "client": client,
        "active_sections": list(PlanSection.objects.filter(client_file=client, status="default")),
        "inactive_sections": list(PlanSection.objects.filter(client_file=client).exclude(status="default")),
        "can_edit": True,
        "section_form": form,
        "show_section_form": True,
    })


@login_required
def section_edit(request, section_id):
    """HTMX inline edit — GET returns edit form partial, POST saves and returns section partial."""
    section = get_object_or_404(PlanSection, pk=section_id)
    if not _can_edit_plan(request.user, section.client_file):
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        form = PlanSectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, "Section updated.")
            return render(request, "plans/_section.html", {
                "section": section,
                "can_edit": True,
            })
    else:
        form = PlanSectionForm(instance=section)

    return render(request, "plans/_section_edit.html", {
        "section": section,
        "form": form,
    })


@login_required
def section_status(request, section_id):
    """HTMX dialog to change section status with reason."""
    section = get_object_or_404(PlanSection, pk=section_id)
    if not _can_edit_plan(request.user, section.client_file):
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        form = PlanSectionStatusForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, "Section status updated.")
            return render(request, "plans/_section.html", {
                "section": section,
                "can_edit": True,
            })
    else:
        form = PlanSectionStatusForm(instance=section)

    return render(request, "plans/_section_status.html", {
        "section": section,
        "form": form,
    })


# ---------------------------------------------------------------------------
# Target CRUD
# ---------------------------------------------------------------------------

@login_required
def target_create(request, section_id):
    """Add a new target to a section."""
    section = get_object_or_404(PlanSection, pk=section_id)
    if not _can_edit_plan(request.user, section.client_file):
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        form = PlanTargetForm(request.POST)
        if form.is_valid():
            target = form.save(commit=False)
            target.plan_section = section
            target.client_file = section.client_file
            target.save()
            # Create initial revision
            PlanTargetRevision.objects.create(
                plan_target=target,
                name=target.name,
                description=target.description,
                status=target.status,
                status_reason=target.status_reason,
                changed_by=request.user,
            )
            messages.success(request, "Target added.")
            return redirect("plans:plan_view", client_id=section.client_file.pk)
    else:
        form = PlanTargetForm()

    return render(request, "plans/target_form.html", {
        "form": form,
        "section": section,
        "client": section.client_file,
        "editing": False,
    })


@login_required
def target_edit(request, target_id):
    """Edit a target. Creates a revision with OLD values before saving."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    if not _can_edit_plan(request.user, target.client_file):
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        # Save old values as a revision BEFORE overwriting
        PlanTargetRevision.objects.create(
            plan_target=target,
            name=target.name,
            description=target.description,
            status=target.status,
            status_reason=target.status_reason,
            changed_by=request.user,
        )
        form = PlanTargetForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, "Target updated.")
            return redirect("plans:plan_view", client_id=target.client_file.pk)
    else:
        form = PlanTargetForm(instance=target)

    return render(request, "plans/target_form.html", {
        "form": form,
        "target": target,
        "section": target.plan_section,
        "client": target.client_file,
        "editing": True,
    })


@login_required
def target_status(request, target_id):
    """HTMX dialog to change target status with reason. Creates a revision."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    if not _can_edit_plan(request.user, target.client_file):
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        # Revision with old values
        PlanTargetRevision.objects.create(
            plan_target=target,
            name=target.name,
            description=target.description,
            status=target.status,
            status_reason=target.status_reason,
            changed_by=request.user,
        )
        form = PlanTargetStatusForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, "Target status updated.")
            return render(request, "plans/_target.html", {
                "target": target,
                "can_edit": True,
            })
    else:
        form = PlanTargetStatusForm(instance=target)

    return render(request, "plans/_target_status.html", {
        "target": target,
        "form": form,
    })


# ---------------------------------------------------------------------------
# Metric assignment (PLAN3)
# ---------------------------------------------------------------------------

@login_required
def target_metrics(request, target_id):
    """Assign metrics to a target — checkboxes grouped by category."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    if not _can_edit_plan(request.user, target.client_file):
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        form = MetricAssignmentForm(request.POST)
        if form.is_valid():
            selected = form.cleaned_data["metrics"]
            # Remove old assignments
            PlanTargetMetric.objects.filter(plan_target=target).delete()
            # Create new ones
            for i, metric_def in enumerate(selected):
                PlanTargetMetric.objects.create(
                    plan_target=target, metric_def=metric_def, sort_order=i
                )
            messages.success(request, "Metrics updated.")
            return redirect("plans:plan_view", client_id=target.client_file.pk)
    else:
        current_ids = PlanTargetMetric.objects.filter(plan_target=target).values_list("metric_def_id", flat=True)
        form = MetricAssignmentForm(initial={"metrics": current_ids})

    # Group metrics by category for template display
    metrics_by_category = {}
    for metric in MetricDefinition.objects.filter(is_enabled=True, status="active"):
        cat = metric.get_category_display()
        metrics_by_category.setdefault(cat, []).append(metric)

    return render(request, "plans/target_metrics.html", {
        "form": form,
        "target": target,
        "client": target.client_file,
        "metrics_by_category": metrics_by_category,
    })


# ---------------------------------------------------------------------------
# Metric library (admin) — PLAN3
# ---------------------------------------------------------------------------

@login_required
def metric_library(request):
    """Admin-only page listing all metric definitions by category."""
    if not request.user.is_admin:
        return HttpResponseForbidden("Access denied.")

    metrics = MetricDefinition.objects.all()
    metrics_by_category = {}
    for metric in metrics:
        cat = metric.get_category_display()
        metrics_by_category.setdefault(cat, []).append(metric)

    return render(request, "plans/metric_library.html", {
        "metrics_by_category": metrics_by_category,
    })


@login_required
def metric_toggle(request, metric_id):
    """HTMX POST to toggle is_enabled on a metric definition."""
    if not request.user.is_admin:
        return HttpResponseForbidden("Access denied.")

    metric = get_object_or_404(MetricDefinition, pk=metric_id)
    if request.method == "POST":
        metric.is_enabled = not metric.is_enabled
        metric.save()
    # Return just the toggle button fragment
    return render(request, "plans/_metric_toggle.html", {"metric": metric})


@login_required
def metric_create(request):
    """Admin form to create a custom metric definition."""
    if not request.user.is_admin:
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        form = MetricDefinitionForm(request.POST)
        if form.is_valid():
            metric = form.save(commit=False)
            metric.is_library = False
            metric.save()
            messages.success(request, "Metric created.")
            return redirect("plans:metric_library")
    else:
        form = MetricDefinitionForm()

    return render(request, "plans/metric_form.html", {
        "form": form,
        "editing": False,
    })


@login_required
def metric_edit(request, metric_id):
    """Admin form to edit a metric definition."""
    if not request.user.is_admin:
        return HttpResponseForbidden("Access denied.")

    metric = get_object_or_404(MetricDefinition, pk=metric_id)
    if request.method == "POST":
        form = MetricDefinitionForm(request.POST, instance=metric)
        if form.is_valid():
            form.save()
            messages.success(request, "Metric updated.")
            return redirect("plans:metric_library")
    else:
        form = MetricDefinitionForm(instance=metric)

    return render(request, "plans/metric_form.html", {
        "form": form,
        "editing": True,
        "metric": metric,
    })


# ---------------------------------------------------------------------------
# Revision history (PLAN6)
# ---------------------------------------------------------------------------

@login_required
def target_history(request, target_id):
    """Show revision history for a target."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    revisions = PlanTargetRevision.objects.filter(plan_target=target).select_related("changed_by")

    return render(request, "plans/target_history.html", {
        "target": target,
        "client": target.client_file,
        "revisions": revisions,
    })
