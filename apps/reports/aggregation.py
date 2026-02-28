"""Metric aggregation engine for template-driven reports.

Computes aggregated metric values (count, average, threshold_percentage, etc.)
per demographic group, as defined by ReportMetric.aggregation.

See tasks/design-rationale/reporting-architecture.md § Aggregation Rules.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.clients.models import ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote

logger = logging.getLogger(__name__)


def _to_float(value: str) -> float | None:
    """Safely convert a string value to float, returning None if invalid."""
    if not value:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def compute_metric_aggregation(
    client_values: dict[int, list[tuple[datetime, float]]],
    aggregation_type: str,
    threshold_value: float | None = None,
) -> dict[str, Any]:
    """Aggregate per-client metric time-series into a single result.

    Args:
        client_values: {client_id: [(effective_datetime, numeric_value), ...]}
            Each client's time-series of metric recordings, unsorted.
        aggregation_type: One of the ReportMetric.AGGREGATION_TYPES choices.
        threshold_value: Required for threshold_count, threshold_percentage,
            and percentage aggregation types.

    Returns:
        Dict with:
            - "value": the aggregated number (float or int)
            - "n": count of clients contributing to the result
            - "label_suffix": e.g. "(mean)", "(n)", "(%)" for display
    """
    if not client_values:
        return {"value": 0, "n": 0, "label_suffix": ""}

    n = len(client_values)

    if aggregation_type == "count":
        return {"value": n, "n": n, "label_suffix": "(n)"}

    # For most types, compute each client's representative value (latest)
    client_latest = {}
    for client_id, values in client_values.items():
        sorted_vals = sorted(values, key=lambda x: x[0] if x[0] else datetime.min)
        client_latest[client_id] = sorted_vals[-1][1]

    if aggregation_type == "average":
        if not client_latest:
            return {"value": 0, "n": 0, "label_suffix": _("(mean)")}
        avg = sum(client_latest.values()) / len(client_latest)
        return {"value": round(avg, 1), "n": n, "label_suffix": _("(mean)")}

    if aggregation_type == "sum":
        total = sum(client_latest.values())
        return {"value": round(total, 1), "n": n, "label_suffix": _("(total)")}

    if aggregation_type == "average_change":
        changes = []
        for client_id, values in client_values.items():
            if len(values) < 2:
                continue
            sorted_vals = sorted(
                values, key=lambda x: x[0] if x[0] else datetime.min,
            )
            change = sorted_vals[-1][1] - sorted_vals[0][1]
            changes.append(change)
        if not changes:
            return {"value": 0, "n": 0, "label_suffix": _("(change)")}
        avg_change = sum(changes) / len(changes)
        return {
            "value": round(avg_change, 1),
            "n": len(changes),
            "label_suffix": _("(change)"),
        }

    if aggregation_type in ("threshold_count", "threshold_percentage", "percentage"):
        tv = float(threshold_value) if threshold_value is not None else 0
        met_count = sum(1 for v in client_latest.values() if v >= tv)
        if aggregation_type == "threshold_count":
            return {"value": met_count, "n": n, "label_suffix": f"(>= {tv})"}
        pct = round((met_count / n) * 100, 1) if n > 0 else 0
        return {"value": pct, "n": n, "label_suffix": "(%)"}

    raise ValueError(
        f"Unknown aggregation type {aggregation_type!r}. "
        f"Valid types: count, average, sum, average_change, "
        f"threshold_count, threshold_percentage, percentage."
    )


def compute_template_metrics(
    program,
    date_from: date,
    date_to: date,
    report_metrics,
    demographic_groups: dict[str, list[int]],
    user=None,
) -> list[dict[str, Any]]:
    """Compute aggregated metrics per demographic group for a report template.

    Args:
        program: Program instance.
        date_from: Start of reporting period (inclusive).
        date_to: End of reporting period (inclusive).
        report_metrics: Iterable of ReportMetric instances (with
            .metric_definition, .aggregation, .threshold_value, .translated_label).
        demographic_groups: {"All Participants": [client_ids], "Age 13-17": [...], ...}
        user: Optional user for demo/real filtering.

    Returns:
        List of metric result dicts:
        [
            {
                "label": "Youth Engagement Index",
                "aggregation": "average",
                "values": {
                    "All Participants": {"value": 3.8, "n": 50, "label_suffix": "(mean)"},
                    "Age 13-17": {"value": 3.2, "n": 12, "label_suffix": "(mean)"},
                    ...
                },
            },
            ...
        ]
    """
    report_metrics = list(report_metrics)
    if not report_metrics:
        return []

    # Collect all metric definitions we need
    metric_defs = [rm.metric_definition for rm in report_metrics]
    metric_def_ids = {md.pk for md in metric_defs}

    # Get enrolled client IDs
    enrolled_client_ids = set(
        ClientProgramEnrolment.objects.filter(
            program=program, status="active",
        ).values_list("client_file_id", flat=True)
    )

    # Filter by demo status if needed
    if user is not None:
        from apps.clients.models import ClientFile
        if user.is_demo:
            accessible_ids = set(
                ClientFile.objects.demo().values_list("pk", flat=True)
            )
        else:
            accessible_ids = set(
                ClientFile.objects.real().values_list("pk", flat=True)
            )
        enrolled_client_ids = enrolled_client_ids & accessible_ids

    # Build date filter for notes
    date_from_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, time.max))

    note_filter = Q(client_file_id__in=enrolled_client_ids, status="default")
    note_filter &= (
        Q(backdate__range=(date_from_dt, date_to_dt))
        | Q(backdate__isnull=True, created_at__range=(date_from_dt, date_to_dt))
    )
    notes = ProgressNote.objects.filter(note_filter)

    # Query all metric values for our metrics in one go
    metric_values_qs = MetricValue.objects.filter(
        progress_note_target__progress_note__in=notes,
        metric_def_id__in=metric_def_ids,
    ).select_related(
        "metric_def",
        "progress_note_target__progress_note",
    )

    # Build structure: {metric_def_id: {client_id: [(datetime, value)]}}
    metric_data: dict[int, dict[int, list[tuple[datetime, float]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for mv in metric_values_qs:
        numeric_val = _to_float(mv.value)
        if numeric_val is None:
            continue
        note = mv.progress_note_target.progress_note
        effective_dt = note.backdate or note.created_at
        client_id = note.client_file_id
        metric_data[mv.metric_def_id][client_id].append((effective_dt, numeric_val))

    # Compute aggregation per metric × per demographic group
    results = []
    for rm in report_metrics:
        md_id = rm.metric_definition_id
        all_client_values = metric_data.get(md_id, {})

        threshold = (
            float(rm.threshold_value) if rm.threshold_value is not None else None
        )

        group_results = {}
        for group_label, group_client_ids in demographic_groups.items():
            group_ids_set = set(group_client_ids)
            # Filter to clients in this demographic group
            filtered = {
                cid: vals
                for cid, vals in all_client_values.items()
                if cid in group_ids_set
            }
            group_results[group_label] = compute_metric_aggregation(
                filtered, rm.aggregation, threshold,
            )

        results.append({
            "label": rm.translated_label,
            "aggregation": rm.aggregation,
            "values": group_results,
        })

    return results
