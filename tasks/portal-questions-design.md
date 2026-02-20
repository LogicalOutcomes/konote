# PORTAL-Q1 — "Questions for You" (Portal Survey Experience)

**Related to:** SURVEY1 (Surveys — Structured Feedback Collection)

## The Idea

Add a "Questions for You" section to the Participant Portal where participants can fill in forms, check-ins, or assessments assigned by their staff or by automatic trigger rules. This is the participant-facing side of the survey system described in SURVEY1.

## Why This Matters

Nonprofits regularly ask participants to fill in forms — intake questionnaires, weekly check-ins, pre/post assessments, satisfaction surveys, self-rating scales. Today these live on paper, in Google Forms, or in separate tools. Participants don't have a single place to see what's been asked of them and what they've already completed.

A "Questions for You" card on the portal dashboard gives participants a clear, friendly entry point. Combined with SURVEY1's trigger rules, forms appear automatically at the right time — at intake, every 30 days, after a crisis event — without staff having to remember to assign them.

## What the Participant Sees

### On the Dashboard

A new card alongside My Goals, My Progress, etc.:

- **Card title:** "Questions for You"
- **Card description:** "Forms and check-ins from your [worker]" (uses terminology override)
- **Badge:** Shows count of pending + in-progress forms (e.g., "2 new")
- Hidden when no assignments exist (pending, in-progress, or completed)

### When They Tap the Card

**One pending form:** Go straight to the form. No list page needed. After submitting, show confirmation and return to dashboard.

**Multiple forms (or a mix of pending and completed):** Show the list page.

### Questions List — `/my/questions/`

```
Questions for You

  New
  ────────────────────────────────────
  □ Weekly wellness check-in                    →
    Due: Friday, Feb 21

  □ Monthly housing stability                   →
    Page 1 of 3 saved — pick up where you left off

  Completed
  ────────────────────────────────────
  ✓ How's it going? — completed Feb 10          →
  ✓ Getting started survey — completed Jan 28   →
```

- Pending and in-progress forms at the top, completed below
- In-progress forms show progress hint ("Page 1 of 3 saved")
- Due date shown only if the trigger rule set one
- Tapping a completed form opens the read-only review
- Empty state: "No questions right now — check back later."

### Filling In a Form

Two form layouts depending on whether the survey uses page breaks:

#### Multi-Page (survey has sections with page_break=True)

```
Page 1 of 3: About You
━━━━━━━━━━━━━━━━━━━━━━

For each question below, select the answer that best describes you.

1. What is your current housing situation? *
   ○ Own home    ○ Renting    ○ Shelter    ○ Other

2. How long have you been at your current address?
   ○ Less than 6 months  ○ 6-12 months  ○ 1-3 years  ○ 3+ years

3. Do you have children living with you? *
   ○ Yes    ○ No

                                              [Next →]
```

- Navigation: [← Back] and [Next →] buttons between pages
- "Next" saves all answers on the current page, then shows the next page
- "Back" preserves all answers (no data loss)
- Progress indicator: "Page 2 of 4" (updates as conditional sections appear/disappear)
- Final page shows [← Back] and [Submit]

#### Scrolling Form (no page breaks)

```
Weekly Wellness Check-in
━━━━━━━━━━━━━━━━━━━━━━━

Question 2 of 5

Over the past week...

1. How have you been feeling overall? *
   ○ Much worse  ○ Worse  ○ About the same  ○ Better  ○ Much better

2. How well have you been sleeping?
   ○ Very poorly  ○ Poorly  ○ OK  ○ Well  ○ Very well

...

                                              [Submit]
```

- All questions visible on one scrolling page
- Progress indicator: "Question 2 of 5" (tracks which question is in focus)
- [Submit] button at the bottom

#### Conditional Sections

When a section has a `condition_question` set:
- The section is hidden until the participant answers the triggering question
- On multi-page forms: conditional sections may appear as additional pages after the page with the trigger question
- If the participant changes their answer and the condition is no longer met, the conditional section disappears and any answers in it are cleared
- Visual cue when a section appears: "(This section appeared based on your earlier answer)"

#### Submission Confirmation

```
Thanks! Your answers have been saved.

[If scored and show_scores_to_participant=True:]
Your scores:
  Physical Health: 14 / 20
  Mental Health: 8 / 15
  Overall: 22 / 35

Your [worker] will review these results with you.

[← Back to dashboard]
```

### Viewing Past Responses — `/my/questions/<id>/review/`

```
Getting Started Survey
Submitted on January 28, 2026

About You
─────────
1. What is your current housing situation?
   → Renting

2. How long have you been at your current address?
   → 6-12 months

[If scored and show_scores_to_participant=True:]
Section score: 14 / 20

Your Goals
──────────
8. What would you most like to achieve in the next 3 months?
   → "I want to get my driver's licence so I can get to work on my own"
```

- Sections shown as headings
- Conditional sections that were skipped are not shown
- Participants can always see their own past responses — it's their data

## Real-World Examples

| Agency Type | Form Name | Structure | Trigger |
|---|---|---|---|
| Youth recreation | "How was today's session?" | 1 section, 3 quick ratings | Manual (after sessions) |
| Employment program | "Weekly job search check-in" | 2 sections, 5 mixed | Recurring: every 7 days |
| Mental health | "PHQ-9 mood check" | 1 scored section, 9 standardised items | Recurring: every 14 days |
| Settlement services | "Getting started" intake | 4 sections with page breaks, 12 questions | Enrolment trigger |
| After-school program | "End of term feedback" | 2 sections, 6 mixed | Manual (end of term) |
| Housing support | "Monthly housing stability" | 3 scored sections, 8 items | Recurring: every 30 days |
| Crisis services | "Post-crisis check-in" | 1 section + 1 conditional, 6 items | Event trigger: Crisis event |

## Design Decisions

1. **Naming:** "Questions for You" — warm, clear, non-clinical. Used consistently in dashboard card and navigation.
2. **Multi-page vs scrolling:** Depends on survey structure. Surveys with page-break sections use multi-page navigation. Surveys without page breaks use a scrolling form. Both work well on mobile with Pico CSS.
3. **Reminders:** Dashboard card shows a badge with pending count. No email/push notifications in Phase 1.
4. **Partial saves:** Auto-save via HTMX after each question loses focus (blur event) and on page navigation. Participants can close the browser and resume later.
5. **Viewing past responses:** Always visible. Participants can always see what they submitted — it's their data.
6. **Scores:** Configurable per survey. `show_scores_to_participant` defaults to False. When enabled, section scores shown on confirmation and review pages.
7. **Conditional sections:** Section-level branching only (not question-level). A section appears/disappears based on one question's answer. Simpler to build and understand than arbitrary branching.
8. **Connection to outcomes:** Deferred. Survey responses are stored independently for now.

## Build Order

**SURVEY1 must be built first.** PORTAL-Q1 depends on:
- `Survey`, `SurveySection`, and `SurveyQuestion` models (staff-side, built in SURVEY1)
- `SurveyAssignment` model (assignment tracking, built in SURVEY1)
- `SurveyTriggerRule` and evaluation engine (trigger system, built in SURVEY1)

PORTAL-Q1 adds the participant-facing views, templates, and auto-save mechanism on top of that foundation.

## Models Added by PORTAL-Q1

### PartialAnswer

Stores in-progress answers for auto-save. Moved to `SurveyAnswer` on final submit.

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | PK |
| `assignment` | FK → SurveyAssignment | Which assignment |
| `question` | FK → SurveyQuestion | Which question |
| `value_encrypted` | BinaryField | Fernet-encrypted answer text |
| `updated_at` | DateTimeField | Auto (tracks last auto-save) |

Unique constraint: `(assignment, question)` — one partial answer per question per assignment.

## URLs

All under the portal namespace (`/my/`):

| URL | View | Method | Description |
|---|---|---|---|
| `/my/questions/` | `questions_list` | GET | List pending and completed assignments |
| `/my/questions/<id>/` | `question_form` | GET | Show form (first page or scrolling) |
| `/my/questions/<id>/page/<n>/` | `question_form_page` | GET | Specific page for multi-page surveys |
| `/my/questions/<id>/save/` | `question_autosave` | POST (HTMX) | Auto-save a single answer on blur |
| `/my/questions/<id>/save-page/` | `question_save_page` | POST (HTMX) | Save all answers on current page + navigate |
| `/my/questions/<id>/submit/` | `question_submit` | POST | Final submission |
| `/my/questions/<id>/review/` | `question_review` | GET | Read-only view of completed answers |

## Templates

| Template | Description |
|---|---|
| `portal/questions_list.html` | Two sections: "New" (pending/in-progress with due dates) and "Completed" (with dates). Empty state message. |
| `portal/question_form.html` | Form layout — adapts for multi-page (with nav) or scrolling (single page). Progress indicator. Auto-save via HTMX on blur. |
| `portal/question_form_page.html` | HTMX partial for a single page in multi-page surveys. Section heading, instructions, questions. |
| `portal/question_review.html` | Read-only view of submitted answers with section headings and optional scores. |
| `portal/question_confirm.html` | Submission confirmation with optional scores and link back to dashboard. |

## Dashboard Card

In `templates/portal/dashboard.html`, conditional on `features.surveys`:

```
Questions for You
Forms and check-ins from your [worker]
[2 new]
```

- Badge shows count of pending + in-progress assignments
- Hidden when no assignments exist
- Tapping goes to `/my/questions/` (or directly to the form if only one pending)

## Auto-Save Flow

1. Participant opens a form → `started_at` is set, assignment status moves to `in_progress`
2. As they fill in each question, HTMX fires on `blur` (field loses focus) → POST to `/save/`
3. `question_autosave` encrypts the answer and upserts into `PartialAnswer`
4. On page navigation ("Next"), all answers on the current page are saved → POST to `/save-page/`
5. On submit, all `PartialAnswer` rows are validated, moved to `SurveyResponse` + `SurveyAnswer`, assignment status → `completed`
6. `PartialAnswer` rows are deleted after successful submit
7. If the survey has scored sections, section scores are calculated and stored

## Conditional Section Evaluation

On page navigation or form load:

1. For each section in sort order:
   - If `condition_question` is null → always show
   - If `condition_question` is set → look up the participant's answer (from `PartialAnswer` or submitted answer)
   - If answer matches `condition_value` → show section
   - If answer doesn't match or doesn't exist → hide section, clear any partial answers for its questions
2. Update page count to reflect visible sections
3. Use `aria-live="polite"` regions for sections that appear/disappear

## Accessibility

- All form fields have proper `<label>` elements
- Rating scales use `<fieldset>` + `<legend>` with radio buttons
- Focus management: after auto-save, focus stays on the current field
- On page navigation, focus moves to the first field on the new page
- Keyboard navigation works for all question types
- Progress indicator uses `aria-live="polite"` for screen readers
- Multi-page navigation uses `<nav aria-label="Survey pages">`
- Conditional sections use `aria-live="polite"` when appearing/disappearing
- Touch targets: minimum 44px (WCAG 2.5.8)

## Assignment Status Flow

```
awaiting_approval → pending (staff approves)
awaiting_approval → dismissed (staff declines)
pending → in_progress (participant opens form)
in_progress → completed (participant submits)
```

- `awaiting_approval`: created by trigger rule with auto_assign=False. Visible to staff only.
- `pending`: visible to participant on dashboard and questions list.
- `in_progress`: participant has opened the form and may have partial answers.
- `completed`: participant has submitted. Answers stored in SurveyResponse/SurveyAnswer.
- `dismissed`: staff declined the suggested assignment. Not visible to participant.

## Out of Scope for Initial Build

- Question-level conditional logic (show question B only if A = "yes") — section-level conditions cover the common case
- Email/push notifications about pending forms
- Anonymous surveys in the portal (portal surveys are always linked to the participant)
- Offline/PWA support for form filling
- Recurring survey scheduling via cron (check-on-access handles this)
