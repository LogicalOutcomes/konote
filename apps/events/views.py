"""Views for events and alerts — admin event types + client-scoped events/alerts."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.auth_app.constants import ROLE_RANK
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.access import (
    build_program_display_context,
    get_author_program,
    get_client_or_403,
    get_user_program_ids,
)
from apps.auth_app.decorators import admin_required, minimum_role, programme_role_required, requires_permission
from apps.programs.models import Program, UserProgramRole

from .forms import AlertCancelForm, AlertForm, EventForm, EventTypeForm
from .models import Alert, Event, EventType


# Use shared access helpers from apps.programs.access
_get_client_or_403 = get_client_or_403
_get_author_program = get_author_program


# ---------------------------------------------------------------------------
# Helper functions for programme_role_required decorator
# ---------------------------------------------------------------------------


def _get_programme_from_client(request, client_id, **kwargs):
    """Find the shared programme where user has the highest role."""
    client = get_object_or_404(ClientFile, pk=client_id)

    user_roles = UserProgramRole.objects.filter(
        user=request.user, status="active"
    ).values_list("program_id", "role")

    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client, status="enrolled"
        ).values_list("program_id", flat=True)
    )

    best_program_id = None
    best_rank = -1
    for program_id, role in user_roles:
        if program_id in client_program_ids:
            rank = ROLE_RANK.get(role, 0)
            if rank > best_rank:
                best_rank = rank
                best_program_id = program_id

    if best_program_id is None:
        raise ValueError(f"User has no shared programme with client {client_id}")

    return Program.objects.get(pk=best_program_id)


def _get_programme_from_alert(request, alert_id, **kwargs):
    """Extract programme via alert → client."""
    alert = get_object_or_404(Alert, pk=alert_id)
    return _get_programme_from_client(request, alert.client_file_id)


# ---------------------------------------------------------------------------
# Event Type Admin (admin-only)
# ---------------------------------------------------------------------------

@login_required
@admin_required
def event_type_list(request):
    """List all event types (admin only)."""
    event_types = EventType.objects.all()
    return render(request, "events/event_type_list.html", {"event_types": event_types})


@login_required
@admin_required
def event_type_create(request):
    """Create a new event type (admin only)."""
    if request.method == "POST":
        form = EventTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Event type created."))
            return redirect("events:event_type_list")
    else:
        form = EventTypeForm()
    return render(request, "events/event_type_form.html", {"form": form, "editing": False})


@login_required
@admin_required
def event_type_edit(request, type_id):
    """Edit an event type (admin only)."""
    event_type = get_object_or_404(EventType, pk=type_id)
    if request.method == "POST":
        form = EventTypeForm(request.POST, instance=event_type)
        if form.is_valid():
            form.save()
            messages.success(request, _("Event type updated."))
            return redirect("events:event_type_list")
    else:
        form = EventTypeForm(instance=event_type)
    return render(request, "events/event_type_form.html", {
        "form": form,
        "editing": True,
        "event_type": event_type,
    })


# ---------------------------------------------------------------------------
# Event CRUD (client-scoped)
# ---------------------------------------------------------------------------

@login_required
@requires_permission("event.view", _get_programme_from_client)
def event_list(request, client_id):
    """Combined timeline: events + notes for a client, sorted chronologically."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # Get user's accessible programs (respects CONF9 context switcher)
    active_ids = getattr(request, "active_program_ids", None)
    user_program_ids = get_user_program_ids(request.user, active_ids)
    program_ctx = build_program_display_context(request.user, active_ids)

    # Filter events, alerts, and notes by user's accessible programs
    program_q = Q(author_program_id__in=user_program_ids) | Q(author_program__isnull=True)

    events = Event.objects.filter(client_file=client).filter(program_q).select_related("event_type", "author_program")
    alerts = Alert.objects.filter(client_file=client).filter(program_q).select_related("author_program")

    # Build combined timeline entries
    from apps.notes.models import ProgressNote
    notes = ProgressNote.objects.filter(client_file=client).filter(program_q).select_related("author", "author_program")

    timeline = []
    for event in events:
        timeline.append({
            "type": "event",
            "date": event.start_timestamp,
            "obj": event,
        })
    for note in notes:
        timeline.append({
            "type": "note",
            "date": note.effective_date,
            "obj": note,
        })
    # Sort newest first
    timeline.sort(key=lambda x: x["date"], reverse=True)

    context = {
        "client": client,
        "events": events,
        "alerts": alerts,
        "timeline": timeline,
        "active_tab": "events",
        "show_program_ui": program_ctx["show_program_ui"],
    }
    if request.headers.get("HX-Request"):
        return render(request, "events/_tab_events.html", context)
    return render(request, "events/event_list.html", context)


@login_required
@requires_permission("event.create", _get_programme_from_client)
def event_create(request, client_id):
    """Create an event for a client."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.client_file = client
            event.author_program = _get_author_program(request.user, client)
            event.save()
            messages.success(request, _("Event created."))
            return redirect("events:event_list", client_id=client.pk)
    else:
        form = EventForm()
    return render(request, "events/event_form.html", {
        "form": form,
        "client": client,
    })


# ---------------------------------------------------------------------------
# Alert CRUD (client-scoped)
# ---------------------------------------------------------------------------

@login_required
@requires_permission("alert.create", _get_programme_from_client)
def alert_create(request, client_id):
    """Create an alert for a client."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")
    if request.method == "POST":
        form = AlertForm(request.POST)
        if form.is_valid():
            Alert.objects.create(
                client_file=client,
                content=form.cleaned_data["content"],
                author=request.user,
                author_program=_get_author_program(request.user, client),
            )
            messages.success(request, _("Alert created."))
            return redirect("events:event_list", client_id=client.pk)
    else:
        form = AlertForm()
    return render(request, "events/alert_form.html", {
        "form": form,
        "client": client,
    })


@login_required
@programme_role_required("staff", _get_programme_from_alert)
def alert_cancel(request, alert_id):
    """Cancel an alert with a reason (never delete). Only author or admin can cancel."""
    alert = get_object_or_404(Alert, pk=alert_id)
    client = _get_client_or_403(request, alert.client_file_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    user = request.user
    # Permission: only author or admin can cancel
    if not user.is_admin and alert.author_id != user.pk:
        return HttpResponseForbidden("You can only cancel your own alerts.")

    if alert.status == "cancelled":
        messages.info(request, _("This alert is already cancelled."))
        return redirect("events:event_list", client_id=client.pk)

    if request.method == "POST":
        form = AlertCancelForm(request.POST)
        if form.is_valid():
            alert.status = "cancelled"
            alert.status_reason = form.cleaned_data["status_reason"]
            alert.save()
            # Audit log
            from apps.audit.models import AuditLog
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=user.pk,
                user_display=user.display_name if hasattr(user, "display_name") else str(user),
                action="cancel",
                resource_type="alert",
                resource_id=alert.pk,
                is_demo_context=getattr(user, "is_demo", False),
                metadata={"reason": form.cleaned_data["status_reason"]},
            )
            messages.success(request, _("Alert cancelled."))
            return redirect("events:event_list", client_id=client.pk)
    else:
        form = AlertCancelForm()

    return render(request, "events/alert_cancel_form.html", {
        "form": form,
        "alert": alert,
        "client": client,
    })
