"""Phase 3: Plan editing views — sections, targets, metrics, revisions."""
import csv
import io
from collections import OrderedDict

from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.audit.models import AuditLog
from apps.auth_app.constants import ROLE_RANK
from apps.auth_app.decorators import admin_required, programme_role_required, requires_permission
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.access import (
    build_program_display_context,
    get_client_or_403,
    get_user_program_ids,
)
from apps.programs.models import Program, UserProgramRole

from .forms import (
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


def _get_programme_from_client(request, client_id, **kwargs):
    """Find the shared programme where user has the highest role.

    Used by programme_role_required decorator. Picks the most permissive
    valid programme so the user isn't arbitrarily denied.
    """
    client = get_object_or_404(ClientFile, pk=client_id)

    user_roles = UserProgramRole.objects.filter(
        user=request.user, status="active"
    ).values_list("program_id", "role")

    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client, status="enrolled"
        ).values_list("program_id", flat=True)
    )

    best_program_id = None
    best_rank = -1
    for program_id, role in user_roles:
        if program_id in client_program_ids:
            rank = ROLE_RANK.get(role, 0)
            if rank > best_rank:
                best_rank = rank
                best_program_id = program_id

    if best_program_id is None:
        raise ValueError(f"User has no shared programme with client {client_id}")

    return Program.objects.get(pk=best_program_id)


def _get_programme_from_section(request, section_id, **kwargs):
    """Extract programme via section → client."""
    section = get_object_or_404(PlanSection, pk=section_id)
    return _get_programme_from_client(request, section.client_file_id)


def _get_programme_from_target(request, target_id, **kwargs):
    """Extract programme via target → client."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    return _get_programme_from_client(request, target.client_file_id)


def _can_edit_plan(user, client_file):
    """Return True if the user may modify this client's plan.

    Programme managers can edit plan structure (sections, targets, metrics).
    Staff and front desk cannot edit plans.

    Note: admin status does NOT bypass programme role checks (PERM-S2).
    Admins need a programme manager role to edit plans.
    """
    enrolled_program_ids = ClientProgramEnrolment.objects.filter(
        client_file=client_file, status="enrolled"
    ).values_list("program_id", flat=True)
    return UserProgramRole.objects.filter(
        user=user,
        program_id__in=enrolled_program_ids,
        role="program_manager",
        status="active",
    ).exists()



# ---------------------------------------------------------------------------
# Plan tab view
# ---------------------------------------------------------------------------

@login_required
@requires_permission("plan.view", _get_programme_from_client)
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

    context = {
        "client": client,
        "active_sections": active_sections,
        "inactive_sections": inactive_sections,
        "can_edit": can_edit,
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
@requires_permission("plan.edit", _get_programme_from_client)
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
@requires_permission("plan.edit", _get_programme_from_section)
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
@requires_permission("plan.edit", _get_programme_from_section)
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

    return render(request, "plans/_section_status.html", {
        "section": section,
        "form": form,
    })


# ---------------------------------------------------------------------------
# Target CRUD
# ---------------------------------------------------------------------------

@login_required
@requires_permission("plan.edit", _get_programme_from_section)
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
@requires_permission("plan.edit", _get_programme_from_target)
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
@requires_permission("plan.edit", _get_programme_from_target)
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
# Metric assignment (PLAN3)
# ---------------------------------------------------------------------------

@login_required
@requires_permission("plan.edit", _get_programme_from_target)
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
# Metric library (admin) — PLAN3
# ---------------------------------------------------------------------------

@login_required
@admin_required
def metric_library(request):
    """Admin-only page listing all metric definitions by category."""
    metrics = MetricDefinition.objects.all()
    metrics_by_category = {}
    for metric in metrics:
        cat = metric.get_category_display()
        metrics_by_category.setdefault(cat, []).append(metric)

    return render(request, "plans/metric_library.html", {
        "metrics_by_category": metrics_by_category,
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
    writer.writerow(["id", "name", "definition", "category", "min_value",
                     "max_value", "unit", "is_enabled", "status"])

    for m in metrics:
        writer.writerow(sanitise_csv_row([
            m.pk,
            m.name,
            m.definition,
            m.category,
            m.min_value if m.min_value is not None else "",
            m.max_value if m.max_value is not None else "",
            m.unit,
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
@admin_required
def metric_toggle(request, metric_id):
    """HTMX POST to toggle is_enabled on a metric definition."""
    metric = get_object_or_404(MetricDefinition, pk=metric_id)
    if request.method == "POST":
        metric.is_enabled = not metric.is_enabled
        metric.save()
    # Return just the toggle button fragment
    return render(request, "plans/_metric_toggle.html", {"metric": metric})


@login_required
@admin_required
def metric_create(request):
    """Admin form to create a custom metric definition."""
    if request.method == "POST":
        form = MetricDefinitionForm(request.POST)
        if form.is_valid():
            metric = form.save(commit=False)
            metric.is_library = False
            metric.save()
            messages.success(request, _("Metric created."))
            return redirect("plans:metric_library")
    else:
        form = MetricDefinitionForm()

    return render(request, "plans/metric_form.html", {
        "form": form,
        "editing": False,
    })


@login_required
@admin_required
def metric_edit(request, metric_id):
    """Admin form to edit a metric definition."""
    metric = get_object_or_404(MetricDefinition, pk=metric_id)
    if request.method == "POST":
        form = MetricDefinitionForm(request.POST, instance=metric)
        if form.is_valid():
            form.save()
            messages.success(request, _("Metric updated."))
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
@requires_permission("plan.view", _get_programme_from_target)
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
                    "definition": definition,
                    "category": category,
                    "min_value": parsed_min,
                    "max_value": parsed_max,
                    "unit": unit,
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
                return redirect("plans:metric_import")

            # Create or update the metrics
            created_count = 0
            updated_count = 0
            for row_data in cached_rows:
                fields = {
                    "name": row_data["name"],
                    "definition": row_data["definition"],
                    "category": row_data["category"],
                    "min_value": row_data["min_value"],
                    "max_value": row_data["max_value"],
                    "unit": row_data["unit"],
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
            return redirect("plans:metric_library")

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
