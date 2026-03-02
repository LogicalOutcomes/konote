# QA Action Plan — Round 8b (2026-03-01)

**Date:** 2026-03-01
**Round:** 8b (second evaluation after screenshot manifest fix)
**Source report:** `konote-qa-scenarios/reports/2026-03-01ab-satisfaction-report.md`
**Primary action plan:** `tasks/qa-action-plan-2026-03-01.md` (Round 8a — all tasks remain valid)

This is a **supplementary** action plan. Round 8b re-evaluated the same deployed code as Round 8a with cleaned-up screenshots after the manifest overwrite fix. No code changes occurred between evaluations.

## Headline Metrics

| Metric | Round 7 (aa) | Round 8 (ab) | Change |
|--------|-------------|-------------|--------|
| Satisfaction gap | 0.93 | 1.30 | +0.37 (new bottom: R2-FR at 2.60) |
| Coverage | 44/48 (92%) | 47/49 (96%) | +4% |
| BLOCKERs | 13 | 3 | -10 |
| Red-band | 8 | 3 | -5 |
| Permission violations | 2 | 0 | -2 |
| Overall mean | — | 2.96 | — |
| Tickets | 84 | 76 | -8 |

**Calibration: PASS.** All three anchors within range. CAL-005 was updated on 2026-02-11 from "inaccessible page" (1.0-1.9) to "accessible data table" (3.0-4.5). Score of 3.36 is within the corrected range. Accessibility scores in this report are trustworthy.

---

## Data Integrity Issue

The improvement tickets file (`qa/2026-03-01ab-improvement-tickets.md`) contains **stale Round 7 (aa) data** — 83 tickets with Report ID 2026-03-01aa instead of the expected 76 Round 8 tickets. The file in `konote-qa-scenarios/reports/2026-03-01ab-improvement-tickets.md` has the same problem.

This analysis is based on the satisfaction report (`konote-qa-scenarios/reports/2026-03-01ab-satisfaction-report.md`), which correctly contains Round 8 data.

---

## Expert Panel Summary

**Panel:** Accessibility Specialist, UX Designer, Django Developer, Nonprofit Operations Lead

### Key Insights

**Accessibility Specialist:**
- Calibration is PASS — accessibility scores are valid. No manual verification caveat needed.
- 19 scenarios improved 0.5+ points, with the strongest gains in accessibility areas: SCN-061 (+1.50, form error recovery), SCN-053 (+1.10, form field labels), SCN-054 (+1.00, tab panel), SCN-055 (+1.00, search announcements), SCN-062/063/064/065 (+1.00 each, ARIA and focus improvements).
- Skip link (SCN-052) improved from Red 1.90 to Orange 2.70 — progress, but not yet fixed. The existing QA-R8-A11Y1 verification task is still needed.
- ARIA tablist (SCN-054) improved from 2.00 to 3.00 — now Yellow, but arrow key navigation still fails. QA-R8-A11Y3 remains high priority.

**UX Designer:**
- Satisfaction gap widened from 0.93 to 1.30 — driven by R2-FR (Amelie, French receptionist) scoring 2.60 as the new bottom persona. French language bleed-through in welcome banners is the root cause.
- SCN-086 (funder report) improved dramatically from 1.94 to 3.29 (+1.35) — privacy messaging and aggregate data explanations are working well.
- The 3 Red-band scenarios are all infrastructure-caused: SCN-035 (wrong URL in YAML), SCN-115/SCN-116 (surveys module not built). These are not UX regressions.

**Django Developer:**
- Both regressions are infrastructure-caused, not code regressions:
  - SCN-035 (-0.77): Scenario YAML navigates to `/reports/funder/` but the correct URL is `/reports/funder-report/`. Fix in qa-scenarios repo.
  - SCN-056 (-0.60): Test runner did not apply 200% zoom or high-contrast settings.
- PIPEDA features (BUG-12/13/15 — data export, consent withdrawal, secure links) were built in QA-R7-PRIVACY1 and SEC3 (2026-02-28). SCN-070 still scores 2.39 — verify whether the test runner is reaching the correct UI, or whether the features need UI improvements.
- No new Django code issues found beyond what's in the primary action plan.

**Nonprofit Operations Lead:**
- The primary action plan (Round 8a) remains the correct task list. No reprioritisation needed.
- French language issues (R2-FR as bottom persona) should be escalated: this is a legal compliance matter (Ontario FLSA), not just a UX improvement.
- Survey module (5 scenarios blocked) is tracked separately as SURVEY-LINK1 — exclude from satisfaction scoring calculations until built.
- Test infrastructure (Finding Group #1: interactive step execution) is the highest-ROI fix: it affects 16+ scenarios and artificially deflates scores by producing duplicate screenshots instead of testing the actual workflow.

### Areas of Agreement

1. **Primary action plan is still valid** — all QA-R8 tasks in TODO.md remain correctly prioritised (unanimous)
2. **No code regressions detected** — both score drops are infrastructure-caused (unanimous)
3. **Previous fixes are working** — 19 scenarios improved 0.5+ points, confirming Round 7 fixes had measurable impact (unanimous)
4. **Test runner is the #1 infrastructure priority** — interactive step failures affect the most scenarios and block accurate evaluation (unanimous)
5. **French language is a legal issue** — R2-FR at 2.60 driving the satisfaction gap should be treated as compliance, not polish (unanimous)

### Productive Disagreements

**Should QA-R8-SEC1 (login autofocus race) stay Tier 1?**
- Django Developer: SCN-059 improved from 2.64 to 3.48 — the issue may have been partially addressed or the cleaner screenshots didn't capture it. Verify before prioritising.
- Operations Lead: Keep Tier 1 — credentials in a search bar is a security issue regardless of score improvement. Even if the evaluator didn't catch it, the underlying race condition still exists.
- **Resolution:** Keep Tier 1. Security issues don't downgrade based on score improvements. Verify and fix.

---

## Score Trends

### Improvements (19 scenarios, +0.5 points or more)

| Scenario | R7 | R8 | Change | What Improved |
|----------|-----|-----|--------|---------------|
| SCN-061 | 2.14 | 3.64 | **+1.50** | Form error recovery — error summary, focus management |
| SCN-086 | 1.94 | 3.29 | **+1.35** | Funder report — privacy messaging, aggregate data |
| SCN-053 | 2.00 | 3.10 | **+1.10** | Form field accessibility — clear labels, required indicators |
| SCN-054 | 2.00 | 3.00 | **+1.00** | Tab panels — visual layout (ARIA still missing) |
| SCN-055 | 2.20 | 3.20 | **+1.00** | Search announcements — result rendering |
| SCN-062 | 2.36 | 3.36 | **+1.00** | ARIA live — result count, empty state |
| SCN-063 | 2.36 | 3.36 | **+1.00** | Alt text — colour + text status badges |
| SCN-064 | 2.43 | 3.43 | **+1.00** | Page titles — heading structure |
| SCN-065 | 2.71 | 3.71 | **+1.00** | Focus visibility — blue focus ring |
| SCN-047 | 2.91 | 3.77 | **+0.86** | Mobile 375px — hamburger menu, stacked layout |
| SCN-059 | 2.64 | 3.48 | **+0.84** | Voice nav — visible labels, breadcrumbs |
| SCN-051 | 2.40 | 3.20 | **+0.80** | Login focus — page orientation |
| SCN-052 | 1.90 | 2.70 | **+0.80** | Skip link — partial improvement, still Orange |
| SCN-085 | 2.93 | 3.63 | **+0.70** | Receptionist 403 — consistent template |
| SCN-042 | 2.71 | 3.36 | **+0.65** | Cross-programme — clear isolation messaging |
| SCN-036 | 2.85 | 3.45 | **+0.60** | Programme settings — self-service admin |
| SCN-045 | 2.77 | 3.32 | **+0.55** | Error states — validation messaging |
| SCN-076 | 2.46 | 3.00 | **+0.54** | Group management — permission enforcement |
| SCN-057 | 3.04 | 3.57 | **+0.53** | Touch targets — generous inputs, prominent buttons |

### Regressions (2 scenarios, -0.5 points or more)

| Scenario | R7 | R8 | Change | Root Cause |
|----------|-----|-----|--------|------------|
| SCN-035 | 2.34 | 1.57 | **-0.77** | YAML URL wrong: `/reports/funder/` → should be `/reports/funder-report/` |
| SCN-056 | 3.10 | 2.50 | **-0.60** | Test runner did not apply 200% zoom / high-contrast settings |

Both regressions are infrastructure-caused. No UX or code regressions.

---

## New Items (not in primary action plan)

Only 3 genuinely new items identified:

### 1. Fix SCN-035 YAML URL (qa-scenarios repo)
- SCN-035 navigates to `/reports/funder/` but the correct URL is `/reports/funder-report/`
- This is the sole cause of BLOCKER-1 (score 1.57, Red band)
- Fix in `konote-qa-scenarios/scenarios/periodic/SCN-035.yaml`
- Quick fix (5 min)

### 2. Fix test runner interactive step execution (qa-scenarios repo)
- Finding Group #1 — affects SCN-015, SCN-020, SCN-026, SCN-036, SCN-040, SCN-048, SCN-050, SCN-058, SCN-059, SCN-070, SCN-080, SCN-081, SCN-082, SCN-083, SCN-086 (16+ scenarios)
- The test runner fails to click buttons, fill forms, and trigger HTMX requests — producing duplicate screenshots instead
- Highest-ROI fix for improving evaluation accuracy
- Medium complexity (investigate runner's click/fill logic)

### 3. Fix URL placeholder substitution (qa-scenarios repo)
- Finding Group #2 — affects SCN-075, SCN-076, SCN-084
- Dynamic IDs like `{group_id}`, `{alert_id}`, `{client_id_alex}` appear as literal strings in URLs
- The test runner's prerequisite data ID resolution is not working
- Medium complexity

---

## Existing Plan Confirmation

All tasks in the primary action plan (`tasks/qa-action-plan-2026-03-01.md`) remain valid:

**Tier 1 (Active Work):** QA-R8-SEC1, QA-R8-SEC2, QA-R8-A11Y1, QA-R8-A11Y2, QA-R8-A11Y3, QA-R8-UX1, QA-R8-UX2, QA-R8-PERM1 — no changes.

**Tier 2 (Coming Up):** QA-R8-LANG1 through QA-R8-A11Y7 — no changes.

**Tier 3 (Parking Lot):** QA-R8-VERIFY1, QA-R8-UX13, QA-R8-A11Y8, QA-R8-RPT1, QA-R8-PERM2 — no changes.

---

## Fix Verification Status

Items from `qa/fix-log.json` checked against Round 8 scores:

| Fix | Fix Date | R7 Score | R8 Score | Status |
|-----|---------|---------|---------|--------|
| Skip link (FG-S-5) | 2026-02-21 | SCN-052: 1.90 | 2.70 | Improved but still Orange — not fully verified |
| 404→403 (FG-S-1) | 2026-02-21 | SCN-010: 3.12 | 3.50 | Improved, Yellow — tickets still filed |
| Language (FG-S-2) | 2026-02-21 | SCN-026: 2.25 | 2.60 | Improved but still Orange — language bleed persists |
| Executive nav | 2026-02-22 | SCN-030: 2.71 | 3.25 | Improved, Yellow — "Admin" link still reported visible |
| ARIA tablist | 2026-02-21 | SCN-054: 2.50 | 3.00 | Improved, Yellow — arrow key nav still fails |
| Data export (FG-S-8) | 2026-02-28 | SCN-070: — | 2.39 | Orange — test runner may not reach correct UI |
| Secure links | 2026-02-28 | SCN-151: — | N/E | Not evaluable — test runner blocked |

No fixes can be marked as verified (Green band) in this round. All show improvement but remain Yellow or Orange.

---

## Satisfaction Gap Trend

| Round | Date | Gap | Bottom Persona | Coverage |
|-------|------|-----|----------------|----------|
| 1 | 2026-02-07 | 2.3 | DS3 (1.5) | 69% |
| 2b | 2026-02-08 | 1.5 | DS3 (2.0) | 50% |
| 2c | 2026-02-08 | 1.3 | DS3 (1.9) | 75% |
| 3 | 2026-02-09 | 1.4 | DS2 (2.6) | 75% |
| 4 | 2026-02-12 | 1.3 | DS3 (2.9) | 63% |
| 5 | 2026-02-13 | 0.9 | DS3 (3.2) | 91% |
| 6 | 2026-02-17 | 1.0 | DS4 (3.2) | 67% |
| 7 | 2026-02-21 | 0.93 | DS3 (3.21) | 92% |
| **8** | **2026-03-01** | **1.30** | **R2-FR (2.60)** | **96%** |

Gap widened from 0.93 to 1.30 — driven by R2-FR (French receptionist) becoming the bottom persona due to untranslated English strings in welcome banners (BUG-3/4, FG-S-2). DS3 average improved from 2.55 to 3.13 — the bottom is no longer the accessibility persona.

---

## Pipeline Brittleness — Issues Identified This Round

This section documents process failures and fragile points encountered during the Round 8b `/process-qa-report` run. These are not app bugs — they're weaknesses in the QA pipeline itself.

### B1: Cross-repo file location confusion (FIXED)

**What happened:** The session searched for the satisfaction report and rounds-summary.json inside `konote/reports/` and `konote/qa/` — they don't exist there. It then incorrectly modified `.qa-handoff.json` instead of the actual files.

**Root cause:** The `/process-qa-report` skill definition only referenced `qa/` paths (all inside konote), with no mention that the satisfaction report and rounds-summary.json live in the `konote-qa-scenarios` repo.

**Fix applied:** Added a "File Locations — Two Repos" section to the skill definition with a complete path table. Removed the redundant memory entry.

**Status:** Fixed in `.claude/commands/process-qa-report.md`

### B2: Stale improvement tickets file (NOT FIXED)

**What happened:** The `2026-03-01ab-improvement-tickets.md` file in **both repos** contained Round 7 (aa) data (83 tickets, Report ID `2026-03-01aa`) instead of the expected Round 8 data (76 tickets). The filename says `ab` but the content is from the `aa` round.

**Root cause:** The `/run-scenarios` evaluation pipeline (Step 2) likely overwrote the tickets file with stale data during a partial re-run, or the file was never regenerated for the `ab` round.

**Workaround used:** Fell back to the satisfaction report as the primary data source (it correctly contained Round 8 data).

**Fix applied to skill:** Added a mandatory data integrity check — verify the Report ID in the tickets file matches the current round. If wrong, fall back to the satisfaction report.

**Remaining work:** The root cause is in the `/run-scenarios` pipeline. That skill should validate its output before writing handoff files. This is tracked as a qa-scenarios repo issue, not a konote issue.

### B3: Handoff JSON paths are relative to different repos (DOCUMENTED)

**What happened:** `.qa-handoff.json` contains paths like `"satisfaction_file": "reports/2026-03-01ab-satisfaction-report.md"` — but this path is relative to `konote-qa-scenarios`, not `konote`. A naive `Read("reports/...")` from konote's root fails silently.

**Fix applied:** Documented in the skill's file location table. The handoff JSON now has explicit comments in the skill about which paths are relative to which repo.

### B4: No ticket count validation between pipeline steps (NOT FIXED)

**What happened:** The pipeline log said "76 new tickets" (Step 2) but the tickets file contained 83 tickets from a different round. There's no automated check that Step 2's ticket count matches the file's actual content.

**Recommendation:** The `/run-scenarios` pipeline should write a checksum or ticket count into `.qa-handoff.json` that `/process-qa-report` can validate before proceeding. This would catch stale-file issues immediately.

### B5: External modifications between steps (OBSERVED)

**What happened:** Between the start and end of the `/process-qa-report` run, external processes modified the satisfaction report (changing calibration from PARTIAL PASS to PASS), removed the `calibration_warning` field from `.qa-handoff.json`, and removed it from `rounds-summary.json`.

**Impact:** Low — the session adapted to the corrected data. But this could cause confusion if a session reads a file early, makes decisions based on it, then the file changes underneath.

**Recommendation:** The skill should read all input files at the start and work from those snapshots, not re-read files partway through.

---

*Generated by 4-expert panel review — 2026-03-01*
*Supplementary to primary action plan (tasks/qa-action-plan-2026-03-01.md)*
*76 tickets analysed, 3 new items added, existing plan confirmed valid*
*Pipeline brittleness section added — 5 issues documented, 2 fixed, 3 recommendations*
