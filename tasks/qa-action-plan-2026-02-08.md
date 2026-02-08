# QA Action Plan — Round 2c (2026-02-08)

**Date:** 2026-02-08
**Round:** 2c (fifth evaluation)
**Source report:** `qa/2026-02-08d-improvement-tickets.md`
**Satisfaction report:** `konote-qa-scenarios/reports/2026-02-08d-satisfaction-report.md`

## Headline Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Satisfaction gap | 1.3 | Down from 2.3 → 1.5 → 1.3 |
| Worst persona | DS3 (Amara, screen reader) 1.9 | — |
| Coverage | 24/32 (75%) | Up from 50% |
| Active tickets | 13 | Unchanged (0 new, 0 closed this round) |
| Blockers | 0 confirmed, 2 need verification | — |

**Key finding:** BUG-7, BUG-9, BUG-10 were committed as fixed (45db041, merged via PR #37) but evaluation says NOT FIXED. Likely a deployment timing issue — screenshots taken at 14:40 may predate Railway deploy. **Re-test before writing code.**

---

## Expert Panel Summary

**Panel:** Accessibility Specialist, UX Designer, Django Developer, Nonprofit Operations Lead

### Key Insights by Expert

**Accessibility Specialist:**
- DS3 score of 1.9 means screen reader users are being failed
- BLOCKER-1/2 are potential Level A violations — must verify manually before anything else
- BUG-10 (tab order) is WCAG 2.4.3 Level A — form is unusable, not just inconvenient
- BUG-6 (blank page) has zero accessibility — no feedback for assistive technology

**UX Designer:**
- BUG-7 + IMPROVE-5 are two halves of the same workflow — ship together
- BUG-8/9/11 are experientially one problem: "French doesn't work"
- Quick design wins: IMPROVE-5 (flash message), BUG-3 (CSS width), IMPROVE-1 (template text)
- BUG-13 (accent search) will be discovered in the first week of real use

**Django Developer:**
- BUG-7/9/10 likely already fixed — re-test before coding
- BUG-8 (untranslated strings) is a .po file addition — quick fix
- BUG-11 (program names) is architecturally different — DB content, not .po strings
- Recommended `name_fr` quick hack for BUG-11; Phase G replaces it later
- BUG-13 needs PostgreSQL `unaccent` extension + Django lookup

**Nonprofit Operations Lead:**
- BUG-7 destroys trust: caseworker in front of client sees 404
- BUG-13 is daily friction for Franco-Ontarian client names
- French cluster matters for Ontario funder reporting on bilingual capacity
- IMPROVE-7 (onboarding) is nice-to-have — a help link is sufficient for now

### Areas of Agreement

1. **Verify BUG-7/9/10 deployment first** — all four experts agree
2. **BLOCKER-1/2 must be manually verified** — 10 minutes with keyboard
3. **BUG-7 + IMPROVE-5 should ship together** — redirect + confirmation
4. **BUG-8/9/11 are the "French experience" cluster** — coordinated effort
5. **BUG-13 is essential** for Canadian bilingual app
6. **IMPROVE-7 moves to Tier 3** — help link sufficient for now

### Disagreements Resolved

- **BUG-11 approach:** `name_fr` field now (quick), Phase G TranslatableMixin later
- **BUG-6 priority:** Moderate (Tier 2) — simple JS handler, not full service worker

### Shared Root Causes

1. **French experience cluster** (BUG-8 + BUG-9 + BUG-11): Three symptoms, two root causes — (a) cookie/middleware for persistence, (b) translation coverage for strings/content
2. **Create workflow** (BUG-7 + IMPROVE-5): Redirect target + success feedback — one code change
3. **Form accessibility** (BUG-10 + IMPROVE-6 + BLOCKER-1/2): All relate to keyboard/AT interaction with forms

---

## Priority Tiers

### Pre-Work — Verify Before Coding (20 min)

| Action | Time | Notes |
|--------|------|-------|
| Manually test BLOCKER-1 (skip link) with keyboard | 10 min | Tab through from page load — does focus reach content? |
| Manually test BLOCKER-2 (post-login focus) with keyboard | 10 min | After login, where does first Tab go? |
| Re-test BUG-7, BUG-9, BUG-10 against current deployment | — | Re-run scenarios or manually test. If fixed, close. |

### Tier 1 — Fix Now

**1. BUG-10 — Tab order mismatch on create form** (if still broken after re-test)
- **Expert reasoning:** WCAG 2.4.3 Level A violation. #1 driver of DS3 satisfaction score (1.9). Data ends up in wrong fields = data integrity risk.
- **Complexity:** Quick fix (15 min) — verify DOM order matches visual order, remove any explicit tabindex overrides
- **Dependencies:** Unblocks DS3 and keyboard-user scenarios
- **Task ID:** QA-W9

**2. BUG-7 + IMPROVE-5 — 404 after create + success confirmation** (coupled fix, if BUG-7 still broken after re-test)
- **Expert reasoning:** Core intake workflow is broken. "Trust destruction" — caseworker in front of client sees error. IMPROVE-5 completes the fix (redirect without feedback is still confusing).
- **Complexity:** Quick fix (20 min) — correct redirect URL + `messages.success()` after create
- **Dependencies:** BUG-7 fix makes IMPROVE-5 visible (no point confirming if 404)
- **Task ID:** QA-W10

**3. BUG-9 — Language persistence across navigation** (if still broken after re-test)
- **Expert reasoning:** Blocks bilingual workflows. DS2 completion at 33%. French dashboard → English form destroys francophone user experience.
- **Complexity:** Quick fix (15 min) — cookie path or middleware ordering
- **Dependencies:** Unblocks BUG-8 verification (hard to test translation when language keeps switching)
- **Task ID:** QA-W11

### Tier 2 — Fix Next

**4. BUG-13 — Accent-insensitive search**
- **Expert reasoning:** Essential for Canadian bilingual app. Franco-Ontarian names with accents are common. Daily workflow friction.
- **Complexity:** Moderate (45 min) — PostgreSQL `unaccent` extension + Django lookup or Python-side normalization
- **Dependencies:** None
- **Task ID:** QA-W12

**5. BUG-8 — Untranslated system strings in French UI**
- **Expert reasoning:** Part of French experience cluster. "Safety concern noted" in English on French page is confusing.
- **Complexity:** Quick fix (20 min) — find untranslated strings, add to .po, run translate_strings
- **Dependencies:** BUG-9 fix helps verify (language must persist to see translations)
- **Task ID:** QA-W13

**6. BUG-12 — New Participant button visible to Front Desk on home page**
- **Expert reasoning:** Permission inconsistency. Button visible on home but hidden on list page. Confusing UX.
- **Complexity:** Quick fix (10 min) — template conditional `{% if perms.clients.add_clientfile %}`
- **Dependencies:** None
- **Task ID:** QA-W14

**7. BUG-6 — Blank page on network failure**
- **Expert reasoning:** Zero UX, zero accessibility. No error, no recovery path. Affects all users.
- **Complexity:** Moderate (30 min) — JS offline handler + friendly error message. NOT a full service worker/PWA.
- **Dependencies:** None
- **Task ID:** QA-W15

**8. BUG-11 — Program names not translated to French**
- **Expert reasoning:** French experience cluster. DB content (not .po strings) — requires model change.
- **Complexity:** Moderate (60 min) — add `name_fr` field to Program model + migration + template conditional. Phase G TranslatableMixin replaces this later.
- **Dependencies:** None, but best done after BUG-9 (language persistence)
- **Task ID:** QA-W16

### Tier 3 — Backlog

**9. BUG-3 — Audit log filter truncation**
- **Expert reasoning:** Minor cosmetic issue in admin-only view. "All acti..." truncated.
- **Complexity:** Quick fix (10 min) — CSS min-width on select element
- **Task ID:** QA-W17

**10. IMPROVE-1 — Settings cards missing status (2 remaining)**
- **Expert reasoning:** Instance Settings and Demo Accounts cards lack status indicators. Admin-only.
- **Complexity:** Quick fix (15 min) — add status text to 2 template cards
- **Task ID:** QA-W18

**11. IMPROVE-7 — Onboarding guidance for new users**
- **Expert reasoning:** Panel consensus: help link is sufficient for now. Full onboarding wizard is nice-to-have.
- **Complexity:** Moderate (60 min) — first-run detection + dismissible banner or help link
- **Task ID:** QA-W19

**12. IMPROVE-6 — Reduce form tab stops**
- **Expert reasoning:** Not yet tested. Excessive tab stops burden keyboard users. Carry forward.
- **Complexity:** Moderate (30 min) — tabindex audit, skip non-essential fields
- **Task ID:** QA-W20

---

## Recommended Fix Order

1. **Verify** BLOCKER-1 + BLOCKER-2 manually (keyboard test)
2. **Re-test** BUG-7, BUG-9, BUG-10 against current deployment
3. Fix BUG-10 if still broken (tab order — QA-W9)
4. Fix BUG-7 + IMPROVE-5 together if BUG-7 still broken (redirect + confirmation — QA-W10)
5. Fix BUG-9 if still broken (language persistence — QA-W11)
6. Fix BUG-13 (accent search — QA-W12)
7. Fix BUG-8 (untranslated strings — QA-W13)
8. Fix BUG-12 (button permission — QA-W14)
9. Fix BUG-6 (offline error page — QA-W15)
10. Fix BUG-11 (program name_fr — QA-W16)
11. Fix BUG-3, IMPROVE-1 (cosmetic — QA-W17, QA-W18)
12. Address IMPROVE-7, IMPROVE-6 when convenient (QA-W19, QA-W20)

---

## Test Environment Fixes (separate from app work)

These affect QA coverage reliability, not the app itself. Fix in `konote-qa-scenarios` repo.

- **TEST-1:** Update SCN-010 scenario YAML — search term doesn't match seed data name
- **TEST-2:** Update CAL-005 URL — /reports/outcomes/ returns 404 for DS3 role
- **TEST-3:** Ensure fresh browser context per persona — set `django_language=en` cookie explicitly

---

## Items NOT Filed as Tickets

The evaluation flagged these but the panel agrees they're not app issues:
- Participant count of 83 — test runner artifact
- Record IDs all blank — optional field, not populated in test data
- Consent compliance at 2% — test data artifact (83 participants, 2 with consent)
- "Safety concern noted" visible to Front Desk — needs product decision (may be intentional)
