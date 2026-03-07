# Phase 0.5: Quick Full Tier Nodes from Existing Data — Agent Prompt

Extend the Basic Tier export to emit 4 additional CIDS Full Tier classes from data that already exists in the database. No new models needed.

## Prerequisites

Phase 0 must be merged and deployed (TaxonomyMapping migration applied, `cids_jsonld.py` committed and working).

## Branch

Create branch `feat/cids-quick-full-tier-nodes` off `develop`.

## Context

The Basic Tier export currently emits 6 CIDS classes: Organization, Outcome, Indicator, IndicatorReport, Theme, Code (plus Address). Full Tier requires 8 additional classes. Four of those can be derived from existing data without any new models:

| Class | Data source | How |
|-------|------------|-----|
| `cids:ImpactModel` | `Program.description` | One node per program — theory of change from program description |
| `cids:Stakeholder` | `Program.population_served_codes` | One node per population code — stakeholder *groups*, not individuals |
| `cids:StakeholderOutcome` | Aggregate `PlanTarget.achievement_status` | Group outcomes by achievement status distribution |
| `cids:Output` | `MetricValue` observation counts | Aggregate output totals per metric |

The remaining 4 (Service, Activity, ImpactRisk, Counterfactual) require structured evaluation data that doesn't exist yet — those come from Phase 1 (EvaluationComponent).

## 1. Edit `apps/reports/cids_jsonld.py`

### Add helper functions before `build_cids_jsonld_document()`:

```python
def _build_impact_model_node(program, org_id, outcome_refs, indicator_refs):
    """Build a cids:ImpactModel node from program description."""
    from apps.plans.cids import build_local_cids_uri

    model_id = build_local_cids_uri("impact-model", program.pk)
    node = {
        "@id": model_id,
        "@type": "cids:ImpactModel",
        "cids:hasName": f"Impact Model: {program.name}",
        "cids:forOrganization": {"@id": org_id},
    }
    if program.description:
        node["cids:hasDescription"] = program.description
    if outcome_refs:
        node["cids:hasOutcome"] = outcome_refs
    if indicator_refs:
        node["cids:hasIndicator"] = indicator_refs
    return model_id, node


def _build_stakeholder_nodes(program, org_id):
    """Build cids:Stakeholder nodes from population_served_codes."""
    from apps.plans.cids import build_local_cids_uri

    nodes = []
    codes = program.population_served_codes or []
    if not codes:
        return nodes

    for i, code in enumerate(codes):
        stakeholder_id = build_local_cids_uri("stakeholder", f"{program.pk}-{i}")
        label = code.replace("_", " ").title()
        node = {
            "@id": stakeholder_id,
            "@type": "cids:Stakeholder",
            "cids:hasName": label,
            "cids:hasDescription": f"Stakeholder group: {label}",
            "cids:forOrganization": {"@id": org_id},
        }
        nodes.append((stakeholder_id, node))

    return nodes


def _build_stakeholder_outcome_node(program, org_id, outcome_id):
    """Build a cids:StakeholderOutcome from aggregate achievement data."""
    from apps.plans.cids import build_local_cids_uri
    from apps.plans.models import PlanTarget

    targets = PlanTarget.objects.filter(
        plan_section__program=program,
        status__in=["default", "completed"],
    )
    total = targets.count()
    if total == 0:
        return None, None

    # Count by achievement status
    from django.db.models import Count
    status_counts = dict(
        targets.exclude(achievement_status="")
        .values_list("achievement_status")
        .annotate(c=Count("pk"))
        .values_list("achievement_status", "c")
    )

    achieved = status_counts.get("achieved", 0) + status_counts.get("sustaining", 0)
    in_progress = status_counts.get("in_progress", 0) + status_counts.get("improving", 0)

    so_id = build_local_cids_uri("stakeholder-outcome", program.pk)
    node = {
        "@id": so_id,
        "@type": "cids:StakeholderOutcome",
        "cids:hasName": f"Aggregate outcomes: {program.name}",
        "cids:forOutcome": {"@id": outcome_id},
        "cids:forOrganization": {"@id": org_id},
        "cids:hasDescription": (
            f"Of {total} participant targets: "
            f"{achieved} achieved/sustaining, "
            f"{in_progress} in progress/improving."
        ),
    }
    return so_id, node


def _build_output_nodes(program, org_id, metric_ids, note_filter):
    """Build cids:Output nodes from observation counts."""
    from apps.plans.cids import build_local_cids_uri
    from apps.notes.models import MetricValue
    from apps.plans.models import MetricDefinition
    from django.db.models import Count

    metrics_with_counts = (
        MetricValue.objects.filter(
            metric_def_id__in=metric_ids,
            progress_note_target__plan_target__plan_section__program=program,
            progress_note_target__progress_note__status="default",
        )
        .filter(note_filter)
        .values("metric_def_id", "metric_def__name")
        .annotate(obs_count=Count("pk"))
    )

    nodes = []
    for entry in metrics_with_counts:
        output_id = build_local_cids_uri("output", f"{program.pk}-{entry['metric_def_id']}")
        node = {
            "@id": output_id,
            "@type": "cids:Output",
            "cids:hasName": f"Observations: {entry['metric_def__name']}",
            "cids:hasDescription": (
                f"{entry['obs_count']} recorded observations for "
                f"{entry['metric_def__name']} in {program.name}."
            ),
            "cids:forOrganization": {"@id": org_id},
        }
        nodes.append((output_id, node))

    return nodes
```

### Integrate into `build_cids_jsonld_document()`

In the main function, after the per-program metrics loop (after `add_node(outcome_node)` and `org_outcomes.append(...)`), add:

```python
        # ── Full Tier stub nodes from existing data ──────────────
        # ImpactModel
        impact_model_id, impact_model_node = _build_impact_model_node(
            program, org_id,
            outcome_refs=[{"@id": outcome_id}],
            indicator_refs=outcome_indicator_refs,
        )
        add_node(impact_model_node)

        # Stakeholder groups
        stakeholder_nodes = _build_stakeholder_nodes(program, org_id)
        stakeholder_refs = []
        for sh_id, sh_node in stakeholder_nodes:
            add_node(sh_node)
            stakeholder_refs.append({"@id": sh_id})
        if stakeholder_refs:
            impact_model_node["cids:hasStakeholder"] = stakeholder_refs

        # StakeholderOutcome (aggregate achievement)
        so_id, so_node = _build_stakeholder_outcome_node(
            program, org_id, outcome_id,
        )
        if so_node:
            add_node(so_node)
            impact_model_node["cids:hasStakeholderOutcome"] = [{"@id": so_id}]

        # Output nodes (observation counts)
        output_nodes = _build_output_nodes(
            program, org_id, metric_ids, note_filter,
        )
        output_refs = []
        for out_id, out_node in output_nodes:
            add_node(out_node)
            output_refs.append({"@id": out_id})
        if output_refs:
            impact_model_node["cids:hasOutput"] = output_refs
```

## 2. Update tests — edit `tests/test_cids.py`

Add tests verifying the new nodes:

```python
class FullTierStubNodesTest(TestCase):
    """Test that Full Tier stub nodes are emitted from existing data."""

    def setUp(self):
        enc_module._fernet = None
        self.org = OrganizationProfile.get_solo()
        self.org.legal_name = "Test Org"
        self.org.save()

        self.program = Program.objects.create(
            name="Test Program",
            description="A program that helps youth find employment.",
            population_served_codes=["youth_16_24", "unemployed"],
            cids_sector_code="6100",
        )

    def test_impact_model_emitted(self):
        doc = build_cids_jsonld_document(programs=[self.program])
        types = {n["@type"] for n in doc["@graph"]}
        self.assertIn("cids:ImpactModel", types)
        im = next(n for n in doc["@graph"] if n["@type"] == "cids:ImpactModel")
        self.assertIn("A program that helps youth", im["cids:hasDescription"])

    def test_stakeholder_nodes_from_population_codes(self):
        doc = build_cids_jsonld_document(programs=[self.program])
        stakeholders = [n for n in doc["@graph"] if n["@type"] == "cids:Stakeholder"]
        self.assertEqual(len(stakeholders), 2)  # youth_16_24, unemployed
        names = {s["cids:hasName"] for s in stakeholders}
        self.assertIn("Youth 16 24", names)
        self.assertIn("Unemployed", names)

    def test_no_stakeholder_when_no_codes(self):
        self.program.population_served_codes = []
        self.program.save()
        doc = build_cids_jsonld_document(programs=[self.program])
        stakeholders = [n for n in doc["@graph"] if n["@type"] == "cids:Stakeholder"]
        self.assertEqual(len(stakeholders), 0)

    def test_stakeholder_outcome_with_targets(self):
        # Create client, section, target with achievement
        user = User.objects.create_user(username="t@t.ca", password="x", is_admin=True)
        client = ClientFile(record_id="T-001", status="active", is_demo=True)
        client.first_name = "Test"
        client.last_name = "Person"
        client.save()
        section = PlanSection.objects.create(
            client_file=client, program=self.program, name="Goals",
        )
        target = PlanTarget(plan_section=section, client_file=client)
        target.name = "Get a job"
        target.achievement_status = "achieved"
        target.save()

        doc = build_cids_jsonld_document(programs=[self.program])
        so_nodes = [n for n in doc["@graph"] if n["@type"] == "cids:StakeholderOutcome"]
        self.assertEqual(len(so_nodes), 1)
        self.assertIn("1 achieved", so_nodes[0]["cids:hasDescription"])

    def test_no_pii_in_stakeholder_outcome(self):
        """StakeholderOutcome must be aggregate — no participant names."""
        user = User.objects.create_user(username="t2@t.ca", password="x", is_admin=True)
        client = ClientFile(record_id="T-002", status="active", is_demo=True)
        client.first_name = "SecretName"
        client.last_name = "Hidden"
        client.save()
        section = PlanSection.objects.create(
            client_file=client, program=self.program, name="Goals",
        )
        target = PlanTarget(plan_section=section, client_file=client)
        target.name = "Confidential goal"
        target.achievement_status = "in_progress"
        target.save()

        doc = build_cids_jsonld_document(programs=[self.program])
        export_str = json.dumps(doc)
        self.assertNotIn("SecretName", export_str)
        self.assertNotIn("Confidential goal", export_str)
```

## 3. Update the export command

Edit `apps/admin_settings/management/commands/export_cids_jsonld.py` — no changes needed. The command already calls `build_cids_jsonld_document()` which will now emit the extra nodes automatically.

## 4. Run SHACL validation

After making changes, run:
```bash
python manage.py validate_cids_jsonld
```

The Basic Tier SHACL shapes won't validate Full Tier classes (they're not in the shapes). But the export should still pass Basic Tier validation — the extra nodes should be ignored by the shapes validator.

If SHACL validation fails because of the new nodes, wrap them in a flag:
```python
def build_cids_jsonld_document(..., include_full_tier_stubs=True):
```
And only add the stub nodes when `include_full_tier_stubs=True`. The validate command can pass `include_full_tier_stubs=False`.

## Acceptance criteria

- [ ] `build_cids_jsonld_document()` now emits ImpactModel, Stakeholder, StakeholderOutcome, Output nodes
- [ ] ImpactModel node links to Outcomes, Indicators, Stakeholders, StakeholderOutcomes, Outputs
- [ ] Stakeholder nodes derived from `Program.population_served_codes`
- [ ] StakeholderOutcome aggregates PlanTarget achievement — **no individual names or goals**
- [ ] Output nodes show observation counts per metric
- [ ] PII absence verified in tests
- [ ] Basic Tier SHACL validation still passes
- [ ] Coverage rises from ~50% to ~79% (11/14 classes)
- [ ] French translations if any new user-facing strings
