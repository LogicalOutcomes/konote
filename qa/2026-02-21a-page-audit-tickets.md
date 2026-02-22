# KoNote2 Page Audit Tickets — 2026-02-21

**Round:** 3
**Pages audited:** 11
**Report:** `2026-02-21a-page-audit-report.md`

---

## BLOCKER Tickets

### BLOCKER-P-1: Survey management pages not implemented (404 on all 3 URLs)

**Severity:** BLOCKER
**Personas:** PM1 (Morgan Tremblay), admin (Priya Sharma)
**Pages:** survey-list, survey-create, survey-csv-import
**Heuristic:** H01 (First Impression)
**Pass:** heuristic
**Screenshots:** survey-list-PM1-default-1366x768.png, survey-create-PM1-default-1366x768.png, survey-csv-import-PM1-default-1366x768.png, survey-list-admin-default-1366x768.png, survey-create-admin-default-1366x768.png, survey-csv-import-admin-default-1366x768.png

**What's wrong:** All three survey management URLs (`/manage/surveys/`, `/manage/surveys/new/`, `/manage/surveys/import/`) return a 404 "Page Not Found" for both PM1 and admin. The survey management feature, listed in page-inventory v2.1 (2026-02-21), has no working views. Neither persona can list, create, or import surveys.

**Note:** This is likely a premature capture — the page inventory was updated before the feature code was deployed to the test environment. Cross-references FG-S-3 from scenario evaluation (survey feature missing).

**Where to look:** `konote-app/` — check if URL patterns are registered in `urls.py` for the surveys app. If the surveys app exists, the `include()` in root `urls.py` may be missing.

**What "fixed" looks like:** Each URL renders its intended page: survey list with status/actions, survey creation form with bilingual fields, CSV upload interface.

**Acceptance criteria:**
- [ ] `/manage/surveys/` returns 200 and renders survey list for PM1 and admin
- [ ] `/manage/surveys/new/` returns 200 and renders survey creation form
- [ ] `/manage/surveys/import/` returns 200 and renders CSV import interface
- [ ] Navigable from "Manage" dropdown in PM1's nav
- [ ] Re-audit all 3 pages at Green band (4.0+)

**Verification scenarios:** All survey-related scenarios (SCN-111, 114, 115, 116, 117)

**Finding group:** FG-P-7

---

### BLOCKER-P-2: client-surveys page returns 404 for all authorized personas

**Severity:** BLOCKER
**Personas:** DS1, DS2, DS3, DS4, PM1
**Page:** client-surveys (`/surveys/participant/1/`)
**Heuristic:** H01 (First Impression)
**Pass:** heuristic
**Screenshot:** client-surveys-DS1-default-1366x768.png (representative)

**What's wrong:** The URL `/surveys/participant/1/` returns 404 for every authorized persona. Staff cannot view or manage participant survey assignments. Part of the survey feature not being deployed (FG-P-7).

**Where to look:** `konote-app/apps/surveys/urls.py` — check if `/surveys/participant/<int:client_id>/` is registered.

**What "fixed" looks like:** Navigating to `/surveys/participant/1/` shows the participant's survey assignments (pending, completed, dismissed) with actions to assign and enter data.

**Acceptance criteria:**
- [ ] URL resolves for DS1-DS4 and PM1
- [ ] Shows survey assignments for the specified participant
- [ ] Returns 403 (not 404) for unauthorized personas (R1, R2)
- [ ] Re-audit at Green band (4.0+)

**Finding group:** FG-P-7

---

### BLOCKER-P-3: public-survey-link returns raw Django 500 server error

**Severity:** BLOCKER
**Persona:** unauthenticated (general public)
**Page:** public-survey-link (`/s/<token>/`)
**Heuristic:** H01 (First Impression), H03 (Navigation Context), H10 (Aesthetic Coherence)
**Pass:** heuristic
**Screenshots:** public-survey-link-unauthenticated-default-1366x768.png, public-survey-link-unauthenticated-default-375x667.png

**What's wrong:** The public survey link page returns a raw Django 500 error: "A server error occurred. Please contact the administrator." No KoNote branding, no styling, no navigation, no recovery path. Community members clicking a survey link from an email or flyer see this and have no way to complete the survey or understand what went wrong. "Contact the administrator" is meaningless to an unauthenticated community member.

**Where to look:**
1. `konote-app/apps/surveys/views.py` — the view handling `/s/<str:token>/` is raising an unhandled exception. Check Django error logs for the stack trace.
2. `konote-app/templates/500.html` — the 500 error template is either missing or not styled.

**What "fixed" looks like:**
1. The underlying bug causing the 500 is fixed (survey loads successfully)
2. The 500 fallback page is styled with KoNote branding and friendly messaging
3. Invalid/expired tokens show a styled error page (not 500)

**Acceptance criteria:**
- [ ] `/s/<valid_token>/` loads the survey form
- [ ] `/s/<invalid_token>/` shows a styled "link expired or invalid" error page
- [ ] 500 fallback page (if triggered) is styled with branding and recovery guidance
- [ ] Works on mobile (375x667)
- [ ] Re-audit at Green band (4.0+)

**Dimension breakdown (unauthenticated):**

| Dimension | Score |
|-----------|-------|
| Clarity | 1.0 |
| Efficiency | 1.0 |
| Feedback | 1.5 |
| Error Recovery | 1.0 |
| Accessibility | 2.0 |
| Language | 1.5 |
| Confidence | 1.0 |

**Finding group:** FG-P-8

---

### BLOCKER-P-4: public-unsubscribe returns 500 server error (CASL compliance risk)

**Severity:** BLOCKER
**Persona:** unauthenticated (email recipient)
**Page:** public-unsubscribe (`/communications/unsubscribe/<token>/`)
**Heuristic:** H01, H03, H06 (Error Prevention), H10
**Pass:** heuristic
**Screenshots:** public-unsubscribe-unauthenticated-default-1366x768.png, public-unsubscribe-unauthenticated-default-375x667.png

**What's wrong:** The CASL-required email unsubscribe page returns a raw Django 500 error. Under Canada's Anti-Spam Legislation (CASL, S.C. 2010, c. 23, s. 6(2)(c)), every commercial electronic message must include a working unsubscribe mechanism. A non-functional unsubscribe page means the agency is sending emails without providing the legally required opt-out. Recipients remain subscribed against their will. This could lead to CRTC complaints.

**Compliance references:** CASL (S.C. 2010, c. 23, s. 6(2)(c)), PIPEDA

**Where to look:** `konote-app/apps/communications/views.py` — the view handling `/communications/unsubscribe/<str:token>/` is raising an unhandled exception.

**What "fixed" looks like:**
1. Unsubscribe page loads showing: "You are unsubscribing from communications from [agency]. Click 'Unsubscribe' to confirm."
2. After clicking: "You have been unsubscribed."
3. Page is bilingual (EN/FR) and styled
4. Invalid/expired tokens show a styled error (not 500)

**Acceptance criteria:**
- [ ] `/communications/unsubscribe/<valid_token>/` loads the unsubscribe confirmation
- [ ] Clicking "Unsubscribe" withdraws consent and shows confirmation
- [ ] Invalid token shows styled "link expired" (not 500)
- [ ] Page is bilingual (EN/FR)
- [ ] Works on mobile (375x667)
- [ ] CASL: unsubscribe takes effect within 10 business days
- [ ] Re-audit at Green band (4.0+)

**Dimension breakdown (unauthenticated):**

| Dimension | Score |
|-----------|-------|
| Clarity | 1.0 |
| Efficiency | 1.0 |
| Feedback | 1.0 |
| Error Recovery | 1.0 |
| Accessibility | 2.0 |
| Language | 1.5 |
| Confidence | 1.0 |

**Finding group:** FG-P-8

---

### BLOCKER-P-5: 404 page not translated to French (systemic)

**Severity:** BLOCKER (bilingual compliance)
**Persona:** DS2 (Jean-Luc Bergeron), R2-FR (Amelie Tremblay), and any French-preference user
**Affected pages:** Any page that triggers a 404
**Heuristic:** H05 (Terminology — Q4: all translated for FR personas?)
**Pass:** heuristic
**Screenshot:** client-surveys-DS2-default-1366x768.png

**What's wrong:** When a French-preference user hits a 404, the entire page displays in English: "Page Not Found", "The page you're looking for doesn't exist or has been moved", "What you can do", "Check the address for typos", "Go Back", "Home". The navigation bar labels are also in English. This is a bilingual compliance failure.

**Where to look:** `konote-app/templates/404.html` — check if the template uses `{% trans %}` or `{% blocktrans %}`. Check `.po` translation files include 404 page strings.

**What "fixed" looks like:** French-preference users see: "Page non trouvee", "La page que vous recherchez n'existe pas", "Retour", "Accueil".

**Acceptance criteria:**
- [ ] 404 page displays in user's selected language
- [ ] All text translated: heading, body, suggestions, button labels
- [ ] Navigation bar labels in French when preference is French
- [ ] Re-audit DS2 — Language dimension improves to 4.0+

**Finding group:** FG-P-9 (systemic French localization failure — carried from Round 1 BUG-14, matches FG-S-1)

---

### BLOCKER-P-6: comm-leave-message entirely in English for R2-FR

**Severity:** BLOCKER (bilingual compliance)
**Persona:** R2-FR (Amelie Tremblay)
**Page:** comm-leave-message (`/communications/client/1/leave-message/`)
**Heuristic:** H05 (Terminology — Q4, Q5)
**Pass:** heuristic
**Screenshot:** comm-leave-message-R2-FR-default-1366x768.png

**What's wrong:** The entire leave-message form is in English for R2-FR despite her French language preference. Page heading, form labels, buttons, navigation — all English. R2-FR expects and legally requires French-language interfaces (Official Languages Act for federally funded agencies).

**Where to look:** `konote-app/apps/communications/templates/communications/leave_message.html` — check `{% trans %}` tags. Check `.po` files for message form strings.

**What "fixed" looks like:** French-preference users see: "Laisser un message", form labels in French, "Envoyer" button.

**Acceptance criteria:**
- [ ] comm-leave-message page fully translated for FR users
- [ ] All text: heading, labels, buttons, success/error messages in French
- [ ] Re-audit R2-FR — Language dimension improves to 4.0+

**Finding group:** FG-P-9

---

## BUG Tickets

### BUG-P-1: plan-goal-create heading says "Add Target" instead of "Add Goal"

**Severity:** BUG — Priority fix
**Persona:** DS1b (Casey Makwa, first week)
**Page:** plan-goal-create (`/plans/client/1/goals/create/`)
**Heuristic:** H05 (Terminology — Q1)
**Pass:** heuristic
**Screenshot:** plan-goal-create-DS1b-default-1366x768.png

**What's wrong:** The page heading says "Add Target" but the URL says "goals/create", the body asks "What does Jane want to work on?", and the button says "Next: shape this into a goal." Three different framings of the same action. DS1b (first week, no training) does not know what a "target" is and cannot reconcile the competing terminology.

**Where to look:** `konote-app/apps/plans/templates/plans/goal_create.html` — change the h1 heading text.

**What "fixed" looks like:** Consistent terminology throughout: heading "Add a Goal", body "What does [client] want to work on?", button "Save Goal" or "Create Goal".

**Acceptance criteria:**
- [ ] Page heading says "Add a Goal" (or "Add Goal")
- [ ] All references on the page use "goal" consistently (not "target")
- [ ] DS1b re-audit improves from Orange (2.9) to Yellow or Green

**Finding group:** FG-P-11

---

### BUG-P-2: plan-goal-create has no onboarding for first-time users

**Severity:** BUG — Priority fix
**Persona:** DS1b (Casey Makwa, first week)
**Page:** plan-goal-create
**Heuristic:** H05 (Terminology — Q1), H02 (Information Hierarchy)
**Pass:** first_impression
**Screenshot:** plan-goal-create-DS1b-default-1366x768.png

**What's wrong:** A first-time user (DS1b) landing on this page has no context about what a "goal" is in KoNote, how it relates to a service plan, or what the autocomplete/common goal cards mean. There is no intro text, no tooltip, no link to help documentation.

**Where to look:** Add a brief intro paragraph or collapsible help section at the top of the form.

**What "fixed" looks like:** A 1-2 sentence intro: "A goal is something [client name] wants to achieve. Choose a common goal or type your own." Optionally, a "Learn more" link to the help page.

**Acceptance criteria:**
- [ ] New users see brief context text explaining what a goal is
- [ ] Context text does not add visual clutter for experienced users (collapsible or dismissible)
- [ ] DS1b re-audit — Clarity dimension improves to 3.5+

**Finding group:** FG-P-11

---

### BUG-P-3: groups-attendance "--" values are ambiguous and screen-reader-hostile

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara Osei, screen reader)
**Page:** groups-attendance (`/groups/1/attendance/`)
**Heuristic:** H08 (Accessibility — Q1), H05 (Terminology)
**Pass:** heuristic
**Screenshot:** groups-attendance-DS3-populated-1366x768.png

**What's wrong:** Attendance cells use "--" (double dash) for unrecorded values. For DS3 using JAWS, this would be announced as "dash dash" with no context — is this "absent", "not recorded", or "not applicable"? The meaning is ambiguous even for sighted users. Additionally, for funder reporting, "--" may be misinterpreted as missing data vs. intentional non-attendance.

**Where to look:** `konote-app/apps/groups/templates/groups/attendance.html` — replace `--` with descriptive text.

**What "fixed" looks like:** Use "N/R" (Not Recorded) with `aria-label="Not recorded"` or `<abbr title="Not recorded">N/R</abbr>`.

**Acceptance criteria:**
- [ ] Attendance cells use descriptive text instead of "--"
- [ ] Screen reader announces meaningful label (not "dash dash")
- [ ] Legend or key explains what the symbol means
- [ ] Re-audit DS3 — Accessibility dimension improves to 4.0+

---

### BUG-P-4: groups-attendance grammar error "1 sessions"

**Severity:** BUG — Priority fix
**Persona:** All
**Page:** groups-attendance
**Heuristic:** H05 (Terminology — Q3)
**Pass:** heuristic
**Screenshot:** groups-attendance-DS1-populated-1366x768.png

**What's wrong:** The page shows "1 sessions" instead of "1 session". Missing pluralization logic.

**Where to look:** Django template — use `{{ count }} session{{ count|pluralize }}` or `{% blocktrans count counter=sessions_count %}{{ counter }} session{% plural %}{{ counter }} sessions{% endblocktrans %}`.

**Acceptance criteria:**
- [ ] "1 session" (singular) displays correctly
- [ ] "2 sessions" (plural) displays correctly
- [ ] French translation handles pluralization correctly

---

### BUG-P-5: groups-attendance "Rate" column header is ambiguous

**Severity:** BUG — Priority fix
**Persona:** DS1b (new user), PM1 (reporting)
**Page:** groups-attendance
**Heuristic:** H05 (Terminology — Q1), H02 (Information Hierarchy — Q1)
**Pass:** heuristic
**Screenshot:** groups-attendance-PM1-populated-1366x768.png

**What's wrong:** The "Rate" column header is ambiguous — rate of what? Attendance rate? Participation rate? For PM1 preparing funder reports, the metric name must be unambiguous. For DS1b (first week), "Rate" means nothing without context.

**Where to look:** Change column header to "Attendance Rate" or "Attendance %" and add a tooltip explaining the calculation.

**Acceptance criteria:**
- [ ] Column header says "Attendance Rate" (or similar descriptive label)
- [ ] Tooltip or help text explains how the rate is calculated

---

### BUG-P-6: comm-my-messages empty state provides no guidance

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey Makwa)
**Page:** comm-my-messages (`/communications/my-messages/`)
**Heuristic:** H07 (Feedback), H01 (First Impression)
**Pass:** first_impression
**Screenshot:** comm-my-messages-DS1-default-1366x768.png

**What's wrong:** The empty state shows "No unread messages" which is ambiguous — does this mean no messages exist at all, or all messages have been read? There is no guidance about what messages are, who sends them, or what to expect. For DS1 (first time seeing this page), there's no context.

**Where to look:** `konote-app/apps/communications/templates/communications/my_messages.html` — update empty state text.

**What "fixed" looks like:** "No messages yet. Messages from the front desk and colleagues will appear here when they have updates about your participants."

**Acceptance criteria:**
- [ ] Empty state distinguishes between "no messages ever" and "all messages read"
- [ ] Guidance text explains what messages are and who sends them
- [ ] Re-audit DS1 — Feedback dimension improves to 4.0+

---

### BUG-P-7: comm-leave-message has no required-field indicator

**Severity:** BUG — Priority fix
**Persona:** R1 (Dana Petrescu), DS1 (Casey Makwa)
**Page:** comm-leave-message
**Heuristic:** H06 (Error Prevention — Q2)
**Pass:** heuristic
**Screenshot:** comm-leave-message-R1-default-1366x768.png

**What's wrong:** The message textarea has no required-field indicator (asterisk or "(required)"). While the form only has one field (making it somewhat obvious), accessibility standards and consistency with other forms require marking required fields before the user starts filling the form.

**Where to look:** Add `*` or "(required)" label to the textarea field label.

**Acceptance criteria:**
- [ ] Message textarea is visually marked as required
- [ ] `aria-required="true"` is set on the textarea
- [ ] Consistent with required-field marking on other forms in the app

---

### BUG-P-8: comm-my-messages in English for DS2 (French user)

**Severity:** BUG — Priority fix
**Persona:** DS2 (Jean-Luc Bergeron)
**Page:** comm-my-messages
**Heuristic:** H05 (Terminology — Q4, Q5)
**Pass:** heuristic
**Screenshot:** comm-my-messages-DS2-populated-1366x768.png

**What's wrong:** The entire comm-my-messages page is in English for DS2 despite his French language preference. Part of the systemic French localization failure (FG-P-9).

**Where to look:** `konote-app/apps/communications/templates/communications/my_messages.html` — add `{% trans %}` tags. Update `.po` files.

**Acceptance criteria:**
- [ ] Page fully translated for FR users
- [ ] Heading, labels, empty state text, buttons all in French
- [ ] Re-audit DS2 — Language dimension improves to 4.0+

**Finding group:** FG-P-9

---

## IMPROVE Tickets

### IMPROVE-P-1: comm-my-messages empty state should provide guidance

**Severity:** IMPROVE — Review recommended
**Persona:** DS1, PM1
**Page:** comm-my-messages
**Heuristic:** H01 (First Impression)

**Recommendation:** Add contextual guidance to the empty state explaining what messages are and where they come from. Example: "Messages from the front desk and your colleagues will appear here."

---

### IMPROVE-P-2: plan-goal-create needs progress indicator for wizard steps

**Severity:** IMPROVE — Review recommended
**Persona:** DS1c (ADHD), DS1b (new user)
**Page:** plan-goal-create
**Heuristic:** H03 (Navigation Context)

**Recommendation:** Add a step indicator (e.g., "Step 1 of 2") for the multi-step goal creation wizard. DS1c loses track of where she is in multi-step workflows.

---

### IMPROVE-P-3: admin-erasure-requests needs PIPEDA compliance context

**Severity:** IMPROVE — Review recommended
**Persona:** PM1, admin
**Page:** admin-erasure-requests (`/erasure/`)
**Heuristic:** H05 (Terminology)

**Recommendation:** Add a brief explanation of what erasure means in the PIPEDA context: "Under PIPEDA, individuals have the right to request deletion of their personal information. Review and process requests below." Also explain what happens when a request is approved (what data is deleted, what is retained for legal requirements).

---

### IMPROVE-P-4: admin-erasure-requests decorative element may be mistaken for spinner

**Severity:** IMPROVE — Review recommended
**Persona:** admin (Priya Sharma)
**Page:** admin-erasure-requests
**Heuristic:** H07 (Feedback — Q3)

**Recommendation:** The circular decorative element on the empty state could be mistaken for a loading spinner. Replace with a static icon (e.g., checkmark or shield) or remove.

---

## TEST Infrastructure Tickets

### TEST-P-1: groups-attendance needs full data seeding (8+ members, 12+ sessions)

**Type:** Test infrastructure (not an app bug)
**Page:** groups-attendance
**Reason:** All screenshots show 1 member x 1 session. The spec describes an 8x12 matrix (96 cells). The primary evaluation target (table accessibility for DS3, info density for DS1c) cannot be assessed with sparse data.

**Fix in:** konote-app test runner — seed groups with 8+ members and 12+ sessions before capture.
**Priority:** Fix before next round — this page was specifically selected for a11y table evaluation.

---

### TEST-P-2: comm-my-messages "populated" state shows empty inbox

**Type:** Test infrastructure (not an app bug)
**Page:** comm-my-messages
**Reason:** All "populated" state screenshots show "No unread messages" — identical to the "default" state. The test runner failed to seed messages before capturing the populated state.

**Fix in:** konote-app test runner — create 5+ inter-staff messages before capturing the populated state.
**Priority:** Fix before next round.

---

### TEST-P-3: Raw Django 500 error page needs custom styled template

**Type:** Test infrastructure + app configuration
**Pages:** public-survey-link, public-unsubscribe
**Reason:** Both public pages return the default Django production 500 error ("A server error occurred. Please contact the administrator.") instead of a custom styled error page. This suggests `templates/500.html` doesn't exist or is not configured.

**Fix in:** konote-app — create `templates/500.html` with KoNote branding, bilingual text, and recovery links.
**Priority:** Fix before next round — these are public-facing pages.

---

## Finding Groups

| Group | Root Cause | Primary Ticket | Also Affects |
|-------|-----------|---------------|-------------|
| FG-P-7 | Survey feature URLs not registered (404 on `/manage/surveys/*` and `/surveys/participant/*`) | BLOCKER-P-1 | BLOCKER-P-2 — 12 persona x page combinations. Cross-method: FG-S-3 |
| FG-P-8 | Public pages return raw Django 500 (no custom 500 template) | BLOCKER-P-3 | BLOCKER-P-4 — public-survey-link, public-unsubscribe |
| FG-P-9 | French localization failure (systemic, from Round 1 BUG-14) | BLOCKER-P-5 | BLOCKER-P-6, BUG-P-8 — 404 page, comm-leave-message, comm-my-messages. Cross-method: FG-S-1 |
| FG-P-10 | Test data seeding incomplete | TEST-P-1 | TEST-P-2 — groups-attendance, comm-my-messages |
| FG-P-11 | plan-goal-create terminology mismatch ("Target" vs "Goal") | BUG-P-1 | BUG-P-2 |

---

## Items NOT Filed as Tickets

These observations are noted but not ticketed because they are either positive findings, test artifacts, or below the threshold for action:

1. **404 error page is well-designed.** Clear heading, helpful suggestions, proper button hierarchy, responsive on mobile. The 404 page quality is not the issue — the missing pages are.

2. **comm-leave-message is exemplary.** The write-only permission boundary, minimal design, and single-purpose focus should be the model for other forms. No ticket needed — this is the standard to replicate.

3. **DS1c ADHD evaluation on groups-attendance was accidentally positive.** With only 1 member x 1 session, the information density is very low — accidentally ADHD-friendly. This does not reflect real-world use. Re-test with full data.

4. **PM1 denial page on plan-goal-create is well-designed.** Clear explanation of why access is denied and who to contact. Green band (4.1). This is the standard for denial pages.
