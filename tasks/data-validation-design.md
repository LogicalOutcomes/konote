# Data Validation — Two-Level Design Thinking

Task IDs: DQ1 (entry-time), DQ2 (pre-report)

## The Problem

Staff enter numeric data (metric values, financial fields) with no plausibility checking beyond hard min/max limits. A typo or misunderstanding can produce an outlier that silently distorts funder reports. There's also no quality gate before reports are exported — data flows straight from the database to the CSV/PDF.

## Level 1 — Entry-Time Plausibility Warnings (DQ1)

**What exists today:** `MetricValueForm.clean_value()` enforces hard min/max from `MetricDefinition`. Values outside the range are rejected. `number`-type custom fields have zero validation.

**What's needed:** A soft warning layer. Values within the valid range but unlikely get flagged for confirmation — staff can override but must acknowledge.

### Two plausibility signals

1. **Statistical outlier** — value is far from the client's recent history for that metric. Example: PHQ-9 scores have been 5-8 for months, suddenly entered as 25.
2. **Absolute plausibility** — value seems implausible regardless of history. Example: $1,000,000 debt on a financial metric where typical range is $0-$50,000.

### Possible approaches

- Add `warn_min` / `warn_max` fields to `MetricDefinition` (separate from hard `min_value` / `max_value`) — admin-configurable soft thresholds
- Or: compute a warning dynamically based on historical standard deviation (e.g., flag if > 2 SD from client's mean)
- Or: both — admin-set soft thresholds AND dynamic historical comparison

### UX concept

- JavaScript-driven warning banner on the note form — appears when a value looks unlikely
- Not a hard Django validation error — the form can still submit
- Staff must click "Confirm this value" or similar to proceed
- Override is logged (who confirmed, when, what the flagged value was)

### Gaps to address

- `number`-type `CustomFieldDefinition` fields have no min/max at all — need basic range validation first
- `MetricDefinition` doesn't validate that `min_value < max_value`

### Key files

- `apps/plans/models.py` — `MetricDefinition` model
- `apps/notes/forms.py` — `MetricValueForm`
- `apps/clients/models.py` — `CustomFieldDefinition`
- Templates: note entry forms (full note with metric inputs)

---

## Level 2 — Pre-Report Data Quality Check (DQ2)

**What exists today:** Reports export data as-is. The `_to_float()` helper silently skips non-numeric values. Small-cell suppression exists but is a privacy control, not quality control.

**What's needed:** A quality check step before funder reports are generated, showing a summary of potential issues for staff to review.

### What could be flagged

- **Outlier values** — individual metric entries that are statistical outliers across the program
- **Missing data** — clients with gaps in expected metric recordings (e.g., monthly metric with no entry for 2+ months in the report period)
- **Non-numeric values** — metric entries that can't be parsed as numbers (currently silently dropped)
- **Stale records** — clients whose last note is months old but are still enrolled
- **Unusual patterns** — sudden spikes or drops across many clients that might indicate systematic data entry errors
- **Demographic inconsistencies** — totals that don't reconcile

### UX concept

- Before the export link is generated, show a "Data Quality Summary" screen
- List warnings grouped by severity (errors vs. warnings vs. info)
- Staff can: fix the underlying data, acknowledge warnings and proceed, or cancel
- Could also be a standalone "Data Quality Report" page accessible outside the export flow (useful for ongoing monitoring)

### Key files

- `apps/reports/views.py` — export views (add quality gate step)
- `apps/reports/funder_report.py` — `generate_funder_report_data()`
- `apps/reports/aggregations.py` — where data is assembled
- New module: `apps/reports/data_quality.py`

---

## Open Questions (for when we implement)

1. Should the Level 1 warning thresholds be per-metric (admin configures) or computed automatically from data?
2. Should Level 2 quality checks block the export or just warn?
3. Should there be a "data quality score" shown on the report form before generation?
4. How do we handle metrics with very few data points (not enough history for statistical comparison)?
5. Should overridden warnings be visible in the exported report itself (so funders know)?
6. Who reviews override logs, and when? Consider a weekly "data quality digest" email to program managers showing overridden entries.
7. How should portal self-reported values (participants entering their own financial data) get different plausibility thresholds than staff-entered clinical metrics?
