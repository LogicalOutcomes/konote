"""Communication services — business logic for sending messages.

Views call these functions; they handle consent checking, channel routing,
sending, and logging. Docstrings explain business rules (the "why") for
AI-assisted maintainers.
"""
import logging
from datetime import date, timedelta

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.communications.models import Communication, SystemHealthCheck

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

# Default message templates — used when admin hasn't configured custom templates.
# Placeholders: {date}, {time}, {org_phone}
DEFAULT_TEMPLATES = {
    "reminder_sms_en": (
        "Reminder: You have an appointment on {date} at {time}. "
        "Reply STOP to opt out."
    ),
    "reminder_sms_fr": (
        "Rappel : Vous avez un rendez-vous le {date} \u00e0 {time}. "
        "R\u00e9pondez STOP pour vous d\u00e9sinscrire."
    ),
    "reminder_email_subject_en": "Appointment Reminder",
    "reminder_email_subject_fr": "Rappel de rendez-vous",
    "reminder_email_body_en": (
        "Reminder: You have an appointment on {date} at {time}.\n\n"
        "If you need to reschedule, please contact us."
    ),
    "reminder_email_body_fr": (
        "Rappel : Vous avez un rendez-vous le {date} \u00e0 {time}.\n\n"
        "Si vous devez reporter, veuillez nous contacter."
    ),
}


# ---------------------------------------------------------------------------
# Pre-send checks
# ---------------------------------------------------------------------------

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


def can_send(client_file, channel):
    """Check all prerequisites before sending a message.

    Returns (allowed: bool, reason: str).
    Checks are ordered from broadest restriction to narrowest:
    1. Safety-First mode — blocks everything
    2. Messaging profile — record_keeping blocks all outbound
    3. Channel capability — FeatureToggle must be enabled
    4. Client consent — CASL compliance
    5. Consent expiry — implied consent 2-year rule
    6. Contact info exists
    """
    from apps.admin_settings.models import FeatureToggle, InstanceSetting

    # 1. Safety-First mode
    if InstanceSetting.get("safety_first_mode", "false") == "true":
        return False, _("Safety-First mode is enabled — no outbound messages")

    # 2. Messaging profile
    profile = InstanceSetting.get("messaging_profile", "record_keeping")
    if profile == "record_keeping":
        return False, _("Messaging is set to record-keeping only")

    # 3. Channel capability
    flags = FeatureToggle.get_all_flags()
    if channel == "sms" and not flags.get("messaging_sms", False):
        return False, _("Text messaging is not set up")
    if channel == "email" and not flags.get("messaging_email", False):
        return False, _("Email is not set up")

    # 4 & 5. Consent + expiry (reuse existing check_consent)
    ok, reason = check_consent(client_file, channel)
    if not ok:
        return False, reason

    # 6. Contact info (double-check — check_consent checks has_phone/has_email
    # but only when consent is True, so this catches edge cases)
    if channel == "sms" and not client_file.has_phone:
        return False, _("No phone number on file")
    if channel == "email" and not client_file.has_email:
        return False, _("No email address on file")

    return True, "OK"


# ---------------------------------------------------------------------------
# Message template rendering
# ---------------------------------------------------------------------------

def render_message_template(template_key, client_file, meeting, personal_note=""):
    """Render a message template with meeting/client context.

    Uses admin-configured template from InstanceSetting, falling back
    to DEFAULT_TEMPLATES. Selects language based on client preference.
    Substitutes {date}, {time}, {org_phone} placeholders.

    Args:
        template_key: Base key like "reminder_sms" or "reminder_email_body"
        client_file: The client receiving the message
        meeting: The meeting being reminded about
        personal_note: Optional staff note appended to the message
    """
    from apps.admin_settings.models import InstanceSetting

    lang = getattr(client_file, "preferred_language", "en")
    key = f"{template_key}_{lang}"
    fallback_key = f"{template_key}_en"

    # Try admin-configured template, then default
    template_text = (
        InstanceSetting.get(key, "")
        or InstanceSetting.get(fallback_key, "")
        or DEFAULT_TEMPLATES.get(key, DEFAULT_TEMPLATES.get(fallback_key, ""))
    )

    time_str = meeting.event.start_timestamp.strftime("%I:%M %p").lstrip("0")
    date_str = meeting.event.start_timestamp.strftime("%B %d, %Y")

    rendered = template_text.format(
        date=date_str,
        time=time_str,
        org_phone=InstanceSetting.get("support_contact_phone", ""),
    )

    if personal_note:
        rendered += f"\n\n\u2014 {personal_note}"

    return rendered


# ---------------------------------------------------------------------------
# Unsubscribe URL generation
# ---------------------------------------------------------------------------

def generate_unsubscribe_url(client_file, channel="email"):
    """Generate a signed unsubscribe URL for email footers.

    Token expires after 60 days. Uses django.core.signing for
    tamper-proof, expiring tokens without a database lookup.
    """
    token = signing.dumps(
        {"client_id": client_file.pk, "channel": channel},
        salt="unsubscribe",
    )
    return reverse("communications:email_unsubscribe", kwargs={"token": token})


# ---------------------------------------------------------------------------
# Sending functions
# ---------------------------------------------------------------------------

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
        SystemHealthCheck.record_success("sms")
        return True, message.sid
    except ImportError:
        logger.error("twilio package not installed")
        return False, _("SMS service not available — twilio package not installed")
    except Exception as e:
        plain_error = translate_error(e)
        logger.warning("SMS send failed: %s", str(e))
        SystemHealthCheck.record_failure("sms", plain_error)
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
        SystemHealthCheck.record_success("email")
        return True, None
    except Exception as e:
        logger.warning("Email send failed to %s: %s", to_email, str(e))
        error_msg = _("Email could not be delivered — check the email address with the client")
        SystemHealthCheck.record_failure("email", str(e)[:255])
        return False, error_msg


def send_reminder(meeting, logged_by=None, personal_note=""):
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

    # Pre-check with can_send() — checks safety mode, profile, toggles, consent
    send_channel = "sms" if channel in ("sms", "both") else "email"
    allowed, block_reason = can_send(client_file, send_channel)
    if not allowed:
        # Try the other channel if "both"
        if channel == "both":
            alt_channel = "email" if send_channel == "sms" else "sms"
            allowed, block_reason = can_send(client_file, alt_channel)
            if allowed:
                send_channel = alt_channel

        if not allowed:
            status = "blocked" if "set up" in block_reason.lower() or "record-keeping" in block_reason.lower() else "no_consent"
            _record_reminder_status(meeting, status, block_reason)
            return False, block_reason

    reason = ""

    if send_channel == "sms" or (channel == "both" and send_channel != "email"):
        ok, msg = _send_sms_reminder(meeting, client_file, logged_by, personal_note)
        if ok:
            return True, "Sent"
        reason = msg

    if send_channel == "email" or (channel == "both" and not reason):
        ok, msg = _send_email_reminder(meeting, client_file, logged_by, personal_note)
        if ok:
            return True, "Sent"
        reason = msg

    if reason:
        _record_reminder_status(meeting, "failed", reason)

    return False, reason


def _send_sms_reminder(meeting, client_file, logged_by=None, personal_note=""):
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

    # Build message from configurable template
    body = render_message_template("reminder_sms", client_file, meeting, personal_note)

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


def _send_email_reminder(meeting, client_file, logged_by=None, personal_note=""):
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

    # Build message from configurable template
    lang = getattr(client_file, "preferred_language", "en")
    subject_key = f"reminder_email_subject_{lang}"
    subject = DEFAULT_TEMPLATES.get(subject_key, DEFAULT_TEMPLATES["reminder_email_subject_en"])

    # Check for admin-configured subject
    from apps.admin_settings.models import InstanceSetting
    subject = InstanceSetting.get(subject_key, "") or subject

    body = render_message_template("reminder_email_body", client_file, meeting, personal_note)

    # Append unsubscribe link for CASL compliance
    unsubscribe_url = generate_unsubscribe_url(client_file, "email")
    body += f"\n\n---\n{_('To stop receiving these messages')}: {unsubscribe_url}"

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


# ---------------------------------------------------------------------------
# System health alerts
# ---------------------------------------------------------------------------

def check_and_send_health_alert():
    """Send alert email to admin if a messaging channel has been failing 24+ hours.

    Called by the send_reminders management command after each batch.
    Only sends one alert per channel per 24h to avoid spamming.
    """
    from apps.admin_settings.models import InstanceSetting

    admin_email = InstanceSetting.get("support_email", "")
    if not admin_email:
        return

    now = timezone.now()

    for health in SystemHealthCheck.objects.filter(consecutive_failures__gte=3):
        if not health.last_failure_at:
            continue

        hours_since_failure = (now - health.last_failure_at).total_seconds() / 3600

        # Only alert for recent failures (within last 48h)
        if hours_since_failure > 48:
            continue

        # Check if we already sent an alert in the last 24h
        if health.alert_email_sent_at:
            hours_since_alert = (now - health.alert_email_sent_at).total_seconds() / 3600
            if hours_since_alert < 24:
                continue

        # Send alert
        product_name = InstanceSetting.get("product_name", "KoNote")
        channel_name = health.get_channel_display()
        send_email_message(
            to_email=admin_email,
            subject=f"{product_name} — {channel_name} reminders not working",
            body_text=(
                f"{channel_name} reminders have not been working since "
                f"{health.last_failure_at.strftime('%B %d at %I:%M %p')}. "
                f"{health.consecutive_failures} reminders could not be sent.\n\n"
                f"Last error: {health.last_failure_reason}\n\n"
                f"Please check the messaging configuration or contact your technical support person."
            ),
        )
        health.alert_email_sent_at = now
        health.save(update_fields=["alert_email_sent_at"])


# ---------------------------------------------------------------------------
# Manual communication logging
# ---------------------------------------------------------------------------

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
