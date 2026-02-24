"""Metric distribution aggregation for the Insights page.

Three core functions that power the quantitative sections of the
per-program insights page. All aggregation is per-participant (not
per-target) — see DRR §3.

Privacy: band counts < 5 are suppressed. Metrics with n < 10 are excluded.

Functions:
    get_metric_distributions  — scale metric band distributions
    get_achievement_rates     — achievement metric success rates
    get_metric_trends         — monthly band percentage time series
    get_two_lenses            — participant self-report vs staff comparison
    get_data_completeness     — enrolled vs scored participant counts
"""
import logging
from collections import defaultdict
from statistics import median

from django.db.models import DateTimeField
from django.db.models.functions import Coalesce, TruncMonth

from apps.clients.models import ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
from apps.plans.models import MetricDefinition, PlanTargetMetric, SELF_EFFICACY_METRIC_NAME

logger = logging.getLogger(__name__)

# Privacy thresholds (from DRR)
MIN_N_FOR_DISPLAY = 10      # Minimum participants for a metric section to appear
MIN_N_FOR_BAND = 5          # Suppress individual band counts below this
SUPPRESSED_LABEL = "< 5"    # Canadian n < 5 suppression standard


def _to_float(value):
    """Safely convert a metric value string to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _get_metric_values_qs(program, date_from, date_to):
    """Base queryset for MetricValues within a program and date range.

    Uses effective date (backdate if set, else created_at) for filtering.
    """
    qs = MetricValue.objects.filter(
        progress_note_target__progress_note__status="default",
        progress_note_target__progress_note__client_file__enrolments__program=program,
        progress_note_target__progress_note__client_file__enrolments__status="enrolled",
    ).annotate(
        _effective_date=Coalesce(
            "progress_note_target__progress_note__backdate",
            "progress_note_target__progress_note__created_at",
            output_field=DateTimeField(),
        ),
    )
    if date_from:
        qs = qs.filter(_effective_date__date__gte=date_from)
    if date_to:
        qs = qs.filter(_effective_date__date__lte=date_to)
    return qs


def _get_participant_id(mv):
    """Extract client_file_id from a MetricValue with select_related."""
    return mv.progress_note_target.progress_note.client_file_id


def get_metric_distributions(program, date_from, date_to):
    """Compute band distributions for each scale metric used by this program.

    Per-participant aggregation: for each participant, take the median of
    their latest scores across all their goals, then classify into bands.

    Returns:
        dict: {metric_id: {
            name, metric_id,
            band_low_count, band_mid_count, band_high_count,
            band_low_pct, band_mid_pct, band_high_pct,
            total, n_new_participants, last_recorded,
            higher_is_better, threshold_low, threshold_high,
        }}
        Metrics with total < MIN_N_FOR_DISPLAY are excluded.
        Band counts < MIN_N_FOR_BAND are replaced with SUPPRESSED_LABEL.
    """
    # Get all scale metrics used in this program's targets
    metric_ids = set(
        PlanTargetMetric.objects.filter(
            plan_target__plan_section__program=program,
            metric_def__metric_type="scale",
            metric_def__status="active",
        ).values_list("metric_def_id", flat=True)
    )
    if not metric_ids:
        return {}

    metrics = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_ids)}

    # Get all metric values in the date range
    qs = _get_metric_values_qs(program, date_from, date_to).filter(
        metric_def_id__in=metric_ids,
    ).select_related(
        "progress_note_target__progress_note",
        "progress_note_target__plan_target",
        "metric_def",
    ).order_by("-_effective_date")

    # Group values by (metric_id, client_file_id, target_id) to get latest per target
    # Structure: {metric_id: {client_id: {target_id: [values]}}}
    metric_client_target_values = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    # Track how many assessments each client has per metric (for "new" flagging)
    client_assessment_counts = defaultdict(lambda: defaultdict(int))

    for mv in qs:
        val = _to_float(mv.value)
        if val is None:
            continue
        client_id = _get_participant_id(mv)
        metric_id = mv.metric_def_id
        target_id = mv.progress_note_target.plan_target_id
        metric_client_target_values[metric_id][client_id][target_id].append(val)
        client_assessment_counts[metric_id][client_id] += 1

    results = {}

    for metric_id, client_targets in metric_client_target_values.items():
        metric_def = metrics.get(metric_id)
        if not metric_def:
            continue

        band_counts = {"band_low": 0, "band_mid": 0, "band_high": 0}
        n_new = 0  # Participants with only 1 assessment
        included_count = 0

        for client_id, targets in client_targets.items():
            total_assessments = client_assessment_counts[metric_id][client_id]
            if total_assessments <= 1:
                n_new += 1
                continue  # Exclude single-assessment participants from distributions

            # Per-participant median: take latest value per target, then median
            latest_per_target = []
            for target_id, values in targets.items():
                latest_per_target.append(values[0])  # Already ordered by -effective_date

            participant_median = median(latest_per_target)
            band = metric_def.classify_band(participant_median)
            if band:
                band_counts[band] += 1
                included_count += 1

        if included_count < MIN_N_FOR_DISPLAY:
            continue

        # Find last recorded date for this metric
        last_mv = qs.filter(metric_def_id=metric_id).first()
        last_recorded = None
        if last_mv:
            note = last_mv.progress_note_target.progress_note
            last_recorded = (note.backdate or note.created_at)
            if last_recorded:
                last_recorded = last_recorded.date() if hasattr(last_recorded, "date") else last_recorded

        # Apply privacy suppression
        def _suppress(count):
            return SUPPRESSED_LABEL if count < MIN_N_FOR_BAND else count

        results[metric_id] = {
            "name": metric_def.translated_name,
            "metric_id": metric_id,
            "band_low_count": _suppress(band_counts["band_low"]),
            "band_mid_count": _suppress(band_counts["band_mid"]),
            "band_high_count": _suppress(band_counts["band_high"]),
            "band_low_pct": round(band_counts["band_low"] / included_count * 100, 1),
            "band_mid_pct": round(band_counts["band_mid"] / included_count * 100, 1),
            "band_high_pct": round(band_counts["band_high"] / included_count * 100, 1),
            "total": included_count,
            "n_new_participants": n_new,
            "last_recorded": last_recorded,
            "higher_is_better": metric_def.higher_is_better,
            "threshold_low": metric_def.effective_threshold_low,
            "threshold_high": metric_def.effective_threshold_high,
            "is_universal": metric_def.is_universal,
            "category": metric_def.category,
        }

    # Sort: universal metrics first, then by category
    sorted_results = dict(sorted(
        results.items(),
        key=lambda item: (not item[1]["is_universal"], item[1]["category"], item[1]["name"]),
    ))

    return sorted_results


def get_achievement_rates(program, date_from, date_to):
    """Compute achievement rates for each achievement metric used by this program.

    Returns:
        dict: {metric_id: {
            name, metric_id,
            achieved_count, total, achieved_pct,
            target_rate, last_recorded,
        }}
        Metrics with total < MIN_N_FOR_DISPLAY are excluded.
    """
    metric_ids = set(
        PlanTargetMetric.objects.filter(
            plan_target__plan_section__program=program,
            metric_def__metric_type="achievement",
            metric_def__status="active",
        ).values_list("metric_def_id", flat=True)
    )
    if not metric_ids:
        return {}

    metrics = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_ids)}

    qs = _get_metric_values_qs(program, date_from, date_to).filter(
        metric_def_id__in=metric_ids,
    ).select_related(
        "progress_note_target__progress_note",
        "metric_def",
    ).order_by("-_effective_date")

    # Get latest value per participant per metric
    # {metric_id: {client_id: latest_value_string}}
    metric_client_values = defaultdict(dict)

    for mv in qs:
        client_id = _get_participant_id(mv)
        metric_id = mv.metric_def_id
        if client_id not in metric_client_values[metric_id]:
            metric_client_values[metric_id][client_id] = mv.value

    results = {}

    for metric_id, client_values in metric_client_values.items():
        metric_def = metrics.get(metric_id)
        if not metric_def:
            continue

        total = len(client_values)
        if total < MIN_N_FOR_DISPLAY:
            continue

        success_values = set(metric_def.achievement_success_values or [])
        achieved = sum(1 for v in client_values.values() if v in success_values)

        # Find last recorded date
        last_mv = qs.filter(metric_def_id=metric_id).first()
        last_recorded = None
        if last_mv:
            note = last_mv.progress_note_target.progress_note
            last_recorded = (note.backdate or note.created_at)
            if last_recorded:
                last_recorded = last_recorded.date() if hasattr(last_recorded, "date") else last_recorded

        results[metric_id] = {
            "name": metric_def.translated_name,
            "metric_id": metric_id,
            "achieved_count": achieved,
            "total": total,
            "achieved_pct": round(achieved / total * 100, 1),
            "target_rate": metric_def.target_rate,
            "last_recorded": last_recorded,
        }

    return results


def get_metric_trends(program, date_from, date_to):
    """Compute monthly band percentage trends for each scale metric.

    Returns:
        dict: {metric_id: [
            {month, band_low_pct, band_high_pct, total}
        ]}
        Months with total < MIN_N_FOR_DISPLAY are excluded.
    """
    metric_ids = set(
        PlanTargetMetric.objects.filter(
            plan_target__plan_section__program=program,
            metric_def__metric_type="scale",
            metric_def__status="active",
        ).values_list("metric_def_id", flat=True)
    )
    if not metric_ids:
        return {}

    metrics = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_ids)}

    qs = _get_metric_values_qs(program, date_from, date_to).filter(
        metric_def_id__in=metric_ids,
    ).annotate(
        month=TruncMonth("_effective_date"),
    ).select_related(
        "progress_note_target__progress_note",
        "progress_note_target__plan_target",
        "metric_def",
    ).order_by("month", "-_effective_date")

    # Group by (metric_id, month, client_id, target_id)
    # Structure: {metric_id: {month: {client_id: {target_id: [values]}}}}
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    for mv in qs:
        val = _to_float(mv.value)
        if val is None:
            continue
        month_str = mv.month.strftime("%Y-%m")
        client_id = _get_participant_id(mv)
        metric_id = mv.metric_def_id
        target_id = mv.progress_note_target.plan_target_id
        data[metric_id][month_str][client_id][target_id].append(val)

    results = {}

    for metric_id, months in data.items():
        metric_def = metrics.get(metric_id)
        if not metric_def:
            continue

        trend = []
        for month_str in sorted(months.keys()):
            clients = months[month_str]
            band_counts = {"band_low": 0, "band_mid": 0, "band_high": 0}
            included = 0

            for client_id, targets in clients.items():
                latest_per_target = [vals[0] for vals in targets.values()]
                participant_median = median(latest_per_target)
                band = metric_def.classify_band(participant_median)
                if band:
                    band_counts[band] += 1
                    included += 1

            if included < MIN_N_FOR_DISPLAY:
                continue

            trend.append({
                "month": month_str,
                "band_low_pct": round(band_counts["band_low"] / included * 100, 1),
                "band_high_pct": round(band_counts["band_high"] / included * 100, 1),
                "total": included,
            })

        if trend:
            results[metric_id] = trend

    return results


def get_two_lenses(program, date_from, date_to, distributions=None):
    """Compare participant self-report (Self-Efficacy) with staff descriptor data.

    Args:
        distributions: Pre-computed result from get_metric_distributions().
            If None, distributions will be computed (extra DB query).

    Returns:
        dict or None: {
            self_report_pct, staff_pct, gap, gap_direction,
            has_sufficient_data,
        }
        Returns None if either data stream has n < MIN_N_FOR_DISPLAY.
    """
    # Self-report: % of participants in high band for Self-Efficacy
    self_efficacy = MetricDefinition.objects.filter(
        name=SELF_EFFICACY_METRIC_NAME,
        metric_type="scale",
        status="active",
    ).first()

    if not self_efficacy:
        return None

    # Get Self-Efficacy distributions (reuse pre-computed if available)
    if distributions is None:
        distributions = get_metric_distributions(program, date_from, date_to)
    se_dist = distributions.get(self_efficacy.pk)
    if not se_dist or se_dist["total"] < MIN_N_FOR_DISPLAY:
        return None

    self_report_pct = se_dist["band_high_pct"]

    # Staff descriptor data: % rated "good_place"
    notes_qs = ProgressNote.objects.filter(
        status="default",
        client_file__enrolments__program=program,
        client_file__enrolments__status="enrolled",
    ).annotate(
        _effective_date=Coalesce("backdate", "created_at", output_field=DateTimeField()),
    )
    if date_from:
        notes_qs = notes_qs.filter(_effective_date__date__gte=date_from)
    if date_to:
        notes_qs = notes_qs.filter(_effective_date__date__lte=date_to)

    targets_qs = ProgressNoteTarget.objects.filter(
        progress_note__in=notes_qs,
    ).exclude(progress_descriptor="")

    total_descriptors = targets_qs.count()
    if total_descriptors < MIN_N_FOR_DISPLAY:
        return None

    good_place_count = targets_qs.filter(progress_descriptor="good_place").count()
    staff_pct = round(good_place_count / total_descriptors * 100, 1)

    gap = round(self_report_pct - staff_pct, 1)
    if gap > 0:
        gap_direction = "participants_higher"
    elif gap < 0:
        gap_direction = "staff_higher"
    else:
        gap_direction = "aligned"

    return {
        "self_report_pct": self_report_pct,
        "staff_pct": staff_pct,
        "gap": gap,
        "gap_abs": abs(gap),
        "gap_direction": gap_direction,
        "has_sufficient_data": True,
    }


def get_data_completeness(program, date_from, date_to):
    """Count enrolled participants vs those with metric scores in the period.

    Returns:
        dict: {
            enrolled_count, with_scores_count, completeness_pct,
            completeness_level ("full" / "partial" / "low"),
        }
    """
    enrolled_count = (
        ClientProgramEnrolment.objects.filter(
            program=program,
            status="enrolled",
        )
        .values("client_file_id")
        .distinct()
        .count()
    )

    if enrolled_count == 0:
        return {
            "enrolled_count": 0,
            "with_scores_count": 0,
            "completeness_pct": 0,
            "completeness_level": "low",
        }

    # Count participants with at least one MetricValue in the date range
    mv_qs = _get_metric_values_qs(program, date_from, date_to).exclude(value="")
    with_scores_count = (
        mv_qs.values("progress_note_target__progress_note__client_file_id")
        .distinct()
        .count()
    )

    completeness_pct = round(with_scores_count / enrolled_count * 100, 1)

    if completeness_pct > 80:
        level = "full"
    elif completeness_pct >= 50:
        level = "partial"
    else:
        level = "low"

    return {
        "enrolled_count": enrolled_count,
        "with_scores_count": with_scores_count,
        "completeness_pct": completeness_pct,
        "completeness_level": level,
    }


def get_trend_direction(trends, metric_id):
    """Determine trend direction for a metric from its monthly data.

    Returns "improving", "stable", or "declining" based on the last 3 months
    of band_high_pct changes.
    """
    metric_trends = trends.get(metric_id, [])
    if len(metric_trends) < 2:
        return "stable"

    recent = metric_trends[-3:]  # Last 3 months
    first_high = recent[0]["band_high_pct"]
    last_high = recent[-1]["band_high_pct"]
    change = last_high - first_high

    if change > 5:
        return "improving"
    elif change < -5:
        return "declining"
    return "stable"
