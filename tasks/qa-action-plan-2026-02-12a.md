# QA Action Plan — Round 4 (2026-02-12a)

**Date:** 2026-02-12
**Round:** 4
**Source report:** `qa/2026-02-12a-improvement-tickets.md`
**Previous action plan:** `tasks/qa-action-plan-2026-02-08.md` (Round 2c)

## Headline Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Average score | 3.04 | — |
| Satisfaction gap | 1.3 | Flat (1.3 → 1.4 → 1.3) |
| Worst personas | E1, DS3 | DS3 avg 2.9 |
| Coverage | 25/40 (63%) | Down from 75% (denominator increased to 40) |
| Blockers | 0 | — |
| Regressions | 0 | — |
| Improvements | 2 | CAL-004 +1.2, SCN-040 +0.6 |
| Permission violations | 0 | — |
| New tickets | 6 | 1 bug, 5 test infrastructure |
| Fixed tickets | 6 | BUG-7, BUG-10, BUG-12, BUG-6, TEST-2, TEST-4 |
| Bands | 2 green, 14 yellow, 9 orange, 0 red | — |

**Key finding:** Only 1 of 6 new tickets is an actual app bug (BUG-14). The other 5 are test infrastructure issues causing duplicate screenshots, which suppress coverage. Fixing the test issues would raise coverage significantly toward the 80% target.

**Positive signal:** Six previously filed tickets verified as FIXED this cycle. CAL-004 jumped from 2.8 → 4.0 (+1.2 pts) after the BUG-10 tab order fix. SCN-040 gained +0.6 after BUG-9 language persistence fix.

---

## Expert Panel Summary

**Panel:** Accessibility Specialist, UX Designer, Django Developer, Nonprofit Operations Lead

### Round 1: Independent Analysis

---

#### Accessibility Specialist

**BUG-14** is a WCAG 3.1.1 Language of Page (Level A) failure. When `<html lang="fr">` is set on an English-language page, screen readers (JAWS, NVDA, VoiceOver) will apply French pronunciation rules to English content — making it unintelligible. This is not cosmetic; it's a functional barrier that makes the reports page inaccessible to screen reader users. This is also an AODA obligation under Ontario law.

BUG-14 appears to be a residual case of BUG-9 (language persistence). The BUG-9 fix clearly worked for most pages (verified by improved scores), but the `/reports/insights/` page may use a different template inheritance path or have a view that forces the French locale.

The 5 TEST tickets don't affect accessibility directly, but they prevent us from evaluating accessibility on those scenarios — particularly TEST-8 (mobile viewport) which is critical for touch target sizing (WCAG 2.5.8) and reflow (WCAG 1.4.10).

**Priority recommendation:** BUG-14 first (Level A violation), then TEST-5/8 for coverage.

---

#### UX Designer

The good news: 6 fixes landed and are verified. CAL-004's +1.2 point jump shows that fixing tab order had an outsized UX impact — validates the prioritization from the Round 2c action plan.

BUG-14 is the only user-facing issue this round. It's a single-page problem on `/reports/insights/` and likely a quick fix. The UX impact is severe for screen reader users but invisible to sighted users — making it easy to overlook.

The 5 TEST tickets are actually the bigger strategic concern. They represent **coverage gaps** — scenarios we can't evaluate at all. TEST-5 blocks the entire PM1 funder reporting workflow. TEST-8 blocks all mobile R2 testing. Until these are fixed, we have blind spots in the QA pipeline. The denominator went from 32 to 40 scenarios this round, and coverage dropped from 75% to 63% specifically because these test issues prevent evaluation.

**Quick design wins:** None in app code this round. The wins are in test infrastructure — fixing navigation waits and mobile hamburger menu interactions.

---

#### Django Developer

**BUG-14 root cause analysis:** The base template uses `<html lang="{{ LANGUAGE_CODE }}">`. The `LANGUAGE_CODE` variable is set by Django's `LocaleMiddleware`. If the `/reports/insights/` view or any middleware sets the language before rendering, it will persist. Most likely cause: the BUG-9 fix (cookie-based language persistence) works correctly, but a previous visit to a French page set the `django_language` cookie to `fr`, and the reports view isn't overriding it based on the user's profile preference. Fix: ensure the language middleware reads the user's saved preference first, cookie second.

Alternatively, the QA test runner (DS3 persona Amara) may have navigated French pages earlier in the scenario, and the cookie carried over. This would mean BUG-14 is actually a **test environment artifact** — in production, a user who prefers English would have the cookie set to `en`.

**Complexity estimates:**
- BUG-14: Quick fix (15 min) — verify middleware ordering, check if reports views force locale
- TEST-5: Moderate (30 min) — need to debug PM1 user permissions + URL paths in qa-scenarios repo
- TEST-6/7: Quick fix (10 min each) — add `page.wait_for_url()` after client profile clicks
- TEST-8: Moderate (30 min) — mobile viewport needs hamburger menu interaction before nav
- TEST-9: Moderate (30 min) — offline simulation needs pre-load before throttling

**Shared root cause:** TEST-6 and TEST-7 are the exact same bug (missing wait after navigation click). A single shared helper `navigate_to_client_profile()` fixes both.

---

#### Nonprofit Operations Lead

From a caseworker perspective, this is a good round. The 6 fixed tickets address the most serious workflow issues: the 404 after creating a client (BUG-7) was the top caseworker complaint, and tab order on forms (BUG-10) affected everyone doing data entry.

BUG-14 is invisible to most staff — only screen reader users on the reports page would notice. However, it's an **accessibility compliance liability**. If this agency serves clients with disabilities (many nonprofits do), having an inaccessible reports page undermines the mission.

The test infrastructure tickets don't affect production users at all, but they're important for quality assurance confidence. When a funder asks "how do you assure quality?", being able to show 80%+ scenario coverage is much stronger than 63%.

**Priority recommendation:** BUG-14 for compliance, then test coverage improvements. The carried-forward French translation tickets (BUG-8, BUG-11) remain the biggest outstanding user-experience issue for francophone staff.

---

### Round 2: Cross-Examination

**Accessibility Specialist responds to Django Developer:** The observation that BUG-14 might be a test artifact is important. If the cookie carries over from a French page visit earlier in the scenario, then in real use, an English-preferring user would never see `lang="fr"` on reports. However — the middleware should still respect the user's preference over the cookie. Even if this is a test artifact, the underlying architecture allows `lang="fr"` to appear for users who haven't explicitly chosen French. That's still a WCAG 3.1.1 risk. Fix the middleware regardless.

**Django Developer responds to Accessibility Specialist:** Agreed. The correct fix is: user profile language preference > cookie > Accept-Language header. If the middleware already does this (it should after the BUG-9 fix), then BUG-14 is purely a test environment issue. Either way, we should verify.

**UX Designer responds to Nonprofit Operations Lead:** The carried-forward BUG-8/BUG-11 (French translations) are now the oldest open tickets — filed in Round 2. Every round they remain unfixed is a round where francophone staff see partially-English interfaces. I'd put these ahead of test infrastructure improvements in terms of user impact.

**Nonprofit Operations Lead responds to UX Designer:** Agreed on BUG-8/BUG-11 priority. However, they were filed as separate task IDs (QA-W13, QA-W16) in the last action plan and marked as NOT FIXED. They should be flagged for active work rather than sitting in Coming Up.

---

### Areas of Agreement

1. **BUG-14 is the only app-level fix needed** — all four experts agree
2. **BUG-14 may be a test artifact** but should be fixed in the middleware regardless (Accessibility + Django Developer)
3. **TEST-6/TEST-7 share a root cause** and should be fixed together with a shared helper
4. **BUG-8/BUG-11 (French translations) are overdue** — carried since Round 2, should be escalated from Coming Up to Active Work
5. **Coverage improvement is the strategic priority** — fixing 5 TEST tickets would significantly boost coverage toward 80%

### Disagreements

- **Priority of test fixes vs. French translations:** UX Designer and Nonprofit Ops Lead want BUG-8/BUG-11 prioritized over test infrastructure. Django Developer and Accessibility Specialist prefer fixing test coverage first (to detect real issues faster). **Resolution:** BUG-14 first, then BUG-8/BUG-11 (user-facing), then TEST tickets (pipeline quality). The test tickets are in the qa-scenarios repo anyway, so they can be worked in parallel.

### Shared Root Causes

1. **Language middleware ordering** (BUG-14 + residual BUG-9): The language preference resolution chain needs verification. User preference should take precedence over cookie.
2. **Missing navigation waits** (TEST-6 + TEST-7): Both scenarios fail to wait for page navigation after clicking a client. One shared helper fixes both.
3. **French translation debt** (BUG-8 + BUG-11): Both date from Round 2. BUG-8 is .po file additions, BUG-11 is DB content (name_fr field). Different fix mechanisms but same user impact.

---

## Priority Tiers

### Tier 1 — Fix Now

**1. BUG-14 — `lang="fr"` on `/reports/insights/` page**
- **Expert reasoning:** WCAG 3.1.1 Level A violation. Screen readers apply wrong pronunciation rules, making page unintelligible. AODA compliance risk. Blocks CAL-005 from reaching Green band (would score ~3.7 without language penalty).
- **Complexity:** Quick fix (15 min) — verify language middleware respects user preference over cookie on reports views
- **Dependencies:** Related to BUG-9 (partially fixed). May unblock CAL-005 improvement.
- **Fix in:** konote-app

**2. BUG-8 — French translation gaps (DS2 affected) [CARRIED FROM ROUND 2]**
- **Expert reasoning:** Oldest open ticket. Francophone staff see English strings on French UI. Panel consensus: overdue for active work.
- **Complexity:** Quick fix (20 min) — find untranslated strings, add to .po, run `translate_strings`
- **Dependencies:** None (BUG-9 language persistence is now working for most pages)
- **Fix in:** konote-app

**3. BUG-11 — French translation gaps for program names (PM2-FR affected) [CARRIED FROM ROUND 2]**
- **Expert reasoning:** Oldest open ticket alongside BUG-8. DB content not in .po file — requires model-level translation.
- **Complexity:** Already has `name_fr` field and `translated_name` property (fixed in Round 2c). Verify translations are populated in seed data and admin UI.
- **Dependencies:** None
- **Fix in:** konote-app

### Tier 2 — Fix Next

**4. TEST-5 — SCN-035 all steps produce identical screenshots (PM1 funder reporting)**
- **Expert reasoning:** Blocks entire PM1 persona evaluation. Likely permissions issue or wrong URL paths. Fixing this adds a full scenario to coverage.
- **Complexity:** Moderate (30 min) — debug PM1 user permissions, verify URL paths match scenario YAML
- **Dependencies:** None
- **Fix in:** konote-qa-scenarios

**5. TEST-8 — SCN-047 mobile viewport duplication (R2 mobile)**
- **Expert reasoning:** Mobile testing completely broken. Touch targets and hamburger menu navigation not handled at 375px viewport width.
- **Complexity:** Moderate (30 min) — add hamburger menu open before nav clicks, viewport-specific selectors
- **Dependencies:** None
- **Fix in:** konote-qa-scenarios

**6. TEST-6 / TEST-7 — SCN-020 and SCN-025 duplicate screenshots (client profile navigation)**
- **Expert reasoning:** Quick fix, shared root cause. Both fail to wait for navigation after clicking a client. A shared `navigate_to_client_profile()` helper fixes both.
- **Complexity:** Quick fix (15 min total) — add `page.wait_for_url()` after client click
- **Dependencies:** None
- **Fix in:** konote-qa-scenarios

### Tier 3 — Backlog

**7. TEST-9 — SCN-048 offline simulation producing blank screenshots**
- **Expert reasoning:** Edge case scenario. Offline simulation blocks all resources including base HTML. Lower priority but affects offline UX evaluation.
- **Complexity:** Moderate (30 min) — pre-load page before applying network throttling
- **Dependencies:** None
- **Fix in:** konote-qa-scenarios

---

## Recommended Fix Order

1. **BUG-14** — Fix `lang="fr"` on reports page (konote-app, 15 min)
2. **BUG-8** — Add missing French translations to .po file (konote-app, 20 min)
3. **BUG-11** — Verify program `name_fr` translations are complete (konote-app, 15 min)
4. **TEST-6 + TEST-7** — Add navigation waits with shared helper (konote-qa-scenarios, 15 min)
5. **TEST-5** — Fix PM1 funder reporting scenario (konote-qa-scenarios, 30 min)
6. **TEST-8** — Fix mobile viewport hamburger menu (konote-qa-scenarios, 30 min)
7. **TEST-9** — Fix offline simulation pre-load (konote-qa-scenarios, 30 min)

**Estimated total effort:** ~2.5 hours (45 min konote-app, 1.75 hours konote-qa-scenarios)

---

## Items Flagged as Likely Test Artifacts

The panel noted one item:
- **BUG-14 may be partially a test artifact** — the DS3 persona test runner may carry a `django_language=fr` cookie from earlier scenario steps. In real use, an English-preferring user's profile preference should prevent this. However, the underlying middleware issue should still be fixed to ensure robustness.

---

## Items NOT Filed as Tickets

The evaluation noted these as context, not issues:
- DS3 average of 2.9 — driven primarily by BUG-14 language penalty and carried BUG-8/BUG-11 translation gaps. Fixing these three tickets should raise DS3 noticeably.
- Coverage drop from 75% to 63% — denominator increased from 32 to 40 scenarios. Actual evaluated count went from 24 to 25. Not a regression; the pipeline is testing more scenarios.
- Permissions hash mismatch caveat — stale persona YAML permissions. Run permissions sync before Round 5.

---

## Cross-Reference: Previously Completed Tasks

These QA-W tasks from the Round 2c action plan are now verified FIXED and should be marked complete in TODO.md:

| Task ID | Ticket | Status |
|---------|--------|--------|
| QA-W9 | BUG-10 (tab order) | FIXED — CAL-004 +1.2 improvement |
| QA-W10 | BUG-7 (404 after create) | FIXED — no 404s observed |
| QA-W14 | BUG-12 (front desk button) | FIXED — R1 workflows normal |
| QA-W15 | BUG-6 (offline error page) | FIXED — styled error pages observed |
| QA-W21/QA-W25 | TEST-5 (originally) | FIXED — TEST-2/TEST-4 resolved |

Note: BUG-9 (QA-W11) is PARTIALLY FIXED — most pages resolved but `/reports/insights/` still shows `lang="fr"` (see BUG-14).
