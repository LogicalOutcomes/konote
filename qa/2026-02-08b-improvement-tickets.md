# KoNote Improvement Tickets — Round 2 (2026-02-08b)

**Date:** 2026-02-08 (report "b" — supersedes earlier 2026-02-08b draft)
**Round:** Round 2 (post-fix re-evaluation with full screenshot analysis)
**Source:** 77 screenshots from run manifest 2026-02-08T15:06:00

---

## Previous Ticket Status

| Ticket | Description | Status | Evidence |
|--------|------------|--------|---------|
| BLOCKER-1 | No skip-to-content link (WCAG 2.4.1) | **NEEDS VERIFICATION** | No visible skip link in screenshots (SCN-050, 051, 052). Skip links are hidden until focused — cannot confirm from visual evidence. SCN-052 step 2 shows focus on First Name, possibly via skip link. **Needs manual JAWS test.** |
| BLOCKER-2 | Focus goes to footer after login (WCAG 2.4.3) | **NEEDS VERIFICATION** | SCN-051 shows no visible focus indicator after login. Cannot determine focus position from screenshots. **Needs manual keyboard test.** |
| BUG-1 | Wrong empty-state message on search | **FIXED** | SCN-010 step 1: "No Participants found matching 'Marie Santos'. Try a different name or check the spelling." |
| BUG-2 | Create buttons visible to wrong roles | **PARTIALLY FIXED** | Participants LIST page: button hidden for Front Desk ✓. HOME page: "+ New Participant" button still visible for Front Desk ✗ (see BUG-12). |
| BUG-3 | Audit log jargon/complexity | **PARTIALLY FIXED** | CAL-003: "Created"/"Logged in" badges (improved ✓). IP hidden behind toggle (improved ✓). BUT: filter dropdowns truncated ("All acti..."), date fields show "yyyy-" only. |
| BUG-4 | Language not tied to user account | **PARTIALLY FIXED** | Language CAN be toggled, but does NOT persist across page navigations within the same session. SCN-040: French dashboard → English create form. See BUG-9 for refinement. |
| BUG-5 | Executive landing page exposes PII | **FIXED** | DITL-E1: Executive dashboard shows 77 participants as aggregate only. No individual names. Confidentiality message prominent. |
| BUG-6 | Blank page on network failure | **NOT FIXED** | SCN-048 steps 3-4: Completely blank white page. No error, no banner, no recovery. |
| BUG-7 | 404 after create participant form | **NOT FIXED** | SCN-010 step 6: "Page Not Found" after create workflow. |
| BUG-8 | Untranslated strings in French UI | **NOT FIXED** | SCN-040: "Safety concern noted" and "Housing Support" in English on French dashboard. (Reported in earlier 2026-02-08b, confirmed again.) |
| IMPROVE-1 | Settings cards lack state indicators | **PARTIALLY FIXED** | CAL-002: 4/6 cards show status. Instance Settings and Demo Accounts still missing. |
| IMPROVE-2 | Pre-select single program on create form | **FIXED** | SCN-005 step 3: "Housing Support" pre-checked. |
| IMPROVE-3 | 403 page is scary/unhelpful | **FIXED** | SCN-010 step 3: "This page is available to staff members and program managers." Warm tone, Go Back/Home buttons. |
| IMPROVE-4 | Dashboard has no timestamp | **FIXED** | CAL-001: "Last updated: 2026-02-08 03:04" visible. |
| IMPROVE-5 | No confirmation after participant creation | **NOT FIXED** | SCN-005 step 4: Dashboard unchanged. No success message. |
| IMPROVE-6 | Reduce form tab stops | **NOT TESTED** | Carried forward. |

**Summary: 5 FIXED | 4 PARTIALLY FIXED | 4 NOT FIXED | 2 NEEDS VERIFICATION | 1 NOT TESTED**

---

## New Tickets This Round

### BUG-9: Language Preference Doesn't Persist Across Page Navigations (NEW)

**Severity:** BUG — Priority fix
**Confidence:** High

**What's wrong:** Refines BUG-4. Language preference is lost when navigating between pages within the SAME session. Jean-Luc (DS2) sees his dashboard in French, but clicking "New Participant" loads the Create form in English. This is NOT test contamination — it happens within a single user's session.

**Evidence:**
- SCN-040 step 1: French dashboard ✓ → SCN-040 step 2: English create form ✗
- DITL-DS2: Both screenshots in English despite Jean-Luc being francophone

**Where to look:** Language middleware / session cookie handling. The language toggle likely sets a session variable that gets lost or overridden on navigation. Check Django `LocaleMiddleware`, HTMX navigation headers, and whether the language cookie is set with the correct path.

**What "fixed" looks like:** Once language is set to French, every subsequent page loads in French until explicitly changed.

**Acceptance criteria:**
- [ ] Set language to French → navigate to 5 different pages → all display in French
- [ ] Language persists across browser refresh
- [ ] Language persists after logout/login (tied to user profile)
- [ ] HTMX partial page loads respect the language setting

**Screenshot reference:** `SCN-040_step1_DS2_home.png` (French), `SCN-040_step2_DS2_clients-create.png` (English)
**Priority:** Priority fix — breaks bilingual workflow.

---

### BUG-10: Tab Order Mismatch on Create Participant Form (NEW)

**Severity:** BUG — Priority fix
**Confidence:** Medium

**What's wrong:** When using Tab key to navigate the Create Participant form, focus does not follow the visual field order. Data entered via keyboard goes into the WRONG fields:
- "James" (intended for First Name) → ends up in Last Name
- "Thompson" (intended for Last Name) → ends up in Preferred Name
- Note text → entered into Last Name field

Compare SCN-050 (Tab navigation, data in wrong fields) with SCN-053 (selector-based entry, data in correct fields). The form's DOM order doesn't match its visual layout.

**Evidence:**
- SCN-050 step 4: "James" in Last Name, "Thompson" in Preferred Name
- SCN-050 step 6: Full paragraph of note text in Last Name field
- SCN-053 step 2: Same form, same data, CORRECTLY placed — proving the form works when fields are targeted by ID

**Where to look:** Create participant form template. Check:
- DOM source order of form fields (must match visual left-to-right, top-to-bottom)
- Any `tabindex` attributes that override natural tab order
- CSS `float` or `flex` ordering that visually rearranges elements without changing DOM order

**What "fixed" looks like:** Tab key moves focus in this exact order:
1. First Name → 2. Last Name → 3. Preferred Name → 4. Middle Name → 5. Phone Number → 6. Date of Birth → 7. Record ID → 8. Status → 9. Programs → 10. Create Participant → 11. Cancel

**Acceptance criteria:**
- [ ] Tab order matches visual field order (verify with keyboard navigation)
- [ ] Data entered via Tab+Type goes into the visually indicated field
- [ ] JAWS/NVDA announces the correct field label at each Tab stop
- [ ] Remove any explicit `tabindex` values > 0
- [ ] Run SCN-050 and verify "James" goes into First Name, "Thompson" into Last Name

**Screenshot reference:** `SCN-050_step4_DS3_clients-create.png`, `SCN-050_step6_DS3_clients-create.png`
**Priority:** Priority fix — makes form unusable for keyboard-only and screen reader users (WCAG 2.4.3).

---

### BUG-11: Program Names Not Translated to French (NEW)

**Severity:** BUG — Review recommended
**Confidence:** High

**What's wrong:** "Housing Support" appears in English in the French interface. All labels, buttons, and messages are French, but the program name stays in English.

**Where to look:** Program model. Names are likely stored as plain text without translation support. Add a `name_fr` field or use Django's translation framework for model data.

**What "fixed" looks like:** French interface displays "Soutien au logement" (or agency's chosen French name) instead of "Housing Support."

**Acceptance criteria:**
- [ ] Program names have French translations
- [ ] French interface shows French program names in all locations (filters, forms, lists, dashboard)

**Screenshot reference:** `SCN-040_step3_DS2_clients-create.png`
**Priority:** Review recommended.

---

### BUG-12: New Participant Button Visible to Front Desk on Home Page (NEW)

**Severity:** BUG — Review recommended
**Confidence:** High

**What's wrong:** The home page shows a prominent "+ New Participant" button to Front Desk role users. Clicking it leads to a 403. The Participants LIST page correctly hides this button — but the HOME page doesn't.

**Evidence:**
- DITL-R1 step 1: Home page shows "+ New Participant" for "Dana Front Desk"
- DITL-R1 step 2: Participants list does NOT show the button (correct)
- SCN-010 step 3: /clients/create/ returns 403 for Front Desk

**Where to look:** Home page template. The "New Participant" button is rendered without a permission check. Wrap it in the same check used on the Participants list page.

**Acceptance criteria:**
- [ ] Home page hides "New Participant" button for Front Desk role
- [ ] Participants list page behaviour unchanged (already correct)
- [ ] Staff and Program Manager roles still see the button on both pages

**Screenshot reference:** `DITL-R1_step1_R1_home.png`
**Priority:** Review recommended — misleading but not blocking (403 page is well-designed).

---

### BUG-13: Search Fails for "Benoit" Despite Participant Existing (NEW)

**Severity:** BUG — Priority fix
**Confidence:** Medium

**What's wrong:** Jean-Luc searches for "Benoit" and gets zero results, despite "Benoit Tremblay" appearing in other users' participant lists. Possible causes: accent encoding mismatch (stored as "Benoît" with circumflex), user/session scoping, or search timing.

**Evidence:**
- SCN-040 step 4: "No Participants found matching 'Benoit'" for DS2 (Jean-Luc)
- SCN-015 step 2, step 5: Full list shows "Benoit Tremblay" for DS1 (Casey)

**Where to look:** Search query logic. Check database collation for accent-insensitive matching. If using PostgreSQL, verify `unaccent` extension or Django's `__unaccent` lookup.

**Acceptance criteria:**
- [ ] "Benoit" (no accent) finds "Benoît Tremblay" (with accent)
- [ ] "Benoît" (with accent) also finds the participant
- [ ] Search works identically across all user roles with access to the same program

**Screenshot reference:** `SCN-040_step4_DS2_clients.png`
**Priority:** Priority fix — accent-insensitive search is essential for a bilingual Canadian app.

---

### IMPROVE-7: No Onboarding Guidance for New Users (NEW)

**Severity:** IMPROVE — Review recommended
**Confidence:** High

**What's wrong:** First-time users see the full dashboard with metrics, priority items, and alerts — but no guidance on what to do first. No "getting started" message, no walkthrough, no highlighted first action.

**Evidence:** SCN-005 steps 1-2: DS1b (Casey, first week) sees a full dashboard with zero context.

**What "fixed" looks like:** First-time users see a dismissible welcome banner: "Welcome to KoNote! Start by searching for a participant or creating a new one."

**Acceptance criteria:**
- [ ] First login shows an orientation message
- [ ] Message is dismissible and doesn't appear after dismissal
- [ ] Returning users don't see it

**Screenshot reference:** `SCN-005_step1_DS1b_home.png`
**Priority:** Review recommended.

---

## Items NOT Filed as Tickets (Likely Test Artifacts)

| Finding | Why Not Filed | Action |
|---------|--------------|--------|
| SCN-047: Never got past login at 375px | Test runner failure, not app bug | Fix test runner mobile login handling |
| SCN-010 step 4: French form for English user | Language carryover between test personas | Implement test runner isolation protocol |
| SCN-015 steps 2-3: French interface for Casey | Same as above | Same fix |
| SCN-050 steps 5, 7: Duplicate screenshots | Test runner captured same state twice | No action needed |
| DITL-E1 step 2: Identical to step 1 | Duplicate capture | No action needed |
| CAL-005: 404 instead of reports/outcomes | URL doesn't exist for DS3 role | Update CAL-005 scenario YAML with correct URL |
| SCN-048 step 1: "Jane Doe" in "James" search | May match note content, not just names | Verify before filing — could be expected behaviour |
| Record IDs all blank (em dashes) | Optional field not populated in test data | Not a bug |

---

## Fix Priority Order

### Fix First (unblocks other testing)
1. **BUG-7** — 404 after create participant (blocks core intake workflow)
2. **BUG-10** — Tab order mismatch (blocks keyboard-only users from creating participants)
3. **BUG-9** — Language persistence (blocks bilingual testing, cross-contaminates results)

### Fix Next (significant UX impact)
4. **BUG-6** — Offline handling (blank white page is terrible UX)
5. **BUG-13** — Accent-insensitive search (essential for bilingual Canadian app)
6. **IMPROVE-5** — Creation confirmation (users don't know if save worked)

### Fix When Possible (important but not blocking)
7. **BUG-8** — Complete French translations (untranslated strings)
8. **BUG-11** — Translate program names
9. **BUG-12** — Hide New Participant button from Front Desk on home page
10. **BUG-3** — Complete audit log filter UI (fix truncation)
11. **IMPROVE-1** — Complete settings cards (2 remaining)
12. **IMPROVE-7** — Add onboarding guidance for new users

### Verify Manually (cannot confirm from screenshots)
13. **BLOCKER-1** — Test skip link with actual keyboard/JAWS
14. **BLOCKER-2** — Test post-login focus with actual keyboard/JAWS

---

## All Active Tickets — Summary

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| BLOCKER-1 | BLOCKER | No skip-to-content link (WCAG 2.4.1) | NEEDS VERIFICATION |
| BLOCKER-2 | BLOCKER | Focus goes to footer after login (WCAG 2.4.3) | NEEDS VERIFICATION |
| BUG-3 | BUG | Audit log filter truncation | PARTIALLY FIXED |
| BUG-4 | BUG | Language not tied to user account | PARTIALLY FIXED (see BUG-9) |
| BUG-6 | BUG | Blank page on network failure | NOT FIXED |
| BUG-7 | BUG | 404 after create participant | NOT FIXED |
| BUG-8 | BUG | Untranslated strings in French UI | NOT FIXED |
| BUG-9 | BUG | Language doesn't persist across navigation | **NEW** |
| BUG-10 | BUG | Tab order mismatch on create form | **NEW** |
| BUG-11 | BUG | Program names not translated | **NEW** |
| BUG-12 | BUG | New Participant button visible to Front Desk on home | **NEW** |
| BUG-13 | BUG | Search fails for accented names | **NEW** |
| IMPROVE-1 | IMPROVE | Settings cards missing status (2/6) | PARTIALLY FIXED |
| IMPROVE-5 | IMPROVE | No creation confirmation | NOT FIXED |
| IMPROVE-6 | IMPROVE | Reduce form tab stops | NOT TESTED |
| IMPROVE-7 | IMPROVE | No onboarding guidance | **NEW** |

**Closed this round:** BUG-1, BUG-2 (partial→see BUG-12), BUG-5, IMPROVE-2, IMPROVE-3, IMPROVE-4

**New this round:** BUG-9, BUG-10, BUG-11, BUG-12, BUG-13, IMPROVE-7

**Total active: 2 BLOCKERS (need verification) | 8 BUGS | 3 IMPROVEMENTS = 13 tickets**
