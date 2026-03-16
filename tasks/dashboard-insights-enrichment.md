# Dashboard & Insights Enrichment — Design Spec

**Status:** Design — awaiting approval
**Created:** 2026-03-16
**Expert panel:** 5 experts, 2 rounds (Nonprofit Program Director, Data Storytelling Specialist, Evaluation Methodologist, Information Design Expert, Feedback-Informed Practice Specialist)
**Data quality review:** Features filtered for real-world data completeness — only uses always-populated fields or gracefully degrades when data is partial

---

## What This Is

Seven enhancements to the Executive Dashboard and Outcome Insights page, all using data that is automatically populated (no new data entry), all self-aware about data gaps, and all maintainable with Django templates + HTMX + Pico CSS + Chart.js.

## Design Principles

1. **Use only reliable data.** Note counts, goal counts, episode types, and goal_source are always complete (auto-populated on save). Duration, alliance, and end_reason are often missing — never depend on them as the sole data source for a feature.
2. **Degrade gracefully.** Every feature must handle "not enough data" by showing a clear message, not by showing misleading partial results. Use data sufficiency thresholds.
3. **Narrative over numbers.** Lead with plain-language sentences that a board member can understand. Show the supporting numbers underneath.
4. **Process and outcomes together.** Show how the service is being delivered (process quality) alongside what's happening for participants (outcomes).
5. **No cross-program comparison.** Per DRR: different programs serve different populations with different metrics. Show per-program trends, not league tables.
6. **Maintain existing patterns.** Use `<details>` for layered disclosure, Pico CSS grid for cards, Chart.js for visualisations, HTMX for interactivity. No new frontend dependencies.

---

## Two Pages, Two Audiences

| | Executive Dashboard | Outcome Insights |
|---|---|---|
| **URL** | `/clients/executive/` | `/reports/insights/` |
| **Audience** | Executive director, board, agency leadership | Program managers |
| **Question it answers** | "What's happening across the agency?" | "How is this program working and why?" |
| **Scope** | All programs on one screen | One program at a time |
| **Depth** | Headlines, summaries, funder-ready stats | Analytical — distributions, cross-tabs, process quality |
| **Individual data** | Never — aggregate only (RBAC enforced) | Aggregate with richer breakdowns; participant voice for PM role |
| **New features** | D (summary sentence), F (funder stats), G (attention signal) | A (goal source chart), B (cross-tab), C (health bar), E (cohort comparison) |

**Design rule:** The dashboard should never require a program manager's analytical eye to interpret. If a number needs context to avoid misinterpretation, it belongs on the Insights page, not the dashboard.

---

## Feature A: Goal Source Distribution (Insights Page)

**What it shows:** A horizontal stacked bar showing what proportion of goals were participant-initiated, jointly developed, worker-initiated, or funder-required.

**Data source:** `PlanTarget.goal_source` — auto-classified on save from description/client_goal field patterns. Always populated for goals where at least one of those fields is filled in.

**Query:**
```python
PlanTarget.objects.filter(
    plan_section__program=program,
    status__in=PlanTarget.ACTIVE_STATUSES,
    goal_source__gt="",
).values("goal_source").annotate(count=Count("id"))
```

**Display:**
```
Who initiates goals?  (n=142)
  Jointly developed  ████████████████████  58%
  Participant         ██████               20%
  Worker              ████                 15%
  Funder-required     ██                    7%
```

Horizontal stacked bar (Chart.js). Plain-language headline above. Sample size shown. Suppression: if any category < 5, suppress that category's count (show "< 5").

**Threshold:** Only show when total goals with goal_source >= 20 AND goals come from >= 5 distinct participants (aligns with `SMALL_PROGRAM_THRESHOLD`).

**Where it goes:** Insights page, new section "Practice Quality" placed after the existing Participant Voice section. Wrapped in `<details>` with auto-expand logic.

**Accessibility:** Data table in `<details>` below chart. Colour + text labels. `aria-label` on canvas.

---

## Feature B: Goal Source vs. Achievement Cross-Tab (Insights Page)

**What it shows:** Do jointly-developed goals get achieved at higher rates than worker-initiated ones? A simple table with rates and sample sizes.

**Data source:** `PlanTarget.goal_source` + `PlanTarget.achievement_status`. Both auto-populated. Achievement status depends on metric entry, so this only appears when sufficient data exists.

**Query:**
```python
targets = PlanTarget.objects.filter(
    plan_section__program=program,
    goal_source__gt="",
    achievement_status__gt="",
)
# Group by goal_source, count achieved/sustaining vs total
for source in ["participant", "worker", "joint", "funder_required"]:
    group = targets.filter(goal_source=source)
    total = group.count()
    achieved = group.filter(
        achievement_status__in=["achieved", "sustaining"]
    ).count()
```

**Display:**
```
Goal source and achievement

                        Achieved    Total    Rate
Jointly developed          41        58      71%
Participant-initiated      12        19      63%
Worker-initiated            8        22      36%

Goals developed with participants are achieved nearly twice as
often as worker-initiated goals.
```

Plain table. Below the table, an auto-generated plain-language comparison sentence. The sentence template:

- If joint rate > worker rate by 10+ points: "Goals developed with participants are achieved at a {diff} percentage-point higher rate than worker-initiated goals." (where `diff = joint_rate - worker_rate`, a simple subtraction — not relative difference)
- If rates are similar (within 10 points): "Achievement rates are similar regardless of who initiated the goal."
- If worker rate > joint rate: "Worker-initiated goals have a higher achievement rate — this may reflect more conservative goal-setting."

**Threshold:** Only show when at least 2 goal_source categories each have >= 10 goals with achievement_status. Below that, show: "Not enough data yet to compare achievement by goal source. As more goals are tracked, this analysis will appear automatically."

**Suppression:** Any row with total < 5 is suppressed entirely.

**Where it goes:** Insights page, inside the "Practice Quality" section, below the goal source distribution chart.

---

## Feature C: Practice Health Bar (Insights Page)

**What it shows:** A compact row of 3-4 process quality indicators across the top of the Insights page.

**Indicators (using only reliable data):**

| Indicator | Source | Computation | Always Complete? |
|---|---|---|---|
| % goals jointly developed | goal_source | joint / (joint + participant + worker + funder_required) | Yes (for goals with goal_source) |
| Data completeness | metric recordings / enrolled participants | Existing `get_data_completeness()` function | Yes |
| Participant voice | % of detailed notes with participant reflection or suggestion recorded | `_participant_reflection_encrypted != b""` OR `_participant_suggestion_encrypted != b""` on ProgressNote where note_type="full" | Yes (field is populated or not) |
| Sessions per participant | note count / active participant count | Always-complete counts | Yes |

**Display:**
```html
<div class="grid exec-health-bar">
  <div class="exec-health-item">
    <span class="exec-health-icon" aria-hidden="true">&#9679;</span>
    <span class="sr-only">Jointly developed:</span>
    <strong>78%</strong> jointly developed
  </div>
  <!-- ... repeat for each indicator -->
</div>
```

Compact horizontal row using Pico CSS grid. Each indicator uses the existing `exec-` CSS namespace and `completeness-indicator` pattern from the dashboard template (lines 467-475). No emojis — use styled spans with `aria-hidden` and separate `sr-only` labels for screen readers.

**Colour coding:** Each indicator gets a contextual colour:
- Jointly developed: >= 60% green, 40-59% neutral, < 40% amber
- Data completeness: >= 80% green, 50-79% neutral, < 50% amber
- Participant voice: >= 60% green, 30-59% neutral, < 30% amber
- Sessions/participant: no colour (informational only, no inherent "good" threshold)

**Threshold:** Show bar when program has >= 5 active participants. Hide individual indicators when their data is insufficient (e.g., no goals → hide jointly developed; no detailed notes → hide participant voice).

**Where it goes:** Insights page, immediately below the filter form and above the existing summary cards. Always visible (not in `<details>`).

---

## Feature D: Structured Program Summary (Executive Dashboard)

**What it shows:** A 2-3 sentence paragraph per program that synthesises key statistics into a narrative. No AI needed — programmatically generated from a sentence template with computed values.

**Data sources (all reliable):**

| Data Point | Query | Always Complete? |
|---|---|---|
| Active participant count | ServiceEpisode.filter(status__in=ACCESSIBLE) | Yes |
| New this period | ServiceEpisode.filter(episode_type="new_intake", enrolled_at__gte=period_start) — matches existing `_batch_enrolment_stats` pattern | Yes |
| Returning this period | ServiceEpisode.filter(episode_type="re_enrolment", enrolled_at__gte=period_start) | Yes |
| Total sessions this period | ProgressNote.filter(author_program=X, created_at__gte=period_start).count() — uses author_program to match existing dashboard queries | Yes |
| Goals set (with source) | PlanTarget.filter(plan_section__program=X).count() + goal_source breakdown | Yes |
| Achievement rate | PlanTarget with achievement_status in achieved/sustaining / total with any achievement_status | Partial — only when metrics recorded |

**Sentence templates:**

Template 1 (sufficient data — achievement available):
> "{program} is serving {active} participants ({new} new, {returning} returning this {period}). Staff recorded {sessions} sessions. {goal_count} goals are active, {joint_pct}% jointly developed with participants. {achievement_pct}% of tracked goals show improvement or achievement."

Template 2 (minimal data — no achievement):
> "{program} is serving {active} participants ({new} new this {period}). Staff recorded {sessions} sessions across {goal_count} active goals, {joint_pct}% jointly developed with participants."

Template 3 (very small program — < 5 participants):
> "{program} has {active} active participants. Aggregate statistics are not shown for programs with fewer than 5 participants to protect privacy."

**Display:** Appears as the first element in each program card on the executive dashboard. Slightly styled to stand out from the numeric stats below it (e.g., a bordered card or subtle background). Replaces nothing — it's additive above the existing stats.

**Where it goes:** Executive dashboard, per-program card, at the top before existing metrics.

**Implementation:** Data for summaries should be computed in the existing batch query pattern (following `_batch_enrolment_stats`, `_batch_engagement_quality`). A new `_batch_program_summaries(programs, period_start)` function returns a dict keyed by program_id with template variables. This avoids per-program query loops that would regress the dashboard's O(10) query architecture to O(10*N).

**Translation:** Sentence templates must use Django `gettext()` with `%(name)s` placeholders — not f-strings or `.format()`. Example:
```python
from django.utils.translation import gettext as _
summary = _("%(program)s is serving %(active)d participants (%(new)d new, %(returning)d returning this %(period)s).") % {
    "program": program_name, "active": active, "new": new, "returning": returning, "period": period_label,
}
```
This ensures French translations work correctly via the .po file.

---

## Feature E: Cohort Comparison — New vs. Returning (Insights Page)

**What it shows:** Side-by-side comparison of outcomes for first-time participants vs. re-enrolments.

**Data source:** `ServiceEpisode.episode_type` (auto-derived, always populated) crossed with goal achievement data.

**Query:**
```python
for cohort in ["new_intake", "re_enrolment"]:
    episodes = ServiceEpisode.objects.filter(
        program=program, episode_type=cohort,
        status__in=["active", "on_hold", "finished"],
        enrolled_at__gte=date_from,  # Respect Insights page date filter
    )
    # client_ids is a lazy queryset — Django handles as subquery
    client_ids = episodes.values_list("client_file_id", flat=True)
    targets = PlanTarget.objects.filter(
        client_file_id__in=client_ids,
        plan_section__program=program,
        achievement_status__gt="",
    )
    # Compute achievement rate, goal count, session count
```

**Display:**
```
New vs. Returning Participants

                    New Intakes    Re-enrolments
Participants             38              9
Goals per person         3.2            2.8
Sessions per person      12.4           8.1
Achieving/improving      68%            52%
```

Simple comparison table. Below, a plain-language observation:
- If new > returning by 10+ points: "First-time participants are achieving at higher rates than those returning to the program."
- If returning > new: "Returning participants are achieving at higher rates — the program may be more effective as a 'booster' intervention."
- If similar: "Achievement rates are similar for new and returning participants."

**Threshold:** Only show when both cohorts have >= 10 participants with achievement data. If re-enrolments < 10, show: "Your program has very few returning participants — cohort comparison will appear when there are at least 10 in each group."

**Suppression:** Standard small-cell rules apply.

**Where it goes:** Insights page, new section "Cohort Analysis" after Program Outcomes. Wrapped in `<details>`.

---

## Feature F: Funder-Ready Stat Cards (Executive Dashboard)

**What it shows:** Pre-computed answers to the 5 questions every funder asks, with data confidence indicators.

**The five stats:**

| Stat | Source | Confidence |
|---|---|---|
| Participants served | Episode count by type | Always complete |
| Sessions delivered | Note count per episode | Always complete |
| Goals jointly developed | goal_source distribution | Always complete (when goals exist) |
| Achieving or improving | achievement_status distribution | Partial (depends on metric entry) |
| Program completion | end_reason on finished episodes | Partial (depends on discharge workflow) |

**Display:**
```
Funder Quick Stats (Youth Employment, Apr 2025 – Mar 2026)

  Served: 47 participants (38 new, 9 returning)         ● reliable
  Sessions: 342 sessions delivered                       ● reliable
  Goals: 78% jointly developed with participants         ● reliable
  Improving: 68% of tracked goals improving or achieved  ◐ partial (34 of 47 have metric data)
  Completed: data not available                          ○ insufficient
```

Each stat has a confidence dot:
- ● (green) = data covers > 80% of relevant records
- ◐ (amber) = data covers 50-80%
- ○ (grey) = data covers < 50% or not applicable — stat hidden or shows "not available"

**Key design decision:** Stats with ○ confidence are shown as "not available" rather than hidden, so executives understand what data the agency needs to improve, not just what's working.

**Where it goes:** Executive dashboard, expandable `<details>` per program below the summary sentence. Label: "Funder Quick Stats".

**Implementation:** Computed within the same `_batch_program_summaries()` function as Feature D to avoid additional per-program queries. Returns a list of stat dicts with value, label, confidence level, and explanatory note. Confidence dots reuse existing CSS classes (`completeness-indicator`, `completeness-partial`, `completeness-low`) from the dashboard template.

---

## Feature G: Simple Attention Signal (Executive Dashboard)

**What it shows:** Participants in active service episodes who haven't had a session recently — a more precise version of the current "participants without notes this month."

**Data source:** Episodes with `status__in=ACCESSIBLE_STATUSES` + last note date per client. Uses only always-complete data (episode status, note created_at). Query uses `author_program` (not episode FK) to match the existing `_count_without_notes()` function pattern.

**Current implementation:** `_count_without_notes()` in `dashboard_views.py` line 51 counts clients with no notes this month. Crude — doesn't consider episode status.

**Improved version (enhances existing function in place):**
```python
# Participants in active episodes with no note in the last 30 days
# Uses author_program for consistency with existing dashboard queries
stale_episodes = ServiceEpisode.objects.filter(
    program=program,
    status__in=ServiceEpisode.ACCESSIBLE_STATUSES,
).exclude(
    client_file_id__in=ProgressNote.objects.filter(
        author_program=program,
        created_at__gte=thirty_days_ago,
    ).values("client_file_id")
)
```

**Display:** On the executive dashboard summary cards, replace "Participants without notes this month" with:

```
⚠ 3 active participants haven't been seen in 30+ days
```

If > 5: amber alert card. If 0: no card shown (reduce noise).

**Where it goes:** Executive dashboard, replaces or enhances the existing "without notes" summary card.

---

## Files to Modify

| File | Changes |
|---|---|
| `apps/reports/insights_views.py` | Add goal source distribution, cross-tab, cohort comparison data to context |
| `apps/reports/insights.py` (or new `insights_fhir.py`) | Computation functions for features A, B, E |
| `templates/reports/insights.html` | Add Practice Health Bar, goal source chart, cross-tab table, cohort section |
| `templates/reports/_insights_goal_source.html` | New partial for goal source chart |
| `templates/reports/_insights_cohort.html` | New partial for cohort comparison |
| `apps/clients/dashboard_views.py` | Add `_batch_program_summaries()` (for Features D+F), enhance `_count_without_notes()` for Feature G |
| `templates/clients/executive_dashboard.html` | Add summary sentence, funder stats `<details>`, improved alert card |
| `tests/test_insights.py` or `tests/test_executive_dashboard.py` | Tests for new computation functions |

## What This Does NOT Change

- No new Django models or migrations (all data already exists)
- No new form fields or user-facing inputs
- No new JavaScript dependencies (Chart.js already present)
- No changes to the existing metric distribution, achievement rate, or participant voice sections
- No cross-program comparisons
- No features that depend on optional fields (duration, alliance, end_reason) as sole data source

## Privacy & Accessibility

- All existing suppression rules apply (n < 5 → suppress, n < 10 → skip section)
- Goal source cross-tab suppresses any row with < 5 goals
- Cohort comparison requires >= 10 per cohort
- Data confidence dots use colour + symbol (not colour alone)
- All charts get accessible data tables in `<details>`
- All new text is translatable (`{% trans %}` / `gettext`)
- Sentence templates are bilingual (EN template + FR template)

## Data Sufficiency Thresholds Summary

| Feature | Minimum to Show |
|---|---|
| Goal Source Distribution | 20+ goals with goal_source |
| Goal Source vs. Achievement | 2+ categories with 10+ goals each having achievement_status |
| Practice Health Bar | 5+ active participants |
| Structured Summary | 1+ active participant (template adapts) |
| Cohort Comparison | 10+ in each cohort with achievement data |
| Funder-Ready Stats | Per-stat confidence threshold (see above) |
| Attention Signal | 1+ active episode (always relevant) |
