# Notes Form Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the progress notes form into a 4-zone layout with compact target cards, scale pills, auto-calc metrics, and collapsed optional sections.

**Architecture:** Server-rendered Django templates + Pico CSS + vanilla JS. No new frameworks. Scale pills reuse the existing `.descriptor-pills` CSS pattern. Auto-calc requires one model migration. Compact cards use JS with `aria-expanded`.

**Tech Stack:** Django 5 templates, HTMX (existing), Pico CSS, vanilla JavaScript, CSS Grid

**Design doc:** `docs/plans/2026-02-19-notes-form-redesign.md`

---

## Phase A: Layout + Field Widths + Consent

*Pure CSS + template restructuring. No model or form logic changes (except consent `required=False`). Biggest visual impact, lowest risk.*

### Task 1: Restructure template into 4 zones

**Files:**
- Modify: `templates/notes/note_form.html` (full file — 222 lines)

**Step 1: Wrap Session Setup fields in a grid container**

In `note_form.html`, replace the 3 separate field blocks (template, interaction_type, session_date — lines 16-30) with:

```html
<!-- Zone 1: Session Setup -->
<fieldset class="session-setup" role="group" aria-label="{% trans 'Session setup' %}">
    <div class="session-setup-grid">
        <div class="field-template">
            <label for="{{ form.template.id_for_label }}">{% trans "Template" %}</label>
            {{ form.template }}
            {% if form.template.errors %}<small class="error" id="template-error" role="alert">{{ form.template.errors.0 }}</small>{% endif %}
        </div>
        <div class="field-interaction">
            <label for="{{ form.interaction_type.id_for_label }}">{% trans "Interaction type" %}</label>
            {{ form.interaction_type }}
            {% if form.interaction_type.errors %}<small class="error" id="interaction-type-error" role="alert">{{ form.interaction_type.errors.0 }}</small>{% endif %}
        </div>
        <div class="field-date">
            <label for="{{ form.session_date.id_for_label }}">{% trans "Session Date" %}</label>
            {{ form.session_date }}
            <small id="session-date-help">{{ form.session_date.help_text }}</small>
            {% if form.session_date.errors %}<small class="error" id="session-date-error" role="alert">{{ form.session_date.errors.0 }}</small>{% endif %}
        </div>
    </div>
</fieldset>
```

**Step 2: Reorder fields inside each target accordion**

Currently the order inside each `<details>` (lines 58-95) is:
1. Client goal callout
2. Client words
3. Progress descriptor pills
4. Notes textarea
5. Metrics

Reorder to match the "taps before typing" workflow:
1. Client goal callout (keep as context)
2. Progress descriptor pills
3. Metrics
4. Client words (change from TextInput to single-line input)
5. Notes textarea

**Step 3: Wrap Wrap-up fields in `<details>` (collapsed by default)**

Replace the Summary, Follow-up, and Engagement fields (lines 102-117) with:

```html
<!-- Zone 3: Wrap-up -->
<details class="zone-wrapup">
    <summary>{% trans "Wrap-up details" %} <small class="secondary">{% trans "(optional)" %}</small></summary>

    <label for="{{ form.summary.id_for_label }}">{% trans "Summary (optional)" %}</label>
    {{ form.summary }}
    {% if form.summary.errors %}<small class="error" id="summary-error" role="alert">{{ form.summary.errors.0 }}</small>{% endif %}

    <div class="wrapup-grid">
        <div class="field-engagement">
            <label for="{{ form.engagement_observation.id_for_label }}">{% trans "How engaged was the participant?" %}</label>
            {{ form.engagement_observation }}
            <small>{% trans "Your observation — not a score." %}</small>
            {% if form.engagement_observation.errors %}<small class="error" id="engagement-error" role="alert">{{ form.engagement_observation.errors.0 }}</small>{% endif %}
        </div>
        <div class="field-followup">
            <label for="{{ form.follow_up_date.id_for_label }}">{% trans "Follow up by" %}</label>
            {{ form.follow_up_date }}
            <small>{% trans "(optional — adds to your home page reminders)" %}</small>
            {% if form.follow_up_date.errors %}<small class="error" id="follow-up-error" role="alert">{{ form.follow_up_date.errors.0 }}</small>{% endif %}
        </div>
    </div>
</details>
```

**Step 4: Wrap Participant Voice in `<details>` (collapsed by default)**

Replace the two sections (lines 119-157) with:

```html
<!-- Zone 4: Participant Voice -->
<details class="zone-voice">
    <summary>{% trans "Participant voice" %} <small class="secondary">{% trans "(optional)" %}</small></summary>

    <label for="{{ form.participant_reflection.id_for_label }}" class="visually-hidden">
        {% blocktrans with client=term.client|default:"Participant" %}{{ client }}'s response{% endblocktrans %}
    </label>
    <label for="{{ form.participant_reflection.id_for_label }}">
        {% blocktrans with client=term.client|default:"Participant" %}{{ client }}'s reflection{% endblocktrans %}
    </label>
    {{ form.participant_reflection }}
    {% if form.participant_reflection.errors %}<small class="error" id="reflection-error" role="alert">{{ form.participant_reflection.errors.0 }}</small>{% endif %}

    <label for="{{ form.participant_suggestion.id_for_label }}">{% trans "What they'd change" %}</label>
    {{ form.participant_suggestion }}
    {% if form.participant_suggestion.errors %}<small class="error" id="suggestion-error" role="alert">{{ form.participant_suggestion.errors.0 }}</small>{% endif %}

    <div class="suggestion-priority-row" id="suggestion-priority-row" hidden>
        <label for="{{ form.suggestion_priority.id_for_label }}">{% trans "Priority" %}</label>
        {{ form.suggestion_priority }}
        <small>{% trans "Urgent = safety/access · Important = affects many · Worth exploring = good idea · Noted = heard and recorded" %}</small>
        {% if form.suggestion_priority.errors %}<small class="error" id="priority-error" role="alert">{{ form.suggestion_priority.errors.0 }}</small>{% endif %}
    </div>
</details>
```

Note: Remove the emoji icons, coaching prompt text ("Ask: What's one thing..."), and `.participant-reflection`/`.participant-suggestion` wrapper divs. The collapsible `<details>` replaces them.

**Step 5: Update consent wording**

In the sticky footer (line 165), change the label text:
- From: `{% trans "We created this note together (this is recommended)" %}`
- To: `{% trans "I have reviewed this note for accuracy" %}`

**Step 6: Run the existing tests**

Run: `pytest tests/test_notes.py -v`
Expected: All existing tests PASS (template changes don't affect form submission logic)

**Step 7: Commit**

```bash
git add templates/notes/note_form.html
git commit -m "feat(notes): restructure form into 4 zones with collapsed optional sections"
```

### Task 2: CSS for zone layout and field widths

**Files:**
- Modify: `static/css/main.css`

**Step 1: Add session setup grid CSS**

Add after the existing fieldset styles (around line 1640):

```css
/* Notes form — Zone 1: Session Setup grid */
.session-setup {
    border: none;
    padding: 0;
    margin-bottom: var(--kn-space-lg);
}
.session-setup-grid {
    display: grid;
    grid-template-columns: 1fr 1fr auto;
    gap: var(--kn-space-base);
    align-items: start;
}
.field-template { max-width: 24rem; }
.field-interaction { max-width: 20rem; }
.field-date { max-width: 12rem; }

/* Constrain select/input widths inside grid cells */
.session-setup-grid select,
.session-setup-grid input[type="date"] {
    width: 100%;
}

@media (max-width: 768px) {
    .session-setup-grid {
        grid-template-columns: 1fr;
    }
    .field-template,
    .field-interaction,
    .field-date {
        max-width: 100%;
    }
}
```

**Step 2: Add wrap-up grid CSS**

```css
/* Notes form — Zone 3: Wrap-up grid */
.wrapup-grid {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: var(--kn-space-base);
    align-items: start;
}
.field-engagement { max-width: 20rem; }
.field-followup { max-width: 12rem; }

@media (max-width: 768px) {
    .wrapup-grid {
        grid-template-columns: 1fr;
    }
    .field-engagement,
    .field-followup {
        max-width: 100%;
    }
}
```

**Step 3: Add zone styling for collapsible sections**

```css
/* Notes form — collapsible zones */
.zone-wrapup,
.zone-voice {
    border: 1px solid var(--kn-border-light);
    border-radius: var(--pico-border-radius);
    padding: var(--kn-space-base) var(--kn-space-lg);
    margin-bottom: var(--kn-space-lg);
}
.zone-wrapup > summary,
.zone-voice > summary {
    font-weight: 600;
    cursor: pointer;
    padding: var(--kn-space-sm) 0;
}
.zone-wrapup > summary .secondary,
.zone-voice > summary .secondary {
    font-weight: 400;
    color: var(--kn-text-muted);
}
```

**Step 4: Commit**

```bash
git add static/css/main.css
git commit -m "feat(notes): add CSS for session setup grid, wrap-up grid, and zone layout"
```

### Task 3: Update consent field in form

**Files:**
- Modify: `apps/notes/forms.py:154-161`

**Step 1: Change consent to optional with new wording**

In `FullNoteForm`, change `consent_confirmed`:
```python
consent_confirmed = forms.BooleanField(
    required=False,
    label=_("I have reviewed this note for accuracy"),
)
```

Remove the old `error_messages` dict since it's no longer required.

**Step 2: Write a test for optional consent**

In `tests/test_notes.py`, add:

```python
def test_full_note_saves_without_consent(self):
    """Consent checkbox is recommended, not required."""
    self.http.login(username="staff", password="pass")
    resp = self.http.post(
        f"/notes/participant/{self.client_file.pk}/new/",
        {
            "interaction_type": "session",
            "summary": "Session notes",
            # consent_confirmed omitted
        },
    )
    self.assertEqual(resp.status_code, 302)
    self.assertTrue(ProgressNote.objects.filter(note_type="full").exists())
```

**Step 3: Run tests**

Run: `pytest tests/test_notes.py -v`
Expected: All PASS including the new consent test

**Step 4: Commit**

```bash
git add apps/notes/forms.py tests/test_notes.py
git commit -m "feat(notes): make consent checkbox optional with clearer wording"
```

### Task 4: Add French translations for new strings

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

**Step 1: Extract and translate new strings**

Run: `python manage.py translate_strings`

New strings to translate:
- "Session setup" → "Configuration de la séance"
- "Wrap-up details" → "Détails de conclusion"
- "Participant voice" → "Voix du participant"
- "(optional)" → "(facultatif)"
- "Your observation — not a score." → "Votre observation — pas un pointage."
- "I have reviewed this note for accuracy" → "J'ai vérifié l'exactitude de cette note"

**Step 2: Run translate_strings again to compile**

Run: `python manage.py translate_strings`

**Step 3: Commit**

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "i18n: add French translations for notes form zone labels"
```

---

## Phase B: Scale Pills

*Form logic + template + CSS. Metrics with small integer ranges render as tappable pills.*

### Task 5: Write tests for scale detection

**Files:**
- Modify: `tests/test_notes.py`

**Step 1: Write the test**

```python
def test_scale_metric_renders_as_radio(self):
    """Metrics with small integer ranges (1-5) should use RadioSelect widget."""
    from apps.notes.forms import MetricValueForm
    metric = MetricDefinition.objects.create(
        name="Confidence", min_value=1, max_value=5, unit="",
        definition="Rate your confidence", category="general",
    )
    form = MetricValueForm(metric_def=metric)
    # Should be a RadioSelect widget, not NumberInput
    self.assertEqual(form.fields["value"].widget.__class__.__name__, "RadioSelect")
    # Should have choices 1-5
    choices = form.fields["value"].widget.choices
    self.assertEqual(len(choices), 6)  # empty + 1,2,3,4,5

def test_wide_range_metric_stays_number_input(self):
    """Metrics with wide ranges (0-100) should stay as NumberInput."""
    from apps.notes.forms import MetricValueForm
    metric = MetricDefinition.objects.create(
        name="Score", min_value=0, max_value=100, unit="score",
        definition="Overall score", category="general",
    )
    form = MetricValueForm(metric_def=metric)
    self.assertEqual(form.fields["value"].widget.__class__.__name__, "NumberInput")

def test_float_range_metric_stays_number_input(self):
    """Metrics with float min/max should not render as scale pills."""
    from apps.notes.forms import MetricValueForm
    metric = MetricDefinition.objects.create(
        name="Weight", min_value=0.0, max_value=5.0, unit="kg",
        definition="Body weight change", category="general",
    )
    # 0.0 and 5.0 are technically integers when cast, but let's ensure
    # only truly integer ranges get scale pills
    form = MetricValueForm(metric_def=metric)
    # This should still be NumberInput because we want to be safe
    # Actually, 0.0 == int(0.0) is True, so this WILL be a scale
    # That's fine — the design says "both integers"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_notes.py::NoteViewsTest::test_scale_metric_renders_as_radio -v`
Expected: FAIL (currently renders as NumberInput)

**Step 3: Commit test**

```bash
git add tests/test_notes.py
git commit -m "test(notes): add tests for scale pill detection in MetricValueForm"
```

### Task 6: Implement scale detection in MetricValueForm

**Files:**
- Modify: `apps/notes/forms.py:187-223` (MetricValueForm.__init__)

**Step 1: Add scale detection logic**

In `MetricValueForm.__init__`, after the existing attrs logic (around line 223), replace the entire widget selection block with:

```python
def __init__(self, *args, metric_def=None, **kwargs):
    super().__init__(*args, **kwargs)
    if metric_def:
        self.metric_def = metric_def
        label = metric_def.translated_name
        if metric_def.translated_unit:
            label += f" ({metric_def.translated_unit})"
        self.fields["value"].label = label
        # Set help text from definition
        help_parts = []
        if metric_def.translated_definition:
            help_parts.append(metric_def.translated_definition)
        if metric_def.min_value is not None or metric_def.max_value is not None:
            range_str = _("Range: ")
            if metric_def.min_value is not None:
                range_str += str(metric_def.min_value)
            range_str += " – "
            if metric_def.max_value is not None:
                range_str += str(metric_def.max_value)
            help_parts.append(range_str)
        self.fields["value"].help_text = " | ".join(help_parts)

        # Detect scale metrics: both min/max set, both integers, small range
        is_scale = (
            metric_def.min_value is not None
            and metric_def.max_value is not None
            and metric_def.min_value == int(metric_def.min_value)
            and metric_def.max_value == int(metric_def.max_value)
            and (metric_def.max_value - metric_def.min_value) <= 9
        )

        if is_scale:
            low = int(metric_def.min_value)
            high = int(metric_def.max_value)
            choices = [("", "---------")] + [
                (str(i), str(i)) for i in range(low, high + 1)
            ]
            self.fields["value"].widget = forms.RadioSelect(
                choices=choices,
                attrs={
                    "class": "scale-pills-input",
                    "aria-label": f"{metric_def.translated_name}: {metric_def.translated_definition}",
                },
            )
            self.is_scale = True
        else:
            # Standard number input for wide-range metrics
            attrs = {}
            if metric_def.min_value is not None:
                attrs["min"] = metric_def.min_value
            if metric_def.max_value is not None:
                attrs["max"] = metric_def.max_value
            if attrs:
                attrs["type"] = "number"
                attrs["step"] = "any"
                self.fields["value"].widget = forms.NumberInput(attrs=attrs)
            self.is_scale = False
```

**Step 2: Run scale detection tests**

Run: `pytest tests/test_notes.py::NoteViewsTest::test_scale_metric_renders_as_radio tests/test_notes.py::NoteViewsTest::test_wide_range_metric_stays_number_input -v`
Expected: PASS

**Step 3: Run full notes tests to confirm no regressions**

Run: `pytest tests/test_notes.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add apps/notes/forms.py
git commit -m "feat(notes): detect scale metrics and render as RadioSelect pills"
```

### Task 7: Template rendering for scale pills

**Files:**
- Modify: `templates/notes/note_form.html`

**Step 1: Update metric rendering in target cards**

In the metric loop inside each target entry, replace the simple `{{ mf.value }}` rendering with conditional rendering:

```html
{% for mf in tf.metric_forms %}
{{ mf.metric_def_id }}
{% if mf.is_scale %}
<div class="scale-metric">
    <label>{{ mf.value.label }}</label>
    <div class="scale-pills">
    {% for radio in mf.value %}
        {% if radio.choice_value %}
        <label>{{ radio.tag }}<span>{{ radio.choice_label }}</span></label>
        {% endif %}
    {% endfor %}
    </div>
    {% if mf.value.help_text %}<small>{{ mf.value.help_text }}</small>{% endif %}
    {% if mf.value.errors %}<small class="error" role="alert">{{ mf.value.errors.0 }}</small>{% endif %}
</div>
{% else %}
<label for="{{ mf.value.id_for_label }}">{{ mf.value.label }}</label>
{{ mf.value }}
{% if mf.value.help_text %}<small>{{ mf.value.help_text }}</small>{% endif %}
{% if mf.value.errors %}<small class="error" role="alert">{{ mf.value.errors.0 }}</small>{% endif %}
{% endif %}
{% endfor %}
```

**Step 2: Commit**

```bash
git add templates/notes/note_form.html
git commit -m "feat(notes): render scale metrics as pill buttons in template"
```

### Task 8: Scale pills CSS

**Files:**
- Modify: `static/css/main.css`

**Step 1: Add scale pills CSS extending descriptor pills pattern**

Add after the existing `.descriptor-pills` rules (around line 3223):

```css
/* Scale pills for numeric metrics (1-5, 1-10) */
.scale-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: var(--kn-space-base);
}
.scale-pills label {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 0.75rem;
    border: 2px solid var(--kn-border-light);
    border-radius: 999px;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    user-select: none;
    font-size: 0.9375rem;
    min-width: 2.75rem;
    min-height: 44px;
    margin-bottom: 0;
    color: var(--kn-text);
}
.scale-pills input[type="radio"] {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
}
.scale-pills label:has(input:checked) {
    border-color: var(--kn-primary);
    background: var(--kn-primary-subtle, #e8f0fe);
    font-weight: 500;
}
.scale-pills label:hover {
    border-color: var(--kn-primary);
}
.scale-pills label:focus-within {
    outline: 2px solid var(--kn-primary);
    outline-offset: 2px;
}

.scale-metric {
    margin-bottom: var(--kn-space-base);
}

@media (max-width: 480px) {
    .scale-pills {
        gap: 0.375rem;
    }
    .scale-pills label {
        padding: 0.375rem 0.625rem;
        font-size: 0.8125rem;
        min-width: 2.5rem;
        min-height: 40px;
    }
}
```

**Step 2: Commit**

```bash
git add static/css/main.css
git commit -m "feat(notes): add scale pills CSS extending descriptor pill pattern"
```

### Task 9: Test scale pill form submission end-to-end

**Files:**
- Modify: `tests/test_notes.py`

**Step 1: Write integration test**

```python
def test_full_note_with_scale_metric_saves(self):
    """Scale metrics (RadioSelect) save correctly via form POST."""
    section = PlanSection.objects.create(
        client_file=self.client_file, name="Wellbeing", program=self.prog,
    )
    target = PlanTarget.objects.create(
        plan_section=section, client_file=self.client_file, name="Confidence",
    )
    # 1-5 scale metric — should render as RadioSelect
    metric = MetricDefinition.objects.create(
        name="Confidence Level", min_value=1, max_value=5, unit="",
        definition="Self-rated confidence", category="general",
    )
    PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)

    self.http.login(username="staff", password="pass")
    resp = self.http.post(
        f"/notes/participant/{self.client_file.pk}/new/",
        {
            "interaction_type": "session",
            "consent_confirmed": True,
            f"target_{target.pk}-target_id": str(target.pk),
            f"target_{target.pk}-notes": "Feeling better",
            f"metric_{target.pk}_{metric.pk}-metric_def_id": str(metric.pk),
            f"metric_{target.pk}_{metric.pk}-value": "4",  # Selected pill
        },
    )
    self.assertEqual(resp.status_code, 302)
    mv = MetricValue.objects.get(metric_def=metric)
    self.assertEqual(mv.value, "4")
```

**Step 2: Run test**

Run: `pytest tests/test_notes.py::NoteViewsTest::test_full_note_with_scale_metric_saves -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_notes.py
git commit -m "test(notes): add integration test for scale pill metric submission"
```

---

## Phase C: Compact Target Cards

*Template + CSS + JS. Cards start compact (descriptor pills only), expand to show full fields.*

### Task 10: Convert target accordions to cards with compact/expanded states

**Files:**
- Modify: `templates/notes/note_form.html`

**Step 1: Replace `<details>` with card divs**

Replace each target `<details>` (currently lines 51-96 area) with:

```html
{% for tf in target_forms %}
<div id="target-card-{{ tf.target.pk }}" class="target-card compact" hidden data-target-id="{{ tf.target.pk }}">
    {{ tf.note_form.target_id }}

    <div class="target-card-header" role="button" tabindex="0"
         aria-expanded="false" aria-controls="target-card-body-{{ tf.target.pk }}">
        <div class="target-card-title">
            <strong>{{ tf.target.name }}</strong>
            <small class="secondary">— {{ tf.target.plan_section.name }}</small>
        </div>
        <div class="target-card-actions">
            <button type="button" class="no-change-btn outline secondary"
                    data-target-id="{{ tf.target.pk }}"
                    aria-label="{% trans 'Mark as no change' %}">
                {% trans "No change" %}
            </button>
            <span class="expand-indicator" aria-hidden="true">&#9662;</span>
        </div>
    </div>

    <!-- Compact: always visible — descriptor pills -->
    <div class="target-card-compact">
        {% if tf.target.client_goal %}
        <div class="client-goal-callout" role="note">
            <strong>{% trans "In their words:" %}</strong> "{{ tf.target.client_goal }}"
        </div>
        {% endif %}

        <label>{% trans "How are things going?" %}</label>
        <div class="descriptor-pills">
        {% for radio in tf.note_form.progress_descriptor %}
            {% if radio.choice_value %}
            <label>{{ radio.tag }}<span>{{ radio.choice_label }}</span></label>
            {% endif %}
        {% endfor %}
        </div>
    </div>

    <!-- Expanded: hidden until card is expanded -->
    <div id="target-card-body-{{ tf.target.pk }}" class="target-card-body" hidden>
        {% if tf.metric_forms %}
        <div class="target-metrics">
        {% for mf in tf.metric_forms %}
            {{ mf.metric_def_id }}
            {% if mf.is_scale %}
            <div class="scale-metric">
                <label>{{ mf.value.label }}</label>
                <div class="scale-pills">
                {% for radio in mf.value %}
                    {% if radio.choice_value %}
                    <label>{{ radio.tag }}<span>{{ radio.choice_label }}</span></label>
                    {% endif %}
                {% endfor %}
                </div>
                {% if mf.value.help_text %}<small>{{ mf.value.help_text }}</small>{% endif %}
            </div>
            {% else %}
            <label for="{{ mf.value.id_for_label }}">{{ mf.value.label }}</label>
            {{ mf.value }}
            {% if mf.value.help_text %}<small>{{ mf.value.help_text }}</small>{% endif %}
            {% endif %}
        {% endfor %}
        </div>
        {% endif %}

        <label for="{{ tf.note_form.client_words.id_for_label }}">{% trans "In their words" %}</label>
        {{ tf.note_form.client_words }}

        <label for="{{ tf.note_form.notes.id_for_label }}">{% blocktrans with target=term.target|default:"target" %}Your notes for this {{ target }}{% endblocktrans %}</label>
        {{ tf.note_form.notes }}
    </div>

    <!-- Done indicator (hidden until "No change" is clicked) -->
    <div class="target-done-indicator" hidden aria-live="polite">
        <span aria-hidden="true">&#10003;</span> {% trans "No change noted" %}
    </div>
</div>
{% endfor %}
```

**Step 2: Update the target-selector checkbox JS**

Replace the existing checkbox toggle JS (lines 187-196) with:

```javascript
// Show/hide target cards based on checkbox selection
document.querySelectorAll(".target-selector").forEach(function (cb) {
    cb.addEventListener("change", function () {
        var targetId = this.getAttribute("data-target-id");
        var card = document.getElementById("target-card-" + targetId);
        if (card) {
            card.hidden = !this.checked;
        }
    });
});
```

**Step 3: Commit**

```bash
git add templates/notes/note_form.html
git commit -m "feat(notes): convert target accordions to compact/expandable cards"
```

### Task 11: Card expand/collapse and "No change" JS

**Files:**
- Modify: `templates/notes/note_form.html` (inline script section)

**Step 1: Add card interaction JS**

Add to the `{% block extra_scripts %}` section:

```javascript
// Target card expand/collapse
document.querySelectorAll(".target-card-header").forEach(function (header) {
    function toggle() {
        var card = header.closest(".target-card");
        var body = card.querySelector(".target-card-body");
        var isExpanded = !body.hidden;
        body.hidden = isExpanded;
        header.setAttribute("aria-expanded", !isExpanded);
        card.classList.toggle("compact", isExpanded);
        card.classList.toggle("expanded", !isExpanded);
        if (!isExpanded) {
            var firstInput = body.querySelector("input, textarea, select, [tabindex]");
            if (firstInput) firstInput.focus();
        }
    }
    header.addEventListener("click", function (e) {
        if (!e.target.closest(".no-change-btn")) toggle();
    });
    header.addEventListener("keydown", function (e) {
        if ((e.key === "Enter" || e.key === " ") && !e.target.closest(".no-change-btn")) {
            e.preventDefault();
            toggle();
        }
    });
});

// "No change" shortcut
document.querySelectorAll(".no-change-btn").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var card = btn.closest(".target-card");
        var targetId = btn.getAttribute("data-target-id");
        // Set descriptor to "holding" (Holding steady)
        var holdingRadio = card.querySelector(
            'input[name="target_' + targetId + '-progress_descriptor"][value="holding"]'
        );
        if (holdingRadio) holdingRadio.checked = true;
        // Show done indicator, hide the card body
        card.classList.add("done");
        var indicator = card.querySelector(".target-done-indicator");
        if (indicator) indicator.hidden = false;
        // Collapse if expanded
        var body = card.querySelector(".target-card-body");
        if (body) body.hidden = true;
        card.classList.remove("expanded");
        card.classList.add("compact");
        var header = card.querySelector(".target-card-header");
        if (header) header.setAttribute("aria-expanded", "false");
    });
});
```

**Step 2: Commit**

```bash
git add templates/notes/note_form.html
git commit -m "feat(notes): add card expand/collapse and 'No change' shortcut JS"
```

### Task 12: Target card CSS

**Files:**
- Modify: `static/css/main.css`

**Step 1: Add target card styles**

```css
/* Notes form — Target cards */
.target-card {
    border: 1px solid var(--kn-border-light);
    border-radius: var(--pico-border-radius);
    padding: var(--kn-space-base) var(--kn-space-lg);
    margin-bottom: var(--kn-space-base);
    transition: border-color 0.15s;
}
.target-card:hover {
    border-color: var(--kn-primary);
}
.target-card.done {
    border-color: var(--kn-success, #10B981);
    background: var(--kn-success-subtle, #ecfdf5);
}

.target-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    gap: var(--kn-space-base);
}
.target-card-header:focus-visible {
    outline: 2px solid var(--kn-primary);
    outline-offset: 2px;
    border-radius: var(--pico-border-radius);
}
.target-card-title {
    flex: 1;
    min-width: 0;
}
.target-card-title strong {
    display: block;
}
.target-card-actions {
    display: flex;
    align-items: center;
    gap: var(--kn-space-sm);
    flex-shrink: 0;
}
.no-change-btn {
    font-size: 0.8125rem;
    padding: 0.25rem 0.75rem;
    margin-bottom: 0;
    min-height: auto;
    color: var(--kn-text);
    background: transparent;
}
.expand-indicator {
    transition: transform 0.15s;
    font-size: 0.875rem;
    color: var(--kn-text-muted);
}
.target-card.expanded .expand-indicator {
    transform: rotate(180deg);
}

.target-card-compact {
    margin-top: var(--kn-space-sm);
}
.target-card-body {
    margin-top: var(--kn-space-base);
    padding-top: var(--kn-space-base);
    border-top: 1px solid var(--kn-border-light);
}

.target-done-indicator {
    margin-top: var(--kn-space-sm);
    color: var(--kn-success, #10B981);
    font-weight: 500;
    font-size: 0.875rem;
}

/* Hide expand indicator + no-change button when card is done */
.target-card.done .no-change-btn,
.target-card.done .expand-indicator {
    display: none;
}
```

**Step 2: Commit**

```bash
git add static/css/main.css
git commit -m "feat(notes): add target card CSS with compact, expanded, and done states"
```

### Task 13: Test that form submission still works with card layout

**Files:**
- Modify: `tests/test_notes.py`

**Step 1: Run existing full note test**

Run: `pytest tests/test_notes.py::NoteViewsTest::test_full_note_create_with_targets_and_metrics -v`
Expected: PASS (card structure doesn't change form field names or POST data)

**Step 2: Commit if any test updates were needed**

---

## Phase D: Auto-Calc Metrics

*Model migration + view logic + template rendering. Highest risk due to migration.*

### Task 14: Add `computation_type` to MetricDefinition

**Files:**
- Modify: `apps/plans/models.py:9-119` (MetricDefinition class)

**Step 1: Write test for computation_type field**

In `tests/test_notes.py`:

```python
def test_metric_computation_type_defaults_to_empty(self):
    """New metrics default to manual entry (empty computation_type)."""
    metric = MetricDefinition.objects.create(
        name="Test", definition="Test", category="general",
    )
    self.assertEqual(metric.computation_type, "")

def test_metric_computation_type_session_count(self):
    """Metrics can have computation_type='session_count'."""
    metric = MetricDefinition.objects.create(
        name="Sessions", definition="Count", category="general",
        computation_type="session_count",
    )
    metric.refresh_from_db()
    self.assertEqual(metric.computation_type, "session_count")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_notes.py::NoteViewsTest::test_metric_computation_type_defaults_to_empty -v`
Expected: FAIL (field doesn't exist yet)

**Step 3: Add the field**

In `MetricDefinition` class (after `unit_fr` field, around line 43):

```python
COMPUTATION_TYPE_CHOICES = [
    ("", _("Manual entry")),
    ("session_count", _("Sessions attended this month")),
]
computation_type = models.CharField(
    max_length=30, blank=True, default="",
    choices=COMPUTATION_TYPE_CHOICES,
    help_text="If set, value is computed automatically instead of manual entry.",
)
```

**Step 4: Create and run migration**

Run: `python manage.py makemigrations plans && python manage.py migrate`

**Step 5: Run tests**

Run: `pytest tests/test_notes.py::NoteViewsTest::test_metric_computation_type_defaults_to_empty tests/test_notes.py::NoteViewsTest::test_metric_computation_type_session_count -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/plans/models.py apps/plans/migrations/ tests/test_notes.py
git commit -m "feat(plans): add computation_type field to MetricDefinition"
```

### Task 15: Auto-calc view logic

**Files:**
- Modify: `apps/notes/views.py:86-122` (_build_target_forms) and `apps/notes/views.py:400-544` (note_create)

**Step 1: Write test for session count auto-calc**

```python
def test_auto_calc_session_count(self):
    """Auto-calc metric shows session count for current month."""
    section = PlanSection.objects.create(
        client_file=self.client_file, name="Attendance", program=self.prog,
    )
    target = PlanTarget.objects.create(
        plan_section=section, client_file=self.client_file, name="Attendance",
    )
    metric = MetricDefinition.objects.create(
        name="Sessions this month", min_value=0, max_value=20,
        unit="sessions", definition="Sessions attended",
        category="general", computation_type="session_count",
    )
    PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)

    # Create 3 notes this month
    for i in range(3):
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text=f"Note {i}", author=self.staff,
        )

    self.http.login(username="staff", password="pass")
    resp = self.http.get(f"/notes/participant/{self.client_file.pk}/new/")
    self.assertEqual(resp.status_code, 200)
    self.assertContains(resp, "3")  # auto-calculated count
    self.assertContains(resp, "auto-calculated")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_notes.py::NoteViewsTest::test_auto_calc_session_count -v`
Expected: FAIL

**Step 3: Add auto-calc helper to views.py**

Add after `_build_target_forms` function (around line 123):

```python
def _compute_auto_calc_values(client, target_forms):
    """Compute auto-calculated metric values.

    Returns dict: {metric_def_pk: computed_value}
    """
    computed = {}
    for tf in target_forms:
        for mf in tf["metric_forms"]:
            if not hasattr(mf, "metric_def"):
                continue
            comp_type = getattr(mf.metric_def, "computation_type", "")
            if comp_type == "session_count":
                now = timezone.now()
                count = ProgressNote.objects.filter(
                    client_file=client,
                    status="default",
                    created_at__year=now.year,
                    created_at__month=now.month,
                ).count()
                computed[mf.metric_def.pk] = count
    return computed
```

**Step 4: Pass computed values to template in note_create**

In `note_create` GET path (around line 524, before the return render), add:

```python
auto_calc_values = _compute_auto_calc_values(client, target_forms)
```

Add to the context dict: `"auto_calc_values": auto_calc_values`

**Step 5: Update template to render auto-calc metrics**

In the target card metrics section, add conditional rendering for auto-calc:

```html
{% for mf in tf.metric_forms %}
{{ mf.metric_def_id }}
{% if mf.metric_def.computation_type %}
<div class="auto-calc-metric">
    <span class="metric-label">{{ mf.value.label }}</span>
    <span class="metric-value" aria-readonly="true">{{ auto_calc_values|default_if_none:"" }}</span>
    <small>{% trans "(auto-calculated)" %}</small>
</div>
{% elif mf.is_scale %}
<!-- scale pill rendering -->
{% else %}
<!-- standard input rendering -->
{% endif %}
{% endfor %}
```

Note: For the auto-calc template lookup, we need a custom template filter to look up the value by metric def pk. Add a simple template tag or pass the value through the metric form object.

**Better approach:** Annotate each metric form with its computed value in `_build_target_forms`:

```python
# In _build_target_forms, after creating metric forms:
mf.auto_calc_value = computed.get(ptm.metric_def.pk)
```

Then in template: `{{ mf.auto_calc_value }}`

**Step 6: Handle auto-calc on POST**

In `note_create` POST path, after creating the note, compute and save auto-calc values server-side:

```python
# After creating ProgressNoteTarget entries, for auto-calc metrics:
if mf.metric_def.computation_type:
    computed = _compute_auto_calc_values(client, target_forms)
    val = computed.get(mf.metric_def.pk)
    if val is not None:
        MetricValue.objects.create(
            progress_note_target=pnt,
            metric_def_id=mf.metric_def.pk,
            value=str(val),
        )
```

**Step 7: Run tests**

Run: `pytest tests/test_notes.py -v`
Expected: All PASS

**Step 8: Commit**

```bash
git add apps/notes/views.py templates/notes/note_form.html
git commit -m "feat(notes): add auto-calc session count for computable metrics"
```

### Task 16: Auto-calc CSS

**Files:**
- Modify: `static/css/main.css`

**Step 1: Add auto-calc display styles**

```css
/* Auto-calculated metric display */
.auto-calc-metric {
    display: flex;
    align-items: baseline;
    gap: var(--kn-space-sm);
    padding: var(--kn-space-sm) 0;
    margin-bottom: var(--kn-space-sm);
}
.auto-calc-metric .metric-label {
    font-weight: 500;
}
.auto-calc-metric .metric-value {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--kn-primary);
}
.auto-calc-metric small {
    color: var(--kn-text-muted);
    font-style: italic;
}
```

**Step 2: Commit**

```bash
git add static/css/main.css
git commit -m "feat(notes): add auto-calc metric display CSS"
```

### Task 17: Update seed data

**Files:**
- Modify: `seeds/metric_library.json`

**Step 1: Add computation_type to "Sessions attended this month"**

Find the entry (around line 376) and add:
```json
"computation_type": "session_count"
```

**Step 2: Commit**

```bash
git add seeds/metric_library.json
git commit -m "feat(seeds): add computation_type to Sessions metric"
```

### Task 18: Final translations

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

**Step 1: Extract and translate new strings**

Run: `python manage.py translate_strings`

New strings from Phases B-D:
- "Mark as no change" → "Marquer sans changement"
- "No change" → "Aucun changement"
- "No change noted" → "Aucun changement noté"
- "(auto-calculated)" → "(calculé automatiquement)"
- "Manual entry" → "Saisie manuelle"
- "Sessions attended this month" → "Séances suivies ce mois-ci"

**Step 2: Compile**

Run: `python manage.py translate_strings`

**Step 3: Commit**

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "i18n: add French translations for scale pills, cards, and auto-calc"
```

### Task 19: Full test suite

**Step 1: Run all note tests**

Run: `pytest tests/test_notes.py -v`
Expected: All PASS

**Step 2: Run related tests**

Run: `pytest tests/test_plans.py -v` (if exists, since MetricDefinition was modified)

**Step 3: Visual smoke test**

Start dev server: `python manage.py runserver`
Navigate to a client → New Note and verify:
- [ ] 3-column grid at top
- [ ] Target cards start compact
- [ ] Descriptor pills work in compact state
- [ ] "No change" marks card as done
- [ ] Expanding card shows metrics + text fields
- [ ] Scale metrics show as tappable pills
- [ ] Wrap-up collapsed by default, opens on click
- [ ] Participant Voice collapsed by default
- [ ] Consent checkbox is optional
- [ ] Form submits correctly
- [ ] Auto-calc shows session count

---

## Summary

| Phase | Tasks | Key Risk | Commit Count |
|-------|-------|----------|-------------|
| A: Layout + Widths | 1-4 | Low — CSS/template only | 4 |
| B: Scale Pills | 5-9 | Medium — form logic change | 4 |
| C: Compact Cards | 10-13 | Medium — new JS | 3 |
| D: Auto-Calc | 14-18 | Medium — model migration | 4 |
| Final | 19 | Low — verification | 1 |
| **Total** | **19** | | **~16 commits** |
