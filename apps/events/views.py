"""Views for events and alerts — admin event types + client-scoped events/alerts."""
import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.access import (
    build_program_display_context,
    get_author_program,
    get_client_or_403,
    get_program_from_client,
    get_user_program_ids,
)
from django_ratelimit.decorators import ratelimit

from apps.auth_app.decorators import admin_required, requires_permission, requires_permission_global
from apps.programs.models import Program, UserProgramRole

from .forms import (
    AlertCancelForm, AlertForm, AlertRecommendCancelForm, AlertReviewRecommendationForm,
    EventForm, EventTypeForm, MeetingEditForm, MeetingQuickCreateForm,
)
from .models import Alert, AlertCancellationRecommendation, CalendarFeedToken, Event, EventType, Meeting


# Use shared access helpers from apps.programs.access
_get_client_or_403 = get_client_or_403
_get_author_program = get_author_program


# ---------------------------------------------------------------------------
# Helper functions for @requires_permission decorator
# ---------------------------------------------------------------------------

# Alias for local use
_get_program_from_client = get_program_from_client


def _get_program_from_alert(request, alert_id, **kwargs):
    """Extract program via alert → client."""
    alert = get_object_or_404(Alert, pk=alert_id)
    return get_program_from_client(request, alert.client_file_id)


def _get_program_from_recommendation(request, recommendation_id, **kwargs):
    """Extract program via recommendation → alert → client."""
    recommendation = get_object_or_404(AlertCancellationRecommendation, pk=recommendation_id)
    return _get_program_from_client(request, recommendation.alert.client_file_id)


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
@requires_permission("event.view", _get_program_from_client)
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
    alerts = Alert.objects.filter(client_file=client).filter(program_q).select_related(
        "author_program",
    ).prefetch_related("cancellation_recommendations")

    # Build combined timeline entries
    from apps.notes.models import ProgressNote
    from apps.communications.models import Communication

    notes = ProgressNote.objects.filter(client_file=client).filter(program_q).select_related("author", "author_program")

    # Communications — filter by user's accessible programs (same as events/notes)
    communications = (
        Communication.objects.filter(client_file=client)
        .filter(program_q)
        .select_related("logged_by", "author_program")
    )

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
    for comm in communications:
        timeline.append({
            "type": "communication",
            "date": comm.created_at,
            "obj": comm,
        })
    # Sort newest first
    timeline.sort(key=lambda x: x["date"], reverse=True)

    # Timeline filtering (UXP5)
    filter_type = request.GET.get("filter", "all")
    if filter_type == "notes":
        timeline = [e for e in timeline if e["type"] == "note"]
    elif filter_type == "events":
        timeline = [e for e in timeline if e["type"] == "event"]
    elif filter_type == "communications":
        timeline = [e for e in timeline if e["type"] == "communication"]

    # Pagination — 20 entries per page with "Show more"
    page_size = 20
    try:
        offset = int(request.GET.get("offset", 0))
    except (ValueError, TypeError):
        offset = 0
    has_more = len(timeline) > offset + page_size
    timeline = timeline[offset:offset + page_size]

    # Recent communications for the quick-log section
    recent_communications = communications.order_by("-created_at")[:5]

    context = {
        "client": client,
        "events": events,
        "alerts": alerts,
        "timeline": timeline,
        "recent_communications": recent_communications,
        "active_tab": "events",
        "show_program_ui": program_ctx["show_program_ui"],
        "active_filter": filter_type,
        "has_more": has_more,
        "next_offset": offset + page_size,
        "is_append": offset > 0,
    }
    # HTMX partial response — return just the timeline entries for filter/pagination
    if request.headers.get("HX-Request") and "filter" in request.GET:
        return render(request, "events/_timeline_entries.html", context)
    if request.headers.get("HX-Request"):
        return render(request, "events/_tab_events.html", context)
    return render(request, "events/event_list.html", context)


@login_required
@requires_permission("event.create", _get_program_from_client)
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
@requires_permission("alert.create", _get_program_from_client)
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
@requires_permission("alert.cancel", _get_program_from_alert)
def alert_cancel(request, alert_id):
    """Cancel an alert with a reason (never delete). PM-only (matrix-enforced)."""
    alert = get_object_or_404(Alert, pk=alert_id)
    client = _get_client_or_403(request, alert.client_file_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    if alert.status == "cancelled":
        messages.info(request, _("This alert is already cancelled."))
        return redirect("events:event_list", client_id=client.pk)

    user = request.user
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


# ---------------------------------------------------------------------------
# Alert Cancellation Recommendation Workflow (two-person safety rule)
# ---------------------------------------------------------------------------


@login_required
@requires_permission("alert.recommend_cancel", _get_program_from_alert)
def alert_recommend_cancel(request, alert_id):
    """Staff recommends cancellation of an alert (two-person safety rule)."""
    alert = get_object_or_404(Alert, pk=alert_id)
    client = _get_client_or_403(request, alert.client_file_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    if alert.status == "cancelled":
        messages.info(request, _("This alert is already cancelled."))
        return redirect("events:event_list", client_id=client.pk)

    # Block if a pending recommendation already exists
    existing = alert.cancellation_recommendations.filter(status="pending").first()
    if existing:
        messages.info(request, _("A cancellation recommendation is already pending for this alert."))
        return redirect("events:event_list", client_id=client.pk)

    if request.method == "POST":
        form = AlertRecommendCancelForm(request.POST)
        if form.is_valid():
            AlertCancellationRecommendation.objects.create(
                alert=alert,
                recommended_by=request.user,
                assessment=form.cleaned_data["assessment"],
            )
            # Audit log
            from apps.audit.models import AuditLog
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=request.user.display_name if hasattr(request.user, "display_name") else str(request.user),
                action="create",
                resource_type="alert_cancellation_recommendation",
                resource_id=alert.pk,
                is_demo_context=getattr(request.user, "is_demo", False),
                metadata={
                    "alert_id": alert.pk,
                    "assessment_preview": form.cleaned_data["assessment"][:100],
                },
            )
            messages.success(request, _("Cancellation recommendation submitted for review."))
            return redirect("events:event_list", client_id=client.pk)
    else:
        form = AlertRecommendCancelForm()

    return render(request, "events/alert_recommend_cancel_form.html", {
        "form": form,
        "alert": alert,
        "client": client,
    })


@login_required
@requires_permission_global("alert.review_cancel_recommendation")
def alert_recommendation_queue(request):
    """PM queue: pending alert cancellation recommendations across their programs."""
    from apps.auth_app.permissions import DENY, can_access

    # Matrix-driven: find programs where the user's role grants review permission,
    # so changes to the matrix take effect automatically.
    reviewer_program_ids = set()
    for role_obj in UserProgramRole.objects.filter(user=request.user, status="active"):
        if can_access(role_obj.role, "alert.review_cancel_recommendation") != DENY:
            reviewer_program_ids.add(role_obj.program_id)

    pending = AlertCancellationRecommendation.objects.filter(
        status="pending",
        alert__author_program_id__in=reviewer_program_ids,
    ).select_related(
        "alert", "alert__client_file", "alert__author_program", "recommended_by",
    ).order_by("-created_at")

    breadcrumbs = [
        {"url": "", "label": _("Reviews")},
    ]
    return render(request, "events/alert_recommendation_queue.html", {
        "pending_recommendations": pending,
        "nav_active": "recommendations",
        "breadcrumbs": breadcrumbs,
    })


@login_required
@requires_permission("alert.review_cancel_recommendation", _get_program_from_recommendation)
def alert_recommendation_review(request, recommendation_id):
    """PM reviews a cancellation recommendation: approve or reject."""
    recommendation = get_object_or_404(AlertCancellationRecommendation, pk=recommendation_id)
    alert = recommendation.alert
    client = _get_client_or_403(request, alert.client_file_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    if recommendation.status != "pending":
        messages.info(request, _("This recommendation has already been reviewed."))
        return redirect("events:event_list", client_id=client.pk)

    if request.method == "POST":
        form = AlertReviewRecommendationForm(request.POST)
        if form.is_valid():
            from apps.audit.models import AuditLog
            action = form.cleaned_data["action"]
            review_note = form.cleaned_data.get("review_note", "")

            recommendation.reviewed_by = request.user
            recommendation.review_note = review_note
            recommendation.reviewed_at = timezone.now()

            if action == "approve":
                recommendation.status = "approved"
                recommendation.save()
                # Cancel the alert
                alert.status = "cancelled"
                status_parts = [_("Cancelled on recommendation by %(name)s.") % {
                    "name": recommendation.recommended_by.display_name
                    if hasattr(recommendation.recommended_by, "display_name")
                    else str(recommendation.recommended_by)
                }]
                status_parts.append(_("Assessment: %(text)s") % {"text": recommendation.assessment})
                if review_note:
                    status_parts.append(_("PM note: %(text)s") % {"text": review_note})
                alert.status_reason = " ".join(status_parts)
                alert.save()
                # Audit
                AuditLog.objects.using("audit").create(
                    event_timestamp=timezone.now(),
                    user_id=request.user.pk,
                    user_display=request.user.display_name if hasattr(request.user, "display_name") else str(request.user),
                    action="cancel",
                    resource_type="alert",
                    resource_id=alert.pk,
                    is_demo_context=getattr(request.user, "is_demo", False),
                    metadata={
                        "reason": alert.status_reason,
                        "recommendation_id": recommendation.pk,
                        "review_action": "approved",
                    },
                )
                messages.success(request, _("Recommendation approved. Alert cancelled."))
            else:
                recommendation.status = "rejected"
                recommendation.save()
                # Audit
                AuditLog.objects.using("audit").create(
                    event_timestamp=timezone.now(),
                    user_id=request.user.pk,
                    user_display=request.user.display_name if hasattr(request.user, "display_name") else str(request.user),
                    action="update",
                    resource_type="alert_cancellation_recommendation",
                    resource_id=recommendation.pk,
                    is_demo_context=getattr(request.user, "is_demo", False),
                    metadata={
                        "review_action": "rejected",
                        "review_note": review_note,
                        "alert_id": alert.pk,
                    },
                )
                messages.success(request, _("Recommendation rejected. Alert remains active."))

            return redirect("events:event_list", client_id=client.pk)
    else:
        form = AlertReviewRecommendationForm()

    breadcrumbs = [
        {"url": reverse("events:alert_recommendation_queue"), "label": _("Reviews")},
        {"url": "", "label": _("Review Recommendation")},
    ]
    return render(request, "events/alert_recommendation_review.html", {
        "form": form,
        "recommendation": recommendation,
        "alert": alert,
        "client": client,
        "breadcrumbs": breadcrumbs,
    })


# ---------------------------------------------------------------------------
# Helper functions for meeting views
# ---------------------------------------------------------------------------

def _get_program_from_meeting(request, event_id, **kwargs):
    """Extract program via meeting -> event -> client."""
    event = get_object_or_404(Event, pk=event_id)
    return get_program_from_client(request, event.client_file_id)


# ---------------------------------------------------------------------------
# Meeting CRUD (client-scoped)
# ---------------------------------------------------------------------------

@login_required
@requires_permission("meeting.create", _get_program_from_client)
def meeting_create(request, client_id):
    """Quick-create a meeting for a client (3 fields, under 60 seconds)."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    if request.method == "POST":
        form = MeetingQuickCreateForm(request.POST)
        if form.is_valid():
            # Create the underlying Event
            event = Event.objects.create(
                client_file=client,
                title=_("Meeting"),
                start_timestamp=form.cleaned_data["start_timestamp"],
                author_program=_get_author_program(request.user, client),
            )
            # Create the Meeting linked to it
            meeting = Meeting.objects.create(
                event=event,
                location=form.cleaned_data.get("location", ""),
            )
            # Add the requesting user as an attendee
            meeting.attendees.add(request.user)
            messages.success(request, _("Meeting created."))
            return redirect("events:event_list", client_id=client.pk)
    else:
        form = MeetingQuickCreateForm()

    # Check if this client has consented to reminders
    can_send_reminders = client.sms_consent or client.email_consent

    return render(request, "events/meeting_form.html", {
        "form": form,
        "client": client,
        "editing": False,
        "can_send_reminders": can_send_reminders,
    })


@login_required
@requires_permission("meeting.edit", _get_program_from_meeting)
def meeting_update(request, client_id, event_id):
    """Full edit form for an existing meeting."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    event = get_object_or_404(Event, pk=event_id, client_file=client)
    meeting = get_object_or_404(Meeting, event=event)

    if request.method == "POST":
        form = MeetingEditForm(request.POST)
        if form.is_valid():
            # Update the Event
            event.start_timestamp = form.cleaned_data["start_timestamp"]
            event.save()
            # Update the Meeting
            meeting.location = form.cleaned_data.get("location", "")
            meeting.duration_minutes = form.cleaned_data.get("duration_minutes")
            meeting.status = form.cleaned_data["status"]
            meeting.save()
            messages.success(request, _("Meeting updated."))
            return redirect("events:event_list", client_id=client.pk)
    else:
        form = MeetingEditForm(initial={
            "start_timestamp": event.start_timestamp.strftime("%Y-%m-%dT%H:%M") if event.start_timestamp else "",
            "location": meeting.location,
            "duration_minutes": meeting.duration_minutes,
            "status": meeting.status,
        })

    return render(request, "events/meeting_form.html", {
        "form": form,
        "client": client,
        "meeting": meeting,
        "editing": True,
    })


@login_required
def meeting_list(request):
    """Staff's upcoming meetings dashboard — shows their own meetings."""
    now = timezone.now()
    upcoming_cutoff = now + timedelta(days=30)
    recent_cutoff = now - timedelta(days=7)

    upcoming_meetings = (
        Meeting.objects.filter(
            attendees=request.user,
            status="scheduled",
            event__start_timestamp__gte=now,
            event__start_timestamp__lte=upcoming_cutoff,
        )
        .select_related("event", "event__client_file")
        .order_by("event__start_timestamp")
    )

    past_meetings = (
        Meeting.objects.filter(
            attendees=request.user,
            event__start_timestamp__gte=recent_cutoff,
            event__start_timestamp__lt=now,
        )
        .select_related("event", "event__client_file")
        .order_by("-event__start_timestamp")
    )

    # System health warnings — show banners when messaging channels are failing
    health_warnings = []
    from apps.admin_settings.models import FeatureToggle
    from apps.communications.models import SystemHealthCheck

    flags = FeatureToggle.get_all_flags()
    if flags.get("messaging_sms") or flags.get("messaging_email"):
        now_time = timezone.now()
        for health in SystemHealthCheck.objects.filter(consecutive_failures__gt=0):
            if not health.last_failure_at:
                continue
            hours_since = (now_time - health.last_failure_at).total_seconds() / 3600
            channel_name = health.get_channel_display()
            if hours_since <= 24 and health.consecutive_failures < 3:
                health_warnings.append({
                    "level": "warning",
                    "message": _(
                        "%(count)s %(channel)s reminder(s) could not be sent recently."
                    ) % {"count": health.consecutive_failures, "channel": channel_name},
                })
            elif health.consecutive_failures >= 3:
                health_warnings.append({
                    "level": "danger",
                    "message": _(
                        "%(channel)s reminders have not been working since %(date)s. "
                        "Please contact your support person."
                    ) % {
                        "channel": channel_name,
                        "date": health.last_failure_at.strftime("%B %d"),
                    },
                })

    breadcrumbs = [
        {"url": "", "label": _("My Meetings")},
    ]
    return render(request, "events/meeting_list.html", {
        "upcoming_meetings": upcoming_meetings,
        "past_meetings": past_meetings,
        "health_warnings": health_warnings,
        "breadcrumbs": breadcrumbs,
        "nav_active": "meetings",
    })


@login_required
@requires_permission("meeting.edit", _get_program_from_meeting)
def meeting_status_update(request, event_id):
    """HTMX partial: update meeting status (scheduled/completed/cancelled/no_show)."""
    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    event = get_object_or_404(Event, pk=event_id)
    meeting = get_object_or_404(Meeting, event=event)

    new_status = request.POST.get("status", "").strip()
    valid_statuses = ["scheduled", "completed", "cancelled", "no_show"]
    if new_status not in valid_statuses:
        return HttpResponse("Invalid status.", status=400)

    meeting.status = new_status
    meeting.save()

    return render(request, "events/_meeting_status.html", {"meeting": meeting})


# ---------------------------------------------------------------------------
# Calendar Feed (iCal / .ics)
# ---------------------------------------------------------------------------

@ratelimit(key="user_or_ip", rate="60/h", block=True)
def calendar_feed(request, token):
    """Public .ics endpoint — token-based auth, no login required.

    PRIVACY: Only include initials + record_id in summary — NO full names,
    NO phone numbers. Rate limited to 60 requests/hour.
    """
    feed_token = CalendarFeedToken.objects.filter(token=token, is_active=True).select_related("user").first()
    if not feed_token:
        from django.http import Http404
        raise Http404

    # Update last accessed timestamp
    feed_token.last_accessed_at = timezone.now()
    feed_token.save(update_fields=["last_accessed_at"])

    # Get the user's scheduled meetings
    meetings = (
        Meeting.objects.filter(
            attendees=feed_token.user,
            status="scheduled",
        )
        .select_related("event", "event__client_file")
        .order_by("event__start_timestamp")
    )

    # Build iCal output
    try:
        from icalendar import Calendar as ICalCalendar, Event as ICalEvent
    except ImportError:
        return HttpResponse(
            "iCalendar library not installed.", status=503, content_type="text/plain"
        )

    cal = ICalCalendar()
    cal.add("prodid", "-//KoNote//Calendar Feed//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", "KoNote Meetings")

    for meeting in meetings:
        ical_event = ICalEvent()

        # PRIVACY: use initials + record_id only — no full names
        client = meeting.event.client_file
        initials = ""
        if hasattr(client, "first_name") and client.first_name:
            initials += client.first_name[0].upper()
        if hasattr(client, "last_name") and client.last_name:
            initials += client.last_name[0].upper()
        record_id = getattr(client, "record_id", "") or ""
        summary_parts = ["Meeting"]
        if initials:
            summary_parts.append(initials)
        if record_id:
            summary_parts.append(f"({record_id})")
        ical_event.add("summary", " ".join(summary_parts))

        ical_event.add("dtstart", meeting.event.start_timestamp)
        if meeting.duration_minutes:
            ical_event.add("dtend", meeting.event.start_timestamp + timedelta(minutes=meeting.duration_minutes))
        else:
            # Default to 1 hour if no duration specified
            ical_event.add("dtend", meeting.event.start_timestamp + timedelta(hours=1))

        if meeting.location:
            ical_event.add("location", meeting.location)

        ical_event.add("uid", f"meeting-{meeting.pk}@konote")
        ical_event.add("dtstamp", timezone.now())

        cal.add_component(ical_event)

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response["Content-Disposition"] = 'attachment; filename="konote-meetings.ics"'
    return response


@login_required
def calendar_feed_settings(request):
    """Manage calendar feed token — generate, regenerate, or view feed URL."""
    feed_token = CalendarFeedToken.objects.filter(user=request.user).first()

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action in ("generate", "regenerate"):
            if feed_token:
                # Regenerate: update existing token
                feed_token.token = secrets.token_urlsafe(32)
                feed_token.is_active = True
                feed_token.save()
                messages.success(request, _("Calendar feed URL regenerated. Update your calendar app with the new URL."))
            else:
                # Generate: create new token
                feed_token = CalendarFeedToken.objects.create(
                    user=request.user,
                    token=secrets.token_urlsafe(32),
                )
                messages.success(request, _("Calendar feed generated."))

    # Build feed URL
    feed_url = None
    if feed_token and feed_token.is_active:
        feed_url = request.build_absolute_uri(
            reverse("calendar_feed", kwargs={"token": feed_token.token})
        )

    breadcrumbs = [
        {"url": reverse("events:meeting_list"), "label": _("My Meetings")},
        {"url": "", "label": _("Calendar Feed")},
    ]
    return render(request, "events/calendar_feed_settings.html", {
        "feed_url": feed_url,
        "feed_token": feed_token,
        "breadcrumbs": breadcrumbs,
    })
