"""Test settings — SQLite for fast tests without PostgreSQL.

Local dev: uses in-memory SQLite by default (fast, no cleanup needed).
CI: set DATABASE_URL and AUDIT_DATABASE_URL env vars to file-based SQLite
    (e.g. sqlite:///ci-test.db) so xdist workers and TransactionTestCase
    sqlflush calls work correctly across process boundaries.

Multi-tenancy: When using SQLite, TenantMainMiddleware is replaced with
a no-op because SQLite doesn't support PostgreSQL schemas. Tests that need
real tenant isolation must set DATABASE_URL to a PostgreSQL connection.
"""
import os

import dj_database_url

# Provide test defaults BEFORE importing base (which calls require_env).
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("AUDIT_DATABASE_URL", "sqlite://:memory:")
# Test-only key — never use in development or production
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "TUVSTlZ6a09VRWlMU0FzZjhOWlNhTFZfVFIxaURFbXM=")

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
SESSION_COOKIE_SECURE = False
LANGUAGE_COOKIE_SECURE = False  # BUG-9: allow language cookie on HTTP test servers

# Use env vars so CI can override with file-based SQLite (required for xdist
# workers and TransactionTestCase/sqlflush). Falls back to :memory: locally.
DATABASES = {
    "default": dj_database_url.parse(
        os.environ["DATABASE_URL"],
        conn_max_age=0,
    ),
    "audit": dj_database_url.parse(
        os.environ["AUDIT_DATABASE_URL"],
        conn_max_age=0,
    ),
}

# Use fast password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# When using SQLite, disable django-tenants components that require PostgreSQL
_disabled_middleware = {"csp.middleware.CSPMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware"}
_using_sqlite = "sqlite" in os.environ.get("DATABASE_URL", "sqlite")
if _using_sqlite:
    _disabled_middleware.add("django_tenants.middleware.main.TenantMainMiddleware")
MIDDLEWARE = [
    m for m in MIDDLEWARE
    if m not in _disabled_middleware
]

# When using SQLite, replace TenantSyncRouter with a pass-through that won't
# crash on missing schema_name. TENANT_SYNC_ROUTER tells django_tenants.apps
# to validate our NoOpTenantRouter instead of looking for TenantSyncRouter.
if _using_sqlite:
    TENANT_SYNC_ROUTER = "konote.db_router.NoOpTenantRouter"
    DATABASE_ROUTERS = [
        "konote.db_router.NoOpTenantRouter",
        "konote.db_router.AuditRouter",
    ]

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
