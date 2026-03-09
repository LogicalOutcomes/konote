"""CIDS standards alignment data for enriched reports.

Provides theme derivation and standards alignment data that can be
included in partner reports as an appendix page. This is the "quick
win for funders" — no ServiceEpisode needed.

Local fallback URIs are treated as registration metadata only. They make the
export internally consistent, but they do not count as external taxonomy
alignment.

Theme derivation has three tiers:
1. Primary: iris_metric_code → CidsCodeList(IRISImpactTheme) lookup
2. Admin override: cids_theme_override on MetricDefinition
3. Future (Session 5): TaxonomyMapping lookups add a third tier

References CIDS v3.2 (not v2.0).
"""
import logging

from django.utils.translation import gettext_lazy as _lazy

from apps.plans.cids import is_local_konote_cids_uri

logger = logging.getLogger(__name__)


TAXONOMY_LENS_CHOICES = [
    ("common_approach", _lazy("Common Approach")),
    ("iris_plus", _lazy("IRIS+")),
    ("sdg", _lazy("SDG")),
]


def get_taxonomy_lens_choices():
    return TAXONOMY_LENS_CHOICES


def get_taxonomy_lens_label(taxonomy_lens):
    for value, label in TAXONOMY_LENS_CHOICES:
        if value == taxonomy_lens:
            return str(label)
    return str(dict(TAXONOMY_LENS_CHOICES)["iris_plus"])


def _get_approved_metric_mapping(metric_definition, taxonomy_lens):
    return (
        metric_definition.taxonomy_mappings
        .filter(mapping_status="approved", taxonomy_system=taxonomy_lens)
        .order_by("-reviewed_at", "-created_at")
        .first()
    )


def _get_metric_lens_values(metric_definition, taxonomy_lens):
    approved_mapping = _get_approved_metric_mapping(metric_definition, taxonomy_lens)
    if approved_mapping:
        return {
            "code": approved_mapping.taxonomy_code,
            "label": approved_mapping.taxonomy_label,
            "list_name": approved_mapping.taxonomy_list_name,
            "source": "approved_mapping",
        }

    if taxonomy_lens == "iris_plus" and metric_definition.iris_metric_code:
        from apps.admin_settings.models import CidsCodeList

        entry = CidsCodeList.objects.filter(
            list_name="IrisMetric53",
            code=metric_definition.iris_metric_code,
        ).first()
        return {
            "code": metric_definition.iris_metric_code,
            "label": entry.label if entry else "",
            "list_name": "IrisMetric53",
            "source": "metric_definition",
        }

    if taxonomy_lens == "sdg" and metric_definition.sdg_goals:
        from apps.admin_settings.models import CidsCodeList

        joined = ", ".join(str(goal) for goal in metric_definition.sdg_goals)
        labels = list(
            CidsCodeList.objects.filter(
                list_name="SDGImpacts",
                code__in=[str(goal) for goal in metric_definition.sdg_goals],
            ).order_by("code").values_list("label", flat=True)
        )
        return {
            "code": joined,
            "label": ", ".join(labels) if labels else joined,
            "list_name": "SDGImpacts",
            "source": "metric_definition",
        }

    if (
        taxonomy_lens == "common_approach"
        and metric_definition.cids_indicator_uri
        and not is_local_konote_cids_uri(metric_definition.cids_indicator_uri)
    ):
        return {
            "code": metric_definition.cids_indicator_uri,
            "label": metric_definition.cids_indicator_uri,
            "list_name": "",
            "source": "metric_definition",
        }

    return {
        "code": "",
        "label": "",
        "list_name": "",
        "source": "",
    }


def derive_cids_theme(metric_definition):
    """Derive the CIDS impact theme for a MetricDefinition.

    Returns:
        Tuple of (theme_label, derivation_source) where derivation_source
        is one of: "override", "iris_lookup", or None if no theme found.
    """
    # Tier 1: Admin override takes precedence
    if metric_definition.cids_theme_override:
        return metric_definition.cids_theme_override, "override"

    # Tier 2: Look up via iris_metric_code → IRISImpactTheme
    if metric_definition.iris_metric_code:
        from apps.admin_settings.models import CidsCodeList

        theme_entry = CidsCodeList.objects.filter(
            list_name="IRISImpactTheme",
            code=metric_definition.iris_metric_code,
        ).first()
        if theme_entry:
            return theme_entry.label, "iris_lookup"

    return None, None


def get_standards_alignment_data(program, metric_definitions=None, taxonomy_lens="iris_plus"):
    """Build standards alignment data for a program's report appendix.

    Args:
        program: Program instance.
        metric_definitions: Optional queryset of MetricDefinition objects.
            If not provided, fetches metrics linked to the program's plan targets.

    Returns:
        Dict with keys:
            cids_version: str
            program_cids: dict with sector_code, population_served, funder_code
            metrics: list of dicts with metric CIDS data
            sdg_summary: dict of SDG goal number → count of metrics
            theme_summary: dict of theme → count of metrics
                mapped_count: int (metrics with at least one reference for the selected lens)
            total_count: int (total metrics)
    """
    from apps.plans.models import MetricDefinition, PlanTargetMetric

    if metric_definitions is None:
        # Get metrics linked to active plan targets in this program
        from apps.clients.models import ClientProgramEnrolment

        enrolled_ids = list(
            ClientProgramEnrolment.objects.filter(
                program=program, status="active",
            ).values_list("client_file_id", flat=True)
        )
        metric_ids = set(
            PlanTargetMetric.objects.filter(
                plan_target__client_file_id__in=enrolled_ids,
                plan_target__status="default",
            ).values_list("metric_def_id", flat=True)
        )
        metric_definitions = MetricDefinition.objects.filter(pk__in=metric_ids)

    metrics_data = []
    sdg_counter = {}
    theme_counter = {}
    lens_counter = {}
    mapped_count = 0

    for metric in metric_definitions:
        theme, theme_source = derive_cids_theme(metric)
        lens_values = _get_metric_lens_values(metric, taxonomy_lens)

        has_mapping = bool(lens_values["code"])
        if has_mapping:
            mapped_count += 1
            key = lens_values["label"] or lens_values["code"]
            lens_counter[key] = lens_counter.get(key, 0) + 1

        # Count SDG goals
        for goal in (metric.sdg_goals or []):
            sdg_counter[goal] = sdg_counter.get(goal, 0) + 1

        # Count themes
        if theme:
            theme_counter[theme] = theme_counter.get(theme, 0) + 1

        metrics_data.append({
            "name": metric.name,
            "iris_code": metric.iris_metric_code or "",
            "cids_indicator_uri": metric.cids_indicator_uri or "",
            "sdg_goals": metric.sdg_goals or [],
            "selected_code": lens_values["code"],
            "selected_label": lens_values["label"],
            "selected_list_name": lens_values["list_name"],
            "selected_source": lens_values["source"],
            "unit_description": metric.cids_unit_description or "",
            "defined_by": metric.cids_defined_by or "",
            "has_baseline": metric.cids_has_baseline or "",
            "theme": theme or "",
            "theme_source": theme_source or "",
        })

    return {
        "cids_version": "3.2.0",
        "taxonomy_lens": taxonomy_lens,
        "taxonomy_lens_label": get_taxonomy_lens_label(taxonomy_lens),
        "program_cids": {
            "sector_code": program.cids_sector_code or "",
            "population_served": program.population_served_codes or [],
            "funder_code": program.funder_program_code or "",
            "description_fr": program.description_fr or "",
        },
        "metrics": metrics_data,
        "lens_summary": dict(sorted(lens_counter.items())),
        "sdg_summary": dict(sorted(sdg_counter.items())),
        "theme_summary": dict(sorted(theme_counter.items())),
        "mapped_count": mapped_count,
        "total_count": len(metrics_data),
    }
