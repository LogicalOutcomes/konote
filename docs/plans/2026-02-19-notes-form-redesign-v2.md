# Detailed Notes Form — Round 2 Redesign

**Date:** 2026-02-19
**Status:** Design — expert-reviewed
**Supersedes:** `2026-02-19-notes-form-redesign.md` (Round 1, implemented)
**Task ID:** UX-NOTES2

## Practice Model

KoNote implements **Feedback-Informed Treatment (FIT)** — an evidence-based approach where the participant is asked for structured input at every session. Outcome data comes from two parallel streams:

1. **Participant voice** — what the participant reports about their own experience
2. **Staff observations** — what the worker sees (engagement, progress, case notes)

These are equally weighted. The participant's self-report is often more predictive of outcomes than staff observation. **The form must give equal visual prominence to both perspectives.**

## Problems (Round 1 remaining issues)

| # | Issue | Root Cause |
|---|-------|-----------|
| 1 | Unreadable text below target header | Contrast issue with `<small class="secondary">` |
| 2 | "Sessions attended this month (sessions)" nonsensical | Auto-calc metric label poorly worded, styled like form field |
| 3 | Form too spread out, important fields hidden | `<details>` hides Participant Voice — staff never open it |
| 4 | Scale metrics (1–5) render as text input, not pills | `MetricDefinition` likely missing `min_value`/`max_value` in DB |
| 5 | Follow-up chips stack vertically | Narrow column in 2-column grid |
| 6 | Consent checkbox — remove | Adds friction, original intent unclear |
| 7 | Engagement is a dropdown with "----------" | Poor UX for 6 qualitative choices |

## Design: FIT-Aligned Single Flow

### Form Flow (5 sections)

```
1. WHAT HAPPENED         Session Setup (3-column grid)
                         Target Selection (checkboxes)

2. HOW DID IT GO         Target Cards (per target):
   (per target)            - Progress descriptors (pills)
                           - Metrics (pills for scales, badge for auto-calc)
                           - "What did they say about this?" (text input)
                           - "Your notes" (textarea)

3. THE SESSION OVERALL   Two-lens layout:
   (two perspectives)     Left: "Their perspective"
                            - "How did they feel about today's session?"
                            - "Anything they'd change about the program?"
                            - Priority (if suggestion filled)
                          Right: "Your observations"
                            - Engagement (pill buttons)
                            - Session notes (optional textarea)

4. WHAT'S NEXT           Follow-up chips (horizontal row)
                          Tomorrow | 3 days | This week | Next week |
                          2 weeks | Pick date

5. SAVE                  Footer: ✓ 2/3 targets  [Cancel] [Save Note]
```

### Section 1: Session Setup — no changes

3-column grid: Template, Interaction Type, Session Date. Works well.

### Section 2: Target Selection — no changes

Checkbox list. Works well.

### Section 3: Target Cards — fixes

**Header:** Ensure contrast — `<small class="secondary">` uses `var(--kn-text-muted)`.

**Auto-calc metrics:** Read-only inline badge, not a form field:
- Format: `Sessions this month: 4 (auto-calculated)`
- No input border, no focus state

**Scale metrics:** Must render as pill buttons. Fix metric definitions in DB if `min_value`/`max_value` are missing.

**Per-target participant voice:** Rename label from "In their words" to **"What did they say about this?"** — prompts verbatim capture of topic-specific feedback.

**"No change" collapse:** When clicked, card collapses to a single-line strip:
```
✓ Find stable housing — No change
```
Form physically shrinks as staff work through targets (progress reward).

### Section 4: The Session Overall — major redesign

**Replace both "Wrap-up" and "Participant Voice" zones** with a single two-column section.

```
┌─── The session overall ──────────────────────────────────┐
│                                                          │
│  Their perspective          │  Your observations         │
│  ────────────────           │  ─────────────────         │
│                             │                            │
│  How did they feel about    │  Engagement:               │
│  today's session?           │  ○ Not participating       │
│  [________________________] │  ○ Going through motions   │
│                             │  ○ Guarded                 │
│  Anything they'd change     │  ● Engaged                 │
│  about the program?         │  ○ Fully invested          │
│  [________________________] │  ○ No 1-on-1               │
│                             │  Your observation, not a   │
│                             │  score.                    │
│  Priority: [if filled]      │                            │
│                             │  Session notes (optional)  │
│                             │  [______________________]  │
└──────────────────────────────────────────────────────────┘
```

**Design rationale:**
- FIT methodology made visible in the UI — two parallel data streams side by side
- "Their perspective" on the left (primary in FIT) with light blue background (`--kn-primary-subtle`)
- "Your observations" on the right with neutral background
- Neither side is hidden or de-emphasised — both are equally prominent
- Summary absorbed into "Your observations" as "Session notes (optional)"

**Engagement labels (revised for behavioural language):**
- Not participating
- Going through motions
- Guarded
- Engaged
- Fully invested
- No 1-on-1

**Engagement widget:** Pill buttons (`.engagement-pills`), same pattern as `.descriptor-pills`.

**Responsive:**
- Desktop (≥900px): Two equal columns side by side
- Tablet (600–899px): Stack vertically, participant first, thin separator
- Mobile (<600px): Stack vertically, participant first

**DOM order:** "Their perspective" comes first — matches both visual order and FIT priority.

### Section 5: Follow-up — standalone row

Horizontal chip row below "The session overall":
- Tomorrow | 3 days | This week | Next week | 2 weeks | Pick date
- Helper: "(optional — adds to your home page reminders)"

New: "This week" chip added (common real-world follow-up interval).

### Section 6: Sticky Footer — simplified

**Remove consent checkbox.** New layout:

```
✓ 2 of 3 targets                    [Cancel] [Save Note]
```

- Completeness indicator on left: `✓ 2 of 3 targets` (updates live via JS)
- Autosave indicator in middle
- Cancel + Save on right

## Files to Change

| File | Changes |
|------|---------|
| `templates/notes/note_form.html` | Remove `<details>`, two-lens layout, remove consent, "No change" collapse markup |
| `static/css/main.css` | `.session-overall` two-column, `.engagement-pills`, single-line "done" strip, completeness indicator |
| `apps/notes/forms.py` | Remove `consent_confirmed`, engagement as RadioSelect with pill widget |
| `apps/notes/views.py` | Remove consent validation |
| `static/js/app.js` | "No change" single-line collapse, completeness counter, auto-update |
| `static/js/followup-picker.js` | Add "This week" chip |
| `locale/fr/LC_MESSAGES/django.po` | New/changed strings |

## Data Fix

Verify all scale metrics (1–5, 1–10) in `MetricDefinition` have `min_value` and `max_value` set. Add data migration or management command to fix existing records.

## Accessibility

- Two-lens section: `<fieldset>` with `<legend>`, `<h3>` subheadings for each column
- Engagement pills: `role="radiogroup"` with `aria-label`, hidden radio inputs, `:has(:checked)`
- Keyboard: arrow keys within pill groups, Tab between sections
- "Their perspective" first in DOM order (also first for screen readers)
- Auto-calc badge: `aria-label="Sessions this month: 4, auto-calculated"`
- Colour contrast: WCAG 2.2 AA on all text including muted styles
- Use `var(--kn-text)` not `var(--pico-color)` on interactive elements
- Focus indicators on all interactive elements, 44px minimum touch targets

## Expert Panel (reconvened)

Design reviewed by 5-member panel on 2026-02-19:
- **Outcome-Based Practice Specialist** — identified FIT alignment as core design constraint
- **UX Form Design Specialist** — proposed two-lens layout mapping to FIT data streams
- **Frontline Case Manager** — validated workflow, suggested label improvements
- **Accessibility Consultant** — DOM order, column semantics, breakpoints
- **Information Architect** — corrected visual hierarchy to reflect practice model

Key insight: Participant voice is not optional in FIT — it's the primary data source. The form must make this visible in its structure, not just in its labels.
