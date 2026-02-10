"""
Production settings — secure defaults for all deployment platforms.

Supported platforms (auto-detected):
- Railway: Sets RAILWAY_ENVIRONMENT, provides PORT
- Azure App Service: Sets WEBSITE_SITE_NAME, provides PORT
- Elestio: Sets ELESTIO_VM_NAME
- Docker/self-hosted: Set DATABASE_URL and other required vars

Required environment variables for all platforms:
- DATABASE_URL: PostgreSQL connection string
- AUDIT_DATABASE_URL: PostgreSQL connection string (can be same as DATABASE_URL)
- SECRET_KEY: Random string for cryptographic signing
- FIELD_ENCRYPTION_KEY: Fernet key for PII encryption

Optional but recommended:
- ALLOWED_HOSTS: Comma-separated list of allowed domains (auto-detected for known platforms)
"""
import os
from .base import *  # noqa: F401, F403

DEBUG = False

# ALLOWED_HOSTS — start with explicit configuration, then auto-detect
_allowed_hosts = os.environ.get("ALLOWED_HOSTS", "").split(",")
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts if h.strip()]

# Auto-detect platform and add appropriate domains
# ─────────────────────────────────────────────────────────────────────

# Railway
if os.environ.get("RAILWAY_ENVIRONMENT"):
    ALLOWED_HOSTS.extend([".railway.app", ".up.railway.app"])

# Azure App Service
if os.environ.get("WEBSITE_SITE_NAME"):
    site_name = os.environ.get("WEBSITE_SITE_NAME")
    ALLOWED_HOSTS.extend([
        f"{site_name}.azurewebsites.net",
        ".azurewebsites.net",
    ])

# Elestio
if os.environ.get("ELESTIO_VM_NAME"):
    # Elestio provides CNAME or custom domain via env vars
    elestio_domain = os.environ.get("ELESTIO_DOMAIN", "")
    if elestio_domain:
        ALLOWED_HOSTS.append(elestio_domain)
    ALLOWED_HOSTS.append(".elest.io")

# Docker/self-hosted — allow localhost and local network for testing
# In production, clients should set ALLOWED_HOSTS explicitly
if not ALLOWED_HOSTS:
    # Fallback: allow common local development hosts
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Remove duplicates while preserving order
ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS))

# HTTPS — Railway handles TLS at the edge, so we don't redirect internally.
# SECURE_PROXY_SSL_HEADER tells Django to trust the proxy's forwarded header.
SECURE_SSL_REDIRECT = False  # Railway edge handles HTTPS redirect
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Secure cookies — default to True in production
# Can override via environment if needed (e.g., for local HTTPS testing)
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True").lower() != "false"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "True").lower() != "false"

# CSRF_TRUSTED_ORIGINS — required by Django 4.0+ for HTTPS POST requests.
# Django verifies the Origin header against this list. Without it, form
# submissions (login, logout, etc.) fail with 403 "CSRF verification failed".
# Mirrors the ALLOWED_HOSTS auto-detection above.
_trusted_origins = []
_explicit = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if _explicit:
    _trusted_origins.extend([o.strip() for o in _explicit.split(",") if o.strip()])

if os.environ.get("RAILWAY_ENVIRONMENT"):
    _trusted_origins.append("https://*.railway.app")
    _trusted_origins.append("https://*.up.railway.app")

if os.environ.get("WEBSITE_SITE_NAME"):
    site_name = os.environ.get("WEBSITE_SITE_NAME")
    _trusted_origins.append(f"https://{site_name}.azurewebsites.net")

if os.environ.get("ELESTIO_VM_NAME"):
    elestio_domain = os.environ.get("ELESTIO_DOMAIN", "")
    if elestio_domain:
        _trusted_origins.append(f"https://{elestio_domain}")

CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_trusted_origins))

# CSP — production overrides
# ─────────────────────────────────────────────────────────────────────
# Report URI: set CSP_REPORT_URI_ENDPOINT in your environment to receive
# browser reports when a CSP violation occurs (e.g. a Sentry or report-uri
# endpoint). Leave unset to disable reporting.
#
# Note on 'unsafe-inline' for styles: Pico CSS currently requires it.
# If you vendor Pico locally in future, you can remove 'unsafe-inline'
# from CSP_STYLE_SRC in base.py for a tighter policy.
# ─────────────────────────────────────────────────────────────────────
_csp_report_uri = os.environ.get("CSP_REPORT_URI_ENDPOINT")
if _csp_report_uri:
    CSP_REPORT_URI = (_csp_report_uri,)
