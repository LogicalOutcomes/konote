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

from apps.auth_app.decorators import requires_permission, requires_permission_global

from django.db import models as db_models

from .forms import CommunicationLogForm, PersonalNoteForm, QuickLogForm, SendEmailForm, StaffMessageForm
from .models import Communication


# ---------------------------------------------------------------------------
# Helper for @requires_permission decorator
# ---------------------------------------------------------------------------

_get_program_from_client = get_program_from_client


# ---------------------------------------------------------------------------
# Quick-log — the 2-click workflow
# ---------------------------------------------------------------------------

@login_required
@requires_permission("communication.log", _get_program_from_client)
def quick_log(request, client_id):
    """Deprecated: manual contact logging has moved to Quick Notes."""
    messages.info(request, _("Contact logging has moved to Quick Notes."))
    return redirect("events:event_list", client_id=client_id)


@login_required
@requires_permission("communication.log", _get_program_from_client)
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
                return render(request, "communications/compose_email.html", {
                    "client": client,
                    "form": form,
                    "allowed": allowed,
                    "reason": reason,
                    "masked_email": masked_email,
                    "preview": True,
                })

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

    CASL compliance (S.C. 2010, c. 23, s. 6(2)(c)): this endpoint must
    always render a user-friendly page — never a raw 500.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from .services import UNSUBSCRIBE_TOKEN_MAX_AGE
    except ImportError:
        logger.exception("Failed to import UNSUBSCRIBE_TOKEN_MAX_AGE")
        return render(request, "communications/unsubscribe.html", {
            "error": _("This service is temporarily unavailable. "
                       "Please contact the organisation directly to update your preferences."),
        })

    try:
        data = signing.loads(token, salt="unsubscribe", max_age=UNSUBSCRIBE_TOKEN_MAX_AGE)
    except (signing.BadSignature, Exception) as exc:
        if not isinstance(exc, signing.BadSignature):
            logger.exception("Unexpected error validating unsubscribe token")
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


# ---------------------------------------------------------------------------
# Staff Messages — front desk leaves messages for case workers
# ---------------------------------------------------------------------------

@login_required
@requires_permission("message.leave", _get_program_from_client)
def leave_message(request, client_id):
    """Leave a message for a case worker about a participant."""
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(_("You do not have access to this client."))

    # Build staff choices for dropdown
    from apps.programs.access import get_user_program_ids
    from apps.clients.models import ClientProgramEnrolment
    from apps.programs.models import UserProgramRole

    user_program_ids = set(get_user_program_ids(request.user))
    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client, status="active"
        ).values_list("program_id", flat=True)
    )
    shared_program_ids = client_program_ids & user_program_ids

    staff_user_ids = UserProgramRole.objects.filter(
        program_id__in=shared_program_ids,
        role__in=["staff", "program_manager"],
        status="active",
    ).values_list("user_id", flat=True).distinct()

    from django.contrib.auth import get_user_model
    User = get_user_model()
    staff_users = User.objects.filter(pk__in=staff_user_ids).order_by("display_name")
    staff_choices = [(u.pk, u.display_name) for u in staff_users]

    worker_term = request.get_term("worker", "worker")
    if request.method == "POST":
        form = StaffMessageForm(request.POST, staff_choices=staff_choices, worker_term=worker_term)
        if form.is_valid():
            from .models import StaffMessage

            msg = StaffMessage()
            msg.client_file = client
            msg.content = form.cleaned_data["message"]
            msg.left_by = request.user
            msg.for_user = form.cleaned_data.get("for_user")
            msg.author_program = get_author_program(request.user, client)
            msg.is_urgent = form.cleaned_data.get("is_urgent", False)
            msg.save()

            messages.success(request, _("Message left successfully."))
            return redirect("clients:client_detail", client_id=client.pk)
    else:
        form = StaffMessageForm(staff_choices=staff_choices, worker_term=worker_term)

    from django.urls import reverse
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": "", "label": _("Leave Message")},
    ]

    return render(request, "communications/leave_message.html", {
        "client": client,
        "form": form,
        "breadcrumbs": breadcrumbs,
    })


@login_required
@requires_permission("message.view", _get_program_from_client)
def client_messages(request, client_id):
    """View messages for a specific client."""
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(_("You do not have access to this client."))

    from .models import StaffMessage

    # Show messages for this user or unassigned
    staff_messages = StaffMessage.objects.filter(
        client_file=client,
        status__in=["unread", "read"],
    ).filter(
        db_models.Q(for_user=request.user) | db_models.Q(for_user__isnull=True)
    ).select_related("left_by", "for_user")

    from django.urls import reverse
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": "", "label": _("Messages")},
    ]

    return render(request, "communications/client_messages.html", {
        "client": client,
        "staff_messages": staff_messages,
        "breadcrumbs": breadcrumbs,
    })


@login_required
@requires_permission("message.view", _get_program_from_client)
def mark_message_read(request, client_id, message_id):
    """Mark a message as read (HTMX POST)."""
    if request.method != "POST":
        return redirect("communications:client_messages", client_id=client_id)

    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(_("You do not have access to this client."))

    from .models import StaffMessage

    msg = get_object_or_404(StaffMessage, pk=message_id, client_file=client)

    if msg.for_user == request.user or msg.for_user is None:
        msg.status = "read"
        msg.read_at = timezone.now()
        msg.save(update_fields=["status", "read_at"])

    if request.headers.get("HX-Request"):
        # Use the correct card partial based on which page initiated the request
        current_url = request.headers.get("HX-Current-URL", "")
        if "my-messages" in current_url:
            template = "communications/_my_message_card.html"
        else:
            template = "communications/_message_card.html"
        return render(request, template, {
            "msg": msg,
            "client": client,
        })

    return redirect("communications:client_messages", client_id=client.pk)


@login_required
@requires_permission_global("message.view")
def my_messages(request):
    """Dashboard showing all unread messages for the current user."""
    from .models import StaffMessage
    from apps.programs.access import get_user_program_ids
    from apps.clients.models import ClientProgramEnrolment

    user_program_ids = set(get_user_program_ids(request.user))
    accessible_client_ids = set(
        ClientProgramEnrolment.objects.filter(
            program_id__in=user_program_ids,
            status="active",
        ).values_list("client_file_id", flat=True)
    )

    user_messages_qs = StaffMessage.objects.filter(
        client_file_id__in=accessible_client_ids,
    ).filter(
        db_models.Q(for_user=request.user) | db_models.Q(for_user__isnull=True)
    )

    staff_messages = user_messages_qs.filter(
        status="unread",
    ).select_related("left_by", "for_user", "client_file").order_by("-is_urgent", "-created_at")

    return render(request, "communications/my_messages.html", {
        "staff_messages": staff_messages,
        "has_any_messages": user_messages_qs.exists(),
        "nav_active": "messages",
    })
