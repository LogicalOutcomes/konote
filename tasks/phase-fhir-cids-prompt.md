# Implementation Prompts: FHIR-Informed Data Foundations + CIDS Compliance

Five sessions implementing the interleaved FHIR + CIDS sequence from `tasks/fhir-informed-data-modelling.md`. Each session is a self-contained prompt — paste one into a new Claude Code session.

**Important:** These sessions must be done in order. Each builds on the previous.

---

## Session 1: CIDS Phase 1 — Metadata Fields + OrganizationProfile

### Prompt

We're implementing CIDS Phase 1 metadata fields. This is step 1 of the interleaved sequence described in `tasks/fhir-informed-data-modelling.md`.

#### Before you start

0. **Pull main first.** Run `git pull origin main` before anything else. Your worktree may be missing recently merged files.

1. Read these files in order — **all five are required before writing any code**:
   - `tasks/fhir-informed-data-modelling.md` — the full implementation plan (focus on the REMOVED Phase F0 section — understand WHY outcome_domain was dropped)
   - `tasks/design-rationale/fhir-informed-modelling.md` — anti-patterns and trade-offs (DO NOT violate these). Pay special attention to the Taxonomy Panel addendum.
   - `tasks/cids-json-ld-export.md` — Phase 1 fields (sections 1a through 1d)
   - `tasks/cids-plan-validation.md` — corrections to the CIDS plan
   - `CLAUDE.md` — project conventions and development rules

2. Read the current models:
   - `apps/plans/models.py` — MetricDefinition (has `category` field — DO NOT change it) and PlanTarget
   - `apps/clients/models.py` — ClientProgramEnrolment (for context, not changed in this step)
   - `apps/programs/models.py` — Program model
   - `apps/admin_settings/models.py` — where OrganizationProfile will live

#### What to build

**On MetricDefinition** — add CIDS metadata fields (DO NOT touch `category`):

| Field | Type | Notes |
|---|---|---|
| `cids_indicator_uri` | CharField(max_length=500, blank=True) | CIDS `@id` — use CharField not URLField (URIs may use `urn:` schemes) |
| `iris_metric_code` | CharField(max_length=100, blank=True) | From IrisMetric53 code list |
| `sdg_goals` | JSONField(default=list, blank=True) | List of SDG numbers (1–17) |
| `cids_unit_description` | CharField(max_length=255, blank=True) | Human-readable unit label |
| `cids_defined_by` | CharField(max_length=500, blank=True) | URI of defining organisation |
| `cids_has_baseline` | CharField(max_length=255, blank=True) | Baseline description — CharField, NOT BooleanField (e.g., "Average score 3.2 at intake") |
| `cids_theme_override` | CharField(max_length=50, blank=True) | Admin escape hatch for CIDS theme derivation |

**On Program** — add CIDS metadata fields:

| Field | Type | Notes |
|---|---|---|
| `cids_sector_code` | CharField(max_length=100, blank=True) | From ICNPOsector or ESDCSector |
| `population_served_codes` | JSONField(default=list, blank=True) | From PopulationServed code list |
| `description_fr` | TextField(blank=True) | French description for bilingual CIDS exports |
| `funder_program_code` | CharField(max_length=100, blank=True) | Funder-assigned ID |

**On PlanTarget** — add CIDS metadata field:

| Field | Type | Notes |
|---|---|---|
| `cids_outcome_uri` | CharField(max_length=500, blank=True) | CIDS outcome `@id` |

Do NOT add `cids_impact_theme` — it was removed in favour of export-time derivation.

**New model: OrganizationProfile** (in `apps/admin_settings/models.py`):

Singleton pattern (only one row per instance). Place alongside existing TerminologyOverride / FeatureToggle / InstanceSetting.

| Field | Type | Notes |
|---|---|---|
| `legal_name` | CharField(max_length=255, blank=True) | Required for CIDS BasicTier |
| `operating_name` | CharField(max_length=255, blank=True) | Display name |
| `description` | TextField(blank=True) | Mission statement |
| `description_fr` | TextField(blank=True) | French mission statement |
| `legal_status` | CharField(max_length=100, blank=True) | Charity, nonprofit, etc. |
| `sector_codes` | JSONField(default=list, blank=True) | From ICNPOsector code list — JSONField not CharField |
| `street_address` | CharField(max_length=255, blank=True) | |
| `city` | CharField(max_length=100, blank=True) | |
| `province` | CharField(max_length=2, blank=True) | Two-letter province code |
| `postal_code` | CharField(max_length=10, blank=True) | |
| `country` | CharField(max_length=2, default="CA") | ISO 3166-1 alpha-2 |
| `website` | URLField(blank=True) | |

Implement singleton with a `get_solo()` class method or similar pattern. Check how the project handles singletons (InstanceSetting may already have a pattern).

#### What NOT to touch

- `MetricDefinition.category` — leave this field completely unchanged. It is for internal UI grouping only. Do NOT rename it, expand its choices, or add `outcome_domain`.
- Do NOT add `outcome_domain` to MetricDefinition, Program, or PlanTarget — this was explicitly removed by the taxonomy panel (see DRR).
- ServiceEpisode (Phase F1) — that's Session 3
- Achievement status (Phase F2) — that's Session 4
- Author role (Phase F3) — that's Session 4
- CidsCodeList import (CIDS Phase 2) — that's Session 2
- Admin UI dropdowns (CIDS Phase 2) — that's Session 2

#### Rules

- Create `forms.py` for any admin-facing forms (Django ModelForm, never raw POST)
- Write tests for the new fields and OrganizationProfile singleton
- Run `makemigrations` and `migrate`, commit migration files
- Run `python manage.py translate_strings` after any template changes
- All new fields must be `blank=True` or have defaults — no data loss on migration
- Follow the project's existing patterns for CharFields with choices

#### When done

- Mark these TODO.md tasks as done: CIDS-META1 + CIDS-ORG1
- Run relevant tests: `pytest tests/test_plans.py tests/test_clients.py`
- **GK reviews:** Flag for GK review — this adds fields to outcome models (MetricDefinition, PlanTarget). Note in the PR description: "GK reviews: CIDS metadata field selection."
- Create a PR to merge into main

---

## Session 2: CIDS Phase 2 + 2.5 — Code Lists, Taxonomy Mapping, Enriched Reports

### Prompt

We're implementing CIDS Phase 2 (code list import + taxonomy mapping) and Phase 2.5 (enriched reports). This is step 2 of the interleaved sequence.

#### Before you start

0. **Pull main first.** Run `git pull origin main` — Session 1 must be merged before starting.

1. Read these files:
   - `tasks/fhir-informed-data-modelling.md` — sequencing table and "What changes in the CIDS plan" section
   - `tasks/design-rationale/fhir-informed-modelling.md` — Taxonomy Panel addendum (explains why the taxonomy mapping layer exists)
   - `tasks/cids-json-ld-export.md` — Phase 2 (CidsCodeList model, management command) and Phase 2.5 (enriched reports)
   - `tasks/cids-plan-validation.md` — Code object SHACL requirements (6 required fields)

2. Read the current models (after Session 1 merge):
   - `apps/plans/models.py` — MetricDefinition with new CIDS fields
   - `apps/programs/models.py` — Program with new CIDS fields
   - `apps/admin_settings/models.py` — OrganizationProfile

#### What to build

**New model: `CidsCodeList`** (in `apps/admin_settings/models.py` or a new `apps/cids/` app — follow project conventions):

| Field | Type | Notes |
|---|---|---|
| `list_name` | CharField(max_length=100) | e.g., "ICNPOsector", "SDGImpacts", "PopulationServed", "IrisMetric53" |
| `code` | CharField(max_length=100) | The code value |
| `label` | CharField(max_length=255) | Display label (English) |
| `label_fr` | CharField(max_length=255, blank=True) | French label |
| `description` | TextField(blank=True) | Longer description |
| `specification_uri` | CharField(max_length=500, blank=True) | URI of code list spec |
| `defined_by_name` | CharField(max_length=255, blank=True) | Organisation name |
| `defined_by_uri` | CharField(max_length=500, blank=True) | URI of defining org |
| `source_url` | URLField(blank=True) | Common Approach code list page |
| `version_date` | DateField(blank=True, null=True) | For staleness warnings |

`unique_together = [("list_name", "code")]`

**New model: `TaxonomyMapping`** — supports multiple external taxonomies per metric:

| Field | Type | Notes |
|---|---|---|
| `content_type` | FK to ContentType | Generic FK — allows mapping metrics, programs, or targets |
| `object_id` | PositiveIntegerField | |
| `taxonomy` | CharField(max_length=100) | Which external system: "cids_iris", "united_way", "phac", etc. |
| `code` | CharField(max_length=100) | The code within that taxonomy |
| `label` | CharField(max_length=255, blank=True) | Display label (cached from code list or manually entered) |
| `context` | CharField(max_length=100, blank=True) | Optional: which funder/partner relationship (blank = universal) |

`unique_together = [("content_type", "object_id", "taxonomy", "code", "context")]`

This model enables: one metric → multiple taxonomy codes across multiple external systems. Config templates can pre-populate these mappings during agency onboarding.

**Management command: `import_cids_codelists`**
- Fetches 17 code lists from `codelist.commonapproach.org`
- Populates CidsCodeList table
- Supports `--dry-run` and `--force` flags
- Warns if local copy is stale (compare version_date)
- See `tasks/cids-json-ld-export.md` Phase 2a for details

**Admin UI: CIDS tagging dropdowns**
- On MetricDefinition admin form: dropdown for `iris_metric_code` populated from CidsCodeList (list_name="IrisMetric53")
- On Program admin form: dropdown for `cids_sector_code` from CidsCodeList
- On MetricDefinition admin form: multi-select for `sdg_goals` from CidsCodeList (list_name="SDGImpacts")
- Pre-mapped via config templates — admin UI is for overrides only

**CIDS-enriched reports (Phase 2.5):**
- Add CIDS codes to existing CSV/PDF partner reports
- "Standards Alignment" appendix page showing: IRIS+ codes, SDG alignment, CIDS theme derivation
- CIDS theme derivation: `iris_metric_code` → CidsCodeList parent theme lookup (primary), `cids_theme_override` (admin override)
- This is the **quick win for funders** — no ServiceEpisode needed

#### What NOT to build yet

- ServiceEpisode (Session 3)
- JSON-LD export (Session 5)
- Full SHACL validation (Session 5)

#### When done

- Mark TODO.md tasks: CIDS-CODES1 + CIDS-ADMIN1 + CIDS-ENRICH1
- Run relevant tests
- Create a PR

---

## Session 3: Phase F1 — ServiceEpisode

### Prompt

We're implementing Phase F1: extending ClientProgramEnrolment into ServiceEpisode. This is step 3 of the interleaved sequence — the biggest model change in the plan.

#### Before you start

0. **Pull main first.** Run `git pull origin main` — Sessions 1–2 must be merged before starting.

1. Read these files:
   - `tasks/fhir-informed-data-modelling.md` — Phase F1 section (ServiceEpisode, StatusChange, migration strategy, UI changes)
   - `tasks/design-rationale/fhir-informed-modelling.md` — anti-patterns: DO NOT let workers select episode type, DO NOT ask workers to select role
   - `CLAUDE.md` — development rules (forms.py, tests, migrations)

2. Read the current models:
   - `apps/clients/models.py` — ClientProgramEnrolment (the model being extended)
   - Check all views/templates that reference ClientProgramEnrolment to understand the blast radius

#### What to build

**Extend ClientProgramEnrolment into ServiceEpisode** (in place — no table rename):

The existing `status` field gets new choices (was: enrolled/unenrolled → becomes: planned/waitlist/active/on_hold/finished/cancelled). This is an EXISTING field getting expanded choices, not a new field.

New fields to add (all nullable/optional — see Phase F1 field table in the plan):
- `status_reason` (TextField, blank=True)
- `episode_type` (CharField, max_length=20, blank=True) — **auto-derived, never worker-entered**
- `primary_worker` (FK to User, null=True, blank=True)
- `referral_source` (CharField, max_length=30, blank=True)
- `started_at` (DateTimeField, null=True) — populated from enrolled_at during migration
- `ended_at` (DateTimeField, null=True, blank=True)
- `end_reason` (CharField, max_length=30, blank=True)

**New model: `ServiceEpisodeStatusChange`** — append-only status history.

**Data migration:**
1. `RenameModel`: ClientProgramEnrolment → ServiceEpisode
2. Add new fields (all nullable)
3. Populate: `started_at = enrolled_at`, status "enrolled" → "active", status "unenrolled" → "finished"
4. Create initial StatusChange rows
5. Add `ClientProgramEnrolment = ServiceEpisode` alias for backwards compatibility

**UI changes:**
- Discharge modal: "Why is this person leaving?" — radio buttons for end_reason + optional text
- On hold / resume actions on client profile
- Episode type shown as informational on client profile

See the full field tables, choice lists, and migration script in the implementation plan.

#### What NOT to build

- Achievement status (Session 4)
- Author role (Session 4)
- JSON-LD export (Session 5)
- DO NOT add `outcome_domain` to anything — it was removed from the plan

#### When done

- Mark TODO.md tasks: FHIR-EPISODE1 + FHIR-MIGRATE1
- Run full client tests: `pytest tests/test_clients.py`
- **GK reviews:** Flag for GK review — this changes the data model for service tracking. Note in PR: "GK reviews: ServiceEpisode data model, status choices, end_reason choices."
- Create a PR

---

## Session 4: Phase F2 + F3 — Achievement Status + Encounter Role

### Prompt

We're implementing Phase F2 (Goal Achievement Status on PlanTarget) and Phase F3 (Encounter Participant Role on ProgressNote). These are steps 5–6 of the interleaved sequence.

#### Before you start

0. **Pull main first.** Run `git pull origin main` — Sessions 1–3 must be merged before starting.

1. Read these files:
   - `tasks/fhir-informed-data-modelling.md` — Phase F2 (achievement_status, derivation logic, sparse data rules, edge cases) and Phase F3 (author_role)
   - `tasks/design-rationale/fhir-informed-modelling.md` — trade-offs: auto-compute with worker override, `not_attainable` never auto-computed

2. Read the current models:
   - `apps/plans/models.py` — PlanTarget, ProgressNoteTarget (has progress_descriptor)
   - `apps/programs/models.py` — ProgressNote, UserProgramRole

#### What to build

**Phase F2 — new fields on PlanTarget:**

| Field | Type | Notes |
|---|---|---|
| `achievement_status` | CharField(max_length=20, blank=True) | Values: in_progress, improving, worsening, no_change, achieved, sustaining, not_achieved, not_attainable |
| `achievement_status_source` | CharField(max_length=20, blank=True) | `auto_computed` or `worker_assessed` |
| `achievement_status_updated_at` | DateTimeField(null=True) | When last computed/assessed |
| `first_achieved_at` | DateTimeField(null=True, blank=True) | Never cleared once set |

**Derivation logic** (see implementation plan for full details):
- Quantitative (MetricValues exist): 3-point trend analysis
- Qualitative (progress_descriptor only): map from harder/holding/shifting/good_place
- Sparse data rules: 0 points → in_progress, 1 point → in_progress (unless meets target → achieved), 2 points → simple comparison, 3+ → full trend
- `not_attainable` — **NEVER auto-computed**, always deliberate worker/PM decision
- Worker override: "(auto)" badge on plan view, click to override
- Trigger: recalculate when ProgressNote saved with ProgressNoteTarget

**Phase F3 — new field on ProgressNote:**

| Field | Type | Notes |
|---|---|---|
| `author_role` | CharField(max_length=30, blank=True) | Auto-filled from UserProgramRole at note creation |

**No UI change for F3.** The worker never sees or selects this field.

#### What NOT to build

- Presenting Issues (Phase F4) — deferred until triggered by need
- Service Referrals (Phase F5) — deferred
- Care Team (Phase F6) — deferred
- DO NOT add `outcome_domain` to anything

#### When done

- Mark TODO.md tasks: FHIR-ACHIEVE1 + FHIR-ROLE1
- Run relevant tests: `pytest tests/test_plans.py`
- **GK reviews:** Flag for GK review — achievement status methodology. Note in PR: "GK reviews: achievement_status derivation logic, progress_descriptor mapping, sparse data rules."
- Create a PR

---

## Session 5: CIDS Phase 3 + 4 + 5 — JSON-LD Export, Impact Dimensions, Conformance

### Prompt

We're implementing the final CIDS phases: JSON-LD export with SHACL validation (Phase 3), computed impact dimensions (Phase 4), and conformance badge (Phase 5). This is the culmination of all prior work.

**Note:** Phase 3 alone is substantial. If time is limited, complete Phase 3 and stop — Phases 4 and 5 can be a separate session.

#### Before you start

0. **Pull main first.** Run `git pull origin main` — Sessions 1–4 must be merged before starting.

1. Read these files:
   - `tasks/cids-json-ld-export.md` — Phases 3, 4, 5 (JSON-LD examples, impact dimensions, conformance)
   - `tasks/cids-plan-validation.md` — Phase 3 implementation notes (Code SHACL fields, StakeholderOutcome construction, BeneficialStakeholder = group not individual, i72:Measure wrapping)
   - `tasks/fhir-informed-data-modelling.md` — "What changes in the CIDS plan" section (how ServiceEpisode and achievement_status enrich the export)

2. Read the current models (after all sessions merged):
   - All models with CIDS fields
   - CidsCodeList (from Session 2)
   - TaxonomyMapping (from Session 2)
   - ServiceEpisode (from Session 3)
   - PlanTarget with achievement_status (from Session 4)

#### What to build

**Phase 3: JSON-LD export**
- Management command or admin action: "Export CIDS JSON-LD"
- Build JSON-LD document following the examples in cids-json-ld-export.md
- Target FullTier compliance
- CIDS theme derivation: iris_metric_code → CidsCodeList lookup (primary), taxonomy mappings (middle), cids_theme_override (admin override)
- Construct StakeholderOutcome at export time from Program cohort + PlanTarget
- BeneficialStakeholder = aggregate group/cohort, NOT individual clients
- `i72:value` wraps in `i72:Measure` objects
- All entities get `@id` fields
- Basic SHACL validation (pass/fail check before export)

**Phase 4: Impact dimensions** (can be deferred to a follow-up session)
- Compute ImpactScale, ImpactDepth, ImpactDuration from existing data
- ImpactDepth enriched by achievement_status
- ImpactScale from ServiceEpisode counts
- ImpactDuration from episode start/end dates and first_achieved_at

**Phase 5: Conformance badge** (can be deferred to a follow-up session)
- Detailed SHACL validation reporting (not just pass/fail)
- Conformance badge for admin dashboard
- Tier-by-tier validation results

#### When done

- Mark TODO.md tasks: CIDS-EXPORT1, CIDS-IMPACT1, CIDS-VALIDATE1 (whichever were completed)
- Run full test suite: `pytest -m "not browser and not scenario_eval"`
- Create a PR

---

## Quick Reference: What Was Removed and Why

The original plan included a 14-value `outcome_domain` taxonomy that would replace `MetricDefinition.category` and be added to Program and PlanTarget. **This was removed** after a taxonomy panel (4 experts, 3 rounds) concluded:

1. Every funder, partner, and collaboration uses a different outcome taxonomy
2. The nonprofit sector has tried for years to standardise a taxonomy and failed
3. A hardcoded internal taxonomy becomes useless when `custom` is the default
4. One metric maps to multiple indicators across different external taxonomies

**Instead:** `MetricDefinition.category` (7 values) stays unchanged for UI grouping. External taxonomy mappings are handled by the `TaxonomyMapping` model (Session 2), which supports multiple taxonomies per metric with optional funder/partner context.

See `tasks/design-rationale/fhir-informed-modelling.md` — Taxonomy Panel addendum for the full discussion.
