"""Utilities for building Common Approach CIDS JSON-LD exports.

Supports Basic Tier (7 classes) and extended Basic+Stubs (11 classes).
Full Tier (14 classes) requires Phase 1 EvaluationFramework models.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time
import json
import math
from statistics import mean, median, stdev

from django.db.models import Count, Q
from django.utils import timezone

from apps.admin_settings.models import CidsCodeList, OrganizationProfile, TaxonomyMapping
from apps.notes.models import MetricValue
from apps.plans.models import MetricDefinition, PlanTarget, PlanTargetMetric

from .cids_enrichment import derive_cids_theme, get_taxonomy_lens_label


CIDS_CONTEXT = "https://ontology.commonapproach.org/contexts/cidsContext.jsonld"
CIDS_VERSION = "3.2.0"


def _note_date_q(prefix, date_from=None, date_to=None):
    if not date_from or not date_to:
        return Q()
    start_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    end_dt = timezone.make_aware(datetime.combine(date_to, time.max))
    return (
        Q(**{f"{prefix}backdate__range": (start_dt, end_dt)})
        | Q(**{f"{prefix}backdate__isnull": True, f"{prefix}created_at__range": (start_dt, end_dt)})
    )


def _normalise_note_date(backdate, created_at):
    return backdate or created_at or timezone.now()


# ── IndicatorReport aggregation helpers ─────────────────────────────


def _parse_numeric_values(values_qs):
    """Extract numeric values from MetricValue queryset, skipping unparseable.

    Returns (nums, skipped_count) so callers can report data quality.
    """
    nums = []
    skipped = 0
    for mv in values_qs:
        try:
            nums.append(float(mv.value))
        except (ValueError, TypeError):
            skipped += 1
    return nums, skipped


def _group_by_participant(values_qs):
    """Group metric values by participant, ordered by date within each group."""
    by_participant = defaultdict(list)
    for mv in values_qs:
        client_id = mv.progress_note_target.plan_target.client_file_id
        note_date = _normalise_note_date(
            mv.progress_note_target.progress_note.backdate,
            mv.progress_note_target.progress_note.created_at,
        )
        by_participant[client_id].append((note_date, mv.value))
    # Sort each participant's observations by date
    for client_id in by_participant:
        by_participant[client_id].sort(key=lambda x: x[0])
    return by_participant


def _compute_achievement_report(metric, values_qs, observation_count, program):
    """Compute aggregate statistics for achievement metrics.

    Achievement metrics have categorical values (e.g., "Employed", "In training").
    MetricDefinition.achievement_success_values defines which count as achieved.
    """
    success_values = set(metric.achievement_success_values or [])
    all_values = [mv.value for mv in values_qs]

    # Distribution: count per option
    distribution = defaultdict(int)
    for v in all_values:
        distribution[v] += 1

    # Latest value per participant (most recent observation wins)
    by_participant = _group_by_participant(values_qs)
    participants = len(by_participant)
    latest_values = [observations[-1][1] for observations in by_participant.values()]

    achieved = sum(1 for v in latest_values if v in success_values)
    success_rate = (achieved / participants * 100) if participants else 0

    measures = [
        {
            "@type": "i72:Measure",
            "hasNumericalValue": str(round(success_rate, 1)),
            "hasUnit": {"@value": "percent"},
            "measureType": "konote:success_rate",
        },
        {
            "@type": "i72:Measure",
            "hasNumericalValue": str(achieved),
            "hasUnit": {"@value": f"of {participants} participants"},
            "measureType": "konote:count_achieved",
        },
    ]

    # Distribution breakdown (for bar/pie charts)
    distribution_items = []
    for option in (metric.achievement_options or []):
        count = distribution.get(option, 0)
        distribution_items.append({
            "label": option,
            "count": count,
            "percent": round(count / observation_count * 100, 1) if observation_count else 0,
            "isSuccess": option in success_values,
        })

    if distribution_items:
        measures.append({
            "@type": "i72:Measure",
            "measureType": "konote:distribution",
            "distribution": distribution_items,
        })

    # Target comparison
    if metric.target_rate is not None:
        measures.append({
            "@type": "i72:Measure",
            "hasNumericalValue": str(metric.target_rate),
            "hasUnit": {"@value": "percent"},
            "measureType": "konote:target_rate",
        })

    comment = (
        f"{achieved} of {participants} participants achieved "
        f"({round(success_rate, 1)}%) for {metric.name} in {program.name}"
    )
    if metric.target_rate is not None:
        comment += f" (target: {metric.target_rate}%)"

    return measures, comment


def _compute_scale_report(metric, values_qs, observation_count, program):
    """Compute aggregate statistics for scale metrics.

    Scale metrics have numeric values recorded repeatedly over time.
    Computes central tendency, spread, band distribution, and pre/post change.
    """
    nums, skipped = _parse_numeric_values(values_qs)
    if not nums:
        return (
            [{"@type": "i72:Measure", "hasNumericalValue": str(observation_count),
              "measureType": "konote:observation_count"}],
            f"{observation_count} observations for {metric.name} in {program.name} (no parseable values)",
        )

    avg = mean(nums)
    med = median(nums)
    lo = min(nums)
    hi = max(nums)

    measures = [
        {
            "@type": "i72:Measure",
            "hasNumericalValue": str(round(avg, 2)),
            "hasUnit": {"@value": metric.unit or "score"},
            "measureType": "konote:mean",
        },
        {
            "@type": "i72:Measure",
            "hasNumericalValue": str(round(med, 2)),
            "hasUnit": {"@value": metric.unit or "score"},
            "measureType": "konote:median",
        },
    ]

    # Only emit SD when there are enough values for it to be meaningful
    if len(nums) >= 2:
        sd = stdev(nums)
        measures.append({
            "@type": "i72:Measure",
            "hasNumericalValue": str(round(sd, 2)),
            "measureType": "konote:standard_deviation",
        })
    else:
        sd = None

    measures.extend([
        {
            "@type": "i72:Measure",
            "hasNumericalValue": str(round(lo, 2)),
            "measureType": "konote:minimum",
        },
        {
            "@type": "i72:Measure",
            "hasNumericalValue": str(round(hi, 2)),
            "measureType": "konote:maximum",
        },
    ])

    # Report skipped (unparseable) values so consumers know about data quality
    if skipped:
        measures.append({
            "@type": "i72:Measure",
            "hasNumericalValue": str(skipped),
            "measureType": "konote:skipped_unparseable",
        })

    # Band distribution (low / medium / high) for stacked bar or donut charts
    if metric.threshold_low is not None and metric.threshold_high is not None:
        low_count = sum(1 for v in nums if v < metric.threshold_low)
        mid_count = sum(1 for v in nums if metric.threshold_low <= v < metric.threshold_high)
        high_count = sum(1 for v in nums if v >= metric.threshold_high)
        total = len(nums)
        measures.append({
            "@type": "i72:Measure",
            "measureType": "konote:band_distribution",
            "distribution": [
                {"label": "Low", "count": low_count, "percent": round(low_count / total * 100, 1)},
                {"label": "Medium", "count": mid_count, "percent": round(mid_count / total * 100, 1)},
                {"label": "High", "count": high_count, "percent": round(high_count / total * 100, 1)},
            ],
        })
        if metric.target_band_high_pct is not None:
            measures.append({
                "@type": "i72:Measure",
                "hasNumericalValue": str(metric.target_band_high_pct),
                "hasUnit": {"@value": "percent"},
                "measureType": "konote:target_high_band_percent",
            })

    # Pre/post analysis: first and last observation per participant
    by_participant = _group_by_participant(values_qs)
    participants_with_multiple = {
        cid: obs for cid, obs in by_participant.items() if len(obs) >= 2
    }
    if participants_with_multiple:
        first_values = []
        last_values = []
        improved_count = 0
        for cid, obs in participants_with_multiple.items():
            try:
                first_val = float(obs[0][1])
                last_val = float(obs[-1][1])
            except (ValueError, TypeError):
                continue
            first_values.append(first_val)
            last_values.append(last_val)
            if metric.higher_is_better:
                if last_val > first_val:
                    improved_count += 1
            else:
                if last_val < first_val:
                    improved_count += 1

        if first_values:
            pre_mean = mean(first_values)
            post_mean = mean(last_values)
            n_compared = len(first_values)
            improvement_rate = round(improved_count / n_compared * 100, 1)

            # Effect size (Cohen's d) — useful for bubble charts comparing
            # programs: x = cohort size, y = effect size, bubble = success rate
            pooled_sd = None
            if n_compared >= 2:
                pre_sd = stdev(first_values) if len(first_values) >= 2 else 0.0
                post_sd = stdev(last_values) if len(last_values) >= 2 else 0.0
                pooled_var = (pre_sd ** 2 + post_sd ** 2) / 2
                pooled_sd = math.sqrt(pooled_var) if pooled_var > 0 else None

            measures.append({
                "@type": "i72:Measure",
                "measureType": "konote:pre_post_change",
                "preMean": round(pre_mean, 2),
                "postMean": round(post_mean, 2),
                "participantsCompared": n_compared,
                "improvedCount": improved_count,
                "improvementRate": improvement_rate,
                **({"effectSize": round((post_mean - pre_mean) / pooled_sd, 2)}
                   if pooled_sd else {}),
            })

    # Participants count (useful as bubble size dimension)
    measures.append({
        "@type": "i72:Measure",
        "hasNumericalValue": str(len(by_participant)),
        "measureType": "konote:participant_count",
    })

    comment_parts = [
        f"Mean {round(avg, 2)}, median {round(med, 2)}",
        f"SD {round(sd, 2)}" if sd is not None else None,
        f"range {round(lo, 2)}–{round(hi, 2)}" if lo != hi else None,
        f"n={len(by_participant)} participants",
    ]
    comment = f"{metric.name} in {program.name}: " + ", ".join(p for p in comment_parts if p)

    if participants_with_multiple and first_values:
        comment += f". Pre/post: {round(pre_mean, 2)} → {round(post_mean, 2)}, {improvement_rate}% improved"

    return measures, comment


def _compute_indicator_report(metric, values_qs, observation_count, program):
    """Dispatch to the right aggregation based on metric type."""
    if metric.metric_type == "achievement":
        return _compute_achievement_report(metric, values_qs, observation_count, program)
    elif metric.metric_type == "scale":
        return _compute_scale_report(metric, values_qs, observation_count, program)
    else:
        # Open text — count is the only meaningful aggregate
        return (
            [{"@type": "i72:Measure", "hasNumericalValue": str(observation_count),
              "measureType": "konote:observation_count"}],
            f"{observation_count} recorded observations for {metric.name} in {program.name}",
        )


def _build_dqv_quality(metric, values_qs, observation_count, program, measures,
                       eligible_count=None):
    """Build DQV quality measurements and annotations for an IndicatorReport.

    Follows the "describe, don't rank" principle: quality signals tell funders
    *how* the data was generated so they can make contextual judgments.

    Tier 1 — Quantitative measurements (computed automatically):
      - Reporting rate (completeness): participants who reported / eligible
      - Data parsability (completeness): % of values successfully parsed
      - Observation density (precision): observations per participant

    Tier 2 — Structured annotations (from MetricDefinition fields):
      - Evidence type: how data is generated (self-report, staff-observed, etc.)
      - Measure basis: how the measure was developed (published, custom, etc.)
      - Derivation method: how the value was produced (when not a direct response)

    Args:
        eligible_count: Pre-computed eligible participant count for this metric.
            Pass from a batched query to avoid per-metric DB hits.
    """
    quality_measurements = []
    quality_annotations = []

    # ── Tier 1: Quantitative measurements ───────────────────────────

    # Reporting rate (completeness)
    measures_by_type = {m.get("measureType"): m for m in measures}

    participant_measure = measures_by_type.get("konote:participant_count")
    if participant_measure:
        reported = int(participant_measure["hasNumericalValue"])
    else:
        # Achievement metrics don't emit participant_count; count from queryset
        reported = (
            values_qs
            .values_list(
                "progress_note_target__plan_target__client_file_id", flat=True,
            )
            .distinct()
            .count()
        )

    eligible = eligible_count if eligible_count is not None else (
        PlanTargetMetric.objects.filter(
            plan_target__plan_section__program=program,
            metric_def=metric,
            plan_target__status__in=["default", "completed"],
        )
        .values_list("plan_target__client_file_id", flat=True)
        .distinct()
        .count()
    )

    if eligible > 0 and reported > 0:
        response_rate = round(reported / eligible * 100, 1)
        quality_measurements.append({
            "@type": "dqv:QualityMeasurement",
            "dqv:isMeasurementOf": "completeness",
            "dqv:value": response_rate,
            "konote:numerator": reported,
            "konote:denominator": eligible,
            "konote:dimensionLabel": "Reporting rate (participants reported / eligible)",
        })

    # Data parsability (completeness, scale metrics only)
    skipped_measure = measures_by_type.get("konote:skipped_unparseable")
    if skipped_measure and observation_count > 0:
        skipped = int(skipped_measure["hasNumericalValue"])
        parseable = observation_count - skipped
        parsability_rate = round(parseable / observation_count * 100, 1)
        quality_measurements.append({
            "@type": "dqv:QualityMeasurement",
            "dqv:isMeasurementOf": "completeness",
            "dqv:value": parsability_rate,
            "konote:dimensionLabel": "Data parsability (% of values successfully parsed)",
        })

    # Observation density (precision)
    if observation_count > 0 and reported > 0:
        density = round(observation_count / reported, 1)
        quality_measurements.append({
            "@type": "dqv:QualityMeasurement",
            "dqv:isMeasurementOf": "precision",
            "dqv:value": density,
            "konote:dimensionLabel": "Observation density (observations per participant)",
            "konote:totalObservations": observation_count,
            "konote:totalParticipants": reported,
        })

    # ── Tier 2: Structured descriptors ──────────────────────────────

    _DESCRIPTOR_FIELDS = [
        ("evidence_type", MetricDefinition.EVIDENCE_TYPE_CHOICES),
        ("measure_basis", MetricDefinition.MEASURE_BASIS_CHOICES),
        ("derivation_method", MetricDefinition.DERIVATION_METHOD_CHOICES),
    ]
    for field_name, choices in _DESCRIPTOR_FIELDS:
        value = getattr(metric, field_name, "")
        if not value:
            continue
        label = str(dict(choices).get(value, value))
        # Include instrument name for published measures
        if field_name == "measure_basis" and value in (
            "published_validated", "published_adapted",
        ):
            instrument = getattr(metric, "instrument_name", "")
            if instrument:
                label = f"{label}: {instrument}"
        quality_annotations.append({
            "@type": "dqv:QualityAnnotation",
            "oa:hasBody": {
                "@type": "oa:TextualBody",
                "rdf:value": label,
            },
            "oa:motivatedBy": "dqv:qualityAssessment",
            "konote:annotationType": field_name,
            "konote:annotationCategory": value,
        })

    return {
        "dqv:hasQualityMeasurement": quality_measurements,
        "dqv:hasQualityAnnotation": quality_annotations,
    }


def _build_address_node(org, org_id):
    if not all([
        org.street_address,
        org.city,
        org.province,
        org.postal_code,
        org.country,
    ]):
        return None
    address_id = f"{org_id}:address"
    return address_id, {
        "@id": address_id,
        "@type": "cids:Address",
        "streetAddress": org.street_address,
        "addressLocality": org.city,
        "addressRegion": org.province,
        "postalCode": org.postal_code,
        "addressCountry": org.country,
    }


def _get_mapping_for_metric(metric_definition, taxonomy_lens):
    return (
        metric_definition.taxonomy_mappings
        .filter(mapping_status="approved", taxonomy_system=taxonomy_lens)
        .order_by("-reviewed_at", "-created_at")
        .first()
    )


def _build_code_node_from_mapping(mapping):
    code_id = f"urn:konote:code:{mapping.taxonomy_system}:{mapping.taxonomy_code}"
    code_list = None
    if mapping.taxonomy_list_name:
        code_list = CidsCodeList.objects.filter(
            list_name=mapping.taxonomy_list_name,
            code=mapping.taxonomy_code,
        ).first()
    if code_list and code_list.specification_uri:
        code_id = code_list.specification_uri
    elif mapping.taxonomy_system == "common_approach" and mapping.taxonomy_code.startswith(("http://", "https://", "urn:")):
        code_id = mapping.taxonomy_code

    label = mapping.taxonomy_label or (code_list.label if code_list else "") or mapping.taxonomy_code
    return code_id, {
        "@id": code_id,
        "@type": "cids:Code",
        "hasName": label,
    }


def _build_code_node_from_metric(metric_definition, taxonomy_lens):
    if taxonomy_lens == "iris_plus" and metric_definition.iris_metric_code:
        code_list = CidsCodeList.objects.filter(
            list_name="IrisMetric53",
            code=metric_definition.iris_metric_code,
        ).first()
        code_id = (
            code_list.specification_uri
            if code_list and code_list.specification_uri
            else f"urn:konote:code:iris_plus:{metric_definition.iris_metric_code}"
        )
        return code_id, {
            "@id": code_id,
            "@type": "cids:Code",
            "hasName": (code_list.label if code_list else metric_definition.iris_metric_code),
        }

    if taxonomy_lens == "sdg" and metric_definition.sdg_goals:
        goal = str(metric_definition.sdg_goals[0])
        code_list = CidsCodeList.objects.filter(
            list_name="SDGImpacts",
            code=goal,
        ).first()
        code_id = (
            code_list.specification_uri
            if code_list and code_list.specification_uri
            else f"urn:konote:code:sdg:{goal}"
        )
        return code_id, {
            "@id": code_id,
            "@type": "cids:Code",
            "hasName": (code_list.label if code_list else goal),
        }

    if (
        taxonomy_lens == "common_approach"
        and metric_definition.cids_indicator_uri
        and not metric_definition.cids_indicator_uri.startswith("urn:konote:indicator-definition:")
        and metric_definition.cids_indicator_uri.startswith(("http://", "https://", "urn:"))
    ):
        code_id = metric_definition.cids_indicator_uri
        return code_id, {
            "@id": code_id,
            "@type": "cids:Code",
            "hasName": metric_definition.name,
        }

    return None, None


def _get_metric_code_node(metric_definition, taxonomy_lens):
    mapping = _get_mapping_for_metric(metric_definition, taxonomy_lens)
    if mapping:
        return _build_code_node_from_mapping(mapping)
    return _build_code_node_from_metric(metric_definition, taxonomy_lens)


def _build_theme_node(metric_definition):
    theme_label, _theme_source = derive_cids_theme(metric_definition)
    if not theme_label:
        return None, None

    code_list = CidsCodeList.objects.filter(
        list_name="IRISImpactTheme",
        label=theme_label,
    ).first()
    theme_id = (
        code_list.specification_uri
        if code_list and code_list.specification_uri
        else f"urn:konote:theme:{theme_label.lower().replace(' ', '-') }"
    )
    theme_node = {
        "@id": theme_id,
        "@type": "cids:Theme",
        "hasName": theme_label,
        "hasDescription": code_list.description if code_list and code_list.description else theme_label,
    }
    return theme_id, theme_node


def _build_impact_model_node(program, org_id):
    """Derive a cids:ImpactModel stub from Program.description."""
    if not program.description:
        return None
    model_id = f"urn:konote:impact-model:{program.pk}"
    return {
        "@id": model_id,
        "@type": "cids:ImpactModel",
        "hasName": f"{program.name} program model",
        "hasDescription": program.description,
        "forOrganization": {"@id": org_id},
    }


def _build_stakeholder_nodes(program, org_id):
    """Derive cids:Stakeholder nodes from Program.population_served_codes."""
    codes = program.population_served_codes or []
    if not codes:
        return []
    nodes = []
    for code in codes:
        code_label = code if isinstance(code, str) else str(code)
        code_list = CidsCodeList.objects.filter(
            list_name="PopulationServed", code=code_label,
        ).first()
        label = (code_list.label if code_list else code_label)
        stakeholder_id = f"urn:konote:stakeholder:{program.pk}:{code_label}"
        nodes.append({
            "@id": stakeholder_id,
            "@type": "cids:BeneficialStakeholder",
            "hasName": label,
            "hasDescription": f"Population group: {label}",
            "forOrganization": {"@id": org_id},
        })
    return nodes


def _build_stakeholder_outcome_node(program, outcome_id, org_id):
    """Derive a cids:StakeholderOutcome from aggregate PlanTarget achievement."""
    targets = PlanTarget.objects.filter(
        plan_section__program=program,
        status__in=["default", "completed"],
    )
    total = targets.count()
    if not total:
        return None
    achieved = targets.filter(achievement_status="achieved").count()
    sustaining = targets.filter(achievement_status="sustaining").count()
    met_count = achieved + sustaining
    rate = round(met_count / total * 100, 1)

    so_id = f"urn:konote:stakeholder-outcome:{program.pk}"
    return {
        "@id": so_id,
        "@type": "cids:StakeholderOutcome",
        "hasName": f"{program.name} participant outcomes",
        "hasDescription": (
            f"{met_count} of {total} targets achieved or sustaining ({rate}%)"
        ),
        "forOutcome": [{"@id": outcome_id}],
        "forOrganization": {"@id": org_id},
    }


def _build_output_node(program, org_id, note_filter):
    """Derive a cids:Output from observation counts."""
    observation_count = MetricValue.objects.filter(
        progress_note_target__plan_target__plan_section__program=program,
        progress_note_target__progress_note__status="default",
    ).filter(note_filter).count()
    if not observation_count:
        return None

    output_id = f"urn:konote:output:{program.pk}"
    return {
        "@id": output_id,
        "@type": "cids:Output",
        "hasName": f"{program.name} service outputs",
        "hasDescription": (
            f"{observation_count} metric observations recorded"
        ),
        "forOrganization": {"@id": org_id},
    }


def build_cids_jsonld_document(programs, taxonomy_lens="common_approach", date_from=None, date_to=None, metric_definitions=None, include_full_tier_stubs=False):
    """Build a CIDS JSON-LD document for one or more programs.

    The export is intentionally aggregate-only. It avoids client-specific target
    names and instead emits one program-level outcome node per program.

    When ``include_full_tier_stubs`` is True, additional nodes are emitted:
    ImpactModel, BeneficialStakeholder, StakeholderOutcome, and Output —
    derived from existing Program and PlanTarget data without new models.
    """
    programs = list(programs)
    org = OrganizationProfile.get_solo()
    org_id = f"urn:konote:org:{org.pk or 1}"
    graph = []
    seen_nodes = set()

    def add_node(node):
        node_id = node["@id"]
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        graph.append(node)

    org_node = {
        "@id": org_id,
        "@type": "cids:Organization",
        "hasLegalName": org.legal_name or org.operating_name or "Organisation",
    }
    address_info = _build_address_node(org, org_id)
    if address_info:
        address_id, address_node = address_info
        org_node["hasAddress"] = [{"@id": address_id}]
        add_node(address_node)

    org_outcomes = []
    org_indicators = []
    theme_refs_by_program = defaultdict(list)

    metric_queryset = MetricDefinition.objects.filter(status="active")
    if metric_definitions is not None:
        metric_queryset = metric_queryset.filter(pk__in=[metric.pk for metric in metric_definitions])

    note_filter = _note_date_q("progress_note_target__progress_note__", date_from, date_to)

    for program in programs:
        outcome_id = f"urn:konote:program-outcome:{program.pk}"
        outcome_node = {
            "@id": outcome_id,
            "@type": "cids:Outcome",
            "hasName": f"{program.name} outcomes",
            "hasDescription": (
                program.description
                or f"Aggregate participant outcomes reported for {program.name}."
            ),
            "forOrganization": {"@id": org_id},
        }

        metric_ids = set(
            PlanTargetMetric.objects.filter(
                plan_target__plan_section__program=program,
                plan_target__status__in=["default", "completed"],
                metric_def__in=metric_queryset,
            ).values_list("metric_def_id", flat=True)
        )
        metric_ids.update(
            MetricValue.objects.filter(
                progress_note_target__plan_target__plan_section__program=program,
                progress_note_target__progress_note__status="default",
                metric_def__in=metric_queryset,
            ).filter(note_filter).values_list("metric_def_id", flat=True)
        )

        program_metrics = list(metric_queryset.filter(pk__in=metric_ids).distinct())

        # Batch eligible participant counts per metric (avoids N+1 in DQV)
        eligible_by_metric = dict(
            PlanTargetMetric.objects.filter(
                plan_target__plan_section__program=program,
                metric_def__in=program_metrics,
                plan_target__status__in=["default", "completed"],
            )
            .values("metric_def_id")
            .annotate(eligible=Count("plan_target__client_file_id", distinct=True))
            .values_list("metric_def_id", "eligible")
        )

        outcome_indicator_refs = []

        for metric in program_metrics:
            indicator_id = f"urn:konote:indicator:{program.pk}:{metric.pk}"
            indicator_node = {
                "@id": indicator_id,
                "@type": "cids:Indicator",
                "hasName": metric.name,
                "hasDescription": metric.definition or metric.name,
                "unitDescription": metric.cids_unit_description or metric.unit or "Recorded observations",
                "forOrganization": {"@id": org_id},
                "forOutcome": [{"@id": outcome_id}],
            }

            theme_id, theme_node = _build_theme_node(metric)
            if theme_id and theme_node:
                add_node(theme_node)
                indicator_node["forTheme"] = [{"@id": theme_id}]
                theme_refs_by_program[program.pk].append({"@id": theme_id})

            code_id, code_node = _get_metric_code_node(metric, taxonomy_lens)
            if code_id and code_node:
                add_node(code_node)
                indicator_node["hasCode"] = [{"@id": code_id}]

            values_qs = MetricValue.objects.filter(
                metric_def=metric,
                progress_note_target__plan_target__plan_section__program=program,
                progress_note_target__progress_note__status="default",
            ).filter(note_filter).select_related(
                "progress_note_target__progress_note",
                "progress_note_target__plan_target",
            )

            observation_count = values_qs.count()
            if observation_count:
                note_dates = [
                    _normalise_note_date(
                        metric_value.progress_note_target.progress_note.backdate,
                        metric_value.progress_note_target.progress_note.created_at,
                    )
                    for metric_value in values_qs
                ]
                started_at = min(note_dates).isoformat()
                ended_at = max(note_dates).isoformat()

                measures, comment = _compute_indicator_report(
                    metric, values_qs, observation_count, program,
                )

                report_id = f"urn:konote:indicator-report:{program.pk}:{metric.pk}"
                report_node = {
                    "@id": report_id,
                    "@type": "cids:IndicatorReport",
                    "hasName": f"{metric.name} report",
                    "forOrganization": {"@id": org_id},
                    "forIndicator": {"@id": indicator_id},
                    "startedAtTime": started_at,
                    "endedAtTime": ended_at,
                    "value": measures,
                    "hasComment": comment,
                }
                # Add DQV data quality signals
                dqv = _build_dqv_quality(
                    metric, values_qs, observation_count, program, measures,
                    eligible_count=eligible_by_metric.get(metric.pk),
                )
                if dqv.get("dqv:hasQualityMeasurement"):
                    report_node["dqv:hasQualityMeasurement"] = dqv["dqv:hasQualityMeasurement"]
                if dqv.get("dqv:hasQualityAnnotation"):
                    report_node["dqv:hasQualityAnnotation"] = dqv["dqv:hasQualityAnnotation"]

                indicator_node["hasIndicatorReport"] = [{"@id": report_id}]
                add_node(report_node)

            add_node(indicator_node)
            org_indicators.append({"@id": indicator_id})
            outcome_indicator_refs.append({"@id": indicator_id})

        if outcome_indicator_refs:
            outcome_node["hasIndicator"] = outcome_indicator_refs
        if theme_refs_by_program[program.pk]:
            deduped_themes = []
            seen_theme_ids = set()
            for theme_ref in theme_refs_by_program[program.pk]:
                theme_ref_id = theme_ref["@id"]
                if theme_ref_id in seen_theme_ids:
                    continue
                seen_theme_ids.add(theme_ref_id)
                deduped_themes.append(theme_ref)
            if deduped_themes:
                outcome_node["forTheme"] = deduped_themes

        add_node(outcome_node)
        org_outcomes.append({"@id": outcome_id})

        if include_full_tier_stubs:
            impact_model = _build_impact_model_node(program, org_id)
            if impact_model:
                outcome_node["forImpactModel"] = [{"@id": impact_model["@id"]}]
                add_node(impact_model)

            stakeholder_nodes = _build_stakeholder_nodes(program, org_id)
            for sn in stakeholder_nodes:
                add_node(sn)

            so_node = _build_stakeholder_outcome_node(program, outcome_id, org_id)
            if so_node:
                stakeholder_refs = [{"@id": sn["@id"]} for sn in stakeholder_nodes]
                if stakeholder_refs:
                    so_node["forStakeholder"] = stakeholder_refs
                add_node(so_node)

            output_node = _build_output_node(program, org_id, note_filter)
            if output_node:
                add_node(output_node)

    if org.operating_name:
        org_node["hasName"] = org.operating_name
    if org.description:
        org_node["hasDescription"] = org.description
    if org_outcomes:
        org_node["hasOutcome"] = org_outcomes
    if org_indicators:
        deduped_indicators = []
        seen_indicator_ids = set()
        for indicator_ref in org_indicators:
            indicator_ref_id = indicator_ref["@id"]
            if indicator_ref_id in seen_indicator_ids:
                continue
            seen_indicator_ids.add(indicator_ref_id)
            deduped_indicators.append(indicator_ref)
        org_node["hasIndicator"] = deduped_indicators
    add_node(org_node)

    doc = {
        "@context": [
            CIDS_CONTEXT,
            {
                "dqv": "http://www.w3.org/ns/dqv#",
                "oa": "http://www.w3.org/ns/oa#",
                "konote": "https://konote.ca/cids/extensions#",
                "konote:mean": {"@id": "konote:mean", "@type": "@id"},
                "konote:median": {"@id": "konote:median", "@type": "@id"},
                "konote:standard_deviation": {"@id": "konote:standard_deviation", "@type": "@id"},
                "konote:minimum": {"@id": "konote:minimum", "@type": "@id"},
                "konote:maximum": {"@id": "konote:maximum", "@type": "@id"},
                "konote:success_rate": {"@id": "konote:success_rate", "@type": "@id"},
                "konote:count_achieved": {"@id": "konote:count_achieved", "@type": "@id"},
                "konote:distribution": {"@id": "konote:distribution", "@type": "@id"},
                "konote:band_distribution": {"@id": "konote:band_distribution", "@type": "@id"},
                "konote:pre_post_change": {"@id": "konote:pre_post_change", "@type": "@id"},
                "konote:participant_count": {"@id": "konote:participant_count", "@type": "@id"},
                "konote:observation_count": {"@id": "konote:observation_count", "@type": "@id"},
                "konote:target_rate": {"@id": "konote:target_rate", "@type": "@id"},
                "konote:target_high_band_percent": {"@id": "konote:target_high_band_percent", "@type": "@id"},
                "konote:skipped_unparseable": {"@id": "konote:skipped_unparseable", "@type": "@id"},
                "konote:numerator": {"@id": "konote:numerator"},
                "konote:denominator": {"@id": "konote:denominator"},
                "konote:dimensionLabel": {"@id": "konote:dimensionLabel"},
                "konote:annotationType": {"@id": "konote:annotationType"},
                "konote:annotationCategory": {"@id": "konote:annotationCategory"},
                "konote:totalObservations": {"@id": "konote:totalObservations"},
                "konote:totalParticipants": {"@id": "konote:totalParticipants"},
            },
        ],
        "@graph": graph,
        "cids:version": CIDS_VERSION,
        "cids:exportedAt": timezone.now().isoformat(),
        "cids:exportedBy": "KoNote",
        "cids:taxonomyLens": taxonomy_lens,
        "cids:taxonomyLensLabel": get_taxonomy_lens_label(taxonomy_lens),
    }
    if include_full_tier_stubs:
        doc["cids:complianceTier"] = "EssentialTier"
        doc["cids:classCount"] = len({n["@type"] for n in graph if "@type" in n})
    return doc


def serialize_cids_jsonld(*args, indent=2, **kwargs):
    document = build_cids_jsonld_document(*args, **kwargs)
    return json.dumps(document, indent=indent, ensure_ascii=False)