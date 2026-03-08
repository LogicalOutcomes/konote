"""Audit logging for registration events.

Shared by both public registration views (no authenticated user) and
admin review views (authenticated staff/PM).
"""
from django.utils import timezone

from apps.audit.models import AuditLog
from konote.utils import get_client_ip


def log_registration_event(submission, action, *, request=None, old_status=None,
                           metadata=None, new_values=None):
    """Write an immutable audit row for a registration event.

    Args:
        submission: RegistrationSubmission instance.
        action: Audit action string (e.g. "create", "update").
        request: Django request (optional). When provided, records user and IP.
        old_status: Previous status value for review actions.
        metadata: Dict of non-PII contextual data.
        new_values: Dict of new field values to record.
    """
    if request and hasattr(request, "user") and request.user.is_authenticated:
        user_id = request.user.pk
        user_display = str(request.user)
        is_demo = getattr(request.user, "is_demo", False)
    else:
        user_id = None
        user_display = "Public registration"
        is_demo = False

    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=user_id,
        user_display=user_display,
        ip_address=get_client_ip(request) if request else None,
        action=action,
        resource_type="registration",
        resource_id=submission.pk,
        program_id=submission.registration_link.program_id,
        old_values={"status": old_status} if old_status else {},
        new_values=new_values or {},
        metadata=metadata or {},
        is_demo_context=is_demo,
    )
