"""Executive dashboard -- aggregate, de-identified metrics for leadership.

Performance note: The per-program statistics section uses batch queries
(annotate + values) instead of per-program loops.  This reduces the query
count from ~12 * N (where N = number of programs) to a fixed ~10 queries
regardless of how many programs exist.
"""
import datetime
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _


# Minimum active participants before percentage metrics are shown.
# Below this threshold, percentages could identify individuals.
SMALL_PROGRAM_THRESHOLD = 5


# ---------------------------------------------------------------------------
# Metric helper functions (single-program versions, kept for unit tests)
# ---------------------------------------------------------------------------
def _count_without_notes(active_client_ids, program_ids, month_start):
    """Active clients with no ProgressNote created this month."""
    from apps.notes.models import ProgressNote

    if not active_client_ids:
        return 0
    clients_with_notes = set(
        ProgressNote.objects.filter(
            client_file_id__in=active_client_ids,
            author_program_id__in=program_ids,
            created_at__gte=month_start,
            status="default",
        ).values_list("client_file_id", flat=True)
    )
    return len(set(active_client_ids) - clients_with_notes)


def _count_overdue_followups(client_ids, today):
    """Notes with a follow-up date in the past that haven't been completed."""
    from apps.notes.models import ProgressNote

    if not client_ids:
        return 0
    return ProgressNote.objects.filter(
        client_file_id__in=client_ids,
        follow_up_date__lt=today,
        follow_up_completed_at__isnull=True,
        status="default",
    ).count()


def _count_active_alerts(client_ids):
    """Active safety alerts across the given clients."""
    from apps.events.models import Alert

    if not client_ids:
        return 0
    return Alert.objects.filter(
        client_file_id__in=client_ids,
        status="default",
    ).count()


def _get_alert_oversight_data(client_ids):
    """Enhanced safety alert metrics for the executive oversight card.

    Returns dict with:
        active: total active alerts
        aging: active alerts older than 14 days
        pending_cancellation: alerts with pending cancellation review
    """
    from apps.events.models import Alert, AlertCancellationRecommendation

    if not client_ids:
        return {"active": 0, "aging": 0, "pending_cancellation": 0}

    active_qs = Alert.objects.filter(
        client_file_id__in=client_ids,
        status="default",
    )
    active_count = active_qs.count()

    cutoff = timezone.now() - timedelta(days=14)
    aging_count = active_qs.filter(created_at__lt=cutoff).count()

    pending_count = AlertCancellationRecommendation.objects.filter(
        alert__client_file_id__in=client_ids,
        alert__status="default",
        status="pending",
    ).count()

    return {
        "active": active_count,
        "aging": aging_count,
        "pending_cancellation": pending_count,
    }


def _batch_alerts_by_program(filtered_program_ids, base_client_ids):
    """Alert counts grouped by program for the oversight breakdown page.

    Returns dict of program_id -> {active, aging, pending_cancellation}.
    """
    from apps.clients.models import ClientProgramEnrolment
    from apps.events.models import Alert, AlertCancellationRecommendation

    enrolments = ClientProgramEnrolment.objects.filter(
        program_id__in=filtered_program_ids,
        status="enrolled",
        client_file_id__in=base_client_ids,
    ).values_list("program_id", "client_file_id")

    program_client_map = {}
    for pid, cid in enrolments:
        program_client_map.setdefault(pid, set()).add(cid)

    cutoff = timezone.now() - timedelta(days=14)
    result = {}

    for pid in filtered_program_ids:
        cids = program_client_map.get(pid, set())
        if not cids:
            result[pid] = {"active": 0, "aging": 0, "pending_cancellation": 0}
            continue

        active_qs = Alert.objects.filter(
            client_file_id__in=cids, status="default",
        )
        result[pid] = {
            "active": active_qs.count(),
            "aging": active_qs.filter(created_at__lt=cutoff).count(),
            "pending_cancellation": AlertCancellationRecommendation.objects.filter(
                alert__client_file_id__in=cids,
                alert__status="default",
                status="pending",
            ).count(),
        }

    return result


def _calc_no_show_rate(program, month_start):
    """No-show meetings as % of completed + no-show this month."""
    from apps.events.models import Meeting

    meetings = Meeting.objects.filter(
        event__author_program=program,
        event__start_timestamp__gte=month_start,
        status__in=["completed", "no_show"],
    )
    total = meetings.count()
    if total == 0:
        return None
    no_shows = meetings.filter(status="no_show").count()
    return round(no_shows / total * 100)


def _calc_engagement_quality(program, month_start):
    """% of notes with positive engagement observations this month."""
    from apps.notes.models import ProgressNote

    notes_with_obs = ProgressNote.objects.filter(
        author_program=program,
        created_at__gte=month_start,
        status="default",
    ).exclude(
        engagement_observation__in=["", "no_interaction"]
    )
    total = notes_with_obs.count()
    if total == 0:
        return None
    positive = notes_with_obs.filter(
        engagement_observation__in=["engaged", "valuing"]
    ).count()
    return round(positive / total * 100)


def _calc_goal_completion(program):
    """% of active + completed targets that are completed."""
    from apps.plans.models import PlanTarget

    targets = PlanTarget.objects.filter(
        plan_section__program=program,
        status__in=["default", "completed"],
    )
    total = targets.count()
    if total == 0:
        return None
    completed = targets.filter(status="completed").count()
    return round(completed / total * 100)


def _count_intake_pending(program):
    """Pending registration submissions for this program."""
    from apps.registration.models import RegistrationSubmission

    return RegistrationSubmission.objects.filter(
        registration_link__program=program,
        status="pending",
    ).count()


def _calc_group_attendance(program, month_start):
    """% present of total attendance records this month."""
    from apps.groups.models import GroupSessionAttendance

    attendance = GroupSessionAttendance.objects.filter(
        group_session__group__program=program,
        group_session__session_date__gte=month_start.date(),
    )
    total = attendance.count()
    if total == 0:
        return None
    present = attendance.filter(present=True).count()
    return round(present / total * 100)


def _calc_portal_adoption(active_client_ids):
    """% of active clients with a portal account."""
    from apps.portal.models import ParticipantUser

    total = len(active_client_ids)
    if total == 0:
        return None
    with_portal = ParticipantUser.objects.filter(
        client_file_id__in=active_client_ids,
        is_active=True,
    ).count()
    return round(with_portal / total * 100)


# ---------------------------------------------------------------------------
# Batch metric helpers (all programs in one query each)
# ---------------------------------------------------------------------------

def _batch_enrolment_stats(filtered_program_ids, base_client_ids, month_start):
    """Return per-program client counts in a single pass.

    Returns dict of program_id -> {total, active, new_this_month, active_ids,
    enrolled_ids}.
    """
    from apps.clients.models import ClientProgramEnrolment

    # One query: all enrolments for filtered programs, joined to client status
    enrolments = (
        ClientProgramEnrolment.objects.filter(
            program_id__in=filtered_program_ids,
            status="enrolled",
            client_file_id__in=base_client_ids,
        )
        .values_list(
            "program_id",
            "client_file_id",
            "client_file__status",
            "client_file__created_at",
        )
    )

    stats = {}
    for pid in filtered_program_ids:
        stats[pid] = {
            "total": 0,
            "active": 0,
            "new_this_month": 0,
            "active_ids": set(),
            "enrolled_ids": set(),
        }

    for prog_id, client_id, client_status, created_at in enrolments:
        s = stats.get(prog_id)
        if s is None:
            continue
        s["total"] += 1
        s["enrolled_ids"].add(client_id)
        if client_status == "active":
            s["active"] += 1
            s["active_ids"].add(client_id)
        if created_at and created_at >= month_start:
            s["new_this_month"] += 1

    return stats


def _batch_notes_this_week(filtered_program_ids, week_start):
    """Count notes created this week, grouped by author_program_id."""
    from apps.notes.models import ProgressNote

    rows = (
        ProgressNote.objects.filter(
            author_program_id__in=filtered_program_ids,
            created_at__gte=week_start,
            status="default",
        )
        .values("author_program_id")
        .annotate(cnt=Count("id"))
    )
    return {r["author_program_id"]: r["cnt"] for r in rows}


def _batch_engagement_quality(filtered_program_ids, month_start):
    """Engagement quality % per program in one query.

    Returns dict of program_id -> int (percentage) or None.
    """
    from apps.notes.models import ProgressNote

    rows = (
        ProgressNote.objects.filter(
            author_program_id__in=filtered_program_ids,
            created_at__gte=month_start,
            status="default",
        )
        .exclude(engagement_observation__in=["", "no_interaction"])
        .values("author_program_id")
        .annotate(
            total=Count("id"),
            positive=Count(
                "id",
                filter=Q(engagement_observation__in=["engaged", "valuing"]),
            ),
        )
    )
    result = {}
    for r in rows:
        total = r["total"]
        if total == 0:
            result[r["author_program_id"]] = None
        else:
            result[r["author_program_id"]] = round(r["positive"] / total * 100)
    return result


def _batch_goal_completion(filtered_program_ids):
    """Goal completion % per program in one query.

    Returns dict of program_id -> int (percentage) or None.
    """
    from apps.plans.models import PlanTarget

    rows = (
        PlanTarget.objects.filter(
            plan_section__program_id__in=filtered_program_ids,
            status__in=["default", "completed"],
        )
        .values("plan_section__program_id")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
        )
    )
    result = {}
    for r in rows:
        pid = r["plan_section__program_id"]
        total = r["total"]
        if total == 0:
            result[pid] = None
        else:
            result[pid] = round(r["completed"] / total * 100)
    return result


def _batch_intake_pending(filtered_program_ids):
    """Pending intake count per program in one query."""
    from apps.registration.models import RegistrationSubmission

    rows = (
        RegistrationSubmission.objects.filter(
            registration_link__program_id__in=filtered_program_ids,
            status="pending",
        )
        .values("registration_link__program_id")
        .annotate(cnt=Count("id"))
    )
    return {r["registration_link__program_id"]: r["cnt"] for r in rows}


def _batch_no_show_rate(filtered_program_ids, month_start):
    """No-show rate per program in one query.

    Returns dict of program_id -> int (percentage) or None.
    """
    from apps.events.models import Meeting

    rows = (
        Meeting.objects.filter(
            event__author_program_id__in=filtered_program_ids,
            event__start_timestamp__gte=month_start,
            status__in=["completed", "no_show"],
        )
        .values("event__author_program_id")
        .annotate(
            total=Count("id"),
            no_shows=Count("id", filter=Q(status="no_show")),
        )
    )
    result = {}
    for r in rows:
        pid = r["event__author_program_id"]
        total = r["total"]
        if total == 0:
            result[pid] = None
        else:
            result[pid] = round(r["no_shows"] / total * 100)
    return result


def _batch_group_attendance(filtered_program_ids, month_start):
    """Group attendance % per program in one query.

    Returns a tuple of (attendance_map, programs_with_groups) where
    attendance_map is dict of program_id -> int (percentage) or None,
    and programs_with_groups is a set of program IDs that have active groups.
    """
    from apps.groups.models import Group, GroupSessionAttendance

    # Which programs have active groups? (one query)
    programs_with_groups = set(
        Group.objects.filter(
            program_id__in=filtered_program_ids,
            status="active",
        ).values_list("program_id", flat=True)
    )

    if not programs_with_groups:
        return {}, programs_with_groups

    rows = (
        GroupSessionAttendance.objects.filter(
            group_session__group__program_id__in=programs_with_groups,
            group_session__session_date__gte=month_start.date(),
        )
        .values("group_session__group__program_id")
        .annotate(
            total=Count("id"),
            present=Count("id", filter=Q(present=True)),
        )
    )
    result = {}
    for r in rows:
        pid = r["group_session__group__program_id"]
        total = r["total"]
        if total == 0:
            result[pid] = None
        else:
            result[pid] = round(r["present"] / total * 100)
    return result, programs_with_groups


def _batch_portal_adoption(enrolment_stats):
    """Portal adoption % per program in one query.

    Takes the enrolment_stats dict (from _batch_enrolment_stats) and returns
    dict of program_id -> int (percentage) or None.
    """
    from apps.portal.models import ParticipantUser

    # Collect all active client IDs across all programs
    all_active_ids = set()
    for s in enrolment_stats.values():
        all_active_ids.update(s["active_ids"])

    if not all_active_ids:
        return {}

    # One query: which active clients have portal accounts?
    clients_with_portal = set(
        ParticipantUser.objects.filter(
            client_file_id__in=all_active_ids,
            is_active=True,
        ).values_list("client_file_id", flat=True)
    )

    result = {}
    for pid, s in enrolment_stats.items():
        active_ids = s["active_ids"]
        if not active_ids:
            result[pid] = None
        else:
            with_portal = len(active_ids & clients_with_portal)
            result[pid] = round(with_portal / len(active_ids) * 100)
    return result


def _batch_top_themes(filtered_program_ids, limit_per_program=3):
    """Active themes per program: both counts and top theme details in one query.

    Returns (counts_map, themes_map) where:
        counts_map: dict of program_id -> {total, open, in_progress}
        themes_map: dict of program_id -> list of up to *limit_per_program*
                    theme dicts with keys: pk, name, status, priority
    """
    from apps.notes.models import SuggestionTheme, deduplicate_themes

    PRIORITY_RANK = {"urgent": 0, "important": 1, "noted": 2}

    themes = list(
        SuggestionTheme.objects.active()
        .filter(program_id__in=filtered_program_ids)
        .annotate(link_count=Count("links"))
        .values("pk", "name", "status", "priority", "program_id", "updated_at",
                "link_count")
    )

    # Merge any duplicate theme names within the same program
    themes = deduplicate_themes(themes)

    # Sort: highest priority first, then most recently updated
    themes.sort(
        key=lambda t: (
            PRIORITY_RANK.get(t["priority"], 9),
            -t["updated_at"].timestamp(),
        )
    )

    # Build both counts and top-N lists in one pass
    counts_map = {}
    themes_map = {}
    for t in themes:
        pid = t["program_id"]

        # Counts
        if pid not in counts_map:
            counts_map[pid] = {"total": 0, "open": 0, "in_progress": 0}
        counts_map[pid]["total"] += 1
        if t["status"] == "open":
            counts_map[pid]["open"] += 1
        elif t["status"] == "in_progress":
            counts_map[pid]["in_progress"] += 1

        # Top themes (capped at limit)
        if pid not in themes_map:
            themes_map[pid] = []
        if len(themes_map[pid]) < limit_per_program:
            themes_map[pid].append(t)

    return counts_map, themes_map


def _batch_program_learning(programs, date_from, date_to):
    """Compute program learning data for executive dashboard cards.

    For each program, computes:
        - Lead outcome headline (achievement rate or scale "goals within reach" %)
        - Trend direction (improving / stable / declining)
        - Target rate (if set)
        - Data completeness (level + counts)
        - Open feedback theme count with urgency flag

    Returns dict of program_id -> {
        headline_label, headline_pct, headline_type,
        target_rate, trend_direction, trend_label,
        completeness_level, completeness_enrolled, completeness_with_data,
        theme_open_count, has_urgent_theme, suppress,
    }
    """
    from apps.reports.metric_insights import (
        get_achievement_rates,
        get_data_completeness,
        get_metric_distributions,
    )
    from apps.reports.insights import get_structured_insights
    from apps.reports.insights_views import _compute_trend_direction
    from apps.notes.models import SuggestionTheme, deduplicate_themes

    result = {}

    for program in programs:
        pid = program.pk

        # Achievement rates (Layer 2)
        achievement = get_achievement_rates(program, date_from, date_to)
        # Scale distributions (Layer 1)
        distributions = get_metric_distributions(program, date_from, date_to)
        # Data completeness
        completeness = get_data_completeness(program, date_from, date_to)
        # Structured insights for trend direction
        structured = get_structured_insights(
            program=program, date_from=date_from, date_to=date_to,
        )
        trend_direction = _compute_trend_direction(structured.get("descriptor_trend", []))

        # Determine lead headline
        headline_label = None
        headline_pct = None
        headline_type = None  # "achievement" or "scale"
        target_rate = None

        # Prefer achievement rate (Layer 2) if available
        if achievement:
            lead = next(iter(achievement.values()))
            headline_label = lead["name"]
            headline_pct = lead["achieved_pct"]
            headline_type = "achievement"
            target_rate = lead.get("target_rate")
        elif distributions:
            # Fallback to scale metric "goals within reach" %
            # Prefer universal metric, else first available
            lead_dist = None
            for mid, dist in distributions.items():
                if dist.get("is_universal"):
                    lead_dist = dist
                    break
            if not lead_dist:
                lead_dist = next(iter(distributions.values()))
            headline_label = lead_dist["name"]
            headline_pct = lead_dist["band_high_pct"]
            headline_type = "scale"
            target_rate = lead_dist.get("target_band_high_pct")

        # Suppress if total participants with data < 5 (privacy threshold)
        suppress = False
        if completeness["with_scores_count"] < SMALL_PROGRAM_THRESHOLD:
            suppress = True
            headline_pct = None

        # Open feedback themes
        active_themes = list(
            SuggestionTheme.objects.active()
            .filter(program=program)
            .values("pk", "name", "status", "priority", "program_id",
                    "updated_at")
        )
        active_themes = deduplicate_themes(active_themes)
        theme_open_count = len(active_themes)
        has_urgent_theme = any(t.get("priority") == "urgent" for t in active_themes)

        # Trend label for display
        if trend_direction == _("improving"):
            trend_label = "\u2191"  # ↑
        elif trend_direction == _("declining"):
            trend_label = "\u2193"  # ↓
        elif trend_direction == _("stable"):
            trend_label = "\u2192"  # →
        else:
            trend_label = ""

        result[pid] = {
            "headline_label": headline_label,
            "headline_pct": headline_pct,
            "headline_type": headline_type,
            "target_rate": target_rate,
            "trend_direction": trend_direction,
            "trend_label": trend_label,
            "completeness_level": completeness["completeness_level"],
            "completeness_enrolled": completeness["enrolled_count"],
            "completeness_with_data": completeness["with_scores_count"],
            "theme_open_count": theme_open_count,
            "has_urgent_theme": has_urgent_theme,
            "suppress": suppress,
        }

    return result


def _batch_suggestion_counts(filtered_program_ids):
    """Suggestion counts per program, grouped by priority, in one query.

    Returns dict of program_id -> {total, important, urgent}.
    """
    from apps.notes.models import ProgressNote

    rows = (
        ProgressNote.objects.filter(
            author_program_id__in=filtered_program_ids,
            status="default",
        )
        .exclude(suggestion_priority="")
        .values("author_program_id", "suggestion_priority")
        .annotate(count=Count("id"))
    )

    result = {}
    for r in rows:
        pid = r["author_program_id"]
        if pid not in result:
            result[pid] = {"total": 0, "important": 0, "urgent": 0}
        result[pid]["total"] += r["count"]
        if r["suggestion_priority"] == "important":
            result[pid]["important"] = r["count"]
        elif r["suggestion_priority"] == "urgent":
            result[pid]["urgent"] = r["count"]

    return result


# ---------------------------------------------------------------------------
# Feature flags (reuse cached context processor pattern)
# ---------------------------------------------------------------------------

def _parse_date_range(request, now):
    """Parse start_date query param into an aware datetime for filtering.

    Returns (month_start, custom_start_date) where month_start is an aware
    datetime and custom_start_date is a date object for template display.
    """
    start_date_str = request.GET.get("start_date", "")
    try:
        custom_start = datetime.date.fromisoformat(start_date_str) if start_date_str else None
    except ValueError:
        custom_start = None

    default_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if custom_start:
        month_start = timezone.make_aware(
            datetime.datetime.combine(custom_start, datetime.time.min)
        )
    else:
        month_start = default_month_start
        custom_start = month_start.date()

    return month_start, custom_start


def _get_feature_flags():
    """Return feature flags dict, using cache if available."""
    flags = cache.get("feature_toggles")
    if flags is None:
        from apps.admin_settings.models import FeatureToggle
        from apps.admin_settings.views import DEFAULT_FEATURES, FEATURES_DEFAULT_ENABLED

        db_flags = FeatureToggle.get_all_flags()
        flags = {key: key in FEATURES_DEFAULT_ENABLED for key in DEFAULT_FEATURES}
        flags.update(db_flags)
        cache.set("feature_toggles", flags, 300)
    return flags



# ---------------------------------------------------------------------------
# Inline data helpers (for role-based home dashboard)
# ---------------------------------------------------------------------------

def _get_pm_summary_data(user, program_ids, base_client_ids):
    """Fetch PM program health metrics for inline display on home page.

    Returns a list of per-program dicts with: program, active count,
    notes this week, overdue follow-ups, and clients without recent notes.
    """
    from apps.notes.models import ProgressNote
    from apps.programs.models import Program

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    today = now.date()

    programs = Program.objects.filter(pk__in=program_ids, status="active")
    filtered_program_ids = list(programs.values_list("pk", flat=True))

    if not filtered_program_ids:
        return []

    enrolment_stats = _batch_enrolment_stats(
        filtered_program_ids, base_client_ids, month_start,
    )
    notes_week_map = _batch_notes_this_week(filtered_program_ids, week_start)

    # Overdue follow-ups per program (batch)
    overdue_rows = (
        ProgressNote.objects.filter(
            author_program_id__in=filtered_program_ids,
            follow_up_date__lt=today,
            follow_up_completed_at__isnull=True,
            status="default",
        )
        .values("author_program_id")
        .annotate(cnt=Count("id"))
    )
    overdue_map = {r["author_program_id"]: r["cnt"] for r in overdue_rows}

    # Clients without notes this month per program (batch)
    thirty_days_ago = now - timedelta(days=30)
    clients_with_recent = set(
        ProgressNote.objects.filter(
            author_program_id__in=filtered_program_ids,
            created_at__gte=thirty_days_ago,
            status="default",
        ).values_list("client_file_id", flat=True)
    )

    program_stats = []
    for program in programs:
        pid = program.pk
        es = enrolment_stats.get(pid, {})
        active_ids = es.get("active_ids", set())
        without_recent = len(active_ids - clients_with_recent)

        program_stats.append({
            "program": program,
            "active": es.get("active", 0),
            "total": es.get("total", 0),
            "notes_this_week": notes_week_map.get(pid, 0),
            "overdue_followups": overdue_map.get(pid, 0),
            "without_recent_notes": without_recent,
        })

    return program_stats


def _get_executive_inline_data(user, program_ids, base_client_ids):
    """Fetch executive summary metrics for inline display on home page.

    Returns a dict with top-line cards, per-program stats, and feature flags.
    Reuses the same batch queries as executive_dashboard().
    """
    from apps.clients.models import ClientProgramEnrolment
    from apps.programs.models import Program

    flags = _get_feature_flags()

    now = timezone.now()
    today = now.date()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())

    programs = Program.objects.filter(pk__in=program_ids, status="active")
    filtered_program_ids = list(programs.values_list("pk", flat=True))

    if not filtered_program_ids:
        return {
            "total_active": 0,
            "program_stats": [],
            "flags": flags,
            "without_notes": 0,
            "overdue_followups": 0,
            "active_alerts": None,
            "show_alerts": flags.get("alerts", False),
            "show_events": flags.get("events", False),
            "show_portal": flags.get("portal_journal", False) or flags.get("portal_messaging", False),
            "total_suggestions_important": 0,
        }

    # Collect all enrolled/active client IDs
    from apps.clients.models import ClientFile
    all_enrolled_ids = set(
        ClientProgramEnrolment.objects.filter(
            program_id__in=filtered_program_ids, status="enrolled",
            client_file_id__in=base_client_ids,
        ).values_list("client_file_id", flat=True)
    )
    all_active_ids = set(
        ClientFile.objects.filter(
            pk__in=all_enrolled_ids, status="active",
        ).values_list("pk", flat=True)
    )
    all_client_ids = set(
        ClientFile.objects.filter(
            pk__in=all_enrolled_ids,
        ).values_list("pk", flat=True)
    )

    # Top-line cards
    total_active = len(all_active_ids)
    without_notes = _count_without_notes(all_active_ids, filtered_program_ids, month_start)
    overdue_followups = _count_overdue_followups(all_client_ids, today)

    show_alerts = flags.get("alerts", False)
    active_alerts = _count_active_alerts(all_client_ids) if show_alerts else None
    alert_oversight = (
        _get_alert_oversight_data(all_client_ids) if show_alerts else None
    )

    show_events = flags.get("events", False)
    show_portal = flags.get("portal_journal", False) or flags.get("portal_messaging", False)

    # Batch per-program metrics
    enrolment_stats = _batch_enrolment_stats(filtered_program_ids, base_client_ids, month_start)
    notes_week_map = _batch_notes_this_week(filtered_program_ids, week_start)
    engagement_map = _batch_engagement_quality(filtered_program_ids, month_start)
    goal_map = _batch_goal_completion(filtered_program_ids)
    intake_map = _batch_intake_pending(filtered_program_ids)
    suggestion_map = _batch_suggestion_counts(filtered_program_ids)

    program_stats = []
    for program in programs:
        pid = program.pk
        es = enrolment_stats.get(pid, {})
        stat = {
            "program": program,
            "total": es.get("total", 0),
            "active": es.get("active", 0),
            "new_this_month": es.get("new_this_month", 0),
            "notes_this_week": notes_week_map.get(pid, 0),
            "engagement_quality": engagement_map.get(pid),
            "goal_completion": goal_map.get(pid),
            "intake_pending": intake_map.get(pid, 0),
        }
        sugg = suggestion_map.get(pid, {})
        stat["suggestion_total"] = sugg.get("total", 0)
        stat["suggestion_important"] = sugg.get("important", 0) + sugg.get("urgent", 0)
        program_stats.append(stat)

    total_suggestions_important = sum(
        s.get("important", 0) + s.get("urgent", 0)
        for s in suggestion_map.values()
    )

    return {
        "total_active": total_active,
        "program_stats": program_stats,
        "flags": flags,
        "without_notes": without_notes,
        "overdue_followups": overdue_followups,
        "active_alerts": active_alerts,
        "alert_oversight": alert_oversight,
        "show_alerts": show_alerts,
        "show_events": show_events,
        "show_portal": show_portal,
        "total_suggestions_important": total_suggestions_important,
    }


# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------

@login_required
def executive_dashboard(request):
    """
    Executive dashboard with aggregate statistics only.

    Executives see high-level program metrics without access to individual
    client records. This protects client confidentiality while giving
    leadership the oversight they need.

    Optimised: uses batch queries (annotate/values grouped by program_id)
    instead of per-program loops. Total query count is fixed (~10) regardless
    of the number of programs.
    """
    from apps.clients.models import ClientProgramEnrolment
    from apps.programs.models import Program, UserProgramRole

    from .views import get_client_queryset

    # Feature flags
    flags = _get_feature_flags()

    # Programs the user is assigned to
    user_program_ids = list(
        UserProgramRole.objects.filter(
            user=request.user, status="active"
        ).values_list("program_id", flat=True)
    )
    programs = Program.objects.filter(pk__in=user_program_ids, status="active")

    # Only users assigned to at least one programme may view this page
    if not user_program_ids:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(
            "Access restricted to staff assigned to at least one programme."
        )

    # Program filter
    selected_program_id = request.GET.get("program")
    if selected_program_id:
        try:
            selected_program_id = int(selected_program_id)
            if selected_program_id not in user_program_ids:
                selected_program_id = None
        except (ValueError, TypeError):
            selected_program_id = None

    if selected_program_id:
        filtered_programs = programs.filter(pk=selected_program_id)
    else:
        filtered_programs = programs

    # Base client queryset (respects demo/real separation)
    base_clients = get_client_queryset(request.user)

    # Time boundaries — support custom start date via query param (BUG-9/10)
    now = timezone.now()
    today = now.date()

    month_start, custom_start = _parse_date_range(request, now)

    week_start = now - timedelta(days=now.weekday())

    # Collect all active client IDs across filtered programs (for top-line cards)
    all_enrolled_ids = set(
        ClientProgramEnrolment.objects.filter(
            program__in=filtered_programs, status="enrolled"
        ).values_list("client_file_id", flat=True)
    )
    all_active_ids = set(
        base_clients.filter(
            pk__in=all_enrolled_ids, status="active"
        ).values_list("pk", flat=True)
    )
    all_client_ids = set(
        base_clients.filter(
            pk__in=all_enrolled_ids
        ).values_list("pk", flat=True)
    )
    filtered_program_ids = list(filtered_programs.values_list("pk", flat=True))

    # -- Top-line summary cards ------------------------------------------
    total_active = len(all_active_ids)
    without_notes = _count_without_notes(all_active_ids, filtered_program_ids, month_start)
    overdue_followups = _count_overdue_followups(all_client_ids, today)

    show_alerts = flags.get("alerts", False)
    active_alerts = _count_active_alerts(all_client_ids) if show_alerts else None
    alert_oversight = (
        _get_alert_oversight_data(all_client_ids) if show_alerts else None
    )

    # -- Per-program cards (batch queries) -------------------------------
    show_events = flags.get("events", False)
    show_portal = flags.get("portal_journal", False) or flags.get("portal_messaging", False)

    # All base_client IDs (for filtering enrolments to accessible clients)
    base_client_ids = set(base_clients.values_list("pk", flat=True))

    # Batch: enrolment stats (total, active, new_this_month per program)
    enrolment_stats = _batch_enrolment_stats(
        filtered_program_ids, base_client_ids, month_start,
    )

    # Batch: notes this week per program
    notes_week_map = _batch_notes_this_week(filtered_program_ids, week_start)

    # Batch: engagement quality per program
    engagement_map = _batch_engagement_quality(filtered_program_ids, month_start)

    # Batch: goal completion per program
    goal_map = _batch_goal_completion(filtered_program_ids)

    # Batch: intake pending per program
    intake_map = _batch_intake_pending(filtered_program_ids)

    # Batch: no-show rate per program (conditional)
    no_show_map = (
        _batch_no_show_rate(filtered_program_ids, month_start)
        if show_events else {}
    )

    # Batch: group attendance per program
    group_att_map, programs_with_groups = _batch_group_attendance(
        filtered_program_ids, month_start,
    )

    # Batch: portal adoption per program (conditional)
    portal_map = (
        _batch_portal_adoption(enrolment_stats)
        if show_portal else {}
    )

    # Batch: suggestion counts per program
    suggestion_map = _batch_suggestion_counts(filtered_program_ids)

    # Batch: active theme counts + top theme details per program
    theme_map, top_themes_map = _batch_top_themes(filtered_program_ids)

    # Batch: program learning data (outcome headlines, trend, completeness)
    # Use the dashboard date range (month_start to today) for consistency
    learning_date_from = month_start.date()
    learning_date_to = today
    learning_map = _batch_program_learning(
        filtered_programs, learning_date_from, learning_date_to,
    )

    # Assemble per-program stat dicts
    program_stats = []
    total_clients = 0

    for program in filtered_programs:
        pid = program.pk
        es = enrolment_stats.get(pid, {})

        active_count = es.get("active", 0)
        # Suppress percentage metrics for small programs to prevent
        # statistical disclosure (identifying individuals from aggregates).
        suppress_pct = active_count < SMALL_PROGRAM_THRESHOLD

        stat = {
            "program": program,
            "total": es.get("total", 0),
            "active": active_count,
            "new_this_month": es.get("new_this_month", 0),
            "notes_this_week": notes_week_map.get(pid, 0),
            "engagement_quality": None if suppress_pct else engagement_map.get(pid),
            "goal_completion": None if suppress_pct else goal_map.get(pid),
            "intake_pending": intake_map.get(pid, 0),
            "suppress_pct": suppress_pct,
        }

        if show_events:
            stat["no_show_rate"] = None if suppress_pct else no_show_map.get(pid)

        if pid in programs_with_groups:
            stat["group_attendance"] = None if suppress_pct else group_att_map.get(pid)

        if show_portal:
            stat["portal_adoption"] = None if suppress_pct else portal_map.get(pid)

        sugg = suggestion_map.get(pid, {})
        stat["suggestion_total"] = sugg.get("total", 0)
        stat["suggestion_important"] = sugg.get("important", 0) + sugg.get("urgent", 0)

        themes = theme_map.get(pid, {})
        stat["theme_total"] = themes.get("total", 0)
        stat["theme_open"] = themes.get("open", 0)
        stat["theme_in_progress"] = themes.get("in_progress", 0)
        top = top_themes_map.get(pid, [])
        stat["top_themes"] = top
        stat["theme_overflow"] = max(0, themes.get("total", 0) - len(top))

        # Program learning data (outcome headline, trend, completeness)
        learning = learning_map.get(pid, {})
        stat["learning"] = learning

        program_stats.append(stat)
        total_clients += es.get("total", 0)

    total_suggestions_important = sum(
        s.get("important", 0) + s.get("urgent", 0)
        for s in suggestion_map.values()
    )

    return render(request, "clients/executive_dashboard.html", {
        "programs": programs,
        "program_stats": program_stats,
        "total_clients": total_clients,
        "total_active": total_active,
        "without_notes": without_notes,
        "overdue_followups": overdue_followups,
        "active_alerts": active_alerts,
        "alert_oversight": alert_oversight,
        "show_alerts": show_alerts,
        "show_events": show_events,
        "show_portal": show_portal,
        "total_suggestions_important": total_suggestions_important,
        "selected_program_id": selected_program_id,
        "start_date": custom_start,
        "data_refreshed_at": now,
        "nav_active": "executive",
    })


@login_required
def executive_dashboard_export(request):
    """Export executive dashboard program stats as CSV (BUG-9/10)."""
    import csv
    from django.http import HttpResponse, HttpResponseForbidden
    from apps.programs.models import Program, UserProgramRole
    from .views import get_client_queryset

    # Role gate: only executives, PMs, and admins may export
    from apps.auth_app.decorators import _get_user_highest_role_any
    user_role = getattr(request, "user_program_role", None) or _get_user_highest_role_any(request.user)
    is_admin = getattr(request.user, "is_admin", False)
    if user_role not in ("executive", "program_manager") and not is_admin:
        return HttpResponseForbidden("Access restricted to management roles.")

    user_program_ids = list(
        UserProgramRole.objects.filter(
            user=request.user, status="active"
        ).values_list("program_id", flat=True)
    )
    if not user_program_ids:
        return HttpResponseForbidden("No programs assigned.")

    programs = Program.objects.filter(pk__in=user_program_ids, status="active")

    selected_program_id = request.GET.get("program")
    if selected_program_id:
        try:
            selected_program_id = int(selected_program_id)
            if selected_program_id not in user_program_ids:
                selected_program_id = None
        except (ValueError, TypeError):
            selected_program_id = None

    filtered_programs = programs.filter(pk=selected_program_id) if selected_program_id else programs

    now = timezone.now()
    month_start, _ = _parse_date_range(request, now)
    week_start = now - timedelta(days=now.weekday())

    base_clients = get_client_queryset(request.user)
    base_client_ids = set(base_clients.values_list("pk", flat=True))
    filtered_program_ids = list(filtered_programs.values_list("pk", flat=True))

    enrolment_stats = _batch_enrolment_stats(filtered_program_ids, base_client_ids, month_start)
    notes_week_map = _batch_notes_this_week(filtered_program_ids, week_start)
    engagement_map = _batch_engagement_quality(filtered_program_ids, month_start)
    goal_map = _batch_goal_completion(filtered_program_ids)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="executive-dashboard.csv"'
    writer = csv.writer(response)
    writer.writerow(["Program", "Total Enrolled", "Active", "New This Period", "Notes This Week", "Engagement %", "Goal Completion %"])

    for program in filtered_programs:
        pid = program.pk
        es = enrolment_stats.get(pid, {})
        active_count = es.get("active", 0)
        suppress_pct = active_count < SMALL_PROGRAM_THRESHOLD
        eng = None if suppress_pct else engagement_map.get(pid)
        goal = None if suppress_pct else goal_map.get(pid)
        writer.writerow([
            program.translated_name,
            es.get("total", 0),
            active_count,
            es.get("new_this_month", 0),
            notes_week_map.get(pid, 0),
            f"{eng}%" if eng is not None else ("suppressed" if suppress_pct else ""),
            f"{goal}%" if goal is not None else ("suppressed" if suppress_pct else ""),
        ])

    # Audit log entry for export
    from apps.audit.models import AuditLog
    AuditLog.objects.using("audit").create(
        event_timestamp=now,
        user_id=request.user.pk,
        user_display=getattr(request.user, "display_name", str(request.user)),
        action="export",
        resource_type="executive_dashboard",
        resource_id=0,
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "format": "csv",
            "programs": filtered_program_ids,
            "start_date": str(month_start.date()),
        },
    )

    return response


# ---------------------------------------------------------------------------
# Alert overview by program
# ---------------------------------------------------------------------------

@login_required
def alert_overview_by_program(request):
    """Safety alert breakdown by program for executive oversight."""
    from apps.clients.views import get_client_queryset
    from apps.programs.models import Program, UserProgramRole

    user_program_ids = list(
        UserProgramRole.objects.filter(
            user=request.user, status="active",
        ).values_list("program_id", flat=True)
    )
    if not user_program_ids:
        return render(request, "403.html", status=403)

    programs = Program.objects.filter(pk__in=user_program_ids).order_by("name")
    base_client_ids = set(
        get_client_queryset(request.user).values_list("pk", flat=True)
    )
    filtered_program_ids = list(programs.values_list("pk", flat=True))

    alert_map = _batch_alerts_by_program(filtered_program_ids, base_client_ids)

    program_alerts = []
    for program in programs:
        data = alert_map.get(program.pk, {})
        program_alerts.append({
            "program": program,
            "active": data.get("active", 0),
            "aging": data.get("aging", 0),
            "pending_cancellation": data.get("pending_cancellation", 0),
        })

    return render(request, "clients/alert_overview.html", {
        "program_alerts": program_alerts,
        "nav_active": "executive",
    })
