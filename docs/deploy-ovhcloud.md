# Deploying KoNote on OVHcloud VPS

This guide walks you through deploying KoNote on an OVHcloud VPS from scratch. It assumes:

- You have an OVHcloud VPS with Ubuntu 24.04 or 25.04 (fresh install)
- You have a domain name you can point to the VPS
- You are working from a Windows computer
- You have Claude Code available to help if you get stuck

**Time estimate:** 45–90 minutes for a first deployment.

---

## Table of Contents

1. [Connect to Your VPS via SSH](#1-connect-to-your-vps-via-ssh)
2. [Secure the VPS](#2-secure-the-vps)
3. [Install Docker](#3-install-docker)
4. [Clone KoNote](#4-clone-konote)
5. [Generate Credentials](#5-generate-credentials)
6. [Create the .env File](#6-create-the-env-file)
7. [Point Your Domain to the VPS](#7-point-your-domain-to-the-vps)
8. [Deploy KoNote](#8-deploy-konote)
9. [Verify the Deployment](#9-verify-the-deployment)
10. [Create Your First Admin User](#10-create-your-first-admin-user)
11. [Set Up Backups](#11-set-up-backups)
12. [Set Up Monitoring](#12-set-up-monitoring)
13. [Set Up Email (External Relay)](#13-set-up-email-external-relay)
14. [Run a Second Instance (Dev/Demo)](#14-run-a-second-instance-devdemo)
15. [Updating KoNote](#15-updating-konote)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. Connect to Your VPS via SSH

When OVHcloud set up your VPS, they emailed you a **root password** and the **VPS IP address**. You will use these to connect.

### From Windows (PowerShell or Windows Terminal)

Open **PowerShell** or **Windows Terminal** and type:

```bash
ssh root@YOUR_VPS_IP
```

Replace `YOUR_VPS_IP` with the IP address from your OVHcloud email (e.g., `51.195.123.45`).

The first time you connect, you will see a message like:

```
The authenticity of host '51.195.123.45' can't be established.
ED25519 key fingerprint is SHA256:abc123...
Are you sure you want to continue connecting (yes/no)?
```

Type **yes** and press Enter. Then enter your root password when prompted.

> **Tip:** The password will not show as you type — this is normal. Just type it and press Enter.

If you see a `root@vps-xxxxx:~#` prompt, you are connected.

### Set Up SSH Key (Optional but Recommended)

Using an SSH key means you will not need to type your password every time. On your **local Windows machine** (not the VPS):

```powershell
# Generate a key (press Enter for all defaults)
ssh-keygen -t ed25519

# Copy the key to your VPS
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@YOUR_VPS_IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

After this, `ssh root@YOUR_VPS_IP` will connect without a password.

---

## 2. Secure the VPS

Run these commands on the VPS (you should be logged in via SSH as root):

### Update the system

```bash
apt update && apt upgrade -y
```

### Set up the firewall

```bash
# Allow SSH, HTTP, and HTTPS only
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status
```

You should see:

```
Status: active
To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

### Enable automatic security updates

```bash
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

Select **Yes** when prompted.

---

## 3. Install Docker

```bash
# Install Docker using the official convenience script
curl -fsSL https://get.docker.com | sh

# Verify Docker is running
docker --version
docker compose version
```

You should see version numbers for both. Docker Compose is included with modern Docker.

---

## 4. Clone KoNote

```bash
# Create the deployment directory
mkdir -p /opt/konote
cd /opt/konote

# Clone the repository
git clone https://github.com/LogicalOutcomes/konote.git .
```

> **Note:** The `.` at the end means "clone into the current directory" (not a subdirectory).

If the repository is private, you will need a GitHub Personal Access Token:

```bash
git clone https://YOUR_GITHUB_TOKEN@github.com/LogicalOutcomes/konote.git .
```

---

## 5. Generate Credentials

You need to generate three secret values. Run these commands on the VPS:

```bash
# Install Python temporarily (for key generation only)
apt install -y python3 python3-pip
pip3 install cryptography --break-system-packages

# Generate Django secret key
echo "SECRET_KEY:"
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

# Generate encryption key for participant data
echo "FIELD_ENCRYPTION_KEY:"
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate database passwords
echo "POSTGRES_PASSWORD:"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

echo "AUDIT_POSTGRES_PASSWORD:"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Write these down** — you will need them in the next step. The `FIELD_ENCRYPTION_KEY` is especially critical:

> **WARNING:** If you lose the `FIELD_ENCRYPTION_KEY`, all encrypted participant data (names, emails, birth dates) is **permanently unrecoverable**. Save a copy in your password manager and store a printed backup in a secure location.

---

## 6. Create the .env File

Create the environment file with your production values:

```bash
nano /opt/konote/.env
```

Paste the following, replacing the placeholder values with your actual credentials from Step 5:

```ini
# ==============================================================================
# REQUIRED
# ==============================================================================

SECRET_KEY=PASTE_YOUR_SECRET_KEY_HERE
FIELD_ENCRYPTION_KEY=PASTE_YOUR_ENCRYPTION_KEY_HERE

# Main database
POSTGRES_USER=konote
POSTGRES_PASSWORD=PASTE_YOUR_POSTGRES_PASSWORD_HERE
POSTGRES_DB=konote

# Audit database
AUDIT_POSTGRES_USER=audit_writer
AUDIT_POSTGRES_PASSWORD=PASTE_YOUR_AUDIT_PASSWORD_HERE
AUDIT_POSTGRES_DB=konote_audit

# ==============================================================================
# DOMAIN AND SECURITY
# ==============================================================================

# Your domain name — Caddy uses this for automatic HTTPS
DOMAIN=konote.example.ca

# Allowed hosts — must match your domain
ALLOWED_HOSTS=konote.example.ca

# CSRF protection — must include https://
CSRF_TRUSTED_ORIGINS=https://konote.example.ca

# Authentication mode
AUTH_MODE=local

# Production mode — blocks startup if security checks fail
KONOTE_MODE=production

# ==============================================================================
# EMAIL (OPTIONAL — see Step 13)
# ==============================================================================

# Uncomment and configure after setting up Resend (Step 13)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.resend.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=resend
# EMAIL_HOST_PASSWORD=re_your_resend_api_key
# DEFAULT_FROM_EMAIL=KoNote <noreply@yourdomain.ca>

# ==============================================================================
# AI FEATURES (OPTIONAL)
# ==============================================================================

# Uncomment to enable AI Goal Builder (requires OpenRouter account)
# OPENROUTER_API_KEY=sk-or-...
```

Save the file: press **Ctrl+O**, then **Enter**, then **Ctrl+X** to exit nano.

**Important:** Replace `konote.example.ca` with your actual domain (e.g., `konote.llewelyn.ca`).

---

## 7. Point Your Domain to the VPS

You need to create a DNS record that points your domain to the VPS IP address.

### If your domain is managed by Cloudflare, Namecheap, GoDaddy, etc.

1. Log in to your domain registrar or DNS provider
2. Go to **DNS settings** for your domain
3. Add a new record:
   - **Type:** A
   - **Name:** `konote` (or whatever subdomain you want, e.g., `konote` for `konote.yourdomain.ca`)
   - **Value:** Your VPS IP address (e.g., `51.195.123.45`)
   - **TTL:** 300 (5 minutes) or Auto
4. If using Cloudflare: set the **proxy status to DNS only** (grey cloud, not orange). Caddy handles HTTPS directly — Cloudflare's proxy would interfere with Let's Encrypt certificate issuance.

### Verify DNS is working

Wait a few minutes, then test from your local machine:

```bash
nslookup konote.yourdomain.ca
```

You should see your VPS IP address in the response.

> **Note:** DNS changes can take up to 48 hours to propagate, but usually work within 5–15 minutes.

---

## 8. Deploy KoNote

Make sure you are in the KoNote directory on your VPS:

```bash
cd /opt/konote
```

Build and start all containers:

```bash
docker compose up -d --build
```

This will:
1. Build the KoNote Docker image (2–5 minutes the first time)
2. Pull PostgreSQL and Caddy images
3. Start all containers
4. Run database migrations automatically
5. Obtain a Let's Encrypt HTTPS certificate for your domain

Watch the startup progress:

```bash
docker compose logs -f web
```

You should see:
```
Running migrations...
Migrations complete.
Running audit migrations...
Audit migrations complete.
Seeding data...
Running security checks...
Starting gunicorn on port 8000
```

Press **Ctrl+C** to stop watching logs (the containers keep running).

---

## 9. Verify the Deployment

### Check all containers are running

```bash
docker compose ps
```

You should see 5 containers, all with status "Up" or "Up (healthy)":

```
NAME          SERVICE     STATUS
konote-web-1       web         Up (healthy)
konote-db-1        db          Up (healthy)
konote-audit_db-1  audit_db    Up (healthy)
konote-caddy-1     caddy       Up
konote-autoheal-1  autoheal    Up
```

### Check HTTPS is working

Open your browser and go to:

```
https://konote.yourdomain.ca
```

You should see the KoNote login page with a valid HTTPS certificate (padlock icon in the address bar).

### If something is wrong

Check the logs:

```bash
# All container logs
docker compose logs

# Just the web app
docker compose logs web

# Just Caddy (HTTPS issues)
docker compose logs caddy
```

See [Troubleshooting](#16-troubleshooting) for common issues.

---

## 10. Create Your First Admin User

```bash
docker compose exec web python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password. This creates a System Admin account that can configure the agency.

After logging in, go to **Admin → Settings** to:
- Set your organisation name
- Configure terminology (what you call participants, programs, etc.)
- Enable or disable features

---

## 11. Set Up Backups

KoNote includes a backup script that dumps both databases nightly.

### Make the scripts executable

```bash
chmod +x /opt/konote/scripts/backup-vps.sh
chmod +x /opt/konote/scripts/disk-check.sh
```

### Create the backup directory

```bash
mkdir -p /opt/konote/backups
```

### Test the backup manually

```bash
/opt/konote/scripts/backup-vps.sh
```

You should see output showing both databases being backed up.

### Set up automated backups via cron

```bash
crontab -e
```

If asked to choose an editor, select **nano** (option 1).

Add these lines at the bottom:

```cron
# KoNote: Nightly database backup at 2 AM
0 2 * * * /opt/konote/scripts/backup-vps.sh >> /var/log/konote-backup.log 2>&1

# KoNote: Hourly disk usage check
0 * * * * /opt/konote/scripts/disk-check.sh >> /var/log/konote-disk.log 2>&1

# KoNote: Weekly Docker cleanup (remove old images)
0 4 * * 0 docker system prune -f >> /var/log/docker-prune.log 2>&1
```

Save and exit (**Ctrl+O**, **Enter**, **Ctrl+X**).

### Verify cron is set up

```bash
crontab -l
```

You should see your three cron entries.

---

## 12. Set Up Monitoring

[UptimeRobot](https://uptimerobot.com/) is a free service that checks your site every 5 minutes and emails you if it goes down.

1. Create a free account at [uptimerobot.com](https://uptimerobot.com/)
2. Click **Add New Monitor**
3. Configure:
   - **Monitor Type:** HTTPS
   - **Friendly Name:** KoNote Production
   - **URL:** `https://konote.yourdomain.ca/auth/login/`
   - **Monitoring Interval:** 5 minutes
4. Set up **Alert Contacts** (your email)
5. Save

UptimeRobot will now check your site every 5 minutes and email you within minutes if it goes down.

---

## 13. Set Up Email (External Relay)

OVHcloud LocalZone VPS instances block outgoing email ports (25, 587, 465). To send email (password resets, export notifications, erasure approvals), you need an external email relay service.

### Option A: Resend (Recommended — Free Tier)

[Resend](https://resend.com/) offers 100 emails/day free, which is plenty for a small nonprofit.

1. Create an account at [resend.com](https://resend.com/)
2. Add and verify your domain (Resend will give you DNS records to add)
3. Create an API key
4. Update your `.env` file on the VPS:

```bash
nano /opt/konote/.env
```

Uncomment and fill in the email section:

```ini
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=re_YOUR_RESEND_API_KEY
DEFAULT_FROM_EMAIL=KoNote <noreply@yourdomain.ca>
```

5. Restart KoNote to pick up the changes:

```bash
cd /opt/konote
docker compose up -d
```

### Option B: Brevo (Alternative — Free Tier)

[Brevo](https://www.brevo.com/) (formerly Sendinblue) offers 300 emails/day free.

```ini
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-brevo-email@example.com
EMAIL_HOST_PASSWORD=your-brevo-smtp-key
DEFAULT_FROM_EMAIL=KoNote <noreply@yourdomain.ca>
```

### Test email is working

```bash
docker compose exec web python manage.py shell -c "
from django.core.mail import send_mail
send_mail('KoNote Test', 'Email is working!', None, ['your-email@example.com'])
print('Sent!')
"
```

Check your inbox for the test email.

---

## 14. Run a Second Instance (Dev/Demo)

You can run a demo instance alongside production on the same VPS — useful for testing, training, and showing KoNote to prospective agencies.

### Create a separate directory

```bash
mkdir -p /opt/konote-dev
cd /opt/konote-dev

# Clone the same repo
git clone https://github.com/LogicalOutcomes/konote.git .
```

### Create a dev .env file

```bash
nano /opt/konote-dev/.env
```

```ini
# Dev instance — demo mode with sample data
SECRET_KEY=GENERATE_A_DIFFERENT_SECRET_KEY
FIELD_ENCRYPTION_KEY=GENERATE_A_DIFFERENT_ENCRYPTION_KEY

POSTGRES_USER=konote_dev
POSTGRES_PASSWORD=GENERATE_A_DIFFERENT_PASSWORD
POSTGRES_DB=konote_dev

AUDIT_POSTGRES_USER=audit_dev
AUDIT_POSTGRES_PASSWORD=GENERATE_A_DIFFERENT_PASSWORD
AUDIT_POSTGRES_DB=konote_dev_audit

DOMAIN=konote-dev.yourdomain.ca
ALLOWED_HOSTS=konote-dev.yourdomain.ca
CSRF_TRUSTED_ORIGINS=https://konote-dev.yourdomain.ca

AUTH_MODE=local
KONOTE_MODE=demo
DEMO_MODE=true
```

### Create a dev docker-compose override

The dev instance needs different container names, ports, and volume names so it does not conflict with production. Create a file called `docker-compose.override.yml`:

```bash
nano /opt/konote-dev/docker-compose.override.yml
```

```yaml
services:
  web:
    container_name: konote-dev-web
    ports:
      - "127.0.0.1:8001:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/auth/login/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

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
    container_name: konote-dev-caddy
    ports:
      - "8080:80"
      - "8443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - dev_caddy_data:/data
      - dev_caddy_config:/config

  autoheal:
    container_name: konote-dev-autoheal

volumes:
  dev_pgdata:
  dev_audit_pgdata:
  dev_caddy_data:
  dev_caddy_config:
```

### Important: Caddy port conflict

Both prod and dev cannot share ports 80 and 443. The simplest approach is to use a **shared Caddy instance** on the production stack that reverse-proxies both domains. Alternatively, use the override above which puts the dev Caddy on ports 8080/8443.

**Recommended approach — shared Caddy:**

1. Update the **production** Caddyfile (`/opt/konote/Caddyfile`) to serve both domains:

```
konote.yourdomain.ca {
    reverse_proxy web:8000

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()"
        -Server
    }

    encode gzip
}

konote-dev.yourdomain.ca {
    reverse_proxy 127.0.0.1:8001

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()"
        -Server
    }

    encode gzip
}
```

2. In the dev `docker-compose.override.yml`, **remove the caddy service entirely** (the prod Caddy handles both):

```yaml
services:
  web:
    container_name: konote-dev-web
    ports:
      - "127.0.0.1:8001:8000"

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
```

3. Add the DNS A record for `konote-dev.yourdomain.ca` pointing to the same VPS IP.

4. Start the dev instance:

```bash
cd /opt/konote-dev
docker compose up -d --build
```

5. Reload production Caddy to pick up the new domain:

```bash
cd /opt/konote
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

The dev instance will be available at `https://konote-dev.yourdomain.ca` with demo data and quick-login buttons.

---

## 15. Updating KoNote

When a new version is released:

```bash
cd /opt/konote

# Pull the latest code
git pull origin main

# Rebuild and restart (migrations run automatically on startup)
docker compose up -d --build
```

The entrypoint script handles database migrations automatically. Downtime is typically under 2 minutes.

### Update the dev instance too

```bash
cd /opt/konote-dev
git pull origin main
docker compose up -d --build
```

---

## 16. Troubleshooting

### "Cannot connect" or timeout when accessing the site

1. **Check containers are running:** `docker compose ps`
2. **Check firewall:** `ufw status` — ports 80 and 443 must be open
3. **Check DNS:** `nslookup konote.yourdomain.ca` from your local machine — must show VPS IP
4. **Check Caddy logs:** `docker compose logs caddy` — look for certificate errors

### "502 Bad Gateway" from Caddy

The web container is not ready yet or has crashed:

```bash
docker compose logs web
```

Look for error messages. Common causes:
- Missing environment variable (check `.env`)
- Database not ready (wait 30 seconds and try again)
- Security check failed (check `KONOTE_MODE` setting)

### "CSRF verification failed"

The `CSRF_TRUSTED_ORIGINS` in `.env` does not match your domain. It must include `https://`:

```ini
# Correct
CSRF_TRUSTED_ORIGINS=https://konote.yourdomain.ca

# Wrong
CSRF_TRUSTED_ORIGINS=konote.yourdomain.ca
```

After fixing, restart: `docker compose up -d`

### Caddy cannot get HTTPS certificate

- DNS must point to the VPS **before** starting Caddy
- Port 80 must be open (Let's Encrypt uses HTTP-01 challenge)
- If using Cloudflare: set proxy to **DNS only** (grey cloud)
- Check Caddy logs: `docker compose logs caddy`

### Container keeps restarting

Check what is failing:

```bash
docker compose logs --tail 50 web
```

If you see "security check failed", the app is in production mode and a required setting is missing. Either fix the setting or temporarily set `KONOTE_MODE=demo` in `.env` to start with warnings instead of hard failures.

### Disk running low

```bash
# Check disk usage
df -h /

# Remove old Docker images
docker system prune -f

# Check backup sizes
du -sh /opt/konote/backups/
```

### Restore from backup

If you need to restore a database from backup:

```bash
# Stop the web container (keep databases running)
docker compose stop web

# Restore main database
gunzip -c /opt/konote/backups/main_2026-03-01_0200.sql.gz | \
  docker compose exec -T db psql -U konote konote

# Restore audit database
gunzip -c /opt/konote/backups/audit_2026-03-01_0200.sql.gz | \
  docker compose exec -T audit_db psql -U audit_writer konote_audit

# Restart the web container
docker compose start web
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start KoNote | `cd /opt/konote && docker compose up -d` |
| Stop KoNote | `cd /opt/konote && docker compose down` |
| View logs | `cd /opt/konote && docker compose logs -f web` |
| Restart after .env change | `cd /opt/konote && docker compose up -d` |
| Rebuild after code update | `cd /opt/konote && git pull && docker compose up -d --build` |
| Create admin user | `docker compose exec web python manage.py createsuperuser` |
| Run backup now | `/opt/konote/scripts/backup-vps.sh` |
| Check container health | `docker compose ps` |
| Check disk space | `df -h /` |
| View backup files | `ls -lh /opt/konote/backups/` |
| SSH to VPS | `ssh root@YOUR_VPS_IP` |
