# Session 4: Parallel Documentation, Features & Code Cleanup

## Pre-flight (do first, sequentially)

Merge the 3 open PRs, then pull develop:

```
gh pr merge 222 --merge --repo LogicalOutcomes/konote
gh pr merge 224 --merge --repo LogicalOutcomes/konote
gh pr merge 225 --merge --repo LogicalOutcomes/konote
git pull origin develop
```

Then create a feature branch: `git checkout -b chore/session-4-parallel-work`

## Parallel agents (launch all at once — no file conflicts between them)

### Agent A: DEPLOY-TOOLKIT1 — Admin toolkit decision documents

**Files:** `docs/agency-setup-guide/01-*.md` through `docs/agency-setup-guide/09-*.md`

Create 9 decision documents for AI-assisted agency setup. The spec is in `tasks/ai-assisted-admin-toolkit.md` — read it first, especially the document format template and the table at "Decision Document Set."

Source material to reformat:
- `tasks/deployment-protocol.md` — Phases 1-4, sections 3.1-3.5
- `tasks/agency-permissions-interview.md` — full interview script
- `docs/admin/` — existing feature docs for reference
- `config_templates/` — example configurations for financial coaching

Each document follows this structure: What This Configures, Decisions Needed (with options and consequences), Common Configurations (financial coaching example using config_templates/), Output Format, Dependencies.

Documents 00 and 10 already exist — do not overwrite them.

### Agent B: DOC-DEPLOY1 + DOC-TECH1 — Deployment and technical docs

**Files:** `docs/deploying-konote.md` and `docs/technical-documentation.md`

**DOC-DEPLOY1:** Add sections to `docs/deploying-konote.md` covering deployment of surveys and portal features. Read `apps/surveys/` and `apps/portal/` to understand what they do. Document: environment variables needed, database tables created by migrations, feature toggles that enable/disable them, any additional setup steps.

**DOC-TECH1:** Add sections to `docs/technical-documentation.md` covering the technical architecture of surveys and portal. Document: models, views, URL patterns, template structure, encryption of PII fields, permission checks, HTMX patterns used.

Read the existing docs first to match tone and format. Canadian spelling.

### Agent C: WEBSITE-UPDATE1 — Update konote-website

**Repo:** `C:\Users\gilli\GitHub\konote-website` (separate repo, create a branch there)

Read the KoNote `CHANGELOG.md`, `TODO.md` Recently Done section, and `docs/` to understand recent features. Then update the marketing website:

1. **features.html** — add entries for: surveys & assessments, participant portal, multi-tenancy/server sharing, CIDS data standards compliance, demo/training mode, data export & offboarding, accessibility (WCAG 2.2 AA with axe-core CI)
2. **security.html** — add: Fernet encryption for PII, per-agency encryption keys, AES-256-GCM export, secure download links, PHIPA consent enforcement, rate limiting
3. **index.html** — update feature highlights if the hero section lists features
4. **faq.html** — add relevant Q&A for new features

Match the existing HTML structure, CSS classes, and tone. Include `alt` text on any images. Keep `robots.txt` and noindex meta tags as-is.

### Agent D: TEMPLATE-ALIGN1 — Report template field naming alignment

**Files:** `apps/reports/` only (models.py, forms.py, csv_parser.py, funder_report.py, migrations/)

The `DemographicBreakdown` model uses a field called `bins_json`, but the report template JSON files use `bins`. Align the naming so they're consistent:

1. Read `apps/reports/models.py` to find the `DemographicBreakdown` model and its `bins_json` field
2. Search for all references to `bins` vs `bins_json` in report-related code
3. Decide the canonical name (prefer what the model uses) and align all references
4. If renaming a model field, create a migration
5. Run `pytest tests/test_exports.py` to verify nothing breaks

Do NOT touch files outside `apps/reports/` and its migrations.

### Agent E: AI-TOGGLE1 — Split AI feature toggle

**Files:** `konote/ai_views.py`, `apps/admin_settings/views.py`, `apps/admin_settings/management/commands/seed.py`, `apps/reports/insights_views.py`, `tests/test_ai_endpoints.py`, `tests/test_goal_builder.py`, `seeds/sample_setup_config.json`, `.env.example`, `docs/admin/features-and-modules.md`

Split the single `ai_assist` toggle into two: `ai_assist_tools_only` (default enabled) and `ai_assist_participant_data` (default disabled, depends on tools_only).

**Read first:** `tasks/design-rationale/ai-feature-toggles.md` — the full DRR with approved design, migration notes, and anti-patterns.

Implementation steps (from DRR "Migration Notes" section):

1. In `apps/admin_settings/views.py` `DEFAULT_FEATURES` dict: rename `ai_assist` entry to `ai_assist_tools_only`, change default to **enabled**, add `ai_assist_participant_data` as a new entry with `depends_on: ai_assist_tools_only` and default **disabled**
2. Update admin UI labels per DRR: `ai_assist_tools_only` labelled "AI Tools (no participant data)", `ai_assist_participant_data` labelled "AI Participant Insights"
3. In `konote/ai_views.py`: split `_ai_enabled()` — create `_ai_tools_enabled()` checking `ai_assist_tools_only` and `_ai_participant_data_enabled()` checking `ai_assist_participant_data`
4. Update endpoints: `suggest_metrics_view`, `improve_outcome_view`, `generate_narrative_view`, `suggest_note_structure_view`, `suggest_target_view`, `goal_builder_start`, `goal_builder_chat` → use `_ai_tools_enabled()`
5. Update `outcome_insights_view` → use `_ai_participant_data_enabled()`
6. In `apps/reports/insights_views.py`: update lines ~374 and ~426 to check `ai_assist_participant_data` instead of `ai_assist`
7. Add confirmation modal for enabling `ai_assist_participant_data` (governance nudge — see DRR "Confirmation modal" section)
8. Add audit logging when `ai_assist_participant_data` is toggled — use `AuditLog.objects.using("audit")`
9. Update seed.py: set `ai_assist_tools_only=True` by default, `ai_assist_participant_data=True` only in demo mode
10. Data migration: agencies with existing `ai_assist=True` get both new toggles set to True
11. Update tests in `test_ai_endpoints.py` and `test_goal_builder.py` to use new toggle names
12. Update `seeds/sample_setup_config.json` and `.env.example`
13. Update `docs/admin/features-and-modules.md`
14. Run `pytest tests/test_ai_endpoints.py tests/test_goal_builder.py` to verify

Do NOT touch: `apps/reports/models.py`, `apps/reports/forms.py` (Agent D's territory), `apps/plans/`, `apps/notes/` (Agent F's territory).

### Agent F: DQ1 — Entry-time plausibility warnings

**Files:** `apps/plans/models.py`, `apps/plans/forms.py`, `apps/notes/forms.py`, `apps/notes/views.py`, `templates/notes/note_form.html`, `tests/test_notes.py`, `apps/plans/migrations/`

Add soft plausibility warnings when metric values look unusual during data entry. Prioritise financial metrics.

**Read first:** `tasks/data-validation-design.md` — the full design with proposed thresholds.

Implementation steps:

1. **Model:** Add `warn_min` (FloatField, null=True) and `warn_max` (FloatField, null=True) to `MetricDefinition` in `apps/plans/models.py`. Add clean() validation: warn_min <= warn_max, warn thresholds inside hard min/max limits. Create migration.
2. **Admin form:** Add `warn_min` and `warn_max` fields to `MetricDefinitionForm` in `apps/plans/forms.py` with number input widgets
3. **Metric value form:** In `apps/notes/forms.py` `MetricValueForm.clean_value()`: after hard validation passes, check if value is outside warn_min/warn_max range. If so, add a soft warning (not a ValidationError). Add a `_confirm_plausibility` hidden field that staff must check to override.
4. **Template:** In `templates/notes/note_form.html`: add a warning banner area (styled differently from errors — amber/yellow, not red). Show: "This value ({value}) is outside the expected range ({warn_min}–{warn_max}) for {metric_name}. Please confirm if correct." Add confirmation checkbox.
5. **View:** In `apps/notes/views.py`: handle the `_confirm_plausibility` flag. If warning exists and not confirmed, re-render form with warning visible. If confirmed, save and log the override to audit DB.
6. **Seed data:** Pre-populate warn_min/warn_max for built-in financial coaching metrics from the thresholds table in the design doc
7. **Tests:** Add to `tests/test_notes.py`: warning triggered when value outside range, form re-renders with warning, confirmation checkbox allows save, override logged to audit, null warn_min/warn_max means no warning
8. Run `pytest tests/test_notes.py tests/test_plans.py` to verify

Do NOT touch: `apps/reports/` (Agent D's territory), `konote/ai_views.py` or `apps/admin_settings/views.py` (Agent E's territory).

## After all agents finish

1. Review each agent's work — check for consistency, conflicts, correct Canadian spelling
2. Run `python manage.py translate_strings` if any templates were modified
3. Run `python manage.py makemigrations` — verify no conflicts between Agent D (reports), Agent E (admin_settings), and Agent F (plans) migrations
4. Commit each agent's work as a separate commit with the relevant task ID(s)
5. Push and create PR to `develop`
6. Update TODO.md: mark DEPLOY-TOOLKIT1, DOC-DEPLOY1, DOC-TECH1, WEBSITE-UPDATE1, TEMPLATE-ALIGN1, AI-TOGGLE1, DQ1 as done

## File conflict matrix (why these are safe in parallel)

| Agent | Task IDs | Files touched | Conflicts with |
|-------|----------|--------------|----------------|
| A | DEPLOY-TOOLKIT1 | `docs/agency-setup-guide/01-09` | None |
| B | DOC-DEPLOY1 + DOC-TECH1 | `docs/deploying-konote.md`, `docs/technical-documentation.md` | None |
| C | WEBSITE-UPDATE1 | `konote-website/` (separate repo) | None |
| D | TEMPLATE-ALIGN1 | `apps/reports/{models,forms,csv_parser,funder_report}` | None |
| E | AI-TOGGLE1 | `konote/ai_views.py`, `apps/admin_settings/`, `apps/reports/insights_views.py`, tests | None (E touches insights_views.py, D touches other reports/ files) |
| F | DQ1 | `apps/plans/`, `apps/notes/`, `templates/notes/`, `tests/test_notes.py` | None |
