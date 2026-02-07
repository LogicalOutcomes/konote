"""Utility functions for registration processing."""
import hashlib

from django.utils import timezone

from apps.clients.models import (
    ClientFile,
    ClientDetailValue,
    ClientProgramEnrolment,
    CustomFieldDefinition,
)


def approve_submission(submission, reviewed_by=None):
    """
    Approve a submission: create ClientFile, enrol in program, update status.

    Args:
        submission: RegistrationSubmission instance
        reviewed_by: User who approved (None for auto-approve)

    Returns:
        ClientFile instance
    """
    # Create the client file with name from submission
    client = ClientFile()
    client.first_name = submission.first_name
    client.last_name = submission.last_name
    # Preferred name is stored in field_values (not an encrypted model field on submission)
    preferred_name = (submission.field_values or {}).get("preferred_name", "")
    if preferred_name:
        client.preferred_name = preferred_name
    client.status = "active"
    client.consent_given_at = submission.submitted_at
    client.consent_type = "registration_form"
    client.save()

    # Copy custom field values to ClientDetailValues
    if submission.field_values:
        for field_pk_str, value in submission.field_values.items():
            if field_pk_str == "preferred_name":
                continue  # Already handled above
            try:
                field_pk = int(field_pk_str)
                field_def = CustomFieldDefinition.objects.get(pk=field_pk)
                cdv = ClientDetailValue(client_file=client, field_def=field_def)
                cdv.set_value(str(value) if value is not None else "")
                cdv.save()
            except (ValueError, CustomFieldDefinition.DoesNotExist):
                # Skip invalid field references
                continue

    # Create program enrolment
    ClientProgramEnrolment.objects.create(
        client_file=client,
        program=submission.registration_link.program,
        status="enrolled",
    )

    # Update submission status
    submission.status = "approved"
    submission.client_file = client
    submission.reviewed_by = reviewed_by
    submission.reviewed_at = timezone.now()
    submission.save()

    return client


def find_duplicate_clients(submission):
    """
    Find existing clients that might match this submission.

    Returns list of potential matches with confidence:
    [{"client": ClientFile, "match_type": "email_exact", "confidence": "high"}, ...]

    Note: Due to encryption, name matching requires loading and decrypting
    client names in Python. This is acceptable for agencies with up to ~2,000 clients.
    """
    matches = []
    seen_client_ids = set()

    # 1. Email exact match (high confidence)
    # Compare submission email_hash with stored client email hashes
    if submission.email_hash:
        # Find clients with matching email hash in their custom fields
        # Email fields are typically stored in ClientDetailValue
        email_field_defs = CustomFieldDefinition.objects.filter(
            name__icontains="email", status="active"
        )

        for cdv in ClientDetailValue.objects.filter(field_def__in=email_field_defs):
            stored_email = cdv.get_value()
            if stored_email:
                stored_hash = hashlib.sha256(
                    stored_email.lower().strip().encode()
                ).hexdigest()
                if stored_hash == submission.email_hash:
                    if cdv.client_file_id not in seen_client_ids:
                        matches.append({
                            "client": cdv.client_file,
                            "match_type": "email_exact",
                            "confidence": "high",
                        })
                        seen_client_ids.add(cdv.client_file_id)

    # 2. Name match (medium confidence)
    # Load active clients and compare decrypted names
    submission_first = (submission.first_name or "").lower().strip()
    submission_last = (submission.last_name or "").lower().strip()

    if submission_first and submission_last:
        # Get clients in the same program (more likely to be duplicates)
        program = submission.registration_link.program
        enrolled_client_ids = ClientProgramEnrolment.objects.filter(
            program=program
        ).values_list("client_file_id", flat=True)

        for client in ClientFile.objects.filter(
            pk__in=enrolled_client_ids, status__in=["active", "inactive"]
        ):
            if client.pk in seen_client_ids:
                continue

            client_first = (client.first_name or "").lower().strip()
            client_last = (client.last_name or "").lower().strip()

            # Exact name match
            if client_first == submission_first and client_last == submission_last:
                matches.append({
                    "client": client,
                    "match_type": "name_exact",
                    "confidence": "medium",
                })
                seen_client_ids.add(client.pk)

    # Sort by confidence (high first)
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    matches.sort(key=lambda m: confidence_order.get(m["confidence"], 99))

    return matches


def reject_submission(submission, reviewed_by, notes=""):
    """
    Reject a submission.

    Args:
        submission: RegistrationSubmission instance
        reviewed_by: User who rejected
        notes: Optional rejection notes
    """
    submission.status = "rejected"
    submission.reviewed_by = reviewed_by
    submission.reviewed_at = timezone.now()
    submission.review_notes = notes
    submission.save()


def waitlist_submission(submission, reviewed_by, notes=""):
    """
    Move a submission to the waitlist.

    Args:
        submission: RegistrationSubmission instance
        reviewed_by: User who waitlisted
        notes: Optional notes
    """
    submission.status = "waitlist"
    submission.reviewed_by = reviewed_by
    submission.reviewed_at = timezone.now()
    submission.review_notes = notes
    submission.save()


def merge_with_existing(submission, existing_client, reviewed_by):
    """
    Instead of creating a new client, enrol an existing client in the program.

    Args:
        submission: RegistrationSubmission instance
        existing_client: ClientFile to enrol
        reviewed_by: User who approved the merge

    Returns:
        ClientFile instance (the existing client)
    """
    program = submission.registration_link.program

    # Check if already enrolled
    enrolment, created = ClientProgramEnrolment.objects.get_or_create(
        client_file=existing_client,
        program=program,
        defaults={"status": "enrolled"}
    )

    # If previously unenrolled, re-enrol
    if not created and enrolment.status == "unenrolled":
        enrolment.status = "enrolled"
        enrolment.unenrolled_at = None
        enrolment.save()

    # Update submission
    submission.status = "approved"
    submission.client_file = existing_client
    submission.reviewed_by = reviewed_by
    submission.reviewed_at = timezone.now()
    submission.review_notes = f"Merged with existing client #{existing_client.pk}"
    submission.save()

    return existing_client
