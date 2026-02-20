# Data Validation — Two-Level Design Thinking

Task IDs: DQ1 (entry-time), DQ2 (pre-report)

## The Problem

Staff enter numeric data (metric values, financial fields) with no plausibility checking beyond hard min/max limits. A typo or misunderstanding can produce an outlier that silently distorts funder reports. There's also no quality gate before reports are exported — data flows straight from the database to the CSV/PDF.

## Level 1 — Entry-Time Plausibility Warnings (DQ1)

**What exists today:** `MetricValueForm.clean_value()` enforces hard min/max from `MetricDefinition`. Values outside the range are rejected. `number`-type custom fields have zero validation.

**What's needed:** A soft warning layer. Values within the valid range but unlikely get flagged for confirmation — staff can override but must acknowledge.

### Priority: Financial Metric Plausibility

Financial coaching metrics are the highest priority for plausibility warnings. The motivating example: a $700M debt entry (typo — actual value was $700) at a West Neighbourhood House financial coaching session. Without plausibility checks, this kind of error flows straight into funder reports and distorts aggregate outcomes.

**Why financial metrics first:**
- Financial values span a wide valid range (debt can genuinely be $0 to $200,000+), so hard min/max alone won't catch typos
- Typos in financial data often involve extra digits ($700 → $700,000) or misplaced decimals ($7.00 → $700)
- Funders like Prosper Canada aggregate financial outcomes across agencies — one outlier distorts the whole picture
- Clinical scales (PHQ-9, GAD-7) already have narrow ranges that catch most typos via hard min/max

#### Suggested `warn_min` / `warn_max` for Financial Coaching Metrics

These are soft thresholds — the form shows a warning but still allows submission after confirmation.

| Metric | Hard Min | Hard Max | warn_min | warn_max | Rationale |
|--------|----------|----------|----------|----------|-----------|
| Total Debt | $0 | $10,000,000 | $0 | $200,000 | Most individual consumer debt under $200K; above that warrants a second look |
| Monthly Income | $0 | $1,000,000 | $0 | $15,000 | ~$180K/year; high but plausible for dual-income households |
| Monthly Savings | -$10,000 | $1,000,000 | -$500 | $5,000 | Negative = drawing down savings; >$5K/month is unusual for coaching clients |
| Credit Score | 300 | 900 | 300 | 900 | Canadian credit scores are 300-900; hard limits suffice here |
| Credit Score Change | -600 | 600 | -100 | 150 | Most changes are <100 points per reporting period |
| Debt-to-Income Ratio | 0 | 100 | 0 | 50 | Ratios above 50% are rare and should be double-checked |
| Savings Rate (%) | -100 | 100 | -20 | 60 | Negative = spending more than earning; >60% is exceptional |
| Income Change ($) | -$100,000 | $100,000 | -$5,000 | $10,000 | Large swings warrant verification |

**Notes:**
- `_confirm: true` — these ranges need validation with Prosper Canada / Claire before setting as defaults
- Agencies can adjust warn_min/warn_max per metric in Admin Settings
- The warning message should say something like: "This value ($700,000) is unusually high for Total Debt. Please double-check. If correct, click Confirm."

### Two plausibility signals

1. **Statistical outlier** — value is far from the client's recent history for that metric. Example: PHQ-9 scores have been 5-8 for months, suddenly entered as 25.
2. **Absolute plausibility** — value seems implausible regardless of history. Example: $700,000,000 debt on a financial metric where the actual value was $700 (the typo that motivated this feature — flagged by Rebekah at West Neighbourhood House).

### Possible approaches

- **Recommended:** Add `warn_min` / `warn_max` fields to `MetricDefinition` (separate from hard `min_value` / `max_value`) — admin-configurable soft thresholds. Start with the financial metric defaults above, expand to other categories later.
- Or: compute a warning dynamically based on historical standard deviation (e.g., flag if > 2 SD from client's mean) — better for clinical scales with enough history, but requires data
- Or: both — admin-set soft thresholds AND dynamic historical comparison (ideal long-term, but start with static thresholds)

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
