# Funder Report Approval Workflow — Implementation Plan

**Task ID:** RPT-APPROVE1
**Date:** 2026-02-20
**Design:** [tasks/funder-report-approval.md](../../tasks/funder-report-approval.md)
**Related:** DQ2 (pre-report data quality checks), RPT-SCHEMA1 (standardised report schema)

## Summary

Add a quality review + annotation + approval step to the funder report export flow. Currently, data flows straight from database to CSV. After this change, staff will preview the report, review flagged issues, add context notes, and explicitly approve before the export is created.

## Current State

The funder report export flow lives in two key files:

- [apps/reports/views.py](../../apps/reports/views.py) — `funder_report_form()` view (line ~979): handles GET (show form) and POST (generate report)
- [apps/reports/funder_report.py](../../apps/reports/funder_report.py) — `generate_funder_report_data()`: assembles all the data (service stats, demographics, outcomes)
- [apps/reports/models.py](../../apps/reports/models.py) — `SecureExportLink` model stores export metadata; `ReportTemplate` + `DemographicBreakdown` define report schemas

Current POST flow:
1. User submits form (program, dates, fiscal year, format, template)
2. `generate_funder_report_data()` assembles everything
3. Small-cell suppression applied
4. CSV/PDF generated
5. `_save_export_and_create_link()` saves file + creates `SecureExportLink`
6. Audit log written
7. User sees download link

**What's missing:** There's no preview, no quality check, no annotation, and no explicit "I approve this for sharing."

## Proposed Implementation

### Phase A: Report Preview + Annotation (1 week)

Insert a preview step between form submission and export generation.

#### Step 1: Add `agency_notes` field to `SecureExportLink`

**File:** `apps/reports/models.py`

```python
# Add to SecureExportLink model
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

Run `makemigrations` and `migrate`.

#### Step 2: Split funder_report_form into preview + approve

**File:** `apps/reports/views.py`

Split the current `funder_report_form()` POST handler into two steps:

1. **POST to `/reports/funder/`** — validate form, generate report data, store in session, redirect to preview
2. **GET `/reports/funder/preview/`** — render the preview page showing report summary, any data quality warnings, and an annotation text field
3. **POST to `/reports/funder/approve/`** — read report data from session, generate CSV/PDF, create SecureExportLink with agency_notes, write audit log

New views:
- `funder_report_preview(request)` — render preview template
- `funder_report_approve(request)` — generate export with annotation

**URL changes** in `apps/reports/urls.py`:
```python
path("funder/preview/", views.funder_report_preview, name="funder_report_preview"),
path("funder/approve/", views.funder_report_approve, name="funder_report_approve"),
```

#### Step 3: Create preview template

**File:** `templates/reports/funder_report_preview.html`

Show:
- Report metadata (program, date range, fiscal year)
- Service statistics summary (individuals served, contacts)
- Demographic breakdown preview
- Outcome indicators preview
- "Agency Notes" textarea (optional free-text annotation)
- "Approve and Export" button
- "Go Back" link to modify filters

#### Step 4: Include agency notes in CSV output

**File:** `apps/reports/funder_report.py`

Update `generate_funder_report_csv_rows()` to accept optional `agency_notes` parameter and include it as a header section:

```
AGENCY NOTES
[text content]
```

#### Step 5: Audit log the approval

Update the audit log entry in `funder_report_approve()` to include:
- `"approved_by"`: staff display name
- `"agency_notes"`: first 200 chars of the annotation
- `"warnings_acknowledged"`: count of any data quality warnings the user saw

### Phase B: Data Quality Warnings (2-3 weeks)

Add the quality check layer to the preview screen. This depends on DQ2 design.

#### Step 6: Create data quality check module

**File:** `apps/reports/data_quality.py` (new)

Functions:
- `check_outlier_values(program, date_from, date_to)` — flag metric values that exceed warn_min/warn_max
- `check_missing_data(program, date_from, date_to)` — flag clients with gaps in expected metric recordings
- `check_stale_records(program, date_from, date_to)` — flag enrolled clients with no recent notes
- `check_nonnumeric_values(program, date_from, date_to)` — flag metric entries that can't be parsed as numbers

Each function returns a list of warning dicts:
```python
{
    "severity": "warning",  # or "error", "info"
    "category": "outlier",
    "message": "Participant #247: Total Debt of $700,000 exceeds warn_max of $200,000",
    "client_id": 247,
    "metric_name": "Total Debt",
    "value": 700000,
}
```

#### Step 7: Show warnings on preview screen

Update `funder_report_preview()` to call the quality check functions and display warnings grouped by severity. Each warning shows:
- Description of the issue
- Link to the client record (so staff can fix the data without losing their place)
- "Acknowledge" checkbox (JavaScript toggle)

Staff must either fix the data or acknowledge all warnings before the "Approve and Export" button is enabled.

#### Step 8: Store acknowledged warnings

Add a JSON field to SecureExportLink:
```python
quality_warnings_json = models.JSONField(default=dict, blank=True)
```

Store the count and categories of warnings that were acknowledged (not the full list, to avoid storing client IDs in export metadata).

### Phase C: Report History View (1 week)

#### Step 9: Add report history page

**File:** `apps/reports/views.py` — new `report_history()` view

Show past approved funder reports with:
- Date generated, program, fiscal year
- Who approved it
- Agency notes (expandable)
- Warning count at time of approval
- Download link (if still valid)

**URL:** `/reports/funder/history/`

This reuses the existing `SecureExportLink` data — no new models needed.

## Files Changed

| File | Change |
|------|--------|
| `apps/reports/models.py` | Add agency_notes, approved_by, approved_at, quality_warnings_json fields |
| `apps/reports/views.py` | Split funder_report_form; add preview + approve views; add history view |
| `apps/reports/urls.py` | Add preview, approve, and history URLs |
| `apps/reports/funder_report.py` | Update CSV generation to include agency notes |
| `apps/reports/data_quality.py` | New module — quality check functions |
| `apps/reports/forms.py` | Add annotation form for the preview page |
| `templates/reports/funder_report_preview.html` | New preview + annotation template |
| `templates/reports/funder_report_history.html` | New report history template |
| `tests/test_reports.py` | Add tests for preview, approve, history, quality checks |
| `locale/fr/LC_MESSAGES/django.po` | French translations for new strings |

## Migration

One migration adding fields to `SecureExportLink`. Non-breaking — all new fields are nullable or have defaults.

## Dependencies

- **DQ1 (entry-time warnings):** Not blocking, but if warn_min/warn_max fields exist on MetricDefinition, the quality check module can use them. Without DQ1, the quality checks use hardcoded thresholds.
- **RPT-SCHEMA1 (standardised schema):** Not blocking. Quality checks work regardless of whether a report template is selected.

## Implementation Order

1. Phase A first — preview + annotation is the most valuable piece and has no dependencies
2. Phase B second — quality warnings add safety but require more work
3. Phase C third — history view is a nice-to-have that rounds out the feature

## Open Questions (carry forward from design doc)

1. Should the quality review screen block the export, or just warn? **Recommendation: warn only** — staff can proceed with acknowledged warnings. Blocking would create friction for legitimate edge cases.
2. Should acknowledged warnings be listed in the export? **Recommendation: include a summary line** — e.g. "This report was approved with 3 acknowledged data quality warnings."
3. What format for agency notes in CSV? **Recommendation: header rows** — same pattern as existing metadata headers.
4. Should there be a "draft" state? **Recommendation: no** — the preview IS the draft. Keep it simple.
