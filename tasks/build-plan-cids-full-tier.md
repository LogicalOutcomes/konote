# CIDS Full Tier — Build Plan

Date: 2026-03-07
Status: Ready to execute

## What exists today (built and working)

- Basic Tier JSON-LD export (`apps/reports/cids_jsonld.py` — `build_cids_jsonld_document()`)
- SHACL validation command (`apps/admin_settings/management/commands/validate_cids_jsonld.py`)
- CidsCodeList model with ICNPOsector, PopulationServed, SDG, IRIS+ code lists imported
- TaxonomyMapping model with AI suggestion pipeline (`apps/admin_settings/taxonomy_review.py`)
- Program model with CIDS fields (cids_sector_code, population_served_codes)
- MetricDefinition/PlanTarget with CIDS fields (`apps/plans/cids.py`)
- SecureExportLink with approval flow, PII tracking, elevated export delays
- AI module (`konote/ai.py`) with OpenRouter integration, PII safety controls
- PII scrubbing (`apps/reports/pii_scrub.py`)
- k-anonymity suppression in reports (k>=5)
- OrganizationProfile for agency-level CIDS metadata

## What needs building (4 phases, sequential)

Each phase has a self-contained agent prompt in `tasks/agent-prompts/`.

| Phase | Prompt file | Models | Dependencies |
|-------|------------|--------|-------------|
| 1 | `phase-1-evaluation-planning.md` | EvaluationFramework, EvaluationComponent, EvaluationEvidenceLink | None (builds on existing Program model) |
| 2 | `phase-2-report-artifact-validation.md` | ReportValidationProfile, CanonicalReportArtifact, EnrichmentRun | Phase 1 (uses EvaluationFramework in artifact) |
| 3 | `phase-3-ai-enrichment-review.md` | EnrichedMetadataItem, ExportMetadataSnapshot | Phase 2 (enriches CanonicalReportArtifact) |
| 4 | `phase-4-full-tier-export.md` | No new models — assembles Full Tier JSON-LD | Phase 1 + 2 + 3 |

## Phase 1 can be split into parallel sub-agents

Phase 1 has three independent tasks that can run in parallel:

| Sub-agent | Task | Files |
|-----------|------|-------|
| 1A | Models + migrations | `apps/programs/models.py`, migration files |
| 1B | Forms + views + URLs | `apps/programs/forms.py`, `apps/programs/views.py`, `apps/programs/urls.py` |
| 1C | Templates | `templates/programs/evaluation_framework_*.html` |

However, 1B and 1C depend on 1A (need model definitions). Safest approach: run Phase 1 as a single agent.

## How to execute

1. Open a fresh Claude Code session
2. Paste the contents of `tasks/agent-prompts/phase-1-evaluation-planning.md`
3. Let it run to completion (creates branch, builds, tests, PRs to develop)
4. Merge the PR
5. Repeat with Phase 2, 3, 4 in order

Each prompt is self-contained with:
- Exact file paths to create/modify
- Model field definitions
- View signatures and URL patterns
- Template structure
- Test requirements
- Acceptance criteria
