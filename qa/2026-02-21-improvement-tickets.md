# KoNote2 Round 7 — Improvement Tickets

**Date:** 2026-02-21
**Evaluator:** Claude (automated, with sub-agent batching)
**Scenarios evaluated:** 42 (7 batches of 6)
**Personas:** DS1, DS1b, DS1c, DS2, DS3, DS4, R1, R2, R2-FR, PM1, E1, E2

---

## Previous Ticket Status

Previous ticket file not available in this worktree. Status review deferred to expert panel (Step 3).

---

## PERMISSION-1: Receptionist can access calendar feed settings page (calendar_feed: deny violated)

**Severity:** BLOCKER (authorization violation)
**Persona:** R1 (Dana Petrescu)
**Scenario:** SCN-085, Step 3

**Violation type:** action_scope

**What's wrong:** Dana (receptionist) has `calendar_feed: false` in her permission scope, but the calendar feed settings page at `/events/calendar/settings/` loaded with HTTP 200 and displayed the full calendar setup UI including a "Set up my calendar link" button. The meetings page at `/events/meetings/` correctly returns 403, but this specific calendar settings route was missed. A receptionist should never see calendar feed configuration.

**Expected behaviour:** Receptionist accessing `/events/calendar/settings/` should receive a styled 403 page explaining the feature is restricted to staff and programme managers.

**Compliance references:** PIPEDA 4.7 (limiting use)

**Where to look:** The Django view for the calendar feed settings page (likely in `events/views.py` or a similar module). Add a permission check matching the one on `/events/meetings/`.

**Acceptance criteria:**
- [ ] Calendar feed settings page returns 403 for receptionist role
- [ ] Permission check added to the calendar feed settings view
- [ ] Re-run SCN-085 step 3 — 403 page is displayed with helpful explanation

**Screenshot reference:** SCN-085_step3_R1_events-calendar-settings.png

---

## BLOCKER-1: PM self-service admin (plan templates, note templates, event types) blocked by admin-only permission gate

**Severity:** BLOCKER
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-036, Steps 1-2
**Screenshot:** SCN-036_step1_PM1_admin-plan-templates.png

**What's wrong:** Morgan has `template.plan.manage: scoped`, `template.note.manage: scoped`, and `event_type.manage: scoped` permissions. However, the `/admin/` path prefix requires full admin privileges, blocking all PM self-service functionality. Plan templates, note templates, and event types are all inaccessible. Programme managers cannot configure their own programme without requesting admin assistance, which defeats the self-service design. The permission model grants scoped access but the URL routing enforces admin-only access.

**Where to look:** Django URL routing for `/admin/` prefix. Either create a separate `/program-admin/` or `/manage/` path with scoped permission checks, or add granular permission checks to the existing `/admin/` views.

**What "fixed" looks like:** PM1 can access plan templates, note templates, and event types for their own programme via a self-service admin hub.

**Acceptance criteria:**
- [ ] PM role can access `/admin/plan-templates/` (or equivalent self-service path) to manage templates scoped to their own programme
- [ ] PM role can access note templates and event types for their programme
- [ ] A self-service admin hub exists with navigation between plan templates, note templates, event types, and metrics
- [ ] Re-run SCN-036 steps 1-2 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-036/1, SCN-036/2, SCN-036/4, SCN-037/1

**Dimension breakdown:**
| Dimension | Score |
|-----------|-------|
| Clarity | 2.5 |
| Efficiency | 1.0 |
| Feedback | 2.0 |
| Error Recovery | 2.0 |
| Accessibility | 3.5 |
| Language | 4.0 |
| Confidence | 1.0 |

---

## BLOCKER-2: PM blocked from user management — user.manage: scoped not implemented

**Severity:** BLOCKER
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-037, Steps 1-4
**Screenshot:** SCN-037_step1_PM1_admin-users.png

**What's wrong:** Programme managers with `user.manage: scoped` cannot access `/admin/users/` at all. The page requires full admin privileges. Morgan cannot create, deactivate, or manage staff accounts in her own programme — she must ask IT for every staff change. This blocks a core PM workflow. The same `/admin/` prefix gate as BLOCKER-1 is the root cause.

**Where to look:** Same as BLOCKER-1 — the `/admin/` URL prefix enforces a blanket admin-only check. Scoped user management views need to be added.

**What "fixed" looks like:** PM can view and manage staff assigned to their programme, create new staff/receptionist accounts, and deactivate (not delete) accounts. Role dropdown restricts elevation (no PM or executive options).

**Acceptance criteria:**
- [ ] PM with `user.manage: scoped` can access a staff management view showing only their programme's team
- [ ] PM can create new staff/receptionist accounts assigned to their programme
- [ ] PM can deactivate (not delete) staff accounts
- [ ] Role dropdown restricts elevation (no PM or executive options)
- [ ] Re-run SCN-037 steps 1-4 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-037/1, SCN-037/2, SCN-037/3, SCN-037/4

**Dimension breakdown:**
| Dimension | Score |
|-----------|-------|
| Clarity | 2.5 |
| Efficiency | 1.0 |
| Feedback | 2.5 |
| Error Recovery | 2.0 |
| Accessibility | 3.0 |
| Language | 1.5 |
| Confidence | 1.0 |

---

## BLOCKER-3: PM blocked from audit log — audit.view: scoped not implemented

**Severity:** BLOCKER
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-037, Steps 5-6
**Screenshot:** SCN-037_step5_PM1_admin-audit-log.png

**What's wrong:** Programme managers with `audit.view: scoped` cannot access `/admin/audit-log/` at all. Morgan cannot perform her quarterly QA review of staff documentation activity without asking IT to pull reports. Same `/admin/` prefix root cause as BLOCKER-1 and BLOCKER-2.

**Where to look:** Same as BLOCKER-1. Add a scoped audit log view filtered to the PM's programme.

**What "fixed" looks like:** PM can access an audit log filtered to their programme, with entries from other programmes hidden. Log uses plain language and is filterable by user, date range, and action type.

**Acceptance criteria:**
- [ ] PM with `audit.view: scoped` can access an audit log filtered to their programme
- [ ] Audit entries from other programmes are not visible
- [ ] Log uses plain language (not database-level detail)
- [ ] Log is filterable by user, date range, and action type
- [ ] Re-run SCN-037 steps 5-6 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-037/5, SCN-037/6

**Dimension breakdown:**
| Dimension | Score |
|-----------|-------|
| Clarity | 2.5 |
| Efficiency | 1.0 |
| Feedback | 2.5 |
| Error Recovery | 1.5 |
| Accessibility | 3.0 |
| Language | 1.5 |
| Confidence | 1.0 |

---

## BLOCKER-4: Surveys feature does not exist — 5 scenarios score Red

**Severity:** BLOCKER (expected — feature not yet built)
**Persona:** DS1 (Casey Makwa), PM1 (Morgan Tremblay), DS2 (Jean-Luc Bergeron)
**Scenarios:** SCN-111, SCN-114, SCN-115, SCN-116, SCN-117
**Screenshot:** SCN-111_step1_DS1_participants.png

**What's wrong:** The `/surveys/` route returns 404 for all roles. There is no survey assignment mechanism on participant profiles and no "Surveys" link in the navigation. The entire surveys module has not been implemented. Five scenarios (SCN-111 through SCN-117) all score Red (1.5 average) because the feature simply does not exist. This is expected — the feature has not been built yet.

**Where to look:** No existing code to fix. This is a new feature that needs to be built.

**What "fixed" looks like:** A surveys module exists with routes for assignment (staff), results viewing (PM), editing (staff), conditional logic (staff), and bilingual support (DS2).

**Acceptance criteria:**
- [ ] `/surveys/` route exists and is accessible
- [ ] Staff can assign surveys to participants from the participant profile
- [ ] PM can view aggregate survey results
- [ ] Survey form supports conditional/skip logic
- [ ] French translation of survey interface works correctly
- [ ] Re-run SCN-111, SCN-114, SCN-115, SCN-116, SCN-117 — scores improve to Green band (4.0+)

**Note:** These 5 scenarios should be excluded from satisfaction scoring until the feature is built, to avoid inflating the failure count with a single missing feature.

**Verification scenarios:** SCN-111/1, SCN-114/1, SCN-115/1, SCN-116/1, SCN-117/1

---

## BLOCKER-5: Keyboard-only full workflow fails for screen reader user

**Severity:** BLOCKER
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-050, Steps 3-7
**Screenshot:** SCN-050_step3_DS3_participants-create.png

**What's wrong:** The full keyboard-only intake workflow fails catastrophically for a screen reader user. Tab sequence does not allow filling form fields before reaching the submit button. Arrow keys open the Actions menu rather than navigating between ARIA tabs on the client profile. The note creation step lands on an Event form instead of a Note form. Amara cannot complete the core intake-to-note workflow by keyboard alone.

**Where to look:** Create-participant form tab order, client profile tab bar ARIA implementation, and Actions dropdown keyboard interaction.

**What "fixed" looks like:** Tab order through the create-participant form allows filling all required fields before reaching submit. Profile tabs implement the ARIA tablist pattern with arrow key navigation. Quick Note is reachable by keyboard without landing on the wrong action.

**Acceptance criteria:**
- [ ] Tab order through create-participant form allows filling all required fields before reaching submit button
- [ ] Profile tabs implement ARIA tablist pattern with arrow key navigation between tabs
- [ ] Quick Note is reachable by keyboard from the client profile without landing on wrong action
- [ ] Re-run SCN-050 all steps — score improves to Green band (4.0+)

**Verification scenarios:** SCN-050/3, SCN-050/5, SCN-050/6, SCN-054/2

**Dimension breakdown:**
| Dimension | Score |
|-----------|-------|
| Clarity | 2.5 |
| Efficiency | 1.5 |
| Feedback | 2.0 |
| Error Recovery | 2.0 |
| Accessibility | 2.5 |
| Language | 4.0 |
| Confidence | 1.5 |

---

## BLOCKER-6: PIPEDA data export function not available on client profile

**Severity:** BLOCKER
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-070, Steps 2-3
**Screenshot:** SCN-070_step2_PM1_participants-7.png

**What's wrong:** There is no accessible data export function on the client profile page. The "Privacy & Data Management" collapsible section exists but does not contain a working export action. Morgan cannot fulfil a PIPEDA Section 8 access request (client's right to see their data) through the application. She would need to ask IT or a developer to pull the data manually.

**Where to look:** The client profile template (likely `participants/detail.html` or similar) and the "Privacy & Data Management" section. An export view needs to be created.

**What "fixed" looks like:** A clearly labelled "Export Data" or "Privacy Request" action is available on the client profile. The export produces a readable file (PDF or structured document) containing all data categories. Morgan can initiate and complete the export without IT involvement.

**Acceptance criteria:**
- [ ] A clearly labelled export action is available on the client profile (within "Privacy & Data Management" or "Actions" dropdown)
- [ ] The export produces a readable file containing all data categories
- [ ] Morgan can initiate and complete the export without IT involvement
- [ ] Re-run SCN-070 step 2 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-070/2, SCN-070/3

---

## BLOCKER-7: No consent withdrawal or data deletion workflow available

**Severity:** BLOCKER
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-070, Step 4
**Screenshot:** SCN-070_step4_PM1_participants-7.png

**What's wrong:** There is no consent withdrawal or data deletion workflow on the client profile. When a client withdraws consent under PIPEDA, the programme manager has no way to process this through KoNote. PIPEDA requires organisations to delete personal information upon withdrawal of consent, and the PM needs a self-service workflow to do so.

**Where to look:** The client profile "Privacy & Data Management" section. A consent withdrawal wizard/form needs to be created.

**What "fixed" looks like:** A consent withdrawal form or wizard is accessible from the client profile. The form explains what will be deleted vs. retained (with funder retention reasons). The workflow is completable by a programme manager without IT involvement.

**Acceptance criteria:**
- [ ] A consent withdrawal form or wizard is accessible from the client profile
- [ ] The form explains what will be deleted vs. retained (with reasons)
- [ ] Funder retention requirements are clearly stated
- [ ] The workflow is completable by a programme manager without IT involvement
- [ ] Re-run SCN-070 step 4 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-070/4, SCN-070/5

---

## BUG-1: Language preference does not persist across page navigation (cross-cutting)

**Severity:** BUG — Priority fix
**Persona:** All personas affected
**Primary scenario:** SCN-010, Step 3 (R1 sees French on create form)
**Screenshot:** SCN-010_step3_R1_participants-create.png

**What's wrong:** This is the most pervasive issue in Round 7. The user's language preference does not persist reliably across page navigation. English-speaking users see French interfaces, and French-speaking users see English interfaces, often mid-workflow without any user action. The issue manifests in three ways:

1. **Language resets on navigation:** English users navigate to a new page and it loads in French (SCN-010/3, SCN-015/2, SCN-040/2, SCN-045/1, SCN-047/1-4, SCN-076/1-2)
2. **Language resets after form submission:** The language reverts after a POST request (SCN-020/3, SCN-035/3, SCN-083/2, SCN-117/2)
3. **Mixed languages on one page:** Error messages display in English while page chrome is French (SCN-025/4, SCN-037/2-6, SCN-086/2-5)

**Affected scenarios (22):** SCN-010, SCN-015, SCN-020, SCN-025, SCN-035, SCN-036, SCN-037, SCN-040, SCN-045, SCN-046, SCN-047, SCN-056, SCN-058, SCN-075, SCN-076, SCN-080, SCN-081, SCN-083, SCN-086, SCN-117

**Where to look:** Django i18n middleware. Verify that the language preference is stored in the user profile (not just a session cookie) and that the middleware reads this preference on every request. Check that POST requests preserve the language setting. Check that error templates and banner text are included in the translation catalogue.

**What "fixed" looks like:** Once a user's language preference is set, every page — including error pages, form submissions, and redirects — displays in that language. No manual toggling required.

**Acceptance criteria:**
- [ ] User's language preference persists across all page navigations
- [ ] Language does not reset after form submissions (POST requests)
- [ ] Error messages, banner text, and help text are all in the selected language
- [ ] No English strings appear on a French-mode page (and vice versa)
- [ ] Re-run SCN-010 step 3, SCN-040 step 2, SCN-117 step 2 — Language dimension scores 4.0+

**Verification scenarios:** SCN-010/3, SCN-015/2, SCN-020/3, SCN-040/2, SCN-047/1, SCN-080/2, SCN-117/2

**Dimension breakdown (SCN-010/3 as primary):**
| Dimension | Score |
|-----------|-------|
| Clarity | 3.5 |
| Efficiency | 3.0 |
| Feedback | 3.0 |
| Error Recovery | 3.0 |
| Accessibility | 3.0 |
| Language | 1.0 |
| Confidence | 3.0 |

---

## BUG-2: Notes URL returns 404 instead of styled 403 for receptionist

**Severity:** BUG — Priority fix
**Persona:** R1 (Dana Petrescu)
**Scenario:** SCN-010, Step 6
**Screenshot:** SCN-010_step6_R1_participants-1-notes.png

**What's wrong:** When a receptionist navigates to a client's notes URL, the system returns a 404 "Page non trouvee" instead of a proper 403 permission-denied page. The message "The page you are looking for does not exist or has been moved" is misleading — the page exists but is restricted. Dana does not understand WHY she cannot see notes or what she should do instead.

**Where to look:** The notes view URL routing. The view likely does not check permissions before returning — it falls through to a 404 when the receptionist's filtered queryset returns empty.

**What "fixed" looks like:** Receptionist accessing `/participants/{id}/notes/` sees a styled 403 page explaining that notes are restricted to staff and managers.

**Acceptance criteria:**
- [ ] Receptionist accessing `/participants/{id}/notes/` sees a styled 403 page
- [ ] The 403 page explains notes are restricted to staff and managers
- [ ] Re-run SCN-010 step 6 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-010/6, SCN-025/3

---

## BUG-3: 403 page shows mixed English/French and misleading denial reason

**Severity:** BUG — Priority fix
**Persona:** R2 (Omar Hussain)
**Scenario:** SCN-025, Step 4
**Screenshot:** SCN-025_step4_R2_participants-1.png

**What's wrong:** The access-denied page mixes languages: heading and suggestions in French, but the error banner text in English ("Access denied. You are not assigned to this client's program."). Additionally, the denial reason is misleading — it says "not assigned to this client's program" when the actual restriction is role-based (receptionist role does not have `note.view` permission). Omar would try to get himself reassigned to the programme, which is not the solution.

**Where to look:** The 403 template and the permission denial view. The error message needs to be (a) translated and (b) role-aware.

**What "fixed" looks like:** 403 page displays entirely in the user's language preference. Error message accurately describes the role-based restriction.

**Acceptance criteria:**
- [ ] 403 page displays entirely in the user's language preference
- [ ] Error message accurately describes role-based restrictions, not just programme assignment
- [ ] Re-run SCN-025 step 4 — language is consistent and reason is accurate

**Verification scenarios:** SCN-025/4, SCN-010/6, SCN-076/3

---

## BUG-4: Phone number update shows no confirmation and old value persists

**Severity:** BUG — Priority fix
**Persona:** R1 (Dana Petrescu)
**Scenario:** SCN-020, Step 3
**Screenshot:** SCN-020_step3_R1_participants-21.png

**What's wrong:** After attempting to update a phone number, the profile still shows the old number (555-1234). No save confirmation message is visible. Additionally, the page switched to French after the edit action (related to BUG-1). Dana has no way to know if her change was saved.

**Where to look:** The participant edit form view and its redirect/response after save. Ensure a success message is set in the Django messages framework and the updated value is displayed.

**What "fixed" looks like:** After saving a phone number update, a visible confirmation message appears and the updated value is immediately displayed.

**Acceptance criteria:**
- [ ] After saving a phone number update, a visible confirmation message appears (e.g., "Phone number updated")
- [ ] Updated value is immediately displayed on the profile
- [ ] Language stays in the user's preferred language after form submission
- [ ] Re-run SCN-020 step 3 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-020/3, SCN-047/5

**Dimension breakdown:**
| Dimension | Score |
|-----------|-------|
| Clarity | 4.0 |
| Efficiency | 3.5 |
| Feedback | 3.0 |
| Error Recovery | 3.5 |
| Accessibility | 3.5 |
| Language | 1.5 |
| Confidence | 3.5 |

---

## BUG-5: Client search returns no results for existing client in assigned programme

**Severity:** BUG — Priority fix
**Persona:** R2 (Omar Hussain)
**Scenario:** SCN-025, Step 1
**Screenshot:** SCN-025_step1_R2_participants.png

**What's wrong:** Omar (R2, frontdesk2, Youth Services programme) searched for "Priya" but received no results. The scenario prerequisite specifies Priya Patel should be an active client in Youth Services. Either test data setup failed or there is a programme scoping bug preventing receptionists from seeing clients in their assigned programme. The entire scenario was blocked because the client could not be found.

**Where to look:** The participant search view and its programme scoping filter. Also verify test data seeding.

**What "fixed" looks like:** Receptionist assigned to a programme can find active clients in that programme via search.

**Acceptance criteria:**
- [ ] Receptionist assigned to a programme can find active clients in that programme via search
- [ ] Re-run SCN-025 step 1 — client appears in search results

**Verification scenarios:** SCN-025/1, SCN-025/2

**Dimension breakdown:**
| Dimension | Score |
|-----------|-------|
| Clarity | 3.5 |
| Efficiency | 2.5 |
| Feedback | 3.0 |
| Error Recovery | 3.0 |
| Accessibility | 3.0 |
| Language | 2.5 |
| Confidence | 2.0 |

---

## BUG-6: French receptionist landing page missing "+ New Participant" button

**Severity:** BUG — Priority fix
**Persona:** R2-FR (Amelie Tremblay)
**Scenario:** SCN-026, Step 1
**Screenshot:** SCN-026_step1_R2-FR_home.png

**What's wrong:** The French receptionist landing page shows "Voir tout" and "Filtres de recherche" but does NOT show the "+ Nouveau/Nouvelle Participant(e)" button that appears prominently on the staff landing page (e.g., SCN-005). The receptionist role has `client.create: allow` permission, so a create button should be visible. Its absence means Amelie cannot start intake without finding the URL manually.

**Where to look:** The landing page template. Check whether the create button is conditionally rendered based on role and whether the receptionist condition is missing.

**What "fixed" looks like:** French receptionist landing page shows "+ Nouveau/Nouvelle Participant(e)" button when the user has `client.create` permission.

**Acceptance criteria:**
- [ ] French receptionist landing page shows "+ Nouveau/Nouvelle Participant(e)" button when the user has `client.create` permission
- [ ] Button label is fully in French
- [ ] Re-run SCN-026 step 1 — create button is visible

**Verification scenarios:** SCN-026/1, SCN-026/2

---

## BUG-7: Communication quick-log workflow unreachable — client record lacks Events/Meetings tab

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-080, Step 1; SCN-081, Step 1
**Screenshot:** SCN-080_step1_DS1_events-meetings.png

**What's wrong:** The client record page shows tabs for Info, Plan, Notes, History, and Analysis, but no Events or Meetings tab. There is no visible link to log a communication or schedule a meeting from the client context. Communication logging and meeting scheduling are only accessible from the top-level Meetings nav, which is disconnected from the client. Casey cannot log a phone call in under 30 seconds as required.

**Where to look:** The client profile template tab configuration. An Events or Communications tab needs to be added to the client record.

**What "fixed" looks like:** Client record has a visible way to log communications (quick-log buttons for phone/text/email) and create meetings for that client, with the client name pre-filled.

**Acceptance criteria:**
- [ ] Client record page has a visible way to log communications (e.g., Events tab or Actions dropdown)
- [ ] Meeting creation from client context pre-fills the client name
- [ ] Quick-log communication can be completed in under 30 seconds
- [ ] Re-run SCN-080 step 1, SCN-081 step 1 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-080/1, SCN-081/1

---

## BUG-8: Calendar feed URL generation does not advance past setup page

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-083, Step 2
**Screenshot:** SCN-083_step2_DS1_events-calendar-settings.png

**What's wrong:** Clicking the "Set up my calendar link" button does not produce a feed URL. Steps 2-4 all show the same pre-setup page with no feed URL, no copy button, no instructions, and no regeneration option. The calendar feed generation may have failed silently.

**Where to look:** The calendar feed settings view and the POST handler for feed generation.

**What "fixed" looks like:** Clicking "Set up my calendar link" generates a feed URL and displays it with a Copy button. Subscription instructions for Google Calendar, Outlook, and Apple Calendar are shown.

**Acceptance criteria:**
- [ ] Clicking "Set up my calendar link" generates a feed URL and displays it
- [ ] Copy button is available for the generated URL
- [ ] Subscription instructions are shown for Google Calendar, Outlook, and Apple Calendar
- [ ] A regenerate token option is available after initial generation
- [ ] Re-run SCN-083 step 2 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-083/2, SCN-083/3, SCN-083/4

---

## BUG-9: No export functionality on executive dashboard

**Severity:** BUG — Priority fix
**Persona:** E2 (Kwame Asante)
**Scenario:** SCN-030, Step 3
**Screenshot:** SCN-030_step3_E2_participants-executive.png

**What's wrong:** The executive dashboard has no visible export button (PDF, CSV, or any format). Kwame needs to produce a board package with programme data. The "Need More Details?" section says to contact the Programme Manager, which defeats the purpose of having an executive dashboard. Kwame would have to screenshot and paste manually.

**Where to look:** The executive dashboard template. Add an export button with PDF and/or CSV options.

**What "fixed" looks like:** Executive dashboard has a visible Export button offering PDF and/or CSV. Export includes the dashboard summary data with date and programme context.

**Acceptance criteria:**
- [ ] Executive dashboard has a visible Export button offering PDF and/or CSV
- [ ] Export includes the dashboard summary data with date and programme context
- [ ] Re-run SCN-030 step 3 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-030/3, SCN-030/4

---

## BUG-10: No date range filter on executive dashboard — cannot isolate quarterly data

**Severity:** BUG — Priority fix
**Persona:** E2 (Kwame Asante)
**Scenario:** SCN-030, Step 4
**Screenshot:** SCN-030_step4_E2_participants-executive.png

**What's wrong:** The executive dashboard only has a "Filter by Program" dropdown. There is no date range selector, no presets (This month, Last quarter, Year to date), and no way to compare periods. Board prep requires quarterly data isolation. Kwame, who benchmarks against Power BI, would find this dashboard static and inflexible.

**Where to look:** The executive dashboard template and view. Add date range filtering with presets.

**What "fixed" looks like:** Date range filter with presets (This month, Last quarter, Year to date, Custom) is available. Active filter is clearly indicated.

**Acceptance criteria:**
- [ ] Date range filter with presets (This month, Last quarter, Year to date, Custom) is available
- [ ] Active filter is clearly indicated on the dashboard
- [ ] Re-run SCN-030 step 4 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-030/4

---

## BUG-11: Self-service admin navigation pages return 404 — note templates and event types paths do not exist

**Severity:** BUG — Priority fix
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-036, Step 4
**Screenshot:** SCN-036_step4_PM1_settings-programs-youth-services.png

**What's wrong:** The self-service admin pages for note templates and event types either do not exist at the expected URLs or have not been implemented yet. Even if the 403 at `/admin/` were resolved (BLOCKER-1), PM cannot navigate between self-service configuration pages.

**Where to look:** URL routing for programme configuration pages. These pages need to be created.

**What "fixed" looks like:** Note templates and event types pages exist at consistent URLs and are accessible to the PM role, with navigation links between all self-service admin pages.

**Acceptance criteria:**
- [ ] Note templates page exists and is accessible to PM role
- [ ] Event types page exists and is accessible to PM role
- [ ] Navigation links between all self-service admin pages are present
- [ ] Re-run SCN-036 step 4 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-036/4

---

## BUG-12: No funder profile selection on funder report page

**Severity:** BUG — Priority fix
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-086, Steps 1-2
**Screenshot:** SCN-086_step1_PM1_reports-funder-report.png

**What's wrong:** The funder report page shows a generic "Program Outcome Report Template" with programme and fiscal year selectors but no funder profile dropdown. Morgan cannot select a funder profile to apply custom age bins or reporting requirements. The page title warns it is a "Draft Template" which further reduces confidence.

**Where to look:** The funder report template and view. A funder profile selector needs to be added.

**What "fixed" looks like:** Funder profile dropdown is available on the report form. Selecting a profile changes visible report configuration (e.g., age bins). Morgan can verify which funder requirements will be applied before generating.

**Acceptance criteria:**
- [ ] Funder profile dropdown is available on the report form
- [ ] Selecting a funder profile changes visible report configuration
- [ ] Morgan can verify which funder requirements will be applied before generating
- [ ] Re-run SCN-086 step 1 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-086/1, SCN-086/2

---

## BUG-13: Accented characters may be stripped from saved participant names

**Severity:** BUG — Priority fix
**Persona:** DS2 (Jean-Luc Bergeron)
**Scenario:** SCN-040, Step 4
**Screenshot:** SCN-040_step4_DS2_participants.png

**What's wrong:** The search results show "Benoit Tremblay" without the accent on the i (should be Benoit with circumflex). The accent appears to have been stripped during save. Note: the surname also differs from the expected "Levesque" — this may partially be a test data issue. Needs manual verification.

**Where to look:** The participant model's name fields and the database collation settings. Verify that Unicode characters are preserved through create, save, and display.

**What "fixed" looks like:** Accented characters are preserved through the full lifecycle (create, save, search, display).

**Acceptance criteria:**
- [ ] Accented characters (e with accent, i with circumflex, etc.) are preserved through create, save, and display
- [ ] Search results display names with correct accents
- [ ] Searching with accented characters finds matching records
- [ ] Re-run SCN-040 step 4 — accents preserved in search results

**Verification scenarios:** SCN-040/4

---

## BUG-14: Profile tabs lack ARIA tablist pattern — arrow keys do not navigate between tabs

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-054, Step 2; SCN-050, Step 5
**Screenshot:** SCN-054_step2_DS3_participants-21.png

**What's wrong:** The client profile tabs (Info, Plan, Notes, History, Analysis) do not implement the ARIA tablist/tab/tabpanel pattern. When Amara presses arrow keys expecting to move between tabs (standard WCAG pattern), the Actions dropdown menu opens instead. JAWS would not announce these as tabs or indicate which is selected. This is the root cause behind BLOCKER-5's tab navigation failure.

**Where to look:** The client profile template's tab bar HTML. Needs `role="tablist"`, `role="tab"`, `aria-selected`, and `role="tabpanel"` attributes added, plus arrow key JavaScript handlers.

**What "fixed" looks like:** Profile tab bar uses `role="tablist"` with `role="tab"` on each tab. Arrow keys navigate between tabs. Tab panel content has `role="tabpanel"` with `aria-labelledby`.

**Acceptance criteria:**
- [ ] Profile tab bar uses `role="tablist"` with `role="tab"` on each tab
- [ ] Active tab has `aria-selected="true"`
- [ ] Arrow keys navigate between tabs within the tablist
- [ ] Tab panel content has `role="tabpanel"` with `aria-labelledby` pointing to its tab
- [ ] HTMX content swap is announced via aria-live region
- [ ] Re-run SCN-054 step 2 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-054/2, SCN-050/5

---

## BUG-15: No skip-to-content link on participant list page

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-052, Step 1
**Screenshot:** SCN-052_step1_DS3_participants-create.png

**What's wrong:** When Amara presses Tab on the participant list page, no skip-to-content link appears. Instead, the first Tab lands on a navigation or action element (likely "+ New Participant" button), and pressing Enter navigates away from the list entirely. WCAG 2.4.1 requires a mechanism to bypass blocks of repeated content. Without a skip link, Amara must Tab through the entire navigation bar on every page load.

**Where to look:** The base template. A "Skip to main content" link needs to be added before the navigation bar.

**What "fixed" looks like:** A "Skip to main content" link appears on first Tab press on every page. It is visually hidden until focused, then becomes visible. Activating it moves focus into the `<main>` landmark.

**Acceptance criteria:**
- [ ] A "Skip to main content" link appears on first Tab press on every page
- [ ] The skip link is visually hidden until focused, then becomes visible
- [ ] Activating the skip link moves focus into the `<main>` landmark
- [ ] Re-run SCN-052 step 1 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-052/1, SCN-050/2

---

## BUG-16: Form validation errors use browser-native tooltip instead of ARIA live announcement

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-061, Step 1
**Screenshot:** SCN-061_step1_DS3_participants-create.png

**What's wrong:** When the create-participant form is submitted with a missing required field, the error is displayed as a browser-native "Please fill out this field" tooltip, not a custom error message announced via `aria-live` or `role="alert"`. JAWS support for native validation tooltips varies. The error message is generic rather than identifying which field is required. Focus does correctly move to the error field, which is positive.

**Where to look:** The create-participant form template. Replace browser-native validation with custom validation that uses `aria-live="assertive"` or `role="alert"`.

**What "fixed" looks like:** Form validation errors are announced via `aria-live="assertive"`. Error messages identify the specific field (e.g., "First Name is required"). Errors are associated with fields via `aria-describedby`.

**Acceptance criteria:**
- [ ] Form validation errors are announced via `aria-live="assertive"` or `role="alert"`
- [ ] Error message identifies the specific field (e.g., "First Name is required")
- [ ] Error is associated with the field via `aria-describedby` or `aria-errormessage`
- [ ] Re-run SCN-061 step 1 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-061/1, SCN-050/3

---

## BUG-17: Blank white page when connection drops during navigation

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-048, Step 3
**Screenshot:** SCN-048_step3_DS1.png

**What's wrong:** When the network connection drops mid-workflow, the main page renders as completely blank white with no content, no error message, and no indication of what happened. The browser's own offline page appears on an alternate capture but KoNote itself provides no graceful degradation. Casey, with medium-low tech comfort, would think she broke something and close the tab.

**Where to look:** Service worker configuration or offline fallback page. KoNote needs its own offline error page that preserves in-progress form data.

**What "fixed" looks like:** KoNote displays its own offline error page (not a blank white screen) when the connection drops. The offline page preserves any in-progress form data. A "Try again" button is available.

**Acceptance criteria:**
- [ ] KoNote displays its own offline error page when the connection drops
- [ ] The offline page preserves any in-progress form data in the DOM or local storage
- [ ] A "Try again" button is available within the KoNote interface
- [ ] Re-run SCN-048 step 3 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-048/3, SCN-048/4

---

## BUG-18: Dashboard information density overwhelms ADHD users

**Severity:** BUG — Priority fix
**Persona:** DS1c (Casey Makwa, ADHD)
**Scenario:** SCN-058, Step 1
**Screenshot:** SCN-058_step1_DS1c_home.png

**What's wrong:** Dashboard displays 8+ distinct information blocks simultaneously: 5 stat cards, Priority Items list with 11 entries, Recently Viewed panel, search box, and 2 action buttons. For Casey with ADHD-inattentive type, this exceeds the 5-6 distinct blocks threshold and creates cognitive overload. All stat cards have equal visual weight, making it impossible to identify the most important next action within 5 seconds.

**Where to look:** The dashboard template. Reduce competing calls to action above the fold. Give primary information (alerts, overdue items) clearly larger visual weight than secondary stats.

**What "fixed" looks like:** Dashboard shows no more than 3 competing calls to action above the fold. Primary information has clearly larger visual weight than secondary stats.

**Acceptance criteria:**
- [ ] Dashboard shows no more than 3 competing calls to action above the fold
- [ ] Primary information (alerts, overdue items) has clearly larger visual weight than secondary stats
- [ ] Re-run SCN-058 step 1 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-058/1, SCN-005/2

---

## BUG-19: No persistent notification system — notifications are inline Django messages only

**Severity:** BUG — Priority fix
**Persona:** DS1c (Casey Makwa, ADHD)
**Scenario:** SCN-058, Step 2
**Screenshot:** SCN-058_step2_DS1c_home.png

**What's wrong:** There is no notification panel, bell icon, or inbox for reviewing accumulated notifications. The only notification mechanism visible is inline Django messages that appear once on page load and cannot be reviewed later. For Casey with ADHD, toast/flash messages that disappear are a known frustration — she needs persistent, reviewable notifications she can check when ready.

**Where to look:** The base template and notification system architecture. A persistent notification panel or inbox needs to be created.

**What "fixed" looks like:** Notifications are persistent and reviewable in a panel or inbox. Each notification has a clear urgency level distinction.

**Acceptance criteria:**
- [ ] Notifications are persistent and reviewable in a panel or inbox, not just toast/flash messages
- [ ] Each notification has a clear urgency level distinction
- [ ] Re-run SCN-058 step 2 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-058/2

---

## BUG-20: Console shows htmx:syntax:error messages on create-participant page

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-061, Step 1
**Screenshot:** SCN-061_step1_DS3_participants-create.png

**What's wrong:** The browser console shows 10 `htmx:syntax:error` messages on the create-participant page. While not directly visible to users, these indicate broken HTMX attributes that could affect dynamic form behaviour, aria-live announcements, and screen reader interaction. For Amara using JAWS, broken HTMX can mean silent failures where expected announcements never fire.

**Where to look:** The create-participant form template. Audit all `hx-*` attributes for syntax errors.

**What "fixed" looks like:** Zero `htmx:syntax:error` messages on the create-participant page. All HTMX attributes use valid syntax.

**Acceptance criteria:**
- [ ] Zero htmx:syntax:error messages on the create-participant page
- [ ] All HTMX attributes use valid syntax
- [ ] Re-run SCN-061 — console is clean

**Verification scenarios:** SCN-061/1, SCN-053/2

---

## BUG-21: Form data may not be preserved after validation error

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-045, Step 2
**Screenshot:** SCN-045_step2_DS1_participants-create.png

**What's wrong:** After submitting with a missing first name (step 1), step 2 shows a blank form. The previously-entered last name ("Santos") does not appear to be preserved. The scenario requires data preservation on validation error. However, this may be a test runner artefact — the screenshot may show the state after successfully correcting and resubmitting. Confidence is Medium.

**Where to look:** The create-participant form view's POST handler. Ensure the form is re-rendered with submitted data when validation fails.

**What "fixed" looks like:** Previously entered form data is preserved on validation failure. Error message appears next to the missing field.

**Acceptance criteria:**
- [ ] Previously entered form data is preserved on validation failure
- [ ] Error message appears next to the missing field
- [ ] Re-run SCN-045 steps 1-2 with manual verification of data preservation

**Verification scenarios:** SCN-045/1, SCN-045/2

---

## BUG-22: Group creation form defaults to "Aucun programme" instead of pre-selecting user's programme

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-076, Step 2
**Screenshot:** SCN-076_step2_DS1_groups-create.png

**What's wrong:** Staff users who only have access to one programme should see that programme pre-selected on the group creation form. Instead, the dropdown shows "Aucun programme" (No programme), requiring an extra click. For Casey with medium-low tech comfort, this introduces unnecessary confusion about whether she's creating the group in the right programme.

**Where to look:** The group creation form view. When the user has access to exactly one programme, pre-select it.

**What "fixed" looks like:** Programme dropdown is pre-selected to the user's only programme when they have access to exactly one.

**Acceptance criteria:**
- [ ] Programme dropdown is pre-selected to the user's only programme when they have access to exactly one
- [ ] Re-run SCN-076 step 2 — Efficiency dimension improves to 4.0+

**Verification scenarios:** SCN-076/2

---

## BUG-23: Settings page returns 404 for staff role at /settings/

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-064, Step 3
**Screenshot:** SCN-064_step3_DS3_settings.png

**What's wrong:** Navigating to `/settings/` as a staff user returns a 404 "Page Not Found" error. The persona's permission scope indicates `settings: true` (own profile only), so this page should be accessible. Either the URL is wrong (settings may be at a different path like `/accounts/settings/` or `/profile/`) or the route is not configured.

**Where to look:** URL routing for user settings/profile page. Either fix the route or update the scenario YAML.

**What "fixed" looks like:** Settings page is accessible at a documented URL for staff role.

**Acceptance criteria:**
- [ ] Settings page is accessible at a documented URL for staff role
- [ ] Scenario YAML updated with correct settings URL
- [ ] Re-run SCN-064 step 3 to verify settings page title

**Verification scenarios:** SCN-064/3

---

## Finding Groups

| Group | Root Cause | Primary Ticket | Also Affects |
|-------|-----------|---------------|-------------|
| FG-S-1 | Language preference not persisted across page navigation | BUG-1 | SCN-010/3, SCN-015/2, SCN-020/3, SCN-025/4, SCN-035/3, SCN-037/2, SCN-040/2, SCN-045/1, SCN-046/3, SCN-047/1-4, SCN-056/2-4, SCN-058/6, SCN-075/1, SCN-076/1-2, SCN-080/2-4, SCN-081/2-3, SCN-083/2-4, SCN-086/2-5, SCN-117/2 |
| FG-S-2 | /admin/ URL prefix blocks PM scoped permissions | BLOCKER-1 | SCN-036/1-2, SCN-036/4, SCN-037/1-6 (also BLOCKER-2, BLOCKER-3, BUG-11) |
| FG-S-3 | Client record lacks Events/Meetings integration | BUG-7 | SCN-080/1, SCN-081/1 |
| FG-S-4 | Permission denial pages use misleading reasons | BUG-3 | SCN-010/6, SCN-025/3-4, SCN-076/3, SCN-076/6, SCN-085/1-2 |
| FG-S-5 | Surveys module not implemented | BLOCKER-4 | SCN-111/1-2, SCN-114/1-2, SCN-115/1-2, SCN-116/1-2, SCN-117/1-2 |
| FG-S-6 | PIPEDA privacy workflows not implemented | BLOCKER-6 | SCN-070/2-4 (also BLOCKER-7) |
| FG-S-7 | Missing ARIA tab pattern on client profile | BUG-14 | SCN-050/5, SCN-054/2 (also BLOCKER-5) |
| FG-S-8 | Missing skip-to-content link | BUG-15 | SCN-050/2, SCN-052/1 |
| FG-S-9 | URL placeholder resolution failures in test runner | TEST-3 | SCN-075/2-3, SCN-075/5, SCN-076/4-5, SCN-084/1-3 (also TEST-4, TEST-5) |
| FG-S-10 | Test navigation failures (wrong page loaded) | TEST-6 | SCN-015/2-4, SCN-026/1-4, SCN-058/4, SCN-059/1 (also TEST-1, TEST-2, TEST-7, TEST-8) |
| FG-S-11 | htmx:syntax:error on form pages | BUG-20 | SCN-053/2, SCN-058/4, SCN-061/1 |
| FG-S-12 | Dashboard information density exceeds cognitive thresholds | BUG-18 | SCN-005/2, SCN-058/1 |

---

## IMPROVE-1: No onboarding guidance for first-time users

**Severity:** IMPROVE — Review recommended
**Persona:** DS1b (Casey Makwa, first week)
**Scenario:** SCN-005, Step 2
**Screenshot:** SCN-005_step1_DS1b_home.png

**What's wrong:** Landing page shows 5 stat cards, priority items with 11 entries, alerts, and multiple navigation options without any onboarding prompt or "start here" guidance. A first-week user like Casey with medium-low tech comfort would feel overwhelmed rather than oriented.

**Acceptance criteria:**
- [ ] First-time login shows a brief onboarding prompt or "start here" call to action
- [ ] Re-run SCN-005 step 2 — score improves to Green band (4.0+)

---

## IMPROVE-2: No "Create New" prompt in empty search results

**Severity:** IMPROVE — Review recommended
**Persona:** R1 (Dana Petrescu)
**Scenario:** SCN-010, Step 2
**Screenshot:** SCN-010_step2_R1_participants.png

**What's wrong:** When search returns no results, the page shows a helpful message and a Clear Search button, but does not offer a "Create New Participant" link or button. For a receptionist who just confirmed a client is not in the system, the logical next step should be immediately visible.

**Acceptance criteria:**
- [ ] No-results state includes a visible "Create New Participant" button or link
- [ ] Re-run SCN-010 step 2 — score improves to Green band (4.0+)

---

## IMPROVE-3: Admin dropdown visible in navigation for executive role (E2)

**Severity:** IMPROVE — Review recommended
**Persona:** E2 (Kwame Asante)
**Scenario:** SCN-030, Step 3
**Screenshot:** SCN-030_step3_E2_participants-executive.png

**What's wrong:** E2 sees an "Admin" dropdown menu in the top navigation bar. Executives have `user.manage: deny` and `settings.manage: deny`. While the admin pages may correctly deny access, showing the menu item creates confusion about role boundaries. E1 (Margaret) does not see this menu item — the inconsistency suggests E2 may have elevated permissions.

**Acceptance criteria:**
- [ ] Admin dropdown is hidden for executive role users
- [ ] Navigation shows only pages the role has access to

---

## IMPROVE-4: Funder report uses Fiscal Year only — no quarterly date range option

**Severity:** IMPROVE — Review recommended
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-035, Step 2
**Screenshot:** SCN-035_step2_PM1_reports-funder-report.png

**What's wrong:** The funder report form offers only Fiscal Year (April-March) granularity. Morgan needs quarterly data for her funder submission. There are no quarter presets, no custom date range, and no way to isolate Q3 or Q4 data specifically.

**Acceptance criteria:**
- [ ] Date range selector includes quarterly presets (Q1, Q2, Q3, Q4) in addition to Fiscal Year
- [ ] Custom date range option available for non-standard reporting periods

---

## IMPROVE-5: No restricted-content message when staff views multi-programme client

**Severity:** IMPROVE — Review recommended
**Persona:** DS1 (Casey Makwa)
**Scenario:** SCN-042, Step 2
**Screenshot:** SCN-042_step2_DS1_participants-6.png

**What's wrong:** When Casey (Housing Support staff) views Aaliyah Thompson's profile, only Housing Support is listed under Programmes. There is no indication that Aaliyah is enrolled in another programme with restricted notes. Casey would assume Housing Support is the only programme, which could lead to incomplete understanding of the client's situation.

**Acceptance criteria:**
- [ ] When a staff member views a multi-programme client, a message indicates that content from other programmes exists but is restricted
- [ ] The message is non-alarming and provides guidance (e.g., "contact your programme manager")
- [ ] Re-run SCN-042 step 2 — restricted content message visible

---

## IMPROVE-6: 403 denial pages should use role-specific messaging instead of generic "Access denied"

**Severity:** IMPROVE — Review recommended
**Persona:** R1 (Dana Petrescu)
**Scenario:** SCN-085, Steps 1-2
**Screenshot:** SCN-085_step1_R1_events-meetings.png

**What's wrong:** The 403 page says "Access denied. Your role does not have permission for this action." This is accurate but generic. For Dana (low tech comfort, panics at error messages), a role-specific message like "Meeting scheduling is managed by direct service staff and programme managers. As front desk staff, you can look up participants and update contact information." would be more reassuring and informative.

**Acceptance criteria:**
- [ ] 403 pages display role-aware messaging that explains which roles CAN access the feature
- [ ] Message tone is reassuring, not accusatory
- [ ] Re-run SCN-085 steps 1-2 — Confidence dimension improves to 3.5+

---

## IMPROVE-7: Executive role needs aggregate compliance report access (not raw audit log)

**Severity:** IMPROVE — Review recommended
**Persona:** E1 (Margaret Whitfield)
**Scenario:** SCN-070, Step 6
**Screenshot:** SCN-070_step6_E1_admin-audit-log.png

**What's wrong:** Margaret is correctly denied access to the raw audit log (appropriate for PIPEDA 4.4). However, there is no alternative mechanism for executives to verify compliance. Margaret needs an aggregate compliance dashboard or report that shows "privacy requests processed this quarter" without exposing individual records. Currently, she must ask Morgan or IT.

**Acceptance criteria:**
- [ ] An aggregate compliance report or dashboard section is available to executives
- [ ] The report shows privacy request counts, processing times, and completion status without individual PII
- [ ] Margaret can verify PIPEDA compliance without accessing the raw audit log

---

## IMPROVE-8: Mobile participant list should show result count

**Severity:** IMPROVE — Review recommended
**Persona:** R2 (Omar Hussain)
**Scenario:** SCN-047, Step 3
**Screenshot:** SCN-047_step3_R2_home.png

**What's wrong:** When Omar searches for "Aisha," the search result card appears but there is no visible count like "1 result found." For a receptionist handling 30-40 clients per day, knowing how many results matched helps confirm the search is complete, especially on mobile where the interface is more constrained.

**Acceptance criteria:**
- [ ] Search results show a count (e.g., "1 participant found" or "Showing 1 of 1")
- [ ] Count is visible on mobile without scrolling

---

## IMPROVE-9: Form tab order may confuse screen reader users with two-column layout

**Severity:** IMPROVE — Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-053, Step 2
**Screenshot:** SCN-053_step2_DS3_participants-create.png

**What's wrong:** The create-participant form uses a two-column layout where Tab order goes left then right within each row. For a screen reader user who cannot see the visual layout, this left-right-left-right pattern can be confusing. Data ended up in wrong fields.

**Acceptance criteria:**
- [ ] Tab order through form fields is predictable and announced by JAWS in logical sequence
- [ ] Consider stacking required fields in single column to make tab order more intuitive for screen readers
- [ ] HTMX errors during form interaction are resolved
- [ ] Re-run SCN-053 step 2 — score improves to Green band (4.0+)

---

## IMPROVE-10: Filter controls intercept Tab order between search field and results

**Severity:** IMPROVE — Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-055, Step 2
**Screenshot:** SCN-055_step2_DS3_participants.png

**What's wrong:** After searching for a client, Tab from the search field goes to Status and Programme filter dropdowns before reaching the result links. For a screen reader user who just searched and wants to navigate to the result, this adds 2-3 extra Tab presses through controls she does not need.

**Acceptance criteria:**
- [ ] After search results load, Tab from search field reaches the first result link within 3 presses
- [ ] Consider an aria landmark or skip mechanism to bypass filter controls when results are present
- [ ] Re-run SCN-055 step 2 — score improves to Green band (4.0+)

---

## IMPROVE-11: Status dropdown opens on Tab navigation, adding friction for keyboard users

**Severity:** IMPROVE — Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-062, Step 2
**Screenshot:** SCN-062_step2_DS3_participants.png

**What's wrong:** During keyboard Tab navigation through the participants search form, the Status dropdown opens automatically, adding an extra interaction step that Amara must navigate past on every lookup. The dropdown should not open on focus — it should open on Enter/Space activation only.

**Acceptance criteria:**
- [ ] Status dropdown does not auto-open when receiving Tab focus
- [ ] Dropdown opens only on explicit activation (Enter, Space, or arrow keys)
- [ ] Re-run SCN-062 — no unintended dropdown opening during Tab navigation

---

## IMPROVE-12: Verify "Results loaded" text is in an aria-live region

**Severity:** IMPROVE — Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-062, Step 1
**Screenshot:** SCN-062_step1_DS3_participants.png

**What's wrong:** The "Results loaded" status text appears visually on every search, which is positive. However, from the screenshots alone it is not possible to confirm whether this text is in an `aria-live="polite"` region that JAWS would announce. If it is not in a live region, Amara would not hear the result count. The empty-state message appears to be in a different container — if one is in a live region and the other is not, the inconsistency could cause missed announcements.

**Acceptance criteria:**
- [ ] "Results loaded" and its count are in an `aria-live="polite"` region
- [ ] Empty-state message uses the same live region
- [ ] Error states use `aria-live="assertive"` or `role="alert"` for distinction
- [ ] Verify with JAWS that all three states are announced consistently

---

## IMPROVE-13: Status indication uses colour-only green dot — needs text alternative

**Severity:** IMPROVE — Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-063, Step 2
**Screenshot:** SCN-063_step2_DS3_participants.png

**What's wrong:** The programme column in the participants list uses a green dot icon before the programme name. While the programme name text is visible, the green dot appears to convey "active/enrolled" status through colour alone. If this dot has no text alternative, it fails WCAG 1.4.1 (Use of Colour).

**Acceptance criteria:**
- [ ] Green dot icons have `aria-hidden="true"` if purely decorative (programme name text is sufficient)
- [ ] If green dot conveys additional meaning (e.g., "enrolled"), it has a text alternative
- [ ] Arrow icons beside names have `aria-hidden="true"` or descriptive alt text
- [ ] No JAWS announcement of "image" or "graphic" without description

---

## Test Infrastructure Issues

### TEST-1: SCN-015 batch note workflow not executed by test automation

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-015, Steps 2-4, Persona DS1
**Reason:** Steps 2-4 show identical or near-identical screenshots of Jane Doe's Info tab. The test automation failed to navigate to the quick note form, create a note, switch to the second client, or execute the batch workflow. The core purpose of this scenario (batch note entry speed) was not tested.

**Fix in:** konote-app test runner (not the app)
**Priority:** Fix before next round — blocks DS1 coverage for batch note workflow

---

### TEST-2: SCN-026 test automation failed to navigate beyond landing page

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-026, Steps 1-4, Persona R2-FR
**Reason:** All 4 screenshots show the identical landing page. The test automation never clicked "Creer un participant," never filled the form, never submitted, and never searched. The French intake UX cannot be evaluated. The receptionist landing page for R2-FR does not show a prominent create button (see BUG-6), which may explain why the click action failed.

**Fix in:** konote-app test runner (not the app); also fix BUG-6 to ensure the button exists
**Priority:** Fix before next round — blocks R2-FR coverage entirely

---

### TEST-3: SCN-075 and SCN-076 URL placeholders ({alert_id}, {group_id}) not resolved

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-075, Steps 2-3, 5; SCN-076, Steps 4-5, Persona DS1/PM1
**Reason:** The test runner navigated to URLs containing literal `{alert_id}`, `{recommendation_id}`, and `{group_id}` placeholder text instead of actual IDs. All affected steps show 404 errors. The test runner needs to either capture IDs from prerequisite setup or use a lookup mechanism at runtime.

**Fix in:** konote-app test runner
**Priority:** Fix before next round — blocks alert workflow and group milestone/attendance coverage

---

### TEST-4: SCN-082 meeting data not seeded — entire scenario blocked

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-082, Steps 1-5, Persona PM1
**Reason:** The scenario requires 3 prerequisite meetings but the meeting dashboard shows 0 upcoming and 0 recent meetings. The test environment did not seed the prerequisite data.

**Fix in:** konote-app test runner (data seeding)
**Priority:** Fix before next round — blocks PM meeting dashboard evaluation

---

### TEST-5: SCN-084 communication/reminder URL placeholders not resolved

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-084, Steps 1-3, Persona DS1
**Reason:** All three DS1 steps navigate to URLs containing literal `{client_id_alex}`, `{meeting_id_alex}`, `{client_id_priya}`, `{meeting_id_priya}` placeholder text. The consent guardrail workflow could not be evaluated.

**Fix in:** konote-app test runner
**Priority:** Fix before next round — blocks consent guardrail coverage

---

### TEST-6: SCN-046 session timeout cannot be simulated by test runner

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-046, Steps 1-4, Persona DS1
**Reason:** The test runner could not navigate to the quick note form, could not simulate a 20-minute idle period, and could not trigger session timeout or note recovery. This scenario requires a different approach (manual testing, session cookie manipulation, or shorter timeout configuration).

**Fix in:** konote-app test runner or manual test protocol
**Priority:** Consider manual testing for this scenario

---

### TEST-7: SCN-049 Playwright timing failure blocks shared device handoff test

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-049, Steps 1-6, Persona DS1/R1
**Reason:** Playwright timing failure prevented the multi-user shared device handoff scenario from completing. The test requires two sequential user sessions on the same browser context with precise timing.

**Fix in:** konote-app test runner (Playwright timeout configuration)
**Priority:** Fix before next round — PIPEDA shared-device test is important

---

### TEST-8: SCN-048 test data missing consent for James Thompson

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-048, Step 2, Persona DS1
**Reason:** The test prerequisite specifies James Thompson as an active client, but his record has "No Consent" status, blocking the entire note-writing workflow. The consent gate is correct application behaviour, but the test data should have consent recorded.

**Fix in:** konote-app test runner (data seeding)
**Priority:** Fix before next round — blocks slow-network note-writing coverage

---

### TEST-9: SCN-058 test runner navigated to wrong page (create-participant instead of note form)

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-058, Step 4, Persona DS1c
**Reason:** Test runner navigated to the create-participant form instead of Jane Doe's profile and note form. The ADHD interruption-recovery scenario could not be evaluated.

**Fix in:** konote-app test runner (selector correction)
**Priority:** Fix before next round

---

### TEST-10: SCN-059 used wrong login URL (/auth/login/ vs /accounts/login/)

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-059, Step 1, Persona DS4
**Reason:** The scenario directed the test runner to `/auth/login/` but the application uses `/accounts/login/`. Riley sees a 404 instead of the login form.

**Fix in:** Scenario YAML and/or test runner URL mapping
**Priority:** Fix before next round — blocks voice navigation login test

---

### TEST-11: SCN-059 note creation flow incomplete — dictation not verified

**Type:** Test infrastructure (not an app bug)
**Scenario:** SCN-059, Steps 5-6, Persona DS4
**Reason:** The test runner did not successfully create a new note. Steps 5 and 6 show identical screenshots with only a pre-existing note visible. The core test objective (Dragon can dictate into a textarea and save) was not achieved.

**Fix in:** konote-app test runner (selector correction for note creation)
**Priority:** Fix before next round — blocks voice navigation note-writing coverage

---

## Items NOT Filed as Tickets (Probable Test Artefacts)

The following observations look like bugs but are actually test runner limitations or test data issues. They are documented here to prevent re-filing in future rounds.

1. **SCN-010 step 4: Casey (DS1) sees French participant list** — Language session bleed from Dana's French session in step 3. The test runner shares a browser context between persona switches. This is a test infrastructure issue, though BUG-1 (language persistence) would prevent it in production if fixed.

2. **SCN-025 step 2: Identical screenshot to step 1** — The search returned no results for "Priya" in both steps. The consecutive identical screenshots are expected because the search query was the same. Not a separate bug from BUG-5.

3. **SCN-042 step 4: 404 for slug-based participant URL** — Casey attempted to access `/participants/aaliyah-thompson/notes/` but the actual URL uses numeric IDs (`/participants/6/notes/`). The test runner used a human-readable slug instead of the database ID. This is a test URL resolution issue, not an app bug.

4. **SCN-056 steps 2-4: Language switch during 200% zoom test** — The login sequence at 200% zoom appears to have Tab-activated the language toggle, switching Amara's interface to French. This is partially a test artefact (the zoom test accidentally triggered the toggle) and partially an accessibility issue (the toggle should not be so easily activated). Filed as BUG-1 (language persistence) rather than a separate accessibility bug.

5. **SCN-075 step 1: Wrong client (Jane Doe instead of David Park)** — The test navigated to participant ID 1 instead of the prerequisite client. Test data setup issue.

6. **SCN-062 step 5: Network error simulation did not produce visible error** — The Playwright network intercept for a 500 error did not surface a visible error in the application. The test infrastructure cannot reliably simulate server errors via network interception. Consider using a test endpoint that returns a 500 instead.

---

*Generated by Claude (automated evaluation pipeline) — 2026-02-21*
*42 scenarios across 7 batches, 13 personas*
*Totals: 1 PERMISSION, 7 BLOCKERS, 23 BUGS, 13 IMPROVES, 11 TEST tickets*
*After deduplication of cross-cutting language issue (22 scenarios consolidated into BUG-1)*
