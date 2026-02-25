"""On-screen report preview views (REP-PREVIEW1).

Allows users to preview report data in the browser before downloading
as PDF/CSV.  Both the template-driven and ad-hoc export paths support
preview.

Security: applies the same permission decorators and aggregate-only
enforcement as the download views.  Executives still see aggregate data
only.  The ``is_aggregate_only_user()`` check is applied identically.

See tasks/design-rationale/reporting-architecture.md for architecture.
"""

import logging
from collections import defaultdict
from datetime import datetime, time

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.audit.models import AuditLog
from apps.auth_app.decorators import requires_permission
from apps.clients.models import ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote

from .achievements import get_achievement_summary
from .aggregations import aggregate_metrics, _stats_from_list
from .demographics import (
    aggregate_by_demographic,
    group_clients_by_age,
    group_clients_by_custom_field,
    parse_grouping_choice,
)
from .forms import MetricExportForm, TemplateExportForm, build_period_choices
from .models import DemographicBreakdown, ReportTemplate
from .suppression import SMALL_CELL_THRESHOLD, suppress_small_cell
from .utils import (
    can_create_export,
    get_manageable_programs,
    is_aggregate_only_user,
)

logger = logging.getLogger(__name__)

from konote.utils import get_client_ip as _get_client_ip


def _querydict_to_pairs(qd):
    """Convert a QueryDict to a list of (key, value) tuples.

    Handles multi-value fields (like ``metrics``) by emitting one pair
    per value.  Excludes ``csrfmiddlewaretoken`` and ``preview`` since
    the download forms provide those themselves.
    """
    pairs = []
    for key in qd:
        if key in ("csrfmiddlewaretoken", "preview", "format"):
            continue
        values = qd.getlist(key)
        for val in values:
            if val and val.strip():
                pairs.append((key, val))
    return pairs


# ---------------------------------------------------------------------------
# Template-driven report preview
# ---------------------------------------------------------------------------

@login_required
@requires_permission("report.funder_report", allow_admin=True)
def template_report_preview(request):
    """Preview a template-driven report on screen.

    Accepts the same POST data as ``generate_report_form``.  Instead of
    generating a downloadable file, renders the report data in an HTML
    template so users can review before downloading.

    GET requests redirect to the generation form.
    """
    from .export_engine import generate_template_report
    from .funder_report import generate_funder_report_data, get_demographic_groups
    from .aggregation import compute_template_metrics
    from .export_engine import _get_active_client_ids
    from .models import ReportMetric, ReportSection

    if request.method != "POST":
        from django.shortcuts import redirect
        return redirect("reports:generate_report")

    form = TemplateExportForm(request.POST, user=request.user)
    if not form.is_valid():
        has_templates = form.fields["report_template"].queryset.exists()
        return render(request, "reports/export_template_driven.html", {
            "form": form,
            "has_templates": has_templates,
        })

    template = form.cleaned_data["report_template"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    period_label = form.cleaned_data.get("period_label", f"{date_from} to {date_to}")

    # Generate report data using the same pipeline as the download path
    programs = list(template.partner.get_programs())
    program = programs[0] if programs else None

    if not program:
        from django.contrib import messages
        messages.error(request, _("No programs are linked to this report template."))
        return render(request, "reports/export_template_driven.html", {
            "form": form,
            "has_templates": True,
        })

    try:
        report_data = generate_funder_report_data(
            program,
            date_from=date_from,
            date_to=date_to,
            fiscal_year_label=period_label,
            user=request.user,
            report_template=template,
        )
    except Exception:
        logger.exception("Failed to generate template report preview data")
        from django.contrib import messages
        messages.error(
            request,
            _("Something went wrong generating the preview. Please try again."),
        )
        return render(request, "reports/export_template_driven.html", {
            "form": form,
            "has_templates": True,
        })

    # Apply small-cell suppression (same as export_engine)
    report_data["total_individuals_served"] = suppress_small_cell(
        report_data["total_individuals_served"], program,
    )
    report_data["new_clients_this_period"] = suppress_small_cell(
        report_data["new_clients_this_period"], program,
    )

    # Check for ReportMetric records with aggregation rules
    report_metrics = list(
        ReportMetric.objects.filter(
            report_template=template,
        ).select_related("metric_definition").order_by("sort_order")
    )
    has_aggregation = bool(report_metrics)

    metric_results = []
    demographic_labels = []

    if has_aggregation:
        active_ids = _get_active_client_ids(program, date_from, date_to, request.user)
        demo_groups = get_demographic_groups(active_ids, date_to, template)
        metric_results = compute_template_metrics(
            program, date_from, date_to,
            report_metrics, demo_groups, request.user,
        )
        demographic_labels = list(demo_groups.keys())

    # Apply suppression to metric results for preview
    suppressed_metric_results = []
    for mr in metric_results:
        suppressed_values = {}
        for group_label in demographic_labels:
            group_data = mr["values"].get(group_label, {})
            n = group_data.get("n", 0)
            value = group_data.get("value", "")
            label_suffix = group_data.get("label_suffix", "")

            if isinstance(n, int) and 0 < n < SMALL_CELL_THRESHOLD:
                suppressed_values[group_label] = {
                    "value": f"< {SMALL_CELL_THRESHOLD}",
                    "n": f"< {SMALL_CELL_THRESHOLD}",
                    "label_suffix": label_suffix,
                    "suppressed": True,
                }
            else:
                display_value = value
                if mr["aggregation"] in ("threshold_percentage", "percentage"):
                    display_value = f"{value}%"
                suppressed_values[group_label] = {
                    "value": display_value,
                    "n": n,
                    "label_suffix": label_suffix,
                    "suppressed": False,
                }
        suppressed_metric_results.append({
            "label": mr["label"],
            "aggregation": mr["aggregation"],
            "values": suppressed_values,
        })

    # Query ReportSections for structuring
    sections = list(
        ReportSection.objects.filter(
            report_template=template,
        ).order_by("sort_order")
    )

    # Build download URLs (form data is re-submitted via hidden fields)
    generate_url = reverse("reports:generate_report")

    # Audit log for preview action
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="preview",
        resource_type="template_report",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "template": template.name,
            "partner": template.partner.name,
            "period": period_label,
            "date_from": str(date_from),
            "date_to": str(date_to),
        },
    )

    return render(request, "reports/report_preview.html", {
        "preview_type": "template",
        "template": template,
        "program": program,
        "programs": programs,
        "period_label": period_label,
        "date_from": date_from,
        "date_to": date_to,
        "report_data": report_data,
        "metric_results": suppressed_metric_results,
        "demographic_labels": demographic_labels,
        "has_aggregation": has_aggregation,
        "sections": sections,
        "generate_url": generate_url,
        "form_pairs": _querydict_to_pairs(request.POST),
        "generated_by": request.user.display_name,
        "generated_at": timezone.now(),
    })


# ---------------------------------------------------------------------------
# Ad-hoc export preview
# ---------------------------------------------------------------------------

@login_required
@requires_permission("report.program_report", allow_admin=True)
def adhoc_report_preview(request):
    """Preview an ad-hoc export on screen.

    Accepts the same POST data as ``export_form``.  Instead of
    generating a downloadable file, renders aggregate data in an HTML
    table so users can review before downloading.

    Aggregate-only enforcement is identical to the download path:
    executives see summary statistics only.

    GET requests redirect to the export form.
    """
    from apps.clients.views import get_client_queryset

    if request.method != "POST":
        from django.shortcuts import redirect
        return redirect("reports:export_form")

    is_aggregate = is_aggregate_only_user(request.user)

    form = MetricExportForm(request.POST, user=request.user)
    if not form.is_valid():
        return render(request, "reports/export_form.html", {
            "form": form,
            "is_aggregate_only": is_aggregate,
        })

    program = form.cleaned_data["program"]
    all_programs_mode = form.is_all_programs

    if all_programs_mode:
        if not can_create_export(request.user, "metrics"):
            return HttpResponseForbidden(
                "You do not have permission to export data."
            )
        is_aggregate = True
    else:
        if not can_create_export(request.user, "metrics", program=program):
            return HttpResponseForbidden(
                "You do not have permission to export data for this program."
            )

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

    grouping_type, grouping_field = parse_grouping_choice(group_by_value)
    if report_template:
        grouping_type = "none"
        grouping_field = None

    # Find matching clients and metric values (same as export_form)
    accessible_client_ids = get_client_queryset(request.user).values_list("pk", flat=True)
    if all_programs_mode:
        accessible_programs = get_manageable_programs(request.user)
        _has_confidential = accessible_programs.filter(is_confidential=True).exists()
        client_ids = ClientProgramEnrolment.objects.filter(
            program__in=accessible_programs, status="enrolled",
            client_file_id__in=accessible_client_ids,
        ).values_list("client_file_id", flat=True).distinct()
    else:
        _has_confidential = getattr(program, "is_confidential", False) if program else False
        client_ids = ClientProgramEnrolment.objects.filter(
            program=program, status="enrolled",
            client_file_id__in=accessible_client_ids,
        ).values_list("client_file_id", flat=True)

    date_from_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, time.max))

    notes = ProgressNote.objects.filter(
        client_file_id__in=client_ids,
        status="default",
    ).filter(
        Q(backdate__range=(date_from_dt, date_to_dt))
        | Q(backdate__isnull=True, created_at__range=(date_from_dt, date_to_dt))
    )

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
        return render(request, "reports/export_form.html", {
            "form": form,
            "no_data": True,
            "is_aggregate_only": is_aggregate,
        })

    # Build aggregate statistics (same logic as export_form)
    agg_by_metric = aggregate_metrics(metric_values, group_by="metric")

    unique_clients = set()
    metric_client_sets = {}
    for mv in metric_values:
        client_id = mv.progress_note_target.progress_note.client_file_id
        unique_clients.add(client_id)
        mid = mv.metric_def_id
        if mid not in metric_client_sets:
            metric_client_sets[mid] = set()
        metric_client_sets[mid].add(client_id)

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
            "clients_measured": suppress_small_cell(
                len(metric_client_sets.get(mid, set())),
                program, is_confidential=_has_confidential,
            ),
            "data_points": suppress_small_cell(
                stats.get("valid_count", 0),
                program, is_confidential=_has_confidential,
            ),
            "avg": avg_val,
            "min": stats.get("min", "N/A"),
            "max": stats.get("max", "N/A"),
        })

    # Demographic breakdown
    demographic_rows = []
    grouping_label = ""
    if grouping_type != "none":
        grouping_label = _get_grouping_label(group_by_value, grouping_field)
        for mv_metric_def in selected_metrics:
            metric_specific_mvs = metric_values.filter(metric_def=mv_metric_def)
            if not metric_specific_mvs.exists():
                continue
            demo_agg = aggregate_by_demographic(
                metric_specific_mvs, grouping_type, grouping_field, date_to,
            )
            for group_label, stats in demo_agg.items():
                client_count = len(stats.get("client_ids", set()))
                avg_val = round(stats["avg"], 1) if stats.get("avg") is not None else "N/A"
                demographic_rows.append({
                    "demographic_group": group_label,
                    "metric_name": mv_metric_def.name,
                    "clients_measured": suppress_small_cell(
                        client_count, program, is_confidential=_has_confidential,
                    ),
                    "avg": avg_val,
                    "min": stats.get("min", "N/A"),
                    "max": stats.get("max", "N/A"),
                })

    # Report template multi-breakdown sections
    template_breakdown_sections = []
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
                                s = {
                                    "count": 0, "valid_count": 0,
                                    "avg": None, "min": None,
                                    "max": None, "sum": None,
                                }
                            s["client_ids"] = set(cids)
                            demo_agg[gl] = s
                elif bd.source_type == "custom_field" and bd.custom_field:
                    demo_agg = aggregate_by_demographic(
                        metric_specific_mvs, "custom_field", bd.custom_field, date_to,
                    )
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
                                s = {
                                    "count": 0, "valid_count": 0,
                                    "avg": None, "min": None,
                                    "max": None, "sum": None,
                                }
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
                        "clients_measured": suppress_small_cell(
                            client_count, program, is_confidential=_has_confidential,
                        ),
                        "avg": avg_val,
                        "min": stats.get("min", "N/A"),
                        "max": stats.get("max", "N/A"),
                    })

            if section_rows:
                template_breakdown_sections.append({
                    "label": bd.label,
                    "rows": section_rows,
                })

    # Achievement summary
    achievement_summary = None
    if include_achievement:
        if all_programs_mode:
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

    total_clients_display = suppress_small_cell(
        len(unique_clients), program, is_confidential=_has_confidential,
    )

    # Build individual data rows for non-aggregate users
    individual_rows = []
    if not is_aggregate:
        for mv in metric_values:
            note = mv.progress_note_target.progress_note
            client = note.client_file
            plan_target = mv.progress_note_target.plan_target
            goal_name = plan_target.name if plan_target else ""
            individual_rows.append({
                "record_id": client.record_id,
                "goal_name": goal_name,
                "metric_name": mv.metric_def.name,
                "value": mv.value,
                "date": note.effective_date.strftime("%Y-%m-%d"),
                "author": note.author.display_name,
            })

    export_url = reverse("reports:export_form")

    # Audit log for preview
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="preview",
        resource_type="metric_report",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "program": str(program_display_name),
            "all_programs": all_programs_mode,
            "metrics": [m.name for m in selected_metrics],
            "date_from": str(date_from),
            "date_to": str(date_to),
            "export_mode": "aggregate" if is_aggregate else "individual",
        },
    )

    return render(request, "reports/report_preview.html", {
        "preview_type": "adhoc",
        "program_display_name": program_display_name,
        "program": program,
        "date_from": date_from,
        "date_to": date_to,
        "selected_metrics": selected_metrics,
        "aggregate_rows": aggregate_rows,
        "demographic_rows": demographic_rows,
        "grouping_label": grouping_label,
        "template_breakdown_sections": template_breakdown_sections,
        "report_template": report_template,
        "achievement_summary": achievement_summary,
        "total_clients_display": total_clients_display,
        "is_aggregate_only": is_aggregate,
        "individual_rows": individual_rows if not is_aggregate else [],
        "export_url": export_url,
        "form_pairs": _querydict_to_pairs(request.POST),
        "generated_by": request.user.display_name,
        "generated_at": timezone.now(),
    })


def _get_grouping_label(group_by_value, grouping_field):
    """Return a human-readable label for the selected grouping."""
    if not group_by_value:
        return ""
    if group_by_value == "age_range":
        return _("Age Range")
    if grouping_field:
        return grouping_field.name
    return str(group_by_value)
