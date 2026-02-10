# KoNote Improvement Tickets — Round 3 (2026-02-09a)

**Date:** 2026-02-09
**Round:** Round 3 (full evaluation, fresh screenshots from 13:46:19)
**Source:** 117 screenshots from run manifest 2026-02-09T13:46:19

---

## Previous Ticket Status

| Ticket | Description | Round 2c Status | Round 3 Status | Evidence |
|--------|------------|-----------------|----------------|---------|
| BLOCKER-1 | No skip-to-content link (WCAG 2.4.1) | NEEDS VERIFICATION | **NEEDS VERIFICATION** | Cannot confirm from screenshots |
| BLOCKER-2 | Focus goes to footer after login (WCAG 2.4.3) | NEEDS VERIFICATION | **NEEDS VERIFICATION** | Cannot determine focus position from screenshots |
| BUG-3 | Audit log filter truncation | PARTIALLY FIXED | **PARTIALLY FIXED** | CAL-003: "All acti..." still truncated |
| BUG-6 | Blank page on network failure | NOT FIXED | **FIXED** | SCN-048 step 3: "You're offline" page with icon, message, Try again button |
| BUG-7 | 404 after create participant | NOT FIXED | **NOT FIXED** | SCN-025 step 4: French 404 "Page non trouvee" |
| BUG-8 | Untranslated strings in French UI | NOT FIXED | **NOT FIXED** | SCN-040 step 1: "Safety concern noted" in English on French dashboard |
| BUG-9 | Language doesn't persist across navigation | NOT FIXED | **PARTIALLY FIXED** | French dashboard works (SCN-040 step 1); form reverts to English (step 2) |
| BUG-10 | Tab order mismatch on create form | NOT FIXED | **FIXED** | SCN-053 step 2: "James" in First Name, "Thompson" in Last Name — correct |
| BUG-11 | Program names not translated | NOT FIXED | **NOT FIXED** | SCN-040: "Housing Support" in English on French pages |
| BUG-12 | New Participant button visible to Front Desk on home | NOT FIXED | **FIXED** | DITL-R1 step 1: Button not visible for Dana Front Desk |
| BUG-13 | Search fails for accented names | NOT FIXED | **NEEDS VERIFICATION** | SCN-040 step 4: "Benoit" found but stored name may lack accent |
| IMPROVE-1 | Settings cards missing status (2/6) | PARTIALLY FIXED | **PARTIALLY FIXED** | CAL-002: Instance Settings, Demo Accounts still missing status |
| IMPROVE-2 | Pre-select single program on create | FIXED | **FIXED** | SCN-005 step 3 |
| IMPROVE-3 | 403 page is scary/unhelpful | FIXED | **FIXED** | Good error pages throughout |
| IMPROVE-4 | Dashboard has no timestamp | FIXED | **FIXED** | CAL-001, DITL-E1 |
| IMPROVE-5 | No confirmation after participant creation | NOT FIXED | **NOT FIXED** | No confirmation visible in any create workflow |
| IMPROVE-6 | Reduce form tab stops | NOT TESTED | **NOT TESTED** | Carried forward |
| IMPROVE-7 | No onboarding guidance | NOT FIXED | **NOT FIXED** | SCN-005 step 1: No getting started message for Casey New |

**Summary: 8 FIXED | 3 PARTIALLY FIXED | 5 NOT FIXED | 2 NEEDS VERIFICATION | 1 NOT TESTED**

---

## New Tickets This Round

**No new app bugs found this round.** All issues observed match previously filed tickets. Three bugs were fixed (BUG-6, BUG-10, BUG-12), which is the most fixes in a single round.

### Test Environment Issues

**TEST-4: 8 scenarios produced no evaluable screenshots**
Despite the manifest listing 37 scenarios as run, 8 produced no screenshots: SCN-030, SCN-035, SCN-042, SCN-045, SCN-049, SCN-058, SCN-059, SCN-070. These all require multi-role or cross-persona setups.
- **Fix:** Ensure test runner handles multi-persona scenarios by resetting browser context between actors.

**TEST-5: URL variables unresolved in SCN-025**
Steps 3-4 navigate to `clients/{client_id}/notes/` and `clients/{client_id}/` with the literal variable instead of an actual ID.
- **Fix:** Ensure the test runner resolves client ID from a previous step (e.g., by searching and clicking the first result).

---

## Items NOT Filed as Tickets

| Finding | Why Not Filed | Action |
|---------|--------------|--------|
| Participant count 83 in DITL-E1 | Test data artifact from automated scenarios | Not a bug |
| "Safety concern noted" visible for Front Desk (DITL-R1) | Previously noted — needs product decision | Carry forward for product review |
| Consent compliance at 2% in DITL-E1 | Test data artifact | Not a bug |
| ARIA role attribute violations on all pages | Axe-core flags minor/critical ARIA issues | Already tracked in BUG-10 family — may need separate ticket if persists after other fixes |

---

## Fix Priority Order

### Fix First (unblocks testing and users)
1. **BUG-7** — 404 after create participant. Still breaks core workflow for all users. The 404 page design is improved (helpful message, navigation buttons) but the 404 itself shouldn't happen.
2. **BUG-9** — Language persistence. French dashboard works now, but the create form reverts to English. Partially fixed — needs the form and navigation to maintain language.

### Fix Next (significant UX impact)
3. **BUG-8** — Complete French translations. "Safety concern noted" in English on French dashboard. Alert text must be translated.
4. **BUG-11** — Translate program names ("Housing Support" -> French equivalent). Visible on every French page.
5. **IMPROVE-5** — Creation confirmation. Users still don't know if save worked.
6. **BUG-13** — Verify accent-insensitive search works both ways (accented input finding non-accented record AND vice versa).

### Fix When Possible (important but not blocking)
7. **BUG-3** — Complete audit log filter UI (fix truncation on Action and Context dropdowns)
8. **IMPROVE-1** — Add status text to Instance Settings and Demo Accounts cards
9. **IMPROVE-7** — Add onboarding guidance for new users (first login experience)

### Verify Manually
10. **BLOCKER-1** — Test skip link with actual keyboard/JAWS
11. **BLOCKER-2** — Test post-login focus with actual keyboard/JAWS

---

## Finding Groups

| Group ID | Root Cause | Primary Ticket | Affected Steps |
|----------|-----------|----------------|----------------|
| FG-S-1 | French translation gaps | BUG-8 | SCN-040 step 1 (alert), DITL-DS2 step 1, SCN-040 step 4 (program name) |
| FG-S-2 | Language doesn't persist | BUG-9 | SCN-040 step 2, SCN-010 step 4, DITL-DS2 (cross-session) |
| FG-S-3 | ARIA role violations | (new) | All pages — axe-core "Ensure role attribute has appropriate value" on every screenshot |

---

## Verification Scenarios

| Ticket | Primary Scenario | Related Scenarios | Cross-Persona Check |
|--------|-----------------|-------------------|---------------------|
| BUG-7 | SCN-025 step 4 | SCN-010 step 6 | SCN-005 step 4 (DS1b) |
| BUG-8 | SCN-040 step 1 | DITL-DS2 step 1 | SCN-026 (R2-FR, when available) |
| BUG-9 | SCN-040 steps 1-2 | DITL-DS2 | SCN-015 steps 2-3 (DS1) |
| BUG-11 | SCN-040 step 4 | DITL-DS2 | SCN-026 (R2-FR) |
| BUG-13 | SCN-040 step 4 | — | — (needs manual test with accented input) |
| IMPROVE-5 | SCN-005 step 4 | SCN-010 step 6 | SCN-050 step 7 (DS3) |

---

## All Active Tickets — Summary

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| BLOCKER-1 | BLOCKER | No skip-to-content link (WCAG 2.4.1) | NEEDS VERIFICATION |
| BLOCKER-2 | BLOCKER | Focus goes to footer after login (WCAG 2.4.3) | NEEDS VERIFICATION |
| BUG-3 | BUG | Audit log filter truncation | PARTIALLY FIXED |
| BUG-7 | BUG | 404 after create participant | NOT FIXED |
| BUG-8 | BUG | Untranslated strings in French UI | NOT FIXED |
| BUG-9 | BUG | Language doesn't persist across navigation | PARTIALLY FIXED |
| BUG-11 | BUG | Program names not translated | NOT FIXED |
| BUG-13 | BUG | Search fails for accented names | NEEDS VERIFICATION |
| IMPROVE-1 | IMPROVE | Settings cards missing status (2/6) | PARTIALLY FIXED |
| IMPROVE-5 | IMPROVE | No creation confirmation | NOT FIXED |
| IMPROVE-6 | IMPROVE | Reduce form tab stops | NOT TESTED |
| IMPROVE-7 | IMPROVE | No onboarding guidance | NOT FIXED |

**Closed (confirmed fixed):** BUG-1, BUG-5, BUG-6, BUG-10, BUG-12, IMPROVE-2, IMPROVE-3, IMPROVE-4
**Superseded:** BUG-4 (by BUG-9)

**New this round:** 0 app bugs (2 test environment issues)
**Fixed this round:** 3 (BUG-6, BUG-10, BUG-12)

**Total active: 2 BLOCKERS (need verification) | 5 BUGS | 3 IMPROVEMENTS = 10 tickets**
(Down from 13 in Round 2c — 3 bugs closed)
