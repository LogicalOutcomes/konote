"""PDF export views for client progress reports, program outcome reports, board summaries, and individual client data export."""
import csv
import io
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.admin_settings.models import InstanceSetting
from apps.audit.models import AuditLog
from apps.auth_app.decorators import admin_required, minimum_role, requires_permission
from apps.clients.models import ClientDetailValue, ClientProgramEnrolment
from apps.events.models import Event
from apps.notes.models import MetricValue, ProgressNote, SuggestionTheme, THEME_PRIORITY_RANK
from apps.plans.models import PlanSection, PlanTarget, PlanTargetMetric
from apps.programs.models import Program

from .csv_utils import sanitise_csv_row, sanitise_filename
from .forms import IndividualClientExportForm
from .insights import get_structured_insights, collect_quotes, MIN_PARTICIPANTS_FOR_QUOTES
from .metric_insights import get_achievement_rates, get_metric_trends, get_data_completeness
from .pdf_utils import (
    audit_pdf_export,
    get_pdf_unavailable_reason,
    is_pdf_available,
    render_pdf,
)
from .suppression import SMALL_CELL_THRESHOLD
from .views import _get_client_ip, _get_client_or_403

logger = logging.getLogger(__name__)


def _pdf_unavailable_response(request):
    """Return a user-friendly response when PDF generation is unavailable."""
    return render(
        request,
        "reports/pdf_unavailable.html",
        {
            "reason": get_pdf_unavailable_reason(),
        },
        status=503,
    )


@login_required
@requires_permission("metric.view_individual")
def client_progress_pdf(request, client_id):
    """Generate a PDF progress report for an individual client.

    Available to staff (scoped to their programs) and program managers.
    Uses the same permission as client_analysis — if you can see the
    charts in-app, you can generate a PDF of them. Admin-only users
    (no program roles) are blocked by _get_client_or_403().
    """
    if not is_pdf_available():
        return _pdf_unavailable_response(request)

    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # Program enrolments
    enrolments = ClientProgramEnrolment.objects.filter(
        client_file=client, status="enrolled"
    ).select_related("program")

    # Plan sections and targets
    sections = PlanSection.objects.filter(
        client_file=client, status="default"
    ).prefetch_related("targets")

    # Build metric tables: for each target, collect metric values
    metric_tables = []
    targets = PlanTarget.objects.filter(
        client_file=client, status="default"
    ).prefetch_related("metrics")

    for target in targets:
        ptm_links = PlanTargetMetric.objects.filter(
            plan_target=target
        ).select_related("metric_def")

        for ptm in ptm_links:
            metric_def = ptm.metric_def
            values = MetricValue.objects.filter(
                metric_def=metric_def,
                progress_note_target__plan_target=target,
                progress_note_target__progress_note__client_file=client,
                progress_note_target__progress_note__status="default",
            ).select_related(
                "progress_note_target__progress_note__author"
            ).order_by(
                "progress_note_target__progress_note__created_at"
            )

            if not values:
                continue

            rows = []
            for mv in values:
                note = mv.progress_note_target.progress_note
                try:
                    numeric_val = float(mv.value)
                except (ValueError, TypeError):
                    numeric_val = mv.value
                rows.append({
                    "date": note.effective_date.strftime("%Y-%m-%d"),
                    "value": numeric_val,
                    "author": note.author.display_name,
                })

            metric_tables.append({
                "target_name": target.name,
                "metric_name": metric_def.name,
                "unit": metric_def.unit or "",
                "min_value": metric_def.min_value,
                "max_value": metric_def.max_value,
                "rows": rows,
            })

    # Recent progress notes (last 20)
    notes = ProgressNote.objects.filter(
        client_file=client, status="default"
    ).select_related("author")[:20]

    # Recent events (last 20)
    events = Event.objects.filter(
        client_file=client, status="default"
    ).select_related("event_type")[:20]

    context = {
        "client": client,
        "enrolments": enrolments,
        "sections": sections,
        "metric_tables": metric_tables,
        "notes": notes,
        "events": events,
        "generated_at": timezone.now(),
        "generated_by": request.user.display_name,
    }

    safe_id = sanitise_filename(client.record_id or str(client.pk))
    filename = f"progress_report_{safe_id}_{timezone.now():%Y-%m-%d}.pdf"

    audit_pdf_export(request, "export", "client_progress_pdf", {
        "client_id": client.pk,
        "record_id": client.record_id,
        "format": "pdf",
    })

    return render_pdf("reports/pdf_client_progress.html", context, filename)


def generate_outcome_report_pdf(
    request, program, selected_metrics, date_from, date_to, rows, unique_clients,
    grouping_type="none", grouping_label=None, achievement_summary=None,
    total_clients_display=None, total_data_points_display=None,
    is_aggregate=False, aggregate_rows=None, demographic_aggregate_rows=None,
):
    """Generate a PDF program outcome report. Called from export_form view.

    Args:
        request: The HTTP request.
        program: The Program object.
        selected_metrics: List of MetricDefinition objects.
        date_from: Start date for the report.
        date_to: End date for the report.
        rows: List of row dicts with metric data (empty for aggregate).
        unique_clients: Set of unique client IDs in the report.
        grouping_type: "none", "age_range", or "custom_field".
        grouping_label: Human-readable label for the grouping.
        achievement_summary: Optional dict with achievement rates.
        total_clients_display: Suppressed client count for confidential programs.
        total_data_points_display: Suppressed data points count.
        is_aggregate: If True, show aggregate summary instead of individual rows.
        aggregate_rows: List of aggregate row dicts (metric stats).
        demographic_aggregate_rows: List of demographic breakdown row dicts.
    """
    if not is_pdf_available():
        return _pdf_unavailable_response(request)

    # Group rows by demographic if grouping is enabled (individual path only)
    grouped_rows = {}
    if not is_aggregate and grouping_type != "none" and grouping_label:
        for row in rows:
            group = row.get("demographic_group", _("Unknown"))
            if group not in grouped_rows:
                grouped_rows[group] = []
            grouped_rows[group].append(row)
        # Sort groups alphabetically, but put "Unknown" at the end
        sorted_groups = sorted(
            grouped_rows.keys(),
            key=lambda x: (x == _("Unknown"), str(x))
        )
        grouped_rows = {k: grouped_rows[k] for k in sorted_groups}

    context = {
        "program": program,
        "metrics": selected_metrics,
        "date_from": date_from,
        "date_to": date_to,
        "rows": rows,
        "total_clients": total_clients_display if total_clients_display is not None else len(unique_clients),
        "total_data_points": total_data_points_display if total_data_points_display is not None else len(rows),
        "generated_at": timezone.now(),
        "generated_by": request.user.display_name,
        "grouping_type": grouping_type,
        "grouping_label": grouping_label,
        "grouped_rows": grouped_rows if grouping_type != "none" else None,
        "achievement_summary": achievement_summary,
        "is_aggregate": is_aggregate,
        "aggregate_rows": aggregate_rows or [],
        "demographic_aggregate_rows": demographic_aggregate_rows or [],
    }

    safe_prog_name = sanitise_filename(program.name.replace(" ", "_"))
    filename = f"outcome_report_{safe_prog_name}_{date_from}_{date_to}.pdf"

    audit_metadata = {
        "program": program.name,
        "metrics": [m.name for m in selected_metrics],
        "date_from": str(date_from),
        "date_to": str(date_to),
        "total_clients": len(unique_clients),
        "total_data_points": len(rows),
        "format": "pdf",
    }
    if grouping_type != "none":
        audit_metadata["grouped_by"] = grouping_label
    if achievement_summary:
        audit_metadata["include_achievement_rate"] = True
        audit_metadata["achievement_rate"] = achievement_summary.get("overall_rate")

    audit_pdf_export(request, "export", "outcome_report_pdf", audit_metadata)

    return render_pdf("reports/pdf_funder_report.html", context, filename)


def generate_funder_report_pdf(request, report_data, sections=None,
                               metric_results=None):
    """
    Generate a PDF for funder report (aggregate program outcome report).

    Args:
        request: The HTTP request.
        report_data: Dict returned by generate_funder_report_data().
        sections: Optional list of ReportSection instances (ordered by
            sort_order) to structure the PDF layout.  When provided, the
            template renders sections in order instead of hard-coded layout.
        metric_results: Optional list from compute_template_metrics()
            providing aggregated metric values per demographic group.

    Returns:
        HttpResponse with PDF attachment.
    """
    if not is_pdf_available():
        return _pdf_unavailable_response(request)

    from .suppression import SMALL_CELL_THRESHOLD

    context = {
        "report_data": report_data,
        "generated_by": request.user.display_name,
        "suppression_threshold": SMALL_CELL_THRESHOLD,
    }

    if sections:
        context["sections"] = sections
    if metric_results:
        context["metric_results"] = metric_results

    safe_name = sanitise_filename(report_data["program_name"].replace(" ", "_"))
    fy_label = sanitise_filename(report_data["reporting_period"].replace(" ", "_"))
    filename = f"Funder_Report_{safe_name}_{fy_label}.pdf"

    audit_pdf_export(request, "export", "funder_report_pdf", {
        "program": report_data["program_name"],
        "organisation": report_data["organisation_name"],
        "reporting_period": report_data["reporting_period"],
        "total_individuals_served": report_data["total_individuals_served"],
        "format": "pdf",
    })

    return render_pdf("reports/pdf_funder_outcome_report.html", context, filename)


def _collect_client_data(client, include_plans, include_notes, include_metrics, include_events, include_custom_fields, user_program_ids=None):
    """Collect all data for an individual client export."""
    data = {}

    # Include enrolments (all statuses, not just enrolled) — filtered to
    # programs the requesting user can see, so confidential program
    # enrolments are never leaked in exports.
    enrolments_qs = ClientProgramEnrolment.objects.filter(
        client_file=client
    ).select_related("program").order_by("-enrolled_at")
    if user_program_ids is not None:
        enrolments_qs = enrolments_qs.filter(program_id__in=user_program_ids)
    data["enrolments"] = enrolments_qs

    # Custom fields
    if include_custom_fields:
        detail_values = ClientDetailValue.objects.filter(
            client_file=client,
            field_def__status="active",
        ).select_related("field_def")
        data["custom_fields"] = [
            {"name": dv.field_def.name, "value": dv.get_value()}
            for dv in detail_values
        ]
    else:
        data["custom_fields"] = []

    # Plan sections and targets
    if include_plans:
        data["sections"] = PlanSection.objects.filter(
            client_file=client, status="default"
        ).prefetch_related("targets")
    else:
        data["sections"] = []

    # Metric tables
    if include_metrics:
        metric_tables = []
        targets = PlanTarget.objects.filter(
            client_file=client, status="default"
        ).prefetch_related("metrics")

        for target in targets:
            ptm_links = PlanTargetMetric.objects.filter(
                plan_target=target
            ).select_related("metric_def")

            for ptm in ptm_links:
                metric_def = ptm.metric_def
                values = MetricValue.objects.filter(
                    metric_def=metric_def,
                    progress_note_target__plan_target=target,
                    progress_note_target__progress_note__client_file=client,
                    progress_note_target__progress_note__status="default",
                ).select_related(
                    "progress_note_target__progress_note__author"
                ).order_by(
                    "progress_note_target__progress_note__created_at"
                )

                if not values:
                    continue

                rows = []
                for mv in values:
                    note = mv.progress_note_target.progress_note
                    try:
                        numeric_val = float(mv.value)
                    except (ValueError, TypeError):
                        numeric_val = mv.value
                    rows.append({
                        "date": note.effective_date.strftime("%Y-%m-%d"),
                        "value": numeric_val,
                        "author": note.author.display_name,
                    })

                metric_tables.append({
                    "target_name": target.name,
                    "metric_name": metric_def.name,
                    "unit": metric_def.unit or "",
                    "min_value": metric_def.min_value,
                    "max_value": metric_def.max_value,
                    "rows": rows,
                })
        data["metric_tables"] = metric_tables
    else:
        data["metric_tables"] = []

    # Progress notes (all, not just last 20 — this is a full data export)
    if include_notes:
        data["notes"] = ProgressNote.objects.filter(
            client_file=client, status="default"
        ).select_related("author").order_by("-created_at")
    else:
        data["notes"] = []

    # Events (all)
    if include_events:
        data["events"] = Event.objects.filter(
            client_file=client, status="default"
        ).select_related("event_type").order_by("-start_timestamp")
    else:
        data["events"] = []

    return data


def _generate_client_csv(client, data):
    """Generate a CSV export of an individual client's data.

    All cell values are sanitised to prevent CSV injection (formula injection)
    in spreadsheet applications. See csv_utils.sanitise_csv_row().
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Client info section
    writer.writerow(sanitise_csv_row(["=== %s ===" % _("CLIENT INFORMATION")]))
    writer.writerow(sanitise_csv_row([_("First Name"), client.first_name]))
    writer.writerow(sanitise_csv_row([_("Last Name"), client.last_name]))
    if client.middle_name:
        writer.writerow(sanitise_csv_row([_("Middle Name"), client.middle_name]))
    if client.record_id:
        writer.writerow(sanitise_csv_row([_("Record ID"), client.record_id]))
    if client.birth_date:
        writer.writerow(sanitise_csv_row([_("Date of Birth"), client.birth_date]))
    writer.writerow(sanitise_csv_row([_("Status"), client.status]))
    writer.writerow(sanitise_csv_row([_("Created"), client.created_at.strftime("%Y-%m-%d")]))
    if client.consent_given_at:
        writer.writerow(sanitise_csv_row([_("Consent Given"), client.consent_given_at.strftime("%Y-%m-%d")]))
        if client.consent_type:
            writer.writerow(sanitise_csv_row([_("Consent Type"), client.consent_type]))
    writer.writerow([])

    # Enrolments
    if data["enrolments"]:
        writer.writerow(sanitise_csv_row(["=== %s ===" % _("PROGRAM ENROLMENTS")]))
        writer.writerow(sanitise_csv_row([_("Program"), _("Status"), _("Enrolled"), _("Unenrolled")]))
        for e in data["enrolments"]:
            writer.writerow(sanitise_csv_row([
                e.program.name,
                e.get_status_display(),
                e.enrolled_at.strftime("%Y-%m-%d"),
                e.unenrolled_at.strftime("%Y-%m-%d") if e.unenrolled_at else "",
            ]))
        writer.writerow([])

    # Custom fields
    if data["custom_fields"]:
        writer.writerow(sanitise_csv_row(["=== %s ===" % _("CUSTOM FIELDS")]))
        writer.writerow(sanitise_csv_row([_("Field"), _("Value")]))
        for field in data["custom_fields"]:
            writer.writerow(sanitise_csv_row([field["name"], field["value"]]))
        writer.writerow([])

    # Plans
    if data["sections"]:
        writer.writerow(sanitise_csv_row(["=== %s ===" % _("PLAN SECTIONS & TARGETS")]))
        writer.writerow(sanitise_csv_row([_("Section"), _("Target"), _("Description")]))
        for section in data["sections"]:
            for target in section.targets.all():
                writer.writerow(sanitise_csv_row([section.name, target.name, target.description or ""]))
        writer.writerow([])

    # Metrics
    if data["metric_tables"]:
        writer.writerow(sanitise_csv_row(["=== %s ===" % _("METRIC PROGRESS")]))
        writer.writerow(sanitise_csv_row([_("Target"), _("Metric"), _("Date"), _("Value"), _("Author")]))
        for table in data["metric_tables"]:
            for row in table["rows"]:
                writer.writerow(sanitise_csv_row([
                    table["target_name"], table["metric_name"],
                    row["date"], row["value"], row["author"],
                ]))
        writer.writerow([])

    # Notes
    if data["notes"]:
        writer.writerow(sanitise_csv_row(["=== %s ===" % _("PROGRESS NOTES")]))
        writer.writerow(sanitise_csv_row([_("Date"), _("Type"), _("Author"), _("Content"), _("Summary")]))
        for note in data["notes"]:
            writer.writerow(sanitise_csv_row([
                note.effective_date.strftime("%Y-%m-%d"),
                note.get_note_type_display(),
                note.author.display_name,
                note.notes_text or "",
                note.summary or "",
            ]))
        writer.writerow([])

    # Events
    if data["events"]:
        writer.writerow(sanitise_csv_row(["=== %s ===" % _("EVENTS")]))
        writer.writerow(sanitise_csv_row([_("Date"), _("Type"), _("Title"), _("Description")]))
        for event in data["events"]:
            writer.writerow(sanitise_csv_row([
                event.start_timestamp.strftime("%Y-%m-%d"),
                event.event_type.name if event.event_type else "",
                event.title or "",
                event.description or "",
            ]))

    return output.getvalue()


@login_required
@requires_permission("report.data_extract")
def client_export(request, client_id):
    """Export all data for an individual client (PIPEDA data portability).

    Available to program managers (ALLOW in matrix). PMs handle data
    portability requests for clients in their programs. Staff and
    executives are blocked (DENY). Admin-only users without program
    roles are blocked by _get_client_or_403().
    """
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    client_name = f"{client.first_name} {client.last_name}"

    if request.method == "POST":
        form = IndividualClientExportForm(request.POST)
        if form.is_valid():
            export_format = form.cleaned_data["format"]
            include_plans = form.cleaned_data["include_plans"]
            include_notes = form.cleaned_data["include_notes"]
            include_metrics = form.cleaned_data["include_metrics"]
            include_events = form.cleaned_data["include_events"]
            include_custom_fields = form.cleaned_data["include_custom_fields"]
            recipient = form.get_recipient_display()

            # Collect all requested data — pass user's program IDs so
            # confidential program enrolments are excluded from export.
            from apps.clients.views import _get_user_program_ids
            user_program_ids = _get_user_program_ids(request.user)
            data = _collect_client_data(
                client, include_plans, include_notes,
                include_metrics, include_events, include_custom_fields,
                user_program_ids=user_program_ids,
            )

            # Audit log
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=request.user.display_name,
                action="export",
                resource_type="individual_client_export",
                resource_id=client.pk,
                ip_address=_get_client_ip(request),
                is_demo_context=getattr(request.user, "is_demo", False),
                metadata={
                    "client_id": client.pk,
                    "record_id": client.record_id,
                    "format": export_format,
                    "include_plans": include_plans,
                    "include_notes": include_notes,
                    "include_metrics": include_metrics,
                    "include_events": include_events,
                    "include_custom_fields": include_custom_fields,
                    "recipient": recipient,
                },
            )

            safe_name = sanitise_filename(client.record_id or str(client.pk))
            date_str = timezone.now().strftime("%Y-%m-%d")

            if export_format == "csv":
                csv_content = _generate_client_csv(client, data)
                response = HttpResponse(csv_content, content_type="text/csv")
                response["Content-Disposition"] = (
                    f'attachment; filename="client_export_{safe_name}_{date_str}.csv"'
                )
                return response

            # PDF format
            if not is_pdf_available():
                return _pdf_unavailable_response(request)

            context = {
                "client": client,
                "enrolments": data["enrolments"],
                "custom_fields": data["custom_fields"],
                "sections": data["sections"],
                "metric_tables": data["metric_tables"],
                "notes": data["notes"],
                "events": data["events"],
                "include_plans": include_plans,
                "include_notes": include_notes,
                "include_metrics": include_metrics,
                "include_events": include_events,
                "generated_at": timezone.now(),
                "generated_by": request.user.display_name,
            }

            filename = f"client_export_{safe_name}_{date_str}.pdf"
            return render_pdf("reports/pdf_client_data_export.html", context, filename)
    else:
        form = IndividualClientExportForm()

    return render(request, "reports/client_export_form.html", {
        "form": form,
        "client": client,
        "client_name": client_name,
    })


# ---------------------------------------------------------------------------
# Board Summary PDF
# ---------------------------------------------------------------------------

def _derive_outcome_trend(metric_id, metric_trends):
    """Derive a trend direction for a single metric from monthly trend data.

    Uses the band_high_pct (percentage in the top band) from the first
    and last months to determine direction:
      - >5pp increase  -> "improving"
      - >5pp decrease  -> "declining"
      - otherwise       -> "stable"
      - <2 data points -> "new"

    Does NOT show band counts (DRR anti-pattern: show trend direction only).
    """
    trend_points = metric_trends.get(metric_id, [])
    if len(trend_points) < 2:
        return "new"

    first_high = trend_points[0].get("band_high_pct", 0)
    last_high = trend_points[-1].get("band_high_pct", 0)
    diff = last_high - first_high

    if diff > 5:
        return "improving"
    elif diff < -5:
        return "declining"
    return "stable"


def generate_board_summary_pdf(request, program, date_from, date_to,
                               period_label, narrative=None):
    """Generate a Board Summary PDF for a single program.

    Collects data from multiple insight sources and renders a compact
    1-2 page summary suitable for board meetings.

    Args:
        request: The HTTP request.
        program: Program instance.
        date_from: Start date for the reporting period.
        date_to: End date for the reporting period.
        period_label: Human-readable period (e.g. "Q3 FY2025-26").
        narrative: Optional narrative text for the qualitative section.

    Returns:
        HttpResponse with PDF attachment.
    """
    if not is_pdf_available():
        return _pdf_unavailable_response(request)

    # Organisation name
    organisation_name = InstanceSetting.get("organisation_name", "")
    if not organisation_name:
        organisation_name = InstanceSetting.get("agency_name", "")

    # --- Section 1: Program Overview ---
    structured = get_structured_insights(
        program=program,
        date_from=date_from,
        date_to=date_to,
    )

    enrolled_count = (
        ClientProgramEnrolment.objects.filter(
            program=program, status="enrolled",
        ).values("client_file_id").distinct().count()
    )

    # Achievement rates for outcome metrics
    achievement_rates = get_achievement_rates(program, date_from, date_to)

    # Metric trends for trend direction (no band counts — DRR anti-pattern)
    metric_trends = get_metric_trends(program, date_from, date_to)

    # Build outcome rows: name, current rate, target, trend direction
    outcomes = []
    for metric_id, ach_data in achievement_rates.items():
        trend = _derive_outcome_trend(metric_id, metric_trends)
        outcomes.append({
            "name": ach_data["name"],
            "achieved_pct": ach_data["achieved_pct"],
            "target_rate": ach_data.get("target_rate"),
            "trend": trend,
        })

    # --- Section 2: What Participants Are Telling Us ---
    # Feedback themes (top 5, sorted by priority)
    active_themes = list(
        SuggestionTheme.objects.active()
        .filter(program=program)
        .annotate(link_count=Count("links"))
        .values("pk", "name", "status", "priority", "updated_at", "link_count")
    )
    active_themes.sort(key=lambda t: (
        -THEME_PRIORITY_RANK.get(t["priority"], 0),
        -t["updated_at"].timestamp(),
    ))
    # Limit to top 5 for board summary
    themes = active_themes[:5]

    # Curated quotes (privacy-gated: suppress if <MIN_PARTICIPANTS_FOR_QUOTES)
    quotes = []
    quotes_suppressed = False
    if enrolled_count >= MIN_PARTICIPANTS_FOR_QUOTES:
        quotes = collect_quotes(
            program=program,
            date_from=date_from,
            date_to=date_to,
            max_quotes=3,          # Board summary: 3 curated quotes max
            include_dates=False,   # Privacy: no dates in board report
        )
    elif enrolled_count > 0:
        quotes_suppressed = True

    # --- Section 3: Data Quality ---
    completeness = get_data_completeness(program, date_from, date_to)

    # --- Build context ---
    context = {
        "program": program,
        "organisation_name": organisation_name,
        "period_label": period_label,
        "generated_at": timezone.now(),
        # Section 1: Program Overview
        "enrolled_count": enrolled_count,
        "notes_count": structured["note_count"],
        "months_of_data": structured["month_count"],
        "outcomes": outcomes,
        # Section 2: What Participants Are Telling Us
        "themes": themes,
        "quotes": quotes,
        "quotes_suppressed": quotes_suppressed,
        "min_participants_for_quotes": MIN_PARTICIPANTS_FOR_QUOTES,
        # Section 3: Data Quality
        "completeness": completeness,
        # Section 4: Narrative
        "narrative": narrative,
    }

    safe_prog = sanitise_filename(program.name.replace(" ", "_"))
    safe_period = sanitise_filename(period_label.replace(" ", "_"))
    filename = f"Board_Summary_{safe_prog}_{safe_period}.pdf"

    audit_pdf_export(request, "export", "board_summary_pdf", {
        "program": program.name,
        "period": period_label,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "format": "pdf",
    })

    return render_pdf("reports/pdf_board_summary.html", context, filename)


@login_required
@requires_permission("report.funder_report")
def board_summary_pdf(request, program_id):
    """Generate a Board Summary PDF for a program.

    GET parameters:
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).
        period_label: Human-readable period label (optional).

    Access: Same as funder report (admin, program_manager, executive).
    """
    from datetime import date

    program = get_object_or_404(Program, pk=program_id)

    # Parse date range from query params
    date_from_str = request.GET.get("date_from", "")
    date_to_str = request.GET.get("date_to", "")

    try:
        date_from = date.fromisoformat(date_from_str)
    except (ValueError, TypeError):
        # Default: last 12 months
        date_to = date.today()
        date_from = date(date_to.year - 1, date_to.month, date_to.day)

    try:
        date_to = date.fromisoformat(date_to_str)
    except (ValueError, TypeError):
        date_to = date.today()

    period_label = request.GET.get(
        "period_label",
        f"{date_from.strftime('%b %Y')} \u2013 {date_to.strftime('%b %Y')}",
    )

    return generate_board_summary_pdf(
        request=request,
        program=program,
        date_from=date_from,
        date_to=date_to,
        period_label=period_label,
    )
