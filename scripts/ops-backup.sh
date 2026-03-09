#!/bin/bash
# ==============================================================================
# KoNote Ops — Database Backup
# ==============================================================================
# Runs inside the ops container. Connects directly to db:5432 and audit_db:5432
# over the Docker backend network (no docker compose exec needed).
#
# Features:
#   - Dumps both databases (main + audit) in custom format (-Fc)
#     Custom format is compressed, supports parallel restore (pg_restore -j),
#     and writes atomically (no separate gzip step).
#   - One retry with 60s delay for transient database failures
#   - Size sanity check (alerts if today < 50% of yesterday)
#   - Retention management (configurable via env vars)
#   - Dead man's switch ping on success (HEALTHCHECK_PING_URL)
#   - Failure alert via webhook (ALERT_WEBHOOK_URL)
set -euo pipefail

# Load environment (cron runs without env vars on Alpine)
set -a; source /etc/environment; set +a

BACKUP_DIR="/backups"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
AUDIT_RETENTION_DAYS="${AUDIT_RETENTION_DAYS:-90}"
TIMESTAMP=$(date +%Y-%m-%d_%H%M)

# Alert on failure
alert_failure() {
    local msg="KoNote backup FAILED at $(date). Check ops container logs."
    echo "  ERROR: $msg"
    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
        curl -s -m 10 -X POST "$ALERT_WEBHOOK_URL" -d "$msg" || true
    fi
}
trap alert_failure ERR

mkdir -p "$BACKUP_DIR"

echo "[$TIMESTAMP] Starting KoNote backup..."

# ---------------------------------------------------------------------------
# Retry helper — one retry with 60s delay for transient DB failures
# ---------------------------------------------------------------------------
dump_with_retry() {
    local label="$1"; shift
    if "$@"; then
        return 0
    fi
    echo "  WARNING: $label dump failed, retrying in 60s..."
    sleep 60
    "$@"
}

# Dump main database (custom format: compressed, supports parallel restore)
echo "  Backing up main database (${POSTGRES_DB:-konote})..."
dump_with_retry "main" \
    env PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -Fc -h db -U "${POSTGRES_USER}" "${POSTGRES_DB:-konote}" \
    -f "$BACKUP_DIR/main_$TIMESTAMP.dump"

# Dump audit database
echo "  Backing up audit database (${AUDIT_POSTGRES_DB:-konote_audit})..."
dump_with_retry "audit" \
    env PGPASSWORD="${AUDIT_POSTGRES_PASSWORD}" pg_dump \
    -Fc -h audit_db -U "${AUDIT_POSTGRES_USER}" "${AUDIT_POSTGRES_DB:-konote_audit}" \
    -f "$BACKUP_DIR/audit_$TIMESTAMP.dump"

# Show backup sizes
MAIN_SIZE=$(du -h "$BACKUP_DIR/main_$TIMESTAMP.dump" | cut -f1)
AUDIT_SIZE=$(du -h "$BACKUP_DIR/audit_$TIMESTAMP.dump" | cut -f1)
echo "  Main backup: $MAIN_SIZE"
echo "  Audit backup: $AUDIT_SIZE"

# Size sanity check — alert if today's main backup is less than half yesterday's
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || echo "")
if [ -n "$YESTERDAY" ]; then
    YESTERDAY_BACKUP=$(ls "$BACKUP_DIR"/main_${YESTERDAY}*.dump 2>/dev/null | head -1 || true)
    if [ -n "${YESTERDAY_BACKUP:-}" ]; then
        TODAY_BYTES=$(stat -c%s "$BACKUP_DIR/main_$TIMESTAMP.dump" 2>/dev/null || echo 0)
        YESTERDAY_BYTES=$(stat -c%s "$YESTERDAY_BACKUP" 2>/dev/null || echo 0)
        if [ "$YESTERDAY_BYTES" -gt 0 ] && [ "$TODAY_BYTES" -lt $((YESTERDAY_BYTES / 2)) ]; then
            echo "  WARNING: Today's backup ($TODAY_BYTES bytes) is less than half of yesterday's ($YESTERDAY_BYTES bytes)"
            if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
                curl -s -m 10 -X POST "$ALERT_WEBHOOK_URL" \
                    -d "KoNote backup size anomaly: today $TODAY_BYTES bytes vs yesterday $YESTERDAY_BYTES bytes" || true
            fi
        fi
    fi
fi

# Clean up old backups
echo "  Cleaning up backups older than $RETENTION_DAYS days (main) and $AUDIT_RETENTION_DAYS days (audit)..."
find "$BACKUP_DIR" -name "main_*.dump" -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "audit_*.dump" -mtime +"$AUDIT_RETENTION_DAYS" -delete

# Dead man's switch — ping on success
if [ -n "${HEALTHCHECK_PING_URL:-}" ]; then
    curl -s -m 10 "$HEALTHCHECK_PING_URL" || echo "  WARNING: Healthcheck ping failed (non-fatal)"
fi

echo "[$TIMESTAMP] Backup complete."
