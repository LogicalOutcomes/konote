# Improvement Tickets — Round 7

**Date:** 2026-03-01
**Report ID:** 2026-03-01aa
**Round:** Round 7
**Total tickets:** 84 (2 PERMISSION, 13 BLOCKER, 35 BUG, 16 IMPROVE, 18 TEST)

---

## Status of Previous Tickets (Round 6)

No tickets from Round 6 have been confirmed fixed. The gap between Round 6 (2026-02-17) and Round 7 focused on new scenario development (SCN-150–162) rather than bug fixing.

---

## PERMISSION Tickets (2)

### PERMISSION-1: Admin nav item visible for executive role

**Severity:** BLOCKER (authorization violation)
**Persona:** E2 (Kwame)
**Scenario:** SCN-030, Step 1

**Violation type:** page_access

**What's wrong:** The executive dashboard shows admin navigation items visible to E2. Executives should see aggregate data only — admin navigation implies access to individual records.

**Expected behaviour:** E2's `permission_scope` limits access to aggregate dashboards only. Admin nav items should be hidden.

**Compliance references:** PIPEDA 4.7 (safeguards)

**Where to look:** Django template nav include, view-level permission check

**Acceptance criteria:**
- [ ] E2 login shows no admin nav items
- [ ] Re-run SCN-030 step 1 — only executive-appropriate nav visible

**Screenshot reference:** SCN-030_step1_E2_participants.png

---

### PERMISSION-2: Executive audit log access design gap

**Severity:** BLOCKER (authorization design conflict)
**Persona:** E1 (Margaret)
**Scenario:** SCN-070, Step 4

**Violation type:** data_scope (design gap)

**What's wrong:** SCN-070 expects E1 to view the audit log for PIPEDA board oversight, but the E1 persona definition has `audit.view: deny`. This is a policy design question, not a code bug.

**Expected behaviour:** Decision needed — should executives have read-only audit log access for PIPEDA 4.1.4 (board accountability)?

**Compliance references:** PIPEDA 4.1.4 (accountability)

**Acceptance criteria:**
- [ ] Decision documented on whether E1 gets audit.view access
- [ ] If yes: update persona YAML and grant access
- [ ] If no: update SCN-070 to remove the E1 audit step

---

## BLOCKER Tickets (12)

### BLOCKER-1: Funder demographic profile dropdown absent

**Severity:** BLOCKER
**Persona:** PM1 (Morgan)
**Scenario:** SCN-086, Step 2
**Screenshot:** SCN-086_step2_PM1_participants.png

**What's wrong:** The funder report page has no demographic profile dropdown. Small-cell suppression (the privacy protection that prevents individual client identification in demographic tables) cannot be verified.

**Where to look:** Funder report template, view for demographic profile selection

**Acceptance criteria:**
- [ ] Demographic profile dropdown is available on funder report page
- [ ] Small-cell suppression is active when any cell contains < 5 records
- [ ] Re-run SCN-086 — score improves to Green band (4.0+)

---

### BLOCKER-2: /communications/ URL namespace retired

**Severity:** BLOCKER
**Persona:** DS1 (Casey), PM1 (Morgan)
**Scenario:** SCN-084

**What's wrong:** The `/communications/` URL path was replaced by Quick Notes. The SCN-084 scenario YAML needs updated URLs to test the consent guardrail workflow.

**Where to look:** Scenario YAML update needed (not an app bug)

**Acceptance criteria:**
- [ ] SCN-084 YAML updated with current Quick Notes URL pattern
- [ ] Re-run SCN-084 to evaluate the consent guardrail workflow

---

### BLOCKER-3: Service episode lifecycle feature not visible

**Severity:** BLOCKER
**Persona:** PM1 (Morgan)
**Scenario:** SCN-155, Steps 2–4

**What's wrong:** Steps 2–4 contain only `wait_for: networkidle` with no navigation or click actions. The service episode lifecycle (on-hold, reactivation, discharge) is either not implemented or the scenario YAML is incomplete. All 4 screenshots are identical (client profile).

**Where to look:** Feature implementation status; scenario YAML actions

**Acceptance criteria:**
- [ ] Service episode status change UI is available on client profile
- [ ] SCN-155 YAML updated with correct selectors and actions
- [ ] Re-run SCN-155 — episode lifecycle transitions work

---

### BLOCKER-4: Skip link navigates to Privacy Policy instead of main content

**Severity:** BLOCKER
**Persona:** DS3 (Amara)
**Scenario:** SCN-050, Step 2

**What's wrong:** Activating the skip link sends the user to the Privacy Policy page instead of the main content area. WCAG 2.4.1 failure.

**Where to look:** Skip link `href` target in base template

**Acceptance criteria:**
- [ ] Skip link navigates to `#main-content` or equivalent
- [ ] Verified with JAWS screen reader
- [ ] Re-run SCN-050 step 2 — score improves to Green band (4.0+)

---

### BLOCKER-5: Language toggle buttons intercept Tab flow before login form

**Severity:** BLOCKER
**Persona:** DS3 (Amara)
**Scenario:** SCN-050, Step 1

**What's wrong:** Language toggle buttons (English/Français) are early in the Tab order, before the login form fields. Keyboard users must Tab through them to reach the login form. Accidental activation switches the interface language. WCAG 2.4.3 failure.

**Where to look:** Login template Tab order, language toggle placement

**Acceptance criteria:**
- [ ] Login form fields receive focus before language toggle
- [ ] Language toggle is after the login form or uses a different interaction pattern
- [ ] Re-run SCN-050 step 1 and SCN-051 step 1

---

### BLOCKER-6: Actions dropdown keyboard navigation activates wrong menu item

**Severity:** BLOCKER
**Persona:** DS3 (Amara)
**Scenario:** SCN-050, Step 6

**What's wrong:** Using keyboard navigation in the Actions dropdown opens "Record Event" instead of "Quick Note." The dropdown does not follow the ARIA menu pattern for keyboard interaction. WCAG 4.1.2 failure.

**Where to look:** Actions dropdown JavaScript, ARIA roles and keyboard event handlers

**Acceptance criteria:**
- [ ] ArrowDown/Up navigates dropdown items without activating them
- [ ] Enter/Space activates the focused item
- [ ] Re-run SCN-050 step 6 — correct item is activated

---

### BLOCKER-7: Skip link on participants list misdirected

**Severity:** BLOCKER
**Persona:** DS3 (Amara)
**Scenario:** SCN-052, Step 1

**What's wrong:** Skip link on the participants list page navigates to the New Participant form instead of the main content area. Same root cause as BLOCKER-4. WCAG 2.4.1 failure.

**Where to look:** Skip link `href` target on participants list template

**Acceptance criteria:**
- [ ] Skip link navigates to the participant list content
- [ ] Re-run SCN-052 step 1

---

### BLOCKER-8: Session timeout — note form never reached

**Severity:** BLOCKER
**Persona:** DS1 (Casey)
**Scenario:** SCN-046, Steps 1–4

**What's wrong:** The note form was never reached because the quick note selector (`a[href*="quick"]`) did not match. Auto-save and timeout recovery could not be tested. This is partially a test infrastructure issue (TEST-6) but the underlying question — does auto-save work during session timeout? — remains unanswered.

**Where to look:** Quick note URL pattern, auto-save JavaScript

**Acceptance criteria:**
- [ ] Quick note URL pattern updated in scenario YAML
- [ ] Auto-save activates after 30 seconds of inactivity
- [ ] Session timeout does not destroy unsaved note content
- [ ] Re-run SCN-046

---

### BLOCKER-9: Demo login buttons allow credential-free access

**Severity:** BLOCKER (security)
**Persona:** DS1 (Casey), R1 (Dana)
**Scenario:** SCN-049, Step 2

**What's wrong:** The login page displays one-click demo login buttons for all staff/admin personas by name and role. On a shared nonprofit device after shift handoff, anyone can click "Front Desk — Dana" and access the system without credentials.

**Where to look:** Login template — confirm these are dev-only and not present in production

**Acceptance criteria:**
- [ ] Demo login buttons are only shown in DEBUG mode or development environments
- [ ] Production login requires credentials
- [ ] Re-run SCN-049 in a production-like environment

---

### BLOCKER-10: Data export workflow not implemented

**Severity:** BLOCKER (PIPEDA compliance)
**Persona:** PM1 (Morgan), E1 (Margaret)
**Scenario:** SCN-070, Steps 1–2

**What's wrong:** There is no data export button or workflow on the client profile. PIPEDA Principle 9 (right of access) requires organizations to provide individuals with access to their personal information upon request.

**Where to look:** Client profile template, export view

**Acceptance criteria:**
- [ ] Data export button available on client profile for authorized roles
- [ ] Export generates a secure download link
- [ ] Export is logged in the audit trail
- [ ] Re-run SCN-070 steps 1–2

---

### BLOCKER-11: Consent withdrawal workflow not implemented

**Severity:** BLOCKER (PIPEDA compliance)
**Persona:** PM1 (Morgan)
**Scenario:** SCN-070, Steps 3–4

**What's wrong:** There is no consent withdrawal or data deletion workflow. PIPEDA Principle 4.5 requires that personal information no longer needed be destroyed.

**Where to look:** Client profile consent section, deletion workflow

**Acceptance criteria:**
- [ ] Consent withdrawal option available on client profile
- [ ] Withdrawal triggers data anonymization or deletion per policy
- [ ] Audit trail records the withdrawal
- [ ] Re-run SCN-070 steps 3–4

---

### BLOCKER-12: Secure download link infrastructure not implemented

**Severity:** BLOCKER (PIPEDA compliance)
**Persona:** PM1 (Morgan), ADMIN1 (Priya)
**Scenario:** SCN-151, Steps 1–4

**What's wrong:** The entire secure download link infrastructure is missing. `/reports/download/{id}/` returns a generic 404. `/admin/export-links/` (admin management page) also returns 404. Single-use enforcement, 24-hour expiry, and admin revocation cannot be tested.

**Where to look:** Download link model, view, URL routing, admin management page

**Acceptance criteria:**
- [ ] Download links are single-use
- [ ] Links expire after 24 hours
- [ ] Admin can view and revoke active links
- [ ] Expired/used/revoked links return clear plain-language messages
- [ ] Re-run SCN-151

---

### BLOCKER-13: Login autofocus race condition exposes credentials in search bar

**Severity:** BLOCKER (security)
**Persona:** DS4 (voice control user)
**Scenario:** SCN-059, Step 1

**What's wrong:** After login, the password text `testpassword` appeared in the dashboard search bar as `stafftestpassword`. Two elements on the login page compete for autofocus, creating a race condition where Dragon NaturallySpeaking's pending keystrokes flush into the dashboard search bar after redirect. The password is displayed in plain text on screen and sent as a search query.

**Where to look:** Login template autofocus, redirect handling after login POST

**Acceptance criteria:**
- [ ] Only one element has autofocus on the login page
- [ ] After login redirect, no input field receives stale keystrokes
- [ ] Password text never appears in any non-password field
- [ ] Re-run SCN-059 step 1

---

## BUG Tickets (35)

### BUG-1: Newly created client not searchable by other users

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-010, Step 4

**What's wrong:** DS1 searched for "Sofia Reyes" immediately after R1 created her and got zero results. Cross-role intake handoff fails.

**Acceptance criteria:**
- [ ] Newly created clients are immediately searchable by other users
- [ ] Re-run SCN-010 step 4

---

### BUG-2: 404 instead of 403 for receptionist accessing notes

**Severity:** BUG — Priority fix
**Persona:** R1 (Dana)
**Scenario:** SCN-010, Step 6

**What's wrong:** Navigating to `/participants/NNN/notes/` as receptionist returns "Page Not Found" instead of "Access Denied." Dana thinks she typed something wrong rather than understanding it's a permission restriction.

**Acceptance criteria:**
- [ ] Restricted pages return a styled 403 with "You don't have permission" message
- [ ] Re-run SCN-010 step 6 and SCN-025 step 3

---

### BUG-3: Mixed French/English on client profile

**Severity:** BUG — Priority fix
**Persona:** DS1/DS2
**Scenario:** SCN-010, Step 5

**What's wrong:** Client profile shows "Phone Number" (English label) while section headers are in French.

---

### BUG-4: Quick-note entry point unreachable

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-015, Step 2

**What's wrong:** The selector `a[href*='quick']` matches nothing on the client profile. Quick note creation is inaccessible via expected URL pattern.

---

### BUG-5: 404 instead of 403 for R2 accessing notes

**Severity:** BUG — Priority fix
**Persona:** R2 (Omar)
**Scenario:** SCN-025, Step 3

**What's wrong:** Same as BUG-2 but affecting R2 persona. Same root cause (FG-S-1).

---

### BUG-6: English-only text on French home page

**Severity:** BUG — Priority fix
**Persona:** R2-FR (Amélie)
**Scenario:** SCN-026, Step 1

**What's wrong:** Onboarding banner and "Vos outils de reception" section have English-only bullet points despite French language preference.

---

### BUG-7: French create-participant navigation broken

**Severity:** BUG — Priority fix
**Persona:** R2-FR (Amélie)
**Scenario:** SCN-026, Step 1

**What's wrong:** French "Créer un participant" navigation does not work.

---

### BUG-8: Calendar feed URL generation silently fails

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-083, Step 2

**What's wrong:** Clicking the generate button for calendar feed URL produces no visible result.

---

### BUG-9: No date-range presets on executive dashboard

**Severity:** BUG — Priority fix
**Persona:** E1 (Margaret)
**Scenario:** SCN-030, Step 1

**What's wrong:** Executive dashboard has no quarter or date-range presets for filtering.

---

### BUG-10: Executive dashboard exports CSV only — no PDF

**Severity:** BUG — Priority fix
**Persona:** E1 (Margaret)
**Scenario:** SCN-030, Step 2

**What's wrong:** Export is CSV only. Margaret needs PDF for board packages.

---

### BUG-11: Interface switches to French for English-preferring PM

**Severity:** BUG — Priority fix
**Persona:** PM1 (Morgan)
**Scenario:** SCN-035, Step 1

**What's wrong:** The interface switches to French mid-session for Morgan, who prefers English. Language preference not persisting.

---

### BUG-12: /reports/funder/ returns 404

**Severity:** BUG — Priority fix
**Persona:** PM1 (Morgan)
**Scenario:** SCN-035, Step 2

**What's wrong:** The funder report export URL does not exist.

---

### BUG-13: PM user management path missing

**Severity:** BUG — Priority fix
**Persona:** PM1 (Morgan)
**Scenario:** SCN-037, Step 1

**What's wrong:** `/manage/users/` is missing or not linked. PM cannot manage staff.

---

### BUG-14: English strings in French onboarding banner

**Severity:** BUG — Priority fix
**Persona:** DS2 (Jean-Luc)
**Scenario:** SCN-040, Step 1

**What's wrong:** Dashboard onboarding banner contains English strings despite French language preference.

---

### BUG-15: Accent stripping in client list display

**Severity:** BUG — Priority fix
**Persona:** DS2 (Jean-Luc)
**Scenario:** SCN-040, Step 2

**What's wrong:** "Benoît" appears as "Benoit" in the client list — accents stripped from display.

---

### BUG-16: Cross-program URL returns 404 instead of 403

**Severity:** BUG — Priority fix
**Persona:** PM1 (Morgan)
**Scenario:** SCN-042, Step 4

**What's wrong:** Accessing a client in another program returns "Page Not Found" instead of "Access Denied."

---

### BUG-17: Alert cancel URL returns 404 instead of 403

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-075, Step 2

**What's wrong:** Alert action URL returns 404 instead of 403.

---

### BUG-18: Group form doesn't auto-scope programme

**Severity:** BUG — Priority fix
**Persona:** PM1 (Morgan)
**Scenario:** SCN-076, Step 2

**What's wrong:** Group creation form does not auto-select PM's programme. Morgan must manually select "Housing Support."

---

### BUG-19: Language toggles precede login form in Tab order

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara)
**Scenario:** SCN-051, Step 1

**What's wrong:** Language toggles come before the login form in Tab order. WCAG 2.4.3 issue.

---

### BUG-20: Create form Tab order doesn't match visual layout

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara)
**Scenario:** SCN-053, Step 1

**What's wrong:** Last Name receives focus before First Name in two-column layout. WCAG 1.3.2 / 2.4.3.

---

### BUG-21: Profile tabs don't support arrow key navigation

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara)
**Scenario:** SCN-054, Step 2

**What's wrong:** ArrowRight on profile tabs opens the Actions dropdown instead of navigating to the next tab. WCAG 4.1.2.

---

### BUG-22: Excessive Tab presses to reach search results

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara)
**Scenario:** SCN-055, Step 2

**What's wrong:** Filter controls sit between search field and results in Tab order, requiring > 5 Tab presses. WCAG 2.4.3 / 4.1.3.

---

### BUG-23: Checkboxes too small for tablet touch

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-057, Step 4

**What's wrong:** Checkboxes in create form are browser default ~16px, below WCAG 2.5.8 minimum 24px target.

---

### BUG-24: Validation error not displayed after missing required field

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-045, Step 2

**What's wrong:** Submitting form with missing required field shows no validation error message.

---

### BUG-25: French /clients/create/ URL returns 404

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-045, Step 3

**What's wrong:** French locale `/clients/create/` routing is broken.

---

### BUG-26: No success confirmation after participant creation

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-045, Step 2

**What's wrong:** After submitting the participant form, there is no visible success confirmation.

---

### BUG-27: French locale persists into English R2 session

**Severity:** BUG — Priority fix
**Persona:** R2 (Omar)
**Scenario:** SCN-047, Step 2

**What's wrong:** French language state from a previous session bleeds into Omar's English session on mobile.

---

### BUG-28: Mobile edit navigates to wrong form

**Severity:** BUG — Priority fix
**Persona:** R2 (Omar)
**Scenario:** SCN-047, Step 4

**What's wrong:** Edit contact info on mobile navigates to the New Participant form instead of the contact edit form.

---

### BUG-29: Offline navigation renders blank white page

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-048, Step 4

**What's wrong:** Navigating while offline shows a blank white page instead of the styled offline error page.

---

### BUG-30: Survey feature missing — assignment interface

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-111, Step 1

**What's wrong:** `/surveys/` URL and navigation entry do not exist. Survey assignment feature not deployed.

---

### BUG-31: Survey feature missing — results page

**Severity:** BUG — Priority fix
**Persona:** PM1 (Morgan)
**Scenario:** SCN-114, Step 1

**What's wrong:** `/surveys/` returns 404 for program manager viewing survey results.

---

### BUG-32: Survey feature missing — edit interface

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey)
**Scenario:** SCN-115, Step 1

**What's wrong:** `/surveys/` returns 404 for staff editing survey responses.

---

### BUG-33: Form validation destroys entered Last Name data

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara)
**Scenario:** SCN-061, Step 2

**What's wrong:** When a form validation error occurs, the Last Name value migrates to the Preferred Name field — silent data corruption especially problematic for screen reader users who can't visually notice the shift.

---

### BUG-34: Form resubmission navigates to help page

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara)
**Scenario:** SCN-061, Step 3

**What's wrong:** Resubmitting the corrected participant form navigates to a help page instead of completing the creation.

---

### BUG-35: Tab after search lands on status filter, not first result

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara)
**Scenario:** SCN-062, Step 1

**What's wrong:** After searching, Tab key focuses the status filter dropdown instead of the first search result row. Screen reader users must Tab through multiple filter controls to reach results.

---

## IMPROVE Tickets (15)

### IMPROVE-1: First-login attention panel overwhelming for new users

**Scenario:** SCN-005, Step 2 (DS1b)

The "What Needs Your Attention" panel shows 10+ unfamiliar client names for a brand-new user. Consider showing a simpler welcome panel for first-week users.

---

### IMPROVE-2: No "Notes Today" counter for batch entry confirmation

**Scenario:** SCN-015, Step 5 (DS1)

Add a counter showing how many notes were entered today so Casey can confirm she's caught up.

---

### IMPROVE-3: Section-level edit instead of field-level inline edit

**Scenario:** SCN-020, Step 3 (R1)

Phone number update requires section-level Edit instead of field-level inline editing. Consider inline edit for single-field updates.

---

### IMPROVE-4: Calendar-quarter date presets for funder report

**Scenario:** SCN-035 (PM1)

Add Q1/Q2/Q3/Q4 date presets to the funder report form so Morgan doesn't have to manually enter date ranges.

---

### IMPROVE-5: Navigation sidebar across PM admin pages

**Scenario:** SCN-036 (PM1)

PM self-service admin pages have no navigation sidebar. Add sidebar linking all PM admin sections.

---

### IMPROVE-6: Programme scope label on template/group pages

**Scenario:** SCN-036 (PM1)

Template and group management pages should show which programme they belong to.

---

### IMPROVE-7: Audit log programme scope label

**Scenario:** SCN-037 (PM1)

Audit log subtitle implies unscoped access — add programme scope label so Morgan knows she's seeing her programme's logs only.

---

### IMPROVE-8: Meeting dashboard positive health indicator

**Scenario:** SCN-082 (PM1)

Meeting dashboard should show a positive status indicator ("All meetings on track") rather than just absence of warnings.

---

### IMPROVE-9: Per-program staff access summary for PM view

**Scenario:** SCN-042 (PM1)

Add a summary showing which staff have access to the client, so Morgan doesn't wonder why she can't see everything.

---

### IMPROVE-10: Role-specific 403 messaging for front desk

**Scenario:** SCN-085 (R1)

The 403 denial page is generic. Consider role-specific messaging for front desk users explaining what they can do instead.

---

### IMPROVE-11: Language toggle accidental activation risk

**Scenario:** SCN-056 (DS3)

Language toggle is too easily activated by keyboard, causing accidental language switches. Consider a confirmation or different interaction pattern.

---

### IMPROVE-12: Breadcrumb navigation links too small for tablet

**Scenario:** SCN-057 (DS1)

Breadcrumb links are too small for reliable tablet tapping. Increase touch target size.

---

### IMPROVE-13: Add "Preferred Language for Messages" above fold

**Scenario:** SCN-061 (DS3)

Required field "Preferred Language for Messages" is below the fold. Move it to visible area.

---

### IMPROVE-14: Icon-only dismiss buttons need accessible labels

**Scenario:** SCN-063 (DS3)

Dashboard list items have icon-only dismiss buttons with no accessible labels. Add `aria-label` or visible text.

---

### IMPROVE-15: Settings URL navigates to admin settings, not user profile

**Scenario:** SCN-064 (DS3)

Step 3 navigates to admin settings URL instead of user profile settings. Either the scenario URL or the settings navigation needs correction.

---

## TEST Tickets — Test Infrastructure Issues (16)

These are test runner or test data problems, not app bugs. Fix in `konote-app` test infrastructure.

### TEST-1: Client Events tab missing from profile

**Scenario:** SCN-080, Step 1 (DS1)
**Reason:** The visible tabs are Info, Plan, Notes, History, Analysis — no "Events" or "Meetings" tab. Communication logging workflow inaccessible from client record.
**Priority:** Investigate whether Events tab exists elsewhere or needs implementation.

### TEST-2: Meeting create link not on client profile

**Scenario:** SCN-081, Step 1 (DS1)
**Reason:** Meeting scheduling selector did not match any element on client profile. Test runner fell back to My Meetings dashboard (empty).

### TEST-3: SCN-040 note creation form selector mismatch

**Scenario:** SCN-040, Step 3 (DS2)
**Reason:** Quick link selector did not match on French interface.

### TEST-4: SCN-075 dynamic IDs not resolved

**Scenario:** SCN-075, Steps 2, 3, 5 (DS1/PM1/R1)
**Reason:** Template variables `{alert_id}` and `{recommendation_id}` used as literal strings in URLs.

### TEST-5: SCN-076 group_id not resolved

**Scenario:** SCN-076, Steps 4, 5 (PM1/DS1/R1)
**Reason:** `{group_id}` not resolved — milestone and attendance URLs used literal placeholder.

### TEST-6: SCN-046 quick note selector mismatch

**Scenario:** SCN-046, Steps 1–4 (DS1)
**Reason:** `a[href*="quick"]` does not match current UI pattern.

### TEST-7: SCN-048 consent data not seeded

**Scenario:** SCN-048, Steps 2–3 (DS1)
**Reason:** James Thompson missing consent record — "Consent Required" gate correctly blocked note creation but test data should have included consent.

### TEST-8: SCN-049 runner stopped after step 2

**Scenario:** SCN-049, Steps 3–6 (DS1/R1)
**Reason:** Test runner stopped execution after step 2 — steps 3–6 not captured.

### TEST-9: SCN-151 template variables not resolved

**Scenario:** SCN-151, Steps 1–4 (PM1/ADMIN1)
**Reason:** `{used_link_id}`, `{expired_link_id}`, `{revoked_link_id}` used as literal strings.

### TEST-10: SCN-116 conditional logic untestable

**Scenario:** SCN-116 (DS1)
**Reason:** Conditional survey logic cannot be tested until surveys feature is deployed.

### TEST-11: SCN-117 French survey untestable

**Scenario:** SCN-117 (DS2)
**Reason:** French survey completion cannot be tested until surveys feature is deployed. (Positive note: the French 404 page itself is fully translated.)

### TEST-12: SCN-062 network error intercept not firing

**Scenario:** SCN-062, Step 5 (DS3)
**Reason:** Network error simulation did not trigger — cannot test error recovery for screen reader user.

### TEST-13: SCN-063 requires axe/JAWS audit

**Scenario:** SCN-063 (DS3)
**Reason:** Alt text and icon accessibility not verifiable from static screenshots. Needs supplemental tooling.

### TEST-14: SCN-064 requires document.title inspection

**Scenario:** SCN-064 (DS3)
**Reason:** `document.title` changes not visible in screenshots. Needs browser title capture in test runner.

### TEST-15: SCN-065 requires scrolled screenshots

**Scenario:** SCN-065 (DS3)
**Reason:** Focus-not-obscured verification needs screenshots at various scroll positions.

### TEST-16: SCN-082 meeting test data not seeded

**Scenario:** SCN-082, Steps 2–4 (PM1)
**Reason:** No meeting data in test fixtures. Steps 2–4 entirely untestable.

---

## Finding Groups

| Group | Root Cause | Primary Ticket | Also Affects |
|-------|-----------|----------------|-------------|
| FG-S-1 | 404 instead of 403 for restricted pages | BUG-2 | SCN-010/6, SCN-025/3, SCN-042/4, SCN-075/2 |
| FG-S-2 | French/English language mixing | BUG-6 | SCN-026/1, SCN-035/1, SCN-040/1, SCN-047/2 |
| FG-S-3 | Quick note selector mismatch (`a[href*='quick']`) | BUG-4 | SCN-015/2, SCN-046, SCN-048 |
| FG-S-4 | Client Events/Meetings tab missing | TEST-1 | SCN-080, SCN-081 |
| FG-S-5 | Skip link misdirection | BLOCKER-4 | SCN-050/2, SCN-052/1 |
| FG-S-6 | Language toggle in Tab flow | BLOCKER-5 | SCN-050/1, SCN-051/1, SCN-056/3 |
| FG-S-7 | Actions dropdown ARIA pattern broken | BLOCKER-6 | SCN-050/6, SCN-054/2 |
| FG-S-8 | PIPEDA compliance features not implemented | BLOCKER-10 | SCN-070, SCN-151 |
| FG-S-9 | Survey feature not deployed | BUG-30 | SCN-111, SCN-114, SCN-115, SCN-116, SCN-117 |
| FG-S-10 | Funder report feature incomplete | BLOCKER-1 | SCN-035, SCN-086 |
| FG-S-11 | PM self-service paths inconsistent | BUG-13 | SCN-036, SCN-037 |
| FG-S-12 | Test data not seeded | TEST-7 | SCN-046, SCN-048, SCN-082 |
| FG-S-13 | Demo login buttons on shared device | BLOCKER-9 | SCN-049 |
| FG-S-14 | /communications/ namespace retired | BLOCKER-2 | SCN-084 |
| FG-S-15 | Service episode lifecycle not implemented | BLOCKER-3 | SCN-155 |
| FG-S-16 | Login autofocus race condition | BLOCKER-13 | SCN-059 |
| FG-S-17 | Dashboard cognitive load for ADHD users | IMPROVE-16 | SCN-058 |

---

## Items NOT Filed as Tickets

The following were noted but are probable test artifacts, not app bugs:

1. **SCN-117 French 404 page** — The 404 page is fully translated to French with zero English bleed-through. This is a positive finding showing the 404 template handles i18n correctly. Filed as part of FG-S-9 (survey feature not deployed).

2. **SCN-049 demo login buttons** — Filed as BLOCKER-9 but may be intentional in development/staging environments. Needs verification that they don't appear in production.

3. **DITL score stability** — All 5 DITL scores are within 0.1 of Round 6, suggesting the overall app experience is consistent even though individual scenario scores dropped. This supports the "stricter evaluation" interpretation over "app degradation."
