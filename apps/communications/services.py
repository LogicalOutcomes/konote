"""Communication services — business logic for sending messages.

Views call these functions; they handle consent checking, channel routing,
sending, and logging. Docstrings explain business rules (the "why") for
AI-assisted maintainers.
"""
import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.communications.models import Communication

logger = logging.getLogger(__name__)


# Plain-language error translations for Twilio error codes.
# Staff have no IT department — errors must be self-explanatory.
PLAIN_LANGUAGE_ERRORS = {
    "TwilioRestException": "Text messaging service is temporarily unavailable",
    "21211": "This phone number doesn't appear to be valid",
    "21614": "This phone number can't receive text messages",
    "21610": "This number has opted out of text messages",
    "30003": "The phone may be turned off or out of service",
    "30005": "Unknown phone number",
    "30006": "Phone number can't be reached — it may no longer be in service",
}


def check_consent(client_file, channel):
    """Check consent including implied consent 2-year expiry.

    CASL requires express or implied consent. Implied consent
    (e.g. existing service relationship) expires after 2 years
    from the date of last interaction.

    Returns:
        (ok, reason) tuple — ok is True if consent is valid.
    """
    if channel == "sms":
        if not client_file.sms_consent:
            return False, _("Client has not consented to text reminders")
        if not client_file.has_phone:
            return False, _("No phone number on file")
    elif channel == "email":
        if not client_file.email_consent:
            return False, _("Client has not consented to email")
        if not client_file.has_email:
            return False, _("No email address on file")

    # Check implied consent expiry (CASL: 2 years)
    if getattr(client_file, "consent_type", "") == "implied":
        consent_date = (
            client_file.sms_consent_date if channel == "sms"
            else client_file.email_consent_date
        )
        if consent_date and consent_date < date.today() - timedelta(days=730):
            return False, _("Consent expired — please re-confirm with client")

    return True, "OK"


def send_sms(phone_number, message_body):
    """Send an SMS via Twilio. Returns (success, sid_or_error).

    Business rules:
    - SMS must contain no PII — org name may be sensitive
    - 160 chars per segment for cost control
    - CASL opt-out instruction should be in the message
    """
    if not getattr(settings, "SMS_ENABLED", False):
        return False, _("SMS is not configured")

    try:
        from twilio.rest import Client as TwilioClient

        client = TwilioClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        message = client.messages.create(
            body=message_body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=phone_number,
        )
        return True, message.sid
    except ImportError:
        logger.error("twilio package not installed")
        return False, _("SMS service not available — twilio package not installed")
    except Exception as e:
        plain_error = translate_error(e)
        logger.warning("SMS send failed to %s: %s", phone_number[-4:], str(e))
        return False, plain_error


def send_email_message(to_email, subject, body_text, body_html=None):
    """Send an email using Django's configured SMTP backend.

    Returns (success, error_message_or_none).
    """
    try:
        send_mail(
            subject=subject,
            message=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=body_html,
            fail_silently=False,
        )
        return True, None
    except Exception as e:
        logger.warning("Email send failed to %s: %s", to_email, str(e))
        return False, _("Email could not be delivered — check the email address with the client")


def send_reminder(meeting, logged_by=None):
    """Send an appointment reminder for a meeting.

    Checks consent, selects channel based on client preference,
    renders template in client's preferred language, sends, and
    records the result on both the Communication log and the
    Meeting.reminder_status field (so staff see it on the meeting card).

    Business rules:
    - CASL requires consent before sending (even though transactional
      messages may be exempt, we enforce as best practice)
    - Implied consent expires after 2 years (CASL standard)
    - SMS must contain no PII — org name may be sensitive
    - Contact info is read at send time, never cached

    Returns:
        (success, reason) tuple
    """
    client_file = meeting.event.client_file
    channel = getattr(client_file, "preferred_contact_method", "none")

    if channel == "none":
        _record_reminder_status(meeting, "no_consent", _("Client has not consented to reminders"))
        return False, "No consent"

    reason = ""

    if channel in ("sms", "both"):
        ok, msg = _send_sms_reminder(meeting, client_file, logged_by)
        if ok:
            return True, "Sent"
        reason = msg

    if channel in ("email", "both"):
        ok, msg = _send_email_reminder(meeting, client_file, logged_by)
        if ok:
            return True, "Sent"
        reason = msg

    if reason:
        _record_reminder_status(meeting, "failed", reason)

    return False, reason


def _send_sms_reminder(meeting, client_file, logged_by=None):
    """Send SMS reminder for a meeting. Internal helper.

    Returns (success, reason).
    """
    ok, reason = check_consent(client_file, "sms")
    if not ok:
        status = "no_phone" if "phone" in reason.lower() else "no_consent"
        _record_reminder_status(meeting, status, reason)
        return False, reason

    # Get phone number at send time (never cached)
    phone = getattr(client_file, "phone", None)
    if not phone:
        _record_reminder_status(meeting, "no_phone", _("No phone number on file"))
        return False, _("No phone number on file")

    # Build message in client's preferred language
    lang = getattr(client_file, "preferred_language", "en")
    time_str = meeting.event.start_timestamp.strftime("%I:%M %p").lstrip("0")
    date_str = meeting.event.start_timestamp.strftime("%B %d")

    if lang == "fr":
        body = (
            f"Rappel : Vous avez un rendez-vous le {date_str} \u00e0 {time_str}. "
            f"R\u00e9pondez STOP pour vous d\u00e9sinscrire."
        )
    else:
        body = (
            f"Reminder: You have an appointment on {date_str} at {time_str}. "
            f"Reply STOP to opt out."
        )

    success, sid_or_error = send_sms(phone, body)

    # Log to Communication model
    comm = Communication.objects.create(
        client_file=client_file,
        direction="outbound",
        channel="sms",
        method="system_sent",
        subject="Appointment reminder",
        delivery_status="sent" if success else "failed",
        delivery_status_display="" if success else sid_or_error,
        external_id=sid_or_error if success else "",
        logged_by=logged_by,
        author_program=getattr(meeting.event, "author_program", None),
    )
    if success:
        comm.content = body
        comm.save()

    if success:
        _record_reminder_status(meeting, "sent", _("Reminder sent by text"))
    else:
        _record_reminder_status(meeting, "failed", sid_or_error)

    return success, sid_or_error if not success else "Sent"


def _send_email_reminder(meeting, client_file, logged_by=None):
    """Send email reminder for a meeting. Internal helper.

    Returns (success, reason).
    """
    ok, reason = check_consent(client_file, "email")
    if not ok:
        _record_reminder_status(meeting, "no_consent", reason)
        return False, reason

    email = getattr(client_file, "email", None)
    if not email:
        _record_reminder_status(meeting, "blocked", _("No email address on file"))
        return False, _("No email address on file")

    # Build message in client's preferred language
    lang = getattr(client_file, "preferred_language", "en")
    time_str = meeting.event.start_timestamp.strftime("%I:%M %p").lstrip("0")
    date_str = meeting.event.start_timestamp.strftime("%B %d, %Y")

    if lang == "fr":
        subject = "Rappel de rendez-vous"
        body = (
            f"Rappel : Vous avez un rendez-vous le {date_str} \u00e0 {time_str}.\n\n"
            f"Si vous devez reporter, veuillez nous contacter."
        )
    else:
        subject = "Appointment Reminder"
        body = (
            f"Reminder: You have an appointment on {date_str} at {time_str}.\n\n"
            f"If you need to reschedule, please contact us."
        )

    success, error = send_email_message(email, subject, body)

    # Log to Communication model
    Communication.objects.create(
        client_file=client_file,
        direction="outbound",
        channel="email",
        method="system_sent",
        subject=subject,
        delivery_status="sent" if success else "failed",
        delivery_status_display="" if success else (error or ""),
        logged_by=logged_by,
        author_program=getattr(meeting.event, "author_program", None),
    )

    if success:
        _record_reminder_status(meeting, "sent", _("Reminder sent by email"))
    else:
        _record_reminder_status(meeting, "failed", error or _("Email delivery failed"))

    return success, error


def _record_reminder_status(meeting, status, reason):
    """Update the meeting card's reminder indicator.

    This is what staff see. Use plain language.
    CRITICAL: Only set reminder_sent=True on actual success.
    Do NOT mark as sent on failure — the cron job must retry.
    """
    meeting.reminder_status = status
    meeting.reminder_status_reason = reason
    if status == "sent":
        meeting.reminder_sent = True
    meeting.save(update_fields=["reminder_status", "reminder_status_reason", "reminder_sent"])


def translate_error(error):
    """Turn technical errors into language a case worker understands."""
    error_str = str(error)
    for code, message in PLAIN_LANGUAGE_ERRORS.items():
        if code in error_str:
            return message
    return _("Text could not be delivered — try confirming the phone number with the client")


def log_communication(client_file, direction, channel, logged_by, content="", subject="", author_program=None):
    """Record a manual communication log entry.

    Used by the quick-log buttons and full communication log form.
    Returns the created Communication object.
    """
    comm = Communication.objects.create(
        client_file=client_file,
        direction=direction,
        channel=channel,
        method="manual_log",
        subject=subject,
        delivery_status="sent",
        logged_by=logged_by,
        author_program=author_program,
    )
    if content:
        comm.content = content
        comm.save()

    # Audit log
    from apps.audit.models import AuditLog
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=logged_by.pk if logged_by else None,
        user_display=getattr(logged_by, "display_name", str(logged_by)) if logged_by else "System",
        action="create",
        resource_type="communication",
        resource_id=comm.pk,
        is_demo_context=getattr(logged_by, "is_demo", False) if logged_by else False,
        metadata={
            "client_file_id": client_file.pk,
            "channel": channel,
            "direction": direction,
        },
    )

    return comm
