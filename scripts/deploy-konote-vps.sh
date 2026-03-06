#!/bin/bash
# ==============================================================================
# deploy-konote-vps.sh — Automated KoNote Agency Provisioning
# ==============================================================================
#
# Deploys a new KoNote instance on an OVHcloud VPS (Ubuntu 24.04+).
# Automates the manual steps from docs/deploy-ovhcloud.md.
#
# Usage:
#   ./scripts/deploy-konote-vps.sh \
#     --host YOUR_VPS_IP \
#     --domain konote.agency.ca \
#     --admin-email admin@agency.ca \
#     --org-name "My Nonprofit"
#
# Prerequisites:
#   - SSH access to the target VPS (key-based recommended)
#   - Domain DNS A record pointing to the VPS IP
#   - Python 3 with cryptography package (locally, for key generation)
#
# Design doc: docs/plans/2026-02-20-deploy-script-design.md
# ==============================================================================

set -euo pipefail

# ==============================================================================
# Colour output
# ==============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No colour

step_msg()  { echo -e "${YELLOW}▸ $1${NC}"; }
ok_msg()    { echo -e "  ${GREEN}✓ $1${NC}"; }
err_msg()   { echo -e "  ${RED}✗ $1${NC}"; }
info_msg()  { echo -e "  ${CYAN}ℹ $1${NC}"; }
warn_msg()  { echo -e "  ${YELLOW}⚠ $1${NC}"; }

# ==============================================================================
# Defaults
# ==============================================================================
HOST=""
DOMAIN=""
ADMIN_EMAIL=""
ORG_NAME=""
ADMIN_USER="admin"
CLIENT_TERM="client"
SSH_KEY=""
SSH_USER="ubuntu"
BRANCH="main"
DRY_RUN=false
FORCE_ENV=false
DEPLOY_DIR="/opt/konote"
REPO_URL="https://github.com/LogicalOutcomes/konote.git"

# ==============================================================================
# Usage
# ==============================================================================
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Deploy a new KoNote instance on an OVHcloud VPS.

Required:
  --host HOST             VPS IP address or hostname
  --domain DOMAIN         Domain name (e.g., konote.agency.ca)
  --admin-email EMAIL     Email for the admin user
  --org-name NAME         Organization name

Optional:
  --admin-user USER       Admin username (default: admin)
  --client-term TERM      What participants are called (default: client)
  --ssh-key PATH          Path to SSH private key
  --ssh-user USER         SSH username (default: ubuntu)
  --branch BRANCH         Git branch to deploy (default: main)
  --force-env             Overwrite existing .env file on VPS
  --dry-run               Print commands without executing
  --help                  Show this help message

Examples:
  # Basic deployment
  $(basename "$0") --host YOUR_VPS_IP --domain konote.example.ca \\
    --admin-email admin@example.ca --org-name "Example Nonprofit"

  # With SSH key and custom branch
  $(basename "$0") --host YOUR_VPS_IP --domain konote.example.ca \\
    --admin-email admin@example.ca --org-name "Example Nonprofit" \\
    --ssh-key ~/.ssh/ovh_konote --branch develop

  # Dry run (preview commands)
  $(basename "$0") --host YOUR_VPS_IP --domain konote.example.ca \\
    --admin-email admin@example.ca --org-name "Example Nonprofit" --dry-run
EOF
    exit 0
}

# ==============================================================================
# Parse arguments
# ==============================================================================
while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)        HOST="$2"; shift 2 ;;
        --domain)      DOMAIN="$2"; shift 2 ;;
        --admin-email) ADMIN_EMAIL="$2"; shift 2 ;;
        --org-name)    ORG_NAME="$2"; shift 2 ;;
        --admin-user)  ADMIN_USER="$2"; shift 2 ;;
        --client-term) CLIENT_TERM="$2"; shift 2 ;;
        --ssh-key)     SSH_KEY="$2"; shift 2 ;;
        --ssh-user)    SSH_USER="$2"; shift 2 ;;
        --branch)      BRANCH="$2"; shift 2 ;;
        --force-env)   FORCE_ENV=true; shift ;;
        --dry-run)     DRY_RUN=true; shift ;;
        --help)        usage ;;
        *)
            err_msg "Unknown option: $1"
            echo "Run '$(basename "$0") --help' for usage."
            exit 1
            ;;
    esac
done

# ==============================================================================
# Validate required arguments
# ==============================================================================
MISSING=()
[[ -z "$HOST" ]]        && MISSING+=("--host")
[[ -z "$DOMAIN" ]]      && MISSING+=("--domain")
[[ -z "$ADMIN_EMAIL" ]] && MISSING+=("--admin-email")
[[ -z "$ORG_NAME" ]]    && MISSING+=("--org-name")

if [[ ${#MISSING[@]} -gt 0 ]]; then
    err_msg "Missing required arguments: ${MISSING[*]}"
    echo "Run '$(basename "$0") --help' for usage."
    exit 1
fi

# ==============================================================================
# SSH setup (ControlMaster for connection reuse — disabled on Windows/MSYS2)
# ==============================================================================
SSH_OPTS=(
    -o "StrictHostKeyChecking=accept-new"
    -o "ConnectTimeout=15"
)

# ControlMaster uses Unix domain sockets which don't work on Windows/MSYS2/Git Bash
if [[ "$(uname -s)" != MINGW* && "$(uname -s)" != MSYS* && "$(uname -s)" != CYGWIN* ]]; then
    SSH_CONTROL_DIR=$(mktemp -d)
    SSH_CONTROL_PATH="${SSH_CONTROL_DIR}/konote-%r@%h:%p"
    SSH_OPTS+=(
        -o "ControlMaster=auto"
        -o "ControlPath=${SSH_CONTROL_PATH}"
        -o "ControlPersist=300"
    )
fi

if [[ -n "$SSH_KEY" ]]; then
    SSH_OPTS+=(-i "$SSH_KEY")
fi

SSH_TARGET="${SSH_USER}@${HOST}"

# Helper: run a command on the VPS via SSH
run_remote() {
    if [[ "$DRY_RUN" == true ]]; then
        echo "  [DRY RUN] ssh ${SSH_TARGET}: $*"
        return 0
    fi
    ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "$@"
}

# Helper: run a command on the VPS with sudo
run_remote_sudo() {
    run_remote "sudo bash -c '$*'"
}

# Cleanup: close SSH ControlMaster on exit (only if enabled)
cleanup() {
    if [[ -n "${SSH_CONTROL_DIR:-}" ]]; then
        ssh "${SSH_OPTS[@]}" -O exit "${SSH_TARGET}" 2>/dev/null || true
        rm -rf "${SSH_CONTROL_DIR}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ==============================================================================
# Pre-flight checks
# ==============================================================================
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        KoNote VPS Deployment Script              ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Host:        ${CYAN}${HOST}${NC}"
echo -e "  Domain:      ${CYAN}${DOMAIN}${NC}"
echo -e "  Org:         ${CYAN}${ORG_NAME}${NC}"
echo -e "  Admin:       ${CYAN}${ADMIN_USER} <${ADMIN_EMAIL}>${NC}"
echo -e "  Branch:      ${CYAN}${BRANCH}${NC}"
echo -e "  Client term: ${CYAN}${CLIENT_TERM}${NC}"
if [[ "$DRY_RUN" == true ]]; then
    echo -e "  Mode:        ${YELLOW}DRY RUN (no changes will be made)${NC}"
fi
echo ""

# --- Check local Python + cryptography ---
step_msg "Pre-flight: Checking local Python..."
if ! command -v python3 &>/dev/null; then
    err_msg "Python 3 is required locally for credential generation."
    err_msg "Install Python 3 and the 'cryptography' package, then retry."
    exit 1
fi

if ! python3 -c "from cryptography.fernet import Fernet" 2>/dev/null; then
    err_msg "Python 'cryptography' package is required locally."
    err_msg "Install it: pip install cryptography"
    exit 1
fi
ok_msg "Python 3 + cryptography available"

# --- Check SSH connectivity ---
step_msg "Pre-flight: Testing SSH connection to ${HOST}..."
if [[ "$DRY_RUN" == false ]]; then
    if ! ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "echo ok" &>/dev/null; then
        err_msg "Cannot connect to ${SSH_TARGET}"
        err_msg "Check that:"
        err_msg "  - The VPS IP is correct"
        err_msg "  - Your SSH key is set up (see deploy-ovhcloud.md Step 1)"
        err_msg "  - The VPS is running and accepting connections"
        exit 1
    fi
    ok_msg "SSH connection successful"
else
    info_msg "[DRY RUN] Skipping SSH connection test"
fi

# ==============================================================================
# Generate credentials (locally)
# ==============================================================================
step_msg "Generating credentials locally..."

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
FIELD_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
AUDIT_POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

ok_msg "All credentials generated (Django secret, encryption key, 2 DB passwords, admin password)"

# Save credentials locally for disaster recovery
CREDS_FILE="konote-credentials-${DOMAIN}-$(date +%Y%m%d_%H%M%S).txt"
cat > "$CREDS_FILE" <<CREDS
# KoNote Credentials for ${DOMAIN}
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
#
# KEEP THIS FILE SECURE — it contains all keys needed to access
# and decrypt your data.
#
# Save these in your password manager, then delete this file.

DOMAIN=${DOMAIN}
ADMIN_USER=${ADMIN_USER}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
SECRET_KEY=${SECRET_KEY}
FIELD_ENCRYPTION_KEY=${FIELD_ENCRYPTION_KEY}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
AUDIT_POSTGRES_PASSWORD=${AUDIT_POSTGRES_PASSWORD}
CREDS
chmod 600 "$CREDS_FILE"
ok_msg "Credentials saved to ./${CREDS_FILE}"
warn_msg "Save this file in your password manager, then delete it"

# Capture version for health reports (local repo commit being deployed)
DEPLOY_VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# ==============================================================================
# Step 1/9: Secure the VPS
# ==============================================================================
STEP=1
TOTAL=9
step_msg "Step ${STEP}/${TOTAL}: Securing the VPS (updates, firewall, auto-updates)..."

run_remote "sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq"
ok_msg "System packages updated"

# Configure firewall
run_remote "sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable" 2>/dev/null
ok_msg "Firewall configured (SSH + HTTP + HTTPS)"

# Enable unattended security upgrades
run_remote "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq unattended-upgrades"
run_remote "echo 'Unattended-Upgrade::Automatic-Reboot \"false\";' | sudo tee /etc/apt/apt.conf.d/51konote-no-reboot >/dev/null"
ok_msg "Unattended security upgrades enabled (auto-reboot disabled)"

# ==============================================================================
# Step 2/9: Install Docker
# ==============================================================================
STEP=2
step_msg "Step ${STEP}/${TOTAL}: Installing Docker..."

DOCKER_INSTALLED=$(run_remote "command -v docker >/dev/null 2>&1 && echo yes || echo no")

if [[ "$DOCKER_INSTALLED" == "yes" ]]; then
    DOCKER_VERSION=$(run_remote "docker --version 2>/dev/null | head -1")
    ok_msg "Docker already installed: ${DOCKER_VERSION}"
else
    run_remote "curl -fsSL https://get.docker.com | sudo sh"
    DOCKER_VERSION=$(run_remote "docker --version 2>/dev/null | head -1")
    ok_msg "Docker installed: ${DOCKER_VERSION}"
fi

# Verify docker compose is available
COMPOSE_VERSION=$(run_remote "sudo docker compose version 2>/dev/null | head -1" || true)
if [[ -z "$COMPOSE_VERSION" ]]; then
    err_msg "Docker Compose not found. Docker installation may be incomplete."
    exit 1
fi
ok_msg "Docker Compose available: ${COMPOSE_VERSION}"

# ==============================================================================
# Step 3/9: Clone KoNote
# ==============================================================================
STEP=3
step_msg "Step ${STEP}/${TOTAL}: Cloning KoNote to ${DEPLOY_DIR}..."

REPO_EXISTS=$(run_remote "test -d ${DEPLOY_DIR}/.git && echo yes || echo no")

if [[ "$REPO_EXISTS" == "yes" ]]; then
    info_msg "Repository already exists at ${DEPLOY_DIR}"
    run_remote "cd ${DEPLOY_DIR} && sudo git fetch origin && sudo git checkout ${BRANCH} && sudo git pull origin ${BRANCH}"
    ok_msg "Updated to latest ${BRANCH}"
else
    run_remote "sudo mkdir -p ${DEPLOY_DIR}"
    run_remote "sudo git clone --branch ${BRANCH} ${REPO_URL} ${DEPLOY_DIR}"
    ok_msg "Cloned ${BRANCH} branch to ${DEPLOY_DIR}"
fi

# ==============================================================================
# Step 4/9: Create .env file
# ==============================================================================
STEP=4
step_msg "Step ${STEP}/${TOTAL}: Creating .env configuration file..."

ENV_EXISTS=$(run_remote "test -f ${DEPLOY_DIR}/.env && echo yes || echo no")

if [[ "$ENV_EXISTS" == "yes" && "$FORCE_ENV" == false ]]; then
    warn_msg ".env file already exists at ${DEPLOY_DIR}/.env"
    warn_msg "Use --force-env to overwrite (this will regenerate ALL credentials)"
    info_msg "Skipping .env creation — using existing file"
else
    if [[ "$ENV_EXISTS" == "yes" ]]; then
        # Back up existing .env before overwriting
        run_remote "sudo cp ${DEPLOY_DIR}/.env ${DEPLOY_DIR}/.env.backup.\$(date +%Y%m%d_%H%M%S)"
        info_msg "Backed up existing .env"
    fi

    # Write .env via heredoc over SSH (credentials travel through the SSH tunnel)
    if [[ "$DRY_RUN" == true ]]; then
        info_msg "[DRY RUN] Would write .env to ${DEPLOY_DIR}/.env"
    else
        ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "sudo tee ${DEPLOY_DIR}/.env > /dev/null" <<ENVFILE
# ==============================================================================
# KoNote Production Configuration
# Generated by deploy-konote-vps.sh on $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# ==============================================================================

# --- Security Keys ---
SECRET_KEY=${SECRET_KEY}
FIELD_ENCRYPTION_KEY=${FIELD_ENCRYPTION_KEY}

# --- Main Database ---
POSTGRES_USER=konote
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=konote

# --- Audit Database ---
AUDIT_POSTGRES_USER=audit_writer
AUDIT_POSTGRES_PASSWORD=${AUDIT_POSTGRES_PASSWORD}
AUDIT_POSTGRES_DB=konote_audit

# --- Domain & Security ---
DOMAIN=${DOMAIN}
ALLOWED_HOSTS=${DOMAIN},localhost
CSRF_TRUSTED_ORIGINS=https://${DOMAIN}
AUTH_MODE=local
KONOTE_MODE=production

# --- Demo Mode ---
# Creates demo users with quick-login buttons for staff training.
# Demo users are separate from real participants (is_demo=True).
DEMO_MODE=true

# --- Email (configure manually later — see deploy-ovhcloud.md Step 13) ---
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.resend.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=resend
# EMAIL_HOST_PASSWORD=re_your_resend_api_key
# DEFAULT_FROM_EMAIL=KoNote <noreply@${DOMAIN}>

# --- Ops Sidecar (optional — see deploy-ovhcloud.md Section 11) ---
# Dead man's switch: alerts you if backups STOP running
# HEALTHCHECK_PING_URL=https://hc-ping.com/your-uuid-here
# Alert webhook: notifies on backup failure or disk warnings
# ALERT_WEBHOOK_URL=https://ntfy.sh/your-topic
# Daily health email recipient (requires email configured above)
# OPS_HEALTH_REPORT_TO=admin@youragency.ca
# Backup retention (defaults: 30 days main, 90 days audit)
# BACKUP_RETENTION_DAYS=30
# AUDIT_RETENTION_DAYS=90

# --- AI Features (optional) ---
# OPENROUTER_API_KEY=sk-or-...

# --- Version (set during deploy for health reports) ---
KONOTE_VERSION=${DEPLOY_VERSION:-unknown}
ENVFILE
    fi

    # Lock down .env permissions
    run_remote "sudo chmod 600 ${DEPLOY_DIR}/.env"
    run_remote "sudo chown root:root ${DEPLOY_DIR}/.env"
    ok_msg ".env written and locked down (chmod 600, owned by root)"
fi

# ==============================================================================
# Step 5/9: Deploy (docker compose up)
# ==============================================================================
STEP=5
step_msg "Step ${STEP}/${TOTAL}: Building and starting containers..."

run_remote "cd ${DEPLOY_DIR} && sudo docker compose up -d --build"
ok_msg "Docker Compose started"

# ==============================================================================
# Step 6/9: Wait for health check
# ==============================================================================
STEP=6
step_msg "Step ${STEP}/${TOTAL}: Waiting for KoNote to become healthy..."

if [[ "$DRY_RUN" == true ]]; then
    info_msg "[DRY RUN] Would wait for health check"
else
    MAX_WAIT=300  # 5 minutes
    INTERVAL=10
    ELAPSED=0

    while [[ $ELAPSED -lt $MAX_WAIT ]]; do
        HEALTH=$(run_remote "sudo docker compose -f ${DEPLOY_DIR}/docker-compose.yml ps --format json 2>/dev/null | grep -o '\"Health\":\"[^\"]*\"' | head -1" || true)

        if echo "$HEALTH" | grep -q "healthy"; then
            ok_msg "Web container is healthy (${ELAPSED}s)"
            break
        fi

        if [[ $ELAPSED -gt 0 && $((ELAPSED % 30)) -eq 0 ]]; then
            info_msg "Still waiting... (${ELAPSED}s / ${MAX_WAIT}s)"
        fi

        sleep "$INTERVAL"
        ELAPSED=$((ELAPSED + INTERVAL))
    done

    if [[ $ELAPSED -ge $MAX_WAIT ]]; then
        warn_msg "Health check timed out after ${MAX_WAIT}s"
        warn_msg "The container may still be starting (first build can take 5+ minutes)"
        info_msg "Check logs: ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo docker compose logs -f web'"
        info_msg "Continuing with remaining steps..."
    fi
fi

# ==============================================================================
# Step 7/9: Create admin user
# ==============================================================================
STEP=7
step_msg "Step ${STEP}/${TOTAL}: Creating admin user '${ADMIN_USER}'..."

if [[ "$DRY_RUN" == true ]]; then
    info_msg "[DRY RUN] Would create admin user"
else
    # Use Django's createsuperuser --noinput with env vars
    # The password and username are passed as environment variables for this
    # single command execution, not stored anywhere on the VPS.
    ADMIN_CREATE_RESULT=$(run_remote "cd ${DEPLOY_DIR} && sudo docker compose exec -T \
        -e DJANGO_SUPERUSER_USERNAME='${ADMIN_USER}' \
        -e DJANGO_SUPERUSER_PASSWORD='${ADMIN_PASSWORD}' \
        -e DJANGO_SUPERUSER_DISPLAY_NAME='System Admin' \
        web python manage.py createsuperuser --noinput 2>&1" || true)

    if echo "$ADMIN_CREATE_RESULT" | grep -qi "already taken\|already exists\|duplicate"; then
        warn_msg "Admin user '${ADMIN_USER}' already exists — skipping"
    elif echo "$ADMIN_CREATE_RESULT" | grep -qi "error\|traceback"; then
        warn_msg "Admin creation had issues: ${ADMIN_CREATE_RESULT}"
        info_msg "You can create the admin manually: ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo docker compose exec web python manage.py createsuperuser'"
    else
        ok_msg "Admin user '${ADMIN_USER}' created"
    fi
fi

# ==============================================================================
# Step 8/9: Verify ops sidecar (automated backups + monitoring)
# ==============================================================================
STEP=8
step_msg "Step ${STEP}/${TOTAL}: Verifying ops sidecar..."

# Create backup directory on host (bind-mounted into ops container)
run_remote "sudo mkdir -p ${DEPLOY_DIR}/backups"

# The ops container handles all scheduled tasks automatically:
#   - Nightly database backups (2 AM)
#   - Hourly disk usage checks
#   - Daily health report emails (7 AM)
#   - Weekly Docker cleanup (Sundays 4 AM)
#   - Weekly backup verification (Sundays 5 AM)
# No host-level cron jobs needed.

if [[ "$DRY_RUN" == true ]]; then
    info_msg "[DRY RUN] Would verify ops container started"
else
    OPS_STATUS=$(run_remote "cd ${DEPLOY_DIR} && sudo docker compose ps ops --format json 2>/dev/null | grep -o '\"State\":\"[^\"]*\"' | head -1" || true)

    if echo "$OPS_STATUS" | grep -q "running"; then
        ok_msg "Ops sidecar running (automated backups, monitoring, health reports)"
    else
        warn_msg "Ops container may still be starting"
        info_msg "Check: ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo docker compose logs ops'"
    fi
fi

info_msg "Backups run automatically at 2 AM (configurable via .env)"
info_msg "Set OPS_HEALTH_REPORT_TO in .env for daily health emails"
info_msg "Set HEALTHCHECK_PING_URL in .env for dead man's switch monitoring"

# ==============================================================================
# Step 9/9: Verify deployment
# ==============================================================================
STEP=9
step_msg "Step ${STEP}/${TOTAL}: Verifying deployment..."

if [[ "$DRY_RUN" == true ]]; then
    info_msg "[DRY RUN] Would verify HTTPS at https://${DOMAIN}/auth/login/"
else
    # Check HTTPS endpoint from the VPS itself (doesn't depend on DNS propagation
    # to the operator's machine)
    HTTP_STATUS=$(run_remote "curl -s -o /dev/null -w '%{http_code}' --max-time 15 https://${DOMAIN}/auth/login/ 2>/dev/null" || echo "000")

    if [[ "$HTTP_STATUS" == "200" ]]; then
        ok_msg "HTTPS is working — https://${DOMAIN}/auth/login/ returned 200"
    elif [[ "$HTTP_STATUS" == "000" ]]; then
        warn_msg "Could not reach https://${DOMAIN}/ from the VPS"
        info_msg "This is normal if DNS hasn't fully propagated yet."
        info_msg "Caddy will obtain the HTTPS certificate automatically once DNS resolves."
        info_msg "Check Caddy logs: ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo docker compose logs caddy'"
    else
        warn_msg "https://${DOMAIN}/auth/login/ returned HTTP ${HTTP_STATUS}"
        info_msg "The app may still be starting. Check: ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo docker compose logs web'"
    fi
fi

# ==============================================================================
# Final summary
# ==============================================================================
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║              Deployment Complete                 ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}URL:${NC}           https://${DOMAIN}"
echo -e "  ${GREEN}Admin user:${NC}    ${ADMIN_USER}"
echo -e "  ${GREEN}Admin email:${NC}   ${ADMIN_EMAIL}"
echo -e "  ${GREEN}Admin pass:${NC}    ${ADMIN_PASSWORD}"
echo ""
echo -e "${RED}${BOLD}  ┌──────────────────────────────────────────────────────────┐${NC}"
echo -e "${RED}${BOLD}  │  WARNING: SAVE THESE CREDENTIALS NOW                     │${NC}"
echo -e "${RED}${BOLD}  │                                                          │${NC}"
echo -e "${RED}${BOLD}  │  Encryption Key:                                         │${NC}"
echo -e "${RED}${BOLD}  │  ${FIELD_ENCRYPTION_KEY}  │${NC}"
echo -e "${RED}${BOLD}  │                                                          │${NC}"
echo -e "${RED}${BOLD}  │  If you lose this key, ALL encrypted participant data    │${NC}"
echo -e "${RED}${BOLD}  │  (names, emails, birth dates) is PERMANENTLY lost.       │${NC}"
echo -e "${RED}${BOLD}  │                                                          │${NC}"
echo -e "${RED}${BOLD}  │  Save it in your password manager NOW.                   │${NC}"
echo -e "${RED}${BOLD}  │  Print a backup copy and store it securely.              │${NC}"
echo -e "${RED}${BOLD}  └──────────────────────────────────────────────────────────┘${NC}"
echo ""
echo -e "  ${YELLOW}Post-deploy checklist:${NC}"
echo -e "    1. Save ALL credentials above in your password manager"
echo -e "    2. Verify DNS: nslookup ${DOMAIN} (should return ${HOST})"
echo -e "    3. Log in at https://${DOMAIN} and set org name + terminology"
echo -e "    4. Set up UptimeRobot monitoring: https://uptimerobot.com/"
echo -e "    5. Set up email relay (Resend/Brevo) — see deploy-ovhcloud.md Step 13"
echo -e "    6. Set OPS_HEALTH_REPORT_TO in .env for daily health emails"
echo -e "    7. Set HEALTHCHECK_PING_URL in .env for backup dead man's switch"
echo ""
echo -e "  ${GREEN}Automated by ops sidecar (no action needed):${NC}"
echo -e "    - Nightly database backups at 2 AM"
echo -e "    - Hourly disk usage monitoring"
echo -e "    - Weekly Docker cleanup (Sundays 4 AM)"
echo -e "    - Weekly backup verification (Sundays 5 AM)"
echo ""
echo -e "  ${CYAN}Useful commands:${NC}"
echo -e "    View logs:     ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo docker compose logs -f web'"
echo -e "    Ops logs:      ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo docker compose logs --tail 50 ops'"
echo -e "    Restart:       ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo docker compose up -d'"
echo -e "    Update:        ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo git pull && sudo docker compose up -d --build'"
echo -e "    Manual backup: ssh ${SSH_TARGET} 'cd ${DEPLOY_DIR} && sudo docker compose exec ops /usr/local/bin/ops-backup.sh'"
echo ""
