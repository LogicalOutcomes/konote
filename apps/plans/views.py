"""Phase 3: Plan editing views — sections, targets, metrics, revisions."""
import csv
import io
from collections import OrderedDict

from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.audit.models import AuditLog
from apps.auth_app.decorators import admin_required, program_role_required, requires_permission
from apps.auth_app.permissions import DENY, can_access
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.access import (
    build_program_display_context,
    get_client_or_403,
    get_program_from_client,
    get_user_program_ids,
)
from apps.programs.models import UserProgramRole

from django.db import transaction
from django.http import JsonResponse

from .forms import (
    GoalForm,
    MetricAssignmentForm,
    MetricDefinitionForm,
    MetricImportForm,
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
# Permission helpers
# ---------------------------------------------------------------------------

_get_program_from_client = get_program_from_client


def _get_program_from_section(request, section_id, **kwargs):
    """Extract program via section → client."""
    section = get_object_or_404(PlanSection, pk=section_id)
    return _get_program_from_client(request, section.client_file_id)


def _get_program_from_target(request, target_id, **kwargs):
    """Extract program via target → client."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    return _get_program_from_client(request, target.client_file_id)


def _can_edit_plan(user, client_file):
    """Return True if the user may modify this client's plan.

    Uses the permissions matrix (plan.edit) — only roles with ALLOW or SCOPED
    for plan.edit can edit. Currently staff has SCOPED, PM has DENY.

    Note: admin status does NOT bypass program role checks (PERM-S2).
    """
    from apps.auth_app.permissions import DENY, can_access

    enrolled_program_ids = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client_file, status="enrolled"
        ).values_list("program_id", flat=True)
    )
    return UserProgramRole.objects.filter(
        user=user,
        program_id__in=enrolled_program_ids,
        status="active",
    ).exclude(
        role__in=[
            r for r in ["receptionist", "staff", "program_manager", "executive"]
            if can_access(r, "plan.edit") == DENY
        ]
    ).exists()



# ---------------------------------------------------------------------------
# Plan tab view
# ---------------------------------------------------------------------------

@login_required
@requires_permission("plan.view", _get_program_from_client)
def plan_view(request, client_id):
    """Full plan tab — all sections with targets and metrics."""
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")
    can_edit = _can_edit_plan(request.user, client)

    # Get user's accessible programs (respects CONF9 context switcher)
    active_ids = getattr(request, "active_program_ids", None)
    user_program_ids = get_user_program_ids(request.user, active_ids)
    program_ctx = build_program_display_context(request.user, active_ids)

    # Filter sections to user's accessible programs + null-program sections
    sections = (
        PlanSection.objects.filter(client_file=client)
        .filter(Q(program_id__in=user_program_ids) | Q(program__isnull=True))
        .prefetch_related("targets__metrics")
        .select_related("program")
        .order_by("sort_order")
    )

    active_sections = [s for s in sections if s.status == "default"]
    inactive_sections = [s for s in sections if s.status != "default"]

    # Build grouped context for multi-program display
    grouped_active_sections = None
    general_sections = None
    if program_ctx["show_grouping"]:
        grouped_active_sections = OrderedDict()
        general_sections = []
        for section in active_sections:
            if section.program_id:
                key = section.program_id
                if key not in grouped_active_sections:
                    grouped_active_sections[key] = {
                        "program": section.program,
                        "sections": [],
                    }
                grouped_active_sections[key]["sections"].append(section)
            else:
                general_sections.append(section)

    # Check if user can apply templates (admin or PM with template.plan.manage)
    can_apply_template = request.user.is_admin or any(
        can_access(r.role, "template.plan.manage") != DENY
        for r in UserProgramRole.objects.filter(user=request.user, status="active")
    )

    # Check if AI Goal Builder is available
    from konote.ai_views import _ai_enabled
    ai_enabled = can_edit and _ai_enabled()

    context = {
        "client": client,
        "active_sections": active_sections,
        "inactive_sections": inactive_sections,
        "can_edit": can_edit,
        "can_apply_template": can_apply_template,
        "ai_enabled": ai_enabled,
        "active_tab": "plan",
        "show_grouping": program_ctx["show_grouping"],
        "show_program_ui": program_ctx["show_program_ui"],
        "grouped_active_sections": grouped_active_sections,
        "general_sections": general_sections,
    }
    if request.headers.get("HX-Request"):
        return render(request, "plans/_tab_plan.html", context)
    return render(request, "plans/plan_view.html", context)


# ---------------------------------------------------------------------------
# Section CRUD
# ---------------------------------------------------------------------------

@login_required
@requires_permission("plan.edit", _get_program_from_client)
def section_create(request, client_id):
    """Add a new section to a client's plan."""
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")
    if not _can_edit_plan(request.user, client):
        raise PermissionDenied(_("You don't have permission to access this page."))

    if request.method == "POST":
        form = PlanSectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.client_file = client
            section.save()
            messages.success(request, _("Section added."))
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
@requires_permission("plan.edit", _get_program_from_section)
def section_edit(request, section_id):
    """HTMX inline edit — GET returns edit form partial, POST saves and returns section partial."""
    section = get_object_or_404(PlanSection, pk=section_id)
    if not _can_edit_plan(request.user, section.client_file):
        raise PermissionDenied(_("You don't have permission to access this page."))

    if request.method == "POST":
        form = PlanSectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, _("Section updated."))
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
@requires_permission("plan.edit", _get_program_from_section)
def section_status(request, section_id):
    """HTMX dialog to change section status with reason."""
    section = get_object_or_404(PlanSection, pk=section_id)
    if not _can_edit_plan(request.user, section.client_file):
        raise PermissionDenied(_("You don't have permission to access this page."))

    if request.method == "POST":
        form = PlanSectionStatusForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, _("Section status updated."))
            return render(request, "plans/_section.html", {
                "section": section,
                "can_edit": True,
            })
    else:
        form = PlanSectionStatusForm(instance=section)

    active_target_count = section.targets.filter(status="default").count()
    return render(request, "plans/_section_status.html", {
        "section": section,
        "form": form,
        "active_target_count": active_target_count,
    })


# ---------------------------------------------------------------------------
# Target CRUD
# ---------------------------------------------------------------------------

@login_required
@requires_permission("plan.edit", _get_program_from_section)
def target_create(request, section_id):
    """Add a new target to a section."""
    section = get_object_or_404(PlanSection, pk=section_id)
    if not _can_edit_plan(request.user, section.client_file):
        raise PermissionDenied(_("You don't have permission to access this page."))

    if request.method == "POST":
        form = PlanTargetForm(request.POST)
        if form.is_valid():
            target = PlanTarget(
                plan_section=section,
                client_file=section.client_file,
            )
            target.name = form.cleaned_data["name"]
            target.description = form.cleaned_data.get("description", "")
            target.client_goal = form.cleaned_data.get("client_goal", "")
            target.save()
            # Create initial revision
            PlanTargetRevision.objects.create(
                plan_target=target,
                name=target.name,
                description=target.description,
                client_goal=target.client_goal,
                status=target.status,
                status_reason=target.status_reason,
                changed_by=request.user,
            )
            messages.success(request, _("Target added."))
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
@requires_permission("plan.edit", _get_program_from_target)
def target_edit(request, target_id):
    """Edit a target. Creates a revision with OLD values before saving."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    if not _can_edit_plan(request.user, target.client_file):
        raise PermissionDenied(_("You don't have permission to access this page."))

    if request.method == "POST":
        form = PlanTargetForm(request.POST)
        if form.is_valid():
            # Save old values as a revision BEFORE overwriting
            PlanTargetRevision.objects.create(
                plan_target=target,
                name=target.name,
                description=target.description,
                client_goal=target.client_goal,
                status=target.status,
                status_reason=target.status_reason,
                changed_by=request.user,
            )
            target.name = form.cleaned_data["name"]
            target.description = form.cleaned_data.get("description", "")
            target.client_goal = form.cleaned_data.get("client_goal", "")
            target.save()
            messages.success(request, _("Target updated."))
            return redirect("plans:plan_view", client_id=target.client_file.pk)
    else:
        form = PlanTargetForm(initial={
            "name": target.name,
            "description": target.description,
            "client_goal": target.client_goal,
        })

    return render(request, "plans/target_form.html", {
        "form": form,
        "target": target,
        "section": target.plan_section,
        "client": target.client_file,
        "editing": True,
    })


@login_required
@requires_permission("plan.edit", _get_program_from_target)
def target_status(request, target_id):
    """HTMX dialog to change target status with reason. Creates a revision."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    if not _can_edit_plan(request.user, target.client_file):
        raise PermissionDenied(_("You don't have permission to access this page."))

    if request.method == "POST":
        form = PlanTargetStatusForm(request.POST)
        if form.is_valid():
            # Revision with old values BEFORE overwriting
            PlanTargetRevision.objects.create(
                plan_target=target,
                name=target.name,
                description=target.description,
                client_goal=target.client_goal,
                status=target.status,
                status_reason=target.status_reason,
                changed_by=request.user,
            )
            target.status = form.cleaned_data["status"]
            target.status_reason = form.cleaned_data.get("status_reason", "")
            target.save()
            messages.success(request, _("Target status updated."))
            return render(request, "plans/_target.html", {
                "target": target,
                "can_edit": True,
            })
    else:
        form = PlanTargetStatusForm(initial={
            "status": target.status,
            "status_reason": target.status_reason,
        })

    return render(request, "plans/_target_status.html", {
        "target": target,
        "form": form,
    })


# ---------------------------------------------------------------------------
# Combined goal creation — shared helper + view + autocomplete
# ---------------------------------------------------------------------------


def _create_goal(*, client_file, user, name, description="", client_goal="",
                 section=None, new_section_name="", program=None, metric_ids=None):
    """Atomically create section (if new) + target + revision + metric assignments.

    Called by both goal_create view and goal_builder_save in ai_views.py.
    Returns the created PlanTarget.
    """
    with transaction.atomic():
        # 1. Determine or create section
        if section is None and new_section_name:
            section = PlanSection.objects.create(
                client_file=client_file,
                name=new_section_name,
                program=program,
            )

        if section is None:
            raise ValueError("A section or new_section_name is required.")

        # 2. Create PlanTarget with encrypted fields
        target = PlanTarget(
            plan_section=section,
            client_file=client_file,
        )
        target.name = name
        target.description = description
        target.client_goal = client_goal
        target.save()

        # 3. Create initial revision
        PlanTargetRevision.objects.create(
            plan_target=target,
            name=target.name,
            description=target.description,
            client_goal=target.client_goal,
            status=target.status,
            status_reason=target.status_reason,
            changed_by=user,
        )

        # 4. Assign metrics
        if metric_ids:
            for i, mid in enumerate(metric_ids):
                PlanTargetMetric.objects.create(
                    plan_target=target,
                    metric_def_id=mid,
                    sort_order=i,
                )

    return target


@login_required
@requires_permission("plan.edit", _get_program_from_client)
def goal_create(request, client_id):
    """Combined goal creation — section + target + metrics in one page."""
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")
    if not _can_edit_plan(request.user, client):
        raise PermissionDenied(_("You don't have permission to access this page."))

    participant_name = client.display_name if hasattr(client, "display_name") else ""

    # Pre-selected section from query param (validate as integer)
    preselected_section = None
    try:
        preselected_section_id = int(request.GET.get("section", ""))
    except (ValueError, TypeError):
        preselected_section_id = None
    if preselected_section_id:
        preselected_section = PlanSection.objects.filter(
            pk=preselected_section_id, client_file=client, status="default",
        ).first()

    # Get program from enrolment (for new section creation)
    enrolment = (
        ClientProgramEnrolment.objects.filter(client_file=client, status="enrolled")
        .select_related("program")
        .first()
    )
    program = enrolment.program if enrolment else None

    if request.method == "POST":
        form = GoalForm(request.POST, client_file=client,
                        participant_name=participant_name)
        if form.is_valid():
            cleaned = form.cleaned_data
            section_choice = cleaned["section_choice"]

            # Resolve section
            section = None
            if section_choice != "new":
                section = PlanSection.objects.filter(
                    pk=int(section_choice), client_file=client,
                ).first()

            try:
                _create_goal(
                    client_file=client,
                    user=request.user,
                    name=cleaned["name"],
                    description=cleaned.get("description", ""),
                    client_goal=cleaned.get("client_goal", ""),
                    section=section,
                    new_section_name=cleaned.get("new_section_name", "").strip(),
                    program=program,
                    metric_ids=[m.pk for m in cleaned.get("metrics", [])],
                )
                messages.success(request, _("Goal added."))
                return redirect("plans:plan_view", client_id=client.pk)
            except ValueError as e:
                form.add_error(None, str(e))
    else:
        initial = {}
        if preselected_section:
            initial["section_choice"] = str(preselected_section.pk)
        form = GoalForm(initial=initial, client_file=client,
                        participant_name=participant_name)

    # --- Build metric context for 3-tier display ---
    # Tier 1: Universal metrics
    universal_metrics = list(
        MetricDefinition.objects.filter(
            is_universal=True, is_enabled=True, status="active",
        )
    )

    # Tier 2: Metrics already used in this program (excluding universal)
    program_used_metrics = []
    if program:
        universal_ids = {m.pk for m in universal_metrics}
        program_used_qs = (
            MetricDefinition.objects.filter(
                is_enabled=True, status="active",
                plantargetmetric__plan_target__client_file__enrolments__program=program,
            )
            .exclude(pk__in=universal_ids)
            .distinct()
        )
        # Count usage per metric
        program_used_qs = program_used_qs.annotate(
            usage_count=Count("plantargetmetric")
        ).order_by("-usage_count")
        program_used_metrics = list(program_used_qs)

    # Tier 3: Full library grouped by category (excluding universal + program-used)
    exclude_ids = {m.pk for m in universal_metrics} | {m.pk for m in program_used_metrics}
    all_metrics = MetricDefinition.objects.filter(
        is_enabled=True, status="active",
    ).exclude(pk__in=exclude_ids).order_by("category", "name")
    metrics_by_category = {}
    for metric in all_metrics:
        cat = metric.get_category_display()
        metrics_by_category.setdefault(cat, []).append(metric)

    # --- Common goal cards (top 5-8 most common goals in program) ---
    common_goals = []
    if program:
        targets_in_program = PlanTarget.objects.filter(
            client_file__enrolments__program=program,
        ).select_related().prefetch_related("metrics")
        # Decrypt and count names (encrypted fields require Python-side processing)
        name_counts = {}
        name_metric = {}
        for t in targets_in_program:
            tname = t.name
            if not tname:
                continue
            name_lower = tname.lower().strip()
            name_counts[name_lower] = name_counts.get(name_lower, 0) + 1
            # Track display name (keep first capitalisation seen)
            if name_lower not in name_metric:
                # Get first metric for this target
                first_metric = t.metrics.first()
                name_metric[name_lower] = {
                    "display_name": tname,
                    "metric_name": first_metric.translated_name if first_metric else "",
                    "metric_id": first_metric.pk if first_metric else None,
                }
        # Sort by count descending, take top 8
        sorted_goals = sorted(name_counts.items(), key=lambda x: x[1], reverse=True)
        for name_lower, count in sorted_goals[:8]:
            info = name_metric[name_lower]
            common_goals.append({
                "name": info["display_name"],
                "metric_name": info["metric_name"],
                "metric_id": info["metric_id"],
                "count": count,
            })

    # Build a set of integer PKs for selected metrics so the template can
    # check checkbox state without type-mismatch (POST values are strings).
    selected_metric_ids = set()
    for raw in request.POST.getlist("metrics"):
        try:
            selected_metric_ids.add(int(raw))
        except (ValueError, TypeError):
            pass

    # Check if AI Goal Builder is available
    from konote.ai_views import _ai_enabled
    ai_enabled = _can_edit_plan(request.user, client) and _ai_enabled()

    context = {
        "form": form,
        "client": client,
        "preselected_section": preselected_section,
        "universal_metrics": universal_metrics,
        "program_used_metrics": program_used_metrics,
        "metrics_by_category": metrics_by_category,
        "common_goals": common_goals,
        "selected_metric_ids": selected_metric_ids,
        "ai_enabled": ai_enabled,
    }
    return render(request, "plans/goal_form.html", context)


@login_required
@requires_permission("plan.view", _get_program_from_client)
def goal_name_suggestions(request, client_id):
    """HTMX endpoint: return goal name suggestions for autocomplete.

    Returns all deduplicated target names in the client's programs with usage
    counts. One server call; subsequent filtering happens client-side in JS.
    """
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden()

    active_ids = getattr(request, "active_program_ids", None)
    user_program_ids = get_user_program_ids(request.user, active_ids)

    # Load all targets in user's programs, decrypt names, deduplicate
    targets = PlanTarget.objects.filter(
        client_file__enrolments__program_id__in=user_program_ids,
    ).prefetch_related("metrics")

    name_data = {}
    for t in targets:
        tname = t.name
        if not tname:
            continue
        name_lower = tname.lower().strip()
        if name_lower not in name_data:
            first_metric = t.metrics.first()
            name_data[name_lower] = {
                "name": tname,
                "count": 0,
                "metric_id": first_metric.pk if first_metric else None,
            }
        name_data[name_lower]["count"] += 1

    # Sort by count descending
    suggestions = sorted(name_data.values(), key=lambda x: x["count"], reverse=True)

    return render(request, "plans/_goal_suggestions.html", {
        "suggestions": suggestions,
    })


# ---------------------------------------------------------------------------
# Metric assignment (PLAN3)
# ---------------------------------------------------------------------------

@login_required
@requires_permission("plan.edit", _get_program_from_target)
def target_metrics(request, target_id):
    """Assign metrics to a target — checkboxes grouped by category."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    if not _can_edit_plan(request.user, target.client_file):
        raise PermissionDenied(_("You don't have permission to access this page."))

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
            messages.success(request, _("Metrics updated."))
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
# Metric library (admin + PM) — PLAN3
# ---------------------------------------------------------------------------


def _get_pm_program_ids_for_metrics(user):
    """Return set of program IDs where the user is an active PM."""
    return set(
        UserProgramRole.objects.filter(
            user=user, role="program_manager", status="active",
        ).values_list("program_id", flat=True)
    )


def _can_edit_metric(user, metric):
    """Check if the user can edit a metric definition."""
    if user.is_admin:
        return True
    if metric.owning_program_id is None:
        return False  # Global/library metrics are admin-only
    return metric.owning_program_id in _get_pm_program_ids_for_metrics(user)


@login_required
@requires_permission("metric.manage", allow_admin=True)
def metric_library(request):
    """List all metric definitions by category."""
    if request.user.is_admin:
        metrics = MetricDefinition.objects.all()
    else:
        pm_program_ids = _get_pm_program_ids_for_metrics(request.user)
        metrics = MetricDefinition.objects.filter(
            Q(owning_program_id__in=pm_program_ids) | Q(owning_program__isnull=True)
        )
    metrics_by_category = {}
    for metric in metrics:
        cat = metric.get_category_display()
        metrics_by_category.setdefault(cat, []).append(metric)

    return render(request, "plans/metric_library.html", {
        "metrics_by_category": metrics_by_category,
        "is_admin": request.user.is_admin,
    })


@login_required
@admin_required
def metric_export(request):
    """Admin-only CSV export of all metric definitions for review/editing."""
    from apps.reports.csv_utils import sanitise_csv_row

    metrics = MetricDefinition.objects.all()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="metric_definitions.csv"'
    # UTF-8 BOM so Excel opens the file correctly
    response.write("\ufeff")

    writer = csv.writer(response)
    writer.writerow(["id", "name", "name_fr", "definition", "definition_fr",
                     "category", "min_value", "max_value", "unit", "unit_fr",
                     "portal_description", "portal_description_fr",
                     "is_enabled", "status"])

    for m in metrics:
        writer.writerow(sanitise_csv_row([
            m.pk,
            m.name,
            m.name_fr,
            m.definition,
            m.definition_fr,
            m.category,
            m.min_value if m.min_value is not None else "",
            m.max_value if m.max_value is not None else "",
            m.unit,
            m.unit_fr,
            m.portal_description,
            m.portal_description_fr,
            "yes" if m.is_enabled else "no",
            m.status,
        ]))

    # Audit log
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=getattr(request.user, "display_name", str(request.user)),
        action="export",
        resource_type="MetricDefinition",
        ip_address=request.META.get("REMOTE_ADDR", ""),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={"detail": f"Exported {metrics.count()} metric definitions to CSV"},
    )

    return response


@login_required
@requires_permission("metric.manage", allow_admin=True)
def metric_toggle(request, metric_id):
    """HTMX POST to toggle is_enabled on a metric definition."""
    metric = get_object_or_404(MetricDefinition, pk=metric_id)

    if not _can_edit_metric(request.user, metric):
        return HttpResponseForbidden(_("Access denied. You can only manage metrics in your programs."))

    if request.method == "POST":
        metric.is_enabled = not metric.is_enabled
        metric.save()
    # Return just the toggle button fragment
    return render(request, "plans/_metric_toggle.html", {"metric": metric})


@login_required
@requires_permission("metric.manage", allow_admin=True)
def metric_create(request):
    """Create a custom metric definition."""
    if request.method == "POST":
        form = MetricDefinitionForm(request.POST, requesting_user=request.user)
        if form.is_valid():
            metric = form.save(commit=False)
            metric.is_library = False
            # Auto-assign program for single-program PMs
            if not request.user.is_admin and metric.owning_program_id is None:
                pm_program_ids = _get_pm_program_ids_for_metrics(request.user)
                if len(pm_program_ids) == 1:
                    metric.owning_program_id = next(iter(pm_program_ids))
            metric.save()
            messages.success(request, _("Metric created."))
            return redirect("metrics:metric_library")
    else:
        form = MetricDefinitionForm(requesting_user=request.user)

    return render(request, "plans/metric_form.html", {
        "form": form,
        "editing": False,
    })


@login_required
@requires_permission("metric.manage", allow_admin=True)
def metric_edit(request, metric_id):
    """Edit a metric definition."""
    metric = get_object_or_404(MetricDefinition, pk=metric_id)

    if not _can_edit_metric(request.user, metric):
        return HttpResponseForbidden(_("Access denied. You can only edit metrics in your programs."))

    if request.method == "POST":
        form = MetricDefinitionForm(request.POST, instance=metric, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Metric updated."))
            return redirect("metrics:metric_library")
    else:
        form = MetricDefinitionForm(instance=metric, requesting_user=request.user)

    return render(request, "plans/metric_form.html", {
        "form": form,
        "editing": True,
        "metric": metric,
    })


# ---------------------------------------------------------------------------
# Revision history (PLAN6)
# ---------------------------------------------------------------------------

@login_required
@requires_permission("plan.view", _get_program_from_target)
def target_history(request, target_id):
    """Show revision history for a target."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    client = get_client_or_403(request, target.client_file_id)
    if client is None:
        return HttpResponseForbidden(_("You do not have access to this participant."))
    revisions = PlanTargetRevision.objects.filter(plan_target=target).select_related("changed_by")

    return render(request, "plans/target_history.html", {
        "target": target,
        "client": client,
        "revisions": revisions,
    })


# ---------------------------------------------------------------------------
# Metric CSV import (admin)
# ---------------------------------------------------------------------------

VALID_CATEGORIES = dict(MetricDefinition.CATEGORY_CHOICES)


def _parse_metric_csv(csv_file):
    """
    Parse a CSV file and return (rows, errors).
    rows: list of dicts with metric data (includes 'id' for updates)
    errors: list of error strings

    If the CSV has an 'id' column, rows with a valid id will be matched
    to existing metrics for updating. Rows without an id are treated as new.
    """
    rows = []
    errors = []

    try:
        # Read and decode the file
        content = csv_file.read().decode("utf-8-sig")  # utf-8-sig handles BOM from Excel
        reader = csv.DictReader(io.StringIO(content))

        # Validate headers
        required_headers = {"name", "definition", "category"}
        if reader.fieldnames is None:
            errors.append("CSV file is empty or has no headers.")
            return rows, errors

        headers = set(h.strip().lower() for h in reader.fieldnames)
        missing = required_headers - headers
        if missing:
            errors.append(f"Missing required columns: {', '.join(sorted(missing))}")
            return rows, errors

        has_id_column = "id" in headers
        has_enabled_column = "is_enabled" in headers
        has_status_column = "status" in headers

        # Pre-fetch existing metric ids for validation
        existing_ids = set()
        if has_id_column:
            existing_ids = set(MetricDefinition.objects.values_list("pk", flat=True))

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is headers)
            # Normalize keys to lowercase
            row = {k.strip().lower(): v.strip() if v else "" for k, v in row.items()}

            row_errors = []

            # Optional id for update-or-create
            raw_id = row.get("id", "")
            metric_id = None
            action = "new"
            if has_id_column and raw_id:
                try:
                    metric_id = int(raw_id)
                    if metric_id not in existing_ids:
                        row_errors.append(f"id {metric_id} does not match any existing metric")
                        metric_id = None
                    else:
                        action = "update"
                except ValueError:
                    row_errors.append(f"id '{raw_id}' is not a valid number")

            # Required fields
            name = row.get("name", "")
            definition = row.get("definition", "")
            category = row.get("category", "")

            if not name:
                row_errors.append("name is required")
            if not definition:
                row_errors.append("definition is required")
            if not category:
                row_errors.append("category is required")
            elif category not in VALID_CATEGORIES:
                row_errors.append(f"invalid category '{category}' (valid: {', '.join(VALID_CATEGORIES.keys())})")

            # Optional French translation fields
            name_fr = row.get("name_fr", "")
            definition_fr = row.get("definition_fr", "")
            unit_fr = row.get("unit_fr", "")
            portal_description_fr = row.get("portal_description_fr", "")

            # Optional numeric fields
            min_value = row.get("min_value", "")
            max_value = row.get("max_value", "")
            unit = row.get("unit", "")

            parsed_min = None
            parsed_max = None

            if min_value:
                try:
                    parsed_min = float(min_value)
                except ValueError:
                    row_errors.append(f"min_value '{min_value}' is not a number")

            if max_value:
                try:
                    parsed_max = float(max_value)
                except ValueError:
                    row_errors.append(f"max_value '{max_value}' is not a number")

            # Validate min <= max if both provided
            if parsed_min is not None and parsed_max is not None and parsed_min > parsed_max:
                row_errors.append(f"min_value ({parsed_min}) cannot be greater than max_value ({parsed_max})")

            # is_enabled (optional — defaults to True for new, unchanged for updates)
            is_enabled = True
            if has_enabled_column:
                raw_enabled = row.get("is_enabled", "").lower()
                if raw_enabled in ("yes", "true", "1"):
                    is_enabled = True
                elif raw_enabled in ("no", "false", "0"):
                    is_enabled = False
                elif raw_enabled:
                    row_errors.append(f"is_enabled '{row.get('is_enabled', '')}' must be yes/no")

            # status (optional — defaults to 'active' for new)
            status = "active"
            if has_status_column:
                raw_status = row.get("status", "").lower()
                if raw_status in ("active", "deactivated"):
                    status = raw_status
                elif raw_status:
                    row_errors.append(f"status '{row.get('status', '')}' must be active/deactivated")

            if row_errors:
                errors.append(f"Row {row_num}: {'; '.join(row_errors)}")
            else:
                rows.append({
                    "id": metric_id,
                    "action": action,
                    "name": name,
                    "name_fr": name_fr,
                    "definition": definition,
                    "definition_fr": definition_fr,
                    "category": category,
                    "min_value": parsed_min,
                    "max_value": parsed_max,
                    "unit": unit,
                    "unit_fr": unit_fr,
                    "portal_description_fr": portal_description_fr,
                    "is_enabled": is_enabled,
                    "status": status,
                })

    except UnicodeDecodeError:
        errors.append("File encoding error. Please save the CSV as UTF-8.")
    except csv.Error as e:
        errors.append(f"CSV parsing error: {e}")

    return rows, errors


@login_required
@admin_required
def metric_import(request):
    """
    Admin page to import metric definitions from CSV.
    GET: Show upload form
    POST without confirm: Parse CSV and show preview
    POST with confirm: Import the metrics
    """
    preview_rows = []
    parse_errors = []
    form = MetricImportForm()

    if request.method == "POST":
        # Check if this is the confirmation step
        if "confirm_import" in request.POST:
            # Retrieve cached data from session
            cached_rows = request.session.pop("metric_import_rows", None)
            if not cached_rows:
                messages.error(request, _("Import session expired. Please upload the file again."))
                return redirect("metrics:metric_import")

            # Create or update the metrics
            created_count = 0
            updated_count = 0
            for row_data in cached_rows:
                fields = {
                    "name": row_data["name"],
                    "name_fr": row_data.get("name_fr", ""),
                    "definition": row_data["definition"],
                    "definition_fr": row_data.get("definition_fr", ""),
                    "category": row_data["category"],
                    "min_value": row_data["min_value"],
                    "max_value": row_data["max_value"],
                    "unit": row_data["unit"],
                    "unit_fr": row_data.get("unit_fr", ""),
                    "portal_description_fr": row_data.get("portal_description_fr", ""),
                    "is_enabled": row_data.get("is_enabled", True),
                    "status": row_data.get("status", "active"),
                }

                if row_data.get("id"):
                    # Update existing metric
                    MetricDefinition.objects.filter(pk=row_data["id"]).update(**fields)
                    updated_count += 1
                else:
                    # Create new metric
                    MetricDefinition.objects.create(is_library=False, **fields)
                    created_count += 1

            # Audit log
            parts = []
            if created_count:
                parts.append(f"created {created_count}")
            if updated_count:
                parts.append(f"updated {updated_count}")
            detail = f"CSV import: {', '.join(parts)} metric definitions"

            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=getattr(request.user, "display_name", str(request.user)),
                action="import",
                resource_type="MetricDefinition",
                ip_address=request.META.get("REMOTE_ADDR", ""),
                is_demo_context=getattr(request.user, "is_demo", False),
                metadata={"detail": detail},
            )

            # Build success message
            msg_parts = []
            if created_count:
                msg_parts.append(_("%(count)d new") % {"count": created_count})
            if updated_count:
                msg_parts.append(_("%(count)d updated") % {"count": updated_count})
            messages.success(request, _("Import complete: %s.") % ", ".join(msg_parts))
            return redirect("metrics:metric_library")

        # This is the upload step - parse the CSV
        form = MetricImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            preview_rows, parse_errors = _parse_metric_csv(csv_file)

            if not parse_errors and preview_rows:
                # Cache the parsed data in session for confirmation
                request.session["metric_import_rows"] = preview_rows

    update_count = sum(1 for r in preview_rows if r.get("action") == "update")
    new_count = len(preview_rows) - update_count

    return render(request, "plans/metric_import.html", {
        "form": form,
        "preview_rows": preview_rows,
        "parse_errors": parse_errors,
        "category_choices": VALID_CATEGORIES,
        "update_count": update_count,
        "new_count": new_count,
    })
