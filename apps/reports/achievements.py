"""Outcome achievement rate calculations for programme reporting.

Calculates what percentage of clients met their outcome targets.
Uses latest or average metric values to determine if clients achieved their goals.
"""
from datetime import date, datetime, time
from typing import Any, Literal

from django.db.models import Q
from django.utils import timezone

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote
from apps.plans.models import MetricDefinition


def _to_float(value: str) -> float | None:
    """Safely convert a string value to float, returning None if invalid."""
    if not value:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _build_date_filter(date_from: date | None, date_to: date | None) -> Q:
    """Build a Q filter for effective date range (backdate or created_at)."""
    if not date_from and not date_to:
        return Q()

    date_from_dt = (
        timezone.make_aware(datetime.combine(date_from, time.min))
        if date_from else None
    )
    date_to_dt = (
        timezone.make_aware(datetime.combine(date_to, time.max))
        if date_to else None
    )

    if date_from_dt and date_to_dt:
        return (
            Q(backdate__range=(date_from_dt, date_to_dt))
            | Q(backdate__isnull=True, created_at__range=(date_from_dt, date_to_dt))
        )
    elif date_from_dt:
        return (
            Q(backdate__gte=date_from_dt)
            | Q(backdate__isnull=True, created_at__gte=date_from_dt)
        )
    else:  # date_to_dt only
        return (
            Q(backdate__lte=date_to_dt)
            | Q(backdate__isnull=True, created_at__lte=date_to_dt)
        )


ComparisonType = Literal["gte", "lte", "eq", "range"]


def calculate_achievement_status(
    metric_value: float,
    target_value: float,
    comparison: ComparisonType = "gte",
    min_value: float | None = None,
    max_value: float | None = None,
) -> bool:
    """
    Determine if a metric value meets the target.

    Args:
        metric_value: The recorded metric value to evaluate.
        target_value: The target threshold to compare against.
        comparison: How to compare value to target:
            - "gte": value >= target (improvement metrics, e.g., housing stability)
            - "lte": value <= target (reduction metrics, e.g., PHQ-9 depression score)
            - "eq": value == target (exact match)
            - "range": value is within min_value to max_value (target_value ignored)
        min_value: Minimum value for range comparison (required if comparison="range").
        max_value: Maximum value for range comparison (required if comparison="range").

    Returns:
        True if target is met, False otherwise.
    """
    if comparison == "gte":
        return metric_value >= target_value
    elif comparison == "lte":
        return metric_value <= target_value
    elif comparison == "eq":
        return metric_value == target_value
    elif comparison == "range":
        if min_value is None or max_value is None:
            return False
        return min_value <= metric_value <= max_value
    return False


def get_client_achievement_rate(
    client_file: ClientFile,
    metric_def: MetricDefinition,
    target_value: float,
    date_from: date | None = None,
    date_to: date | None = None,
    comparison: ComparisonType = "gte",
) -> dict[str, Any]:
    """
    Calculate what percentage of a client's measurements meet the target.

    Args:
        client_file: The client to analyse.
        metric_def: The metric definition to evaluate.
        target_value: The target threshold value.
        date_from: Start of date range (inclusive).
        date_to: End of date range (inclusive).
        comparison: How to compare values to target ("gte", "lte", "eq", "range").

    Returns:
        dict with:
            - total_measurements: Total number of valid numeric measurements
            - measurements_met_target: Count of measurements meeting target
            - achievement_rate: Percentage (0.0-100.0) with 1 decimal place
            - latest_value: Most recent metric value (or None)
            - latest_met_target: Whether latest value met target (or None)
    """
    # Build note filter with date range
    note_filter = Q(client_file=client_file, status="default")
    if date_from or date_to:
        note_filter &= _build_date_filter(date_from, date_to)

    note_ids = ProgressNote.objects.filter(note_filter).values_list("pk", flat=True)

    # Get metric values for this client and metric
    metric_values = MetricValue.objects.filter(
        metric_def=metric_def,
        progress_note_target__progress_note_id__in=note_ids,
    ).select_related(
        "progress_note_target__progress_note"
    ).order_by(
        "progress_note_target__progress_note__created_at"
    )

    total_measurements = 0
    measurements_met = 0
    latest_value = None
    latest_met = None

    for mv in metric_values:
        numeric_val = _to_float(mv.value)
        if numeric_val is None:
            continue

        total_measurements += 1
        met_target = calculate_achievement_status(
            numeric_val, target_value, comparison,
            min_value=metric_def.min_value,
            max_value=metric_def.max_value,
        )
        if met_target:
            measurements_met += 1

        # Track latest value (queryset is ordered by created_at ascending)
        latest_value = numeric_val
        latest_met = met_target

    achievement_rate = 0.0
    if total_measurements > 0:
        achievement_rate = round((measurements_met / total_measurements) * 100, 1)

    return {
        "total_measurements": total_measurements,
        "measurements_met_target": measurements_met,
        "achievement_rate": achievement_rate,
        "latest_value": latest_value,
        "latest_met_target": latest_met,
    }


def get_program_achievement_rate(
    program,
    metric_def: MetricDefinition,
    target_value: float,
    date_from: date | None = None,
    date_to: date | None = None,
    comparison: ComparisonType = "gte",
    use_latest: bool = True,
) -> dict[str, Any]:
    """
    Calculate what percentage of clients in a programme met the target.

    Args:
        program: The programme to analyse.
        metric_def: The metric definition to evaluate.
        target_value: The target threshold value.
        date_from: Start of date range (inclusive).
        date_to: End of date range (inclusive).
        comparison: How to compare values to target ("gte", "lte", "eq", "range").
        use_latest: If True, use client's latest value; if False, use average.

    Returns:
        dict with:
            - total_clients: Clients with any metric data in the period
            - clients_met_target: Clients whose value met target
            - achievement_rate: Percentage (0.0-100.0) with 1 decimal place
    """
    # Get clients enrolled in the programme
    client_ids = ClientProgramEnrolment.objects.filter(
        program=program, status="enrolled"
    ).values_list("client_file_id", flat=True)

    # Build note filter with date range
    note_filter = Q(client_file_id__in=client_ids, status="default")
    if date_from or date_to:
        note_filter &= _build_date_filter(date_from, date_to)

    notes = ProgressNote.objects.filter(note_filter)

    # Get all metric values for this metric in the programme
    metric_values = MetricValue.objects.filter(
        metric_def=metric_def,
        progress_note_target__progress_note__in=notes,
    ).select_related(
        "progress_note_target__progress_note__client_file",
        "progress_note_target__progress_note",
    )

    # Group values by client
    client_values: dict[int, list[tuple[datetime, float]]] = {}
    for mv in metric_values:
        numeric_val = _to_float(mv.value)
        if numeric_val is None:
            continue

        client_id = mv.progress_note_target.progress_note.client_file_id
        note = mv.progress_note_target.progress_note
        effective_dt = note.backdate or note.created_at

        if client_id not in client_values:
            client_values[client_id] = []
        client_values[client_id].append((effective_dt, numeric_val))

    total_clients = len(client_values)
    clients_met = 0

    for client_id, values in client_values.items():
        if not values:
            continue

        if use_latest:
            # Sort by date and use most recent value
            values.sort(key=lambda x: x[0] if x[0] else datetime.min)
            client_value = values[-1][1]
        else:
            # Use average of all values
            all_values = [v[1] for v in values]
            client_value = sum(all_values) / len(all_values)

        if calculate_achievement_status(
            client_value, target_value, comparison,
            min_value=metric_def.min_value,
            max_value=metric_def.max_value,
        ):
            clients_met += 1

    achievement_rate = 0.0
    if total_clients > 0:
        achievement_rate = round((clients_met / total_clients) * 100, 1)

    return {
        "total_clients": total_clients,
        "clients_met_target": clients_met,
        "achievement_rate": achievement_rate,
    }


def get_achievement_summary(
    program,
    date_from: date | None = None,
    date_to: date | None = None,
    metric_defs: list[MetricDefinition] | None = None,
    use_latest: bool = True,
) -> dict[str, Any]:
    """
    Calculate achievement rates for all metrics in a programme.

    For each metric, uses max_value as the target threshold when available.
    Metrics without defined targets are included but marked as having no target.

    Args:
        program: The programme to analyse.
        date_from: Start of date range (inclusive).
        date_to: End of date range (inclusive).
        metric_defs: Optional list of specific metrics to include. If None,
                     includes all metrics with data in the period.
        use_latest: If True, use client's latest value; if False, use average.

    Returns:
        dict with:
            - total_clients: Unique clients with any metric data
            - clients_met_any_target: Clients who met at least one target
            - overall_rate: Overall achievement rate across all metrics
            - by_metric: List of dicts with per-metric breakdown:
                - metric_id: MetricDefinition pk
                - metric_name: Name of the metric
                - target_value: The target threshold (max_value or None)
                - has_target: Whether this metric has a defined target
                - total_clients: Clients with data for this metric
                - clients_met_target: Clients meeting target for this metric
                - achievement_rate: Percentage for this metric
    """
    # Get clients enrolled in the programme
    client_ids = ClientProgramEnrolment.objects.filter(
        program=program, status="enrolled"
    ).values_list("client_file_id", flat=True)

    # Build note filter with date range
    note_filter = Q(client_file_id__in=client_ids, status="default")
    if date_from or date_to:
        note_filter &= _build_date_filter(date_from, date_to)

    notes = ProgressNote.objects.filter(note_filter)

    # Build metric value filter
    mv_filter = {"progress_note_target__progress_note__in": notes}
    if metric_defs:
        mv_filter["metric_def__in"] = metric_defs

    # Get all metric values
    metric_values = MetricValue.objects.filter(**mv_filter).select_related(
        "metric_def",
        "progress_note_target__progress_note__client_file",
        "progress_note_target__progress_note",
    )

    # Group values by metric and client
    # Structure: {metric_id: {client_id: [(datetime, value), ...]}}
    metric_client_values: dict[int, dict[int, list[tuple[datetime, float]]]] = {}
    metric_defs_seen: dict[int, MetricDefinition] = {}

    for mv in metric_values:
        numeric_val = _to_float(mv.value)
        if numeric_val is None:
            continue

        metric_id = mv.metric_def_id
        client_id = mv.progress_note_target.progress_note.client_file_id
        note = mv.progress_note_target.progress_note
        effective_dt = note.backdate or note.created_at

        if metric_id not in metric_client_values:
            metric_client_values[metric_id] = {}
            metric_defs_seen[metric_id] = mv.metric_def

        if client_id not in metric_client_values[metric_id]:
            metric_client_values[metric_id][client_id] = []

        metric_client_values[metric_id][client_id].append((effective_dt, numeric_val))

    # Calculate per-metric achievement rates
    by_metric = []
    all_clients_with_data: set[int] = set()
    clients_met_any: set[int] = set()

    for metric_id, client_values in metric_client_values.items():
        metric_def = metric_defs_seen[metric_id]
        target_value = metric_def.max_value
        has_target = target_value is not None

        total_clients = len(client_values)
        clients_met = 0

        for client_id, values in client_values.items():
            all_clients_with_data.add(client_id)

            if not values or not has_target:
                continue

            if use_latest:
                # Sort by date and use most recent value
                values.sort(key=lambda x: x[0] if x[0] else datetime.min)
                client_value = values[-1][1]
            else:
                # Use average of all values
                all_vals = [v[1] for v in values]
                client_value = sum(all_vals) / len(all_vals)

            # Default comparison is >= target (improvement metrics)
            if calculate_achievement_status(client_value, target_value, "gte"):
                clients_met += 1
                clients_met_any.add(client_id)

        achievement_rate = 0.0
        if total_clients > 0 and has_target:
            achievement_rate = round((clients_met / total_clients) * 100, 1)

        by_metric.append({
            "metric_id": metric_id,
            "metric_name": metric_def.name,
            "target_value": target_value,
            "has_target": has_target,
            "total_clients": total_clients,
            "clients_met_target": clients_met if has_target else None,
            "achievement_rate": achievement_rate if has_target else None,
        })

    # Calculate overall rate
    total_unique_clients = len(all_clients_with_data)
    clients_met_any_count = len(clients_met_any)
    overall_rate = 0.0
    if total_unique_clients > 0:
        overall_rate = round((clients_met_any_count / total_unique_clients) * 100, 1)

    return {
        "total_clients": total_unique_clients,
        "clients_met_any_target": clients_met_any_count,
        "overall_rate": overall_rate,
        "by_metric": by_metric,
    }


def format_achievement_summary(summary: dict[str, Any]) -> str:
    """
    Format achievement summary as a human-readable string for reports.

    Args:
        summary: The dict returned by get_achievement_summary().

    Returns:
        A formatted string suitable for CSV header or PDF text.
    """
    lines = []

    # Overall summary
    if summary["total_clients"] > 0:
        lines.append(
            f"Overall Achievement: {summary['clients_met_any_target']} of "
            f"{summary['total_clients']} clients ({summary['overall_rate']}%) "
            "met at least one target"
        )
    else:
        lines.append("No client data available for achievement calculation")

    # Per-metric breakdown
    for metric in summary.get("by_metric", []):
        if metric["has_target"]:
            lines.append(
                f"{metric['metric_name']}: {metric['clients_met_target']} of "
                f"{metric['total_clients']} clients ({metric['achievement_rate']}%) "
                f"met target of {metric['target_value']}"
            )
        else:
            lines.append(
                f"{metric['metric_name']}: {metric['total_clients']} clients "
                "(no target defined)"
            )

    return "\n".join(lines)
