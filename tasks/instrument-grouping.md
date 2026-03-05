# Instrument Grouping for Metric Batteries — Implementation Plan

**Status:** Parking Lot: Ready to Build
**ID:** METRIC-INST1
**Depends on:** Metric library update (PR #288)

## Context

KoNote's metric library includes multi-item instruments that should be reported as batteries:
- **PHQ-9** (9 items, but KoNote stores total score — already a single metric)
- **GAD-7** (same — single score metric)
- **K10** (same — single score metric)
- **LogicalOutcomes Inclusivity Battery** (5 separate 4-point scale items)

The inclusivity battery is the primary use case. Its 5 items are designed for top-two-box analysis (% of respondents scoring 3 "Somewhat true" or 4 "Very true"). Currently they're 5 independent metrics with no grouping mechanism.

## Implementation Steps

### 1. Add instrument_name to MetricDefinition

**File:** `apps/plans/models.py`

```python
instrument_name = models.CharField(
    max_length=100, blank=True, default="",
    help_text=_("Group name for multi-item instruments (e.g. 'PHQ-9'). "
                "Metrics sharing an instrument_name are reported together."),
)
```

### 2. Migration + seed backfill

**File:** `seeds/metric_library.json`

Add `"instrument_name"` to relevant metrics:
- 5 inclusivity items: `"LogicalOutcomes Inclusivity Battery"`
- PHQ-9: `"PHQ-9"` (single metric, but labels it as standardized)
- GAD-7: `"GAD-7"`
- K10: `"K10"`

**File:** `apps/admin_settings/management/commands/seed.py`

Add `instrument_name` to the `defaults` dict and the backfill section.

### 3. Metric library admin — display grouping

**File:** `templates/plans/metric_library.html`

Show `instrument_name` badge next to metrics that have one. Optionally group metrics by instrument in the library view.

### 4. Reporting — aggregate instrument scores

**File:** `apps/reports/` (wherever program reports are generated)

When generating metric reports, if metrics share an `instrument_name`:
- Show individual item results
- Add an aggregate row: for inclusivity battery, compute top-two-box % (count of values >= 3 / total responses * 100)
- For PHQ-9/GAD-7/K10 this is already a single score, so no aggregation needed

### 5. Insights page — instrument-level view

**File:** `apps/plans/views.py` (insights view, if it exists)

Group metrics by instrument_name when displaying trends. Show the battery as a single card with sparklines for each item.

## Scoring Convention

Document in metric_library.json:
- **Top-two-box:** For 4-point Likert items (1-4), "top two" = values 3 and 4. Report as "X% positive" where positive means scored 3 or 4.
- **Scoring bands:** Already exist for PHQ-9/GAD-7/K10 (added in PR #288).

## Testing

- Unit test: instrument_name saves and retrieves correctly
- Unit test: metrics with same instrument_name are grouped in reports
- Seed test: verify backfill sets instrument_name on correct metrics
