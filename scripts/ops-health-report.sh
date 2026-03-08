#!/bin/bash
# ==============================================================================
# KoNote Ops — Daily Health Report
# ==============================================================================
# Sends operational status email. No PII included.
# If email is not configured, prints report to stdout (Docker logs).
set -euo pipefail

# Load environment (cron runs without env vars on Alpine)
set -a; source /etc/environment; set +a

REPORT_DATE=$(date +"%Y-%m-%d %H:%M %Z")

# --- Gather health data ---

# Version
VERSION=$(cat /etc/konote-version 2>/dev/null || echo "unknown")

# Database connectivity
DB_STATUS="OK"
pg_isready -h db -U "${POSTGRES_USER}" -d "${POSTGRES_DB:-konote}" -q 2>/dev/null || DB_STATUS="UNREACHABLE"

AUDIT_DB_STATUS="OK"
pg_isready -h audit_db -U "${AUDIT_POSTGRES_USER}" -d "${AUDIT_POSTGRES_DB:-konote_audit}" -q 2>/dev/null || AUDIT_DB_STATUS="UNREACHABLE"

# Database sizes (no PII — just byte counts)
DB_SIZE="unknown"
if [ "$DB_STATUS" = "OK" ]; then
    DB_SIZE=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h db -U "${POSTGRES_USER}" -d "${POSTGRES_DB:-konote}" -t -A \
        -c "SELECT pg_size_pretty(pg_database_size('${POSTGRES_DB:-konote}'));" 2>/dev/null || echo "unknown")
fi

AUDIT_DB_SIZE="unknown"
if [ "$AUDIT_DB_STATUS" = "OK" ]; then
    AUDIT_DB_SIZE=$(PGPASSWORD="${AUDIT_POSTGRES_PASSWORD}" psql -h audit_db -U "${AUDIT_POSTGRES_USER}" -d "${AUDIT_POSTGRES_DB:-konote_audit}" -t -A \
        -c "SELECT pg_size_pretty(pg_database_size('${AUDIT_POSTGRES_DB:-konote_audit}'));" 2>/dev/null || echo "unknown")
fi

# Latest backup info
LATEST_MAIN=$(ls -1t /backups/main_*.dump 2>/dev/null | head -1 || true)
if [ -n "${LATEST_MAIN:-}" ]; then
    LATEST_BACKUP_DATE=$(stat -c%y "$LATEST_MAIN" 2>/dev/null | cut -d. -f1)
    LATEST_BACKUP_SIZE=$(du -h "$LATEST_MAIN" | cut -f1)
else
    LATEST_BACKUP_DATE="NO BACKUPS FOUND"
    LATEST_BACKUP_SIZE="N/A"
fi

BACKUP_COUNT=$(find /backups -maxdepth 1 -name 'main_*.dump' 2>/dev/null | wc -l)

# Disk usage
DISK_USAGE=$(df -h / 2>/dev/null | tail -1 | awk '{print $5}')
DISK_AVAIL=$(df -h / 2>/dev/null | tail -1 | awk '{print $4}')

# --- Build report ---

REPORT=$(cat <<EOF
KoNote Daily Health Report
==========================
Generated: ${REPORT_DATE}
Instance:  ${DOMAIN:-unknown}
Version:   ${VERSION}

DATABASE STATUS
  Main DB:     ${DB_STATUS} (${DB_SIZE})
  Audit DB:    ${AUDIT_DB_STATUS} (${AUDIT_DB_SIZE})

BACKUPS
  Latest:        ${LATEST_BACKUP_DATE}
  Size:          ${LATEST_BACKUP_SIZE}
  Total on disk: ${BACKUP_COUNT} backup(s)

DISK
  Usage:     ${DISK_USAGE}
  Available: ${DISK_AVAIL}

---
This is an automated report from the KoNote ops sidecar.
No participant data is included in this report.
EOF
)

# --- Send or log ---

if [ -n "${OPS_HEALTH_REPORT_TO:-}" ] && [ -n "${EMAIL_HOST:-}" ]; then
    # Send via msmtp
    {
        echo "To: ${OPS_HEALTH_REPORT_TO}"
        echo "From: ${DEFAULT_FROM_EMAIL:-KoNote Ops <noreply@konote.app>}"
        echo "Subject: [KoNote] Daily Health Report - ${DOMAIN:-unknown} - $(date +%Y-%m-%d)"
        echo "Content-Type: text/plain; charset=UTF-8"
        echo ""
        echo "$REPORT"
    } | msmtp -t "${OPS_HEALTH_REPORT_TO}"

    echo "[$(date)] Health report emailed to ${OPS_HEALTH_REPORT_TO}"
else
    # Log to stdout (captured by Docker)
    echo ""
    echo "$REPORT"
    echo ""
fi
