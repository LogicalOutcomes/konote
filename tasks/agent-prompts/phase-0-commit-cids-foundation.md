# Phase 0: Commit & Deploy CIDS Foundation — Agent Prompt

**This must be done FIRST.** There is a large body of uncommitted CIDS code in the working tree. None of it has ever been deployed or tested against a live database. This phase commits it all, runs tests, and deploys.

## Problem

The following files exist locally but have never been committed or deployed:

### New files (untracked)
- `apps/reports/cids_jsonld.py` — Basic Tier JSON-LD export builder
- `apps/plans/cids.py` — CIDS URI helpers and default signals
- `apps/admin_settings/management/commands/validate_cids_jsonld.py` — SHACL validation
- `apps/admin_settings/taxonomy_review.py` — taxonomy suggestion pipeline
- `apps/admin_settings/classification_forms.py` — taxonomy classification forms
- `apps/admin_settings/classification_views.py` — taxonomy classification views
- `apps/admin_settings/migrations/0008_taxonomymapping_review_fields.py`
- `apps/admin_settings/migrations/0009_taxonomymapping_list_name.py`
- `apps/admin_settings/migrations/0010_taxonomymapping_taxonomy_system_labels.py`
- `templates/admin_settings/classification/` — taxonomy review templates
- `tests/test_taxonomy_review.py`

### Modified files (uncommitted changes)
- `apps/admin_settings/models.py` — TaxonomyMapping gains `mapping_status`, `mapping_source`, `confidence_score`, `taxonomy_list_name`, `rationale`, `reviewed_by`, `reviewed_at` fields
- `apps/admin_settings/management/commands/export_cids_jsonld.py` — export command
- `apps/admin_settings/urls.py` — classification routes
- `apps/plans/signals.py` — CIDS default signals
- `apps/plans/forms.py` — CIDS fields on metric/target forms
- `apps/reports/cids_enrichment.py` — theme derivation, standards alignment
- `apps/reports/export_engine.py` — `cids_json` export format support
- `apps/reports/views.py` — CIDS export in report views
- `apps/reports/forms.py` — taxonomy lens field
- `apps/reports/funder_report.py` — standards alignment in reports
- `apps/reports/preview_views.py` — CIDS preview
- `konote/ai.py` — AI module updates
- `templates/admin_settings/dashboard.html` — CIDS section on admin dashboard
- `templates/reports/export_template_driven.html` — CIDS export format option
- `templates/reports/funder_report_form.html` — taxonomy lens selector
- `templates/reports/funder_report_preview.html` — standards alignment display
- `templates/reports/html_report.html` — CIDS metadata in HTML reports
- `templates/reports/pdf_funder_outcome_report.html` — CIDS data in PDF reports
- `templates/reports/report_preview.html` — CIDS preview additions
- `tests/ux_walkthrough/browser_base.py` — browser test base updates
- `tests/test_cids.py` — CIDS test suite
- `tests/test_reports.py` — report tests with CIDS
- `requirements-test.txt` — adds `pyshacl` dependency for SHACL validation

## Branch

Create branch `feat/cids-foundation` off `develop`.

## Steps

### 1. Stage and review all CIDS-related changes

```bash
git add \
  apps/reports/cids_jsonld.py \
  apps/reports/cids_enrichment.py \
  apps/plans/cids.py \
  apps/admin_settings/taxonomy_review.py \
  apps/admin_settings/classification_forms.py \
  apps/admin_settings/classification_views.py \
  apps/admin_settings/management/commands/validate_cids_jsonld.py \
  apps/admin_settings/management/commands/export_cids_jsonld.py \
  apps/admin_settings/models.py \
  apps/admin_settings/urls.py \
  apps/admin_settings/migrations/0008_taxonomymapping_review_fields.py \
  apps/admin_settings/migrations/0009_taxonomymapping_list_name.py \
  apps/admin_settings/migrations/0010_taxonomymapping_taxonomy_system_labels.py \
  apps/plans/signals.py \
  apps/plans/forms.py \
  apps/reports/export_engine.py \
  apps/reports/views.py \
  apps/reports/forms.py \
  apps/reports/funder_report.py \
  apps/reports/preview_views.py \
  konote/ai.py \
  templates/admin_settings/ \
  templates/reports/export_template_driven.html \
  templates/reports/funder_report_form.html \
  templates/reports/funder_report_preview.html \
  templates/reports/html_report.html \
  templates/reports/pdf_funder_outcome_report.html \
  templates/reports/report_preview.html \
  tests/test_cids.py \
  tests/test_reports.py \
  tests/test_taxonomy_review.py \
  tests/ux_walkthrough/browser_base.py \
  requirements-test.txt
```

### 2. Review the diff carefully

Before committing, read through every staged change. Check for:
- Hardcoded paths or credentials
- References to models/fields that don't exist yet (the EvaluationFramework models from Phase 1 do NOT exist — make sure nothing imports them)
- PII in test fixtures
- Broken imports

### 3. Verify TaxonomyMapping migration chain

Read the three migration files. Verify they:
- Add fields to the existing `taxonomy_mappings` table (not recreating it)
- Have correct dependencies (each depends on the previous)
- Don't drop any existing data

### 4. Run existing tests

```bash
pytest tests/test_cids.py tests/test_reports.py tests/test_taxonomy_review.py -v --tb=short
```

Fix any failures before proceeding.

### 5. Run the Basic Tier export against live data

After deploying to the dev VPS, test the export:

```bash
ssh konote-vps "sudo docker compose -f /opt/konote-dev/docker-compose.yml exec web python manage.py export_cids_jsonld --indent 2"
```

This should produce a valid JSON-LD document. If it crashes, diagnose and fix.

### 6. Run SHACL validation

```bash
ssh konote-vps "sudo docker compose -f /opt/konote-dev/docker-compose.yml exec web python manage.py validate_cids_jsonld"
```

This validates the export against the official Common Approach Basic Tier SHACL shapes. Fix any validation failures.

### 7. Commit, push, PR, deploy

Commit with a clear message about what's being committed and why it's all going in together (accumulated CIDS work).

Deploy to dev VPS and verify the migration applies cleanly.

## Acceptance criteria

- [ ] All CIDS-related files committed in a single branch
- [ ] TaxonomyMapping migration applies cleanly on dev VPS
- [ ] `export_cids_jsonld` command runs and produces valid JSON-LD
- [ ] `validate_cids_jsonld` command passes SHACL validation
- [ ] `pytest tests/test_cids.py` passes
- [ ] `pytest tests/test_taxonomy_review.py` passes
- [ ] No references to EvaluationFramework (doesn't exist yet)
- [ ] French translations compiled

## Critical notes

- **Do NOT stage `TODO.md` or `.Jules/`** — those have unrelated changes that shouldn't be in this commit.
- **Do NOT modify the uncommitted files beyond fixing bugs.** This phase is about committing existing work, not adding new features.
- **The TaxonomyMapping model gains 7 new fields.** The migration must handle existing rows (all new fields have defaults or are nullable).
- **`cids_jsonld.py` references `mapping_status="approved"` on TaxonomyMapping.** This will crash until the migration is applied. That's why deployment order matters: migration first, then the code that uses the new fields.
- **`pyshacl` and `rdflib` are test dependencies.** They're in `requirements-test.txt`, not `requirements.txt`. The validate command will raise `CommandError` if they're not installed. This is fine — validation is a dev/test operation.
