# Implementation Prompt: FHIR-Informed Data Foundations + CIDS Phase 1

Paste this into a new Claude Code session to begin implementation.

---

## Prompt

We're implementing the first step of the FHIR-informed data modelling plan combined with CIDS Phase 1 metadata. This is step 1 of the interleaved sequence described in `tasks/fhir-informed-data-modelling.md`.

### Before you start

1. Read these files in order:
   - `tasks/fhir-informed-data-modelling.md` — the full implementation plan (focus on Phase F0)
   - `tasks/design-rationale/fhir-informed-modelling.md` — anti-patterns and trade-offs (DO NOT violate these)
   - `tasks/cids-json-ld-export.md` — Phase 1 fields (sections 1a through 1d)
   - `tasks/cids-plan-validation.md` — corrections to the CIDS plan

2. Read the current models:
   - `apps/plans/models.py` — MetricDefinition (has `category` field to replace) and PlanTarget
   - `apps/clients/models.py` — ClientProgramEnrolment (for context, not changed in this step)
   - `apps/programs/models.py` — Program model

### What to build (F0 + CIDS Phase 1 combined)

**On MetricDefinition:**
- Replace `category` CharField (7 values) with `outcome_domain` CharField (14 values). Data migration maps old values — see the mapping table in the plan. The value `general` needs manual review during migration; map to `custom` for now.
- Add CIDS fields from Phase 1b: `cids_indicator_uri`, `iris_metric_code`, `sdg_goals` (JSONField), `cids_unit_description`, `cids_defined_by`, `cids_has_baseline` (BooleanField)
- Add `cids_theme_override` (CharField, max_length=50, blank=True) — admin escape hatch for three-tier theme derivation

**On Program:**
- Add `outcome_domain` (CharField, blank=True)
- Add CIDS fields from Phase 1c: `cids_sector_code`, `population_served_codes` (JSONField), `description_fr`, `funder_program_code`

**On PlanTarget:**
- Add `outcome_domain` (CharField, blank=True) — inherited from program or metrics
- Add CIDS field from Phase 1d: `cids_outcome_uri`
- Do NOT add `cids_impact_theme` — it was removed in favour of three-tier derivation

**New model: OrganizationProfile** (from CIDS Phase 1a)
- `legal_name`, `operating_name`, `sector` (CharField), `address_street`, `address_city`, `address_province`, `address_postal_code`, `country` (default "CA"), `description`, `description_fr`
- Singleton pattern (only one row). Use `get_solo()` or similar.
- See `tasks/cids-json-ld-export.md` Phase 1a for the full field list.

### Rules

- Create forms.py for any admin-facing forms (Django ModelForm, never raw POST)
- Write tests for the migration logic and new fields
- Run makemigrations and migrate, commit migration files
- Run translations: `python manage.py translate_strings` after any template changes
- All new fields must be blank=True or have defaults — no data loss on migration
- Follow the project's existing patterns — check how other CharFields with choices are done

### What NOT to build yet

- ServiceEpisode (Phase F1) — that's a later session
- Achievement status (Phase F2) — that's a later session
- Author role (Phase F3) — that's a later session
- CidsCodeList import (CIDS Phase 2) — that's the next step after this one
- Admin UI dropdowns (CIDS Phase 2) — that's the next step after this one

### When done

- Mark these TODO.md tasks as done: FHIR-DOMAIN1 + CIDS-META1 + CIDS-ORG1
- Run relevant tests: `pytest tests/test_plans.py tests/test_clients.py`
- Create a PR to merge into main
