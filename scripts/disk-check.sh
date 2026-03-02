#!/bin/bash
# KoNote VPS Disk Usage Monitor
# ==============================
# Alerts when disk usage exceeds threshold.
# Run via cron: 0 * * * * /opt/konote/scripts/disk-check.sh
#
# Optional:
#   - Set ALERT_WEBHOOK_URL in .env or environment to receive alerts
#     Alerts are sent as plain-text HTTP POST (no JSON, no Content-Type header).
#     Compatible with: UptimeRobot push monitors, Slack incoming webhooks,
#     ntfy.sh, Uptime Kuma push monitors.
#   - Set DISK_THRESHOLD (default: 80) to change the alert threshold percentage

set -euo pipefail

KONOTE_DIR="${KONOTE_DIR:-/opt/konote}"
THRESHOLD="${DISK_THRESHOLD:-80}"

# Load environment variables from .env
if [ -f "$KONOTE_DIR/.env" ]; then
    set -a
    source "$KONOTE_DIR/.env"
    set +a
fi

USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    MSG="KoNote VPS disk usage at ${USAGE}% (threshold: ${THRESHOLD}%)"
    echo "$(date): WARNING — $MSG"

    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
        curl -s -X POST "$ALERT_WEBHOOK_URL" -d "$MSG" || true
    fi
else
    echo "$(date): Disk usage at ${USAGE}% — OK"
fi
