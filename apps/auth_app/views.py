"""Authentication views — Azure AD SSO and local login."""
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django_ratelimit.decorators import ratelimit


def login_view(request):
    """Route to appropriate login method based on AUTH_MODE."""
    if request.user.is_authenticated:
        return redirect("/")

    if settings.AUTH_MODE == "azure":
        return _azure_login_redirect(request)
    return _local_login(request)


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def _local_login(request):
    """Username/password login with rate limiting."""
    from apps.auth_app.models import User

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        try:
            user = User.objects.get(username=username, is_active=True)
            if user.check_password(password):
                login(request, user)
                user.last_login_at = timezone.now()
                user.save(update_fields=["last_login_at"])
                # Log to audit
                _audit_login(request, user)
                return redirect("/")
            else:
                error = "Invalid username or password."
        except User.DoesNotExist:
            error = "Invalid username or password."

    return render(request, "auth/login.html", {"error": error, "auth_mode": "local"})


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
    return redirect("/")


@login_required
def logout_view(request):
    """Log out and destroy server-side session."""
    _audit_logout(request)
    logout(request)
    return redirect("/auth/login/")


def _audit_login(request, user):
    """Record login event in audit log."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=user.id,
            user_display=user.get_display_name(),
            ip_address=request.META.get("REMOTE_ADDR", ""),
            action="login",
            resource_type="session",
        )
    except Exception:
        pass


def _audit_logout(request):
    """Record logout event in audit log."""
    try:
        from apps.audit.models import AuditLog

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.id,
            user_display=request.user.get_display_name(),
            ip_address=request.META.get("REMOTE_ADDR", ""),
            action="logout",
            resource_type="session",
        )
    except Exception:
        pass
