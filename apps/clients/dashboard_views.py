"""Executive dashboard — aggregate, de-identified metrics for leadership."""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render
from django.utils import timezone


# ---------------------------------------------------------------------------
# Metric helper functions
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
# Feature flags (reuse cached context processor pattern)
# ---------------------------------------------------------------------------

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
# Main view
# ---------------------------------------------------------------------------

@login_required
def executive_dashboard(request):
    """
    Executive dashboard with aggregate statistics only.

    Executives see high-level program metrics without access to individual
    client records. This protects client confidentiality while giving
    leadership the oversight they need.
    """
    from apps.clients.models import ClientFile, ClientProgramEnrolment
    from apps.groups.models import Group
    from apps.notes.models import ProgressNote
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

    # Time boundaries
    now = timezone.now()
    today = now.date()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
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

    # ── Top-line summary cards ──────────────────────────────────────────
    total_active = len(all_active_ids)
    without_notes = _count_without_notes(all_active_ids, filtered_program_ids, month_start)
    overdue_followups = _count_overdue_followups(all_client_ids, today)

    show_alerts = flags.get("alerts", False)
    active_alerts = _count_active_alerts(all_client_ids) if show_alerts else None

    # ── Per-program cards ───────────────────────────────────────────────
    program_stats = []
    total_clients = 0

    show_events = flags.get("events", False)
    show_portal = flags.get("portal_journal", False) or flags.get("portal_messaging", False)

    for program in filtered_programs:
        # Clients enrolled in this program
        enrolled_client_ids = set(
            ClientProgramEnrolment.objects.filter(
                program=program, status="enrolled"
            ).values_list("client_file_id", flat=True)
        )
        program_clients = base_clients.filter(pk__in=enrolled_client_ids)

        active = program_clients.filter(status="active").count()
        total = program_clients.count()
        active_ids = set(
            program_clients.filter(status="active").values_list("pk", flat=True)
        )

        new_this_month = program_clients.filter(created_at__gte=month_start).count()

        notes_this_week = ProgressNote.objects.filter(
            client_file_id__in=enrolled_client_ids,
            created_at__gte=week_start,
            status="default",
        ).count()

        stat = {
            "program": program,
            "total": total,
            "active": active,
            "new_this_month": new_this_month,
            "notes_this_week": notes_this_week,
            # New metrics
            "engagement_quality": _calc_engagement_quality(program, month_start),
            "goal_completion": _calc_goal_completion(program),
            "intake_pending": _count_intake_pending(program),
        }

        # Conditional metrics
        if show_events:
            stat["no_show_rate"] = _calc_no_show_rate(program, month_start)

        has_groups = Group.objects.filter(program=program, status="active").exists()
        if has_groups:
            stat["group_attendance"] = _calc_group_attendance(program, month_start)

        if show_portal:
            stat["portal_adoption"] = _calc_portal_adoption(active_ids)

        program_stats.append(stat)
        total_clients += total

    return render(request, "clients/executive_dashboard.html", {
        "programs": programs,
        "program_stats": program_stats,
        "total_clients": total_clients,
        "total_active": total_active,
        "without_notes": without_notes,
        "overdue_followups": overdue_followups,
        "active_alerts": active_alerts,
        "show_alerts": show_alerts,
        "show_events": show_events,
        "show_portal": show_portal,
        "selected_program_id": selected_program_id,
        "data_refreshed_at": now,
        "nav_active": "executive",
    })
