# QA Action Plan — Round 7 Page Audit (2026-02-21)

**Date:** 2026-02-21
**Type:** Page audit (Pipeline B, Round 3)
**Source report:** `qa/2026-02-21a-page-audit-tickets.md`
**Previous page audit:** Round 2 (2026-02-13)
**Companion plan:** `tasks/qa-action-plan-2026-02-21.md` (Round 7 scenario evaluation)

## Headline Metrics

| Metric | Value | Trend (vs. Round 2 page audit) |
|--------|-------|-------------------------------|
| Pages audited | 11 | Down from 12 (rotating sample) |
| Persona x page evaluations | 38 | Down from 39 |
| Permission violations | 0 | Down from 2 |
| BLOCKER tickets | 6 | Up from 1 |
| BUG tickets | 8 | Down from 10 |
| IMPROVE tickets | 4 | Down from 18 |
| TEST tickets | 3 | New category |
| Pages scoring Red | 5/11 (45%) | — |
| Pages scoring Green | 1/11 (9%) | — |
| Pages not evaluable (404/500) | 6/11 (55%) | — |
| Finding groups | 5 (FG-P-7 through FG-P-11) | — |

**Key finding:** 6 of 11 pages cannot be evaluated because they return 404 or 500 errors. Five are survey pages (feature not deployed to test environment — page inventory updated before code shipped). Two are public-facing pages with raw Django 500 errors, one of which is a **CASL compliance risk** (broken unsubscribe).

**What's different from the scenario evaluation (Round 7):**
- Page audit found **2 new public-facing blockers** (BLOCKER-P-3, P-4) not caught by scenarios — public pages have no scenarios yet
- **CASL compliance risk** (BLOCKER-P-4) is net new — the email unsubscribe page has never been evaluated before
- Page audit confirmed **FG-P-9 = FG-S-1** — the French localization failure seen in scenarios is confirmed on 3 more pages
- **8 targeted UX bugs** on existing working pages (comm, plans, groups) — these are precision fixes, not systemic

---

## Expert Panel Summary

**Panel:** Accessibility Specialist, UX Designer, Django Developer, Nonprofit Operations Lead

### Cross-Reference with Round 7 Scenario Action Plan

Before tiering, the panel identified overlaps with the existing `qa-action-plan-2026-02-21.md`:

| Page Audit Ticket | Existing Round 7 Ticket | Status |
|-------------------|------------------------|--------|
| BLOCKER-P-1/P-2 (survey 404s) | BLOCKER-4 / Tier 3 #17 / SURVEY1 | Already tracked — exclude from scoring |
| BLOCKER-P-5 (404 page untranslated) | BUG-1 / QA-R7-BUG1 (language middleware) | Tier 1 in Round 7 — middleware fix will resolve |
| BLOCKER-P-6 (comm-leave-message FR) | BUG-1 / QA-R7-BUG1 | Same — middleware fix will resolve |
| BUG-P-8 (comm-my-messages FR) | BUG-1 / QA-R7-BUG1 | Same — middleware fix will resolve |

**3 tickets (BLOCKER-P-5, P-6, BUG-P-8) are subsumed by QA-R7-BUG1** (language middleware). They need no separate TODO items — when the middleware ships, these will be fixed.

**2 tickets (BLOCKER-P-1, P-2) are already tracked as SURVEY1** in Parking Lot. The survey feature is not built; this is not a regression.

### Key Insights by Expert

**Accessibility Specialist:**
- BUG-P-3 (groups-attendance "--" for screen readers) is a genuine a11y gap — JAWS reads "dash dash" with no semantic meaning. Quick fix with `<abbr>` or `aria-label`.
- BUG-P-7 (no required-field indicator on comm-leave-message) is inconsistent with other forms and fails WCAG 3.3.2 (Labels or Instructions). Simple fix.
- TEST-P-1 (sparse attendance data) blocks the evaluation that this page was specifically selected for — 1x1 data cannot test 96-cell table accessibility.

**UX Designer:**
- BUG-P-1 (plan-goal-create "Add Target" heading) is a direct carry-over from the terminology migration — the heading was missed when "target" was renamed to "goal" elsewhere. 5-minute fix.
- BUG-P-2 (no onboarding for first-time users) is valid but should be scoped carefully — a collapsible helper, not a tutorial. Avoid over-engineering.
- BUG-P-6 (comm-my-messages empty state) and IMPROVE-P-1 overlap — consolidate into one fix: distinguish "no messages yet" from "all messages read" with guidance text.
- IMPROVE-P-2 (progress indicator on goal wizard) is worth doing — DS1c (ADHD) persona loses track in multi-step flows.

**Django Developer:**
- BLOCKER-P-3 and P-4 (public pages returning 500) are likely the same root cause: the survey and communications apps have views that reference objects that don't exist in the test database, and there's no custom `500.html` template. Two fixes needed: (1) fix the underlying bugs, (2) create a styled `500.html`.
- TEST-P-3 (no custom 500 template) is the safety net — even after fixing individual 500s, the template should exist for any future unhandled errors.
- BUG-P-4 (pluralization "1 sessions") is a one-line template fix with `{{ count|pluralize }}`.
- BUG-P-5 (ambiguous "Rate" column) and BUG-P-3 (ambiguous "--") can be fixed together since they're on the same template.

**Nonprofit Operations Lead:**
- **BLOCKER-P-4 (CASL unsubscribe) is the most urgent new finding.** Canadian agencies cannot send emails without a functional unsubscribe mechanism. This is a legal compliance issue, not a UX preference. Even if the email feature is not yet in production, the route exists and must work before any agency enables email communications.
- BLOCKER-P-3 (public survey link 500) affects community trust — a community member clicking a survey link from a flyer sees "server error" and will never try again.
- IMPROVE-P-3 (PIPEDA context on erasure page) is sensible but should be reviewed by GK — the explanation of what gets deleted vs. retained is a policy decision.

### Areas of Agreement

1. **BLOCKER-P-4 (CASL unsubscribe) is the top priority from this audit** — legal compliance, fix before any agency enables email (unanimous)
2. **BLOCKER-P-3 (public survey link 500) should be fixed alongside BLOCKER-P-4** — same root cause category (public pages with no error handling) (unanimous)
3. **BUG-P-1 ("Add Target" heading) is a 5-minute fix** — do it immediately (unanimous)
4. **3 French localization tickets are subsumed by QA-R7-BUG1** — no new TODO items needed (unanimous)
5. **Survey 404s should continue to be excluded from scoring** (unanimous)
6. **TEST-P-3 (custom 500 template) is prerequisite work** — even after fixing individual 500s, the fallback must be styled and bilingual (unanimous)

### Productive Disagreements

**BUG-P-2 (plan-goal-create onboarding) — Tier 1 or Tier 2?**
- UX Designer: Tier 2 — it's a new-user polish item, not a broken workflow
- Operations Lead: Tier 1 — first impressions matter for agency adoption; if DS1b can't understand the form, the agency won't adopt KoNote
- **Resolution:** Tier 2. The form works, and DS1 (experienced user) scores Green (4.0). The onboarding text helps but isn't blocking any workflow. Bundle with BUG-P-1 (heading fix) since they're on the same page.

**IMPROVE-P-3 (PIPEDA context on erasure page) — ticket or GK gate?**
- Django Developer: Simple — add explanatory text, no policy decisions
- Operations Lead: The text about "what gets deleted vs retained" IS a policy decision. GK must review.
- **Resolution:** Add to Tier 3 with GK review gate. The current page works; it just lacks context.

---

## Priority Tiers

### Tier 1 — Fix Now (4 items, 3 are net new)

**1. BLOCKER-P-4 — Fix public unsubscribe page (CASL compliance)**
- **Expert reasoning:** Legal compliance under Canada's Anti-Spam Legislation (S.C. 2010, c. 23, s. 6(2)(c)). The unsubscribe route exists but returns 500. Must work before any agency enables email communications.
- **Complexity:** Moderate (1-2 hours) — fix underlying view error, style the page, add bilingual text, handle invalid/expired tokens
- **Dependencies:** Needs custom 500.html as safety net (TEST-P-3)
- **Fix in:** konote-app (communications views, templates)
- **Acceptance:** Valid token loads unsubscribe confirmation; invalid token shows styled error; page is bilingual; works on mobile
- **GK gate:** No — this is a compliance obligation with clear requirements

**2. BLOCKER-P-3 — Fix public survey link page (500 error)**
- **Expert reasoning:** Public-facing page that community members reach from email/flyer links. Raw 500 destroys trust — they'll never try again. Same category as BLOCKER-P-4 (public pages with no error handling).
- **Complexity:** Moderate (1 hour) — fix underlying view error, handle invalid tokens gracefully
- **Dependencies:** Survey model must exist (it does). Needs custom 500.html as safety net.
- **Fix in:** konote-app (surveys views, templates)
- **Acceptance:** Valid token loads survey form; invalid/expired token shows styled "link not available" page; works on mobile

**3. TEST-P-3 — Create custom styled 500.html template**
- **Expert reasoning:** Safety net for all public-facing pages. Even after fixing BLOCKER-P-3 and P-4, any future unhandled error should show a branded, bilingual page — not raw Django "A server error occurred." This is infrastructure, not a bug fix.
- **Complexity:** Quick (30 min) — create `templates/500.html` with KoNote branding, bilingual text, recovery links
- **Dependencies:** None
- **Fix in:** konote-app (templates/500.html, possibly 400.html and 403.html review)
- **Acceptance:** Triggering a 500 error shows branded, bilingual page with recovery guidance

**4. BUG-P-1 — Fix plan-goal-create heading ("Add Target" → "Add Goal")**
- **Expert reasoning:** Terminology migration artifact. The heading says "Add Target" but the rest of the page says "goal." 5-minute fix in the template. Currently confuses DS1b (first-week users).
- **Complexity:** Quick (5 min) — change h1 text in `goal_create.html`
- **Dependencies:** None
- **Fix in:** konote-app (plans/goal_create.html)
- **Acceptance:** Heading reads "Add a Goal" (or uses `{{ term.goal }}` for configurable terminology)

### Tier 2 — Fix Soon (8 items)

**5. BUG-P-3 + BUG-P-5 — Fix groups-attendance accessibility ("--" and "Rate" column)**
- **Expert reasoning:** Bundle — same template, same page. Replace "--" with `<abbr title="Not recorded">N/R</abbr>` (screen-reader-friendly). Rename "Rate" column to "Attendance Rate" with tooltip.
- **Complexity:** Quick (30 min)
- **Fix in:** konote-app (groups/attendance.html)

**6. BUG-P-4 — Fix "1 sessions" pluralization**
- **Expert reasoning:** One-line fix with Django `pluralize` filter. Also needs French pluralization in blocktrans.
- **Complexity:** Quick (10 min)
- **Fix in:** konote-app (groups/attendance.html)

**7. BUG-P-6 + IMPROVE-P-1 — Improve comm-my-messages empty state**
- **Expert reasoning:** Consolidate — both tickets ask for better empty state guidance. Distinguish "no messages yet" from "all read." Add contextual guidance ("Messages from colleagues will appear here").
- **Complexity:** Quick (20 min)
- **Fix in:** konote-app (communications/my_messages.html)

**8. BUG-P-7 — Add required-field indicator to comm-leave-message**
- **Expert reasoning:** Consistency with other forms. Add asterisk or "(required)" to textarea label. Add `aria-required="true"` to the textarea.
- **Complexity:** Quick (10 min)
- **Fix in:** konote-app (communications/leave_message.html)

**9. BUG-P-2 — Add onboarding context to plan-goal-create**
- **Expert reasoning:** First-time users (DS1b) need a 1-2 sentence explanation: "A goal is something [client name] wants to achieve." Should be collapsible/dismissible so experienced users aren't cluttered.
- **Complexity:** Quick (20 min) — add collapsible helper text
- **Fix in:** konote-app (plans/goal_create.html)

**10. IMPROVE-P-2 — Add step indicator to goal creation wizard**
- **Expert reasoning:** DS1c (ADHD persona) loses track in multi-step workflows. "Step 1 of 2" text at the top of each wizard page.
- **Complexity:** Quick (15 min)
- **Fix in:** konote-app (plans/goal_create.html, goal_shape.html)

**11. TEST-P-1 — Seed groups-attendance with full data (8+ members, 12+ sessions)**
- **Expert reasoning:** This page was specifically selected for screen reader table accessibility evaluation. 1x1 data cannot test the 96-cell matrix that DS3 would encounter in real use.
- **Complexity:** Moderate (1 hour)
- **Fix in:** konote-qa-scenarios test runner (data seeding)

**12. TEST-P-2 — Seed comm-my-messages populated state with actual messages**
- **Expert reasoning:** "Populated" screenshots are identical to "default" — test runner didn't seed messages before capture.
- **Complexity:** Moderate (30 min)
- **Fix in:** konote-qa-scenarios test runner (data seeding)

### Tier 3 — Backlog (3 items)

**13. IMPROVE-P-3 — Add PIPEDA compliance context to admin-erasure-requests** — GK reviews privacy/data retention
- The current page works but lacks explanation of what erasure means, what gets deleted vs. retained. This is a policy decision requiring GK review.

**14. IMPROVE-P-4 — Replace decorative element on erasure empty state**
- Low priority cosmetic fix — circular decoration could be mistaken for a spinner. Replace with static icon.

**15. Already tracked — no new tickets needed**
- BLOCKER-P-1/P-2 (survey 404s) → already SURVEY1 in Parking Lot
- BLOCKER-P-5/P-6, BUG-P-8 (French localization) → subsumed by QA-R7-BUG1 (language middleware)

---

## Deduplication Summary

| This Audit | Existing TODO Item | Action |
|------------|-------------------|--------|
| BLOCKER-P-1/P-2 (survey 404s) | SURVEY1 (Parking Lot) | No new item — feature not built |
| BLOCKER-P-5 (404 page FR) | QA-R7-BUG1 (Tier 1) | No new item — middleware fix covers it |
| BLOCKER-P-6 (comm-leave-message FR) | QA-R7-BUG1 (Tier 1) | No new item — middleware fix covers it |
| BUG-P-8 (comm-my-messages FR) | QA-R7-BUG1 (Tier 1) | No new item — middleware fix covers it |

**Net new items for TODO.md: 14** (4 Tier 1, 8 Tier 2, 2 Tier 3)

---

## Recommended Fix Order

### Tier 1 (estimated 2-3 hours total)

1. **TEST-P-3** — Custom 500.html (30 min) — prerequisite for BLOCKER-P-3/P-4
2. **BLOCKER-P-4** — Public unsubscribe / CASL fix (1-2 hours)
3. **BLOCKER-P-3** — Public survey link fix (1 hour)
4. **BUG-P-1** — Goal heading terminology (5 min)

### Tier 2 (estimated 3-4 hours total)

5. BUG-P-3 + BUG-P-5 — Groups attendance a11y (30 min)
6. BUG-P-4 — Pluralization fix (10 min)
7. BUG-P-6 + IMPROVE-P-1 — Messages empty state (20 min)
8. BUG-P-7 — Required-field indicator (10 min)
9. BUG-P-2 — Goal onboarding text (20 min)
10. IMPROVE-P-2 — Goal wizard step indicator (15 min)
11. TEST-P-1 — Groups data seeding (1 hour, qa-scenarios repo)
12. TEST-P-2 — Messages data seeding (30 min, qa-scenarios repo)

---

## Cross-Method Validation

This page audit confirms and extends findings from the Round 7 scenario evaluation:

| Finding Group | Scenario Eval | Page Audit | Confirmed? |
|---------------|--------------|------------|-----------|
| FG-S-1 (language persistence) | 22 scenarios | FG-P-9 (3 more pages) | Yes — systemic |
| FG-S-3 (surveys not built) | 5 scenarios Red | FG-P-7 (5 pages 404) | Yes — same root cause |
| FG-S-8 (test data gaps) | 12+ scenarios | FG-P-10 (2 pages) | Yes — parallel workstream |
| FG-P-8 (public pages 500) | Not caught | 2 pages | **Net new** — scenarios don't cover unauthenticated public pages |
| FG-P-11 (goal terminology) | Not caught | 1 page | **Net new** — scenario didn't examine heading text |

**The page audit's biggest unique contribution:** discovering the public-facing 500 errors (BLOCKER-P-3, P-4) that scenarios missed because there are no unauthenticated scenarios yet.

---

*Generated by 4-expert panel review — 2026-02-21*
*21 tickets filed, 5 deduplicated against Round 7 scenario plan, 14 net new for TODO*
*4 Tier 1 (fix now), 8 Tier 2 (fix soon), 2 Tier 3 (backlog), 2 TEST (qa-scenarios)*
