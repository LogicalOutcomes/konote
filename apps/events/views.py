"""Views for events and alerts — admin event types + client-scoped events/alerts."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
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
from apps.auth_app.decorators import admin_required, requires_permission, requires_permission_global
from apps.programs.models import Program, UserProgramRole

from .forms import AlertCancelForm, AlertForm, AlertRecommendCancelForm, AlertReviewRecommendationForm, EventForm, EventTypeForm
from .models import Alert, AlertCancellationRecommendation, Event, EventType


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
