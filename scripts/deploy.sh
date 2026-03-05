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
#   1. Pulls latest develop branch
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
NC='\033[0m'

PROD_DIR="/opt/konote"
DEV_DIR="/opt/konote-dev"

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
# deploy_instance — Deploy a single KoNote instance
# ==============================================================================
# Args: $1 = directory, $2 = instance name, $3 = "true" if dev instance
deploy_instance() {
    local dir="$1"
    local name="$2"
    local is_dev="$3"

    echo ""
    echo -e "${YELLOW}=== Deploying ${name} (${dir}) ===${NC}"

    if [ ! -d "$dir" ]; then
        echo -e "${RED}ERROR: Directory ${dir} does not exist${NC}"
        return 1
    fi

    cd "$dir"

    # --- Pull latest code ---
    echo "=== Pulling latest code ==="
    git pull origin develop

    # --- Rebuild web (and ops if Dockerfile.ops exists) ---
    echo "=== Rebuilding containers ==="
    docker compose build web
    if [ -f "Dockerfile.ops" ]; then
        docker compose build ops 2>/dev/null || true
    fi

    # --- Restart ---
    echo "=== Restarting ==="
    docker compose up -d

    # --- Wait for health check ---
    echo "=== Waiting for health check ==="
    local healthy=false
    for i in $(seq 1 30); do
        local status
        status=$(docker compose ps web --format "{{.Status}}" 2>/dev/null || echo "unknown")

        if echo "$status" | grep -q "healthy)"; then
            echo -e "${GREEN}=== ${name}: Deploy complete — web is healthy ===${NC}"
            healthy=true
            break
        fi

        # Check for crash-loop (restart count > 0)
        if echo "$status" | grep -q "Restarting"; then
            echo -e "${YELLOW}=== ${name}: Container is restarting ===${NC}"

            if [ "$is_dev" = "true" ]; then
                echo -e "${YELLOW}=== Dev instance: checking if migration failure ===${NC}"
                local logs
                logs=$(docker logs "$(docker compose ps -q web)" --tail=20 2>&1 || true)

                if echo "$logs" | grep -qiE "UndefinedTable|ProgrammingError|relation.*does not exist|migration.*error|migrate_default.*Phase|RuntimeError.*migrat"; then
                    echo -e "${YELLOW}=== Dev instance: migration failure detected ===${NC}"
                    echo -e "${YELLOW}=== Resetting dev database (demo data only — safe to reset) ===${NC}"
                    reset_dev_database "$dir"
                    healthy=true
                    break
                fi
            fi

            # Not a dev instance or not a migration failure — show logs and fail
            if [ "$is_dev" != "true" ]; then
                echo -e "${RED}=== ${name}: Container is crash-looping ===${NC}"
                docker compose logs web --tail=20
                return 1
            fi
        fi

        sleep 2
    done

    if [ "$healthy" != "true" ]; then
        echo -e "${RED}=== WARNING: ${name} — web container not healthy after 60s ===${NC}"
        docker compose logs web --tail=20
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

    # Read database config from .env
    local pg_user pg_db audit_user audit_db
    pg_user=$(grep '^POSTGRES_USER=' .env | cut -d= -f2)
    pg_db=$(grep '^POSTGRES_DB=' .env | cut -d= -f2)
    audit_user=$(grep '^AUDIT_POSTGRES_USER=' .env | cut -d= -f2)
    audit_db=$(grep '^AUDIT_POSTGRES_DB=' .env | cut -d= -f2)

    echo "  Dropping and recreating main database (${pg_db})..."
    docker compose exec -T db psql -U "$pg_user" -d postgres \
        -c "DROP DATABASE IF EXISTS ${pg_db};" \
        -c "CREATE DATABASE ${pg_db} OWNER ${pg_user};"

    echo "  Dropping and recreating audit database (${audit_db})..."
    docker compose exec -T audit_db psql -U "$audit_user" -d postgres \
        -c "DROP DATABASE IF EXISTS ${audit_db};" \
        -c "CREATE DATABASE ${audit_db} OWNER ${audit_user};"

    echo "  Starting web container (will auto-migrate and seed)..."
    docker compose up -d web

    # Wait for the fresh startup to complete
    echo "  Waiting for fresh startup..."
    for i in $(seq 1 60); do
        local status
        status=$(docker compose ps web --format "{{.Status}}" 2>/dev/null || echo "unknown")

        if echo "$status" | grep -q "healthy)"; then
            echo -e "${GREEN}  Dev database reset complete — web is healthy${NC}"
            return 0
        fi

        if echo "$status" | grep -q "Restarting"; then
            echo -e "${RED}  Dev instance still failing after database reset${NC}"
            docker compose logs web --tail=20
            return 1
        fi

        sleep 3
    done

    echo -e "${RED}  Dev instance not healthy after database reset (timeout 180s)${NC}"
    docker compose logs web --tail=20
    return 1
}

# ==============================================================================
# Main
# ==============================================================================

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
