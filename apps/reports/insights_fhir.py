"""FHIR-metadata-powered computations for Insights and Dashboard.

All functions return plain dicts — no template logic, no HTML.
Privacy thresholds applied at computation level.
"""
import logging
from django.db.models import Count
from django.utils.translation import gettext as _

from apps.clients.models import ServiceEpisode
from apps.notes.models import ProgressNote
from apps.plans.models import PlanTarget
from apps.reports.metric_insights import get_data_completeness

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

    rows = list(qs.values("goal_source").annotate(
        count=Count("id"),
    ).order_by("-count"))

    total = sum(r["count"] for r in rows)
    # Distinct participant count (single efficient query)
    total_participants = (
        qs.values("client_file_id").distinct().count()
        if total >= MIN_GOALS_FOR_SOURCE_DIST else 0
    )
    sufficient = (
        total >= MIN_GOALS_FOR_SOURCE_DIST
        and total_participants >= MIN_DISTINCT_PARTICIPANTS
    )

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

    NOTE: Not currently wired to any view (cross-tab removed from Insights
    page during simplification). Retained for potential future use; tested
    in test_insights_fhir.py.

    Returns dict with:
        rows: list of {source, label, achieved, total, rate}
        sufficient: bool
        comparison_sentence: str (plain-language comparison)
    """
    # Intentionally includes all statuses (not just ACTIVE_STATUSES) because
    # completed/deactivated goals with achievement data are valid for
    # cross-tab analysis — we want the full historical picture.
    qs = PlanTarget.objects.filter(
        plan_section__program=program,
        goal_source__gt="",
        achievement_status__gt="",
    )
    if date_from:
        qs = qs.filter(created_at__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__lte=date_to)

    rows = []
    rates_by_source = {}

    for source_val, source_label in PlanTarget.GOAL_SOURCE_CHOICES:
        group = qs.filter(goal_source=source_val)
        total = group.count()
        if total < SMALL_PROGRAM_THRESHOLD:
            continue  # suppress small cells
        achieved = group.filter(
            achievement_status__in=PlanTarget.POSITIVE_ACHIEVEMENT_STATUSES
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
                    "%(diff)d percentage-point higher rate than "
                    "worker-initiated goals."
                ) % {"diff": diff}
            elif diff <= -10:
                comparison = _(
                    "Worker-initiated goals have a higher achievement rate "
                    "— this may reflect more conservative goal-setting."
                )
            else:
                comparison = _(
                    "Achievement rates are similar regardless of who "
                    "initiated the goal."
                )

    return {
        "rows": rows,
        "sufficient": sufficient,
        "comparison_sentence": comparison,
    }


def get_practice_health(program, date_from=None, date_to=None,
                        goal_source_dist=None, data_completeness=None):
    """Practice quality indicators for the health bar (Feature C).

    Args:
        goal_source_dist: Pre-computed result from get_goal_source_distribution
            (avoids redundant query when caller already has it).
        data_completeness: Pre-computed result from get_data_completeness
            (avoids redundant query when caller already has it).

    Returns dict of indicator dicts, each with:
        value, label, level (good/fair/low), show (bool)
    """
    indicators = {}

    # 1. % goals jointly developed
    source_dist = goal_source_dist or get_goal_source_distribution(program, date_from, date_to)
    joint_row = next(
        (s for s in source_dist["sources"] if s["source"] == "joint"),
        None,
    )
    can_show_joint_indicator = (
        source_dist["total"] >= SMALL_PROGRAM_THRESHOLD
        and (joint_row is None or not joint_row["suppressed"])
    )
    if can_show_joint_indicator:
        joint_pct = joint_row["pct"] if joint_row else 0
        level = "good" if joint_pct >= 60 else ("fair" if joint_pct >= 40 else "low")
        indicators["jointly_developed"] = {
            "value": f"{joint_pct}%",
            "label": _("jointly developed"),
            "level": level,
            "show": True,
        }
    else:
        indicators["jointly_developed"] = {"show": False}

    # 2. Data completeness (reuse existing function or pre-computed value)
    if data_completeness is None:
        data_completeness = get_data_completeness(program, date_from, date_to)
    completeness = data_completeness
    if completeness and completeness.get("enrolled_count", 0) > 0:
        pct = completeness.get("completeness_pct", 0)
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
        per_participant = (
            round(note_count / active_count, 1) if active_count else 0
        )
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

    NOTE: Not currently wired to any view (removed from Insights page —
    insufficient N at typical nonprofit scales). Retained for future use.

    Returns dict with:
        cohorts: list of {type, label, participants, goals_per,
                          sessions_per, achievement_pct}
        sufficient: bool
        observation: str
    """
    cohorts = []
    rates = {}

    for cohort_type, cohort_label in [
        ("new_intake", _("New Intakes")),
        ("re_enrolment", _("Re-enrolments")),
    ]:
        ep_qs = ServiceEpisode.objects.filter(
            program=program,
            episode_type=cohort_type,
            status__in=["active", "on_hold", "finished"],
        )
        if date_from:
            ep_qs = ep_qs.filter(enrolled_at__gte=date_from)

        client_ids = list(
            ep_qs.values_list("client_file_id", flat=True).distinct()
        )
        participant_count = len(client_ids)

        if participant_count < MIN_PER_CATEGORY_FOR_CROSSTAB:
            cohorts.append({
                "type": cohort_type,
                "label": str(cohort_label),
                "participants": participant_count,
                "sufficient": False,
            })
            continue

        # Goals per participant
        target_qs = PlanTarget.objects.filter(
            client_file_id__in=client_ids,
            plan_section__program=program,
            status__in=PlanTarget.ACTIVE_STATUSES,
        )
        goal_count = target_qs.count()
        goals_per = (
            round(goal_count / participant_count, 1)
            if participant_count
            else 0
        )

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
        sessions_per = (
            round(sessions / participant_count, 1)
            if participant_count
            else 0
        )

        # Achievement rate
        with_achievement = target_qs.filter(achievement_status__gt="")
        total_with = with_achievement.count()
        achieved = with_achievement.filter(
            achievement_status__in=PlanTarget.POSITIVE_ACHIEVEMENT_STATUSES
        ).count()
        ach_pct = (
            round(achieved / total_with * 100) if total_with >= 10 else None
        )
        rates[cohort_type] = ach_pct

        cohorts.append({
            "type": cohort_type,
            "label": str(cohort_label),
            "participants": participant_count,
            "goals_per": goals_per,
            "sessions_per": sessions_per,
            "achievement_pct": ach_pct,
            "sufficient": True,
        })

    sufficient = (
        all(c.get("sufficient", False) for c in cohorts)
        and len(cohorts) == 2
    )

    # Observation sentence
    observation = ""
    if (
        sufficient
        and rates.get("new_intake") is not None
        and rates.get("re_enrolment") is not None
    ):
        diff = rates["new_intake"] - rates["re_enrolment"]
        if diff >= 10:
            observation = _(
                "First-time participants are achieving at higher rates "
                "than those returning to the program."
            )
        elif diff <= -10:
            observation = _(
                "Returning participants are achieving at higher rates "
                "— the program may be more effective as a 'booster' "
                "intervention."
            )
        else:
            observation = _(
                "Achievement rates are similar for new and returning "
                "participants."
            )

    return {
        "cohorts": cohorts,
        "sufficient": sufficient,
        "observation": observation,
    }


def build_program_summary(program, enrolment_stats, period_label="quarter"):
    """Build structured summary sentence for a program (Feature D).

    NOTE: Dashboard uses _batch_fhir_enrichment (batched version) instead.
    This per-program version is retained for single-program contexts.

    Args:
        program: Program instance
        enrolment_stats: dict from _batch_enrolment_stats with total,
            active, etc.
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
        achievement_status__in=PlanTarget.POSITIVE_ACHIEVEMENT_STATUSES
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
    """Pre-computed stat cards with confidence levels (Feature F).

    NOTE: Removed from dashboard UI (duplicated metric rows). Retained
    for potential export/report contexts.

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
    total_served = (
        episodes.values("client_file_id").distinct().count()
    )
    new_count = (
        episodes.filter(episode_type="new_intake")
        .values("client_file_id").distinct().count()
    )
    returning_count = (
        episodes.filter(episode_type="re_enrolment")
        .values("client_file_id").distinct().count()
    )
    stats.append({
        "label": _("Served"),
        "value": _(
            "%(total)d participants (%(new)d new, %(returning)d returning)"
        ) % {
            "total": total_served,
            "new": new_count,
            "returning": returning_count,
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
            "value": _(
                "%(pct)d%% jointly developed with participants"
            ) % {"pct": pct},
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
            achievement_status__in=PlanTarget.POSITIVE_ACHIEVEMENT_STATUSES
        ).count()
        pct = round(positive / total_tracked * 100)
        coverage = (
            round(total_tracked / total_all * 100) if total_all else 0
        )
        conf = "reliable" if coverage >= 80 else "partial"
        stats.append({
            "label": _("Improving"),
            "value": _(
                "%(pct)d%% of tracked goals improving or achieved"
            ) % {"pct": pct},
            "confidence": conf,
            "note": _(
                "%(tracked)d of %(total)d have metric data"
            ) % {
                "tracked": total_tracked,
                "total": total_all,
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
        completed = finished.filter(
            end_reason__in=["completed", "goals_met"]
        ).count()
        pct = round(completed / total_finished * 100)
        coverage = round(with_reason / total_finished * 100)
        conf = "reliable" if coverage >= 80 else "partial"
        stats.append({
            "label": _("Completed"),
            "value": _(
                "%(pct)d%% completed program"
            ) % {"pct": pct},
            "confidence": conf,
            "note": _(
                "%(with_reason)d of %(total)d have discharge reason"
            ) % {
                "with_reason": with_reason,
                "total": total_finished,
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
