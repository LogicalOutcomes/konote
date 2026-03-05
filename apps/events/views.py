"""Views for events and alerts — admin event types + client-scoped events/alerts."""
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlparse, urlunparse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.access import (
    apply_consent_filter,
    build_program_display_context,
    get_author_program,
    get_client_or_403,
    get_program_from_client,
    get_user_program_ids,
)
from django_ratelimit.decorators import ratelimit

from apps.auth_app.constants import ROLE_EXECUTIVE, ROLE_PROGRAM_MANAGER
from apps.auth_app.decorators import admin_required, requires_permission, requires_permission_global
from apps.auth_app.permissions import ALLOW, DENY, can_access
from apps.programs.models import Program, UserProgramRole

from .forms import (
    AlertCancelForm, AlertForm, AlertRecommendCancelForm, AlertReviewRecommendationForm,
    EventForm, EventTypeForm, MeetingEditForm, MeetingQuickCreateForm, SRECategoryForm,
)
from .models import Alert, AlertCancellationRecommendation, CalendarFeedToken, Event, EventType, Meeting, SRECategory

logger = logging.getLogger(__name__)


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
# Event Type Admin (admin + PM access)
# ---------------------------------------------------------------------------


def _get_pm_program_ids(user):
    """Return set of program IDs where the user is an active PM."""
    return set(
        UserProgramRole.objects.filter(
            user=user, role=ROLE_PROGRAM_MANAGER, status="active",
        ).values_list("program_id", flat=True)
    )


def _can_edit_event_type(user, event_type):
    """Check if the user can edit an event type."""
    if user.is_admin:
        return True
    if event_type.owning_program_id is None:
        return False
    return event_type.owning_program_id in _get_pm_program_ids(user)


@login_required
@requires_permission("event_type.manage", allow_admin=True)
def event_type_list(request):
    """List event types visible to the user."""
    if request.user.is_admin:
        event_types = EventType.objects.all()
    else:
        pm_program_ids = _get_pm_program_ids(request.user)
        event_types = EventType.objects.filter(
            Q(owning_program_id__in=pm_program_ids) | Q(owning_program__isnull=True)
        )
    return render(request, "events/event_type_list.html", {
        "event_types": event_types,
        "is_admin": request.user.is_admin,
    })


@login_required
@requires_permission("event_type.manage", allow_admin=True)
def event_type_create(request):
    """Create a new event type."""
    if request.method == "POST":
        form = EventTypeForm(request.POST, requesting_user=request.user)
        if form.is_valid():
            event_type = form.save(commit=False)
            if not request.user.is_admin and event_type.owning_program_id is None:
                pm_program_ids = _get_pm_program_ids(request.user)
                if len(pm_program_ids) == 1:
                    event_type.owning_program_id = next(iter(pm_program_ids))
            event_type.save()
            messages.success(request, _("Event type created."))
            return redirect("event_types:event_type_list")
    else:
        form = EventTypeForm(requesting_user=request.user)
    return render(request, "events/event_type_form.html", {"form": form, "editing": False})


@login_required
@requires_permission("event_type.manage", allow_admin=True)
def event_type_edit(request, type_id):
    """Edit an event type."""
    event_type = get_object_or_404(EventType, pk=type_id)

    if not _can_edit_event_type(request.user, event_type):
        return HttpResponseForbidden(_("Access denied. You can only edit event types in your programs."))

    if request.method == "POST":
        form = EventTypeForm(request.POST, instance=event_type, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Event type updated."))
            return redirect("event_types:event_type_list")
    else:
        form = EventTypeForm(instance=event_type, requesting_user=request.user)
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

    # program_q scopes to the user's programs; consent filter below narrows
    # further to the viewing program when cross-program sharing is OFF.
    # Both are needed: consent filter passes through when sharing is ON.
    notes = ProgressNote.objects.filter(client_file=client).filter(program_q).select_related("author", "author_program")

    # PHIPA: apply consent filter to notes in the timeline
    notes, consent_viewing_program = apply_consent_filter(
        notes, client, request.user, user_program_ids,
        active_program_ids=active_ids,
    )

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

    # Timeline filtering — simplified: All or Events only
    filter_type = request.GET.get("filter", "all")
    if filter_type == "events":
        timeline = [e for e in timeline if e["type"] == "event"]
    # "all" shows everything (default)

    # Pagination — 20 entries per page with "Show more"
    page_size = 20
    try:
        offset = int(request.GET.get("offset", 0))
    except (ValueError, TypeError):
        offset = 0
    has_more = len(timeline) > offset + page_size
    timeline = timeline[offset:offset + page_size]

    context = {
        "client": client,
        "events": events,
        "alerts": alerts,
        "timeline": timeline,
        "active_tab": "events",
        "show_program_ui": program_ctx["show_program_ui"],
        "active_filter": filter_type,
        "has_more": has_more,
        "next_offset": offset + page_size,
        "is_append": offset > 0,
        "consent_viewing_program": consent_viewing_program,
    }
    # HTMX partial response — return just the timeline entries for filter/pagination
    if request.headers.get("HX-Request") and "filter" in request.GET:
        return render(request, "events/_timeline_entries.html", context)
    if request.headers.get("HX-Request"):
        return render(request, "events/_tab_events.html", context)
    return render(request, "events/event_list.html", context)


def _user_can_flag_sre(user):
    """Check if user has sre.flag permission based on their highest role."""
    from apps.auth_app.decorators import _get_user_highest_role_any
    if getattr(user, "is_admin", False):
        return True
    role = _get_user_highest_role_any(user)
    if role is None:
        return False
    return can_access(role, "sre.flag") != DENY


def _send_sre_notification(event, request):
    """Send SRE notification emails to admins and executives.

    Recipients: admin/executive roles in the event's program + all site-wide admins.
    Level 1 severity: "[URGENT]" in subject.
    If email fails, log but don't block save.
    """
    from apps.auth_app.models import User
    from apps.communications.services import send_email_message

    category = event.sre_category
    severity = category.severity if category else 2
    category_name = str(category) if category else _("Unknown")

    # Build recipient list: admins + executives/PMs in the event's program
    recipient_emails = set()

    # All site-wide admins
    for admin_user in User.objects.filter(is_admin=True, is_active=True):
        if admin_user.email:
            recipient_emails.add(admin_user.email)

    # PMs and executives in the event's program
    if event.author_program_id:
        roles_qs = UserProgramRole.objects.filter(
            program_id=event.author_program_id,
            role__in=[ROLE_PROGRAM_MANAGER, ROLE_EXECUTIVE],
            status="active",
        ).select_related("user")
        for role_obj in roles_qs:
            if role_obj.user.is_active and role_obj.user.email:
                recipient_emails.add(role_obj.user.email)

    if not recipient_emails:
        logger.warning("SRE notification: no recipients found for event %s", event.pk)
        return

    # Build subject
    urgent_prefix = "[URGENT] " if severity == 1 else ""
    subject = f"{urgent_prefix}{_('Serious Reportable Event')} — {category_name}"

    # Build body
    date_str = event.start_timestamp.strftime("%Y-%m-%d") if event.start_timestamp else _("(no date)")
    program_name = event.author_program.name if event.author_program else _("(no program)")
    flagged_by = event.sre_flagged_by.display_name if event.sre_flagged_by and hasattr(event.sre_flagged_by, "display_name") else str(event.sre_flagged_by or _("Unknown"))

    # Bilingual category name
    category_en = category.name if category else ""
    category_fr = category.name_fr if category else ""
    bilingual_category = f"{category_en} / {category_fr}" if category_fr else category_en

    severity_labels = {1: _("Level 1 — Immediate"), 2: _("Level 2 — Within 24 hours"), 3: _("Level 3 — Within 7 days")}
    severity_label = severity_labels.get(severity, _("Unknown"))

    body = (
        f"{_('A Serious Reportable Event has been flagged.')}\n\n"
        f"{_('Category')}: {bilingual_category}\n"
        f"{_('Severity')}: {severity_label}\n"
        f"{_('Date')}: {date_str}\n"
        f"{_('Program')}: {program_name}\n"
        f"{_('Flagged by')}: {flagged_by}\n"
    )
    if event.title:
        body += f"{_('Event')}: {event.title}\n"

    # Do NOT include event.description in email — it may contain PII
    # (participant names, clinical details). Email is the alert; staff
    # click through to the app to read details behind RBAC.

    try:
        event_url = request.build_absolute_uri(
            reverse("events:event_list", kwargs={"client_id": event.client_file_id})
        )
        body += f"\n{_('View event')}: {event_url}\n"
    except Exception:
        pass

    # Send to each recipient individually
    for email_addr in recipient_emails:
        try:
            send_email_message(email_addr, subject, body)
        except Exception as exc:
            logger.warning("SRE notification failed for %s: %s", email_addr[:5] + "***", str(exc))

    event.sre_notifications_sent = True
    event.save(update_fields=["sre_notifications_sent"])


@login_required
@requires_permission("event.create", _get_program_from_client)
def event_create(request, client_id):
    """Create an event for a client."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # Block edits when consent has been withdrawn (QA-R7-PRIVACY2)
    if client.is_consent_withdrawn:
        messages.error(request, _("This record is read-only because consent has been withdrawn."))
        return redirect("events:event_list", client_id=client.pk)

    can_flag_sre = _user_can_flag_sre(request.user)

    if request.method == "POST":
        form = EventForm(request.POST, can_flag_sre=can_flag_sre)
        if form.is_valid():
            event = form.save(commit=False)
            event.client_file = client
            event.author_program = getattr(
                request, "user_program", None
            ) or _get_author_program(request.user, client)

            # Handle SRE flagging
            if event.is_sre and can_flag_sre:
                event.sre_flagged_by = request.user
                event.sre_flagged_at = timezone.now()

            event.save()

            # SRE audit log + notification
            if event.is_sre:
                from apps.audit.models import AuditLog
                AuditLog.objects.using("audit").create(
                    event_timestamp=timezone.now(),
                    user_id=request.user.pk,
                    user_display=request.user.display_name if hasattr(request.user, "display_name") else str(request.user),
                    action="create",
                    resource_type="sre_event",
                    resource_id=event.pk,
                    is_demo_context=getattr(request.user, "is_demo", False),
                    metadata={
                        "client_id": client.pk,
                        "sre_category_id": event.sre_category_id,
                        "sre_category_name": str(event.sre_category) if event.sre_category else "",
                        "severity": event.sre_category.severity if event.sre_category else None,
                    },
                )
                _send_sre_notification(event, request)
                messages.success(request, _("Event created and flagged as a Serious Reportable Event. Notifications have been sent."))
            else:
                messages.success(request, _("Event created."))

            return redirect("events:event_list", client_id=client.pk)
    else:
        form = EventForm(can_flag_sre=can_flag_sre)

    return render(request, "events/event_form.html", {
        "form": form,
        "client": client,
        "can_flag_sre": can_flag_sre,
    })


@login_required
@requires_permission("event.create", _get_program_from_client)
def event_edit(request, client_id, event_id):
    """Edit an existing event for a client, including SRE flagging."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # Block edits when consent has been withdrawn (QA-R7-PRIVACY2)
    if client.is_consent_withdrawn:
        messages.error(request, _("This record is read-only because consent has been withdrawn."))
        return redirect("events:event_list", client_id=client.pk)

    event = get_object_or_404(Event, pk=event_id, client_file=client)

    can_flag_sre = _user_can_flag_sre(request.user)
    was_sre = event.is_sre

    if request.method == "POST":
        form = EventForm(request.POST, instance=event, can_flag_sre=can_flag_sre)
        if form.is_valid():
            event = form.save(commit=False)

            # Handle SRE transition: non-SRE → SRE (new flagging)
            if event.is_sre and not was_sre and can_flag_sre:
                event.sre_flagged_by = request.user
                event.sre_flagged_at = timezone.now()

            event.save()

            # Audit log + notification only on NEW SRE flagging
            if event.is_sre and not was_sre:
                from apps.audit.models import AuditLog
                AuditLog.objects.using("audit").create(
                    event_timestamp=timezone.now(),
                    user_id=request.user.pk,
                    user_display=request.user.display_name if hasattr(request.user, "display_name") else str(request.user),
                    action="update",
                    resource_type="sre_event",
                    resource_id=event.pk,
                    is_demo_context=getattr(request.user, "is_demo", False),
                    metadata={
                        "action": "flag",
                        "client_id": client.pk,
                        "sre_category_id": event.sre_category_id,
                        "sre_category_name": str(event.sre_category) if event.sre_category else "",
                        "severity": event.sre_category.severity if event.sre_category else None,
                    },
                )
                if not event.sre_notifications_sent:
                    _send_sre_notification(event, request)
                messages.success(request, _("Event updated and flagged as a Serious Reportable Event. Notifications have been sent."))
            else:
                messages.success(request, _("Event updated."))

            return redirect("events:event_list", client_id=client.pk)
    else:
        form = EventForm(instance=event, can_flag_sre=can_flag_sre)

    return render(request, "events/event_form.html", {
        "form": form,
        "client": client,
        "editing": True,
        "can_flag_sre": can_flag_sre,
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
            alert = Alert.objects.create(
                client_file=client,
                content=form.cleaned_data["content"],
                author=request.user,
                author_program=_get_author_program(request.user, client),
            )
            from apps.audit.models import AuditLog
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=request.user.display_name if hasattr(request.user, "display_name") else str(request.user),
                action="create",
                resource_type="alert",
                resource_id=alert.pk,
                is_demo_context=getattr(request.user, "is_demo", False),
                metadata={"client_id": client.pk},
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
        {"url": "", "label": _("Approvals")},
    ]
    return render(request, "events/alert_recommendation_queue.html", {
        "pending_recommendations": pending,
        "nav_active": "manage",
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
        {"url": reverse("events:alert_recommendation_queue"), "label": _("Approvals")},
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

def _get_meeting_settings():
    """Read meeting scheduling settings from InstanceSetting."""
    from apps.admin_settings.models import InstanceSetting
    from .forms import DEFAULT_LOCATION_OPTIONS

    settings = InstanceSetting.get_all()
    raw_locations = settings.get("meeting_location_options", "")
    if raw_locations.strip():
        location_choices = [line.strip() for line in raw_locations.splitlines() if line.strip()]
    else:
        location_choices = DEFAULT_LOCATION_OPTIONS

    return {
        "location_choices": location_choices,
        "meeting_time_start": int(settings.get("meeting_time_start", 9)),
        "meeting_time_end": int(settings.get("meeting_time_end", 17)),
        "meeting_time_step": int(settings.get("meeting_time_step", 30)),
    }


@login_required
@requires_permission("meeting.create", _get_program_from_client)
def meeting_create(request, client_id):
    """Quick-create a meeting for a client (3 fields, under 60 seconds)."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    mtg_settings = _get_meeting_settings()

    if request.method == "POST":
        form = MeetingQuickCreateForm(request.POST, location_choices=mtg_settings["location_choices"])
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
            # "Save & Schedule Another" keeps the user on the create form
            if request.POST.get("save_and_new"):
                return redirect("events:meeting_create", client_id=client.pk)
            return redirect("events:event_list", client_id=client.pk)
    else:
        form = MeetingQuickCreateForm(location_choices=mtg_settings["location_choices"])

    # Check if this client has consented to reminders
    can_send_reminders = client.sms_consent or client.email_consent

    return render(request, "events/meeting_form.html", {
        "form": form,
        "client": client,
        "editing": False,
        "can_send_reminders": can_send_reminders,
        "meeting_time_start": mtg_settings["meeting_time_start"],
        "meeting_time_end": mtg_settings["meeting_time_end"],
        "meeting_time_step": mtg_settings["meeting_time_step"],
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
    mtg_settings = _get_meeting_settings()

    if request.method == "POST":
        form = MeetingEditForm(request.POST, location_choices=mtg_settings["location_choices"])
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
        form = MeetingEditForm(
            initial={
                "start_timestamp": event.start_timestamp.strftime("%Y-%m-%dT%H:%M") if event.start_timestamp else "",
                "location": meeting.location,
                "duration_minutes": meeting.duration_minutes,
                "status": meeting.status,
            },
            location_choices=mtg_settings["location_choices"],
        )

    return render(request, "events/meeting_form.html", {
        "form": form,
        "client": client,
        "meeting": meeting,
        "editing": True,
        "meeting_time_start": mtg_settings["meeting_time_start"],
        "meeting_time_end": mtg_settings["meeting_time_end"],
        "meeting_time_step": mtg_settings["meeting_time_step"],
    })


@login_required
@requires_permission_global("meeting.view")
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
    cal.add("method", "PUBLISH")
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

    response = HttpResponse(cal.to_ical(), content_type="text/calendar; charset=utf-8")
    return response


@login_required
@requires_permission("meeting.view", allow_admin=True)
def calendar_feed_settings(request):
    """Manage calendar feed token — generate, regenerate, or view feed URL."""
    feed_token = CalendarFeedToken.objects.filter(user=request.user).first()

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action in ("generate", "regenerate"):
            try:
                new_token = secrets.token_urlsafe(32)
                if feed_token:
                    # Regenerate: update existing token
                    feed_token.token = new_token
                    feed_token.is_active = True
                    feed_token.save()
                    messages.success(
                        request,
                        _("Calendar feed URL regenerated. Update your calendar app with the new URL."),
                    )
                else:
                    # Generate: create new token
                    feed_token = CalendarFeedToken.objects.create(
                        user=request.user,
                        token=new_token,
                    )
                    messages.success(
                        request,
                        _("Calendar link created. Copy the link below and add it to your calendar app."),
                    )
            except Exception:
                messages.error(
                    request,
                    _("Something went wrong generating your calendar link. Please try again."),
                )
        # POST-Redirect-GET: redirect after any POST to prevent form re-submission on browser reload
        return redirect("events:calendar_feed_settings")

    # Build feed URL
    feed_url = None
    outlook_subscribe_url = None
    if feed_token and feed_token.is_active:
        try:
            raw_url = request.build_absolute_uri(
                reverse("calendar_feed", kwargs={"token": feed_token.token})
            )
            parsed = urlparse(raw_url)
            # Validate that the URL has a usable scheme and netloc before showing it
            if parsed.scheme in ("http", "https") and parsed.netloc:
                feed_url = raw_url
                outlook_subscribe_url = urlunparse(parsed._replace(scheme="webcal"))
            else:
                messages.error(
                    request,
                    _("Could not build your calendar link. Please contact support."),
                )
        except Exception:
            messages.error(
                request,
                _("Could not build your calendar link. Please contact support."),
            )

    breadcrumbs = [
        {"url": reverse("events:meeting_list"), "label": _("My Meetings")},
        {"url": "", "label": _("Calendar Feed")},
    ]
    return render(request, "events/calendar_feed_settings.html", {
        "feed_url": feed_url,
        "outlook_subscribe_url": outlook_subscribe_url,
        "feed_token": feed_token,
        "breadcrumbs": breadcrumbs,
    })


# ---------------------------------------------------------------------------
# SRE Un-flagging (Admin only)
# ---------------------------------------------------------------------------

@login_required
@admin_required
def sre_unflag(request, event_id):
    """Remove SRE flag from an event. Admin-only, creates audit log."""
    event = get_object_or_404(Event, pk=event_id)
    if not event.is_sre:
        messages.info(request, _("This event is not flagged as an SRE."))
        return redirect("events:event_list", client_id=event.client_file_id)

    if request.method == "POST":
        old_category = str(event.sre_category) if event.sre_category else ""
        old_severity = event.sre_category.severity if event.sre_category else None

        event.is_sre = False
        event.sre_category = None
        event.save(update_fields=["is_sre", "sre_category"])

        # Audit log for un-flagging
        from apps.audit.models import AuditLog
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.pk,
            user_display=request.user.display_name if hasattr(request.user, "display_name") else str(request.user),
            action="update",
            resource_type="sre_event",
            resource_id=event.pk,
            is_demo_context=getattr(request.user, "is_demo", False),
            metadata={
                "action": "unflag",
                "previous_category": old_category,
                "previous_severity": old_severity,
            },
        )
        messages.success(request, _("SRE flag removed from this event."))
        return redirect("events:event_list", client_id=event.client_file_id)

    return render(request, "events/sre_unflag_confirm.html", {
        "event": event,
    })


# ---------------------------------------------------------------------------
# SRE Category Admin Management (Admin only)
# ---------------------------------------------------------------------------

@login_required
@admin_required
def sre_category_list(request):
    """List all SRE categories."""
    categories = SRECategory.objects.all()
    breadcrumbs = [
        {"url": "", "label": _("SRE Categories")},
    ]
    return render(request, "events/sre_category_list.html", {
        "categories": categories,
        "breadcrumbs": breadcrumbs,
        "nav_active": "manage",
    })


@login_required
@admin_required
def sre_category_create(request):
    """Create a new SRE category."""
    if request.method == "POST":
        form = SRECategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("SRE category created."))
            return redirect("sre_categories:sre_category_list")
    else:
        form = SRECategoryForm()
    breadcrumbs = [
        {"url": reverse("sre_categories:sre_category_list"), "label": _("SRE Categories")},
        {"url": "", "label": _("New")},
    ]
    return render(request, "events/sre_category_form.html", {
        "form": form,
        "editing": False,
        "breadcrumbs": breadcrumbs,
        "nav_active": "manage",
    })


@login_required
@admin_required
def sre_category_edit(request, category_id):
    """Edit an existing SRE category."""
    category = get_object_or_404(SRECategory, pk=category_id)
    if request.method == "POST":
        form = SRECategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _("SRE category updated."))
            return redirect("sre_categories:sre_category_list")
    else:
        form = SRECategoryForm(instance=category)
    breadcrumbs = [
        {"url": reverse("sre_categories:sre_category_list"), "label": _("SRE Categories")},
        {"url": "", "label": category.name},
    ]
    return render(request, "events/sre_category_form.html", {
        "form": form,
        "editing": True,
        "category": category,
        "breadcrumbs": breadcrumbs,
        "nav_active": "manage",
    })


@login_required
@admin_required
def sre_category_toggle_active(request, category_id):
    """Archive or unarchive an SRE category."""
    category = get_object_or_404(SRECategory, pk=category_id)
    if request.method == "POST":
        category.is_active = not category.is_active
        category.save(update_fields=["is_active"])
        status_msg = _("activated") if category.is_active else _("archived")
        messages.success(request, _("SRE category %(name)s %(status)s.") % {"name": category.name, "status": status_msg})
    return redirect("sre_categories:sre_category_list")


# ---------------------------------------------------------------------------
# SRE Report (Admin/Executive/PM)
# ---------------------------------------------------------------------------

@login_required
@requires_permission("sre.view_report", allow_admin=True)
def sre_report(request):
    """SRE report: all SRE events in date range, filterable by program and category.

    Admin and Executive see all programs. PMs see only their own programs.
    """
    import datetime

    # Default date range: last 90 days
    today = timezone.now().date()
    default_start = today - timedelta(days=90)
    start_date_str = request.GET.get("start_date", "")
    end_date_str = request.GET.get("end_date", "")
    program_id = request.GET.get("program", "")
    category_id = request.GET.get("category", "")

    try:
        start_date = datetime.date.fromisoformat(start_date_str) if start_date_str else default_start
    except ValueError:
        start_date = default_start
    try:
        end_date = datetime.date.fromisoformat(end_date_str) if end_date_str else today
    except ValueError:
        end_date = today

    # Convert dates to datetimes for query
    start_dt = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
    end_dt = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))

    # Base queryset: SRE events only
    sre_events = Event.objects.filter(
        is_sre=True,
        start_timestamp__gte=start_dt,
        start_timestamp__lte=end_dt,
    ).select_related("sre_category", "author_program", "sre_flagged_by", "event_type")

    # Scope to user's programs if not admin
    if not request.user.is_admin:
        user_program_ids = get_user_program_ids(request.user)
        sre_events = sre_events.filter(author_program_id__in=user_program_ids)

    # Filters
    if program_id:
        try:
            sre_events = sre_events.filter(author_program_id=int(program_id))
        except (ValueError, TypeError):
            pass
    if category_id:
        try:
            sre_events = sre_events.filter(sre_category_id=int(category_id))
        except (ValueError, TypeError):
            pass

    sre_events = sre_events.order_by("-start_timestamp")

    # Aggregate counts by category (use IDs so templates can call get_translated_name)
    category_counts_raw = (
        sre_events.values("sre_category_id", "sre_category__severity")
        .annotate(count=Count("pk"))
        .order_by("sre_category__severity")
    )
    # Resolve to category objects for bilingual display
    cat_map = {c.pk: c for c in SRECategory.objects.filter(
        pk__in=[r["sre_category_id"] for r in category_counts_raw if r["sre_category_id"]]
    )}
    category_counts = [
        {"category": cat_map.get(r["sre_category_id"]), "severity": r["sre_category__severity"], "count": r["count"]}
        for r in category_counts_raw
    ]

    # Aggregate counts by program
    program_counts = (
        sre_events.values("author_program__name")
        .annotate(count=Count("pk"))
        .order_by("author_program__name")
    )

    # Filter options
    if request.user.is_admin:
        programs = Program.objects.filter(status="active").order_by("name")
    else:
        user_program_ids = get_user_program_ids(request.user)
        programs = Program.objects.filter(pk__in=user_program_ids, status="active").order_by("name")
    categories = SRECategory.objects.filter(is_active=True)

    breadcrumbs = [
        {"url": "", "label": _("SRE Report")},
    ]
    return render(request, "events/sre_report.html", {
        "sre_events": sre_events,
        "category_counts": category_counts,
        "program_counts": program_counts,
        "start_date": start_date,
        "end_date": end_date,
        "programs": programs,
        "categories": categories,
        "selected_program": program_id,
        "selected_category": category_id,
        "total_count": sre_events.count(),
        "breadcrumbs": breadcrumbs,
        "nav_active": "manage",
    })
