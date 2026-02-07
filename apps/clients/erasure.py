"""Client data erasure service — tiered anonymisation and deletion logic.

This module contains the business logic for the multi-PM erasure approval
workflow. Views call these functions; they never call client.delete() directly.

Three tiers of erasure:
  - anonymise (default): Strip PII, keep all service records intact.
  - anonymise_purge: Strip PII and blank all narrative content.
  - full_erasure: CASCADE delete (only when retention period has expired).
"""
import logging

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def build_data_summary(client_file):
    """Build a statistical summary for a ClientFile.

    Returns a dict of integer counts and non-PII metadata.
    Used to populate ErasureRequest.data_summary at request time.
    This data forms the statistical tombstone that survives after erasure.
    """
    from apps.events.models import Alert, Event
    from apps.notes.models import MetricValue, ProgressNote
    from apps.plans.models import PlanSection, PlanTarget

    from .models import ClientDetailValue, ClientProgramEnrolment

    # Record counts (existing)
    summary = {
        "progress_notes": ProgressNote.objects.filter(client_file=client_file).count(),
        "plan_sections": PlanSection.objects.filter(client_file=client_file).count(),
        "plan_targets": PlanTarget.objects.filter(client_file=client_file).count(),
        "events": Event.objects.filter(client_file=client_file).count(),
        "alerts": Alert.objects.filter(client_file=client_file).count(),
        "custom_field_values": ClientDetailValue.objects.filter(client_file=client_file).count(),
        "enrolments": ClientProgramEnrolment.objects.filter(client_file=client_file).count(),
        "metric_values": MetricValue.objects.filter(
            progress_note_target__progress_note__client_file=client_file
        ).count(),
    }

    # Programme names (not PII — programme names are organisational, not personal)
    enrolments = ClientProgramEnrolment.objects.filter(
        client_file=client_file,
    ).select_related("program")
    summary["programmes"] = list({e.program.name for e in enrolments if e.program})

    # Service period (earliest enrolment → latest activity)
    first_enrolment = enrolments.order_by("enrolled_at").first()
    if first_enrolment and first_enrolment.enrolled_at:
        summary["service_period_start"] = first_enrolment.enrolled_at.isoformat()
    last_note = ProgressNote.objects.filter(
        client_file=client_file,
    ).order_by("-created_at").first()
    if last_note:
        summary["service_period_end"] = last_note.created_at.isoformat()

    # Outcome summary (target status counts)
    targets = PlanTarget.objects.filter(client_file=client_file)
    if targets.exists():
        from collections import Counter
        status_counts = Counter(targets.values_list("status", flat=True))
        summary["outcome_summary"] = dict(status_counts)

    return summary


def get_available_tiers(client_file):
    """Determine which erasure tiers are available based on retention status.

    Returns a dict of tier → {available: bool, reason: str}.
    Tiers 1 (anonymise) and 2 (anonymise_purge) are always available.
    Tier 3 (full_erasure) requires the retention period to have expired.
    """
    today = timezone.now().date()

    result = {
        "anonymise": {"available": True, "reason": ""},
        "anonymise_purge": {"available": True, "reason": ""},
        "full_erasure": {"available": False, "reason": ""},
    }

    if client_file.retention_expires:
        if client_file.retention_expires <= today:
            result["full_erasure"]["available"] = True
            result["full_erasure"]["reason"] = ""
        else:
            days_remaining = (client_file.retention_expires - today).days
            result["full_erasure"]["reason"] = _(
                "Retention period has not expired. %(days)s days remaining "
                "(expires %(date)s). Only anonymisation is available."
            ) % {"days": days_remaining, "date": client_file.retention_expires}
    else:
        result["full_erasure"]["reason"] = _(
            "No retention period has been set for this client. "
            "Set a retention expiry date before requesting full erasure."
        )

    return result


def get_required_programs(client_file):
    """Return list of programs that need PM approval for this client.

    Logic (never returns empty):
    1. Active enrolments (status="enrolled")
    2. If empty: historical enrolments (any status)
    3. If still empty: all active programs (any PM can approve)
    """
    from apps.programs.models import Program

    from .models import ClientProgramEnrolment

    # 1. Active enrolments
    active_program_ids = list(
        ClientProgramEnrolment.objects.filter(
            client_file=client_file, status="enrolled",
        ).values_list("program_id", flat=True).distinct()
    )
    if active_program_ids:
        return list(Program.objects.filter(pk__in=active_program_ids, status="active").values_list("pk", flat=True))

    # 2. Historical enrolments (includes unenrolled)
    historical_program_ids = list(
        ClientProgramEnrolment.objects.filter(
            client_file=client_file,
        ).values_list("program_id", flat=True).distinct()
    )
    if historical_program_ids:
        active_programs = list(
            Program.objects.filter(pk__in=historical_program_ids, status="active").values_list("pk", flat=True)
        )
        if active_programs:
            return active_programs

    # 3. Safety net: any active program (so at least one PM must approve)
    any_program = Program.objects.filter(status="active").values_list("pk", flat=True).first()
    if any_program:
        return [any_program]

    # Should never happen — there must be at least one program in the system
    raise ValueError("Cannot determine approval requirements: no active programs exist.")


def check_all_approved(erasure_request):
    """Check whether all required programs have an approval.

    Uses count-based comparison to handle edge case of deleted programs.
    """
    required_count = len(erasure_request.programs_required)
    approval_count = erasure_request.approvals.count()
    return approval_count >= required_count


def is_deadlocked(erasure_request):
    """Check if the requester is the only active PM for all remaining unapproved programs.

    Returns True if an admin fallback is needed to break the deadlock.
    """
    from apps.programs.models import UserProgramRole

    if erasure_request.status != "pending":
        return False

    requester = erasure_request.requested_by
    if requester is None:
        return False

    # Find programs that still need approval
    approved_program_ids = set(
        erasure_request.approvals.values_list("program_id", flat=True)
    )
    remaining_program_ids = [
        pk for pk in erasure_request.programs_required
        if pk not in approved_program_ids
    ]

    if not remaining_program_ids:
        return False  # All approved, not deadlocked

    # For each remaining program, check if there's an active PM who isn't the requester
    for program_id in remaining_program_ids:
        other_pms = UserProgramRole.objects.filter(
            program_id=program_id,
            role="program_manager",
            status="active",
        ).exclude(user=requester)
        if other_pms.exists():
            return False  # At least one other PM can approve this program

    return True  # Requester is the only PM for all remaining programs


def record_approval(erasure_request, user, program, ip_address, review_notes=""):
    """Record a PM's approval for one program and auto-execute if all approved.

    Uses select_for_update() to prevent concurrent double-execution.

    Returns:
        tuple: (approval, executed) — the ErasureApproval and whether erasure ran.

    Raises:
        ValueError: If request isn't pending, user can't approve, etc.
    """
    from .models import ErasureApproval

    with transaction.atomic():
        # Lock the request row to prevent concurrent double-execution
        er = type(erasure_request).objects.select_for_update().get(pk=erasure_request.pk)

        if er.status != "pending":
            raise ValueError(f"Cannot approve — status is '{er.status}', not 'pending'.")

        if er.requested_by == user and not _is_admin_fallback(er, user):
            raise ValueError(_("You cannot approve your own erasure request."))

        # Check this program hasn't already been approved
        if er.approvals.filter(program=program).exists():
            raise ValueError(f"Program '{program.name}' has already been approved.")

        # Create the approval record
        approval = ErasureApproval.objects.create(
            erasure_request=er,
            program=program,
            approved_by=user,
            approved_by_display=user.get_display_name(),
            review_notes=review_notes,
        )

        # Log the individual approval
        _log_audit(
            user=user,
            action="update",
            resource_type="erasure_approval",
            resource_id=er.pk,
            ip_address=ip_address,
            metadata={
                "client_pk": er.client_pk,
                "program_id": program.pk,
                "program_name": program.name,
                "approval_id": approval.pk,
            },
        )

        # Check if all programs are now approved
        if check_all_approved(er):
            execute_erasure(er, ip_address)
            return approval, True

    return approval, False


def execute_erasure(erasure_request, ip_address):
    """Dispatch to the appropriate tier's execution logic.

    Must be called within a transaction (record_approval wraps it).
    """
    tier = erasure_request.erasure_tier

    if tier == "anonymise":
        _execute_tier1_anonymise(erasure_request, ip_address)
    elif tier == "anonymise_purge":
        _execute_tier2_anonymise_purge(erasure_request, ip_address)
    elif tier == "full_erasure":
        _execute_tier3_full_erasure(erasure_request, ip_address)
    else:
        raise ValueError(f"Unknown erasure tier: {tier}")


def _scrub_registration_submissions(client):
    """Scrub PII from RegistrationSubmissions linked to a client."""
    from apps.registration.models import RegistrationSubmission

    RegistrationSubmission.objects.filter(client_file=client).update(
        _first_name_encrypted=b"",
        _last_name_encrypted=b"",
        _email_encrypted=b"",
        _phone_encrypted=b"",
        email_hash="",
    )


def _anonymise_client_pii(client, erasure_code):
    """Strip all PII from a ClientFile record, keeping the record intact.

    Sets encrypted fields to empty bytes, replaces record_id with erasure code.
    """
    from .models import ClientDetailValue

    # Blank client identifying fields
    client._first_name_encrypted = b""
    client._preferred_name_encrypted = b""
    client._middle_name_encrypted = b""
    client._last_name_encrypted = b""
    client._birth_date_encrypted = b""
    client.record_id = erasure_code
    client.status = "discharged"
    client.is_anonymised = True
    client.erasure_completed_at = timezone.now()
    client.save()

    # Blank sensitive custom field values
    ClientDetailValue.objects.filter(
        client_file=client,
        field_def__is_sensitive=True,
    ).update(_value_encrypted=b"", value="")

    # Also blank non-sensitive custom field values (may contain identifying info)
    ClientDetailValue.objects.filter(
        client_file=client,
        field_def__is_sensitive=False,
    ).update(value="")


def _purge_narrative_content(client):
    """Blank all narrative/text content from a client's related records.

    Keeps the records themselves (dates, structure, numeric metrics survive).
    """
    from apps.events.models import Alert, Event
    from apps.notes.models import ProgressNote, ProgressNoteTarget

    # Blank progress note text
    ProgressNote.objects.filter(client_file=client).update(
        _notes_text_encrypted=b"",
        _summary_encrypted=b"",
        _participant_reflection_encrypted=b"",
    )

    # Blank target-level notes
    ProgressNoteTarget.objects.filter(
        progress_note__client_file=client,
    ).update(_notes_encrypted=b"")

    # Blank alert content
    Alert.objects.filter(client_file=client).update(content="")

    # Blank event text (titles and descriptions may contain identifying info)
    Event.objects.filter(client_file=client).update(title="", description="")


def _log_erasure_audit(erasure_request, client_pk, record_id, action, ip_address):
    """Write the audit log entry for an erasure execution.

    Raises on failure — erasure must not proceed without an audit trail.
    """
    _log_audit(
        user=None,
        action=action,
        resource_type="client_erasure",
        resource_id=client_pk,
        ip_address=ip_address,
        metadata={
            "erasure_request_id": erasure_request.pk,
            "erasure_code": erasure_request.erasure_code,
            "erasure_tier": erasure_request.erasure_tier,
            "record_id": record_id,
            "requested_by": erasure_request.requested_by_display,
            "reason_category": erasure_request.reason_category,
            "reason": erasure_request.request_reason,
            "data_summary": erasure_request.data_summary,
            "programs_required": erasure_request.programs_required,
            "approvals": [
                {"program_id": a.program_id, "approved_by": a.approved_by_display}
                for a in erasure_request.approvals.all()
            ],
        },
    )


def _execute_tier1_anonymise(erasure_request, ip_address):
    """Tier 1: Strip all PII, keep all service records intact.

    The client record survives as [ANONYMISED] with programme enrolments,
    progress notes, plans, metrics, events, and alerts all preserved.
    No identifying information remains linked to the record.
    """
    client = erasure_request.client_file
    if client is None:
        raise ValueError("Client file no longer exists.")

    client_pk = client.pk
    record_id = client.record_id

    # Write audit FIRST — if this fails, erasure doesn't proceed
    _log_erasure_audit(erasure_request, client_pk, record_id, "update", ip_address)

    _scrub_registration_submissions(client)
    _anonymise_client_pii(client, erasure_request.erasure_code)

    # Update the ErasureRequest — client_file stays linked (record still exists)
    erasure_request.status = "anonymised"
    erasure_request.completed_at = timezone.now()
    erasure_request.save(update_fields=["status", "completed_at"])


def _execute_tier2_anonymise_purge(erasure_request, ip_address):
    """Tier 2: Strip all PII AND blank all narrative content.

    Like Tier 1 but also removes text from notes, alerts, and events.
    Numeric metrics, plan structure, and programme enrolments survive.
    """
    client = erasure_request.client_file
    if client is None:
        raise ValueError("Client file no longer exists.")

    client_pk = client.pk
    record_id = client.record_id

    # Write audit FIRST — if this fails, erasure doesn't proceed
    _log_erasure_audit(erasure_request, client_pk, record_id, "update", ip_address)

    _scrub_registration_submissions(client)
    _anonymise_client_pii(client, erasure_request.erasure_code)
    _purge_narrative_content(client)

    erasure_request.status = "anonymised"
    erasure_request.completed_at = timezone.now()
    erasure_request.save(update_fields=["status", "completed_at"])


def _execute_tier3_full_erasure(erasure_request, ip_address):
    """Tier 3: CASCADE delete — the original behaviour.

    Deletes the ClientFile and all related records. Only the ErasureRequest
    tombstone survives (with data_summary counts and erasure_code).
    Only available when the retention period has expired.
    """
    client = erasure_request.client_file
    if client is None:
        raise ValueError("Client file no longer exists.")

    client_pk = client.pk
    record_id = client.record_id

    # Write audit FIRST — if this fails, erasure doesn't proceed
    _log_erasure_audit(erasure_request, client_pk, record_id, "delete", ip_address)

    _scrub_registration_submissions(client)
    client.delete()

    erasure_request.status = "approved"
    erasure_request.completed_at = timezone.now()
    erasure_request.client_file = None
    erasure_request.save(update_fields=["status", "completed_at", "client_file"])


def _is_admin_fallback(erasure_request, user):
    """Check if this is a valid admin fallback approval (deadlock scenario)."""
    return getattr(user, "is_admin", False) and is_deadlocked(erasure_request)


def _log_audit(user, action, resource_type, resource_id, ip_address, metadata=None):
    """Write an audit log entry to the separate audit database."""
    from apps.audit.models import AuditLog

    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=user.pk if user else None,
        user_display=user.get_display_name() if user else "[system]",
        ip_address=ip_address or "",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        is_demo_context=getattr(user, "is_demo", False) if user else False,
        metadata=metadata or {},
    )
