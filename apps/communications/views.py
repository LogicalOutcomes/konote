"""Views for communication logging, send previews, and unsubscribe."""
import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.clients.models import ClientFile
from apps.events.models import Event, Meeting
from apps.programs.access import get_author_program, get_client_or_403, get_program_from_client

from apps.auth_app.decorators import requires_permission

from .forms import CommunicationLogForm, PersonalNoteForm, QuickLogForm, SendEmailForm
from .models import Communication


# ---------------------------------------------------------------------------
# Helper for @requires_permission decorator
# ---------------------------------------------------------------------------

_get_program_from_client = get_program_from_client


# ---------------------------------------------------------------------------
# Quick-log — the 2-click workflow
# ---------------------------------------------------------------------------

@login_required
def quick_log(request, client_id):
    """Deprecated: manual contact logging has moved to Quick Notes."""
    messages.info(request, _("Contact logging has moved to Quick Notes."))
    return redirect("events:event_list", client_id=client_id)


@login_required
def communication_log(request, client_id):
    """Deprecated: manual contact logging has moved to Quick Notes."""
    messages.info(request, _("Contact logging has moved to Quick Notes."))
    return redirect("notes:quick_note_create", client_id=client_id)


# ---------------------------------------------------------------------------
# Compose Email — staff sends a free-form email to a participant
# ---------------------------------------------------------------------------

@login_required
@requires_permission("communication.log", _get_program_from_client)
def compose_email(request, client_id):
    """Compose and send a free-form email to a participant.

    GET: Show compose form (or explanation if email can't be sent).
    POST action=preview: Show preview of the message.
    POST action=send: Send the email and log it.
    """
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(_("You do not have access to this client."))

    from .services import can_send, send_staff_email

    allowed, reason = can_send(client, "email")

    # Mask email for display
    masked_email = ""
    if client.has_email:
        email_addr = client.email
        if email_addr and "@" in email_addr:
            local, domain = email_addr.split("@", 1)
            masked_email = f"{local[:2]}***@{domain}"
        elif email_addr:
            masked_email = "***"

    action = request.POST.get("action", "")

    if request.method == "POST" and action == "send":
        form = SendEmailForm(request.POST)
        if form.is_valid() and allowed:
            success, error = send_staff_email(
                client_file=client,
                subject=form.cleaned_data["subject"],
                body_text=form.cleaned_data["message"],
                logged_by=request.user,
                author_program=get_author_program(request.user, client),
                request=request,
            )
            if success:
                messages.success(request, _("Email sent successfully."))
                return redirect("clients:client_detail", client_id=client.pk)
            else:
                messages.error(request, error)

    elif request.method == "POST" and action == "preview":
        form = SendEmailForm(request.POST)
        if form.is_valid():
            return render(request, "communications/compose_email.html", {
                "client": client,
                "form": form,
                "allowed": allowed,
                "reason": reason,
                "masked_email": masked_email,
                "preview": True,
            })
    else:
        form = SendEmailForm()

    return render(request, "communications/compose_email.html", {
        "client": client,
        "form": form,
        "allowed": allowed,
        "reason": reason,
        "masked_email": masked_email,
        "preview": False,
    })


# ---------------------------------------------------------------------------
# Send Reminder Preview — staff previews message before sending
# ---------------------------------------------------------------------------

@login_required
@requires_permission("communication.log", _get_program_from_client)
def send_reminder_preview(request, client_id, event_id):
    """Preview a reminder before sending.

    GET: Returns the preview partial showing the exact message text,
         channel, and masked recipient info.
    POST: Sends the reminder and returns the updated meeting status partial.
    """
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(_("You do not have access to this client."))

    event = get_object_or_404(Event, pk=event_id, client_file=client)
    meeting = get_object_or_404(Meeting, event=event)

    channel = getattr(client, "preferred_contact_method", "none")

    from .services import can_send, render_message_template, send_reminder

    # Determine the actual channel to check
    check_channel = "sms" if channel in ("sms", "both") else "email"
    allowed, reason = can_send(client, check_channel)

    # If primary channel blocked but "both", try the other
    if not allowed and channel == "both":
        alt_channel = "email" if check_channel == "sms" else "sms"
        allowed, reason = can_send(client, alt_channel)
        if allowed:
            check_channel = alt_channel

    if request.method == "POST":
        send_succeeded = False
        if not allowed:
            messages.error(request, reason)
        else:
            note_form = PersonalNoteForm(request.POST)
            if note_form.is_valid():
                personal_note = note_form.cleaned_data["personal_note"]
            else:
                personal_note = ""
                messages.warning(request, _("Your personal note was too long and was not included."))
            success, send_reason = send_reminder(meeting, logged_by=request.user, personal_note=personal_note)
            if success:
                messages.success(request, _("Reminder sent."))
                send_succeeded = True
            else:
                messages.error(request, send_reason)

        # Return updated meeting status partial
        meeting.refresh_from_db()
        response = render(request, "events/_meeting_status.html", {"meeting": meeting})
        # UXP2: trigger success toast so HTMX shows a confirmation (WCAG 4.1.3)
        if send_succeeded:
            response["HX-Trigger"] = json.dumps({"showSuccess": str(_("Reminder sent."))})
        return response

    # GET: show preview
    preview_text = ""
    if allowed:
        template_key = "reminder_sms" if check_channel == "sms" else "reminder_email_body"
        preview_text = render_message_template(template_key, client, meeting)

    # Mask recipient info for preview
    masked_recipient = ""
    if check_channel == "sms":
        phone = getattr(client, "phone", "")
        if phone and len(phone) >= 4:
            masked_recipient = f"***-**{phone[-2:]}"
        elif phone:
            masked_recipient = "***"
    elif check_channel == "email":
        email_addr = getattr(client, "email", "")
        if email_addr and "@" in email_addr:
            local, domain = email_addr.split("@", 1)
            masked_recipient = f"{local[:2]}***@{domain}"
        elif email_addr:
            masked_recipient = "***"

    return render(request, "communications/_send_reminder_preview.html", {
        "meeting": meeting,
        "client": client,
        "channel": check_channel,
        "allowed": allowed,
        "reason": reason,
        "preview_text": preview_text,
        "masked_recipient": masked_recipient,
    })


# ---------------------------------------------------------------------------
# Email Unsubscribe — public endpoint, no login required
# ---------------------------------------------------------------------------

def email_unsubscribe(request, token):
    """Handle email unsubscribe links.

    Token is signed with django.core.signing — contains client_file_id
    and channel. Expires after 60 days. No login required.
    """
    from .services import UNSUBSCRIBE_TOKEN_MAX_AGE
    try:
        data = signing.loads(token, salt="unsubscribe", max_age=UNSUBSCRIBE_TOKEN_MAX_AGE)
    except signing.BadSignature:
        return render(request, "communications/unsubscribe.html", {
            "error": _("This unsubscribe link has expired or is invalid. "
                       "Please contact the organisation directly to update your preferences."),
        })

    client_file_id = data.get("client_id")
    channel = data.get("channel", "email")

    try:
        client = ClientFile.objects.get(pk=client_file_id)
    except ClientFile.DoesNotExist:
        return render(request, "communications/unsubscribe.html", {
            "error": _("This unsubscribe link is no longer valid."),
        })

    if request.method == "POST":
        if channel == "email":
            client.email_consent = False
            client.email_consent_withdrawn_date = date.today()
        elif channel == "sms":
            client.sms_consent = False
            client.sms_consent_withdrawn_date = date.today()
        client.save()

        # Audit log
        from apps.audit.models import AuditLog
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=None,
            user_display="Self-service unsubscribe",
            action="update",
            resource_type="clients",
            resource_id=client.pk,
            metadata={"channel": channel, "method": "email_unsubscribe_link"},
        )

        return render(request, "communications/unsubscribe.html", {
            "success": True,
            "channel": channel,
        })

    channel_display = _("email") if channel == "email" else _("text messages")
    return render(request, "communications/unsubscribe.html", {
        "confirm": True,
        "channel": channel,
        "channel_display": channel_display,
    })
