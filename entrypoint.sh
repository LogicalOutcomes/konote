#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput 2>&1 || echo "Migration failed, continuing..."

echo "Running audit migrations..."
python manage.py migrate --database=audit --noinput 2>&1 || echo "Audit migration failed, continuing..."

echo "Seeding data..."
python manage.py seed 2>&1 || echo "Seed failed, continuing..."

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
