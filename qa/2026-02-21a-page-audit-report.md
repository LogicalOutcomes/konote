# KoNote2 Page Audit Report — 2026-02-21

**Date:** 2026-02-21
**Type:** Rotating sample audit (Round 3)
**Scope:** 11 pages, 38 persona x page evaluations, ~50 screenshots examined
**Methodology:** Multi-pass heuristic evaluation (3 passes per page x persona)
**Screenshots:** From 2026-02-22 capture (914 total, `.pages-manifest.json`)
**Previous audits:** Round 1: 2026-02-09c (all 43 pages), Round 2: 2026-02-13 (12 pages)
**Calibration anchor:** 2026-02-21 satisfaction reports (Round 7)

---

## Executive Summary

This is the third page audit — an 11-page rotating sample focused on **5 brand-new survey pages** (never audited, added in page-inventory v2.1) plus **6 high-impact pages** not covered in Round 2. The results reveal that the survey feature is not yet deployed to the test environment, and two public-facing pages have critical compliance failures.

### Headline Metrics

| Metric | Value | Trend (vs. Round 2) |
|--------|-------|---------------------|
| **Permission violations** | **0** | Down from 2 |
| **BLOCKER tickets** | **6** | Up from 1 |
| **BUG tickets** | **8** | Down from 10 |
| **IMPROVE tickets** | **4** | Down from 18 |
| **TEST tickets** | **3** | New category |
| **Finding groups** | **5** (FG-P-7 through FG-P-11) | — |
| **Pages scoring Red** | **5/11** (45%) | — |
| **Pages scoring Green** | **1/11** (9%) — comm-leave-message for DS1/DS3/PM1 | — |
| **Pages scoring Yellow** | **3/11** (27%) | — |
| **Pages not evaluable (404/500)** | **6/11** (55%) | — |
| **Bilingual compliance** | Still failing — FG-P-9 (systemic, carried from Round 1 BUG-14) | Same |
| **CASL compliance** | **BLOCKER-P-4** — unsubscribe page returns 500 | NEW |

### Top Findings

1. **BLOCKER-P-1: All survey management pages return 404.** survey-list, survey-create, and survey-csv-import all show "Page Not Found" for both PM1 and admin. The survey feature was added to the page inventory (v2.1, 2026-02-21) but the corresponding Django routes are not registered in the running application. **Likely cause:** page inventory updated before feature code was deployed to the test environment. Cross-references FG-S-3 from scenario evaluation (survey feature missing).

2. **BLOCKER-P-2: client-surveys page returns 404.** The `/surveys/participant/1/` route does not resolve for any authorized persona (DS1-DS4, PM1). Staff cannot view or manage participant survey assignments.

3. **BLOCKER-P-3: public-survey-link returns raw Django 500.** Community members clicking a survey link from an email or flyer see "A server error occurred. Please contact the administrator." — no branding, no styling, no recovery path.

4. **BLOCKER-P-4: public-unsubscribe returns raw Django 500 (CASL compliance risk).** The CASL-required email unsubscribe page is non-functional. Under Canada's Anti-Spam Legislation (S.C. 2010, c. 23, s. 6(2)(c)), every commercial electronic message must include a working unsubscribe mechanism. Legal compliance risk.

5. **BLOCKER-P-5: 404 page not translated to French (systemic).** When DS2 or any French-preference user hits a 404, the entire page displays in English. Part of the systemic French localization failure carried since Round 1.

6. **BLOCKER-P-6: comm-leave-message entirely in English for R2-FR.** The leave-message form is untranslated for the French receptionist persona. Part of systemic FG-P-9.

7. **Positive: comm-leave-message is the best-designed form in the app.** Clean permission boundaries (receptionists see only the write-only form — no clinical data, no message history), minimal fields, clear purpose, excellent responsive design. This is the model for how permission-scoped pages should work.

8. **plan-goal-create terminology mismatch.** The heading says "Add Target" but the URL says "goals/create" and the button says "Next: shape this into a goal." Three different framings confuse DS1b (first-week user, Orange band 2.9).

---

## Permission Violations

**None.** All 38 persona x page evaluations passed the permission gate. Notable positives:

- **comm-leave-message (R1, R2-FR):** Receptionists correctly see ONLY a write-only message form. No clinical data, no message history, no staff notes exposed. Exemplary permission boundary.
- **comm-my-messages:** No receptionist screenshots exist — the test runner correctly excluded R1/R2/R2-FR, matching `my_messages: false` in their permission scope.
- **plan-goal-create (PM1):** PM1 is correctly denied access (plan.edit: deny). Well-designed denial page.

---

## Findings by Page

### 1. survey-list (`/manage/surveys/`) — Red (1.0)

**Status:** Page returns 404 for both PM1 and admin.
**Root cause:** Django URL pattern not registered (FG-P-7).
**Cross-method dedup:** Matches FG-S-3 from scenario evaluation.

| Persona | Band | Score | Task Outcome |
|---------|------|-------|-------------|
| PM1 | Red | 1.0 | blocked |
| admin | Red | 1.0 | blocked |

**404 page quality note:** The 404 error page itself is well-designed — clear heading, helpful recovery suggestions, proper visual hierarchy ("Go Back" outlined, "Home" filled), responsive on mobile.

### 2. survey-create (`/manage/surveys/new/`) — Red (1.0)

**Status:** Page returns 404. Same root cause (FG-P-7).

| Persona | Band | Score | Task Outcome |
|---------|------|-------|-------------|
| PM1 | Red | 1.0 | blocked |
| admin | Red | 1.0 | blocked |

### 3. survey-csv-import (`/manage/surveys/import/`) — Red (1.0)

**Status:** Page returns 404. Same root cause (FG-P-7).

| Persona | Band | Score | Task Outcome |
|---------|------|-------|-------------|
| PM1 | Red | 1.0 | blocked |
| admin | Red | 1.0 | blocked |

### 4. client-surveys (`/surveys/participant/1/`) — Red/Orange (avg 2.9)

**Status:** Page returns 404 for all 5 authorized personas. Part of FG-P-7.

| Persona | Band | Score | Task Outcome | Notes |
|---------|------|-------|-------------|-------|
| DS1 | Orange | 3.0 | no | 404 is clear but task impossible |
| DS2 | Orange | 2.4 | no | 404 page entirely in English (BLOCKER-P-5) |
| DS3 | Yellow | 3.0 | no | 404 page accessible but task impossible |
| DS4 | Yellow | 3.1 | no | 404 page voice-accessible |
| PM1 | Yellow | 3.1 | no | Cannot oversee survey data |

**Satisfaction gap:** 0.7 (DS2 at 2.4 vs DS4 at 3.1 — French localization penalty).

### 5. public-survey-link (`/s/<token>/`) — Red (1.3)

**Status:** Raw Django 500 server error. No branding, no styling, no recovery.

| Persona | Band | Score | Task Outcome |
|---------|------|-------|-------------|
| unauthenticated | Red | 1.3 | no |

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Clarity | 1.0 | "A server error occurred" is meaningless to community members |
| Efficiency | 1.0 | Cannot complete survey |
| Feedback | 1.5 | Message exists but not actionable |
| Error Recovery | 1.0 | Complete dead end — no links, no buttons |
| Accessibility | 2.0 | Readable text but no semantic structure |
| Language | 1.5 | English-only, technical jargon |
| Confidence | 1.0 | Community member would never try again |

### 6. public-unsubscribe (`/communications/unsubscribe/<token>/`) — Red (1.2)

**Status:** Raw Django 500 server error. CASL compliance failure.

| Persona | Band | Score | Task Outcome |
|---------|------|-------|-------------|
| unauthenticated | Red | 1.2 | no |

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Clarity | 1.0 | Raw error, no context |
| Efficiency | 1.0 | Cannot unsubscribe (CASL non-compliance) |
| Feedback | 1.0 | No confirmation of any kind |
| Error Recovery | 1.0 | Complete dead end |
| Accessibility | 2.0 | Text readable, no semantic structure |
| Language | 1.5 | English-only |
| Confidence | 1.0 | Maximum frustration — wanted to STOP emails, can't |

### 7. comm-leave-message (`/communications/client/1/leave-message/`) — Green/Orange (avg 3.8)

**Status:** Functional and well-designed. French localization failure for R2-FR.

| Persona | Band | Score | Task Outcome | Notes |
|---------|------|-------|-------------|-------|
| R1 | Green | 4.2 | yes | Clean write-only form, no clinical data visible |
| R2-FR | Orange | 2.5 | partial | Entire page in English — BLOCKER-P-6 |
| DS1 | Green | 4.3 | yes | Big clear buttons, minimal fields |
| DS3 | Green | 4.0 | yes | Accessible heading structure, keyboard operable |
| PM1 | Green | 4.1 | yes | Clear purpose, efficient |

**Satisfaction gap:** 1.8 (R2-FR at 2.5 vs DS1 at 4.3 — French localization is the sole cause).

**Positive findings (model for other pages):**
- Permission boundary is exemplary: receptionists see ONLY the message textarea and send button
- No clinical data, no message history, no staff notes exposed
- Minimal cognitive load (single purpose, single action)
- Responsive: mobile layout stacks cleanly, touch targets adequate

### 8. comm-my-messages (`/communications/my-messages/`) — Yellow (avg 3.3)

**Status:** Functional but "populated" screenshots show empty inbox (test data seeding failure).

| Persona | Band | Score | Task Outcome | Notes |
|---------|------|-------|-------------|-------|
| DS1 | Yellow | 3.5 | partial | Empty state lacks guidance |
| DS1c | Yellow | 3.2 | partial | Low density accidentally ADHD-friendly |
| DS2 | Orange | 2.5 | partial | Page in English despite FR preference |
| DS3 | Yellow | 3.5 | partial | Accessible but empty state not announced |
| PM1 | Yellow | 3.5 | partial | Empty state — cannot verify team oversight |

**Key findings:**
- BUG-P-6: Empty state says "No unread messages" — ambiguous (no messages, or all read?)
- BUG-P-8: French localization failure for DS2 (part of FG-P-9)
- TEST-P-2: Populated screenshots show empty inbox — test data seeding failure

### 9. plan-goal-create (`/plans/client/1/goals/create/`) — Yellow (avg 3.5)

**Status:** Functional. Terminology mismatch is the primary issue.

| Persona | Band | Score | Task Outcome | Notes |
|---------|------|-------|-------------|-------|
| DS1 | Green | 4.0 | yes | Form works well, clear actions |
| DS1b | Orange | 2.9 | partial | "Add Target" jargon, no onboarding |
| DS3 | Yellow | 3.5 | yes | Accessible but no progress indicator |
| DS4 | Yellow | 3.5 | yes | Labels present; autocomplete may not work with Dragon |
| PM1 | Green | 4.1 | n/a | Correctly denied — well-designed denial page |

**Satisfaction gap:** 1.6 (DS1b at 2.9 vs PM1 at 4.1).

### 10. groups-attendance (`/groups/1/attendance/`) — Yellow (avg 3.5)

**Status:** Functional but test data too sparse (1 member x 1 session instead of 8 x 12).

| Persona | Band | Score | Task Outcome | Notes |
|---------|------|-------|-------------|-------|
| DS1 | Yellow | 3.5 | partial | Sparse data limits evaluation |
| DS1c | Yellow | 3.5 | partial | Low density accidentally ADHD-friendly |
| DS3 | Yellow | 3.0 | partial | Cannot evaluate 96-cell table a11y with 1x1 data |
| PM1 | Yellow | 3.5 | partial | Sparse data limits oversight evaluation |

### 11. admin-erasure-requests (`/erasure/`) — Yellow (avg 3.6)

**Status:** Functional. Shows empty state (no pending requests).

| Persona | Band | Score | Task Outcome | Notes |
|---------|------|-------|-------------|-------|
| PM1 | Yellow | 3.5 | partial | No PIPEDA compliance context |
| admin | Yellow | 3.7 | partial | No explanation of erasure consequences |

---

## Cross-Persona Summary

| Persona | Pages Evaluated | Green | Yellow | Orange | Red |
|---------|----------------|-------|--------|--------|-----|
| PM1 | 10 | 2 | 4 | 0 | 4 |
| admin | 5 | 0 | 1 | 0 | 4 |
| DS1 | 6 | 2 | 2 | 1 | 0 |
| DS1b | 1 | 0 | 0 | 1 | 0 |
| DS1c | 2 | 0 | 2 | 0 | 0 |
| DS2 | 2 | 0 | 0 | 2 | 0 |
| DS3 | 4 | 1 | 2 | 0 | 0 |
| DS4 | 3 | 0 | 2 | 0 | 0 |
| R1 | 1 | 1 | 0 | 0 | 0 |
| R2-FR | 1 | 0 | 0 | 1 | 0 |
| unauthenticated | 2 | 0 | 0 | 0 | 2 |

**Most impacted:** unauthenticated (both pages Red), admin (4 Red), DS2 (both pages Orange — bilingual failures).

---

## Finding Groups

| Group | Root Cause | Primary Ticket | Also Affects | Cross-Method |
|-------|-----------|---------------|-------------|-------------|
| FG-P-7 | Survey feature URLs not registered (all `/manage/surveys/*` and `/surveys/participant/*` routes return 404) | BLOCKER-P-1 | BLOCKER-P-2 — 12 persona x page combinations | Matches FG-S-3 |
| FG-P-8 | Public pages return raw Django 500 errors (no custom 500 template) | BLOCKER-P-3 | BLOCKER-P-4 — 2 public pages | New |
| FG-P-9 | French localization failure (systemic, carried from Round 1) | BLOCKER-P-5 | BLOCKER-P-6, BUG-P-8 — 404 page, comm-leave-message R2-FR, comm-my-messages DS2 | Matches FG-S-1 |
| FG-P-10 | Test data seeding incomplete for populated states | TEST-P-1 | TEST-P-2 — groups-attendance, comm-my-messages | Partially matches FG-S-8 |
| FG-P-11 | plan-goal-create terminology mismatch ("Target" vs "Goal") | BUG-P-1 | BUG-P-2 | New |

---

## Coverage Heat Map (Round 3)

| Category | Pages | PM1 | admin | DS1 | DS1b | DS1c | DS2 | DS3 | DS4 | R1 | R2-FR | unauth |
|----------|-------|-----|-------|-----|------|------|-----|-----|-----|----|-------|--------|
| surveys (mgmt) | 3 | Red | Red | — | — | — | — | — | — | — | — | — |
| surveys (staff) | 1 | Ylw | — | Org | — | — | Org | Ylw | Ylw | — | — | — |
| public | 2 | — | — | — | — | — | — | — | — | — | — | Red |
| communications | 2 | Grn/Ylw | — | Grn/Ylw | — | Ylw | Org | Grn/Ylw | — | Grn | Org | — |
| clinical plans | 1 | Grn | — | Grn | Org | — | — | Ylw | Ylw | — | — | — |
| groups | 1 | Ylw | — | Ylw | — | Ylw | — | Ylw | — | — | — | — |
| admin | 1 | Ylw | Ylw | — | — | — | — | — | — | — | — | — |
