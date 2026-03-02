# QA Action Plan — Page Audit Round 4 (2026-03-01)

**Date:** 2026-03-01
**Type:** Page audit (Pipeline B, Round 4)
**Source reports:** `qa/2026-03-01-page-audit-tickets.md`, `qa/2026-03-01-page-audit-report.md`
**Previous page audit:** Round 3 (2026-02-21, `tasks/qa-action-plan-2026-02-21-page-audit.md`)
**Companion plans:** `tasks/qa-action-plan-2026-03-01.md` (Round 8 scenario), `tasks/qa-action-plan-2026-03-01b.md` (Round 8b supplement)

## Pipeline Note

No Step 2b entry exists in `qa/pipeline-log.txt` for this page audit round. The report and tickets files were manually placed in `qa/` and `.qa-handoff.json` was updated by the user. Ticket provenance is based on the `page_audit_findings` section of `.qa-handoff.json` (timestamp 2026-03-02T02:30:00).

## Headline Metrics

| Metric | Round 3 (2026-02-21) | Round 4 (2026-03-01) | Change |
|--------|----------------------|----------------------|--------|
| Pages audited | 11 | 12 | +1 |
| Persona x page evaluations | 38 | ~65 | +27 |
| Permission violations | 0 | **1** | +1 |
| BLOCKER tickets | 6 | 4 | -2 |
| BUG tickets | 8 | 5 | -3 |
| IMPROVE tickets | 4 | 3 | -1 |
| TEST tickets | 3 | 2 | -1 |
| Total tickets | 21 | **15** | -6 |
| Pages scoring Red | 5/11 (45%) | 5/12 (42%) | Slight improvement |
| Pages scoring Green | 1/11 (9%) | 1/12 (8%) | Stable (dashboard-executive) |
| Pages not functional (404/500) | 6/11 (55%) | 4/12 (33%) | Improved (surveys removed from sample) |
| Best page | erasure-requests (3.5) | **dashboard-executive E1 (4.2)** | First Green page |
| Worst page | public-survey-link (1.0) | public-unsubscribe (1.0) | Same class of issue |

**Key findings:**
- dashboard-executive is the first page to score Green (4.2) — excellent design patterns worth replicating
- 4 of 12 pages are non-functional (3 × 404 for v2.2 features not yet deployed, 1 × 500 on public-unsubscribe regression)
- French localisation failure confirmed on 5 additional pages — now the single largest contributor to satisfaction inequality
- CASL compliance risk persists: public-unsubscribe returns 500 (unfixed since Round 3 BLOCKER-P-4)
- One permission violation: E2 sees Admin nav despite `admin: false` (E1 does NOT see it)

---

## Expert Panel Summary

**Panel:** Accessibility Specialist, UX Designer, Django Developer, Nonprofit Operations Lead

### Cross-Reference with Fix Log and Existing TODO

Before tiering, the panel cross-referenced all 15 tickets against `qa/fix-log.json`, TODO.md (Active Work + Coming Up), and `tasks/ARCHIVE.md`:

| Page Audit Ticket | Known Fix / Existing Track | Status |
|-------------------|--------------------------|--------|
| PERMISSION-P-1 (E2 admin nav) | fix-log: "Executive nav shows admin items" fixed 2026-02-22 (QA-R7-TIER2). QA-R8-PERM1 "verified admin nav hidden" completed 2026-03-01. | **RE-VERIFY** — QA-R8-PERM1 verified E1 only; E2 is a different persona with a potentially different config |
| BLOCKER-P-7 (unsubscribe 500) | Round 3 page audit Tier 1 #1. ARCHIVE: "QA Page Audit Tier 1 + Tier 2 — 500.html standalone, public view hardening" completed 2026-02-22. | **CARRYOVER** — fix was incomplete or regressed; still returning raw 500 |
| BLOCKER-P-8 (export-confirm 500) | Not previously tracked. Custom 500.html should prevent raw errors (built 2026-02-22). | **NEW + VERIFY** — check if 500.html is being served; feature may not be built |
| BLOCKER-P-9 (three v2.2 404s) | client-export: fix-log "Individual client data export" fixed 2026-02-28 (QA-R7-PRIVACY1). admin-backup-settings, admin-export-links: not built. | **MIXED** — client-export VERIFY (URL mismatch?); other two are premature page-inventory entries |
| BLOCKER-P-10 (French 5 pages) | fix-log: "Language preference not persisting" fixed 2026-02-21. TODO: QA-R8-LANG1 (verify language middleware) + QA-R8-I18N1 (fix French navigation). | **ALREADY TRACKED** — no new TODO item needed |
| BUG-P-9 (Actions CSS) | Not in fix-log or TODO. | **NEW** |
| BUG-P-10 (no autosave) | ARCHIVE: "Note auto-save / draft recovery — 2026-02-03 (UX21)" completed. | **VERIFY** — feature was built; indicator may be missing or invisible |
| BUG-P-11 (exec audit fields) | Not in fix-log or TODO. | **NEW** — needs GK gate |
| BUG-P-12 (Target→Goal) | Round 3 BUG-P-1 partially fixed. ARCHIVE: "QA Page Audit Tier 1 + Tier 2" 2026-02-22 fixed plan-goal-create heading only. | **CARRYOVER** — plan-view and notes-create still use "Target" |
| BUG-P-13 (notes-create cognitive load) | Not in fix-log or TODO. | **NEW** |
| IMPROVE-P-5 (progress indicator) | Not tracked. | **NEW** |
| IMPROVE-P-6 (insights preview) | Not tracked. | **NEW** |
| IMPROVE-P-7 (exec dashboard pattern) | Positive finding. No action needed. | **DOCUMENT ONLY** |
| TEST-P-4 (insights data seeding) | Not tracked. | **NEW** (qa-scenarios repo) |
| TEST-P-5 (page-inventory gating) | Same pattern as Round 3 FG-P-7. | **PROCESS** (qa-scenarios repo) |

### Key Insights by Expert

**Accessibility Specialist:**
- BUG-P-9 (Actions text renders vertically) is a critical accessibility failure: screen reader announces individual characters, voice control can't target it. Quick CSS fix with `white-space: nowrap` or `min-width`.
- BUG-P-13 (notes-create cognitive load) has two distinct a11y issues: (1) no section headings for screen reader skip-navigation (WCAG 1.3.1), and (2) no `aria-required` on required fields (WCAG 3.3.2). These should be fixed together.
- The dashboard-executive privacy subtitle ("This dashboard shows overall numbers — individual participant records are kept private") is an exemplary accessibility pattern: it communicates context via text, not just visual cues. Worth replicating.

**UX Designer:**
- BUG-P-10 (autosave): The archive confirms autosave was built in 2026-02-03 (UX21). The most likely explanation is that the autosave runs but the UI indicator is too subtle or absent. Verify before re-implementing.
- BUG-P-12 (Target vs Goal): This is the third round this has been flagged. The Round 3 fix was scoped too narrowly (heading only). A `{% trans %}` search-and-replace across plan-view and notes-create templates should resolve it permanently.
- notes-create is the lowest-scoring functional page (2.6 Orange). The three bugs on it (BUG-P-10, BUG-P-12, BUG-P-13) should be bundled into a single "notes-create UX overhaul" task for coherent improvement.

**Django Developer:**
- BLOCKER-P-7 (unsubscribe 500): The 500.html template was created in Round 3 Tier 1 (2026-02-22, ARCHIVE line 82). If the unsubscribe page still shows a **raw** Django 500 (no branding), it means either: (1) the 500.html has a syntax error that causes it to fail silently, (2) the view is returning an `HttpResponseServerError()` directly instead of raising an exception, or (3) `DEBUG=True` in the test environment is showing the debug traceback page. Investigate the specific error before coding.
- BLOCKER-P-9 (client-export 404): The `client_data_export` view was built (QA-R7-PRIVACY1) and uses `SecureExportLink`. But the URL registered in `urls.py` may differ from the page-inventory URL (`/participants/<id>/export/`). Check the actual route registered for `ClientDataExportView`.
- BLOCKER-P-8 (export-confirmation 500) and admin-backup-settings/admin-export-links (404): These v2.2 page-inventory entries were added before the features were deployed. Same pattern as surveys (FG-P-7, Round 3). The export-confirmation showing 500 instead of 404 suggests a partial route match with an unhandled exception.

**Nonprofit Operations Lead:**
- **BLOCKER-P-7 remains the single most urgent compliance issue** across all page audits. It was first flagged in Round 3 (2026-02-21) and has NOT been fixed. Under CASL s. 6(2)(c), every agency using email communications without a working unsubscribe page is in violation. This has been open for 8 days.
- PERMISSION-P-1 (E2 admin nav) is the only permission violation found across 4 rounds of page auditing. Even if backend enforcement blocks actual admin actions, the UI exposure violates least-privilege and creates confusion for E2 (Director of Programs).
- Three v2.2 page-inventory entries (admin-backup-settings, admin-export-links, export-confirmation) should be **removed from the page inventory** until the features are deployed. They consume evaluation time and generate false BLOCKER tickets.
- BUG-P-11 (executive audit fields) is a real workflow issue for agencies with active boards. Executives who generate funder reports for board meetings shouldn't face the same audit trail requirements as program managers. This needs GK review.

### Areas of Agreement

1. **BLOCKER-P-7 (CASL unsubscribe) is the top priority — again** (unanimous). It was Tier 1 in Round 3 and must be resolved before any agency enables email communications.
2. **Investigate before fixing** (unanimous). The 500.html template was built; the unsubscribe "public view hardening" was done. Something regressed or was incomplete. Check Django error logs and the 500.html template first.
3. **BUG-P-12 (Target→Goal) is overdue** (unanimous). Third round flagged. Do a codebase-wide search-and-replace this time, not a single template fix.
4. **BUG-P-9 (Actions CSS) is a quick, high-impact fix** (unanimous). Accessibility and visual impact, 10-minute CSS fix.
5. **French localisation (BLOCKER-P-10) is already tracked** (unanimous). QA-R8-LANG1 and QA-R8-I18N1 cover it. The page audit confirms it's systemic but creates no new items.
6. **v2.2 page-inventory entries should be deferred** (unanimous). admin-backup-settings and admin-export-links are premature entries. Remove or mark as "planned" in the inventory.

### Productive Disagreements

**BUG-P-11 (executive audit fields) — Tier 2 or Tier 3?**
- UX Designer: Tier 2 — real workflow friction for executives
- Operations Lead: Tier 2 — but only after GK review of the reporting approach
- Django Developer: Tier 3 — the funder reporting form needs broader redesign work; this one change in isolation creates inconsistency
- **Resolution:** Tier 2 with GK gate. The fix (pre-filling or making fields optional for executive roles) is scoped and doesn't require a full redesign. GK reviews reporting methodology before implementation.

**BUG-P-13 (notes-create cognitive load) — single task or bundle?**
- UX Designer: Bundle with BUG-P-10 and BUG-P-12 as "notes-create overhaul"
- Accessibility Specialist: Split into two: accessibility fixes (landmarks, aria-required) as Tier 1, and cognitive load improvements (collapsible sections) as Tier 2
- **Resolution:** Two tasks. The accessibility fixes (WCAG compliance) are Tier 2 since notes-create is still functional. The cognitive load improvements (collapsible sections, progress indicator) are Tier 3 as UX enhancement.

---

## Priority Tiers

### Tier 1 — Fix Now (4 items)

**1. BLOCKER-P-7 — Fix public-unsubscribe 500 (CASL compliance)**
- **Status:** CARRYOVER from Round 3 BLOCKER-P-4 — "public view hardening" (2026-02-22) did not resolve the issue
- **Expert reasoning:** Legal compliance under CASL s. 6(2)(c). Open for 8 days. Must work before any agency enables email. Raw Django 500 means the custom 500.html (built 2026-02-22) is not being served for this view.
- **Investigation first:** Check (1) Django error logs for the unsubscribe view's stack trace, (2) whether 500.html exists and renders correctly, (3) whether the view is returning an `HttpResponseServerError()` directly
- **Complexity:** Moderate (1-2 hours) — fix underlying exception, ensure 500.html is served as fallback
- **Fix in:** konote-app (apps/communications/views.py, templates)
- **Acceptance:** Valid token loads unsubscribe confirmation; invalid token shows styled error; page is bilingual; works on mobile; CASL: unsubscribe takes effect within 10 business days
- **GK gate:** No — legal compliance with clear requirements

**2. PERMISSION-P-1 — Re-verify E2 admin nav visibility**
- **Status:** RE-VERIFY — QA-R8-PERM1 (completed 2026-03-01) verified E1 does NOT see Admin nav, but did not check E2
- **Expert reasoning:** E2 (Kwame Asante, Director of Programs) has `admin: false` in permission scope but sees an "Admin" dropdown. E1 (Eva Executive, same role family, same `admin: false`) does NOT. This is E2-specific — likely a group membership or role flag configuration error.
- **Investigation first:** Check E2's user groups, role flags, and any E2-specific permission overrides. Compare E2's config to E1's.
- **Complexity:** Quick (15-30 min) — find and fix the config difference
- **Fix in:** konote-app (auth configuration, possibly nav template)
- **Acceptance:** E2 navigation matches E1 (no Admin dropdown); clicking admin URLs as E2 returns 403

**3. BUG-P-9 — Fix plan-view Actions CSS vertical rendering**
- **Status:** NEW — not previously identified
- **Expert reasoning:** "Actions" renders as individual stacked characters on plan-view. JAWS announces "A c t i o n s" as 7 separate characters. Voice control can't target it. Quick CSS fix.
- **Complexity:** Quick (10-15 min) — add `white-space: nowrap` or `min-width` to the Actions button/column
- **Fix in:** konote-app (apps/plans/templates/plans/plan_view.html or associated CSS)
- **Acceptance:** "Actions" renders horizontally; screen reader announces as single word; voice control targets correctly

**4. BUG-P-12 — Fix Target→Goal terminology across plan-view and notes-create**
- **Status:** CARRYOVER — Round 3 BUG-P-1 fixed plan-goal-create heading only; plan-view and notes-create still use "Target"
- **Expert reasoning:** Third consecutive round this has been flagged. Previous fix was too narrow. Needs codebase-wide search-and-replace of "Target" → "Goal" (or `{{ term.goal }}` where terminology is configurable).
- **Complexity:** Quick (20-30 min) — search all template files for "Target" and replace with "Goal" or term reference
- **Fix in:** konote-app (plan_view.html, notes/create.html, any other templates using "Target")
- **Acceptance:** plan-view column header says "Goal"; buttons say "Add a Goal"; notes-create says "Which Goals did you work on?"; French uses "Objectif" (not "Cible")

### Tier 1 — Verify (2 items)

**V1. Verify custom 500.html template is being served**
- **Previous fix:** ARCHIVE: "QA Page Audit Tier 1 + Tier 2 — 500.html standalone" (2026-02-22)
- **Issue:** Round 4 audit found "raw Django 500 error text" on both public-unsubscribe and export-confirmation — "no KoNote branding, no styling, monospace font." The custom 500.html should be catching these.
- **Verify:** Check `templates/500.html` exists, renders without errors, and is served when Django encounters an unhandled exception. Test by temporarily raising an exception in a test view.
- **If broken:** Fix the template or its placement. This is the safety net for all future 500 errors.

**V2. Verify client-export URL matches page-inventory**
- **Previous fix:** fix-log: "Individual client data export" fixed 2026-02-28 (QA-R7-PRIVACY1). SecureExportLink infrastructure built.
- **Issue:** Page inventory expects `/participants/<id>/export/` but the actual view URL may differ.
- **Verify:** Check `apps/clients/urls.py` (or equivalent) for the export route. If the URL differs from the page inventory, update the page inventory.
- **Existing TODO item:** QA-R8-VERIFY1 ("Verify BLOCKER-10/12 data export against recent SEC3 work") in Parking Lot covers this.

### Tier 2 — Fix Soon (3 items)

**5. BUG-P-13 — Fix notes-create accessibility (landmarks, required indicators)**
- **Status:** NEW
- **Expert reasoning:** No section headings for screen reader skip-navigation (WCAG 1.3.1). No `aria-required` on required fields (WCAG 3.3.2). DS3 (screen reader) scores 2.6 on this page.
- **Complexity:** Moderate (1 hour) — add heading levels (`<h2>`, `<h3>`) for form sections, add `aria-required="true"` to required fields, add visible "required" indicators
- **Fix in:** konote-app (apps/notes/templates/notes/create.html)
- **Acceptance:** Required fields marked visually and with `aria-required`; section headings allow screen reader jump-navigation

**6. BUG-P-11 — Fix reports-funder executive audit fields** — GK reviews reporting methodology
- **Status:** NEW
- **Expert reasoning:** Audit trail fields ("Who is receiving this data?" + "Reason") are appropriate for PM but create friction for executives generating board reports. Consider pre-filling defaults or making optional for executive roles.
- **Complexity:** Quick (30 min after GK review)
- **Fix in:** konote-app (apps/reports/templates/reports/funder_report.html, possibly views.py)
- **GK gate:** Yes — whether to change audit trail behaviour for executive users is a policy decision

**7. BUG-P-10 — Verify notes-create autosave indicator**
- **Status:** VERIFY — feature was built 2026-02-03 (UX21 in ARCHIVE: "Note auto-save / draft recovery")
- **Expert reasoning:** The page audit found "no autosave indicator, no draft status, no warning about unsaved changes." Either the autosave is working but the indicator is too subtle, or the feature regressed.
- **Verify first:** Check notes/create.html and associated JS for draft/autosave functionality. If it works, enhance the visual indicator. If not working, re-implement.
- **Complexity:** Quick (15-30 min for verification + indicator enhancement)
- **Fix in:** konote-app (apps/notes/templates/notes/create.html, JS)

### Tier 3 — Backlog (2 items)

**8. IMPROVE-P-5 — Add progress indicator to notes-create**
- Long form with 7+ sections. DS1c (ADHD) and DS1b (first week) lose track. A sidebar checklist or top progress bar showing "Template [done] > Details > Targets > Follow-up" would help.
- Bundle with BUG-P-13 a11y fixes when scheduling.

**9. IMPROVE-P-6 — Add sample/preview to reports-insights pre-query**
- Pre-query form shows only dropdowns with no preview of what insights look like. New users don't know what to expect. Add faded mock-up or description below the form.

### Already Tracked — No New TODO Items

| Page Audit Ticket | Existing Tracking | Why No New Item |
|-------------------|-------------------|-----------------|
| BLOCKER-P-10 (French localisation, 5 pages) | QA-R8-LANG1 + QA-R8-I18N1 in Coming Up | Systemic issue already tracked; page audit confirms scope but creates no new work |
| BLOCKER-P-9 (admin-backup-settings 404) | Premature page-inventory entry | Feature not built; same pattern as surveys (Round 3 FG-P-7) |
| BLOCKER-P-9 (admin-export-links 404) | Premature page-inventory entry | Feature not built |
| BLOCKER-P-8 (export-confirmation 500) | Covered by V1 (500.html verification) + premature entry | Feature may not be built; 500.html should catch as fallback |
| IMPROVE-P-7 (exec dashboard pattern) | Positive finding | No action needed — documented as exemplary pattern |
| TEST-P-4 (insights data seeding) | Tracked in this action plan only | Fix in qa-scenarios repo |
| TEST-P-5 (page-inventory gating) | Tracked in this action plan only | Process improvement, not code fix |

---

## Test Infrastructure Issues (qa-scenarios repo, 2 items)

| Ticket | Issue | Fix In | Priority |
|--------|-------|--------|----------|
| TEST-P-4 | reports-insights "populated" state shows pre-query form only — test runner didn't submit the form | qa-scenarios test runner | High — blocks insights evaluation |
| TEST-P-5 | Page-inventory v2.2 entries added before features deployed (4 pages) | qa-scenarios page-inventory process | Medium — prevents wasted evaluation effort |

**TEST-P-5 recommendation:** Add a `status: planned | deployed | deprecated` field to page-inventory entries. Only evaluate pages where `status: deployed`. This was the same recommendation from Round 3 (FG-P-7) and still hasn't been implemented.

---

## Deduplication Summary

| This Audit | Existing TODO/Tracking | Action |
|------------|----------------------|--------|
| BLOCKER-P-10 (French, 5 pages) | QA-R8-LANG1, QA-R8-I18N1 | No new item |
| BLOCKER-P-9 (admin-backup, admin-export-links) | Premature page-inventory entries | No new item |
| BLOCKER-P-8 (export-confirmation) | V1 (500.html verify) covers | No new item |
| BLOCKER-P-9 (client-export) | QA-R8-VERIFY1 covers partially | V2 added for URL check |
| PERMISSION-P-1 (E2 nav) | QA-R8-PERM1 was incomplete | New verify item (re-check E2) |
| BUG-P-12 (Target→Goal) | Round 3 BUG-P-1 partially fixed | New fix item (complete the work) |
| BLOCKER-P-7 (unsubscribe) | Round 3 BLOCKER-P-4 fix incomplete | New fix item (carryover) |

**Net new items for TODO.md: 11** (4 Tier 1 fix, 2 Tier 1 verify, 3 Tier 2, 2 Tier 3)

---

## Cross-Method Validation

This page audit confirms and extends findings from the Round 8 scenario evaluation:

| Finding Group | Scenario Eval | Page Audit Round 4 | Confirmed? |
|---------------|--------------|-------------------|-----------|
| FG-S-2 (language mixing) | R2-FR bottom persona (2.60) | FG-P-9 (5 more pages, all English for FR users) | Yes — systemic, widening |
| FG-S-8 (data export) | SCN-070 scores 2.39 | client-export 404 (URL mismatch?) | Needs verification |
| FG-P-8 Round 3 (public 500s) | Not caught by scenarios | FG-P-13 (public-unsubscribe STILL 500, export-confirm 500) | Persistent — scenarios still don't cover public pages |
| FG-P-11 (Goal terminology) | Not caught by scenarios | BUG-P-12 (plan-view + notes-create) | Persistent — third round |
| FG-P-15 (E2 admin nav) | Executive nav verified OK in scenarios | PERMISSION-P-1 (E2-specific) | **Net new** — scenario verified E1 but not E2 |

**The page audit's biggest unique contribution this round:**
1. Confirming the CASL unsubscribe regression (BLOCKER-P-7) — scenarios don't test unauthenticated public pages
2. Catching E2-specific permission violation — scenario verification checked E1 only
3. Identifying the Actions CSS bug on plan-view — scenarios don't examine visual CSS rendering

---

## Recommended Fix Order

### Tier 1 (estimated 2-3 hours total)

1. **V1** — Verify 500.html template works (15 min) — prerequisite context for BLOCKER-P-7
2. **BLOCKER-P-7** — Public unsubscribe / CASL fix (1-2 hours) — legal compliance, 8 days overdue
3. **PERMISSION-P-1** — E2 admin nav investigation + fix (15-30 min)
4. **BUG-P-9** — Actions CSS fix (10-15 min)
5. **BUG-P-12** — Target→Goal search-and-replace (20-30 min)
6. **V2** — Verify client-export URL (10 min) — may already be covered by QA-R8-VERIFY1

### Tier 2 (estimated 2-3 hours total)

7. BUG-P-13 — notes-create a11y landmarks + required indicators (1 hour)
8. BUG-P-11 — reports-funder executive audit fields (30 min after GK review)
9. BUG-P-10 — notes-create autosave indicator verify + enhance (30 min)

---

## Positive Findings Worth Documenting

The Round 4 page audit identified several exemplary patterns that should be replicated:

1. **dashboard-executive privacy subtitle** — "This dashboard shows overall numbers — individual participant records are kept private" as a subtitle, not a warning banner
2. **Small-cell suppression messaging** — "Percentages hidden (fewer than 5 active participants)" with clear explanation
3. **Data quality indicator** — "Data: Low" badge shows confidence level
4. **Delegation guidance** — "Need More Details? For detailed reports, reach out to the Program Manager" at bottom
5. **plan-view PM1 view-only banner** — Clear explanation of WHY access is limited and WHAT to do next
6. **KoNote 404 page design** — Clear heading, helpful suggestions, Go Back/Home buttons, consistent styling

These patterns should become the standard for all reporting and dashboard pages.

---

*Generated by 4-expert panel review — 2026-03-01*
*15 tickets analysed, 5 deduplicated against existing tracking, 11 net new for TODO*
*4 Tier 1 fixes, 2 Tier 1 verifications, 3 Tier 2, 2 Tier 3*
*2 TEST infrastructure items (qa-scenarios repo, tracked in action plan only)*
