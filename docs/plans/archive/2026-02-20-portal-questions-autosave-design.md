# PORTAL-Q1 Implementation Design: Auto-Save, Multi-Page, Full Feature

**Date:** 2026-02-20
**Related:** [tasks/portal-questions-design.md](../../tasks/portal-questions-design.md), PORTAL-Q1

## Summary

Completes the "Questions for You" portal feature by adding HTMX auto-save, multi-page navigation, conditional sections, a review page, and a dashboard badge on top of the existing survey models and basic portal views.

## Expert Panel Decisions

These decisions were validated by a four-person expert panel (Social Services UX Designer, Nonprofit Program Manager, Django/HTMX Developer, Accessibility Specialist):

| Decision | Choice | Rationale |
|---|---|---|
| Auto-save transport | HTMX blur/change, 200 with indicator | Invisible to participant, degrades to full-page submit |
| Page navigation | Standard form POST + redirect | More robust for unreliable connections than HTMX swaps |
| Conditional sections | Server-side, page-navigation only | Simpler code and better for screen readers |
| Form semantics | `<fieldset>` + `<legend>` per question group | WCAG compliance for grouped inputs |
| URL pattern | Keep `/my/surveys/`, add new endpoints | No URL breakage, "Questions for You" is a display label |

## 1. Auto-Save

### Participant Experience

- Answers save silently as the participant fills in the form
- A brief "Saved" indicator appears near the top of the form, fades after 2 seconds
- Closing the browser preserves all answers; returning pre-fills the form
- If auto-save fails: "Could not save" indicator; full-page submit still works

### Technical Design

**Endpoint:** `POST /my/surveys/<id>/save/`

**Request:** `question_id=<pk>&value=<text>` (for multiple_choice: all checked values joined with `;`)

**Trigger attributes on inputs:**
- Text inputs, textareas: `hx-trigger="blur"`
- Radio buttons, selects: `hx-trigger="change"`
- Checkboxes (multiple_choice): `hx-trigger="change"` with JS to serialize all checked values

**Server logic:**
```
PartialAnswer.objects.update_or_create(
    assignment=assignment,
    question_id=question_id,
    defaults={"value": raw_value}  # uses .value setter for Fernet encryption
)
```

**Response:** 200 with `<span role="status">Saved</span>` swapped into `#save-status` region. On error: `<span role="status" class="save-error">Could not save</span>`.

**PartialAnswer model change:** Add `.value` property getter/setter for Fernet encryption (matching SurveyAnswer pattern).

## 2. Multi-Page Navigation

### When Multi-Page Activates

A survey becomes multi-page when any `SurveySection` has `page_break=True`. Sections are grouped into pages: everything before the first page break is page 1, each subsequent page break starts a new page.

### Participant Experience

- Page header: "Page 1 of 3: Section Title" with a progress bar
- Bottom of each page: `[Back]` (link) and `[Next]` (submit button)
- Final page: `[Back]` and `[Submit]`
- Returning participants are taken to the furthest page with saved answers

### Technical Design

**URL:** `/my/surveys/<id>/fill/?page=N` (query parameter)

**"Next" button:** `<button type="submit" name="action" value="next">` — standard form POST. Server saves all answers on current page to PartialAnswer, validates required fields, redirects to `?page=N+1`.

**"Back" button:** `<a href="?page=N-1">` — simple link. Answers already auto-saved.

**Page-level validation:** Required questions checked on "Next". On failure, re-render same page with inline errors next to the relevant questions.

### Scrolling Form (No Page Breaks)

All sections on one page. Auto-save on blur/change. Progress shows "X of Y answered". Submit button at bottom.

## 3. Conditional Sections

### Evaluation

- Server-side only, on page load and page navigation
- Each section's `condition_question` and `condition_value` checked against PartialAnswer data
- Hidden sections don't render, don't count toward page total
- Clearing: when a condition is no longer met, that section's PartialAnswer rows are deleted

### Limitation (v1)

Conditional sections on the same page as the trigger question won't appear dynamically. The participant must navigate away and back. This is acceptable and simpler for screen readers.

## 4. Submit Flow

1. Participant clicks "Submit" on final page
2. Server reads all PartialAnswer rows for the assignment
3. Validates all required questions have answers
4. Inside `transaction.atomic()`:
   - Creates SurveyResponse (channel="portal")
   - Creates SurveyAnswer for each PartialAnswer (with encryption transfer)
   - Extracts numeric_value for scored question types
   - Marks assignment as completed
   - Deletes all PartialAnswer rows
5. Redirects to thank-you page

## 5. Review Page

**URL:** `GET /my/surveys/<id>/review/`

- Read-only view of completed responses
- Sections as headings, questions and answers in clean format
- Skipped conditional sections not shown
- Section scores shown when `show_scores_to_participant=True`
- Accessible from surveys list (completed items link here)

## 6. Thank-You Page Enhancement

- Show section scores when `show_scores_to_participant=True`
- Display: "Your [worker] will review these results with you." (terminology override)
- Link back to dashboard

## 7. Dashboard Badge

- Card: "Questions for You" with description "Forms and check-ins from your [worker]"
- Badge: count of pending + in-progress assignments
- Tap behaviour: 1 assignment = go straight to form; multiple = go to list
- Hidden when no assignments exist

## 8. Accessibility

- Every grouped-input question (radio, checkbox, rating) in `<fieldset>` + `<legend>`
- `aria-required="true"` on required fields
- Save indicator in `aria-live="polite"` region
- After page navigation, focus moves to page heading (`tabindex="-1"`, JS focus)
- 44px minimum touch targets
- Progress uses `role="status"` for announcements
- CSS animations respect `prefers-reduced-motion`
- Conditional section containers use `aria-live="polite"`

## URL Summary

| URL | Method | Purpose |
|---|---|---|
| `/my/surveys/` | GET | List pending + completed |
| `/my/surveys/<id>/fill/` | GET | Render form (page 1 or scrolling) |
| `/my/surveys/<id>/fill/?page=N` | GET | Specific page |
| `/my/surveys/<id>/fill/` | POST | "Next" navigation or final submit |
| `/my/surveys/<id>/save/` | POST | HTMX auto-save single answer |
| `/my/surveys/<id>/review/` | GET | Read-only completed view |
| `/my/surveys/<id>/thanks/` | GET | Thank-you page (existing) |

## Files to Modify/Create

| File | Change |
|---|---|
| `apps/surveys/models.py` | Add `.value` property to PartialAnswer |
| `apps/portal/views.py` | Refactor fill view, add autosave + review views |
| `apps/portal/urls.py` | Add save and review URLs |
| `apps/portal/templates/portal/survey_fill.html` | Full rewrite with HTMX, multi-page, accessibility |
| `apps/portal/templates/portal/survey_review.html` | New template |
| `apps/portal/templates/portal/survey_thank_you.html` | Add scores |
| `apps/portal/templates/portal/surveys_list.html` | Link completed items to review |
| `apps/portal/templates/portal/dashboard.html` | Add "Questions for You" card |
