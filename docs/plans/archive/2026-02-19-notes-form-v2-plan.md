# Notes Form Round 2 Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the detailed notes form to align with Feedback-Informed Treatment (FIT): two-lens "Session Overall" section, engagement pills, always-visible participant voice, simplified footer.

**Architecture:** Template restructure (remove `<details>`, two-column layout), form field changes (engagement as RadioSelect, remove consent), CSS additions (engagement pills, two-lens grid, single-line "done" strip), JS updates (completeness counter, card collapse).

**Tech Stack:** Django templates, Pico CSS, vanilla JS, Django forms

**Design doc:** `docs/plans/2026-02-19-notes-form-redesign-v2.md`

---

### Task 1: Remove consent_confirmed from FullNoteForm

The consent checkbox ("I have reviewed this note for accuracy") is being removed from the full note form. It is not referenced in `views.py` at all — it's purely a form field + template element.

**Note:** The QuickNoteForm in the same file has its own `consent_confirmed` field with different wording ("We created this note together"). Do NOT remove that one — it serves a different purpose on the quick note inline form.

**Files:**
- Modify: `apps/notes/forms.py:154` — remove the `consent_confirmed` field from `FullNoteForm`
- Modify: `static/js/app.js:496,521` — remove the `consent_confirmed` skip in autosave
- Test: `tests/test_notes.py` — update all test payloads

**Step 1: Update tests — remove consent_confirmed from all FullNoteForm test payloads**

In `tests/test_notes.py`, remove `"consent_confirmed": True` from every POST data dict that submits to the full note form. There are instances at approximately lines 59, 71, 114, 237, 304, 327, 352, 439, 590, 611. Also update these test files:
- `tests/test_french_journey.py:745`
- `tests/ux_walkthrough/test_scenarios.py:266`
- `tests/ux_walkthrough/test_roles.py:195,245`

Do NOT touch the QuickNoteForm tests — those use a separate consent field.

**Step 2: Run tests to verify they still pass (consent was already `required=False`)**

Run: `pytest tests/test_notes.py -v -x`
Expected: All PASS (field was optional, removing from payload changes nothing yet)

**Step 3: Remove consent_confirmed from FullNoteForm**

In `apps/notes/forms.py`, delete lines 154–157:
```python
    consent_confirmed = forms.BooleanField(
        required=False,
        label=_("I have reviewed this note for accuracy"),
    )
```

**Step 4: Remove consent_confirmed skip from app.js autosave**

In `static/js/app.js`, find the two lines that skip `consent_confirmed` in autosave:
```javascript
if (el.name === "consent_confirmed") return; // Don't save consent - must be re-confirmed
```
Remove both instances (around lines 496 and 521).

**Step 5: Run tests to verify**

Run: `pytest tests/test_notes.py -v -x`
Expected: All PASS

**Step 6: Commit**

```bash
git add apps/notes/forms.py static/js/app.js tests/test_notes.py tests/test_french_journey.py tests/ux_walkthrough/test_scenarios.py tests/ux_walkthrough/test_roles.py
git commit -m "refactor: remove consent_confirmed from FullNoteForm (UX-NOTES2)"
```

---

### Task 2: Update engagement labels and widget to pill buttons

Change engagement from a `<select>` dropdown to pill-style radio buttons with shorter, behavioural labels.

**Files:**
- Modify: `apps/notes/models.py:208-216` — update `ENGAGEMENT_CHOICES` labels
- Modify: `apps/notes/forms.py:126-131` — change widget to RadioSelect
- Modify: `static/css/main.css` — add `.engagement-pills` styles
- Test: `tests/test_notes.py`

**Step 1: Write a test for the new engagement labels**

Add to `tests/test_notes.py` in the `NoteViewsTest` class:

```python
def test_engagement_choices_are_behavioural(self):
    """Engagement labels should use observable behavioural language."""
    from apps.notes.models import ProgressNote
    labels = [label for _, label in ProgressNote.ENGAGEMENT_CHOICES if label != "---------"]
    # Shortened behavioural labels from expert panel
    self.assertIn("Not participating", [str(l) for l in labels])
    self.assertIn("Engaged", [str(l) for l in labels])
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_notes.py::NoteViewsTest::test_engagement_choices_are_behavioural -v`
Expected: FAIL — current labels are "Disengaged", not "Not participating"

**Step 3: Update ENGAGEMENT_CHOICES in models.py**

In `apps/notes/models.py`, replace the `ENGAGEMENT_CHOICES` list (lines 208–216):

```python
ENGAGEMENT_CHOICES = [
    ("", "---------"),
    ("disengaged", _("Not participating")),
    ("motions", _("Going through motions")),
    ("guarded", _("Guarded")),
    ("engaged", _("Engaged")),
    ("valuing", _("Fully invested")),
    ("no_interaction", _("No 1-on-1")),
]
```

Note: the internal values (`disengaged`, `motions`, etc.) stay the same — only the display labels change. No migration needed.

**Step 4: Change engagement_observation to RadioSelect in FullNoteForm**

In `apps/notes/forms.py`, update the `engagement_observation` field (lines 126–131):

```python
engagement_observation = forms.ChoiceField(
    choices=ProgressNote.ENGAGEMENT_CHOICES,
    required=False,
    label=_("Engagement"),
    help_text=_("Your observation — not a score."),
    widget=forms.RadioSelect(attrs={"class": "engagement-pills-input"}),
)
```

**Step 5: Add `.engagement-pills` CSS**

In `static/css/main.css`, add after the `.descriptor-pills` section (around line 3456):

```css
/* Engagement observation pills */
.engagement-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: var(--kn-space-base);
}

.engagement-pills label {
    display: inline-flex;
    align-items: center;
    padding: 0.5rem 1rem;
    border: 2px solid var(--kn-border-light, #ccc);
    border-radius: 999px;
    cursor: pointer;
    font-size: 0.875rem;
    min-height: 44px;
    transition: border-color 0.15s, background 0.15s;
    user-select: none;
    margin-bottom: 0;
    color: var(--kn-text);
}

.engagement-pills input[type="radio"] {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
}

.engagement-pills label:has(input:checked) {
    border-color: var(--kn-primary);
    background: var(--kn-primary-subtle, #e8f0fe);
    font-weight: 500;
}

.engagement-pills label:hover {
    border-color: var(--kn-primary);
}

.engagement-pills label:focus-within {
    outline: 2px solid var(--kn-primary);
    outline-offset: 2px;
}

@media (max-width: 480px) {
    .engagement-pills {
        gap: 0.375rem;
    }
    .engagement-pills label {
        padding: 0.375rem 0.75rem;
        font-size: 0.8125rem;
        min-height: 40px;
    }
}
```

**Step 6: Run tests**

Run: `pytest tests/test_notes.py -v -x`
Expected: All PASS

**Step 7: Commit**

```bash
git add apps/notes/models.py apps/notes/forms.py static/css/main.css tests/test_notes.py
git commit -m "feat: engagement as pill buttons with behavioural labels (UX-NOTES2)"
```

---

### Task 3: Restructure template — two-lens "Session Overall" layout

This is the main template change: remove `<details>` wrappers, create the two-lens layout, update footer.

**Files:**
- Modify: `templates/notes/note_form.html` — full restructure of zones 3–5
- Modify: `static/css/main.css` — `.session-overall`, `.two-lens`, footer changes

**Step 1: Replace Zone 3 (Wrap-up) and Zone 4 (Participant Voice) with two-lens section**

In `templates/notes/note_form.html`, replace everything from `<!-- Zone 3: Wrap-up -->` (line 151) through the closing `</details>` of Zone 4 (line 198) with:

```html
    <!-- Section: The session overall — two-lens FIT layout -->
    <fieldset class="session-overall" aria-label="{% trans 'The session overall' %}">
        <legend><h2>{% trans "The session overall" %}</h2></legend>

        <div class="two-lens">
            <!-- Left lens: Their perspective -->
            <div class="lens lens-participant">
                <h3>{% trans "Their perspective" %}</h3>

                <label for="{{ form.participant_reflection.id_for_label }}">
                    {% blocktrans with client=term.client|default:"Participant" %}How did {{ client }} feel about today's session?{% endblocktrans %}
                </label>
                {{ form.participant_reflection }}
                {% if form.participant_reflection.errors %}<small class="error" id="reflection-error" role="alert">{{ form.participant_reflection.errors.0 }}</small>{% endif %}

                <label for="{{ form.participant_suggestion.id_for_label }}">{% trans "Anything they'd change about the program?" %}</label>
                {{ form.participant_suggestion }}
                {% if form.participant_suggestion.errors %}<small class="error" id="suggestion-error" role="alert">{{ form.participant_suggestion.errors.0 }}</small>{% endif %}

                <div class="suggestion-priority-row" id="suggestion-priority-row" hidden>
                    <label for="{{ form.suggestion_priority.id_for_label }}">{% trans "Priority" %}</label>
                    {{ form.suggestion_priority }}
                    <small>{% trans "Urgent = safety/access · Important = affects many · Worth exploring = good idea · Noted = heard and recorded" %}</small>
                    {% if form.suggestion_priority.errors %}<small class="error" id="priority-error" role="alert">{{ form.suggestion_priority.errors.0 }}</small>{% endif %}
                </div>
            </div>

            <!-- Right lens: Your observations -->
            <div class="lens lens-worker">
                <h3>{% trans "Your observations" %}</h3>

                <label>{% trans "Engagement" %}</label>
                <div class="engagement-pills">
                {% for radio in form.engagement_observation %}
                    {% if radio.choice_value %}
                    <label>{{ radio.tag }}<span>{{ radio.choice_label }}</span></label>
                    {% endif %}
                {% endfor %}
                </div>
                <small>{% trans "Your observation — not a score." %}</small>
                {% if form.engagement_observation.errors %}<small class="error" id="engagement-error" role="alert">{{ form.engagement_observation.errors.0 }}</small>{% endif %}

                <label for="{{ form.summary.id_for_label }}">{% trans "Session notes" %} <small class="secondary">{% trans "(optional)" %}</small></label>
                {{ form.summary }}
                {% if form.summary.errors %}<small class="error" id="summary-error" role="alert">{{ form.summary.errors.0 }}</small>{% endif %}
            </div>
        </div>
    </fieldset>

    <!-- Section: Follow-up -->
    <div class="followup-section">
        <label for="{{ form.follow_up_date.id_for_label }}">{% trans "Follow up by" %}</label>
        {{ form.follow_up_date }}
        <small>{% trans "(optional — adds to your home page reminders)" %}</small>
        {% if form.follow_up_date.errors %}<small class="error" id="follow-up-error" role="alert">{{ form.follow_up_date.errors.0 }}</small>{% endif %}
    </div>
```

**Step 2: Replace the sticky footer — remove consent, add completeness indicator**

Replace the entire `<!-- Sticky footer -->` block (lines 200–220 approximately) with:

```html
    <!-- Sticky footer — simplified -->
    <div class="sticky-form-footer" role="region" aria-label="{% trans 'Save' %}">
        <div class="sticky-form-footer-inner">
            <span class="completeness-indicator" id="completeness-indicator" aria-live="polite" role="status"></span>
            <span class="autosave-indicator" id="autosave-status" hidden aria-live="polite" role="status">
                <span class="status-text">{% trans "Saved" %}</span>
            </span>
            <div class="button-group">
                <a href="{% url 'notes:note_list' client_id=client.pk %}" role="button" class="outline secondary">{% trans "Cancel" %}</a>
                <button type="submit">{% blocktrans with note=term.progress_note|default:"Note" %}Save {{ note }}{% endblocktrans %}</button>
            </div>
        </div>
    </div>
```

**Step 3: Add two-lens CSS**

In `static/css/main.css`, add after the existing `.zone-wrapup` / `.zone-voice` styles (around line 1712). Also remove or comment out the old `.zone-wrapup`, `.zone-voice`, and `.wrapup-grid` styles since they're no longer used.

New CSS:

```css
/* Session Overall — two-lens FIT layout */
.session-overall {
    border: none;
    padding: 0;
    margin-top: var(--kn-space-lg);
    margin-bottom: var(--kn-space-lg);
}
.session-overall legend h2 {
    margin-bottom: var(--kn-space-base);
    padding-top: var(--kn-space-base);
    border-top: 1px solid var(--kn-border-light);
}

.two-lens {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--kn-space-lg);
}

.lens {
    padding: var(--kn-space-base) var(--kn-space-lg);
    border-radius: var(--pico-border-radius);
}

.lens-participant {
    background: var(--kn-primary-subtle, #e8f0fe);
}

.lens-worker {
    background: var(--kn-card-bg, #f8f9fa);
    border: 1px solid var(--kn-border-light);
}

.lens h3 {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: var(--kn-space-base);
    color: var(--kn-text);
}

@media (max-width: 899px) {
    .two-lens {
        grid-template-columns: 1fr;
    }
}

/* Follow-up section — standalone row */
.followup-section {
    margin-top: var(--kn-space-lg);
    margin-bottom: var(--kn-space-lg);
    max-width: 40rem;
}

/* Completeness indicator in footer */
.completeness-indicator {
    font-size: 0.875rem;
    color: var(--kn-text-muted);
    font-weight: 500;
}
```

**Step 4: Update sticky footer CSS — remove consent styles**

In `static/css/main.css`, remove these CSS blocks (they reference the consent section which no longer exists):
- `.sticky-form-footer .consent-section` (line ~2916)
- `.sticky-form-footer .consent-section label` (line ~2924)
- `.sticky-form-footer .consent-section input[type="checkbox"]` (line ~2934)
- `.sticky-form-footer .consent-help` (line ~2941)
- `.sticky-form-footer.has-error` (line ~2975)
- `.sticky-form-footer.has-error .consent-section label` (line ~2980)
- Mobile consent styles inside `@media (max-width: 600px)` (~lines 3021–3028)

**Step 5: Run tests**

Run: `pytest tests/test_notes.py -v -x`
Expected: All PASS

**Step 6: Commit**

```bash
git add templates/notes/note_form.html static/css/main.css
git commit -m "feat: two-lens Session Overall layout, remove consent from footer (UX-NOTES2)"
```

---

### Task 4: Update per-target "In their words" label

Change the label to prompt verbatim capture per FIT methodology.

**Files:**
- Modify: `apps/notes/forms.py:164-168` — update label and help_text

**Step 1: Update TargetNoteForm client_words field**

In `apps/notes/forms.py`, change the `client_words` field in `TargetNoteForm`:

```python
client_words = forms.CharField(
    widget=forms.TextInput(attrs={"placeholder": _("What did they say about this?")}),
    required=False,
    label=_("What did they say about this?"),
)
```

Remove the `help_text` — the label is now self-explanatory.

**Step 2: Run tests**

Run: `pytest tests/test_notes.py -v -x`
Expected: All PASS

**Step 3: Commit**

```bash
git add apps/notes/forms.py
git commit -m "feat: relabel per-target voice field for FIT verbatim capture (UX-NOTES2)"
```

---

### Task 5: "No change" card collapses to single-line strip

When "No change" is clicked, collapse the target card to a minimal done strip.

**Files:**
- Modify: `templates/notes/note_form.html` — update done indicator markup
- Modify: `static/css/main.css` — single-line done strip styling
- Modify: `static/js/app.js` or inline script in template — update "No change" JS

**Step 1: Update the done indicator in the template**

In `templates/notes/note_form.html`, find the target-done-indicator div inside each target card (around line 142) and update to include the target name:

```html
        <!-- Done indicator (hidden until "No change" is clicked) -->
        <div class="target-done-indicator" hidden aria-live="polite">
            <span aria-hidden="true">&#10003;</span> <strong>{{ tf.target.name }}</strong> — {% trans "No change" %}
        </div>
```

**Step 2: Update CSS for single-line done strip**

In `static/css/main.css`, update the `.target-card.done` and `.target-done-indicator` styles:

```css
.target-card.done {
    border-color: var(--kn-success, #10B981);
    background: var(--kn-success-subtle, #ecfdf5);
    padding: var(--kn-space-sm) var(--kn-space-lg);
}

.target-done-indicator {
    color: var(--kn-success, #10B981);
    font-weight: 500;
    font-size: 0.875rem;
}

/* Hide all card content when done — show only the single-line indicator */
.target-card.done .target-card-header,
.target-card.done .target-card-compact,
.target-card.done .target-card-body {
    display: none;
}
```

**Step 3: Update "No change" JS — ensure proper collapse**

In the template's `<script>` block, the existing "No change" handler (lines 264–287) already adds `.done` class and shows the indicator. Verify that hiding the header + compact sections works with the new CSS. No JS changes should be needed — the CSS `display: none` on `.target-card.done .target-card-header` handles it.

If the existing JS explicitly sets `body.hidden = true` but doesn't touch the header/compact, the CSS approach is cleaner. Test in browser to confirm.

**Step 4: Run tests**

Run: `pytest tests/test_notes.py -v -x`
Expected: All PASS

**Step 5: Commit**

```bash
git add templates/notes/note_form.html static/css/main.css
git commit -m "feat: No Change collapses target card to single-line strip (UX-NOTES2)"
```

---

### Task 6: Add "This week" follow-up chip

Add a 5th quick-pick option to the follow-up date picker.

**Files:**
- Modify: `static/js/followup-picker.js:27-53` — add translated labels and option

**Step 1: Add "This week" labels**

In `static/js/followup-picker.js`, add `thisWeek` to both language objects (lines 28–43):

```javascript
var labels = {
    en: {
        tomorrow: "Tomorrow",
        days: "{n} days",
        thisWeek: "This week",
        nextWeek: "Next week",
        weeks: "{n} weeks",
        pickDate: "Pick date",
        followUp: "Follow-up date"
    },
    fr: {
        tomorrow: "Demain",
        days: "{n} jours",
        thisWeek: "Cette semaine",
        nextWeek: "Semaine prochaine",
        weeks: "{n} semaines",
        pickDate: "Choisir une date",
        followUp: "Date de suivi"
    }
};
```

**Step 2: Add "This week" to the options array**

Update the `options` array (lines 48–53) — insert "This week" between "3 days" and "Next week". "This week" = next Friday (end of business week), calculated as days until Friday:

```javascript
// Calculate days until Friday (end of work week)
var dayOfWeek = today.getDay(); // 0=Sun, 1=Mon, ..., 5=Fri, 6=Sat
var daysUntilFriday = (5 - dayOfWeek + 7) % 7;
if (daysUntilFriday === 0) daysUntilFriday = 7; // If today is Friday, next Friday

var options = [
    { label: t.tomorrow, offset: 1 },
    { label: t.days.replace("{n}", "3"), offset: 3 },
    { label: t.thisWeek, offset: daysUntilFriday },
    { label: t.nextWeek, offset: 7 },
    { label: t.weeks.replace("{n}", "2"), offset: 14 }
];
```

**Step 3: Test in browser**

Load the notes form and verify:
- 5 chips appear + "Pick date"
- "This week" shows the correct Friday date
- All chips are keyboard-navigable

**Step 4: Commit**

```bash
git add static/js/followup-picker.js
git commit -m "feat: add This Week follow-up chip (UX-NOTES2)"
```

---

### Task 7: Add completeness indicator in footer

Show a live count of targets recorded in the sticky footer.

**Files:**
- Modify: template inline `<script>` in `templates/notes/note_form.html`

**Step 1: Add completeness counter JS**

In the template's `<script>` block (at the end, before `</script>`), add:

```javascript
// Completeness indicator — counts targets with data
function updateCompleteness() {
    var checkboxes = document.querySelectorAll(".target-selector");
    var selected = 0;
    var recorded = 0;
    checkboxes.forEach(function (cb) {
        if (!cb.checked) return;
        selected++;
        var targetId = cb.getAttribute("data-target-id");
        var card = document.getElementById("target-card-" + targetId);
        if (!card) return;
        // A target is "recorded" if it has a descriptor selected or is marked done
        if (card.classList.contains("done")) { recorded++; return; }
        var checkedRadio = card.querySelector('.descriptor-pills input[type="radio"]:checked');
        if (checkedRadio) recorded++;
    });
    var indicator = document.getElementById("completeness-indicator");
    if (indicator) {
        if (selected > 0) {
            indicator.textContent = "\u2713 " + recorded + " of " + selected + " targets";
        } else {
            indicator.textContent = "";
        }
    }
}
// Run on changes
document.addEventListener("change", updateCompleteness);
document.addEventListener("click", function (e) {
    if (e.target.closest(".no-change-btn") || e.target.closest(".target-selector")) {
        setTimeout(updateCompleteness, 50);
    }
});
updateCompleteness();
```

**Step 2: Test in browser**

- Select 3 targets, record 2 → footer shows "✓ 2 of 3 targets"
- Mark one as "No change" → counter increments
- Deselect a target → counter updates

**Step 3: Commit**

```bash
git add templates/notes/note_form.html
git commit -m "feat: add completeness indicator in footer (UX-NOTES2)"
```

---

### Task 8: Clean up old CSS — remove unused zone styles

**Files:**
- Modify: `static/css/main.css`

**Step 1: Remove or comment out obsolete styles**

Remove these blocks that are no longer used (the `<details>` zones are gone):
- `.zone-wrapup, .zone-voice` (line ~1695)
- `.zone-wrapup > summary, .zone-voice > summary` (line ~1702)
- `.zone-wrapup > summary .secondary, .zone-voice > summary .secondary` (line ~1708)
- `.wrapup-grid` (line ~1675)
- `.field-engagement` (line ~1681)
- `.field-followup` (line ~1682)
- The `@media` block for `.wrapup-grid` (line ~1684)

**Step 2: Commit**

```bash
git add static/css/main.css
git commit -m "chore: remove obsolete zone CSS from notes form (UX-NOTES2)"
```

---

### Task 9: Translations — extract and translate new strings

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

**Step 1: Run string extraction**

```bash
python manage.py translate_strings
```

**Step 2: Translate new French strings**

Open `locale/fr/LC_MESSAGES/django.po` and fill in translations for new/changed strings:

| English | French |
|---------|--------|
| The session overall | La session dans l'ensemble |
| Their perspective | Leur perspective |
| Your observations | Vos observations |
| How did [Client] feel about today's session? | Comment [Client] s'est senti(e) à propos de la session d'aujourd'hui ? |
| Anything they'd change about the program? | Y a-t-il quelque chose qu'ils changeraient dans le programme ? |
| Engagement | Engagement |
| Your observation — not a score. | Votre observation — pas un pointage. |
| Session notes | Notes de session |
| What did they say about this? | Qu'ont-ils dit à ce sujet ? |
| Not participating | Ne participe pas |
| Going through motions | Fait les gestes |
| Guarded | Sur ses gardes |
| Fully invested | Pleinement investi(e) |
| No 1-on-1 | Pas de tête-à-tête |
| This week | Cette semaine |

**Step 3: Compile translations**

```bash
python manage.py translate_strings
```

**Step 4: Commit**

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "i18n: French translations for notes form redesign (UX-NOTES2)"
```

---

### Task 10: Run full test suite and fix any failures

**Step 1: Run notes-related tests**

```bash
pytest tests/test_notes.py tests/test_french_journey.py tests/ux_walkthrough/test_scenarios.py tests/ux_walkthrough/test_roles.py -v
```

Expected: All PASS

**Step 2: Run broader test suite (exclude browser tests)**

```bash
pytest -m "not browser and not scenario_eval" -v
```

Fix any failures.

**Step 3: Commit any fixes**

```bash
git commit -am "fix: test adjustments for notes form redesign (UX-NOTES2)"
```

---

### Task 11: Visual QA — browser verification

**Step 1: Start the dev server**

```bash
python manage.py runserver
```

**Step 2: Verify in browser**

Navigate to a participant's note form and check:

- [ ] Two-lens section visible without scrolling past targets
- [ ] "Their perspective" has light blue background, on the left
- [ ] "Your observations" has neutral background, on the right
- [ ] Engagement renders as pill buttons, not a dropdown
- [ ] Follow-up chips display horizontally
- [ ] "This week" chip shows correct Friday date
- [ ] "No change" collapses card to single green line
- [ ] Footer shows completeness count (no consent checkbox)
- [ ] Scale metrics render as pills (if test data has min/max set)
- [ ] Auto-calc metrics show as inline badge
- [ ] Mobile (resize to 600px): columns stack, participant first
- [ ] Tablet (resize to 899px): columns stack
- [ ] Autosave still works
- [ ] Form submits successfully

**Step 3: Fix any visual issues found**

**Step 4: Final commit**

```bash
git commit -am "fix: visual QA adjustments for notes form (UX-NOTES2)"
```

---

## Data Fix (separate — run after deployment)

Scale metrics that render as text inputs instead of pills need `min_value` and `max_value` set on their `MetricDefinition` records. Check the database:

```python
from apps.plans.models import MetricDefinition
# Find metrics that look like scales but lack min/max
for m in MetricDefinition.objects.all():
    if "1" in m.name.lower() and "5" in m.name.lower() and m.min_value is None:
        print(f"NEEDS FIX: {m.pk} {m.name} — min={m.min_value} max={m.max_value}")
```

Fix via Django admin or a one-off management command.
