#!/bin/bash
# ==============================================================================
# deploy.sh — Deploy KoNote instances on the VPS
# ==============================================================================
#
# Usage (run ON the VPS, not locally):
#   /opt/konote/deploy.sh          # Deploy production only
#   /opt/konote/deploy.sh --dev    # Deploy dev only
#   /opt/konote/deploy.sh --all    # Deploy both production and dev
#
# The /deploy-to-vps skill runs this via: ssh konote-vps /opt/konote/deploy.sh [flags]
#
# What it does:
#   1. Pulls latest code (main for production, develop for dev)
#   2. Rebuilds the web container
#   3. Restarts containers
#   4. Waits for health check
#
# For the dev instance (--dev or --all):
#   - If migrations fail (container crash-loops), automatically resets
#     the database and re-seeds demo data. This is safe because the dev
#     instance only has demo data (DEMO_MODE=true).
#
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROD_DIR="/opt/konote"
DEV_DIR="/opt/konote-dev"
DEPLOY_LOG="/var/log/konote-deploy.log"

# Parse arguments
DEPLOY_PROD=false
DEPLOY_DEV=false

case "${1:-}" in
    --dev)  DEPLOY_DEV=true ;;
    --all)  DEPLOY_PROD=true; DEPLOY_DEV=true ;;
    "")     DEPLOY_PROD=true ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo "Usage: $0 [--dev | --all]"
        exit 1
        ;;
esac

# ==============================================================================
# log_event — Append timestamped event to deploy log
# ==============================================================================
log_event() {
    local message="$1"
    echo "$(date -u +"%Y-%m-%d %H:%M:%S UTC") $message" >> "$DEPLOY_LOG" 2>/dev/null || true
}

# ==============================================================================
# validate_db_name — Ensure database name is safe (alphanumeric + underscore)
# ==============================================================================
validate_db_name() {
    local name="$1"
    local label="$2"
    if [[ ! "$name" =~ ^[a-zA-Z0-9_]+$ ]]; then
        echo -e "${RED}ERROR: Invalid ${label} in .env: '${name}'${NC}"
        echo -e "${RED}Database names must be alphanumeric with underscores only.${NC}"
        return 1
    fi
}

# ==============================================================================
# deploy_instance — Deploy a single KoNote instance
# ==============================================================================
# Args: $1 = directory, $2 = instance name, $3 = "true" if dev instance
deploy_instance() {
    local dir="$1"
    local name="$2"
    local is_dev="$3"

    echo ""
    echo -e "${YELLOW}=== Deploying ${name} (${dir}) ===${NC}"
    log_event "DEPLOY START: ${name} (${dir})"

    if [ ! -d "$dir" ]; then
        echo -e "${RED}ERROR: Directory ${dir} does not exist${NC}"
        log_event "DEPLOY FAILED: ${name} — directory not found"
        return 1
    fi

    cd "$dir"

    # --- Production backup reminder ---
    if [ "$is_dev" != "true" ]; then
        echo ""
        echo -e "${YELLOW}  ⚠ PRODUCTION DEPLOY — have you backed up today?${NC}"
        echo -e "  Run this first if not: ${CYAN}docker compose exec ops /usr/local/bin/ops-backup.sh${NC}"
        echo ""
    fi

    # --- Record before-commit ---
    local before_commit
    before_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo -e "  Before: ${CYAN}${before_commit}${NC}"

    # --- Pull latest code ---
    echo "=== Pulling latest code ==="

    # Preserve the Caddyfile — multi-instance setups use a custom Caddyfile
    # that differs from the single-instance template in the repo. Without
    # this, git operations overwrite it and Caddy routes break.
    # Uses cp (not shell variable) to preserve the file byte-for-byte.
    local caddyfile_saved=false
    if [ -f "Caddyfile" ]; then
        cp Caddyfile /tmp/.caddyfile.deploy.bak
        caddyfile_saved=true
    fi

    git checkout -- . 2>/dev/null || true  # Reset any local modifications (e.g. CRLF fixes)

    # Determine the correct branch for this instance
    local target_branch="main"
    if [ "$is_dev" = "true" ]; then
        target_branch="develop"
    fi

    # Ensure the instance is on the correct branch
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    if [ "$current_branch" != "$target_branch" ]; then
        echo -e "  ${YELLOW}Instance on '${current_branch}' — switching to '${target_branch}'${NC}"
        git fetch origin "$target_branch"
        git checkout "$target_branch"
        git reset --hard "origin/${target_branch}"
    fi

    git pull origin "$target_branch"

    # Restore the Caddyfile after all git operations are done
    if [ "$caddyfile_saved" = "true" ]; then
        cp /tmp/.caddyfile.deploy.bak Caddyfile
        rm -f /tmp/.caddyfile.deploy.bak
    fi

    # --- Record after-commit ---
    local after_commit
    after_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo -e "  After:  ${CYAN}${after_commit}${NC}"

    if [ "$before_commit" = "$after_commit" ]; then
        echo -e "  ${GREEN}Already up to date.${NC}"
    else
        echo -e "  ${GREEN}Updated: ${before_commit} → ${after_commit}${NC}"
    fi
    log_event "DEPLOY PULL: ${name} ${before_commit} → ${after_commit}"

    # --- Rebuild web (and ops if Dockerfile.ops exists) ---
    echo "=== Rebuilding containers ==="
    docker compose build web
    if [ -f "Dockerfile.ops" ]; then
        docker compose build ops 2>/dev/null || true
    fi

    # --- Restart ---
    echo "=== Restarting ==="
    docker compose up -d

    # --- Ensure Caddy can reach this instance + verify routing ---
    # Caddy runs in the production stack. For the dev instance, Caddy needs to
    # be connected to the dev frontend network so it can reverse-proxy to
    # konote-dev-web. Also verify the Caddyfile uses explicit container names
    # (not bare service names) to prevent Docker DNS conflicts.
    if [ "$is_dev" = "true" ]; then
        local caddy_container="konote-caddy-1"
        local dev_network="konote-dev_frontend"
        if docker ps --format '{{.Names}}' | grep -q "^${caddy_container}$"; then
            # Connect Caddy to dev network (idempotent)
            if ! docker inspect "$caddy_container" --format '{{json .NetworkSettings.Networks}}' | grep -q "$dev_network"; then
                echo "=== Connecting Caddy to dev frontend network ==="
                docker network connect "$dev_network" "$caddy_container" 2>/dev/null || true
            fi

            # Warn if Caddyfile uses bare service names (DNS conflict risk)
            local caddyfile_content
            caddyfile_content=$(docker exec "$caddy_container" cat /etc/caddy/Caddyfile 2>/dev/null || true)
            if echo "$caddyfile_content" | grep -q "reverse_proxy web:"; then
                echo -e "${YELLOW}  WARNING: Caddyfile uses bare 'web' service name instead of explicit${NC}"
                echo -e "${YELLOW}  container name. This causes DNS conflicts in multi-instance setups.${NC}"
                echo -e "${YELLOW}  Fix: use 'konote-web-1:8000' instead of 'web:8000' in the Caddyfile.${NC}"
                log_event "DEPLOY WARNING: Caddyfile uses bare 'web' — DNS conflict risk"
            fi
        fi
    fi

    # --- Wait for health check (time-based migration failure detection) ---
    echo "=== Waiting for health check ==="
    local healthy=false
    local checked_migration=false
    local elapsed=0
    local max_wait=120  # 2 minutes for production
    if [ "$is_dev" = "true" ]; then
        max_wait=300  # 5 minutes for dev (ghost migration cleanup can be slow)
    fi

    while [ "$elapsed" -lt "$max_wait" ]; do
        local status
        status=$(docker compose ps web --format "{{.Status}}" 2>/dev/null || echo "unknown")

        if echo "$status" | grep -q "healthy)"; then
            echo -e "${GREEN}=== ${name}: Deploy complete — web is healthy (${elapsed}s) ===${NC}"
            log_event "DEPLOY OK: ${name} — healthy in ${elapsed}s (${after_commit})"
            healthy=true
            break
        fi

        # Time-based migration failure check for dev instances:
        # After 30s without healthy, check the logs regardless of container status.
        # This avoids relying on catching the exact "Restarting" status string.
        if [ "$is_dev" = "true" ] && [ "$elapsed" -ge 30 ] && [ "$checked_migration" = "false" ]; then
            checked_migration=true
            echo -e "${YELLOW}=== Dev instance: not healthy after 30s — checking for migration errors ===${NC}"

            local logs
            logs=$(docker compose logs web --tail=40 2>&1 || true)

            if echo "$logs" | grep -qiE "UndefinedTable|ProgrammingError|relation.*does not exist|migration.*error|migrate_default.*Phase|RuntimeError.*migrat"; then
                echo -e "${YELLOW}=== Dev instance: migration failure detected ===${NC}"
                echo -e "${YELLOW}=== Resetting dev database (demo data only — safe to reset) ===${NC}"
                log_event "DEPLOY RESET: ${name} — migration failure, resetting database"
                reset_dev_database "$dir"
                healthy=true
                break
            fi
        fi

        # Re-check for migration errors every 15s after the first check at 30s
        # (the error may not appear until 40-60s when migrations take time)
        if [ "$is_dev" = "true" ] && [ "$checked_migration" = "true" ] && [ $((elapsed % 15)) -eq 0 ]; then
            local logs
            logs=$(docker compose logs web --tail=40 2>&1 || true)

            if echo "$logs" | grep -qiE "UndefinedTable|ProgrammingError|relation.*does not exist|migration.*error|migrate_default.*Phase|RuntimeError.*migrat"; then
                echo -e "${YELLOW}=== Dev instance: migration failure detected (at ${elapsed}s) ===${NC}"
                echo -e "${YELLOW}=== Resetting dev database (demo data only — safe to reset) ===${NC}"
                log_event "DEPLOY RESET: ${name} — migration failure at ${elapsed}s, resetting database"
                reset_dev_database "$dir"
                healthy=true
                break
            fi
        fi

        # For production crash-loops, fail fast
        if [ "$is_dev" != "true" ] && echo "$status" | grep -q "Restarting"; then
            echo -e "${RED}=== ${name}: Container is crash-looping ===${NC}"
            docker compose logs web --tail=20
            log_event "DEPLOY FAILED: ${name} — crash-loop (${after_commit})"
            return 1
        fi

        sleep 3
        elapsed=$((elapsed + 3))
    done

    if [ "$healthy" != "true" ]; then
        echo -e "${RED}=== WARNING: ${name} — web container not healthy after ${max_wait}s ===${NC}"
        docker compose logs web --tail=20
        log_event "DEPLOY FAILED: ${name} — timeout after ${max_wait}s (${after_commit})"
        return 1
    fi
}

# ==============================================================================
# reset_dev_database — Drop and recreate dev databases, then restart
# ==============================================================================
# This is ONLY called for the dev instance when migrations fail.
# The dev instance uses DEMO_MODE=true, so all data is demo data.
reset_dev_database() {
    local dir="$1"
    cd "$dir"

    echo "  Stopping web container..."
    docker compose stop web

    # Read database config from .env and validate
    local pg_user pg_db audit_user audit_db
    pg_user=$(grep '^POSTGRES_USER=' .env | cut -d= -f2)
    pg_db=$(grep '^POSTGRES_DB=' .env | cut -d= -f2)
    audit_user=$(grep '^AUDIT_POSTGRES_USER=' .env | cut -d= -f2)
    audit_db=$(grep '^AUDIT_POSTGRES_DB=' .env | cut -d= -f2)

    validate_db_name "$pg_user" "POSTGRES_USER" || return 1
    validate_db_name "$pg_db" "POSTGRES_DB" || return 1
    validate_db_name "$audit_user" "AUDIT_POSTGRES_USER" || return 1
    validate_db_name "$audit_db" "AUDIT_POSTGRES_DB" || return 1

    # Use dropdb/createdb CLI tools instead of raw SQL interpolation
    echo "  Dropping and recreating main database (${pg_db})..."
    docker compose exec -T db dropdb -U "$pg_user" --if-exists "$pg_db"
    docker compose exec -T db createdb -U "$pg_user" -O "$pg_user" "$pg_db"

    echo "  Dropping and recreating audit database (${audit_db})..."
    docker compose exec -T audit_db dropdb -U "$audit_user" --if-exists "$audit_db"
    docker compose exec -T audit_db createdb -U "$audit_user" -O "$audit_user" "$audit_db"

    echo "  Starting web container (will auto-migrate and seed)..."
    docker compose up -d web

    # Wait for the fresh startup to complete
    echo "  Waiting for fresh startup..."
    local elapsed=0
    local max_wait=180  # 3 minutes for fresh migration + seed

    while [ "$elapsed" -lt "$max_wait" ]; do
        local status
        status=$(docker compose ps web --format "{{.Status}}" 2>/dev/null || echo "unknown")

        if echo "$status" | grep -q "healthy)"; then
            echo -e "${GREEN}  Dev database reset complete — web is healthy (${elapsed}s)${NC}"
            log_event "DEPLOY RESET OK: Dev — healthy in ${elapsed}s after DB reset"
            return 0
        fi

        if echo "$status" | grep -q "Restarting"; then
            echo -e "${RED}  Dev instance still failing after database reset${NC}"
            docker compose logs web --tail=20
            log_event "DEPLOY RESET FAILED: Dev — still crash-looping after DB reset"
            return 1
        fi

        sleep 3
        elapsed=$((elapsed + 3))
    done

    echo -e "${RED}  Dev instance not healthy after database reset (timeout ${max_wait}s)${NC}"
    docker compose logs web --tail=20
    log_event "DEPLOY RESET FAILED: Dev — timeout after ${max_wait}s"
    return 1
}

# ==============================================================================
# Main
# ==============================================================================

log_event "--- deploy.sh invoked with args: ${*:-<none>}"

FAILED=0

if [ "$DEPLOY_PROD" = "true" ]; then
    deploy_instance "$PROD_DIR" "Production" "false" || FAILED=$((FAILED + 1))
fi

if [ "$DEPLOY_DEV" = "true" ]; then
    deploy_instance "$DEV_DIR" "Dev" "true" || FAILED=$((FAILED + 1))
fi

if [ $FAILED -gt 0 ]; then
    echo ""
    echo -e "${RED}=== ${FAILED} instance(s) failed to deploy ===${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== All deployments complete ===${NC}"
exit 0
