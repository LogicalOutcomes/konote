"""CIDS standards alignment data for enriched reports.

Provides theme derivation and standards alignment data that can be
included in partner reports as an appendix page. This is the "quick
win for funders" — no ServiceEpisode needed.

Theme derivation has three tiers:
1. Primary: iris_metric_code → CidsCodeList(IRISImpactTheme) lookup
2. Admin override: cids_theme_override on MetricDefinition
3. Future (Session 5): TaxonomyMapping lookups add a third tier

References CIDS v3.2 (not v2.0).
"""
import logging

logger = logging.getLogger(__name__)


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


def get_standards_alignment_data(program, metric_definitions=None):
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
            mapped_count: int (metrics with at least one CIDS mapping)
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
    mapped_count = 0

    for metric in metric_definitions:
        theme, theme_source = derive_cids_theme(metric)

        has_mapping = bool(
            metric.iris_metric_code
            or metric.cids_indicator_uri
            or metric.sdg_goals
            or theme
        )
        if has_mapping:
            mapped_count += 1

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
            "unit_description": metric.cids_unit_description or "",
            "defined_by": metric.cids_defined_by or "",
            "has_baseline": metric.cids_has_baseline or "",
            "theme": theme or "",
            "theme_source": theme_source or "",
        })

    return {
        "cids_version": "3.2.0",
        "program_cids": {
            "sector_code": program.cids_sector_code or "",
            "population_served": program.population_served_codes or [],
            "funder_code": program.funder_program_code or "",
            "description_fr": program.description_fr or "",
        },
        "metrics": metrics_data,
        "sdg_summary": dict(sorted(sdg_counter.items())),
        "theme_summary": dict(sorted(theme_counter.items())),
        "mapped_count": mapped_count,
        "total_count": len(metrics_data),
    }
