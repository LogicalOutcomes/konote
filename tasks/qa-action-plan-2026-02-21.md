# QA Action Plan — Round 7 (2026-02-21)

**Date:** 2026-02-21
**Round:** 7
**Source report:** `qa/2026-02-21-improvement-tickets.md`
**Previous action plan:** `tasks/qa-action-plan-2026-02-17a.md` (Round 6)

## Headline Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Satisfaction gap | 1.22 | Up 0.22 from Round 6 (1.0) — first regression since Round 4 |
| DS3 avg | 3.01 | Down 0.29 from Round 6 (3.30) |
| Coverage | 49/65 (75%) | Up from 67% (Round 6), but down from 91% (Round 5) |
| Blockers | 6 | +6 from Round 6 (0). 5 are unbuilt survey feature or PIPEDA workflows |
| Permission violations | 1 | PERMISSION-1 (calendar feed) — already fixed same-day |
| New tickets | 55 | 1 PERMISSION, 7 BLOCKER, 23 BUG, 13 IMPROVE, 11 TEST |
| Already fixed (same-day) | 13 | See "Already Fixed" section below |
| Remaining for review | 42 | 7 BLOCKER, 14 BUG, 10 IMPROVE, 11 TEST |
| Regressions (0.5+ pts) | 16 | Mostly from language persistence (BUG-1) |
| Finding groups | 12 | FG-S-1 (language) is dominant — 22 scenarios affected |

**Key finding:** The satisfaction gap regressed for the first time since Round 4, driven primarily by one cross-cutting issue: **BUG-1 (language persistence)** which affects 22 of 42 evaluated scenarios. This single bug causes the Language dimension to score 1.0-2.0 across most personas. Fixing BUG-1 alone would likely close the gap by 0.3-0.5 pts.

**Positive signals:**
- 13 tickets were already fixed same-day before this panel convened (ARIA tablist, form validation, dashboard UX, executive filters, offline fallback, etc.)
- Coverage expanded from 45 to 65 scenarios (survey scenarios added)
- Round 6's Tier 1 items (PERMISSION-5, TEST-21) were resolved
- The /manage/ URL restructuring (QA-W59) shipped on 2026-02-18

**Concerning signals:**
- Language persistence (FG-1) has been flagged in every action plan since Round 2 — page-by-page fixes are not working
- 5 survey scenarios all score Red (expected — feature not built)
- 2 new PIPEDA blockers (data export, consent withdrawal) — compliance gap
- BLOCKER-1/2/3 (PM self-service) may indicate the /manage/ move didn't cover all admin functions

---

## Already Fixed (Same-Day, Before Panel)

These 13 tickets were resolved in the "UX + QA Round 7 Fixes" phase on 2026-02-21, after screenshots were captured but before this panel:

| Ticket | Fix | TODO ID |
|--------|-----|---------|
| PERMISSION-1 | Calendar feed settings access control added | PERMISSION-1 |
| BUG-3 | 403 page: removed raw exception, added role-specific messages | BUG-3 |
| BUG-9 + BUG-10 | Executive dashboard: date range filter + CSV export | BUG-9/10 |
| BUG-14 | ARIA tablist on client profile tabs with arrow key nav | BUG-14 |
| BUG-16 | Form validation: novalidate + custom errors with aria-describedby | BUG-16 |
| BUG-17 | Offline fallback page (service worker) | BUG-17 |
| BUG-18 | Task-oriented dashboard layout (reduced info density) | BUG-18 |
| BUG-19 | Dismissable priority items (localStorage, daily reset) | BUG-19 |
| BUG-22 | Group creation pre-selects programme for single-programme users | BUG-22 |
| IMPROVE-2 | "Create New" button in empty search results + result count | IMPROVE-2 |
| IMPROVE-5 | Hidden programmes notice on client profile | IMPROVE-5 |
| IMPROVE-8 | Search result count on participant list | IMPROVE-8 |

**Note:** BLOCKER-5 (keyboard-only workflow) is partially addressed by the BUG-14 fix (ARIA tablist). Remaining issues (tab order, quick note reachability) are in Tier 2.

---

## Expert Panel Summary

**Panel:** Accessibility Specialist, UX Designer, Django Developer, Nonprofit Operations Lead

### Key Insights by Expert

**Accessibility Specialist:**
- BUG-15 (skip-to-content link) is a WCAG 2.4.1 Level A violation — must be fixed before claiming any WCAG conformance level
- BUG-14 fix (ARIA tablist) resolves the most critical part of BLOCKER-5, but tab order through forms still needs work
- BUG-20 (htmx syntax errors) is suspicious — broken HTMX can silently prevent aria-live announcements
- The 5 remaining IMPROVE tickets (9-13) form a coherent accessibility polish bundle — should be done together
- DS3 avg dropping to 3.01 (from 3.30) is concerning even though BUG-14 was the biggest blocker

**UX Designer:**
- BUG-1 (language persistence) is the single most damaging issue — it touches 22 scenarios and makes the entire app feel broken for bilingual users
- This is the fourth round where FG-1 has been flagged. Page-by-page fixes have demonstrably failed. Middleware refactor is overdue.
- BLOCKER-1 may be a false positive — QA-W59 moved pages to /manage/ on Feb 18, but the scenario YAMLs likely still point to /admin/. Verify before coding.
- BLOCKER-6/7 (PIPEDA workflows) are genuinely missing features, not bugs. They need design before implementation.
- BUG-7 (communication from client profile) is a significant UX gap — the feature exists at top-level but is disconnected from client context

**Django Developer:**
- BUG-1 needs a systemic fix: custom `UserLanguageMiddleware` that reads the user profile's `preferred_language` field and calls `translation.activate()` before Django's `LocaleMiddleware`. This makes the user record authoritative, not the cookie.
- BLOCKER-1/2/3 need investigation: the /manage/ namespace exists (QA-W59) but may not cover user management (BLOCKER-2) or audit log (BLOCKER-3) — those were never part of the original move.
- BUG-2 (notes 404 vs 403) is a queryset filter pattern — when permissions restrict the queryset to empty, Django returns 404. Need explicit permission check before queryset filter.
- BUG-20 (htmx syntax errors) — likely `hx-*` attributes with invalid selectors or missing quotes. 10 errors suggests a batch issue, not 10 separate bugs.
- BUG-15 (skip link) is a 15-minute fix in the base template.

**Nonprofit Operations Lead:**
- BUG-1 is a trust issue — bilingual agencies will not adopt a tool that randomly switches languages. This must be resolved before any agency deployment.
- BLOCKER-6/7 (PIPEDA data export and consent withdrawal) are compliance obligations, not nice-to-haves. But they need GK review for data retention rules.
- BLOCKER-2 (PM user management) affects daily operations — PMs must be able to manage their own team without IT tickets.
- The 5 survey BLOCKERs (BLOCKER-4) should be excluded from scoring — they inflate the failure count with a single unbuilt feature.
- 11 TEST tickets represent significant coverage gaps — fixing test infrastructure should be a parallel workstream.

### Areas of Agreement

1. **BUG-1 (language middleware refactor) is the #1 priority** — systemic fix, not another page patch (unanimous)
2. **BLOCKER-1 needs verification before coding** — likely a scenario YAML issue, not an app issue (unanimous)
3. **BUG-15 (skip-to-content) is a quick, mandatory fix** — WCAG Level A, 15 minutes (unanimous)
4. **BLOCKER-4 (surveys) should be excluded from scoring** — inflates failure count (unanimous)
5. **BLOCKER-6/7 need GK review before implementation** — privacy/data retention decisions (Operations Lead + UX Designer, accepted by all)
6. **TEST tickets are a parallel workstream** — fix in qa-scenarios repo, don't mix with app fixes (unanimous)

### Productive Disagreements

**BLOCKER-2/3 (PM user management + audit log) — Tier 1 or Tier 2?**
- Operations Lead: Tier 1 — PMs can't do their jobs without these
- Django Developer: Tier 2 — these are new features (2-4 hours each), not quick fixes
- **Resolution:** Tier 2. These are genuinely new views, not broken existing ones. The /manage/ namespace is ready for them. Plan and build after Tier 1 stabilisation.

**BUG-7 (communication from client) — scope of fix?**
- UX Designer: Full Events/Communications tab on client profile
- Django Developer: Simpler — add "Log Communication" to Actions dropdown, pre-fill client
- **Resolution:** Start with Actions dropdown (Django Developer's approach). If adoption data shows users want a full tab, add it later. Avoid over-engineering.

**IMPROVE-9 through 13 (accessibility polish) — individual tickets or bundle?**
- Accessibility Specialist: Bundle — they share the same code paths (form templates, search results, participant list)
- UX Designer: Individual — each has different acceptance criteria
- **Resolution:** Bundle in the action plan for scheduling, but track acceptance criteria individually. One PR, multiple test verifications.

### Shared Root Causes (Finding Groups)

| Group | Root Cause | Primary Ticket | Scenario Count |
|-------|-----------|---------------|---------------|
| FG-S-1 | Language preference not persisted | BUG-1 | 22 scenarios |
| FG-S-2 | /admin/ URL blocks PM scoped permissions | BLOCKER-1/2/3 | 8 scenarios |
| FG-S-5 | Surveys module not implemented | BLOCKER-4 | 5 scenarios |
| FG-S-6 | PIPEDA privacy workflows missing | BLOCKER-6/7 | 3 scenarios |
| FG-S-7 | Keyboard/ARIA on client profile | BUG-14 (fixed) + BLOCKER-5 | 4 scenarios |
| FG-S-9/10 | Test runner URL/navigation failures | TEST-1 through 11 | 12+ scenarios |

---

## Priority Tiers

### Tier 1 — Fix Now (5 items)

**1. BUG-1 — Language middleware refactor (systemic)**
- **Expert reasoning:** Most pervasive issue in Round 7 (22 scenarios). Fourth consecutive round flagged. Page-by-page fixes have demonstrably failed. Needs custom `UserLanguageMiddleware` that makes user profile `preferred_language` authoritative, overriding cookie/session state.
- **Complexity:** Moderate (2-3 hours) — middleware + remove cookie-based approach + test all personas
- **Dependencies:** None
- **Fix in:** konote-app (middleware, settings, user model)
- **Acceptance:** Language dimension scores 4.0+ for all personas in Round 8

**2. BLOCKER-1 verification — Verify /manage/ routes cover PM self-service**
- **Expert reasoning:** QA-W59 moved PM management pages to /manage/ on 2026-02-18. The evaluation on 2026-02-21 still found BLOCKER-1. Most likely cause: scenario YAMLs still point to /admin/ URLs. Verify before writing any new code.
- **Complexity:** Quick (30 min) — check /manage/ routes, update scenario YAMLs if needed
- **Dependencies:** None
- **Fix in:** Verify konote-app routes; update konote-qa-scenarios YAMLs
- **Acceptance:** PM1 can access /manage/plan-templates/, /manage/note-templates/, /manage/event-types/

**3. BUG-15 — Add skip-to-content link to base template**
- **Expert reasoning:** WCAG 2.4.1 Level A violation. Every page requires a mechanism to bypass repeated navigation. Quick fix in base template.
- **Complexity:** Quick (15 min) — add visually-hidden skip link before nav in base template
- **Dependencies:** None
- **Fix in:** konote-app (base template, CSS)
- **Acceptance:** First Tab press on any page shows "Skip to main content" link

**4. BUG-2 — Notes URL returns 404 instead of 403 for receptionist**
- **Expert reasoning:** Misleading error — receptionist thinks the page doesn't exist rather than understanding it's restricted. The permission-filtered queryset returns empty, causing 404 instead of explicit 403.
- **Complexity:** Quick (30 min) — add explicit permission check before queryset filter in notes view
- **Dependencies:** None
- **Fix in:** konote-app (notes view)
- **Acceptance:** Receptionist at /participants/{id}/notes/ sees styled 403 with role explanation

**5. BUG-20 — Fix htmx:syntax:error messages on create-participant page**
- **Expert reasoning:** 10 syntax errors suggest broken `hx-*` attributes. Can silently prevent dynamic form behavior and aria-live announcements. Quick audit of HTMX attributes on the form.
- **Complexity:** Quick (30 min) — audit and fix all hx-* attributes on create-participant template
- **Dependencies:** None
- **Fix in:** konote-app (participant create template)
- **Acceptance:** Zero htmx:syntax:error messages in browser console

### Tier 2 — Fix Soon (11 items)

**6. BLOCKER-5 remaining — Keyboard tab order and quick note reachability**
- **Expert reasoning:** BUG-14 fix (ARIA tablist) resolved the tab bar, but the create-participant form tab order and quick note keyboard reachability still need work. Bundle with IMPROVE-9/10.
- **Complexity:** Moderate (1-2 hours)
- **Fix in:** konote-app (create-participant template, client profile actions)

**7. BUG-5 + BUG-6 — French receptionist fixes (search + create button)**
- **Expert reasoning:** BUG-5 blocks R2's entire scenario. BUG-6 blocks R2-FR's entire scenario. Both affect receptionist workflows. BUG-5 may be a programme scoping bug or test data issue. BUG-6 is a conditional rendering gap.
- **Complexity:** Moderate (1 hour combined)
- **Fix in:** konote-app (participant search, landing page template)

**8. BUG-7 — Communication quick-log from client profile**
- **Expert reasoning:** Core workflow gap — communication logging is only accessible from top-level Meetings nav, disconnected from client context. Add "Log Communication" to client profile Actions dropdown.
- **Complexity:** Moderate (1-2 hours)
- **Fix in:** konote-app (client profile template, communication views)

**9. BUG-8 — Calendar feed URL generation**
- **Expert reasoning:** "Set up my calendar link" button doesn't generate a feed URL. POST handler may be failing silently.
- **Complexity:** Moderate (1 hour)
- **Fix in:** konote-app (calendar feed views)

**10. BUG-4 — Phone update confirmation message**
- **Expert reasoning:** No visible save confirmation after editing phone number. Django messages framework may not be firing after the form save.
- **Complexity:** Quick (30 min)
- **Fix in:** konote-app (participant edit view)

**11. BUG-11 + BUG-12 — Self-service admin pages and funder report**
- **Expert reasoning:** Note templates and event types pages may not exist at /manage/ yet (BUG-11). Funder report lacks funder profile selector (BUG-12). Both are PM workflow gaps.
- **Complexity:** Moderate (2 hours combined)
- **Fix in:** konote-app (manage views, funder report template)

**12. IMPROVE-3 — Hide admin dropdown for executives**
- **Expert reasoning:** Executive role sees "Admin" nav item they cannot access. Nav should respect permissions.
- **Complexity:** Quick (20 min)
- **Fix in:** konote-app (base template nav logic)

**13. Accessibility polish bundle (IMPROVE-9, 10, 11, 12, 13)**
- **Expert reasoning:** Five related a11y improvements sharing common code paths: form tab order for screen readers, filter Tab order, status dropdown auto-open, aria-live verification, colour-only status indicators.
- **Complexity:** Moderate (2 hours as bundle)
- **Fix in:** konote-app (participant templates, search forms, list templates)

**14. BUG-23 — Settings page route for staff**
- **Expert reasoning:** /settings/ returns 404 for staff. Settings may be at /accounts/settings/ or /profile/. Either fix the route or update the scenario YAML.
- **Complexity:** Quick (15 min) — investigate and fix
- **Fix in:** konote-app or konote-qa-scenarios (depends on root cause)

**15. BLOCKER-2 — Scoped user management for PMs**
- **Expert reasoning:** New feature — PMs need to manage staff in their programme without IT tickets. The /manage/ namespace is ready for it. Significant feature work.
- **Complexity:** Significant (3-4 hours) — new views, templates, permission checks
- **Dependencies:** /manage/ namespace (done in QA-W59)
- **Fix in:** konote-app

**16. BLOCKER-3 — Scoped audit log for PMs**
- **Expert reasoning:** New feature — PMs need programme-filtered audit log for quarterly QA reviews. Simpler than BLOCKER-2 since audit data already exists.
- **Complexity:** Moderate (2 hours) — new view with programme filter
- **Dependencies:** None
- **Fix in:** konote-app

### Tier 3 — Backlog (7 items)

**17. BLOCKER-4 — Surveys module not built**
- Already tracked as SURVEY1 in Parking Lot. Exclude 5 survey scenarios (SCN-111 through SCN-117) from satisfaction scoring until feature ships.

**18. BLOCKER-6 — PIPEDA data export from client profile** — GK reviews privacy workflow
- New feature: "Export Data" action on client profile for PIPEDA Section 8 access requests. Needs design for what data categories to include and output format.

**19. BLOCKER-7 — Consent withdrawal workflow** — GK reviews privacy/data retention
- New feature: consent withdrawal wizard on client profile. Must define what gets deleted vs. retained (funder retention rules). PIPEDA compliance obligation.

**20. IMPROVE-7 — Executive compliance report** — GK reviews reporting methodology
- Aggregate compliance dashboard for executives: privacy request counts, processing times, completion status. No individual PII exposed.

**21. IMPROVE-4 — Quarterly date range on funder report**
- Enhancement: add quarterly presets (Q1-Q4) and custom date range to funder report form.

**22. BUG-13 — Accented character preservation (needs verification)**
- May be test data issue. Needs manual verification that Unicode characters survive create/save/display cycle. Low confidence that this is an actual bug.

**23. BUG-21 — Form data preservation after validation error (needs verification)**
- Medium confidence. May be test runner artefact (screenshot timing). Needs manual verification of Django form re-rendering with submitted data.

---

## Test Infrastructure Issues (qa-scenarios repo)

11 TEST tickets identified. These should be fixed in the konote-qa-scenarios repo as a parallel workstream before Round 8:

| Ticket | Issue | Priority |
|--------|-------|----------|
| TEST-1 | SCN-015 batch note workflow not executed | High — blocks DS1 batch note coverage |
| TEST-2 | SCN-026 navigation failed (stuck on landing page) | High — blocks R2-FR coverage |
| TEST-3 | URL placeholders ({alert_id}, {group_id}) not resolved | High — blocks 3 scenarios |
| TEST-4 | SCN-082 meeting data not seeded | Medium — blocks PM meeting dashboard |
| TEST-5 | SCN-084 communication URL placeholders not resolved | Medium — blocks consent guardrail |
| TEST-6 | SCN-046 session timeout cannot be simulated | Low — consider manual testing |
| TEST-7 | SCN-049 Playwright timing failure | Medium — PIPEDA shared device test |
| TEST-8 | SCN-048 missing consent for test client | Medium — blocks slow-network coverage |
| TEST-9 | SCN-058 wrong page navigation (create instead of note) | Medium — blocks ADHD scenario |
| TEST-10 | SCN-059 wrong login URL (/auth/ vs /accounts/) | High — quick fix |
| TEST-11 | SCN-059 note creation incomplete | Medium — blocks voice navigation |

**Recommended order:** TEST-10 (quick URL fix), TEST-3/5 (placeholder resolution), TEST-1/2 (navigation fixes), then TEST-4/8 (data seeding).

---

## Recommended Fix Order

### Tier 1 (estimated 4-5 hours total)

1. **BUG-1** — Language middleware refactor (2-3 hours)
2. **BLOCKER-1 verify** — Check /manage/ routes, update scenario YAMLs (30 min)
3. **BUG-15** — Skip-to-content link (15 min)
4. **BUG-2** — Notes 404 to 403 (30 min)
5. **BUG-20** — htmx syntax errors (30 min)

### Tier 2 (estimated 12-15 hours total, across multiple sessions)

6. BUG-5 + BUG-6 (French receptionist fixes)
7. BUG-4 (phone update confirmation)
8. BUG-23 (settings route)
9. IMPROVE-3 (hide admin nav for executives)
10. BUG-7 (communication quick-log from client)
11. BUG-8 (calendar feed generation)
12. BUG-11 + BUG-12 (self-service pages + funder report)
13. BLOCKER-5 + IMPROVE-9/10 (keyboard accessibility)
14. IMPROVE-11/12/13 (ARIA polish)
15. BLOCKER-2 (scoped user management)
16. BLOCKER-3 (scoped audit log)

---

## Cross-Reference: Previous Ticket Status

| Ticket (Round 6) | Description | Status in Round 7 |
|-------------------|-------------|-------------------|
| PERMISSION-5 | Receptionist access to meetings page | FIXED (confirmed in Round 7) |
| BUG-24 / FG-1 | Language persistence | NOT FIXED — resurfaced as BUG-1 (worse: 22 scenarios) |
| IMPROVE-8 (Round 6) | Alert text not translated | Likely subsumed by BUG-1 language fix |
| TEST-21 | Mass 404s from /clients/ URLs | FIXED — coverage restored |
| TEST-22 | Test credentials in search field | NOT VERIFIED — DS4 scenario still fails (TEST-10) |
| FG-2 | /admin/ namespace blocks PM | PARTIALLY FIXED — QA-W59 moved pages, but BLOCKER-2/3 show gaps remain |
| PERMISSION-1-4 (carried) | Various permission violations | PERMISSION-1 (calendar) fixed. Others: BLOCKER-1 (verify), BLOCKER-2/3 (new features needed) |
| BLOCKER-1 (carried) | Funder reporting URL | NOT VERIFIED in Round 7 tickets |
| IMPROVE-1/2 (carried) | Permission denial page improvements | BUG-3 fixed (403 page), IMPROVE-6 partially addressed |

---

## Satisfaction Gap Trend

| Round | Date | Gap | DS3 | Coverage |
|-------|------|-----|-----|----------|
| 1 | 2026-02-07 | 2.3 | 1.5 | 69% |
| 2b | 2026-02-08 | 1.5 | 2.0 | 50% |
| 2c | 2026-02-08 | 1.3 | 1.9 | 75% |
| 3 | 2026-02-09 | 1.4 | — | 75% |
| 4 | 2026-02-12 | 1.3 | 2.9 | 63% |
| 5 | 2026-02-13 | 0.9 | 3.2 | 91% |
| 6 | 2026-02-17 | 1.0 | 3.3 | 67% |
| **7** | **2026-02-21** | **1.22** | **3.01** | **75%** |

The gap regression from 1.0 to 1.22 is primarily driven by BUG-1 (language persistence) affecting the Language dimension across 22 scenarios. Excluding the 5 unbuilt survey scenarios would reduce the gap further. The 13 same-day fixes (ARIA, dashboard, offline, etc.) are not yet reflected in scores.

---

*Generated by 4-expert panel review — 2026-02-21*
*55 tickets filed, 13 already fixed, 42 analysed*
*5 Tier 1 (fix now), 11 Tier 2 (fix soon), 7 Tier 3 (backlog), 11 TEST (qa-scenarios)*
