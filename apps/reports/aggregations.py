"""Report aggregation utilities for metric data analysis.

Provides functions to aggregate MetricValue data by various groupings:
- Count (number of clients, notes, or values)
- Average (mean metric value)
- Min/Max (range of values)
- Sum (total values)

All functions handle null/invalid values gracefully and convert string
values to floats where needed.
"""
from datetime import date, datetime, time
from typing import Any

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote
from apps.plans.models import MetricDefinition, PlanTarget


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


def metric_stats(metric_values_qs: QuerySet[MetricValue]) -> dict[str, Any]:
    """
    Calculate aggregate statistics for a queryset of MetricValue objects.

    Returns a dict with count, avg, min, max, sum, and valid_count.
    Invalid/non-numeric values are excluded from calculations but included
    in count.

    Args:
        metric_values_qs: A QuerySet of MetricValue objects.

    Returns:
        dict with keys: count, valid_count, avg, min, max, sum
        - count: total number of values (including invalid)
        - valid_count: number of valid numeric values
        - avg: mean of valid values (None if no valid values)
        - min: minimum valid value (None if no valid values)
        - max: maximum valid value (None if no valid values)
        - sum: sum of valid values (None if no valid values)
    """
    total_count = 0
    valid_values = []

    for mv in metric_values_qs:
        total_count += 1
        numeric_val = _to_float(mv.value)
        if numeric_val is not None:
            valid_values.append(numeric_val)

    valid_count = len(valid_values)

    if valid_count == 0:
        return {
            "count": total_count,
            "valid_count": 0,
            "avg": None,
            "min": None,
            "max": None,
            "sum": None,
        }

    total_sum = sum(valid_values)
    return {
        "count": total_count,
        "valid_count": valid_count,
        "avg": total_sum / valid_count,
        "min": min(valid_values),
        "max": max(valid_values),
        "sum": total_sum,
    }


def count_clients_by_program(
    program,
    date_from: date | None = None,
    date_to: date | None = None,
    active_only: bool = True,
) -> int:
    """
    Count unique clients enrolled in a program within a date range.

    Args:
        program: A Program instance to filter by.
        date_from: Start of date range (inclusive). If None, no lower bound.
        date_to: End of date range (inclusive). If None, no upper bound.
        active_only: If True, only count clients with active enrolment status.

    Returns:
        Count of unique clients enrolled in the program.
    """
    enrolment_filter = {"program": program}
    if active_only:
        enrolment_filter["status"] = "active"

    client_ids = ClientProgramEnrolment.objects.filter(
        **enrolment_filter
    ).values_list("client_file_id", flat=True)

    if not date_from and not date_to:
        return len(set(client_ids))

    # Filter clients who have notes in the date range
    date_filter = _build_date_filter(date_from, date_to)
    clients_with_notes = (
        ProgressNote.objects.filter(
            client_file_id__in=client_ids,
            status="default",
        )
        .filter(date_filter)
        .values_list("client_file_id", flat=True)
        .distinct()
    )

    return clients_with_notes.count()


def average_metric_by_target(
    metric_def: MetricDefinition,
    target: PlanTarget,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    """
    Calculate the average metric value for a specific target.

    Args:
        metric_def: The MetricDefinition to aggregate.
        target: The PlanTarget to filter by.
        date_from: Start of date range (inclusive).
        date_to: End of date range (inclusive).

    Returns:
        dict with keys: avg, count, valid_count, min, max, sum
    """
    # Base query for metric values on this target
    mv_qs = MetricValue.objects.filter(
        metric_def=metric_def,
        progress_note_target__plan_target=target,
        progress_note_target__progress_note__status="default",
    ).select_related(
        "progress_note_target__progress_note"
    )

    # Apply date filtering if provided
    if date_from or date_to:
        date_filter = _build_date_filter(date_from, date_to)
        # We need to filter via the related progress note
        note_ids = (
            ProgressNote.objects.filter(date_filter, status="default")
            .values_list("pk", flat=True)
        )
        mv_qs = mv_qs.filter(
            progress_note_target__progress_note_id__in=note_ids
        )

    return metric_stats(mv_qs)


def aggregate_metrics(
    queryset: QuerySet[MetricValue],
    group_by: str = "none",
) -> dict[str, dict[str, Any]]:
    """
    Flexible aggregation of MetricValue queryset with grouping options.

    Args:
        queryset: A QuerySet of MetricValue objects.
        group_by: Grouping option - one of:
            - "none": No grouping, return overall stats
            - "metric": Group by metric definition
            - "target": Group by plan target
            - "client": Group by client
            - "date": Group by effective date (YYYY-MM-DD)

    Returns:
        dict mapping group keys to stats dicts (from metric_stats).
        For group_by="none", returns {"all": stats}.
    """
    if group_by == "none":
        return {"all": metric_stats(queryset)}

    # Prefetch related objects for efficient grouping
    if group_by == "metric":
        queryset = queryset.select_related("metric_def")
    elif group_by in ("target", "client", "date"):
        queryset = queryset.select_related(
            "progress_note_target__progress_note__client_file",
            "progress_note_target__plan_target",
        )

    groups: dict[str, list[MetricValue]] = {}

    for mv in queryset:
        if group_by == "metric":
            key = str(mv.metric_def_id)
        elif group_by == "target":
            key = str(mv.progress_note_target.plan_target_id)
        elif group_by == "client":
            key = str(mv.progress_note_target.progress_note.client_file_id)
        elif group_by == "date":
            note = mv.progress_note_target.progress_note
            effective = note.backdate or note.created_at
            key = effective.strftime("%Y-%m-%d") if effective else "unknown"
        else:
            key = "all"

        if key not in groups:
            groups[key] = []
        groups[key].append(mv)

    # Calculate stats for each group
    results = {}
    for key, values in groups.items():
        # Create a simple list wrapper that iterates like a queryset
        results[key] = _stats_from_list(values)

    return results


def _stats_from_list(metric_values: list[MetricValue]) -> dict[str, Any]:
    """Calculate stats from a list of MetricValue objects (not a queryset)."""
    total_count = len(metric_values)
    valid_values = []

    for mv in metric_values:
        numeric_val = _to_float(mv.value)
        if numeric_val is not None:
            valid_values.append(numeric_val)

    valid_count = len(valid_values)

    if valid_count == 0:
        return {
            "count": total_count,
            "valid_count": 0,
            "avg": None,
            "min": None,
            "max": None,
            "sum": None,
        }

    total_sum = sum(valid_values)
    return {
        "count": total_count,
        "valid_count": valid_count,
        "avg": total_sum / valid_count,
        "min": min(valid_values),
        "max": max(valid_values),
        "sum": total_sum,
    }


def get_metric_values_for_program(
    program,
    metric_defs: list[MetricDefinition] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    active_enrolments_only: bool = True,
) -> QuerySet[MetricValue]:
    """
    Get all MetricValue objects for clients enrolled in a program.

    This is a utility function to build the base queryset for aggregation.

    Args:
        program: A Program instance to filter by.
        metric_defs: Optional list of MetricDefinition to filter by.
        date_from: Start of date range (inclusive).
        date_to: End of date range (inclusive).
        active_enrolments_only: If True, only include actively enrolled clients.

    Returns:
        QuerySet of MetricValue objects with related objects prefetched.
    """
    # Get client IDs for the program
    enrolment_filter = {"program": program}
    if active_enrolments_only:
        enrolment_filter["status"] = "active"

    client_ids = ClientProgramEnrolment.objects.filter(
        **enrolment_filter
    ).values_list("client_file_id", flat=True)

    # Build note filter
    note_filter = Q(client_file_id__in=client_ids, status="default")
    if date_from or date_to:
        date_filter = _build_date_filter(date_from, date_to)
        note_filter &= date_filter

    notes = ProgressNote.objects.filter(note_filter)

    # Build metric value queryset
    mv_filter = {"progress_note_target__progress_note__in": notes}
    if metric_defs:
        mv_filter["metric_def__in"] = metric_defs

    return MetricValue.objects.filter(**mv_filter).select_related(
        "metric_def",
        "progress_note_target__progress_note__client_file",
        "progress_note_target__plan_target",
    )


def count_notes_by_program(
    program,
    date_from: date | None = None,
    date_to: date | None = None,
    note_type: str | None = None,
) -> int:
    """
    Count progress notes for clients in a program.

    Args:
        program: A Program instance to filter by.
        date_from: Start of date range (inclusive).
        date_to: End of date range (inclusive).
        note_type: Optional filter for note type ("quick" or "full").

    Returns:
        Count of progress notes.
    """
    client_ids = ClientProgramEnrolment.objects.filter(
        program=program, status="active"
    ).values_list("client_file_id", flat=True)

    note_filter = Q(client_file_id__in=client_ids, status="default")

    if date_from or date_to:
        date_filter = _build_date_filter(date_from, date_to)
        note_filter &= date_filter

    if note_type:
        note_filter &= Q(note_type=note_type)

    return ProgressNote.objects.filter(note_filter).count()


def count_contacts_by_outcome(
    program,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, int]:
    """
    Count contact notes by outcome for funder reporting.

    Counts ProgressNotes with contact interaction types (phone, sms, email)
    and splits by outcome (reached vs. attempted).

    Returns:
        Dict with keys: total_contacts, successful_contacts, contact_attempts
    """
    client_ids = ClientProgramEnrolment.objects.filter(
        program=program, status="active"
    ).values_list("client_file_id", flat=True)

    note_filter = Q(
        client_file_id__in=client_ids,
        status="default",
        interaction_type__in=("phone", "sms", "email"),
    )

    if date_from or date_to:
        date_filter = _build_date_filter(date_from, date_to)
        note_filter &= date_filter

    contacts = ProgressNote.objects.filter(note_filter)
    total = contacts.count()
    successful = contacts.filter(outcome="reached").count()
    attempts = contacts.filter(outcome__in=("no_answer", "left_message")).count()

    return {
        "total_contacts": total,
        "successful_contacts": successful,
        "contact_attempts": attempts,
    }
