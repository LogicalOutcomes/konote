# PORTAL-Q1 — "Questions for You" (Portal Survey Experience)

**Related to:** SURVEY1 (Surveys — Lightweight Structured Feedback)

## The Idea

Add a "Questions for You" section to the Participant Portal where participants can fill in forms, check-ins, or assessments assigned by their staff. This is the participant-facing side of the survey system described in SURVEY1.

## Why This Matters

Nonprofits regularly ask participants to fill in forms — intake questionnaires, weekly check-ins, pre/post assessments, satisfaction surveys, self-rating scales. Today these live on paper, in Google Forms, or in separate tools. Participants don't have a single place to see what's been asked of them and what they've already completed.

A "Questions for you" card on the portal dashboard gives participants a clear, friendly entry point.

## What the Participant Sees

### On the Dashboard

A new card alongside My Goals, My Progress, etc.:

- **Card title:** "Questions for You" (or similar — e.g., "Check-Ins", "Things to Fill In")
- **Card description:** Something warm and clear, like "Forms and check-ins from your [worker]"
- **Badge:** Shows count of pending/new forms (e.g., "1 new")

### When They Tap the Card — Two Scenarios

**Scenario A — One form waiting:**
Go straight to the form. No list page needed. After submitting, show a confirmation and return to dashboard.

**Scenario B — Multiple forms (or a mix of done and pending):**
Show a simple list:

```
Questions for You

  [ ] Weekly check-in (due Friday)          →
  [x] How's it going? — completed Feb 10
  [x] Getting started survey — completed Jan 28
```

- Pending forms are at the top, completed ones below
- Tapping a completed form shows their responses (read-only)
- Tapping a pending form opens it to fill in

### Filling In a Form

- One question per screen (mobile-friendly) or a simple scrolling form
- Question types from SURVEY1: single choice, multiple choice, rating scale, short text, long text, yes/no
- Progress indicator: "Question 2 of 5"
- Save and finish later (don't lose partial answers)
- Clear submit confirmation: "Thanks! Your answers have been saved."

## Real-World Examples

These examples show the range of nonprofits that might use this:

| Agency Type | Form Name | Questions | Frequency |
|---|---|---|---|
| Youth recreation | "How was today's session?" | 3 quick ratings | After each session |
| Employment program | "Weekly job search check-in" | 5 mixed (text + scale) | Weekly |
| Mental health | "PHQ-9 mood check" | 9 standardised scale items | Every 2 weeks |
| Settlement services | "Getting started" intake | 12 mixed questions | Once, at intake |
| After-school program | "End of term feedback" | 6 mixed questions | End of term |
| Housing support | "Monthly housing stability" | 8 scale + text | Monthly |

## Design Decisions (Resolved)

1. **Naming:** "Questions for You" — warm, clear, non-clinical. Used consistently in dashboard card and nav.
2. **One-at-a-time vs scrolling form:** Scrolling form for all lengths. Simpler to build, works well on mobile with Pico CSS. Progress indicator shows "Question 2 of 5" at top.
3. **Reminders:** Dashboard card shows a badge with pending count. No email/push notifications in Phase 1.
4. **Partial saves:** Yes — auto-save via HTMX after each question loses focus. Participants can close the browser and resume later.
5. **Viewing past responses:** Always visible. Participants can always see what they submitted — it's their data.
6. **Connection to outcomes:** Deferred to a later phase. Survey responses are stored independently for now.

## What Staff See (Brief — Full Detail in SURVEY1)

- Staff assign a survey to a participant (or to all participants in a program)
- They can see who has completed it and who hasn't
- Responses appear in the participant's timeline

## Complexity Notes

This feature builds on the SURVEY1 foundation (survey builder, question types, response storage). The portal-specific work is:

- Dashboard card with pending count
- List page (pending + completed forms)
- Form-filling UI (accessible, mobile-friendly)
- Read-only view of past responses
- Auto-save for partial answers

The survey builder itself (creating questions, assigning to participants) is staff-side work covered by SURVEY1.

---

## Implementation Details

### Build Order

**SURVEY1 must be built first.** PORTAL-Q1 depends on:
- `Survey` and `SurveyQuestion` models (staff-side, built in SURVEY1)
- Survey assignment infrastructure (who gets which survey)

PORTAL-Q1 adds the participant-facing views on top of that foundation.

### New Models (added by PORTAL-Q1)

#### SurveyAssignment

Tracks which surveys are assigned to which participants.

| Field | Type | Notes |
|-------|------|-------|
| `id` | AutoField | PK |
| `survey` | FK → Survey | Which survey |
| `participant_user` | FK → User | Portal user (participant) |
| `status` | CharField | `pending` / `in_progress` / `completed` |
| `due_date` | DateField (nullable) | Optional deadline |
| `started_at` | DateTimeField (nullable) | When they first opened it |
| `completed_at` | DateTimeField (nullable) | When they submitted |
| `assigned_by` | FK → User | Staff member who assigned it |
| `created_at` | DateTimeField | Auto |

Unique constraint: `(survey, participant_user)` — one assignment per survey per participant.

#### PartialAnswer

Stores in-progress answers for auto-save. Moved to `SurveyResponse` on final submit.

| Field | Type | Notes |
|-------|------|-------|
| `id` | AutoField | PK |
| `assignment` | FK → SurveyAssignment | Which assignment |
| `question` | FK → SurveyQuestion | Which question |
| `value_encrypted` | BinaryField | Fernet-encrypted answer text |
| `updated_at` | DateTimeField | Auto (tracks last auto-save) |

Unique constraint: `(assignment, question)` — one partial answer per question per assignment.

### URLs

All under the portal namespace (`/my/`):

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/my/questions/` | `questions_list` | GET | List pending and completed assignments |
| `/my/questions/<id>/` | `question_form` | GET | Show the scrolling form for an assignment |
| `/my/questions/<id>/save/` | `question_autosave` | POST (HTMX) | Auto-save a single answer |
| `/my/questions/<id>/submit/` | `question_submit` | POST | Final submission |
| `/my/questions/<id>/review/` | `question_review` | GET | Read-only view of completed answers |

### Templates

| Template | Description |
|----------|-------------|
| `templates/portal/questions_list.html` | Two sections: "Pending" (with due dates) and "Completed" (with completion dates). Empty state: "No questions right now." |
| `templates/portal/question_form.html` | Scrolling form with all questions. Progress indicator at top. Auto-save via HTMX on blur. Submit button at bottom. |
| `templates/portal/question_review.html` | Read-only view of submitted answers. "Submitted on [date]" header. |

### Dashboard Card

In `templates/portal/dashboard.html`, a new card conditional on `features.surveys`:

```
Questions for You
Forms and check-ins from your [worker]
[1 new]
```

- Badge shows count of pending assignments
- Hidden when no assignments exist (pending or completed)
- Tapping goes to `/my/questions/`

### Auto-Save Flow

1. Participant opens a form → `started_at` is set, status moves to `in_progress`
2. As they fill in each question, HTMX fires on `blur` (field loses focus)
3. `question_autosave` encrypts the answer and upserts into `PartialAnswer`
4. On submit, all `PartialAnswer` rows are moved to `SurveyResponse`, assignment status → `completed`
5. `PartialAnswer` rows are deleted after successful submit

### Accessibility

- All form fields have proper `<label>` elements
- Rating scales use `<fieldset>` + `<legend>` with radio buttons
- Focus management: after auto-save, focus stays on the current field
- Keyboard navigation works for all question types
- Progress indicator uses `aria-live="polite"` for screen readers

---

## Out of Scope for Initial Design

- Conditional/branching logic (show question B only if A = "yes")
- Scheduled recurring surveys (auto-assign every 2 weeks)
- Anonymous surveys (portal surveys are always linked to the participant)
- Notifications/email reminders about pending forms
