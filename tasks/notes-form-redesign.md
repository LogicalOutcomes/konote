# UX-NOTES1: Redesign Detailed Notes Form

**Status:** Not started
**ID:** UX-NOTES1
**Owner:** GG

## Problem

The detailed progress notes form (`templates/notes/note_form.html`) is the most-used data entry screen, but it's poorly designed for daily use:

1. **Every field stretches full-width** — Pico CSS defaults all inputs to `width: 100%`. A date picker, a dropdown, and a textarea all get the same width. Fields should be sized to their expected input.
2. **Metrics are confusing text boxes** — "How are you feeling today?" (1-5) is a plain text input with tiny help text. Should be 5 clickable buttons.
3. **Auto-calculable data requires manual entry** — "Sessions attended this month" is a text box where staff must count and type a number. The system already has this data.
4. **Form is long and forbidding** — 11+ fields at the same visual hierarchy level with no grouping. Feels bureaucratic.
5. **Metrics buried at bottom of target accordions** — disconnected from the target they belong to.

## Expert Panel Synthesis

Three experts (UX Form Design, Frontline Social Services Worker, Accessibility Consultant) agreed on:

1. **Section the form** — Session Setup (compact grid), Targets (card-based), Wrap-up (lighter), Participant Voice (collapsible)
2. **Constrain field widths** — dropdowns 20-24rem, date pickers 12rem, textareas 100% of container
3. **Render 1-5 metrics as tappable scale pills** — reuse the progress descriptor pill pattern
4. **Auto-calculate computable metrics** — session count from note history, displayed read-only
5. **Reorder target cards** — quick inputs first (pills, scales), typing last (words, notes)
6. **Support rapid-fire workflow** — select targets, then flow through each: tap pill, tap scale, type sentence, next

## Implementation Summary

### Files to modify

| File | Change |
|---|---|
| `apps/plans/models.py` | Add `computation_type` field + `render_type` property to MetricDefinition |
| `apps/notes/views.py` | Auto-calc helpers, annotate metric forms with render type / scale choices |
| `templates/notes/note_form.html` | Complete redesign — sections, cards, scale pills, width constraints |
| `static/css/main.css` | Session grid, target cards, scale pills, auto-calc display, field widths |
| `seeds/metric_library.json` | Add `computation_type` to "Sessions attended this month" |
| `locale/fr/LC_MESSAGES/django.po` | New translatable strings |
| `tests/test_notes.py` | Tests for auto-calc, scale rendering, render_type property |

### New form layout

```
[Session Details — 3-col grid]
  Template (24rem) | Interaction type (20rem) | Date (12rem)

[Targets]
  Checkbox selector
  Target cards (each with: progress pills -> metrics -> text fields)

[Wrap-up — lighter styling]
  Summary | Engagement (20rem) | Follow-up (12rem)

[Participant Voice — collapsible]
  Reflection | Suggestion + priority
```

### Key design decisions

- **`computation_type` as explicit model field** (not name matching) — reliable across languages
- **Scale detection** — min/max both set, both integers, range <= 9 steps
- **Parse scale labels from definition text** — avoids schema change, falls back to bare numbers
- **No tabs/wizard** — preserves single-form submission and autosave
- **`:has()` CSS** — already used in existing descriptor pills, good browser support

Full plan: `.claude/plans/golden-kindling-token.md`
