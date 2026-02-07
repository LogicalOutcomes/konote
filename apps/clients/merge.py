"""Duplicate client merge service — find candidates, compare, execute.

This module contains the business logic for merging duplicate client records.
Views call these functions; they never modify client data directly.

Security rules:
  - Clients with ANY confidential programme enrolment (current or historical)
    are excluded from merge candidates and cannot be merged.
  - Demo/real separation is enforced.
  - Both clients must be free of pending ErasureRequests.
  - All merges are audited in the separate audit database.
"""
import logging
from collections import defaultdict

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from .matching import _iter_matchable_clients
from .models import (
    ClientDetailValue,
    ClientFile,
    ClientMerge,
    ClientProgramEnrolment,
    ErasureRequest,
)
from .validators import normalize_phone_number

logger = logging.getLogger(__name__)

# Maximum clients to scan — beyond this, show a message instead of timing out.
MAX_MATCHABLE_CLIENTS = 2000


def _get_all_confidential_client_ids():
    """Return set of client IDs with ANY confidential enrolment (current or historical).

    This is broader than the matching.py filter, which only checks status='enrolled'.
    A client who was ever in a confidential programme retains a privacy interest.
    """
    return set(
        ClientProgramEnrolment.objects.filter(
            program__is_confidential=True,
        ).values_list("client_file_id", flat=True)
    )


def _get_program_names(client):
    """Return list of Standard programme names this client is enrolled in."""
    return list(
        ClientProgramEnrolment.objects.filter(
            client_file=client,
            status="enrolled",
            program__is_confidential=False,
        ).select_related("program")
        .values_list("program__name", flat=True)
    )


def _parse_date(val):
    """Parse a date value to a date object, or return None."""
    from datetime import date

    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


def find_merge_candidates(user):
    """Find pairs of clients that may be duplicates.

    Uses the same matching logic as duplicate detection:
    - Phone match (exact, normalised) — primary, stronger signal
    - Name + DOB match (first 3 chars of first name + exact DOB) — secondary

    Returns dict with keys:
      - 'phone': list of candidate pair dicts
      - 'name_dob': list of candidate pair dicts
      - 'too_many': True if client count exceeds MAX_MATCHABLE_CLIENTS
      - 'phone_count': int
      - 'name_dob_count': int

    Each pair dict: {client_a: {...}, client_b: {...}, match_type: str}

    Confidential programme clients (current or historical) are excluded.
    Demo/real separation is enforced by _iter_matchable_clients().
    """
    # Additional filter: exclude clients with any historical confidential enrolment
    historical_confidential_ids = _get_all_confidential_client_ids()

    # Single pass through all matchable clients — build lookup dicts
    phone_groups = defaultdict(list)  # normalised_phone → [client_info, ...]
    name_dob_groups = defaultdict(list)  # (name_prefix, dob) → [client_info, ...]

    client_count = 0
    for client in _iter_matchable_clients(user):
        # Skip clients with any historical confidential enrolment
        if client.pk in historical_confidential_ids:
            continue
        # Skip anonymised clients
        if client.is_anonymised:
            continue

        client_count += 1
        if client_count > MAX_MATCHABLE_CLIENTS:
            return {
                "phone": [],
                "name_dob": [],
                "too_many": True,
                "phone_count": 0,
                "name_dob_count": 0,
            }

        info = {
            "client_id": client.pk,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "phone": client.phone,
            "birth_date": str(client.birth_date) if client.birth_date else "",
            "program_names": _get_program_names(client),
            "created_at": client.created_at,
        }

        # Index by phone
        phone = normalize_phone_number(client.phone or "")
        if phone:
            phone_groups[phone].append(info)

        # Index by name prefix + DOB
        prefix = (client.first_name or "").strip()[:3].casefold()
        dob = _parse_date(client.birth_date)
        if len(prefix) >= 3 and dob is not None:
            name_dob_groups[(prefix, dob)].append(info)

    # Build candidate pairs from groups with 2+ members
    phone_pairs = []
    seen_pairs = set()
    for _phone, clients in phone_groups.items():
        if len(clients) < 2:
            continue
        for i in range(len(clients)):
            for j in range(i + 1, len(clients)):
                pair_key = tuple(sorted([clients[i]["client_id"], clients[j]["client_id"]]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    phone_pairs.append({
                        "client_a": clients[i],
                        "client_b": clients[j],
                        "match_type": "phone",
                    })

    name_dob_pairs = []
    for _key, clients in name_dob_groups.items():
        if len(clients) < 2:
            continue
        for i in range(len(clients)):
            for j in range(i + 1, len(clients)):
                pair_key = tuple(sorted([clients[i]["client_id"], clients[j]["client_id"]]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    name_dob_pairs.append({
                        "client_a": clients[i],
                        "client_b": clients[j],
                        "match_type": "name_dob",
                    })

    return {
        "phone": phone_pairs,
        "name_dob": name_dob_pairs,
        "too_many": False,
        "phone_count": len(phone_pairs),
        "name_dob_count": len(name_dob_pairs),
    }


def build_comparison(client_a, client_b):
    """Build side-by-side comparison data for two clients.

    Returns dict with all the data needed for the comparison template.
    """
    from apps.events.models import Alert, Event
    from apps.groups.models import GroupMembership
    from apps.notes.models import ProgressNote
    from apps.plans.models import PlanSection, PlanTarget

    # PII field comparison
    pii_fields = []
    for field_name, label in [
        ("first_name", _("First Name")),
        ("middle_name", _("Middle Name")),
        ("last_name", _("Last Name")),
        ("birth_date", _("Date of Birth")),
        ("phone", _("Phone Number")),
    ]:
        val_a = getattr(client_a, field_name, "") or ""
        val_b = getattr(client_b, field_name, "") or ""
        pii_fields.append({
            "field_name": field_name,
            "label": label,
            "value_a": str(val_a),
            "value_b": str(val_b),
            "differs": str(val_a) != str(val_b),
        })

    # Record counts
    def _counts(client):
        last_note = ProgressNote.objects.filter(
            client_file=client,
        ).order_by("-created_at").first()
        return {
            "notes": ProgressNote.objects.filter(client_file=client).count(),
            "events": Event.objects.filter(client_file=client).count(),
            "alerts": Alert.objects.filter(client_file=client).count(),
            "plan_sections": PlanSection.objects.filter(client_file=client).count(),
            "plan_targets": PlanTarget.objects.filter(client_file=client).count(),
            "custom_fields": ClientDetailValue.objects.filter(client_file=client).count(),
            "group_memberships": GroupMembership.objects.filter(client_file=client).count(),
            "enrolments": ClientProgramEnrolment.objects.filter(client_file=client).count(),
            "last_note_date": last_note.created_at if last_note else None,
        }

    counts_a = _counts(client_a)
    counts_b = _counts(client_b)

    # Custom field conflicts
    # Get all field values for both clients
    cdv_a = {
        cdv.field_def_id: cdv
        for cdv in ClientDetailValue.objects.filter(client_file=client_a).select_related("field_def")
    }
    cdv_b = {
        cdv.field_def_id: cdv
        for cdv in ClientDetailValue.objects.filter(client_file=client_b).select_related("field_def")
    }

    field_conflicts = []
    for field_def_id in set(cdv_a.keys()) & set(cdv_b.keys()):
        val_a_obj = cdv_a[field_def_id]
        val_b_obj = cdv_b[field_def_id]
        # Use the encrypted value accessor if sensitive, plain value otherwise
        a_val = val_a_obj.display_value if hasattr(val_a_obj, "display_value") else val_a_obj.value
        b_val = val_b_obj.display_value if hasattr(val_b_obj, "display_value") else val_b_obj.value
        if str(a_val) != str(b_val):
            field_conflicts.append({
                "field_def_id": field_def_id,
                "field_name": val_a_obj.field_def.name if val_a_obj.field_def else f"Field #{field_def_id}",
                "value_a": str(a_val),
                "value_b": str(b_val),
            })

    # Enrolment overlaps
    enrolments_a = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client_a, status="enrolled",
        ).values_list("program_id", flat=True)
    )
    enrolments_b = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client_b, status="enrolled",
        ).values_list("program_id", flat=True)
    )
    overlapping_program_ids = enrolments_a & enrolments_b

    # Post-merge programme list (all programmes both clients are in)
    from apps.programs.models import Program

    all_program_ids = enrolments_a | enrolments_b
    post_merge_programs = list(
        Program.objects.filter(pk__in=all_program_ids).values_list("name", flat=True)
    )

    return {
        "pii_fields": pii_fields,
        "counts_a": counts_a,
        "counts_b": counts_b,
        "field_conflicts": field_conflicts,
        "overlapping_program_count": len(overlapping_program_ids),
        "post_merge_programs": post_merge_programs,
    }


def _validate_merge_preconditions(kept, archived):
    """Validate that a merge can proceed. Returns list of error messages."""
    errors = []

    if kept.is_anonymised:
        errors.append(_("The primary client record has been anonymised and cannot be merged."))
    if archived.is_anonymised:
        errors.append(_("The secondary client record has been anonymised and cannot be merged."))

    if kept.is_demo != archived.is_demo:
        errors.append(_("Cannot merge a demo client with a real client."))

    # Check for ANY confidential enrolment (current or historical)
    confidential_ids = _get_all_confidential_client_ids()
    if kept.pk in confidential_ids:
        errors.append(_("The primary client has a confidential programme enrolment and cannot be merged."))
    if archived.pk in confidential_ids:
        errors.append(_("The secondary client has a confidential programme enrolment and cannot be merged."))

    # Check for pending erasure requests
    pending_statuses = ["pending"]
    if ErasureRequest.objects.filter(
        client_file__in=[kept, archived],
        status__in=pending_statuses,
    ).exists():
        errors.append(
            _("One of these clients has a pending data erasure request. "
              "Complete or cancel the erasure before merging.")
        )

    return errors


@transaction.atomic
def execute_merge(kept, archived, pii_choices, field_resolutions, user, ip_address):
    """Execute the merge of archived client into kept client.

    All related records transfer from archived → kept. The archived client
    is anonymised (PII stripped, status discharged). This cannot be undone.

    Args:
        kept: ClientFile to keep (surviving record)
        archived: ClientFile to archive (will be anonymised)
        pii_choices: dict of {field_name: 'kept'|'archived'} for differing PII fields
        field_resolutions: dict of {field_def_id: 'kept'|'archived'} for custom field conflicts
        user: User performing the merge
        ip_address: Request IP for audit logging

    Returns:
        ClientMerge instance

    Raises:
        ValueError: If preconditions are not met
    """
    from apps.events.models import Alert, Event
    from apps.groups.models import GroupMembership
    from apps.notes.models import ProgressNote
    from apps.plans.models import PlanSection, PlanTarget
    from apps.registration.models import RegistrationSubmission

    # 1. Lock both rows — lower PK first to prevent deadlocks
    lock_ids = sorted([kept.pk, archived.pk])
    locked = list(
        ClientFile.objects.filter(pk__in=lock_ids).select_for_update().order_by("pk")
    )
    if len(locked) != 2:
        raise ValueError(_("One or both client records no longer exist."))
    # Re-assign to locked instances
    kept = locked[0] if locked[0].pk == kept.pk else locked[1]
    archived = locked[0] if locked[0].pk == archived.pk else locked[1]

    # 2. Validate preconditions
    errors = _validate_merge_preconditions(kept, archived)
    if errors:
        raise ValueError(" ".join(errors))

    # 3. Apply PII choices — copy fields from archived if admin chose them
    for field_name, choice in pii_choices.items():
        if choice == "archived":
            if field_name == "first_name":
                kept.first_name = archived.first_name
            elif field_name == "middle_name":
                kept.middle_name = archived.middle_name
            elif field_name == "last_name":
                kept.last_name = archived.last_name
            elif field_name == "birth_date":
                kept._birth_date_encrypted = archived._birth_date_encrypted
            elif field_name == "phone":
                kept._phone_encrypted = archived._phone_encrypted
    kept.save()

    # Build transfer summary as we go
    summary = {}

    # 4. Transfer related records via bulk update
    summary["notes"] = ProgressNote.objects.filter(client_file=archived).update(client_file=kept)
    summary["plan_targets"] = PlanTarget.objects.filter(client_file=archived).update(client_file=kept)
    summary["plan_sections"] = PlanSection.objects.filter(client_file=archived).update(client_file=kept)
    summary["events"] = Event.objects.filter(client_file=archived).update(client_file=kept)
    summary["alerts"] = Alert.objects.filter(client_file=archived).update(client_file=kept)
    summary["registration_submissions"] = RegistrationSubmission.objects.filter(
        client_file=archived
    ).update(client_file=kept)
    summary["erasure_requests"] = ErasureRequest.objects.filter(
        client_file=archived
    ).update(client_file=kept)

    # 5. Handle enrolment conflicts — preserve history, don't delete
    kept_enrolment_programs = set(
        ClientProgramEnrolment.objects.filter(
            client_file=kept,
        ).values_list("program_id", flat=True)
    )

    archived_enrolments = ClientProgramEnrolment.objects.filter(client_file=archived)
    enrolments_transferred = 0
    enrolments_marked_unenrolled = 0

    for enrolment in archived_enrolments:
        if enrolment.program_id in kept_enrolment_programs:
            # Both enrolled in same programme — keep earlier enrolled_at on kept's,
            # mark archived's as unenrolled to preserve the history
            kept_enrolment = ClientProgramEnrolment.objects.get(
                client_file=kept, program_id=enrolment.program_id,
            )
            if enrolment.enrolled_at < kept_enrolment.enrolled_at:
                kept_enrolment.enrolled_at = enrolment.enrolled_at
                kept_enrolment.save(update_fields=["enrolled_at"])
            enrolment.status = "unenrolled"
            enrolment.unenrolled_at = timezone.now()
            enrolment.client_file = kept
            enrolment.save(update_fields=["status", "unenrolled_at", "client_file"])
            enrolments_marked_unenrolled += 1
        else:
            # No conflict — transfer
            enrolment.client_file = kept
            enrolment.save(update_fields=["client_file"])
            enrolments_transferred += 1

    summary["enrolments_transferred"] = enrolments_transferred
    summary["enrolments_marked_unenrolled"] = enrolments_marked_unenrolled

    # 6. Handle custom field conflicts (ClientDetailValue unique_together)
    kept_field_ids = set(
        ClientDetailValue.objects.filter(client_file=kept).values_list("field_def_id", flat=True)
    )

    archived_cdvs = ClientDetailValue.objects.filter(client_file=archived)
    fields_transferred = 0
    fields_resolved = 0

    for cdv in archived_cdvs:
        if cdv.field_def_id in kept_field_ids:
            # Conflict — resolve based on admin's choice
            resolution = field_resolutions.get(str(cdv.field_def_id), "kept")
            if resolution == "archived":
                # Admin chose archived's value — update kept's value
                kept_cdv = ClientDetailValue.objects.get(
                    client_file=kept, field_def_id=cdv.field_def_id,
                )
                kept_cdv.value = cdv.value
                kept_cdv._value_encrypted = cdv._value_encrypted
                kept_cdv.save()
            # Delete archived's CDV (resolves unique constraint)
            cdv.delete()
            fields_resolved += 1
        else:
            # No conflict — transfer
            cdv.client_file = kept
            cdv.save(update_fields=["client_file"])
            fields_transferred += 1

    summary["custom_fields_transferred"] = fields_transferred
    summary["custom_fields_resolved"] = fields_resolved

    # 7. Handle group memberships (conditional unique constraint)
    kept_active_groups = set(
        GroupMembership.objects.filter(
            client_file=kept, status="active",
        ).values_list("group_id", flat=True)
    )

    archived_memberships = GroupMembership.objects.filter(client_file=archived)
    memberships_transferred = 0
    memberships_deactivated = 0

    for membership in archived_memberships:
        if membership.group_id in kept_active_groups and membership.status == "active":
            # Both active in same group — deactivate archived's
            membership.status = "inactive"
            membership.client_file = kept
            membership.save(update_fields=["status", "client_file"])
            memberships_deactivated += 1
        else:
            membership.client_file = kept
            membership.save(update_fields=["client_file"])
            memberships_transferred += 1

    summary["group_memberships_transferred"] = memberships_transferred
    summary["group_memberships_deactivated"] = memberships_deactivated

    # 8. Anonymise archived client
    archived._first_name_encrypted = b""
    archived._middle_name_encrypted = b""
    archived._last_name_encrypted = b""
    archived._birth_date_encrypted = b""
    archived._phone_encrypted = b""
    archived.status = "discharged"
    archived.is_anonymised = True
    archived.status_reason = f"Merged into Client #{kept.pk}"
    archived.record_id = f"MERGED-{kept.pk}"
    archived.save()

    # Also blank custom fields on archived (all were either transferred or resolved)
    ClientDetailValue.objects.filter(client_file=archived).delete()

    # 9. Create ClientMerge audit record (main database)
    merge_record = ClientMerge.objects.create(
        kept_client=kept,
        archived_client=archived,
        kept_client_pk=kept.pk,
        archived_client_pk=archived.pk,
        kept_record_id=kept.record_id or "",
        archived_record_id=f"MERGED-{kept.pk}",
        merged_by=user,
        merged_by_display=user.get_display_name() if hasattr(user, "get_display_name") else str(user),
        transfer_summary=summary,
        pii_choices=pii_choices,
        field_conflict_resolutions=field_resolutions,
    )

    # 10. Write to AuditLog (audit database)
    _log_merge_audit(user, kept, archived, summary, ip_address)

    logger.info(
        "Merged Client #%d into Client #%d by %s — %s",
        archived.pk, kept.pk, user, summary,
    )

    return merge_record


def _log_merge_audit(user, kept, archived, summary, ip_address):
    """Write merge audit entry to the separate audit database."""
    from apps.audit.models import AuditLog

    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=user.pk if user else None,
        user_display=user.get_display_name() if hasattr(user, "get_display_name") else str(user),
        ip_address=ip_address or "",
        action="update",
        resource_type="client_merge",
        resource_id=kept.pk,
        is_demo_context=getattr(user, "is_demo", False) if user else False,
        metadata={
            "archived_client_pk": archived.pk,
            "kept_client_pk": kept.pk,
            "transfer_summary": summary,
        },
    )
