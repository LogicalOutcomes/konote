# KoNote2 Page Audit — Improvement Tickets (2026-02-13)

**Date:** 2026-02-13
**Source:** Page audit Round 2 (12-page rotating sample)
**Ticket numbering:** Page audit uses PERMISSION-P-N, BUG-P-N, IMPROVE-P-N
**Finding group prefix:** FG-P-N (page audit findings)

---

## Summary

| Category | Count | Severity |
|----------|-------|----------|
| Permission violations | 2 | 1 BLOCKER (over-permission), 1 systemic BUG (under-permission) |
| Bugs | 10 | BUG |
| Improvements | 18 | IMPROVE |
| **Total new findings** | **30** | |
| **Finding groups** | **6** | |

---

## Previous Ticket Status Update

| Ticket | Description | Previous Status | Current Status |
|--------|-------------|-----------------|----------------|
| PERMISSION-1 | PM1 sees Edit buttons on client-detail | BLOCKER | **STILL NOT FIXED** |
| PERMISSION-2 | PM1 sees 9 edit/add controls on plan-view | BLOCKER | **RESOLVED** |
| PERMISSION-3-6 | Various template permission guards | Mixed | Not re-checked this round |
| BUG-14 | French i18n not activated | BUG (systemic) | **STILL NOT FIXED** |
| BUG-20 | E2 Admin dropdown visible | Under investigation | **CONFIRMED — BLOCKER** |
| BLOCKER-1 (09c) | French translation failure | BLOCKER | **STILL NOT FIXED** |
| BLOCKER-2 (09c) | Public registration 404 | BLOCKER | Not re-checked this round |

---

## PERMISSION Tickets

### PERMISSION-P-1: E2 sees Admin dropdown in navigation

**Severity:** BLOCKER (authorization violation — over-permission)
**Persona:** E2 (Kwame Asante, Director of Programs)
**Pages affected:** All pages E2 can access (confirmed on dashboard-executive, reports-insights)
**Heuristic:** H04 (Controls and Actions)
**Pass:** Heuristic audit

**Violation type:** action_scope

**What's wrong:** The top navigation bar shows an "Admin" dropdown with chevron for E2, who has `admin: false` and `user.manage: deny`. E1 (identical permission scope) does NOT see this menu. E2 is also missing the "Audit Log" nav item despite `audit.view: allow`.

**Expected behaviour:** E2's nav should match E1's: Dashboard, Programs, Insights, Reports, Audit Log. No Admin dropdown.

**Compliance references:** PIPEDA 4.7, AODA (consistent interface)

**Where to look:** Django base template nav rendering logic. Check conditional for Admin menu visibility — may use a different permission key than `user.manage`. Also check E2 test user's database role.

**Acceptance criteria:**
- [ ] E2 does not see Admin dropdown in navigation
- [ ] E2 sees Audit Log nav item (audit.view: allow)
- [ ] E1 and E2 see identical nav items (same permission scope = same nav)
- [ ] Re-run page capture for E2 on dashboard-executive and reports-insights

**Screenshot references:** `dashboard-executive-E2-populated-1366x768.png`, `reports-insights-E2-populated-1366x768.png`
**Cross-reference:** BUG-20 (2026-02-13a satisfaction report), BUG-P-1 below
**Finding group:** FG-P-1

---

### PERMISSION-P-2: PM1 sees Edit buttons on client-detail (STILL NOT FIXED)

**Severity:** BLOCKER (authorization violation — over-permission)
**Persona:** PM1 (Morgan Tremblay, Program Manager)
**Page:** client-detail (/clients/1/)
**Heuristic:** H04 (Controls and Actions)
**Pass:** Heuristic audit

**Violation type:** action_scope

**What's wrong:** Edit button and wrench "Edit" button beside "Additional Details" are visible. PM1 has `client.edit: deny`. These controls should be hidden via template-level permission checks.

**Expected behaviour:** PM1 sees client detail in read-only mode with no Edit buttons.

**Compliance references:** PIPEDA 4.7

**Where to look:** Client detail template — add `{% if perms.client.edit %}` guard around edit controls.

**Acceptance criteria:**
- [ ] PM1 sees client detail page with no Edit buttons
- [ ] Edit button still appears for DS1 (staff with edit permission)
- [ ] Re-run page audit for client-detail × PM1

**Screenshot reference:** `client-detail-PM1-default-1366x768.png`
**Original ticket:** PERMISSION-1 (2026-02-09c page audit)
**Finding group:** FG-P-2

---

## BUG Tickets

### BUG-P-1: E2 missing Audit Log nav item despite audit.view: allow

**Severity:** BUG — Priority fix
**Persona:** E2 (Kwame Asante)
**Pages affected:** All pages
**Heuristic:** H03 (Navigation Context)
**Pass:** Heuristic audit

**What's wrong:** E2's navigation bar is missing the "Audit Log" link, despite `audit.view: allow` in the permission scope. E1 (identical permission scope) DOES see the Audit Log link. This is an under-permission issue — E2 cannot access a feature they should have.

**Where to look:** Same nav rendering logic as PERMISSION-P-1. The Admin dropdown may be replacing the Audit Log link.

**Acceptance criteria:**
- [ ] E2 sees "Audit Log" in navigation
- [ ] Audit Log link leads to /admin/audit/ and returns 200

**Finding group:** FG-P-1

---

### BUG-P-2: French accent stripping in display name

**Severity:** BUG — Priority fix
**Persona:** R2-FR (Amélie Tremblay)
**Pages affected:** All pages (nav bar, footer)
**Heuristic:** H05 (Terminology)
**Pass:** Heuristic audit

**What's wrong:** "Amélie Tremblay" displays as "Amelie Tremblay" without the accent aigu on the first 'e'. This is a character encoding issue in the user profile or authentication system.

**Where to look:** User model, authentication pipeline, template rendering. Check database encoding (UTF-8) and that templates render `{{ user.display_name }}` without stripping diacritics.

**Acceptance criteria:**
- [ ] Display name shows "Amélie Tremblay" with correct accent
- [ ] All diacritics preserved across nav, footer, profile page

---

### BUG-P-3: Receptionist personas missing "New Participant" button

**Severity:** BUG — Priority fix (systemic)
**Personas:** R1 (Dana Petrescu), R2 (Omar Hussain), R2-FR (Amélie Tremblay)
**Pages affected:** dashboard-staff (/), client-list (/clients/)
**Heuristic:** H04 (Controls and Actions)
**Pass:** Heuristic audit

**What's wrong:** No "New Participant" button is visible on either the dashboard or client list for receptionist personas, despite `client.create: allow` in their permission scope. Staff roles (DS1, DS2, etc.) see the button prominently. This blocks walk-in intake workflow.

**Expected behaviour:** Receptionists should see a "New Participant" button on the dashboard and client list, identical to the staff view.

**Where to look:** Dashboard template and client-list template. The button visibility is likely gated on role name ("staff") rather than the `client.create` permission.

**Acceptance criteria:**
- [ ] R1 sees "+ New Participant" button on dashboard
- [ ] R1 sees "+ New Participant" button on client list
- [ ] R2-FR sees the same button (in French: "+ Nouveau participant")

**Finding group:** FG-P-4

---

### BUG-P-4: French i18n failure on client-create form

**Severity:** BUG — Priority fix
**Persona:** DS2 (Jean-Luc Bergeron)
**Page:** client-create (/clients/create/)
**Heuristic:** H05 (Terminology)
**Pass:** Heuristic audit

**What's wrong:** The entire intake form — heading, all field labels, placeholders, and both action buttons — renders in English despite DS2's language preference being French. This is a fundamental i18n failure.

**Cross-reference:** BUG-14 (systemic French localization failure). This is the same root cause applied to a specific high-impact page (intake form).

**Acceptance criteria:**
- [ ] Client create form renders in French when language preference is `fr`
- [ ] All labels, placeholders, buttons, and validation messages are translated

**Finding group:** FG-P-3

---

### BUG-P-5: No required-field indicators on notes-create

**Severity:** BUG — Priority fix
**Personas:** DS1 (Casey), DS1c (ADHD), DS4 (Riley)
**Page:** notes-create (/notes/client/1/new/)
**Heuristic:** H06 (Error Prevention)
**Pass:** Heuristic audit

**What's wrong:** The note creation form has no asterisks, "(required)" labels, or other indicators marking which fields must be filled in. Users cannot tell what is required before submission. If the form rejects due to a missing field, DS4 (RSI) must re-dictate and DS1c (ADHD) loses attention momentum.

**Where to look:** Note creation template. Add `required` HTML attribute with visible asterisk/legend styling.

**Acceptance criteria:**
- [ ] Required fields marked with asterisks and a "* Required" legend
- [ ] Optional fields labelled "(optional)" for clarity
- [ ] Re-run page capture — required indicators visible

**Finding group:** FG-P-5

---

### BUG-P-6: No auto-save or unsaved-changes protection on notes-create

**Severity:** BUG — Priority fix
**Personas:** DS1 (Casey), DS1c (ADHD)
**Page:** notes-create (/notes/client/1/new/)
**Heuristic:** H07 (Feedback)
**Pass:** Heuristic audit

**What's wrong:** No auto-save indicator, no unsaved-changes warning, no "Draft saved" heartbeat. Casey's #1 frustration: "Losing a note because the session expired." DS1c's task-switching cost means an interruption + data loss = abandoned task.

**Where to look:** Note creation view. Options: (a) periodic auto-save to draft, (b) `beforeunload` warning, (c) localStorage backup.

**Acceptance criteria:**
- [ ] Visible "Draft saved" indicator appears after auto-save
- [ ] Navigating away with unsaved changes shows confirmation prompt
- [ ] Session timeout preserves draft content

**Finding group:** FG-P-5

---

### BUG-P-7: Misleading "View only" banner on plan-view

**Severity:** BUG
**Persona:** PM1 (Morgan Tremblay)
**Page:** plan-view (/plans/client/1/)
**Heuristic:** H04 (Controls and Actions)
**Pass:** Heuristic audit

**What's wrong:** The "View only" banner reads: "View only — to edit this plan, you must be assigned to a Program this Participant is enrolled in." Morgan IS assigned to Housing Support — she manages it. The real reason is `plan.edit: deny` on her role. The message should reference role permissions.

**Acceptance criteria:**
- [ ] Banner text accurately explains the read-only reason (role-based, not programme-based)

---

### BUG-P-8: Help page has no French translation

**Severity:** BUG — Priority fix
**Personas:** DS2 (Jean-Luc), R2-FR (Amélie)
**Page:** public-help (/help/)
**Heuristic:** H05 (Terminology)
**Pass:** Heuristic audit

**What's wrong:** The help page is entirely in English for French-preference users. No translated headings, section content, or tab labels.

**Compliance references:** Official Languages Act, Quebec Charter of the French Language

**Where to look:** Help page template and content. Check if i18n framework covers the help page.

**Acceptance criteria:**
- [ ] Help page renders in French when user language is `fr`
- [ ] All section headings, body text, and navigation tabs are translated

**Finding group:** FG-P-3

---

### BUG-P-9: No active navigation indicator for groups-list page

**Severity:** BUG
**Personas:** DS1, DS3, PM1
**Page:** groups-list (/groups/)
**Heuristic:** H03 (Navigation Context)
**Pass:** Heuristic audit

**What's wrong:** No top-nav item shows an active/underline state when on /groups/. Users cannot confirm via the nav bar that they are on the correct page.

**Where to look:** Nav template — check URL pattern matching for the groups page active state.

**Acceptance criteria:**
- [ ] A nav item is highlighted/active when viewing /groups/

**Finding group:** FG-P-6

---

### BUG-P-10: Nav highlight shows "Audit Log" active on erasure-requests page

**Severity:** BUG
**Persona:** PM1 (Morgan Tremblay)
**Page:** admin-erasure-requests (/erasure/)
**Heuristic:** H03 (Navigation Context)
**Pass:** Heuristic audit

**What's wrong:** The "Audit Log" nav item is highlighted/active when viewing the Erasure Requests page. Morgan might think she is on the wrong page.

**Where to look:** Nav template — check URL prefix matching. The /erasure/ URL may match the Audit Log nav item's URL prefix.

**Acceptance criteria:**
- [ ] Nav active state correctly reflects the erasure requests page

**Finding group:** FG-P-6

---

### BUG-P-11: Duplicate link text on plan-view (WCAG 2.4.4)

**Severity:** BUG
**Persona:** DS3 (Amara Osei, screen reader)
**Page:** plan-view (/plans/client/1/)
**Heuristic:** H08 (Accessibility)
**Pass:** Heuristic audit

**What's wrong:** "Edit" appears at both section level and target level. "Status" appears at both levels. JAWS "list all links" shows ambiguous entries. Violates WCAG 2.4.4 (Link Purpose in Context).

**Where to look:** Plan-view template. Add `aria-label` to disambiguate (e.g., `aria-label="Edit Mental Health Goals section"` vs `aria-label="Edit Reduce depression symptoms target"`).

**Acceptance criteria:**
- [ ] All "Edit" and "Status" links have unique `aria-label` attributes
- [ ] JAWS "list all links" shows disambiguated link text
- [ ] Verified with DS3 (screen reader) persona

---

### BUG-P-12: Dashboard cognitive overload for ADHD persona

**Severity:** BUG
**Persona:** DS1c (Casey Makwa, ADHD)
**Page:** dashboard-staff (/)
**Heuristic:** H08 (Accessibility — cognitive)
**Pass:** Heuristic audit

**What's wrong:** The dashboard presents 9+ distinct information blocks competing for attention, exceeding DS1c's documented 5-6 block threshold. ALL-CAPS stat card labels create visual "shouting." The urgent safety alert is buried below informational stat cards.

**Acceptance criteria:**
- [ ] Stat card labels use sentence case (not ALL-CAPS)
- [ ] Safety alerts promoted above or beside stat cards
- [ ] Information density reduced to ≤6 distinct visual blocks

---

## IMPROVE Tickets (Summary)

| ID | Page | Persona(s) | Finding |
|----|------|-----------|---------|
| IMPROVE-P-1 | dashboard-staff | DS1 | Dual primary actions — search box should visually dominate over "+ New Participant" |
| IMPROVE-P-2 | dashboard-staff | DS1c | Promote safety alerts above stat cards |
| IMPROVE-P-3 | dashboard-staff | R1 | Add role context text to sparse receptionist dashboard |
| IMPROVE-P-4 | dashboard-staff | DS3 | Code audit: heading hierarchy, landmarks, skip-nav, ARIA on stat cards |
| IMPROVE-P-5 | client-list | R1 | Restyle "Clear filters" button as outlined (looks destructive) |
| IMPROVE-P-6 | client-list | DS3, DS4 | Verify filter dropdowns are native `<select>` (not custom JS) |
| IMPROVE-P-7 | client-list | DS4 | Verify search field accessible name matches visible label (WCAG 2.5.3) |
| IMPROVE-P-8 | notes-create | DS1c | Add progressive disclosure or stepper for 9+ form fields |
| IMPROVE-P-9 | notes-create | DS1, DS1c | Sticky footer overlaps form content during scroll |
| IMPROVE-P-10 | notes-create | DS4 | Calendar icon buttons lack visible text labels for Dragon |
| IMPROVE-P-11 | plan-view | DS1, DS3, PM1 | Add breadcrumbs to client record pages |
| IMPROVE-P-12 | groups-list | All | Members column shows blank — display count (even "0") |
| IMPROVE-P-13 | groups-list | PM1 | Add oversight metadata: facilitator, last session, next session |
| IMPROVE-P-14 | reports-insights | PM1 | Pre-select user's primary program in filter dropdown |
| IMPROVE-P-15 | reports-insights | E1 | Add empty-state guidance text below "Show Insights" button |
| IMPROVE-P-16 | public-help | R1 | Scope help content by role — receptionist sees only relevant sections |
| IMPROVE-P-17 | public-help | All | Add search/filter to help page to reduce information overload |
| IMPROVE-P-18 | admin-erasure | Admin, PM1 | Add breadcrumbs: Admin > Erasure Requests |

---

## Finding Groups

| Group | Root Cause | Primary Ticket | Also Affects |
|-------|-----------|---------------|-------------|
| FG-P-1 | Nav rendering not matching permission scope for E2 | PERMISSION-P-1 | BUG-P-1 (missing Audit Log) |
| FG-P-2 | Template-level permission guards missing on client-detail | PERMISSION-P-2 | — |
| FG-P-3 | French i18n not activated / language preference not applied | BUG-14 (scenario) | BUG-P-4, BUG-P-8, all DS2/R2-FR pages |
| FG-P-4 | Receptionist role UI omits create button despite permission | BUG-P-3 | dashboard-staff, client-list |
| FG-P-5 | notes-create form lacks defensive UX | BUG-P-5, BUG-P-6 | DS1, DS1c, DS4 |
| FG-P-6 | Nav active-state URL matching inaccurate | BUG-P-9, BUG-P-10 | groups-list, admin-erasure |

---

## Items NOT Filed as Tickets (Probable Test Artefacts)

| Finding | Reason Not Ticketed |
|---------|-------------------|
| "LogicalOutcomes" branding in dashboard body | Likely production branding vs. "KoNote" nav logo — cosmetic only |
| "Record ID" column shows "—" | Test data artefact — column likely populated in production |
| Search placeholder truncated on mobile | Cosmetic — "Search by na..." readable enough |
| Engagement dropdown default "----------" | Cosmetic — minor placeholder issue |
| DS3 stat card semantics (dl/dt/dd) | Needs code verification — filed as IMPROVE-P-4 |
