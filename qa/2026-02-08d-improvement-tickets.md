# KoNote Improvement Tickets — Round 2c (2026-02-08d)

**Date:** 2026-02-08
**Round:** Round 2c (fifth evaluation, fresh screenshots from 14:40:09)
**Source:** 114 screenshots from run manifest 2026-02-08T14:40:09

---

## Previous Ticket Status

| Ticket | Description | Round 2b Status | Round 2c Status | Evidence |
|--------|------------|-----------------|-----------------|---------|
| BLOCKER-1 | No skip-to-content link (WCAG 2.4.1) | NEEDS VERIFICATION | **NEEDS VERIFICATION** | Cannot confirm from screenshots. Skip links hidden until focused. |
| BLOCKER-2 | Focus goes to footer after login (WCAG 2.4.3) | NEEDS VERIFICATION | **NEEDS VERIFICATION** | Cannot determine focus position from screenshots. |
| BUG-1 | Wrong empty-state message on search | FIXED | **FIXED** | SCN-010 step 1: correct message shown |
| BUG-3 | Audit log filter truncation | PARTIALLY FIXED | **PARTIALLY FIXED** | CAL-003: "All acti..." still truncated |
| BUG-4 | Language not tied to user account | PARTIALLY FIXED | **SUPERSEDED by BUG-9** | — |
| BUG-5 | Executive landing page exposes PII | FIXED | **FIXED** | DITL-E1: aggregate only, no names |
| BUG-6 | Blank page on network failure | NOT FIXED | **NOT FIXED** | SCN-048 step 3: blank white page |
| BUG-7 | 404 after create participant | NOT FIXED | **NOT FIXED** | SCN-010 step 6, SCN-025 step 4 |
| BUG-8 | Untranslated strings in French UI | NOT FIXED | **NOT FIXED** | SCN-040 step 1: "Safety concern noted" in English |
| BUG-9 | Language doesn't persist across navigation | NEW (2b) | **NOT FIXED** | SCN-040: French dashboard → English form. DITL-DS2: English dashboard for francophone. |
| BUG-10 | Tab order mismatch on create form | NEW (2b) | **NOT FIXED** | SCN-050 steps 3-7, SCN-053 step 2, SCN-061: data in wrong fields |
| BUG-11 | Program names not translated | NEW (2b) | **NOT FIXED** | SCN-040: "Housing Support" in English on French pages |
| BUG-12 | New Participant button visible to Front Desk on home | NEW (2b) | **NOT FIXED** | DITL-R1 step 1: button visible for Dana Front Desk |
| BUG-13 | Search fails for accented names | NEW (2b) | **NOT FIXED** | SCN-040 step 4: "Benoit" returns no results |
| IMPROVE-1 | Settings cards missing status (2/6) | PARTIALLY FIXED | **PARTIALLY FIXED** | CAL-002: Instance Settings, Demo Accounts still missing |
| IMPROVE-2 | Pre-select single program on create | FIXED | **FIXED** | SCN-005 step 3 |
| IMPROVE-3 | 403 page is scary/unhelpful | FIXED | **FIXED** | SCN-010 step 3: warm tone, actionable |
| IMPROVE-4 | Dashboard has no timestamp | FIXED | **FIXED** | CAL-001, DITL-E1 |
| IMPROVE-5 | No confirmation after participant creation | NOT FIXED | **NOT FIXED** | SCN-005 step 4: dashboard unchanged |
| IMPROVE-6 | Reduce form tab stops | NOT TESTED | **NOT TESTED** | Carried forward |
| IMPROVE-7 | No onboarding guidance | NEW (2b) | **NOT FIXED** | SCN-005 step 1: no getting started message |

**Summary: 5 FIXED | 3 PARTIALLY FIXED | 8 NOT FIXED | 2 NEEDS VERIFICATION | 1 NOT TESTED | 1 SUPERSEDED**

---

## New Tickets This Round

**No new app bugs found this round.** All issues observed match previously filed tickets. This is encouraging — no regressions detected.

### Test Environment Issues to Fix (not app bugs)

**TEST-1: Search term mismatch in SCN-010**
The scenario searches for "Marie Santos" but seed data has "Maria Santos". The git log shows commit ce8dcc0 renamed to "Sofia Reyes" but the test runner appears to use stale data.
- **Fix:** Verify the scenario YAML and test runner are using the updated name.

**TEST-2: CAL-005 captures wrong page**
The test navigates to /reports/outcomes/ which returns 404 for DS3 role. The Insights page (/reports/insights/) shows only a filter form, not the data table. The calibration scenario cannot be validated.
- **Fix:** Update CAL-005-inaccessible-page.yaml with a URL that the DS3 role can access and that contains the intended data table.

**TEST-3: Language carryover between test personas**
Multiple scenarios show French interface for English-speaking personas (SCN-015 steps 2-3, SCN-020 step 3, SCN-025 step 4, SCN-056 step 2). This is test runner isolation failure, not BUG-9.
- **Fix:** Ensure fresh browser context per persona in test runner. Set `document.cookie = "django_language=en"` explicitly.

---

## Items NOT Filed as Tickets

| Finding | Why Not Filed | Action |
|---------|--------------|--------|
| Participant count shows 83 in DITL-E1 | Test runner created participants during automated scenarios | Not a bug — expected in test environment |
| "Safety concern noted" visible for Front Desk (DITL-R1) | May be intentional safety alert for all staff | Needs product decision — is this appropriate for Front Desk role? |
| Record IDs all blank (em dashes) | Optional field not populated in test data | Not a bug |
| Consent compliance at 2% in DITL-E1 | Test data artifact (83 participants, 2 with consent) | Not a bug |

---

## Fix Priority Order

### Fix First (unblocks testing and users)
1. **BUG-10** — Tab order mismatch on create form. Makes form UNUSABLE for keyboard-only and screen reader users. This is the #1 driver of the satisfaction gap. WCAG 2.4.3 violation.
2. **BUG-7** — 404 after create participant. Breaks core workflow for all users.
3. **BUG-9** — Language persistence. Breaks bilingual workflow, cross-contaminates test results.

### Fix Next (significant UX impact)
4. **BUG-6** — Offline handling. Blank white page is terrible UX with no recovery path.
5. **BUG-13** — Accent-insensitive search. Essential for a bilingual Canadian app using French names.
6. **IMPROVE-5** — Creation confirmation. Users don't know if save worked.

### Fix When Possible (important but not blocking)
7. **BUG-8** — Complete French translations (untranslated strings)
8. **BUG-11** — Translate program names to French
9. **BUG-12** — Hide New Participant button from Front Desk on home page
10. **BUG-3** — Complete audit log filter UI (fix truncation)
11. **IMPROVE-1** — Complete settings cards (2 remaining)
12. **IMPROVE-7** — Add onboarding guidance for new users

### Verify Manually
13. **BLOCKER-1** — Test skip link with actual keyboard/JAWS
14. **BLOCKER-2** — Test post-login focus with actual keyboard/JAWS

---

## All Active Tickets — Summary

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| BLOCKER-1 | BLOCKER | No skip-to-content link (WCAG 2.4.1) | NEEDS VERIFICATION |
| BLOCKER-2 | BLOCKER | Focus goes to footer after login (WCAG 2.4.3) | NEEDS VERIFICATION |
| BUG-3 | BUG | Audit log filter truncation | PARTIALLY FIXED |
| BUG-6 | BUG | Blank page on network failure | NOT FIXED |
| BUG-7 | BUG | 404 after create participant | NOT FIXED |
| BUG-8 | BUG | Untranslated strings in French UI | NOT FIXED |
| BUG-9 | BUG | Language doesn't persist across navigation | NOT FIXED |
| BUG-10 | BUG | Tab order mismatch on create form | NOT FIXED |
| BUG-11 | BUG | Program names not translated | NOT FIXED |
| BUG-12 | BUG | New Participant button visible to Front Desk on home | NOT FIXED |
| BUG-13 | BUG | Search fails for accented names | NOT FIXED |
| IMPROVE-1 | IMPROVE | Settings cards missing status (2/6) | PARTIALLY FIXED |
| IMPROVE-5 | IMPROVE | No creation confirmation | NOT FIXED |
| IMPROVE-6 | IMPROVE | Reduce form tab stops | NOT TESTED |
| IMPROVE-7 | IMPROVE | No onboarding guidance | NOT FIXED |

**Closed (confirmed fixed):** BUG-1, BUG-5, IMPROVE-2, IMPROVE-3, IMPROVE-4
**Superseded:** BUG-4 (by BUG-9)

**New this round:** 0 app bugs (3 test environment issues)

**Total active: 2 BLOCKERS (need verification) | 8 BUGS | 3 IMPROVEMENTS = 13 tickets**
(unchanged from Round 2b — no bugs fixed, no new bugs found)
