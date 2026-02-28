# Design: Improved Targets & Metrics

**Date:** 2026-02-20
**Branch:** `feat/improve-targets-metrics`
**Evidence:** [docs/evidence-outcome-measurement.md](../evidence-outcome-measurement.md)

---

## Problem

KoNote's current universal metrics (Confidence, Progress, Wellbeing) are generic, unanchored self-report scales that violate established measurement principles. The AI goal builder produces SMART-formatted targets but doesn't enforce the full validation criteria from the research literature. The result: vague goals like "build confidence with English" pass through the system without being improved.

## Goals

1. Replace the three universal metrics with research-grounded constructs
2. Incorporate the 8-criteria validation table into the AI workflow
3. Add AI-generated target-specific metrics (optional Tier 2)
4. Create a public evidence page documenting the research basis
5. Enhance the `client_goal` field as the participant's vision of success

---

## Section 1: Universal Metrics Redesign

### What changes

Replace the three `is_universal=True` metrics in `seeds/metric_library.json`:

| Current metric | New metric | Key difference |
|---------------|------------|----------------|
| Confidence | **Self-Efficacy** | Domain-specific: "How sure do you feel about being able to [target behaviour]?" Pure certainty anchors, no support-level confound. |
| Progress | **Goal Progress** | Behaviourally anchored stages of change. Level 5 = "This is a regular part of my life now" (not "independently"). |
| Wellbeing | **Satisfaction** | Cleaner construct: "How satisfied are you with how things are going in this area?" Captures participant voice. |

### Metric definitions

**Goal Progress:**

```
1 = Haven't started working on this yet
2 = Exploring or learning about this
3 = Practising or trying this out
4 = Doing this regularly or consistently
5 = This is a regular part of my life now
```

French:
```
1 = Je n'ai pas encore commencé
2 = J'explore ou j'apprends
3 = Je pratique ou j'essaie
4 = Je fais cela régulièrement
5 = Cela fait partie de ma vie maintenant
```

**Self-Efficacy:**

Prompt: "How sure do you feel about being able to [target behaviour]?"

```
1 = Not at all sure I can do this
2 = A little sure — it feels hard
3 = Somewhat sure — I'm getting there
4 = Quite sure — I can usually do this
5 = Very sure — I know I can do this
```

French prompt: "À quel point êtes-vous sûr(e) de pouvoir [target behaviour]?"

```
1 = Pas du tout sûr(e) de pouvoir le faire
2 = Un peu sûr(e) — c'est difficile
3 = Assez sûr(e) — j'y arrive
4 = Plutôt sûr(e) — j'y arrive d'habitude
5 = Très sûr(e) — je sais que je peux
```

**Satisfaction:**

```
1 = Very unsatisfied
2 = Unsatisfied
3 = Neutral — it's okay
4 = Satisfied
5 = Very satisfied
```

French:
```
1 = Très insatisfait(e)
2 = Insatisfait(e)
3 = Neutre — ça va
4 = Satisfait(e)
5 = Très satisfait(e)
```

### Files to change

- `seeds/metric_library.json` — update the three `is_universal: true` entries
- `apps/plans/management/commands/seed_metrics.py` — no structural change, just re-run after seed update
- Templates showing universal metric cards — `templates/plans/goal_form.html` (universal cards section)
- `templates/notes/note_form.html` — if metric names are displayed during recording

### No model changes needed

The `MetricDefinition` model already supports everything: `name`, `name_fr`, `definition`, `definition_fr`, `min_value`, `max_value`, `unit`, `is_universal`. This is purely a data/content update.

---

## Section 2: AI Workflow — Target Validation Criteria

### What changes

Update the system prompts in `konote/ai.py` to enforce the 8-criteria validation table when generating or improving targets.

### Functions to update

**`suggest_target()`** — Add the 8 criteria to the system prompt. The AI must check each criterion and include all eight in the generated SMART description. Current prompt says "SMART outcome statement" — new prompt will enumerate the specific criteria.

**`build_goal_chat()`** — Same criteria added to the conversational goal builder. The AI should ask about missing criteria during the conversation (e.g., "What timeframe are you thinking?" if no time-bound element is present).

**`improve_outcome()`** — Currently just rewrites as SMART. Update to validate against all 8 criteria and flag which are missing.

### The 8 criteria (added to all three prompts)

```
VALIDATION CRITERIA — every target must satisfy all eight:
1. Observable behaviour (Mager): uses an action verb you can see or hear
2. Specific (Locke & Latham): two people would agree on whether achieved
3. Measurable indicator (Bandura, GAS): has a scale, score, count, or threshold
4. Conditions stated (Mager): specifies circumstances — with or without support
5. Success threshold (Mager, SMART): defines what level counts as "met"
6. Time-bound (Doran): specifies a deadline or review date
7. Causally linked (Weiss): achieving this plausibly leads to the participant's larger goal
8. Participant-meaningful (GAS, Outcome Star): defined with the participant, matters to them
```

### No new API endpoints

This is a prompt content change only. No new views, URLs, or forms.

---

## Section 3: AI-Generated Target-Specific Metrics (Tier 2)

### What changes

When the AI generates a target suggestion (via `suggest_target()` or `build_goal_chat()`), it also generates a **target-specific metric** with 5 behaviourally anchored levels specific to that target. This is a simplified Goal Attainment Scale.

### How it works

The AI returns a `custom_metric` object in its response:

```json
{
  "name": "Cooking independence",
  "definition": "1 = Haven't tried cooking yet\n2 = Have watched someone cook or looked at recipes\n3 = Have cooked a simple meal with help\n4 = Cook a few meals per week on my own\n5 = Plan and cook healthy meals for the week independently",
  "min_value": 1,
  "max_value": 5,
  "unit": "score"
}
```

The coach can:
- **Accept** — metric is created as a `MetricDefinition` with `is_library=False` and assigned to the target
- **Edit** — modify the levels before accepting
- **Decline** — skip the target-specific metric; the three universals are always present

### Prompt changes

Add to `suggest_target()` and `build_goal_chat()`:

```
TARGET-SPECIFIC METRIC:
In addition to suggesting existing metrics from the catalogue, generate ONE
custom metric specific to this target. This metric should:
- Use a 1–5 scale with behaviourally anchored levels
- Each level describes an observable state or action, not a feeling
- Level 1 = not started, Level 5 = sustained mastery
- Be specific to THIS target (not generic)
- Use plain language the participant would understand
```

### UI changes

- `templates/plans/_ai_suggestion.html` — add a "Suggested metric" card showing the 5 levels, with Accept/Edit/Decline buttons
- `templates/plans/_goal_builder.html` — show the custom metric in the draft card with editable levels
- `templates/plans/goal_form.html` — if a custom metric is accepted, include it in the form submission alongside universal metrics

### Backend changes

- `konote/ai.py` — update `suggest_target()` and `build_goal_chat()` response format to include `custom_metric`
- `konote/ai.py` — update validation functions to validate the custom metric structure
- `apps/plans/views.py` — `goal_builder_save` already handles creating custom metrics (it creates `MetricDefinition` with `is_library=False`). Extend `_create_goal()` to also accept custom metrics from the `suggest_target` path.
- `konote/forms.py` — `GoalBuilderSaveForm` already has `metric_name`, `metric_definition`, etc. May need to add these to `GoalForm` or create a separate flow.

---

## Section 4: Self-Efficacy Domain Reference

### What changes

The Self-Efficacy metric prompt includes "[target behaviour]" — this needs to be dynamically populated. When a metric value is recorded in a progress note, the Self-Efficacy question should read: "How sure do you feel about being able to **cook a healthy meal**?" — not the generic "How sure do you feel about being able to do this?"

### Implementation

The `MetricValue` is recorded in the context of a `ProgressNoteTarget`, which links to a `PlanTarget`, which has a `name` field. The template can insert the target name into the Self-Efficacy prompt.

In the notes form template, when rendering the Self-Efficacy metric:

```html
{% if metric.name == "Self-Efficacy" %}
  <label>How sure do you feel about being able to {{ target.name|lower }}?</label>
{% else %}
  <label>{{ metric.definition }}</label>
{% endif %}
```

This is a template-only change. No model changes needed.

---

## Section 5: `client_goal` Field Enhancement

### What changes

Make the `client_goal` field more prominent in both the goal creation flow and the participant portal. This field serves as the participant's own definition of success — the qualitative anchor that makes the quantitative metrics meaningful.

### UI changes

- **Goal creation form** — Relabel from "In their words" to "What success looks like to you" or "The participant's own words." Move it visually above the SMART description so the participant's voice comes first.
- **AI suggestion card** — Show `client_goal` prominently, labelled "In their words."
- **Plan view** — Show `client_goal` on the target card, not hidden behind an expand.
- **Portal** — If the participant portal shows targets, display `client_goal` as the primary text.

### No model changes

The `PlanTarget.client_goal` field already exists as an encrypted property. This is a template/display change only.

---

## Section 6: Evidence Page

### Status: DONE

Created at `docs/evidence-outcome-measurement.md`. Covers:
- Goal-setting theory (Locke & Latham)
- SMART goals (Doran) and behavioural objectives (Mager)
- Self-report validity (PROMIS, pain measurement literature)
- Self-efficacy theory (Bandura)
- Goal Attainment Scaling (Kiresuk & Sherman)
- Three-dimension factor analysis (Wilson & Cleary, Recovery Star, WHOQOL-BREF)
- Practical tools (Outcome Star, Dewson, Friedman, Weiss, CLB)
- Design decisions table with rationale
- Full metric definitions with bilingual descriptions

Will be converted to an HTML page at `/about/evidence/` in a later phase (website integration).

---

## Section 7: Translations

All new metric definitions include French translations. After implementation:
1. Run `python manage.py translate_strings`
2. Verify/update any new template strings in `locale/fr/LC_MESSAGES/django.po`
3. Run `python manage.py translate_strings` again to compile
4. Commit both `.po` and `.mo` files

---

## Section 8: Testing

### Tests to update

- `tests/test_plans.py` — update any tests that reference "Confidence", "Progress", or "Wellbeing" by name. Replace with "Self-Efficacy", "Goal Progress", "Satisfaction".
- `tests/test_plans.py` — add test for target-specific metric creation via AI suggestion flow.
- AI-related tests (if any) — update expected prompt content.

### Tests to add

- Test that all three universal metrics are always assigned to new targets created via the goal form.
- Test that a target-specific metric can be created, edited, and declined.
- Test that Self-Efficacy prompt includes target name in notes form context.

---

## What's NOT in scope

- **Production data migration** — KoNote is pre-launch. No migration path needed yet. (Document the pattern for future reference.)
- **Evidence page as HTML** — stays as markdown for now. Website integration is a separate task.
- **Metric library admin changes** — the admin/PM metric library UI doesn't change. Custom metrics created by the AI appear in the library with `is_library=False`.
- **Report template changes** — aggregate reports already work with 1–5 scores. The metric names change but the data format doesn't.
- **"Anything different?" prompt for stable metrics** — deferred to a future UX improvement. The notes form continues to show all metrics each time for now.

---

## Summary of changes by file

| File | Change type | Description |
|------|------------|-------------|
| `seeds/metric_library.json` | Data | Replace 3 universal metric definitions |
| `konote/ai.py` | Prompt content | Add 8 criteria to suggest_target, build_goal_chat, improve_outcome. Add custom_metric generation. |
| `konote/ai.py` | Validation | Update response validators for custom_metric field |
| `templates/plans/goal_form.html` | Template | Update universal metric card labels/descriptions |
| `templates/plans/_ai_suggestion.html` | Template | Add target-specific metric card |
| `templates/plans/_goal_builder.html` | Template | Show custom metric in draft card |
| `templates/notes/note_form.html` | Template | Domain-specific Self-Efficacy prompt |
| `templates/plans/_target.html` | Template | Show client_goal more prominently |
| `apps/plans/views.py` | View logic | Extend _create_goal for custom metrics from suggest_target path |
| `konote/forms.py` | Form | Possibly extend GoalForm for custom metric fields |
| `locale/fr/LC_MESSAGES/django.po` | Translation | New/updated French strings |
| `tests/test_plans.py` | Tests | Update metric name references, add new tests |
| `docs/evidence-outcome-measurement.md` | Docs | Already done |
