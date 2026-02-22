"""Metric distribution aggregation for the Insights page.

Produces per-participant distributions for scale metrics, achievement rates
for achievement metrics, trend data for Chart.js, Two Lenses comparison,
and data completeness.  All aggregation is per-participant (not per-target)
to avoid over-counting people with many goals.

Privacy thresholds (from DRR):
  - Band counts < 5 → suppress (return "< 5")
  - Metric total n < 10 → skip entirely
"""
import statistics
from collections import defaultdict
from django.db.models import DateTimeField
from django.db.models.functions import Coalesce, TruncMonth

from apps.clients.models import ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
from apps.plans.models import MetricDefinition

# Privacy thresholds
MIN_N_FOR_DISTRIBUTION = 10
MIN_BAND_COUNT = 5


def _effective_date_annotation():
    """Return Coalesce expression for effective date (backdate preferred)."""
    return Coalesce(
        "progress_note_target__progress_note__backdate",
        "progress_note_target__progress_note__created_at",
        output_field=DateTimeField(),
    )


def _base_metric_values_qs(program, date_from, date_to):
    """Base queryset for MetricValues in a program within a date range."""
    qs = MetricValue.objects.filter(
        progress_note_target__progress_note__status="default",
        progress_note_target__progress_note__client_file__enrolments__program=program,
        progress_note_target__progress_note__client_file__enrolments__status="enrolled",
    ).annotate(
        _effective_date=_effective_date_annotation(),
    )
    if date_from:
        qs = qs.filter(_effective_date__date__gte=date_from)
    if date_to:
        qs = qs.filter(_effective_date__date__lte=date_to)
    return qs


def _classify_band(value, threshold_low, threshold_high, higher_is_better):
    """Classify a numeric value into band_low, band_mid, or band_high."""
    if higher_is_better:
        if value <= threshold_low:
            return "band_low"
        elif value >= threshold_high:
            return "band_high"
        else:
            return "band_mid"
    else:
        # Lower is better (e.g. PHQ-9): low score = good
        if value <= threshold_low:
            return "band_high"
        elif value >= threshold_high:
            return "band_low"
        else:
            return "band_mid"


def _get_thresholds(metric_def):
    """Return (threshold_low, threshold_high) with fallback to scale-thirds."""
    if metric_def.threshold_low is not None and metric_def.threshold_high is not None:
        return (metric_def.threshold_low, metric_def.threshold_high)
    # Fallback: thirds of the range
    min_val = metric_def.min_value if metric_def.min_value is not None else 1
    max_val = metric_def.max_value if metric_def.max_value is not None else 5
    range_size = max_val - min_val
    return (min_val + range_size / 3, min_val + 2 * range_size / 3)


def _suppress_band_count(count):
    """Return '< 5' string if count is below privacy threshold, else the count."""
    if count < MIN_BAND_COUNT:
        return "< 5"
    return count


def get_metric_distributions(program, date_from, date_to):
    """Compute per-participant band distributions for each scale metric.

    Returns:
        dict: {metric_id: {
            name, metric_def_id, band_low_count, band_mid_count, band_high_count,
            total, band_low_pct, band_mid_pct, band_high_pct,
            n_new_participants, last_recorded, higher_is_better,
            target_band_high_pct, is_universal,
        }}
    """
    qs = _base_metric_values_qs(program, date_from, date_to)
    # Only scale metrics
    qs = qs.filter(metric_def__metric_type="scale")

    # Collect all values grouped by metric and participant
    # metric_id → client_file_id → list of (value, effective_date, assessment_count_for_participant)
    metric_participant_values = defaultdict(lambda: defaultdict(list))
    # Track how many assessments each participant has per metric
    metric_participant_assessment_count = defaultdict(lambda: defaultdict(int))
    metric_defs = {}
    last_recorded_per_metric = {}

    values_data = qs.select_related("metric_def").values_list(
        "pk",  # MetricValue PK for distinct rows
        "metric_def_id",
        "progress_note_target__plan_target__client_file_id",
        "value",
        "_effective_date",
    ).distinct()

    for mv_pk, metric_def_id, client_file_id, raw_value, effective_date in values_data:
        try:
            numeric_value = float(raw_value)
        except (ValueError, TypeError):
            continue
        metric_participant_values[metric_def_id][client_file_id].append(numeric_value)
        metric_participant_assessment_count[metric_def_id][client_file_id] += 1
        # Track last recorded
        if metric_def_id not in last_recorded_per_metric or effective_date > last_recorded_per_metric[metric_def_id]:
            last_recorded_per_metric[metric_def_id] = effective_date

    # Load metric definitions for all found metrics
    metric_ids = list(metric_participant_values.keys())
    if metric_ids:
        for md in MetricDefinition.objects.filter(pk__in=metric_ids):
            metric_defs[md.pk] = md

    results = {}
    for metric_id, participant_values in metric_participant_values.items():
        metric_def = metric_defs.get(metric_id)
        if not metric_def:
            continue

        threshold_low, threshold_high = _get_thresholds(metric_def)

        # Per-participant: take median across their goals, exclude new participants (1 assessment)
        band_counts = {"band_low": 0, "band_mid": 0, "band_high": 0}
        n_new = 0
        included_count = 0

        for client_id, values in participant_values.items():
            assessment_count = metric_participant_assessment_count[metric_id][client_id]
            if assessment_count <= 1:
                n_new += 1
                continue

            median_val = statistics.median(values)
            band = _classify_band(median_val, threshold_low, threshold_high, metric_def.higher_is_better)
            band_counts[band] += 1
            included_count += 1

        # Skip if insufficient data
        if included_count < MIN_N_FOR_DISTRIBUTION:
            continue

        total = included_count
        results[metric_id] = {
            "name": metric_def.translated_name,
            "metric_def_id": metric_id,
            "band_low_count": _suppress_band_count(band_counts["band_low"]),
            "band_mid_count": _suppress_band_count(band_counts["band_mid"]),
            "band_high_count": _suppress_band_count(band_counts["band_high"]),
            "band_low_pct": round(band_counts["band_low"] / total * 100, 1) if total else 0,
            "band_mid_pct": round(band_counts["band_mid"] / total * 100, 1) if total else 0,
            "band_high_pct": round(band_counts["band_high"] / total * 100, 1) if total else 0,
            "total": total,
            "n_new_participants": n_new,
            "last_recorded": last_recorded_per_metric.get(metric_id),
            "higher_is_better": metric_def.higher_is_better,
            "target_band_high_pct": metric_def.target_band_high_pct,
            "is_universal": metric_def.is_universal,
        }

    return results


def get_achievement_rates(program, date_from, date_to):
    """Compute achievement rates for achievement metrics.

    Returns:
        dict: {metric_id: {
            name, achieved_count, total, achieved_pct, target_rate,
            last_recorded,
        }}
    """
    qs = _base_metric_values_qs(program, date_from, date_to)
    qs = qs.filter(metric_def__metric_type="achievement")

    # Group by metric and participant — take latest value per participant
    # metric_id → client_file_id → (value, effective_date)
    metric_participant_latest = defaultdict(dict)
    metric_defs = {}

    values_data = qs.values_list(
        "pk",
        "metric_def_id",
        "progress_note_target__plan_target__client_file_id",
        "value",
        "_effective_date",
    ).distinct()

    for mv_pk, metric_def_id, client_file_id, raw_value, effective_date in values_data:
        existing = metric_participant_latest[metric_def_id].get(client_file_id)
        if existing is None or effective_date > existing[1]:
            metric_participant_latest[metric_def_id][client_file_id] = (raw_value, effective_date)

    metric_ids = list(metric_participant_latest.keys())
    if metric_ids:
        for md in MetricDefinition.objects.filter(pk__in=metric_ids):
            metric_defs[md.pk] = md

    results = {}
    for metric_id, participant_values in metric_participant_latest.items():
        metric_def = metric_defs.get(metric_id)
        if not metric_def:
            continue

        total = len(participant_values)
        if total < MIN_N_FOR_DISTRIBUTION:
            continue

        success_values = set(metric_def.achievement_success_values or [])
        achieved = sum(1 for val, _ in participant_values.values() if val in success_values)

        last_date = max(dt for _, dt in participant_values.values())

        results[metric_id] = {
            "name": metric_def.translated_name,
            "achieved_count": achieved,
            "total": total,
            "achieved_pct": round(achieved / total * 100, 1) if total else 0,
            "target_rate": metric_def.target_rate,
            "last_recorded": last_date,
        }

    return results


def get_metric_trends(program, date_from, date_to):
    """Compute monthly band distributions for trend charts.

    Returns:
        dict: {metric_id: [
            {month, band_low_pct, band_high_pct, total},
        ]}
    """
    qs = _base_metric_values_qs(program, date_from, date_to)
    qs = qs.filter(metric_def__metric_type="scale")

    # Annotate with month
    qs = qs.annotate(month=TruncMonth("_effective_date"))

    # Collect: metric_id → month → client_file_id → [values]
    metric_month_participant = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    # Also track assessment counts per participant per metric (across all months)
    metric_participant_total_assessments = defaultdict(lambda: defaultdict(int))
    metric_defs = {}

    values_data = qs.values_list(
        "pk",
        "metric_def_id",
        "progress_note_target__plan_target__client_file_id",
        "value",
        "month",
    ).distinct()

    for mv_pk, metric_def_id, client_file_id, raw_value, month in values_data:
        try:
            numeric_value = float(raw_value)
        except (ValueError, TypeError):
            continue
        month_str = month.strftime("%Y-%m")
        metric_month_participant[metric_def_id][month_str][client_file_id].append(numeric_value)
        metric_participant_total_assessments[metric_def_id][client_file_id] += 1

    metric_ids = list(metric_month_participant.keys())
    if metric_ids:
        for md in MetricDefinition.objects.filter(pk__in=metric_ids):
            metric_defs[md.pk] = md

    results = {}
    for metric_id, months_data in metric_month_participant.items():
        metric_def = metric_defs.get(metric_id)
        if not metric_def:
            continue

        threshold_low, threshold_high = _get_thresholds(metric_def)
        trend_points = []

        for month_str in sorted(months_data.keys()):
            participants = months_data[month_str]
            band_counts = {"band_low": 0, "band_mid": 0, "band_high": 0}
            included = 0

            for client_id, values in participants.items():
                # Skip new participants (only 1 assessment total for this metric)
                if metric_participant_total_assessments[metric_id][client_id] <= 1:
                    continue
                median_val = statistics.median(values)
                band = _classify_band(median_val, threshold_low, threshold_high, metric_def.higher_is_better)
                band_counts[band] += 1
                included += 1

            if included < MIN_N_FOR_DISTRIBUTION:
                continue

            trend_points.append({
                "month": month_str,
                "band_low_pct": round(band_counts["band_low"] / included * 100, 1),
                "band_high_pct": round(band_counts["band_high"] / included * 100, 1),
                "total": included,
            })

        if trend_points:
            results[metric_id] = trend_points

    return results


def get_two_lenses(program, date_from, date_to, structured=None, distributions=None):
    """Compare participant self-report vs. staff assessment.

    When program has both Self-Efficacy data and staff descriptors with n >= 10,
    returns the gap between participant self-report high band % and staff
    'good_place' descriptor %.

    Args:
        structured: Pre-computed result from get_structured_insights() (avoids re-query).
        distributions: Pre-computed result from get_metric_distributions() (avoids re-query).

    Returns:
        dict or None: {self_report_pct, staff_pct, gap, n_self_report, n_staff,
                       has_sufficient_data}
    """
    # Use pre-computed data if available, otherwise fetch
    if structured is None:
        from apps.reports.insights import get_structured_insights
        structured = get_structured_insights(program=program, date_from=date_from, date_to=date_to)

    staff_good_place_pct = structured.get("descriptor_distribution", {}).get("In a good place", 0)
    staff_participant_count = structured.get("participant_count", 0)

    if staff_participant_count < MIN_N_FOR_DISTRIBUTION:
        return None

    if distributions is None:
        distributions = get_metric_distributions(program, date_from, date_to)

    # Find Self-Efficacy metric in distributions
    from apps.plans.models import SELF_EFFICACY_METRIC_NAME
    self_eff_data = None
    for metric_id, data in distributions.items():
        md = MetricDefinition.objects.filter(pk=metric_id, name=SELF_EFFICACY_METRIC_NAME).first()
        if md:
            self_eff_data = data
            break

    if not self_eff_data or self_eff_data["total"] < MIN_N_FOR_DISTRIBUTION:
        return None

    self_report_pct = self_eff_data["band_high_pct"]
    gap = round(self_report_pct - staff_good_place_pct, 1)

    return {
        "self_report_pct": self_report_pct,
        "staff_pct": staff_good_place_pct,
        "gap": gap,
        "n_self_report": self_eff_data["total"],
        "n_staff": staff_participant_count,
        "has_sufficient_data": True,
    }


def get_data_completeness(program, date_from, date_to):
    """Compute data completeness for a program in a date range.

    Returns:
        dict: {enrolled_count, with_scores_count, completeness_pct, completeness_level}
        completeness_level: "full" (>80%), "partial" (50-80%), "low" (<50%)
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
    with_scores_count = (
        _base_metric_values_qs(program, date_from, date_to)
        .values("progress_note_target__plan_target__client_file_id")
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
