# CIDS Full Tier — Build Plan

Date: 2026-03-07
Status: Ready to execute

## Current state (honest assessment)

### Deployed and working
- Program model with CIDS fields (cids_sector_code, population_served_codes)
- MetricDefinition/PlanTarget with CIDS fields
- CidsCodeList model with ICNPOsector, PopulationServed, SDG, IRIS+ code lists
- TaxonomyMapping model (base fields only — no mapping_status yet)
- SecureExportLink with approval flow, PII tracking
- AI module (`konote/ai.py`) with OpenRouter integration
- PII scrubbing (`apps/reports/pii_scrub.py`)
- k-anonymity suppression in reports (k>=5)
- OrganizationProfile for agency-level CIDS metadata

### Written but NOT deployed (uncommitted code)
- `apps/reports/cids_jsonld.py` — Basic Tier JSON-LD export builder (347 lines)
- `apps/reports/cids_enrichment.py` — theme derivation, standards alignment
- `apps/plans/cids.py` — URI helpers and default signals
- `apps/admin_settings/management/commands/validate_cids_jsonld.py` — SHACL validation
- `apps/admin_settings/management/commands/export_cids_jsonld.py` — export command
- `apps/admin_settings/taxonomy_review.py` — taxonomy suggestion pipeline
- `apps/admin_settings/classification_forms.py` / `classification_views.py`
- 3 uncommitted migrations (0008-0010) adding `mapping_status`, `mapping_source`, `confidence_score`, `taxonomy_list_name`, `rationale`, `reviewed_by`, `reviewed_at` to TaxonomyMapping
- Classification templates, test files
- Changes to models.py, urls.py, signals.py, forms.py, views.py, templates, etc.

**Critical:** `cids_jsonld.py` queries `mapping_status="approved"` on TaxonomyMapping — crashes until migrations 0008-0010 are applied.

## CIDS class coverage roadmap

| After phase | Classes | Coverage |
|-------------|---------|----------|
| Phase 0 (commit existing) | Organization, Outcome, Indicator, IndicatorReport, Theme, Code, Address | 7/14 (50%) |
| Phase 0.5 (quick stubs) | + ImpactModel, Stakeholder, StakeholderOutcome, Output | 11/14 (79%) |
| Phase 1 (evaluation planning) | + Service, Activity, ImpactRisk, Counterfactual | 14/14 (100%) |
| Phase 4 (Full Tier assembly) | All 14 classes in a single Full Tier document | Full Tier |

## Build phases (6 phases, execute in order)

Each phase has a self-contained agent prompt in `tasks/agent-prompts/`.

| Phase | Prompt file | What it does | Dependencies |
|-------|------------|--------------|-------------|
| **0** | `phase-0-commit-cids-foundation.md` | Commit all existing CIDS code, apply migrations, deploy | None |
| **0.5** | `phase-0.5-quick-full-tier-nodes.md` | Add ImpactModel, Stakeholder, StakeholderOutcome, Output from existing data | Phase 0 |
| **1** | `phase-1-evaluation-planning.md` | EvaluationFramework, EvaluationComponent, EvaluationEvidenceLink models + CRUD | Phase 0.5 |
| **4** | `phase-4-full-tier-export.md` | Full Tier JSON-LD serialiser with 3-layer architecture | Phase 1 |
| 2 | `phase-2-report-artifact-validation.md` | ReportValidationProfile, CanonicalReportArtifact, EnrichmentRun | Phase 1 (deferred — not a compliance blocker) |
| 3 | `phase-3-ai-enrichment-review.md` | EnrichedMetadataItem, ExportMetadataSnapshot, AI enrichment | Phase 2 (deferred — not a compliance blocker) |

**Key insight:** Phases 2 and 3 improve metadata quality but don't add any CIDS class coverage. They can be deferred without affecting Full Tier compliance.

## KoNote model quirks (must-know for agents)

- **User model**: `display_name` field, `get_display_name()` method — NO `first_name`/`last_name`/`get_full_name()`
- **TaxonomyMapping** (after Phase 0): `taxonomy_system`, `taxonomy_code`, `taxonomy_label`, `funder_context`, `mapping_status`, `mapping_source`, `confidence_score`, `taxonomy_list_name`, `rationale`, `reviewed_by`, `reviewed_at`
- **PlanTarget** achievement_status: `in_progress`, `improving`, `worsening`, `no_change`, `achieved`, `sustaining`, `not_achieved`, `not_attainable`
- **PlanSection**: required `client_file` FK, nullable `program` FK. NO `Plan` model.
- **ProgressNote**: `interaction_type` (session/group/phone/etc.), `note_type` (quick/full/assessment). NO `service_type`.
- **ClientProgramEnrolment**: in `apps.clients.models` — not `Enrolment`
- **No local dev environment**: all Django commands run on VPS via SSH into Docker containers

## How to execute

1. Open a fresh Claude Code session
2. Paste the contents of the phase prompt file
3. Let it run to completion (creates branch, builds, tests, PRs to develop)
4. Merge the PR
5. Repeat with next phase

Execute Phases 0 → 0.5 → 1 → 4 in order. Phases 2-3 can be done later.
