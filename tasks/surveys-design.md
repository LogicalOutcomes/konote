# SURVEY1 — Surveys (Lightweight Structured Feedback)

## Summary

Add a survey system so agencies can collect structured feedback from participants. Surveys are shareable via link (no login required), optionally available through the participant portal, and can be entered by staff on someone's behalf.

## Why This Matters

Nonprofits regularly collect structured feedback — program satisfaction, intake questionnaires, exit surveys, pre/post assessments. Most use separate tools (Google Forms, SurveyMonkey, paper) which means data lives outside the case management system. A built-in survey tool keeps feedback connected to participant records, respects encryption and privacy rules, and reduces tool sprawl.

## Data Collection Channels

Surveys need to reach people in different situations. Three channels cover the common cases:

### 1. Shareable link (primary — no login needed)
- Staff create a survey and get a unique URL with a secure token
- Anyone with the link can respond (no portal account required)
- Works for: anonymous feedback, intake forms, event attendees, exit surveys
- Optionally collect a name/email, or keep it fully anonymous
- Token-based — each survey instance gets a unique link; links can be set to expire

### 2. Portal integration (optional — requires PORTAL1)
- If the participant portal is enabled and the participant has an account, pending surveys appear on their dashboard
- Responses are automatically linked to the participant's client file
- Works for: recurring check-ins, ongoing self-assessments
- This channel is additive — SURVEY1 works without PORTAL1

### 3. Staff data entry
- Staff can fill in a survey on behalf of a participant (e.g., from a phone call, paper form, or in-person interview)
- Response is linked to the client file with an audit note that it was staff-entered
- Works for: participants who prefer phone or in-person, accessibility accommodations

## How It Would Work

### Survey builder (staff side)
1. **Create a survey** — give it a name, optional description, and set whether it's anonymous or linked
2. **Add questions** — supported types:
   - Single choice (radio buttons)
   - Multiple choice (checkboxes)
   - Rating scale (1-5 or 1-10)
   - Short text
   - Long text
   - Yes/No
3. **Set options** — expiry date, response limit, language (EN/FR), whether to show on portal
4. **Generate link** — get a shareable URL; optionally generate a QR code for printing

### Response collection
- Responses are stored encrypted at rest (like all PII in KoNote)
- Anonymous responses have no client file link
- Linked responses attach to the client file and appear in their timeline
- Each response records: timestamp, channel (link/portal/staff-entered), language used

### Viewing results (staff side)
- Summary view: response count, completion rate, aggregate charts per question
- Individual responses: viewable by staff with appropriate permissions
- Export: CSV/Excel download of responses (respects existing export permissions)

## Models (rough outline)

- **Survey** — name, description, status (draft/active/closed), created_by, anonymous flag, portal_visible flag, expires_at
- **SurveyQuestion** — survey FK, question_text, question_type, sort_order, required flag, options JSON (for choice questions)
- **SurveyResponse** — survey FK, client_file FK (nullable for anonymous), channel (link/portal/staff), respondent_name (optional, encrypted), submitted_at, token
- **SurveyAnswer** — response FK, question FK, value (text), numeric_value (for scales)

## Design Considerations

- **SURVEY1 is independent of PORTAL1** — the shareable link channel works without the portal. Portal integration is a bonus when both features are enabled.
- **Anonymous vs. linked** — the survey creator decides at creation time. Anonymous surveys never store a client file link, even if the respondent has a portal account.
- **Accessibility** — survey forms must meet WCAG 2.2 AA. Keep the respondent-facing pages simple (Pico CSS, no JavaScript frameworks).
- **Bilingual** — question text should support EN/FR fields. The respondent-facing page respects the language setting or a `?lang=fr` parameter.
- **Encryption** — free-text answers are encrypted at rest (same Fernet pattern as other PII). Choice/scale answers may be stored as plain integers for aggregate queries.
- **Permissions** — creating/editing surveys: admin or PM. Viewing results: admin, PM, or survey creator. Staff data entry: any staff with client access.
- **No external dependencies** — no SurveyMonkey API or third-party form service. Everything runs within KoNote.

## Out of Scope (for now)

- Conditional/branching logic (show question B only if answer to A is "yes")
- Recurring/scheduled surveys (auto-send every 30 days)
- Pre-built survey templates (e.g., standard satisfaction questionnaires)
- Public-facing surveys with no agency context (surveys always belong to an agency instance)

These could be added later as enhancements.

## Dependencies

- None required — SURVEY1 can be built independently
- PORTAL1 (optional) — enables the portal dashboard channel
- Email (OPS3, optional) — enables sending survey links via email
