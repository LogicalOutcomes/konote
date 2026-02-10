"""
Django system checks for KoNote security.

These checks run automatically with every manage.py command (runserver, migrate, etc.).
They catch configuration issues early, before the app starts serving requests.

Check IDs:
    KoNote.E001 — FIELD_ENCRYPTION_KEY not configured (Error)
    KoNote.E002 — Security middleware missing (Error)
    KoNote.W001 — DEBUG=True in production (Warning, deploy only)
    KoNote.W002 — SESSION_COOKIE_SECURE=False (Warning, deploy only)

Run checks manually:
    python manage.py check           # Basic checks
    python manage.py check --deploy  # Include deployment checks
"""

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security)
def check_encryption_key(app_configs, **kwargs):
    """E001: Verify FIELD_ENCRYPTION_KEY is configured."""
    errors = []

    key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
    if not key:
        errors.append(
            Error(
                "FIELD_ENCRYPTION_KEY is not configured.",
                hint="Set FIELD_ENCRYPTION_KEY environment variable to a valid Fernet key.",
                id="KoNote.E001",
            )
        )
    else:
        # Validate it's a valid Fernet key
        try:
            from cryptography.fernet import Fernet
            Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            errors.append(
                Error(
                    f"FIELD_ENCRYPTION_KEY is invalid: {e}",
                    hint="Generate a new key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"",
                    id="KoNote.E001",
                )
            )

    return errors


@register(Tags.security)
def check_middleware_chain(app_configs, **kwargs):
    """E002: Verify security middleware is in the chain."""
    errors = []

    required_middleware = [
        ("konote.middleware.program_access.ProgramAccessMiddleware", "RBAC enforcement"),
        ("konote.middleware.audit.AuditMiddleware", "Audit logging"),
    ]

    middleware = getattr(settings, "MIDDLEWARE", [])

    for mw_path, description in required_middleware:
        if mw_path not in middleware:
            errors.append(
                Error(
                    f"{mw_path} is not in MIDDLEWARE.",
                    hint=f"Add '{mw_path}' to MIDDLEWARE in settings. This provides {description}.",
                    id="KoNote.E002",
                )
            )

    return errors


@register(Tags.security, deploy=True)
def check_debug_mode(app_configs, **kwargs):
    """W001: Warn if DEBUG is True (deploy check only)."""
    warnings = []

    if settings.DEBUG:
        warnings.append(
            Warning(
                "DEBUG is True.",
                hint="Set DEBUG=False in production to hide error details and improve security.",
                id="KoNote.W001",
            )
        )

    return warnings


@register(Tags.security, deploy=True)
def check_secure_cookies(app_configs, **kwargs):
    """W002: Warn if secure cookie settings are disabled (deploy check only)."""
    warnings = []

    if not getattr(settings, "SESSION_COOKIE_SECURE", False):
        warnings.append(
            Warning(
                "SESSION_COOKIE_SECURE is False.",
                hint="Set SESSION_COOKIE_SECURE=True when using HTTPS to prevent session hijacking.",
                id="KoNote.W002",
            )
        )

    if not getattr(settings, "CSRF_COOKIE_SECURE", False):
        warnings.append(
            Warning(
                "CSRF_COOKIE_SECURE is False.",
                hint="Set CSRF_COOKIE_SECURE=True when using HTTPS.",
                id="KoNote.W003",
            )
        )

    return warnings


@register(Tags.security, deploy=True)
def check_password_hasher(app_configs, **kwargs):
    """W004: Warn if Argon2 is not the primary password hasher."""
    warnings = []

    hashers = getattr(settings, "PASSWORD_HASHERS", [])
    if hashers and "Argon2" not in hashers[0]:
        warnings.append(
            Warning(
                "Argon2 is not the primary password hasher.",
                hint="Add 'django.contrib.auth.hashers.Argon2PasswordHasher' as the first entry in PASSWORD_HASHERS for stronger password security.",
                id="KoNote.W004",
            )
        )

    return warnings
