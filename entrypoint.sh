#!/bin/sh
set -e

# Activate custom git hooks (harmless if .git doesn't exist in container)
if [ -d ".git" ]; then
    git config core.hooksPath .githooks 2>/dev/null || true
fi

echo "Running migrations..."
python manage.py migrate --noinput
echo "Migrations complete."

# Bootstrap single-tenant deployments: register the domain in the agency_domains
# table so TenantMainMiddleware can route requests.  Safe to re-run (idempotent).
# Uses ALLOWED_HOSTS env var for the domain; does nothing if already registered.
echo ""
echo "Registering tenant domain..."
python manage.py setup_public_tenant 2>&1 || echo "WARNING: setup_public_tenant failed (see above). Site may not be accessible."
echo "Tenant domain registration complete."

echo "Running audit migrations..."
# migrate_audit is a custom command that bypasses the django-tenants migrate_schemas
# override; the audit DB uses the standard PostgreSQL backend which does not have
# the set_schema() method that migrate_schemas requires.
python manage.py migrate_audit --noinput
echo "Audit migrations complete."

echo "Locking down audit database permissions..."
python manage.py lockdown_audit_db 2>&1 || echo "WARNING: Audit lockdown failed (see error above). Audit logs may not be write-protected."

# Seed runs all sub-commands in the right order:
# metrics, features, settings, event types, note templates, intake fields,
# demo data (if DEMO_MODE), and demo client field values
echo ""
echo "Seeding data..."
python manage.py seed 2>&1 || echo "WARNING: Seed failed (see error above). App will start but may be missing data."

# Merge any duplicate suggestion themes (non-blocking — safe to run repeatedly)
# TODO: Remove this merge step once migration 0016_unique_theme_per_program
# has been deployed and verified. The unique constraint and this merge step
# should be removed together.
echo ""
echo "Merging duplicate suggestion themes..."
python manage.py merge_duplicate_themes 2>&1 || echo "WARNING: Theme merge failed (see error above). App will start normally."

# Translation check (non-blocking — logs issues but never prevents startup)
echo ""
echo "Checking translations..."
python manage.py check_translations 2>&1 || echo "WARNING: Translation issues detected (non-blocking — app will start)"

# Security check before starting the application
# Set KONOTE_MODE=demo to allow startup with security warnings (for evaluation)
# Set KONOTE_MODE=production (default) to block startup if security checks fail
echo ""
echo "Running security checks..."
python manage.py startup_check
# If startup_check exits non-zero, the script stops here (set -e)

PORT=${PORT:-8000}
echo "Starting gunicorn on port $PORT"
exec gunicorn konote.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --error-logfile - \
    --access-logfile -
