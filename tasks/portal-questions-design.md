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

## Design Decisions to Make

1. **Naming:** "Questions for You" vs "Check-Ins" vs "Forms" vs "Things to Fill In" — what feels least clinical and most inviting?
2. **One-at-a-time vs scrolling form:** For short forms (3-5 questions), a single scrolling page is probably fine. For longer ones (10+), one question per screen may feel less overwhelming. Do we support both, or pick one?
3. **Reminders:** Should the dashboard highlight overdue or new forms? A gentle "You have a new check-in" banner?
4. **Partial saves:** If someone closes the browser mid-form, do we save their progress? (Recommended: yes, auto-save after each question.)
5. **Viewing past responses:** Can participants always see what they submitted, or only if the staff allows it? (Recommended: always visible — it's their data.)
6. **Connection to outcomes:** Some forms might map to plan metrics (e.g., a self-rating scale feeds into a progress chart). This connection is powerful but adds complexity — possibly a later enhancement.

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

## Out of Scope for Initial Design

- Conditional/branching logic (show question B only if A = "yes")
- Scheduled recurring surveys (auto-assign every 2 weeks)
- Anonymous surveys (portal surveys are always linked to the participant)
- Notifications/email reminders about pending forms
