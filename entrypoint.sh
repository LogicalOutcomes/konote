#!/bin/sh
set -e

# Activate custom git hooks (harmless if .git doesn't exist in container)
if [ -d ".git" ]; then
    git config core.hooksPath .githooks 2>/dev/null || true
fi

echo "Running migrations..."
python manage.py migrate --noinput
echo "Migrations complete."

echo "Running audit migrations..."
python manage.py migrate --database=audit --noinput
echo "Audit migrations complete."

echo "Locking down audit database permissions..."
python manage.py lockdown_audit_db 2>&1 || echo "WARNING: Audit lockdown failed (see error above). Audit logs may not be write-protected."

# Seed runs all sub-commands in the right order:
# metrics, features, settings, event types, note templates, intake fields,
# demo data (if DEMO_MODE), and demo client field values
echo ""
echo "Seeding data..."
python manage.py seed 2>&1 || echo "WARNING: Seed failed (see error above). App will start but may be missing data."

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
