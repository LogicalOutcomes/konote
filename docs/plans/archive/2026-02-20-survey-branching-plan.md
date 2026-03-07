# Survey Conditional Branching — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add UI for setting, displaying, and enforcing conditional branching on survey sections — in the builder, admin detail, staff data entry, and portal.

**Architecture:** Server-side section filtering (already built for portal) extended to staff data entry. Builder gets condition fields with dynamic value dropdowns via HTMX. Activation-time validation catches misconfigured conditions. Minimal JS (~20 lines) for staff entry show/hide only.

**Tech Stack:** Django 5, HTMX, Pico CSS, inline JS for staff entry

**Design doc:** `docs/plans/2026-02-20-survey-branching-design.md`

---

## Task 1: Add condition fields to SurveySectionForm

**Files:**
- Modify: `apps/surveys/forms.py:43-66` (SurveySectionForm)
- Test: `tests/test_surveys.py`

**Step 1: Write the failing test**

Add to `tests/test_surveys.py` after the existing `SurveyModelTests` class:

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SurveySectionFormTests(TestCase):
    """Test SurveySectionForm includes condition fields."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="form_staff", password="testpass123",
            display_name="Form Staff",
        )
        self.survey = Survey.objects.create(name="Form Test", created_by=self.staff)
        self.s1 = SurveySection.objects.create(
            survey=self.survey, title="Section 1", sort_order=1,
        )
        self.trigger_q = SurveyQuestion.objects.create(
            section=self.s1, question_text="Has children?",
            question_type="yes_no", sort_order=1,
        )

    def test_form_includes_condition_fields(self):
        from apps.surveys.forms import SurveySectionForm
        form = SurveySectionForm()
        self.assertIn("condition_question", form.fields)
        self.assertIn("condition_value", form.fields)

    def test_form_saves_condition(self):
        from apps.surveys.forms import SurveySectionForm
        form = SurveySectionForm(data={
            "title": "Childcare",
            "sort_order": "2",
            "page_break": "",
            "scoring_method": "none",
            "condition_question": str(self.trigger_q.pk),
            "condition_value": "1",
        })
        self.assertTrue(form.is_valid(), form.errors)
        section = form.save(commit=False)
        section.survey = self.survey
        section.save()
        self.assertEqual(section.condition_question_id, self.trigger_q.pk)
        self.assertEqual(section.condition_value, "1")

    def test_form_valid_without_condition(self):
        from apps.surveys.forms import SurveySectionForm
        form = SurveySectionForm(data={
            "title": "No Condition",
            "sort_order": "1",
            "page_break": "",
            "scoring_method": "none",
            "condition_question": "",
            "condition_value": "",
        })
        self.assertTrue(form.is_valid(), form.errors)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::SurveySectionFormTests -v`
Expected: FAIL — `condition_question` not in form fields

**Step 3: Write minimal implementation**

In `apps/surveys/forms.py`, update `SurveySectionForm.Meta.fields` to include the condition fields:

```python
class SurveySectionForm(forms.ModelForm):
    """Form for a survey section."""

    class Meta:
        model = SurveySection
        fields = [
            "title", "title_fr", "instructions", "instructions_fr",
            "sort_order", "page_break", "scoring_method", "max_score",
            "condition_question", "condition_value",
        ]
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 2}),
            "instructions_fr": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "title": _("Section title"),
            "title_fr": _("Section title (French)"),
            "instructions": _("Instructions"),
            "instructions_fr": _("Instructions (French)"),
            "sort_order": _("Display order"),
            "page_break": _("Start new page"),
            "scoring_method": _("Scoring method"),
            "max_score": _("Maximum score"),
            "condition_question": _("Show only when"),
            "condition_value": _("is answered"),
        }
        help_texts = {
            "condition_question": _("Leave blank to always show this section."),
            "condition_value": _("The answer value that makes this section visible."),
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_surveys.py::SurveySectionFormTests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/surveys/forms.py tests/test_surveys.py
git commit -m "feat: add condition fields to SurveySectionForm"
```

---

## Task 2: HTMX endpoint for condition value options

**Files:**
- Modify: `apps/surveys/views.py` (add `condition_values` view)
- Modify: `apps/surveys/manage_urls.py` (add URL)
- Test: `tests/test_surveys.py`

**Step 1: Write the failing test**

Add to `tests/test_surveys.py`:

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConditionValuesEndpointTests(TestCase):
    """Test the HTMX endpoint that returns condition value options."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="cv_staff", password="testpass123",
            display_name="CV Staff", role="admin",
        )
        self.client.login(username="cv_staff", password="testpass123")
        self.survey = Survey.objects.create(name="CV Test", created_by=self.staff)
        self.section = SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )

    def test_yes_no_returns_two_options(self):
        q = SurveyQuestion.objects.create(
            section=self.section, question_text="Yes or no?",
            question_type="yes_no", sort_order=1,
        )
        url = f"/manage/surveys/{self.survey.pk}/condition-values/{q.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('value="1"', content)
        self.assertIn('value="0"', content)

    def test_single_choice_returns_option_values(self):
        q = SurveyQuestion.objects.create(
            section=self.section, question_text="Pick one",
            question_type="single_choice", sort_order=1,
            options_json=[
                {"value": "a", "label": "Alpha"},
                {"value": "b", "label": "Beta"},
            ],
        )
        url = f"/manage/surveys/{self.survey.pk}/condition-values/{q.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('value="a"', content)
        self.assertIn("Alpha", content)
        self.assertIn('value="b"', content)

    def test_text_question_returns_text_input(self):
        q = SurveyQuestion.objects.create(
            section=self.section, question_text="Name?",
            question_type="short_text", sort_order=1,
        )
        url = f"/manage/surveys/{self.survey.pk}/condition-values/{q.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('type="text"', content)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::ConditionValuesEndpointTests -v`
Expected: FAIL — 404, URL doesn't exist

**Step 3: Write the view**

Add to `apps/surveys/views.py` after the existing management views (around line 236):

```python
@login_required
@requires_permission("template.note.manage", allow_admin=True)
def condition_values(request, survey_id, question_id):
    """Return HTML options for the condition_value dropdown (HTMX)."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)
    question = get_object_or_404(
        SurveyQuestion, pk=question_id, section__survey=survey,
    )

    if question.question_type == "yes_no":
        options = [("1", _("Yes")), ("0", _("No"))]
    elif question.question_type in ("single_choice", "multiple_choice", "rating_scale"):
        options = [
            (opt["value"], opt.get("label", opt["value"]))
            for opt in (question.options_json or [])
        ]
    else:
        # short_text / long_text — return a text input instead of a select
        html = (
            '<input type="text" name="condition_value" '
            f'placeholder="{_("Type the exact answer value")}">'
        )
        return HttpResponse(html)

    html_parts = [f'<option value="">— {_("Select a value")} —</option>']
    for value, label in options:
        html_parts.append(f'<option value="{value}">{label}</option>')
    return HttpResponse("\n".join(html_parts))
```

Add the import at the top of `apps/surveys/views.py`:

```python
from django.http import Http404, HttpResponse, HttpResponseForbidden
```

**Step 4: Add the URL**

Add to `apps/surveys/manage_urls.py`:

```python
path(
    "<int:survey_id>/condition-values/<int:question_id>/",
    views.condition_values,
    name="condition_values",
),
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_surveys.py::ConditionValuesEndpointTests -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/surveys/views.py apps/surveys/manage_urls.py tests/test_surveys.py
git commit -m "feat: add HTMX endpoint for condition value options"
```

---

## Task 3: Render condition fields in survey builder template

**Files:**
- Modify: `templates/surveys/admin/survey_form.html`
- Modify: `apps/surveys/views.py` (survey_create and survey_edit — set queryset)

**Step 1: Update the views to set condition_question queryset**

In `apps/surveys/views.py`, modify `survey_create` (around line 73) — after creating the formset, set the queryset on each form. Since this is a new survey with no saved questions yet, the queryset should be empty for create:

```python
# In survey_create, after the else block (GET):
form = SurveyForm()
formset = SectionFormSet()
for section_form in formset:
    section_form.fields["condition_question"].queryset = SurveyQuestion.objects.none()
```

In `survey_edit` (around line 99), set the queryset to questions from this survey:

```python
# In survey_edit, after creating the formset (both POST and GET branches):
all_questions = SurveyQuestion.objects.filter(
    section__survey=survey, section__is_active=True,
).select_related("section").order_by("section__sort_order", "sort_order")
for section_form in formset:
    section_form.fields["condition_question"].queryset = all_questions
    section_form.fields["condition_question"].label_from_instance = (
        lambda q: f"{q.section.title} → {q.question_text[:60]}"
    )
```

Also do the same for the POST branch in both views (when re-rendering after validation errors).

**Step 2: Update the template**

In `templates/surveys/admin/survey_form.html`, the section formset loop currently renders all fields generically. Modify the section `<article>` to render condition fields as a readable sentence. Replace the generic field loop (lines 37-43) with explicit rendering that groups the condition fields:

```html
{{ section_form.id }}
{% for field in section_form %}
    {% if field.name != "id" and field.name != "DELETE" and field.name != "condition_question" and field.name != "condition_value" %}
    <label for="{{ field.id_for_label }}">{{ field.label }}</label>
    {{ field }}
    {% if field.help_text %}<small>{{ field.help_text }}</small>{% endif %}
    {% if field.errors %}<small class="error" role="alert">{{ field.errors.0 }}</small>{% endif %}
    {% endif %}
{% endfor %}

{# Condition fields rendered as a sentence #}
<fieldset>
    <legend><small>{% trans "Conditional visibility" %}</small></legend>
    <p>
        <label for="{{ section_form.condition_question.id_for_label }}">
            {% trans "Show only when" %}
        </label>
        {{ section_form.condition_question }}
        <label for="{{ section_form.condition_value.id_for_label }}">
            {% trans "is answered" %}
        </label>
        <span
            id="condition-value-wrapper-{{ forloop.counter0 }}"
            hx-get=""
            hx-trigger="change from:[name='{{ section_form.condition_question.html_name }}']"
            hx-include="[name='{{ section_form.condition_question.html_name }}']"
        >
            {{ section_form.condition_value }}
        </span>
    </p>
    <small>{% trans "Leave blank to always show this section." %}</small>
</fieldset>
```

The HTMX `hx-get` URL will be set dynamically via JS or inline — when the condition_question dropdown changes, it fetches from `/manage/surveys/<survey_id>/condition-values/<question_id>/` and replaces the condition_value dropdown contents.

**Step 3: Commit**

```bash
git add templates/surveys/admin/survey_form.html apps/surveys/views.py
git commit -m "feat: render condition fields in survey builder"
```

---

## Task 4: Conditional badge in admin detail and questions views

**Files:**
- Modify: `templates/surveys/admin/survey_detail.html:48-67`
- Modify: `templates/surveys/admin/survey_questions.html:24-30`

**Step 1: Update survey_detail.html**

In the section loop (line 49), after `<header>{{ section.title }}</header>`, add:

```html
{% if section.condition_question %}
<p><small>
    <strong>{% trans "Conditional" %}</strong> —
    {% blocktrans with question=section.condition_question.question_text value=section.condition_value %}
    shown when "{{ question }}" is answered "{{ value }}"
    {% endblocktrans %}
</small></p>
{% endif %}
```

**Step 2: Update survey_questions.html**

In the section header (line 26), after the title `<strong>`, add the same badge:

```html
<header>
    <strong>{{ section.title }}</strong>
    {% if section.condition_question %}
    <br><small>
        <strong>{% trans "Conditional" %}</strong> —
        {% blocktrans with question=section.condition_question.question_text value=section.condition_value %}
        shown when "{{ question }}" is answered "{{ value }}"
        {% endblocktrans %}
    </small>
    {% endif %}
    {% if section.instructions %}
    <br><small>{{ section.instructions }}</small>
    {% endif %}
</header>
```

**Step 3: Update the detail view to select_related**

In `apps/surveys/views.py`, `survey_detail` view (line 128), add `select_related` for the condition question:

```python
sections = survey.sections.filter(is_active=True).prefetch_related("questions").select_related("condition_question")
```

Same for `survey_questions` view (line 147):

```python
sections = survey.sections.filter(is_active=True).order_by("sort_order").select_related("condition_question")
```

**Step 4: Commit**

```bash
git add templates/surveys/admin/survey_detail.html templates/surveys/admin/survey_questions.html apps/surveys/views.py
git commit -m "feat: show conditional badge in admin detail and questions views"
```

---

## Task 5: Staff data entry — server-side filtering on POST

**Files:**
- Modify: `apps/surveys/views.py:497-576` (staff_data_entry)
- Test: `tests/test_surveys.py`

**Step 1: Write the failing test**

Add to `tests/test_surveys.py`:

```python
@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-staff",
)
class StaffDataEntryConditionTests(TestCase):
    """Test staff data entry respects conditional sections."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="sde_staff", password="testpass123",
            display_name="SDE Staff", role="admin",
        )
        self.client_obj = ClientFile.objects.create(
            record_id="SDE-001", status="active",
        )
        self.client_obj.first_name = "Test"
        self.client_obj.last_name = "Client"
        self.client_obj.save()
        # Ensure staff can access this client
        self.program = Program.objects.create(name="SDE Program")
        ClientProgramEnrolment.objects.create(
            client_file=self.client_obj, program=self.program,
        )
        self.staff.accessible_programs.add(self.program)

        self.survey = Survey.objects.create(
            name="Condition Entry", created_by=self.staff, status="active",
        )
        self.s1 = SurveySection.objects.create(
            survey=self.survey, title="Main", sort_order=1,
        )
        self.trigger_q = SurveyQuestion.objects.create(
            section=self.s1, question_text="Has children?",
            question_type="yes_no", sort_order=1, required=True,
        )
        self.s2 = SurveySection.objects.create(
            survey=self.survey, title="Childcare", sort_order=2,
            condition_question=self.trigger_q, condition_value="1",
        )
        self.cond_q = SurveyQuestion.objects.create(
            section=self.s2, question_text="Childcare needed?",
            question_type="yes_no", sort_order=1, required=True,
        )
        FeatureToggle.objects.update_or_create(
            name="surveys", defaults={"is_enabled": True},
        )
        self.client.login(username="sde_staff", password="testpass123")

    def test_hidden_section_required_field_not_enforced(self):
        """When trigger answer hides a section, its required fields don't cause errors."""
        url = f"/surveys/participant/{self.client_obj.pk}/enter/{self.survey.pk}/"
        resp = self.client.post(url, {
            f"q_{self.trigger_q.pk}": "0",  # No — hides childcare section
            # cond_q not submitted (section hidden by JS)
        })
        # Should succeed — childcare section is hidden, required not enforced
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(SurveyResponse.objects.count(), 1)

    def test_visible_section_required_field_enforced(self):
        """When trigger answer shows a section, its required fields are enforced."""
        url = f"/surveys/participant/{self.client_obj.pk}/enter/{self.survey.pk}/"
        resp = self.client.post(url, {
            f"q_{self.trigger_q.pk}": "1",  # Yes — shows childcare section
            # cond_q not submitted — should cause error
        })
        # Should fail — childcare section visible, required field missing
        self.assertEqual(resp.status_code, 200)  # re-renders form with error
        self.assertEqual(SurveyResponse.objects.count(), 0)

    def test_extra_answers_from_hidden_section_saved(self):
        """If JS didn't hide section and staff filled it in, answers are still saved."""
        url = f"/surveys/participant/{self.client_obj.pk}/enter/{self.survey.pk}/"
        resp = self.client.post(url, {
            f"q_{self.trigger_q.pk}": "0",  # No — hides childcare
            f"q_{self.cond_q.pk}": "1",     # But staff submitted anyway (JS failed)
        })
        self.assertEqual(resp.status_code, 302)
        response = SurveyResponse.objects.first()
        # Both answers saved — extra data preserved
        self.assertEqual(response.answers.count(), 2)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::StaffDataEntryConditionTests -v`
Expected: FAIL — required field error on hidden section

**Step 3: Update the staff_data_entry view**

Replace the POST handling in `apps/surveys/views.py` `staff_data_entry` (lines 512-568). The key change: build answers dict first, call `filter_visible_sections()`, then only enforce `required` on visible sections:

```python
    if request.method == "POST":
        from apps.portal.survey_helpers import filter_visible_sections

        # 1. Collect all submitted answers
        all_answers = {}
        for section in sections:
            for question in section.questions.all().order_by("sort_order"):
                field_name = f"q_{question.pk}"
                if question.question_type == "multiple_choice":
                    raw_values = request.POST.getlist(field_name)
                    raw_value = ";".join(raw_values) if raw_values else ""
                else:
                    raw_value = request.POST.get(field_name, "").strip()
                if raw_value:
                    all_answers[question.pk] = raw_value

        # 2. Determine which sections are visible based on answers
        all_sections_list = list(sections)
        visible_sections = filter_visible_sections(all_sections_list, all_answers)
        visible_section_pks = {s.pk for s in visible_sections}

        # 3. Validate required fields only in visible sections
        errors = []
        answers_data = []
        for section in sections:
            for question in section.questions.all().order_by("sort_order"):
                raw_value = all_answers.get(question.pk, "")
                if (question.required
                        and not raw_value
                        and section.pk in visible_section_pks):
                    errors.append(question.question_text)
                if raw_value:
                    answers_data.append((question, raw_value))

        if errors:
            messages.error(
                request,
                _("Please answer all required questions."),
            )
            return render(request, "surveys/staff_data_entry.html", {
                "client": client,
                "survey": survey,
                "sections": sections,
                "posted": request.POST,
                "breadcrumbs": _staff_entry_breadcrumbs(request, client, survey),
            })

        # 4. Save all submitted answers (even from hidden sections)
        with transaction.atomic():
            response = SurveyResponse.objects.create(
                survey=survey,
                client_file=client,
                channel="staff_entered",
            )
            for question, raw_value in answers_data:
                answer = SurveyAnswer(
                    response=response,
                    question=question,
                )
                answer.value = raw_value
                if question.question_type in ("rating_scale", "yes_no"):
                    try:
                        answer.numeric_value = int(raw_value)
                    except (ValueError, TypeError):
                        pass
                elif question.question_type == "single_choice":
                    for opt in (question.options_json or []):
                        if opt.get("value") == raw_value:
                            answer.numeric_value = opt.get("score")
                            break
                answer.save()

        messages.success(request, _("Survey response saved."))
        return redirect("surveys:client_surveys", client_id=client_id)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_surveys.py::StaffDataEntryConditionTests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/surveys/views.py tests/test_surveys.py
git commit -m "feat: staff data entry filters sections by condition on POST"
```

---

## Task 6: Staff data entry template — JS show/hide

**Files:**
- Modify: `templates/surveys/staff_data_entry.html`

**Step 1: Add data attributes and JS to the template**

Replace the section loop and add the JS. Each section gets `data-condition-*` attributes if conditional:

```html
{% for section in sections %}
<fieldset
    {% if section.condition_question_id %}
    data-condition-question="q_{{ section.condition_question_id }}"
    data-condition-value="{{ section.condition_value }}"
    style="display:none"
    {% endif %}
>
    <legend>{{ section.title }}</legend>
    {% if section.condition_question %}
    <p class="condition-note" style="display:none">
        <small class="secondary">
            {% blocktrans with question=section.condition_question.question_text value=section.condition_value %}
            This section appears because "{{ question }}" was answered "{{ value }}".
            {% endblocktrans %}
        </small>
    </p>
    {% endif %}
    {% if section.instructions %}<p><small>{{ section.instructions }}</small></p>{% endif %}

    {% for question in section.questions.all %}
    <div class="form-group" style="margin-bottom:1.5rem">
        {# ... existing question rendering unchanged ... #}
    </div>
    {% endfor %}
</fieldset>
{% endfor %}
```

Add the JS before `</form>` or in a `{% block extra_js %}`:

```html
<script>
(function() {
    function evaluateConditions() {
        document.querySelectorAll("fieldset[data-condition-question]").forEach(function(fs) {
            var qName = fs.dataset.conditionQuestion;
            var expected = fs.dataset.conditionValue;
            var inputs = document.querySelectorAll("[name='" + qName + "']");
            var actual = "";
            inputs.forEach(function(el) {
                if (el.type === "radio" || el.type === "checkbox") {
                    if (el.checked) actual = el.value;
                } else {
                    actual = el.value;
                }
            });
            var visible = (actual === expected);
            fs.style.display = visible ? "" : "none";
            var note = fs.querySelector(".condition-note");
            if (note) note.style.display = visible ? "" : "none";
            // Disable/enable inputs so hidden required fields don't block submit
            fs.querySelectorAll("input, select, textarea").forEach(function(el) {
                if (!el.name.startsWith("q_")) return;
                el.disabled = !visible;
            });
        });
    }
    // Run on page load and on any input change
    evaluateConditions();
    document.querySelector("form").addEventListener("change", evaluateConditions);
})();
</script>
```

**Step 2: Update the view to select_related for condition_question**

In `staff_data_entry` GET path, update the sections queryset:

```python
sections = survey.sections.filter(
    is_active=True,
).prefetch_related("questions").select_related("condition_question").order_by("sort_order")
```

**Step 3: Commit**

```bash
git add templates/surveys/staff_data_entry.html apps/surveys/views.py
git commit -m "feat: staff data entry JS show/hide for conditional sections"
```

---

## Task 7: Activation-time validation

**Files:**
- Modify: `apps/surveys/views.py` (survey_status view, ~line 217)
- Modify: `apps/surveys/views.py` (survey_questions activate action, ~line 201)
- Test: `tests/test_surveys.py`

**Step 1: Write the failing test**

Add to `tests/test_surveys.py`:

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ActivationValidationTests(TestCase):
    """Test activation-time validation of conditional sections."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="act_staff", password="testpass123",
            display_name="Act Staff", role="admin",
        )
        self.client.login(username="act_staff", password="testpass123")
        FeatureToggle.objects.update_or_create(
            name="surveys", defaults={"is_enabled": True},
        )

    def test_activation_blocked_with_invalid_condition_value(self):
        """Cannot activate survey if condition_value doesn't match any answer."""
        survey = Survey.objects.create(
            name="Bad Condition", created_by=self.staff, status="draft",
        )
        s1 = SurveySection.objects.create(
            survey=survey, title="Main", sort_order=1,
        )
        trigger_q = SurveyQuestion.objects.create(
            section=s1, question_text="Yes or no?",
            question_type="yes_no", sort_order=1,
        )
        SurveySection.objects.create(
            survey=survey, title="Conditional", sort_order=2,
            condition_question=trigger_q, condition_value="yes",  # Wrong! Should be "1"
        )
        url = f"/manage/surveys/{survey.pk}/status/"
        resp = self.client.post(url, {"status": "active"})
        survey.refresh_from_db()
        self.assertEqual(survey.status, "draft")  # Not activated

    def test_activation_allowed_with_valid_condition(self):
        """Can activate survey when condition_value matches a real answer."""
        survey = Survey.objects.create(
            name="Good Condition", created_by=self.staff, status="draft",
        )
        s1 = SurveySection.objects.create(
            survey=survey, title="Main", sort_order=1,
        )
        trigger_q = SurveyQuestion.objects.create(
            section=s1, question_text="Yes or no?",
            question_type="yes_no", sort_order=1,
        )
        SurveySection.objects.create(
            survey=survey, title="Conditional", sort_order=2,
            condition_question=trigger_q, condition_value="1",  # Correct
        )
        url = f"/manage/surveys/{survey.pk}/status/"
        resp = self.client.post(url, {"status": "active"})
        survey.refresh_from_db()
        self.assertEqual(survey.status, "active")

    def test_activation_blocked_with_forward_reference(self):
        """Cannot activate if condition_question is in a later section."""
        survey = Survey.objects.create(
            name="Forward Ref", created_by=self.staff, status="draft",
        )
        s1 = SurveySection.objects.create(
            survey=survey, title="First", sort_order=1,
        )
        s2 = SurveySection.objects.create(
            survey=survey, title="Second", sort_order=2,
        )
        later_q = SurveyQuestion.objects.create(
            section=s2, question_text="Later question",
            question_type="yes_no", sort_order=1,
        )
        # s1 depends on a question in s2 (forward reference)
        s1.condition_question = later_q
        s1.condition_value = "1"
        s1.save()
        url = f"/manage/surveys/{survey.pk}/status/"
        resp = self.client.post(url, {"status": "active"})
        survey.refresh_from_db()
        self.assertEqual(survey.status, "draft")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::ActivationValidationTests -v`
Expected: FAIL — survey activates without validation

**Step 3: Write the validation helper**

Add a helper function to `apps/surveys/views.py`:

```python
def _validate_survey_conditions(survey):
    """Validate all conditional sections have valid conditions.

    Returns a list of error message strings. Empty list means valid.
    """
    errors = []
    sections = survey.sections.filter(
        is_active=True, condition_question__isnull=False,
    ).select_related("condition_question", "condition_question__section")

    for section in sections:
        cq = section.condition_question
        # Check forward reference
        if cq.section.sort_order >= section.sort_order:
            errors.append(
                _('Section "%(section)s" depends on a question in "%(other)s" '
                  "which is not an earlier section.")
                % {"section": section.title, "other": cq.section.title}
            )
            continue

        # Check condition_value is valid for the question type
        valid_values = _get_valid_condition_values(cq)
        if valid_values is not None and section.condition_value not in valid_values:
            errors.append(
                _('Section "%(section)s" has condition value "%(value)s" '
                  'which is not a valid answer for "%(question)s".')
                % {
                    "section": section.title,
                    "value": section.condition_value,
                    "question": cq.question_text,
                }
            )
    return errors


def _get_valid_condition_values(question):
    """Return set of valid answer values for a question, or None if any value is OK."""
    if question.question_type == "yes_no":
        return {"1", "0"}
    elif question.question_type in ("single_choice", "multiple_choice", "rating_scale"):
        return {opt["value"] for opt in (question.options_json or [])}
    else:
        # short_text / long_text — any value is valid
        return None
```

**Step 4: Wire validation into survey_status view**

In `survey_status` (around line 221), add validation before activating:

```python
if new_status in dict(Survey.STATUS_CHOICES):
    # Validate conditions when activating
    if new_status == "active" and survey.status == "draft":
        condition_errors = _validate_survey_conditions(survey)
        if condition_errors:
            for err in condition_errors:
                messages.error(request, err)
            return redirect("survey_manage:survey_detail", survey_id=survey.pk)

    old_status = survey.status
    # ... rest of existing code
```

Also wire into the `survey_questions` activate action (around line 201):

```python
elif action == "activate":
    condition_errors = _validate_survey_conditions(survey)
    if condition_errors:
        for err in condition_errors:
            messages.error(request, err)
        return redirect("survey_manage:survey_questions", survey_id=survey.pk)
    survey.status = "active"
    survey.save(update_fields=["status"])
    messages.success(request, _("Survey is now active."))
    return redirect("survey_manage:survey_detail", survey_id=survey.pk)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_surveys.py::ActivationValidationTests -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/surveys/views.py tests/test_surveys.py
git commit -m "feat: activation-time validation for conditional sections"
```

---

## Task 8: Question deletion warning

**Files:**
- Modify: `templates/surveys/admin/survey_questions.html`
- Modify: `apps/surveys/views.py` (delete_question action, ~line 190)

**Step 1: Update the delete button in survey_questions.html**

In the question delete form (around line 52), add a JS confirmation that checks for dependent sections. The view will pass dependency info as a data attribute:

```html
<form method="post" style="margin-left:1rem"
    {% if q.dependent_sections.exists %}
    onsubmit="return confirm('{% blocktrans with section_titles=q.dependent_section_titles %}This question is a condition trigger for: {{ section_titles }}. Deleting it will make those sections always visible. Continue?{% endblocktrans %}')"
    {% endif %}
>
```

Since `dependent_sections` is already a reverse FK (`related_name="dependent_sections"`), we can access it in the template. But we need a helper property or annotation. Simpler approach: add the confirmation in the view's delete handler instead. In the template, just add a generic `onsubmit` confirm:

```html
<form method="post" style="margin-left:1rem">
    {% csrf_token %}
    <input type="hidden" name="action" value="delete_question">
    <input type="hidden" name="question_id" value="{{ q.pk }}">
    <button type="submit" class="outline secondary"
            aria-label="{% trans 'Remove question' %}"
            onclick="return confirm('{% trans "Remove this question?" %}')">✕</button>
</form>
```

In the view's `delete_question` handler, after finding the question, check for dependent sections and add an info message:

```python
elif action == "delete_question":
    question_id = request.POST.get("question_id")
    question = get_object_or_404(
        SurveyQuestion, pk=question_id, section__survey=survey,
    )
    # Warn about dependent sections that will become unconditional
    dependent = list(
        SurveySection.objects.filter(condition_question=question)
        .values_list("title", flat=True)
    )
    question.delete()
    if dependent:
        messages.warning(
            request,
            _("The following sections are now always visible (their condition "
              "trigger was removed): %(sections)s")
            % {"sections": ", ".join(dependent)},
        )
    messages.success(request, _("Question removed."))
```

**Step 2: Commit**

```bash
git add templates/surveys/admin/survey_questions.html apps/surveys/views.py
git commit -m "feat: warn when deleting a question used as condition trigger"
```

---

## Task 9: Translations

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

**Step 1: Run translate_strings to extract new strings**

```bash
python manage.py translate_strings
```

**Step 2: Fill in French translations for new strings**

Key new strings to translate:
- "Show only when" → "Afficher seulement quand"
- "is answered" → "la réponse est"
- "Leave blank to always show this section." → "Laisser vide pour toujours afficher cette section."
- "The answer value that makes this section visible." → "La valeur de réponse qui rend cette section visible."
- "Conditional" → "Conditionnel"
- "shown when ..." → "affiché quand ..."
- "This section appears because ..." → "Cette section apparaît parce que ..."
- "Select a value" → "Sélectionner une valeur"
- "Type the exact answer value" → "Tapez la valeur exacte de la réponse"
- "Conditional visibility" → "Visibilité conditionnelle"
- Activation error messages
- Deletion warning message

**Step 3: Recompile**

```bash
python manage.py translate_strings
```

**Step 4: Commit**

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "i18n: add French translations for survey branching"
```

---

## Task 10: Run related tests and verify

**Step 1: Run all survey and portal survey tests**

```bash
pytest tests/test_surveys.py tests/test_portal_surveys.py -v
```

Expected: All tests pass, including existing conditional section tests and new tests.

**Step 2: Commit any fixes if needed**

---

## Summary

| Task | Description | Test file |
|------|-------------|-----------|
| 1 | Add condition fields to SurveySectionForm | test_surveys.py |
| 2 | HTMX endpoint for condition value options | test_surveys.py |
| 3 | Render condition fields in builder template | Manual |
| 4 | Conditional badge in admin detail/questions | Manual |
| 5 | Staff data entry — server-side filtering on POST | test_surveys.py |
| 6 | Staff data entry — JS show/hide template | Manual |
| 7 | Activation-time validation | test_surveys.py |
| 8 | Question deletion warning | Manual |
| 9 | Translations | Manual |
| 10 | Run all related tests | — |
