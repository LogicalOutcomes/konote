# Phase 4: Full Tier CIDS JSON-LD Export Assembly — Agent Prompt

Assemble Privacy-First Full Tier CIDS export using evaluation frameworks, enriched metadata, and existing aggregate measurement. Depends on Phases 1-3.

## Context

KoNote already has a working Basic Tier JSON-LD export at `apps/reports/cids_jsonld.py` via `build_cids_jsonld_document()`. This phase extends it to Full Tier by adding:

- **Layer 1 (Program Model)**: ImpactModel, Service, Activity, Output, Stakeholder, StakeholderOutcome, ImpactRisk, Counterfactual — all from EvaluationFramework/EvaluationComponent data
- **Layer 2 (Aggregate Measurement)**: Already exists (IndicatorReport from Basic Tier)
- **Layer 3 (Optional Case Trajectories)**: Pseudonymised individual outcome pathways with de-identification

The existing `build_cids_jsonld_document()` handles Layer 2. This phase adds Layer 1 and optionally Layer 3.

## Branch

Create branch `feat/full-tier-cids-export` off `develop`.

## Prerequisites

Phases 1-3 must be merged.

## 1. Full Tier serialiser — create `apps/reports/cids_full_tier.py`

```python
"""
Full Tier CIDS JSON-LD export builder.

Extends the Basic Tier export (cids_jsonld.py) with:
- Layer 1: Program model metadata from EvaluationFramework/EvaluationComponent
- Layer 3 (optional): De-identified individual outcome trajectories

Layer 2 (aggregate measurement) is already handled by build_cids_jsonld_document().
"""
from __future__ import annotations

import json
from datetime import datetime

from django.utils import timezone

from apps.admin_settings.models import OrganizationProfile, TaxonomyMapping
from apps.programs.models import EvaluationFramework, EvaluationComponent, Program
from apps.reports.cids_jsonld import (
    CIDS_CONTEXT,
    CIDS_VERSION,
    build_cids_jsonld_document,
)
from apps.reports.models import ExportMetadataSnapshot


def build_full_tier_jsonld(
    program,
    date_from=None,
    date_to=None,
    include_layer3=False,
    snapshot=None,
):
    """
    Build a CIDS Full Tier JSON-LD document.

    Args:
        program: Program instance
        date_from: Start date for measurement period
        date_to: End date for measurement period
        include_layer3: Whether to include de-identified case trajectories
        snapshot: ExportMetadataSnapshot to apply (or None)

    Returns:
        dict: JSON-LD document
    """
    # Start with Basic Tier (Layer 2)
    basic_doc = build_cids_jsonld_document(
        programs=[program],
        date_from=date_from,
        date_to=date_to,
    )

    graph = basic_doc.get("@graph", [])

    # Layer 1: Program model from EvaluationFramework
    try:
        framework = program.evaluation_framework
    except EvaluationFramework.DoesNotExist:
        framework = None

    if framework:
        layer1_nodes = _build_layer1_nodes(program, framework)
        graph.extend(layer1_nodes)

    # Apply enriched metadata from snapshot
    if snapshot:
        _apply_snapshot_metadata(graph, snapshot)

    # Layer 3: Optional de-identified trajectories
    if include_layer3:
        layer3_nodes = _build_layer3_trajectories(program, date_from, date_to)
        graph.extend(layer3_nodes)

    # Add Full Tier metadata
    basic_doc["@graph"] = graph
    basic_doc["cids:complianceTier"] = "Full"
    basic_doc["cids:version"] = CIDS_VERSION

    # Add evaluator attestation if present
    if framework and framework.attested_by:
        basic_doc["cids:evaluatorAttestation"] = {
            "attestedBy": framework.attested_by.get_full_name(),
            "attestedAt": framework.attested_at.isoformat() if framework.attested_at else None,
            "attestationNote": framework.attestation_note,
        }

    return basic_doc


def _build_layer1_nodes(program, framework):
    """Build Layer 1 JSON-LD nodes from EvaluationFramework and components."""
    from apps.plans.cids import build_local_cids_uri

    nodes = []
    program_uri = build_local_cids_uri("program", program.pk)

    # ImpactModel node
    impact_model_uri = build_local_cids_uri("impact-model", framework.pk)
    impact_model = {
        "@id": impact_model_uri,
        "@type": "cids:ImpactModel",
        "cids:hasName": f"Impact Model: {program.name}",
        "cids:forOrganization": program_uri,
    }
    if framework.outcome_chain_summary:
        impact_model["cids:hasDescription"] = framework.outcome_chain_summary

    # Collect component references
    stakeholder_uris = []
    outcome_uris = []
    risk_uris = []

    for comp in framework.components.all():
        node = _build_component_node(comp, program_uri, framework)
        if node:
            nodes.append(node)
            comp_uri = node["@id"]

            if comp.component_type == "participant_group":
                stakeholder_uris.append(comp_uri)
            elif comp.component_type == "outcome":
                outcome_uris.append(comp_uri)
            elif comp.component_type in ("risk", "mitigation"):
                risk_uris.append(comp_uri)

    # Link to impact model
    if stakeholder_uris:
        impact_model["cids:hasStakeholder"] = stakeholder_uris
    if outcome_uris:
        impact_model["cids:hasStakeholderOutcome"] = outcome_uris
    if risk_uris:
        impact_model["cids:hasImpactRisk"] = risk_uris

    nodes.insert(0, impact_model)
    return nodes


def _build_component_node(comp, program_uri, framework):
    """Build a JSON-LD node for a single EvaluationComponent."""
    from apps.plans.cids import build_local_cids_uri

    cids_class = comp.cids_class
    if not cids_class:
        return None  # Skip metadata-only types (assumption)

    comp_uri = build_local_cids_uri(
        comp.component_type.replace("_", "-"), comp.pk
    )

    node = {
        "@id": comp_uri,
        "@type": cids_class,
        "cids:hasName": comp.title,
    }

    if comp.description:
        node["cids:hasDescription"] = comp.description

    # Add structured payload fields
    payload = comp.structured_payload or {}

    if comp.component_type == "participant_group":
        if payload.get("demographics"):
            node["cids:hasDemographic"] = payload["demographics"]
        if payload.get("estimated_size"):
            node["cids:hasSize"] = payload["estimated_size"]

    elif comp.component_type == "outcome":
        if payload.get("indicator_name"):
            node["cids:hasIndicator"] = payload["indicator_name"]
        if payload.get("measurement_method"):
            node["cids:hasMeasurementMethod"] = payload["measurement_method"]

    elif comp.component_type in ("risk", "mitigation"):
        if payload.get("likelihood"):
            node["cids:hasLikelihood"] = payload["likelihood"]
        if payload.get("severity"):
            node["cids:hasSeverity"] = payload["severity"]
        if payload.get("mitigation_strategy"):
            node["cids:hasMitigation"] = payload["mitigation_strategy"]

    elif comp.component_type == "counterfactual":
        node["cids:hasCounterfactualDescription"] = comp.description

    # Add taxonomy mappings for this component
    mappings = TaxonomyMapping.objects.filter(
        subject_id=str(comp.pk),
        review_status="approved",
    )
    if mappings.exists():
        node["cids:hasCode"] = [
            {
                "@type": "cids:Code",
                "cids:hasCodeValue": m.code_value,
                "cids:hasCodeLabel": m.code_label,
                "cids:inCodeList": m.list_name,
            }
            for m in mappings
        ]

    return node


def _apply_snapshot_metadata(graph, snapshot):
    """Apply enriched metadata from a snapshot to the graph."""
    payload = snapshot.snapshot_payload or {}
    # Snapshot items are narrative improvements — they don't add new nodes,
    # they enrich existing ones. For now, add as annotations.
    for item in payload.get("accepted_items", []):
        # Find matching node by field_path and update description
        # This is a simple implementation — could be more sophisticated
        pass  # Phase 4 refinement: match items to nodes


def _build_layer3_trajectories(program, date_from, date_to):
    """
    Build Layer 3: de-identified individual outcome trajectories.

    Uses k-anonymity (k>=5), date generalisation (quarters), n>=15 minimum.
    Only includes programs with sufficient participants.
    """
    from apps.clients.models import Enrolment
    from apps.notes.models import MetricValue
    from apps.plans.models import PlanTarget

    nodes = []

    # Count active participants
    enrolments = Enrolment.objects.filter(
        program=program,
        status="active",
    )
    participant_count = enrolments.count()

    if participant_count < 15:
        # Below threshold — skip Layer 3
        return nodes

    # Get plan targets with achievement data
    targets = PlanTarget.objects.filter(
        plan__enrolment__program=program,
        plan__enrolment__status="active",
    ).select_related("plan", "plan__enrolment")

    # Group by outcome type for k-anonymity
    outcome_groups = {}
    for target in targets:
        key = target.description[:50]  # Group by target description prefix
        if key not in outcome_groups:
            outcome_groups[key] = []
        outcome_groups[key].append(target)

    from apps.plans.cids import build_local_cids_uri

    for group_key, group_targets in outcome_groups.items():
        if len(group_targets) < 5:
            # k-anonymity: suppress groups smaller than 5
            continue

        # Build de-identified trajectory node
        trajectory_uri = build_local_cids_uri(
            "trajectory",
            hash(group_key) % 100000,
        )

        # Generalise dates to quarters
        quarters = set()
        for t in group_targets:
            if t.created_at:
                q = f"{t.created_at.year}-Q{(t.created_at.month - 1) // 3 + 1}"
                quarters.add(q)

        # Count achievement statuses
        statuses = {}
        for t in group_targets:
            status = getattr(t, "achievement_status", "unknown")
            statuses[status] = statuses.get(status, 0) + 1

        node = {
            "@id": trajectory_uri,
            "@type": "cids:OutcomeTrajectory",
            "cids:hasName": f"De-identified trajectory: {group_key}",
            "cids:cohortSize": len(group_targets),
            "cids:reportingPeriods": sorted(quarters),
            "cids:achievementDistribution": statuses,
            "cids:deIdentificationMethod": "k-anonymity (k>=5), dates generalised to quarters",
        }
        nodes.append(node)

    return nodes


def get_full_tier_coverage(program):
    """
    Return a coverage report showing which CIDS Full Tier classes are populated.

    Used by the export status page to show compliance progress.
    """
    coverage = {}

    try:
        framework = program.evaluation_framework
    except EvaluationFramework.DoesNotExist:
        framework = None

    # Check each CIDS class
    cids_classes = [
        ("cids:ImpactModel", "Impact Model"),
        ("cids:Service", "Service"),
        ("cids:Activity", "Activity"),
        ("cids:Output", "Output"),
        ("cids:Stakeholder", "Stakeholder"),
        ("cids:StakeholderOutcome", "Stakeholder Outcome"),
        ("cids:ImpactRisk", "Impact Risk"),
        ("cids:Counterfactual", "Counterfactual"),
        ("cids:Input", "Input"),
        ("cids:ImpactDimension", "Impact Dimension"),
        ("cids:Indicator", "Indicator"),
        ("cids:IndicatorReport", "Indicator Report"),
        ("cids:Outcome", "Outcome"),
    ]

    for cids_uri, label in cids_classes:
        populated = False
        source = "Not started"

        if cids_uri == "cids:ImpactModel":
            populated = framework is not None
            source = "Evaluation Framework" if populated else "Create framework"

        elif cids_uri in ("cids:Indicator", "cids:IndicatorReport", "cids:Outcome"):
            # These come from Basic Tier (existing)
            from apps.plans.models import MetricDefinition
            populated = MetricDefinition.objects.filter(
                programs=program
            ).exists()
            source = "Metric definitions" if populated else "Add metrics"

        elif framework:
            # Check for matching component type
            type_map = {
                "cids:Service": "service",
                "cids:Activity": "activity",
                "cids:Output": "output",
                "cids:Stakeholder": "participant_group",
                "cids:StakeholderOutcome": "outcome",
                "cids:ImpactRisk": "risk",
                "cids:Counterfactual": "counterfactual",
                "cids:Input": "input",
                "cids:ImpactDimension": "impact_dimension",
            }
            comp_type = type_map.get(cids_uri)
            if comp_type:
                populated = framework.components.filter(
                    component_type=comp_type
                ).exists()
                source = "Evaluation component" if populated else f"Add {comp_type} component"

        coverage[cids_uri] = {
            "label": label,
            "populated": populated,
            "source": source,
        }

    return coverage
```

## 2. Export view — add to `apps/reports/views.py`

```python
@login_required
@admin_required
def full_tier_export_status(request, program_id):
    """Show Full Tier CIDS export status and coverage for a program."""
    program = get_object_or_404(Program, pk=program_id)

    from apps.reports.cids_full_tier import get_full_tier_coverage
    coverage = get_full_tier_coverage(program)

    try:
        framework = program.evaluation_framework
    except EvaluationFramework.DoesNotExist:
        framework = None

    total = len(coverage)
    populated = sum(1 for v in coverage.values() if v["populated"])

    return render(request, "reports/full_tier_export_status.html", {
        "program": program,
        "framework": framework,
        "coverage": coverage,
        "total_classes": total,
        "populated_classes": populated,
        "coverage_pct": round(populated / total * 100) if total else 0,
    })


@login_required
@admin_required
def generate_full_tier_export(request, program_id):
    """Generate Full Tier CIDS JSON-LD export."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    program = get_object_or_404(Program, pk=program_id)

    from apps.reports.cids_full_tier import build_full_tier_jsonld
    import json
    import os
    import tempfile

    include_layer3 = request.POST.get("include_layer3") == "on"

    doc = build_full_tier_jsonld(
        program=program,
        include_layer3=include_layer3,
    )

    # Save to file
    export_dir = getattr(settings, "SECURE_EXPORT_DIR", tempfile.gettempdir())
    filename = f"cids-full-tier-{program.pk}-{timezone.now().strftime('%Y%m%d-%H%M%S')}.jsonld"
    filepath = os.path.join(export_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)

    # Create SecureExportLink
    link = SecureExportLink.objects.create(
        created_by=request.user,
        expires_at=timezone.now() + timedelta(hours=24),
        export_type="standard_report",
        client_count=0,
        recipient="CIDS Full Tier Export",
        filename=filename,
        file_path=filepath,
        contains_pii=include_layer3,  # Layer 3 may contain de-identified data
        filters_json=json.dumps({"program_id": program.pk, "tier": "full"}),
    )

    messages.success(request, _("Full Tier CIDS export generated."))
    return redirect("reports:export_link_created", link_id=link.pk)
```

## 3. URLs — add to `apps/reports/urls.py`

```python
path("programs/<int:program_id>/full-tier-status/",
     views.full_tier_export_status,
     name="full_tier_export_status"),
path("programs/<int:program_id>/full-tier-export/",
     views.generate_full_tier_export,
     name="generate_full_tier_export"),
```

## 4. Template — create `templates/reports/full_tier_export_status.html`

```html
{% extends "base.html" %}
{% load i18n %}

{% block title %}{% trans "Full Tier CIDS Export" %} — {{ program.name }}{% endblock %}

{% block content %}
<h1>{% trans "Full Tier CIDS Export Status" %}</h1>
<p>{{ program.name }}</p>

<h2>{% trans "CIDS Class Coverage" %}: {{ populated_classes }}/{{ total_classes }} ({{ coverage_pct }}%)</h2>

<progress value="{{ populated_classes }}" max="{{ total_classes }}"></progress>

<table role="grid">
  <thead>
    <tr>
      <th>{% trans "CIDS Class" %}</th>
      <th>{% trans "Status" %}</th>
      <th>{% trans "Source" %}</th>
    </tr>
  </thead>
  <tbody>
    {% for uri, info in coverage.items %}
    <tr>
      <td><code>{{ uri }}</code> <small>({{ info.label }})</small></td>
      <td>{% if info.populated %}&#10003;{% else %}&#10007;{% endif %}</td>
      <td>{{ info.source }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<h2>{% trans "Three-Layer Architecture" %}</h2>
<table role="grid">
  <thead>
    <tr><th>{% trans "Layer" %}</th><th>{% trans "Status" %}</th><th>{% trans "Privacy" %}</th></tr>
  </thead>
  <tbody>
    <tr>
      <td>{% trans "1. Program Model" %}</td>
      <td>{% if framework %}<mark>{% trans "Ready" %}</mark>{% else %}{% trans "Create framework" %}{% endif %}</td>
      <td>{% trans "No privacy concern" %}</td>
    </tr>
    <tr>
      <td>{% trans "2. Aggregate Measurement" %}</td>
      <td><mark>{% trans "Ready" %}</mark> <small>({% trans "Basic Tier export" %})</small></td>
      <td>{% trans "Existing suppression (k>=5)" %}</td>
    </tr>
    <tr>
      <td>{% trans "3. Case Trajectories" %} <small>({% trans "optional" %})</small></td>
      <td>{% trans "Available" %}</td>
      <td>{% trans "De-identified (k>=5, dates to quarters, n>=15)" %}</td>
    </tr>
  </tbody>
</table>

{% if framework and framework.attested_by %}
<h2>{% trans "Evaluator Attestation" %}</h2>
<dl>
  <dt>{% trans "Attested by" %}</dt>
  <dd>{{ framework.attested_by.get_full_name }}</dd>
  <dt>{% trans "Date" %}</dt>
  <dd>{{ framework.attested_at|date:"Y-m-d" }}</dd>
  <dt>{% trans "Note" %}</dt>
  <dd>{{ framework.attestation_note }}</dd>
</dl>
{% endif %}

<h2>{% trans "Generate Export" %}</h2>
<form method="post" action="{% url 'reports:generate_full_tier_export' program_id=program.pk %}">
  {% csrf_token %}
  <label>
    <input type="checkbox" name="include_layer3">
    {% trans "Include Layer 3 (de-identified case trajectories)" %}
  </label>
  <small>{% trans "Layer 3 uses k-anonymity (k>=5) and date generalisation. Programs must have at least 15 participants." %}</small>
  <button type="submit" {% if coverage_pct < 30 %}class="secondary"{% endif %}>
    {% trans "Generate Full Tier JSON-LD" %}
  </button>
  {% if coverage_pct < 30 %}
  <small>{% trans "Low coverage — consider adding more evaluation components first." %}</small>
  {% endif %}
</form>

{% if framework %}
<p><a href="{% url 'programs:evaluation_framework_detail' framework_id=framework.pk %}">{% trans "Edit Evaluation Framework" %}</a></p>
{% else %}
<p><a href="{% url 'programs:evaluation_framework_create' program_id=program.pk %}" role="button" class="secondary">{% trans "Create Evaluation Framework" %}</a></p>
{% endif %}
{% endblock %}
```

## 5. Tests — create `tests/test_full_tier_export.py`

```python
"""Tests for Full Tier CIDS JSON-LD export."""
import json
from datetime import date

from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import (
    Program, UserProgramRole, EvaluationFramework, EvaluationComponent,
)
from apps.reports.cids_full_tier import (
    build_full_tier_jsonld, get_full_tier_coverage,
)

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FullTierExportTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="admin@test.ca", password="testpass123", is_admin=True,
        )
        self.program = Program.objects.create(
            name="Youth Employment",
            cids_sector_code="ICNPO:6100",
        )
        self.framework = EvaluationFramework.objects.create(
            program=self.program,
            outcome_chain_summary="Youth gain employment skills through training",
            risk_summary="Economic downturn may reduce job placements",
            counterfactual_summary="Without intervention, youth unemployment persists",
            quality_state="confirmed",
            created_by=self.user,
        )

    def test_basic_full_tier_structure(self):
        doc = build_full_tier_jsonld(self.program)
        self.assertEqual(doc.get("cids:complianceTier"), "Full")
        graph = doc.get("@graph", [])
        # Should have at least ImpactModel node
        types = [n.get("@type") for n in graph]
        self.assertIn("cids:ImpactModel", types)

    def test_components_in_export(self):
        EvaluationComponent.objects.create(
            framework=self.framework,
            component_type="participant_group",
            title="Youth aged 16-24",
            description="Unemployed youth in Toronto",
        )
        EvaluationComponent.objects.create(
            framework=self.framework,
            component_type="service",
            title="Job readiness training",
        )
        EvaluationComponent.objects.create(
            framework=self.framework,
            component_type="risk",
            title="Economic downturn",
            structured_payload={"likelihood": "medium", "severity": "high"},
        )

        doc = build_full_tier_jsonld(self.program)
        graph = doc.get("@graph", [])
        types = [n.get("@type") for n in graph]

        self.assertIn("cids:Stakeholder", types)
        self.assertIn("cids:Service", types)
        self.assertIn("cids:ImpactRisk", types)

    def test_evaluator_attestation(self):
        self.framework.attested_by = self.user
        self.framework.attested_at = timezone.now()
        self.framework.attestation_note = "Confirmed accuracy"
        self.framework.save()

        doc = build_full_tier_jsonld(self.program)
        attestation = doc.get("cids:evaluatorAttestation")
        self.assertIsNotNone(attestation)
        self.assertEqual(attestation["attestationNote"], "Confirmed accuracy")

    def test_coverage_report(self):
        EvaluationComponent.objects.create(
            framework=self.framework,
            component_type="participant_group",
            title="Youth",
        )
        coverage = get_full_tier_coverage(self.program)
        self.assertTrue(coverage["cids:ImpactModel"]["populated"])
        self.assertTrue(coverage["cids:Stakeholder"]["populated"])
        self.assertFalse(coverage["cids:Service"]["populated"])

    def test_no_framework_still_works(self):
        """Programs without frameworks should still export (Basic Tier only)."""
        program2 = Program.objects.create(name="No Framework Program")
        doc = build_full_tier_jsonld(program2)
        # Should still have @graph but no ImpactModel
        types = [n.get("@type") for n in doc.get("@graph", [])]
        self.assertNotIn("cids:ImpactModel", types)

    def test_layer3_suppressed_below_threshold(self):
        """Layer 3 should be empty when participant count < 15."""
        doc = build_full_tier_jsonld(
            self.program, include_layer3=True,
        )
        # No trajectories because no enrolments
        trajectory_nodes = [
            n for n in doc.get("@graph", [])
            if n.get("@type") == "cids:OutcomeTrajectory"
        ]
        self.assertEqual(len(trajectory_nodes), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FullTierExportViewTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="admin@test.ca", password="testpass123", is_admin=True,
        )
        self.program = Program.objects.create(name="Youth Employment")
        self.client_http = Client()
        self.client_http.login(username="admin@test.ca", password="testpass123")

    def test_status_page_loads(self):
        response = self.client_http.get(
            f"/reports/programs/{self.program.pk}/full-tier-status/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CIDS Class Coverage")

    def test_non_admin_blocked(self):
        User.objects.create_user(
            username="staff@test.ca", password="testpass123", is_admin=False,
        )
        self.client_http.login(username="staff@test.ca", password="testpass123")
        response = self.client_http.get(
            f"/reports/programs/{self.program.pk}/full-tier-status/"
        )
        self.assertEqual(response.status_code, 403)
```

## 6. Link from program detail and evaluation framework

Add a link to the Full Tier export status page from:

1. `templates/programs/evaluation_framework_detail.html` — add at the bottom:
```html
<a href="{% url 'reports:full_tier_export_status' program_id=framework.program.pk %}" role="button" class="secondary">
  {% trans "Full Tier Export Status" %}
</a>
```

2. `templates/programs/detail.html` — add alongside the framework link:
```html
<a href="{% url 'reports:full_tier_export_status' program_id=program.pk %}">{% trans "Full Tier Export" %}</a>
```

## Acceptance criteria

- [ ] `cids_full_tier.py` with `build_full_tier_jsonld()` and `get_full_tier_coverage()`
- [ ] Full Tier document includes `cids:complianceTier: "Full"`
- [ ] Layer 1 nodes built from EvaluationFramework/Component (ImpactModel, Service, Activity, etc.)
- [ ] Layer 3 trajectories use k-anonymity (k>=5), date generalisation (quarters), n>=15 threshold
- [ ] Coverage report shows which CIDS classes are populated vs. missing
- [ ] Evaluator attestation included in export when present
- [ ] Export status page with coverage table, three-layer architecture, generate button
- [ ] Views admin-only
- [ ] Tests: structure, components in export, attestation, coverage, Layer 3 suppression
- [ ] French translations
- [ ] Links from program detail and framework detail pages
