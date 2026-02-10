"""Authentication views — Azure AD SSO and local login."""
import logging

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)

# Account lockout settings
LOCKOUT_THRESHOLD = 5  # Failed attempts before lockout
LOCKOUT_DURATION = 900  # 15 minutes in seconds
FAILED_ATTEMPT_WINDOW = 900  # Track attempts for 15 minutes


from konote.utils import get_client_ip as _get_client_ip


def _get_lockout_key(ip):
    """Return cache key for tracking failed attempts by IP."""
    return f"login_attempts:{ip}"


def _is_locked_out(ip):
    """Check if an IP address is currently locked out."""
    key = _get_lockout_key(ip)
    attempts = cache.get(key, 0)
    return attempts >= LOCKOUT_THRESHOLD


def _record_failed_attempt(ip):
    """Increment failed login counter for an IP address."""
    key = _get_lockout_key(ip)
    attempts = cache.get(key, 0)
    cache.set(key, attempts + 1, FAILED_ATTEMPT_WINDOW)
    return attempts + 1


def _clear_failed_attempts(ip):
    """Clear failed login counter on successful login."""
    key = _get_lockout_key(ip)
    cache.delete(key)


def sync_language_on_login(request, user):
    """Sync language preference between session and user profile.

    Called after successful login on all paths (local, Azure, demo).
    - If user has a saved preference → activate it for this request
    - If no preference saved → save current language to profile
    Returns the activated language code so callers can set the cookie.
    """
    if user.preferred_language:
        lang_code = user.preferred_language
        try:
            translation.activate(lang_code)
        except (UnicodeDecodeError, Exception) as e:
            logger.error("Failed to activate language '%s' on login: %s",
                         lang_code, e)
            lang_code = "en"
            translation.activate(lang_code)
    else:
        lang_code = translation.get_language() or "en"
        user.preferred_language = lang_code
        user.save(update_fields=["preferred_language"])
    return lang_code


def _login_redirect(user, request_session):
    """Determine the post-login redirect for a user."""
    from apps.programs.context import needs_program_selection
    from apps.programs.models import UserProgramRole

    if needs_program_selection(user, request_session):
        return redirect("programs:select_program")
    if UserProgramRole.is_executive_only(user):
        return redirect("clients:executive_dashboard")
    return redirect("/")


def _set_language_cookie(response, lang_code):
    """Set the language cookie on a response with all the correct settings."""
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        lang_code,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )
    return response


def switch_language(request):
    """Switch language — sets session, cookie, AND user.preferred_language.

    Replaces Django's built-in set_language for authenticated users so that
    the User model stays in sync with the session/cookie.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    lang_code = request.POST.get("language", "en")
    # Validate against configured languages
    valid_codes = [code for code, _name in settings.LANGUAGES]
    if lang_code not in valid_codes:
        lang_code = "en"

    # Activate for this request — wrapped in try/except because
    # translation.activate() parses .mo files and will crash with
    # UnicodeDecodeError if the container locale isn't UTF-8.
    try:
        translation.activate(lang_code)
    except (UnicodeDecodeError, Exception) as e:
        logger.error("Failed to activate language '%s': %s", lang_code, e)
        lang_code = "en"
        translation.activate(lang_code)

    # Save to user profile if logged in
    if request.user.is_authenticated:
        request.user.preferred_language = lang_code
        request.user.save(update_fields=["preferred_language"])

    # Save to portal participant profile if present.
    # PortalAuthMiddleware only loads participant_user for /my/* paths,
    # but this view is at /i18n/switch/ — so fall back to the session.
    participant = getattr(request, "participant_user", None)
    if not participant:
        participant_id = request.session.get("_portal_participant_id")
        if participant_id:
            from apps.portal.models import ParticipantUser
            try:
                participant = ParticipantUser.objects.get(
                    pk=participant_id, is_active=True
                )
            except ParticipantUser.DoesNotExist:
                participant = None
    if participant:
        participant.preferred_language = lang_code
        participant.save(update_fields=["preferred_language"])

    # Redirect back to referring page (with safety check)
    next_url = request.POST.get("next", request.META.get("HTTP_REFERER", "/"))
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"

    response = redirect(next_url)
    return _set_language_cookie(response, lang_code)


def login_view(request):
    """Route to appropriate login method based on AUTH_MODE."""
    if request.user.is_authenticated:
        return redirect("/")

    if settings.AUTH_MODE == "azure":
        return _azure_login_redirect(request)
    return _local_login(request)


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def _local_login(request):
    """Username/password login with rate limiting and account lockout."""
    from apps.auth_app.forms import LoginForm
    from apps.auth_app.models import User

    client_ip = _get_client_ip(request)
    error = None
    locked_out = False

    # Check for lockout before processing login attempt
    if _is_locked_out(client_ip):
        locked_out = True
        error = "Too many failed login attempts. Please try again in 15 minutes."
        _audit_failed_login(request, "(locked out)", "account_locked")

    if request.method == "POST" and not locked_out:
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            password = form.cleaned_data["password"]
            try:
                user = User.objects.get(username=username, is_active=True)
                if user.check_password(password):
                    # Successful login — clear lockout counter
                    _clear_failed_attempts(client_ip)
                    login(request, user)
                    user.last_login_at = timezone.now()
                    user.save(update_fields=["last_login_at"])
                    _audit_login(request, user)
                    lang_code = sync_language_on_login(request, user)
                    response = _login_redirect(user, request.session)
                    return _set_language_cookie(response, lang_code)
                else:
                    attempts = _record_failed_attempt(client_ip)
                    _audit_failed_login(request, username, "invalid_password")
                    if attempts >= LOCKOUT_THRESHOLD:
                        error = "Too many failed login attempts. Please try again in 15 minutes."
                    else:
                        remaining = LOCKOUT_THRESHOLD - attempts
                        error = f"Invalid username or password. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
            except User.DoesNotExist:
                attempts = _record_failed_attempt(client_ip)
                _audit_failed_login(request, username, "user_not_found")
                if attempts >= LOCKOUT_THRESHOLD:
                    error = "Too many failed login attempts. Please try again in 15 minutes."
                else:
                    remaining = LOCKOUT_THRESHOLD - attempts
                    error = f"Invalid username or password. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
        else:
            error = "Please enter both username and password."
    else:
        form = LoginForm()

    has_language_cookie = bool(request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME))
    return render(request, "auth/login.html", {
        "error": error,
        "form": form,
        "auth_mode": "local",
        "demo_mode": settings.DEMO_MODE,
        "has_language_cookie": has_language_cookie,
    })


def _azure_login_redirect(request):
    """Redirect to Azure AD for authentication."""
    from authlib.integrations.django_client import OAuth

    oauth = OAuth()
    azure = oauth.register(
        name="azure",
        client_id=settings.AZURE_CLIENT_ID,
        client_secret=settings.AZURE_CLIENT_SECRET,
        server_metadata_url=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    redirect_uri = settings.AZURE_REDIRECT_URI or request.build_absolute_uri("/auth/callback/")
    return azure.authorize_redirect(request, redirect_uri)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"], block=True)
def azure_callback(request):
    """Handle Azure AD OIDC callback (rate-limited to prevent abuse)."""
    from authlib.integrations.django_client import OAuth
    from apps.auth_app.models import User

    oauth = OAuth()
    azure = oauth.register(
        name="azure",
        client_id=settings.AZURE_CLIENT_ID,
        client_secret=settings.AZURE_CLIENT_SECRET,
        server_metadata_url=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    token = azure.authorize_access_token(request)
    userinfo = token.get("userinfo", {})

    # Find or create user by Azure AD object ID
    external_id = userinfo.get("sub") or userinfo.get("oid")
    if not external_id:
        return render(request, "auth/login.html", {"error": "Azure AD did not return a user ID."})

    user, created = User.objects.get_or_create(
        external_id=external_id,
        defaults={
            "username": userinfo.get("preferred_username", external_id),
            "display_name": userinfo.get("name", ""),
        },
    )
    if not created:
        # Update display name on each login
        user.display_name = userinfo.get("name", user.display_name)

    user.last_login_at = timezone.now()
    user.save()

    if userinfo.get("email"):
        user.email = userinfo["email"]
        user.save(update_fields=["_email_encrypted"])

    login(request, user)
    _audit_login(request, user)
    lang_code = sync_language_on_login(request, user)
    response = _login_redirect(user, request.session)
    return _set_language_cookie(response, lang_code)


def demo_login(request, role):
    """Quick-login as a demo user. Only available when DEMO_MODE is enabled."""
    if not settings.DEMO_MODE:
        from django.http import Http404
        raise Http404

    from apps.auth_app.models import User

    demo_usernames = {
        "frontdesk": "demo-frontdesk",
        "worker-1": "demo-worker-1",
        "worker-2": "demo-worker-2",
        "manager": "demo-manager",
        "executive": "demo-executive",
        "admin": "demo-admin",
    }
    username = demo_usernames.get(role)
    if not username:
        from django.http import Http404
        raise Http404

    try:
        user = User.objects.get(username=username, is_active=True)
    except User.DoesNotExist:
        from django.http import Http404
        raise Http404

    login(request, user)
    user.last_login_at = timezone.now()
    user.save(update_fields=["last_login_at"])
    lang_code = sync_language_on_login(request, user)
    response = _login_redirect(user, request.session)
    return _set_language_cookie(response, lang_code)


def demo_portal_login(request):
    """Quick-login as the demo participant. Only available when DEMO_MODE is enabled."""
    if not settings.DEMO_MODE:
        raise Http404

    from apps.clients.models import ClientFile
    from apps.portal.models import ParticipantUser

    demo_client = ClientFile.objects.filter(record_id="DEMO-001").first()
    if not demo_client:
        raise Http404

    try:
        participant = ParticipantUser.objects.get(
            client_file=demo_client, is_active=True
        )
    except ParticipantUser.DoesNotExist:
        raise Http404

    # Set portal session (same pattern as portal_login view)
    participant.last_login = timezone.now()
    participant.save(update_fields=["last_login"])
    request.session["_portal_participant_id"] = str(participant.pk)

    return redirect("/my/")


@login_required
def logout_view(request):
    """Log out and destroy server-side session.

    Clears the language cookie so the next user on a shared browser
    sees the bilingual hero instead of inheriting this user's language.
    """
    _audit_logout(request)
    logout(request)
    response = redirect("/auth/login/")
    response.delete_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )
    return response


def _audit_login(request, user):
    """Record login event in audit log."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=user.id,
            user_display=user.get_display_name(),
            ip_address=_get_client_ip(request),
            action="login",
            resource_type="session",
            is_demo_context=getattr(user, "is_demo", False),
        )
    except Exception as e:
        logger.error("Audit logging failed for login (user=%s): %s", user.username, e)


def _audit_failed_login(request, attempted_username, reason):
    """Record failed login attempt in audit log for security monitoring."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=None,
            user_display=f"[failed: {attempted_username}]",
            ip_address=_get_client_ip(request),
            action="login_failed",
            resource_type="session",
            metadata={"reason": reason},
        )
    except Exception as e:
        logger.error("Audit logging failed for failed login (user=%s): %s", attempted_username, e)


def _audit_logout(request):
    """Record logout event in audit log."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.id,
            user_display=request.user.get_display_name(),
            ip_address=_get_client_ip(request),
            action="logout",
            resource_type="session",
            is_demo_context=getattr(request.user, "is_demo", False),
        )
    except Exception as e:
        logger.error("Audit logging failed for logout (user=%s): %s", request.user.username, e)
