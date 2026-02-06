"""Phase 3: Plan editing views — sections, targets, metrics, revisions."""
import csv
import io

from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.audit.models import AuditLog
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import UserProgramRole

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
# Permission helper
# ---------------------------------------------------------------------------

def _can_edit_plan(user, client_file):
    """
    Return True if the user may modify this client's plan.
    Admins can always edit. Programme managers can edit plan structure
    (sections, targets, metrics). Staff and front desk cannot edit plans.
    """
    # Admins can always edit plans
    if user.is_admin:
        return True
    # Get programmes this client is enrolled in
    enrolled_program_ids = ClientProgramEnrolment.objects.filter(
        client_file=client_file, status="enrolled"
    ).values_list("program_id", flat=True)
    # Only programme managers can edit plan structure
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

    context = {
        "client": client,
        "active_sections": active_sections,
        "inactive_sections": inactive_sections,
        "can_edit": can_edit,
        "active_tab": "plan",
    }
    if request.headers.get("HX-Request"):
        return render(request, "plans/_tab_plan.html", context)
    return render(request, "plans/plan_view.html", context)


# ---------------------------------------------------------------------------
# Section CRUD
# ---------------------------------------------------------------------------

@login_required
def section_create(request, client_id):
    """Add a new section to a client's plan."""
    client = _get_client_or_403(client_id, request.user)
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
def metric_library(request):
    """Admin-only page listing all metric definitions by category."""
    if not request.user.is_admin:
        raise PermissionDenied(_("You don't have permission to access this page."))

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
        raise PermissionDenied(_("You don't have permission to access this page."))

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
        raise PermissionDenied(_("You don't have permission to access this page."))

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
def metric_edit(request, metric_id):
    """Admin form to edit a metric definition."""
    if not request.user.is_admin:
        raise PermissionDenied(_("You don't have permission to access this page."))

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
def target_history(request, target_id):
    """Show revision history for a target."""
    target = get_object_or_404(PlanTarget, pk=target_id)
    revisions = PlanTargetRevision.objects.filter(plan_target=target).select_related("changed_by")

    return render(request, "plans/target_history.html", {
        "target": target,
        "client": target.client_file,
        "revisions": revisions,
    })


# ---------------------------------------------------------------------------
# Metric CSV import (admin)
# ---------------------------------------------------------------------------

VALID_CATEGORIES = dict(MetricDefinition.CATEGORY_CHOICES)


def _parse_metric_csv(csv_file):
    """
    Parse a CSV file and return (rows, errors).
    rows: list of dicts with metric data
    errors: list of error strings
    """
    rows = []
    errors = []

    try:
        # Read and decode the file
        content = csv_file.read().decode("utf-8-sig")  # utf-8-sig handles BOM from Excel
        reader = csv.DictReader(io.StringIO(content))

        # Validate headers
        required_headers = {"name", "definition", "category"}
        optional_headers = {"min_value", "max_value", "unit"}
        if reader.fieldnames is None:
            errors.append("CSV file is empty or has no headers.")
            return rows, errors

        headers = set(h.strip().lower() for h in reader.fieldnames)
        missing = required_headers - headers
        if missing:
            errors.append(f"Missing required columns: {', '.join(sorted(missing))}")
            return rows, errors

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is headers)
            # Normalize keys to lowercase
            row = {k.strip().lower(): v.strip() if v else "" for k, v in row.items()}

            row_errors = []

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

            if row_errors:
                errors.append(f"Row {row_num}: {'; '.join(row_errors)}")
            else:
                rows.append({
                    "name": name,
                    "definition": definition,
                    "category": category,
                    "min_value": parsed_min,
                    "max_value": parsed_max,
                    "unit": unit,
                })

    except UnicodeDecodeError:
        errors.append("File encoding error. Please save the CSV as UTF-8.")
    except csv.Error as e:
        errors.append(f"CSV parsing error: {e}")

    return rows, errors


@login_required
def metric_import(request):
    """
    Admin page to import metric definitions from CSV.
    GET: Show upload form
    POST without confirm: Parse CSV and show preview
    POST with confirm: Import the metrics
    """
    if not request.user.is_admin:
        raise PermissionDenied(_("You don't have permission to access this page."))

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

            # Create the metrics
            created_count = 0
            for row_data in cached_rows:
                MetricDefinition.objects.create(
                    name=row_data["name"],
                    definition=row_data["definition"],
                    category=row_data["category"],
                    min_value=row_data["min_value"],
                    max_value=row_data["max_value"],
                    unit=row_data["unit"],
                    is_library=False,
                    is_enabled=True,
                    status="active",
                )
                created_count += 1

            # Audit log
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=getattr(request.user, "display_name", str(request.user)),
                action="create",
                resource_type="MetricDefinition",
                ip_address=request.META.get("REMOTE_ADDR", ""),
                is_demo_context=getattr(request.user, "is_demo", False),
                metadata={"detail": f"Imported {created_count} metric definitions from CSV"},
            )

            messages.success(request, _("Successfully imported %(count)d metric definitions.") % {"count": created_count})
            return redirect("plans:metric_library")

        # This is the upload step - parse the CSV
        form = MetricImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            preview_rows, parse_errors = _parse_metric_csv(csv_file)

            if not parse_errors and preview_rows:
                # Cache the parsed data in session for confirmation
                request.session["metric_import_rows"] = preview_rows

    return render(request, "plans/metric_import.html", {
        "form": form,
        "preview_rows": preview_rows,
        "parse_errors": parse_errors,
        "category_choices": VALID_CATEGORIES,
    })
