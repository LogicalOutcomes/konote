# Dashboard & Insights Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 7 FHIR-metadata-powered features to the Executive Dashboard and Outcome Insights page — all auto-generated from existing data, zero new data entry.

**Architecture:** New computation functions in `apps/reports/insights_fhir.py` (shared by both pages). Dashboard features integrated into existing batch query pattern in `dashboard_views.py`. Insights features added to `insights_views.py` with new template partials.

**Tech Stack:** Django 5, PostgreSQL 16, Chart.js (existing), Pico CSS (existing), HTMX (existing)

**Spec:** `tasks/dashboard-insights-enrichment.md`

---

## File Structure

| File | Responsibility | New/Modify |
|---|---|---|
| `apps/reports/insights_fhir.py` | All FHIR-metadata computation functions (goal source stats, cohort comparison, practice health, program summary, funder stats) | **Create** |
| `apps/reports/insights_views.py` | Add FHIR data to Insights page context | Modify |
| `apps/clients/dashboard_views.py` | Add program summary + funder stats + improved attention signal to dashboard context | Modify |
| `templates/reports/_insights_practice_quality.html` | Practice Health Bar + Goal Source chart + Cross-tab table | **Create** |
| `templates/reports/_insights_cohort.html` | Cohort comparison table | **Create** |
| `templates/reports/insights.html` | Include new partials | Modify |
| `templates/clients/_exec_program_summary.html` | Summary sentence + funder stats partial | **Create** |
| `templates/clients/executive_dashboard.html` | Include summary partial, improved alert | Modify |
| `tests/test_insights_fhir.py` | Tests for all computation functions | **Create** |

---

## Task 1: Computation Functions (insights_fhir.py)

**Files:**
- Create: `apps/reports/insights_fhir.py`
- Test: `tests/test_insights_fhir.py`

This is the shared computation layer. All 7 features pull from functions here.

- [ ] **Step 1: Create `apps/reports/insights_fhir.py` with all computation functions**

```python
"""FHIR-metadata-powered computations for Insights and Dashboard.

All functions return plain dicts — no template logic, no HTML.
Privacy thresholds applied at computation level.
"""
import logging
from collections import defaultdict
from django.db.models import Count, Q
from django.utils.translation import gettext as _

from apps.clients.models import ServiceEpisode
from apps.notes.models import ProgressNote
from apps.plans.models import PlanTarget

logger = logging.getLogger(__name__)

SMALL_PROGRAM_THRESHOLD = 5
MIN_GOALS_FOR_SOURCE_DIST = 20
MIN_DISTINCT_PARTICIPANTS = 5
MIN_PER_CATEGORY_FOR_CROSSTAB = 10


def get_goal_source_distribution(program, date_from=None, date_to=None):
    """Goal source breakdown for a program (Feature A).

    Returns dict with:
        sources: list of {source, label, count, pct}
        total: int
        sufficient: bool (>= MIN_GOALS and >= MIN_DISTINCT_PARTICIPANTS)
    """
    qs = PlanTarget.objects.filter(
        plan_section__program=program,
        status__in=PlanTarget.ACTIVE_STATUSES,
        goal_source__gt="",
    )
    if date_from:
        qs = qs.filter(created_at__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__lte=date_to)

    rows = qs.values("goal_source").annotate(
        count=Count("id"),
        participants=Count("client_file_id", distinct=True),
    ).order_by("-count")

    total = sum(r["count"] for r in rows)
    total_participants = len(set(
        qs.values_list("client_file_id", flat=True)
    ))
    sufficient = total >= MIN_GOALS_FOR_SOURCE_DIST and total_participants >= MIN_DISTINCT_PARTICIPANTS

    labels = dict(PlanTarget.GOAL_SOURCE_CHOICES)
    sources = []
    for r in rows:
        pct = round(r["count"] / total * 100) if total else 0
        # Suppress if count < SMALL_PROGRAM_THRESHOLD
        if r["count"] < SMALL_PROGRAM_THRESHOLD:
            sources.append({
                "source": r["goal_source"],
                "label": str(labels.get(r["goal_source"], r["goal_source"])),
                "count": None,  # suppressed
                "pct": None,
                "suppressed": True,
            })
        else:
            sources.append({
                "source": r["goal_source"],
                "label": str(labels.get(r["goal_source"], r["goal_source"])),
                "count": r["count"],
                "pct": pct,
                "suppressed": False,
            })

    return {"sources": sources, "total": total, "sufficient": sufficient}


def get_goal_source_vs_achievement(program, date_from=None, date_to=None):
    """Goal source crossed with achievement status (Feature B).

    Returns dict with:
        rows: list of {source, label, achieved, total, rate}
        sufficient: bool
        comparison_sentence: str (plain-language comparison)
    """
    qs = PlanTarget.objects.filter(
        plan_section__program=program,
        goal_source__gt="",
        achievement_status__gt="",
    )
    if date_from:
        qs = qs.filter(created_at__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__lte=date_to)

    labels = dict(PlanTarget.GOAL_SOURCE_CHOICES)
    rows = []
    rates_by_source = {}

    for source_val, source_label in PlanTarget.GOAL_SOURCE_CHOICES:
        group = qs.filter(goal_source=source_val)
        total = group.count()
        if total < SMALL_PROGRAM_THRESHOLD:
            continue  # suppress small cells
        achieved = group.filter(
            achievement_status__in=["achieved", "sustaining", "improving"]
        ).count()
        rate = round(achieved / total * 100) if total else 0
        rows.append({
            "source": source_val,
            "label": str(source_label),
            "achieved": achieved,
            "total": total,
            "rate": rate,
        })
        rates_by_source[source_val] = rate

    # Need at least 2 categories with >= MIN_PER_CATEGORY
    qualifying = [r for r in rows if r["total"] >= MIN_PER_CATEGORY_FOR_CROSSTAB]
    sufficient = len(qualifying) >= 2

    # Generate comparison sentence
    comparison = ""
    if sufficient:
        joint_rate = rates_by_source.get("joint", 0)
        worker_rate = rates_by_source.get("worker", 0)
        if joint_rate and worker_rate:
            diff = joint_rate - worker_rate
            if diff >= 10:
                comparison = _(
                    "Goals developed with participants are achieved at a "
                    "%(diff)d percentage-point higher rate than worker-initiated goals."
                ) % {"diff": diff}
            elif diff <= -10:
                comparison = _(
                    "Worker-initiated goals have a higher achievement rate — "
                    "this may reflect more conservative goal-setting."
                )
            else:
                comparison = _(
                    "Achievement rates are similar regardless of who initiated the goal."
                )

    return {"rows": rows, "sufficient": sufficient, "comparison_sentence": comparison}


def get_practice_health(program, date_from=None, date_to=None):
    """Practice quality indicators for the health bar (Feature C).

    Returns dict of indicator dicts, each with:
        value, label, level (good/fair/low), show (bool)
    """
    indicators = {}

    # 1. % goals jointly developed
    source_dist = get_goal_source_distribution(program, date_from, date_to)
    if source_dist["sufficient"]:
        joint_row = next((s for s in source_dist["sources"] if s["source"] == "joint"), None)
        joint_pct = joint_row["pct"] if joint_row and not joint_row["suppressed"] else 0
        level = "good" if joint_pct >= 60 else ("fair" if joint_pct >= 40 else "low")
        indicators["jointly_developed"] = {
            "value": f"{joint_pct}%",
            "label": _("jointly developed"),
            "level": level,
            "show": True,
        }
    else:
        indicators["jointly_developed"] = {"show": False}

    # 2. Data completeness (reuse existing function)
    from apps.reports.metric_insights import get_data_completeness
    completeness = get_data_completeness(program, date_from, date_to)
    if completeness and completeness.get("enrolled", 0) > 0:
        pct = completeness.get("pct", 0)
        level = "good" if pct >= 80 else ("fair" if pct >= 50 else "low")
        indicators["data_completeness"] = {
            "value": f"{pct}%",
            "label": _("data complete"),
            "level": level,
            "show": True,
        }
    else:
        indicators["data_completeness"] = {"show": False}

    # 3. Participant voice (% of detailed notes with reflection/suggestion)
    note_qs = ProgressNote.objects.filter(
        author_program=program,
        note_type="full",
        status="default",
    )
    if date_from:
        note_qs = note_qs.filter(created_at__gte=date_from)
    if date_to:
        note_qs = note_qs.filter(created_at__lte=date_to)
    total_full = note_qs.count()
    if total_full >= 10:
        with_voice = note_qs.exclude(
            _participant_reflection_encrypted=b"",
            _participant_suggestion_encrypted=b"",
        ).count()
        pct = round(with_voice / total_full * 100) if total_full else 0
        level = "good" if pct >= 60 else ("fair" if pct >= 30 else "low")
        indicators["participant_voice"] = {
            "value": f"{pct}%",
            "label": _("participant voice recorded"),
            "level": level,
            "show": True,
        }
    else:
        indicators["participant_voice"] = {"show": False}

    # 4. Sessions per participant
    episodes = ServiceEpisode.objects.filter(
        program=program,
        status__in=ServiceEpisode.ACCESSIBLE_STATUSES,
    )
    active_count = episodes.values("client_file_id").distinct().count()
    if active_count >= SMALL_PROGRAM_THRESHOLD:
        note_count_qs = ProgressNote.objects.filter(
            author_program=program,
            status="default",
        )
        if date_from:
            note_count_qs = note_count_qs.filter(created_at__gte=date_from)
        if date_to:
            note_count_qs = note_count_qs.filter(created_at__lte=date_to)
        note_count = note_count_qs.count()
        per_participant = round(note_count / active_count, 1) if active_count else 0
        indicators["sessions_per_participant"] = {
            "value": str(per_participant),
            "label": _("sessions/participant"),
            "level": "neutral",
            "show": True,
        }
    else:
        indicators["sessions_per_participant"] = {"show": False}

    return indicators


def get_cohort_comparison(program, date_from=None, date_to=None):
    """New intakes vs. re-enrolments outcome comparison (Feature E).

    Returns dict with:
        cohorts: list of {type, label, participants, goals_per, sessions_per, achievement_pct}
        sufficient: bool
        observation: str
    """
    cohorts = []
    rates = {}

    for cohort_type, cohort_label in [("new_intake", _("New Intakes")), ("re_enrolment", _("Re-enrolments"))]:
        ep_qs = ServiceEpisode.objects.filter(
            program=program,
            episode_type=cohort_type,
            status__in=["active", "on_hold", "finished"],
        )
        if date_from:
            ep_qs = ep_qs.filter(enrolled_at__gte=date_from)

        client_ids = list(ep_qs.values_list("client_file_id", flat=True).distinct())
        participant_count = len(client_ids)

        if participant_count < MIN_PER_CATEGORY_FOR_CROSSTAB:
            cohorts.append({
                "type": cohort_type, "label": str(cohort_label),
                "participants": participant_count, "sufficient": False,
            })
            continue

        # Goals per participant
        target_qs = PlanTarget.objects.filter(
            client_file_id__in=client_ids,
            plan_section__program=program,
            status__in=PlanTarget.ACTIVE_STATUSES,
        )
        goal_count = target_qs.count()
        goals_per = round(goal_count / participant_count, 1) if participant_count else 0

        # Sessions per participant
        note_qs = ProgressNote.objects.filter(
            author_program=program,
            client_file_id__in=client_ids,
            status="default",
        )
        if date_from:
            note_qs = note_qs.filter(created_at__gte=date_from)
        if date_to:
            note_qs = note_qs.filter(created_at__lte=date_to)
        sessions = note_qs.count()
        sessions_per = round(sessions / participant_count, 1) if participant_count else 0

        # Achievement rate
        with_achievement = target_qs.filter(achievement_status__gt="")
        total_with = with_achievement.count()
        achieved = with_achievement.filter(
            achievement_status__in=["achieved", "sustaining", "improving"]
        ).count()
        ach_pct = round(achieved / total_with * 100) if total_with >= 10 else None
        rates[cohort_type] = ach_pct

        cohorts.append({
            "type": cohort_type, "label": str(cohort_label),
            "participants": participant_count,
            "goals_per": goals_per,
            "sessions_per": sessions_per,
            "achievement_pct": ach_pct,
            "sufficient": True,
        })

    sufficient = all(c.get("sufficient", False) for c in cohorts) and len(cohorts) == 2

    # Observation sentence
    observation = ""
    if sufficient and rates.get("new_intake") is not None and rates.get("re_enrolment") is not None:
        diff = rates["new_intake"] - rates["re_enrolment"]
        if diff >= 10:
            observation = _("First-time participants are achieving at higher rates than those returning to the program.")
        elif diff <= -10:
            observation = _("Returning participants are achieving at higher rates — the program may be more effective as a 'booster' intervention.")
        else:
            observation = _("Achievement rates are similar for new and returning participants.")

    return {"cohorts": cohorts, "sufficient": sufficient, "observation": observation}


def build_program_summary(program, enrolment_stats, period_label="quarter"):
    """Build structured summary sentence for a program (Feature D).

    Args:
        program: Program instance
        enrolment_stats: dict from _batch_enrolment_stats with total, active, etc.
        period_label: str for the time period

    Returns: str (the formatted sentence) or None if insufficient data
    """
    active = enrolment_stats.get("active", 0)

    if active < SMALL_PROGRAM_THRESHOLD:
        return _(
            "%(program)s has %(active)d active participants. "
            "Aggregate statistics are not shown for programs with fewer "
            "than 5 participants to protect privacy."
        ) % {"program": program.name, "active": active}

    # Count episodes by type
    new_count = ServiceEpisode.objects.filter(
        program=program,
        episode_type="new_intake",
        status__in=ServiceEpisode.ACCESSIBLE_STATUSES,
    ).count()
    returning_count = ServiceEpisode.objects.filter(
        program=program,
        episode_type="re_enrolment",
        status__in=ServiceEpisode.ACCESSIBLE_STATUSES,
    ).count()

    # Session count
    session_count = ProgressNote.objects.filter(
        author_program=program,
        status="default",
    ).count()

    # Goal source
    goal_qs = PlanTarget.objects.filter(
        plan_section__program=program,
        status__in=PlanTarget.ACTIVE_STATUSES,
    )
    goal_count = goal_qs.count()
    joint_count = goal_qs.filter(goal_source="joint").count()
    joint_pct = round(joint_count / goal_count * 100) if goal_count else 0

    # Achievement (partial data)
    with_achievement = goal_qs.filter(achievement_status__gt="")
    total_tracked = with_achievement.count()
    positive = with_achievement.filter(
        achievement_status__in=["achieved", "sustaining", "improving"]
    ).count()

    if total_tracked >= 10:
        ach_pct = round(positive / total_tracked * 100)
        return _(
            "%(program)s is serving %(active)d participants "
            "(%(new)d new, %(returning)d returning this %(period)s). "
            "Staff recorded %(sessions)d sessions. "
            "%(goals)d goals are active, %(joint_pct)d%% jointly developed "
            "with participants. %(ach_pct)d%% of tracked goals show "
            "improvement or achievement."
        ) % {
            "program": program.name, "active": active,
            "new": new_count, "returning": returning_count,
            "period": period_label, "sessions": session_count,
            "goals": goal_count, "joint_pct": joint_pct,
            "ach_pct": ach_pct,
        }
    else:
        return _(
            "%(program)s is serving %(active)d participants "
            "(%(new)d new this %(period)s). "
            "Staff recorded %(sessions)d sessions across "
            "%(goals)d active goals, %(joint_pct)d%% jointly developed "
            "with participants."
        ) % {
            "program": program.name, "active": active,
            "new": new_count, "period": period_label,
            "sessions": session_count, "goals": goal_count,
            "joint_pct": joint_pct,
        }


def build_funder_stats(program, date_from=None, date_to=None):
    """Pre-computed funder-ready stat cards (Feature F).

    Returns list of dicts: {label, value, confidence, note}
    confidence: 'reliable', 'partial', 'insufficient'
    """
    stats = []

    # 1. Participants served (always reliable)
    episodes = ServiceEpisode.objects.filter(
        program=program,
        status__in=["active", "on_hold", "finished"],
    )
    if date_from:
        episodes = episodes.filter(enrolled_at__gte=date_from)
    total_served = episodes.values("client_file_id").distinct().count()
    new_count = episodes.filter(episode_type="new_intake").values("client_file_id").distinct().count()
    returning_count = episodes.filter(episode_type="re_enrolment").values("client_file_id").distinct().count()
    stats.append({
        "label": _("Served"),
        "value": _("%(total)d participants (%(new)d new, %(returning)d returning)") % {
            "total": total_served, "new": new_count, "returning": returning_count,
        },
        "confidence": "reliable",
        "note": "",
    })

    # 2. Sessions delivered (always reliable)
    note_qs = ProgressNote.objects.filter(
        author_program=program,
        status="default",
    )
    if date_from:
        note_qs = note_qs.filter(created_at__gte=date_from)
    if date_to:
        note_qs = note_qs.filter(created_at__lte=date_to)
    session_count = note_qs.count()
    stats.append({
        "label": _("Sessions"),
        "value": _("%(count)d sessions delivered") % {"count": session_count},
        "confidence": "reliable",
        "note": "",
    })

    # 3. Goals jointly developed (reliable when goals exist)
    goal_qs = PlanTarget.objects.filter(
        plan_section__program=program,
        status__in=PlanTarget.ACTIVE_STATUSES,
        goal_source__gt="",
    )
    total_goals = goal_qs.count()
    if total_goals >= 5:
        joint = goal_qs.filter(goal_source="joint").count()
        pct = round(joint / total_goals * 100)
        stats.append({
            "label": _("Goals"),
            "value": _("%(pct)d%% jointly developed with participants") % {"pct": pct},
            "confidence": "reliable",
            "note": "",
        })
    else:
        stats.append({
            "label": _("Goals"),
            "value": _("not enough data"),
            "confidence": "insufficient",
            "note": "",
        })

    # 4. Achieving or improving (partial — depends on metric entry)
    ach_qs = PlanTarget.objects.filter(
        plan_section__program=program,
        status__in=PlanTarget.ACTIVE_STATUSES,
        achievement_status__gt="",
    )
    total_tracked = ach_qs.count()
    total_all = PlanTarget.objects.filter(
        plan_section__program=program,
        status__in=PlanTarget.ACTIVE_STATUSES,
    ).count()
    if total_tracked >= 10:
        positive = ach_qs.filter(
            achievement_status__in=["achieved", "sustaining", "improving"]
        ).count()
        pct = round(positive / total_tracked * 100)
        coverage = round(total_tracked / total_all * 100) if total_all else 0
        conf = "reliable" if coverage >= 80 else "partial"
        stats.append({
            "label": _("Improving"),
            "value": _("%(pct)d%% of tracked goals improving or achieved") % {"pct": pct},
            "confidence": conf,
            "note": _("%(tracked)d of %(total)d have metric data") % {
                "tracked": total_tracked, "total": total_all,
            } if conf == "partial" else "",
        })
    else:
        stats.append({
            "label": _("Improving"),
            "value": _("not enough data"),
            "confidence": "insufficient",
            "note": "",
        })

    # 5. Program completion (partial — depends on discharge workflow)
    finished = ServiceEpisode.objects.filter(
        program=program, status="finished",
    )
    if date_from:
        finished = finished.filter(ended_at__gte=date_from)
    total_finished = finished.count()
    with_reason = finished.exclude(end_reason="").count()
    if total_finished >= 10 and with_reason / total_finished >= 0.5:
        completed = finished.filter(end_reason__in=["completed", "goals_met"]).count()
        pct = round(completed / total_finished * 100)
        coverage = round(with_reason / total_finished * 100)
        conf = "reliable" if coverage >= 80 else "partial"
        stats.append({
            "label": _("Completed"),
            "value": _("%(pct)d%% completed program") % {"pct": pct},
            "confidence": conf,
            "note": _("%(with_reason)d of %(total)d have discharge reason") % {
                "with_reason": with_reason, "total": total_finished,
            } if conf == "partial" else "",
        })
    else:
        stats.append({
            "label": _("Completed"),
            "value": _("not enough data"),
            "confidence": "insufficient",
            "note": "",
        })

    return stats
```

- [ ] **Step 2: Create `tests/test_insights_fhir.py` with core tests**

Tests for goal source distribution, cross-tab, practice health, cohort comparison, program summary, and funder stats. Follow existing test patterns from `tests/test_insights.py` — use `@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)`, `databases = {"default", "audit"}`, create Program, ClientFile, PlanSection, PlanTarget, ServiceEpisode, ProgressNote in setUp.

Key test scenarios:
- `test_goal_source_distribution_basic` — 3 sources, correct counts/pcts
- `test_goal_source_distribution_suppression` — category with < 5 shows suppressed
- `test_goal_source_distribution_insufficient` — < 20 goals returns sufficient=False
- `test_crosstab_comparison_sentence` — joint rate > worker rate by 10+ → correct sentence
- `test_crosstab_insufficient` — < 2 qualifying categories → sufficient=False
- `test_practice_health_indicators` — all 4 indicators computed
- `test_cohort_comparison_basic` — new vs returning with different rates
- `test_cohort_comparison_insufficient_returning` — < 10 re-enrolments → sufficient=False
- `test_program_summary_sufficient_data` — full template rendered
- `test_program_summary_small_program` — < 5 participants → privacy template
- `test_funder_stats_confidence_levels` — reliable, partial, insufficient stats

- [ ] **Step 3: Commit**

```bash
git add apps/reports/insights_fhir.py tests/test_insights_fhir.py
git commit -m "feat: add FHIR metadata computation functions for insights and dashboard"
```

---

## Task 2: Insights Page Integration (Features A, B, C, E)

**Files:**
- Modify: `apps/reports/insights_views.py`
- Create: `templates/reports/_insights_practice_quality.html`
- Create: `templates/reports/_insights_cohort.html`
- Modify: `templates/reports/insights.html`

- [ ] **Step 1: Add FHIR data to Insights view context**

In `apps/reports/insights_views.py`, in the main `insights_view` function, after existing data computation (metric distributions, achievement rates, etc.), add:

```python
from apps.reports.insights_fhir import (
    get_goal_source_distribution,
    get_goal_source_vs_achievement,
    get_practice_health,
    get_cohort_comparison,
)

# FHIR metadata features
goal_source_dist = get_goal_source_distribution(program, date_from, date_to)
goal_source_crosstab = get_goal_source_vs_achievement(program, date_from, date_to)
practice_health = get_practice_health(program, date_from, date_to)
cohort_data = get_cohort_comparison(program, date_from, date_to)
```

Add these to the template context dict.

- [ ] **Step 2: Create `templates/reports/_insights_practice_quality.html`**

Practice Health Bar (Feature C) + Goal Source Distribution chart (Feature A) + Cross-tab table (Feature B). Uses existing `exec-` CSS namespace, `<details>` for layered disclosure, Chart.js horizontal bar chart via `{% json_script %}`, accessible data table.

- [ ] **Step 3: Create `templates/reports/_insights_cohort.html`**

Cohort comparison table (Feature E) with observation sentence. Wrapped in `<details>`.

- [ ] **Step 4: Include partials in `templates/reports/insights.html`**

Add after existing "Program Outcomes" section:
```django
{% include "reports/_insights_practice_quality.html" %}
{% include "reports/_insights_cohort.html" %}
```

- [ ] **Step 5: Commit**

```bash
git add apps/reports/insights_views.py templates/reports/_insights_practice_quality.html templates/reports/_insights_cohort.html templates/reports/insights.html
git commit -m "feat: add practice quality and cohort analysis to Insights page"
```

---

## Task 3: Executive Dashboard Integration (Features D, F, G)

**Files:**
- Modify: `apps/clients/dashboard_views.py`
- Create: `templates/clients/_exec_program_summary.html`
- Modify: `templates/clients/executive_dashboard.html`

- [ ] **Step 1: Add summary + funder stats to dashboard view**

In `dashboard_views.py`, in the main `executive_dashboard` view, after existing batch computations, add per-program summary and funder stats. Since `_batch_program_learning` already iterates per-program, add the summary computation inside that existing loop to avoid a new loop.

```python
from apps.reports.insights_fhir import build_program_summary, build_funder_stats

# Inside the per-program data assembly:
program_data["summary_sentence"] = build_program_summary(
    program, enrolment_stats.get(pid, {}), period_label
)
program_data["funder_stats"] = build_funder_stats(
    program, date_from, date_to
)
```

- [ ] **Step 2: Improve attention signal (Feature G)**

Enhance existing `_count_without_notes` to use episode-aware query. Replace the current simple count with:

```python
def _count_stale_episodes(program_id, active_client_ids, thirty_days_ago):
    """Active episodes with no note in 30+ days (enhanced attention signal)."""
    if not active_client_ids:
        return 0
    clients_with_recent = set(
        ProgressNote.objects.filter(
            client_file_id__in=active_client_ids,
            author_program_id=program_id,
            created_at__gte=thirty_days_ago,
            status="default",
        ).values_list("client_file_id", flat=True)
    )
    return len(active_client_ids - clients_with_recent)
```

- [ ] **Step 3: Create `templates/clients/_exec_program_summary.html`**

Summary sentence card + expandable funder stats `<details>`. Uses existing `exec-` CSS namespace and `completeness-indicator` classes for confidence dots.

- [ ] **Step 4: Include partial in `templates/clients/executive_dashboard.html`**

Add `{% include "clients/_exec_program_summary.html" %}` at the top of each program card, before existing metric rows.

- [ ] **Step 5: Commit**

```bash
git add apps/clients/dashboard_views.py templates/clients/_exec_program_summary.html templates/clients/executive_dashboard.html
git commit -m "feat: add program summary, funder stats, and improved alerts to dashboard"
```

---

## Task 4: Translations

- [ ] **Step 1: Run translate_strings on VPS**

```bash
ssh konote-vps "cd /opt/konote-dev && sudo docker compose exec -T web python manage.py translate_strings"
```

- [ ] **Step 2: Fill French translations for new strings**

New translatable strings in `insights_fhir.py` — all the `_()` wrapped strings need French equivalents in the .po file.

- [ ] **Step 3: Recompile and commit**

```bash
ssh konote-vps "cd /opt/konote-dev && sudo docker compose exec -T web python manage.py translate_strings"
git add locale/
git commit -m "chore: add French translations for insights enrichment"
```

---

## Task 5: Deploy and Verify

- [ ] **Step 1: Push, create PR, merge**
- [ ] **Step 2: Deploy to dev VPS**
- [ ] **Step 3: Verify Insights page loads with new sections**
- [ ] **Step 4: Verify Executive Dashboard shows summary sentences**
- [ ] **Step 5: Check accessibility (data tables present, screen reader labels)**
