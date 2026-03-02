# Improvement Tickets -- Round 7

**Date:** 2026-03-01
**Report ID:** 2026-03-01aa
**Round:** Round 7 (batch evaluation of 45 scenarios across 7 sub-agent batches)
**Scenarios evaluated:** 45 (38 scoreable, 7 not evaluable)
**Permission violations:** 0
**Total tickets:** 83 (0 PERMISSION, 3 BLOCKER, 23 BUG, 30 IMPROVE, 27 TEST)

---

## Status of Previous Tickets

First evaluation of this run. No prior round in the 2026-03-01 series to compare against.

---

## PERMISSION Tickets (0)

No permission violations detected this round. All 45 scenarios passed the Permission Gate.

---

## BLOCKER Tickets (3)

Red band scenarios (score 1.0--1.9). These represent total workflow failures.

---

### BLOCKER-1: Funder reporting workflow completely blocked by wrong URL

**Severity:** BLOCKER
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-035, Steps 1--5
**Screenshot:** SCN-035_step1_PM1_reports-funder.png

**What's wrong:** All 5 steps show a 404 "Page Not Found" error. The scenario navigates to `/reports/funder/` but the funder report feature lives at `/reports/funder-report/` (confirmed by SCN-086 which loads successfully at that URL). Morgan cannot generate, verify, or export any funder report. This scenario scored 1.57 overall.

**Where to look:** Scenario YAML (`scenarios/periodic/SCN-035.yaml`) -- update the `goto` URL. Alternatively, add a redirect from `/reports/funder/` to `/reports/funder-report/` in `konote-app` routing.

**What "fixed" looks like:** Morgan navigates to `/reports/funder-report/`, sees the report generation form, selects programme and date range, generates and exports the report.

**Acceptance criteria:**
- [ ] SCN-035 YAML updated with correct URL `/reports/funder-report/`
- [ ] Alternatively, Django routing adds redirect from `/reports/funder/` to `/reports/funder-report/`
- [ ] Re-run SCN-035 -- all steps show distinct funder report content, score improves to Green band (4.0+)

**Verification scenarios:** SCN-035/1--5, SCN-086/1 (uses correct URL)

**Dimension breakdown:**

| Dimension | Score |
|-----------|-------|
| Clarity | 3.0 |
| Efficiency | 1.0 |
| Feedback | 1.0 |
| Error Recovery | 2.0 |
| Accessibility | 3.0 |
| Language | 1.0 |
| Confidence | 1.0 |

---

### BLOCKER-2: Staff cannot edit survey responses -- surveys module missing

**Severity:** BLOCKER
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-115, Steps 1--2
**Screenshot:** SCN-115_step1_DS1_surveys.png

**What's wrong:** Both steps show a 404 "Page Not Found" at `/surveys/`. The surveys module does not exist in the application. Casey realised she entered wrong answers and needs to correct them, but the entire survey editing workflow is unreachable. She cannot fix her data entry error, which is a data integrity issue. Score: 1.9.

**Where to look:** The `/surveys/` URL is not routed in `konote-app`. The surveys module either needs to be built or the scenario YAML needs to point to the correct location if surveys exist elsewhere.

**What "fixed" looks like:** Casey navigates to a participant's submitted survey, edits the incorrect responses, saves changes, and sees a confirmation with an audit trail of the edit.

**Acceptance criteria:**
- [ ] Survey editing interface exists and is accessible to staff for their clients
- [ ] Edit history/audit trail is maintained for survey response changes
- [ ] Re-run SCN-115 -- score improves to Green band (4.0+)

**Verification scenarios:** SCN-115/1--2, SCN-111/1, SCN-114/1, SCN-116/1

**Dimension breakdown:**

| Dimension | Score |
|-----------|-------|
| Clarity | 3.5 |
| Efficiency | 1.0 |
| Feedback | 2.5 |
| Error Recovery | 2.5 |
| Accessibility | 3.0 |
| Language | 4.0 |
| Confidence | 1.0 |

---

### BLOCKER-3: Survey conditional logic untestable -- surveys module missing

**Severity:** BLOCKER
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-116, Steps 1--2
**Screenshot:** SCN-116_step1_DS1_surveys.png

**What's wrong:** Both steps show a 404 at `/surveys/`. Casey was asked to complete a survey with conditional questions (skip patterns) but the module does not exist. Same root cause as BLOCKER-2. Score: 1.9.

**Where to look:** Same as BLOCKER-2. Conditional logic (skip patterns) requires the surveys module to be built first.

**What "fixed" looks like:** Casey opens a survey form, sees conditional questions that show/hide based on previous answers, completes the survey, and sees a confirmation.

**Acceptance criteria:**
- [ ] Survey form supports conditional question visibility (skip patterns)
- [ ] Conditional logic is clear to the user (hidden questions do not confuse)
- [ ] Re-run SCN-116 -- score improves to Green band (4.0+)

**Verification scenarios:** SCN-116/1--2, SCN-115/1, SCN-111/1

**Dimension breakdown:**

| Dimension | Score |
|-----------|-------|
| Clarity | 3.5 |
| Efficiency | 1.0 |
| Feedback | 2.5 |
| Error Recovery | 2.5 |
| Accessibility | 3.0 |
| Language | 4.0 |
| Confidence | 1.0 |

---

## BUG Tickets (23)

Orange band scenarios (score 2.0--2.9). These are priority fixes.

---

### BUG-1: Permission denied shows "Page Not Found" instead of 403 explanation

**Severity:** BUG -- Priority fix
**Persona:** R1 (Dana Petrescu)
**Scenario:** SCN-010, Step 6
**Screenshot:** SCN-010_step6_R1_participants-1-notes.png

**What's wrong:** When a receptionist navigates to a restricted page (notes), the system shows "Page Not Found" instead of a styled 403 that explains why access is denied and which roles have access. Dana feels confused and thinks she broke something. The error page does not mention permissions at all.

**Where to look:** Django view/middleware for restricted pages. The `PermissionDenied` exception should be caught and rendered with a custom 403 template.

**What "fixed" looks like:** Dana sees "You do not have access to participant notes. Notes are available to staff and programme managers." with a link back to the client profile.

**Acceptance criteria:**
- [ ] Restricted pages show a styled 403 with plain-language explanation (e.g., "Notes are only visible to staff and programme managers")
- [ ] 403 page includes a link back to the client profile, not just Home
- [ ] Re-run SCN-010 step 6 -- score improves to Green band (4.0+)

**Verification scenarios:** SCN-010/6, SCN-025/3, SCN-042/4

---

### BUG-2: Permission denied shows 404 for R2 accessing notes (same root cause)

**Severity:** BUG -- Priority fix
**Persona:** R2 (Omar Hussain)
**Scenario:** SCN-025, Step 3
**Screenshot:** SCN-025_step3_R2_participants-30-notes.png

**What's wrong:** Same as BUG-1 but affecting R2. Omar is tech-savvy and recognises this as a permission issue disguised as a 404, making it more frustrating. No role-based explanation, no link back to the client profile.

**Acceptance criteria:**
- [ ] 403 page explains which roles have access to notes
- [ ] 403 page includes a direct link back to the client profile
- [ ] Re-run SCN-025 step 3 -- score improves to Green band (4.0+)

**Verification scenarios:** SCN-025/3, SCN-010/6

---

### BUG-3: French interface contains untranslated English in help banners and tooltips

**Severity:** BUG -- Priority fix
**Persona:** R2-FR (Amelie Tremblay)
**Scenario:** SCN-026, Step 1
**Screenshot:** SCN-026_step1_R2-FR_home.png

**What's wrong:** When the interface is set to French, the welcome banner and "Vos outils de reception" section contain multiple English sentences (e.g., "Use the search bar to find Participant(e)s", "Open a Participant(e) profile to view their plan, notes, and progress"). This violates French Language Services Act compliance and would embarrass Amelie in front of French-speaking clients.

**Where to look:** Django templates for the home page welcome banner. Missing French translations in `.po` files for help text strings.

**Acceptance criteria:**
- [ ] All text in the welcome banner is translated to French when French is selected
- [ ] All text in the receptionist tools section is translated to French
- [ ] No English fragments appear when French mode is active
- [ ] Re-run SCN-026 step 1 -- Language dimension scores 4.0+

**Verification scenarios:** SCN-026/1, SCN-040/1

---

### BUG-4: French welcome tips contain English strings on staff dashboard

**Severity:** BUG -- Priority fix
**Persona:** DS2 (Jean-Luc Bergeron)
**Scenario:** SCN-040, Step 1
**Screenshot:** SCN-040_step1_DS2_home.png

**What's wrong:** The welcome banner on the French dashboard shows two help tips in English ("Use the search bar to find Participant(e)s..." and "Open a Participant(e) profile..."). Only the third tip and the help link are in French. Same root cause as BUG-3.

**Acceptance criteria:**
- [ ] All three welcome tips are translated to French when interface language is set to French
- [ ] Re-run SCN-040 step 1 -- Language dimension scores 4.0+

**Verification scenarios:** SCN-040/1, SCN-026/1

---

### BUG-5: Accented characters corrupted on save

**Severity:** BUG -- Priority fix
**Persona:** DS2 (Jean-Luc Bergeron)
**Scenario:** SCN-040, Step 4
**Screenshot:** SCN-040_step4_DS2_participants.png

**What's wrong:** Client created as "Benoit Levesque" with accents in the form, but the saved record shows accents stripped and surname corrupted. This is unacceptable for a bilingual system serving French-speaking clients.

**Where to look:** Database encoding (ensure UTF-8), form serialization, Django model save method for participant names.

**Acceptance criteria:**
- [ ] Accented characters (e.g., e with accent, i with circumflex) are preserved in first name, last name, and preferred name after save
- [ ] Search by accented name returns the correct client with accents intact
- [ ] Re-run SCN-040 step 4 -- score improves to Green band (4.0+)

**Verification scenarios:** SCN-040/4, SCN-026/2

---

### BUG-6: Cross-programme URL returns 404 instead of role-aware 403

**Severity:** BUG -- Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-042, Step 4
**Screenshot:** SCN-042_step4_DS1_participants-aaliyah-thompson-notes.png

**What's wrong:** When Casey navigates directly to a Youth Services notes URL, she gets a generic 404 "Page Not Found" instead of a 403 access denied page. While no data is leaked, the 404 is confusing -- Casey thinks the page is broken rather than understanding she lacks permission. The suggestion "Check the address for typos" is unhelpful.

**Acceptance criteria:**
- [ ] Cross-programme note URLs return a 403 with role-aware messaging (e.g., "You do not have access to Youth Services notes. Contact your programme manager.")
- [ ] No note content is visible in the error response
- [ ] A link back to the client profile or the user's own programme notes is provided
- [ ] Re-run SCN-042 step 4 -- score improves to Green band (4.0+)

**Verification scenarios:** SCN-042/4, SCN-010/6, SCN-025/3

---

### BUG-7: PM scoped user management not accessible -- /admin/users/ requires full admin

**Severity:** BUG -- Priority fix
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-037, Steps 1--4
**Screenshot:** SCN-037_step1_PM1_admin-users.png

**What's wrong:** PM1 has `user.manage: scoped` for her own programme team, but `/admin/users/` returns "Access denied. Admin privileges are required." The scoped user management feature either does not exist at this URL or needs to be at a PM-accessible path like `/manage/team/`. Morgan cannot create staff accounts, deactivate users, or manage her team without going through IT.

**Where to look:** User management views and URL routing. A PM-scoped version of user management needs to be created at a non-admin path.

**Acceptance criteria:**
- [ ] PM1 can access a user management page scoped to her own programme (e.g., `/manage/team/`)
- [ ] The page shows only Housing Support staff, not users from other programmes
- [ ] PM1 can create a new staff account and assign it to Housing Support
- [ ] PM1 can deactivate (not delete) a staff account
- [ ] Role dropdown shows only receptionist and staff (not PM or executive)
- [ ] Re-run SCN-037 steps 1--4 -- all steps score Green (4.0+)

**Verification scenarios:** SCN-037/1--4, SCN-036/5

---

### BUG-8: Meetings features return 404 -- test runner navigated to empty meetings page

**Severity:** BUG -- Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-080, Steps 1--5
**Screenshot:** SCN-080_step1_DS1_events-meetings.png

**What's wrong:** All 5 steps show identical My Meetings page (0 upcoming, 0 recent). The test was supposed to navigate to a specific client's Events tab to test quick-log communication buttons, but instead went to `/events/meetings/` (the global meetings dashboard). The entire communication logging workflow was never exercised.

**Where to look:** Client profile template -- verify that an Events/Communications tab exists. Scenario YAML may need URL correction.

**Acceptance criteria:**
- [ ] Test navigates to `/participants/{client_id}/events/` (client Events tab)
- [ ] Quick-log communication buttons are visible on the Events tab
- [ ] Phone call can be logged and appears in recent communications
- [ ] Re-run SCN-080 -- all steps show distinct, scenario-appropriate content

**Verification scenarios:** SCN-080/1--5, SCN-081/1

---

### BUG-9: Meeting creation link not found on client profile

**Severity:** BUG -- Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-081, Steps 1--4
**Screenshot:** SCN-081_step1_DS1_participants-21.png

**What's wrong:** The test runner could not find `a[href*='meetings/create']` on the client profile page. Steps 1--4 all show identical client profile screenshots. The meeting scheduling and reminder workflow was never exercised. The "Schedule Meeting" action may be inside the Actions dropdown rather than a visible link.

**Acceptance criteria:**
- [ ] A "Schedule Meeting" option is accessible from the client profile (either directly or via Actions menu)
- [ ] Meeting creation form loads with date/time, location, and send reminder fields
- [ ] Re-run SCN-081 -- meeting is created and appears on My Meetings dashboard

**Verification scenarios:** SCN-081/1--4, SCN-082/1

---

### BUG-10: PM meetings dashboard shows empty data -- no meeting oversight possible

**Severity:** BUG -- Priority fix
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-082, Steps 1--4
**Screenshot:** SCN-082_step1_PM1_events-meetings.png

**What's wrong:** All 5 screenshots show the same empty "My Meetings" page with 0 Upcoming and 0 Recent. The scenario prerequisites specify 3 meetings but none were created in the test environment. The heading "My Meetings" also implies personal meetings only, not programme oversight.

**Where to look:** Test data seeding for meetings. Also, the meeting dashboard heading should reflect programme scope for PM users.

**Acceptance criteria:**
- [ ] Test environment is seeded with prerequisite meeting data
- [ ] Meeting dashboard for PM role shows "Programme Meetings" or "Team Meetings" heading
- [ ] Re-run SCN-082 steps 2--4 -- distinct content visible for each step

**Verification scenarios:** SCN-082/1--4, SCN-081/1

---

### BUG-11: Communication reminder URLs return 404

**Severity:** BUG -- Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-084, Steps 1--3
**Screenshot:** SCN-084_step1_DS1_communications-participant-{client_id_alex}-meeting-{meet...}.png

**What's wrong:** All communication URLs contain literal placeholder variables (`{client_id_alex}`, `{client_id_priya}`, `{meeting_id_alex}`, `{meeting_id_priya}`) that were not substituted. The test runner did not resolve prerequisite data IDs. Additionally, the `/communications/` URL namespace may have been retired. Steps 4--5 also ended on the wrong page. The scenario is 0% evaluable for its core purpose (consent guardrails).

**Where to look:** Scenario YAML URLs and test runner placeholder substitution. The `/communications/` URL namespace may need updating to the current Quick Notes pattern.

**Acceptance criteria:**
- [ ] SCN-084 YAML updated with current URL pattern (if communications namespace was replaced)
- [ ] Test runner substitutes dynamic IDs from prerequisite data
- [ ] Re-run SCN-084 -- consent guardrail workflow is evaluable

**Verification scenarios:** SCN-084/1--5

---

### BUG-12: PIPEDA data export function not implemented

**Severity:** BUG -- Priority fix
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-070, Steps 1--3
**Screenshot:** SCN-070_step1_PM1_participants-7.png

**What's wrong:** Morgan cannot locate or trigger a data export for a client's PIPEDA access request. The "Privacy & Data Management" section on the client profile is collapsed and the export action is not accessible. Console shows 404 errors, suggesting the export endpoint is not implemented. PIPEDA requires organisations to provide personal data upon request within 30 days.

**Where to look:** Client profile Privacy & Data Management section. Export view and endpoint need implementation.

**Acceptance criteria:**
- [ ] A clearly labelled "Export Data" or "Data Request" button is visible on the client profile
- [ ] The export offers format choices (PDF, CSV, JSON) with descriptions
- [ ] The export includes all data categories: demographics, notes, plans, consent history, service episodes
- [ ] Cross-programme notes are filtered by PHIPA consent rules
- [ ] Re-run SCN-070 steps 1--3 -- score improves to Green band (4.0+)

**Compliance references:** PIPEDA Principle 9 (right of access)

**Verification scenarios:** SCN-070/1--3, SCN-151/1

---

### BUG-13: PIPEDA consent withdrawal workflow not implemented

**Severity:** BUG -- Priority fix
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-070, Step 4
**Screenshot:** SCN-070_step4_PM1_participants-7.png

**What's wrong:** Morgan cannot initiate a consent withdrawal or data deletion request for a client. The Privacy & Data Management section exists on the profile but the consent withdrawal action is not accessible. Console shows 404. PIPEDA requires organisations to honour consent withdrawal requests.

**Where to look:** Client profile consent section. Deletion/anonymisation workflow needs implementation.

**Acceptance criteria:**
- [ ] A consent withdrawal workflow is accessible from the client profile Privacy & Data Management section
- [ ] The workflow explains what will be deleted vs. retained (with funder retention reasons)
- [ ] A confirmation step prevents accidental deletion
- [ ] After withdrawal, the client no longer appears in searches or reports
- [ ] An audit trail entry is created automatically
- [ ] Re-run SCN-070 step 4 -- score improves to Green band (4.0+)

**Compliance references:** PIPEDA Principle 4.5 (limiting use, disclosure, and retention)

**Verification scenarios:** SCN-070/4, SCN-151/3

---

### BUG-14: Executive role cannot access audit log for PIPEDA compliance oversight

**Severity:** BUG -- Priority fix
**Persona:** E1 (Margaret Whitfield)
**Scenario:** SCN-070, Step 6
**Screenshot:** SCN-070_step6_E1_manage-audit.png

**What's wrong:** Margaret (executive director) is denied access to the audit log at `/manage/audit/`. The permission model has `audit_log: false` for executives. However, PIPEDA Principle 4.1 (accountability) requires that leadership can verify privacy request handling. Margaret needs at minimum a read-only, aggregate view of privacy-related audit events without individual client PII.

**Where to look:** Permission model for executive role. A filtered, anonymised audit view is needed.

**Acceptance criteria:**
- [ ] Executive role can access a filtered audit view showing privacy-related events (consent withdrawal, data export, data deletion) without individual client PII
- [ ] Individual client names are replaced with anonymised references (e.g., "Client #7")
- [ ] Re-run SCN-070 step 6 -- Margaret can verify PIPEDA compliance from the audit view

**Compliance references:** PIPEDA Principle 4.1 (accountability)

**Verification scenarios:** SCN-070/6

---

### BUG-15: Secure download link infrastructure not implemented

**Severity:** BUG -- Priority fix
**Persona:** PM1 (Morgan Tremblay) / ADMIN1 (Priya Sharma)
**Scenario:** SCN-151, Steps 1--4

**What's wrong:** All four secure download link endpoints return 404: used link re-use, expired link access, admin link management page (`/admin/export-links/`), and revoked link access. The entire secure download link lifecycle (single-use, 24-hour expiry, admin revocation) is unimplemented. This is a privacy and security gap -- if data exports are generated via SCN-070, the download links need expiry and revocation controls.

**Acceptance criteria:**
- [ ] Used download links return a clear "This link has already been used" message
- [ ] Expired links (past 24 hours) return a clear "This link has expired" message
- [ ] Admin can view and revoke active download links from `/admin/export-links/`
- [ ] Revoked links return a clear "This link has been revoked" message
- [ ] Revocation is logged in the audit trail
- [ ] Re-run SCN-151 all steps -- scores reach Green band (4.0+)

**Compliance references:** PIPEDA 4.7 (safeguards)

**Verification scenarios:** SCN-151/1--4, SCN-070/2

---

### BUG-16: Keyboard Tab order skips First Name field on create form

**Severity:** BUG -- Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-053, Step 2
**Screenshot:** SCN-053_step2_DS3_participants-create.png

**What's wrong:** When keyboard-only user Tabs into the create-participant form and begins typing, the first typed value ("James") lands in the Last Name field instead of First Name. The second value ("Thompson") lands in Preferred Name instead of Last Name. The Tab order either skips the First Name field or focuses it without it being evident. For a screen reader user, this means data silently goes into wrong fields -- a data integrity issue.

**Where to look:** Create-participant form HTML. The `tabindex` attributes or field order in the DOM does not match the visual layout. WCAG 1.3.2 (Meaningful Sequence) and 2.4.3 (Focus Order).

**Acceptance criteria:**
- [ ] First Tab press from the page heading lands on the First Name field
- [ ] JAWS announces "First Name, required, edit text" on first Tab
- [ ] Tab order follows visual order: First Name, Last Name, Preferred Name, etc.
- [ ] Re-run SCN-053 step 2 -- "James" appears in First Name, "Thompson" in Last Name
- [ ] Verified with JAWS screen reader

**Verification scenarios:** SCN-053/2, SCN-050/4, SCN-056/4

---

### BUG-17: Skip-to-content link missing or incorrectly targeted

**Severity:** BUG -- Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-052, Step 1
**Screenshot:** SCN-052_step1_DS3_participants-create.png

**What's wrong:** On the participants home page, pressing Tab then Enter (the standard skip-link pattern) navigates to the create-participant form instead of skipping to the main content area. Either no skip-to-content link exists, or the skip link target is wrong. WCAG 2.4.1 requires a mechanism to bypass repeated navigation blocks.

**Where to look:** Base template. The skip link `href` must target `#main-content` or equivalent `<main>` landmark.

**Acceptance criteria:**
- [ ] A "Skip to main content" link is the first focusable element on the page
- [ ] The link becomes visible when focused (not permanently hidden)
- [ ] Activating the link moves focus into the `<main>` landmark, before any action buttons
- [ ] Re-run SCN-052 step 1 -- focus lands within `<main>` content area
- [ ] Verified with JAWS screen reader

**Verification scenarios:** SCN-052/1, SCN-050/2, SCN-055/1

---

### BUG-18: Tab order navigates to nav bar instead of main content after skip link

**Severity:** BUG -- Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-050, Step 3
**Screenshot:** SCN-050_step3_DS3_programs.png

**What's wrong:** After login, pressing Tab 5 times lands on the "Programs" navigation link instead of the "+ New Participant" button in main content. The keyboard Tab sequence passes through the entire nav bar before reaching page content. The skip-to-content link either does not exist on the home page or was not activated by the test.

**Acceptance criteria:**
- [ ] Skip-to-content link is the first focusable element after page load
- [ ] Activating skip link moves focus into `<main>` landmark
- [ ] Tab from within `<main>` reaches "+ New Participant" within 5 presses
- [ ] Re-run SCN-050 step 3 -- create button reached without leaving the page

**Verification scenarios:** SCN-050/3, SCN-052/1, SCN-051/2

---

### BUG-19: Client profile tabs do not implement ARIA tablist pattern

**Severity:** BUG -- Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-054, Step 2
**Screenshot:** SCN-054_step2_DS3_participants-1.png

**What's wrong:** The client profile tabs (Info, Plan, Notes, History, Analysis) do not respond to ArrowRight/ArrowLeft keyboard navigation as expected by the WAI-ARIA tablist pattern. Pressing ArrowRight while focused near the tabs opens the Actions dropdown instead of switching to the next tab. WCAG 4.1.2 (Name, Role, Value) violation.

**Where to look:** Client profile template JavaScript. Tabs need `role="tablist"`, individual tabs need `role="tab"`, and arrow key handlers need to be added.

**Acceptance criteria:**
- [ ] Tab container has `role="tablist"`
- [ ] Each tab has `role="tab"` and `aria-selected` attribute
- [ ] Tab panel has `role="tabpanel"` with `aria-labelledby` pointing to its tab
- [ ] ArrowRight/ArrowLeft moves between tabs within the tablist
- [ ] Re-run SCN-054 step 2 -- Notes tab activates via ArrowRight
- [ ] Verified with JAWS screen reader

**Verification scenarios:** SCN-054/2, SCN-050/5

---

### BUG-20: Form validation error shifts data to wrong fields

**Severity:** BUG -- Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-061, Step 1
**Screenshot:** SCN-061_step1_DS3_participants-create.png

**What's wrong:** When the form is submitted with First Name empty, the previously entered Last Name value ("Thompson") shifts to the Preferred Name field, and both First Name and Last Name are now empty. Amara must re-enter data she already typed. For a screen reader user, this silent data shift is especially confusing because JAWS would not announce that field values changed.

**Where to look:** Create-participant form template. The form rendering after validation error is not correctly mapping field values back to their original fields. Check the `name` attributes and server-side form binding.

**Acceptance criteria:**
- [ ] Form validation preserves all previously entered field values in their original fields
- [ ] Only the fields with errors are highlighted -- other fields retain their values
- [ ] Re-run SCN-061 step 1 -- error_recovery dimension improves to 4.0+

**Verification scenarios:** SCN-061/1, SCN-053/2, SCN-045/1

---

### BUG-21: Dashboard overwhelms ADHD user with info density

**Severity:** BUG -- Priority fix
**Persona:** DS1c (Casey Makwa, ADHD)
**Scenario:** SCN-058, Step 1
**Screenshot:** SCN-058_step1_DS1c_home.png

**What's wrong:** The dashboard presents 5 stat cards, a welcome banner, search area, 2 action buttons, a scrolling attention list with 11 items, and a "Pick up where you left off" panel -- far exceeding the 5--6 distinct info block threshold for users with ADHD. The notification badge showing "11" creates background anxiety. No clear primary call to action. Casey cannot identify her most important next action within 5 seconds.

**Where to look:** Home page template. Consider a condensed dashboard mode or progressive disclosure pattern.

**Acceptance criteria:**
- [ ] Dashboard shows no more than 3 competing calls to action above the fold
- [ ] Attention items are collapsible or paginated (not a scrolling list of 11)
- [ ] Notification badge uses calmer visual treatment
- [ ] Re-run SCN-058 step 1 -- clarity dimension improves to 4.0+

**Verification scenarios:** SCN-058/1--2

---

### BUG-22: HTMX search fails to filter results on slow connection

**Severity:** BUG -- Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-048, Step 1
**Screenshot:** SCN-048_step1_DS1_participants.png

**What's wrong:** When Casey types "James" in the search box on a slow 3G connection, the participant list is not filtered -- all 20 participants are displayed. The HTMX search request likely timed out or the response arrived after the screenshot was captured. No loading indicator is visible during the search.

**Where to look:** HTMX search configuration. Add a debounced request with adequate timeout and a visible loading indicator.

**Acceptance criteria:**
- [ ] HTMX search shows a loading indicator within 300ms of typing
- [ ] Search results are filtered even on slow connections (debounced request with adequate timeout)
- [ ] If the search request fails or times out, a visible message explains what happened
- [ ] Re-run SCN-048 step 1 -- score improves to Green band (4.0+)

**Verification scenarios:** SCN-048/1, SCN-055/1

---

### BUG-23: No visible validation error message on participant create form

**Severity:** BUG -- Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-045, Step 1
**Screenshot:** SCN-045_step1_DS1_participants-create.png

**What's wrong:** When a required field (First Name) is left empty and the form is submitted, no visible error message appears near the field. The form re-renders with the previously entered data preserved, but Casey cannot tell what went wrong. The asterisk on the label is not sufficient feedback.

**Where to look:** Create-participant form validation template. Django form error rendering needs inline error messages.

**Acceptance criteria:**
- [ ] Inline validation error appears next to the First Name field with plain-language text (e.g., "Please enter a first name")
- [ ] Error uses colour AND icon/text (not colour alone -- WCAG 1.4.1)
- [ ] Focus moves to the first error field after submission
- [ ] Previously entered data is preserved
- [ ] Re-run SCN-045 step 1 -- score improves to Green band (4.0+)

**Verification scenarios:** SCN-045/1, SCN-061/1

---

## IMPROVE Tickets (30)

Yellow band scenarios (score 3.0--3.9). These are review-recommended improvements.

---

### IMPROVE-1: Landing page too dense for first-time users

**Severity:** IMPROVE -- Review recommended
**Persona:** DS1b (Casey Makwa, first week)
**Scenario:** SCN-005, Step 2
**Screenshot:** SCN-005_step1_DS1b_home.png

**What's wrong:** The "What needs your attention" list shows 10+ client names with overdue notes. For a first-week staff member, this is overwhelming -- she has no context for these clients. The page has more than 10 competing clickable elements.

**Acceptance criteria:**
- [ ] First-time users see a condensed or collapsed attention list (max 3 items)
- [ ] Re-run SCN-005 step 2 -- score improves to Green (4.0+)

---

### IMPROVE-2: Executive dashboard lacks charts and visual comparisons for board presentations

**Severity:** IMPROVE -- Review recommended
**Persona:** E1 (Margaret Whitfield)
**Scenario:** SCN-030, Steps 1--2
**Screenshot:** SCN-030_step1_E1_participants-executive.png

**What's wrong:** Dashboard shows only numeric KPIs with no charts, trend lines, or visual comparisons. Margaret needs screenshot-ready content for board slides. "Data: Low" badges undermine trust in the numbers.

**Acceptance criteria:**
- [ ] Dashboard includes at least one chart (trend line or bar chart) above the fold
- [ ] Programme comparison is visible on one screen without scrolling
- [ ] "Data: Low" badge is either removed or accompanied by a plain-language explanation
- [ ] Re-run SCN-030 steps 1--2 -- score improves to Green (4.0+)

---

### IMPROVE-3: Executive dashboard exports CSV only -- no PDF for board packages

**Severity:** IMPROVE -- Review recommended
**Persona:** E2 (Kwame Asante)
**Scenario:** SCN-030, Step 3
**Screenshot:** SCN-030_step3_E2_participants-executive.png

**What's wrong:** Only "Export CSV" is available. Kwame needs PDF for board packages. Exporting CSV and reformatting in Excel defeats the purpose of the dashboard.

**Acceptance criteria:**
- [ ] Export options include PDF (formatted for board presentations)
- [ ] PDF export includes charts and summary metrics matching the on-screen view
- [ ] Re-run SCN-030 step 3 -- score improves to Green (4.0+)

---

### IMPROVE-4: Executive dashboard date filter has no range or presets

**Severity:** IMPROVE -- Review recommended
**Persona:** E2 (Kwame Asante)
**Scenario:** SCN-030, Step 4
**Screenshot:** SCN-030_step3_E2_participants-executive.png

**What's wrong:** The date filter is a single "Show data from" field with no end date, no presets ("Last quarter", "Year to date"), and no period comparison. An executive preparing a quarterly board package cannot filter to a specific quarter.

**Acceptance criteria:**
- [ ] Date range filter supports both start and end dates
- [ ] Presets include "This month", "Last quarter", "Year to date", and "Custom"
- [ ] Active filter is clearly indicated on the dashboard
- [ ] Re-run SCN-030 step 4 -- score improves to Green (4.0+)

---

### IMPROVE-5: "Admin" navigation item visible to executive role (UI over-exposure)

**Severity:** IMPROVE -- Review recommended
**Persona:** E2 (Kwame Asante)
**Scenario:** SCN-030, Step 3
**Screenshot:** SCN-030_step3_E2_participants-executive.png

**What's wrong:** The navigation bar for Kwame (executive2 role) shows an "Admin" dropdown. Executives have `user.manage: deny` -- the Admin link should not be visible. While it may return 403 if clicked, the presence of the link confuses the role boundary.

**Acceptance criteria:**
- [ ] "Admin" nav item is hidden for executive role
- [ ] Re-run SCN-030 step 3 -- Admin link not visible in navigation

---

### IMPROVE-6: Self-service admin pages lack programme scope indicators

**Severity:** IMPROVE -- Review recommended
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-036, Steps 1, 5
**Screenshot:** SCN-036_step1_PM1_manage-templates.png

**What's wrong:** Plan Templates and other self-service admin pages do not show which programme they are scoped to. Morgan cannot tell whether she is viewing Housing Support templates, all templates, or Youth Services templates.

**Acceptance criteria:**
- [ ] Each self-service admin page shows "Showing: [Programme Name]" or a programme filter
- [ ] When a URL parameter filters to a non-permitted programme, a clear message appears
- [ ] Re-run SCN-036 step 5 -- scope boundary is visible and verifiable

---

### IMPROVE-7: Audit Log subtitle says "all system activity" but PM sees scoped data only

**Severity:** IMPROVE -- Review recommended
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-037, Step 5
**Screenshot:** SCN-037_step5_PM1_manage-audit.png

**What's wrong:** The Audit Log subtitle says "Review all system activity. Use filters to narrow results." but PM1 only has `audit.view: scoped` access. The subtitle should reflect the scoping.

**Acceptance criteria:**
- [ ] Audit Log subtitle for PM role says "Review activity for your programme" or similar scoped language
- [ ] Re-run SCN-037 step 5 -- language accurately reflects scoped access

---

### IMPROVE-8: Meeting dashboard title implies personal only, not programme oversight

**Severity:** IMPROVE -- Review recommended
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-082, Step 1
**Screenshot:** SCN-082_step1_PM1_events-meetings.png

**What's wrong:** The heading "My Meetings" suggests only the PM's own meetings, not meetings across her programme. As a PM, Morgan needs to see all meetings for her team.

**Acceptance criteria:**
- [ ] Meeting dashboard for PM role shows "Programme Meetings" or "Team Meetings" heading
- [ ] Meetings from all staff in the PM's programme are included
- [ ] Re-run SCN-082 step 1 -- heading reflects programme scope

---

### IMPROVE-9: Funder profile selection feature not implemented

**Severity:** IMPROVE -- Review recommended
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-086, Steps 1--2
**Screenshot:** SCN-086_step1_PM1_reports-funder-report.png

**What's wrong:** The scenario expects a funder profile dropdown with custom age bins and per-funder configuration. The actual page shows a generic "Program Outcome Report Template" with no funder profile selector. Morgan cannot select a funder-specific report format.

**Acceptance criteria:**
- [ ] A funder profile dropdown exists on the funder report page
- [ ] Selecting a funder profile changes the report configuration (age bins, required fields, etc.)
- [ ] At least one funder profile ("Youth Services Funder") is available with custom age bins
- [ ] Re-run SCN-086 steps 1--2 -- funder profile selection is visible and functional

---

### IMPROVE-10: No per-role access summary on client profile for programme managers

**Severity:** IMPROVE -- Review recommended
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-042, Step 5
**Screenshot:** SCN-042_step5_PM1_participants-26.png

**What's wrong:** Morgan can see which programmes a client is enrolled in but cannot tell what her staff or receptionists can or cannot see. When Casey asks "Why can I not see everything?", Morgan has no easy way to answer from the client profile.

**Acceptance criteria:**
- [ ] The client profile shows or links to a summary of which roles can see what data
- [ ] Morgan can confidently explain access rules to her staff from the client profile
- [ ] Re-run SCN-042 step 5 -- Confidence dimension scores 4.0+

---

### IMPROVE-11: 403 pages should use role-specific language instead of generic phrasing

**Severity:** IMPROVE -- Review recommended
**Persona:** R1 (Dana Petrescu)
**Scenario:** SCN-085, Steps 1--3; SCN-075, Step 6
**Screenshot:** SCN-085_step1_R1_events-meetings.png

**What's wrong:** All 403 pages use identical generic text: "Access denied. Your role does not have permission for this action." The word "role" is system jargon that Dana (low tech comfort, age 50) may not understand. The page could say "This feature is for case workers and programme managers. You can find what you need on the Participants page." to reduce anxiety and provide a clear path forward.

**Acceptance criteria:**
- [ ] 403 pages include the name of the feature being accessed
- [ ] 403 pages suggest which page the user CAN access instead
- [ ] Language avoids system jargon ("role", "permission", "action")
- [ ] Re-run SCN-085 steps 1--3 -- Clarity dimension scores 4.0+

---

### IMPROVE-12: Group creation form defaults Programme dropdown to "No program"

**Severity:** IMPROVE -- Review recommended
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-076, Step 1
**Screenshot:** SCN-076_step1_PM1_groups-create.png

**What's wrong:** When Morgan opens the group creation form, the Programme dropdown defaults to "No program" instead of pre-selecting her programme(s). This is an extra step and risks creating orphan groups with no programme assignment.

**Acceptance criteria:**
- [ ] If the user has exactly one programme, it is pre-selected
- [ ] If the user has multiple programmes, the dropdown prompts "Select a programme" (not "No program")
- [ ] Re-run SCN-076 step 1 -- Efficiency dimension scores 4.0+

---

### IMPROVE-13: Post-login focus should land on page heading, not action button

**Severity:** IMPROVE -- Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-051, Step 2
**Screenshot:** SCN-051_step2_DS3_home.png

**What's wrong:** After login, keyboard focus lands on the "+ New Participant" button instead of the page heading (h1) or the `<main>` landmark. A screen reader user hears "New Participant, button" with no page context. WCAG 2.4.3 (Focus Order) recommends meaningful initial focus placement.

**Acceptance criteria:**
- [ ] After login, focus lands on the h1 heading or within `<main>` with an aria-label
- [ ] JAWS announces the page context (e.g., "Home -- LogicalOutcomes") on page load
- [ ] Re-run SCN-051 step 2 -- score improves to Green band (4.0+)
- [ ] Verified with JAWS screen reader

---

### IMPROVE-14: HTMX search results lack aria-live announcement for screen readers

**Severity:** IMPROVE -- Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-055, Step 1
**Screenshot:** SCN-055_step1_DS3_participants.png

**What's wrong:** When search results load via HTMX after typing, there is no evidence of an `aria-live` region that would announce "1 result found" or similar to a screen reader user. JAWS users would not know results appeared without manually navigating. WCAG 4.1.3 (Status Messages) violation.

**Acceptance criteria:**
- [ ] Results container has `aria-live="polite"` attribute
- [ ] After HTMX swap, a status message like "1 result found" is announced by JAWS
- [ ] Focus remains in the search field during and after the swap
- [ ] Re-run SCN-055 step 1 -- JAWS announces result count after search
- [ ] Verified with JAWS screen reader

---

### IMPROVE-15: Filter controls add excessive Tab stops between search field and results

**Severity:** IMPROVE -- Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-055, Step 2
**Screenshot:** SCN-055_step2_DS3_participants.png

**What's wrong:** After typing a search query, pressing Tab moves focus to filter dropdowns (All statuses, All Programs, Can edit plans, Clear) before reaching the search results. A keyboard user must Tab through 5+ filter controls to reach the first result link.

**Acceptance criteria:**
- [ ] After typing in search and results load, the next Tab press lands on the first result link (or a results summary)
- [ ] Filter controls remain accessible via a different navigation path
- [ ] Re-run SCN-055 step 2 -- result link reached within 3 Tab presses from search field
- [ ] Verified with JAWS screen reader

---

### IMPROVE-16: Profile tabs too small for tablet touch targets

**Severity:** IMPROVE -- Review recommended
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-057, Step 3
**Screenshot:** SCN-057_step3_DS1_participants-1.png

**What's wrong:** The profile tabs (Info, Plan, Notes, History, Analysis) are rendered as small text links with minimal padding. On a tablet held in one hand, Casey would frequently mis-tap between tabs. The tab targets appear to be below the 44px recommended size and likely below the 24px minimum (WCAG 2.5.8).

**Acceptance criteria:**
- [ ] Profile tabs have at least 44px height with full-width tap areas (not just text width)
- [ ] Re-run SCN-057 step 3 -- accessibility dimension improves to 4.0+

---

### IMPROVE-17: Notifications lack urgency distinction and persistent inbox

**Severity:** IMPROVE -- Review recommended
**Persona:** DS1c (Casey Makwa, ADHD)
**Scenario:** SCN-058, Step 2
**Screenshot:** SCN-058_step2_DS1c_home.png

**What's wrong:** The attention list treats a safety alert (Jane Doe) identically to overdue-note reminders -- no urgency distinction. Items are only dismissable via small x buttons with no "mark as read" or "snooze" option. Dismissing one shifts remaining items (moving target). Casey with ADHD may dismiss the safety alert while trying to clear informational items.

**Acceptance criteria:**
- [ ] Safety alerts are visually distinct from informational reminders (colour, icon, or position)
- [ ] Notifications are reviewable in a persistent inbox, not just inline dismissable items
- [ ] Dismissing one item does not shift remaining items
- [ ] Re-run SCN-058 step 2 -- confidence dimension improves to 4.0+

---

### IMPROVE-18: Nav link says "Participants" but Dragon user expects "Clients"

**Severity:** IMPROVE -- Review recommended
**Persona:** DS4 (Riley Chen)
**Scenario:** SCN-059, Step 2
**Screenshot:** SCN-059_step2_DS4_home.png

**What's wrong:** The scenario assumes Riley would say "Click Clients" but the navigation link text is "Participants". Dragon users must learn the exact label text. WCAG 2.5.3 (Label in Name) requires visible text to match the accessible name.

**Acceptance criteria:**
- [ ] Navigation link visible text matches any `aria-label` exactly
- [ ] User documentation refers to "Participants" consistently (not "Clients")

---

### IMPROVE-19: No visible "New Note" button on notes tab for Dragon targeting

**Severity:** IMPROVE -- Review recommended
**Persona:** DS4 (Riley Chen)
**Scenario:** SCN-059, Step 5
**Screenshot:** SCN-059_step5_DS4_notes-participant-1.png

**What's wrong:** The Notes tab does not show a visible "Quick Note" or "New Note" button. Riley must find the create-note action inside the "Actions" dropdown, which requires extra voice commands. Dragon users strongly prefer a visible, labelled button for primary actions.

**Acceptance criteria:**
- [ ] A visible "New Note" or "Quick Note" button appears on the Notes tab with visible text label
- [ ] Dragon can target it by saying "Click New Note" or "Click Quick Note"
- [ ] Re-run SCN-059 step 5 -- efficiency dimension improves to 4.0+

---

### IMPROVE-20: Status dropdown opens inconsistently during Tab navigation

**Severity:** IMPROVE -- Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-062, Steps 1--6
**Screenshot:** SCN-062_step1_DS3_participants.png

**What's wrong:** In some lookups, pressing Tab from the search field opens the status dropdown (steps 1, 2, 6), while in others it does not (steps 3, 5). This inconsistency breaks Amara's predictable mental model of keyboard navigation order.

**Acceptance criteria:**
- [ ] Tab key behaviour is consistent -- dropdown should not open on focus, only on explicit activation (Enter or Space)
- [ ] Re-run SCN-062 -- all 6 steps show consistent Tab behaviour

---

### IMPROVE-21: Phone icons beside client names may lack accessible labels

**Severity:** IMPROVE -- Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-063, Steps 1--2
**Screenshot:** SCN-063_step2_DS3_participants.png

**What's wrong:** Small phone icons appear beside each client name on both the dashboard attention list and the client list. If these are interactive, they need descriptive accessible labels. If decorative, they need `aria-hidden="true"`. Currently, a screen reader may announce them as unlabelled images or buttons.

**Acceptance criteria:**
- [ ] Interactive phone icons have descriptive labels (e.g., "Copy phone number for Aaliyah Thompson")
- [ ] Decorative icons have `aria-hidden="true"` or empty `alt=""`
- [ ] No unlabelled image announcements from JAWS on dashboard or client list

---

### IMPROVE-22: No result count displayed in participant search results

**Severity:** IMPROVE -- Review recommended
**Persona:** R1 (Dana Petrescu)
**Scenario:** SCN-045, Step 4
**Screenshot:** SCN-045_step4_R1_participants.png

**What's wrong:** The participant list does not display a result count (e.g., "Showing 2 of 2 participants"). Dana cannot tell if the list is complete or filtered.

**Acceptance criteria:**
- [ ] A result count is visible above or below the list (e.g., "2 participants found")
- [ ] If results are paginated, pagination controls and total count are visible
- [ ] Re-run SCN-045 step 4 -- score improves to Green band (4.0+)

---

### IMPROVE-23: No "back online" confirmation when connectivity is restored

**Severity:** IMPROVE -- Review recommended
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-048, Step 4
**Screenshot:** SCN-048_step4_DS1_participants-4.png

**What's wrong:** When the network connection is restored after an offline period, the offline banner disappears but there is no positive confirmation that connectivity is back. Casey, who blames herself for errors, would benefit from a brief "You are back online" message.

**Acceptance criteria:**
- [ ] A brief toast or banner appears when connectivity is restored: "You are back online"
- [ ] The message auto-dismisses after 5 seconds
- [ ] Re-run SCN-048 step 4 -- score improves to Green band (4.0+)

---

### IMPROVE-24: Survey assignment path not visible from participants list

**Severity:** IMPROVE -- Review recommended
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-111, Step 1
**Screenshot:** SCN-111_step1_DS1_participants.png

**What's wrong:** Casey navigated to the participants list to assign a survey. There is no "Surveys" link in the navigation bar, no survey column in the participants table, and no bulk action for survey assignment. If the surveys module is not yet built, this is a missing feature.

**Acceptance criteria:**
- [ ] Survey assignment option is accessible from the participant list (bulk action or per-row action)
- [ ] Alternatively, a "Surveys" item appears in the navigation bar for staff roles
- [ ] Re-run SCN-111 step 1 -- survey assignment path is visible and score improves to Green (4.0+)

---

### IMPROVE-25: Alert recommendation workflow blocked by placeholder URLs

**Severity:** IMPROVE -- Review recommended
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-075, Steps 2--5
**Screenshot:** SCN-075_step2_DS1_events-alerts-{alert_id}-cancel.png

**What's wrong:** Steps 2, 3, and 5 contain literal `{alert_id}` and `{recommendation_id}` placeholders that were not substituted. The core alert workflow (cancel alert, write recommendation, R1 denied access) was only partially evaluable.

**Acceptance criteria:**
- [ ] Test runner resolves dynamic IDs from step 1's created alert
- [ ] Re-run SCN-075 -- all steps show distinct, scenario-appropriate content

---

### IMPROVE-26: Funder report small-cell suppression unverifiable

**Severity:** IMPROVE -- Review recommended
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-086, Steps 3--4
**Screenshot:** SCN-086_step1_PM1_reports-funder-report.png

**What's wrong:** Steps 2--4 show the same unmodified form page. The test runner did not select a programme, fill the form, or click "Generate Outcome Report". Small-cell suppression (step 3) and custom age bins (step 4) could not be verified.

**Acceptance criteria:**
- [ ] Test runner successfully interacts with the funder report form
- [ ] Small-cell suppression is active when any cell contains fewer than 5 records
- [ ] Re-run SCN-086 steps 3--4 -- suppression is verifiable

---

### IMPROVE-27: Page title descriptiveness for screen reader orientation

**Severity:** IMPROVE -- Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-064, Steps 1--4
**Screenshot:** SCN-064_step1_DS3_home.png

**What's wrong:** Page title descriptiveness cannot be fully verified from screenshots alone. However, evaluable steps suggest that `document.title` changes are happening but may not include sufficient context (e.g., "KoNote" vs. "Participants -- KoNote").

**Acceptance criteria:**
- [ ] Each page has a unique, descriptive `document.title` (e.g., "Participants -- KoNote", "Jane Doe -- Profile -- KoNote")
- [ ] Title changes are announced by JAWS on page navigation

---

### IMPROVE-28: Focus visibility with sticky headers may obscure focused elements

**Severity:** IMPROVE -- Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-065, Steps 1--4

**What's wrong:** Focus-not-obscured verification requires screenshots at various scroll positions. The sticky header may overlap focused elements during keyboard navigation. The evaluable steps show acceptable focus indicators but cannot confirm behaviour when scrolled.

**Acceptance criteria:**
- [ ] Focused elements are never fully obscured by sticky headers or footers
- [ ] WCAG 2.4.11 (Focus Not Obscured, Minimum) -- focused element is at least partially visible

---

### IMPROVE-29: Group milestone and attendance URLs use unresolved placeholders

**Severity:** IMPROVE -- Review recommended
**Persona:** DS1 (Casey Makwa) / PM1 (Morgan Tremblay)
**Scenario:** SCN-076, Steps 4--5
**Screenshot:** SCN-076_step4_DS1_groups-{group_id}-milestone.png

**What's wrong:** URLs contain literal `{group_id}` placeholder. The test runner needs to capture the group ID from step 1 or 2's creation response and substitute it.

**Acceptance criteria:**
- [ ] Test runner captures group ID from creation response and substitutes into subsequent URLs
- [ ] Re-run SCN-076 steps 4--5 -- milestone and attendance pages load correctly

---

### IMPROVE-30: Voice control note save not verified

**Severity:** IMPROVE -- Review recommended
**Persona:** DS4 (Riley Chen)
**Scenario:** SCN-059, Step 6
**Screenshot:** SCN-059_step6_DS4_notes-participant-1.png

**What's wrong:** Step 6 is identical to step 5 -- note save was not exercised. The voice control save workflow needs to be tested. Additionally, the scenario revealed that the "Actions" dropdown requires multi-step voice interaction that Dragon users would find cumbersome.

**Acceptance criteria:**
- [ ] Note save produces a visible confirmation
- [ ] Voice command "Click Save" or "Click Submit" works on the note form
- [ ] Re-run SCN-059 step 6 -- post-save confirmation state is visible

---

## Test Infrastructure Issues (27)

These are test runner or test data problems, not app bugs. Fix in `konote-app` test infrastructure.

---

### TEST-1: SCN-035 all steps blocked -- /reports/funder/ URL returns 404

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-035, Steps 1--5, Persona PM1
**Reason:** The scenario navigates to `/reports/funder/` which returns "Page Not Found". The funder report feature exists at `/reports/funder-report/` (confirmed by SCN-086). Fix the scenario URL or add a redirect.
**Fix in:** konote-qa-scenarios scenario YAML or konote-app routing
**Priority:** Fix before next round -- blocks PM1 funder reporting workflow

---

### TEST-2: SCN-036 step 2 blocked -- test runner did not click "Create Template"

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-036, Step 2, Persona PM1
**Reason:** Step 2 screenshot is identical to step 1 -- the test runner did not successfully click the "Create Template" button or interact with the creation form.
**Fix in:** konote-app test runner -- ensure button click selector matches the rendered element
**Priority:** Fix before next round -- blocks PM self-service template creation

---

### TEST-3: SCN-037 steps 5--6 have no audit data -- scope verification impossible

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-037, Steps 5--6, Persona PM1
**Reason:** Audit Log page loads but shows "No audit log entries found." for all searches. The test environment has no audit log data, so the programme scope boundary cannot be verified.
**Fix in:** konote-app test runner -- seed audit log data in test environment prerequisites
**Priority:** Fix before next round -- blocks verification of `audit.view: scoped`

---

### TEST-4: SCN-040 step 3 blocked -- duplicate screenshot

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-040, Step 3, Persona DS2
**Reason:** Duplicate screenshot -- step 2 and step 3 show identical create form. The quick-note navigation or form submission did not execute.
**Fix in:** konote-app test runner -- ensure step 3 navigates to the quick-note form after client creation
**Priority:** Fix before next round if testing French-language note creation

---

### TEST-5: SCN-045 step 4 -- insufficient test data for many-result scenario

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-045, Step 4, Persona R1
**Reason:** Only 2 participants visible to receptionist; scenario requires 15+ clients with names starting with J to test search volume handling.
**Fix in:** konote-app test runner data seeding
**Priority:** Fix before next round if testing search pagination

---

### TEST-6: SCN-046 all steps blocked -- test runner failed to navigate to quick note form

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-046, Steps 1--4, Persona DS1
**Reason:** All 4 screenshots are identical (Jane Doe Info tab). The test runner did not click through to the quick note form. The `a[href*="quick"]` selector likely did not match any element.
**Fix in:** konote-app test runner -- verify quick note URL selector and ensure Notes tab is clicked first
**Priority:** Fix before next round -- this scenario tests Casey's biggest fear (data loss on timeout)

---

### TEST-7: SCN-047 steps 4--5 -- test runner navigated to create form instead of client profile

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-047, Steps 4--5, Persona R2
**Reason:** Click selector `a[href*="/participants/"]` matched the wrong link (likely "+ New Participant" instead of the client profile link from search results).
**Fix in:** konote-app test runner -- use more specific selector for client profile link
**Priority:** Fix before next round -- mobile profile and edit views are untested

---

### TEST-8: SCN-048 steps 2--4 -- consent gate blocked note form access

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-048, Steps 2--4, Persona DS1
**Reason:** James Thompson has "No Consent" status. The app correctly prevents note creation without consent, but this blocked the scenario's core test. Test data needs a client with consent on file.
**Fix in:** konote-app test runner data seeding -- ensure the client used for SCN-048 has consent recorded
**Priority:** Fix before next round -- offline note preservation is critical coverage for DS1

---

### TEST-9: SCN-049 steps 3--6 -- test runner stopped after step 2; multi-user handoff not tested

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-049, Steps 3--6, Personas DS1/R1
**Reason:** Only 2 of 6 screenshots captured. Multi-user scenarios (switching between DS1 and R1 in same browser context) may not be supported by the test runner. The consent gate also prevented establishing cached note data.
**Fix in:** konote-app test runner -- add support for multi-user sequential scenarios
**Priority:** Critical -- shared device data bleed is a PIPEDA compliance test

---

### TEST-10: SCN-050 steps 3--7 blocked by navigation failure at step 3

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-050, Steps 3--7, Persona DS3
**Reason:** Tab sequence at step 3 navigated to Programs page instead of create-participant button, causing cascading failures for all subsequent steps. The keyboard-only test sequence does not match the current Tab order.
**Fix in:** konote-app test runner -- verify keyboard navigation sequences match current page Tab order
**Priority:** Fix before next round -- blocks the primary accessibility scenario

---

### TEST-11: SCN-051 login screenshots may be duplicates

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-051, Steps 1--2, Persona DS3
**Reason:** Both login steps may show identical screenshots since the test runner captures before and after login at the same visual state. Need to verify that step 2 captures the post-login page, not the login form.
**Fix in:** konote-app test runner -- ensure post-login screenshot captures the dashboard
**Priority:** Low -- does not block evaluation if step 2 is correct

---

### TEST-12: SCN-052 landed on wrong page -- test navigation failure

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-052, Steps 1--2, Persona DS3
**Reason:** Test was supposed to navigate to `/participants/` and test skip link; instead ended on `/participants/create/`. Tab+Enter sequence may have activated the "+ New Participant" button instead of a skip link.
**Fix in:** konote-app test runner -- ensure `goto('/participants/')` is confirmed before keyboard actions begin
**Priority:** Fix before next round -- blocks skip link and landmark evaluation

---

### TEST-13: SCN-056 all steps blocked -- 200% zoom and high-contrast mode not applied

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-056, Steps 1--4, Persona DS3
**Reason:** All four screenshots show standard zoom and normal colour scheme. The test runner's `set_zoom(200)` and `set_high_contrast(true)` commands did not take effect.
**Fix in:** konote-app test runner -- implement Playwright browser zoom via CDP and `page.emulateMedia({ forcedColors: 'active' })`
**Priority:** Fix before next round -- 200% zoom and high-contrast testing is critical for AODA compliance

---

### TEST-14: SCN-058 steps 4--6 not exercised (note form never reached)

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-058, Steps 4--6, Persona DS1c
**Reason:** The test runner never navigated from the dashboard to Jane Doe's profile or opened the note form. Steps 4, 5, and 6 all show the same dashboard screenshot.
**Fix in:** konote-app test runner -- ensure navigation to client profile and note form completes
**Priority:** Fix before next round -- cognitive load of note entry is critical for ADHD persona

---

### TEST-15: SCN-059 steps 2--3 and step 6 not exercised (duplicate screenshots)

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-059, Steps 2, 3, 6, Persona DS4
**Reason:** Steps 2 and 3 show the same dashboard screenshot as step 1. Step 6 is identical to step 5. The test runner did not simulate voice control workflow transitions.
**Fix in:** konote-app test runner -- voice control scenarios need simulated workflow transitions
**Priority:** Fix before next round -- Dragon NaturallySpeaking navigation coverage is minimal

---

### TEST-16: SCN-062 step 5 network error simulation did not fire

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-062, Step 5, Persona DS3
**Reason:** Step 5 was designed to test error announcement by intercepting the HTMX request with a 500 status. The screenshot shows a normal successful search result -- the network interception did not work.
**Fix in:** konote-app test runner -- verify network interception fires before HTMX request
**Priority:** Fix before next round -- error announcement testing is important for screen reader users

---

### TEST-17: SCN-075 steps 2, 3, 5 blocked -- {alert_id} and {recommendation_id} not substituted

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-075, Steps 2/3/5, Personas DS1/PM1
**Reason:** URLs contain literal `{alert_id}` and `{recommendation_id}` placeholders instead of actual IDs. The test runner needs to resolve these from step 1's created alert.
**Fix in:** konote-app test runner -- implement dynamic ID substitution from prior step output
**Priority:** Fix before next round -- blocks 3 of 6 steps

---

### TEST-18: SCN-076 steps 4--5 blocked -- {group_id} not substituted

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-076, Steps 4/5, Personas DS1/PM1
**Reason:** URLs contain literal `{group_id}` placeholder. The test runner needs to capture the group ID from step 1 or 2's creation response.
**Fix in:** konote-app test runner -- implement dynamic ID capture and substitution
**Priority:** Fix before next round -- blocks milestone and attendance views

---

### TEST-19: SCN-082 steps 2--4 blocked -- no meeting data in test environment

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-082, Steps 2--4, Persona PM1
**Reason:** All 5 screenshots show the same empty "My Meetings" page. The scenario prerequisites specify 3 meetings but none were created in the test environment.
**Fix in:** konote-app test runner -- create meeting seed data matching scenario prerequisites
**Priority:** Fix before next round -- blocks the entire PM meeting oversight workflow

---

### TEST-20: SCN-084 entirely blocked -- client/meeting IDs not substituted

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-084, Steps 1--5, Personas DS1/PM1
**Reason:** All communication URLs contain literal `{client_id_alex}`, `{client_id_priya}`, `{meeting_id_alex}`, `{meeting_id_priya}` placeholders. Steps 4--5 also ended on wrong page (Meetings dashboard instead of client profile).
**Fix in:** konote-app test runner -- resolve prerequisite data IDs before navigating
**Priority:** Fix before next round -- consent guardrails scenario is 0% evaluable

---

### TEST-21: SCN-086 steps 2--4 blocked -- test runner did not interact with funder report form

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-086, Steps 2--4, Persona PM1
**Reason:** Steps 2--4 show the same unmodified form page. The test runner did not select a programme, fill the form, or click "Generate Outcome Report".
**Fix in:** konote-app test runner -- update selectors for the actual funder report form elements
**Priority:** Fix before next round -- blocks small-cell suppression and funder profile verification

---

### TEST-22: SCN-111 step 2 blocked -- identical screenshot, no survey navigation

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-111, Step 2, Persona DS1
**Reason:** Duplicate screenshot -- test runner navigated to `/participants/` but never advanced to a survey assignment page. The surveys module may not exist at `/surveys/` or may be accessed from within participant records.
**Fix in:** konote-app test runner or scenario YAML
**Priority:** Fix before next round -- surveys category is entirely untestable

---

### TEST-23: SCN-114 steps 1--2 blocked -- /surveys/ returns 404

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-114, Steps 1--2, Persona PM1
**Reason:** The `/surveys/` URL returns 404. The surveys module either does not exist or is at a different URL.
**Fix in:** konote-app (build surveys module) or scenario YAML (correct URL if surveys live elsewhere)
**Priority:** Fix before next round -- entire surveys reporting workflow is untestable for PM role

---

### TEST-24: SCN-115 steps 1--2 blocked -- /surveys/ returns 404

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-115, Steps 1--2, Persona DS1
**Reason:** Same root cause as TEST-23. The `/surveys/` URL returns 404.
**Fix in:** konote-app (build surveys module) or scenario YAML (correct URL)
**Priority:** Fix before next round -- data correction workflow is untestable

---

### TEST-25: SCN-116 steps 1--2 blocked -- /surveys/ returns 404

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-116, Steps 1--2, Persona DS1
**Reason:** Same root cause as TEST-23 and TEST-24. Conditional logic testing is impossible without the surveys module.
**Fix in:** konote-app (build surveys module) or scenario YAML (correct URL)
**Priority:** Fix before next round

---

### TEST-26: SCN-117 steps 1--2 blocked -- /surveys/ returns 404 (French interface)

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-117, Steps 1--2, Persona DS2
**Reason:** Same root cause. Positive finding: the 404 page is fully translated to French with zero English bleed-through, suggesting the i18n infrastructure will support surveys when built.
**Fix in:** konote-app (build surveys module) or scenario YAML (correct URL)
**Priority:** Fix before next round -- French survey completion is entirely untestable

---

### TEST-27: SCN-155 not captured -- no screenshots produced by test runner

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-155, All steps, Persona PM1
**Reason:** No screenshots exist for SCN-155. The test runner either did not include this scenario in the run, or the service episode feature is not yet implemented, or the scenario was excluded from the manifest.
**Fix in:** Check test runner manifest. Include SCN-155 in next test run if the feature is available.
**Priority:** Fix before next round if service episode lifecycle is implemented

---

## Finding Groups

| Group | Root Cause | Primary Ticket | Also Affects |
|-------|-----------|----------------|--------------|
| FG-S-1 | 404 instead of 403 for restricted pages | BUG-1 | SCN-010/6, SCN-025/3, SCN-042/4, SCN-075/2 |
| FG-S-2 | French/English language mixing in welcome banners | BUG-3 | SCN-026/1, SCN-040/1 |
| FG-S-3 | Accented characters corrupted during save/display | BUG-5 | SCN-040/4 |
| FG-S-4 | Test runner does not substitute dynamic URL placeholders | TEST-17 | SCN-075/2-3-5, SCN-076/4-5, SCN-084/1-5 |
| FG-S-5 | Skip-to-content link missing or misdirected | BUG-17 | SCN-050/2-3, SCN-052/1 |
| FG-S-6 | Keyboard Tab order does not follow visual layout on create form | BUG-16 | SCN-050/4, SCN-053/2, SCN-056/4, SCN-061/1 |
| FG-S-7 | Client profile tabs lack ARIA tablist pattern | BUG-19 | SCN-050/5, SCN-054/2 |
| FG-S-8 | Surveys module does not exist at /surveys/ | BLOCKER-2 | SCN-111, SCN-114, SCN-115, SCN-116, SCN-117 |
| FG-S-9 | PIPEDA compliance features not implemented (export, withdrawal, secure links) | BUG-12 | SCN-070/1-4, SCN-151/1-4 |
| FG-S-10 | Executive dashboard lacks board-presentation features | IMPROVE-2 | SCN-030/1-4 |
| FG-S-11 | Programme scope indicators missing from self-service admin pages | IMPROVE-6 | SCN-036/1-5, SCN-037/5, SCN-082/1 |
| FG-S-12 | PM scoped user management path does not exist | BUG-7 | SCN-037/1-4 |
| FG-S-13 | Test data not seeded (meetings, audit, consent) | TEST-3 | SCN-048/2-4, SCN-082/2-4 |
| FG-S-14 | 403 pages use generic jargon instead of role-aware messaging | IMPROVE-11 | SCN-075/6, SCN-076/3-6, SCN-085/1-3 |
| FG-S-15 | Meetings/communications features all 404 or empty | BUG-8 | SCN-080, SCN-081, SCN-082, SCN-084 |
| FG-S-16 | Dashboard cognitive overload for ADHD users | BUG-21 | SCN-058/1-2 |
| FG-S-17 | HTMX search lacks loading indicator and aria-live announcements | BUG-22 | SCN-048/1, SCN-055/1-2 |

---

## Items NOT Filed as Tickets

The following were noted but are probable test artefacts, not app bugs:

1. **SCN-117 French 404 page** -- The 404 page is fully translated to French with zero English bleed-through, including gender-inclusive language (Participant(e)s), footer links, and user identity. This is a **positive finding** showing the 404 template handles i18n correctly. Filed as part of FG-S-8 (survey feature not deployed).

2. **SCN-085 correct 403 denials** -- The receptionist correctly received access denied messages for Meetings, Messaging, and Reports pages. The denial itself is correct behaviour; the only issue is the generic wording (filed as IMPROVE-11). The permission model is working as designed for R1.

3. **SCN-065 focus visibility** -- Steps that were evaluable showed acceptable focus indicators (2px blue outline, visible against white background). The scenario scored 3.71 (Yellow) primarily because sticky-header obscuration could not be fully verified from static screenshots. Not filed as a bug because the evaluable evidence was positive.

4. **SCN-064 page titles** -- Page title descriptiveness cannot be verified from screenshots alone. Filed as IMPROVE-27 for investigation, but may resolve to a TEST ticket once `document.title` capture is added to the test runner.

5. **Duplicate login screenshots across SCN-051** -- Steps 1 and 2 of SCN-051 may show identical login page screenshots. This is a test runner timing issue (screenshot captured before the post-login redirect completes), not an app bug.

6. **SCN-049 demo login buttons** -- The login page displays one-click demo login buttons for all staff/admin personas. These are almost certainly development-only convenience features and would not appear in production. Not filed as a separate ticket here, but previously flagged in prior rounds.
