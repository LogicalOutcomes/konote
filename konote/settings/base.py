"""
Base Django settings for KoNote Web.
Shared across all environments.
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()


def require_env(name):
    """Return an environment variable or raise ImproperlyConfigured."""
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(
            f"Required environment variable {name} is not set. "
            f"See .env.example for details."
        )
    return value


# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security — no fallback; must be set in every environment
SECRET_KEY = require_env("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = []

# Auth mode: "azure" or "local"
AUTH_MODE = os.environ.get("AUTH_MODE", "local")

# Demo mode — shows quick-login buttons on login page
DEMO_MODE = os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # KoNote apps
    "apps.auth_app",
    "apps.programs",
    "apps.clients",
    "apps.plans",
    "apps.notes",
    "apps.events",
    "apps.admin_settings",
    "apps.audit",
    "apps.reports",
    "apps.registration",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "konote.middleware.program_access.ProgramAccessMiddleware",
    "konote.middleware.terminology.TerminologyMiddleware",
    "konote.middleware.audit.AuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
]

ROOT_URLCONF = "konote.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "konote.context_processors.terminology",
                "konote.context_processors.features",
                "konote.context_processors.instance_settings",
                "konote.context_processors.user_roles",
                "konote.context_processors.document_storage",
                "konote.context_processors.pending_submissions",
            ],
        },
    },
]

WSGI_APPLICATION = "konote.wsgi.application"

# Custom user model
AUTH_USER_MODEL = "auth_app.User"

# Databases
DATABASES = {
    "default": dj_database_url.config(
        default=require_env("DATABASE_URL"),
        conn_max_age=600,
    ) | {"OPTIONS": {"connect_timeout": 10}},
    "audit": dj_database_url.config(
        env="AUDIT_DATABASE_URL",
        default=require_env("AUDIT_DATABASE_URL"),
        conn_max_age=600,
    ) | {"OPTIONS": {"connect_timeout": 10}},
}

DATABASE_ROUTERS = ["konote.db_router.AuditRouter"]

# Password hashing — Argon2 first
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Sessions — server-side in database
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_SAVE_EVERY_REQUEST = True  # Reset timeout on activity
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = True

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# CSP — Content Security Policy
# ─────────────────────────────────────────────────────────────────────
# Controls which resources the browser is allowed to load.
#
#   default-src 'self'         — fallback: only same-origin resources
#   script-src  unpkg.com      — HTMX is loaded from unpkg CDN
#   style-src   jsdelivr.net   — Pico CSS is loaded from jsDelivr CDN
#               'unsafe-inline' — required by Pico CSS (see production.py note)
#   img-src     data:          — allows inline data-URI images (e.g. Chart.js)
#   connect-src 'self'         — HTMX fetch/XHR requests to same origin only
#   font-src    'self'         — no external font CDNs
#   frame-src   'none'         — no iframes allowed
#   object-src  'none'         — no plugins (Flash, Java, etc.)
#   base-uri    'self'         — prevents <base> tag injection attacks
#   form-action 'self'         — forms can only submit to same origin
# ─────────────────────────────────────────────────────────────────────
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://unpkg.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:")
CSP_CONNECT_SRC = ("'self'",)
CSP_FONT_SRC = ("'self'",)
CSP_FRAME_SRC = ("'none'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)

# Internationalization
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Available languages for the UI
LANGUAGES = [
    ("en", "English"),
    ("fr", "Français"),
]

# Where to find translation files
LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Static files
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Login URLs
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/auth/login/"

# PII encryption key (Fernet) — required; no fallback
FIELD_ENCRYPTION_KEY = require_env("FIELD_ENCRYPTION_KEY")

# Azure AD / Entra ID settings
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_REDIRECT_URI = os.environ.get("AZURE_REDIRECT_URI", "")

# OpenRouter AI (optional — features hidden when key is empty)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514")
OPENROUTER_SITE_URL = os.environ.get("OPENROUTER_SITE_URL", "https://konote.app")

# Logging — errors to stderr so they appear in Railway logs
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
