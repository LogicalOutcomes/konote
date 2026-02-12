"""Test settings — SQLite in-memory for fast tests without PostgreSQL."""
import os

# Provide test defaults BEFORE importing base (which calls require_env).
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("AUDIT_DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
SESSION_COOKIE_SECURE = False
LANGUAGE_COOKIE_SECURE = False  # BUG-9: allow language cookie on HTTP test servers

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
    "audit": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# Use fast password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable CSP in tests
MIDDLEWARE = [m for m in MIDDLEWARE if m != "csp.middleware.CSPMiddleware"]

# Disable rate limiting in tests (prevents 403s from cumulative POST counts)
RATELIMIT_ENABLE = False

# Use simple static files storage (no manifest needed)
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Scenario-based QA holdout directory (set via env var)
SCENARIO_HOLDOUT_DIR = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
