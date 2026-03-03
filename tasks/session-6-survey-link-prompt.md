# Session 6: SURVEY-LINK1 — Shareable Link Enhancements

## Pre-flight (do first, sequentially)

```
git pull origin develop
git checkout -b feat/survey-link-enhancements develop
```

Read the design doc before starting: `tasks/survey-link-design.md` — it has the full gap analysis, expert panel decisions, and implementation plan.

---

## Context

The shareable link channel for public surveys (no login needed) **already works**. The core is done: SurveyLink model, public views at `/s/<token>/`, staff UI to create/manage links, all 6 question types, honeypot anti-spam, validation with repopulation, bilingual page chrome, WCAG skip link.

This session closes **7 gaps** between the public form and the portal form, split into Phase 1 (must-have) and Phase 2 (UX polish). All decisions have been reviewed and approved by an expert panel — see the "Decisions" table at the bottom of the design doc.

---

## Phase 1 — Must-Have (do these first, in order)

### Task 1: Bilingual template filter for survey content

**Problem:** The public form template always shows English question text (`{{ question.question_text }}`, `{{ opt.label }}`), even when the respondent has toggled to French. The page chrome is bilingual but the actual survey content is not. The portal form (`apps/portal/templates/portal/survey_fill.html`) has the same gap.

**What to do:**

1. Add a `bilingual` template filter to `apps/portal/templatetags/survey_tags.py` (this file already exists with `partial_value` and `in_multi_value` filters):

```python
@register.filter
def bilingual(en_value, fr_value):
    """Return FR text when language is French and FR text exists, else EN."""
    from django.utils.translation import get_language
    if get_language() == "fr" and fr_value:
        return fr_value
    return en_value
```

2. Update `templates/surveys/public_form.html` — replace all hardcoded EN references:
   - `{{ survey.name }}` → `{{ survey.name|bilingual:survey.name_fr }}`
   - `{{ survey.description }}` → `{{ survey.description|bilingual:survey.description_fr }}`
   - `{{ section.title }}` → `{{ section.title|bilingual:section.title_fr }}`
   - `{{ section.instructions }}` → `{{ section.instructions|bilingual:section.instructions_fr }}`
   - `{{ question.question_text }}` → `{{ question.question_text|bilingual:question.question_text_fr }}`
   - `{{ opt.label }}` → `{{ opt.label|bilingual:opt.label_fr }}`

3. Apply the same changes to the portal templates (same gap):
   - `apps/portal/templates/portal/survey_fill.html`
   - `apps/portal/templates/portal/survey_review.html`

**Test:** `test_public_survey_bilingual_content` — set language to FR, load a survey with FR text populated, verify FR content appears in the response HTML.

### Task 2: Conditional section visibility (server-side + client-side)

**Problem:** The public form renders ALL active sections, ignoring `condition_question` and `condition_value` fields. If a section should only appear when a specific question has a specific answer, it currently shows unconditionally.

**What to do:**

1. **Server-side (public_views.py):** Import `filter_visible_sections` from `apps/portal/survey_helpers.py`.

   - On GET: call `filter_visible_sections(sections_list, {})` — empty answers dict means only unconditional sections render.
   - On POST: build `all_answers` dict from submitted form data (same pattern as `apps/surveys/views.py` line 560-576), then call `filter_visible_sections(sections_list, all_answers)` to determine visible sections. Only validate required fields in visible sections.

   The portal view (`apps/surveys/views.py`, `staff_data_entry` function, lines 555-600) already does this exact pattern — use it as reference. Key lines:

   ```python
   from apps.portal.survey_helpers import filter_visible_sections

   sections_list = list(sections)

   # On GET:
   visible_sections = filter_visible_sections(sections_list, {})

   # On POST:
   all_answers = {}
   for section in sections_list:
       for question in section.questions.all().order_by("sort_order"):
           field_name = f"q_{question.pk}"
           if question.question_type == "multiple_choice":
               raw_values = request.POST.getlist(field_name)
               all_answers[question.pk] = ";".join(raw_values)
           else:
               all_answers[question.pk] = request.POST.get(field_name, "").strip()

   visible_sections = filter_visible_sections(sections_list, all_answers)
   visible_pks = {s.pk for s in visible_sections}

   # Only validate required fields in visible sections:
   for section in visible_sections:
       for question in section.questions.all().order_by("sort_order"):
           ...
   ```

2. **Client-side (public_form.html):** Add data attributes to conditional fieldsets and a small JS block.

   On each `<fieldset>` for a section that has a `condition_question`:
   ```html
   <fieldset data-condition-question="q_{{ section.condition_question_id }}"
             data-condition-value="{{ section.condition_value }}"
             {% if section.condition_question_id %}hidden{% endif %}>
   ```

   Add JS at the bottom of the template:
   ```javascript
   document.addEventListener('DOMContentLoaded', function() {
       var conditionals = document.querySelectorAll('[data-condition-question]');
       if (!conditionals.length) return;

       conditionals.forEach(function(fieldset) {
           var qName = fieldset.dataset.conditionQuestion;
           var expected = fieldset.dataset.conditionValue;
           var inputs = document.querySelectorAll('[name="' + qName + '"]');

           function check() {
               var val = '';
               inputs.forEach(function(inp) {
                   if (inp.type === 'radio' || inp.type === 'checkbox') {
                       if (inp.checked) val = inp.value;
                   } else {
                       val = inp.value;
                   }
               });
               fieldset.hidden = (val !== expected);
           }

           inputs.forEach(function(inp) {
               inp.addEventListener('change', check);
           });
       });
   });
   ```

   **Accessibility note (from expert panel):** Use `hidden` attribute (not CSS `display:none` or `visibility:hidden`). Do NOT force focus to newly revealed sections — instead, add a brief live-region announcement:
   ```html
   <div id="section-announce" role="status" aria-live="polite" class="visually-hidden"></div>
   ```
   When a section becomes visible, set its text to "Additional questions appeared below."

**Tests:**
- `test_public_survey_conditional_sections` — create a survey with a conditional section, GET the form, verify the conditional section is NOT in the HTML. POST with the trigger answer, verify the conditional section IS included.
- `test_public_survey_conditional_validation` — POST without the trigger answer and leave conditional section's required fields empty. Verify no validation error.

### Task 3: Audit trail for public submissions

**Problem:** Portal submissions are logged via `_audit_portal_event()`. Public link submissions leave no audit trail.

**What to do:**

In `apps/surveys/public_views.py`, after the `SurveyResponse.objects.create()` call inside the `transaction.atomic()` block, add:

```python
from apps.audit.models import AuditLog

AuditLog.objects.using("audit").create(
    action="public_survey_submitted",
    details=f"Survey: {survey.name} (ID {survey.pk}), Link: {link.token[:8]}..., Response ID: {response.pk}, Anonymous: {survey.is_anonymous}",
)
```

Do NOT log respondent_name or IP address (PIPEDA 4.4 — Limiting Collection, confirmed by expert panel).

**Test:** `test_public_survey_audit_trail` — submit a public survey, query `AuditLog.objects.using("audit")` for `action="public_survey_submitted"`, verify one entry exists with the correct survey ID.

### Task 4: Rate limiting

**Problem:** The public form has no rate limiting. Honeypot catches dumb bots but not scripted spam.

**What to do:**

Add the `@ratelimit` decorator to `public_survey_form` in `apps/surveys/public_views.py`:

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key="ip", rate="30/h", method="POST", block=True)
def public_survey_form(request, token):
    ...
```

This is the same pattern used in `apps/auth_app/views.py`, `apps/portal/views.py`, `apps/events/views.py`, and `konote/ai_views.py`. The library is already installed (`django-ratelimit>=4.1,<5.0` in `requirements.txt`).

The 30/hour threshold is deliberately generous — community settings have shared devices at libraries, shelters, and community centres where many people may submit from the same IP.

**Test:** `test_public_survey_rate_limit` — this is tricky to unit test with django-ratelimit. At minimum, verify the decorator is applied by checking the view function's attributes or by checking the import exists. If the test framework supports it, simulate 31 POST requests and verify the 31st returns 403.

### Task 5: Rename respondent name field label

**Problem:** The "Your name (optional)" label encourages full legal names. Expert panel recommends discouraging PII collection through field labelling.

**What to do:**

In `templates/surveys/public_form.html`, change:
```html
<label for="respondent_name">{% trans "Your name (optional)" %}</label>
<input type="text" id="respondent_name" name="respondent_name" ...>
```
to:
```html
<label for="respondent_name">{% trans "First name or nickname (optional)" %}</label>
<input type="text" id="respondent_name" name="respondent_name" maxlength="50" ...>
```

Update the French translation in `locale/fr/LC_MESSAGES/django.po`:
- msgid: `"First name or nickname (optional)"`
- msgstr: `"Prénom ou surnom (facultatif)"`

Run `python manage.py translate_strings` to compile.

---

## Phase 2 — Nice-to-Have (do these after Phase 1 is committed)

These are UX polish items. Commit Phase 1 first, then work on these.

### Task 6: Client-side multi-page navigation

**Decision:** Client-side only (Option B from design doc). All sections render in HTML; JS groups them by `page_break` and shows one page at a time. No-JS fallback = single-page scroll (current behaviour).

**What to do:**

1. Add `data-page-break="true"` to `<fieldset>` elements where `section.page_break` is True in `public_form.html`.

2. Add JS that:
   - Groups fieldsets into pages (split at `data-page-break="true"`)
   - Hides all pages except page 1
   - Adds "Next" / "Previous" buttons between pages
   - "Next" validates required fields on current page before advancing
   - "Submit" button only appears on the last page
   - Updates a progress indicator: `<div role="status" aria-live="polite">Page X of Y</div>`

3. **ARIA (from expert panel):**
   - Use `role="group"` on page containers with `aria-label="Page 1 of 3"`
   - Move focus to the first heading of the new page on "Next"
   - Use `hidden` attribute for inactive pages

### Task 7: Score display on thank-you page

**Decision:** Respect the existing `show_scores_to_participant` toggle on Survey model.

**What to do:**

1. In `public_views.py`, after creating the response, if `survey.show_scores_to_participant`:
   - Build answers dict from the submitted data
   - Call `calculate_section_scores(visible_sections, answers_dict)` from `apps/portal/survey_helpers.py`
   - Store scores in `request.session[f"survey_scores_{link.token}"]`

2. In `public_survey_thank_you`, retrieve scores from session and pass to template.

3. In `public_thank_you.html`, if scores exist, display in a simple table:
   ```html
   {% if scores %}
   <table>
       <thead><tr><th>Section</th><th>Score</th></tr></thead>
       <tbody>
       {% for s in scores %}
           <tr><td>{{ s.title }}</td><td>{{ s.score }} / {{ s.max_score }}</td></tr>
       {% endfor %}
       </tbody>
   </table>
   {% endif %}
   ```

### Task 8: Copy-to-clipboard + response count in staff UI

**What to do:**

1. **Copy button** — in `templates/surveys/admin/survey_links.html`, next to each active link URL, add:
   ```html
   <button type="button" class="outline secondary"
           onclick="navigator.clipboard.writeText(this.previousElementSibling.value).then(function(){
               document.getElementById('copy-status').textContent='Copied!';
               setTimeout(function(){document.getElementById('copy-status').textContent='';},2000);
           })"
           style="margin-bottom:0">{% trans "Copy" %}</button>
   ```
   Add a live region: `<div id="copy-status" role="status" aria-live="polite"></div>`

2. **Response count** — in `apps/surveys/views.py` (`survey_links` view), annotate the links queryset:
   ```python
   from django.db.models import Count, Q, F
   links = survey.links.all().annotate(
       response_count=Count(
           'survey__responses',
           filter=Q(survey__responses__token=F('token'))
       )
   )
   ```
   Add a "Responses" column to the template table.

### Task 9: Add `single_response` option to SurveyLink

**Decision:** Per-link toggle, signed cookie, soft control only.

**What to do:**

1. Add `single_response = models.BooleanField(default=False)` to `SurveyLink` model. Run `makemigrations` and `migrate`.

2. In `public_views.py`, on GET: check for cookie `survey_done_{token[:8]}`. If `link.single_response` and cookie exists, show a friendly "You've already responded" page.

3. On successful POST: if `link.single_response`, set a signed cookie with 1-year expiry.

4. Add checkbox to the "Create New Link" form in `survey_links.html`.

---

## After all tasks

1. Run related tests: `pytest tests/test_surveys.py -v`
2. Run `python manage.py translate_strings` to compile any new translation strings
3. Commit all changes on the feature branch
4. Push and create PR targeting `develop`:
   ```
   git push -u origin feat/survey-link-enhancements
   gh pr create --title "feat: enhance public survey shareable links" --body "..."
   ```
5. Update TODO.md: mark SURVEY-LINK1 as done, move to Recently Done with date

---

## Key files reference

| File | Role |
|---|---|
| `tasks/survey-link-design.md` | Full design doc with gap analysis and expert decisions |
| `apps/surveys/public_views.py` | Public form + thank-you views (no login) |
| `apps/surveys/models.py` | SurveyLink model (line ~364), SurveyResponse (line ~286) |
| `apps/portal/templatetags/survey_tags.py` | Template filters (`partial_value`, `in_multi_value`) — add `bilingual` here |
| `apps/portal/survey_helpers.py` | `filter_visible_sections()`, `group_sections_into_pages()`, `calculate_section_scores()` |
| `templates/surveys/public_form.html` | Public survey form template |
| `templates/surveys/public_thank_you.html` | Public thank-you template |
| `templates/surveys/admin/survey_links.html` | Staff link management UI |
| `apps/surveys/views.py` | Staff views incl. `survey_links`, `staff_data_entry` (reference for conditional visibility pattern) |
| `apps/portal/templates/portal/survey_fill.html` | Portal form (reference for multi-page, ARIA patterns) |
| `apps/audit/models.py` | AuditLog model |
