#!/bin/bash
# ==============================================================================
# KoNote Ops — Docker System Prune
# ==============================================================================
# Weekly cleanup of unused Docker images and containers.
# Disable by setting OPS_PRUNE_ENABLED=false in .env.
set -euo pipefail

# Load environment (cron runs without env vars on Alpine)
set -a; source /etc/environment; set +a

if [ "${OPS_PRUNE_ENABLED:-true}" != "true" ]; then
    echo "[$(date)] Docker prune disabled (OPS_PRUNE_ENABLED=${OPS_PRUNE_ENABLED})"
    exit 0
fi

echo "[$(date)] Running docker system prune..."
docker system prune -f 2>&1
echo "[$(date)] Docker prune complete."
