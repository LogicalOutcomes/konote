# Targets & Metrics Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace three generic universal metrics (Confidence, Progress, Wellbeing) with research-grounded constructs (Goal Progress, Self-Efficacy, Satisfaction), incorporate 8-criteria validation into AI prompts, and add AI-generated target-specific metrics.

**Architecture:** Data-layer changes (seed JSON + re-seed), AI prompt content updates (no new endpoints), template display updates, and test updates. No model changes. No new database migrations.

**Tech Stack:** Django 5, Python 3.12, HTMX, Pico CSS. AI via OpenRouter (Claude Sonnet).

**Design doc:** `docs/plans/2026-02-20-targets-metrics-redesign.md`
**Evidence:** `docs/evidence-outcome-measurement.md`

---

## Task 1: Update Universal Metric Seed Data

**Files:**
- Modify: `seeds/metric_library.json` (lines 398–434 — the three `is_universal: true` entries)
- Modify: `apps/admin_settings/management/commands/seed.py` (lines 47–92 — `_seed_metrics` method)

**Step 1: Update the three universal metrics in seed JSON**

In `seeds/metric_library.json`, replace the three `is_universal: true` entries. Find the entry with `"name": "Confidence"` (around line 400) and replace all three entries (Confidence, Progress, Wellbeing) with:

```json
  {
    "name": "Goal Progress",
    "name_fr": "Progrès vers l'objectif",
    "definition": "What are you doing toward this goal? 1 = Haven't started working on this yet, 2 = Exploring or learning about this, 3 = Practising or trying this out, 4 = Doing this regularly or consistently, 5 = This is a regular part of my life now.",
    "definition_fr": "Que faites-vous pour atteindre cet objectif? 1 = Je n'ai pas encore commencé, 2 = J'explore ou j'apprends, 3 = Je pratique ou j'essaie, 4 = Je fais cela régulièrement, 5 = Cela fait partie de ma vie maintenant.",
    "category": "general",
    "min_value": 1,
    "max_value": 5,
    "unit": "score",
    "unit_fr": "pointage",
    "is_universal": true
  },
  {
    "name": "Self-Efficacy",
    "name_fr": "Auto-efficacité",
    "definition": "How sure do you feel about being able to do this? 1 = Not at all sure I can do this, 2 = A little sure — it feels hard, 3 = Somewhat sure — I'm getting there, 4 = Quite sure — I can usually do this, 5 = Very sure — I know I can do this.",
    "definition_fr": "À quel point êtes-vous sûr(e) de pouvoir le faire? 1 = Pas du tout sûr(e), 2 = Un peu sûr(e) — c'est difficile, 3 = Assez sûr(e) — j'y arrive, 4 = Plutôt sûr(e) — j'y arrive d'habitude, 5 = Très sûr(e) — je sais que je peux.",
    "category": "general",
    "min_value": 1,
    "max_value": 5,
    "unit": "score",
    "unit_fr": "pointage",
    "is_universal": true
  },
  {
    "name": "Satisfaction",
    "name_fr": "Satisfaction",
    "definition": "How satisfied are you with how things are going in this area? 1 = Very unsatisfied, 2 = Unsatisfied, 3 = Neutral — it's okay, 4 = Satisfied, 5 = Very satisfied.",
    "definition_fr": "À quel point êtes-vous satisfait(e) de la façon dont les choses se passent dans ce domaine? 1 = Très insatisfait(e), 2 = Insatisfait(e), 3 = Neutre — ça va, 4 = Satisfait(e), 5 = Très satisfait(e).",
    "category": "general",
    "min_value": 1,
    "max_value": 5,
    "unit": "score",
    "unit_fr": "pointage",
    "is_universal": true
  }
```

**Step 2: Update `_seed_metrics` to handle renames**

The current `_seed_metrics` uses `get_or_create` keyed on `name`. Since we're renaming metrics, the old names won't match the new ones. We need to:
1. Remove `is_universal` from the old metrics (Confidence, Progress, Wellbeing) if they exist
2. Create the new ones

Add this block at the end of `_seed_metrics()` in `seed.py`, before the final `self.stdout.write(msg)` line:

```python
        # ── Retire old universal metrics replaced by research-grounded versions ──
        old_universals = ["Confidence", "Progress", "Wellbeing"]
        retired = MetricDefinition.objects.filter(
            name__in=old_universals, is_universal=True
        ).update(is_universal=False)
        if retired:
            msg += f" {retired} old universal metric(s) retired."
```

**Step 3: Run seed command to verify**

Run: `python manage.py seed --metrics-only` (or whatever flag limits to metrics seeding)

If there's no `--metrics-only` flag, check `seed.py` for the available options and run accordingly. Verify the output shows 3 created + old universals retired.

**Step 4: Commit**

```bash
git add seeds/metric_library.json apps/admin_settings/management/commands/seed.py
git commit -m "feat: replace universal metrics with research-grounded constructs

Replace Confidence/Progress/Wellbeing with Goal Progress/Self-Efficacy/
Satisfaction. Behaviourally anchored stages, domain-specific efficacy,
and participant satisfaction. See docs/evidence-outcome-measurement.md."
```

---

## Task 2: Update AI Prompt — `suggest_target()`

**Files:**
- Modify: `konote/ai.py` (lines 131–224 — `suggest_target` function)

**Step 1: Write a test for the updated prompt content**

In `tests/test_ai.py` (or create if it doesn't exist), add a test that verifies the system prompt includes the validation criteria. Since the AI module calls an external API, we mock the HTTP call.

```python
from unittest.mock import patch, MagicMock
import json

def test_suggest_target_prompt_includes_validation_criteria():
    """The suggest_target prompt should include all 8 validation criteria."""
    with patch("konote.ai._call_openrouter") as mock_call:
        mock_call.return_value = json.dumps({
            "name": "Test",
            "description": "Test description",
            "client_goal": "Test goal",
            "suggested_section": "Test",
            "metrics": [],
            "custom_metric": None,
        })
        from konote.ai import suggest_target
        suggest_target("test words", "Test Program", [], [])

        # Check the system prompt (first arg to _call_openrouter)
        system_prompt = mock_call.call_args[0][0]
        assert "Observable behaviour" in system_prompt
        assert "Time-bound" in system_prompt
        assert "Causally linked" in system_prompt
        assert "Participant-meaningful" in system_prompt
        assert "custom_metric" in system_prompt.lower() or "target-specific metric" in system_prompt.lower()
```

Run: `pytest tests/test_ai.py::test_suggest_target_prompt_includes_validation_criteria -v`
Expected: FAIL (criteria not in prompt yet)

**Step 2: Update the `suggest_target` system prompt**

In `konote/ai.py`, replace the `system` string in `suggest_target()` (lines 146–204). The new prompt adds the 8-criteria validation and requests a `custom_metric` in the response:

```python
    system = (
        "You are a goal-setting assistant for a Canadian nonprofit. "
        "A caseworker has written down what a participant wants to work on, "
        "in the participant's own words. Turn this into a structured, "
        "measurable target.\n\n"
        "LANGUAGE PRINCIPLES:\n"
        "- Use strengths-based, positive language: 'Build social connections' "
        "not 'Reduce isolation'\n"
        "- The participant will see this target. Write the description "
        "in plain language they would recognise as their own goal.\n"
        "- Honour the participant's intent — if they say 'make friends "
        "outside this group', don't reframe it as a program engagement goal. "
        "Keep their voice and direction.\n"
        "- Use Canadian English spelling (colour, centre, behaviour).\n\n"
        "VALIDATION CRITERIA — every target must satisfy ALL EIGHT:\n"
        "1. Observable behaviour (Mager): uses an action verb you can see or hear\n"
        "2. Specific (Locke & Latham): two people would agree on whether achieved\n"
        "3. Measurable indicator (Bandura, GAS): has a scale, score, count, or threshold\n"
        "4. Conditions stated (Mager): specifies circumstances — with or without support\n"
        "5. Success threshold (Mager, SMART): defines what level counts as 'met'\n"
        "6. Time-bound (Doran): specifies a deadline or review date\n"
        "7. Causally linked (Weiss): achieving this plausibly leads to the participant's larger goal\n"
        "8. Participant-meaningful (GAS, Outcome Star): defined with the participant, matters to them\n\n"
        "METRIC SELECTION — this is critical:\n"
        "- Do NOT keyword-match. A metric about 'the group' does NOT fit a "
        "goal about life OUTSIDE the group.\n"
        "- For each candidate metric, ask: 'Does tracking this metric actually "
        "measure progress toward what the PARTICIPANT described?' If the answer "
        "is no, do not include it.\n"
        "- It is better to suggest 0 metrics than to suggest misaligned ones. "
        "An empty metrics array is a valid response.\n"
        "- Prefer metrics that measure the participant's own actions or "
        "experiences, not program attendance or generic wellbeing.\n\n"
        "TARGET-SPECIFIC METRIC:\n"
        "In addition to suggesting existing metrics from the catalogue, generate ONE "
        "custom metric specific to this target. This metric should:\n"
        "- Use a 1–5 scale with behaviourally anchored levels\n"
        "- Each level describes an observable state or action, not a feeling\n"
        "- Level 1 = not started or lowest level, Level 5 = sustained mastery or highest level\n"
        "- Be specific to THIS target (not generic)\n"
        "- Use plain language the participant would understand\n"
        "- Format the definition as: '1 = descriptor\\n2 = descriptor\\n...\\n5 = descriptor'\n\n"
        "SECTION SELECTION:\n"
        "- Match the section to the participant's life goal, not just the "
        "program structure.\n"
        "- You MUST provide a section. Only pick an existing section if it genuinely fits. Otherwise "
        "suggest a new section name that reflects the participant's goal.\n\n"
        "REQUIREMENTS:\n"
        "- name: A concise target name (under 80 characters)\n"
        "- description: An outcome statement satisfying all 8 validation criteria above, "
        "written in plain language the participant would understand\n"
        "- client_goal: The participant's own words, preserved closely\n"
        "- suggested_section: You MUST provide a section. Pick from existing or suggest new.\n"
        "- metrics: 0–3 existing metrics from the catalogue that truly "
        "measure progress toward the participant's stated goal. Each with "
        "metric_id, name, and a one-sentence reason. Empty array is fine.\n"
        "- custom_metric: ONE target-specific metric as described above.\n\n"
        f"PROGRAM: {program_name}\n\n"
        f"EXISTING PLAN SECTIONS: "
        f"{json.dumps(existing_sections) if existing_sections else 'None yet — suggest a new section name.'}\n\n"
        f"AVAILABLE METRICS:\n"
        f"{json.dumps(metric_catalogue, indent=2) if metric_catalogue else 'No metrics available.'}\n\n"
        "RESPONSE FORMAT — return ONLY a JSON object:\n"
        "{\n"
        '  "name": "Concise target name",\n'
        '  "description": "Outcome statement satisfying all 8 criteria",\n'
        '  "client_goal": "Participant\'s own words, preserved closely",\n'
        '  "suggested_section": "Section name",\n'
        '  "metrics": [\n'
        '    {"metric_id": <int>, "name": "Metric name", '
        '"reason": "Why this metric fits"}\n'
        "  ],\n"
        '  "custom_metric": {\n'
        '    "name": "Target-specific metric name",\n'
        '    "definition": "1 = Level 1\\n2 = Level 2\\n3 = Level 3\\n4 = Level 4\\n5 = Level 5",\n'
        '    "min_value": 1,\n'
        '    "max_value": 5,\n'
        '    "unit": "score"\n'
        "  }\n"
        "}\n\n"
        "Return ONLY the JSON object, no other text."
    )
```

**Step 3: Update `_validate_suggest_target_response` to handle `custom_metric`**

Add validation for the new `custom_metric` field at the end of `_validate_suggest_target_response()` (after the metrics validation, around line 263):

```python
    # Validate custom_metric if present
    cm = response.get("custom_metric")
    if isinstance(cm, dict):
        if not isinstance(cm.get("name"), str) or not cm["name"].strip():
            response["custom_metric"] = None
        elif not isinstance(cm.get("definition"), str) or not cm["definition"].strip():
            response["custom_metric"] = None
        else:
            if not isinstance(cm.get("min_value"), (int, float)):
                cm["min_value"] = 1
            if not isinstance(cm.get("max_value"), (int, float)):
                cm["max_value"] = 5
            if not isinstance(cm.get("unit"), str):
                cm["unit"] = "score"
    else:
        response["custom_metric"] = None
```

**Step 4: Run the test**

Run: `pytest tests/test_ai.py::test_suggest_target_prompt_includes_validation_criteria -v`
Expected: PASS

**Step 5: Commit**

```bash
git add konote/ai.py tests/test_ai.py
git commit -m "feat: add 8-criteria validation and custom_metric to suggest_target

AI prompt now enforces observable behaviour, specificity, measurability,
conditions, threshold, timeframe, causal link, and participant meaning.
Response includes an AI-generated target-specific metric."
```

---

## Task 3: Update AI Prompt — `build_goal_chat()`

**Files:**
- Modify: `konote/ai.py` (lines 577–676 — `build_goal_chat` function)

**Step 1: Update the system prompt**

Replace the `system` string in `build_goal_chat()`. The key additions are: the 8-criteria validation, requesting a `custom_metric` in the draft, and the softer self-efficacy framing. The full updated prompt:

```python
    system = (
        "You are a goal-setting facilitator for a Canadian nonprofit. "
        "A caseworker (and possibly the participant they work with) is defining "
        "a new goal for the participant's plan. Guide them through a conversation "
        "to create a well-structured, measurable goal.\n\n"
        "YOUR ROLE:\n"
        "- Ask clarifying questions to understand what the participant wants to achieve\n"
        "- After 1–2 rounds of questions, present a structured draft goal\n"
        "- Refine the draft based on feedback until the worker is satisfied\n"
        "- Use warm, professional language — you may be read aloud to participants\n"
        "- Use Canadian English spelling (colour, centre, programme is NOT used)\n\n"
        "LANGUAGE PRINCIPLES:\n"
        "- Use strengths-based, positive language: 'Build social connections' not 'Reduce isolation'\n"
        "- The participant will see this goal on their portal. Write the description "
        "in plain language they would recognise as their own goal.\n"
        "- Honour the participant's intent — if they say 'make a friend outside this group', "
        "don't reframe it as a clinical program outcome. Keep their voice.\n"
        "- The client_goal field should preserve their actual words as closely as possible.\n\n"
        "VALIDATION CRITERIA — the description must satisfy ALL EIGHT:\n"
        "1. Observable behaviour (Mager): uses an action verb you can see or hear\n"
        "2. Specific (Locke & Latham): two people would agree on whether achieved\n"
        "3. Measurable indicator (Bandura, GAS): has a scale, score, count, or threshold\n"
        "4. Conditions stated (Mager): specifies circumstances — with or without support\n"
        "5. Success threshold (Mager, SMART): defines what level counts as 'met'\n"
        "6. Time-bound (Doran): specifies a deadline or review date\n"
        "7. Causally linked (Weiss): achieving this plausibly leads to the participant's larger goal\n"
        "8. Participant-meaningful (GAS, Outcome Star): defined with the participant, matters to them\n"
        "If any criteria are missing, ask the caseworker about them during the conversation.\n\n"
        "TECHNICAL REQUIREMENTS — every goal must have:\n"
        "- A concise target name (under 80 characters)\n"
        "- A description satisfying all 8 validation criteria, in plain language\n"
        "- The participant's own words — how they would describe this goal themselves\n"
        "- A measurable metric on a 1–5 scale with clear descriptors for each level\n"
        "- A suggested plan section (from existing sections, or a new one)\n\n"
        "METRIC RULES:\n"
        "- Check the provided metric catalogue FIRST. If an existing metric fits well, "
        "use it (set existing_metric_id to its id).\n"
        "- Only suggest a custom metric when no existing one is a good match.\n"
        "- Custom metrics MUST have a 1–5 scale with behaviourally anchored descriptors — "
        "each level should describe an observable state or action, not a feeling "
        "(e.g., '1 = Haven\\'t thought about how to meet people\\n"
        "2 = Have ideas but haven\\'t tried\\n"
        "3 = Have tried reaching out to someone\\n"
        "4 = Have a regular social contact outside the program\\n"
        "5 = Have a friend I can call to do things together').\n"
        "- The metric must produce meaningful data when tracked over time in progress notes.\n\n"
        f"PROGRAM: {program_name}\n\n"
        f"EXISTING PLAN SECTIONS: {json.dumps(existing_sections) if existing_sections else 'None yet — suggest a new section name.'}\n\n"
        f"AVAILABLE METRICS:\n{json.dumps(metric_catalogue, indent=2) if metric_catalogue else 'No metrics in the library yet.'}\n\n"
        "RESPONSE FORMAT — always return a JSON object:\n"
        "{\n"
        '  "message": "Your conversational response to the worker/participant",\n'
        '  "questions": ["Optional clarifying questions — omit if presenting a draft"],\n'
        '  "draft": null or {\n'
        '    "name": "Concise target name",\n'
        '    "description": "Outcome statement satisfying all 8 criteria",\n'
        '    "client_goal": "How the participant would say it in their own words",\n'
        '    "metric": {\n'
        '      "existing_metric_id": null or integer,\n'
        '      "name": "Metric name",\n'
        '      "definition": "1 = Level 1 descriptor\\n2 = Level 2\\n3 = Level 3\\n4 = Level 4\\n5 = Level 5",\n'
        '      "min_value": 1,\n'
        '      "max_value": 5,\n'
        '      "unit": "score"\n'
        "    },\n"
        '    "suggested_section": "Section name"\n'
        "  }\n"
        "}\n\n"
        "Return ONLY the JSON object, no other text. "
        "Include a draft as soon as you have enough information (usually after 1–2 exchanges). "
        "Update the draft each time the worker provides feedback."
    )
```

**Step 2: Run related tests**

Run: `pytest tests/test_plan_crud.py -v -k "goal"` to make sure nothing is broken.
Expected: All existing tests PASS (the prompt change doesn't affect test fixtures).

**Step 3: Commit**

```bash
git add konote/ai.py
git commit -m "feat: add 8-criteria validation to goal builder chat prompt

Goal builder now asks about missing criteria during conversation and
produces descriptions satisfying all 8 research-based validation criteria."
```

---

## Task 4: Update AI Prompt — `improve_outcome()`

**Files:**
- Modify: `konote/ai.py` (lines 112–128 — `improve_outcome` function)

**Step 1: Update the system prompt**

Replace the `system` string:

```python
    system = (
        "You help nonprofit workers write clear, measurable outcome statements. "
        "Rewrite the draft to satisfy these eight criteria:\n"
        "1. Observable behaviour: uses an action verb you can see or hear\n"
        "2. Specific: two people would agree on whether achieved\n"
        "3. Measurable indicator: has a scale, score, count, or threshold\n"
        "4. Conditions stated: specifies circumstances — with or without support\n"
        "5. Success threshold: defines what level counts as 'met'\n"
        "6. Time-bound: specifies a deadline or review date\n"
        "7. Causally linked: achieving this leads to a larger goal\n"
        "8. Participant-meaningful: the participant would recognise this as their goal\n\n"
        "Use Canadian English spelling (colour, centre). "
        "Write in plain language. "
        "Return only the improved text, no explanation."
    )
```

**Step 2: Commit**

```bash
git add konote/ai.py
git commit -m "feat: add 8-criteria validation to improve_outcome prompt"
```

---

## Task 5: Handle Custom Metric in `suggest_target_view`

**Files:**
- Modify: `konote/ai_views.py` (lines 207–282 — `suggest_target_view`)
- Modify: `templates/plans/_ai_suggestion.html`

**Step 1: Pass custom_metric through to the template**

In `suggest_target_view`, the `result` dict from `ai.suggest_target()` now includes a `custom_metric` key. The `suggestion_json = json.dumps(result)` already serialises it. The template just needs to display it.

No Python change needed in the view — the `custom_metric` flows through via `suggestion_json` and `result`.

But we do need to add `custom_metric` to the template context explicitly so the template can render it server-side:

In `suggest_target_view`, add `custom_metric` to the render context (around line 268):

```python
        return render(request, "plans/_ai_suggestion.html", {
            "suggestion": result,
            "suggestion_json": suggestion_json,
            "client": client_file,
            "participant_words": participant_words,
            "sections": section_choices,
            "matched_section_pk": matched_section_pk,
            "custom_metric": result.get("custom_metric"),
        })
```

**Step 2: Update `_ai_suggestion.html` to show custom metric**

Add a custom metric section after the existing metrics list (after `{% endif %}` for `suggestion.metrics`, around line 38):

```html
        {% if custom_metric %}
        <dt>{% trans "Suggested target-specific metric" %}</dt>
        <dd>
            <div class="custom-metric-preview">
                <strong>{{ custom_metric.name }}</strong>
                <pre class="metric-levels">{{ custom_metric.definition }}</pre>
                <div role="group" class="custom-metric-actions">
                    <button type="button" class="btn-accept-metric outline" data-metric='{{ custom_metric_json }}'>
                        {% trans "Include this metric" %}
                    </button>
                    <button type="button" class="btn-skip-metric outline secondary">
                        {% trans "Skip" %}
                    </button>
                </div>
            </div>
        </dd>
        {% endif %}
```

Also add `custom_metric_json` to the view context:

```python
            "custom_metric_json": json.dumps(result.get("custom_metric")) if result.get("custom_metric") else "",
```

**Step 3: Update the JS that handles "Use this suggestion"**

In `templates/plans/goal_form.html`, the `btn-use-suggestion` click handler reads `data-suggestion` JSON and populates form fields. It needs to also handle `custom_metric` — storing it in a hidden field so the form POST can create it.

Add hidden fields to the goal form for custom metric data (near the existing metric checkboxes):

```html
<input type="hidden" name="custom_metric_name" id="custom-metric-name" value="">
<input type="hidden" name="custom_metric_definition" id="custom-metric-definition" value="">
<input type="hidden" name="custom_metric_accepted" id="custom-metric-accepted" value="">
```

In the JS `btn-use-suggestion` handler, add:

```javascript
// Handle custom metric
if (suggestion.custom_metric) {
    document.getElementById('custom-metric-name').value = suggestion.custom_metric.name || '';
    document.getElementById('custom-metric-definition').value = suggestion.custom_metric.definition || '';
    document.getElementById('custom-metric-accepted').value = 'true';
}
```

And in the `btn-accept-metric` handler:

```javascript
document.addEventListener('click', function(e) {
    if (e.target.closest('.btn-accept-metric')) {
        document.getElementById('custom-metric-accepted').value = 'true';
        e.target.closest('.custom-metric-actions').innerHTML = '<small class="secondary">✓ Included</small>';
    }
    if (e.target.closest('.btn-skip-metric')) {
        document.getElementById('custom-metric-accepted').value = '';
        e.target.closest('.custom-metric-actions').innerHTML = '<small class="secondary">Skipped</small>';
    }
});
```

**Step 4: Handle custom metric creation in `goal_create` view POST**

In `apps/plans/views.py`, in the `goal_create` view's POST handler, after collecting `metric_ids` from the form, check for a custom metric:

```python
        # Handle AI-suggested custom metric
        custom_metric_name = request.POST.get("custom_metric_name", "").strip()
        custom_metric_def = request.POST.get("custom_metric_definition", "").strip()
        custom_metric_accepted = request.POST.get("custom_metric_accepted") == "true"

        if custom_metric_accepted and custom_metric_name:
            from apps.plans.models import MetricDefinition
            custom_metric = MetricDefinition.objects.create(
                name=custom_metric_name,
                definition=custom_metric_def,
                min_value=1,
                max_value=5,
                unit="score",
                is_library=False,
                owning_program=program,
                category="custom",
            )
            metric_ids.append(custom_metric.pk)
```

**Step 5: Run tests**

Run: `pytest tests/test_plan_crud.py -v`
Expected: All existing tests PASS.

**Step 6: Commit**

```bash
git add konote/ai.py konote/ai_views.py templates/plans/_ai_suggestion.html templates/plans/goal_form.html apps/plans/views.py
git commit -m "feat: add target-specific metric to AI suggestion flow

suggest_target now returns a custom_metric with behaviourally anchored
levels. Coaches can include or skip it. Custom metrics are created as
MetricDefinition with is_library=False, owned by the program."
```

---

## Task 6: Domain-Specific Self-Efficacy Prompt in Notes Form

**Files:**
- Modify: `apps/notes/forms.py` (lines 183–239 — `MetricValueForm.__init__`)
- Modify: `apps/notes/views.py` (lines 109–144 — `_build_target_forms`)
- Modify: `templates/notes/note_form.html` (lines 102–134 — metric rendering)

**Step 1: Pass target name into MetricValueForm**

In `apps/notes/forms.py`, add a `target_name` parameter to `MetricValueForm.__init__`:

```python
    def __init__(self, *args, metric_def=None, target_name="", **kwargs):
        super().__init__(*args, **kwargs)
        self.target_name = target_name
        if metric_def:
```

Then, after the label is set (line 190), check if this is the Self-Efficacy metric and customise the label:

```python
            self.fields["value"].label = label
            # Domain-specific prompt for Self-Efficacy
            if metric_def.name == "Self-Efficacy" and target_name:
                from django.utils.translation import gettext as _
                self.fields["value"].label = _(
                    "How sure do you feel about being able to %(target)s?"
                ) % {"target": target_name.lower()}
```

**Step 2: Pass target name when creating MetricValueForm in views**

In `apps/notes/views.py`, in `_build_target_forms()`, pass the target name when creating each `MetricValueForm` (around line 127):

```python
            mf = MetricValueForm(
                post_data,
                prefix=m_prefix,
                metric_def=ptm.metric_def,
                target_name=target.name,
            )
```

**Step 3: Run tests**

Run: `pytest tests/test_notes.py -v` (or whatever the notes test file is called)
Expected: PASS

**Step 4: Commit**

```bash
git add apps/notes/forms.py apps/notes/views.py
git commit -m "feat: domain-specific self-efficacy prompt in notes form

Self-Efficacy metric now shows 'How sure do you feel about being able
to [target name]?' instead of a generic label. Per Bandura (2006),
self-efficacy must be domain-specific to produce valid data."
```

---

## Task 7: Update Test Fixtures

**Files:**
- Modify: `tests/test_plan_crud.py` (lines 511–514, 643–646, 666)

**Step 1: Update test fixture metric names**

In `GoalCreateTest.setUp` (line 511), change the test metric:

```python
self.metric = MetricDefinition.objects.create(
    name="Self-Efficacy", definition="1-5 scale", category="general",
    is_universal=True, is_enabled=True, min_value=1, max_value=5,
)
```

In `test_multiple_metrics_can_be_assigned` (line 643):

```python
metric_b = MetricDefinition.objects.create(
    name="Goal Progress", definition="1-5 progress scale", category="general",
    is_universal=True, is_enabled=True, min_value=1, max_value=5,
)
```

In `test_get_shows_form_with_universal_metrics` (line 666):

```python
self.assertContains(resp, "Self-Efficacy")
```

**Step 2: Run tests**

Run: `pytest tests/test_plan_crud.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_plan_crud.py
git commit -m "test: update metric fixture names to match new universals

Rename Confidence→Self-Efficacy, Progress→Goal Progress in test
fixtures to match the redesigned universal metrics."
```

---

## Task 8: Update `client_goal` Display

**Files:**
- Modify: `templates/plans/_target.html` (line 5)

**Step 1: Make client_goal more prominent**

Currently `client_goal` is shown as truncated small text under the target name. Move it above the description and increase the truncation limit:

```html
<td>
    <strong>{{ target.name }}</strong>
    {% if target.client_goal %}
    <br><small><strong>{% trans "In their words:" %}</strong> "{{ target.client_goal|truncatewords:50 }}"</small>
    {% endif %}
    {% if target.description %}
    <br><small class="secondary">{{ target.description|truncatewords:30 }}</small>
    {% endif %}
</td>
```

The key changes: `truncatewords:30` → `truncatewords:50` for `client_goal`, and `truncatewords:20` → `truncatewords:30` for description. The `client_goal` keeps its current position (above description) but gets more visible text.

**Step 2: Commit**

```bash
git add templates/plans/_target.html
git commit -m "feat: show more of client_goal text in plan target view

Increase truncation from 30 to 50 words for participant's own words,
and from 20 to 30 for the SMART description."
```

---

## Task 9: French Translations

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

**Step 1: Run translate_strings to extract new strings**

Run: `python manage.py translate_strings`

**Step 2: Fill in any empty French translations**

Check `locale/fr/LC_MESSAGES/django.po` for empty `msgstr` entries corresponding to new strings:
- "Suggested target-specific metric"
- "Include this metric"
- "Skip"
- "How sure do you feel about being able to %(target)s?"
- Any other new template strings

Fill them in:
- "Suggested target-specific metric" → "Métrique suggérée pour cet objectif"
- "Include this metric" → "Inclure cette métrique"
- "Skip" → "Ignorer"
- "How sure do you feel about being able to %(target)s?" → "À quel point êtes-vous sûr(e) de pouvoir %(target)s?"

**Step 3: Recompile**

Run: `python manage.py translate_strings`

**Step 4: Commit**

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "i18n: add French translations for targets/metrics redesign"
```

---

## Task 10: Run Full Related Test Suite

**Step 1: Run plan and notes tests**

Run: `pytest tests/test_plan_crud.py tests/test_notes.py -v`
Expected: All PASS

**Step 2: Run AI tests if they exist**

Run: `pytest tests/test_ai.py -v` (if file exists)
Expected: All PASS

**Step 3: Commit any fixes needed**

If tests fail, fix and commit each fix individually.

---

## Summary

| Task | What changes | Files |
|------|-------------|-------|
| 1 | Seed data — new universal metrics | `seeds/metric_library.json`, `seed.py` |
| 2 | AI prompt — `suggest_target` + validation + custom_metric | `konote/ai.py`, `tests/test_ai.py` |
| 3 | AI prompt — `build_goal_chat` + validation | `konote/ai.py` |
| 4 | AI prompt — `improve_outcome` + validation | `konote/ai.py` |
| 5 | Custom metric in suggest flow — view + template + JS | `ai_views.py`, templates, `views.py` |
| 6 | Domain-specific Self-Efficacy in notes | `forms.py`, `views.py`, template |
| 7 | Test fixture updates | `test_plan_crud.py` |
| 8 | `client_goal` display enhancement | `_target.html` |
| 9 | French translations | `.po`, `.mo` |
| 10 | Full test run | — |
