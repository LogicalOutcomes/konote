# Implementation Prompt: G4 + RP2/RP3

**What this is:** A prompt for a Claude Code session to implement the two P0 code deliverables. Copy this into a new session (or a worktree session) and let it run.

**Branch:** Create `feat/p0-approval-workflow-and-g4` from `develop`

---

## Task 1: REQ-G4 — Auto-Update Progress Metrics on Goal Status Change

**What:** When a worker changes a PlanTarget's status (completed, deactivated, or back to default), automatically recompute the achievement_status for that target.

**Current state:**
- `apps/plans/models.py` has `PlanTarget` with `status` field ("default", "completed", "deactivated") and `achievement_status` field
- `apps/notes/signals.py` already has signals that call `update_achievement_status()` when a `ProgressNoteTarget` or `MetricValue` is saved
- `apps/plans/achievement.py` has `compute_achievement_status()` and `update_achievement_status()` — these are the functions to reuse
- `apps/plans/views.py::target_status()` (line ~365) handles the HTMX dialog to change goal status — it updates `target.status` but does NOT call `update_achievement_status()`
- `apps/plans/apps.py` does NOT have a `ready()` method and does NOT import signals

**Implementation:**

1. Create `apps/plans/signals.py`:
```python
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


@receiver(pre_save, sender="plans.PlanTarget")
def capture_previous_status(sender, instance, **kwargs):
    """Store the previous status so post_save can detect changes."""
    if instance.pk:
        try:
            instance._previous_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender="plans.PlanTarget")
def recompute_achievement_on_status_change(sender, instance, **kwargs):
    """When goal status changes, recompute achievement_status."""
    previous = getattr(instance, "_previous_status", None)
    if previous is not None and previous != instance.status:
        from apps.plans.achievement import update_achievement_status
        update_achievement_status(instance)
```

2. Update `apps/plans/apps.py` to import the signals:
```python
class PlansConfig(AppConfig):
    name = "apps.plans"

    def ready(self):
        import apps.plans.signals  # noqa: F401
```

3. Add a test in `tests/test_plans.py`:
- Create a PlanTarget with a metric and some MetricValues
- Change `target.status` to "completed"
- Assert `target.achievement_status` was recomputed
- Change `target.status` to "deactivated"
- Assert `target.achievement_status` was recomputed
- Verify that saving without changing status does NOT trigger recomputation

**Important design note:** The signal should NOT override a worker-assessed achievement status. Check `update_achievement_status()` — it already respects `achievement_status_source == "worker_assessed"`. The signal just calls the same function.

**Files changed:**
- `apps/plans/signals.py` (new)
- `apps/plans/apps.py` (add ready())
- `tests/test_plans.py` (add test)

**Run tests:** `pytest tests/test_plans.py -v`

---

## Task 2: RPT-APPROVE1 — Funder Report Approval Workflow (Phase A)

**What:** Insert a preview + annotation + approval step between the funder report form submission and the export generation.

**Current state:**
- `apps/reports/views.py::funder_report_form()` (line ~979) handles GET (show form) and POST (generate report + create SecureExportLink immediately)
- `apps/reports/funder_report.py` has `generate_funder_report_data()` that assembles all report data
- `apps/reports/models.py` has `SecureExportLink` but NO `agency_notes`, `approved_by`, or `approved_at` fields
- `apps/reports/forms.py` has `FunderReportForm` with a `report_reviewed` checkbox but no DB-backed approval
- Design doc: `docs/plans/2026-02-20-funder-report-approval-design.md`

**Implementation:**

### Step 1: Add fields to SecureExportLink

In `apps/reports/models.py`, add to the `SecureExportLink` model:
```python
agency_notes = models.TextField(
    blank=True,
    default="",
    help_text=_("Agency context notes accompanying this export."),
)
approved_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name="approved_exports",
)
approved_at = models.DateTimeField(null=True, blank=True)
```

Run `python manage.py makemigrations reports` and `python manage.py migrate`.

### Step 2: Split funder_report_form POST into preview + approve

**Current flow:**
1. POST to `/reports/funder-report/` → generate data → create export → show download link

**New flow:**
1. POST to `/reports/funder-report/` → validate form → generate report data → store in session → redirect to preview
2. GET `/reports/funder-report/preview/` → show report summary, agency notes textarea, approve button
3. POST to `/reports/funder-report/approve/` → read data from session → generate CSV/PDF → create SecureExportLink with agency_notes, approved_by, approved_at → show download link

**In `apps/reports/views.py`:**

Modify the POST handler in `funder_report_form()`:
- After generating report data, serialize it to `request.session["pending_funder_report"]`
- Store form parameters too (program, dates, template, format)
- Redirect to the preview URL

Create `funder_report_preview(request)`:
- Read report data from session
- Render `templates/reports/funder_report_preview.html` showing:
  - Report metadata (program, date range, fiscal year, template name)
  - Service statistics summary (individuals served, contacts)
  - Outcome indicators table (metrics with values)
  - Demographic breakdown preview
  - "Agency Notes" textarea (optional)
  - "Approve and Export" button
  - "Go Back" link

Create `funder_report_approve(request)`:
- Read report data from session
- Read agency_notes from POST
- Generate CSV/PDF using existing pipeline
- Create SecureExportLink with:
  - `agency_notes` = form input
  - `approved_by` = request.user
  - `approved_at` = timezone.now()
- Clear session data
- Redirect to download page (existing flow)
- Write audit log entry including approval metadata

**In `apps/reports/urls.py`:**
```python
path("funder-report/preview/", views.funder_report_preview, name="funder_report_preview"),
path("funder-report/approve/", views.funder_report_approve, name="funder_report_approve"),
```

### Step 3: Create preview template

Create `templates/reports/funder_report_preview.html`:
- Extends base template
- Shows report data in a readable table format
- Includes a form with:
  - `agency_notes` textarea (label: "Agency Notes — optional context for this report")
  - CSRF token
  - "Approve and Export" submit button (primary action)
  - "Go Back" link to `/reports/funder-report/` (secondary action)
- Use `{% trans %}` for all user-facing strings
- Follow existing template patterns (Pico CSS, HTMX where appropriate)

### Step 4: Include agency notes in CSV output

In `apps/reports/funder_report.py`, update the CSV generation to include agency notes as header rows:
```
AGENCY NOTES
[text content]

[blank line]
[rest of report]
```

Only include the section if agency_notes is non-empty.

### Step 5: Update audit log

In the approve view, write an audit log entry:
```python
AuditLog.objects.using("audit").create(
    user=request.user,
    action="funder_report_approved",
    details={
        "program": program.name,
        "template": template.name if template else None,
        "period": f"{date_from} to {date_to}",
        "agency_notes_length": len(agency_notes),
        "approved_at": str(timezone.now()),
    },
)
```

### Step 6: Translations

After creating the preview template:
1. Run `python manage.py translate_strings`
2. Fill in French translations in `locale/fr/LC_MESSAGES/django.po`
3. Run `python manage.py translate_strings` again to compile

### Step 7: Tests

Add to `tests/test_reports.py`:
- Test preview page renders with report data in session
- Test preview page redirects to form if no session data
- Test approve creates SecureExportLink with agency_notes, approved_by, approved_at
- Test approve clears session data
- Test agency notes appear in CSV output
- Test audit log entry is created on approval
- Test permission checks (only users who can create exports can approve)

**Run tests:** `pytest tests/test_reports.py -v`

---

## Files Changed Summary

| File | Change |
|------|--------|
| `apps/plans/signals.py` | **New** — post_save signal for PlanTarget status change |
| `apps/plans/apps.py` | Add `ready()` to import signals |
| `apps/reports/models.py` | Add agency_notes, approved_by, approved_at to SecureExportLink |
| `apps/reports/views.py` | Split funder_report_form POST; add preview + approve views |
| `apps/reports/urls.py` | Add preview and approve URL patterns |
| `apps/reports/funder_report.py` | Include agency notes in CSV output |
| `apps/reports/forms.py` | Add approval annotation form (if needed) |
| `templates/reports/funder_report_preview.html` | **New** — preview + annotation template |
| `tests/test_plans.py` | Add G4 signal test |
| `tests/test_reports.py` | Add approval workflow tests |
| `locale/fr/LC_MESSAGES/django.po` | French translations for new strings |

---

## Implementation Order

Both tasks should be completable in a single Claude Code session (~2–3 hours total).

1. **G4 first** (~15 minutes) — small, self-contained, quick win
2. **RPT-APPROVE1 Steps 1–2** (~30 minutes) — model fields + view split
3. **Step 3** (~20 minutes) — preview template
4. **Steps 4–5** (~15 minutes) — CSV update + audit log
5. **Step 6** (~10 minutes) — translations
6. **Step 7** (~30 minutes) — tests

Commit after each step. Run relevant tests after each commit.

---

## What NOT to Build

- **Phase B (data quality warnings):** Deferred — depends on DQ2 design. The preview screen will eventually show warnings, but this prompt only covers Phase A.
- **Phase C (report history view):** Deferred — nice-to-have, not P0.
- **Cross-agency publishing:** Separate plan (tasks/p0-cross-agency-reporting-plan.md). The approval workflow is a prerequisite but doesn't include the "Publish" step.
