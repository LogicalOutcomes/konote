# Session 4: Parallel Documentation + Code Cleanup

## Pre-flight (do first, sequentially)

Merge the 3 open PRs, then pull develop:

```
gh pr merge 222 --merge --repo LogicalOutcomes/konote
gh pr merge 224 --merge --repo LogicalOutcomes/konote
gh pr merge 225 --merge --repo LogicalOutcomes/konote
git pull origin develop
```

Then create a feature branch: `git checkout -b chore/session-4-docs-and-cleanup`

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

## After all agents finish

1. Review each agent's work — check for consistency, conflicts, correct spelling
2. Run `python manage.py translate_strings` if any templates were modified
3. Commit each agent's work as a separate commit with the relevant task ID
4. Push and create PR to `develop`
5. Update TODO.md: mark DEPLOY-TOOLKIT1, DOC-DEPLOY1, DOC-TECH1, WEBSITE-UPDATE1, TEMPLATE-ALIGN1 as done

## File conflict matrix (why these are safe in parallel)

| Agent | Files touched | Conflicts with |
|-------|--------------|----------------|
| A | `docs/agency-setup-guide/01-09` | None |
| B | `docs/deploying-konote.md`, `docs/technical-documentation.md` | None |
| C | `konote-website/` (separate repo) | None |
| D | `apps/reports/` | None |
