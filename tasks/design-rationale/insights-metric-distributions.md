# Insights Page & Program Reporting — Design Rationale Record

**Date:** 2026-02-22
**Status:** Design approved by expert panel (4 rounds). Not yet implemented.
**Expert panels:** Round 1: architecture and separation of concerns. Round 2: aggregation design — distributions not averages. Round 3: three data layers and how they collapse. Round 4: client-centred redesign — language, page ordering, executive dashboard, incentive structures, governance reporting.
**GK review required:** Band display labels (strengths-based framing check), clinical instrument thresholds, achievement metric examples per program type, "Two Lenses" card wording, board summary template content

## Core Principles

### 1. Distributions, not averages

Averages are almost meaningless for program management in human services. A mean of 3.2/5 tells a manager nothing actionable.

- **Distribution shape**: How many people are at each level? Where are the clusters?
- **Tails**: How many need more support (low band)? How many are meeting their goals (high band)?
- **Direction of travel**: Is the distribution shifting over time?
- **Median**: Better central tendency than mean for skewed data, but secondary to distribution

A program where half score 1 and half score 5 looks identical to one where everyone scores 3 when you use averages. The distribution tells completely different stories.

### 2. Three distinct data layers

Programs generate three fundamentally different types of data. Each needs different visualization and aggregation:

| Layer | Logic Model Term | What It Answers | Example |
|---|---|---|---|
| **Program outcomes** | End outcomes | "Did the program achieve its intended results?" | 65% got employment, 48% below clinical threshold |
| **Goal metrics** | Intermediate outcomes | "Is progress happening on individual goals?" | Goal Progress distribution, Self-Efficacy trend |
| **Qualitative** | Process quality | "What's the experience like?" | Participant voice, staff assessments, engagement, suggestion themes |

### 3. Per-participant, not per-target

All program-level aggregation uses **one data point per participant**. A program serves people, not goals. If one participant has 6 goals and another has 1, per-target counting makes the first person six times as important. That's statistically wrong and managerially misleading.

For scale metrics: take each participant's **median score across all their active goals** (most honest representation of "how is this person doing overall").

New participants with only 1 assessment are flagged separately: "X participants have only one assessment — not included in distributions."

### 4. Client-centred page hierarchy

The insights page layout reflects a commitment: **participant-generated data leads, staff-generated data follows, system-derived data supports.** This means:
- Participant voice (quotes, suggestions, themes) appears before staff assessments
- When both participant self-report and staff assessment data exist, their comparison is the headline signal
- Quantitative metrics provide context for the qualitative story, not the other way around

### 5. Two separate systems

The insights page and the report generation system are **separate tools with different purposes**. They must not merge.

| Tool | Purpose | Audience | Data Type |
|------|---------|----------|-----------|
| Insights page (`/reports/insights/`) | Ongoing program learning — the workbench | Program managers, executives | All three layers |
| Report generation (`/reports/generate/`) | Formal accountability exports — the finished product | Partners (funders, boards, networks, regulators, etc.) | Quantitative, template-driven |

### 6. Service-framing, not person-labelling

Band labels and dashboard signals describe the **service's effectiveness**, not the participant's state. "More support needed" is a signal to the program. "Struggling" is a judgment of the person. The language throughout the system frames data as information about whether the service is working, not whether the person is succeeding or failing.

### 7. Measurement must not create perverse incentives

Every quantitative signal shown to executives creates pressure. The system mitigates Campbell's Law through:
- Showing trend direction (not band counts) on executive dashboards
- Pairing every quantitative signal with a qualitative signal (participant voice)
- Showing data completeness prominently (prevents selective recording)
- Using "learning" framing throughout (not "performance")

## Per-Program Insights Page

### Page layout (top to bottom)

1. **Summary cards** — 4 horizontal cards, adapt to available data
2. **Participant Voice** — Layer 3: quotes, suggestion themes (with status/priority), ungrouped suggestions
3. **Where Participants Are** — Layer 1: metric distributions (stacked bars + trend lines)
4. **Program Outcomes** — Layer 2: achievement rates (progress bars with journey context)
5. **Staff Assessments** — Layer 3: existing descriptor chart, relabelled
6. **Engagement** — Layer 3: existing pills
7. **AI Narrative** — existing button

### Progressive disclosure

Sections 2-6 use `<details>` elements with preview `<summary>` lines. The `<summary>` line shows the key signal for that section so a PM scanning the page gets useful information even without expanding.

```html
<details>
  <summary>
    <strong>Participant Voice</strong> — 3 open themes · 12 new quotes this period
  </summary>
  [full section content]
</details>
```

**Auto-expand logic (in priority order):**
1. Section with urgent signals (urgent feedback themes, large negative trend shift) → open by default
2. Section with freshest data (most recent recording) → open by default
3. If tie or no clear signal, Participant Voice opens by default (client-centred tiebreaker)
4. Participant Voice must never be the last section to expand — if only quantitative sections would open, Participant Voice also opens

### Summary cards (adapt to available data)

| Program has | Card 1 | Card 2 | Card 3 | Card 4 |
|---|---|---|---|---|
| Both self-report and staff data | Two Lenses (gap signal) | Lead outcome rate (with target if set) | Data completeness | Open feedback themes |
| Achievement outcomes, no self-report | Lead outcome rate (with target) | Trend direction | Data completeness | Open feedback themes |
| Scale metrics only | "Goals within reach" count | Trend direction | Data completeness | Open feedback themes |
| Only qualitative | Engagement rate | Active participants | Data completeness | Open feedback themes |

Data completeness always appears (Card 3). Feedback themes always appear (Card 4) — they're the corruption-resistant signal.

### Two Lenses card (when both data streams exist)

When a program has both participant self-report (e.g., Self-Efficacy) and staff assessment (descriptor distribution) data with sufficient n:

```
TWO LENSES
Participants: 72% feel confident     Staff: 68% rated "good place"
Gap: +4% — participants slightly more optimistic
```

The gap is the signal. When the gap is large, this is the single most important insight on the page. Appears as Card 1 (compact version) and optionally as expanded detail.

### Section 1: Participant Voice (Layer 3, promoted)

Existing: suggestion themes (with status/priority), ungrouped suggestions, quotes. Moved from Section 6 to Section 2 (after summary cards).

Summary line: `Participant Voice — X open themes · Y new quotes this period`

### Section 2: Where Participants Are (Layer 1)

**Snapshot (horizontal stacked bar per metric):**

```
Goal Progress (n=47, most recent: Feb 15)
More support ████████░░░░░░░░░░░░░░ Goals within reach
   20%           18%      30%      32%
```

**Trend (two-line chart per metric):**
- One line: % in low band (needs more support)
- Other line: % in high band (goals within reach)

Two lines tell the story directly: "the low band is shrinking, the high band is growing." Same Chart.js line chart pattern as existing descriptor chart.

**New participant note:** "X participants have only one assessment — not included in distributions. Movement tracking — who is progressing between bands over time — will be available in a future update."

**Metric ordering:**
1. Universal metrics (Goal Progress, Self-Efficacy, Satisfaction) — always shown first
2. Program-specific metrics — only when n >= 10, grouped by category

Summary line: `Where Participants Are — X scored · Y% need more support · trend: improving/stable/declining`

### Section 3: Program Outcomes (Layer 2)

Horizontal progress bars for achievement metrics. Each bar shows:

```
PROGRAM OUTCOMES (n=52 participants this period)

Employment achieved        ██████████████░░░ 65%  (target: 70%)
                            34 of 52  ↑ from 58% last quarter

  Among those not yet employed:
  72% making progress on employability goals
  4 participants need more support
```

The "among those not yet achieved" context line appears when a corresponding scale metric exists. This prevents achievement rates from being read as a binary verdict.

Only appears if the program has achievement metrics defined with n >= 10. Otherwise skipped.

Accessible data table in `<details>` below the bars.

Summary line: `Program Outcomes — 65% employment (target: 70%) · 48% retention`

### Section 4: Staff Assessments (Layer 3, relabelled)

Existing descriptor trend chart stays but relabelled:

> **Staff Assessments Over Time**
> *How workers rate participant progress at each session — a professional judgment, not a measured score*

Summary line: `Staff Assessments — X% rated "good place" · trend: stable`

### Section 5: Engagement (Layer 3)

Existing engagement pills.

Summary line: `Engagement — X% actively engaged · Y% disengaged`

### Section 6: AI Narrative

Existing button.

## Executive Dashboard — Cross-Program View

The executive dashboard shows **all programs at a glance**. Each card uses a **headline + signal + action** pattern. Band-level counts do NOT appear on executive cards — they create perverse incentive pressure. Executives see trend direction, data quality, and participant voice signals.

### Program cards

```
┌─ Youth Employment ──────────────────────┐
│  65% achieving employment goals          │
│  target: 70% · trend: improving ↑        │
│                                          │
│  ● 34 of 42 participants with data       │
│  💬 3 feedback themes to review          │
│                                          │
│  [View program learning →]               │
└──────────────────────────────────────────┘

┌─ Mental Health Services ────────────────┐
│  48% below clinical threshold            │
│  trend: stable →                         │
│                                          │
│  ◐ 28 of 55 participants with data      │
│  💬 1 urgent theme                       │
│                                          │
│  [View program learning →]              │
└─────────────────────────────────────────┘
```

Each card shows:
- **Line 1**: Lead program outcome rate (Layer 2), or lead metric "goals within reach" % (Layer 1) if no outcomes defined
- **Line 2**: Target (if set) + trend direction. No band counts.
- **Line 3**: Data completeness indicator with count
- **Line 4**: Open feedback theme count (with urgency flag)
- **Link**: "View program learning" → per-program insights page

### Data completeness indicators

| Indicator | Meaning |
|---|---|
| ● Full data | >80% of enrolled participants have current scores |
| ◐ Partial data | 50-80% have scores |
| ○ Low data | <50% have scores |

### Visual emphasis

Cards with urgent feedback themes or declining trends get a subtle left border accent (Pico caution colour, not red). This draws attention without creating alarm.

## Two Metric Types

The existing `MetricDefinition` model needs to distinguish two recording patterns:

| Metric Type | Recorded How | Aggregated How | Example |
|---|---|---|---|
| **Scale** | Numeric value, recorded repeatedly | Distribution of per-participant medians | Goal Progress 1-5, PHQ-9 0-27 |
| **Achievement** | Categorical, typically recorded once or at discharge | % who achieved | Got employment (yes/no) |

**Threshold outcomes** (e.g., "PHQ-9 dropped below 10") are derived from scale metrics at query time — they don't need separate recording. If a scale metric has `threshold_high` or `threshold_low` set, the insights page can show a "% meeting threshold" bar in the Program Outcomes section.

## Model Changes Required

### MetricDefinition — new fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `metric_type` | CharField(choices) | "scale" | "scale" or "achievement" |
| `higher_is_better` | BooleanField | True | Direction for scale metrics. PHQ-9 = False |
| `threshold_low` | FloatField | null | Low band boundary (scale metrics) |
| `threshold_high` | FloatField | null | High band boundary (scale metrics) |
| `achievement_options` | JSONField | [] | Dropdown choices for achievement metrics |
| `achievement_success_values` | JSONField | [] | Which options count as "achieved" |
| `target_rate` | FloatField | null | Optional target % for achievement metrics (e.g., "We aim for 70%") |
| `target_band_high_pct` | FloatField | null | Optional target for % in high band for scale metrics |

### Band language framework

**In code (models, views, aggregation functions):**
- `band_low` — the lowest band (needs more support or, for lower-is-better metrics, goals within reach)
- `band_mid` — the middle band
- `band_high` — the highest band (goals within reach or, for lower-is-better metrics, needs more support)

**In display (templates only):**
- Default labels: "More support needed" / "On track" / "Goals within reach"
- GK can override per metric (clinical instruments may have published terminology)
- The words "struggling" and "thriving" do NOT appear anywhere in code, CSS, or templates
- CSS classes use `band-low`, `band-mid`, `band-high`

### Band threshold defaults

| Scale | Low band | Middle | High band |
|---|---|---|---|
| 1-5 (universal) | 1-2 | 3 | 4-5 |
| PHQ-9 (0-27, lower is better) | 15-27 (mod-severe) | 5-14 (mild-moderate) | 0-4 (minimal) |
| Custom scales | Bottom third of range | Middle third | Top third |

Clinical instruments must use published cutoff scores, not scale-thirds. **GK must review all clinical thresholds.**

Fallback when thresholds not set: `threshold_low = min + (max - min) / 3`, `threshold_high = min + 2 * (max - min) / 3`.

## Privacy and Display Thresholds

| Display element | Minimum n | Rationale |
|---|---|---|
| Metric section appears at all | n >= 10 total scores | Below 10, distribution is too sparse to be meaningful |
| Individual band with < 5 people | Show "< 5" | Canadian n < 5 suppression standard (from multi-tenancy DRR) |
| Metric with n < 10 | Show "X scores recorded — at least 10 needed" | Encourages recording without hiding metric existence |
| Achievement rate | n >= 10 participants | Below 10, percentage is misleading |

## Data Completeness — Always Visible

Data completeness appears at three levels:
- **Summary card** (always Card 3): "34 of 57 enrolled have scores this period (60%)"
- **Executive dashboard card**: Data completeness indicator (●/◐/○) with count
- **Warning** when <80%: "Only 60% of enrolled participants have data this period. Distributions may not represent the full program."

This creates healthy pressure to *record data* rather than to *game data*.

**Note on enrolment counts in executive dashboard:** The completeness indicator on executive dashboard cards shows "X of Y enrolled have scores". The enrolled count (Y) is operational data (how many people are in the program), not clinical data. It is already visible elsewhere on each program card (total/active counts). Showing it alongside data completeness does not introduce new privacy exposure but does provide the denominator needed to interpret the completeness percentage meaningfully.

## Movement Tracking (Deferred)

Movement tracking answers: "How many people changed bands this period?" This is the most powerful insight but requires per-client longitudinal comparison (at least 2 data points per participant).

**Deferred to a second pass.** Build the distribution view first. Movement tracking will be added once distributions are validated with real data.

**Required UI acknowledgment:** The insights page must explicitly state: "This shows where participants are now. X participants are new (one assessment only) and are not included in distributions. Movement tracking — who is progressing between bands over time — will be available in a future update."

## Workbench-to-Report Connection

- Show partner report templates linked to this program below the main insights content
- Show data completeness warnings ("Only 30 of 50 participants have Goal Progress recorded this quarter")
- AI narrative can be exported as plain text for partner report narrative sections (copy button already exists)
- **No export button on the insights page** — all exports go through `/reports/generate/`

## Board Summary Template

Boards don't log into KoNote. They receive reports. "Board Summary" is a recognized report template type designed for governance:
- 1-2 pages, PDF format
- Sections: Program Overview (counts, lead outcomes with targets), What Participants Are Telling Us (top themes + curated quotes with privacy protections), Data Quality (completeness), Narrative (editable placeholder)
- Generated quarterly by the executive or PM via `/reports/generate/`
- This is a template configuration, not an architecture change — uses existing report generation system

## Framing Language

- **Never say "performance"** — frame as "where participants are" or "program learning"
- **Never say "struggling" or "thriving"** — use "more support needed" / "goals within reach" (or GK-approved alternatives)
- **Never show averages as the primary display** — distribution is always the headline
- **Every chart must state its data source** — what the data is, how many data points, when last recorded
- Use agency terminology settings for "participants" vs "clients"
- Executive dashboard link always says "View program learning" not "View insights"

## Anti-Patterns (Rejected)

- **Showing averages as the primary metric display** — hides distribution shape, tells managers nothing actionable
- **Averaging across goals (per-target aggregation)** — over-represents people with many goals
- **Treating achievement metrics like scale metrics** — "did they get a job" is not a 1-5 score
- **Putting metrics and descriptors on the same chart** — different data types need different visual treatments
- **Using tabs to separate layers** — managers need to scroll and see everything, not click tabs
- **Box plots** — not understood by non-technical managers
- **Multi-metric charts** — one chart per metric, stacked vertically; no combining different scales
- **Export button on insights page** — bypasses report generation audit trail and privacy safeguards
- **"Performance" framing** — creates pressure to game scores; frame as learning instead
- **"Struggling" / "thriving" language** — locates the problem in the person, not the service. Use service-framing: "more support needed" / "goals within reach"
- **Merging insights and report generation** — different tools, different audiences, different incentive structures
- **Hardcoding program outcomes** — must be configurable per program via MetricDefinition
- **Showing band counts on executive dashboard** — creates Campbell's Law pressure. Show trend direction and data completeness instead.
- **Person-labelling language in code** — variable names like `struggling_count` bake deficit framing into the codebase. Use `band_low_count`.
- **Achievement rate as sole headline** — binary frame erases the journey. Always show scale progress alongside achievement rates when available.
- **Hiding data completeness** — low completeness makes all metrics unreliable. Showing it creates healthy pressure to record.

## Accessibility Requirements

- Colour alone cannot convey meaning — bars need pattern fills or text labels
- Every chart needs an accessible data table (existing `<details>` pattern)
- Colour scheme for bands must pass 4.5:1 contrast ratio (do NOT use red-to-green — use Pico palette)
- All interactive elements keyboard-navigable
- Screen reader announcements for summary card values
- `<summary>` lines must be descriptive enough for screen reader users to decide whether to expand
- Data completeness indicators (●/◐/○) must have text alternatives
