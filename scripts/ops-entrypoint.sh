#!/bin/bash
# ==============================================================================
# KoNote Ops Sidecar — Entrypoint
# ==============================================================================
# Configures msmtp, waits for databases, builds crontab, starts crond.
# All scheduled tasks run inside this container — no host-level cron needed.
set -euo pipefail

echo "=== KoNote Ops Sidecar ==="
echo "  Version: $(cat /etc/konote-version 2>/dev/null || echo unknown)"
echo "  Started: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"

# ---------------------------------------------------------------------------
# Configure msmtp (SMTP client for health emails)
# ---------------------------------------------------------------------------
if [ -n "${EMAIL_HOST:-}" ]; then
    cat > /etc/msmtprc <<MSMTP
defaults
auth           on
tls            on
tls_starttls   on
logfile        /dev/stderr

account        default
host           ${EMAIL_HOST}
port           ${EMAIL_PORT:-587}
from           ${DEFAULT_FROM_EMAIL:-noreply@konote.app}
user           ${EMAIL_HOST_USER:-}
password       ${EMAIL_HOST_PASSWORD:-}
MSMTP
    chmod 600 /etc/msmtprc
    echo "  Email: configured (${EMAIL_HOST}:${EMAIL_PORT:-587})"
else
    echo "  Email: not configured (health reports will log to stdout)"
fi

# ---------------------------------------------------------------------------
# Wait for databases to be reachable
# ---------------------------------------------------------------------------
echo "  Waiting for databases..."
RETRIES=30
for i in $(seq 1 $RETRIES); do
    if pg_isready -h db -U "${POSTGRES_USER}" -d "${POSTGRES_DB:-konote}" -q 2>/dev/null && \
       pg_isready -h audit_db -U "${AUDIT_POSTGRES_USER}" -d "${AUDIT_POSTGRES_DB:-konote_audit}" -q 2>/dev/null; then
        echo "  Databases: ready"
        break
    fi
    if [ "$i" -eq "$RETRIES" ]; then
        echo "  WARNING: Databases not ready after ${RETRIES} attempts. Continuing anyway."
    fi
    sleep 2
done

# ---------------------------------------------------------------------------
# Export env vars so cron jobs can access them
# (Alpine crond does not pass environment variables to jobs)
# ---------------------------------------------------------------------------
env > /etc/environment
chmod 600 /etc/environment

# ---------------------------------------------------------------------------
# Build crontab
# ---------------------------------------------------------------------------
# Schedules (can be overridden via env vars for testing)
BACKUP_SCHEDULE="${OPS_BACKUP_SCHEDULE:-0 2 * * *}"
DISK_CHECK_SCHEDULE="${OPS_DISK_CHECK_SCHEDULE:-0 * * * *}"
HEALTH_REPORT_SCHEDULE="${OPS_HEALTH_REPORT_SCHEDULE:-0 7 * * *}"
PRUNE_SCHEDULE="${OPS_PRUNE_SCHEDULE:-0 4 * * 0}"
VERIFY_SCHEDULE="${OPS_VERIFY_SCHEDULE:-0 5 * * 0}"

cat > /var/spool/cron/crontabs/root <<CRON
# KoNote Ops — managed by ops-entrypoint.sh (do not edit manually)

# Nightly database backup (both databases)
${BACKUP_SCHEDULE} /usr/local/bin/ops-backup.sh >> /proc/1/fd/1 2>&1

# Hourly disk usage check
${DISK_CHECK_SCHEDULE} /usr/local/bin/ops-disk-check.sh >> /proc/1/fd/1 2>&1

# Daily health report
${HEALTH_REPORT_SCHEDULE} /usr/local/bin/ops-health-report.sh >> /proc/1/fd/1 2>&1

# Weekly Docker system prune (Sundays)
${PRUNE_SCHEDULE} /usr/local/bin/ops-docker-prune.sh >> /proc/1/fd/1 2>&1

# Weekly backup verification (Sundays)
${VERIFY_SCHEDULE} /usr/local/bin/ops-backup-verify.sh >> /proc/1/fd/1 2>&1

CRON

echo "  Crontab installed:"
echo "    Backup:         ${BACKUP_SCHEDULE}"
echo "    Disk check:     ${DISK_CHECK_SCHEDULE}"
echo "    Health report:  ${HEALTH_REPORT_SCHEDULE}"
echo "    Docker prune:   ${PRUNE_SCHEDULE}"
echo "    Verify backup:  ${VERIFY_SCHEDULE}"
echo ""
echo "=== Ops sidecar ready. Starting crond. ==="

# Start crond in foreground (keeps container running)
exec crond -f -l 2
