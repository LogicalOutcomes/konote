# QA Scenarios: Surveys & Portal Feedback

## Summary

8 new scenarios (SCN-110 through SCN-117) covering survey creation, CSV import, manual assignment, staff data entry, portal fill, trigger rules, and permission checks. Scenario YAML files go in **konote-qa-scenarios** repo; test methods go in **konote-app**.

## Scenarios at a Glance

| ID | Title | Type | Persona(s) | Directory |
|----|-------|------|------------|-----------|
| SCN-110 | PM Creates a Survey Manually | Daily | PM1 | scenarios/daily/ |
| SCN-111 | PM Imports a Survey via CSV | Daily | PM1 | scenarios/daily/ |
| SCN-112 | Staff Assigns a Survey to a Participant | Daily | DS1 | scenarios/daily/ |
| SCN-113 | Staff Enters Survey Responses on Behalf of Participant | Daily | DS1 | scenarios/daily/ |
| SCN-114 | Participant Fills Out Survey in Portal | Daily | P1 (portal user) | scenarios/daily/ |
| SCN-115 | PM Reviews Survey Responses | Periodic | PM1 | scenarios/periodic/ |
| SCN-116 | Trigger Rule Auto-Assigns Survey on Enrolment | Cross-role | PM1, DS1 | scenarios/cross-role/ |
| SCN-117 | Front Desk Cannot Access Survey Management | Cross-role | R1, PM1 | scenarios/cross-role/ |

## Writing Order

1. SCN-117 (simplest, permission-only)
2. SCN-110 (single persona, manual survey creation)
3. SCN-111 (single persona, CSV import)
4. SCN-112 (single persona, assignment from client file)
5. SCN-113 (single persona, staff data entry)
6. SCN-114 (portal user, fill and submit)
7. SCN-115 (single persona, review and status change)
8. SCN-116 (cross-role, trigger rule + enrolment)

## URLs Referenced by New Scenarios

| URL | Feature | Used In |
|-----|---------|---------|
| `/manage/surveys/` | Survey list (management) | SCN-110, 111, 115, 117 |
| `/manage/surveys/new/` | Create survey form | SCN-110 |
| `/manage/surveys/<id>/` | Survey detail (responses, rules) | SCN-110, 115 |
| `/manage/surveys/<id>/edit/` | Edit survey | SCN-110 |
| `/manage/surveys/<id>/questions/` | Add/edit questions | SCN-110 |
| `/manage/surveys/<id>/status/` | Change survey status | SCN-110, 115 |
| `/manage/surveys/import/` | CSV import form | SCN-111 |
| `/manage/surveys/<id>/responses/<id>/` | View individual response | SCN-115 |
| `/surveys/participant/<id>/` | Client surveys tab (staff view) | SCN-112, 113 |
| `/surveys/participant/<id>/assign/` | Manual assignment | SCN-112 |
| `/surveys/participant/<id>/enter/<id>/` | Staff data entry form | SCN-113 |
| `/surveys/participant/<id>/response/<id>/` | View client response | SCN-113, 115 |
| `/surveys/assignment/<id>/approve/` | Approve triggered assignment | SCN-116 |
| `/surveys/assignment/<id>/dismiss/` | Dismiss assignment | SCN-116 |
| `/my/surveys/` | Portal survey list | SCN-114 |
| `/my/surveys/<id>/fill/` | Portal fill form | SCN-114 |
| `/my/surveys/<id>/thanks/` | Portal thank-you page | SCN-114 |

## Permissions Tested

| Permission | Role | Expected | Scenario |
|-----------|------|----------|----------|
| survey.create | PM | ALLOW (200) | SCN-110, 111 |
| survey.create | Front desk | DENY (403) | SCN-117 |
| survey.view_list | PM | ALLOW (200) | SCN-115 |
| survey.view_list | Front desk | DENY (403) | SCN-117 |
| survey.assign | Staff | SCOPED (200) | SCN-112 |
| survey.data_entry | Staff | SCOPED (200) | SCN-113 |
| survey.data_entry | Front desk | DENY (403) | SCN-117 |

## Prerequisite Data Requirements

### Needed (add to seed_demo_data)

Survey demo data does **not** currently exist in `seed_demo_data`. The following must be created:

1. **Active survey "Program Satisfaction Survey"** — 2 sections, 6 questions (mix of single_choice, rating_scale, short_text, yes_no), portal_visible=True, show_scores=False
2. **Active survey "PHQ-2 Screen"** — 1 section, 2 rating_scale questions (scored), portal_visible=True, show_scores=True
3. **Draft survey "Exit Interview"** — 1 section, 3 questions (long_text, single_choice, rating_scale)
4. **1 completed SurveyResponse** for "Program Satisfaction Survey" linked to DEMO-001 (Maria Santos)
5. **1 pending SurveyAssignment** for "PHQ-2 Screen" linked to DEMO-003 (Aisha Okafor) — portal user
6. **1 SurveyTriggerRule** on "PHQ-2 Screen" — type=enrolment, repeat=once_per_enrolment
7. **CSV file** at `tests/fixtures/sample-survey-import.csv` — 1 section, 4 questions for import testing

### Existing (already in seed_demo_data)

- Staff user ("staff") with Housing Support programme
- PM user ("manager") with Housing Support programme
- Front desk user ("frontdesk") with Housing Support programme
- Demo clients (DEMO-001 through DEMO-015)
- Portal user accounts (DEMO-003 Aisha Okafor has portal access)

## Scenario Details

### SCN-110: PM Creates a Survey Manually

**Persona:** PM1 (Morgan Tremblay — Program Manager)

**Trigger:** Morgan needs to collect program satisfaction feedback from Housing Support participants at the end of each quarter.

**Goal:** Create a new survey from scratch with sections and questions, add questions of different types, then activate it.

**Steps:**
1. Navigate to `/manage/surveys/` — verify survey list loads
2. Click "New Survey" — fill in name, description, set portal_visible
3. Save survey — verify redirect to detail page
4. Click "Add Questions" — add a section with 2 single-choice questions
5. Add a second section with a rating_scale and a short_text question
6. Return to survey detail — verify sections and questions appear
7. Change status to "Active" — verify status badge updates

**Key checks:** Form validation (required fields), question type rendering, status change workflow, breadcrumb navigation back to survey list.

---

### SCN-111: PM Imports a Survey via CSV

**Persona:** PM1 (Morgan Tremblay)

**Trigger:** Morgan received a standardised intake questionnaire from the funder as a spreadsheet and needs to load it into KoNote without typing each question.

**Goal:** Upload a CSV file to create a complete survey with sections, questions, and scoring, then review the result.

**Steps:**
1. Navigate to `/manage/surveys/import/` — verify import form loads
2. Upload the sample CSV file + enter survey name
3. Submit — verify success message and redirect to survey detail
4. Review created sections, questions, and options — verify they match CSV
5. Check that scored questions have correct score_values

**Key checks:** CSV parsing, error handling for malformed rows, bilingual fields (if CSV includes FR columns), section/question ordering matches CSV order.

---

### SCN-112: Staff Assigns a Survey to a Participant

**Persona:** DS1 (Casey Makwa — Direct Service Staff)

**Trigger:** Casey's supervisor asked her to get the PHQ-2 screen filled out for a participant during their next appointment.

**Goal:** Manually assign an active survey to a specific participant from the client file.

**Steps:**
1. Navigate to participant's client file → Surveys tab at `/surveys/participant/{client_id}/`
2. Verify existing surveys/assignments listed (if any)
3. Click "Assign Survey" — select "PHQ-2 Screen" from dropdown
4. Submit — verify assignment created with "pending" status
5. Verify new assignment appears in the client's survey list

**Key checks:** Only active surveys appear in dropdown, assignment status flow, staff can only see clients in their programme (scoped access).

---

### SCN-113: Staff Enters Survey Responses on Behalf of Participant

**Persona:** DS1 (Casey Makwa)

**Trigger:** Casey is on the phone with a participant who can't access the portal. The participant wants to complete the satisfaction survey verbally.

**Goal:** Fill out the survey form on behalf of the participant, submit, and verify the response is recorded with a "staff_entered" channel marker.

**Steps:**
1. Navigate to `/surveys/participant/{client_id}/enter/{survey_id}/`
2. Verify all questions render correctly (radio buttons, text fields, rating scales)
3. Fill in answers for each question
4. Submit — verify success and redirect
5. Check the response detail — verify "staff entered" notation and answers recorded

**Key checks:** All 6 question types render, required field validation, response linked to correct client, channel shows "staff_entered".

---

### SCN-114: Participant Fills Out Survey in Portal

**Persona:** P1 (Aisha Okafor — portal user, DEMO-003)

**Trigger:** Aisha logs into the participant portal and sees she has a pending survey to complete.

**Goal:** Find the pending survey on the portal dashboard, fill it out, submit, and see the confirmation.

**Steps:**
1. Log in as portal user — navigate to `/my/surveys/`
2. Verify pending survey listed with title and due date (if set)
3. Click survey to begin — verify questions render at `/my/surveys/{id}/fill/`
4. Fill in answers
5. Submit — verify redirect to thank-you page at `/my/surveys/{id}/thanks/`
6. Return to `/my/surveys/` — verify survey moved to "Completed" section

**Key checks:** Portal authentication, survey visibility, form validation, status transition (pending → in_progress → completed), timestamps set correctly.

---

### SCN-115: PM Reviews Survey Responses

**Persona:** PM1 (Morgan Tremblay)

**Trigger:** Morgan wants to check how many participants have completed the satisfaction survey and review individual responses.

**Goal:** View the survey response list, read an individual response, and close the survey.

**Steps:**
1. Navigate to `/manage/surveys/` — verify response count shown on survey card
2. Click into "Program Satisfaction Survey" detail page
3. View response list — verify respondent name, date, channel
4. Click into an individual response — verify all answers displayed
5. Return to detail — change status to "Closed"
6. Verify status badge updates and survey no longer appears as assignable

**Key checks:** Response count accuracy, individual response rendering (all question types), status change from active→closed deactivates trigger rules, closed survey not available for new assignments.

---

### SCN-116: Trigger Rule Auto-Assigns Survey on Enrolment

**Persona:** PM1 (sets up rule), DS1 (enrols participant, sees assignment)

**Trigger:** Morgan wants all new enrolments in Housing Support to automatically receive the PHQ-2 screen.

**Goal:** Verify the trigger rule fires when a new participant is enrolled, creating a pending assignment that staff can approve or the participant sees in the portal.

**Steps:**
1. As PM1 — verify trigger rule exists on PHQ-2 Screen (via Django admin or survey detail)
2. As DS1 — enrol a new participant into Housing Support programme
3. Verify a SurveyAssignment is created automatically (check client surveys tab)
4. Verify assignment status is "awaiting_approval" or "pending" (depending on rule config)
5. Approve or dismiss the assignment
6. If approved — verify survey appears in participant's portal list

**Key checks:** Signal fires on enrolment, repeat policy enforced (once_per_enrolment), overload protection (max 5 pending), assignment linked to correct survey and client.

---

### SCN-117: Front Desk Cannot Access Survey Management

**Persona:** R1 (Receptionist), PM1 (for comparison)

**Trigger:** A front desk worker tries to access the survey management pages.

**Goal:** Verify that survey creation, import, and data entry are restricted by role — front desk gets 403, PM gets 200.

**Steps:**
1. As R1 — navigate to `/manage/surveys/` — verify 403 or redirect
2. As R1 — navigate to `/manage/surveys/new/` — verify 403
3. As R1 — navigate to `/manage/surveys/import/` — verify 403
4. As R1 — navigate to `/surveys/participant/{client_id}/enter/{survey_id}/` — verify 403
5. As PM1 — navigate to `/manage/surveys/` — verify 200
6. As PM1 — navigate to `/manage/surveys/new/` — verify 200

**Key checks:** RBAC middleware blocks all management URLs for front desk role, staff data entry restricted, PM has full access.

## Test Methods (in konote-app)

Add to `tests/scenario_eval/test_scenario_eval.py`:

**TestDailyScenarios:**
- `test_pm_creates_survey_manually` (SCN-110)
- `test_pm_imports_survey_csv` (SCN-111)
- `test_staff_assigns_survey` (SCN-112)
- `test_staff_enters_survey_for_participant` (SCN-113)
- `test_participant_fills_portal_survey` (SCN-114)

**TestPeriodicScenarios:**
- `test_pm_reviews_survey_responses` (SCN-115)

**TestCrossRoleScenarios:**
- `test_trigger_rule_auto_assigns_on_enrolment` (SCN-116)
- `test_front_desk_survey_access_denied` (SCN-117)

## CSV Test Fixture

Create `tests/fixtures/sample-survey-import.csv`:

```csv
section,question,type,required,options,score_values,instructions
"About You","What is your age range?","single_choice","yes","Under 18;18-30;31-50;51-65;Over 65","",""
"About You","How did you hear about us?","single_choice","no","Friend;Website;Community event;Other","",""
"Program Feedback","Overall, how satisfied are you with the program?","rating_scale","yes","","","Rate from 1 (not at all) to 5 (very satisfied)"
"Program Feedback","What could we do better?","long_text","no","","","Please share any suggestions"
```

## Dependencies and Notes

- All 8 scenarios are independent of each other (no cascading dependencies)
- SCN-114 requires portal feature toggle enabled and a portal user account
- SCN-116 requires at least one active trigger rule — must be seeded or created via Django admin
- Survey demo data must be added to `seed_demo_data` before running scenarios
- After writing scenario YAML files, update `pages/page-inventory.yaml` in qa-scenarios repo with new pages: survey_list, survey_form, survey_questions, survey_detail, csv_import, client_surveys, staff_data_entry, portal_surveys, portal_survey_fill
- PORTAL-Q1 enhancements (multi-page, auto-save, conditional sections) are being developed separately — these scenarios test the **current** single-page portal implementation
