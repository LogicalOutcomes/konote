"""Audit log viewer — admin and program manager access."""
import csv
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.auth_app.decorators import admin_required, requires_permission
from apps.reports.csv_utils import sanitise_csv_row

from .models import AuditLog


def _scoped_audit_qs(request):
    """Return an AuditLog queryset scoped to the user's access level.

    Admins see all entries. Program managers see entries scoped to their
    programs (audit.view: PROGRAM in permissions matrix). Non-admin users
    without PM roles are already blocked by the @requires_permission
    decorator, so this function only needs to handle admin vs PM scoping.
    """
    from apps.programs.models import UserProgramRole

    qs = AuditLog.objects.using("audit").all()

    if not getattr(request.user, "is_admin", False):
        # Scope to programs where the user has an active role.
        # request.user_program_role is only set by middleware for
        # client-scoped URLs, so we query program IDs directly
        # (consistent with all other admin views).
        user_program_ids = list(
            UserProgramRole.objects.filter(
                user=request.user, status="active",
            ).values_list("program_id", flat=True)
        )
        qs = qs.filter(program_id__in=user_program_ids)

    return qs


@login_required
@requires_permission("audit.view", allow_admin=True)
def audit_log_list(request):
    """Display paginated, filterable audit log."""

    qs = _scoped_audit_qs(request)

    # Collect filter values
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    user_display = request.GET.get("user_display", "")
    action = request.GET.get("action", "")
    resource_type = request.GET.get("resource_type", "")
    demo_filter = request.GET.get("demo_filter", "")

    # Apply filters
    if demo_filter == "real":
        qs = qs.filter(is_demo_context=False)
    elif demo_filter == "demo":
        qs = qs.filter(is_demo_context=True)

    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            qs = qs.filter(event_timestamp__gte=timezone.make_aware(dt))
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            # Include the entire day
            dt = dt.replace(hour=23, minute=59, second=59)
            qs = qs.filter(event_timestamp__lte=timezone.make_aware(dt))
        except ValueError:
            pass

    if user_display:
        qs = qs.filter(user_display__icontains=user_display)

    if action:
        qs = qs.filter(action=action)

    if resource_type:
        qs = qs.filter(resource_type__icontains=resource_type)

    # Build filter query string for pagination links (exclude 'page')
    filter_params = []
    for key in ("date_from", "date_to", "user_display", "action", "resource_type", "demo_filter"):
        val = request.GET.get(key, "")
        if val:
            filter_params.append(f"{key}={val}")
    filter_query = "&".join(filter_params)

    # Paginate
    paginator = Paginator(qs, 50)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)

    context = {
        "page": page,
        "filter_query": filter_query,
        "action_choices": AuditLog.ACTION_CHOICES,
        # Sticky filter values
        "date_from": date_from,
        "date_to": date_to,
        "user_display": user_display,
        "action_filter": action,
        "resource_type": resource_type,
        "demo_filter": demo_filter,
        "nav_active": "admin",
    }
    return render(request, "audit/log_list.html", context)


@login_required
@requires_permission("audit.view", allow_admin=True)
def audit_log_export(request):
    """Export filtered audit log as CSV."""

    qs = _scoped_audit_qs(request)

    # Apply same filters as list view
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    user_display = request.GET.get("user_display", "")
    action = request.GET.get("action", "")
    resource_type = request.GET.get("resource_type", "")
    demo_filter = request.GET.get("demo_filter", "")

    if demo_filter == "real":
        qs = qs.filter(is_demo_context=False)
    elif demo_filter == "demo":
        qs = qs.filter(is_demo_context=True)

    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            qs = qs.filter(event_timestamp__gte=timezone.make_aware(dt))
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            dt = dt.replace(hour=23, minute=59, second=59)
            qs = qs.filter(event_timestamp__lte=timezone.make_aware(dt))
        except ValueError:
            pass

    if user_display:
        qs = qs.filter(user_display__icontains=user_display)

    if action:
        qs = qs.filter(action=action)

    if resource_type:
        qs = qs.filter(resource_type__icontains=resource_type)

    # Build CSV response
    today = timezone.now().strftime("%Y-%m-%d")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="audit_log_{today}.csv"'

    writer = csv.writer(response)
    writer.writerow(sanitise_csv_row(["Timestamp", "User", "IP Address", "Action", "Resource Type", "Resource ID", "Program ID", "Demo Context"]))

    for entry in qs.iterator():
        writer.writerow(sanitise_csv_row([
            entry.event_timestamp.strftime("%Y-%m-%d %H:%M"),
            entry.user_display,
            entry.ip_address or "",
            entry.action,
            entry.resource_type,
            entry.resource_id or "",
            entry.program_id or "",
            "Yes" if entry.is_demo_context else "No",
        ]))

    # Log the export action
    filters_used = {k: v for k, v in {
        "date_from": date_from, "date_to": date_to,
        "user_display": user_display, "action": action,
        "resource_type": resource_type,
    }.items() if v}

    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=getattr(request.user, "display_name", str(request.user)),
        action="export",
        resource_type="audit_log",
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={"filters": filters_used},
    )

    return response


@login_required
def program_audit_log(request, program_id):
    """Program manager view: audit log for their program's clients.

    Shows all audit entries where the resource is a client enrolled in
    this program. Access limited to program_manager role.
    """
    from apps.clients.models import ClientProgramEnrolment
    from apps.programs.models import Program, UserProgramRole

    program = get_object_or_404(Program, pk=program_id)

    # Check access: user must be program_manager for this program
    role = UserProgramRole.objects.filter(
        user=request.user,
        program=program,
        status="active",
        role="program_manager",
    ).first()

    if not role:
        return HttpResponseForbidden(_("You do not have permission to view audit logs for this program."))

    # Get client IDs enrolled in this program
    client_ids = list(ClientProgramEnrolment.objects.filter(
        program=program, status="active",
    ).values_list("client_file_id", flat=True))

    # Query audit log for entries related to these clients
    qs = AuditLog.objects.using("audit").filter(
        models.Q(program_id=program.pk) |
        models.Q(resource_type="clients", resource_id__in=client_ids)
    )

    # Collect filter values
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    user_display = request.GET.get("user_display", "")
    action = request.GET.get("action", "")

    # Apply filters
    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            qs = qs.filter(event_timestamp__gte=timezone.make_aware(dt))
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            dt = dt.replace(hour=23, minute=59, second=59)
            qs = qs.filter(event_timestamp__lte=timezone.make_aware(dt))
        except ValueError:
            pass

    if user_display:
        qs = qs.filter(user_display__icontains=user_display)

    if action:
        qs = qs.filter(action=action)

    # Build filter query string for pagination
    filter_params = []
    for key in ("date_from", "date_to", "user_display", "action"):
        val = request.GET.get(key, "")
        if val:
            filter_params.append(f"{key}={val}")
    filter_query = "&".join(filter_params)

    # Paginate
    paginator = Paginator(qs, 50)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)

    context = {
        "program": program,
        "page": page,
        "filter_query": filter_query,
        "action_choices": AuditLog.ACTION_CHOICES,
        # Sticky filter values
        "date_from": date_from,
        "date_to": date_to,
        "user_display": user_display,
        "action_filter": action,
        "nav_active": "admin",
    }
    return render(request, "audit/program_audit_log.html", context)


# ---------------------------------------------------------------------------
# Compliance summary — aggregate audit metrics for executives (QA-R8-PERM2)
# ---------------------------------------------------------------------------

@login_required
@requires_permission("compliance.view_summary", allow_admin=True)
def compliance_summary(request):
    """Compliance summary dashboard for executives and admins.

    Shows aggregate audit metrics without individual participant names
    or staff identities.  Designed for board reporting per PIPEDA 4.1.4.

    Three-tier escalation model:
    1. This page: aggregate summary (no PII, no staff names)
    2. Anomaly detail: nature of anomaly + role (not name)
    3. Admin investigation: ED contacts admin for specific log entries
    """
    now = timezone.now()

    # Determine reporting period from query params or default to last 90 days
    date_from_str = request.GET.get("date_from", "")
    date_to_str = request.GET.get("date_to", "")

    if date_from_str:
        try:
            period_start = timezone.make_aware(
                datetime.strptime(date_from_str, "%Y-%m-%d")
            )
        except ValueError:
            period_start = now - timedelta(days=90)
    else:
        period_start = now - timedelta(days=90)

    if date_to_str:
        try:
            period_end = timezone.make_aware(
                datetime.strptime(date_to_str, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59,
                )
            )
        except ValueError:
            period_end = now
    else:
        period_end = now

    # Base queryset — exclude demo activity from compliance metrics
    qs = AuditLog.objects.using("audit").filter(
        event_timestamp__gte=period_start,
        event_timestamp__lte=period_end,
        is_demo_context=False,
    )

    # --- Aggregate metrics ---

    total_events = qs.count()

    # Access events by action type (aggregate counts, no names)
    action_counts = dict(
        qs.values_list("action").annotate(count=Count("id")).order_by("-count")
    )

    # Export events — count by role (from metadata), not by staff name
    export_qs = qs.filter(action="export")
    export_count = export_qs.count()

    # Count exports by role (stored in metadata.user_role)
    export_by_role = {}
    for entry in export_qs.only("metadata").iterator():
        role = "unknown"
        if entry.metadata and isinstance(entry.metadata, dict):
            role = entry.metadata.get("user_role", "unknown")
        export_by_role[role] = export_by_role.get(role, 0) + 1

    # Access denied events — potential security indicator
    access_denied_count = action_counts.get("access_denied", 0)

    # Failed login attempts
    login_failed_count = action_counts.get("login_failed", 0)

    # Record types accessed (aggregate — which types of data are being used)
    resource_type_counts = dict(
        qs.exclude(
            action__in=["login", "logout", "login_failed"],
        ).values_list("resource_type").annotate(
            count=Count("id"),
        ).order_by("-count")[:10]
    )

    # Translate resource type keys to display labels
    resource_type_display = {}
    for rt, count in resource_type_counts.items():
        label = AuditLog.RESOURCE_TYPE_LABELS.get(
            rt, rt.replace("_", " ").title()
        )
        resource_type_display[str(label)] = count

    # Active user count (distinct users with activity, no names)
    active_user_count = (
        qs.exclude(user_id__isnull=True)
        .values("user_id")
        .distinct()
        .count()
    )

    # --- Anomaly detection (role-level, no staff names) ---
    anomalies = []

    # Anomaly: bulk record access (>50 participant views in a single day by one user role)
    from django.db.models.functions import TruncDate
    bulk_access = (
        qs.filter(action="view", resource_type="clients")
        .annotate(day=TruncDate("event_timestamp"))
        .values("day", "metadata__user_role")
        .annotate(count=Count("id"))
        .filter(count__gt=50)
        .order_by("-day")[:5]
    )
    # Note: metadata__user_role lookup may not work with JSONField on all
    # backends; fall back to Python-side grouping if needed.
    # For now, do a simpler per-day aggregate.
    bulk_daily = (
        qs.filter(action="view", resource_type="clients")
        .annotate(day=TruncDate("event_timestamp"))
        .values("day")
        .annotate(count=Count("id"))
        .filter(count__gt=50)
        .order_by("-day")[:5]
    )
    for entry in bulk_daily:
        anomalies.append({
            "type": _("Bulk record access"),
            "detail": _("%(count)s participant records viewed on %(date)s")
            % {"count": entry["count"], "date": entry["day"].strftime("%Y-%m-%d")},
        })

    # Anomaly: access denied spikes (>5 in a day)
    denied_daily = (
        qs.filter(action="access_denied")
        .annotate(day=TruncDate("event_timestamp"))
        .values("day")
        .annotate(count=Count("id"))
        .filter(count__gt=5)
        .order_by("-day")[:5]
    )
    for entry in denied_daily:
        anomalies.append({
            "type": _("Access denied spike"),
            "detail": _("%(count)s access denied events on %(date)s")
            % {"count": entry["count"], "date": entry["day"].strftime("%Y-%m-%d")},
        })

    # Anomaly: failed login spikes (>10 in a day)
    failed_login_daily = (
        qs.filter(action="login_failed")
        .annotate(day=TruncDate("event_timestamp"))
        .values("day")
        .annotate(count=Count("id"))
        .filter(count__gt=10)
        .order_by("-day")[:5]
    )
    for entry in failed_login_daily:
        anomalies.append({
            "type": _("Failed login spike"),
            "detail": _("%(count)s failed login attempts on %(date)s")
            % {"count": entry["count"], "date": entry["day"].strftime("%Y-%m-%d")},
        })

    context = {
        "period_start": period_start,
        "period_end": period_end,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "total_events": total_events,
        "action_counts": action_counts,
        "export_count": export_count,
        "export_by_role": export_by_role,
        "access_denied_count": access_denied_count,
        "login_failed_count": login_failed_count,
        "resource_type_display": resource_type_display,
        "active_user_count": active_user_count,
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "nav_active": "compliance",
    }
    return render(request, "audit/compliance_summary.html", context)
