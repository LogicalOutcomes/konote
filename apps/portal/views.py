"""Views for the participant portal.

The portal is a separate, participant-facing interface. It uses its own
session key (_portal_participant_id) and does NOT use Django's built-in
auth system — participants are ParticipantUser, not User.

Data isolation: every view scopes queries to request.participant_user.client_file.
Sub-objects are always fetched with get_object_or_404(..., client_file=client_file).
"""
import json
import logging
import secrets
from functools import wraps

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.admin_settings.models import FeatureToggle

logger = logging.getLogger(__name__)

# Account lockout settings for participant login
PORTAL_LOCKOUT_THRESHOLD = 5
PORTAL_LOCKOUT_DURATION_MINUTES = 15


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

SESSION_EMERGENCY_LOGOUT_TOKEN = "_portal_emergency_logout_token"


def _set_emergency_logout_token(request):
    """Generate and store a single-use emergency logout token in the session.

    Called at every portal login point so the JavaScript panic button can
    include the token when it calls navigator.sendBeacon(). The token is
    validated in emergency_logout() and removed after use, preventing replay.
    """
    request.session[SESSION_EMERGENCY_LOGOUT_TOKEN] = secrets.token_urlsafe(32)


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
            user_display=f"[portal] {participant.pk}" if participant else "[portal] anonymous",
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
            if participant.mfa_method and participant.mfa_method not in ("none", "exempt"):
                # Store participant ID temporarily for MFA verification
                request.session["_portal_mfa_pending_id"] = str(participant.pk)
                request.session["_portal_mfa_pending_at"] = timezone.now().isoformat()
                return redirect("portal:mfa_verify")

            # No MFA — complete login
            participant.failed_login_count = 0
            participant.locked_until = None
            participant.last_login = timezone.now()
            participant.save(update_fields=[
                "failed_login_count", "locked_until", "last_login",
            ])
            request.session.cycle_key()  # Prevent session fixation
            request.session["_portal_participant_id"] = str(participant.pk)
            _set_emergency_logout_token(request)
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
        "demo_mode": settings.DEMO_MODE,
    })


@portal_feature_required
@require_POST
def portal_logout(request):
    """Clear the portal session and redirect to login."""
    participant_id = request.session.get("_portal_participant_id")
    if participant_id:
        _audit_portal_event(request, "portal_logout", metadata={
            "participant_id": participant_id,
        })
    request.session.flush()
    return redirect("portal:login")


@csrf_exempt  # sendBeacon cannot include CSRF tokens
@portal_feature_required
@require_POST
def emergency_logout(request):
    """Quick logout via sendBeacon — for panic/safety button.

    Returns 204 No Content (no redirect, since sendBeacon is fire-and-forget).

    csrf_exempt is intentional: sendBeacon() cannot attach CSRF tokens because
    it uses Content-Type text/plain and fires asynchronously. As a compensating
    control we require a session-bound single-use token that only the legitimate
    portal page can supply. A cross-origin attacker cannot read the token because
    of the browser's same-origin policy on the session cookie.
    """
    # Validate the session-bound emergency logout token.
    # The token is set on portal login and sent by portal.js via sendBeacon.
    # We use secrets.compare_digest to prevent timing-based attacks.
    expected = request.session.get(SESSION_EMERGENCY_LOGOUT_TOKEN, "")
    submitted = request.POST.get("token", "")
    if not expected or not secrets.compare_digest(expected, submitted):
        return HttpResponse(status=403)

    # Token is single-use — remove it before flushing so it cannot be replayed.
    request.session.pop(SESSION_EMERGENCY_LOGOUT_TOKEN, None)
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

    # Determine if verbal code is required for this invite
    requires_verbal_code = bool(invite.verbal_code)

    if request.method == "POST":
        form = InviteAcceptForm(request.POST)
        if form.is_valid():
            # Enforce verbal code when the invite has one set
            if requires_verbal_code:
                submitted_code = form.cleaned_data.get("verbal_code", "").strip()
                if submitted_code != invite.verbal_code:
                    error = _("The verification code is incorrect. Please check with your worker.")
                    return render(request, "portal/accept_invite.html", {
                        "form": form,
                        "invite": invite,
                        "error": error,
                        "requires_verbal_code": requires_verbal_code,
                    })

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
                request.session.cycle_key()  # Prevent session fixation
                request.session["_portal_participant_id"] = str(participant.pk)
                _set_emergency_logout_token(request)
                return redirect("portal:consent_flow")
    else:
        form = InviteAcceptForm()

    return render(request, "portal/accept_invite.html", {
        "form": form,
        "invite": invite,
        "error": error,
        "requires_verbal_code": requires_verbal_code,
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
            issuer_name="KoNote Portal",
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
    mfa_started_at = request.session.get("_portal_mfa_pending_at")
    if not participant_id:
        return redirect("portal:login")

    # Expire MFA challenge after 5 minutes
    if mfa_started_at:
        from django.utils.dateparse import parse_datetime
        try:
            started = parse_datetime(mfa_started_at)
            if started and (timezone.now() - started).total_seconds() > 300:
                request.session.pop("_portal_mfa_pending_id", None)
                request.session.pop("_portal_mfa_pending_at", None)
                request.session.pop("_portal_mfa_attempts", None)
                return redirect("portal:login")
        except (ValueError, TypeError):
            pass

    try:
        participant = ParticipantUser.objects.get(pk=participant_id, is_active=True)
    except ParticipantUser.DoesNotExist:
        request.session.pop("_portal_mfa_pending_id", None)
        request.session.pop("_portal_mfa_pending_at", None)
        request.session.pop("_portal_mfa_attempts", None)
        return redirect("portal:login")

    error = None

    if request.method == "POST":
        form = MFAVerifyForm(request.POST)
        if form.is_valid():
            import pyotp

            # Check brute-force attempt limit (5 attempts max)
            attempts = request.session.get("_portal_mfa_attempts", 0) + 1
            request.session["_portal_mfa_attempts"] = attempts
            if attempts > 5:
                request.session.pop("_portal_mfa_pending_id", None)
                request.session.pop("_portal_mfa_pending_at", None)
                request.session.pop("_portal_mfa_attempts", None)
                _audit_portal_event(request, "portal_mfa_lockout", metadata={
                    "participant_id": participant_id,
                    "attempts": attempts,
                })
                return redirect("portal:login")

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
                    request.session.pop("_portal_mfa_pending_at", None)
                    request.session.pop("_portal_mfa_attempts", None)
                    request.session.cycle_key()  # Prevent session fixation
                    request.session["_portal_participant_id"] = str(participant.pk)
                    _set_emergency_logout_token(request)
                    _audit_portal_event(request, "portal_login", metadata={
                        "participant_id": str(participant.pk),
                        "mfa": True,
                    })
                    return redirect("portal:dashboard")
                else:
                    remaining = 5 - attempts
                    if remaining > 0:
                        error = _("Invalid code. %(remaining)d attempts remaining.") % {
                            "remaining": remaining,
                        }
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
    from apps.plans.models import PlanTarget
    from apps.portal.models import StaffPortalNote

    participant = request.participant_user
    client_file = _get_client_file(request)

    # Pending surveys count + smart single-survey link
    pending_surveys = 0
    single_survey_url = None
    try:
        from django.urls import reverse
        from apps.surveys.engine import is_surveys_enabled
        from apps.surveys.models import SurveyAssignment
        if is_surveys_enabled():
            survey_assignments = SurveyAssignment.objects.filter(
                participant_user=participant,
                status__in=("pending", "in_progress"),
                survey__portal_visible=True,
            )
            pending_surveys = survey_assignments.count()
            if pending_surveys == 1:
                single_survey_url = reverse(
                    "portal:survey_fill",
                    args=[survey_assignments.first().pk],
                )
    except Exception:
        pass

    # Latest progress note date for this client
    latest_note = (
        ProgressNote.objects.filter(client_file=client_file, status="default")
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )

    # Count and detail of new items since last login
    new_count = 0
    new_details = {}
    if participant.last_login:
        notes_count = ProgressNote.objects.filter(
            client_file=client_file,
            status="default",
            created_at__gt=participant.last_login,
        ).count()
        goals_count = PlanTarget.objects.filter(
            client_file=client_file,
            status="default",
            updated_at__gt=participant.last_login,
        ).count()
        new_count = notes_count + goals_count
        new_details = {
            "notes_count": notes_count,
            "goals_count": goals_count,
        }

    # Staff notes for this participant (most recent, active only)
    staff_notes = StaffPortalNote.objects.filter(
        client_file=client_file, is_active=True,
    )[:5]

    # Build a highlight message from the latest progress note date
    highlight_message = ""
    if latest_note:
        from django.utils.formats import date_format
        formatted = date_format(latest_note, "N j, Y")
        highlight_message = _("Your last session was recorded on %(date)s.") % {
            "date": formatted,
        }

    return render(request, "portal/dashboard.html", {
        "participant": participant,
        "latest_note_date": latest_note,
        "highlight_message": highlight_message,
        "new_count": new_count,
        "new_details": new_details,
        "staff_notes": staff_notes,
        "pending_surveys": pending_surveys,
        "single_survey_url": single_survey_url,
    })


@portal_login_required
def resources_list(request):
    """Show helpful resource links from programs and staff."""
    participant = request.participant_user
    client_file = _get_client_file(request)
    lang = participant.preferred_language or "en"

    flags = FeatureToggle.get_all_flags()
    from apps.admin_settings.views import FEATURES_DEFAULT_ENABLED
    if not flags.get("portal_resources", "portal_resources" in FEATURES_DEFAULT_ENABLED):
        raise Http404

    from apps.clients.models import ClientProgramEnrolment
    from apps.portal.models import ClientResourceLink, PortalResourceLink

    # Get active program IDs for this participant
    active_program_ids = list(
        ClientProgramEnrolment.objects.filter(
            client_file=client_file, status="enrolled",
        ).values_list("program_id", flat=True)
    )

    # Program-level resources
    program_resources = PortalResourceLink.objects.filter(
        program_id__in=active_program_ids, is_active=True,
    ).select_related("program").order_by("display_order", "title")

    # Client-specific resources
    client_resources = ClientResourceLink.objects.filter(
        client_file=client_file, is_active=True,
    ).order_by("-created_at")

    # Build display list with resolved language
    display_resources = []
    for r in program_resources:
        display_resources.append({
            "title": r.get_title(lang),
            "url": r.url,
            "description": r.get_description(lang),
            "source": "program",
            "program_name": r.program.portal_display_name or r.program.name,
        })
    for r in client_resources:
        display_resources.append({
            "title": r.title,
            "url": r.url,
            "description": r.description,
            "source": "staff",
        })

    return render(request, "portal/resources.html", {
        "resources": display_resources,
        "has_resources": len(display_resources) > 0,
    })


@portal_login_required
def settings_view(request):
    """Portal settings — MFA status, password change link."""
    participant = request.participant_user

    return render(request, "portal/settings.html", {
        "participant": participant,
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
                participant.save(update_fields=["password"])
                # Rotate session so compromised sessions are invalidated
                request.session.cycle_key()
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
    to prevent account enumeration. Rate limited to 3 requests per hour.
    """
    from apps.portal.forms import PortalPasswordResetRequestForm
    from apps.portal.models import ParticipantUser
    import secrets
    from datetime import timedelta
    from django.contrib.auth.hashers import make_password
    from django.core.mail import send_mail

    submitted = False

    if request.method == "POST":
        form = PortalPasswordResetRequestForm(request.POST)
        if form.is_valid():
            submitted = True
            email = form.cleaned_data["email"].strip().lower()
            email_hash = ParticipantUser.compute_email_hash(email)

            try:
                participant = ParticipantUser.objects.get(
                    email_hash=email_hash, is_active=True
                )
            except ParticipantUser.DoesNotExist:
                # Don't reveal — show success anyway
                _audit_portal_event(request, "portal_password_reset_requested", metadata={
                    "found": False,
                })
            else:
                if participant.can_request_password_reset():
                    # Generate 6-digit code
                    code = f"{secrets.randbelow(1000000):06d}"
                    participant.password_reset_token_hash = make_password(code)
                    participant.password_reset_expires = timezone.now() + timedelta(minutes=10)
                    participant.password_reset_request_count += 1
                    participant.password_reset_last_request = timezone.now()
                    participant.save(update_fields=[
                        "password_reset_token_hash", "password_reset_expires",
                        "password_reset_request_count", "password_reset_last_request",
                    ])

                    # Send email with the code
                    try:
                        send_mail(
                            subject=_("Your password reset code"),
                            message=_(
                                "Your password reset code is: %(code)s\n\n"
                                "This code expires in 10 minutes.\n"
                                "If you did not request this, you can ignore this email."
                            ) % {"code": code},
                            from_email=None,  # Uses DEFAULT_FROM_EMAIL
                            recipient_list=[participant.email],
                            fail_silently=True,
                        )
                    except Exception:
                        logger.exception("Failed to send portal password reset email")

                _audit_portal_event(request, "portal_password_reset_requested", metadata={
                    "found": True,
                })
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
    from apps.portal.models import ParticipantUser
    from django.contrib.auth.hashers import check_password

    error = None
    success = False

    if request.method == "POST":
        form = PortalPasswordResetConfirmForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            code = form.cleaned_data["code"].strip()
            new_password = form.cleaned_data["new_password"]

            email_hash = ParticipantUser.compute_email_hash(email)
            try:
                participant = ParticipantUser.objects.get(
                    email_hash=email_hash, is_active=True
                )
            except ParticipantUser.DoesNotExist:
                error = _("Invalid code or email address.")
            else:
                # Check expiry
                if not participant.password_reset_expires or participant.password_reset_expires < timezone.now():
                    error = _("This code has expired. Please request a new one.")
                elif not participant.password_reset_token_hash:
                    error = _("No reset code has been requested.")
                elif not check_password(code, participant.password_reset_token_hash):
                    error = _("Invalid code or email address.")
                else:
                    # Code valid — set new password and clear reset fields
                    participant.set_password(new_password)
                    participant.password_reset_token_hash = ""
                    participant.password_reset_expires = None
                    participant.password_reset_request_count = 0
                    participant.save(update_fields=[
                        "password", "password_reset_token_hash",
                        "password_reset_expires", "password_reset_request_count",
                    ])
                    _audit_portal_event(request, "portal_password_reset_completed", metadata={
                        "participant_id": str(participant.pk),
                    })
                    success = True
    else:
        form = PortalPasswordResetConfirmForm()

    return render(request, "portal/password_reset_confirm.html", {
        "form": form,
        "error": error,
        "success": success,
    })


@portal_feature_required
def staff_assisted_login(request, token):
    """Log a participant in via a staff-generated one-time token."""
    from apps.portal.models import StaffAssistedLoginToken

    try:
        token_obj = StaffAssistedLoginToken.objects.select_related(
            "participant_user"
        ).get(token=token)
    except StaffAssistedLoginToken.DoesNotExist:
        raise Http404

    if not token_obj.is_valid:
        token_obj.delete()
        raise Http404

    participant = token_obj.participant_user
    if not participant.is_active:
        token_obj.delete()
        raise Http404

    # Consume the token
    token_obj.delete()

    # Create session
    request.session.cycle_key()
    request.session["_portal_participant_id"] = str(participant.pk)
    _set_emergency_logout_token(request)
    # Mark this as a staff-assisted session (shorter max age)
    request.session["_portal_staff_assisted"] = True
    request.session.set_expiry(30 * 60)  # 30 minutes max

    participant.last_login = timezone.now()
    participant.save(update_fields=["last_login"])

    _audit_portal_event(request, "portal_staff_assisted_login", metadata={
        "participant_id": str(participant.pk),
    })

    return redirect("portal:dashboard")


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
    from apps.notes.models import ProgressNoteTarget
    from apps.plans.models import PlanSection

    client_file = _get_client_file(request)

    sections = (
        PlanSection.objects.filter(client_file=client_file, status="default")
        .prefetch_related("targets")
        .order_by("sort_order")
    )

    # Build a list of sections with only active targets.
    # Attach filtered targets directly to each section object so
    # the template can access section.id, section.name, section.targets.
    filtered_sections = []
    for section in sections:
        active_targets = [
            t for t in section.targets.all() if t.status == "default"
        ]
        if active_targets:
            # Attach latest progress descriptor to each target
            for target in active_targets:
                latest_entry = (
                    ProgressNoteTarget.objects.filter(
                        plan_target=target,
                        progress_note__client_file=client_file,
                        progress_note__status="default",
                    )
                    .exclude(progress_descriptor="")
                    .order_by("-progress_note__created_at")
                    .first()
                )
                target.latest_descriptor = (
                    latest_entry.get_progress_descriptor_display()
                    if latest_entry
                    else ""
                )
            section.active_targets = active_targets
            filtered_sections.append(section)

    return render(request, "portal/goals.html", {
        "sections": filtered_sections,
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

    # Build descriptors list for template: [{date, descriptor}, ...]
    descriptors = []
    client_words_list = []
    for entry in progress_entries:
        if entry.progress_descriptor:
            descriptors.append({
                "date": entry.progress_note.created_at,
                "descriptor": entry.get_progress_descriptor_display(),
            })
        words = entry.client_words
        if words:
            client_words_list.append({
                "date": entry.progress_note.created_at,
                "text": words,
            })

    # Metric data for charts — only portal-visible metrics
    assigned_metrics = PlanTargetMetric.objects.filter(
        plan_target=target,
    ).select_related("metric_def")

    # Build chart_data as a list of chart objects for the template JS.
    # Each chart has: metric_name, labels, values, unit, description,
    # min_value, max_value, begin_at_zero.
    chart_data = []
    for ptm in assigned_metrics:
        metric_def = ptm.metric_def
        if getattr(metric_def, "portal_visibility", "no") == "no":
            continue

        # Get metric values for this target + metric def
        values = list(
            MetricValue.objects.filter(
                progress_note_target__plan_target=target,
                progress_note_target__progress_note__client_file=client_file,
                progress_note_target__progress_note__status="default",
                metric_def=metric_def,
            )
            .select_related("progress_note_target__progress_note")
            .order_by("progress_note_target__progress_note__created_at")
        )

        if values:
            chart_data.append({
                "metric_name": metric_def.translated_name,
                "labels": [
                    v.progress_note_target.progress_note.created_at.strftime("%Y-%m-%d")
                    for v in values
                ],
                "values": [v.value for v in values],
                "unit": metric_def.translated_unit or "",
                "min_value": metric_def.min_value,
                "max_value": metric_def.max_value,
                "description": metric_def.translated_portal_description or "",
                "begin_at_zero": metric_def.min_value == 0 if metric_def.min_value is not None else False,
            })

    return render(request, "portal/goal_detail.html", {
        "target": target,
        "descriptors": descriptors,
        "client_words": client_words_list,
        "chart_data": chart_data,
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
        metric_name = mv.metric_def.translated_name
        if metric_name not in metrics_data:
            metrics_data[metric_name] = {
                "labels": [],
                "values": [],
                "unit": mv.metric_def.translated_unit or "",
                "min_value": mv.metric_def.min_value,
                "max_value": mv.metric_def.max_value,
                "description": mv.metric_def.translated_portal_description or "",
                "goal_names": set(),
            }
        note_date = mv.progress_note_target.progress_note.created_at.strftime("%Y-%m-%d")
        metrics_data[metric_name]["labels"].append(note_date)
        metrics_data[metric_name]["values"].append(mv.value)
        # Track which goals this metric is associated with
        target = mv.progress_note_target.plan_target
        if target and target.name:
            metrics_data[metric_name]["goal_names"].add(target.name)

    # Convert to list format expected by the template JS
    # (sets are not JSON-serialisable, so convert to sorted list)
    chart_data = []
    for name, data in metrics_data.items():
        entry = {"metric_name": name}
        for k, v in data.items():
            entry[k] = sorted(v) if isinstance(v, set) else v
        # Add start/current value summary for the template
        vals = entry.get("values", [])
        if vals:
            entry["start_value"] = vals[0]
            entry["current_value"] = vals[-1]
            entry["start_label"] = str(_("Started at"))
            entry["current_label"] = str(_("Now at"))
        entry["begin_at_zero"] = (
            entry.get("min_value") == 0
            if entry.get("min_value") is not None
            else False
        )
        chart_data.append(entry)

    return render(request, "portal/progress.html", {
        "chart_data": chart_data,
        "has_data": bool(metrics_data),
    })


@portal_login_required
def my_words(request):
    """'What I've been saying' — participant reflections and client words.

    Collects participant_reflection from ProgressNote and client_words
    from ProgressNoteTarget, displayed in reverse date order.

    Template uses {% regroup reflections by session_date %}, so each
    entry needs: session_date, participant_reflection, client_words,
    goal_name.
    """
    from apps.notes.models import ProgressNote, ProgressNoteTarget

    client_file = _get_client_file(request)

    # Get progress notes ordered by date (newest first)
    notes = (
        ProgressNote.objects.filter(
            client_file=client_file,
            status="default",
        )
        .order_by("-created_at")
    )

    # Build entries in the format the template expects.
    # Each entry has: session_date, participant_reflection, client_words,
    # goal_name. One entry per note-target pair (or per note if only
    # a general reflection).
    reflections = []
    for note in notes:
        reflection = note.participant_reflection
        target_entries = (
            ProgressNoteTarget.objects.filter(progress_note=note)
            .select_related("plan_target")
        )

        has_words = False
        for te in target_entries:
            words = te.client_words
            if words:
                has_words = True
                reflections.append({
                    "session_date": note.created_at.date(),
                    "participant_reflection": "",
                    "client_words": words,
                    "goal_name": te.plan_target.name if te.plan_target else "",
                })

        # Add the general reflection once per note (not per target)
        if reflection:
            reflections.append({
                "session_date": note.created_at.date(),
                "participant_reflection": reflection,
                "client_words": "",
                "goal_name": "",
            })

    return render(request, "portal/my_words.html", {
        "reflections": reflections,
    })


@portal_login_required
def milestones(request):
    """Completed goals — plan targets with status='completed'.

    Template expects 'milestones' variable where each item has
    .name, .client_goal, and .completion_date.
    """
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

    # Attach completion_date (alias for updated_at) for template
    milestone_list = list(completed_targets)
    for target in milestone_list:
        target.completion_date = target.updated_at

    return render(request, "portal/milestones.html", {
        "milestones": milestone_list,
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
            # IDOR protection: verify the referenced object belongs to
            # this participant's client_file before creating a correction.
            object_id = form.cleaned_data["object_id"]
            data_type = form.cleaned_data["data_type"]

            if data_type == "goal":
                from apps.plans.models import PlanTarget
                if not PlanTarget.objects.filter(pk=object_id, client_file=client_file).exists():
                    raise Http404
            elif data_type == "metric":
                from apps.plans.models import PlanTargetMetric
                if not PlanTargetMetric.objects.filter(
                    pk=object_id, plan_target__client_file=client_file
                ).exists():
                    raise Http404
            elif data_type == "reflection":
                from apps.notes.models import ProgressNote
                if not ProgressNote.objects.filter(pk=object_id, client_file=client_file).exists():
                    raise Http404
            else:
                raise Http404

            correction = CorrectionRequest(
                participant_user=participant,
                client_file=client_file,
                data_type=data_type,
                object_id=object_id,
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
        # GET with ?form=1 means participant chose "Submit a request now"
        if request.GET.get("form"):
            form = CorrectionRequestForm()
            return render(request, "portal/correction_request.html", {
                "form": form,
                "show_form": True,
            })
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

    # Recent sent messages for this participant
    recent_messages = (
        ParticipantMessage.objects.filter(
            participant_user=participant,
            client_file=client_file,
            message_type="general",
        )
        .order_by("-created_at")[:10]
    )

    return render(request, "portal/message_to_worker.html", {
        "form": form,
        "success": success,
        "recent_messages": recent_messages,
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


# ---------------------------------------------------------------------------
# Surveys — participant-facing survey views
# ---------------------------------------------------------------------------


@portal_login_required
def portal_surveys_list(request):
    """Show pending survey assignments for the logged-in participant."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import SurveyAssignment, SurveyResponse

    if not is_surveys_enabled():
        raise Http404

    participant = request.participant_user
    client_file = _get_client_file(request)

    # Pending / in-progress assignments
    assignments = SurveyAssignment.objects.filter(
        participant_user=participant,
        status__in=("pending", "in_progress"),
        survey__portal_visible=True,
    ).select_related("survey").order_by("-created_at")

    # Completed responses
    responses = SurveyResponse.objects.filter(
        client_file=client_file,
        channel__in=("portal", "staff_entered"),
    ).select_related("survey").order_by("-submitted_at")[:20]

    return render(request, "portal/surveys_list.html", {
        "participant": participant,
        "assignments": assignments,
        "responses": responses,
    })


@portal_login_required
def portal_survey_fill(request, assignment_id):
    """Fill in a survey — supports multi-page and auto-save."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import (
        PartialAnswer,
        SurveyAnswer,
        SurveyAssignment,
        SurveyResponse,
    )
    from apps.portal.survey_helpers import (
        group_sections_into_pages, filter_visible_sections,
        get_partial_answers_dict, calculate_section_scores,
    )
    from konote.encryption import decrypt_field

    if not is_surveys_enabled():
        raise Http404

    participant = request.participant_user
    client_file = _get_client_file(request)

    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status__in=("pending", "in_progress"),
    )
    survey = assignment.survey

    # Mark as in_progress on first visit
    if assignment.status == "pending":
        assignment.status = "in_progress"
        assignment.started_at = timezone.now()
        assignment.save(update_fields=["status", "started_at"])

    # Load all sections and partial answers
    all_sections = list(
        survey.sections.filter(is_active=True)
        .prefetch_related("questions")
        .order_by("sort_order")
    )
    partial_answers = get_partial_answers_dict(assignment)
    visible_sections = filter_visible_sections(all_sections, partial_answers)
    pages = group_sections_into_pages(visible_sections)
    is_multi_page = len(pages) > 1

    # Determine current page
    page_num = 1
    if is_multi_page:
        try:
            page_num = int(request.GET.get("page", 1))
        except (ValueError, TypeError):
            page_num = 1
        page_num = max(1, min(page_num, len(pages)))

    # Load existing partial answers for pre-fill
    partials = {}
    for pa in PartialAnswer.objects.filter(assignment=assignment):
        partials[pa.question_id] = decrypt_field(pa.value_encrypted)

    if request.method == "POST":
        action = request.POST.get("action", "submit")

        if is_multi_page and action == "next":
            # Save current page answers and go to next page
            current_sections = pages[page_num - 1]
            errors = _save_page_answers(
                request, assignment, current_sections, partial_answers,
            )
            if errors:
                return render(request, "portal/survey_fill.html", {
                    "participant": participant,
                    "assignment": assignment,
                    "survey": survey,
                    "sections": current_sections,
                    "page_num": page_num,
                    "total_pages": len(pages),
                    "is_multi_page": is_multi_page,
                    "is_last_page": page_num == len(pages),
                    "partial_answers": partial_answers,
                    "errors": errors,
                })
            # Refresh partial answers and page structure after save
            partial_answers = get_partial_answers_dict(assignment)
            visible_sections = filter_visible_sections(all_sections, partial_answers)
            pages = group_sections_into_pages(visible_sections)
            next_page = min(page_num + 1, len(pages))
            return redirect(f"{request.path}?page={next_page}")

        # Final submit
        # For scrolling form or last page, also save current page
        if is_multi_page:
            current_sections = pages[page_num - 1]
        else:
            current_sections = visible_sections
        page_errors = _save_page_answers(
            request, assignment, current_sections, partial_answers,
        )
        if page_errors:
            return render(request, "portal/survey_fill.html", {
                "participant": participant,
                "assignment": assignment,
                "survey": survey,
                "sections": current_sections,
                "page_num": page_num,
                "total_pages": len(pages),
                "is_multi_page": is_multi_page,
                "is_last_page": True,
                "partial_answers": partial_answers,
                "errors": page_errors,
            })

        # Refresh and validate ALL required questions across all pages
        partial_answers = get_partial_answers_dict(assignment)
        visible_sections = filter_visible_sections(all_sections, partial_answers)
        all_errors = []
        for section in visible_sections:
            for question in section.questions.all().order_by("sort_order"):
                if question.required and not partial_answers.get(question.pk):
                    all_errors.append(question.question_text)

        if all_errors:
            pages = group_sections_into_pages(visible_sections)
            if is_multi_page:
                current_sections = pages[page_num - 1]
            return render(request, "portal/survey_fill.html", {
                "participant": participant,
                "assignment": assignment,
                "survey": survey,
                "sections": current_sections,
                "page_num": page_num,
                "total_pages": len(pages),
                "is_multi_page": is_multi_page,
                "is_last_page": True,
                "partial_answers": partial_answers,
                "errors": all_errors,
            })

        # Create final response from PartialAnswer data
        from django.db import transaction

        with transaction.atomic():
            response_obj = SurveyResponse.objects.create(
                survey=survey,
                assignment=assignment,
                client_file=client_file,
                channel="portal",
            )
            for question_pk, answer_value in partial_answers.items():
                from apps.surveys.models import SurveyQuestion
                try:
                    question = SurveyQuestion.objects.get(pk=question_pk)
                except SurveyQuestion.DoesNotExist:
                    continue

                answer = SurveyAnswer(
                    response=response_obj,
                    question=question,
                )
                answer.value = answer_value

                if question.question_type in ("rating_scale", "yes_no"):
                    try:
                        answer.numeric_value = int(answer_value)
                    except (ValueError, TypeError):
                        pass
                elif question.question_type == "single_choice":
                    for opt in (question.options_json or []):
                        if opt.get("value") == answer_value:
                            answer.numeric_value = opt.get("score")
                            break
                answer.save()

            assignment.status = "completed"
            assignment.completed_at = timezone.now()
            assignment.save(update_fields=["status", "completed_at"])

            # Clean up partial answers after successful submit
            PartialAnswer.objects.filter(assignment=assignment).delete()

        _audit_portal_event(request, "portal_survey_submitted", metadata={
            "survey_id": str(survey.pk),
            "assignment_id": str(assignment.pk),
        })
        return redirect("portal:survey_thank_you", assignment_id=assignment.pk)

    # GET — render form
    if is_multi_page:
        current_sections = pages[page_num - 1]
    else:
        current_sections = visible_sections

    return render(request, "portal/survey_fill.html", {
        "participant": participant,
        "assignment": assignment,
        "survey": survey,
        "sections": current_sections,
        "page_num": page_num,
        "total_pages": len(pages),
        "is_multi_page": is_multi_page,
        "is_last_page": page_num == len(pages),
        "partial_answers": partial_answers,
        "errors": [],
        "partials": partials,
    })


def _save_page_answers(request, assignment, sections, partial_answers):
    """Save answers from POST data for sections on the current page.

    Returns list of error messages for missing required fields.
    Updates partial_answers dict in place.
    """
    from apps.surveys.models import PartialAnswer

    errors = []
    for section in sections:
        for question in section.questions.all().order_by("sort_order"):
            field_name = f"q_{question.pk}"
            if question.question_type == "multiple_choice":
                raw_values = request.POST.getlist(field_name)
                raw_value = ";".join(raw_values) if raw_values else ""
            else:
                raw_value = request.POST.get(field_name, "").strip()

            if question.required and not raw_value:
                errors.append(question.question_text)

            if raw_value:
                pa, _ = PartialAnswer.objects.update_or_create(
                    assignment=assignment,
                    question=question,
                    defaults={},
                )
                pa.value = raw_value
                pa.save()
                partial_answers[question.pk] = raw_value
            else:
                PartialAnswer.objects.filter(
                    assignment=assignment, question=question,
                ).delete()
                partial_answers.pop(question.pk, None)

    return errors


@portal_login_required
@require_POST
def portal_survey_autosave(request, assignment_id):
    """HTMX auto-save: save a single answer to PartialAnswer."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import PartialAnswer, SurveyAssignment, SurveyQuestion

    if not is_surveys_enabled():
        raise Http404

    # Only accept HTMX requests
    if not request.headers.get("HX-Request"):
        return HttpResponseBadRequest("HTMX request required")

    participant = request.participant_user
    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status="in_progress",
    )

    question_id = request.POST.get("question_id")
    value = request.POST.get("value", "")

    # Verify question belongs to this survey
    question = get_object_or_404(
        SurveyQuestion,
        pk=question_id,
        section__survey=assignment.survey,
    )

    if value:
        pa, _ = PartialAnswer.objects.update_or_create(
            assignment=assignment,
            question=question,
            defaults={},
        )
        pa.value = value
        pa.save()
    else:
        # Empty value — delete partial answer if it exists
        PartialAnswer.objects.filter(
            assignment=assignment, question=question,
        ).delete()

    return HttpResponse(
        '<span role="status" class="save-indicator">Saved</span>',
        content_type="text/html",
    )


@portal_login_required
def portal_survey_review(request, assignment_id):
    """Read-only view of a completed survey response."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import SurveyAssignment, SurveyResponse, SurveyAnswer
    from apps.portal.survey_helpers import (
        filter_visible_sections, calculate_section_scores,
    )

    if not is_surveys_enabled():
        raise Http404

    participant = request.participant_user
    client_file = _get_client_file(request)

    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status="completed",
    )
    survey = assignment.survey

    response_obj = SurveyResponse.objects.filter(
        assignment=assignment, client_file=client_file,
    ).first()
    if not response_obj:
        raise Http404

    # Build answers dict {question_pk: value}
    answers = SurveyAnswer.objects.filter(response=response_obj)
    answers_dict = {a.question_id: a.value for a in answers}

    all_sections = list(
        survey.sections.filter(is_active=True)
        .prefetch_related("questions")
        .order_by("sort_order")
    )
    visible_sections = filter_visible_sections(all_sections, answers_dict)

    # Calculate scores if configured
    scores = []
    if survey.show_scores_to_participant:
        scores = calculate_section_scores(visible_sections, answers_dict)

    return render(request, "portal/survey_review.html", {
        "participant": participant,
        "survey": survey,
        "assignment": assignment,
        "response_obj": response_obj,
        "sections": visible_sections,
        "answers": answers_dict,
        "scores": scores,
    })


@portal_login_required
def portal_survey_thank_you(request, assignment_id):
    """Thank-you page after completing a survey — with optional scores."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import SurveyAssignment, SurveyResponse, SurveyAnswer
    from apps.portal.survey_helpers import (
        filter_visible_sections, calculate_section_scores,
    )

    if not is_surveys_enabled():
        raise Http404

    participant = request.participant_user
    client_file = _get_client_file(request)

    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
    )
    survey = assignment.survey

    scores = []
    if survey.show_scores_to_participant:
        response_obj = SurveyResponse.objects.filter(
            assignment=assignment, client_file=client_file,
        ).first()
        if response_obj:
            answers = SurveyAnswer.objects.filter(response=response_obj)
            answers_dict = {a.question_id: a.value for a in answers}
            all_sections = list(
                survey.sections.filter(is_active=True)
                .prefetch_related("questions")
                .order_by("sort_order")
            )
            visible = filter_visible_sections(all_sections, answers_dict)
            scores = calculate_section_scores(visible, answers_dict)

    return render(request, "portal/survey_thank_you.html", {
        "participant": participant,
        "survey": survey,
        "scores": scores,
    })
