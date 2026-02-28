"""Development settings — local use only."""
import os

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Load .env FIRST so its values take priority over the dev defaults below.
# (python-dotenv won't overwrite vars already in the environment, so .env
# values only apply when the shell hasn't already set them.)
load_dotenv()

# Provide safe dev-only defaults AFTER loading .env.
# base.py requires these via require_env(); these defaults only apply
# when the developer hasn't set them in .env or the shell.
os.environ.setdefault("SECRET_KEY", "insecure-dev-key-do-not-use-in-production")
os.environ.setdefault("DATABASE_URL", "postgresql://konote:konote@localhost:5432/konote")
os.environ.setdefault("AUDIT_DATABASE_URL", "postgresql://audit_writer:audit_pass@localhost:5433/konote_audit")

# FIELD_ENCRYPTION_KEY must be set explicitly — no hardcoded fallback.
# A known-public key in dev settings is a security risk: if a developer
# accidentally points dev settings at real data, all PII is encrypted with
# a publicly-committed key.
# Generate a key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
if not os.environ.get("FIELD_ENCRYPTION_KEY"):
    raise ImproperlyConfigured(
        "FIELD_ENCRYPTION_KEY is not set. Add it to your .env file.\n"
        "Generate one with: python -c \"from cryptography.fernet import Fernet; "
        "print(Fernet.generate_key().decode())\""
    )

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Relax security for local dev
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
LANGUAGE_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Allow any origin to embed registration forms in dev so the embed preview
# works without configuring real allowed origins.
EMBED_ALLOWED_ORIGINS = ["*"]
