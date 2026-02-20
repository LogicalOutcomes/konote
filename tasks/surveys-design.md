# SURVEY1 — Surveys (Structured Feedback Collection)

## Summary

Add a survey system so agencies can collect structured feedback from participants. Surveys support sections (visual groupings, scored subscales, and conditional logic), multiple delivery channels, automatic trigger rules, and CSV import for standardised instruments.

## Why This Matters

Nonprofits regularly collect structured feedback — program satisfaction, intake questionnaires, exit surveys, pre/post assessments, standardised clinical instruments (PHQ-9, SPDAT). Most use separate tools (Google Forms, SurveyMonkey, paper) which means data lives outside the case management system. A built-in survey tool keeps feedback connected to participant records, respects encryption and privacy rules, and reduces tool sprawl.

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

## Survey Structure

### Sections

Surveys are organised into sections. Every survey has at least one section. Sections serve four purposes (all optional per section):

| Purpose | How it works |
|---|---|
| **Visual grouping** | A heading that breaks a long form into readable chunks |
| **Page break** | Starts a new page in the participant form (multi-page navigation) |
| **Scored subscale** | Section has its own score (sum or average of numeric answers) |
| **Conditional** | Section only appears if a specific question in a previous section has a specific answer |

A single section can combine these — e.g., a scored section that also has a page break and conditional logic.

### Question Types

| Type | Description | Scored? |
|---|---|---|
| Single choice | Radio buttons — pick one | Yes (via option score values) |
| Multiple choice | Checkboxes — pick multiple | Yes (sum of selected scores) |
| Rating scale | Numeric range (e.g., 1-5 or 1-10) | Yes (numeric value) |
| Short text | Single-line text input | No |
| Long text | Multi-line text area | No |
| Yes/No | Two radio buttons | Yes (1/0 or configurable) |

### Bilingual Support

All text fields (survey name, section titles, instructions, question text, option labels) have EN and FR variants. The respondent-facing page respects the language setting or a `?lang=fr` parameter.

## Models

### Survey

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | PK |
| `name` | CharField | EN name |
| `name_fr` | CharField (blank) | FR name |
| `description` | TextField (blank) | EN description |
| `description_fr` | TextField (blank) | FR description |
| `status` | CharField | `draft` / `active` / `closed` / `archived` |
| `is_anonymous` | BooleanField | If true, responses never link to a client file |
| `show_scores_to_participant` | BooleanField (default False) | Whether participants see section scores after submission |
| `portal_visible` | BooleanField | Whether this survey appears in the portal |
| `expires_at` | DateTimeField (nullable) | Optional expiry for shareable link |
| `created_by` | FK → User | Staff who created the survey |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |

When a survey's status changes to `closed` or `archived`, all its trigger rules are automatically deactivated.

### SurveySection

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | PK |
| `survey` | FK → Survey | Parent survey |
| `title` | CharField | EN section heading |
| `title_fr` | CharField (blank) | FR section heading |
| `instructions` | TextField (blank) | EN section instructions shown to participant |
| `instructions_fr` | TextField (blank) | FR section instructions |
| `sort_order` | PositiveIntegerField | Display order |
| `page_break` | BooleanField (default False) | If true, this section starts on a new page |
| `scoring_method` | CharField | `none` / `sum` / `average` |
| `max_score` | PositiveIntegerField (nullable) | Maximum possible score for display |
| `condition_question` | FK → SurveyQuestion (nullable) | Section only shows when this question... |
| `condition_value` | CharField (blank) | ...has this answer |
| `is_active` | BooleanField (default True) | Can deactivate without deleting |

### SurveyQuestion

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | PK |
| `section` | FK → SurveySection | Parent section |
| `question_text` | CharField | EN text |
| `question_text_fr` | CharField (blank) | FR text |
| `question_type` | CharField | `single_choice` / `multiple_choice` / `rating_scale` / `short_text` / `long_text` / `yes_no` |
| `sort_order` | PositiveIntegerField | Order within section |
| `required` | BooleanField | |
| `options_json` | JSONField | For choice questions: `[{"value": "1", "label": "...", "label_fr": "...", "score": 0}, ...]` |
| `min_value` | IntegerField (nullable) | For rating scales |
| `max_value` | IntegerField (nullable) | For rating scales |

### SurveyTriggerRule

Defines when a survey should be automatically assigned to participants. See "Trigger System" section below.

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | PK |
| `survey` | FK → Survey | Which survey this rule assigns |
| `trigger_type` | CharField | `event` / `time` / `enrolment` / `characteristic` |
| `event_type` | FK → EventType (nullable) | For event triggers |
| `program` | FK → Program (nullable) | For enrolment/characteristic triggers |
| `recurrence_days` | PositiveIntegerField (nullable) | For time triggers: assign every N days |
| `anchor` | CharField | `enrolment_date` / `last_completed` |
| `repeat_policy` | CharField | `once_per_participant` / `once_per_enrolment` / `recurring` |
| `auto_assign` | BooleanField | True = automatic, False = staff must confirm |
| `include_existing` | BooleanField | When first activated, also assign to existing matches |
| `is_active` | BooleanField | |
| `due_days` | PositiveIntegerField (nullable) | Set a due date N days after assignment |
| `created_by` | FK → User | |
| `created_at` | DateTimeField | Auto |

### SurveyAssignment

Tracks which surveys are assigned to which participants.

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | PK |
| `survey` | FK → Survey | Which survey |
| `participant_user` | FK → ParticipantUser | Portal user |
| `client_file` | FK → ClientFile | Redundant FK for cascade safety |
| `status` | CharField | `awaiting_approval` / `pending` / `in_progress` / `completed` / `dismissed` |
| `triggered_by_rule` | FK → SurveyTriggerRule (nullable) | Which rule caused this assignment (null = manual) |
| `trigger_reason` | CharField (blank) | Human-readable reason (e.g., "30-day recurring check-in") |
| `due_date` | DateField (nullable) | Optional deadline |
| `started_at` | DateTimeField (nullable) | When they first opened the form |
| `completed_at` | DateTimeField (nullable) | When they submitted |
| `assigned_by` | FK → User (nullable) | Staff member (null = auto-assigned) |
| `created_at` | DateTimeField | Auto |

### SurveyResponse

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | PK |
| `survey` | FK → Survey | |
| `assignment` | FK → SurveyAssignment (nullable) | Null for link/staff-entered responses |
| `client_file` | FK → ClientFile (nullable) | Null for anonymous |
| `channel` | CharField | `link` / `portal` / `staff_entered` |
| `respondent_name` | CharField (blank, encrypted) | Optional, for link responses |
| `submitted_at` | DateTimeField | |
| `token` | CharField (unique) | For shareable link responses |

### SurveyAnswer

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | PK |
| `response` | FK → SurveyResponse | |
| `question` | FK → SurveyQuestion | |
| `value` | TextField (encrypted) | Text answer (encrypted for free-text) |
| `numeric_value` | IntegerField (nullable) | For scales/scores (stored as plain integer for aggregation) |

### PartialAnswer

Stores in-progress answers for auto-save. Moved to SurveyAnswer on final submit.

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | PK |
| `assignment` | FK → SurveyAssignment | |
| `question` | FK → SurveyQuestion | |
| `value_encrypted` | BinaryField | Fernet-encrypted answer |
| `updated_at` | DateTimeField | Auto |

Unique constraint: `(assignment, question)`.

## Trigger System

### Trigger Types

| Type | Fires when | Example |
|---|---|---|
| `event` | An Event with matching event_type is created for a participant | Crisis event → assign Crisis Follow-Up survey |
| `enrolment` | A participant is enrolled in the specified program | Youth Program enrolment → assign Youth Intake survey |
| `time` | Enough days have passed since an anchor date | 30 days since enrolment → assign 30-Day Check-in |
| `characteristic` | Participant matches criteria (currently: program membership) | All Housing Program participants → assign Housing Stability survey |

### Repeat Policies

| Policy | Behaviour |
|---|---|
| `once_per_participant` | Survey assigned at most once, ever, per participant |
| `once_per_enrolment` | Survey assigned once per enrolment period (handles re-enrolment) |
| `recurring` | Survey re-assigned after recurrence_days; prevents stacking (no new assignment if one is already pending/in progress) |

### Automation Modes

Each trigger rule has an `auto_assign` flag:

- **True (automatic):** Assignment created with status `pending`. Participant sees it immediately.
- **False (staff confirms):** Assignment created with status `awaiting_approval`. Staff see it on the client file and in `/manage/surveys/pending/`. Must click "Approve" for participant to see it.

### Evaluation Engine

The engine checks trigger rules and creates assignments. It runs at four points:

1. **Portal dashboard load** — evaluate time and characteristic rules for this participant
2. **Staff client view load** — same evaluation (catches participants without portal accounts)
3. **Event creation** — immediately evaluate event-type rules (via `post_save` signal with `transaction.on_commit()`)
4. **Enrolment creation** — immediately evaluate enrolment rules (via `post_save` signal with `transaction.on_commit()`)

#### Evaluation Logic

```
evaluate_survey_rules(client_file, participant_user=None):

    Guard: skip if client_file.status == "discharged"
    Guard: skip if participant_user and not participant_user.is_active

    For each active rule where survey.status == "active":

        EVENT rules: handled by signal at event creation, not during access check
        ENROLMENT rules: handled by signal at enrolment creation

        TIME rules:
            - Is participant in rule.program? If not, skip.
            - Find anchor date:
              - enrolment_date: ClientProgramEnrolment.enrolled_at
              - last_completed: most recent completed SurveyAssignment.completed_at
            - Has (now - anchor_date) >= recurrence_days? If not, skip.
            - Check repeat_policy (see below)

        CHARACTERISTIC rules:
            - Is participant in rule.program? If not, skip.
            - Check repeat_policy (see below)

        Repeat policy check:
            once_per_participant: skip if any assignment exists for (survey, participant)
            once_per_enrolment: skip if assignment exists after current enrolment date
            recurring: skip if pending/in_progress assignment exists

        If match: use get_or_create to atomically create SurveyAssignment
            auto_assign=True → status="pending"
            auto_assign=False → status="awaiting_approval"
```

#### Performance

- Typical rule count: 5-20 per agency. Single DB query to load.
- Per-rule evaluation: 1-3 queries (program membership, existing assignments).
- Total: ~10-30ms per page load. Negligible vs. PII decryption costs.
- Cache evaluation result in participant session for 15 minutes.

#### Guardrails

- **Overload protection:** If a participant already has 5+ pending surveys, don't auto-assign more. Show a notice to staff.
- **Auto-deactivation:** When survey status changes to closed/archived, deactivate all its trigger rules.
- **Audit trail:** Every auto-assignment logged to audit database with rule ID, participant, timestamp, trigger type.
- **Rule conflict warnings:** When creating a rule, show warnings if other rules target the same event type or if participants would exceed 5 pending surveys.
- **Retroactive confirmation:** When `include_existing=True`, show exact participant count and require confirmation before creating assignments.

## CSV Import

Agencies can upload standardised instruments (PHQ-9, SPDAT, etc.) via CSV instead of entering questions one by one.

### CSV Format

```csv
section,question,type,required,options,score_values,instructions,page_break,section_fr,question_fr,options_fr
"Over the past 2 weeks","Little interest or pleasure",rating_scale,yes,"Not at all;Several days;More than half;Nearly every day","0;1;2;3","Rate each item",yes,"Au cours des 2 dernières semaines","Peu d'intérêt ou de plaisir","Pas du tout;Plusieurs jours;Plus de la moitié;Presque tous les jours"
```

| Column | Required | Description |
|---|---|---|
| `section` | Yes | Section title. Rows with the same value are grouped. |
| `question` | Yes | Question text |
| `type` | Yes | `rating_scale`, `single_choice`, `multiple_choice`, `short_text`, `long_text`, `yes_no` |
| `required` | Yes | `yes` or `no` |
| `options` | For choice/rating | Semicolon-separated option labels |
| `score_values` | Optional | Semicolon-separated numeric scores (must match options count) |
| `instructions` | Optional | Section instructions (read from first row of each section) |
| `page_break` | Optional | `yes` or `no` (read from first row of each section) |
| `section_fr` | Optional | French section title |
| `question_fr` | Optional | French question text |
| `options_fr` | Optional | French option labels |

### Import Flow

1. Staff go to `/manage/surveys/new/` and click "Import from CSV"
2. Upload the CSV file
3. System parses and shows a preview: sections, questions, types, options
4. Staff review and can edit before saving
5. "Save as Draft" creates Survey, SurveySection, and SurveyQuestion rows
6. Staff proceed to "When should this go out?" (trigger rule setup)

Error handling shows clear messages with line numbers for any parsing issues.

## Staff-Side UI

### Survey Creation Wizard

**Step 1: Survey Content** — `/manage/surveys/new/`

Two paths:
- **Manual:** Form with survey name, description, anonymous toggle, language, then add sections and questions inline
- **CSV import:** Upload file, review preview, edit, save as draft

**Step 2: "When should this go out?"** — shown after saving step 1

Clear options presented as radio buttons:
- "I'll assign it myself" → no trigger rule created
- "When someone joins [Program]" → enrolment trigger
- "Every [N] days" → time trigger (with anchor and program selection)
- "When a [Event Type] is recorded" → event trigger

Each automatic option shows:
- Automation mode: "Assign automatically" vs "Staff reviews first"
- Due date: optional, N days after assignment
- Retroactive: "Also assign to people who already match" (with count preview)

**Preview panel** before activation shows participant count, overload warnings, and rule conflict notices.

### Survey List — `/manage/surveys/`

Table: Name, Status, Response count, Active rules summary, Last response date. Click to open detail page with tabs: Questions, Responses, Rules, Settings.

### Manual Assignment — from Client File

On a participant's staff-side file page, a "Surveys" section shows:
- Pending/in-progress/completed surveys with status badges
- "Assign Survey" button for manual assignment
- Inline approval alert for `awaiting_approval` assignments: "[Survey name] — triggered by [rule description] [Approve] [Dismiss]"

### Bulk Management — `/manage/surveys/pending/`

Table of all `awaiting_approval` assignments across the PM's programs. Bulk approve/dismiss with confirmation.

### Viewing Results

- **Summary view:** Response count, completion rate, aggregate charts per question, section scores
- **Individual responses:** Viewable by staff with permissions
- **Export:** CSV/Excel download (respects export permissions)

## Permissions

| Action | Who |
|---|---|
| Create/edit surveys | Admin, PM |
| Create/edit trigger rules | Admin, PM (scoped to their programs) |
| View survey results | Admin, PM, survey creator |
| Manual assignment | Any staff with client access |
| Approve/dismiss awaiting assignments | Staff assigned to that participant |
| Staff data entry | Any staff with client access |
| CSV import | Admin, PM |

## Design Considerations

- **SURVEY1 is independent of PORTAL1** — shareable link and staff entry work without the portal
- **Anonymous vs. linked** — set at creation time. Anonymous surveys never store a client file link.
- **Accessibility** — WCAG 2.2 AA. Simple Pico CSS forms, no JS frameworks.
- **Encryption** — free-text answers encrypted at rest (Fernet). Choice/scale answers stored as plain integers for aggregation.
- **No external dependencies** — everything runs within KoNote.
- **Survey closed mid-progress** — closing prevents new assignments but doesn't invalidate in-progress responses.

## Feature Toggle

Controlled by `features.surveys`. When disabled, all survey-related navigation and functionality is hidden.

## Dependencies

- None required — SURVEY1 can be built independently
- PORTAL1 (optional) — enables the portal dashboard channel and "Questions for You"
- Email (OPS3, optional) — enables sending survey links via email
