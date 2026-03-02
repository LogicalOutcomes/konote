#!/bin/bash
# KoNote VPS Backup Script
# ========================
# Nightly backup of both PostgreSQL databases (main + audit).
# Run via cron: 0 2 * * * /opt/konote/scripts/backup-vps.sh >> /var/log/konote-backup.log 2>&1
#
# Prerequisites:
#   - Docker Compose running in /opt/konote (or set KONOTE_DIR)
#   - .env file with POSTGRES_USER, POSTGRES_DB, AUDIT_POSTGRES_USER, AUDIT_POSTGRES_DB
#
# Optional:
#   - Set ALERT_WEBHOOK_URL in .env to receive failure alerts
#     Alerts are sent as plain-text HTTP POST (no JSON, no Content-Type header).
#     Compatible with: UptimeRobot push monitors, Slack incoming webhooks,
#     ntfy.sh, Uptime Kuma push monitors. For JSON-only endpoints, use a
#     middleware like Zapier or n8n to transform the request.

set -euo pipefail

# Configuration
KONOTE_DIR="${KONOTE_DIR:-/opt/konote}"
BACKUP_DIR="${BACKUP_DIR:-/opt/konote/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
AUDIT_RETENTION_DAYS="${AUDIT_RETENTION_DAYS:-90}"
TIMESTAMP=$(date +%Y-%m-%d_%H%M)

# Load environment variables from .env
# Safety note: source treats .env as a shell script, so values with shell
# metacharacters (backticks, $(...), semicolons) would be executed. This is
# safe because the deploy guide generates all passwords with Python's
# secrets.token_urlsafe(), which produces only [A-Za-z0-9_-] characters.
# If .env editing ever becomes user-facing, switch to a grep-based approach.
if [ -f "$KONOTE_DIR/.env" ]; then
    set -a
    source "$KONOTE_DIR/.env"
    set +a
fi

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "[$TIMESTAMP] Starting KoNote backup..."

# Dump main database
echo "  Backing up main database (${POSTGRES_DB:-konote})..."
docker compose -f "$KONOTE_DIR/docker-compose.yml" exec -T db \
    pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB:-konote}" \
    > "$BACKUP_DIR/main_$TIMESTAMP.sql"

# Dump audit database
echo "  Backing up audit database (${AUDIT_POSTGRES_DB:-konote_audit})..."
docker compose -f "$KONOTE_DIR/docker-compose.yml" exec -T audit_db \
    pg_dump -U "${AUDIT_POSTGRES_USER}" "${AUDIT_POSTGRES_DB:-konote_audit}" \
    > "$BACKUP_DIR/audit_$TIMESTAMP.sql"

# Compress backups
echo "  Compressing..."
gzip "$BACKUP_DIR/main_$TIMESTAMP.sql"
gzip "$BACKUP_DIR/audit_$TIMESTAMP.sql"

# Show backup sizes
MAIN_SIZE=$(du -h "$BACKUP_DIR/main_$TIMESTAMP.sql.gz" | cut -f1)
AUDIT_SIZE=$(du -h "$BACKUP_DIR/audit_$TIMESTAMP.sql.gz" | cut -f1)
echo "  Main backup: $MAIN_SIZE"
echo "  Audit backup: $AUDIT_SIZE"

# Size sanity check — alert if today's main backup is less than half yesterday's
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null || echo "")
if [ -n "$YESTERDAY" ]; then
    YESTERDAY_BACKUP=$(ls "$BACKUP_DIR"/main_${YESTERDAY}*.sql.gz 2>/dev/null | head -1)
    if [ -n "$YESTERDAY_BACKUP" ]; then
        TODAY_BYTES=$(stat -c%s "$BACKUP_DIR/main_$TIMESTAMP.sql.gz" 2>/dev/null || stat -f%z "$BACKUP_DIR/main_$TIMESTAMP.sql.gz" 2>/dev/null || echo 0)
        YESTERDAY_BYTES=$(stat -c%s "$YESTERDAY_BACKUP" 2>/dev/null || stat -f%z "$YESTERDAY_BACKUP" 2>/dev/null || echo 0)
        if [ "$YESTERDAY_BYTES" -gt 0 ] && [ "$TODAY_BYTES" -lt $((YESTERDAY_BYTES / 2)) ]; then
            echo "  WARNING: Today's backup ($TODAY_BYTES bytes) is less than half of yesterday's ($YESTERDAY_BYTES bytes)"
            if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
                curl -s -X POST "$ALERT_WEBHOOK_URL" \
                    -d "KoNote backup size anomaly: today $TODAY_BYTES bytes vs yesterday $YESTERDAY_BYTES bytes" || true
            fi
        fi
    fi
fi

# Clean up old backups
echo "  Cleaning up backups older than $RETENTION_DAYS days (main) and $AUDIT_RETENTION_DAYS days (audit)..."
find "$BACKUP_DIR" -name "main_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "audit_*.sql.gz" -mtime +"$AUDIT_RETENTION_DAYS" -delete

echo "[$TIMESTAMP] Backup complete."
