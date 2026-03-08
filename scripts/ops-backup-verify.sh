#!/bin/bash
# ==============================================================================
# KoNote Ops — Weekly Backup Verification
# ==============================================================================
# Restores the latest backup into a temporary database on the existing db
# container, verifies table counts match production, then drops it.
# No Docker-in-Docker needed — connects directly to db:5432.
#
# Disable by setting OPS_VERIFY_BACKUPS=false in .env.
set -euo pipefail

# Load environment (cron runs without env vars on Alpine)
set -a; source /etc/environment; set +a

if [ "${OPS_VERIFY_BACKUPS:-true}" != "true" ]; then
    echo "[$(date)] Backup verification disabled (OPS_VERIFY_BACKUPS=${OPS_VERIFY_BACKUPS})"
    exit 0
fi

TEMP_DB="_backup_verify_$(date +%Y%m%d)"
LATEST_BACKUP=$(ls -1t /backups/main_*.dump 2>/dev/null | head -1 || true)

if [ -z "${LATEST_BACKUP:-}" ]; then
    echo "[$(date)] WARNING: No backup files found in /backups/ -- skipping verification"
    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
        curl -s -m 10 -X POST "$ALERT_WEBHOOK_URL" \
            -d "KoNote backup verification: no backup files found" || true
    fi
    exit 1
fi

echo "[$(date)] Starting backup verification..."
echo "  Source: $LATEST_BACKUP"
echo "  Temp DB: $TEMP_DB"

# Cleanup trap — always drop the temp database, even on failure
cleanup() {
    echo "  Cleaning up temporary database..."
    PGPASSWORD="${POSTGRES_PASSWORD}" psql -h db -U "${POSTGRES_USER}" -d "${POSTGRES_DB:-konote}" \
        -c "DROP DATABASE IF EXISTS \"${TEMP_DB}\";" 2>/dev/null || true
}
trap cleanup EXIT

# Create temporary database
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h db -U "${POSTGRES_USER}" -d "${POSTGRES_DB:-konote}" \
    -c "CREATE DATABASE \"${TEMP_DB}\";"

# Restore backup into it (suppress NOTICE messages)
echo "  Restoring backup..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_restore -h db -U "${POSTGRES_USER}" -d "${TEMP_DB}" \
    --no-owner --no-privileges "$LATEST_BACKUP" 2>/dev/null

# Verify: count tables (should match production)
PROD_TABLES=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h db -U "${POSTGRES_USER}" -d "${POSTGRES_DB:-konote}" -t -A \
    -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")

VERIFY_TABLES=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h db -U "${POSTGRES_USER}" -d "${TEMP_DB}" -t -A \
    -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")

echo "  Production tables: $PROD_TABLES"
echo "  Restored tables:   $VERIFY_TABLES"

if [ "$VERIFY_TABLES" -eq "$PROD_TABLES" ]; then
    echo "[$(date)] Backup verification PASSED ($VERIFY_TABLES tables match)"
elif [ "$VERIFY_TABLES" -gt 0 ]; then
    echo "[$(date)] Backup verification WARNING: table count mismatch (prod=$PROD_TABLES, restored=$VERIFY_TABLES)"
    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
        curl -s -m 10 -X POST "$ALERT_WEBHOOK_URL" \
            -d "KoNote backup verify: table count mismatch (prod=$PROD_TABLES, restored=$VERIFY_TABLES)" || true
    fi
else
    echo "[$(date)] Backup verification FAILED: no tables restored"
    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
        curl -s -m 10 -X POST "$ALERT_WEBHOOK_URL" \
            -d "KoNote backup verification FAILED: 0 tables restored from $LATEST_BACKUP" || true
    fi
    exit 1
fi

# Cleanup happens in EXIT trap
