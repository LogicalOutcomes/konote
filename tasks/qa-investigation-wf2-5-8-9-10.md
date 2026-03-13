# QA Investigation: Workflows 2, 5, 8, 9, 10

**Date:** 2026-03-12
**Scope:** Prosper Canada demo instance at `https://konote.logicaloutcomes.net/`
**Method:** Live site navigation (Playwright), seed code review, codebase analysis

---

## Expert Panel: Demo Data & QA Accuracy Review

**Panel Members:**
- **QA Analyst** — validates whether each tester comment is a real bug, a seed data gap, or a test script error
- **Data Engineer** — analyses the seed data pipeline and metric linkage chain
- **Nonprofit UX Specialist** — evaluates discoverability and whether the tester's confusion reflects a real user need

---

### QA Analyst

I navigated the live demo as each role (Raj Coach, Elena Manager, Noor Admin) and compared tester comments to actual site behaviour. Here's the issue-by-issue verdict:

| WF | Tester Comment | Verdict | Evidence |
|----|----------------|---------|----------|
| **WF2** | "Identity basics showing only names; no notes or coaching content" | **Test context error** | Amira has Plan (6 targets), Notes (6), History (6) with coaching content. Tyler has Plan (8), Notes (4), History (3). Tester may not have clicked into tabs. |
| **WF2** | "No reports, meetings, or communications in nav" | **Test context error** | Raj Coach (Direct Service role) sees Meetings and Messages but NOT Reports. Reports requires Program Manager or Executive role. The tester likely expected Reports on a Direct Service account. |
| **WF5** | "No visual charts under Analysis tab" | **Real bug — seed/code gap** | All 12 Prosper participants show "No metric data recorded yet" on the Analysis tab. However, the Insights page confirms MetricValues exist (10 of 12 scored). Root cause is a PlanTargetMetric linkage gap (see Data Engineer analysis below). |
| **WF5** | "Tax filing support content" not found | **Partially valid** | Hana's plan has "Access government benefits" with client goal: "I want to understand what tax benefits I qualify for." Tyler, Olga, Lin, and Kwame have explicit "Tax Filing" plan sections. The tester may have looked at the wrong participant or expected a specific label. |
| **WF8** | "No program called Quality of Life" | **Test script references unbuilt feature** | No program by that name exists. "Quality of Life & Financial Wellbeing Assessment" exists as a **survey** (with 12 completed responses across participants). The two-program design (Quality of Life as a program) is documented in `demo-two-programs.md` but not yet implemented. |
| **WF8** | "No last quarter date range" | **Minor UX gap** | Date filters on the Insights page are: Last 3 months, Last 6 months, Last 12 months, Custom range. "Last quarter" is not an option. |
| **WF9** | "Can't see client's survey history from their file" | **Real UX gap** | Client file tabs are: Info, Plan, Notes, History, Analysis — no Surveys tab. Survey history is only accessible at `/surveys/participant/{id}/` or via Admin > Surveys. The tester's expectation is reasonable. |
| **WF9** | "Hana's tax-filing need isn't listed as a target" | **Accurate but nuanced** | Hana has no "Tax Filing" section. Her closest target is "Access government benefits" with client goal referencing tax benefits. Tyler, Olga, Lin, and Kwame DO have explicit Tax Filing sections with targets. |
| **WF10** | "No admin account called Pridya" | **Test script error** | "Pridya" doesn't exist. Login page shows: Elena Manager, Leila Front Desk, Michel Executive, Noor Admin, Raj Coach. "Priya" is a participant (PC-003), not an admin. |
| **WF10** | "Cannot save settings changes" | **Expected demo behaviour** | Demo accounts use `@demo_read_only` decorator which blocks POST to settings. This is intentional to protect the shared training instance. |

---

### Data Engineer

The critical technical finding is the **PlanTargetMetric linkage gap** that causes empty Analysis charts despite MetricValues existing in the database.

**The data chain has two metric sets that never connect:**

1. **Custom financial metrics** (created in `create_plans`):
   - Monthly Income, Monthly Savings, Credit Score, Debt-to-Income Ratio, etc.
   - These are linked to PlanTargets via `PlanTargetMetric` records
   - But **no MetricValues are ever created** for these metrics

2. **Built-in metrics** (created in `create_metrics`):
   - Goal Progress (1-10), Confidence, Wellbeing, How are you feeling today?, etc.
   - MetricValues ARE created (10 of 12 participants have data)
   - But these are **never linked to PlanTargets** via PlanTargetMetric

**Why Insights works but Analysis doesn't:**

| View | Query path | Works? |
|------|-----------|--------|
| **Insights** (program-level) | `MetricValue → ProgressNote → ClientFile → Enrolment → Program` | Yes — doesn't need PlanTargetMetric |
| **Analysis** (individual) | `PlanTarget → PlanTargetMetric → MetricValue (matching metric_def AND plan_target)` | No — PlanTargetMetric points to financial metrics; MetricValues point to built-in metrics |

**Fix required (seed data):** In `create_metrics()`, add PlanTargetMetric links for the built-in metrics on each participant's plan targets. Specifically:
- Link "Goal Progress (1-10)" to every active PlanTarget (since MetricValues are recorded per-target)
- Link other built-in metrics (Confidence, Wellbeing, etc.) to the first active PlanTarget per participant (since values are only recorded on the first target)

**Fix alternative (code):** Modify the Analysis view to also show MetricValues where the metric_def exists on a ProgressNoteTarget for that plan_target, even without a PlanTargetMetric formal link. This would be more forgiving but changes the design intent (metrics should be formally assigned to targets).

**Recommendation:** Fix the seed data. The Analysis view's strictness (requiring PlanTargetMetric) is correct design — it ensures only intentionally tracked metrics appear on charts.

---

### Nonprofit UX Specialist

From an evaluator/nonprofit manager perspective, three findings matter:

1. **Survey discoverability is poor.** I would expect to find survey results on a client's file, not buried behind a URL I have to memorise. A "Surveys" tab (or at minimum a link from the client file to their survey history) would match how program staff actually work — they open a client file and want to see everything about that person in one place. Priority: medium-high.

2. **"Tax filing" as a plan target label.** The tester's confusion is meaningful. When a participant like Hana explicitly says "I want to understand what tax benefits I qualify for," the plan target "Access government benefits" is semantically correct but not immediately scannable as "tax filing support." This isn't a bug — it's a recognition that plan target names matter for discoverability. The seed data labels are fine for the demo's evaluation purpose.

3. **Role-based navigation is working correctly but confusing in a testing context.** Different demo users see different nav items. The test script should specify which account to use for each workflow, and what nav items that role should see. The fact that the tester expected Reports as a Direct Service worker suggests the test script didn't set expectations for role-based visibility.

---

## Synthesis

### What needs fixing (code or seed data)

| # | Issue | Fix type | Repo | Priority |
|---|-------|----------|------|----------|
| 1 | Analysis tab charts empty for all Prosper participants | **Seed data** — add PlanTargetMetric links for built-in metrics | konote-prosper-canada | **High** |
| 2 | No Surveys tab on client file | **Code** — add Surveys tab or link to client layout | konote | **Medium** |
| 3 | No "last quarter" date filter on Insights | **Code** — add option (nice-to-have) | konote | **Low** |

### What needs fixing (test scripts only)

| # | Issue | Test script fix |
|---|-------|-----------------|
| 4 | "No admin called Pridya" | Correct to "Noor Admin" |
| 5 | "Cannot save settings" | Expected demo behaviour — note in script |
| 6 | "No reports in nav" for Raj Coach | Specify correct role (Elena Manager has Reports) |
| 7 | "No Quality of Life program" | Correct to "Quality of Life & Financial Wellbeing Assessment" survey (not a program) |
| 8 | "Identity basics showing only names" | Add instruction to click into Plan/Notes tabs |

### What's deferred

| Item | Reason |
|------|--------|
| Quality of Life as a separate program | Design exists in `demo-two-programs.md` but awaiting implementation phase |
| Hana-specific tax filing target | Her plan correctly maps to "Access government benefits" — target naming is a content decision, not a bug |
