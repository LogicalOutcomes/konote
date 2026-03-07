# CIDS Full Tier Compliance — Honest Assessment

Date: 2026-03-07
Status: Assessment based on code review + attempted live execution

## Executive Summary

**KoNote cannot currently produce a CIDS Full Tier export.** The Basic Tier export code exists but has never been deployed or tested against a live database. The gap to Full Tier requires building 3 new models (Phase 1) and a new JSON-LD serialiser (Phase 4). Phases 2-3 (artifact pipeline, AI enrichment) are nice-to-have quality improvements, not compliance blockers.

However: **Full Tier is genuinely achievable**, and the existing data model already contains much of what's needed. The biggest gap is structured program model metadata (services, activities, counterfactuals), which requires the EvaluationFramework/EvaluationComponent models from Phase 1.

## What's Actually Working Today

### Deployed and tested (in production container)
- **OrganizationProfile** — singleton with legal name, address, description ✓
- **Program** — CIDS metadata fields (cids_sector_code, population_served_codes, description_fr, funder_program_code) ✓
- **MetricDefinition** — CIDS fields (iris_metric_code, sdg_goals, cids_indicator_uri, cids_unit_description, cids_defined_by, cids_has_baseline, cids_theme_override) ✓
- **PlanTarget** — cids_outcome_uri field ✓
- **TaxonomyMapping** — basic version (taxonomy_system, taxonomy_code, taxonomy_label) ✓
- **CidsCodeList** — imported reference data (IRISImpactTheme, IrisMetric53, SDGImpacts, ICNPOsector) ✓
- **SecureExportLink** — with contains_pii flag and approval workflow ✓
- **PII scrubbing** — `apps/reports/pii_scrub.py` ✓
- **k-anonymity suppression** — in report engine ✓
- **5 active demo programs** with real data ✓

### Written but NOT deployed (uncommitted local files)
- **`apps/reports/cids_jsonld.py`** — `build_cids_jsonld_document()` (347 lines)
  - Builds Basic Tier JSON-LD with Organization, Outcome, Indicator, IndicatorReport, Theme, Code nodes
  - **Problem found:** References `mapping_status` field on TaxonomyMapping, but the deployed model doesn't have this field. The local model definition (also uncommitted) has `mapping_status`, `mapping_source`, `confidence_score`, `reviewed_by`, etc.
  - **Cannot run against the live database until the TaxonomyMapping migration is applied**
- **`apps/reports/cids_enrichment.py`** — `derive_cids_theme()`, `get_standards_alignment_data()`
  - Referenced by cids_jsonld.py
  - Also references uncommitted TaxonomyMapping fields
- **`apps/plans/cids.py`** — `build_local_cids_uri()`, `apply_metric_cids_defaults()`, `apply_target_cids_defaults()`
  - CIDS default helpers, triggered by signals
- **`apps/admin_settings/management/commands/export_cids_jsonld.py`** — CLI export command
- **`apps/admin_settings/management/commands/validate_cids_jsonld.py`** — SHACL validation command
- **TaxonomyMapping model updates** — adds mapping_status, mapping_source, confidence_score, reviewed_by, reviewed_at, taxonomy_list_name, rationale fields
- **Taxonomy review pipeline** — `apps/admin_settings/taxonomy_review.py` with AI suggestion workflow

### Not yet written (proposed in agent prompts)
- EvaluationFramework model
- EvaluationComponent model
- EvaluationEvidenceLink model
- ReportValidationProfile model
- CanonicalReportArtifact model
- EnrichmentRun model
- EnrichedMetadataItem model
- ExportMetadataSnapshot model
- Full Tier JSON-LD serialiser (`build_full_tier_jsonld()`)
- De-identification engine for Layer 3
- All associated views, forms, templates

## CIDS Class Coverage

### What the Basic Tier export (cids_jsonld.py) would emit if deployed

| CIDS Class | Present | Source | Notes |
|------------|---------|--------|-------|
| `cids:Organization` | ✓ | OrganizationProfile | Legal name, address, description |
| `cids:Outcome` | ✓ | One per program | Program-level aggregate |
| `cids:Indicator` | ✓ | MetricDefinition | One per active metric |
| `cids:IndicatorReport` | ✓ | MetricValue aggregates | Observation counts |
| `cids:Theme` | ✓ | derive_cids_theme() | From IRIS+ or override |
| `cids:Code` | ✓ | TaxonomyMapping / metric fields | IRIS+, SDG, CA codes |
| `cids:Address` | ✓ | OrganizationProfile | If address fields populated |

**Basic Tier: 7/7 classes (100%)** — but code has never run against live data.

### What's missing for Full Tier

| CIDS Class | Status | Blocker | Quick fix possible? |
|------------|--------|---------|---------------------|
| `cids:ImpactModel` | MISSING | No EvaluationFramework model | **Yes** — could emit from Program.description as minimal stub |
| `cids:Service` | MISSING | No structured service data | No — Program.service_model is too coarse ("individual"/"group"/"both") |
| `cids:Activity` | MISSING | No activity data exists | No — requires EvaluationComponent |
| `cids:Output` | MISSING | No output data exists | **Partial** — could derive from MetricDefinition counts |
| `cids:Stakeholder` | MISSING | No stakeholder group data | **Yes** — could emit from Program.population_served_codes |
| `cids:StakeholderOutcome` | MISSING | No group-level outcome data | **Yes** — could aggregate PlanTarget achievement rates |
| `cids:ImpactRisk` | MISSING | No risk data exists | No — requires EvaluationComponent |
| `cids:Counterfactual` | MISSING | No counterfactual data exists | No — requires EvaluationComponent |

**Full Tier: 7/14 classes (50%)** without any new code.

### With quick fixes (no new models)

Extending `build_cids_jsonld_document()` to emit stub nodes from existing data:

- `cids:ImpactModel` from Program.description → +1
- `cids:Stakeholder` from Program.population_served_codes → +1
- `cids:StakeholderOutcome` from aggregate PlanTarget achievement → +1
- `cids:Output` from observation counts → +1

**With quick fixes: 11/14 classes (79%).**

### Truly blocked (require Phase 1 EvaluationComponent)

- `cids:Service` — needs structured service descriptions
- `cids:Activity` — needs structured activity descriptions
- `cids:Counterfactual` — needs evaluator input on counterfactual

**With Phase 1: 14/14 classes (100%).**

## Critical Blockers

### 1. TaxonomyMapping migration not applied

The CIDS export code (`cids_jsonld.py`) references fields that don't exist in the deployed database:
- `mapping_status` (deployed model has no review status)
- `taxonomy_list_name` (deployed model has no list name reference)

**Impact:** The Basic Tier export will crash immediately if run against the live database.

**Fix:** Commit and deploy the TaxonomyMapping model changes + migration. This is a prerequisite for everything else.

### 2. No conftest support for running CIDS tests

The test file I created runs into django-tenants conflicts when pytest tries to create the test database. The existing `conftest.py` handles this for the main test suite, but files placed outside the `tests/` directory don't pick it up correctly.

**Fix:** Place the test file in `tests/test_full_tier_demo.py` and commit it as part of a branch that also includes the TaxonomyMapping migration.

### 3. Phase 1 models don't exist

EvaluationFramework and EvaluationComponent are required for 3 of the 14 CIDS classes (Service, Activity, Counterfactual). These are purely program-level metadata — no PII concern — but the models need to be built.

## Revised Phase Priorities

Based on this assessment, the phases should be reordered for fastest path to demonstrable Full Tier compliance:

### Phase 0 (PREREQUISITE — do before anything else)
1. Commit TaxonomyMapping model updates + migration
2. Commit `cids_jsonld.py`, `cids_enrichment.py`, `apps/plans/cids.py`
3. Commit management commands (export_cids_jsonld, validate_cids_jsonld)
4. Deploy to dev VPS
5. Run Basic Tier export against live data and verify it works
6. Run SHACL validation against live output

**Estimated effort:** Small — these files exist, just need committing and a migration.

### Phase 0.5 (QUICK WIN — extend Basic Tier to emit stub Full Tier nodes)
Add to `build_cids_jsonld_document()`:
- `cids:ImpactModel` node from Program.description
- `cids:Stakeholder` node from Program.population_served_codes
- `cids:StakeholderOutcome` node from aggregate PlanTarget achievement
- `cids:Output` node from observation counts

**Result:** 11/14 classes (79%) with no new models.

### Phase 1 (CORE — as specified in agent prompt)
Build EvaluationFramework + EvaluationComponent + EvaluationEvidenceLink.
Add Full Tier JSON-LD serialiser that emits all 14 classes.

**Result:** 14/14 classes (100%).

### Phase 4 (QUALITY — evaluator attestation)
Add attestation workflow, coverage dashboard, export status page.

### Phases 2-3 (OPTIONAL — not needed for compliance)
Artifact pipeline, AI enrichment, metadata snapshots.
These improve metadata quality but don't affect class coverage.

## What to Tell Common Approach

### Honest positioning

"KoNote has a working Basic Tier CIDS export with SHACL validation, and a clear path to Full Tier. The Full Tier architecture is designed — most Full Tier classes describe the program model, not individual participants. We're building the evaluation framework editor now (Phase 1) which will populate the remaining 3 classes (Service, Activity, Counterfactual).

Our privacy-first architecture means participant data never leaves the instance. All Full Tier classes we emit are program-level metadata. We propose evaluator attestation as a provenance best practice."

### What you can actually show
1. **Live demo of Basic Tier export** (after Phase 0 deploy) — real JSON-LD from real program data
2. **SHACL validation passing** — against official Common Approach shapes
3. **Wireframes** of evaluation framework editor and Full Tier export status page
4. **Architecture diagram** of three-layer compliance model

### What you cannot show (yet)
1. A working Full Tier JSON-LD export
2. The evaluation framework editor (it's a wireframe, not built)
3. Evaluator attestation workflow
4. De-identified Layer 3 trajectories

## Recommendations

1. **Do Phase 0 immediately** — commit and deploy the existing CIDS code. Get Basic Tier working against live data before the meeting.

2. **Do Phase 0.5 next** — extend the export with stub Full Tier nodes. This gets you to 79% coverage with minimal effort and lets you show "most Full Tier classes populated."

3. **Phase 1 is the real work** — EvaluationFramework is what makes the Full Tier story complete. The agent prompt is ready. Prioritise this over Phases 2-3.

4. **Skip Phases 2-3 for now** — CanonicalReportArtifact and AI enrichment are quality improvements, not compliance requirements. Build them later.

5. **Revise the agent prompts** — the Phase 1 prompt references `EvaluationFramework` fields but doesn't account for the TaxonomyMapping schema mismatch. The deployment pipeline needs the TaxonomyMapping migration first.
