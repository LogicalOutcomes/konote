# Improvement Tickets — 2026-02-13a (Round 5)

**Generated:** 2026-02-13 14:30
**Round:** 5
**Previous active tickets:** BUG-8, BUG-11 (NOT FIXED), BUG-9/BUG-14 (PARTIALLY FIXED)

---

## Previously Filed Tickets — Status Update

### Fixed This Cycle

| Ticket | Description | Fix Date | Verification |
|--------|-------------|----------|-------------|
| TEST-5 | SCN-035 all steps identical | 2026-02-13 | SCN-035 now scores 3.3 (Yellow), PM reporting navigation works |
| TEST-6 | SCN-020 step 2 duplicate | 2026-02-13 | SCN-020 improved from 3.0 → 3.8 (+0.8) |
| TEST-7 | SCN-025 step 2 duplicate | 2026-02-13 | SCN-025 improved from 2.8 → 3.6 (+0.8) |
| TEST-8 | SCN-047 mobile viewport broken | 2026-02-13 | SCN-047 improved from 2.8 → 3.7 (+0.9) |
| TEST-9 | SCN-048 blank offline screenshots | 2026-02-13 | SCN-048 improved from 3.0 → 3.7 (+0.7) |

### Partially Fixed

| Ticket | Description | Status |
|--------|-------------|--------|
| BUG-9 | Language persistence — compliance critical | Most pages fixed; `/reports/insights/` still shows `lang='fr'`. See BUG-14 (carried). |

### Not Fixed (Carried Forward)

| Ticket | Description | Since |
|--------|-------------|-------|
| BUG-8 | French translation gaps (DS2 affected) | Round 2 |
| BUG-11 | French translation gaps (PM2-FR affected) | Round 2b |
| BUG-14 | lang='fr' on /reports/insights/ — WCAG 3.1.1 violation | Round 4 |

---

## New Tickets — BLOCKER

### BLOCKER-1: No loading indicator during HTMX search on slow network

**Severity:** BLOCKER
**Persona:** DS1 (Casey Makwa), R1 (Dana Petrescu)
**Scenario:** SCN-048, Steps 3–4; also affects SCN-045
**Screenshot:** SCN-048_step3_DS1_clients.png

**What's wrong:** When the network is slow, HTMX search requests on /clients/ show no loading indicator. The user types a search query and nothing visibly happens — no spinner, no "Searching…" text, no progress bar. Low-tech-comfort personas (R1) would assume the system is broken and close the tab.

**Where to look:** HTMX `htmx:beforeRequest` / `htmx:afterRequest` event handlers. Add a loading indicator (spinner or "Searching…" text) to the search results container. CSS class `htmx-request` can be used with `htmx-indicator`.

**What "fixed" looks like:** When a search request takes > 300ms, a visible loading indicator appears in the search results area. Indicator disappears when results load.

**Acceptance criteria:**
- [ ] Loading indicator appears for HTMX requests > 300ms on /clients/ search
- [ ] Indicator includes `aria-live="polite"` announcement for screen readers
- [ ] Re-run SCN-048 steps 3–4 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-048/3-4, SCN-045/2, SCN-055/1-2

**Dimension breakdown:**

| Dimension | Score |
|-----------|-------|
| Clarity | 3.5 |
| Efficiency | 3.0 |
| Feedback | 1.5 |
| Error Recovery | 2.0 |
| Accessibility | 2.5 |
| Language | 4.0 |
| Confidence | 2.0 |

---

### BLOCKER-2: /settings/ pages return 404 — PM cannot configure programmes

**Severity:** BLOCKER
**Persona:** PM1 (Morgan Tremblay)
**Scenario:** SCN-036, Step 3; SCN-042, Step 4
**Screenshot:** SCN-036_step3_PM1_settings.png

**What's wrong:** Navigating to `/settings/` returns "Page Not Found" (404). PM1 has `settings: true` and `program.manage: scoped` in her permission scope — she should be able to access programme configuration. This blocks PM workflows for settings and programme management entirely.

**Where to look:** Check if the settings URL is `/settings/`, `/admin/settings/`, or another path. Verify the view exists and is mapped in `urls.py`. If settings is an admin-only page, PM1 needs a separate programme configuration page.

**What "fixed" looks like:** PM1 can access a settings page showing her profile and programme configuration options. Settings she doesn't have permission for are hidden (not shown as disabled or producing 403).

**Acceptance criteria:**
- [ ] PM1 can navigate to settings without 404
- [ ] Programme configuration is accessible to `program.manage: scoped` users
- [ ] Re-run SCN-036 step 3 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-036/3, SCN-042/4, SCN-030/3

---

## New Tickets — BUG

### BUG-15: Executive denied audit log access despite audit.view: allow

**Severity:** BUG — Priority fix
**Persona:** E1 (Margaret Whitfield)
**Scenario:** SCN-075, Step 3
**Screenshot:** SCN-075_step3_E1_audit.png

**What's wrong:** E1 navigated to the audit log page and received a 403 Forbidden response. Per the persona's permission scope, `audit.view: allow` — executives need audit log access for board oversight. This is an under-permission bug: the permission is defined but not enforced correctly.

**Where to look:** `konote-app/apps/auth_app/permissions.py` — check if `audit.view` is mapped to the audit log view. May also be a URL routing issue if the audit log lives at an unexpected path.

**Expected behaviour:** E1 sees the audit log with entries filtered to her programme scope. No individual client names should be visible (aggregate only).

**Acceptance criteria:**
- [ ] E1 can access the audit log page without 403
- [ ] Audit log entries respect programme scope (E1 sees only Housing Support and Youth Services)
- [ ] No individual client PII visible in audit log entries
- [ ] Re-run SCN-075 step 3 — score improves to Green band (4.0+)

**Verification scenarios:** SCN-075/3, SCN-035/4 (PM audit access)

---

### BUG-16: Skip link missing or not first focusable element on /clients/

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-050 Step 2, SCN-052 Step 1
**Screenshot:** SCN-050_step2_DS3_clients.png, SCN-052_step1_DS3_clients-create.png

**What's wrong:** After login, pressing Tab+Enter does not activate a skip-to-content link. In SCN-050, Tab+Enter navigated to the Privacy Policy page. In SCN-052, Tab+Enter navigated to /clients/create/ (the "New Participant" link was the first focusable element). A skip-to-content link must be the FIRST focusable element on every page per WCAG 2.4.1 (Bypass Blocks, Level A).

**Where to look:** Base template (`base.html` or equivalent). Add `<a href="#main-content" class="skip-link">Skip to main content</a>` as the first child of `<body>`. Visually hide it until focused.

**What "fixed" looks like:** Tab from top of any page focuses a "Skip to main content" link. Enter activates it and moves focus to the `#main-content` landmark.

**Acceptance criteria:**
- [ ] Skip link is the first focusable element on every page
- [ ] Skip link is visually hidden until focused (`.sr-only:focus-within` pattern)
- [ ] Activating skip link moves focus to `<main>` or `#main-content`
- [ ] Verified with JAWS and NVDA
- [ ] Re-run SCN-050 step 2, SCN-052 step 1 — score improves to Green band (4.0+)

**WCAG:** 2.4.1 Bypass Blocks (Level A) — FAIL

**Verification scenarios:** SCN-050/2, SCN-052/1, SCN-065/1

---

### BUG-17: Form validation errors — no role="alert", no aria-errormessage

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-061 Steps 1–2
**Screenshot:** SCN-061_step1_DS3_clients-create.png

**What's wrong:** Form validation errors rely entirely on browser-native `required` attribute tooltips. There is no `role="alert"` container, no `aria-errormessage` attribute on invalid fields, and no error summary component. Browser-native validation tooltips are inconsistent for screen readers — JAWS may or may not announce them depending on version and browser.

**Where to look:** Create form templates (participant create, note create, etc.). Add custom validation with:
1. An error summary `<div role="alert">` at the top of the form listing all errors
2. `aria-invalid="true"` on each invalid field
3. `aria-errormessage` pointing to per-field error descriptions
4. Focus moves to the error summary on submit

**What "fixed" looks like:** When a form is submitted with validation errors, focus moves to an error summary that lists all errors with links to the invalid fields. Screen readers announce the errors immediately.

**Acceptance criteria:**
- [ ] Error summary with `role="alert"` appears on validation failure
- [ ] Each invalid field has `aria-invalid="true"` and `aria-errormessage`
- [ ] Focus moves to error summary on failed submission
- [ ] JAWS/NVDA announce errors without relying on browser tooltips
- [ ] Re-run SCN-061 steps 1–2 — score improves to Green band (4.0+)

**WCAG:** 3.3.1 Error Identification (Level A), 3.3.3 Error Suggestion (Level AA)

**Verification scenarios:** SCN-061/1-2, SCN-053/2, SCN-050/4

---

### BUG-18: Tab order on /clients/ places filters before search field

**Severity:** BUG — Priority fix
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-055 Steps 1–2
**Screenshot:** SCN-055_step1_DS3_clients.png

**What's wrong:** On /clients/, pressing Tab twice from the top of the page (after skip link is fixed) lands on the Status filter dropdown, not the search field. Keyboard and screen reader users doing quick client lookups must Tab past multiple filter controls to reach search. The search field is the most-used element on this page for all persona types.

**Where to look:** Template for the client list page. Move the search `<input>` before the filter controls in the DOM order, or use `tabindex="1"` (less preferred — breaks natural flow).

**What "fixed" looks like:** After activating the skip link, the next Tab press focuses the search field. Filters come after search in tab order.

**Acceptance criteria:**
- [ ] Search field is focusable before filter controls on /clients/
- [ ] Tab order matches visual order (search → filters → results list)
- [ ] Re-run SCN-055 steps 1–2 — score improves to Yellow band (3.0+) minimum

**Verification scenarios:** SCN-055/1-2, SCN-062/1, SCN-065/1

---

### BUG-19: htmx:syntax:error (x10) in console on form pages

**Severity:** BUG — Review recommended
**Persona:** All personas visiting create forms
**Scenario:** SCN-053 Steps 1–2, SCN-052 Step 1, SCN-010 Step 3
**Screenshot:** Multiple console .log files

**What's wrong:** Every page with a create form produces 10+ `htmx:syntax:error` console errors and an "Autofocus processing was blocked" warning. While these don't visibly break the page, they indicate malformed HTMX attributes that may affect dynamic content updates and ARIA live region announcements.

**Where to look:** Inspect HTMX attributes (`hx-get`, `hx-post`, `hx-swap`, etc.) on create form templates. Common causes: missing closing quotes, invalid selectors in `hx-target`, or HTMX processing elements that were already processed.

**Acceptance criteria:**
- [ ] No `htmx:syntax:error` in console on any create form page
- [ ] Autofocus works without being blocked
- [ ] HTMX content swaps function correctly on form pages

**Verification scenarios:** SCN-010/3, SCN-053/1-2, SCN-020/3

---

### BUG-20: "Admin" dropdown visible to E2 despite user.manage: deny

**Severity:** BUG — Investigate
**Persona:** E2 (Kwame Asante)
**Scenario:** SCN-076, Step 2
**Screenshot:** SCN-076_step2_E2_dashboard.png

**What's wrong:** The navigation sidebar shows an "Admin" dropdown menu item for E2. Per E2's permission scope, `user.manage: deny`, `settings.manage: deny`, `program.manage: deny` — E2 should not see admin-related navigation items.

**Investigation needed:** Verify whether clicking the Admin dropdown links produces 403 errors (under-permission) or actually grants access (over-permission). If over-permission, escalate to PERMISSION-1.

**Where to look:** Navigation template — check role-based visibility conditions for the Admin menu item.

**Acceptance criteria:**
- [ ] Admin menu item hidden for users with `user.manage: deny`
- [ ] If Admin links are needed for audit.view, rename the navigation item to "Audit Log" and scope accordingly
- [ ] Re-run SCN-076 step 2 — no Admin dropdown visible

**Verification scenarios:** SCN-076/2, SCN-075/2

---

### BUG-21: E1 sees only 1 programme (expected 2)

**Severity:** BUG — Review recommended
**Persona:** E1 (Margaret Whitfield)
**Scenario:** SCN-075, Step 2
**Screenshot:** SCN-075_step2_E1_dashboard.png

**What's wrong:** E1's dashboard shows data for only 1 programme, but her permission scope defines access to both "Housing Support" and "Youth Services". E2 (same role) correctly sees both programmes.

**Where to look:** Check programme assignment for the `executive` test user account. May be a test data setup issue rather than an app bug.

**Acceptance criteria:**
- [ ] E1 test user has both programmes assigned
- [ ] Dashboard shows aggregate data for both programmes
- [ ] Re-run SCN-075 step 2 — both programmes visible

**Verification scenarios:** SCN-075/2, SCN-030/1

---

### BUG-22: Touch targets may be under WCAG 2.5.8 minimum

**Severity:** BUG — Review recommended
**Persona:** DS1 (Casey Makwa, tablet)
**Scenario:** SCN-057 Steps 1–4
**Screenshot:** SCN-057_step4_DS1_clients-create.png

**What's wrong:** Checkboxes on the create form appear to be default browser size (approximately 13×13px), likely under WCAG 2.5.8's 24×24px minimum target size. Input field heights and filter toggle buttons on /clients/ also need measurement.

**Where to look:** Global CSS for `input[type="checkbox"]`, `input[type="radio"]`, and filter toggle buttons. Apply `min-width: 24px; min-height: 24px;` or use custom checkbox styles with adequate touch area.

**Acceptance criteria:**
- [ ] All interactive elements meet WCAG 2.5.8 minimum (24×24px)
- [ ] Checkboxes and radio buttons have visible, adequately sized touch targets
- [ ] Verified at 1024×768 tablet viewport

**WCAG:** 2.5.8 Target Size (Minimum) (Level AA)

**Verification scenarios:** SCN-057/1-4

---

### BUG-23: Form Tab order differs after validation error

**Severity:** BUG — Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-061, Step 2
**Screenshot:** SCN-061_step2_DS3_clients-create.png

**What's wrong:** After a validation error moves focus to the First Name field and the user types then Tabs, subsequent fields do not follow the expected order. "Thompson" (intended for Last Name) ended up in the Preferred Name field. This suggests the Tab order changes after browser-native validation fires, or the form's autofocus logic interferes with the natural tab sequence.

**Where to look:** Create form template. Check if `autofocus` attribute or JavaScript focus management changes the tab order after validation. Verify DOM order of form fields matches visual order.

**Acceptance criteria:**
- [ ] Tab order is identical before and after validation error
- [ ] Tab sequence: First Name → Last Name → Preferred Name → ...
- [ ] Re-run SCN-061 step 2 — data lands in correct fields

**Verification scenarios:** SCN-061/2, SCN-053/2

---

## New Tickets — IMPROVE

### IMPROVE-8: Post-login focus placement — confirm focus on meaningful element

**Severity:** IMPROVE — Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-051, Step 2

After login, verify focus lands on a meaningful element (the page's `<h1>` or first interactive element), not on `<body>`. Cannot verify from screenshots alone — needs real screen reader testing.

**Acceptance criteria:**
- [ ] Post-login focus is on a meaningful element (h1 or first interactive)
- [ ] Verified with JAWS or NVDA

---

### IMPROVE-9: Form submission should announce success via aria-live

**Severity:** IMPROVE — Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-053, Step 2

After successful form submission (create participant, create note), an `aria-live="polite"` region should announce the success (e.g., "Participant created successfully"). Currently no confirmation is announced to screen readers.

**Acceptance criteria:**
- [ ] Success message announced via aria-live after form submission
- [ ] Focus moves to the newly created record or a confirmation message

---

### IMPROVE-10: Add aria-live region for search results on /clients/

**Severity:** IMPROVE — Review recommended
**Persona:** DS3 (Amara Osei)
**Scenario:** SCN-055, SCN-062

When HTMX swaps search results on /clients/, an `aria-live="polite"` region should announce the result count (e.g., "3 participants found" or "No results found"). This is WCAG 4.1.3 (Status Messages, Level AA).

**WCAG:** 4.1.3 Status Messages (Level AA)

**Acceptance criteria:**
- [ ] aria-live region announces search result count after HTMX swap
- [ ] Announcement is concise and uses `aria-live="polite"` (not "assertive")

---

### IMPROVE-11: 403 denial page should suggest alternatives

**Severity:** IMPROVE — Review recommended
**Persona:** DS3 (Amara Osei), R2 (Omar Hussain)
**Scenario:** SCN-064 Step 3

The 403 "You don't have access to this page" message provides no guidance. Add a suggestion like "To change your profile, go to [Profile Settings]" or "Contact your program manager for access." Especially important for screen reader users who cannot visually scan for alternatives.

**Acceptance criteria:**
- [ ] 403 page includes at least one actionable suggestion or link
- [ ] Suggestion is role-appropriate (different text for different permission levels)

---

### IMPROVE-12: Dashboard cognitive load evaluation for ADHD users

**Severity:** IMPROVE — Review recommended
**Persona:** DS1c (Casey Makwa, ADHD inattentive)
**Scenario:** SCN-058 Step 1

Evaluate whether the dashboard has more than 5–6 distinct information blocks competing for attention. DS1c's threshold for overwhelm is lower than typical users. Step 1 appeared calm but needs detailed evaluation with real users. Consider a "focus mode" or simplified dashboard view.

**Acceptance criteria:**
- [ ] Dashboard information blocks counted and documented
- [ ] If > 6 blocks, consider progressive disclosure or collapsible sections

---

## Test Infrastructure Issues

### TEST-10: SCN-059 uses wrong login URL — all 6 steps return 404

**Type:** Test infrastructure — BLOCKER priority
**Scenario:** SCN-059 (Voice control — DS4/Riley)
**Reason:** Scenario YAML uses `goto: "/accounts/login/"` but KoNote2's login URL is `/auth/login/`. All 6 steps return 404. Zero evaluable data for the only voice control scenario.

**Fix in:** `scenarios/accessibility/SCN-059.yaml` — change URL to `/auth/login/`
**Priority:** Fix before next round — DS4 has 0% coverage

---

### TEST-11: SCN-054 unresolved {jane_doe_id} template variable

**Type:** Test infrastructure — High priority
**Scenario:** SCN-054 (Tab panel ARIA — DS3)
**Reason:** `goto: "/clients/{jane_doe_id}/"` — template variable not resolved by test runner. Both steps show 404.

**Fix in:** Either create Jane Doe in test data seeding with a known ID, or change scenario to navigate via search instead of direct URL.

---

### TEST-12: SCN-063/064 use /dashboard/ URL — returns 404

**Type:** Test infrastructure — High priority
**Scenario:** SCN-063 Step 1, SCN-064 Step 1
**Reason:** `/dashboard/` is not a valid URL. The dashboard is likely at `/` or the post-login landing page.

**Fix in:** Update scenario YAMLs to use correct dashboard URL.

---

### TEST-13: SCN-065 uses hardcoded /clients/1/ — returns 404

**Type:** Test infrastructure — High priority
**Scenario:** SCN-065 Step 2
**Reason:** Hardcoded `/clients/1/` does not exist. Client record focus test could not execute.

**Fix in:** Replace with valid client ID from test data, or navigate via search.

---

### TEST-14: SCN-062 needs 8 prerequisite clients for fatigue test

**Type:** Test infrastructure — High priority
**Scenario:** SCN-062 (ARIA live region fatigue — DS3)
**Reason:** The 8-client lookup test requires Alice Martin, Bob Garcia, Carol Nguyen, David Okafor, Elena Petrov, Frank Yamamoto, Grace Ibrahim, Henry Lavoie. None exist in test data.

**Fix in:** Test data seeding (conftest or fixture).

---

### TEST-15: Language carryover — test runner doesn't reset between scenarios

**Type:** Test infrastructure — Medium priority
**Scenario:** SCN-056 Steps 2–4, SCN-058 Step 6
**Reason:** Language switches to French during test execution and persists into subsequent scenarios where the persona expects English. The test runner must reset `Accept-Language` header and language cookie/session before each scenario.

**Fix in:** Test runner (conftest `setup` method) — add language reset step.

---

### TEST-16: SCN-050 Tab counts need recalibration

**Type:** Test infrastructure — Medium priority
**Scenario:** SCN-050 Steps 3–7
**Reason:** The scenario specifies Tab counts that don't match the actual form field layout. Data was typed into wrong fields. Tab sequence needs to be re-counted and updated in the YAML.

**Fix in:** `scenarios/accessibility/SCN-050.yaml`

---

### TEST-17: SCN-058 notification bell selector doesn't match

**Type:** Test infrastructure — High priority
**Scenario:** SCN-058 Step 2
**Reason:** CSS selectors `[data-testid='notification-bell'], .notification-icon, a[href*='notification']` match nothing on the dashboard. Either notifications are not implemented or selectors need updating.

**Fix in:** Update selectors or mark step as `screenshot_expected: false` if notifications are not yet built.

---

### TEST-18: SCN-058 clients link selector matches wrong element

**Type:** Test infrastructure — High priority
**Scenario:** SCN-058 Step 3
**Reason:** `a[href*='clients']` matches "New Participant" link instead of "Clients" navigation link. Casey navigated to /clients/create/ instead of /clients/.

**Fix in:** Use more specific selector: `nav a[href='/clients/']` or `a[href='/clients/'][data-nav]`.

---

### TEST-19: SCN-046 shared device privacy test entirely blocked

**Type:** Test infrastructure — Medium priority
**Scenario:** SCN-046 (all steps)
**Reason:** The shared device/session privacy test could not execute. Requires multi-session testing capability not available in current test runner.

**Fix in:** Test runner needs session management for multi-user scenarios. Consider manual testing until automated multi-session is available.

---

### TEST-20: URL template variables unresolved across multiple scenarios

**Type:** Test infrastructure — High priority
**Scenario:** SCN-010, SCN-015, SCN-054, SCN-065 and others
**Reason:** Template variables like `{client_id}`, `{alert_id}`, `{jane_doe_id}` in scenario YAMLs are not resolved by the test runner. Steps navigate to URLs like `/clients/{client_id}/` which return 404.

**Fix in:** Test runner needs a template variable resolution step before navigation. Either:
1. Replace variables with known test data IDs at runtime
2. Use a lookup step (search for client by name, extract ID from URL)
3. Pre-populate a variable map in the test fixture

---

## Finding Groups

| Group | Root Cause | Primary Ticket | Also Affects |
|-------|-----------|----------------|-------------|
| FG-S-1 | Skip link / tab order on /clients/ | BUG-16 | BUG-18, SCN-050/2, SCN-052/1, SCN-055/1-2, SCN-065/1 |
| FG-S-2 | Language carryover / persistence | BUG-14 (carried) | BUG-8, BUG-11, TEST-15, SCN-056/2-4, SCN-058/6 |
| FG-S-3 | ARIA live region gaps | BUG-17 | IMPROVE-9, IMPROVE-10, SCN-055, SCN-061, SCN-062 |
| FG-S-4 | URL template variables unresolved | TEST-20 | TEST-11, TEST-12, TEST-13, SCN-010, SCN-015, SCN-054, SCN-065 |
| FG-S-5 | htmx:syntax:error on forms | BUG-19 | SCN-053, SCN-052, SCN-010, SCN-020 |
| FG-S-6 | Executive permission/visibility gaps | BUG-15 | BUG-20, BUG-21, SCN-075, SCN-076 |

---

## Items NOT Filed as Tickets (Probable Test Artefacts)

- **Language scores of 1.0 on SCN-056/058:** Caused by TEST-15 (language carryover), not by the app itself. App's French translation is generally excellent where it loads correctly.
- **SCN-058 steps 3–6 navigation failures:** Caused by TEST-18 (wrong CSS selector), not by cognitive accessibility issues in the app.
- **SCN-062 search failures:** Same Tab-order-to-search issue as SCN-055 (BUG-18). Not a separate bug — resolved by fixing BUG-18.

---

## Priority Order

### Critical (fix before next round)

1. **BUG-16** — Skip link missing (WCAG 2.4.1 Level A violation). Affects ALL keyboard/screen reader scenarios.
2. **BLOCKER-1** — No HTMX loading indicator. User confidence killer on slow networks.
3. **BLOCKER-2** — /settings/ returns 404. Blocks PM programme management entirely.
4. **BUG-15** — Executive denied audit log. Under-permission bug, board oversight blocked.
5. **TEST-10** — SCN-059 wrong URL. Unblocks DS4/Riley (voice control) — currently 0% coverage.

### High priority

6. **BUG-17** — Form validation errors, no role="alert" (WCAG 3.3.1).
7. **BUG-18** — Tab order on /clients/ — filters before search.
8. **BUG-14** (carried) — lang='fr' on /reports/insights/ (WCAG 3.1.1).
9. **TEST-20** — URL template variable resolution (unblocks many scenarios).
10. **TEST-17/18** — SCN-058 selectors (unblocks ADHD evaluation).

### Medium priority

11. **BUG-20** — Admin dropdown visibility for executives.
12. **BUG-23** — Tab order after validation error.
13. **BUG-22** — Touch target sizing (WCAG 2.5.8).
14. **BUG-19** — htmx:syntax:error in console.
15. **BUG-8/11** (carried) — French translation gaps.

### Lower priority

16. **BUG-21** — E1 programme count mismatch (may be test data).
17. **IMPROVE-8 through IMPROVE-12** — Accessibility enhancements.
18. **TEST-11 through TEST-19** — Test infrastructure improvements.

---

## Recommendations for Round 6

1. Fix BUG-16 (skip link) — single fix improves ALL keyboard/screen reader scenarios
2. Fix BLOCKER-1 and BLOCKER-2 — two fixes remove both blockers
3. Fix TEST-10 — one YAML change unblocks DS4 (voice control, currently 0% coverage)
4. Fix TEST-20 (URL template resolution) — unblocks 4+ scenarios
5. Verify BUG-14 is fully resolved (check all pages, not just /clients/)
6. Add `aria-live="polite"` regions for HTMX content swaps (BUG-17, IMPROVE-9, IMPROVE-10)
7. Target 95% coverage (currently 91%) by fixing remaining TEST tickets
