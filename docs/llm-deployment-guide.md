# KoNote Deployment Guide — For AI Assistants

This guide is designed to be given to an AI coding assistant (Claude Code, Cursor, GitHub Copilot, etc.) so it can deploy KoNote on behalf of a nonprofit. It is structured as unambiguous, sequential instructions with exact commands and expected outputs.

**For the full human-readable guide with explanations**, see [deploy-ovhcloud.md](deploy-ovhcloud.md).

---

## Prerequisites (the human must provide these)

Before starting, collect these from the user:

| Item | Example | Notes |
|------|---------|-------|
| VPS IP address | `141.227.151.7` | From the hosting provider (OVHcloud, DigitalOcean, etc.) |
| VPS SSH user | `ubuntu` | OVHcloud default is `ubuntu` |
| SSH access method | Key-based or password | Must be able to run `ssh ubuntu@IP` successfully |
| Production domain | `konote.agency.ca` | DNS A record must point to VPS IP |
| Dev domain (optional) | `konote-dev.agency.ca` | DNS A record must point to same VPS IP |
| Organisation name | `Example Nonprofit` | Used in the UI |
| Admin email | `admin@agency.ca` | For the first admin account |

**Do not proceed until SSH access is confirmed.** Test with: `ssh ubuntu@VPS_IP 'echo ok'`

---

## Phase 1: Initial Server Setup

Run all commands via SSH on the VPS.

### 1.1 Update and secure the OS

```bash
ssh USER@VPS_IP "sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq"
ssh USER@VPS_IP "sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable"
ssh USER@VPS_IP "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq unattended-upgrades"
```

**Verify:** `ssh USER@VPS_IP "sudo ufw status"` — should show OpenSSH, 80/tcp, 443/tcp ALLOW.

### 1.2 Install Docker

```bash
ssh USER@VPS_IP "command -v docker >/dev/null 2>&1 && echo 'Docker already installed' || (curl -fsSL https://get.docker.com | sudo sh)"
```

**Verify:** `ssh USER@VPS_IP "docker --version && docker compose version"` — both should return version numbers.

### 1.3 Clone the repository

```bash
ssh USER@VPS_IP "sudo mkdir -p /opt/konote && sudo chown ubuntu:ubuntu /opt/konote"
ssh USER@VPS_IP "git clone https://github.com/LogicalOutcomes/konote.git /opt/konote"
```

If the repo is private, use a GitHub Personal Access Token:
```bash
ssh USER@VPS_IP "git clone https://TOKEN@github.com/LogicalOutcomes/konote.git /opt/konote"
```

**Verify:** `ssh USER@VPS_IP "ls /opt/konote/docker-compose.yml"` — file should exist.

---

## Phase 2: Generate Credentials

Generate all credentials **locally** (not on the VPS) and save them. These never change after initial setup.

```bash
# Generate on your local machine (requires Python 3 + cryptography)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
FIELD_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
AUDIT_POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
```

**CRITICAL:** Save all values, especially `FIELD_ENCRYPTION_KEY`. If lost, all encrypted participant data is permanently unrecoverable.

---

## Phase 3: Create .env File

Write the .env file to the VPS. Replace ALL placeholder values.

```bash
ssh USER@VPS_IP "cat > /opt/konote/.env << 'ENVEOF'
# KoNote Production Configuration
SECRET_KEY=REPLACE_SECRET_KEY
FIELD_ENCRYPTION_KEY=REPLACE_FIELD_ENCRYPTION_KEY

POSTGRES_USER=konote
POSTGRES_PASSWORD=REPLACE_POSTGRES_PASSWORD
POSTGRES_DB=konote

AUDIT_POSTGRES_USER=audit_writer
AUDIT_POSTGRES_PASSWORD=REPLACE_AUDIT_POSTGRES_PASSWORD
AUDIT_POSTGRES_DB=konote_audit

DOMAIN=REPLACE_DOMAIN
ALLOWED_HOSTS=REPLACE_DOMAIN,localhost
CSRF_TRUSTED_ORIGINS=https://REPLACE_DOMAIN

AUTH_MODE=local
KONOTE_MODE=production
DEMO_MODE=true
ENVEOF"
```

**Important:** `ALLOWED_HOSTS` MUST include `localhost` — the Docker health check pings `http://localhost:8000/auth/login/` from inside the container. Without it, the container never becomes healthy.

**Verify:** `ssh USER@VPS_IP "grep DOMAIN /opt/konote/.env"` — should show the correct domain.

Lock down the file:
```bash
ssh USER@VPS_IP "sudo chmod 600 /opt/konote/.env"
```

---

## Phase 4: Deploy

### 4.1 Set up the deploy script symlink

```bash
ssh USER@VPS_IP "ln -sf /opt/konote/scripts/deploy.sh /opt/konote/deploy.sh"
```

This ensures the deploy script always matches the git-tracked version.

### 4.2 Build and start

```bash
ssh USER@VPS_IP "cd /opt/konote && docker compose up -d --build"
```

This takes 2–5 minutes on first run. It builds the Docker image, starts 6 containers (web, db, audit_db, caddy, ops, autoheal), runs migrations, seeds demo data, and obtains an HTTPS certificate.

### 4.3 Wait for healthy

```bash
ssh USER@VPS_IP 'for i in $(seq 1 60); do
    status=$(cd /opt/konote && docker compose ps web --format "{{.Status}}" 2>/dev/null)
    if echo "$status" | grep -q "healthy)"; then echo "HEALTHY after ${i}0s"; exit 0; fi
    sleep 10
done
echo "TIMEOUT — check logs with: docker compose -f /opt/konote/docker-compose.yml logs web --tail=30"
exit 1'
```

**Expected:** "HEALTHY after Xs" within 2 minutes.

**If unhealthy:** Check logs: `ssh USER@VPS_IP "cd /opt/konote && docker compose logs web --tail=30"`

Common issues:
- "DisallowedHost" → `localhost` missing from `ALLOWED_HOSTS` in `.env`
- Certificate error in Caddy → DNS not yet pointing to VPS IP (Caddy retries automatically)
- Migration error → Check `.env` database credentials match

### 4.4 Create admin user

```bash
ssh USER@VPS_IP "cd /opt/konote && docker compose exec -T \
    -e DJANGO_SUPERUSER_USERNAME=admin \
    -e DJANGO_SUPERUSER_PASSWORD=REPLACE_ADMIN_PASSWORD \
    -e DJANGO_SUPERUSER_DISPLAY_NAME='System Admin' \
    web python manage.py createsuperuser --noinput"
```

### 4.5 Verify

```bash
ssh USER@VPS_IP "curl -s -o /dev/null -w '%{http_code}' --max-time 15 https://REPLACE_DOMAIN/auth/login/"
```

**Expected:** `200`

---

## Phase 5: Dev Instance (Optional but Recommended)

A dev instance lets the agency test changes safely with demo data. It uses the same VPS but separate databases and a separate subdomain.

### 5.1 DNS

Add an A record for `konote-dev.DOMAIN` pointing to the same VPS IP. Wait for propagation (usually 5–15 minutes).

### 5.2 Create shared Docker network

```bash
ssh USER@VPS_IP "docker network create konote-proxy 2>/dev/null || echo 'Network already exists'"
```

### 5.3 Production override (connect to shared network)

```bash
ssh USER@VPS_IP "cat > /opt/konote/docker-compose.override.yml << 'YAMLEOF'
services:
  web:
    networks:
      - frontend
      - backend
      - konote-proxy
  caddy:
    networks:
      - frontend
      - konote-proxy
networks:
  konote-proxy:
    external: true
YAMLEOF"
ssh USER@VPS_IP "cd /opt/konote && docker compose up -d"
```

### 5.4 Multi-domain Caddyfile

Replace the Caddyfile to serve both domains. Use **container names** (not service names) — both instances define a `web` service, so the name would be ambiguous.

```bash
ssh USER@VPS_IP "cat > /opt/konote/Caddyfile << 'CADDYEOF'
REPLACE_PROD_DOMAIN {
    reverse_proxy konote-web-1:8000
    header {
        Strict-Transport-Security \"max-age=31536000; includeSubDomains; preload\"
        X-Content-Type-Options \"nosniff\"
        Permissions-Policy \"camera=(), microphone=(), geolocation=(), payment=()\"
        -Server
    }
    encode gzip
}

REPLACE_DEV_DOMAIN {
    reverse_proxy konote-dev-web:8000
    header {
        Strict-Transport-Security \"max-age=31536000; includeSubDomains; preload\"
        X-Content-Type-Options \"nosniff\"
        Permissions-Policy \"camera=(), microphone=(), geolocation=(), payment=()\"
        -Server
    }
    encode gzip
}
CADDYEOF"
```

### 5.5 Clone and configure the dev instance

Generate separate credentials for dev:
```bash
DEV_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
DEV_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
DEV_PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DEV_AUDIT_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

Clone and write .env:
```bash
ssh USER@VPS_IP "sudo mkdir -p /opt/konote-dev && sudo chown ubuntu:ubuntu /opt/konote-dev"
ssh USER@VPS_IP "git clone https://github.com/LogicalOutcomes/konote.git /opt/konote-dev"
ssh USER@VPS_IP "cat > /opt/konote-dev/.env << 'ENVEOF'
DJANGO_SETTINGS_MODULE=konote.settings.production
SECRET_KEY=REPLACE_DEV_SECRET_KEY
FIELD_ENCRYPTION_KEY=REPLACE_DEV_ENCRYPTION_KEY

POSTGRES_USER=konote_dev
POSTGRES_PASSWORD=REPLACE_DEV_PG_PASSWORD
POSTGRES_DB=konote_dev

AUDIT_POSTGRES_USER=audit_dev
AUDIT_POSTGRES_PASSWORD=REPLACE_DEV_AUDIT_PASSWORD
AUDIT_POSTGRES_DB=konote_dev_audit

DOMAIN=REPLACE_DEV_DOMAIN
ALLOWED_HOSTS=REPLACE_DEV_DOMAIN,localhost
CSRF_TRUSTED_ORIGINS=https://REPLACE_DEV_DOMAIN

AUTH_MODE=local
KONOTE_MODE=demo
DEMO_MODE=true

DEFAULT_FROM_EMAIL=KoNote Dev <noreply@konote.app>
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_PORT=587
EMAIL_USE_TLS=True
ENVEOF"
```

### 5.6 Dev docker-compose override

```bash
ssh USER@VPS_IP "cat > /opt/konote-dev/docker-compose.override.yml << 'YAMLEOF'
services:
  web:
    container_name: konote-dev-web
    ports: !reset []
    networks:
      - frontend
      - backend
      - konote-proxy
  db:
    container_name: konote-dev-db
    volumes:
      - dev_pgdata:/var/lib/postgresql/data
  audit_db:
    container_name: konote-dev-audit-db
    volumes:
      - dev_audit_pgdata:/var/lib/postgresql/data
      - ./scripts/audit_db_init.sql:/docker-entrypoint-initdb.d/01-init.sql
  caddy:
    profiles:
      - disabled
  autoheal:
    container_name: konote-dev-autoheal
volumes:
  dev_pgdata:
  dev_audit_pgdata:
networks:
  konote-proxy:
    external: true
YAMLEOF"
```

### 5.7 Start dev instance and reload Caddy

```bash
ssh USER@VPS_IP "cd /opt/konote-dev && docker compose up -d --build"
ssh USER@VPS_IP "cd /opt/konote && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile"
```

### 5.8 Verify dev instance

```bash
ssh USER@VPS_IP "curl -s -o /dev/null -w '%{http_code}' --max-time 15 https://REPLACE_DEV_DOMAIN/auth/login/"
```

**Expected:** `200`

---

## Phase 6: Post-Deploy Checklist

Tell the user to complete these steps manually:

1. **Save credentials** in a password manager (especially `FIELD_ENCRYPTION_KEY`)
2. **Log in** at `https://DOMAIN` with the admin account
3. **Set organisation name** and terminology in Admin > Settings
4. **Set up external monitoring** — create a free account at [UptimeRobot](https://uptimerobot.com/) and add HTTPS monitors for both URLs
5. **Set up email** (optional) — see [deploy-ovhcloud.md Section 13](deploy-ovhcloud.md#13-set-up-email-external-relay) for Resend setup
6. **Print the encryption key** and store it in a safe place (not just digital)

---

## Ongoing: Updating KoNote

After changes are merged to the `develop` branch on GitHub:

```bash
# Production only
ssh USER@VPS_IP "/opt/konote/deploy.sh"

# Dev only
ssh USER@VPS_IP "/opt/konote/deploy.sh --dev"

# Both
ssh USER@VPS_IP "/opt/konote/deploy.sh --all"
```

The deploy script:
- Pulls latest code from `develop`
- Rebuilds the web container
- Restarts and waits for health check
- Logs events to `/var/log/konote-deploy.log`
- **Dev instance:** auto-resets the database if migrations fail (safe — demo data only)
- **Production:** prints a backup reminder before deploying

---

## Troubleshooting Quick Reference

| Symptom | Cause | Fix |
|---------|-------|-----|
| Container shows "unhealthy" | `localhost` missing from `ALLOWED_HOSTS` | Add `localhost` to `ALLOWED_HOSTS` in `.env`, then `docker compose up -d` |
| "502 Bad Gateway" | Web container crashed | `docker compose logs web --tail=30` to see the error |
| Certificate error | DNS not pointing to VPS | Check with `nslookup DOMAIN` — must show VPS IP. Caddy retries automatically every 60s |
| Migration error (production) | Database schema conflict | Check logs, may need to restore from backup |
| Migration error (dev) | Database out of sync | Run `/opt/konote/deploy.sh --dev` — auto-resets |
| "DisallowedHost" | Wrong domain in `.env` | Update `DOMAIN`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` in `.env` |
| Dev site shows old content | Dev not deployed | Run `/opt/konote/deploy.sh --dev` |

---

## Architecture Reference

```
VPS (/opt/konote/)                    VPS (/opt/konote-dev/)
├── .env (production secrets)         ├── .env (dev secrets)
├── docker-compose.yml                ├── docker-compose.yml
├── docker-compose.override.yml       ├── docker-compose.override.yml
├── Caddyfile (serves BOTH domains)   ├── Caddyfile (unused — disabled)
├── deploy.sh → scripts/deploy.sh     └── (no deploy.sh needed)
└── scripts/deploy.sh (the real one)

Containers (production):              Containers (dev):
  konote-web-1 (port 8000)             konote-dev-web (port 8000)
  konote-db-1 (PostgreSQL)             konote-dev-db (PostgreSQL)
  konote-audit_db-1 (PostgreSQL)       konote-dev-audit-db (PostgreSQL)
  konote-caddy-1 (ports 80,443)        (Caddy disabled — shares prod's)
  konote-ops-1 (backups/monitoring)    konote-dev-autoheal
  konote-autoheal-1

Shared: konote-proxy Docker network (Caddy → both web containers)
```
