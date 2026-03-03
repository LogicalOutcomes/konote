# Session 2 Prompt — Reports & Funder Features

Paste this into a new Claude Code session in the KoNote repo.

---

## Context

You are continuing the parallel sprint from `tasks/parallel-sprint-plan.md`. Session 1 is complete:
- **Wave 1** (7 parallel tracks, 17 bug fixes) — merged via PRs #201–#207
- **Wave 2** (accessibility sweep, 9 fixes + review follow-ups) — PR #208 open, assigned to pboachie

This session builds the partner report approval workflow and fixes related report issues. There are 3 tasks (possibly 4 if a design doc is needed).

---

## Pre-work

1. `git pull origin develop`
2. Read these files before writing any code:
   - `tasks/funder-report-approval.md` — problem statement, design principles, proposed flow
   - `docs/plans/2026-02-20-funder-report-approval-design.md` — implementation plan with code locations, model changes, view splits, template structure
   - `TODO.md` — check current state of RPT-APPROVE1, QA-R8-UX11, QA-R8-UX8, DOC-RP4
3. Create branch: `feat/funder-report-approval` off develop
4. Mark all tasks you're about to work on as 🔨 IN PROGRESS in TODO.md. Commit to the feature branch.

---

## Task 1: QA-R8-UX11 — Fix `/reports/funder/` 404

**Problem:** The QA scenario references `/reports/funder/` but the actual URL is `/reports/funder-report/` (defined in `apps/reports/urls.py` line 22). Users clicking old bookmarks or links get a 404.

**Fix:** Add a redirect from the old URL to the correct one. In `apps/reports/urls.py`, add:

```python
from django.views.generic import RedirectView

# In the urlpatterns list, BEFORE the funder-report/ path:
path("funder/", RedirectView.as_view(pattern_name="reports:funder_report", permanent=True)),
```

**Verify:** Run `pytest tests/test_exports.py -v -k funder` to check nothing breaks. Add a quick test that `/reports/funder/` returns a 301 redirect to `/reports/funder-report/`.

**Commit immediately after this task.**

---

## Task 2: RPT-APPROVE1 — Partner Report Approval Workflow

This is the main task. Follow the implementation plan in `docs/plans/2026-02-20-funder-report-approval-design.md` closely. The plan has two phases — build **Phase A (Report Preview + Annotation)** only. Phase B (Data Quality Review) depends on DQ2 which isn't built yet.

### Step 2a: Model changes

**File:** `apps/reports/models.py`

Add three fields to the `SecureExportLink` model:
- `agency_notes` — TextField, blank, default ""
- `approved_by` — ForeignKey to User, null/blank, SET_NULL
- `approved_at` — DateTimeField, null/blank

Run `makemigrations` and `migrate`. Commit the migration.

### Step 2b: Split the funder report view

**File:** `apps/reports/views.py`

The current `funder_report_form()` view (line ~1102) handles everything in one POST. Split it into a two-step flow:

1. **POST to generate preview** — assemble report data (using existing `generate_funder_report_data()`), store it in the session, redirect to the preview page
2. **GET preview page** — show a read-only preview of what the report contains + an "Agency Notes" textarea + an "Approve and Export" button
3. **POST to approve** — read preview data from session, create the export with `agency_notes` and `approved_by`/`approved_at` populated, redirect to the download page

Key files to understand:
- `apps/reports/funder_report.py` — `generate_funder_report_data()` assembles all report data
- `apps/reports/views.py` line ~1102 — current funder_report_form view
- `apps/reports/forms.py` — FunderReportForm
- `templates/reports/funder_report_form.html` — current form template

Create a new `FunderReportApprovalForm` in `apps/reports/forms.py` with just the `agency_notes` field.

### Step 2c: Templates

Create two new templates:

**`templates/reports/funder_report_preview.html`**
- Extends `base.html`
- Shows a summary of the report: date range, program, template used, metric count, demographic breakdown count
- Shows a sample of the data (first 5–10 rows of key metrics, with column headers)
- "Agency Notes" textarea (optional)
- "Approve and Export" button (POST form with CSRF)
- "Back to Form" link
- Breadcrumbs: Home > Reports > Funder Report > Preview

**`templates/reports/funder_report_approved.html`**
- Extends `base.html`
- Confirmation page: "Report approved and exported"
- Shows: approved by, approved at, agency notes (if any), download link
- Link back to Reports

### Step 2d: URL routing

**File:** `apps/reports/urls.py`

Add two new paths:
```python
path("funder-report/preview/", views.funder_report_preview, name="funder_report_preview"),
path("funder-report/approve/", views.funder_report_approve, name="funder_report_approve"),
```

### Step 2e: Audit logging

When a report is approved, write an audit log entry:
```python
AuditLog.objects.using("audit").create(
    user=request.user,
    action="report_approved",
    detail=f"Funder report approved: {template.name}, {start_date}–{end_date}",
)
```

### Step 2f: Tests

**File:** `tests/test_exports.py` (or create `tests/test_funder_approval.py`)

Test cases:
1. POST to funder report form → redirects to preview (not directly to download)
2. Preview page shows report summary and agency notes textarea
3. POST to approve with notes → creates SecureExportLink with `approved_by`, `approved_at`, and `agency_notes` populated
4. POST to approve without notes → works (notes are optional)
5. Preview page requires authentication + `report.funder_report` permission
6. Approve page requires authentication + `report.funder_report` permission
7. Redirect from `/reports/funder/` → `/reports/funder-report/` works (from Task 1)

Run: `pytest tests/test_exports.py -v`

### Step 2g: Translations

After creating templates with `{% trans %}` tags:
1. Run `python manage.py translate_strings`
2. Fill in any empty French translations in `locale/fr/LC_MESSAGES/django.po`
3. Run `python manage.py translate_strings` again to compile
4. Commit both `.po` and `.mo` files

**Commit after each sub-step (model, views, templates, URLs, tests, translations).**

---

## Task 3: QA-R8-UX8 — Executive Dashboard Date Presets + PDF Export

**Problem:** The executive dashboard has no date presets or PDF export. Users must manually type date ranges.

**Files:**
- `apps/clients/dashboard_views.py` — dashboard view logic
- `templates/clients/executive_dashboard.html` — dashboard template
- `apps/reports/pdf_views.py` — existing PDF generation

### Step 3a: Date presets

Add date preset buttons above the date range picker in the dashboard template:
- "Last 30 days"
- "Last 90 days"
- "Last 365 days"
- "This fiscal year" (April 1 – March 31 for Canadian orgs)
- "Custom" (shows the existing date picker)

Use JavaScript to populate the date fields when a preset is clicked. No backend changes needed — the presets just fill in the form fields client-side.

### Step 3b: PDF export button

Add an "Export PDF" button to the dashboard that:
1. Submits the current filters (date range, programs) to a new endpoint
2. The endpoint renders the dashboard data into a PDF using WeasyPrint (same approach as existing PDF exports)
3. Returns the PDF as a download

Create a new view `executive_dashboard_pdf` in `apps/reports/pdf_views.py` (or `apps/clients/dashboard_views.py`) and a new template `templates/reports/executive_dashboard_pdf.html` for the PDF layout.

Add the URL path and wire the button.

### Step 3c: Tests

Add tests for:
1. Date presets populate the correct date ranges
2. PDF export returns a PDF response (content-type check)
3. PDF export respects permissions (executive role required)

Run: `pytest tests/test_clients.py tests/test_exports.py -v`

**Commit after each sub-step.**

---

## Task 4 (conditional): DOC-RP4 — Funder Reporting Dashboard Design Doc

**Only do this if** the following is true: check `tasks/funder-report-approval.md` section on "Standardised Report Schema" — has Prosper Canada provided their funder reporting templates? Check recent messages or task notes.

**If yes:** Write `docs/plans/funder-reporting-dashboard-design.md` covering:
- Which metrics aggregate across agencies
- How agencies publish data to the dashboard
- How funders view it (read-only, no individual participant data)
- Privacy safeguards (small-cell suppression, consent_to_aggregate_reporting)
- Reference `tasks/design-rationale/multi-tenancy.md` for suppression thresholds
- Reference `tasks/design-rationale/reporting-architecture.md` for the canonical reporting approach

**If no:** Skip this task. Add a note to TODO.md: "DOC-RP4: Still waiting on Prosper Canada funder reporting templates."

---

## After All Tasks

1. Run: `pytest tests/test_exports.py tests/test_clients.py -v`
2. Update `TODO.md`:
   - Mark completed tasks as `[x]` with date
   - Move to Recently Done
   - If DOC-RP4 was skipped, note it in Flagged
3. Push and create PR → develop:
   ```bash
   git push -u origin feat/funder-report-approval
   gh pr create --base develop --title "feat: partner report approval workflow (RPT-APPROVE1)" --body "..."
   ```
4. Assign PR to pboachie

---

## Key Constraints

- **Do NOT build Phase B (Data Quality Review)** from the design doc — that depends on DQ2 which isn't built yet. Phase A (preview + annotation + approval) only.
- **Do NOT build a funder login or portal** — this is an enhanced push model (agency exports data). See design principles in `tasks/funder-report-approval.md`.
- **Session data for preview** — store the assembled report data in Django session between preview and approve. The data is ephemeral — if the session expires, the user starts over.
- **Translations** — all new templates need `{% trans %}` tags and French translations. Run `translate_strings` after creating templates.
- **Existing test patterns** — look at `tests/test_exports.py` for how funder report tests are structured. Follow the same patterns (fixtures, permissions, assertions).
