"""Sessions by Participant report — aggregation and data collection.

A new report TYPE within the reporting architecture. This is NOT a
replacement for template-driven reports; it is a purpose-built report
that answers: "How many sessions did each participant have, and what
was the total contact time?"

This report is useful for:
- Dosage tracking (how much service each participant received)
- Funder reporting on service volume
- Workload analysis by provider

See tasks/session-reporting-research.md for field requirements.
See tasks/design-rationale/reporting-architecture.md for architecture.
"""
import logging
from collections import defaultdict
from datetime import date, datetime, time

from django.db.models import Q, Sum, Count, Min, Max
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import ProgressNote

logger = logging.getLogger(__name__)


def _effective_date_filter(date_from, date_to):
    """Build a Q filter for notes within the given date range.

    Uses backdate if set, otherwise created_at — matching the pattern
    in export_engine._get_active_client_ids().
    """
    date_from_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, time.max))
    return (
        Q(backdate__range=(date_from_dt, date_to_dt))
        | Q(backdate__isnull=True, created_at__range=(date_from_dt, date_to_dt))
    )


def _get_enrolled_client_ids(program, user=None):
    """Get IDs of clients enrolled in the program, filtered by demo/real."""
    enrolled_ids = list(
        ClientProgramEnrolment.objects.filter(
            program=program, status="enrolled",
        ).values_list("client_file_id", flat=True)
    )

    if user is not None:
        if user.is_demo:
            accessible_ids = set(
                ClientFile.objects.demo().values_list("pk", flat=True)
            )
        else:
            accessible_ids = set(
                ClientFile.objects.real().values_list("pk", flat=True)
            )
        enrolled_ids = [cid for cid in enrolled_ids if cid in accessible_ids]

    return enrolled_ids


def generate_session_report(program, date_from, date_to, user=None):
    """Generate a Sessions by Participant report.

    Args:
        program: Program instance to report on.
        date_from: Start of reporting period (date).
        date_to: End of reporting period (date).
        user: Requesting user (for demo/real client filtering).

    Returns:
        dict with:
          - participants: list of dicts, one per participant, with session stats
          - sessions: list of dicts, one per session (note), for detail rows
          - summary: dict with report-level aggregates
          - metadata: dict with program name, date range, etc.
    """
    enrolled_ids = _get_enrolled_client_ids(program, user)

    # PHIPA consent: no apply_consent_filter() needed here. This report is
    # program-scoped (single program enrolment), queries only session metadata
    # (dates, duration, modality), and never displays note content. Matches the
    # DRR exemption for aggregate/de-identified reports.
    # See tasks/design-rationale/phipa-consent-enforcement.md

    # Query notes in the date range for enrolled clients
    date_filter = _effective_date_filter(date_from, date_to)
    notes_qs = (
        ProgressNote.objects.filter(
            client_file_id__in=enrolled_ids,
            status="default",
        )
        .filter(date_filter)
        .select_related("client_file", "author", "template")
        .order_by("client_file_id", "created_at")
    )

    # Build per-participant aggregates
    participant_data = defaultdict(lambda: {
        "sessions": [],
        "total_duration": 0,
        "duration_count": 0,  # sessions with duration recorded
        "modality_counts": defaultdict(int),
        "template_counts": defaultdict(int),
        "first_session": None,
        "last_session": None,
    })

    sessions_list = []

    for note in notes_qs:
        client_id = note.client_file_id
        client = note.client_file
        p = participant_data[client_id]

        eff_date = note.effective_date
        if hasattr(eff_date, "date"):
            eff_date = eff_date.date()

        session_row = {
            "client_id": client_id,
            "client_display_name": client.display_name,
            "client_last_name": client.last_name,
            "session_date": eff_date,
            "session_type": note.template.translated_name if note.template else note.get_interaction_type_display(),
            "duration_minutes": note.duration_minutes,
            "modality": note.get_modality_display() if note.modality else "",
            "modality_raw": note.modality or "",
            "provider": note.author.display_name if note.author else "",
            "interaction_type": note.get_interaction_type_display(),
        }
        sessions_list.append(session_row)
        p["sessions"].append(session_row)

        # Track participant name (use latest for display)
        p["client_display_name"] = client.display_name
        p["client_last_name"] = client.last_name

        # Duration tracking
        if note.duration_minutes:
            p["total_duration"] += note.duration_minutes
            p["duration_count"] += 1

        # Modality breakdown
        if note.modality:
            p["modality_counts"][note.get_modality_display()] += 1

        # Session type breakdown
        template_name = (
            note.template.translated_name
            if note.template
            else note.get_interaction_type_display()
        )
        p["template_counts"][template_name] += 1

        # Date tracking
        if p["first_session"] is None or eff_date < p["first_session"]:
            p["first_session"] = eff_date
        if p["last_session"] is None or eff_date > p["last_session"]:
            p["last_session"] = eff_date

    # Build participant summary list
    participants = []
    total_sessions_all = 0
    total_hours_all = 0.0

    for client_id, p in sorted(
        participant_data.items(),
        key=lambda item: (item[1].get("client_last_name", ""), item[1].get("client_display_name", "")),
    ):
        session_count = len(p["sessions"])
        contact_hours = round(p["total_duration"] / 60, 1) if p["total_duration"] else 0
        days_in_program = (
            (p["last_session"] - p["first_session"]).days
            if p["first_session"] and p["last_session"]
            else 0
        )

        participants.append({
            "client_id": client_id,
            "client_display_name": p["client_display_name"],
            "client_last_name": p["client_last_name"],
            "total_sessions": session_count,
            "total_contact_hours": contact_hours,
            "total_duration_minutes": p["total_duration"],
            "sessions_with_duration": p["duration_count"],
            "first_session": p["first_session"],
            "last_session": p["last_session"],
            "days_in_program": days_in_program,
            "modality_breakdown": dict(p["modality_counts"]),
            "session_type_breakdown": dict(p["template_counts"]),
        })

        total_sessions_all += session_count
        total_hours_all += contact_hours

    unique_participants = len(participants)
    avg_sessions = (
        round(total_sessions_all / unique_participants, 1)
        if unique_participants else 0
    )
    avg_hours = (
        round(total_hours_all / unique_participants, 1)
        if unique_participants else 0
    )

    # Compute modality distribution across all sessions
    modality_distribution = defaultdict(int)
    session_type_distribution = defaultdict(int)
    for s in sessions_list:
        if s["modality"]:
            modality_distribution[s["modality"]] += 1
        session_type_distribution[s["session_type"]] += 1

    summary = {
        "total_unique_participants": unique_participants,
        "total_sessions": total_sessions_all,
        "average_sessions_per_participant": avg_sessions,
        "average_contact_hours_per_participant": avg_hours,
        "total_contact_hours": round(total_hours_all, 1),
        "modality_distribution": dict(modality_distribution),
        "session_type_distribution": dict(session_type_distribution),
    }

    metadata = {
        "program_name": program.translated_name if hasattr(program, "translated_name") else str(program),
        "date_from": date_from,
        "date_to": date_to,
        "generated_at": timezone.now(),
        "generated_by": user.display_name if user and hasattr(user, "display_name") else str(user) if user else "",
    }

    return {
        "participants": participants,
        "sessions": sessions_list,
        "summary": summary,
        "metadata": metadata,
    }
