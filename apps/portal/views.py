"""Views for the participant portal.

The portal is a separate, participant-facing interface. It uses its own
session key (_portal_participant_id) and does NOT use Django's built-in
auth system — participants are ParticipantUser, not User.

Data isolation: every view scopes queries to request.participant_user.client_file.
Sub-objects are always fetched with get_object_or_404(..., client_file=client_file).
"""
import json
import logging
from functools import wraps

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.admin_settings.models import FeatureToggle

logger = logging.getLogger(__name__)

# Account lockout settings for participant login
PORTAL_LOCKOUT_THRESHOLD = 5
PORTAL_LOCKOUT_DURATION_MINUTES = 15


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


def portal_feature_required(view_func):
    """Return 404 if the participant_portal feature toggle is disabled.

    This keeps the entire /my/ URL namespace invisible when the agency
    hasn't turned on the portal.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        flags = FeatureToggle.get_all_flags()
        if not flags.get("participant_portal"):
            raise Http404
        return view_func(request, *args, **kwargs)

    return _wrapped


def portal_login_required(view_func):
    """Require an active participant session.

    Checks:
    1. Feature toggle is enabled (404 if not).
    2. Session contains _portal_participant_id.
    3. The referenced ParticipantUser exists and is active.

    Sets request.participant_user for downstream views.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        # Feature gate
        flags = FeatureToggle.get_all_flags()
        if not flags.get("participant_portal"):
            raise Http404

        # Session check
        participant_id = request.session.get("_portal_participant_id")
        if not participant_id:
            return redirect("portal:login")

        # Load participant user
        from apps.portal.models import ParticipantUser

        try:
            participant = ParticipantUser.objects.select_related(
                "client_file"
            ).get(pk=participant_id, is_active=True)
        except ParticipantUser.DoesNotExist:
            # Stale session — clear it and send to login
            request.session.pop("_portal_participant_id", None)
            return redirect("portal:login")

        request.participant_user = participant
        return view_func(request, *args, **kwargs)

    return _wrapped


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client_file(request):
    """Shorthand to get the client_file from the authenticated participant."""
    return request.participant_user.client_file


def _audit_portal_event(request, action, resource_type="portal", metadata=None):
    """Record a portal event in the audit log."""
    try:
        from apps.audit.models import AuditLog
        from konote.utils import get_client_ip

        participant = getattr(request, "participant_user", None)
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=None,  # Not a staff user
            user_display=f"[portal] {participant.display_name}" if participant else "[portal] anonymous",
            ip_address=get_client_ip(request),
            action=action,
            resource_type=resource_type,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.error("Portal audit log failed (%s): %s", action, e)


# ---------------------------------------------------------------------------
# Phase A: Authentication
# ---------------------------------------------------------------------------


@portal_feature_required
def portal_login(request):
    """Participant login — email + password.

    Handles account lockout (failed_login_count / locked_until on the
    ParticipantUser model) and MFA redirect when enabled.
    """
    from apps.portal.forms import PortalLoginForm
    from apps.portal.models import ParticipantUser

    # Already logged in? Go to dashboard.
    if request.session.get("_portal_participant_id"):
        return redirect("portal:dashboard")

    error = None

    if request.method == "POST":
        form = PortalLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            password = form.cleaned_data["password"]

            # Look up participant by email hash
            email_hash = ParticipantUser.compute_email_hash(email)
            try:
                participant = ParticipantUser.objects.get(
                    email_hash=email_hash, is_active=True
                )
            except ParticipantUser.DoesNotExist:
                # Don't reveal whether the account exists
                error = _("Invalid email or password.")
                _audit_portal_event(request, "portal_login_failed", metadata={
                    "reason": "user_not_found",
                })
                return render(request, "portal/login.html", {
                    "form": form,
                    "error": error,
                })

            # Check lockout
            if participant.locked_until and participant.locked_until > timezone.now():
                error = _(
                    "Too many failed attempts. Please try again in "
                    "%(minutes)d minutes."
                ) % {"minutes": PORTAL_LOCKOUT_DURATION_MINUTES}
                _audit_portal_event(request, "portal_login_failed", metadata={
                    "reason": "account_locked",
                })
                return render(request, "portal/login.html", {
                    "form": form,
                    "error": error,
                })

            # Verify password
            if not participant.check_password(password):
                # Increment failed login counter
                participant.failed_login_count += 1
                if participant.failed_login_count >= PORTAL_LOCKOUT_THRESHOLD:
                    participant.locked_until = timezone.now() + timezone.timedelta(
                        minutes=PORTAL_LOCKOUT_DURATION_MINUTES
                    )
                    error = _(
                        "Too many failed attempts. Please try again in "
                        "%(minutes)d minutes."
                    ) % {"minutes": PORTAL_LOCKOUT_DURATION_MINUTES}
                else:
                    remaining = PORTAL_LOCKOUT_THRESHOLD - participant.failed_login_count
                    error = _("Invalid email or password.")
                participant.save(update_fields=["failed_login_count", "locked_until"])
                _audit_portal_event(request, "portal_login_failed", metadata={
                    "reason": "invalid_password",
                })
                return render(request, "portal/login.html", {
                    "form": form,
                    "error": error,
                })

            # Password correct — check if MFA is required
            if participant.mfa_method and participant.mfa_method != "none":
                # Store participant ID temporarily for MFA verification
                request.session["_portal_mfa_pending_id"] = str(participant.pk)
                return redirect("portal:mfa_verify")

            # No MFA — complete login
            participant.failed_login_count = 0
            participant.locked_until = None
            participant.last_login = timezone.now()
            participant.save(update_fields=[
                "failed_login_count", "locked_until", "last_login",
            ])
            request.session["_portal_participant_id"] = str(participant.pk)
            _audit_portal_event(request, "portal_login", metadata={
                "participant_id": str(participant.pk),
            })
            return redirect("portal:dashboard")
        else:
            error = _("Please enter both your email and password.")
    else:
        form = PortalLoginForm()

    return render(request, "portal/login.html", {
        "form": form,
        "error": error,
    })


@portal_feature_required
def portal_logout(request):
    """Clear the portal session and redirect to login."""
    participant_id = request.session.get("_portal_participant_id")
    if participant_id:
        _audit_portal_event(request, "portal_logout", metadata={
            "participant_id": participant_id,
        })
    request.session.pop("_portal_participant_id", None)
    request.session.pop("_portal_mfa_pending_id", None)
    return redirect("portal:login")


@portal_feature_required
@require_POST
def emergency_logout(request):
    """Quick logout via sendBeacon — for panic/safety button.

    Returns 204 No Content (no redirect, since sendBeacon is fire-and-forget).
    """
    request.session.pop("_portal_participant_id", None)
    request.session.pop("_portal_mfa_pending_id", None)
    return HttpResponse(status=204)


@portal_feature_required
def accept_invite(request, token):
    """Accept a portal invite — register a new ParticipantUser.

    GET: show registration form.
    POST: validate invite token, create account, mark invite accepted.
    """
    from apps.portal.forms import InviteAcceptForm
    from apps.portal.models import ParticipantUser, PortalInvite

    # Look up the invite by token
    try:
        invite = PortalInvite.objects.select_related("client_file").get(token=token)
    except PortalInvite.DoesNotExist:
        raise Http404

    # Check invite is still valid
    if invite.status != "pending":
        return render(request, "portal/invite_status.html", {
            "status": invite.status,
        })

    if invite.expires_at and invite.expires_at < timezone.now():
        invite.status = "expired"
        invite.save(update_fields=["status"])
        return render(request, "portal/invite_status.html", {
            "status": "expired",
        })

    # Check if this client already has a portal account
    existing_account = ParticipantUser.objects.filter(
        client_file=invite.client_file, is_active=True
    ).exists()
    if existing_account:
        return render(request, "portal/invite_status.html", {
            "status": "already_has_access",
        })

    error = None

    if request.method == "POST":
        form = InviteAcceptForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            display_name = form.cleaned_data["display_name"].strip()
            password = form.cleaned_data["password"]

            # Check if email is already used by another participant
            email_hash = ParticipantUser.compute_email_hash(email)
            if ParticipantUser.objects.filter(email_hash=email_hash).exists():
                error = _("This email is already associated with an account.")
            else:
                # Create participant account
                participant = ParticipantUser(
                    client_file=invite.client_file,
                    display_name=display_name,
                )
                participant.email = email  # Uses encrypted property setter
                participant.set_password(password)
                participant.save()

                # Mark invite as accepted
                invite.status = "accepted"
                invite.save(update_fields=["status"])

                _audit_portal_event(request, "portal_invite_accepted", metadata={
                    "participant_id": str(participant.pk),
                    "invite_id": str(invite.pk),
                })

                # Log them in and start consent flow
                request.session["_portal_participant_id"] = str(participant.pk)
                return redirect("portal:consent_flow")
    else:
        form = InviteAcceptForm()

    return render(request, "portal/accept_invite.html", {
        "form": form,
        "invite": invite,
        "error": error,
    })


@portal_login_required
def consent_flow(request):
    """Multi-screen consent flow after registration.

    Tracks which screens have been shown in the PortalInvite's
    consent_screens_shown JSON field. Each POST acknowledges one screen.
    """
    from apps.portal.forms import ConsentScreenForm
    from apps.portal.models import PortalInvite

    participant = request.participant_user

    # Find the invite for this participant's client file
    invite = PortalInvite.objects.filter(
        client_file=participant.client_file,
        status="accepted",
    ).order_by("-created_at").first()

    # Define the consent screens in order
    consent_screens = [
        {
            "id": "privacy",
            "title": _("Your privacy"),
            "content": "privacy_screen",  # Template partial name
        },
        {
            "id": "data_use",
            "title": _("How your information is used"),
            "content": "data_use_screen",
        },
        {
            "id": "rights",
            "title": _("Your rights"),
            "content": "rights_screen",
        },
    ]

    # Determine which screens have been shown
    shown = set()
    if invite and invite.consent_screens_shown:
        shown = set(invite.consent_screens_shown)

    if request.method == "POST":
        form = ConsentScreenForm(request.POST)
        if form.is_valid():
            screen_id = form.cleaned_data["screen_id"]
            shown.add(screen_id)
            if invite:
                invite.consent_screens_shown = list(shown)
                invite.save(update_fields=["consent_screens_shown"])

    # Find the next unshown screen
    next_screen = None
    for screen in consent_screens:
        if screen["id"] not in shown:
            next_screen = screen
            break

    # All screens shown — proceed to dashboard
    if next_screen is None:
        return redirect("portal:dashboard")

    form = ConsentScreenForm(initial={"screen_id": next_screen["id"]})
    return render(request, "portal/consent_flow.html", {
        "screen": next_screen,
        "form": form,
        "progress_current": len(shown) + 1,
        "progress_total": len(consent_screens),
    })


@portal_feature_required
def mfa_setup(request):
    """Set up TOTP-based multi-factor authentication.

    Generates a secret, stores it encrypted, and shows a QR code
    for the participant to scan with their authenticator app.
    """
    from apps.portal.models import ParticipantUser

    participant_id = request.session.get("_portal_participant_id")
    if not participant_id:
        return redirect("portal:login")

    try:
        participant = ParticipantUser.objects.get(pk=participant_id, is_active=True)
    except ParticipantUser.DoesNotExist:
        return redirect("portal:login")

    if request.method == "POST":
        # Generate and store TOTP secret
        import pyotp

        secret = pyotp.random_base32()
        participant.totp_secret = secret  # Uses encrypted property setter
        participant.mfa_method = "totp"
        participant.save(update_fields=["_totp_secret_encrypted", "mfa_method"])

        # Generate provisioning URI for QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=participant.display_name,
            issuer_name="KoNote2 Portal",
        )

        return render(request, "portal/mfa_setup.html", {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "step": "scan",
        })

    return render(request, "portal/mfa_setup.html", {
        "step": "intro",
    })


@portal_feature_required
def mfa_verify(request):
    """Verify a TOTP code — used during login (MFA step) and setup confirmation."""
    from apps.portal.forms import MFAVerifyForm
    from apps.portal.models import ParticipantUser

    # Check for pending MFA session
    participant_id = request.session.get("_portal_mfa_pending_id")
    if not participant_id:
        return redirect("portal:login")

    try:
        participant = ParticipantUser.objects.get(pk=participant_id, is_active=True)
    except ParticipantUser.DoesNotExist:
        request.session.pop("_portal_mfa_pending_id", None)
        return redirect("portal:login")

    error = None

    if request.method == "POST":
        form = MFAVerifyForm(request.POST)
        if form.is_valid():
            import pyotp

            code = form.cleaned_data["code"]
            totp_secret = participant.totp_secret
            if totp_secret:
                totp = pyotp.TOTP(totp_secret)
                if totp.verify(code, valid_window=1):
                    # MFA passed — complete login
                    participant.failed_login_count = 0
                    participant.locked_until = None
                    participant.last_login = timezone.now()
                    participant.save(update_fields=[
                        "failed_login_count", "locked_until", "last_login",
                    ])
                    request.session.pop("_portal_mfa_pending_id", None)
                    request.session["_portal_participant_id"] = str(participant.pk)
                    _audit_portal_event(request, "portal_login", metadata={
                        "participant_id": str(participant.pk),
                        "mfa": True,
                    })
                    return redirect("portal:dashboard")
                else:
                    error = _("Invalid code. Please try again.")
            else:
                error = _("MFA is not configured. Please contact support.")
    else:
        form = MFAVerifyForm()

    return render(request, "portal/mfa_verify.html", {
        "form": form,
        "error": error,
    })


@portal_login_required
def dashboard(request):
    """Participant dashboard — greeting, highlights, navigation.

    Shows the participant's display name, a single highlight (e.g.,
    latest progress note date), and nav links to goals/journal/messages.
    Includes a 'new since last visit' count.
    """
    from apps.notes.models import ProgressNote

    participant = request.participant_user
    client_file = _get_client_file(request)

    # Latest progress note date for this client
    latest_note = (
        ProgressNote.objects.filter(client_file=client_file, status="default")
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )

    # Count of new items since last login
    new_since_last_visit = 0
    if participant.last_login:
        new_since_last_visit = ProgressNote.objects.filter(
            client_file=client_file,
            status="default",
            created_at__gt=participant.last_login,
        ).count()

    return render(request, "portal/dashboard.html", {
        "participant": participant,
        "latest_note_date": latest_note,
        "new_since_last_visit": new_since_last_visit,
    })


@portal_login_required
def settings_view(request):
    """Portal settings — language preference, MFA status, password change link."""
    participant = request.participant_user

    if request.method == "POST":
        # Handle language preference update
        language = request.POST.get("preferred_language")
        if language in [code for code, _name in settings.LANGUAGES]:
            participant.preferred_language = language
            participant.save(update_fields=["preferred_language"])
            from django.utils import translation

            translation.activate(language)
            response = redirect("portal:settings")
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                language,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
            )
            return response

    return render(request, "portal/settings.html", {
        "participant": participant,
        "languages": settings.LANGUAGES,
    })


@portal_login_required
def password_change(request):
    """Change the participant's password."""
    from apps.portal.forms import PortalPasswordChangeForm

    participant = request.participant_user
    error = None
    success = False

    if request.method == "POST":
        form = PortalPasswordChangeForm(request.POST)
        if form.is_valid():
            current_password = form.cleaned_data["current_password"]
            new_password = form.cleaned_data["new_password"]

            if not participant.check_password(current_password):
                error = _("Your current password is incorrect.")
            else:
                participant.set_password(new_password)
                participant.save()
                success = True
                _audit_portal_event(request, "portal_password_changed", metadata={
                    "participant_id": str(participant.pk),
                })
    else:
        form = PortalPasswordChangeForm()

    return render(request, "portal/password_change.html", {
        "form": form,
        "error": error,
        "success": success,
    })


@portal_feature_required
def password_reset_request(request):
    """Request a password reset code via email.

    Always shows success message regardless of whether the email exists,
    to prevent account enumeration.
    """
    from apps.portal.forms import PortalPasswordResetRequestForm

    submitted = False

    if request.method == "POST":
        form = PortalPasswordResetRequestForm(request.POST)
        if form.is_valid():
            # In production, this would send an email with a 6-digit code.
            # The code generation and email sending will be implemented
            # in the email service module.
            submitted = True
            _audit_portal_event(request, "portal_password_reset_requested")
    else:
        form = PortalPasswordResetRequestForm()

    return render(request, "portal/password_reset_request.html", {
        "form": form,
        "submitted": submitted,
    })


@portal_feature_required
def password_reset_confirm(request):
    """Enter the emailed reset code and set a new password."""
    from apps.portal.forms import PortalPasswordResetConfirmForm

    error = None
    success = False

    if request.method == "POST":
        form = PortalPasswordResetConfirmForm(request.POST)
        if form.is_valid():
            # Code verification will be implemented with the email service.
            # For now, this is the form + view structure.
            # TODO: verify code against stored reset token, then set password
            pass
    else:
        form = PortalPasswordResetConfirmForm()

    return render(request, "portal/password_reset_confirm.html", {
        "form": form,
        "error": error,
        "success": success,
    })


@portal_feature_required
def safety_help(request):
    """Pre-auth safety page — no login required.

    Provides information about private browsing, clearing history,
    and the emergency logout button. Accessible without authentication
    so anyone can read it before or after logging in.
    """
    return render(request, "portal/safety_help.html")


# ---------------------------------------------------------------------------
# Phase B: Goals, progress, and corrections
# ---------------------------------------------------------------------------


@portal_login_required
def goals_list(request):
    """'My goals' — plan sections as 'Areas I'm working on'.

    Shows active PlanSections with their PlanTargets, using the
    participant-facing client_goal text.
    """
    from apps.plans.models import PlanSection

    client_file = _get_client_file(request)

    sections = (
        PlanSection.objects.filter(client_file=client_file, status="default")
        .prefetch_related("targets")
        .order_by("sort_order")
    )

    # Build a list of sections with only active targets
    sections_with_targets = []
    for section in sections:
        active_targets = [
            t for t in section.targets.all() if t.status == "default"
        ]
        if active_targets:
            sections_with_targets.append({
                "section": section,
                "targets": active_targets,
            })

    return render(request, "portal/goals.html", {
        "sections_with_targets": sections_with_targets,
    })


@portal_login_required
def goal_detail(request, target_id):
    """Single goal detail — name, description, client_goal, progress timeline, metrics.

    CRITICAL: Always scoped to the participant's client_file.
    """
    from apps.notes.models import MetricValue, ProgressNoteTarget
    from apps.plans.models import PlanTarget, PlanTargetMetric

    client_file = _get_client_file(request)

    # Scoped lookup — prevents accessing another client's data
    target = get_object_or_404(PlanTarget, pk=target_id, client_file=client_file)

    # Progress descriptor timeline from progress notes
    progress_entries = (
        ProgressNoteTarget.objects.filter(
            plan_target=target,
            progress_note__client_file=client_file,
            progress_note__status="default",
        )
        .select_related("progress_note")
        .order_by("-progress_note__created_at")
    )

    # Metric data for charts — only portal-visible metrics
    assigned_metrics = PlanTargetMetric.objects.filter(
        plan_target=target,
    ).select_related("metric_def")

    # Filter to portal-visible metrics
    chart_data = {}
    for ptm in assigned_metrics:
        metric_def = ptm.metric_def
        if getattr(metric_def, "portal_visibility", "no") == "no":
            continue

        # Get metric values for this target + metric def
        values = (
            MetricValue.objects.filter(
                progress_note_target__plan_target=target,
                progress_note_target__progress_note__client_file=client_file,
                progress_note_target__progress_note__status="default",
                metric_def=metric_def,
            )
            .select_related("progress_note_target__progress_note")
            .order_by("progress_note_target__progress_note__created_at")
        )

        if values.exists():
            chart_data[metric_def.name] = {
                "labels": [
                    v.progress_note_target.progress_note.created_at.strftime("%Y-%m-%d")
                    for v in values
                ],
                "values": [v.value for v in values],
                "unit": metric_def.unit or "",
                "min_value": metric_def.min_value,
                "max_value": metric_def.max_value,
            }

    return render(request, "portal/goal_detail.html", {
        "target": target,
        "progress_entries": progress_entries,
        "chart_data_json": json.dumps(chart_data),
    })


@portal_login_required
def progress_view(request):
    """Overall progress charts for all portal-visible metrics.

    Passes metric data as JSON via json_script for Chart.js rendering.
    Only includes metrics where MetricDefinition.portal_visibility != 'no'.
    """
    from apps.notes.models import MetricValue
    from apps.plans.models import MetricDefinition, PlanTargetMetric

    client_file = _get_client_file(request)

    # Get all metric definitions that are portal-visible
    visible_metric_ids = (
        MetricDefinition.objects.exclude(portal_visibility="no")
        .values_list("pk", flat=True)
    )

    # Get metric values for this client's targets, filtered to visible metrics
    values = (
        MetricValue.objects.filter(
            progress_note_target__progress_note__client_file=client_file,
            progress_note_target__progress_note__status="default",
            metric_def_id__in=visible_metric_ids,
        )
        .select_related(
            "metric_def",
            "progress_note_target__progress_note",
            "progress_note_target__plan_target",
        )
        .order_by("progress_note_target__progress_note__created_at")
    )

    # Group by metric definition for chart rendering
    metrics_data = {}
    for mv in values:
        metric_name = mv.metric_def.name
        if metric_name not in metrics_data:
            metrics_data[metric_name] = {
                "labels": [],
                "values": [],
                "unit": mv.metric_def.unit or "",
                "min_value": mv.metric_def.min_value,
                "max_value": mv.metric_def.max_value,
            }
        note_date = mv.progress_note_target.progress_note.created_at.strftime("%Y-%m-%d")
        metrics_data[metric_name]["labels"].append(note_date)
        metrics_data[metric_name]["values"].append(mv.value)

    return render(request, "portal/progress.html", {
        "metrics_data_json": json.dumps(metrics_data),
        "has_data": bool(metrics_data),
    })


@portal_login_required
def my_words(request):
    """'What I've been saying' — participant reflections and client words.

    Collects participant_reflection from ProgressNote and client_words
    from ProgressNoteTarget, displayed in reverse date order.
    """
    from apps.notes.models import ProgressNote, ProgressNoteTarget

    client_file = _get_client_file(request)

    # Get progress notes with participant reflections
    notes_with_reflections = (
        ProgressNote.objects.filter(
            client_file=client_file,
            status="default",
        )
        .order_by("-created_at")
    )

    # Build a combined list of reflections and client words
    entries = []
    for note in notes_with_reflections:
        # Add participant reflection if present
        reflection = note.participant_reflection
        if reflection:
            entries.append({
                "type": "reflection",
                "text": reflection,
                "date": note.created_at,
            })

        # Add client_words from each target entry
        target_entries = ProgressNoteTarget.objects.filter(
            progress_note=note,
        ).select_related("plan_target")

        for te in target_entries:
            client_words = te.client_words
            if client_words:
                entries.append({
                    "type": "client_words",
                    "text": client_words,
                    "date": note.created_at,
                    "target_name": te.plan_target.name if te.plan_target else "",
                })

    # Already ordered by note date (descending) due to outer query order
    return render(request, "portal/my_words.html", {
        "entries": entries,
    })


@portal_login_required
def milestones(request):
    """Completed goals — plan targets with status='completed'."""
    from apps.plans.models import PlanTarget

    client_file = _get_client_file(request)

    completed_targets = (
        PlanTarget.objects.filter(
            client_file=client_file,
            status="completed",
        )
        .select_related("plan_section")
        .order_by("-updated_at")
    )

    return render(request, "portal/milestones.html", {
        "completed_targets": completed_targets,
    })


@portal_login_required
def correction_request_create(request):
    """Request a correction to recorded information.

    Implements a soft step first: the template shows a message suggesting
    the participant discuss the concern with their worker before submitting
    a formal correction request.
    """
    from apps.portal.forms import CorrectionRequestForm
    from apps.portal.models import CorrectionRequest

    client_file = _get_client_file(request)
    participant = request.participant_user
    success = False

    if request.method == "POST":
        # Check if this is the 'soft step' acknowledgement
        if "proceed_to_form" in request.POST:
            # Show the full form
            form = CorrectionRequestForm()
            return render(request, "portal/correction_request.html", {
                "form": form,
                "show_form": True,
            })

        form = CorrectionRequestForm(request.POST)
        if form.is_valid():
            correction = CorrectionRequest(
                participant_user=participant,
                client_file=client_file,
                data_type=form.cleaned_data["data_type"],
                object_id=form.cleaned_data["object_id"],
                status="pending",
            )
            correction.description = form.cleaned_data["description"]
            correction.save()

            _audit_portal_event(request, "portal_correction_requested", metadata={
                "participant_id": str(participant.pk),
                "correction_id": str(correction.pk),
                "data_type": form.cleaned_data["data_type"],
            })
            success = True
    else:
        form = None

    return render(request, "portal/correction_request.html", {
        "form": form,
        "show_form": False,
        "success": success,
    })


# ---------------------------------------------------------------------------
# Phase C: Journal, messages, discuss next (stubs)
# ---------------------------------------------------------------------------


@portal_login_required
def journal_list(request):
    """List the participant's journal entries.

    Checks whether the journal disclosure has been shown; if not,
    redirects to the disclosure page first.
    """
    from apps.portal.models import ParticipantJournalEntry

    participant = request.participant_user
    client_file = _get_client_file(request)

    # Check if disclosure has been shown
    if not participant.journal_disclosure_shown:
        return redirect("portal:journal_disclosure")

    entries = (
        ParticipantJournalEntry.objects.filter(
            participant_user=participant,
            client_file=client_file,
        )
        .order_by("-created_at")
    )

    return render(request, "portal/journal.html", {
        "journal_entries": entries,
    })


@portal_login_required
def journal_create(request):
    """Create a new journal entry."""
    from apps.portal.forms import JournalEntryForm
    from apps.portal.models import ParticipantJournalEntry

    participant = request.participant_user
    client_file = _get_client_file(request)

    # Ensure disclosure has been shown
    if not participant.journal_disclosure_shown:
        return redirect("portal:journal_disclosure")

    if request.method == "POST":
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            entry = ParticipantJournalEntry(
                participant_user=participant,
                client_file=client_file,
            )
            entry.content = form.cleaned_data["content"]

            # Optionally link to a plan target
            target_id = form.cleaned_data.get("plan_target")
            if target_id:
                from apps.plans.models import PlanTarget

                target = get_object_or_404(
                    PlanTarget, pk=target_id, client_file=client_file
                )
                entry.plan_target = target

            entry.save()
            return redirect("portal:journal")
    else:
        form = JournalEntryForm()

    return render(request, "portal/journal_create.html", {
        "form": form,
    })


@portal_login_required
def journal_disclosure(request):
    """One-time privacy notice for the journal feature.

    Explains what the journal is, who can see it, and data retention.
    Marks journal_disclosure_shown=True on acceptance.
    """
    participant = request.participant_user

    if request.method == "POST":
        participant.journal_disclosure_shown = True
        participant.save(update_fields=["journal_disclosure_shown"])
        return redirect("portal:journal")

    return render(request, "portal/journal_disclosure.html", {
        "participant": participant,
    })


@portal_login_required
def message_create(request):
    """'Message to My Worker' — send a message to the assigned staff."""
    from apps.portal.forms import MessageForm
    from apps.portal.models import ParticipantMessage

    participant = request.participant_user
    client_file = _get_client_file(request)
    success = False

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = ParticipantMessage(
                participant_user=participant,
                client_file=client_file,
                message_type=form.cleaned_data.get("message_type", "general"),
            )
            message.content = form.cleaned_data["content"]
            message.save()

            _audit_portal_event(request, "portal_message_sent", metadata={
                "participant_id": str(participant.pk),
                "message_type": message.message_type,
            })
            success = True
    else:
        form = MessageForm()

    return render(request, "portal/message_to_worker.html", {
        "form": form,
        "success": success,
    })


@portal_login_required
def discuss_next(request):
    """'What I want to discuss next time' — pre-session prompt.

    Creates a ParticipantMessage with message_type='pre_session'.
    This appears inline in the staff client view.
    """
    from apps.portal.forms import PreSessionForm
    from apps.portal.models import ParticipantMessage

    participant = request.participant_user
    client_file = _get_client_file(request)
    success = False

    # Show the most recent pre-session message if one exists
    existing = (
        ParticipantMessage.objects.filter(
            participant_user=participant,
            client_file=client_file,
            message_type="pre_session",
            archived_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )

    if request.method == "POST":
        form = PreSessionForm(request.POST)
        if form.is_valid():
            message = ParticipantMessage(
                participant_user=participant,
                client_file=client_file,
                message_type="pre_session",
            )
            message.content = form.cleaned_data["content"]
            message.save()

            _audit_portal_event(request, "portal_discuss_next_saved", metadata={
                "participant_id": str(participant.pk),
            })
            success = True
    else:
        form = PreSessionForm()

    return render(request, "portal/discuss_next.html", {
        "form": form,
        "existing": existing,
        "success": success,
    })
