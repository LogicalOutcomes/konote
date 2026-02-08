"""Development settings — local use only."""
import os

# Provide safe dev-only defaults BEFORE importing base settings.
# base.py requires these via require_env(); these defaults only apply
# when the developer hasn't set them in .env or the shell.
os.environ.setdefault("SECRET_KEY", "insecure-dev-key-do-not-use-in-production")
os.environ.setdefault("DATABASE_URL", "postgresql://KoNote2:KoNote2@localhost:5432/KoNote2")
os.environ.setdefault("AUDIT_DATABASE_URL", "postgresql://audit_writer:audit_pass@localhost:5433/KoNote2_audit")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Relax security for local dev
SESSION_COOKIE_SECURE = False
LANGUAGE_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
