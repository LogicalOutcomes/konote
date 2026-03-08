"""CIDS Full Tier JSON-LD export assembly.

Builds a complete Full Tier document from three layers:
- Layer 1: Program model metadata from EvaluationFramework + EvaluationComponent
- Layer 2: Aggregate measurement from existing Basic Tier export
- Layer 3: Optional de-identified case trajectories (placeholder)
"""
from __future__ import annotations

import json
from datetime import date

from django.db.models import Count, Q
from django.utils import timezone

from apps.admin_settings.models import OrganizationProfile
from apps.programs.models import (
    EvaluationComponent,
    EvaluationFramework,
    Program,
)

from .cids_jsonld import CIDS_CONTEXT, CIDS_VERSION, build_cids_jsonld_document


# ── Layer 1: Program Model Metadata ──────────────────────────────────


def _build_impact_model_from_framework(fw, org_id):
    """Build cids:ImpactModel from EvaluationFramework."""
    model_id = f"urn:konote:impact-model:{fw.program_id}"
    node = {
        "@id": model_id,
        "@type": "cids:ImpactModel",
        "hasName": fw.name,
        "hasDescription": fw.summary or fw.program.description or "",
        "forOrganization": {"@id": org_id},
    }
    if fw.outcome_chain_summary:
        node["cids:outcomeChain"] = fw.outcome_chain_summary
    if fw.is_attested:
        node["cids:evaluatorAttestation"] = {
            "attestedBy": fw.evaluator_attestation_by.display_name if fw.evaluator_attestation_by else "",
            "attestedAt": fw.evaluator_attestation_at.isoformat() if fw.evaluator_attestation_at else "",
            "scope": fw.evaluator_attestation_scope or [],
            "text": fw.evaluator_attestation_text,
        }
    return model_id, node


def _component_to_node(comp, org_id, impact_model_id=None):
    """Convert an EvaluationComponent to a CIDS JSON-LD node."""
    cids_type = comp.cids_class
    if not cids_type:
        return None, None

    node_id = f"urn:konote:component:{comp.framework_id}:{comp.pk}"
    node = {
        "@id": node_id,
        "@type": cids_type,
        "hasName": comp.name,
        "forOrganization": {"@id": org_id},
    }
    if comp.description:
        node["hasDescription"] = comp.description

    if impact_model_id:
        node["forImpactModel"] = [{"@id": impact_model_id}]

    if comp.structured_payload:
        for key, value in comp.structured_payload.items():
            if value:
                node[f"cids:{key}"] = value

    if comp.provenance_source != "manual":
        node["cids:provenance"] = {
            "source": comp.provenance_source,
            "model": comp.provenance_model or "",
            "confidence": comp.confidence_score,
        }

    return node_id, node


def build_layer1_nodes(framework, org_id):
    """Build Layer 1 (program model) nodes from a framework."""
    nodes = []
    refs = {}

    impact_model_id, impact_model_node = _build_impact_model_from_framework(framework, org_id)
    nodes.append(impact_model_node)
    refs["impact_model"] = impact_model_id

    components = framework.components.filter(is_active=True).order_by("sequence_order")
    component_refs_by_type = {}

    for comp in components:
        node_id, node = _component_to_node(comp, org_id, impact_model_id)
        if node_id and node:
            nodes.append(node)
            cids_type = comp.cids_class
            component_refs_by_type.setdefault(cids_type, []).append({"@id": node_id})

    refs["components_by_type"] = component_refs_by_type
    return nodes, refs


# ── Layer 3: De-identified Case Trajectories (placeholder) ────────


def build_layer3_trajectories(program, date_from=None, date_to=None, k_threshold=5):
    """Placeholder for Layer 3 de-identified trajectories.

    Full implementation requires:
    - k-anonymity check (minimum k participants)
    - Date generalisation to quarters
    - Age generalisation to ranges
    - Only for programs with n >= 15
    """
    return []


# ── Full Tier Assembly ────────────────────────────────────────────


def build_full_tier_jsonld(
    programs,
    taxonomy_lens="common_approach",
    date_from=None,
    date_to=None,
    include_layer3=False,
):
    """Assemble a Full Tier CIDS JSON-LD document.

    Combines:
    - Layer 1: Program model from EvaluationFramework/EvaluationComponent
    - Layer 2: Aggregate measurement from Basic Tier export
    - Layer 3: Optional de-identified trajectories
    """
    programs = list(programs)
    org = OrganizationProfile.get_solo()
    org_id = f"urn:konote:org:{org.pk or 1}"

    # Start with Basic Tier + stubs as the foundation (Layer 2)
    basic_doc = build_cids_jsonld_document(
        programs,
        taxonomy_lens=taxonomy_lens,
        date_from=date_from,
        date_to=date_to,
        include_full_tier_stubs=True,
    )

    graph = basic_doc["@graph"]
    seen_ids = {n["@id"] for n in graph if "@id" in n}

    def add_node(node):
        if node["@id"] not in seen_ids:
            seen_ids.add(node["@id"])
            graph.append(node)

    # Layer 1: Add EvaluationFramework-sourced nodes
    all_refs = {}
    for program in programs:
        frameworks = EvaluationFramework.objects.filter(
            program=program,
            status__in=["active", "draft"],
        ).order_by("-status", "-updated_at")

        fw = frameworks.first()
        if not fw:
            continue

        layer1_nodes, refs = build_layer1_nodes(fw, org_id)
        for node in layer1_nodes:
            add_node(node)
        all_refs[program.pk] = refs

    # Layer 3: Optional trajectories
    if include_layer3:
        for program in programs:
            trajectories = build_layer3_trajectories(program, date_from, date_to)
            for node in trajectories:
                add_node(node)

    # Compute class coverage
    cids_classes = {n["@type"] for n in graph if "@type" in n}

    # Determine compliance tier
    full_tier_required = {
        "cids:Service", "cids:Activity", "cids:Counterfactual",
    }
    essential_tier_classes = {
        "cids:ImpactModel", "cids:BeneficialStakeholder",
        "cids:StakeholderOutcome", "cids:Output",
    }

    if full_tier_required.issubset(cids_classes):
        tier = "Full"
    elif essential_tier_classes.intersection(cids_classes):
        tier = "Essential"
    else:
        tier = "Basic"

    basic_doc["cids:complianceTier"] = f"{tier}Tier"
    basic_doc["cids:classCount"] = len(cids_classes)
    basic_doc["cids:classCoverage"] = sorted(cids_classes)

    # Add attestation metadata if any framework is attested
    attested_frameworks = []
    for program in programs:
        for fw in EvaluationFramework.objects.filter(
            program=program, status__in=["active", "draft"],
            evaluator_attestation_by__isnull=False,
        ):
            attested_frameworks.append({
                "program": program.name,
                "framework": fw.name,
                "attestedBy": fw.evaluator_attestation_by.display_name if fw.evaluator_attestation_by else "",
                "attestedAt": fw.evaluator_attestation_at.isoformat() if fw.evaluator_attestation_at else "",
                "scope": fw.evaluator_attestation_scope or [],
            })

    if attested_frameworks:
        basic_doc["cids:evaluatorAttestations"] = attested_frameworks

    return basic_doc


def serialize_full_tier_jsonld(*args, indent=2, **kwargs):
    """Serialize Full Tier JSON-LD to a string."""
    document = build_full_tier_jsonld(*args, **kwargs)
    return json.dumps(document, indent=indent, ensure_ascii=False)


# ── Coverage Dashboard Helpers ─────────────────────────────────────


FULL_TIER_CLASSES = [
    ("cids:Organization", "Organization"),
    ("cids:ImpactModel", "Impact Model"),
    ("cids:Service", "Service"),
    ("cids:Activity", "Activity"),
    ("cids:Output", "Output"),
    ("cids:Outcome", "Outcome"),
    ("cids:Indicator", "Indicator"),
    ("cids:IndicatorReport", "Indicator Report"),
    ("cids:BeneficialStakeholder", "Stakeholder"),
    ("cids:StakeholderOutcome", "Stakeholder Outcome"),
    ("cids:ImpactRisk", "Impact Risk"),
    ("cids:Counterfactual", "Counterfactual"),
    ("cids:Theme", "Theme"),
    ("cids:Code", "Code"),
]


def get_program_cids_coverage(program):
    """Return CIDS class coverage status for a program.

    Returns a list of dicts with class_uri, label, status (present/missing),
    and source (basic_tier/framework/stub).
    """
    # Check what the framework provides
    framework_classes = set()
    fw = EvaluationFramework.objects.filter(
        program=program, status__in=["active", "draft"],
    ).first()
    if fw:
        framework_classes = fw.cids_class_coverage

    # Basic tier always provides these
    basic_classes = {
        "cids:Organization", "cids:Outcome", "cids:Indicator",
        "cids:IndicatorReport", "cids:Theme", "cids:Code",
    }

    # Stub classes from Phase 0.5
    stub_classes = set()
    if program.description:
        stub_classes.add("cids:ImpactModel")
    if program.population_served_codes:
        stub_classes.add("cids:BeneficialStakeholder")

    results = []
    for class_uri, label in FULL_TIER_CLASSES:
        if class_uri in framework_classes:
            source = "framework"
            status = "present"
        elif class_uri in basic_classes:
            source = "basic_tier"
            status = "present"
        elif class_uri in stub_classes:
            source = "stub"
            status = "present"
        else:
            source = ""
            status = "missing"

        results.append({
            "class_uri": class_uri,
            "label": label,
            "status": status,
            "source": source,
        })
    return results


def get_agency_cids_summary():
    """Return agency-wide CIDS compliance summary."""
    programs = Program.objects.filter(status="active")
    program_summaries = []
    for program in programs:
        coverage = get_program_cids_coverage(program)
        present = sum(1 for c in coverage if c["status"] == "present")
        total = len(coverage)
        fw = EvaluationFramework.objects.filter(
            program=program, status__in=["active", "draft"],
        ).first()
        program_summaries.append({
            "program": program,
            "coverage": coverage,
            "present": present,
            "total": total,
            "pct": round(present / total * 100) if total else 0,
            "has_framework": fw is not None,
            "is_attested": fw.is_attested if fw else False,
        })
    return program_summaries
