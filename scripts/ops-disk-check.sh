#!/bin/bash
# ==============================================================================
# KoNote Ops — Disk Usage Check
# ==============================================================================
# Alerts when disk usage exceeds threshold. Runs hourly via ops sidecar cron.
set -euo pipefail

# Load environment (cron runs without env vars on Alpine)
set -a; source /etc/environment; set +a

THRESHOLD="${DISK_THRESHOLD:-80}"
USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    MSG="KoNote VPS disk usage at ${USAGE}% (threshold: ${THRESHOLD}%)"
    echo "$(date): WARNING -- $MSG"

    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
        curl -s -m 10 -X POST "$ALERT_WEBHOOK_URL" -d "$MSG" || true
    fi
else
    echo "$(date): Disk usage at ${USAGE}% -- OK"
fi
