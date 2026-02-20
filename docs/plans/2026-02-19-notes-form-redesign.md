# Notes Form Redesign — Design Document

**Date:** 2026-02-19
**Status:** Approved
**Task ID:** UX-NOTES1
**Owner:** GG

## Problem

The detailed progress notes form (`templates/notes/note_form.html`) is the most-used data entry screen in KoNote. Frontline staff fill it out after every client session, often under time pressure (10-15 minutes between appointments). The current form has these problems:

1. Every field stretches full-width, making the form feel longer than it is
2. Metrics are confusing text boxes instead of quick-tap inputs
3. Auto-calculable data (like session count) requires manual entry
4. 11+ fields at the same visual hierarchy with no grouping
5. Target details are buried in accordions, disconnected from workflow
6. No shortcut for routine "nothing to report" entries

## Design

### 4-Zone Form Layout

The form is divided into four visually distinct zones, ordered by effort:

```
Zone 1: SESSION SETUP (fast — 3 fields in a row)
Zone 2: TARGETS (the work — compact cards, expandable)
Zone 3: WRAP-UP (optional — collapsed by default)
Zone 4: PARTICIPANT VOICE (optional — collapsed by default)
Footer: STICKY SAVE BAR (consent + save)
```

### Zone 1: Session Setup

Three fields in a CSS Grid row, constrained to their natural widths:

| Field | Max Width | Notes |
|-------|-----------|-------|
| Template | 24rem | Dropdown, auto-fills interaction type |
| Interaction type | 20rem | Dropdown |
| Session date | 12rem | Date picker, pre-filled with today |

### Zone 2: Targets

**Target selection:** Checkboxes (unchanged from current design).

**Target cards:** Each selected target renders as a card (`<fieldset>` with `<legend>` for accessibility). Cards start in **compact state**:

- Target name as heading
- Descriptor pills in a row: [Getting easier] [Mixed/Steady] [Getting harder]
- "No change" shortcut button
- Expand indicator

**Compact card behaviour:**
- Staff can tap a descriptor pill without expanding (handles quick assessments)
- "No change" button auto-sets descriptor to "Steady" and marks the card done (visual checkmark)
- Click/tap the card header or expand indicator to reveal full fields

**Expanded card content (ordered for workflow — taps before typing):**
1. Descriptor pills (already visible from compact state)
2. Scale pill metrics (e.g., Confidence 1-5 rendered as tappable pills)
3. Auto-calculated metrics (read-only text, not form inputs)
4. Text input metrics (standard number inputs for non-scale metrics)
5. "In their words" — single-line text input (lighter than current)
6. "Your notes" — textarea

**General "Client said" field:** Below the target cards, a single text field for general client comments not tied to a specific target. Replaces the need to put "In their words" in every target when the client made one general comment.

### Zone 3: Wrap-up

Collapsed by default using `<details>`. Label: "Wrap-up details (optional)".

Contains:
- Summary textarea (optional)
- Engagement observation dropdown (20rem)
- Follow-up date picker (12rem)

### Zone 4: Participant Voice

Collapsed by default using `<details>`. Label: "Participant voice (optional)".

Contains:
- Reflection textarea
- Suggestion textarea
- Priority dropdown (appears when suggestion has content — existing JS)

No coaching prompts in the form itself (moved to staff training materials).

### Sticky Footer

- Consent checkbox — wording changed to: "I have reviewed this note for accuracy (recommended)"
- `required=False` — recommended, not mandatory
- Autosave indicator (existing)
- Cancel and Save buttons (existing)

## Scale Pills

Metrics with small integer ranges (both min and max set, both integers, range <= 9 steps) render as tappable pill buttons instead of text inputs.

**Detection logic** (in `MetricValueForm.__init__`):
```
is_scale = (
    min_value is not None
    and max_value is not None
    and min_value == int(min_value)
    and max_value == int(max_value)
    and (max_value - min_value) <= 9
)
```

When `is_scale` is True, the form widget switches to `RadioSelect` with choices from min to max.

**CSS:** Reuse the existing `.descriptor-pills` pattern (hidden radio, visible label, `:has(:checked)` highlight). New class `.scale-pills` extends this with number-specific sizing.

**Accessibility:** The radiogroup gets `aria-label` including the metric name and definition (for screen readers). Help text below shows the full metric definition.

## Auto-Calculated Metrics

### Model Change

Add `computation_type` field to `MetricDefinition`:

```python
computation_type = models.CharField(
    max_length=30, blank=True, default="",
    choices=[
        ("", "Manual entry"),
        ("session_count", "Sessions attended this month"),
    ],
)
```

Nullable/blank — all existing metrics default to manual entry (empty string).

### View Logic

In `note_create`, after building target forms:
- For each metric with a `computation_type`, compute the value
- `session_count`: count ProgressNote objects for this client in the current month
- Pass computed values to the template as a separate dict

### Template Rendering

Auto-calc metrics render as read-only text:
```html
<div class="auto-calc-metric">
    <span class="metric-label">Sessions this month</span>
    <span class="metric-value" aria-readonly="true">4</span>
    <small>(auto-calculated)</small>
</div>
```

Not a form input — the view saves computed values server-side on POST, preventing stale client-side values.

### Seed Update

Update `seeds/metric_library.json` to set `computation_type: "session_count"` on the "Sessions attended this month" metric.

## Accessibility

- **Form sections:** Each zone uses `<fieldset>`/`<legend>` or `role="group"` with `aria-labelledby`
- **Target cards:** `<fieldset>` with target name as `<legend>`
- **Compact/expanded cards:** `aria-expanded` on the toggle element, keyboard-operable (Enter/Space)
- **Scale pills:** `role="radiogroup"` with `aria-label` including metric definition
- **Auto-calc fields:** `aria-readonly="true"`, clearly labelled
- **Collapsible sections:** Native `<details>`/`<summary>` (built-in accessibility)
- **Colour:** Use `var(--kn-text)` not `var(--pico-color)` on all interactive elements (Pico CSS variable trap)
- **Focus management:** When a card expands, focus moves to the first new field

## Files to Modify

| File | Change |
|------|--------|
| `apps/plans/models.py` | Add `computation_type` field to `MetricDefinition` |
| `apps/notes/views.py` | Auto-calc logic, annotate metric forms with render type |
| `apps/notes/forms.py` | Scale detection in `MetricValueForm.__init__`, switch to RadioSelect |
| `templates/notes/note_form.html` | Complete restructure — 4 zones, compact cards, scale pills |
| `static/css/main.css` | Session grid, target cards, scale pills, compact/expand, auto-calc |
| `static/js/app.js` or inline | Card expand/collapse, "No change" button, general client-said field |
| `seeds/metric_library.json` | Add `computation_type` to session count metric |
| `locale/fr/LC_MESSAGES/django.po` | New translatable strings |
| `tests/test_notes.py` | Tests for auto-calc, scale rendering, new form behaviour |

## Implementation Phases

### Phase A: Layout + Field Widths (CSS + template only)
- Section form into 4 zones
- Constrain field widths (grid for setup, max-width for dropdowns/dates)
- Collapse Wrap-up and Participant Voice by default
- Reorder target card fields (pills before text)
- Update consent wording
- Add general "Client said" field

### Phase B: Scale Pills (form + template + CSS)
- Scale detection logic in `MetricValueForm`
- RadioSelect widget for scale metrics
- `.scale-pills` CSS extending descriptor pill pattern
- Accessibility markup (aria-label on radiogroup)

### Phase C: Compact Target Cards (template + CSS + JS)
- Compact/expanded card states
- "No change" shortcut button
- Card expand/collapse JS with aria-expanded
- Visual "done" indicator on completed cards

### Phase D: Auto-Calc Metrics (model + migration + view + template)
- `computation_type` field on MetricDefinition + migration
- Session count computation in view
- Read-only template rendering
- Seed data update

## Expert Panel

This design was developed through a multi-round expert panel (2026-02-19):

- **UX Form Design Specialist** — form layout, field sizing, progressive disclosure
- **Frontline Social Services Worker** — workflow, speed, common patterns
- **Accessibility Consultant** — WCAG 2.2 AA, keyboard nav, screen readers
- **Django Template Engineer** — practical implementation constraints
- **Burnt-Out Frontline Worker** — stress-tested for reluctant users, time pressure, and form fatigue

Key insight from the burnt-out worker: target cards should start compact (descriptor pills only) with a "No change" shortcut for the 60% of routine entries. This dramatically reduces perceived form length while keeping all fields available.
