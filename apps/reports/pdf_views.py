"""PDF export views for client progress reports, program outcome reports, and individual client data export."""
import csv
import io
import json
import uuid

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.audit.models import AuditLog
from apps.auth_app.decorators import admin_required, minimum_role, requires_permission
from apps.clients.models import ClientDetailValue, ClientProgramEnrolment
from apps.events.models import Event
from apps.notes.models import MetricValue, ProgressNote
from apps.plans.models import PlanSection, PlanTarget, PlanTargetMetric

from .csv_utils import sanitise_csv_row, sanitise_filename
from .forms import IndividualClientExportForm
from .pdf_utils import (
    audit_pdf_export,
    get_pdf_unavailable_reason,
    is_pdf_available,
    render_pdf,
)
from .views import _get_client_ip, _get_client_or_403, _save_export_and_create_link


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
        client_file=client, status="active"
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

    from .chart_utils import generate_metric_charts, is_chart_available
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

        # Generate chart images for chart sections
        if is_chart_available():
            chart_images = generate_metric_charts(metric_results)
            context["chart_images"] = chart_images

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


def _collect_client_data(client, include_plans, include_notes, include_metrics, include_events, include_custom_fields, user_program_ids=None, user=None):
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
                values_qs = MetricValue.objects.filter(
                    metric_def=metric_def,
                    progress_note_target__plan_target=target,
                    progress_note_target__progress_note__client_file=client,
                    progress_note_target__progress_note__status="default",
                ).select_related(
                    "progress_note_target__progress_note__author"
                ).order_by(
                    "progress_note_target__progress_note__created_at"
                )
                # Apply PHIPA consent: exclude metric values from
                # cross-program notes when sharing is restricted.
                if user is not None and user_program_ids is not None:
                    from apps.programs.access import apply_consent_filter
                    visible_note_ids = ProgressNote.objects.filter(
                        client_file=client, status="default"
                    ).values_list("pk", flat=True)
                    filtered_notes, _ = apply_consent_filter(
                        ProgressNote.objects.filter(pk__in=visible_note_ids),
                        client, user, user_program_ids=user_program_ids,
                    )
                    values_qs = values_qs.filter(
                        progress_note_target__progress_note__in=filtered_notes
                    )
                values = values_qs

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
    # Apply PHIPA consent filtering: cross-program notes are only visible
    # when the agency or participant has enabled sharing.
    if include_notes:
        from apps.programs.access import apply_consent_filter
        notes_qs = ProgressNote.objects.filter(
            client_file=client, status="default"
        ).select_related("author").order_by("-created_at")
        if user is not None:
            notes_qs, _ = apply_consent_filter(
                notes_qs, client, user, user_program_ids=user_program_ids,
            )
        data["notes"] = notes_qs
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


def _generate_client_json(client, data, exported_by):
    """Generate a JSON export of an individual client's data (PIPEDA portability).

    Returns a JSON string with nested client-centric structure including
    human-readable labels alongside raw values.
    """
    export = {
        "export_metadata": {
            "exported_at": timezone.now().isoformat(),
            "exported_by": exported_by,
            "format_version": "1.0",
        },
        "client": {
            "first_name": client.first_name,
            "last_name": client.last_name,
        },
    }
    client_data = export["client"]

    if client.middle_name:
        client_data["middle_name"] = client.middle_name
    if client.birth_date:
        client_data["date_of_birth"] = str(client.birth_date)
    if client.record_id:
        client_data["record_id"] = client.record_id
    client_data["status"] = client.status
    client_data["created_at"] = client.created_at.isoformat()
    if client.consent_given_at:
        client_data["consent_given_at"] = client.consent_given_at.isoformat()
        if client.consent_type:
            client_data["consent_type"] = client.consent_type

    # Programs (enrolments with nested plan targets, notes, metrics)
    programs = []
    for enrolment in data["enrolments"]:
        program_entry = {
            "name": enrolment.program.name,
            "status": enrolment.status,
            "enrolled": str(enrolment.enrolled_at) if enrolment.enrolled_at else None,
            "unenrolled": str(enrolment.unenrolled_at) if enrolment.unenrolled_at else None,
        }

        # Plan targets for this program
        plan_targets = []
        for section in data.get("sections", []):
            for target in section.targets.all():
                plan_targets.append({
                    "section": section.name,
                    "name": target.name,
                    "status": target.status,
                })
        program_entry["plan_targets"] = plan_targets

        # Progress notes
        progress_notes = []
        for note in data.get("notes", []):
            note_entry = {
                "date": str(note.effective_date) if note.effective_date else str(note.created_at.date()),
                "interaction_type": {
                    "value": note.interaction_type,
                    "label": note.get_interaction_type_display(),
                },
                "author": note.author.display_name if note.author else "",
                "created_at": note.created_at.isoformat(),
            }
            # Target entries with progress descriptors
            target_entries = []
            for te in note.target_entries.all():
                entry = {
                    "target": te.plan_target.name if te.plan_target else "",
                    "notes": te.notes,
                }
                if te.progress_descriptor:
                    entry["progress_descriptor"] = {
                        "value": te.progress_descriptor,
                        "label": te.get_progress_descriptor_display(),
                    }
                target_entries.append(entry)
            note_entry["target_entries"] = target_entries
            progress_notes.append(note_entry)
        program_entry["progress_notes"] = progress_notes

        # Metric values
        metric_values = []
        for mt in data.get("metric_tables", []):
            metric_entry = {
                "target_name": mt["target_name"],
                "metric_name": mt["metric_name"],
                "unit": mt["unit"],
                "min_value": mt["min_value"],
                "max_value": mt["max_value"],
                "values": mt["rows"],
            }
            metric_values.append(metric_entry)
        program_entry["metric_values"] = metric_values

        programs.append(program_entry)
    client_data["programs"] = programs

    # Events
    events = []
    for event in data.get("events", []):
        events.append({
            "date": event.start_timestamp.strftime("%Y-%m-%d"),
            "type": event.event_type.name if event.event_type else "",
            "title": event.title or "",
            "description": event.description or "",
        })
    client_data["events"] = events

    # Custom fields
    client_data["custom_fields"] = data.get("custom_fields", [])

    return json.dumps(export, ensure_ascii=False, indent=2, default=str)


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
        # Idempotency: reject duplicate POSTs from the same form render.
        # Only enforced when the nonce hidden field is present in the POST
        # (always true in the browser form, not present in direct API calls).
        submitted_nonce = request.POST.get("_export_nonce")
        if submitted_nonce is not None:
            session_key = f"export_nonce_{client_id}"
            expected_nonce = request.session.get(session_key, "")
            if not submitted_nonce or submitted_nonce != expected_nonce:
                form = IndividualClientExportForm()
                nonce = uuid.uuid4().hex
                request.session[session_key] = nonce
                return render(request, "reports/client_export_form.html", {
                    "form": form, "client": client, "client_name": client_name,
                    "duplicate_warning": True, "export_nonce": nonce,
                })
            # Clear nonce so it can't be reused
            request.session.pop(session_key, None)

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
                user=request.user,
            )

            safe_name = sanitise_filename(client.record_id or str(client.pk))
            date_str = timezone.now().strftime("%Y-%m-%d")

            # Generate file content based on format
            if export_format == "json":
                content = _generate_client_json(client, data, request.user.display_name)
                filename = f"client_export_{safe_name}_{date_str}.json"
            elif export_format == "csv":
                content = _generate_client_csv(client, data)
                filename = f"client_export_{safe_name}_{date_str}.csv"
            else:
                # PDF format
                if not is_pdf_available():
                    return _pdf_unavailable_response(request)
                from django.template.loader import render_to_string
                from weasyprint import HTML
                pdf_context = {
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
                from django.conf import settings as django_settings
                html_string = render_to_string("reports/pdf_client_data_export.html", pdf_context)
                base_url = getattr(django_settings, "STATIC_ROOT", None) or "."
                content = HTML(string=html_string, base_url=base_url).write_pdf()
                filename = f"client_export_{safe_name}_{date_str}.pdf"

            # Save to file and create SecureExportLink
            link = _save_export_and_create_link(
                request,
                content=content,
                filename=filename,
                export_type="individual_client",
                client_count=1,
                includes_notes=include_notes,
                recipient=recipient,
                filters_dict={
                    "client_id": client.pk,
                    "format": export_format,
                    "include_plans": include_plans,
                    "include_notes": include_notes,
                    "include_metrics": include_metrics,
                    "include_events": include_events,
                    "include_custom_fields": include_custom_fields,
                },
                contains_pii=True,
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
                    "delivery": "secure_link",
                    "link_id": str(link.pk),
                },
            )

            return render(request, "reports/client_export_ready.html", {
                "client": client,
                "client_name": client_name,
                "link": link,
            })
    else:
        form = IndividualClientExportForm()

    # Generate nonce for idempotency
    nonce = uuid.uuid4().hex
    request.session[f"export_nonce_{client_id}"] = nonce

    return render(request, "reports/client_export_form.html", {
        "form": form,
        "client": client,
        "client_name": client_name,
        "export_nonce": nonce,
    })
