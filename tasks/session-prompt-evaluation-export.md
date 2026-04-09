# Session Prompt: Build De-Identified Evaluation Microdata Export

## What to build

A new export type in KoNote that produces de-identified, participant-level CSV files for external program evaluators. The CSV contains pseudonymous IDs, generalised demographics, and outcome metric values — with all direct identifiers removed and k-anonymity (k=5) enforced. Access is restricted to users with a new `report.evaluation_export` permission. Every export logs evaluator details (name, email, organisation, purpose, agreement expiry) to the immutable audit trail.

## Required reading (do this first)

1. `tasks/design-rationale/evaluation-microdata-export.md` — the DRR. Contains the full rationale, 10-step pipeline, anti-patterns, access control decisions, CSV format, and audit schema. **Do not deviate from this DRR without explicit user approval.**
2. `tasks/phase-evaluation-export-prompt.md` — the detailed implementation prompt with 5 tasks, model/view/form specifications, test cases, and dependency graph.

## Task summary

| Task | ID | What | Depends on |
|------|----|------|-----------|
| Permission | EVAL-PERM1 | New `report.evaluation_export` permission, `can_create_evaluation_export()` utility | — |
| Pipeline engine | EVAL-PIPE1 | `apps/reports/deidentify.py` — 10-step pipeline: extract → consent filter → strip PII → pseudonymise → generalise → k-anonymity → resolve violations → population gate → generate CSV → suppression report | — |
| Form and view | EVAL-FORM1 | `EvaluationExportForm`, `evaluation_export_form()` view with preview/confirm flow, two templates | EVAL-PERM1, EVAL-PIPE1 |
| Navigation | EVAL-NAV1 | Wire into reports nav, add `"evaluation_microdata"` to SecureExportLink export_type, add `linkage_key_encrypted` field | EVAL-FORM1 |
| Admin config | EVAL-ADMIN1 | `is_evaluation_exportable` on CustomFieldGroup, integration into form and pipeline | EVAL-PIPE1 |

Tasks 1 and 2 are independent — build them in parallel if using sub-agents. Task 3 depends on both. Task 4 depends on 3. Task 5 can start after Task 2.

## Key architectural decisions (from the DRR)

- **K-anonymity threshold: k=5** — matches existing small-cell suppression and CIHI guidelines
- **Population thresholds (system-enforced, not advisory):**
  - n < 15 → blocked, aggregate only
  - 15 ≤ n < 30 → max 3 quasi-identifier columns
  - n ≥ 30 → max 5 quasi-identifier columns
- **Suppression ceiling: 15%** — if more records need suppression, block the export and advise fewer QI columns
- **Pseudonymous IDs: random short codes** (e.g., EVL-001) — NOT sequential from record_id, NOT hashed from record_id
- **Linkage table** (real ID ↔ study ID): encrypted with Fernet, stored on SecureExportLink, for participant withdrawal requests only
- **Always elevated**: evaluation exports always use the elevated export flow (delay + admin notification)
- **contains_pii = False**: the export is de-identified, but is_elevated = True because it's individual-level data going to an external party
- **No evaluator accounts**: evaluator email is audit metadata only — KoNote doesn't email, authenticate, or interact with evaluators
- **Consent**: use existing `consent_to_aggregate_reporting` field — do NOT create a new consent flag

## Existing code to reuse (do not rebuild)

- `SecureExportLink` model and download flow (`apps/reports/models.py`, `apps/reports/views.py`)
- Elevated export delay and admin notification (`_notify_admins_elevated_export()`)
- CSV injection prevention (`apps/reports/csv_utils.py`)
- Age grouping logic (`apps/reports/demographics.py`)
- Small-cell suppression logic (`apps/reports/suppression.py`) — adapt from cell-level to row-level
- `AuditLog` model (`apps/audit/models.py`) — no schema change, use existing `metadata` JSONField
- Permission checking patterns (`apps/reports/utils.py`)
- Form field rendering (`templates/includes/_form_field.html`)

## New files to create

- `apps/reports/deidentify.py` — the pipeline engine (Task 2, bulk of the work)
- `templates/reports/evaluation_export.html` — the form
- `templates/reports/evaluation_export_preview.html` — preview/confirm step
- `tests/test_evaluation_export.py` — all tests for this feature

## Environment notes

- Django commands must run on the VPS via SSH, not locally (no local .env or PostgreSQL)
- Migrations: `ssh konote-vps "docker compose -f /opt/konote-dev/docker-compose.yml exec web python manage.py makemigrations"`
- Tests: `ssh konote-vps "docker compose -f /opt/konote-dev/docker-compose.yml exec web pytest tests/test_evaluation_export.py"`
- After template changes with `{% trans %}` tags, run `translate_strings` and add French translations
- Mark each task 🔨 IN PROGRESS in TODO.md before starting, mark [x] when done

## After completion

- Run `pytest tests/test_evaluation_export.py` — verify all tests pass
- Run `pytest tests/test_reports.py` — verify existing export tests still pass
- Update TODO.md: mark EVAL-EXPORT1 as done
- Create PR to `develop`, merge, clean up branch, pull develop
