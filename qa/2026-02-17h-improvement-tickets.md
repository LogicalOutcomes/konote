# Improvement Tickets -- 2026-02-17h

**Round:** Round 6 (Full Evaluation)
**Date:** 2026-02-17
**Source report:** `reports/2026-02-17h-satisfaction-report.md`

---

## Status Table (Previous Tickets from Round 5 / 2026-02-17f)

| Ticket | Description | Status |
|--------|-------------|--------|
| PERMISSION-1 | PM blocked from plan templates admin | NOT FIXED |
| PERMISSION-2 | PM blocked from note templates admin | NOT FIXED |
| PERMISSION-3 | PM blocked from event types admin | NOT FIXED |
| PERMISSION-4 | Executive blocked from audit log | NOT TESTED (no screenshot) |
| BLOCKER-1 | Funder reporting URL 404 | PARTIALLY FIXED (SCN-086 shows working funder template page at different URL) |
| BUG-1 | PM admin entirely gated behind admin-only access | NOT FIXED |
| BUG-14 | Language persistence on /reports/insights/ | NOT FIXED (CAL-005 confirms) |
| IMPROVE-1 | Permission denial pages should distinguish admin-only from scope-boundary | NOT FIXED |
| IMPROVE-2 | Admin denied page should include link back to own programme | NOT FIXED |

---

## PERMISSION Tickets (Authorization Violations -- Always BLOCKER)

### PERMISSION-5: Receptionist can access meetings page despite denied permissions

**Severity:** BLOCKER (over-permission -- authorization violation)
**Persona:** R1 (Dana Petrescu, Receptionist)
**Scenario:** SCN-085, Step 1

**Violation type:** page_access (over-permission)

**What's wrong:** Dana navigates to `/events/meetings/` and the page loads successfully, showing "My Meetings" with upcoming/recent meeting counts. The receptionist role has `meetings: false` and `meeting.view: deny` in her permission scope. The page should return a 403 or redirect to the dashboard.

**Why it matters:** Over-permission violations are more serious than under-permission because they expose data the persona shouldn't see. While the meetings page itself shows no sensitive data (0 upcoming, 0 recent), the principle of least privilege requires that role boundaries be enforced server-side. If meetings are ever scheduled, Dana would see them.

**Expected behaviour:** /events/meetings/ should return 403 "You don't have permission to view this page" or redirect to the receptionist dashboard. The nav bar correctly omits "Meetings" for R1 -- only the direct URL access is unguarded.

**Compliance references:** PIPEDA 4.7 (safeguards principle). AODA: no direct impact but permission enforcement is part of role-appropriate interfaces.

**Where to look:** The view for `/events/meetings/` likely lacks a permission check for `meeting.view`. The nav bar correctly hides the link (R1's nav shows only Participants, Programs) but the server-side view doesn't verify the permission. Check `konote-app/apps/events/views.py` or equivalent.

**Acceptance criteria:**
- [ ] R1 gets 403 or redirect when accessing /events/meetings/ directly
- [ ] R1's nav bar continues to hide Meetings link (already working)
- [ ] PM1 and DS1 can still access /events/meetings/ (their roles allow it)
- [ ] Re-run SCN-085 step 1 -- R1 sees permission denial page

**Verification scenarios:** SCN-085/1

**Screenshot reference:** SCN-085_step1_R1_events-meetings.png

---

## BLOCKER Tickets (Red Band, Score 1.0-1.9)

_No new BLOCKER tickets this round. Previous BLOCKER-1 (funder URL) partially fixed._

---

## BUG Tickets (Orange Band, Score 2.0-2.9)

### BUG-24: Language regression on group create page

**Severity:** BUG -- Priority fix
**Persona:** PM1 (Morgan Tremblay, English-preferring)
**Scenario:** SCN-076, Step 1
**Screenshot:** SCN-076_step1_PM1_groups-create.png

**What's wrong:** The entire group create page (`/groups/create/`) renders in French for Morgan Manager, who prefers English. All labels, buttons, nav items, and footer are in French: "Ajouter Groupe", "Quel type de groupe est-ce?", "Creer Groupe", "Annuler". The nav shows "Participant(e)s", "Reunions", "Messages", "Programmes", "Analyses", "Rapports", "Approbations", "Gerer les". This is a **regression** -- SCN-076 scored 3.4 in Round 5 (English).

**Related to:** BUG-9 (language persistence, Round 2b) and BUG-14 (language on /reports/insights/, Round 4). The language persistence bug appears to be worsening -- now affecting more pages.

**Where to look:** The session language state for the manager user. The test runner may be inheriting a French session from a previous persona's login, or the `/groups/create/` page may not respect the user's language preference. Check `konote-app/apps/auth_app/` for language middleware and session handling.

**What "fixed" looks like:** Morgan sees the group create page in English. Language preference is respected per-user, not per-session.

**Acceptance criteria:**
- [ ] PM1 sees /groups/create/ in English
- [ ] Language toggle shows "Francais" (option to switch), confirming English is active
- [ ] Nav items in English: Participants, Meetings, Messages, Programs, Insights, Reports, Approvals, Manage
- [ ] Re-run SCN-076 -- score returns to Yellow band (3.4+)

**Dimension breakdown:**

| Dimension | Score |
|-----------|-------|
| Clarity | 2.5 |
| Efficiency | 3.0 |
| Feedback | 2.5 |
| Error Recovery | 3.0 |
| Accessibility | 3.0 |
| Language | 1.5 |
| Confidence | 2.0 |

**Verification scenarios:** SCN-076/1

---

## IMPROVE Tickets (Yellow Band Suggestions)

### IMPROVE-8: Alert text not translated in French interface

**Severity:** IMPROVE -- Review recommended
**Persona:** DS2 (Jean-Luc Bergeron, French)
**Scenario:** DITL-DS2, Step 1
**Screenshot:** DITL-DS2_step1_DS2_home.png

**What's wrong:** On Jean-Luc's French-language dashboard, the alert text reads "Safety concern noted" in English while all other UI elements are in French ("Alertes actives", "Elements prioritaires", "Pas de notes recentes", etc.). The alert description should be translated to French.

**Suggested improvement:** Alert descriptions should follow the user's language preference. If the alert was created in English, show a French translation or at minimum flag that the content is in a different language.

**Acceptance criteria:**
- [ ] Alert descriptions display in the user's selected language
- [ ] If untranslatable (user-generated content), show a language indicator

**Verification scenarios:** DITL-DS2/1

---

## Finding Groups (Shared Root Causes)

### FG-1: Language persistence / session contamination

**Affected tickets:** BUG-24, BUG-14 (from R4), BUG-9 (from R2b), IMPROVE-8
**Affected scenarios:** SCN-076, CAL-005, SCN-045, SCN-075, SCN-010 (steps 3-6), DITL-DS2
**Root cause:** Language preference is not reliably bound to the user account. When the test runner switches between personas (French then English), the language state from the previous session bleeds into the next. This may also affect real multi-user environments where staff share a workstation.

**Pattern:** Scenarios captured later in the test run are more likely to show French for English users, suggesting session state accumulation.

### FG-2: /admin/ URL namespace blocks PM self-service

**Affected tickets:** PERMISSION-1, -2, -3, BUG-1 (all from R5/17f)
**Root cause:** All management pages (plan templates, note templates, event types) are under `/admin/` which has a blanket admin-only gate. PM role has scoped management permissions but can't reach the pages.

---

## Test Infrastructure Issues

### TEST-21: Mass 404s from old /clients/ URLs

**Severity:** TEST -- Critical (blocks 14 scenarios)
**Affected scenarios:** SCN-010, 015, 020, 025, 030, 035, 045, 053, 054, 055, 061, 065, 075, 081

**What's wrong:** The app renamed `/clients/` to `/participants/` but 14 scenario configurations in the test runner still use old `/clients/` URL paths. These produce 404 "Page Not Found" errors, blocking evaluation.

**Impact:** Coverage dropped from 91% (Round 5) to 67% (Round 6) due to this single issue.

**Fix:** Update all test runner scenario configs to use `/participants/` instead of `/clients/`. Also update configs using `/clients/{id}` to `/participants/{id}`, and `/clients/create` to `/participants/create`.

**Affected URLs:**
- `/clients/` -> `/participants/`
- `/clients/{id}` -> `/participants/{id}`
- `/clients/create` -> `/participants/create`
- `/clients/executive/` -> `/participants/executive/`
- `/clients/{client_id}/notes` -> `/participants/{id}/notes`

**Acceptance criteria:**
- [ ] All 14 blocked scenarios load their target pages
- [ ] Re-run produces 0 unexpected 404s from /clients/ paths

---

### TEST-22: Test credentials visible in search field

**Severity:** TEST -- Low
**Affected scenario:** SCN-059, Step 1

**What's wrong:** Riley Chen's (DS4) dashboard shows "stafftestpassword" in the search field. The test runner appears to have entered test credentials into the participant search box instead of the login form.

**Fix:** Review test runner login flow for DS4 persona. Ensure credentials are entered only in the login form, not the dashboard search.

**Acceptance criteria:**
- [ ] SCN-059 step 1 shows clean dashboard without credentials in search

---

## Items NOT Filed as Tickets (Probable Test Artifacts)

1. **Duplicate screenshots for some scenarios** -- Multiple capture attempts visible (e.g., SCN-042 has both `_clients.png` and `_clients-63.png` variants). The test runner appears to have run multiple capture passes. Used most specific (URL-suffixed) versions for scoring.

2. **CAL-004 screenshot mismatch** -- CAL-004 expected a login page but captured a dashboard. This is a test configuration issue, not an app bug. The calibration still scored within range.

3. **SCN-047 language** -- Omar (R2, English speaker) seeing French dashboard at /home. May be test session contamination rather than an app bug. Not filed as separate ticket since it falls under FG-1 (language persistence).
