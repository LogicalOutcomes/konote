"""Report views — aggregate metric CSV export, report template report, client analysis charts, and secure links."""
import csv
import datetime as dt
import io
import json
import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import DateTimeField, F, Q
from django.db.models.functions import Coalesce
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

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
from .models import DemographicBreakdown, ReportTemplate, SecureExportLink
from .suppression import suppress_small_cell
from .forms import FunderReportForm, MetricExportForm, TemplateExportForm, build_period_choices
from .aggregations import aggregate_metrics, _stats_from_list
from .utils import (
    can_create_export,
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
    # Use configured notification recipients, falling back to all active admins
    admin_emails = list(getattr(settings, "EXPORT_NOTIFICATION_EMAILS", []))
    if not admin_emails:
        admins = User.objects.filter(is_admin=True, is_active=True)
        admin_emails = [u.email for u in admins if u.email]
    if not admin_emails:
        logger.warning("No email addresses found for elevated export notification (link %s)", link.id)
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
                client_demographic_map[cv.client_file_id] = _("Unknown")
            else:
                display_value = option_labels.get(raw_value, raw_value)
                client_demographic_map[cv.client_file_id] = display_value

        # Mark clients without a value as Unknown
        for client_id in client_ids:
            if client_id not in client_demographic_map:
                client_demographic_map[client_id] = _("Unknown")

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
        return _("Age Range")

    if grouping_field:
        return grouping_field.name

    return _("Demographic Group")


def _write_achievement_csv(writer, achievement_summary, program, *,
                           is_confidential=None):
    """Write the achievement rate summary section to a CSV writer.

    Used by both aggregate and individual export paths. The achievement
    data is already aggregate (counts and percentages) so it's safe for
    all roles.

    Args:
        is_confidential: Optional bool override for All Programs mode
            where program is None but confidential suppression is needed.
    """
    writer.writerow([])  # blank separator
    writer.writerow(sanitise_csv_row([_("# ===== ACHIEVEMENT RATE SUMMARY =====")]))
    ach_total = suppress_small_cell(achievement_summary["total_clients"], program, is_confidential=is_confidential)
    ach_met = suppress_small_cell(achievement_summary["clients_met_any_target"], program, is_confidential=is_confidential)
    if isinstance(ach_total, str) or isinstance(ach_met, str):
        writer.writerow(sanitise_csv_row([
            _("# Overall: %(met)s of %(total)s clients met at least one target")
            % {"met": ach_met, "total": ach_total}
        ]))
    elif achievement_summary["total_clients"] > 0:
        writer.writerow(sanitise_csv_row([
            _("# Overall: %(met)s of %(total)s clients (%(rate)s%%) met at least one target")
            % {"met": ach_met, "total": ach_total, "rate": achievement_summary['overall_rate']}
        ]))
    else:
        writer.writerow(sanitise_csv_row([_("# No client data available for achievement calculation")]))

    for metric in achievement_summary.get("by_metric", []):
        m_total = suppress_small_cell(metric["total_clients"], program, is_confidential=is_confidential)
        m_met = suppress_small_cell(metric.get("clients_met_target", 0), program, is_confidential=is_confidential)
        if metric["has_target"]:
            if isinstance(m_total, str) or isinstance(m_met, str):
                writer.writerow(sanitise_csv_row([
                    _("# %(name)s: %(met)s of %(total)s clients met target of %(target)s")
                    % {"name": metric['metric_name'], "met": m_met, "total": m_total, "target": metric['target_value']}
                ]))
            else:
                writer.writerow(sanitise_csv_row([
                    _("# %(name)s: %(met)s of %(total)s clients (%(rate)s%%) met target of %(target)s")
                    % {"name": metric['metric_name'], "met": m_met, "total": m_total,
                       "rate": metric['achievement_rate'], "target": metric['target_value']}
                ]))
        else:
            writer.writerow(sanitise_csv_row([
                _("# %(name)s: %(total)s clients (no target defined)")
                % {"name": metric['metric_name'], "total": m_total}
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

    def _template_previews(bound_form):
        if "report_template" not in bound_form.fields:
            return ReportTemplate.objects.none()
        return (
            bound_form.fields["report_template"].queryset
            .prefetch_related("breakdowns__custom_field")
            .order_by("name")
        )

    # Show admin hint when templates exist but none are linked to programs
    show_template_hint = (
        request.user.is_admin
        and ReportTemplate.objects.exists()
    )

    delay_minutes = getattr(settings, "ELEVATED_EXPORT_DELAY_MINUTES", 10)

    if request.method != "POST":
        form = MetricExportForm(user=request.user)
        # Only show hint if the dropdown is actually hidden
        hint = show_template_hint and "report_template" not in form.fields
        return render(request, "reports/export_form.html", {
            "form": form,
            "is_aggregate_only": is_aggregate,
            "is_pm_export": is_pm_export,
            "delay_minutes": delay_minutes,
            "template_preview_items": _template_previews(form),
            "show_template_hint": hint,
            "consortium_locked_metrics": form.consortium_locked_metrics,
            "consortium_locked_metric_strings": {str(m) for m in form.consortium_locked_metrics},
            "consortium_partner_name": form.consortium_partner_name,
        })

    # If preview=1 is set, delegate to the preview view
    if request.POST.get("preview") == "1":
        from .preview_views import adhoc_report_preview
        return adhoc_report_preview(request)

    form = MetricExportForm(request.POST, user=request.user)
    if not form.is_valid():
        hint = show_template_hint and "report_template" not in form.fields
        return render(request, "reports/export_form.html", {
            "form": form,
            "is_aggregate_only": is_aggregate,
            "is_pm_export": is_pm_export,
            "delay_minutes": delay_minutes,
            "template_preview_items": _template_previews(form),
            "show_template_hint": hint,
            "consortium_locked_metrics": form.consortium_locked_metrics,
            "consortium_locked_metric_strings": {str(m) for m in form.consortium_locked_metrics},
            "consortium_partner_name": form.consortium_partner_name,
        })

    program = form.cleaned_data["program"]
    all_programs_mode = form.is_all_programs  # True when user selected "All Programs"

    if all_programs_mode:
        # "All Programs" — verify user has general export permission
        if not can_create_export(request.user, "metrics"):
            return HttpResponseForbidden("You do not have permission to export data.")
        # Force aggregate-only for cross-program exports (privacy safeguard)
        is_aggregate = True
        is_pm_export = False
    else:
        if not can_create_export(request.user, "metrics", program=program):
            return HttpResponseForbidden("You do not have permission to export data for this program.")

    # Display label for the program in exports
    program_display_name = (
        _("All Programs \u2014 Organisation Summary") if all_programs_mode
        else program.name
    )

    selected_metrics = form.cleaned_data["metrics"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    group_by_value = form.cleaned_data.get("group_by", "")
    include_achievement = form.cleaned_data.get("include_achievement_rate", False)
    report_template = form.cleaned_data.get("report_template")

    # Parse the grouping choice (legacy single-field mode)
    grouping_type, grouping_field = parse_grouping_choice(group_by_value)

    # If a report template is selected, it overrides the legacy group_by
    # (the form already tells users the legacy field is ignored).
    if report_template:
        grouping_type = "none"
        grouping_field = None

    # Find clients matching user's demo status enrolled in accessible programs
    # Security: Demo users can only export demo clients; real users only real clients
    accessible_client_ids = get_client_queryset(request.user).values_list("pk", flat=True)
    if all_programs_mode:
        # All programs the user has access to
        accessible_programs = get_manageable_programs(request.user)
        _has_confidential_program = accessible_programs.filter(is_confidential=True).exists()
        client_ids = ClientProgramEnrolment.objects.filter(
            program__in=accessible_programs, status="enrolled",
            client_file_id__in=accessible_client_ids,
        ).values_list("client_file_id", flat=True).distinct()
    else:
        _has_confidential_program = program.is_confidential
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
            "progress_note_target__plan_target",
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
                "delay_minutes": delay_minutes,
            },
        )

    # Get grouping label for display
    grouping_label = _get_grouping_label(group_by_value, grouping_field)

    # Calculate achievement rates if requested (aggregate — safe for all roles)
    achievement_summary = None
    if include_achievement:
        if all_programs_mode:
            # Aggregate achievement across all accessible programs
            from .achievements import merge_achievement_summaries
            summaries = []
            for ap in accessible_programs:
                s = get_achievement_summary(
                    ap, date_from=date_from, date_to=date_to,
                    metric_defs=list(selected_metrics), use_latest=True,
                )
                if s:
                    summaries.append(s)
            achievement_summary = merge_achievement_summaries(summaries) if summaries else None
        else:
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
        "program": str(program_display_name),
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
                "clients_measured": suppress_small_cell(len(metric_client_sets.get(mid, set())), program, is_confidential=_has_confidential_program),
                "data_points": suppress_small_cell(stats.get("valid_count", 0), program, is_confidential=_has_confidential_program),
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
                        "clients_measured": suppress_small_cell(client_count, program, is_confidential=_has_confidential_program),
                        "avg": avg_val,
                        "min": stats.get("min", "N/A"),
                        "max": stats.get("max", "N/A"),
                    })

        # ── Report template multi-breakdown (overrides legacy group_by) ──
        report_template_breakdown_sections = []
        if report_template:
            breakdowns = DemographicBreakdown.objects.filter(
                report_template=report_template,
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
                            "clients_measured": suppress_small_cell(client_count, program, is_confidential=_has_confidential_program),
                            "avg": avg_val,
                            "min": stats.get("min", "N/A"),
                            "max": stats.get("max", "N/A"),
                        })

                if section_rows:
                    report_template_breakdown_sections.append({
                        "label": bd.label,
                        "rows": section_rows,
                    })

        total_clients_display = suppress_small_cell(len(unique_clients), program, is_confidential=_has_confidential_program)

        safe_display = sanitise_filename(str(program_display_name).replace(" ", "_"))

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
                    is_confidential=_has_confidential_program,
                ),
                is_aggregate=True,
                aggregate_rows=aggregate_rows,
                demographic_aggregate_rows=demographic_aggregate_rows or None,
                program_display_name=str(program_display_name),
            )
            filename = f"outcome_report_{safe_display}_{date_from}_{date_to}.pdf"
            content = pdf_response.content
        else:
            # Aggregate CSV — summary statistics only
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(sanitise_csv_row([f"# Program: {program_display_name}"]))
            writer.writerow(sanitise_csv_row([f"# Date Range: {date_from} to {date_to}"]))
            writer.writerow(sanitise_csv_row([f"# Total Participants: {total_clients_display}"]))
            writer.writerow(sanitise_csv_row([_("# Export Mode: Aggregate Summary")]))
            if all_programs_mode:
                writer.writerow(sanitise_csv_row([
                    _("# Note: Participants enrolled in multiple programs are counted once per program.")
                ]))
            if grouping_type != "none":
                writer.writerow(sanitise_csv_row([_("# Grouped By: %(label)s") % {"label": grouping_label}]))

            # Achievement rate summary (same as individual path — already aggregate)
            if achievement_summary:
                _write_achievement_csv(writer, achievement_summary, program, is_confidential=_has_confidential_program)

            writer.writerow([])  # blank separator

            # Aggregate data table — NO client record IDs, NO author names
            writer.writerow(sanitise_csv_row([
                _("Metric Name"), _("Participants Measured"), _("Data Points"), _("Average"), _("Min"), _("Max"),
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
                writer.writerow(sanitise_csv_row([_("# ===== BREAKDOWN BY %(label)s =====") % {"label": grouping_label.upper()}]))
                writer.writerow(sanitise_csv_row([
                    grouping_label, _("Metric Name"), _("Participants Measured"), _("Average"), _("Min"), _("Max"),
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

            # Report template multi-breakdown sections
            if report_template_breakdown_sections:
                for section in report_template_breakdown_sections:
                    writer.writerow([])
                    writer.writerow(sanitise_csv_row([_("# ===== %(label)s =====") % {"label": section['label'].upper()}]))
                    writer.writerow(sanitise_csv_row([
                        section["label"], _("Metric Name"), _("Participants Measured"), _("Average"), _("Min"), _("Max"),
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

            filename = f"metric_export_{safe_display}_{date_from}_{date_to}.csv"
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

            # Get goal name from the plan target (encrypted, decrypted via property)
            plan_target = mv.progress_note_target.plan_target
            goal_name = plan_target.name if plan_target else ""

            row = {
                "record_id": client.record_id,
                "goal_name": goal_name,
                "metric_name": mv.metric_def.name,
                "value": mv.value,
                "date": note.effective_date.strftime("%Y-%m-%d"),
                "author": note.author.display_name,
            }

            # Add demographic group if grouping is enabled
            if grouping_type != "none":
                row["demographic_group"] = client_demographic_map.get(client.pk, _("Unknown"))

            rows.append(row)

        # Apply small-cell suppression for confidential programs
        total_clients_display = suppress_small_cell(len(unique_clients), program, is_confidential=_has_confidential_program)
        total_data_points_display = suppress_small_cell(len(rows), program, is_confidential=_has_confidential_program)

        safe_display_indiv = sanitise_filename(str(program_display_name).replace(" ", "_"))

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
                program_display_name=str(program_display_name),
            )
            filename = f"outcome_report_{safe_display_indiv}_{date_from}_{date_to}.pdf"
            content = pdf_response.content
        else:
            # Build CSV in memory buffer (not directly into HttpResponse)
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            # Summary header rows (prefixed with # so spreadsheet apps treat them as comments)
            writer.writerow(sanitise_csv_row([f"# Program: {program_display_name}"]))
            writer.writerow(sanitise_csv_row([f"# Date Range: {date_from} to {date_to}"]))
            writer.writerow(sanitise_csv_row([f"# Total Clients: {total_clients_display}"]))
            writer.writerow(sanitise_csv_row([f"# Total Data Points: {total_data_points_display}"]))
            if grouping_type != "none":
                writer.writerow(sanitise_csv_row([_("# Grouped By: %(label)s") % {"label": grouping_label}]))

            # Achievement rate summary if requested
            if achievement_summary:
                _write_achievement_csv(writer, achievement_summary, program, is_confidential=_has_confidential_program)

            writer.writerow([])  # blank separator

            # Column headers — include demographic column if grouping enabled
            if grouping_type != "none":
                writer.writerow(sanitise_csv_row([grouping_label, _("Client Record ID"), _("Goal"), _("Metric Name"), _("Value"), _("Date"), _("Author")]))
            else:
                writer.writerow(sanitise_csv_row([_("Client Record ID"), _("Goal"), _("Metric Name"), _("Value"), _("Date"), _("Author")]))

            for row in rows:
                if grouping_type != "none":
                    writer.writerow(sanitise_csv_row([
                        row.get("demographic_group", _("Unknown")),
                        row["record_id"],
                        row.get("goal_name", ""),
                        row["metric_name"],
                        row["value"],
                        row["date"],
                        row["author"],
                    ]))
                else:
                    writer.writerow(sanitise_csv_row([
                        row["record_id"],
                        row.get("goal_name", ""),
                        row["metric_name"],
                        row["value"],
                        row["date"],
                        row["author"],
                    ]))

            filename = f"metric_export_{safe_display_indiv}_{date_from}_{date_to}.csv"
            content = csv_buffer.getvalue()

    # Save to file and create secure download link
    try:
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
    except Exception:
        logger.exception("Failed to save metric export file")
        from django.contrib import messages
        messages.error(request, "Something went wrong saving the export. Please try again or contact support.")
        return render(request, "reports/export_form.html", {
            "form": form,
            "export_error": True,
            "is_aggregate_only": is_aggregate,
            "is_pm_export": is_pm_export,
            "delay_minutes": delay_minutes,
        })

    # Audit log with recipient tracking
    audit_metadata = {
        "program": str(program_display_name),
        "all_programs": all_programs_mode,
        "metrics": [m.name for m in selected_metrics],
        "date_from": str(date_from),
        "date_to": str(date_to),
        "total_clients": (
            "suppressed" if _has_confidential_program else len(unique_clients)
        ),
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
        "program_name": str(program_display_name),
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

    # Date range filter — parse query parameters
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    timeframe = request.GET.get("timeframe", "")
    date_from_obj = None
    date_to_obj = None

    # Quick-select timeframes override manual date inputs
    if timeframe == "30d":
        date_from_obj = timezone.now().date() - timedelta(days=30)
    elif timeframe == "3m":
        date_from_obj = timezone.now().date() - timedelta(days=90)
    elif timeframe == "6m":
        date_from_obj = timezone.now().date() - timedelta(days=180)
    elif timeframe == "all":
        pass  # No filtering — show all data
    else:
        # Manual date inputs
        if date_from:
            try:
                date_from_obj = dt.date.fromisoformat(date_from)
            except ValueError:
                pass
        if date_to:
            try:
                date_to_obj = dt.date.fromisoformat(date_to)
            except ValueError:
                pass

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
            # Get recorded values for this metric on this target
            values_qs = MetricValue.objects.filter(
                metric_def=metric_def,
                progress_note_target__plan_target=target,
                progress_note_target__progress_note__client_file=client,
                progress_note_target__progress_note__status="default",
            )

            # Apply date range filter using the note's effective date
            # (Coalesce of backdate and created_at)
            if date_from_obj or date_to_obj:
                values_qs = values_qs.annotate(
                    _note_effective=Coalesce(
                        "progress_note_target__progress_note__backdate",
                        "progress_note_target__progress_note__created_at",
                        output_field=DateTimeField(),
                    )
                )
            if date_from_obj:
                values_qs = values_qs.filter(_note_effective__date__gte=date_from_obj)
            if date_to_obj:
                values_qs = values_qs.filter(_note_effective__date__lte=date_to_obj)

            values = values_qs.select_related(
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
                    "metric_name": metric_def.translated_name,
                    "unit": metric_def.translated_unit or "",
                    "min_value": metric_def.min_value,
                    "max_value": metric_def.max_value,
                    "data_points": data_points,
                    "program_name": program_name,
                    "program_colour": program_colour,
                })

    # Sort by program_name for template {% regroup %} tag
    chart_data.sort(key=lambda c: (c["program_name"] or "", c["target_name"]))

    # Compute active date filter values for the template
    if timeframe in ("30d", "3m", "6m"):
        filter_date_from = date_from_obj.isoformat() if date_from_obj else ""
    else:
        filter_date_from = date_from
    filter_date_to = date_to

    context = {
        "client": client,
        "chart_data": chart_data,
        "active_tab": "analysis",
        "user_role": getattr(request, "user_program_role", None),
        "show_grouping": program_ctx["show_grouping"],
        "show_program_ui": program_ctx["show_program_ui"],
        "filter_date_from": filter_date_from,
        "filter_date_to": filter_date_to,
        "filter_timeframe": timeframe,
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
    def _template_preview_items(bound_form):
        if "report_template" not in bound_form.fields:
            return ReportTemplate.objects.none()
        return (
            bound_form.fields["report_template"].queryset
            .prefetch_related("breakdowns__custom_field", "report_metrics__metric_definition")
            .order_by("name")
        )

    # Show admin hint when templates exist but none are linked to programs
    show_template_hint = (
        request.user.is_admin
        and ReportTemplate.objects.exists()
    )

    if request.method != "POST":
        form = FunderReportForm(user=request.user)
        hint = show_template_hint and "report_template" not in form.fields
        return render(
            request,
            "reports/funder_report_form.html",
            {
                "form": form,
                "template_preview_items": _template_preview_items(form),
                "show_template_hint": hint,
            },
        )

    form = FunderReportForm(request.POST, user=request.user)
    if not form.is_valid():
        hint = show_template_hint and "report_template" not in form.fields
        return render(
            request,
            "reports/funder_report_form.html",
            {
                "form": form,
                "template_preview_items": _template_preview_items(form),
                "show_template_hint": hint,
            },
        )

    program = form.cleaned_data["program"]
    all_programs_mode = form.is_all_programs

    if all_programs_mode:
        if not can_create_export(request.user, "funder_report"):
            return HttpResponseForbidden("You do not have permission to export data.")
    else:
        if not can_create_export(request.user, "funder_report", program=program):
            return HttpResponseForbidden("You do not have permission to export data for this program.")

    program_display_name = (
        _("All Programs \u2014 Organisation Summary") if all_programs_mode
        else program.name
    )

    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    fiscal_year_label = form.cleaned_data["fiscal_year_label"]
    export_format = form.cleaned_data["format"]
    report_template = form.cleaned_data.get("report_template")

    if all_programs_mode:
        # Generate per-program reports and merge into a combined CSV
        accessible_programs = get_manageable_programs(request.user)
        all_report_sections = []
        total_raw_client_count = 0
        for ap in accessible_programs:
            rd = generate_funder_report_data(
                ap, date_from=date_from, date_to=date_to,
                fiscal_year_label=fiscal_year_label,
                user=request.user, report_template=report_template,
            )
            total_raw_client_count += rd.get("total_individuals_served", 0)
            # Suppression per-program
            if ap.is_confidential:
                rd["total_individuals_served"] = suppress_small_cell(
                    rd["total_individuals_served"], ap,
                )
                rd["new_clients_this_period"] = suppress_small_cell(
                    rd["new_clients_this_period"], ap,
                )
            all_report_sections.append((ap, rd))
        raw_client_count = total_raw_client_count
    else:
        # Generate report data for single program
        # Security: Pass user for demo/real filtering
        report_data = generate_funder_report_data(
            program,
            date_from=date_from,
            date_to=date_to,
            fiscal_year_label=fiscal_year_label,
            user=request.user,
            report_template=report_template,
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
        # Without this, reporting-template breakdowns (e.g. Gender Identity) could
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
    safe_name = sanitise_filename(str(program_display_name).replace(" ", "_"))
    safe_fy = sanitise_filename(fiscal_year_label.replace(" ", "_"))

    try:
        if all_programs_mode:
            # Build combined CSV with one section per program
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(sanitise_csv_row([
                f"# All Programs \u2014 Organisation Summary"
            ]))
            writer.writerow(sanitise_csv_row([f"# Fiscal Year: {fiscal_year_label}"]))
            writer.writerow(sanitise_csv_row([
                f"# Date Range: {date_from} to {date_to}"
            ]))
            writer.writerow([])
            for ap, rd in all_report_sections:
                writer.writerow(sanitise_csv_row([
                    f"# ===== {ap.name} ====="
                ]))
                csv_rows = generate_funder_report_csv_rows(rd)
                for row in csv_rows:
                    writer.writerow(sanitise_csv_row(row))
                writer.writerow([])  # blank separator between programs
            filename = f"Reporting_Template_Report_{safe_name}_{safe_fy}.csv"
            content = csv_buffer.getvalue()
        elif export_format == "pdf":
            from .pdf_views import generate_funder_report_pdf
            pdf_response = generate_funder_report_pdf(request, report_data)
            filename = f"Reporting_Template_Report_{safe_name}_{safe_fy}.pdf"
            content = pdf_response.content
        else:
            # Build CSV in memory buffer
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            csv_rows = generate_funder_report_csv_rows(report_data)
            for row in csv_rows:
                writer.writerow(sanitise_csv_row(row))
            filename = f"Reporting_Template_Report_{safe_name}_{safe_fy}.csv"
            content = csv_buffer.getvalue()
    except Exception:
        logger.exception("Failed to generate funder report export")
        from django.contrib import messages
        messages.error(request, "Something went wrong generating the report. Please try again or contact support.")
        return render(request, "reports/funder_report_form.html", {
            "form": form,
            "export_error": True,
        })

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
            "program": str(program_display_name),
            "all_programs": all_programs_mode,
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
            "program": str(program_display_name),
            "all_programs": all_programs_mode,
            "fiscal_year": fiscal_year_label,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "format": export_format,
            "total_individuals_served": (
                raw_client_count if all_programs_mode
                else report_data["total_individuals_served"]
            ),
            "recipient": recipient,
            "secure_link_id": str(link.id),
            "report_template": report_template.name if report_template else None,
            "partner": report_template.partner.name if report_template and report_template.partner else None,
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
        "program_name": str(program_display_name),
        "is_pdf": export_format == "pdf",
    })



# ─── Template-driven report generation (DRR: reporting-architecture.md) ─────


@login_required
@requires_permission("report.funder_report", allow_admin=True)
def generate_report_form(request):
    """
    Template-driven report generation.

    GET  — display the form with template dropdown.
    POST — validate, generate report, create secure download link.

    Access: admin, program_manager, executive (their programmes).
    Enforced by @requires_permission("report.funder_report").
    """
    from apps.auth_app.decorators import _get_user_highest_role_any
    from apps.auth_app.permissions import can_access, DENY
    user_role = _get_user_highest_role_any(request.user)
    can_custom_export = (
        user_role is not None and can_access(user_role, "report.program_report") != DENY
    ) or getattr(request.user, "is_admin", False)

    if request.method != "POST":
        form = TemplateExportForm(user=request.user)
        has_templates = form.fields["report_template"].queryset.exists()
        return render(request, "reports/export_template_driven.html", {
            "form": form,
            "has_templates": has_templates,
            "can_custom_export": can_custom_export,
        })

    # If preview=1 is set, delegate to the preview view
    if request.POST.get("preview") == "1":
        from .preview_views import template_report_preview
        return template_report_preview(request)

    form = TemplateExportForm(request.POST, user=request.user)
    if not form.is_valid():
        has_templates = form.fields["report_template"].queryset.exists()
        return render(request, "reports/export_template_driven.html", {
            "form": form,
            "has_templates": has_templates,
            "can_custom_export": can_custom_export,
        })

    template = form.cleaned_data["report_template"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    period_label = form.cleaned_data.get("period_label", f"{date_from} to {date_to}")
    export_format = form.cleaned_data["format"]
    recipient = form.get_recipient_display()

    # Warn if template spans multiple programs (only first is used)
    template_programs = list(template.partner.get_programs())
    if len(template_programs) > 1:
        from django.contrib import messages as msg
        msg.warning(
            request,
            _("This report template covers multiple programs but currently "
              "only includes data from %(program)s. Multi-program reports "
              "are coming soon.")
            % {"program": template_programs[0].name},
        )

    from .export_engine import generate_template_report
    try:
        content, filename, client_count = generate_template_report(
            template=template,
            date_from=date_from,
            date_to=date_to,
            period_label=period_label,
            user=request.user,
            export_format=export_format,
            request=request,
        )
    except Exception:
        logger.exception("Failed to generate template report")
        from django.contrib import messages
        messages.error(
            request,
            _("Something went wrong generating the report. Please try again."),
        )
        return render(request, "reports/export_template_driven.html", {
            "form": form,
            "has_templates": True,
        })

    link = _save_export_and_create_link(
        request=request,
        content=content,
        filename=filename,
        export_type="funder_report",
        client_count=client_count,
        includes_notes=False,
        recipient=recipient,
        filters_dict={
            "template": template.name,
            "partner": template.partner.name,
            "period": period_label,
            "date_from": str(date_from),
            "date_to": str(date_to),
        },
        contains_pii=False,
    )

    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="template_report",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "template": template.name,
            "partner": template.partner.name,
            "period": period_label,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "format": export_format,
            "recipient": recipient,
            "secure_link_id": str(link.id),
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
        "program_name": template.partner.translated_name,
        "is_pdf": export_format == "pdf",
    })


@login_required
@requires_permission("report.funder_report", allow_admin=True)
def template_period_options(request):
    """
    HTMX endpoint: return period dropdown + template details for a selected template.

    Called when the user changes the template dropdown on the generate
    report form. Returns an HTML fragment injected into #period-panel.
    """
    template_id = request.GET.get("report_template")
    if not template_id:
        return HttpResponse("")

    # Scope to templates the user can access (via their programs)
    from .utils import get_manageable_programs
    accessible_programs = get_manageable_programs(request.user)

    try:
        template = (
            ReportTemplate.objects
            .filter(partner__programs__in=accessible_programs)
            .select_related("partner")
            .prefetch_related(
                "report_metrics__metric_definition",
                "breakdowns__custom_field",
                "partner__programs",
            )
            .distinct()
            .get(pk=template_id, is_active=True)
        )
    except ReportTemplate.DoesNotExist:
        return HttpResponse("")

    period_choices = build_period_choices(template)
    programs = template.partner.get_programs()
    metrics = template.report_metrics.all().order_by("sort_order")
    breakdowns = template.breakdowns.all().order_by("sort_order")

    return render(request, "reports/_period_options.html", {
        "template": template,
        "period_choices": period_choices,
        "programs": programs,
        "metrics": metrics,
        "breakdowns": breakdowns,
        "is_custom_period": template.period_type == "custom",
    })


@login_required
@requires_permission("report.program_report", allow_admin=True)
def adhoc_template_autofill(request):
    """
    HTMX endpoint: return template auto-fill data for the ad-hoc export form.

    When a template is selected in /reports/export/, this returns a JSON
    response with metric definition IDs to check and consortium info.
    """
    from .models import ReportMetric as RM
    from .utils import get_manageable_programs

    template_id = request.GET.get("template_id")
    if not template_id:
        return HttpResponse(
            json.dumps({"metric_ids": [], "consortium_locked": [], "partner_name": ""}),
            content_type="application/json",
        )

    # Scope to templates the user can access (via their programs)
    accessible_programs = get_manageable_programs(request.user)

    try:
        template = (
            ReportTemplate.objects
            .filter(partner__programs__in=accessible_programs)
            .select_related("partner")
            .distinct()
            .get(pk=template_id, is_active=True)
        )
    except ReportTemplate.DoesNotExist:
        return HttpResponse(
            json.dumps({"metric_ids": [], "consortium_locked": [], "partner_name": ""}),
            content_type="application/json",
        )

    report_metrics = RM.objects.filter(
        report_template=template,
    ).select_related("metric_definition")

    metric_ids = [rm.metric_definition_id for rm in report_metrics]
    consortium_locked = [
        rm.metric_definition_id for rm in report_metrics
        if rm.is_consortium_required
    ]

    return HttpResponse(
        json.dumps({
            "metric_ids": metric_ids,
            "consortium_locked": consortium_locked,
            "partner_name": template.partner.translated_name,
        }),
        content_type="application/json",
    )


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
            "delay_minutes": getattr(settings, "ELEVATED_EXPORT_DELAY_MINUTES", 10),
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
def team_meeting_view(request):
    """Staff activity summary for team meetings — PM/admin only.

    Groups recent activity (notes, meetings, comms) by staff member.
    Shows last 7 days by default, configurable to 14 or 30.
    """
    from datetime import timedelta

    from django.db.models import Count, Max, Q

    from apps.auth_app.decorators import _get_user_highest_role
    from apps.auth_app.constants import ROLE_RANK
    from apps.programs.models import UserProgramRole, Program
    from apps.programs.access import get_user_program_ids
    from apps.notes.models import ProgressNote
    from apps.communications.models import Communication
    from apps.events.models import Meeting

    # Check PM/admin permission
    role = _get_user_highest_role(request.user)
    if ROLE_RANK.get(role, 0) < ROLE_RANK.get("program_manager", 99):
        if not getattr(request.user, "is_admin", False):
            return HttpResponseForbidden(_("This view is for program managers only."))

    # Get accessible programs
    user_program_ids = list(get_user_program_ids(request.user))
    accessible_programs = Program.objects.filter(pk__in=user_program_ids, status="active")

    # Date range filter
    days = request.GET.get("days", "7")
    try:
        days = int(days)
    except (ValueError, TypeError):
        days = 7
    if days not in (7, 14, 30):
        days = 7
    cutoff = timezone.now() - timedelta(days=days)

    # Program filter
    program_filter = request.GET.get("program", "")
    if program_filter:
        try:
            filter_program_ids = [int(program_filter)]
            # Ensure the user has access to this program
            filter_program_ids = [pid for pid in filter_program_ids if pid in user_program_ids]
        except (ValueError, TypeError):
            filter_program_ids = user_program_ids
    else:
        filter_program_ids = user_program_ids

    # Get staff members in filtered programs
    staff_roles = UserProgramRole.objects.filter(
        program_id__in=filter_program_ids,
        role__in=["staff", "program_manager"],
        status="active",
    ).select_related("user", "program").order_by("user__display_name")

    # Deduplicate by user and collect role/program info
    user_map = {}  # user_id -> {user, role_display}
    user_programs_map = {}  # user_id -> [program_name, ...]
    for role_obj in staff_roles:
        uid = role_obj.user.pk
        if uid not in user_map:
            user_map[uid] = {"user": role_obj.user, "role_display": role_obj.get_role_display()}
            user_programs_map[uid] = []
        user_programs_map[uid].append(role_obj.program.name)

    staff_user_ids = list(user_map.keys())

    # Batch aggregation: 3 aggregate queries instead of 7N individual queries
    note_agg = {}
    for row in ProgressNote.objects.filter(
        author_id__in=staff_user_ids,
        author_program_id__in=filter_program_ids,
        created_at__gte=cutoff,
        status="default",
    ).values("author_id").annotate(
        count=Count("pk"), last_date=Max("created_at"),
    ):
        note_agg[row["author_id"]] = (row["count"], row["last_date"])

    comm_agg = {}
    for row in Communication.objects.filter(
        logged_by_id__in=staff_user_ids,
        author_program_id__in=filter_program_ids,
        created_at__gte=cutoff,
    ).values("logged_by_id").annotate(
        count=Count("pk"), last_date=Max("created_at"),
    ):
        comm_agg[row["logged_by_id"]] = (row["count"], row["last_date"])

    meeting_agg = {}
    for row in Meeting.objects.filter(
        attendees__in=staff_user_ids,
        event__start_timestamp__gte=cutoff,
    ).values("attendees").annotate(
        count=Count("pk"), last_date=Max("event__start_timestamp"),
    ):
        meeting_agg[row["attendees"]] = (row["count"], row["last_date"])

    # Build activity list from aggregated results
    staff_activity = []
    for uid, info in user_map.items():
        note_count, last_note = note_agg.get(uid, (0, None))
        comm_count, last_comm = comm_agg.get(uid, (0, None))
        meeting_count, last_meeting = meeting_agg.get(uid, (0, None))
        total = note_count + comm_count + meeting_count

        staff_activity.append({
            "user": info["user"],
            "role_display": info["role_display"],
            "programs": user_programs_map.get(uid, []),
            "note_count": note_count,
            "comm_count": comm_count,
            "meeting_count": meeting_count,
            "total_activity": total,
            "last_note": last_note,
            "last_comm": last_comm,
            "last_meeting": last_meeting,
        })

    # Sort: most active first, then alphabetical
    staff_activity.sort(key=lambda x: (-x["total_activity"], x["user"].display_name))

    return render(request, "reports/team_meeting.html", {
        "staff_activity": staff_activity,
        "accessible_programs": accessible_programs,
        "program_filter": program_filter,
        "days": days,
        "cutoff": cutoff,
        "nav_active": "admin",
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


# ---------------------------------------------------------------------------
# Sessions by Participant report (REP-SESS1)
# ---------------------------------------------------------------------------


@login_required
@requires_permission("report.program_report", allow_admin=True)
def session_report_form(request):
    """
    Sessions by Participant report — session counts, contact hours, modality.

    GET  — display the session report form.
    POST — generate and return the CSV report.

    Access: program_manager and admin (via report.program_report permission).
    This report contains individual participant data (names, session details)
    so it is NOT available to executives (aggregate-only users).
    """
    from .forms import SessionReportForm
    from .session_report import generate_session_report
    from .session_csv import generate_session_report_csv

    # Block aggregate-only users — this report contains participant-level data.
    # Admins are exempt (they have system-wide access via allow_admin=True).
    if is_aggregate_only_user(request.user) and not getattr(request.user, "is_admin", False):
        return HttpResponseForbidden(
            _("This report contains individual participant data. "
              "Please use the template-driven report for aggregate output.")
        )

    if request.method != "POST":
        form = SessionReportForm(user=request.user)
        breadcrumbs = [
            {"url": reverse("reports:export_form"), "label": _("Reports")},
            {"url": "", "label": _("Sessions by Participant")},
        ]
        return render(request, "reports/session_report_form.html", {
            "form": form,
            "breadcrumbs": breadcrumbs,
        })

    form = SessionReportForm(request.POST, user=request.user)
    if not form.is_valid():
        breadcrumbs = [
            {"url": reverse("reports:export_form"), "label": _("Reports")},
            {"url": "", "label": _("Sessions by Participant")},
        ]
        return render(request, "reports/session_report_form.html", {
            "form": form,
            "breadcrumbs": breadcrumbs,
        })

    program = form.cleaned_data["program"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    recipient = form.get_recipient_display()

    if program is None:
        return HttpResponseForbidden(
            _("Please select a specific program for session reports.")
        )

    # Permission check
    if not can_create_export(request.user, "session_report", program=program):
        return HttpResponseForbidden(
            _("You do not have permission to export data for this program.")
        )

    # Generate report data
    report_data = generate_session_report(program, date_from, date_to, user=request.user)

    # Generate CSV
    csv_content, filename = generate_session_report_csv(report_data)
    client_count = report_data["summary"]["total_unique_participants"]

    # Save as secure export link (follows existing pattern)
    secure_dir = getattr(settings, "SECURE_EXPORT_DIR", "/tmp/konote_exports")
    os.makedirs(secure_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = os.path.join(secure_dir, f"{file_id}.csv")
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        f.write(csv_content)

    link = SecureExportLink.objects.create(
        created_by=request.user,
        expires_at=timezone.now() + timedelta(hours=24),
        export_type="session_report",
        filters_json=json.dumps({
            "report_type": "session_by_participant",
            "program_id": program.pk,
            "program_name": str(program),
            "date_from": str(date_from),
            "date_to": str(date_to),
        }),
        client_count=client_count,
        includes_notes=False,
        recipient=recipient,
        filename=filename,
        file_path=file_path,
        contains_pii=True,
    )

    # Audit log
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="create",
        resource_type="session_report",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "link_id": str(link.id),
            "program": str(program),
            "date_from": str(date_from),
            "date_to": str(date_to),
            "client_count": client_count,
            "total_sessions": report_data["summary"]["total_sessions"],
            "recipient": recipient,
        },
    )

    from django.contrib import messages
    from django.shortcuts import redirect

    messages.success(
        request,
        _("Session report generated. %(count)d participants, %(sessions)d sessions.")
        % {"count": client_count, "sessions": report_data["summary"]["total_sessions"]},
    )
    return redirect("reports:download_export", link_id=link.pk)
