# Survey Conditional Branching — Design

**Date:** 2026-02-20
**Branch:** feat/portal-q1-implementation
**Status:** Approved

## Problem

The survey data model supports conditional sections (`condition_question` + `condition_value` on `SurveySection`), and the portal already filters sections server-side via `filter_visible_sections()`. However:

1. **Survey builder** has no UI to set conditions on sections
2. **Admin detail view** shows no indicator that a section is conditional
3. **Staff data entry** renders all sections unconditionally
4. The `condition_value` field is a free-text CharField — prone to typos and value mismatches

## Approach: Server-Side Filtering + Minimal Client-Side for Staff Entry

Based on expert panel review focusing on brittleness, robustness, and staff usability.

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| **Server-side only** for portal | Multi-page flow already handles it; no JS needed |
| **Server-side + JS show/hide** for staff entry | Single-page form needs real-time feedback; JS gracefully degrades to "all sections visible" |
| **Dynamic dropdown** for condition value (not free text) | Eliminates the #1 predicted bug: admin types a value that never matches |
| **Activation-time validation** | Catches stale conditions after question edits |
| **Accept all submitted answers on POST** | Extra data is better than lost data; only enforce `required` on visible sections |

## Design by Component

### 1. Survey Builder — Section Condition Fields

**Files:** `apps/surveys/forms.py`, `templates/surveys/admin/survey_form.html`, admin views

Add two fields to `SurveySectionForm`:

- **"Show only when"** — `condition_question`: dropdown of questions from *earlier* sections (lower `sort_order`). Filtered per form instance in the view.
- **"is answered"** — `condition_value`: **dynamic dropdown** populated from the selected trigger question's possible answers. For yes/no questions: "Yes (1)" / "No (0)". For choice questions: option labels with values. For text/rating: free text fallback.

The template renders this as a readable sentence:
> Show this section only when [Question dropdown] is answered [Value dropdown]

Both fields are optional — leaving them blank means the section is always visible.

**Ordering constraint:** The `condition_question` queryset excludes questions in the current section or later sections. Validated in `clean()`.

### 2. Condition Value — Dynamic Dropdown via HTMX

When the admin selects a trigger question in the "Show only when" dropdown, an HTMX request fetches the possible answer values for that question and populates the "is answered" dropdown.

**Endpoint:** `GET /admin/surveys/<survey_id>/condition-values/<question_id>/`
**Returns:** HTML `<option>` elements for the dropdown

Value mapping by question type:

| Question Type | Dropdown Options |
|---------------|-----------------|
| yes_no | "Yes" (value=1), "No" (value=0) |
| single_choice | Each option label (value=option.value) |
| multiple_choice | Each option label (value=option.value) |
| rating_scale | Each scale point label (value=option.value) |
| short_text | Free text input (swap dropdown for text field) |
| long_text | Free text input (swap dropdown for text field) |

### 3. Admin Detail View — Conditional Badge

**File:** `templates/surveys/admin/survey_detail.html`

When a section has `condition_question` set, show below the section title:

> **Conditional** — shown when "[trigger question text]" is answered "[condition value]"

Also show in `survey_questions.html` per section header.

### 4. Staff Data Entry — JS Show/Hide + Server Authority

**Files:** `apps/surveys/views.py` (`staff_data_entry`), `templates/surveys/staff_data_entry.html`

#### Template changes

- Conditional sections get `data-condition-question="q_{pk}"` and `data-condition-value="{value}"` attributes, plus `style="display:none"` initially.
- When a conditional section is visible (JS evaluated the condition), show a subtle note: *"This section appears because [Question X] was answered [Value]."*
- ~20 lines of inline JS: listen for `change` on trigger question inputs, show/hide dependent sections by matching `data-condition-*` attributes.
- Inputs inside hidden sections get `disabled` attribute so browsers don't enforce `required` validation on them. JS re-enables on show.

#### View changes (POST handling)

1. Collect all submitted answers
2. Build `{question_pk: value}` dict from POST data
3. Call `filter_visible_sections(all_sections, answers_dict)` to determine visible sections
4. Enforce `required` only on questions in visible sections
5. Save **all** submitted answers (even from sections the server considers hidden — extra data is acceptable)
6. This means: if JS failed and staff filled in a hidden section, the answers are still saved

#### View changes (GET)

- Pass `all_sections` to template (not filtered) so JS can manage visibility
- Also pass `condition_map`: a dict of `{section_pk: {question_field: "q_{pk}", value: "..."}}` for the JS to use

### 5. Portal — No Changes Needed

The portal's multi-page `portal_survey_fill` view already calls `filter_visible_sections()` on each page navigation. The HTMX auto-save flow persists answers before navigation. No changes required.

### 6. Activation-Time Validation

**File:** `apps/surveys/views.py` (survey status change view)

When changing survey status from "draft" to "active", validate:

- Every `condition_value` matches an actual possible answer for its `condition_question`
- Every `condition_question` is in a section with lower `sort_order` than the dependent section
- Block activation with a clear error message listing which sections have invalid conditions

### 7. Question Deletion Warning

**File:** `templates/surveys/admin/survey_questions.html`, question delete handler

When deleting a question that has `dependent_sections` (reverse FK), show a confirmation message:

> "This question is used as a condition trigger for [Section X]. Deleting it will make that section always visible. Continue?"

### 8. What We're NOT Building

- No complex operators (AND/OR/greater-than) — exact string match only
- No cross-survey conditions
- No JS-driven branching in the portal
- No deletion of answers when a section becomes hidden (answers preserved in database)
- No client-side condition evaluation in the portal (server-side page navigation handles it)

## Files Changed

| File | Change |
|------|--------|
| `apps/surveys/forms.py` | Add `condition_question`, `condition_value` to `SurveySectionForm` |
| `apps/surveys/views.py` (admin) | Set queryset per section form; add condition-values HTMX endpoint; activation validation |
| `apps/surveys/urls.py` | Add condition-values endpoint |
| `templates/surveys/admin/survey_form.html` | Render condition fields as readable sentence |
| `templates/surveys/admin/survey_detail.html` | Conditional badge per section |
| `templates/surveys/admin/survey_questions.html` | Conditional indicator; deletion warning |
| `apps/surveys/views.py` (staff entry) | Filter sections on POST; pass condition map on GET |
| `templates/surveys/staff_data_entry.html` | `data-condition-*` attributes; JS show/hide; visibility notes |
| `tests/test_surveys.py` | Builder form tests, activation validation tests |
| `tests/test_portal_surveys.py` | Staff entry filtering tests |
| Translations | French strings for new labels and messages |
