# QA Action Plan — Round 6 (2026-02-17a)

**Date:** 2026-02-17
**Round:** 6
**Source report:** `qa/2026-02-17h-improvement-tickets.md`
**Previous action plan:** `tasks/qa-action-plan-2026-02-13a.md` (Round 5)

## Headline Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Satisfaction gap | 1.0 | Flat (0.9 → 1.0) |
| Completion gap | DS1: 6/14, DS3: 7/13, PM1: 5/7, R1: 0/5, E1: 0/1 | — |
| Coverage | 30/45 (67%) | Down from 91% — caused by TEST-21 |
| Blockers | 0 | (2 permission violations, always BLOCKER severity) |
| Permission violations | 2 | PERMISSION-5 new, PERMISSION-1-4 carried |
| New tickets | 4 | 1 PERMISSION, 1 BUG, 1 IMPROVE, 2 TEST |
| Carried (not fixed) | 9 | From Round 5 |
| Finding groups | 2 | FG-1 (language), FG-2 (admin namespace) |

**Key finding:** Coverage dropped from 91% to 67% due to a single test infrastructure issue (TEST-21: app renamed `/clients/` to `/participants/` but 14 scenario configs still use old URLs). Fixing TEST-21 alone restores coverage. The satisfaction gap is essentially flat at 1.0. One new permission violation (over-permission) and a language regression (BUG-24) are the main app-level issues.

**Positive signal:** Zero new blockers in the app itself. BLOCKER-1 (funder URL) partially fixed. The carried PERMISSION-1-4 and FG-2 issues are architectural and need a design task, not a rush fix.

---

## Expert Panel Summary

**Panel:** Accessibility Specialist, UX Designer, Django Developer, Nonprofit Operations Lead

### Key Insights by Expert

**Accessibility Specialist:**
- BUG-24 is a WCAG 3.1.1 Level A violation (same class as BUG-14) — screen readers apply wrong pronunciation model
- Two confirmed Level A violations (BUG-24, BUG-14) mean KoNote cannot claim WCAG 2.1 Level A conformance
- AODA compliance risk for agencies with 50+ employees
- IMPROVE-8 needs investigation — if user-generated content, not a WCAG violation

**UX Designer:**
- BUG-24 is the most user-impactful ticket — PM creating groups is a core workflow
- FG-1 language pattern is alarming — bugs in every round since Round 2, suggesting page-by-page fixes aren't working
- TEST-21 is the highest-leverage fix — one config update restores 14 scenarios
- Coverage drop is the strategic headline

**Django Developer:**
- PERMISSION-5 is a 15-minute fix — add permission check to meetings view
- BUG-24/FG-1 needs systemic middleware refactor, not another page-specific patch
- Proposed: custom `UserLanguageMiddleware` that reads user profile preference before Django's `LocaleMiddleware`
- FG-2 (/admin/ namespace) needs 2–4 hours — should be a design task, not rushed
- TEST-21 is a 20-minute find-and-replace in qa-scenarios

**Nonprofit Operations Lead:**
- BUG-24 erodes trust — third time a language bug has appeared
- PERMISSION-5 is a PIPEDA red flag for over-permission
- FG-2 (PM blocked from self-service admin) affects daily PM workflows — carried twice, needs escalation
- IMPROVE-8 "Safety concern noted" is likely a system-generated alert type, not user content

### Areas of Agreement

1. **TEST-21 is the highest-leverage fix** — 20 minutes restores 14 scenarios (unanimous)
2. **BUG-24 needs a systemic fix** — middleware refactor, not page-specific patch (unanimous)
3. **PERMISSION-5 is a straightforward quick fix** — add permission check (unanimous)
4. **FG-2 needs a design task, not a rush fix** — URL restructuring needs planning (UX Designer + Operations Lead, accepted by all)
5. **IMPROVE-8 is likely a missing .po translation** — confirm then fix (Operations Lead)

### Productive Disagreements

**Priority ordering — TEST-21 vs BUG-24:**
- UX Designer / Django Developer: TEST-21 first (restores visibility, faster)
- Accessibility Specialist / Operations Lead: BUG-24 first (user-facing, Level A)
- **Resolution:** Both in Tier 1. TEST-21 first tactically (20 min, restores detection), BUG-24 immediately after (60 min)

**PERMISSION-5 view audit scope:**
- Django Developer: audit all /events/ views for missing permission checks (30 min extra)
- UX Designer: fix what's found, don't gold-plate
- **Resolution:** Fix PERMISSION-5 specifically. Add backlog task for broader permission audit.

**FG-1 test runner responsibility:**
- Django Developer: test runner should also clear django_language cookie between personas
- Accessibility Specialist: app must be resilient regardless
- **Resolution:** Fix both — app-side middleware (konote-app) AND test runner cookie clearing (konote-qa-scenarios)

### Shared Root Causes

1. **FG-1 — Language persistence / session contamination** (BUG-24, BUG-14, BUG-9, IMPROVE-8): Language preference not reliably bound to user account. Session/cookie state bleeds between personas. Needs middleware refactor — user profile preference must be authoritative.

2. **FG-2 — /admin/ URL namespace blocks PM self-service** (PERMISSION-1, -2, -3, BUG-1): All management pages under /admin/ have blanket admin-only gate. PM has scoped permissions but can't reach pages. Needs URL restructuring — design task.

---

## Priority Tiers

### Tier 1 — Fix Now

**1. TEST-21 — Mass 404s from old /clients/ URLs** (blocks 14 scenarios)
- **Expert reasoning:** Highest-leverage fix across entire round. One config update restores coverage from 67% toward 91%+. Unanimous agreement.
- **Complexity:** Quick fix (20 min) — find-and-replace /clients/ → /participants/ in scenario configs
- **Dependencies:** None
- **Fix in:** konote-qa-scenarios

**2. PERMISSION-5 — Receptionist can access meetings page**
- **Expert reasoning:** Over-permission is more serious than under-permission (PIPEDA 4.7). Nav bar correctly hides link but server-side view doesn't check permission. Quick fix.
- **Complexity:** Quick fix (15 min) — add permission check to meetings view
- **Dependencies:** None
- **Fix in:** konote-app (events views)

**3. BUG-24 + BUG-14 (FG-1) — Language middleware refactor**
- **Expert reasoning:** Third time language persistence has caused bugs. Page-by-page fixes don't work. Needs systemic solution: custom UserLanguageMiddleware that makes user profile preference authoritative, running before Django's LocaleMiddleware.
- **Complexity:** Moderate (60 min) — middleware refactor + remove cookie-based approach + test across personas
- **Dependencies:** Resolves BUG-24, BUG-14, and likely BUG-9 residuals
- **Fix in:** konote-app (middleware, settings)

**4. IMPROVE-8 — Alert text not translated in French interface**
- **Expert reasoning:** "Safety concern noted" is likely a system-generated alert type (not user content). If so, add to .po file. Quick confirmation + fix.
- **Complexity:** Quick fix (10 min) — investigate source, add to .po if system string
- **Dependencies:** None
- **Fix in:** konote-app (locale files or alert model)

**5. TEST-22 — Test credentials visible in search field**
- **Expert reasoning:** Low priority but quick fix alongside TEST-21. Test runner login flow for DS4 targets wrong form field.
- **Complexity:** Quick fix (10 min) — fix CSS selector in test runner login
- **Dependencies:** None
- **Fix in:** konote-qa-scenarios

### Tier 2 — Fix Next (Create Design Task)

**6. FG-2 — /admin/ URL namespace blocks PM self-service**
- **Expert reasoning:** Carried since Round 5. PERMISSION-1/2/3 and BUG-1 all share this root cause. Needs URL restructuring (move management pages to /manage/ or /settings/). Significant architectural change — needs design spec first.
- **Complexity:** Significant (2–4 hours) — URL moves affect templates, redirects, bookmarks, tests
- **Dependencies:** Design spec needed before implementation
- **Fix in:** konote-app (urls, views, templates, middleware)

**7. Broader permission view audit**
- **Expert reasoning:** PERMISSION-5 revealed a gap — meetings view lacked permission check despite nav hiding the link. Other views under /events/ (and elsewhere) may have the same gap.
- **Complexity:** Moderate (30 min audit)
- **Dependencies:** None, but informed by PERMISSION-5 fix

### Tier 3 — Backlog

**8. BLOCKER-1 (carried) — Funder reporting URL**
- Partially fixed in Round 6. Monitor in next evaluation round.

**9. IMPROVE-1 / IMPROVE-2 (carried) — Permission denial page improvements**
- Lower priority. Better 403 pages with actionable suggestions and programme links.
- Natural pairing with FG-2 URL restructuring.

---

## Recommended Fix Order

1. **TEST-21** — Update /clients/ → /participants/ in qa-scenarios configs (20 min)
2. **PERMISSION-5** — Add permission check to meetings view (15 min)
3. **BUG-24 + BUG-14 (FG-1)** — Refactor language middleware (60 min)
4. **IMPROVE-8** — Investigate and translate alert text (10 min)
5. **TEST-22** — Fix DS4 login selector in qa-scenarios (10 min)

**Estimated Tier 1 total:** ~2 hours (1.5h konote-app, 0.5h konote-qa-scenarios)

---

## Items Flagged as Likely Test Artefacts

1. **SCN-047 language** (Omar seeing French dashboard) — almost certainly FG-1 session contamination from test runner, not an app bug
2. **CAL-004 screenshot mismatch** — test configuration issue, not app bug
3. **Duplicate screenshots** — multiple capture passes in test runner, not app-related

---

## Cross-Reference: Previous Ticket Status

From the Round 6 status table:

| Ticket | Description | Status | Action |
|--------|-------------|--------|--------|
| PERMISSION-1 | PM blocked from plan templates admin | NOT FIXED | Part of FG-2 design task |
| PERMISSION-2 | PM blocked from note templates admin | NOT FIXED | Part of FG-2 design task |
| PERMISSION-3 | PM blocked from event types admin | NOT FIXED | Part of FG-2 design task |
| PERMISSION-4 | Executive blocked from audit log | NOT TESTED | No screenshot available |
| BLOCKER-1 | Funder reporting URL 404 | PARTIALLY FIXED | Monitor in next round |
| BUG-1 | PM admin gated behind admin-only | NOT FIXED | Part of FG-2 design task |
| BUG-14 | Language persistence /reports/insights/ | NOT FIXED | Included in FG-1 middleware fix |
| IMPROVE-1 | Permission denial page distinction | NOT FIXED | Tier 3 backlog |
| IMPROVE-2 | Admin denied page — link back | NOT FIXED | Tier 3 backlog |
