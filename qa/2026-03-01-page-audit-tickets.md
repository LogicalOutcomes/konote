# KoNote2 Page Audit Tickets — Round 4

**Date:** 2026-03-01
**Round:** 4
**Pages audited:** 12
**Report:** `2026-03-01-page-audit-report.md`
**Total tickets:** 15 (1 PERMISSION, 4 BLOCKER, 5 BUG, 3 IMPROVE, 2 TEST)

---

## Status of Previous Page Audit Tickets (Round 3)

| Ticket | Status | Notes |
|--------|--------|-------|
| BLOCKER-P-1 (surveys 404) | NOT FIXED | Not re-tested — surveys deferred |
| BLOCKER-P-2 (client-surveys 404) | NOT FIXED | Not re-tested |
| BLOCKER-P-3 (public-survey-link 500) | NOT FIXED | Not re-tested |
| **BLOCKER-P-4 (public-unsubscribe 500)** | **NOT FIXED** | **Regression confirmed — new BLOCKER-P-7** |
| BLOCKER-P-5 (404 page FR) | NOT EVALUABLE | Not in this round's selection |
| BLOCKER-P-6 (comm-leave-message FR) | NOT EVALUABLE | Not in this round's selection |
| BUG-P-1 (plan-goal-create "Target") | PARTIALLY FIXED | plan-view still uses "Target" — see BUG-P-9 |
| BUG-P-2 through P-8 | NOT EVALUABLE | Different pages this round |
| TEST-P-3 (custom 500 template) | **NOT FIXED** | Still raw Django 500 — see BLOCKER-P-8 |

---

## PERMISSION Tickets (1)

### PERMISSION-P-1: E2 (Kwame Asante) sees Admin nav dropdown despite admin:false

**Severity:** BLOCKER (authorization violation — over-permission)
**Persona:** E2 (Kwame Asante, Director of Programs)
**Page:** dashboard-executive (and likely all pages for E2)

**Violation type:** page_access (UI layer)

**What's wrong:** E2's navigation bar shows an "Admin" dropdown between "Reports" and "Kwame Asante". E2's permission_scope specifies `admin: false`. E1 (Eva Executive, same executive role family, also `admin: false`) does NOT see this dropdown on the same page. This is an E2-specific configuration error that exposes administrative functionality to an unauthorized user. Even if the backend blocks actual admin actions, the nav item reveals that admin features exist and invites exploration.

**Expected behaviour:** E2's navigation should match E1's: Dashboard, Programs, Insights, Reports, [user menu], Francais. No Admin dropdown.

**Compliance references:** PIPEDA Principle 4.7 (safeguards appropriate to sensitivity of information)

**Where to look:**
1. `konote-app/apps/auth_app/` — check how nav items are rendered per role. E2 may have a role flag or group membership that includes admin nav visibility.
2. Django template for navigation bar — check the conditional logic that shows/hides "Admin".
3. Check if E2's test user has been accidentally assigned to an admin group.

**Acceptance criteria:**
- [ ] E2 navigation does not show "Admin" dropdown
- [ ] E2 navigation matches E1 navigation (Dashboard, Programs, Insights, Reports, user menu)
- [ ] Clicking any admin URL as E2 returns 403 (verify backend enforcement)
- [ ] Re-audit dashboard-executive E2 — no Admin dropdown visible

**Screenshot references:**
- `dashboard-executive-E2-populated-1366x768.png` (Admin visible — incorrect)
- `dashboard-executive-E1-populated-1366x768.png` (no Admin — correct, for comparison)

---

## BLOCKER Tickets (4)

### BLOCKER-P-7: public-unsubscribe still returns raw Django 500 (CASL regression)

**Severity:** BLOCKER
**Persona:** unauthenticated (email recipient)
**Page:** public-unsubscribe (`/communications/unsubscribe/<token>/`)
**Heuristic:** H01, H06, H10
**Pass:** heuristic
**Screenshot:** public-unsubscribe-unauthenticated-default-1366x768.png

**What's wrong:** The CASL-required email unsubscribe page STILL returns a raw Django 500 error: "A server error occurred. Please contact the administrator." This was filed as BLOCKER-P-4 in Round 3 (2026-02-21) and has not been fixed. Under Canada's Anti-Spam Legislation (CASL, S.C. 2010, c. 23, s. 6(2)(c)), every commercial electronic message must include a working unsubscribe mechanism. A non-functional unsubscribe page means the agency is sending emails without providing the legally required opt-out.

**Regression from:** BLOCKER-P-4 (Round 3, 2026-02-21)

**Where to look:**
1. `konote-app/apps/communications/views.py` — the view handling `/communications/unsubscribe/<str:token>/` is raising an unhandled exception
2. `konote-app/templates/500.html` — still missing or not styled (TEST-P-3 from Round 3 also not fixed)
3. Check Django error logs for the stack trace

**What "fixed" looks like:**
1. Unsubscribe page loads with KoNote branding
2. Shows: "You are unsubscribing from communications from [agency]. Click 'Unsubscribe' to confirm."
3. After clicking: "You have been unsubscribed."
4. Bilingual (EN/FR), styled, works on mobile
5. Invalid/expired tokens show a styled error page (not 500)

**Acceptance criteria:**
- [ ] `/communications/unsubscribe/<valid_token>/` loads the unsubscribe confirmation
- [ ] Clicking "Unsubscribe" withdraws consent and shows confirmation
- [ ] Invalid token shows styled "link expired" (not 500)
- [ ] Page is bilingual (EN/FR)
- [ ] Works on mobile (375x667)
- [ ] CASL: unsubscribe takes effect within 10 business days
- [ ] Re-audit at Green band (4.0+)

**Verification scenarios:** All public-unsubscribe screenshots, SCN scenarios involving unsubscribe

**Dimension breakdown (unauthenticated):**

| Dimension | Score |
|-----------|-------|
| Clarity | 1.0 |
| Efficiency | 1.0 |
| Feedback | 1.0 |
| Error Recovery | 1.0 |
| Accessibility | 1.5 |
| Language | 1.0 |
| Confidence | 1.0 |

**Finding group:** FG-P-13

---

### BLOCKER-P-8: export-confirmation returns raw Django 500 server error

**Severity:** BLOCKER
**Persona:** PM1 (Morgan Tremblay)
**Page:** export-confirmation (`/exports/confirm/<token>/`)
**Heuristic:** H01, H10
**Pass:** heuristic
**Screenshot:** export-confirmation-PM1-default-1366x768.png

**What's wrong:** The export confirmation page (new in page-inventory v2.2) returns a raw Django 500 error: "A server error occurred. Please contact the administrator." No KoNote branding, no styling, no recovery path. Morgan has just exported client data and needs to confirm the download — instead she sees a developer error page. This is a data access workflow failure: the export may or may not have been generated, and Morgan has no way to know.

**Where to look:**
1. `konote-app/` — check if the exports app and its views exist. This may be a premature page-inventory entry (feature not yet built).
2. If the view exists, check Django error logs for the stack trace.
3. `konote-app/templates/500.html` — same missing custom template as BLOCKER-P-7.

**What "fixed" looks like:** Page shows export details (what was exported, when, format), a download link, and expiration notice.

**Acceptance criteria:**
- [ ] `/exports/confirm/<valid_token>/` renders the export confirmation page
- [ ] Shows export details and download link
- [ ] Invalid/expired token shows styled error (not 500)
- [ ] Custom 500 page exists as fallback
- [ ] Re-audit at Green band (4.0+)

**Dimension breakdown (PM1):**

| Dimension | Score |
|-----------|-------|
| Clarity | 1.0 |
| Efficiency | 1.0 |
| Feedback | 1.0 |
| Error Recovery | 1.0 |
| Accessibility | 1.5 |
| Language | 1.0 |
| Confidence | 1.0 |

**Finding group:** FG-P-13

---

### BLOCKER-P-9: Three new v2.2 pages return 404 — features not deployed

**Severity:** BLOCKER
**Personas:** PM1 (Morgan Tremblay), admin (Priya Sharma)
**Pages:** client-export, admin-backup-settings, admin-export-links
**Heuristic:** H01
**Pass:** heuristic
**Screenshots:**
- `client-export-PM1-default-1366x768.png`
- `admin-backup-settings-admin-default-1366x768.png`
- `admin-export-links-admin-default-1366x768.png`

**What's wrong:** Three pages added to page-inventory v2.2 (2026-03-01) all return 404 "Page Not Found." The KoNote-branded 404 page is well-designed (clear heading, helpful suggestions, Go Back/Home buttons), but the features simply do not exist in the application yet.

- **client-export** (`/participants/<id>/export/`): PM1 needs to export individual client data for PIPEDA data portability requests. 404 means she cannot fulfil a legal obligation.
- **admin-backup-settings** (`/admin/backup/`): Priya needs to configure backup and export settings. 404 means she cannot manage data retention.
- **admin-export-links** (`/admin/export-links/`): Priya needs to manage secure export download links. 404 means she cannot control data distribution.

**Note:** This follows the same pattern as FG-P-7 (surveys 404 in Round 3) — the page inventory was updated before the feature code was deployed.

**Where to look:** `konote-app/` — check if URL patterns are registered for these paths. The features may need to be built or the page-inventory entry reverted until deployment.

**What "fixed" looks like:** Each URL renders its intended page with full functionality.

**Acceptance criteria:**
- [ ] `/participants/<id>/export/` renders client export interface for PM1
- [ ] `/admin/backup/` renders backup settings for admin
- [ ] `/admin/export-links/` renders export link management for admin
- [ ] Re-audit all 3 pages at Green band (4.0+)

**Dimension breakdown (representative — all three pages identical):**

| Dimension | Score |
|-----------|-------|
| Clarity | 2.0 |
| Efficiency | 1.0 |
| Feedback | 1.0 |
| Error Recovery | 1.5 |
| Accessibility | 2.0 |
| Language | 1.0 |
| Confidence | 1.0 |

**Finding group:** FG-P-12

---

### BLOCKER-P-10: Systemic French localisation failure on 5 additional pages

**Severity:** BLOCKER (bilingual compliance)
**Personas:** R2-FR (Amelie Tremblay), DS2 (Jean-Luc Bergeron)
**Pages:** dashboard-staff, client-detail, notes-create, plan-view, reports-insights
**Heuristic:** H05 (Terminology — Q4, Q5)
**Pass:** heuristic (systemic early-exit after 3 consecutive failures)
**Screenshots (representative):**
- `dashboard-staff-R2-FR-populated-1366x768.png`
- `client-detail-R2-FR-default-1366x768.png`
- `notes-create-DS2-default-1366x768.png`
- `plan-view-DS2-populated-1366x768.png`
- `reports-insights-DS2-populated-1366x768.png`

**What's wrong:** Every element on all 5 pages is in English for French-preference users: page headings, form labels, buttons, navigation bar, footer links, helper text, error messages, placeholder text. This was first identified in Round 1 (BUG-14), escalated to BLOCKER in Round 3 (BLOCKER-P-5, P-6), and is now confirmed on 5 additional pages. The pattern is clear: French localisation has NOT been implemented across the application.

**Specifically confirmed in English for R2-FR on dashboard-staff:**
- "Welcome to KoNote! Need help getting started?"
- "Search Participants", "Name or ID..."
- "+ New Participant", "View All"
- "Your Front Desk Tools" section
- "Pick up where you left off"
- Navigation: "Participants", "Programs", "Front Desk"
- Footer: "Powered by KoNote", "GitHub", "Privacy", "Help"

**Compliance references:** Official Languages Act (for federally funded agencies), AODA (Ontario), agency bilingual service commitments

**Where to look:**
1. `konote-app/` — check if Django's `{% trans %}` / `{% blocktrans %}` tags are used in ANY template
2. Check if `.po` translation files exist for French (`locale/fr/LC_MESSAGES/django.po`)
3. Check Django `settings.py` — is `USE_I18N = True`? Is French in `LANGUAGES`?
4. Check if the language preference is being read from the user profile and applied via `translation.activate()`

**What "fixed" looks like:** All UI text displays in French when the user's language preference is French. Navigation, headings, labels, buttons, helper text, error messages, footer — everything.

**Acceptance criteria:**
- [ ] All 5 pages fully translated for French-preference users
- [ ] Navigation bar in French (Participants → Participants, Programs → Programmes, etc.)
- [ ] Form labels and buttons in French
- [ ] Footer links in French
- [ ] Re-audit R2-FR and DS2 on all 5 pages — Language dimension 4.0+

**Verification scenarios:** All scenarios involving R2-FR, DS2, PM2-FR

**Finding group:** FG-P-9 (continued from Round 1, cross-references FG-S-1 from scenario evaluation)

---

## BUG Tickets (5)

### BUG-P-9: plan-view "Actions" button text renders vertically (CSS overflow)

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey Makwa), DS3 (Amara Osei, screen reader)
**Page:** plan-view (`/plans/client/1/`) — populated state
**Heuristic:** H08 (Accessibility), H10 (Aesthetic Coherence)
**Pass:** heuristic
**Screenshot:** plan-view-DS1-populated-1366x768.png

**What's wrong:** On the populated plan-view for staff with edit permissions (DS1), an "Actions" element on the right side of the goal table renders its text vertically — "A c t i o n s" stacked letter-by-letter down the right margin. This appears to be a column or row-action button that is too narrow to display "Actions" horizontally, causing CSS text overflow. For DS3 (JAWS screen reader), this would be announced as individual characters ("A", "c", "t", "i", "o", "n", "s") — nonsensical. For DS4 (voice control), the target is unusable. PM1 does NOT see this bug because `plan.edit: deny` means no inline row actions are rendered.

**Where to look:** `konote-app/apps/plans/templates/plans/plan_view.html` — check the CSS for the row-level "Actions" button/column. Likely needs `min-width`, `white-space: nowrap`, or the column needs a fixed width.

**What "fixed" looks like:** "Actions" button renders horizontally as a normal dropdown, matching the top-right "Actions" dropdown style.

**Acceptance criteria:**
- [ ] "Actions" text renders horizontally in the goal table
- [ ] Button is clickable and opens a dropdown menu
- [ ] Screen reader announces "Actions" as a single word
- [ ] Voice control can target "Actions" button
- [ ] Re-audit DS1 plan-view — Accessibility dimension improves to 4.0+

**Finding group:** FG-P-11

---

### BUG-P-10: notes-create form has no autosave indicator

**Severity:** BUG — Priority fix
**Persona:** DS1 (Casey Makwa, iPad, between appointments), DS1c (ADHD)
**Page:** notes-create (`/notes/client/1/create/`)
**Heuristic:** H06 (Error Prevention — Q1), H07 (Feedback — Q2)
**Pass:** heuristic
**Screenshot:** notes-create-DS1-default-1366x768.png

**What's wrong:** The notes-create form is long (7+ sections spanning the full viewport) with a single "Save Note" button at the bottom. There is no autosave indicator, no draft status, and no warning about unsaved changes. DS1 (iPad, between appointments) risks losing an entire session note if she loses connectivity, accidentally navigates away, or the browser tab closes. DS1c (ADHD) may context-switch away and forget to save. The form collects critical clinical data — losing it means re-doing the note from memory, which degrades documentation quality.

**Where to look:** `konote-app/apps/notes/templates/notes/create.html` and associated JavaScript. Consider adding:
1. A visible "Draft saved" / "Saving..." indicator
2. `beforeunload` event listener to warn on navigation away with unsaved changes
3. Periodic autosave to localStorage or server draft endpoint

**What "fixed" looks like:** A visible draft indicator near the "Save Note" button: "Draft saved at 2:45 PM" or "Unsaved changes". Navigation away triggers "You have unsaved changes" browser prompt.

**Acceptance criteria:**
- [ ] Unsaved changes trigger a browser warning on navigation away
- [ ] Autosave indicator visible (or at minimum, "unsaved changes" warning)
- [ ] Re-audit DS1 notes-create — Error Recovery dimension improves to 3.5+

---

### BUG-P-11: reports-funder audit trail fields shown to executives

**Severity:** BUG — Priority fix
**Persona:** E1 (Eva Executive), E2 (Kwame Asante)
**Page:** reports-funder (`/reports/funder-report/`)
**Heuristic:** H05 (Terminology — Q2), H02 (Information Hierarchy)
**Pass:** heuristic
**Screenshot:** reports-funder-E1-populated-1366x768.png

**What's wrong:** The funder report form requires "Who is receiving this data?" and "Reason" fields (marked "Required for audit purposes"). These are appropriate for PM1 (who knows the specific recipient and reason) but create friction for executives. E1 (ED, board reporting) and E2 (Director of Programs) typically delegate report generation to program managers. When an executive does generate a report (e.g., for a board meeting), they may not know the specific recipient or may find the audit fields bureaucratic. The fields are not wrong — they're just role-inappropriate for executives who have `report.funder_report: allow`.

**Where to look:** `konote-app/apps/reports/templates/reports/funder_report.html` — consider making audit fields optional for executive roles, or pre-filling with "Board / Executive review" as a default.

**What "fixed" looks like:** For executive users, audit fields are either pre-filled with sensible defaults or marked optional with a note: "For board-level review, these fields are optional."

**Acceptance criteria:**
- [ ] Executive users can generate reports without audit trail friction
- [ ] Audit trail is still captured (via defaults or optional fields)
- [ ] PM1 experience is unchanged (audit fields remain required)
- [ ] Re-audit E1 reports-funder — Efficiency dimension improves to 3.5+

---

### BUG-P-12: notes-create and plan-view use "Target" instead of "Goal"

**Severity:** BUG — Priority fix
**Persona:** DS1b (Casey Makwa, first week)
**Pages:** notes-create, plan-view
**Heuristic:** H05 (Terminology — Q1, Q3)
**Pass:** heuristic
**Screenshots:** notes-create-DS1-default-1366x768.png, plan-view-DS1-populated-1366x768.png

**What's wrong:** The plan-view page uses "Target" as a column header and button label ("Add a Target", "Add Target"). The notes-create form says "Which Targets did you work on?" and "0 of 0 targets." However, scenario descriptions, help documentation, and the plan-goal-create page (partially fixed per BUG-P-1 from Round 3) use "Goal." DS1b (first week, no training) encounters three different terms for the same concept across related pages.

**Note:** This continues FG-P-11 from Round 3. BUG-P-1 addressed the plan-goal-create heading, but the terminology inconsistency persists across plan-view and notes-create.

**Where to look:**
1. `konote-app/apps/plans/templates/plans/plan_view.html` — change "Target" column header and button text to "Goal"
2. `konote-app/apps/notes/templates/notes/create.html` — change "Targets" section heading and checkbox labels
3. Search codebase for "target" (case-insensitive) to find all instances

**What "fixed" looks like:** Consistent use of "Goal" across plan-view, notes-create, and plan-goal-create.

**Acceptance criteria:**
- [ ] plan-view column header says "Goal" (not "Target")
- [ ] plan-view buttons say "Add a Goal" / "Add Goal"
- [ ] notes-create section says "Which Goals did you work on?"
- [ ] notes-create counter says "0 of 0 goals"
- [ ] All pages use "Goal" consistently
- [ ] French translation uses "Objectif" (not "Cible") for consistency

**Finding group:** FG-P-11

---

### BUG-P-13: notes-create form overwhelming for DS1c (ADHD) and DS3 (screen reader)

**Severity:** BUG — Priority fix
**Persona:** DS1c (ADHD), DS3 (Amara Osei, screen reader), DS1b (first week)
**Page:** notes-create
**Heuristic:** H02 (Information Hierarchy), H08 (Accessibility — Q4)
**Pass:** first_impression
**Screenshot:** notes-create-DS1c-default-1366x768.png

**What's wrong:** The notes-create form has 7+ sections visible simultaneously: Template/Interaction/Date row, Duration/Modality row, Target checkboxes, Targets detail section (working relationship check-in, engagement), Follow-up buttons. There is no visual separation between required and optional fields, no collapsible sections, and no progress indicator. For DS1c (ADHD), the cognitive load is high — she loses focus partway through. For DS3 (screen reader), the many form fields create excessive tab stops with no skip-navigation landmarks. For DS1b (first week), there is no guidance about which fields are required.

**Where to look:** `konote-app/apps/notes/templates/notes/create.html` — consider:
1. Collapsible sections for optional fields (working relationship check-in, engagement, follow-up)
2. Required-field indicators (asterisk or "(required)" labels)
3. Landmark headings (`<h2>`, `<h3>`) for screen reader skip-navigation
4. A brief intro for first-time users

**What "fixed" looks like:** Clear required vs optional visual distinction. Optional sections collapsed by default. Landmark headings for screen reader navigation.

**Acceptance criteria:**
- [ ] Required fields visually marked (asterisk or "(required)")
- [ ] `aria-required="true"` on required form elements
- [ ] Section headings use proper heading levels for skip-navigation
- [ ] Optional sections collapsible or clearly separated
- [ ] Re-audit DS1c — Clarity dimension improves to 3.5+
- [ ] Re-audit DS3 — Accessibility dimension improves to 3.5+

---

## IMPROVE Tickets (3)

### IMPROVE-P-5: notes-create should show step/progress indicator

**Severity:** IMPROVE — Review recommended
**Persona:** DS1c (ADHD), DS1b (first week)
**Page:** notes-create
**Heuristic:** H03 (Navigation Context)

**Recommendation:** Add a progress indicator showing which sections have been completed. For DS1c, this provides external structure to compensate for attention drift. For DS1b, it shows how much is left. Example: a sidebar checklist or top progress bar showing "Template [done] > Details [current] > Targets > Follow-up > Review."

---

### IMPROVE-P-6: reports-insights should show sample/preview before query

**Severity:** IMPROVE — Review recommended
**Persona:** PM1, E1, E2
**Page:** reports-insights
**Heuristic:** H01 (First Impression), H07 (Feedback)

**Recommendation:** The pre-query form shows only "Program" and "Time period" dropdowns with a "Show Insights" button. New users have no idea what insights will look like. Add a sample/preview below the form (e.g., a faded mock-up or "Here's what you'll see: participant progress trends, outcome achievement rates, feedback themes") to set expectations and encourage use.

---

### IMPROVE-P-7: dashboard-executive design pattern should be replicated

**Severity:** IMPROVE — Review recommended (positive finding)
**Persona:** E1, E2
**Page:** dashboard-executive

**Recommendation:** The executive dashboard is the best-designed page evaluated in 4 rounds of auditing. Specific patterns worth replicating:
1. **Privacy notice integrated into design** — "This dashboard shows overall numbers — individual participant records are kept private" as a subtitle, not a warning banner
2. **Small-cell suppression** — "Percentages hidden (fewer than 5 active participants)" with a clear explanation
3. **Data quality indicator** — "Data: Low" badge shows data confidence level
4. **Delegation guidance** — "Need More Details? For detailed reports, reach out to the Program Manager for that program" at the bottom
5. **No PII leakage** — aggregate counts only, no names visible

These patterns should be the standard for all reporting and dashboard pages.

---

## Finding Groups

| Group | Root Cause | Primary Ticket | Also Affects |
|-------|-----------|---------------|-------------|
| FG-P-9 | French localisation not implemented (systemic, from Round 1) | BLOCKER-P-10 | dashboard-staff (R2-FR, DS2), client-detail (R2-FR, DS2), notes-create (DS2), plan-view (DS2), reports-insights (DS2). Cross-method: FG-S-1 |
| FG-P-11 | "Target" vs "Goal" terminology inconsistency (continued from Round 3) | BUG-P-12 | BUG-P-9 (plan-view Actions column header). Round 3: BUG-P-1 (plan-goal-create) |
| FG-P-12 | New v2.2 pages not deployed (page-inventory updated before code) | BLOCKER-P-9 | client-export (PM1), admin-backup-settings (admin), admin-export-links (admin). Same pattern as FG-P-7 (surveys) |
| FG-P-13 | Missing custom 500 error template + unhandled exceptions on public pages | BLOCKER-P-7 | BLOCKER-P-8 (export-confirmation). Continued from Round 3 FG-P-8. TEST-P-3 (Round 3) also not fixed |
| FG-P-14 | Populated state screenshots show pre-query content (test data not seeded) | TEST-P-4 | reports-insights (all 9 personas) |
| FG-P-15 | E2 Admin nav visible despite admin:false | PERMISSION-P-1 | dashboard-executive E2 (may affect all E2 pages) |

---

## Test Infrastructure Tickets (2)

### TEST-P-4: reports-insights "populated" state shows pre-query form only

**Type:** Test infrastructure (not an app bug)
**Page:** reports-insights
**Personas affected:** All 9 (DS1, DS1b, DS1c, DS2, DS3, DS4, PM1, E1, E2)
**Reason:** All "populated" state screenshots show only the pre-query form (Program dropdown, Time period dropdown, "Show Insights" button) with no actual insights data. The test runner did not select a program and click "Show Insights" before capturing the populated state. This means we cannot evaluate the insights display, data visualization, or outcome presentation.

**Fix in:** konote-app test runner — select a program, click "Show Insights", wait for data to render, then capture the populated state.
**Priority:** Fix before next round — this page was specifically selected for reporting evaluation and cannot be properly scored.

---

### TEST-P-5: page-inventory v2.2 entries should be gated on feature deployment

**Type:** Test infrastructure (process issue)
**Pages:** client-export, export-confirmation, admin-backup-settings, admin-export-links
**Reason:** Four pages were added to page-inventory v2.2 (2026-03-01) before the feature code was deployed to the test environment. This is the same pattern as Round 3's FG-P-7 (surveys). Each premature entry generates a BLOCKER ticket that consumes evaluation time on pages that were never expected to work.

**Fix in:** page-inventory update process — only add pages to the inventory after confirming the feature is deployed and returning 200 in the test environment. Consider adding a `status: planned | deployed | deprecated` field to page-inventory entries.
**Priority:** Process improvement — prevents wasted evaluation effort in future rounds.

---

## Items NOT Filed as Tickets

1. **KoNote's 404 page is well-designed.** The three 404 pages (client-export, admin-backup-settings, admin-export-links) all render KoNote's custom 404 template with clear heading, helpful suggestions, Go Back/Home buttons, and consistent styling. The 404 page design is not the problem — the missing features are.

2. **plan-view PM1 view-only mode is excellent.** The banner "View only — you can see this plan because this Participant is on your caseload, but editing requires a staff role in one of their enrolled Programs. Contact your administrator if you need edit access." is clear, helpful, and correctly scoped. This is the gold standard for permission-limited views.

3. **dashboard-executive privacy subtitle is exemplary.** "This dashboard shows overall numbers — individual participant records are kept private" integrated as a subtitle (not a warning) is exactly the right approach. No PII visible anywhere.

4. **notes-create breadcrumb navigation is good.** "Home > Participants > Jane Doe > Notes > New Note" provides clear context. Not filing a ticket because this is working correctly.

5. **reports-funder "Draft Template — Customise for Your Needs" banner is helpful.** The warning that this is a generic template and funders may require different formats is appropriate and well-positioned.

6. **dashboard-staff "Data: Low" badges on program cards** (visible on executive dashboard too) are a good data quality signal. They set expectations about the reliability of the numbers shown.
