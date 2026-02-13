# QA Action Plan — Round 5 (2026-02-13a)

**Date:** 2026-02-13
**Round:** 5
**Source report:** `qa/2026-02-13a-improvement-tickets.md`
**Previous action plan:** `tasks/qa-action-plan-2026-02-12a.md` (Round 4)

## Headline Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Average score | 3.35 | +0.31 from Round 4 (3.04) |
| Satisfaction gap | 0.9 | Improving (1.3 → 0.9) |
| Worst personas | E1, DS3 | DS3 avg 3.2 (up from 2.9) |
| Coverage | 40/44 (91%) | Up from 25/40 (63%) |
| Blockers | 2 | New this round |
| Regressions | 0 | — |
| Improvements | 6 | 6 scenarios improved 0.5+ pts |
| Permission violations | 0 | — |
| New tickets | 20 | 2 BLOCKER, 9 BUG, 5 IMPROVE, 11 TEST |
| Fixed tickets | 5 | TEST-5 through TEST-9 |
| Bands | 1 green, 33 yellow, 6 orange, 0 red | — |
| Calibration gate | PASS | — |

**Key finding:** Coverage jumped from 63% to 91% thanks to Round 4 test infrastructure fixes. The satisfaction gap dropped to 0.9 — best ever. However, expanded coverage exposed 2 blockers and 4 WCAG Level A/AA failures that need immediate attention. Six finding groups share root causes — fixing 6 items resolves ~15 symptoms.

**Positive signal:** All 5 test infrastructure tickets from Round 4 are verified FIXED. Six scenarios improved 0.5+ points. DS3 (screen reader persona) average up from 2.9 to 3.2. Zero regressions.

---

## Expert Panel Summary

**Panel:** Accessibility Specialist, UX Designer, Django Developer, Nonprofit Operations Lead

### Key Insights by Expert

**Accessibility Specialist:**
- Four WCAG failures at Level A or AA: BUG-16 (2.4.1 Bypass Blocks), BUG-17 (3.3.1 Error Identification), IMPROVE-10 (4.1.3 Status Messages), BUG-22 (2.5.8 Target Size)
- IMPROVE-10 should be reclassified as a compliance item, not an improvement — WCAG 4.1.3 is Level AA
- BUG-16 (skip link) is the single highest-value fix: 10 minutes, site-wide impact, Level A compliance
- FG-S-3 (ARIA live regions) needs a systematic approach — shared utility for all three tickets

**UX Designer:**
- BLOCKER-2 and BLOCKER-1 are the most user-impactful — complete workflow blockers
- BUG-23 (data in wrong fields) is a data integrity risk, not just a UX issue
- BLOCKER-1 has a quick design win: HTMX `htmx-indicator` is built-in, 15-minute fix
- IMPROVE-12 (ADHD dashboard) should wait for real user testing — don't design in the dark

**Django Developer:**
- 9 of 20 tickets are quick fixes (< 30 min each)
- FG-S-6 (executive permissions): BUG-15 + BUG-20 are both permission mapping bugs — fix together in one `permissions.py` review
- BLOCKER-2 needs investigation — /settings/ view may not exist yet (feature gap, not bug)
- BUG-19 (htmx:syntax:error) needs careful investigation — fixing wrong could break HTMX entirely

**Nonprofit Operations Lead:**
- BLOCKER-2 blocks agency onboarding — a funder demo would expose this immediately
- BUG-15 (audit log denied) undermines board governance messaging
- BUG-23 data integrity risk cascades into reports and client interactions
- TEST-10 matters because some Ontario agencies serve clients who use voice control

### Areas of Agreement

1. **BUG-16 (skip link) is the single highest-value fix** — all four experts agree
2. **BLOCKER-1 and BLOCKER-2 must be fixed before next round** — they block entire workflows
3. **BUG-15 + BUG-20 should be fixed together** — same permissions review, 30 minutes total
4. **IMPROVE-10 should be reclassified as a bug** — WCAG 4.1.3 Level AA compliance
5. **BUG-21 should be verified as test data before coding** — may not need a code fix
6. **TEST-10 is the highest-priority test fix** — one YAML change, DS4 goes from 0% to evaluable
7. **TEST-20 is the highest-leverage test fix** — one runner change unblocks 4+ scenarios

### Disagreements

**BUG-17 approach (Accessibility Specialist vs. Django Developer):**
- Accessibility Specialist wants staged rollout (participant create form first, others later)
- Django Developer prefers a form template pack (applies everywhere at once)
- **Resolution:** Build the template pack, apply to participant create form first as proof of concept. If clean, propagate immediately. If complex, ship single-form fix and iterate.

**BUG-19 priority (UX Designer vs. Django Developer):**
- UX Designer: invisible to users, low priority
- Django Developer: may cause silent HTMX failures in dynamic updates
- **Resolution:** Investigate in Tier 2. Audit HTMX attributes first, fix second. Don't fix blindly.

**IMPROVE-12 placement (Operations Lead vs. UX Designer):**
- Operations Lead wants it visible as future differentiator
- UX Designer says don't design without user data
- **Resolution:** Keep in Backlog as research task, not code task.

### Shared Root Causes

1. **FG-S-1 — Skip link + tab order (BUG-16, BUG-18):** Both are template changes. Fix BUG-16 in base.html (site-wide), BUG-18 in client list template. Same commit.
2. **FG-S-3 — ARIA live region gaps (BUG-17, IMPROVE-9, IMPROVE-10):** No systematic approach to dynamic content announcements. Build a shared pattern — `aria-live` region in base template, form error summary include.
3. **FG-S-6 — Executive permissions (BUG-15, BUG-20, BUG-21):** BUG-15 is under-permission, BUG-20 is over-permission visibility. Same `permissions.py` + nav template review. BUG-21 likely test data.
4. **FG-S-4 — URL template variables (TEST-20, TEST-11, TEST-12, TEST-13):** One test runner fix resolves all four. Needs variable resolution step before navigation.
5. **FG-S-2 — Language carryover (BUG-14, BUG-8, BUG-11):** Carried since Round 2/4. BUG-14 partially fixed. TEST-15 (runner doesn't reset language) may mask remaining issues.
6. **FG-S-5 — htmx:syntax:error (BUG-19):** Malformed HTMX attributes on form templates. Needs investigation before fix.

---

## Priority Tiers

### Tier 1 — Fix Now

**1. BUG-16 — Skip link missing (WCAG 2.4.1 Level A)**
- **Expert reasoning:** All four experts agree: highest value-to-effort ratio. One `<a>` tag in base.html, site-wide impact. Level A means the site fails WCAG conformance entirely without this.
- **Complexity:** Quick fix (10 min)
- **Dependencies:** BUG-18 should be fixed alongside (same template area)
- **Fix in:** konote-app (`base.html`)

**2. BUG-18 — Tab order: filters before search on /clients/**
- **Expert reasoning:** /clients/ is the most-used page. Search should be the first interactive element after skip link. DOM order change.
- **Complexity:** Quick fix (10 min)
- **Dependencies:** Fix with BUG-16 in same commit
- **Fix in:** konote-app (client list template)

**3. BLOCKER-1 — No HTMX loading indicator on /clients/ search**
- **Expert reasoning:** Trust killer on slow networks. Rural Ontario agencies will see this constantly. HTMX has built-in `htmx-indicator` support. Must include `aria-live="polite"` for screen readers.
- **Complexity:** Quick fix (20 min)
- **Dependencies:** None. IMPROVE-10 (aria-live for results) should be done alongside.
- **Fix in:** konote-app (client list template + CSS)

**4. IMPROVE-10 — aria-live for search results (WCAG 4.1.3 Level AA)**
- **Expert reasoning:** Reclassified from IMPROVE to compliance item by panel consensus. When HTMX swaps results, screen readers are silent. 15-minute fix alongside BLOCKER-1.
- **Complexity:** Quick fix (15 min)
- **Dependencies:** Natural pairing with BLOCKER-1
- **Fix in:** konote-app (client list template)

**5. BLOCKER-2 — /settings/ returns 404**
- **Expert reasoning:** Blocks PM workflows entirely. Agency onboarding blocked. Funder demo would expose immediately.
- **Complexity:** Investigation needed (30–60 min) — view may not exist yet
- **Dependencies:** None
- **Fix in:** konote-app (urls.py, views, templates)

**6. BUG-15 + BUG-20 — Executive permission bugs**
- **Expert reasoning:** BUG-15 (audit denied) blocks board governance. BUG-20 (admin visible) is a security risk. Same permissions.py review fixes both.
- **Complexity:** Quick fix (30 min total)
- **Dependencies:** Fix together in one review
- **Fix in:** konote-app (permissions.py + nav template)

**7. BUG-17 — No role="alert" on form errors (WCAG 3.3.1 Level A)**
- **Expert reasoning:** Screen reader users don't know forms failed. Level A violation. Build form error summary template, apply to participant create form first.
- **Complexity:** Moderate (45 min for template pack + first form)
- **Dependencies:** Pattern reused by IMPROVE-9 later
- **Fix in:** konote-app (form templates)

**8. TEST-10 — SCN-059 wrong login URL**
- **Expert reasoning:** One YAML change unblocks DS4 (voice control). Currently 0% coverage.
- **Complexity:** Quick fix (5 min)
- **Dependencies:** None
- **Fix in:** konote-qa-scenarios

**9. TEST-20 — URL template variable resolution**
- **Expert reasoning:** One runner fix unblocks TEST-11, TEST-12, TEST-13, and 4+ scenarios.
- **Complexity:** Moderate (45 min)
- **Dependencies:** Resolves TEST-11, TEST-12, TEST-13 automatically
- **Fix in:** konote-qa-scenarios

### Tier 2 — Fix Next

**10. BUG-23 — Tab order after validation error**
- **Expert reasoning:** Data lands in wrong fields — data integrity risk. Needs investigation of autofocus + validation interaction.
- **Complexity:** Investigation (30–45 min)
- **Dependencies:** Related to BUG-17 (form error handling overhaul may resolve)

**11. BUG-22 — Touch targets under 24×24px (WCAG 2.5.8 Level AA)**
- **Expert reasoning:** Level AA violation. CSS-only fix for checkboxes, radios, filter buttons.
- **Complexity:** Quick fix (15 min)
- **Dependencies:** None

**12. BUG-19 — htmx:syntax:error in console**
- **Expert reasoning:** May cause silent HTMX failures. Needs HTMX attribute audit before fixing.
- **Complexity:** Investigation (30–60 min)
- **Dependencies:** None

**13. BUG-14 (carried) — lang="fr" on /reports/insights/**
- **Expert reasoning:** WCAG 3.1.1 Level A. Carried since Round 4. Verify middleware fix covers all pages.
- **Complexity:** Quick fix (15 min)
- **Dependencies:** Related to FG-S-2

**14. IMPROVE-9 — aria-live for form success messages**
- **Expert reasoning:** Shares pattern with IMPROVE-10. Build once, apply to all HTMX form responses.
- **Complexity:** Moderate (30 min)
- **Dependencies:** Pattern from BUG-17 + IMPROVE-10

**15. IMPROVE-8 — Post-login focus placement**
- **Expert reasoning:** Best practice. Needs screen reader verification.
- **Complexity:** Quick fix (15 min)
- **Dependencies:** None

**16. IMPROVE-11 — 403 page with actionable suggestions**
- **Expert reasoning:** Reduces support burden. Role-aware messaging. Quick template update.
- **Complexity:** Quick fix (20 min)
- **Dependencies:** None

**17. BUG-21 — E1 sees 1 programme not 2**
- **Expert reasoning:** Likely test data issue. Verify before coding.
- **Complexity:** Quick fix (10 min to verify)
- **Dependencies:** None

**18. TEST-15 — Language carryover in test runner**
- **Expert reasoning:** Affects FG-S-2 accuracy. May mask real language bugs.
- **Complexity:** Moderate (30 min)
- **Dependencies:** None
- **Fix in:** konote-qa-scenarios

**19. TEST-17 + TEST-18 — SCN-058 selector mismatches**
- **Expert reasoning:** Two selector fixes unblock ADHD evaluation scenario.
- **Complexity:** Quick fix (15 min total)
- **Dependencies:** None
- **Fix in:** konote-qa-scenarios

### Tier 3 — Backlog

**20. TEST-11 — SCN-054 unresolved variable**
- Resolved by TEST-20 fix

**21. TEST-12 — SCN-063/064 wrong dashboard URL**
- Resolved by TEST-20 fix

**22. TEST-13 — SCN-065 hardcoded /clients/1/**
- Resolved by TEST-20 fix

**23. TEST-14 — SCN-062 needs 8 prerequisite clients**
- Test data seeding task. Medium effort.

**24. TEST-16 — SCN-050 tab count recalibration**
- Depends on BUG-16 + BUG-18 landing first

**25. TEST-19 — SCN-046 shared device test blocked**
- Needs multi-session runner capability. Defer.

**26. BUG-8 + BUG-11 (carried) — French translation gaps**
- Carried since Round 2. Still need .po additions and name_fr verification.

**27. IMPROVE-12 — Dashboard cognitive load (ADHD)**
- Research task — needs real user testing. Keep visible.

---

## Recommended Fix Order

1. **BUG-16 + BUG-18** — Skip link + search-before-filters (20 min, same commit)
2. **BLOCKER-1 + IMPROVE-10** — Loading indicator + aria-live for search results (35 min, same page)
3. **BUG-15 + BUG-20** — Executive permissions audit (30 min, same file)
4. **BLOCKER-2** — Investigate and fix /settings/ URL (30–60 min)
5. **BUG-17** — Form error summary with role="alert" (45 min)
6. **TEST-10** — Fix SCN-059 login URL in YAML (5 min, qa-scenarios repo)
7. **TEST-20** — Template variable resolution in test runner (45 min, qa-scenarios repo)

**Estimated Tier 1 total:** ~3.5 hours (2.5h konote-app, 1h konote-qa-scenarios)

---

## Items Flagged as Likely Test Artefacts

The panel flagged three items as probable test artefacts, not real app issues:
1. **BUG-21 (E1 sees 1 programme)** — Almost certainly test data. E1 test user may only have 1 programme assigned in seed data.
2. **Low language scores on SCN-056/058** — Caused by TEST-15 (language carryover in test runner), not by the app.
3. **SCN-058 navigation failures** — Caused by TEST-18 (wrong CSS selector), not by cognitive accessibility issues.

---

## Cross-Reference: Previously Completed Tasks

These tickets from Round 4 are now verified FIXED:

| Ticket | Status | Verification |
|--------|--------|-------------|
| TEST-5 | FIXED | SCN-035 now scores 3.3 (Yellow), PM reporting works |
| TEST-6 | FIXED | SCN-020 improved from 3.0 → 3.8 (+0.8) |
| TEST-7 | FIXED | SCN-025 improved from 2.8 → 3.6 (+0.8) |
| TEST-8 | FIXED | SCN-047 improved from 2.8 → 3.7 (+0.9) |
| TEST-9 | FIXED | SCN-048 improved from 3.0 → 3.7 (+0.7) |
