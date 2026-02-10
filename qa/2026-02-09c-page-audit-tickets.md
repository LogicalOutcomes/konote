# KoNote Page Audit -- Improvement Tickets (2026-02-09c)

**Date:** 2026-02-09 (sequence c)
**Source:** Page audit evaluation across all auditable pages, personas, states, and breakpoints
**Ticket numbering:** Page audit uses PERMISSION-N, BLOCKER-N, BUG-N, IMPROVE-N, COSMETIC-N, TEST-N
**Finding group prefix:** FG-P-N (page audit findings)

---

## Summary

| Category | Count | Severity |
|----------|-------|----------|
| Permission violations | 6 | 4 BLOCKER, 1 BUG, 1 BUG (test config) |
| Blockers | 2 | BLOCKER |
| Bugs | 10 | BUG |
| Improvements | 32 | IMPROVE |
| Cosmetic | 4 | COSMETIC |
| Test infrastructure | 6 | TEST |
| **Total findings** | **60** | |
| **Finding groups** | **7** | |

**Permission violation count: 6** -- These appear before all other findings because authorization failures are more serious than UX issues.

---

## Permission Tickets

These are authorization violations. Each one means a persona can see or do something they should not. All over-permission violations are BLOCKER severity. Under-permission violations are BUG severity.

---

### PERMISSION-1: PM1 sees Edit buttons on client-detail page

**Severity:** BLOCKER (authorization violation)
**Persona:** PM1 (Morgan Tremblay -- Program Manager)
**Page:** client-detail
**Violation type:** action_scope

**What's wrong:** Edit button is visible on the client detail page. PM1 has `client.edit: deny` and `note.edit: deny` in their permission scope, but the Edit controls appear in the UI. This is an over-permission violation -- PM1 can initiate edits they are not authorized to make.

**Expected behaviour:** No Edit buttons should be visible. PM1 should see a read-only view of client details with no edit affordances.

**Compliance references:** PIPEDA 4.7 (appropriate safeguards -- limit ability to modify records to authorized personnel)

**Where to look:** Django template for client detail view -- need `{% if perms.auth_app.client_edit %}` guard (or equivalent permission check) around the Edit button. Also check the corresponding Django view to ensure POST requests are rejected even if the button is visible.

**Acceptance criteria:**
- [ ] PM1 sees client detail page with no Edit buttons
- [ ] POST to client edit endpoint returns 403 for PM1 role
- [ ] Re-run page audit for client-detail x PM1 -- no action_scope violation

**Screenshot reference:** client-detail-PM1-default-1366x768.png
**Finding Group:** FG-P-2

---

### PERMISSION-2: PM1 sees 9 edit/add controls on plan-view page

**Severity:** BLOCKER (authorization violation)
**Persona:** PM1 (Morgan Tremblay -- Program Manager)
**Page:** plan-view (populated state)
**Violation type:** action_scope

**What's wrong:** Add Section, Add Target, and Edit buttons are all visible on the plan view page. PM1 has `plan.edit: deny` -- these controls should be hidden entirely. Nine separate edit/add controls are exposed, any of which could allow unauthorized modification of client plans.

**Expected behaviour:** PM1 should see the plan in read-only mode with no Add Section, Add Target, or Edit buttons. The plan content should be fully visible for oversight purposes, but no modification controls should appear.

**Compliance references:** PIPEDA 4.7 (appropriate safeguards)

**Where to look:** Plan view template -- wrap all edit controls in `{% if perms.auth_app.plan_edit %}` or equivalent permission guard. There are likely multiple template blocks that each need the guard (section header, target rows, inline edit buttons).

**Acceptance criteria:**
- [ ] PM1 sees plan-view with no Add/Edit buttons
- [ ] All 9 controls hidden for users with plan.edit: deny
- [ ] POST to plan edit endpoints returns 403 for PM1 role
- [ ] Re-run page audit for plan-view x PM1 -- no action_scope violation

**Screenshot reference:** plan-view-PM1-populated-1366x768.png
**Finding Group:** FG-P-2

---

### PERMISSION-3: DS1 sees Edit Group button on groups-detail

**Severity:** BLOCKER (authorization violation)
**Persona:** DS1 (Casey Makwa -- Direct Service Worker)
**Page:** groups-detail
**Violation type:** action_scope

**What's wrong:** Edit Group button is visible on the groups detail page. Staff role has `group.edit: deny` -- only Program Managers should see group editing controls.

**Expected behaviour:** Only PM1 (group.edit: allow) should see the Edit Group button. All staff personas (DS1, DS1b, DS1c, DS2, DS3, DS4) should see a read-only view of group details.

**Compliance references:** PIPEDA 4.7

**Where to look:** Groups detail template -- permission check around the Edit Group button. Check whether the guard uses the correct permission key from `permissions.py`.

**Acceptance criteria:**
- [ ] DS1 sees groups-detail page with no Edit button
- [ ] PM1 still sees Edit button on groups-detail page
- [ ] POST to group edit endpoint returns 403 for staff role

**Screenshot reference:** groups-detail-DS1-default-1366x768.png
**Finding Group:** FG-P-2

---

### PERMISSION-4: Staff personas see "+ New Group" button on groups-list

**Severity:** BLOCKER (authorization violation)
**Persona:** DS1, DS1b, DS1c, DS2, DS3, DS4 (all staff personas)
**Page:** groups-list
**Violation type:** action_scope

**What's wrong:** The "+ New Group" button is visible for all staff personas. Staff have `group.edit: deny` -- they should not see group creation controls. This affects six personas simultaneously.

**Expected behaviour:** Only PM1 and admin should see the "+ New Group" button. Staff personas should see the groups list with no creation affordances.

**Compliance references:** PIPEDA 4.7

**Where to look:** Groups list template -- permission check around the Create button. May be using a different permission key than `group.edit` -- verify against `permissions.py`.

**Acceptance criteria:**
- [ ] No staff persona sees "+ New Group" button on groups-list
- [ ] PM1 still sees "+ New Group" button
- [ ] POST to group create endpoint returns 403 for staff role

**Screenshot reference:** groups-list-DS1-default-1366x768.png (and all other staff variants)
**Finding Group:** FG-P-2

---

### PERMISSION-5: E2 sees Admin dropdown in navigation

**Severity:** BLOCKER (authorization violation)
**Persona:** E2 (Kwame Asante -- Board Treasurer)
**Page:** dashboard-staff (should be dashboard-executive)
**Violation type:** page_access

**What's wrong:** Two issues compounded: (1) Admin dropdown is visible in the navigation bar -- E2 has `admin: false` and should not see admin navigation items. (2) E2 appears to be seeing the staff dashboard instead of the executive dashboard, suggesting the test user role may be misconfigured or the login redirect logic does not distinguish executive from staff roles.

**Expected behaviour:** No admin navigation items should be visible. E2 should see the executive dashboard at `/clients/executive/` with aggregate metrics only -- no individual client data, no admin controls.

**Compliance references:** PIPEDA 4.7 (need-to-know principle -- board members should not have administrative access)

**Where to look:** Base template navigation -- `{% if perms.auth_app.user_manage %}` or `{% if user.is_staff %}` guard around admin dropdown. Also check the login redirect logic to route executive users to `/clients/executive/`. Additionally, verify E2 test user role assignment in fixtures.

**Acceptance criteria:**
- [ ] E2 sees executive dashboard, not staff dashboard
- [ ] No admin menu items visible for executive role
- [ ] Clicking any admin URL directly returns 403 for executive role
- [ ] Re-run page audit for dashboard x E2 -- no page_access violation

**Screenshot reference:** dashboard-staff-E2-default-1366x768.png
**Finding Group:** FG-P-3

---

### PERMISSION-6: R1/R2-FR missing "New Participant" button (under-permission)

**Severity:** BUG (under-permission -- blocks intended workflow)
**Persona:** R1 (Dana Whitecrow -- Receptionist), R2-FR (Amelie Tremblay -- Receptionist, French)
**Page:** client-list
**Violation type:** under-permission

**What's wrong:** The "New Participant" / Create button is missing from the client list page. Receptionist role has `client.create: allow` -- they should see this button because client intake is their primary job responsibility. Without it, receptionists cannot create new participant records, which is a core workflow blocker.

**Expected behaviour:** R1 and R2-FR should see a "New Participant" button on the client list page. Clicking it should navigate to the client-create form.

**Where to look:** Client list template -- check the permission guard condition. The guard may be checking the wrong permission key, or may be using `and` instead of `or` to combine permissions (e.g., requiring both `client.create` and `client.edit` when only `client.create` is needed).

**Acceptance criteria:**
- [ ] R1 sees "New Participant" button on client list
- [ ] R2-FR sees equivalent button (in French when i18n is working)
- [ ] Clicking the button navigates to client-create form
- [ ] Re-run page audit for client-list x R1 -- button present

**Screenshot reference:** client-list-R1-default-1366x768.png
**Finding Group:** FG-P-3

---

## Blocker Tickets

These are non-permission blockers -- critical failures that prevent core functionality.

---

### BLOCKER-1: Complete French translation failure

**Severity:** BLOCKER
**Personas:** DS2 (Jean-Luc Bergeron -- Direct Service Worker, French), R2-FR (Amelie Tremblay -- Receptionist, French)
**Pages affected:** ALL pages -- dashboard-staff, client-list, client-search, client-create, client-detail, client-edit, notes-list, notes-create, plan-view, groups-list, public-help, public-privacy. Every page tested shows zero French text.

**What's wrong:** The entire interface is in English for users whose language preference is French. This is not a partial translation gap -- **zero French text appears on any page**. Every heading, label, button, placeholder, help text, system message, and navigation element is English. Two personas (DS2 and R2-FR) are completely unable to use the application in their preferred language.

**Root cause (likely):** Django i18n framework not activated. Possible causes, in order of likelihood:
1. `LocaleMiddleware` not in `MIDDLEWARE` setting
2. No `.po`/`.mo` translation files generated or compiled
3. `LANGUAGE_CODE` hardcoded to `'en'` without fallback logic
4. Templates not using `{% trans %}` or `{% blocktrans %}` tags
5. `i18n_patterns` not wrapping URL configuration

**Compliance references:**
- Quebec Official Languages Act (services must be available in French)
- Charter of the French Language (Bill 96 -- commercial/service obligations)
- PIPEDA informed consent (user must understand what they are consenting to in their language)

**Acceptance criteria:**
- [ ] DS2 and R2-FR see French interface text on all pages
- [ ] Navigation, buttons, labels, placeholders, and help text all translated
- [ ] User language preference persists across sessions
- [ ] At minimum: login, dashboard, client list, client create, client detail forms in French
- [ ] Privacy policy available in French (PIPEDA informed consent requirement)

**Finding Group:** FG-P-1

---

### BLOCKER-2: Public registration form returns 404

**Severity:** BLOCKER
**Persona:** Unauthenticated (public user)
**Page:** public-registration-form (`/register/intake/`)

**What's wrong:** The URL `/register/intake/` returns a 404 error. The public registration form is how agencies accept new client self-registrations -- if it does not load, this intake pathway is completely blocked.

**Root cause (likely):** URL routing issue. The URL pattern may not be registered in `urls.py`, the view may not exist yet, or the URL may have changed during development.

**Acceptance criteria:**
- [ ] `/register/intake/` returns 200 and displays the registration form
- [ ] Form is accessible to unauthenticated users (no login required)
- [ ] Form fields match what is defined in the admin registration settings
- [ ] Form submission creates a pending intake record

---

## Bug Tickets

These are functional bugs -- things that are broken or behave incorrectly.

---

### BUG-1: R2 (Omar) blocked from client-detail page

**Severity:** BUG
**Persona:** R2 (Omar Kassab -- Receptionist, tech-savvy)
**Page:** client-detail

**What's wrong:** R2 has `client.view_name: allow` but receives a 403 or redirect when trying to view a client detail page. This may be a cross-program scoping issue -- the test client may not be in R2's assigned program, or the permission check may be too restrictive (checking `client.view_full` instead of `client.view_name`).

**Acceptance criteria:**
- [ ] R2 can view client-detail for clients in their assigned programs
- [ ] 403 only shown for clients outside their program scope
- [ ] Client name and basic info visible (consistent with `client.view_name: allow`)

**Finding Group:** FG-P-3

---

### BUG-2: Generic 403 error message does not match actual role

**Severity:** BUG
**Personas:** Multiple (PM1 on notes-create, R1 on restricted pages, others)
**Pages:** Various pages returning 403

**What's wrong:** The 403 page shows a generic "You don't have permission to access this page" without explaining why or what the user's role allows. This causes confusion -- users cannot tell if it is a temporary bug, a system error, or a permanent restriction. They do not know who to contact or what to do next.

**Expected behaviour:** Role-aware denial message, for example: "As a Program Manager, you can view notes but cannot create them. Contact your administrator if you need this access."

**Acceptance criteria:**
- [ ] 403 page shows the user's role name
- [ ] 403 page explains what action was denied and why
- [ ] 403 page suggests who to contact for access changes
- [ ] Message is translated for French-language users

---

### BUG-3: Cancel Note button has no confirmation dialog

**Severity:** BUG
**Personas:** All note-eligible (DS1, DS1b, DS1c, DS2, DS3, DS4)
**Page:** notes-create

**What's wrong:** Clicking "Cancel" on a note form immediately discards all content with no "Are you sure?" prompt. Clinical notes can be lengthy and detailed -- losing them with a single accidental click is a significant data loss risk, especially for DS1c (ADHD -- accidental clicks are more likely).

**Acceptance criteria:**
- [ ] Cancel shows confirmation dialog if form has unsaved content
- [ ] Cancel without content goes back immediately (no unnecessary prompt)
- [ ] Dialog text clearly states that unsaved work will be lost

**Finding Group:** FG-P-4

---

### BUG-4: DS1 cannot edit own notes

**Severity:** BUG
**Persona:** DS1 (Casey Makwa -- Direct Service Worker)
**Page:** notes-detail

**What's wrong:** Staff should be able to edit their own notes (`note.edit: scoped` -- own notes only) but the Edit button is missing on notes-detail for all notes, including those created by the logged-in user. The permission check appears to be `note.edit: deny` rather than the scoped check.

**Expected behaviour:** Edit button visible on notes created by the logged-in user. Hidden on notes created by others. This is a scoped permission, not a blanket deny.

**Acceptance criteria:**
- [ ] DS1 sees Edit button on notes they created
- [ ] DS1 does NOT see Edit button on notes created by others
- [ ] Edit button leads to a working edit form
- [ ] Saving edits updates the note successfully

---

### BUG-5: "--" empty metrics inaccessible to screen readers

**Severity:** BUG
**Persona:** DS3 (Amara Okafor -- Direct Service Worker, screen reader user)
**Pages:** dashboard-staff, plan-view, reports-insights

**What's wrong:** Empty metric values are displayed as "--" (two hyphens) with no screen reader alternative. NVDA would read "dash dash" which conveys no meaning. This affects multiple dashboard cards and report metrics throughout the application.

**Expected behaviour:** Use `aria-label="No data"` or visually hidden text "No data available" alongside the "--" display. The visual presentation should remain unchanged.

**Acceptance criteria:**
- [ ] Screen reader announces "No data" or equivalent when encountering "--"
- [ ] Visual display of "--" unchanged for sighted users
- [ ] Fix applied consistently across dashboard, plan-view, and reports pages

**Finding Group:** FG-P-6

---

### BUG-6: Remove member from group has no confirmation

**Severity:** BUG
**Persona:** PM1 (Morgan Tremblay -- Program Manager)
**Page:** groups-detail

**What's wrong:** The "Remove" button for group members is a one-click destructive action with no confirmation and no undo. Accidentally removing a participant from a group could disrupt service delivery and lose attendance history associations.

**Acceptance criteria:**
- [ ] Remove shows confirmation dialog: "Remove [Name] from [Group]? This cannot be undone."
- [ ] User must confirm before removal executes
- [ ] Confirmation dialog is keyboard-accessible and screen-reader-friendly

**Finding Group:** FG-P-4

---

### BUG-7: No unsaved changes warning on forms

**Severity:** BUG
**Personas:** All form users
**Pages:** client-create, client-edit, notes-create, plan-section-edit

**What's wrong:** Navigating away from a form with unsaved changes loses all data with no browser prompt. Users who accidentally click a navigation link, press the back button, or close the tab lose everything they have entered. This is especially problematic for long clinical notes and detailed client intake forms.

**Expected behaviour:** The `beforeunload` event (or equivalent) warns the user before navigation when the form has been modified.

**Acceptance criteria:**
- [ ] Browser shows "You have unsaved changes" when navigating away from a dirty form
- [ ] Prompt only appears when form has been modified (not on clean forms)
- [ ] Works across all major form pages: client-create, client-edit, notes-create, plan-section-edit

**Finding Group:** FG-P-4

---

### BUG-8: DS3 ARIA semantics unverifiable from screenshots

**Severity:** BUG (testing gap)
**Persona:** DS3 (Amara Okafor -- screen reader user)
**Pages:** All pages

**What's wrong:** ARIA roles, landmarks, live regions, and screen reader announcements cannot be verified from PNG screenshots alone. DS3's full experience is only partially evaluable through the current page audit methodology. This means DS3 scores are likely optimistic -- real screen reader issues may exist that screenshots cannot reveal.

**Recommendation:** Add automated accessibility checks to the test runner (e.g., axe-core integration) and/or conduct manual NVDA walkthrough testing as a supplementary evaluation method.

**Acceptance criteria:**
- [ ] axe-core (or equivalent) integrated into test runner, results captured per page
- [ ] Manual NVDA walkthrough completed for top 5 DS3-critical pages
- [ ] Any new ARIA issues found are filed as separate tickets

---

### BUG-9: Missing accent on Amelie (should be Amelie with accent)

**Severity:** BUG
**Persona:** R2-FR (Amelie Tremblay)
**Pages:** Various (wherever persona name appears in the UI)

**What's wrong:** French diacritical characters are stripped -- "Amelie" displays without the accent aigu on the first "e". This indicates a character encoding issue where UTF-8 is not consistently applied across the data pipeline (database storage, template rendering, HTTP headers).

**Acceptance criteria:**
- [ ] All French characters with accents display correctly throughout the application
- [ ] Database columns use UTF-8 encoding
- [ ] Templates render UTF-8 characters correctly
- [ ] HTTP response headers include `charset=utf-8`

---

### BUG-10: E2 test user receives staff dashboard instead of executive dashboard

**Severity:** BUG (test configuration)
**Persona:** E2 (Kwame Asante -- Board Treasurer)
**Page:** dashboard

**What's wrong:** E2 persona expects the executive dashboard at `/clients/executive/` but screenshots show the staff dashboard at `/`. The test user `executive2` may have the wrong role assigned in fixtures, or the login redirect logic may not differentiate between executive and staff roles.

**Acceptance criteria:**
- [ ] E2 test user (`executive2`) assigned executive role in test fixtures
- [ ] Logging in as `executive2` redirects to `/clients/executive/`
- [ ] Executive dashboard shows aggregate metrics only (no individual client data)

---

## Improvement Tickets

Grouped by theme for easier triage and assignment.

---

### Forms

---

#### IMPROVE-1: No auto-save on clinical forms

**Severity:** IMPROVE
**Pages:** notes-create, plan-section-edit, plan-target-edit

**What's wrong:** Clinical note forms have no auto-save functionality. Staff (especially DS1c with ADHD, who is prone to mid-task interruptions) risk losing significant work if interrupted, if the browser crashes, or if the session times out.

**Recommendation:** Auto-save draft every 30 seconds with a visual indicator ("Draft saved 30s ago"). Drafts should persist across browser sessions (localStorage or server-side).

**Finding Group:** FG-P-5

---

#### IMPROVE-2: Date picker defaults to current date

**Severity:** IMPROVE
**Pages:** notes-create, events-create

**What's wrong:** The date field defaults to today's date. In social services, backdated notes are common (e.g., writing up yesterday's session notes the following morning). Users must always change the date manually, adding friction to a daily task.

**Recommendation:** Default to today but make the date field prominent and easy to change. Consider a "quick pick" for yesterday and last Friday.

---

#### IMPROVE-3: Required fields not visually distinct until validation

**Severity:** IMPROVE
**Pages:** client-create, notes-create

**What's wrong:** Required fields are only identified as required after the user tries to submit the form and validation fails. Users cannot tell which fields are mandatory before filling out the form, leading to wasted effort and frustration.

**Recommendation:** Mark required fields with an asterisk (*) and a "* Required" legend from the start. Use `aria-required="true"` for screen readers.

**Finding Group:** FG-P-5

---

#### IMPROVE-4: Form labels do not indicate character limits

**Severity:** IMPROVE
**Pages:** notes-create (note body field)

**What's wrong:** Text fields with character limits do not show the limit or a character count. Users discover the limit only when they hit it, potentially after writing extensive content.

**Recommendation:** Show "X / 5000 characters" counter below text areas, updating as the user types.

**Finding Group:** FG-P-5

---

#### IMPROVE-5: Dropdown menus show raw category codes

**Severity:** IMPROVE
**Pages:** Various forms with dropdown/select fields

**What's wrong:** Some dropdown menus display internal category codes (e.g., "MENTAL_HEALTH" instead of "Mental Health") rather than human-readable labels. This is confusing for all personas, especially non-technical users like R1 and E1.

**Recommendation:** Ensure all dropdown options use human-readable display labels. Internal codes should remain as values but never be shown to users.

**Finding Group:** FG-P-5

---

#### IMPROVE-7: Text areas do not auto-resize

**Severity:** IMPROVE
**Pages:** notes-create

**What's wrong:** The note body text area has a fixed height. When writing longer clinical notes, users must scroll within the text area rather than seeing their full content. This makes reviewing and editing notes difficult.

**Recommendation:** Text areas should grow vertically as content is added, up to a reasonable maximum (e.g., 80% of viewport height), then switch to scrolling.

**Finding Group:** FG-P-5

---

#### IMPROVE-8: Save button far from form content on mobile

**Severity:** IMPROVE
**Pages:** client-create (375x667 breakpoint)

**What's wrong:** On mobile devices, the Save/Submit button is positioned far below the form content, requiring significant scrolling to reach. Users may not realize the button exists or may lose their place in the form while scrolling to find it.

**Recommendation:** Use a sticky footer bar on mobile with the Save button always visible, or add a secondary Save button at the top of the form.

**Finding Group:** FG-P-5

---

### Navigation

---

#### IMPROVE-9: No breadcrumbs on client sub-pages

**Severity:** IMPROVE
**Pages:** notes-list, notes-create, plan-view, events-list

**What's wrong:** Client sub-pages (notes, plans, events) have no breadcrumb trail showing the navigation hierarchy. Users cannot tell where they are in the application structure or easily navigate back to the client record. This is especially disorienting for DS1c (ADHD -- loses context easily) and DS3 (screen reader -- relies on page structure to orient).

**Recommendation:** Add breadcrumbs: Home > Participants > [Client Name] > Notes. Use `aria-label="Breadcrumb"` and `<nav>` element for accessibility.

**Finding Group:** FG-P-7

---

#### IMPROVE-10: Active nav item not visually distinguished

**Severity:** IMPROVE
**Pages:** All pages with navigation

**What's wrong:** The currently active navigation item looks the same as other navigation items. Users cannot tell which section of the application they are in by glancing at the navigation bar. This fails the "you are here" wayfinding principle.

**Recommendation:** Highlight the active navigation item with a distinct visual treatment (bold text, underline, background colour, or left border). Use `aria-current="page"` for screen readers.

**Finding Group:** FG-P-7

---

#### IMPROVE-11: Back link inconsistent

**Severity:** IMPROVE
**Pages:** Various (some pages have a back link, others do not; placement varies)

**What's wrong:** The back/return navigation pattern is inconsistent. Some pages have a "Back" link at the top, some at the bottom, some have none. Users cannot develop a reliable mental model of how to return to the previous page.

**Recommendation:** Standardize back navigation. Use breadcrumbs (IMPROVE-9) as the primary back navigation, with a consistent "Back to [context]" link below the page heading where breadcrumbs are not feasible.

**Finding Group:** FG-P-7

---

#### IMPROVE-12: Client name not shown in page title

**Severity:** IMPROVE
**Pages:** notes-list, plan-view, events-list

**What's wrong:** When viewing a specific client's notes, plans, or events, the page title/heading does not include the client's name. The heading says "Notes" or "Plan" without context. If a user has multiple tabs open for different clients, they cannot distinguish them. Screen reader users (DS3) hear only "Notes" when the page loads.

**Recommendation:** Include the client name in the page heading and `<title>` element: "Notes -- Sofia Reyes" and `<title>Notes - Sofia Reyes | KoNote</title>`.

**Finding Group:** FG-P-7

---

#### IMPROVE-13: Programs selector does not indicate current selection

**Severity:** IMPROVE
**Page:** programs-selector

**What's wrong:** The program filter/selector does not visually indicate which program is currently active. Users working across multiple programs cannot confirm which program context they are in.

**Recommendation:** Show the selected program name prominently with a visual indicator (e.g., checkmark, highlighted state). Consider persisting the selection across pages.

**Finding Group:** FG-P-7

---

#### IMPROVE-14: Admin sidebar navigation not in logical order

**Severity:** IMPROVE
**Pages:** Admin pages

**What's wrong:** The admin sidebar navigation items are not arranged in a logical task-flow order. Related items (e.g., user management and role management) are separated by unrelated items.

**Recommendation:** Group admin navigation by function: Users & Roles, Programs & Services, System Settings, Data Management.

---

### Dashboard & Reports

---

#### IMPROVE-15: Dashboard cards have no loading state indicator

**Severity:** IMPROVE
**Page:** dashboard-staff

**What's wrong:** When the dashboard loads, metric cards appear empty (showing "--") before data arrives. There is no loading spinner, skeleton screen, or other indicator that data is being fetched. Users may interpret "--" as "no data" rather than "loading."

**Recommendation:** Show skeleton loading states or a spinner within each card while data loads. Replace with actual values once available.

---

#### IMPROVE-16: Chart colours not distinguishable in greyscale

**Severity:** IMPROVE
**Pages:** dashboard-executive, reports-insights

**What's wrong:** Charts use colour alone to distinguish data series. When viewed in greyscale (or by users with colour vision deficiency), the series become indistinguishable. This is a WCAG 1.4.1 (Use of Colour) concern.

**Recommendation:** Add pattern fills, direct labels, or distinct line styles in addition to colour. Ensure a minimum 3:1 contrast ratio between adjacent chart elements.

**Finding Group:** FG-P-6

---

#### IMPROVE-17: Report date range selector has no presets

**Severity:** IMPROVE
**Page:** reports-export

**What's wrong:** The date range selector requires manual entry of start and end dates. Common reporting periods (this month, last quarter, fiscal year, last 12 months) have no preset buttons.

**Recommendation:** Add preset buttons for common periods: "This Month," "Last Quarter," "This Fiscal Year" (April-March for Canadian nonprofits), "Last 12 Months."

---

#### IMPROVE-18: Export button does not indicate format

**Severity:** IMPROVE
**Page:** reports-export

**What's wrong:** The Export button does not indicate what file format will be generated (CSV, Excel, PDF). Users must click to find out, which may produce an unwanted format.

**Recommendation:** Either label the button with the format ("Export as CSV") or provide a dropdown with format options.

---

#### IMPROVE-19: Insights page shows no results

**Severity:** IMPROVE (may be TEST issue)
**Page:** reports-insights (populated state screenshot shows empty)

**What's wrong:** The "populated state" screenshot of the insights page shows an empty results area. This may be a test data issue (no outcomes data in the test database) or an application bug (query returning no results despite data existing).

**Recommendation:** Investigate whether outcomes data exists in the test database. If yes, this is a BUG. If no, add test data and re-evaluate.

---

### Accessibility

---

#### IMPROVE-6: Tab order skips fields on client-create form

**Severity:** IMPROVE
**Personas:** DS3 (screen reader), DS4 (voice control -- Dragon NaturallySpeaking)
**Page:** client-create

**What's wrong:** Pressing Tab through the client-create form skips certain fields, forcing keyboard-only and voice control users to use workarounds to reach all form inputs. This breaks the logical tab sequence expected by assistive technology users.

**Recommendation:** Ensure `tabindex` is either absent (natural DOM order) or set correctly. Verify that no fields have `tabindex="-1"` unintentionally.

**Finding Group:** FG-P-6

---

#### IMPROVE-20: Focus ring invisible or low contrast

**Severity:** IMPROVE
**Pages:** Various (form inputs, buttons, links)

**What's wrong:** The keyboard focus indicator (focus ring) is either invisible or has insufficient contrast against the background. WCAG 2.4.7 requires a visible focus indicator. WCAG 2.4.13 (AAA, but good practice) recommends enhanced focus appearance.

**Recommendation:** Apply a consistent, high-contrast focus ring (e.g., 3px solid #005fcc outline with 2px offset) across all interactive elements. Test against both light and dark backgrounds.

**Finding Group:** FG-P-6

---

#### IMPROVE-21: Touch targets below 44x44px

**Severity:** IMPROVE
**Pages:** Various (375x667 mobile breakpoint)

**What's wrong:** Several interactive elements (buttons, links, form controls) are smaller than the 44x44px minimum touch target size recommended by WCAG 2.5.8 (Target Size -- Minimum). This affects mobile users and DS4 (voice control, where precise targeting is difficult with RSI).

**Recommendation:** Ensure all interactive elements are at least 44x44px on mobile, with at least 8px spacing between adjacent targets.

**Finding Group:** FG-P-6

---

#### IMPROVE-22: Groups attendance table missing column headers for screen readers

**Severity:** IMPROVE
**Page:** groups-attendance

**What's wrong:** The attendance table does not use proper `<th>` elements with `scope="col"` for column headers. Screen readers cannot associate data cells with their column meaning, making the table difficult to navigate.

**Recommendation:** Use `<th scope="col">` for column headers and `<th scope="row">` for row headers. Add a `<caption>` element describing the table purpose.

**Finding Group:** FG-P-6

---

#### IMPROVE-23: Data tables not using proper th scope semantics

**Severity:** IMPROVE
**Pages:** Various pages with data tables (client-list, notes-list, groups-list, reports)

**What's wrong:** Multiple data tables throughout the application lack proper `<th scope>` attributes. Screen readers cannot determine which header applies to which data cell, making tabular data navigation unreliable.

**Recommendation:** Audit all `<table>` elements. Ensure every table has `<th scope="col">` for column headers, `<th scope="row">` where applicable, and a `<caption>` or `aria-label` describing the table's purpose.

**Finding Group:** FG-P-6

---

#### IMPROVE-24: Colour-only status indicators lack text labels

**Severity:** IMPROVE
**Pages:** dashboard-staff, client-list

**What's wrong:** Status indicators (e.g., active/inactive, risk levels) use colour alone to convey meaning. Users with colour vision deficiency, and screen reader users, cannot interpret these indicators. WCAG 1.4.1 violation.

**Recommendation:** Add text labels alongside colour indicators (e.g., a green dot with "Active" text). Use `aria-label` for compact layouts where text would not fit visually.

**Finding Group:** FG-P-6

---

#### IMPROVE-25: Skip link not visible when focused

**Severity:** IMPROVE
**Pages:** All pages

**What's wrong:** The skip-to-content link exists (BLOCKER-1 from Round 1 was fixed) but remains visually hidden even when focused. Sighted keyboard users cannot see it, defeating its purpose for that user group. WCAG 2.4.1 requires the link to be operable, and best practice is for it to become visible on focus.

**Recommendation:** Apply CSS that makes the skip link visible when it receives keyboard focus (`:focus` pseudo-class). Position it at the top of the viewport.

**Finding Group:** FG-P-6

---

#### IMPROVE-26: Mobile hamburger menu ARIA label missing or generic

**Severity:** IMPROVE
**Pages:** All pages (375x667 mobile breakpoint)

**What's wrong:** The mobile hamburger menu toggle button either lacks an `aria-label` or uses a generic label like "Menu" without indicating its expanded/collapsed state. Screen reader users cannot determine whether the menu is open or closed.

**Recommendation:** Use `aria-label="Main menu"` with `aria-expanded="true/false"` on the toggle button. Announce state changes to screen readers.

**Finding Group:** FG-P-6

---

### Cognitive Load

---

#### IMPROVE-27: Dashboard shows 8+ metrics simultaneously

**Severity:** IMPROVE
**Persona:** DS1c (Casey Makwa -- ADHD variant) especially
**Page:** dashboard-staff

**What's wrong:** The staff dashboard displays 8 or more metric cards simultaneously with no progressive disclosure. This creates high cognitive load, especially for DS1c who has difficulty filtering competing information. The "wall of numbers" effect makes it hard to identify which metrics need attention.

**Recommendation:** Group metrics into collapsible sections (e.g., "My Caseload," "Upcoming," "Alerts"). Show 3-4 priority metrics by default, with an "Show more" option for secondary metrics.

---

#### IMPROVE-28: Notifications banner competes with task at hand

**Severity:** IMPROVE
**Persona:** DS1c (Casey Makwa -- ADHD variant) especially
**Pages:** Various (wherever notification banners appear)

**What's wrong:** Notification banners appear at the top of the page and persist, competing for attention with the user's current task. For DS1c (ADHD), this creates involuntary attention switching and makes it difficult to maintain focus on the primary workflow.

**Recommendation:** Use a notification badge/count in the navigation (non-intrusive) rather than persistent banners. Allow users to dismiss notifications. Reserve banner-style alerts for urgent items only.

---

#### IMPROVE-29: Plan view shows all sections expanded

**Severity:** IMPROVE
**Page:** plan-view (populated state)

**What's wrong:** The plan view displays all sections and targets expanded simultaneously, creating a very long page. For complex plans with multiple sections, this makes it difficult to get an overview or find a specific section.

**Recommendation:** Show sections collapsed by default with an "Expand All" option. Highlight sections that have recent changes or upcoming deadlines.

---

#### IMPROVE-30: Client detail page has no visual hierarchy between sections

**Severity:** IMPROVE
**Page:** client-detail

**What's wrong:** All sections on the client detail page have equal visual weight. There is no clear hierarchy distinguishing primary information (name, status, program) from secondary details (demographics, contact) from administrative metadata (dates, IDs).

**Recommendation:** Use typographic hierarchy (larger headings for primary info), colour-coded section headers, or card-based layout to create visual grouping. Place the most-used information above the fold.

---

### Consistency

---

#### IMPROVE-31: Button styles inconsistent

**Severity:** COSMETIC
**Pages:** Various

**What's wrong:** Button styling varies across pages -- some pages use filled buttons for primary actions, others use outlined buttons. Destructive actions (delete, remove) do not consistently use a warning colour. Users cannot predict which button is the primary action based on visual styling alone.

**Recommendation:** Establish and enforce a button style guide: filled for primary actions, outlined for secondary, red/warning for destructive actions. Apply consistently across all pages.

---

#### IMPROVE-32: Empty state messages inconsistent

**Severity:** IMPROVE
**Pages:** Various (client-list, notes-list, groups-list, search results)

**What's wrong:** Empty state messages vary in tone, helpfulness, and format. Some pages show "No results," others show "No Participant files yet," and others show nothing at all. The inconsistency makes it unclear whether the empty state is expected or an error.

**Recommendation:** Standardize empty state messages with: (1) a clear statement of what is empty, (2) a suggestion for what to do next, and (3) a call-to-action button where appropriate (e.g., "No notes yet. Create the first note.").

---

## Cosmetic Tickets

Low-priority visual polish items.

---

### COSMETIC-1: Logo blurry at 1920x1080

**Severity:** COSMETIC
**Pages:** All pages (1920x1080 breakpoint)

**What's wrong:** The application logo appears blurry at high-resolution displays, suggesting it is a raster image scaled up rather than an SVG.

**Recommendation:** Replace with an SVG logo or provide a 2x resolution raster version for high-DPI displays.

---

### COSMETIC-2: Card shadow depth inconsistent

**Severity:** COSMETIC
**Pages:** Various (dashboard cards, detail cards)

**What's wrong:** Card components use different shadow depths across pages. Some cards have a subtle shadow, others have a more pronounced one, creating an inconsistent visual depth.

**Recommendation:** Standardize card shadow to a single elevation level across the application.

---

### COSMETIC-3: Footer copyright year shows 2025

**Severity:** COSMETIC
**Pages:** All pages

**What's wrong:** The footer displays "2025" as the copyright year. It is currently 2026.

**Recommendation:** Use a dynamic year (`{% now "Y" %}` in Django templates) to prevent this from recurring annually.

---

### COSMETIC-4: Help page TOC bullets misaligned

**Severity:** COSMETIC
**Page:** public-help

**What's wrong:** The table of contents on the help page has misaligned bullet points, likely a CSS `list-style-position` or `padding-left` issue.

**Recommendation:** Fix CSS for the help page TOC list to align bullets consistently with content text.

---

## Test Infrastructure Tickets

These are not application bugs -- they are issues with the test environment, test data, or test runner that prevent accurate evaluation.

---

### TEST-1: Populated state screenshots missing for some pages

**Severity:** TEST
**Pages:** events-list, reports-export
**Impact:** Cannot evaluate these pages in their populated state. Only default/empty state was captured, which may not represent the typical user experience.

**Recommendation:** Add test data for events and reports. Capture populated state screenshots after seeding the database with representative data.

---

### TEST-2: DS3/DS4/DS1c personas missing from admin screenshots (expected)

**Severity:** TEST (informational -- no action needed)
**Pages:** Admin pages

**What's wrong:** DS3, DS4, and DS1c personas do not appear in admin page screenshots. This is correct behaviour -- these personas have `admin: false` in their permission scope and should not have admin access.

**Action:** No fix needed. Documenting for completeness so future reviewers do not flag this as a gap.

---

### TEST-3: E2 screenshots show staff dashboard instead of executive

**Severity:** TEST
**Persona:** E2 (Kwame Asante)
**Page:** dashboard

**What's wrong:** E2 screenshots show the staff dashboard at `/` instead of the executive dashboard at `/clients/executive/`. Related to BUG-10 -- the test user role may be misconfigured in fixtures.

**Recommendation:** Fix E2 test user role assignment and re-capture all E2 screenshots.

---

### TEST-4: Some 375x667 mobile screenshots cut off

**Severity:** TEST
**Pages:** Various (375x667 breakpoint)
**Impact:** The bottom portion of some mobile pages is not visible in screenshots. Footer content, below-the-fold buttons, and bottom navigation cannot be evaluated.

**Recommendation:** Configure the test runner to capture full-page screenshots (scrolling capture) for mobile breakpoints, or capture multiple viewport-height segments per page.

---

### TEST-5: Client ID=1 used for all client-specific pages

**Severity:** TEST
**Pages:** All client-specific pages (client-detail, notes-list, plan-view, events-list)
**Impact:** Only one client's data is shown across all screenshots. Cannot evaluate how pages behave with different data states (e.g., a client with many notes vs. few, a client with no plan, a client across multiple programs).

**Recommendation:** Add Client ID=2 to the test matrix to capture variation in data density and completeness. Include at least one client with minimal data and one with extensive data.

---

### TEST-6: No error state screenshots captured

**Severity:** TEST
**Pages:** All auditable pages
**Impact:** The page audit only tested default and populated states. Error states (validation failure, 500 error, timeout, network error) were not captured. Cannot evaluate error messaging, recovery paths, or graceful degradation.

**Recommendation:** Add error states to the test matrix:
- Form validation failure (submit with missing required fields)
- 500 server error (simulated)
- Network timeout (simulated slow response)
- Invalid URL parameter (e.g., client ID that does not exist)

---

## Finding Groups

Related findings clustered by shared root cause. Fixing the root cause resolves multiple tickets simultaneously.

| ID | Root Cause | Findings | Fix Scope |
|----|-----------|----------|-----------|
| FG-P-1 | Django i18n not activated | BLOCKER-1 (12+ pages x 2 personas) | Django settings (`MIDDLEWARE`, `LANGUAGE_CODE`), `LocaleMiddleware`, `.po`/`.mo` translation files, `{% trans %}` tags in all templates |
| FG-P-2 | Permission checks missing in templates | PERMISSION-1, PERMISSION-2, PERMISSION-3, PERMISSION-4 | Template `{% if perms %}` guards on edit/create buttons across client-detail, plan-view, groups-detail, groups-list |
| FG-P-3 | Role-based UI filtering incomplete | PERMISSION-5, PERMISSION-6, BUG-1, BUG-10 | View logic + template conditionals + test fixture role assignments. Covers executive vs. staff routing, receptionist create button, and cross-program scoping |
| FG-P-4 | No confirmation dialogs on destructive actions | BUG-3, BUG-6, BUG-7 | JavaScript confirm/modal pattern applied to all destructive buttons (Cancel with content, Remove member, Navigate away from dirty form) |
| FG-P-5 | Form UX patterns incomplete | IMPROVE-1, IMPROVE-2, IMPROVE-3, IMPROVE-4, IMPROVE-5, IMPROVE-7, IMPROVE-8 | Auto-save, validation indicators, character counts, auto-resize text areas, responsive button placement |
| FG-P-6 | Accessibility markup gaps | BUG-5, IMPROVE-6, IMPROVE-16, IMPROVE-20, IMPROVE-21, IMPROVE-22, IMPROVE-23, IMPROVE-24, IMPROVE-25, IMPROVE-26 | ARIA attributes (`aria-label`, `aria-expanded`, `scope`), semantic HTML (`<th>`, `<caption>`, `<nav>`), focus management, touch targets, colour contrast |
| FG-P-7 | Navigation/wayfinding patterns incomplete | IMPROVE-9, IMPROVE-10, IMPROVE-11, IMPROVE-12, IMPROVE-13 | Breadcrumbs, active nav highlighting, consistent back links, client name in page titles, program selector state |

---

## Fix Priority Order

### 1. Fix Immediately (authorization and compliance)

| Priority | Ticket | Why |
|----------|--------|-----|
| 1 | FG-P-2 (PERMISSION-1 through PERMISSION-4) | Over-permission violations. Users can see/initiate actions they are not authorized to perform. Cannot un-expose data. |
| 2 | FG-P-3 (PERMISSION-5, PERMISSION-6) | Mixed over/under-permission. E2 admin access is a security issue; R1/R2-FR missing create blocks intake workflow. |
| 3 | FG-P-1 (BLOCKER-1) | Complete French translation failure. Legal compliance issue (Quebec language laws, PIPEDA informed consent). |
| 4 | BLOCKER-2 | Public registration form 404 -- blocks external intake pathway. |

### 2. Fix Next (functional bugs)

| Priority | Ticket | Why |
|----------|--------|-----|
| 5 | FG-P-4 (BUG-3, BUG-6, BUG-7) | Data loss risk. No confirmation on destructive actions. |
| 6 | BUG-4 | Staff cannot edit own notes -- blocks clinical documentation workflow. |
| 7 | BUG-2 | Generic 403 messages cause confusion and support requests. |
| 8 | BUG-5 | Screen reader users cannot interpret empty metrics. |
| 9 | BUG-9 | UTF-8 encoding issue affecting French names. |

### 3. Fix When Possible (improvements)

| Priority | Ticket | Why |
|----------|--------|-----|
| 10 | FG-P-6 (accessibility markup) | Multiple WCAG compliance items. |
| 11 | FG-P-7 (navigation/wayfinding) | Affects orientation for all personas. |
| 12 | FG-P-5 (form UX) | Quality-of-life improvements for daily workflows. |
| 13 | IMPROVE-27, IMPROVE-28 | Cognitive load reduction for DS1c. |
| 14 | Remaining IMPROVE tickets | Polish and consistency. |

### 4. Low Priority

| Priority | Ticket | Why |
|----------|--------|-----|
| 15 | COSMETIC-1 through COSMETIC-4 | Visual polish only. |
| 16 | TEST-1 through TEST-6 | Test infrastructure. Important for next audit round but not user-facing. |

---

## Verification Scenarios

After fixes are applied, re-run these scenarios to verify:

| Ticket | Primary Verification | Related Scenarios | Cross-Persona Check |
|--------|---------------------|-------------------|---------------------|
| PERMISSION-1 | Page audit: client-detail x PM1 | SCN-035 (PM1 funder reporting) | SCN-015 (DS1 should still see Edit) |
| PERMISSION-2 | Page audit: plan-view x PM1 | SCN-042 (multi-program client) | DS1 plan workflow |
| PERMISSION-3 | Page audit: groups-detail x DS1 | SCN-036 (PM1 programme config) | PM1 should still see Edit |
| PERMISSION-4 | Page audit: groups-list x all staff | SCN-036 | PM1 should still see + New Group |
| PERMISSION-5 | Page audit: dashboard x E2 | SCN-030 (executive dashboard) | E1 executive dashboard |
| PERMISSION-6 | Page audit: client-list x R1 | SCN-010 (receptionist intake) | SCN-025 (R2 intake) |
| BLOCKER-1 | Page audit: all pages x DS2/R2-FR | SCN-040 (bilingual workflow) | DITL-DS2 |
| BLOCKER-2 | Direct URL test: /register/intake/ | N/A | Unauthenticated user |
| BUG-3 | Page audit: notes-create x DS1 | SCN-015 step 3 | DS1c (accidental click risk) |
| BUG-4 | Page audit: notes-detail x DS1 | SCN-015 (note creation/edit) | DS2 own-note edit |
| BUG-7 | Page audit: all forms | SCN-005, SCN-015, SCN-050 | All form-using personas |
