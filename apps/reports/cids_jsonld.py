"""Utilities for building Common Approach CIDS Basic Tier JSON-LD exports."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time
import json

from django.db.models import Q
from django.utils import timezone

from apps.admin_settings.models import CidsCodeList, OrganizationProfile, TaxonomyMapping
from apps.notes.models import MetricValue
from apps.plans.models import MetricDefinition, PlanTargetMetric

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


def build_cids_jsonld_document(programs, taxonomy_lens="common_approach", date_from=None, date_to=None, metric_definitions=None):
    """Build a CIDS Basic Tier JSON-LD document for one or more programs.

    The export is intentionally aggregate-only. It avoids client-specific target
    names and instead emits one program-level outcome node per program.
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
            ).filter(note_filter).select_related("progress_note_target__progress_note")

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
                report_id = f"urn:konote:indicator-report:{program.pk}:{metric.pk}"
                report_node = {
                    "@id": report_id,
                    "@type": "cids:IndicatorReport",
                    "hasName": f"{metric.name} report",
                    "forOrganization": {"@id": org_id},
                    "forIndicator": {"@id": indicator_id},
                    "startedAtTime": started_at,
                    "endedAtTime": ended_at,
                    "value": {
                        "@type": "i72:Measure",
                        "hasNumericalValue": str(observation_count),
                    },
                    "hasComment": (
                        f"Observation count for {metric.name} in {program.name}"
                    ),
                }
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

    return {
        "@context": CIDS_CONTEXT,
        "@graph": graph,
        "cids:version": CIDS_VERSION,
        "cids:exportedAt": timezone.now().isoformat(),
        "cids:exportedBy": "KoNote",
        "cids:taxonomyLens": taxonomy_lens,
        "cids:taxonomyLensLabel": get_taxonomy_lens_label(taxonomy_lens),
    }


def serialize_cids_jsonld(*args, indent=2, **kwargs):
    document = build_cids_jsonld_document(*args, **kwargs)
    return json.dumps(document, indent=indent, ensure_ascii=False)