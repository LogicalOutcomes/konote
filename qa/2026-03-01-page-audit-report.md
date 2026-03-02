# KoNote2 Page Audit Report — Round 4

**Date:** 2026-03-01
**Pages audited:** 12 (of 77 in inventory)
**Cumulative coverage:** 23 pages audited across Rounds 1-4 (~30%)
**Personas tested:** R1, R2, R2-FR, DS1, DS1b, DS1c, DS2, DS3, DS4, PM1, E1, E2, admin, unauthenticated
**Breakpoints:** 1366x768, 1920x1080, 375x667

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| Permission violations | **1** (E2 Admin nav visible) |
| BLOCKER tickets | 4 |
| BUG tickets | 5 |
| IMPROVE tickets | 3 |
| TEST tickets | 2 |
| **Total tickets** | **15** (1 PERMISSION + 14 other) |
| Worst page | public-unsubscribe (1.0 Red — regression) |
| Best page | dashboard-executive E1 (4.2 Green) |
| Pages not functional | 4 of 12 (404 or 500) |

**Headline:** One-third of audited pages are non-functional (3 x 404, 1 x 500 for new v2.2 features; plus 1 regression 500 on public-unsubscribe). French localization failure continues as the single largest systemic issue across the application, now confirmed on 5 additional pages. The executive dashboard and PM dashboard views are excellent. The notes-create form needs attention for accessibility and cognitive load.

### Page Selection Rationale (Round 4)

| Category | Pages | Why |
|----------|-------|-----|
| New v2.2 pages (never audited) | client-export, export-confirmation, admin-backup-settings, admin-export-links | First audit of features added in page-inventory v2.2 |
| Core high-traffic | dashboard-staff, dashboard-executive, client-detail | Most-used pages, many personas |
| Clinical / reports | notes-create, plan-view, reports-funder | Key workflow pages not yet audited |
| Regression + public | public-unsubscribe, reports-insights | BLOCKER-P-4 regression check; new insights page |

---

## 2. Permission Violations

### PERMISSION-P-1: E2 sees Admin nav dropdown

**Persona:** E2 (Kwame Asante, Director of Programs)
**Page:** dashboard-executive
**Violation type:** page_access (UI layer)

E2's permission_scope specifies `admin: false`, yet the navigation bar shows an "Admin" dropdown between "Reports" and "Kwame Asante". E1 (same role family, also `admin: false`) does NOT see this dropdown — confirming it is an E2-specific configuration error, not a systemic executive issue.

**Screenshot comparison:**
- `dashboard-executive-E1-populated-1366x768.png` — no Admin dropdown (correct)
- `dashboard-executive-E2-populated-1366x768.png` — Admin dropdown visible (incorrect)

Full ticket: PERMISSION-P-1 in page audit tickets.

---

## 3. Findings by Heuristic

### H01 — First Impression

**Most affected pages:** client-export (404), admin-backup-settings (404), admin-export-links (404), export-confirmation (500), public-unsubscribe (500)

Five pages make a terrible first impression because they are non-functional. The three 404 pages use KoNote's well-designed 404 template (which is positive), but the two 500 pages show raw Django error text with no branding.

**Best first impression:** dashboard-executive (E1). Clean, professional, immediately communicates "aggregate view, no PII." The "Percentages hidden (fewer than 5 active participants)" note shows thoughtful small-cell suppression.

### H02 — Information Hierarchy

**Most affected page:** notes-create. The form spans the full viewport height with 7+ sections (template, interaction, date, duration, modality, targets, working relationship check-in, engagement, follow-up). No visual hierarchy separates required from optional fields. For DS1c (ADHD), this is overwhelming.

**Best hierarchy:** dashboard-executive and dashboard-staff PM1 view. Summary cards at top, program detail below, clear visual grouping.

### H03 — Navigation Context

**Most affected page:** notes-create. Breadcrumb is present (Home > Participants > Jane Doe > Notes > New Note) which is good, but there's no step indicator despite the form functioning as a multi-section wizard. DS1c loses track of where she is.

**Best navigation context:** plan-view PM1. View-only banner clearly explains WHY access is limited and WHAT to do next.

### H05 — Terminology

**Systemic French failure (FG-P-9):** Confirmed on 5 new pages this round: dashboard-staff, client-detail, notes-create, plan-view, reports-insights. Every element — headings, labels, buttons, navigation, footer — remains in English for French-preference users. This is the same root cause as Round 1 BUG-14 / Round 3 BLOCKER-P-5/P-6.

**"Target" vs "Goal" inconsistency (FG-P-11 continued):** The plan-view uses "Target" as a column header and button label ("Add a Target", "Add Target"), while the notes-create form says "Which Targets did you work on?" The page-inventory and scenario descriptions use "Goal." This inconsistency confuses DS1b (first-week user).

### H06 — Error Prevention

**notes-create:** No autosave indicator. If Casey (DS1, iPad, between appointments) loses connection or accidentally navigates away, she loses her entire note. The form has a "Save Note" button at the bottom but no draft/autosave assurance.

**reports-funder:** Requires "Who is receiving this data?" and "Reason" before generating a report. For PM1 this is appropriate (audit trail). For E1/E2 (executives delegating to PM), these fields feel like operational burden.

### H07 — Feedback

**reports-insights:** The "populated" state shows only a pre-query form with no results. After selecting a program and clicking "Show Insights," we cannot evaluate the feedback because test data wasn't seeded (TEST issue). The form itself is clean but provides no preview of what insights will look like.

### H08 — Accessibility

**plan-view DS1:** The "Actions" button/column header text renders vertically ("A c t i o n s" stacked letter-by-letter) on the right side of the table, overflowing the layout. For DS3 (screen reader), this would be announced as individual characters. For DS4 (voice control), the target is unusable.

**notes-create DS3:** The long form with many sections creates excessive tab stops for JAWS navigation. No skip-to-section landmarks visible.

### H10 — Aesthetic Coherence

**public-unsubscribe / export-confirmation:** Raw Django 500 error text ("A server error occurred. Please contact the administrator.") — no KoNote branding, no styling, monospace font. Same finding as Round 3 FG-P-8 (not fixed).

**Positive:** dashboard-executive, dashboard-staff (PM1 view), and reports-funder all maintain consistent visual language with KoNote's design system.

---

## 4. Findings by Page

### dashboard-staff

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| R1 | 3.8 | Yellow | Welcome banner helpful; search and quick actions clear |
| R2 | 3.8 | Yellow | Same as R1; R2 (high tech) would navigate faster |
| R2-FR | **2.0** | **Orange** | **BLOCKER: entire page in English** (FG-P-9) |
| DS1 | 3.6 | Yellow | Adequate, summary cards useful |
| DS1b | 3.4 | Yellow | Welcome banner aids onboarding |
| DS1c | 3.3 | Yellow | Some info density but summary cards help |
| DS2 | **2.0** | **Orange** | **BLOCKER: page in English** (FG-P-9) |
| DS3 | 3.5 | Yellow | Dashboard cards appear accessible (Medium confidence — screen reader testing needed) |
| DS4 | 3.5 | Yellow | Voice control adequate for large targets |
| PM1 | **4.0** | **Green** | Excellent — Program Health section, staff documentation overview |
| **Page mean** | **3.2** | **Yellow** | FR personas drag average; EN experience is 3.5-4.0 |

### dashboard-executive

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| E1 | **4.2** | **Green** | Best page in audit — no PII, small-cell suppression, aggregate only |
| E2 | 4.0 | Green | Same quality BUT Admin nav visible (PERMISSION-P-1) |
| **Page mean** | **4.1** | **Green** | Excellent design; fix E2 nav permission |

### client-detail

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| R1 | **4.0** | **Green** | Correctly limited to Info tab; contact info visible |
| R2 | 3.9 | Yellow | Similar to R1, slightly faster navigation |
| R2-FR | **2.0** | **Orange** | **BLOCKER: entire page in English** (FG-P-9) |
| DS1 | 3.8 | Yellow | Full tabs with clinical access |
| DS1b | 3.5 | Yellow | Tab counts help orient new user |
| DS1c | 3.4 | Yellow | Many tabs but manageable |
| DS2 | **2.0** | **Orange** | **BLOCKER: page in English** (FG-P-9) |
| DS3 | 3.7 | Yellow | Tabs with counts; accessible layout (Medium confidence — screen reader testing needed) |
| DS4 | 3.6 | Yellow | Voice control adequate |
| PM1 | 3.9 | Yellow | View-only appropriate; read access for QA oversight |
| **Page mean** | **3.4** | **Yellow** | Solid page; FR localisation only issue |

### notes-create

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| DS1 | 2.9 | Orange | Long form, no autosave, cognitive load |
| DS1b | 2.5 | Orange | No onboarding, unfamiliar terminology |
| DS1c | 2.5 | Orange | Form length overwhelming for ADHD |
| DS2 | **1.0** | **Red** | **BLOCKER: entire page in English** (FG-P-9) |
| DS3 | 2.6 | Orange | Many tab stops, no skip-to-section |
| DS4 | 3.0 | Yellow | Voice control adequate for form fields |
| PM1 | 3.6 | Yellow | Appropriate for PM note creation |
| **Page mean** | **2.6** | **Orange** | Long form, accessibility gaps, FR failure |

### plan-view

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| DS1 | 3.2 | Yellow | Actions button renders vertically (CSS bug) |
| DS1b | 2.8 | Orange | "Target" terminology confusing |
| DS1c | 3.0 | Yellow | Clean layout, manageable |
| DS2 | **1.0** | **Red** | **BLOCKER: entire page in English** (FG-P-9) |
| DS3 | 2.7 | Orange | Vertical "Actions" text hostile to screen reader |
| DS4 | 3.0 | Yellow | Voice targets adequate except Actions overflow |
| PM1 | **3.9** | **Yellow** | View-only banner is excellent; clear, helpful explanation |
| **Page mean** | **2.8** | **Orange** | Actions rendering bug + FR failure |

### reports-funder

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| PM1 | 3.8 | Yellow | Well-designed report builder; audit trail appropriate |
| E1 | 3.0 | Yellow | Audit trail fields feel operational for an executive |
| E2 | 2.5 | Orange | Audit fields + Admin nav = role confusion |
| **Page mean** | **3.1** | **Yellow** | Good design; consider role-specific field visibility |

### reports-insights

| Persona | Score | Band | Confidence | Key Finding |
|---------|-------|------|------------|-------------|
| DS1 | 3.4 | Yellow | Low | Pre-query form only |
| DS1b | 3.2 | Yellow | Low | Pre-query form only |
| DS1c | 3.2 | Yellow | Low | Pre-query form only |
| DS2 | **1.5** | **Red** | Medium | **BLOCKER: pre-query form in English** (FG-P-9) |
| DS3 | 3.3 | Yellow | Low | Pre-query form only |
| DS4 | 3.3 | Yellow | Low | Pre-query form only |
| PM1 | 3.7 | Yellow | Low | Clean form but no data to evaluate |
| E1 | 3.5 | Yellow | Low | Clean form but no data to evaluate |
| E2 | 3.3 | Yellow | Low | Pre-query form only |
| **Page mean** | **3.2** | **Yellow** | **Low** | Cannot fully evaluate — populated state has no data |

### client-export (NEW v2.2)

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| PM1 | **1.0** | **Red** | **BLOCKER: 404 Page Not Found** |

### export-confirmation (NEW v2.2)

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| PM1 | **1.0** | **Red** | **BLOCKER: raw Django 500 server error** |

### admin-backup-settings (NEW v2.2)

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| admin | **1.0** | **Red** | **BLOCKER: 404 Page Not Found** |

### admin-export-links (NEW v2.2)

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| admin | **1.0** | **Red** | **BLOCKER: 404 Page Not Found** |

### public-unsubscribe (REGRESSION CHECK)

| Persona | Score | Band | Key Finding |
|---------|-------|------|-------------|
| unauthenticated | **1.0** | **Red** | **BLOCKER: raw Django 500 — NOT FIXED since Round 3 (BLOCKER-P-4). CASL compliance risk.** |

---

## 5. Finding Groups

| Group | Root Cause | Primary Ticket | Also Affects | Cross-Method |
|-------|-----------|---------------|-------------|-------------|
| FG-P-9 | French localisation failure (systemic, from Round 1) | BLOCKER-P-10 | dashboard-staff (R2-FR, DS2), client-detail (R2-FR, DS2), notes-create (DS2), plan-view (DS2), reports-insights (DS2) | FG-S-1 from scenario eval |
| FG-P-12 | New v2.2 pages not deployed (404) | BLOCKER-P-9 | client-export, admin-backup-settings, admin-export-links | Same pattern as FG-P-7 (surveys) |
| FG-P-13 | Missing custom 500 error template | BLOCKER-P-7 | public-unsubscribe, export-confirmation | FG-P-8 from Round 3 (not fixed) |
| FG-P-14 | Populated state screenshots show pre-query content | TEST-P-4 | reports-insights (all personas) | — |
| FG-P-15 | E2 Admin nav visible despite admin:false | PERMISSION-P-1 | dashboard-executive E2 only | — |
| FG-P-11 | "Target" vs "Goal" terminology (continued) | BUG-P-12 | plan-view, notes-create | BUG-P-1 from Round 3 |
| FG-P-16 | CSS overflow on interactive elements | BUG-P-9 | plan-view (DS1, DS3, DS4) | — |

---

## 6. Cross-Persona Summary

| Persona | Pages Scored | Mean Score | Band | Biggest Issue |
|---------|-------------|------------|------|---------------|
| PM1 | 8 | 3.5 | Yellow | notes-create long form (3.6), client-export 404 (1.0) |
| E1 | 3 | 3.6 | Yellow | reports-funder audit fields (3.0) |
| R1 | 2 | 3.9 | Yellow | Minor — dashboard welcome banner |
| DS4 | 5 | 3.3 | Yellow | plan-view Actions overflow |
| E2 | 3 | 3.3 | Yellow | Admin nav permission + audit fields |
| DS1 | 5 | 3.2 | Yellow | notes-create (2.9), plan-view Actions bug |
| DS3 | 5 | 3.1 | Yellow | notes-create a11y (2.6), plan-view Actions (2.7) |
| DS1c | 5 | 3.1 | Yellow | notes-create cognitive load (2.5) |
| DS1b | 5 | 3.1 | Yellow | notes-create no onboarding (2.5) |
| R2 | 2 | 3.9 | Yellow | Minor — no issues specific to R2 |
| R2-FR | 3 | **2.0** | **Orange** | **All 3 pages in English** (FG-P-9) |
| DS2 | 5 | **1.9** | **Red** | **All 5 pages in English** (FG-P-9) |
| admin | 2 | 1.0 | Red | Both pages 404 |
| unauth | 1 | 1.0 | Red | Raw 500 error |

**Satisfaction gap:** 2.6 points (E1 at 3.6 vs admin at 1.0). Excluding non-functional pages: 1.7 points (E1 at 3.6 vs DS2 at 1.9).

**Pattern:** French-preference personas score 1.5-2.0 points below their English-equivalent peers on every page. This is the single largest contributor to satisfaction inequality.

---

## 7. Coverage Heat Map

Pages audited per category across 4 rounds (cumulative):

| Category | Inventory | Audited | Coverage | Notes |
|----------|-----------|---------|----------|-------|
| Dashboard | 3 | 2 | 67% | dashboard-staff, dashboard-executive |
| Client | 4 | 2 | 50% | client-detail, client-export (404) |
| Notes | 2 | 1 | 50% | notes-create |
| Plans | 3 | 2 | 67% | plan-view, plan-goal-create (Round 3) |
| Groups | 3 | 1 | 33% | groups-attendance (Round 3) |
| Reports | 4 | 2 | 50% | reports-funder, reports-insights |
| Communications | 3 | 2 | 67% | comm-leave-message, comm-my-messages (Round 3) |
| Admin | 10 | 4 | 40% | admin-backup-settings, admin-export-links (404), erasure-requests, audit-log (Rounds 3-4) |
| Public | 3 | 2 | 67% | public-unsubscribe, public-survey-link (Round 3) |
| Surveys | 5 | 0 | 0% | All 404 — deferred until feature deployed |
| Portal | 4 | 0 | 0% | Screenshots missing — deferred |
| Settings | 3 | 0 | 0% | Not yet audited |
| **Total** | **77** | **23** | **30%** | |

**Priority for Round 5:** Settings pages (0% coverage), remaining client pages (client-list, client-create), groups pages (groups-detail, groups-create), remaining admin pages.

**Process note:** A running coverage ledger should be maintained across rounds to track exactly which pages have been audited, when, and at what scores. The cumulative counts above are reconstructed from individual round reports; a dedicated ledger would improve accuracy and make trend tracking easier.

---

## Status of Previous Page Audit Tickets (Round 3)

| Ticket | Description | Status |
|--------|------------|--------|
| BLOCKER-P-1 | Survey management pages 404 | NOT FIXED (not re-tested — surveys deferred) |
| BLOCKER-P-2 | client-surveys 404 | NOT FIXED (not re-tested) |
| BLOCKER-P-3 | public-survey-link 500 | NOT FIXED (not re-tested) |
| BLOCKER-P-4 | **public-unsubscribe 500** | **NOT FIXED — regression confirmed** |
| BLOCKER-P-5 | 404 page not translated to French | NOT EVALUABLE this round |
| BLOCKER-P-6 | comm-leave-message English for R2-FR | NOT EVALUABLE this round |
| BUG-P-1 | plan-goal-create "Add Target" heading | PARTIALLY FIXED — plan-view still uses "Target" |
| BUG-P-2 | plan-goal-create no onboarding | NOT EVALUABLE (different page) |
| BUG-P-3 | groups-attendance "--" values | NOT EVALUABLE this round |
| BUG-P-4 | groups-attendance "1 sessions" | NOT EVALUABLE this round |
| BUG-P-5 | groups-attendance "Rate" ambiguous | NOT EVALUABLE this round |
| BUG-P-6 | comm-my-messages empty state | NOT EVALUABLE this round |
| BUG-P-7 | comm-leave-message no required indicator | NOT EVALUABLE this round |
| BUG-P-8 | comm-my-messages English for DS2 | NOT EVALUABLE this round |
| TEST-P-3 | Custom 500 template needed | **NOT FIXED — still raw Django 500** |

---

*Report generated by page audit Round 4. Tickets: `2026-03-01-page-audit-tickets.md`.*
*Next step: Run `/process-qa-report` in konote to create the action plan.*
