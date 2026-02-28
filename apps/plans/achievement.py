"""Achievement status derivation for PlanTarget (Phase F2).

Computes achievement_status from MetricValues (quantitative path) or
ProgressNoteTarget.progress_descriptor (qualitative path).

Called when a ProgressNote is saved that includes a ProgressNoteTarget
for the goal.  Result is stored on PlanTarget for direct reporting queries.
"""

from django.utils import timezone


def compute_achievement_status(plan_target):
    """Derive achievement_status from recorded data.

    Returns (status, source) tuple.  Does NOT write to the model — caller
    decides whether to save (respecting worker overrides).

    Never returns 'not_attainable' — that requires deliberate worker action.
    """
    from apps.notes.models import MetricValue, ProgressNoteTarget

    # Get the primary metric (first linked metric)
    primary_metric = plan_target.metrics.first()

    if primary_metric:
        return _compute_quantitative(plan_target, primary_metric)
    else:
        return _compute_qualitative(plan_target)


def _compute_quantitative(plan_target, metric_def):
    """Compute from MetricValues for the primary metric.

    Uses last 3 recorded values, respecting higher_is_better direction
    and max_value as target threshold.
    """
    from apps.notes.models import MetricValue

    # Get metric values for this target+metric, ordered by creation date
    values = list(
        MetricValue.objects.filter(
            progress_note_target__plan_target=plan_target,
            metric_def=metric_def,
        )
        .order_by("created_at")
        .values_list("value", flat=True)
    )

    # Parse to floats, skipping non-numeric
    numeric_values = []
    for v in values:
        try:
            numeric_values.append(float(v))
        except (ValueError, TypeError):
            continue

    if not numeric_values:
        return "in_progress", "auto_computed"

    higher_is_better = metric_def.higher_is_better
    target_threshold = metric_def.max_value  # max_value serves as target

    latest = numeric_values[-1]
    was_achieved = bool(plan_target.first_achieved_at)

    # Check if latest meets target
    if target_threshold is not None:
        if higher_is_better:
            meets_target = latest >= target_threshold
        else:
            meets_target = latest <= target_threshold

        if meets_target:
            if was_achieved:
                return "sustaining", "auto_computed"
            return "achieved", "auto_computed"

        # Previously achieved but now dropped
        if was_achieved:
            return "worsening", "auto_computed"

    # Sparse data rules
    count = len(numeric_values)

    if count == 1:
        return "in_progress", "auto_computed"

    if count == 2:
        return _direction_from_pair(
            numeric_values[-2], numeric_values[-1], higher_is_better
        )

    # 3+ points: use last 3 for trend analysis
    last_three = numeric_values[-3:]
    return _trend_from_three(last_three, higher_is_better)


def _direction_from_pair(prev, current, higher_is_better):
    """Simple 2-point comparison."""
    if higher_is_better:
        if current > prev:
            return "improving", "auto_computed"
        elif current < prev:
            return "worsening", "auto_computed"
    else:
        if current < prev:
            return "improving", "auto_computed"
        elif current > prev:
            return "worsening", "auto_computed"
    return "no_change", "auto_computed"


def _trend_from_three(values, higher_is_better):
    """3-point trend: 2 of 3 showing improvement/decline determines direction."""
    improving_count = 0
    worsening_count = 0

    for i in range(1, len(values)):
        if higher_is_better:
            if values[i] > values[i - 1]:
                improving_count += 1
            elif values[i] < values[i - 1]:
                worsening_count += 1
        else:
            if values[i] < values[i - 1]:
                improving_count += 1
            elif values[i] > values[i - 1]:
                worsening_count += 1

    if improving_count >= 2:
        return "improving", "auto_computed"
    if worsening_count >= 2:
        return "worsening", "auto_computed"
    return "no_change", "auto_computed"


def _compute_qualitative(plan_target):
    """Map from latest ProgressNoteTarget.progress_descriptor."""
    from apps.notes.models import ProgressNoteTarget

    latest_entry = (
        ProgressNoteTarget.objects.filter(
            plan_target=plan_target,
            progress_descriptor__in=["harder", "holding", "shifting", "good_place"],
        )
        .order_by("-created_at")
        .first()
    )

    if not latest_entry:
        return "in_progress", "auto_computed"

    descriptor = latest_entry.progress_descriptor
    was_achieved = bool(plan_target.first_achieved_at)

    DESCRIPTOR_MAP = {
        "harder": "worsening",
        "holding": "no_change",
        "shifting": "improving",
    }

    if descriptor == "good_place":
        if was_achieved:
            return "sustaining", "auto_computed"
        return "achieved", "auto_computed"

    return DESCRIPTOR_MAP.get(descriptor, "in_progress"), "auto_computed"


def update_achievement_status(plan_target):
    """Compute and save achievement status, respecting worker overrides.

    Only overwrites if source is 'auto_computed' or empty.
    Sets first_achieved_at when status becomes 'achieved' for the first time.
    """
    # Don't overwrite worker assessments
    if plan_target.achievement_status_source == "worker_assessed":
        return

    status, source = compute_achievement_status(plan_target)

    # Never auto-set not_attainable
    if status == "not_attainable":
        return

    plan_target.achievement_status = status
    plan_target.achievement_status_source = source
    plan_target.achievement_status_updated_at = timezone.now()

    # Set first_achieved_at when first achieved — never clear it
    if status in ("achieved", "sustaining") and not plan_target.first_achieved_at:
        plan_target.first_achieved_at = timezone.now()

    plan_target.save(update_fields=[
        "achievement_status",
        "achievement_status_source",
        "achievement_status_updated_at",
        "first_achieved_at",
    ])
