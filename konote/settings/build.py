"""Build settings — minimal config for Docker build commands (collectstatic, compilemessages)."""
import os

# Provide build defaults BEFORE importing base (which calls require_env).
# These are never used at runtime — only during Docker image build.
os.environ.setdefault("SECRET_KEY", "build-only-not-for-runtime")
os.environ.setdefault("DATABASE_URL", "sqlite:///build-dummy.db")
os.environ.setdefault("AUDIT_DATABASE_URL", "sqlite:///build-dummy-audit.db")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
os.environ.setdefault("EMAIL_HASH_KEY", "build-only-not-for-runtime")

from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

# SQLite for build — no real database needed
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
