"""Safety oversight report generation service.

Computes aggregate metrics for a quarter, determines ROUTINE vs NOTABLE
status based on configurable triggers, and creates frozen report snapshots.
"""
import statistics
from datetime import date

from django.db.models import Count, Q
from django.utils import timezone


def compute_oversight_metrics(period_start, period_end):
    """Compute all metrics for a safety oversight quarter.

    Returns dict with aggregate counts and per-program breakdown.
    All queries are aggregate — no PII in the output.
    """
    from apps.auth_app.models import User
    from apps.clients.models import ClientFile
    from apps.events.models import Alert, AlertCancellationRecommendation
    from apps.notes.models import ProgressNote
    from apps.programs.models import Program

    period_start_dt = timezone.make_aware(
        timezone.datetime.combine(period_start, timezone.datetime.min.time())
    )
    period_end_dt = timezone.make_aware(
        timezone.datetime.combine(period_end, timezone.datetime.max.time())
    )
    now = timezone.now()

    # --- Alert metrics ---
    alerts_in_period = Alert.objects.filter(created_at__range=(period_start_dt, period_end_dt))
    alerts_raised = alerts_in_period.count()

    # Resolved = cancelled during the period
    alerts_resolved = alerts_in_period.filter(status="cancelled").count()

    # Median resolution time (days) for alerts resolved in the period
    resolved_alerts = alerts_in_period.filter(
        status="cancelled",
        updated_at__isnull=False,
    )
    resolution_days = []
    for alert in resolved_alerts.only("created_at", "updated_at"):
        delta = (alert.updated_at - alert.created_at).total_seconds() / 86400
        resolution_days.append(delta)
    median_resolution_days = (
        round(statistics.median(resolution_days), 1) if resolution_days else None
    )

    # Active at quarter end
    active_at_end = Alert.objects.filter(
        created_at__lte=period_end_dt,
        status="default",
    ).count()

    # Aging (>14 days old at quarter end)
    cutoff_14d = period_end_dt - timezone.timedelta(days=14)
    aging_alerts = Alert.objects.filter(
        created_at__lte=cutoff_14d,
        status="default",
    ).count()

    # Pending cancellation reviews
    pending_reviews = AlertCancellationRecommendation.objects.filter(
        status="pending",
        alert__status="default",
    ).count()

    # --- System activity metrics ---
    notes_recorded = ProgressNote.objects.filter(
        created_at__range=(period_start_dt, period_end_dt),
        status="default",
    ).count()

    active_participants = ClientFile.objects.filter(status="active").count()

    active_staff = User.objects.filter(
        is_active=True,
        program_roles__status="active",
    ).distinct().count()

    # --- Program breakdown ---
    program_breakdown = []
    programs = Program.objects.all().order_by("name")
    for program in programs:
        prog_alerts = Alert.objects.filter(
            author_program=program,
            created_at__range=(period_start_dt, period_end_dt),
        )
        prog_active = Alert.objects.filter(
            author_program=program,
            created_at__lte=period_end_dt,
            status="default",
        ).count()
        program_breakdown.append({
            "program_id": program.pk,
            "program_name": str(program.translated_name),
            "alerts_raised": prog_alerts.count(),
            "active_at_end": prog_active,
        })

    # --- Previous quarter for comparison ---
    prev_start, prev_end = _previous_quarter(period_start, period_end)
    prev_start_dt = timezone.make_aware(
        timezone.datetime.combine(prev_start, timezone.datetime.min.time())
    )
    prev_end_dt = timezone.make_aware(
        timezone.datetime.combine(prev_end, timezone.datetime.max.time())
    )
    prev_alerts_raised = Alert.objects.filter(
        created_at__range=(prev_start_dt, prev_end_dt),
    ).count()
    prev_notes_recorded = ProgressNote.objects.filter(
        created_at__range=(prev_start_dt, prev_end_dt),
        status="default",
    ).count()

    return {
        "alerts_raised": alerts_raised,
        "alerts_resolved": alerts_resolved,
        "median_resolution_days": median_resolution_days,
        "active_at_quarter_end": active_at_end,
        "aging_alerts": aging_alerts,
        "pending_reviews": pending_reviews,
        "notes_recorded": notes_recorded,
        "active_participants": active_participants,
        "active_staff": active_staff,
        "program_breakdown": program_breakdown,
        "prev_alerts_raised": prev_alerts_raised,
        "prev_notes_recorded": prev_notes_recorded,
    }


def determine_status(metrics):
    """Return (status, triggers_list) based on metrics.

    Returns ("ROUTINE", []) or ("NOTABLE", [list of trigger descriptions]).
    """
    triggers = []

    if metrics.get("aging_alerts", 0) > 0:
        triggers.append(
            f"{metrics['aging_alerts']} alert(s) older than 14 days"
        )

    if metrics.get("pending_reviews", 0) > 0:
        triggers.append(
            f"{metrics['pending_reviews']} cancellation review(s) pending"
        )

    # Program concentration: any program has >50% of all alerts
    breakdown = metrics.get("program_breakdown", [])
    total_raised = metrics.get("alerts_raised", 0)
    if total_raised >= 4:  # Only check concentration with meaningful volume
        for prog in breakdown:
            if prog["alerts_raised"] > total_raised * 0.5:
                triggers.append(
                    f"{prog['program_name']} has {prog['alerts_raised']} of "
                    f"{total_raised} alerts ({round(prog['alerts_raised'] / total_raised * 100)}%)"
                )

    # Activity drop: notes down >30% from previous quarter
    prev_notes = metrics.get("prev_notes_recorded", 0)
    curr_notes = metrics.get("notes_recorded", 0)
    if prev_notes > 10 and curr_notes < prev_notes * 0.7:
        drop_pct = round((1 - curr_notes / prev_notes) * 100)
        triggers.append(
            f"Progress notes dropped {drop_pct}% from previous quarter "
            f"({curr_notes} vs {prev_notes})"
        )

    status = "NOTABLE" if triggers else "ROUTINE"
    return status, triggers


def generate_oversight_report(period_label, period_start, period_end, user):
    """Full generation pipeline: compute, classify, create snapshot.

    Returns the created OversightReportSnapshot instance.
    """
    from .models import OversightReportSnapshot

    metrics = compute_oversight_metrics(period_start, period_end)
    status, triggers = determine_status(metrics)

    snapshot = OversightReportSnapshot.objects.create(
        period_label=period_label,
        period_start=period_start,
        period_end=period_end,
        metrics_json=metrics,
        overall_status=status,
        notable_triggers=triggers,
        no_aging_alerts=metrics["aging_alerts"] == 0,
        no_pending_reviews=metrics["pending_reviews"] == 0,
        no_program_concentration=not any(
            "has" in t and "alerts" in t for t in triggers
        ),
        generated_by=user,
    )
    return snapshot


def get_oversight_context(snapshot, is_external=False):
    """Build template context from a snapshot.

    If is_external, suppresses counts below 5 in program breakdown.
    """
    metrics = snapshot.metrics_json

    # Apply suppression for external reports
    program_breakdown = list(metrics.get("program_breakdown", []))
    if is_external:
        for prog in program_breakdown:
            for key in ("alerts_raised", "active_at_end"):
                if 0 < prog.get(key, 0) < 5:
                    prog[key] = "<5"

    return {
        "snapshot": snapshot,
        "period_label": snapshot.period_label,
        "period_start": snapshot.period_start,
        "period_end": snapshot.period_end,
        "overall_status": snapshot.overall_status,
        "status_class": "success" if snapshot.overall_status == "ROUTINE" else "warning",
        "notable_triggers": snapshot.notable_triggers,
        "narrative": snapshot.narrative,
        # Key metrics
        "alerts_raised": metrics.get("alerts_raised", 0),
        "alerts_resolved": metrics.get("alerts_resolved", 0),
        "median_resolution_days": metrics.get("median_resolution_days"),
        "active_at_quarter_end": metrics.get("active_at_quarter_end", 0),
        # System activity
        "notes_recorded": metrics.get("notes_recorded", 0),
        "active_participants": metrics.get("active_participants", 0),
        "active_staff": metrics.get("active_staff", 0),
        # Health indicators
        "no_aging_alerts": snapshot.no_aging_alerts,
        "no_pending_reviews": snapshot.no_pending_reviews,
        "no_program_concentration": snapshot.no_program_concentration,
        # Comparison
        "prev_alerts_raised": metrics.get("prev_alerts_raised", 0),
        "prev_notes_recorded": metrics.get("prev_notes_recorded", 0),
        # Program breakdown
        "program_breakdown": program_breakdown,
        # Attestation
        "approved_by": snapshot.approved_by,
        "approved_at": snapshot.approved_at,
        # Meta
        "is_external": is_external,
        "generated_at": snapshot.created_at,
        "generated_by": snapshot.generated_by,
    }


def _previous_quarter(period_start, period_end):
    """Return (start, end) dates for the quarter before the given one."""
    import calendar

    # Go back 3 months from period_start
    month = period_start.month - 3
    year = period_start.year
    while month < 1:
        month += 12
        year -= 1
    prev_start = date(year, month, 1)

    # End is day before current period_start
    prev_end = period_start - timezone.timedelta(days=1)
    return prev_start, prev_end


def quarter_dates(period_label):
    """Parse a period label like 'Q1 2026' into (start, end) dates."""
    try:
        quarter, year_str = period_label.split()
        year = int(year_str)
        quarter_num = int(quarter[1])
        if quarter_num < 1 or quarter_num > 4:
            raise ValueError
    except (ValueError, IndexError):
        raise ValueError(f"Invalid period label: {period_label!r} (expected 'Q1 2026' format)")

    month_start = (quarter_num - 1) * 3 + 1
    start = date(year, month_start, 1)

    month_end = month_start + 2
    import calendar
    end_day = calendar.monthrange(year, month_end)[1]
    end = date(year, month_end, end_day)

    return start, end
