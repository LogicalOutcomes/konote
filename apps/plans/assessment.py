"""Assessment-due detection for standardized instruments.

Checks which standardized assessments (PHQ-9, GAD-7, etc.) are due for a
client based on their active plan targets, intake rules, and periodic
re-administration intervals.
"""
import datetime

from django.db.models import Max
from django.utils import timezone


def get_assessments_due(client, program_ids=None):
    """Return list of dicts for assessments due for this client.

    Each dict: {metric_def, last_date, days_overdue, reason}
    reason: 'intake' | 'periodic'

    Only considers MetricDefinitions with is_standardized_instrument=True
    that are linked to the client's active plan targets via PlanTargetMetric.

    Args:
        client: ClientFile instance
        program_ids: optional iterable of program IDs to restrict the search
    """
    from apps.notes.models import MetricValue
    from apps.plans.models import MetricDefinition, PlanTarget, PlanTargetMetric

    # Find active plan targets for this client, optionally filtered by program
    target_qs = PlanTarget.objects.filter(
        client_file=client,
        status="default",
    )
    if program_ids is not None:
        target_qs = target_qs.filter(plan_section__program_id__in=program_ids)

    target_ids = list(target_qs.values_list("pk", flat=True))
    if not target_ids:
        return []

    # Find standardized instrument metrics linked to those targets
    ptm_qs = PlanTargetMetric.objects.filter(
        plan_target_id__in=target_ids,
        metric_def__is_standardized_instrument=True,
        metric_def__status="active",
    ).select_related("metric_def")

    # Deduplicate by metric_def (a metric may appear on multiple targets)
    seen_metric_ids = set()
    metric_defs = []
    for ptm in ptm_qs:
        if ptm.metric_def_id not in seen_metric_ids:
            seen_metric_ids.add(ptm.metric_def_id)
            metric_defs.append(ptm.metric_def)

    if not metric_defs:
        return []

    # Get the latest MetricValue date for each metric_def for this client
    latest_dates = dict(
        MetricValue.objects.filter(
            metric_def_id__in=[md.pk for md in metric_defs],
            progress_note_target__progress_note__client_file=client,
            progress_note_target__progress_note__status="default",
        ).values("metric_def_id").annotate(
            last_date=Max("created_at"),
        ).values_list("metric_def_id", "last_date")
    )

    today = timezone.now()
    results = []

    for md in metric_defs:
        last_date = latest_dates.get(md.pk)

        # Intake check: assessment_at_intake=True and no MetricValue exists
        if md.assessment_at_intake and last_date is None:
            results.append({
                "metric_def": md,
                "last_date": None,
                "days_overdue": None,
                "reason": "intake",
            })
            continue

        # Periodic check: assessment_interval_days is set and enough time has passed
        if md.assessment_interval_days and last_date is not None:
            days_since = (today - last_date).days
            if days_since > md.assessment_interval_days:
                results.append({
                    "metric_def": md,
                    "last_date": last_date,
                    "days_overdue": days_since - md.assessment_interval_days,
                    "reason": "periodic",
                })

    return results
