# Insights Page — Metric Distributions Implementation Plan

**DRR:** `tasks/design-rationale/insights-metric-distributions.md`
**Created:** 2026-02-22
**Status:** Ready for implementation (pending Phase 0 GK review)

## Overview

Add quantitative metric data (distributions, achievement rates) to the insights page, reorder sections to centre participant voice, relabel existing charts for clarity, and update the executive dashboard with program outcome cards. Three data layers, each with appropriate visualization. Service-framing language throughout.

## Phase 0: Language Review & Metric Admin (HARD BLOCKER on Phase 2)

### Task 0.1: GK language review

**Not a code task.** GK must review and approve before any template work begins:

- [ ] Band display labels: "More support needed" / "On track" / "Goals within reach" — or GK-approved alternatives
- [ ] "Two Lenses" card wording (participant vs. staff comparison)
- [ ] Achievement metric examples for 3-4 common program types (employment, housing, mental health, youth)
- [ ] Band thresholds for clinical instruments (PHQ-9, GAD-7, etc.) — must use published cutoff scores
- [ ] Executive dashboard card content and labels
- [ ] Whether movement tracking should be scoped for next phase

**Phase 2 cannot start until this task is complete.** Language gets baked into templates, CSS, and tests — changing it later is expensive.

### Task 0.2: Update admin form for MetricDefinition

Add `metric_type`, `higher_is_better`, `threshold_low`, `threshold_high`, `achievement_options`, `achievement_success_values`, `target_rate`, `target_band_high_pct` to the admin form for MetricDefinition.

Show `achievement_options` and `achievement_success_values` only when `metric_type="achievement"`.
Show `threshold_low`, `threshold_high`, `higher_is_better` only when `metric_type="scale"`.
Show `target_rate` only when `metric_type="achievement"`.
Show `target_band_high_pct` only when `metric_type="scale"`.

This enables agencies to configure metrics before the visualization is built.

### Task 0.3: Configure at least one test program

Configure achievement metrics on at least one program (using admin form from Task 0.2) so Phase 2-3 development has real data to test against. If using demo data, seed achievement metric values for the demo program.

## Phase 1: Model Changes & Data Layer

### Task 1.1: Add fields to MetricDefinition

**File:** `apps/plans/models.py`

Add to `MetricDefinition`:
```python
METRIC_TYPE_CHOICES = [
    ("scale", _("Numeric scale")),
    ("achievement", _("Achievement")),
]

metric_type = CharField(max_length=20, choices=METRIC_TYPE_CHOICES, default="scale")
higher_is_better = BooleanField(default=True, help_text="False for metrics like PHQ-9 where lower is better.")
threshold_low = FloatField(null=True, blank=True, help_text="Low band boundary.")
threshold_high = FloatField(null=True, blank=True, help_text="High band boundary.")
achievement_options = JSONField(default=list, blank=True, help_text='Options for achievement metrics, e.g. ["Employed", "In training", "Unemployed"].')
achievement_success_values = JSONField(default=list, blank=True, help_text='Which options count as achieved, e.g. ["Employed"].')
target_rate = FloatField(null=True, blank=True, help_text="Optional target % for achievement metrics.")
target_band_high_pct = FloatField(null=True, blank=True, help_text="Optional target for % in high band (scale metrics).")
```

Run `makemigrations` and `migrate`.

**Data migration:** Set default thresholds for universal metrics (Goal Progress, Self-Efficacy, Satisfaction): `threshold_low=2, threshold_high=4`. Leave category-specific metrics null (they use scale-thirds fallback until GK sets clinical values).

**Tests:** Model field tests — ensure threshold_low < threshold_high validation, ensure achievement fields only apply when metric_type="achievement".

### Task 1.2: Build metric aggregation functions

**New file:** `apps/reports/metric_insights.py`

Three functions (pure SQL aggregation, no decryption):

**`get_metric_distributions(program, date_from, date_to)`**

For each scale metric used by this program:
1. Get latest score per target per participant (using effective date)
2. Calculate per-participant median across their goals
3. Classify into bands (low / mid / high) using metric thresholds, respecting `higher_is_better`
4. Return: `{metric_id: {name, band_low_count, band_mid_count, band_high_count, total, band_low_pct, band_high_pct, n_new_participants, last_recorded}}`

Exclude participants with only 1 assessment (flag them as "new").

Privacy: suppress band counts < 5 (return "< 5" string instead of number). Skip metrics with total n < 10.

**`get_achievement_rates(program, date_from, date_to)`**

For each achievement metric used by this program:
1. Get latest value per participant
2. Count achieved vs. not achieved (using `achievement_success_values`)
3. Return: `{metric_id: {name, achieved_count, total, achieved_pct, target_rate, last_recorded}}`

Privacy: skip if total n < 10.

**`get_metric_trends(program, date_from, date_to)`**

For each scale metric:
1. Same per-participant median logic, but grouped by month
2. Return: `{metric_id: [{month, band_low_pct, band_high_pct, total}]}`

Only include months with n >= 10.

**`get_two_lenses(program, date_from, date_to)`**

When program has both Self-Efficacy (participant self-report) and staff descriptor data:
1. Get % of participants in high band for Self-Efficacy
2. Get % of staff descriptors rated "good_place"
3. Return: `{self_report_pct, staff_pct, gap, has_sufficient_data}`

Only return if both streams have n >= 10.

**Tests:** Unit tests with factory-created MetricValues. Test per-participant aggregation (verify multi-goal participants aren't over-counted). Test threshold flipping for higher_is_better=False. Test n < 5 suppression. Test n < 10 exclusion. Test Two Lenses gap calculation.

### Task 1.3: Build data completeness function

**File:** `apps/reports/metric_insights.py` (add to same file)

**`get_data_completeness(program, date_from, date_to)`**

1. Count enrolled participants in this program
2. Count participants with at least one MetricValue in the date range
3. Return: `{enrolled_count, with_scores_count, completeness_pct, completeness_level}` where completeness_level is "full" (>80%), "partial" (50-80%), or "low" (<50%)

## Phase 2: Per-Program Insights Page (BLOCKED on Phase 0)

### Task 2.1: Relabel existing charts

**File:** `templates/reports/_insights_basic.html`

Change:
- "Progress Trend" → "Staff Assessments Over Time"
- Add subtitle: "How workers rate participant progress at each session — a professional judgment, not a measured score"
- Move `interp_trend` text ABOVE the chart (currently below)

No data changes — pure template relabelling.

### Task 2.2: Restructure page with progressive disclosure

**File:** `templates/reports/_insights_basic.html`

Wrap Sections 2-6 in `<details>` elements with preview `<summary>` lines:

```html
<details id="section-participant-voice" {% if expand_participant_voice %}open{% endif %}>
  <summary>
    <strong>{% trans "Participant Voice" %}</strong> —
    {{ open_theme_count }} {% trans "open themes" %} · {{ new_quote_count }} {% trans "new quotes this period" %}
  </summary>
  {% include "reports/_insights_client.html" %}
</details>
```

Implement auto-expand logic in the view:
1. Urgent signals (urgent feedback themes, large negative trend) → open
2. Freshest data → open
3. Tie → Participant Voice opens (client-centred tiebreaker)
4. If only quantitative sections would open, Participant Voice also opens

Move Participant Voice section to position 2 (after summary cards, before metrics).

### Task 2.3: Add summary cards

**File:** `templates/reports/_insights_basic.html` (add at top of results section)

4 cards in a horizontal row, adapting to available data per the DRR summary cards table.

Card 1: Two Lenses gap (when both data streams exist) or lead outcome rate or metric headline
Card 2: Lead outcome/trend or active participants
Card 3: Data completeness (always) — "34 of 57 enrolled have scores (60%)"
Card 4: Open feedback themes count (always)

**File:** `apps/reports/insights_views.py`

Update `program_insights()` to call `get_metric_distributions()`, `get_achievement_rates()`, `get_data_completeness()`, and `get_two_lenses()`, pass results to template context. Determine which summary cards to show based on available data.

**CSS:** `static/css/main.css` — add `.insights-summary-cards` grid (4 cards, responsive, collapses to 2x2 on mobile).

### Task 2.4: Add Where Participants Are section (Layer 1)

**File:** `templates/reports/_insights_distributions.html` (new partial)

For each scale metric with sufficient data:

**Snapshot bar:** Horizontal stacked bar showing band_low / band_mid / band_high percentages. Colour-coded with patterns for accessibility. Shows n and last-recorded date. Labels use GK-approved display text (from Task 0.1).

**Trend chart:** Chart.js line chart with two lines (% in low band, % in high band). Same visual pattern as existing descriptor chart. Accessible data table in `<details>`.

**New participant note + movement tracking acknowledgment:** "X participants have only one assessment — not included in distributions. Movement tracking — who is progressing between bands over time — will be available in a future update."

Universal metrics first, then program-specific grouped by category.

Summary line: `Where Participants Are — X scored · Y% need more support · trend: improving/stable/declining`

### Task 2.5: Add Program Outcomes section (Layer 2)

**File:** `templates/reports/_insights_metrics.html` (new partial, included in `_insights_basic.html`)

Horizontal progress bars for achievement metrics. Each bar shows:
- Metric name
- % achieved (coloured bar)
- Count: "34 of 52"
- Target (if set): "(target: 70%)"
- Change from prior period (if available): "↑ from 58% last quarter"
- Journey context (if corresponding scale metric exists): "Among those not yet achieved: 72% making progress, 4 need more support"

Accessible data table in `<details>` below the bars.

Only renders if program has achievement metrics with n >= 10.

Summary line: `Program Outcomes — 65% employment (target: 70%) · 48% retention`

### Task 2.6: Update insights view to pass all data

**File:** `apps/reports/insights_views.py`

Update `program_insights()`:
1. Call `get_metric_distributions()` → pass as `metric_distributions`
2. Call `get_achievement_rates()` → pass as `achievement_rates`
3. Call `get_metric_trends()` → pass as `metric_trends` (JSON for Chart.js)
4. Call `get_data_completeness()` → pass as `data_completeness`
5. Call `get_two_lenses()` → pass as `two_lenses`
6. Determine auto-expand logic → pass as `expand_participant_voice`, `expand_distributions`, etc.
7. Determine which summary cards to show based on available data
8. Build `<summary>` preview content for each section

### Task 2.7: CSS for new sections

**File:** `static/css/main.css`

Add styles for:
- `.insights-summary-cards` — 4-card grid
- `.insights-two-lenses` — side-by-side participant/staff comparison
- `.insights-outcome-bar` — horizontal progress bar for achievement rates
- `.insights-distribution-bar` — horizontal stacked bar for scale metrics
- `.insights-metric-section` — container for each metric's snapshot + trend
- `.insights-completeness` — data completeness display and indicators
- Band colour variables using `band-low`, `band-mid`, `band-high` (must pass 4.5:1 contrast, NOT red-to-green, use Pico palette)
- Responsive breakpoints (cards → 2x2 on mobile, bars → full width)
- `details > summary` styling for section headers with preview content

## Phase 3: Executive Dashboard Update

### Task 3.1: Add program outcome cards to executive dashboard

**File:** Look at existing executive dashboard template and view.

Add a "Program Overview" section with one card per active program. Each card shows:
- Line 1: Lead outcome rate (Layer 2) or lead metric signal (Layer 1)
- Line 2: Target (if set) + trend direction (improving ↑ / stable → / declining ↓). No band counts.
- Line 3: Data completeness indicator (●/◐/○) with count and text alternative
- Line 4: Open feedback theme count (with urgency flag if any are urgent)
- Link: "View program learning →" to per-program insights page with program pre-selected

**File:** Update executive dashboard view to call metric aggregation functions per program.

Cards with urgent feedback themes or declining trends get a subtle left border accent (Pico caution colour).

### Task 3.2: Tests for executive dashboard

Test that:
- Programs without outcomes show Layer 1 fallback
- Suggestion theme counts are correct
- Privacy thresholds apply (n < 5 suppression on any visible counts)
- Band counts do NOT appear on executive cards (verify no `band_low_count` in rendered HTML)
- Cards link to correct insights page with program pre-selected
- Data completeness indicators are correct
- Trend direction is correctly calculated

## Phase 4: Achievement Metric Recording UI (can run parallel with Phase 2 after Phase 1)

### Task 4.1: Update note form for achievement metrics

When a goal has an achievement metric attached, the note form should show a dropdown (from `achievement_options`) instead of a number input.

**File:** Update note form template and form class to detect `metric_type="achievement"` and render appropriate widget.

### Task 4.2: Tests for note form changes

Test that:
- Achievement metrics show dropdown, not number input
- Scale metrics still show number input
- Achievement values are saved correctly

## Phase 5: Polish & Integration

### Task 5.1: Workbench-to-report connection

Add below insights content:
- List of partner report templates linked to this program ("You have a quarterly report due for United Way — Generate Report")
- Data completeness warning if < 80% of enrolled participants have scores

### Task 5.2: Board summary template design

Design a "Board Summary" report template type:
- 1-2 pages, PDF format
- Sections: Program Overview (counts, lead outcomes with targets), What Participants Are Telling Us (top themes + curated quotes with privacy protections), Data Quality (completeness), Narrative (editable placeholder)
- This uses the existing report generation system — it's a template configuration, not new architecture
- GK reviews content and layout

### Task 5.3: Update CLAUDE.md and documentation

Add to DRR references:
```
- `tasks/design-rationale/insights-metric-distributions.md` — Insights page metric distributions. Three data layers, distribution-based aggregation, service-framing language, executive dashboard cards, anti-patterns. Includes language framework (band_low/mid/high in code, GK-approved labels in display).
```

### Task 5.4: French translations

Run `translate_strings` after all template changes. Fill in French translations for new strings (section headings, card labels, chart labels, band labels, accessibility text, summary lines).

## Dependencies

| Task | Depends On |
|------|-----------|
| 0.1 (GK review) | Nothing |
| 0.2 (admin form) | 1.1 (model fields) — but can start UI scaffolding immediately |
| 0.3 (test program config) | 0.2 |
| 1.1 (model fields) | Nothing |
| 1.2 (aggregation functions) | 1.1 |
| 1.3 (completeness) | Nothing |
| 2.1 (relabel) | Nothing |
| 2.2 (progressive disclosure) | 0.1 (language approved) |
| 2.3 (summary cards) | 0.1, 1.2, 1.3 |
| 2.4 (distributions section) | 0.1, 1.2 |
| 2.5 (outcomes section) | 0.1, 1.2 |
| 2.6 (view update) | 1.2, 1.3 |
| 2.7 (CSS) | 0.1 (need band label names for CSS classes) |
| 3.1 (exec dashboard) | 1.2 |
| 3.2 (exec tests) | 3.1 |
| 4.1 (note form) | 1.1 |
| 4.2 (note form tests) | 4.1 |
| 5.1 (workbench link) | 2.6 |
| 5.2 (board template) | 0.1 (GK reviews content) |
| 5.3 (docs) | All |
| 5.4 (translations) | All templates |

## Independent tasks (can run in parallel)

- 0.1 (GK review) runs independently of all code tasks
- 1.1 + 1.3 + 2.1 (no dependencies between them)
- After 1.1: 0.2 + 1.2 + 4.1 (all depend only on model changes)
- After 0.2: 0.3 (configure test data)
- After 1.2 + 0.1 complete: 2.2 + 2.3 + 2.4 + 2.5 + 2.6 + 2.7 + 3.1 (all depend on aggregation functions + approved language)
- 4.1 + 4.2 can run parallel with Phase 2 (both depend only on Phase 1)

## GK Review Gates

**Phase 0 — HARD BLOCKER on Phase 2:**
- [ ] Band display labels approved ("More support needed" / "On track" / "Goals within reach" or alternatives)
- [ ] Clinical instrument thresholds (PHQ-9, GAD-7, etc.)
- [ ] Achievement metric examples for common program types
- [ ] "Two Lenses" card wording

**Before merging Phase 3:**
- [ ] Executive dashboard card content and labels
- [ ] "View program learning" link text

**Before merging Phase 5:**
- [ ] Board summary template content and layout
- [ ] Whether movement tracking should be scoped for next phase

## Testing Strategy

| What Changed | Test File |
|---|---|
| MetricDefinition fields | `tests/test_plans.py` |
| Metric aggregation functions | `tests/test_metric_insights.py` (new) |
| Insights views | `tests/test_insights.py` (extend existing) |
| Executive dashboard | `tests/test_executive_dashboard.py` (extend) |
| Note form changes | `tests/test_notes.py` |

Minimum test coverage for new code:
- Per-participant aggregation (multi-goal participants)
- Threshold direction flipping (higher_is_better=False)
- n < 5 band suppression
- n < 10 metric exclusion
- Achievement rate calculation with target comparison
- Summary card adaptation (with and without Layer 2 data, with and without Two Lenses)
- Two Lenses gap calculation
- Data completeness levels (full/partial/low)
- Privacy thresholds on executive dashboard cards
- No band counts in executive dashboard HTML
- Auto-expand logic for progressive disclosure
- Journey context line for achievement metrics (when scale metric exists)
