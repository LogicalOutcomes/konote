"""Report views — aggregate metric CSV export, funder report, client analysis charts, and secure links."""
import csv
import io
import json
import logging
import os
import uuid
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import F, Q
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.auth_app.decorators import admin_required, requires_permission
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.clients.views import get_client_queryset
from apps.notes.models import MetricValue, ProgressNote
from apps.plans.models import PlanTarget, PlanTargetMetric
from apps.programs.models import UserProgramRole
from .achievements import get_achievement_summary, format_achievement_summary
from .funder_report import generate_funder_report_data, generate_funder_report_csv_rows
from .csv_utils import sanitise_csv_row, sanitise_filename
from .demographics import (
    aggregate_by_demographic, get_age_range, group_clients_by_age,
    group_clients_by_custom_field, parse_grouping_choice,
)
from .models import DemographicBreakdown, FunderProfile, SecureExportLink
from .suppression import suppress_small_cell
from .forms import FunderReportForm, MetricExportForm
from .aggregations import aggregate_metrics, _stats_from_list
from .utils import (
    can_download_pii_export,
    get_manageable_programs,
    is_aggregate_only_user,
)

logger = logging.getLogger(__name__)


from konote.utils import get_client_ip as _get_client_ip


def _notify_admins_elevated_export(link, request):
    """
    Send email notification to all active admins about an elevated export.

    Elevated exports (100+ clients or includes notes) have a delay before
    download is available. This notification gives admins time to review
    and revoke if needed.

    Fails gracefully — logs a warning if email sending fails but does not
    block the export creation.
    """
    admins = User.objects.filter(is_admin=True, is_active=True)
    admin_emails = [u.email for u in admins if u.email]
    if not admin_emails:
        logger.warning("No admin email addresses found for elevated export notification (link %s)", link.id)
        return

    manage_url = request.build_absolute_uri(
        reverse("reports:manage_export_links")
    )

    context = {
        "link": link,
        "creator_name": link.created_by.display_name,
        "creator_email": link.created_by.email or "no email on file",
        "manage_url": manage_url,
        "available_at": link.available_at,
        "delay_minutes": getattr(settings, "ELEVATED_EXPORT_DELAY_MINUTES", 10),
    }

    subject = f"Elevated Export Alert — {link.client_count} clients"
    text_body = render_to_string("reports/email/elevated_export_alert.txt", context)
    html_body = render_to_string("reports/email/elevated_export_alert.html", context)

    try:
        send_mail(
            subject=subject,
            message=text_body,
            html_message=html_body,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=admin_emails,
        )
        SecureExportLink.objects.filter(pk=link.pk).update(
            admin_notified_at=timezone.now()
        )
    except Exception:
        logger.warning(
            "Failed to send elevated export notification for link %s",
            link.id,
            exc_info=True,
        )


def _save_export_and_create_link(request, content, filename, export_type,
                                  client_count, includes_notes, recipient,
                                  filters_dict=None, contains_pii=True):
    """
    Save export content to a temp file and create a SecureExportLink.

    Args:
        request: The HTTP request (for user info).
        content: File content — str for CSV, bytes for PDF.
        filename: Display filename for downloads (e.g., "export_2026-02-05.csv").
        export_type: One of "metrics", "funder_report".
        client_count: Number of clients in the export.
        includes_notes: Whether clinical note content is included.
        recipient: Who is receiving the data (from ExportRecipientMixin).
        filters_dict: Optional dict of filter parameters for audit.
        contains_pii: Whether the export contains individual client data
                      (record IDs, names, per-client rows). Defaults to True
                      (deny-by-default). Aggregate-only exports must explicitly
                      set False. Used by download_export() for defense-in-depth
                      re-validation — non-admins cannot download PII exports.

    Returns:
        SecureExportLink instance.
    """
    export_dir = settings.SECURE_EXPORT_DIR
    os.makedirs(export_dir, exist_ok=True)

    link_id = uuid.uuid4()
    safe_filename = f"{link_id}_{filename}"
    file_path = os.path.join(export_dir, safe_filename)

    # Write content to file
    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = None if isinstance(content, bytes) else "utf-8"
    with open(file_path, mode, encoding=encoding) as f:
        f.write(content)

    expiry_hours = getattr(settings, "SECURE_EXPORT_LINK_EXPIRY_HOURS", 24)
    # PM individual exports are ALWAYS elevated (delay + admin notification)
    # to add friction for PII access. Other exports use the standard threshold.
    from apps.programs.models import UserProgramRole

    creator_is_pm = UserProgramRole.objects.filter(
        user=request.user, role="program_manager", status="active"
    ).exists()
    is_elevated = (
        client_count >= 100
        or includes_notes
        or (contains_pii and creator_is_pm)
    )
    link = SecureExportLink.objects.create(
        id=link_id,
        created_by=request.user,
        expires_at=timezone.now() + timedelta(hours=expiry_hours),
        export_type=export_type,
        filters_json=json.dumps(filters_dict or {}),
        client_count=client_count,
        includes_notes=includes_notes,
        contains_pii=contains_pii,
        recipient=recipient,
        filename=filename,
        file_path=file_path,
        is_elevated=is_elevated,
    )

    if is_elevated:
        _notify_admins_elevated_export(link, request)

    return link


def _build_demographic_map(metric_values, grouping_type, grouping_field, as_of_date):
    """
    Build a mapping of client IDs to their demographic group labels.

    Args:
        metric_values: QuerySet of MetricValue objects.
        grouping_type: "age_range" or "custom_field".
        grouping_field: CustomFieldDefinition for custom_field grouping.
        as_of_date: Date to use for age calculations.

    Returns:
        Dict mapping client_id to demographic group label.
    """
    from apps.clients.models import ClientDetailValue, ClientFile

    client_demographic_map = {}

    # Collect all unique client IDs
    client_ids = set()
    for mv in metric_values:
        client_ids.add(mv.progress_note_target.progress_note.client_file_id)

    if grouping_type == "age_range":
        # Load clients to access encrypted birth_date
        clients = ClientFile.objects.filter(pk__in=client_ids)
        for client in clients:
            client_demographic_map[client.pk] = get_age_range(client.birth_date, as_of_date)

    elif grouping_type == "custom_field" and grouping_field:
        # Build option labels lookup for dropdown fields
        option_labels = {}
        if grouping_field.input_type == "select" and grouping_field.options_json:
            for option in grouping_field.options_json:
                if isinstance(option, dict):
                    option_labels[option.get("value", "")] = option.get("label", option.get("value", ""))
                else:
                    option_labels[option] = option

        # Get custom field values for all clients
        values = ClientDetailValue.objects.filter(
            client_file_id__in=client_ids,
            field_def=grouping_field,
        )

        for cv in values:
            raw_value = cv.get_value()
            if not raw_value:
                client_demographic_map[cv.client_file_id] = "Unknown"
            else:
                display_value = option_labels.get(raw_value, raw_value)
                client_demographic_map[cv.client_file_id] = display_value

        # Mark clients without a value as Unknown
        for client_id in client_ids:
            if client_id not in client_demographic_map:
                client_demographic_map[client_id] = "Unknown"

    return client_demographic_map


def _get_grouping_label(group_by_value, grouping_field):
    """
    Get a human-readable label for the grouping type.

    Args:
        group_by_value: The raw form value (e.g., "age_range", "custom_123").
        grouping_field: The CustomFieldDefinition if applicable.

    Returns:
        String label for the grouping (e.g., "Age Range", "Gender").
    """
    if not group_by_value:
        return None

    if group_by_value == "age_range":
        return "Age Range"

    if grouping_field:
        return grouping_field.name

    return "Demographic Group"


def _write_achievement_csv(writer, achievement_summary, program):
    """Write the achievement rate summary section to a CSV writer.

    Used by both aggregate and individual export paths. The achievement
    data is already aggregate (counts and percentages) so it's safe for
    all roles.
    """
    writer.writerow([])  # blank separator
    writer.writerow(sanitise_csv_row(["# ===== ACHIEVEMENT RATE SUMMARY ====="]))
    ach_total = suppress_small_cell(achievement_summary["total_clients"], program)
    ach_met = suppress_small_cell(achievement_summary["clients_met_any_target"], program)
    if isinstance(ach_total, str) or isinstance(ach_met, str):
        writer.writerow(sanitise_csv_row([
            f"# Overall: {ach_met} of {ach_total} clients met at least one target"
        ]))
    elif achievement_summary["total_clients"] > 0:
        writer.writerow(sanitise_csv_row([
            f"# Overall: {ach_met} of "
            f"{ach_total} clients "
            f"({achievement_summary['overall_rate']}%) met at least one target"
        ]))
    else:
        writer.writerow(sanitise_csv_row(["# No client data available for achievement calculation"]))

    for metric in achievement_summary.get("by_metric", []):
        m_total = suppress_small_cell(metric["total_clients"], program)
        m_met = suppress_small_cell(metric.get("clients_met_target", 0), program)
        if metric["has_target"]:
            if isinstance(m_total, str) or isinstance(m_met, str):
                writer.writerow(sanitise_csv_row([
                    f"# {metric['metric_name']}: {m_met} of {m_total} clients "
                    f"met target of {metric['target_value']}"
                ]))
            else:
                writer.writerow(sanitise_csv_row([
                    f"# {metric['metric_name']}: {m_met} of "
                    f"{m_total} clients ({metric['achievement_rate']}%) "
                    f"met target of {metric['target_value']}"
                ]))
        else:
            writer.writerow(sanitise_csv_row([
                f"# {metric['metric_name']}: {m_total} clients "
                "(no target defined)"
            ]))


@login_required
@requires_permission("report.program_report", allow_admin=True)
def export_form(request):
    """
    GET  — display the export filter form.
    POST — validate, query metric values, and return a CSV download.

    Access: admin (any program), program_manager or executive (their programs).
    Enforced by @requires_permission("report.program_report").
    """
    is_aggregate = is_aggregate_only_user(request.user)
    is_pm_export = not is_aggregate and not request.user.is_admin

    if request.method != "POST":
        form = MetricExportForm(user=request.user)
        return render(request, "reports/export_form.html", {
            "form": form,
            "is_aggregate_only": is_aggregate,
            "is_pm_export": is_pm_export,
        })

    form = MetricExportForm(request.POST, user=request.user)
    if not form.is_valid():
        return render(request, "reports/export_form.html", {
            "form": form,
            "is_aggregate_only": is_aggregate,
            "is_pm_export": is_pm_export,
        })

    program = form.cleaned_data["program"]
    selected_metrics = form.cleaned_data["metrics"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    group_by_value = form.cleaned_data.get("group_by", "")
    include_achievement = form.cleaned_data.get("include_achievement_rate", False)
    funder_profile = form.cleaned_data.get("funder_profile")

    # Parse the grouping choice (legacy single-field mode)
    grouping_type, grouping_field = parse_grouping_choice(group_by_value)

    # If a funder profile is selected, it overrides the legacy group_by
    # (the form already tells users the legacy field is ignored).
    if funder_profile:
        grouping_type = "none"
        grouping_field = None

    # Find clients matching user's demo status enrolled in the selected program
    # Security: Demo users can only export demo clients; real users only real clients
    accessible_client_ids = get_client_queryset(request.user).values_list("pk", flat=True)
    client_ids = ClientProgramEnrolment.objects.filter(
        program=program, status="enrolled",
        client_file_id__in=accessible_client_ids,
    ).values_list("client_file_id", flat=True)

    # Build date-aware boundaries
    date_from_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, time.max))

    # Filter progress notes by effective date (backdate when present, else created_at)
    notes = ProgressNote.objects.filter(
        client_file_id__in=client_ids,
        status="default",
    ).filter(
        Q(backdate__range=(date_from_dt, date_to_dt))
        | Q(backdate__isnull=True, created_at__range=(date_from_dt, date_to_dt))
    )

    # Get the actual metric values
    metric_values = (
        MetricValue.objects.filter(
            metric_def__in=selected_metrics,
            progress_note_target__progress_note__in=notes,
        )
        .select_related(
            "metric_def",
            "progress_note_target__progress_note__client_file",
            "progress_note_target__progress_note__author",
        )
    )

    if not metric_values.exists():
        return render(
            request,
            "reports/export_form.html",
            {
                "form": form,
                "no_data": True,
                "is_aggregate_only": is_aggregate,
                "is_pm_export": is_pm_export,
            },
        )

    # Get grouping label for display
    grouping_label = _get_grouping_label(group_by_value, grouping_field)

    # Calculate achievement rates if requested (aggregate — safe for all roles)
    achievement_summary = None
    if include_achievement:
        achievement_summary = get_achievement_summary(
            program,
            date_from=date_from,
            date_to=date_to,
            metric_defs=list(selected_metrics),
            use_latest=True,
        )

    export_format = form.cleaned_data["format"]
    recipient = form.get_recipient_display()

    filters_dict = {
        "program": program.name,
        "metrics": [m.name for m in selected_metrics],
        "date_from": str(date_from),
        "date_to": str(date_to),
    }
    if grouping_type != "none":
        filters_dict["grouped_by"] = grouping_label

    # ── Aggregate-only path (executives) ─────────────────────────────
    # Executives see summary statistics only — no client record IDs,
    # no author names, no individual data points.
    # Permission reference: metric.view_individual = DENY,
    #                       metric.view_aggregate = ALLOW
    if is_aggregate:
        # Build per-metric aggregate stats using existing infrastructure
        agg_by_metric = aggregate_metrics(metric_values, group_by="metric")

        # Count unique clients per metric for the summary
        unique_clients = set()
        metric_client_sets = {}  # metric_def_id → set of client_ids
        for mv in metric_values:
            client_id = mv.progress_note_target.progress_note.client_file_id
            unique_clients.add(client_id)
            mid = mv.metric_def_id
            if mid not in metric_client_sets:
                metric_client_sets[mid] = set()
            metric_client_sets[mid].add(client_id)

        # Total data points for audit (sum of valid values across all metrics)
        total_data_points_count = sum(s.get("valid_count", 0) for s in agg_by_metric.values())

        # Build aggregate rows — one per metric, NO client identifiers
        aggregate_rows = []
        seen_metrics = set()
        for mv in metric_values:
            mid = mv.metric_def_id
            if mid in seen_metrics:
                continue
            seen_metrics.add(mid)
            stats = agg_by_metric.get(str(mid), {})
            avg_val = round(stats["avg"], 1) if stats.get("avg") is not None else "N/A"
            aggregate_rows.append({
                "metric_name": mv.metric_def.name,
                "clients_measured": suppress_small_cell(len(metric_client_sets.get(mid, set())), program),
                "data_points": suppress_small_cell(stats.get("valid_count", 0), program),
                "avg": avg_val,
                "min": stats.get("min", "N/A"),
                "max": stats.get("max", "N/A"),
            })

        # Build demographic breakdown if grouping is enabled
        demographic_aggregate_rows = []
        if grouping_type != "none":
            for mv_metric_def in selected_metrics:
                # Filter metric values for this specific metric
                metric_specific_mvs = metric_values.filter(metric_def=mv_metric_def)
                if not metric_specific_mvs.exists():
                    continue
                demo_agg = aggregate_by_demographic(
                    metric_specific_mvs, grouping_type, grouping_field, date_to,
                )
                for group_label, stats in demo_agg.items():
                    client_count = len(stats.get("client_ids", set()))
                    avg_val = round(stats["avg"], 1) if stats.get("avg") is not None else "N/A"
                    demographic_aggregate_rows.append({
                        "demographic_group": group_label,
                        "metric_name": mv_metric_def.name,
                        "clients_measured": suppress_small_cell(client_count, program),
                        "avg": avg_val,
                        "min": stats.get("min", "N/A"),
                        "max": stats.get("max", "N/A"),
                    })

        # ── Funder profile multi-breakdown (overrides legacy group_by) ──
        funder_breakdown_sections = []
        if funder_profile:
            breakdowns = DemographicBreakdown.objects.filter(
                funder_profile=funder_profile,
            ).select_related("custom_field").order_by("sort_order")

            for bd in breakdowns:
                section_rows = []
                for mv_metric_def in selected_metrics:
                    metric_specific_mvs = metric_values.filter(metric_def=mv_metric_def)
                    if not metric_specific_mvs.exists():
                        continue

                    if bd.source_type == "age":
                        custom_bins = bd.bins_json or None
                        demo_agg = aggregate_by_demographic(
                            metric_specific_mvs, "age_range", None, date_to,
                        )
                        # Re-aggregate with custom bins if provided
                        if custom_bins:
                            all_ids = set()
                            client_mv_map = defaultdict(list)
                            for mv in metric_specific_mvs:
                                cid = mv.progress_note_target.progress_note.client_file_id
                                all_ids.add(cid)
                                client_mv_map[cid].append(mv)
                            client_groups = group_clients_by_age(
                                list(all_ids), date_to, custom_bins=custom_bins,
                            )
                            demo_agg = {}
                            for gl, cids in client_groups.items():
                                gvals = []
                                for cid in cids:
                                    gvals.extend(client_mv_map.get(cid, []))
                                if gvals:
                                    s = _stats_from_list(gvals)
                                else:
                                    s = {"count": 0, "valid_count": 0, "avg": None, "min": None, "max": None, "sum": None}
                                s["client_ids"] = set(cids)
                                demo_agg[gl] = s
                    elif bd.source_type == "custom_field" and bd.custom_field:
                        demo_agg = aggregate_by_demographic(
                            metric_specific_mvs, "custom_field", bd.custom_field, date_to,
                        )
                        # Apply merge categories if provided
                        if bd.merge_categories_json:
                            all_ids = set()
                            client_mv_map = defaultdict(list)
                            for mv in metric_specific_mvs:
                                cid = mv.progress_note_target.progress_note.client_file_id
                                all_ids.add(cid)
                                client_mv_map[cid].append(mv)
                            client_groups = group_clients_by_custom_field(
                                list(all_ids), bd.custom_field,
                                merge_categories=bd.merge_categories_json,
                            )
                            demo_agg = {}
                            for gl, cids in client_groups.items():
                                gvals = []
                                for cid in cids:
                                    gvals.extend(client_mv_map.get(cid, []))
                                if gvals:
                                    s = _stats_from_list(gvals)
                                else:
                                    s = {"count": 0, "valid_count": 0, "avg": None, "min": None, "max": None, "sum": None}
                                s["client_ids"] = set(cids)
                                demo_agg[gl] = s
                    else:
                        continue

                    for group_label, stats in demo_agg.items():
                        client_count = len(stats.get("client_ids", set()))
                        avg_val = round(stats["avg"], 1) if stats.get("avg") is not None else "N/A"
                        section_rows.append({
                            "demographic_group": group_label,
                            "metric_name": mv_metric_def.name,
                            "clients_measured": suppress_small_cell(client_count, program),
                            "avg": avg_val,
                            "min": stats.get("min", "N/A"),
                            "max": stats.get("max", "N/A"),
                        })

                if section_rows:
                    funder_breakdown_sections.append({
                        "label": bd.label,
                        "rows": section_rows,
                    })

        total_clients_display = suppress_small_cell(len(unique_clients), program)

        if export_format == "pdf":
            from .pdf_views import generate_outcome_report_pdf
            pdf_response = generate_outcome_report_pdf(
                request, program, selected_metrics,
                date_from, date_to, [], unique_clients,
                grouping_type=grouping_type,
                grouping_label=grouping_label,
                achievement_summary=achievement_summary,
                total_clients_display=total_clients_display,
                total_data_points_display=suppress_small_cell(
                    sum(s.get("valid_count", 0) for s in agg_by_metric.values()), program,
                ),
                is_aggregate=True,
                aggregate_rows=aggregate_rows,
                demographic_aggregate_rows=demographic_aggregate_rows or None,
            )
            safe_name = sanitise_filename(program.name.replace(" ", "_"))
            filename = f"outcome_report_{safe_name}_{date_from}_{date_to}.pdf"
            content = pdf_response.content
        else:
            # Aggregate CSV — summary statistics only
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(sanitise_csv_row([f"# Program: {program.name}"]))
            writer.writerow(sanitise_csv_row([f"# Date Range: {date_from} to {date_to}"]))
            writer.writerow(sanitise_csv_row([f"# Total Participants: {total_clients_display}"]))
            writer.writerow(sanitise_csv_row(["# Export Mode: Aggregate Summary"]))
            if grouping_type != "none":
                writer.writerow(sanitise_csv_row([f"# Grouped By: {grouping_label}"]))

            # Achievement rate summary (same as individual path — already aggregate)
            if achievement_summary:
                _write_achievement_csv(writer, achievement_summary, program)

            writer.writerow([])  # blank separator

            # Aggregate data table — NO client record IDs, NO author names
            writer.writerow(sanitise_csv_row([
                "Metric Name", "Participants Measured", "Data Points", "Average", "Min", "Max",
            ]))
            for agg_row in aggregate_rows:
                writer.writerow(sanitise_csv_row([
                    agg_row["metric_name"],
                    agg_row["clients_measured"],
                    agg_row["data_points"],
                    agg_row["avg"],
                    agg_row["min"],
                    agg_row["max"],
                ]))

            # Demographic breakdown table
            if demographic_aggregate_rows:
                writer.writerow([])
                writer.writerow(sanitise_csv_row([f"# ===== BREAKDOWN BY {grouping_label.upper()} ====="]))
                writer.writerow(sanitise_csv_row([
                    grouping_label, "Metric Name", "Participants Measured", "Average", "Min", "Max",
                ]))
                for demo_row in demographic_aggregate_rows:
                    writer.writerow(sanitise_csv_row([
                        demo_row["demographic_group"],
                        demo_row["metric_name"],
                        demo_row["clients_measured"],
                        demo_row["avg"],
                        demo_row["min"],
                        demo_row["max"],
                    ]))

            # Funder profile multi-breakdown sections
            if funder_breakdown_sections:
                for section in funder_breakdown_sections:
                    writer.writerow([])
                    writer.writerow(sanitise_csv_row([f"# ===== {section['label'].upper()} ====="]))
                    writer.writerow(sanitise_csv_row([
                        section["label"], "Metric Name", "Participants Measured", "Average", "Min", "Max",
                    ]))
                    for demo_row in section["rows"]:
                        writer.writerow(sanitise_csv_row([
                            demo_row["demographic_group"],
                            demo_row["metric_name"],
                            demo_row["clients_measured"],
                            demo_row["avg"],
                            demo_row["min"],
                            demo_row["max"],
                        ]))

            safe_prog = sanitise_filename(program.name.replace(" ", "_"))
            filename = f"metric_export_{safe_prog}_{date_from}_{date_to}.csv"
            content = csv_buffer.getvalue()

        rows = []  # No individual rows for aggregate exports

    # ── Individual path (admin, PM) ──────────────────────────────────
    else:
        # Build demographic lookup for each client if grouping is enabled
        client_demographic_map = {}
        if grouping_type != "none":
            client_demographic_map = _build_demographic_map(
                metric_values, grouping_type, grouping_field, date_to
            )

        # Count unique clients in the result set
        unique_clients = set()
        rows = []
        for mv in metric_values:
            note = mv.progress_note_target.progress_note
            client = note.client_file
            unique_clients.add(client.pk)

            row = {
                "record_id": client.record_id,
                "metric_name": mv.metric_def.name,
                "value": mv.value,
                "date": note.effective_date.strftime("%Y-%m-%d"),
                "author": note.author.display_name,
            }

            # Add demographic group if grouping is enabled
            if grouping_type != "none":
                row["demographic_group"] = client_demographic_map.get(client.pk, "Unknown")

            rows.append(row)

        # Apply small-cell suppression for confidential programs
        total_clients_display = suppress_small_cell(len(unique_clients), program)
        total_data_points_display = suppress_small_cell(len(rows), program)

        if export_format == "pdf":
            from .pdf_views import generate_outcome_report_pdf
            pdf_response = generate_outcome_report_pdf(
                request, program, selected_metrics,
                date_from, date_to, rows, unique_clients,
                grouping_type=grouping_type,
                grouping_label=grouping_label,
                achievement_summary=achievement_summary,
                total_clients_display=total_clients_display,
                total_data_points_display=total_data_points_display,
            )
            safe_name = sanitise_filename(program.name.replace(" ", "_"))
            filename = f"outcome_report_{safe_name}_{date_from}_{date_to}.pdf"
            content = pdf_response.content
        else:
            # Build CSV in memory buffer (not directly into HttpResponse)
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            # Summary header rows (prefixed with # so spreadsheet apps treat them as comments)
            writer.writerow(sanitise_csv_row([f"# Program: {program.name}"]))
            writer.writerow(sanitise_csv_row([f"# Date Range: {date_from} to {date_to}"]))
            writer.writerow(sanitise_csv_row([f"# Total Clients: {total_clients_display}"]))
            writer.writerow(sanitise_csv_row([f"# Total Data Points: {total_data_points_display}"]))
            if grouping_type != "none":
                writer.writerow(sanitise_csv_row([f"# Grouped By: {grouping_label}"]))

            # Achievement rate summary if requested
            if achievement_summary:
                _write_achievement_csv(writer, achievement_summary, program)

            writer.writerow([])  # blank separator

            # Column headers — include demographic column if grouping enabled
            if grouping_type != "none":
                writer.writerow(sanitise_csv_row([grouping_label, "Client Record ID", "Metric Name", "Value", "Date", "Author"]))
            else:
                writer.writerow(sanitise_csv_row(["Client Record ID", "Metric Name", "Value", "Date", "Author"]))

            for row in rows:
                if grouping_type != "none":
                    writer.writerow(sanitise_csv_row([
                        row.get("demographic_group", "Unknown"),
                        row["record_id"],
                        row["metric_name"],
                        row["value"],
                        row["date"],
                        row["author"],
                    ]))
                else:
                    writer.writerow(sanitise_csv_row([
                        row["record_id"],
                        row["metric_name"],
                        row["value"],
                        row["date"],
                        row["author"],
                    ]))

            safe_prog = sanitise_filename(program.name.replace(" ", "_"))
            filename = f"metric_export_{safe_prog}_{date_from}_{date_to}.csv"
            content = csv_buffer.getvalue()

    # Save to file and create secure download link
    link = _save_export_and_create_link(
        request=request,
        content=content,
        filename=filename,
        export_type="metrics",
        client_count=len(unique_clients),
        includes_notes=False,
        recipient=recipient,
        filters_dict=filters_dict,
        contains_pii=not is_aggregate,
    )

    # Audit log with recipient tracking
    audit_metadata = {
        "program": program.name,
        "metrics": [m.name for m in selected_metrics],
        "date_from": str(date_from),
        "date_to": str(date_to),
        "total_clients": len(unique_clients),
        "total_data_points": total_data_points_count if is_aggregate else len(rows),
        "export_mode": "aggregate" if is_aggregate else "individual",
        "recipient": recipient,
        "secure_link_id": str(link.id),
    }
    if grouping_type != "none":
        audit_metadata["grouped_by"] = grouping_label
    if achievement_summary:
        audit_metadata["include_achievement_rate"] = True
        audit_metadata["achievement_rate"] = achievement_summary.get("overall_rate")

    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="metric_report",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata=audit_metadata,
    )

    download_url = request.build_absolute_uri(
        reverse("reports:download_export", args=[link.id])
    )
    download_path = reverse("reports:download_export", args=[link.id])
    return render(request, "reports/export_link_created.html", {
        "link": link,
        "download_url": download_url,
        "download_path": download_path,
        "program_name": program.name,
        "is_pdf": export_format == "pdf",
    })


def _get_client_or_403(request, client_id):
    """Return client if user has access via program roles, otherwise None.

    Delegates to the shared canonical implementation.
    """
    from apps.programs.access import get_client_or_403
    return get_client_or_403(request, client_id)


@login_required
@requires_permission("metric.view_individual")
def client_analysis(request, client_id):
    """Show progress charts for a client's metric data.

    Requires metric.view_individual permission — executives (DENY) cannot
    access individual metric charts. Staff and PMs see metrics for clinical
    purposes through this in-app view.
    """
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # Get user's accessible programs (respects CONF9 context switcher)
    from apps.programs.access import build_program_display_context, get_user_program_ids
    active_ids = getattr(request, "active_program_ids", None)
    user_program_ids = get_user_program_ids(request.user, active_ids)
    program_ctx = build_program_display_context(request.user, active_ids)

    # Get targets with metrics — filtered by user's accessible programs
    # PlanTarget doesn't have a direct program FK, so filter through plan_section.program
    targets = PlanTarget.objects.filter(
        client_file=client, status="default"
    ).filter(
        Q(plan_section__program_id__in=user_program_ids) | Q(plan_section__program__isnull=True)
    ).select_related("plan_section__program").prefetch_related("metrics")

    chart_data = []
    for target in targets:
        ptm_links = PlanTargetMetric.objects.filter(
            plan_target=target
        ).select_related("metric_def")

        # Get program info from the section for grouping
        section_program = target.plan_section.program if target.plan_section else None
        program_name = section_program.name if section_program else None
        program_colour = section_program.colour_hex if section_program else None

        for ptm in ptm_links:
            metric_def = ptm.metric_def
            # Get all recorded values for this metric on this target
            values = MetricValue.objects.filter(
                metric_def=metric_def,
                progress_note_target__plan_target=target,
                progress_note_target__progress_note__client_file=client,
                progress_note_target__progress_note__status="default",
            ).select_related(
                "progress_note_target__progress_note"
            ).order_by(
                "progress_note_target__progress_note__created_at"
            )

            if not values:
                continue

            data_points = []
            for mv in values:
                note = mv.progress_note_target.progress_note
                date = note.effective_date.strftime("%Y-%m-%d")
                try:
                    numeric_val = float(mv.value)
                except (ValueError, TypeError):
                    continue
                data_points.append({"date": date, "value": numeric_val})

            if data_points:
                chart_data.append({
                    "target_name": target.name,
                    "metric_name": metric_def.name,
                    "unit": metric_def.unit or "",
                    "min_value": metric_def.min_value,
                    "max_value": metric_def.max_value,
                    "data_points": data_points,
                    "program_name": program_name,
                    "program_colour": program_colour,
                })

    # Sort by program_name for template {% regroup %} tag
    chart_data.sort(key=lambda c: (c["program_name"] or "", c["target_name"]))

    context = {
        "client": client,
        "chart_data": chart_data,
        "active_tab": "analysis",
        "user_role": getattr(request, "user_program_role", None),
        "show_grouping": program_ctx["show_grouping"],
        "show_program_ui": program_ctx["show_program_ui"],
    }
    if request.headers.get("HX-Request"):
        return render(request, "reports/_tab_analysis.html", context)
    return render(request, "reports/analysis.html", context)


@login_required
@requires_permission("report.funder_report", allow_admin=True)
def funder_report_form(request):
    """
    Funder report export — aggregate program outcome report.

    GET  — display the funder report form.
    POST — generate and return the formatted report.

    Access: admin (any program), program_manager or executive (their programs).
    Enforced by @requires_permission("report.funder_report").

    Reports include:
    - Organisation and program information
    - Service statistics (individuals served, contacts)
    - Age demographics
    - Outcome achievement rates
    """
    if request.method != "POST":
        form = FunderReportForm(user=request.user)
        return render(request, "reports/funder_report_form.html", {"form": form})

    form = FunderReportForm(request.POST, user=request.user)
    if not form.is_valid():
        return render(request, "reports/funder_report_form.html", {"form": form})

    program = form.cleaned_data["program"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    fiscal_year_label = form.cleaned_data["fiscal_year_label"]
    export_format = form.cleaned_data["format"]
    funder_profile = form.cleaned_data.get("funder_profile")

    # Generate report data
    # Security: Pass user for demo/real filtering
    report_data = generate_funder_report_data(
        program,
        date_from=date_from,
        date_to=date_to,
        fiscal_year_label=fiscal_year_label,
        user=request.user,
        funder_profile=funder_profile,
    )

    # Capture raw integer count before suppression — needed for
    # client_count (PositiveIntegerField) and is_elevated check.
    raw_client_count = report_data.get("total_individuals_served", 0)

    # Apply small-cell suppression for confidential programs
    report_data["total_individuals_served"] = suppress_small_cell(
        report_data["total_individuals_served"], program,
    )
    report_data["new_clients_this_period"] = suppress_small_cell(
        report_data["new_clients_this_period"], program,
    )
    # Suppress age demographic counts individually
    if program.is_confidential and "age_demographics" in report_data:
        for age_group, count in report_data["age_demographics"].items():
            if isinstance(count, int):
                report_data["age_demographics"][age_group] = suppress_small_cell(count, program)

    # Suppress custom demographic section counts for confidential programs.
    # Without this, funder profile breakdowns (e.g. Gender Identity) could
    # leak small-cell counts that enable re-identification — a PIPEDA issue.
    if program.is_confidential and "custom_demographic_sections" in report_data:
        for section in report_data["custom_demographic_sections"]:
            any_suppressed = False
            for cat_label, count in section["data"].items():
                if isinstance(count, int):
                    suppressed = suppress_small_cell(count, program)
                    if suppressed != count:
                        any_suppressed = True
                    section["data"][cat_label] = suppressed
            # If any cell was suppressed, suppress the total too —
            # otherwise total minus visible sum reveals the suppressed aggregate.
            if any_suppressed:
                section["total"] = "suppressed"

    recipient = form.get_recipient_display()
    safe_name = sanitise_filename(program.name.replace(" ", "_"))
    safe_fy = sanitise_filename(fiscal_year_label.replace(" ", "_"))

    if export_format == "pdf":
        from .pdf_views import generate_funder_report_pdf
        pdf_response = generate_funder_report_pdf(request, report_data)
        filename = f"Funder_Report_{safe_name}_{safe_fy}.pdf"
        content = pdf_response.content
    else:
        # Build CSV in memory buffer
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        csv_rows = generate_funder_report_csv_rows(report_data)
        for row in csv_rows:
            writer.writerow(sanitise_csv_row(row))
        filename = f"Funder_Report_{safe_name}_{safe_fy}.csv"
        content = csv_buffer.getvalue()

    # Save to file and create secure download link
    # Funder reports are always aggregate — no individual client data
    link = _save_export_and_create_link(
        request=request,
        content=content,
        filename=filename,
        export_type="funder_report",
        client_count=raw_client_count,
        includes_notes=False,
        recipient=recipient,
        filters_dict={
            "program": program.name,
            "fiscal_year": fiscal_year_label,
            "date_from": str(date_from),
            "date_to": str(date_to),
        },
        contains_pii=False,
    )

    # Audit log with recipient tracking
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="funder_report",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "program": program.name,
            "fiscal_year": fiscal_year_label,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "format": export_format,
            "total_individuals_served": report_data["total_individuals_served"],
            "recipient": recipient,
            "secure_link_id": str(link.id),
            "funder_profile": funder_profile.name if funder_profile else None,
        },
    )

    download_url = request.build_absolute_uri(
        reverse("reports:download_export", args=[link.id])
    )
    download_path = reverse("reports:download_export", args=[link.id])
    return render(request, "reports/export_link_created.html", {
        "link": link,
        "download_url": download_url,
        "download_path": download_path,
        "program_name": program.name,
        "is_pdf": export_format == "pdf",
    })



# ─── Secure link views ──────────────────────────────────────────────


@login_required
def download_export(request, link_id):
    """
    Serve an export file if the secure link is still valid.

    The export creator can download their own link. Admins can download
    any link (for oversight).
    Every download is logged with who actually downloaded the file.

    Defense-in-depth: exports containing PII (individual client data) require
    admin or PM access at download time, even if the creator originally had
    permission. This guards against role changes between creation and download.
    """
    link = get_object_or_404(SecureExportLink, id=link_id)

    # Permission: creator can download their own export, admin can download any
    can_download = (request.user == link.created_by) or request.user.is_admin
    if not can_download:
        return HttpResponseForbidden("You do not have permission to download this export.")

    # Defense-in-depth: re-validate PII access at download time.
    # Only admins and PMs may download exports containing individual client
    # data. This catches: (1) legacy links, (2) role demotions between
    # export creation and download.
    if link.contains_pii and not can_download_pii_export(request.user):
        logger.warning(
            "Blocked non-PM/non-admin download of PII export link=%s user=%s",
            link.id, request.user.pk,
        )
        return HttpResponseForbidden(
            "This export contains individual client data. "
            "Only program managers and administrators can download it."
        )

    # Check link validity (revoked / expired)
    if not link.is_valid():
        reason = "revoked" if link.revoked else "expired"
        return render(request, "reports/export_link_expired.html", {
            "reason": reason,
        })

    # Elevated exports have a delay before download is available
    if link.is_elevated and not link.is_available:
        return render(request, "reports/export_link_pending.html", {
            "link": link,
            "available_at": link.available_at,
        })

    # Check file exists separately (Railway ephemeral storage may lose files)
    if not link.file_exists:
        return render(request, "reports/export_link_expired.html", {
            "reason": "missing",
        })

    # Path traversal defence — verify file is within SECURE_EXPORT_DIR
    real_path = os.path.realpath(link.file_path)
    real_export_dir = os.path.realpath(settings.SECURE_EXPORT_DIR)
    if not real_path.startswith(real_export_dir + os.sep):
        return HttpResponseForbidden("Invalid file path.")

    # Atomic update to prevent race condition on download_count
    updated = SecureExportLink.objects.filter(pk=link.pk).update(
        download_count=F("download_count") + 1,
        last_downloaded_at=timezone.now(),
        last_downloaded_by=request.user,
    )

    # Audit log the download (separate from creation audit)
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="export_download",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "link_id": str(link.id),
            "created_by": link.created_by.display_name,
            "export_type": link.export_type,
            "client_count": link.client_count,
        },
    )

    # Serve file — FileResponse handles proper streaming and cleanup
    response = FileResponse(
        open(link.file_path, "rb"),
        as_attachment=True,
        filename=link.filename,
    )
    return response


@login_required
@admin_required
def manage_export_links(request):
    """
    Admin view: list all active and recent secure export links.

    Shows link status, download counts, and revocation controls.
    """

    # Show active links + recently expired (last 7 days)
    cutoff = timezone.now() - timedelta(days=7)
    links = SecureExportLink.objects.filter(
        created_at__gte=cutoff,
    ).select_related("created_by", "last_downloaded_by", "revoked_by")

    # Identify pending elevated exports (still in delay window, not revoked/expired)
    pending_elevated = [
        link for link in links
        if link.is_elevated and not link.revoked
        and not link.is_available
        and link.is_valid()
    ]

    return render(request, "reports/manage_export_links.html", {
        "links": links,
        "pending_elevated": pending_elevated,
    })


@login_required
@admin_required
def revoke_export_link(request, link_id):
    """
    Admin action: revoke a secure export link so it can no longer be downloaded.

    POST only. Uses Post/Redirect/Get to avoid resubmit-on-refresh.
    After revocation, the file is also deleted from disk.
    """
    from django.contrib import messages
    from django.http import HttpResponseNotAllowed
    from django.shortcuts import redirect
    from django.utils.translation import gettext as _

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    link = get_object_or_404(SecureExportLink, id=link_id)

    if link.revoked:
        messages.info(request, _("This link was already revoked."))
        return redirect("reports:manage_export_links")

    # Revoke the link
    link.revoked = True
    link.revoked_by = request.user
    link.revoked_at = timezone.now()
    link.save(update_fields=["revoked", "revoked_by", "revoked_at"])

    # Delete the file from disk
    if link.file_path and os.path.exists(link.file_path):
        try:
            os.remove(link.file_path)
        except OSError:
            pass  # File gone is acceptable — link is already revoked

    # Audit log the revocation
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="update",
        resource_type="export_link_revoked",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "link_id": str(link.id),
            "created_by": link.created_by.display_name,
            "export_type": link.export_type,
            "client_count": link.client_count,
        },
    )

    messages.success(request, _("Export link revoked successfully."))
    return redirect("reports:manage_export_links")
