# Deploying KoNote on OVHcloud VPS

## Two Paths: Automated or Manual

| Path | Time | Best for |
|------|------|----------|
| **Automated** (`scripts/deploy-konote-vps.sh`) | ~30 minutes | Production deployments, operators comfortable with SSH |
| **Manual** (this guide) | 45–90 minutes | Learning, troubleshooting, or when the script can't run |

### Automated Path (Recommended)

The deploy script automates 9 of 15 steps below — from securing the OS through verifying the running instance. You need SSH access and a domain pointing to your VPS IP.

```bash
./scripts/deploy-konote-vps.sh \
  --host YOUR_VPS_IP \
  --domain konote.youragency.ca \
  --admin-email admin@youragency.ca \
  --org-name "Your Agency Name"
```

The script generates all credentials, SSHes into the VPS, hardens the OS, installs Docker, clones the repo, writes `.env`, starts the containers, creates the admin user, and sets up backup cron jobs. It prints credentials and a post-deploy checklist at the end.

- **Safe to re-run** — skips already-completed steps
- **Dry-run mode** — add `--dry-run` to preview without executing
- **Full options** — run `./scripts/deploy-konote-vps.sh --help`
- **Design doc** — see [deploy script design](plans/2026-02-20-deploy-script-design.md) for architecture decisions

After the script finishes, skip to [Section 7: Point Your Domain to the VPS](#7-point-your-domain-to-the-vps) (if DNS isn't already configured) or [Section 12: Set Up External Monitoring](#12-set-up-external-monitoring) to complete the remaining manual steps. Backups and internal monitoring are handled automatically by the ops sidecar.

### Manual Path

Follow the full guide below step by step. This is useful for understanding what the script does, or for environments where the script can't run (e.g., non-Ubuntu servers, restricted SSH access).

---

This guide walks you through deploying KoNote on an OVHcloud VPS from scratch. It assumes:

- You have an OVHcloud VPS with Ubuntu 24.04 or 25.04 (fresh install)
- You have a domain name you can point to the VPS
- You are working from a Windows computer
- You have Claude Code available to help if you get stuck

**Time estimate:** 45–90 minutes for a first deployment (manual path).

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
11. [Backups and Monitoring (Automatic)](#11-backups-and-monitoring-automatic)
12. [Set Up External Monitoring](#12-set-up-external-monitoring)
13. [Set Up Email (External Relay)](#13-set-up-email-external-relay)
14. [Run a Second Instance (Dev/Demo)](#14-run-a-second-instance-devdemo)
15. [Updating KoNote](#15-updating-konote)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. Connect to Your VPS via SSH

When OVHcloud set up your VPS, they emailed you a **password** and the **VPS IP address**. The default username is `ubuntu` (not `root`).

### From Windows (PowerShell or Windows Terminal)

Open **PowerShell** or **Windows Terminal** and type:

```bash
ssh ubuntu@YOUR_VPS_IP
```

Replace `YOUR_VPS_IP` with the IP address from your OVHcloud email.

The first time you connect, you will see a message like:

```
The authenticity of host 'YOUR_VPS_IP' can't be established.
ED25519 key fingerprint is SHA256:abc123...
Are you sure you want to continue connecting (yes/no)?
```

Type **yes** and press Enter. Then enter your password when prompted.

> **Tip:** The password will not show as you type -- this is normal. Just type it and press Enter.

### First login: Mandatory password change

OVHcloud forces a password change on first login. You will see:

```
WARNING: Your password has expired.
You must change your password now and login again!
Current password:
New password:
Retype new password:
```

Enter the OVHcloud-provided password as the current password, then choose a new password. **OVHcloud will disconnect you after the password change** -- this is normal. Reconnect with:

```bash
ssh ubuntu@YOUR_VPS_IP
```

Use your new password this time.

### Set Up SSH Key (Recommended)

Using an SSH key means you will not need to type your password every time.

> **Important:** Complete the password change above **before** setting up the SSH key. The piped command below will fail if the password is still expired.

> **Note:** `ssh-copy-id` is not available on Windows. Use the manual method below.

**Step 1 — Generate a key** (on your local Windows machine, not the VPS):

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\ovh_konote
```

**Step 2 — Copy the public key to the VPS:**

```powershell
type $env:USERPROFILE\.ssh\ovh_konote.pub | ssh ubuntu@YOUR_VPS_IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
```

Enter your **new** password (the one you set in the previous step) when prompted.

**Step 3 — Test key-based login:**

```powershell
ssh -i $env:USERPROFILE\.ssh\ovh_konote ubuntu@YOUR_VPS_IP
```

This should connect **without asking for a password**.

> **Tip:** Add this to your SSH config (`~/.ssh/config`) for convenience:
> ```
> Host konote-vps
>     HostName YOUR_VPS_IP
>     User ubuntu
>     IdentityFile ~/.ssh/ovh_konote
> ```
> Then just type `ssh konote-vps` to connect.

---

## 2. Secure the VPS

Run these commands on the VPS (you should be logged in via SSH):

### Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

### Set up the firewall

```bash
# Allow SSH, HTTP, and HTTPS only
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
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
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Select **Yes** when prompted.

---

## 3. Install Docker

```bash
# Install Docker using the official convenience script
curl -fsSL https://get.docker.com | sudo sh

# Verify Docker is running
docker --version
sudo docker compose version
```

You should see version numbers for both. Docker Compose is included with modern Docker.

> **Note:** On OVHcloud VPS, docker commands require `sudo`. All docker commands in this guide use `sudo`.

---

## 4. Clone KoNote

```bash
# Create the deployment directory
sudo mkdir -p /opt/konote
cd /opt/konote

# Clone the repository
sudo git clone https://github.com/LogicalOutcomes/konote.git .
```

> **Note:** The `.` at the end means "clone into the current directory" (not a subdirectory).

If the repository is private, you will need a GitHub Personal Access Token:

```bash
sudo git clone https://YOUR_GITHUB_TOKEN@github.com/LogicalOutcomes/konote.git .
```

---

## 5. Generate Credentials

You need to generate four secret values. Run these commands on the VPS:

```bash
# Install Python cryptography library (for key generation)
sudo apt install -y python3 python3-pip
pip3 install cryptography --break-system-packages  # this flag is required on Ubuntu 24.04+ — it's a Python safety check, not breaking anything

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

**Save all four values in your password manager immediately.** The `FIELD_ENCRYPTION_KEY` is especially critical:

> **WARNING:** If you lose the `FIELD_ENCRYPTION_KEY`, all encrypted participant data (names, emails, birth dates) is **permanently unrecoverable**. Save a copy in your password manager and store a printed backup in a secure location.

---

## 6. Create the .env File

Create the environment file with your production values:

```bash
sudo nano /opt/konote/.env
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

# Your domain name -- Caddy uses this for automatic HTTPS
DOMAIN=konote.example.ca

# Allowed hosts -- must include your domain AND localhost (for healthcheck)
ALLOWED_HOSTS=konote.example.ca,localhost

# CSRF protection -- must include https://
CSRF_TRUSTED_ORIGINS=https://konote.example.ca

# Authentication mode
AUTH_MODE=local

# Production mode -- blocks startup if security checks fail
KONOTE_MODE=production

# Demo mode -- creates demo users with quick-login buttons for staff training.
# Demo users are completely separate from real participants (is_demo=True).
# Recommended: keep this enabled so staff can train without creating fake
# participants in the real database (which would need legal tracking).
DEMO_MODE=true

# ==============================================================================
# EMAIL (OPTIONAL -- see Step 13)
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

> **Note:** `ALLOWED_HOSTS` must include `localhost` -- the Docker healthcheck pings `http://localhost:8000/auth/login/` from inside the container. Without it, the healthcheck fails and the container will be marked as unhealthy.

---

## 7. Point Your Domain to the VPS

You need to create a DNS **A record** that points your domain to the VPS IP address.

### If your domain is managed by Cloudflare, Namecheap, GoDaddy, etc.

1. Log in to your domain registrar or DNS provider
2. Go to **DNS settings** for your domain
3. **Delete any existing CNAME records** for the same subdomain (e.g., if `konote` has a CNAME pointing to a previous hosting platform, delete it first). CNAME records take priority over A records and will block the new one.
4. Add a new record:
   - **Type:** A
   - **Name:** `konote` (or whatever subdomain you want, e.g., `konote` for `konote.yourdomain.ca`)
   - **Value:** Your VPS IP address (e.g., `YOUR_VPS_IP`)
   - **TTL:** 300 (5 minutes) or Auto
5. If using Cloudflare: set the **proxy status to DNS only** (grey cloud, not orange). Caddy handles HTTPS directly -- Cloudflare's proxy would interfere with Let's Encrypt certificate issuance.

> **Important:** If you previously hosted on another platform (Heroku, etc.), you likely have old CNAME records. These **must be deleted** before adding A records. DNS rules give CNAME priority -- if both exist, the CNAME wins and your A record will be ignored.

### Verify DNS is working

Wait a few minutes, then test from your local machine:

```bash
nslookup konote.yourdomain.ca
```

You should see your VPS IP address in the response.

> **Note:** DNS changes can take up to 48 hours to propagate globally, but usually work within 5-15 minutes for most users. Let's Encrypt uses multiple validation servers worldwide -- if some still see stale DNS, the certificate request will fail on the first attempt but Caddy retries automatically every 60 seconds until all validators see the correct IP.

---

## 8. Deploy KoNote

Make sure you are in the KoNote directory on your VPS:

```bash
cd /opt/konote
```

Build and start all containers:

```bash
sudo docker compose up -d --build
```

This will:
1. Build the KoNote Docker image (2-5 minutes the first time)
2. Pull PostgreSQL and Caddy images
3. Start all containers
4. Run database migrations automatically
5. Obtain a Let's Encrypt HTTPS certificate for your domain

Watch the startup progress:

```bash
sudo docker compose logs -f web
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
sudo docker compose ps
```

You should see 6 containers, all with status "Up" or "Up (healthy)":

```
NAME                 SERVICE     STATUS
konote-web-1         web         Up (healthy)
konote-db-1          db          Up (healthy)
konote-audit_db-1    audit_db    Up (healthy)
konote-caddy-1       caddy       Up
konote-autoheal-1    autoheal    Up (healthy)
konote-ops-1         ops         Up (healthy)
```

> **Note:** The web container takes about 60 seconds to become healthy (it needs to run migrations and start up). If it shows "health: starting", wait a minute and check again.

### Check HTTPS is working

Open your browser and go to:

```
https://konote.yourdomain.ca
```

You should see the KoNote login page with a valid HTTPS certificate (padlock icon in the address bar).

### If HTTPS is not ready yet

Caddy obtains the certificate automatically via Let's Encrypt. If DNS has not fully propagated to all of Let's Encrypt's worldwide validation servers, the first few certificate requests may fail. Check Caddy logs:

```bash
sudo docker compose logs caddy
```

If you see "challenge failed" errors mentioning "secondary validation", this is normal during DNS propagation. Caddy retries every 60 seconds. Once all validators see your IP, the certificate will be obtained automatically -- no action needed from you.

### If something is wrong

Check the logs:

```bash
# All container logs
sudo docker compose logs

# Just the web app
sudo docker compose logs web

# Just Caddy (HTTPS issues)
sudo docker compose logs caddy
```

See [Troubleshooting](#16-troubleshooting) for common issues.

---

## 10. Create Your First Admin User

```bash
cd /opt/konote
sudo docker compose exec web python manage.py createsuperuser
```

Follow the prompts to set a username and password. This creates a System Admin account that can configure the agency.

> **Note:** The `createsuperuser` command asks for username, display name, and password. There is no email field -- KoNote uses a custom User model.

After logging in, go to **Admin > Settings** to:
- Set your organisation name
- Configure terminology (what you call participants, programs, etc.)
- Enable or disable features

---

## 11. Backups and Monitoring (Automatic)

Backups, disk monitoring, health reports, and maintenance all run automatically inside the **ops sidecar container**. No cron jobs to set up.

### What runs automatically

| Task | Schedule | What it does |
|------|----------|--------------|
| Database backup | 2 AM daily | Dumps both databases, compresses, manages retention |
| Disk check | Hourly | Alerts if disk usage exceeds 80% |
| Health report | 7 AM daily | Emails operational status (no participant data) |
| Docker cleanup | 4 AM Sundays | Removes unused images and containers |
| Backup verification | 5 AM Sundays | Test-restores latest backup and verifies integrity |

All of this started when you ran `docker compose up -d` in Step 8. No additional setup needed.

### Create the backup directory

If you used the deploy script, this is already done. If deploying manually:

```bash
sudo mkdir -p /opt/konote/backups
```

### Test the backup manually

```bash
cd /opt/konote
sudo docker compose exec ops /usr/local/bin/ops-backup.sh
```

You should see output showing both databases being backed up with file sizes.

### View backup files

```bash
ls -lh /opt/konote/backups/
```

### Configure optional monitoring

Add these to your `.env` file for enhanced monitoring:

```ini
# Dead man's switch — get alerted if backups STOP running.
# Create a free push monitor at uptimerobot.com or healthchecks.io,
# then paste the URL here.
HEALTHCHECK_PING_URL=https://hc-ping.com/your-uuid-here

# Alert webhook — get notified on backup failure or disk warnings.
# Works with ntfy.sh (free), Slack, or UptimeRobot push monitors.
ALERT_WEBHOOK_URL=https://ntfy.sh/your-topic

# Daily health email — operational status emailed every morning.
# Requires email to be configured (see Step 13).
OPS_HEALTH_REPORT_TO=admin@youragency.ca
```

After updating `.env`, restart to apply:

```bash
cd /opt/konote
sudo docker compose up -d
```

### Verify the ops sidecar is running

```bash
sudo docker compose logs --tail 20 ops
```

You should see the crontab schedule and "Ops sidecar ready. Starting crond."

### Disaster recovery: restoring from a backup

If your VPS fails and you need to restore to a new server:

1. **Deploy a fresh KoNote instance** on a new VPS using the deploy script or this manual guide. This creates empty databases and a running application.

2. **Copy your backup files** from your old VPS (or wherever you saved them) to the new server:

   ```bash
   scp main_2026-03-01_0200.dump ubuntu@NEW-VPS-IP:/opt/konote/backups/
   scp audit_2026-03-01_0200.dump ubuntu@NEW-VPS-IP:/opt/konote/backups/
   ```

3. **Ensure the `.env` file uses the same `FIELD_ENCRYPTION_KEY`** as the original instance. If the key doesn't match, encrypted participant data (names, emails, birth dates) will be unreadable. This is the key you saved in your password manager during initial deployment.

4. **Stop the web app** to prevent writes during restore:

   ```bash
   cd /opt/konote
   sudo docker compose stop web
   ```

5. **Restore the databases** using the ops container (which has database tools and credentials pre-configured):

   ```bash
   # Restore main database (replace filename with your backup)
   sudo docker compose exec -T ops bash -c \
     'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -h db -U "$POSTGRES_USER" \
       -d "${POSTGRES_DB:-konote}" --clean --if-exists --no-owner \
       /backups/main_2026-03-01_0200.dump'

   # Restore audit database
   sudo docker compose exec -T ops bash -c \
     'PGPASSWORD="$AUDIT_POSTGRES_PASSWORD" pg_restore -h audit_db -U "$AUDIT_POSTGRES_USER" \
       -d "${AUDIT_POSTGRES_DB:-konote_audit}" --clean --if-exists --no-owner \
       /backups/audit_2026-03-01_0200.dump'
   ```

6. **Restart the web app:**

   ```bash
   sudo docker compose start web
   ```

7. **Verify** by logging in at `https://yourdomain.ca` and checking that participant data is visible.

> **Important:** The `FIELD_ENCRYPTION_KEY` in your `.env` must match the key used when the data was originally encrypted. Without the correct key, encrypted fields (names, emails, birth dates) are permanently unrecoverable. This is why the deploy script warns you to save this key in your password manager.

> **Note:** The `--clean --if-exists` flags tell pg_restore to drop existing tables before recreating them from the backup. This is safe for a fresh deployment. The `--no-owner` flag prevents permission errors when the restoring database user differs from the original.

---

## 12. Set Up External Monitoring

The ops sidecar provides **internal monitoring** (database health, disk, backups). You should also set up **external monitoring** that checks your site from outside the VPS.

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

> **Note:** The ops sidecar monitors the system from inside (backups, disk, database health). UptimeRobot monitors from outside (is the website reachable?). You should set up both — they catch different failure modes.

---

## 13. Set Up Email (External Relay)

OVHcloud LocalZone VPS instances block outgoing email ports (25, 587, 465). To send email (password resets, export notifications, erasure approvals), you need an external email relay service.

### Option A: Resend (Recommended -- Free Tier)

[Resend](https://resend.com/) offers 100 emails/day free, which is plenty for a small nonprofit.

1. Create an account at [resend.com](https://resend.com/)
2. Add and verify your domain (Resend will give you DNS records to add)
3. Create an API key
4. Update your `.env` file on the VPS:

```bash
sudo nano /opt/konote/.env
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
sudo docker compose up -d
```

> **Important:** After changing `.env`, you must run `docker compose up -d` (not `docker compose restart`). The `restart` command does not re-read the `.env` file -- only `up -d` does.

### Option B: Brevo (Alternative -- Free Tier)

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
sudo docker compose exec web python manage.py shell -c "
from django.core.mail import send_mail
send_mail('KoNote Test', 'Email is working!', None, ['your-email@example.com'])
print('Sent!')
"
```

Check your inbox for the test email.

---

## 14. Run a Second Instance (Dev/Demo)

You can run a demo instance alongside production on the same VPS -- useful for testing, training, and showing KoNote to prospective agencies. The two instances share a single Caddy reverse proxy but have completely separate databases and encryption keys.

### Architecture

```
Internet
  |
  +-- konote.yourdomain.ca -----> Caddy -----> konote-web-1:8000 (production)
  |                                 |
  +-- konote-dev.yourdomain.ca ---> +--------> konote-dev-web:8000 (demo)
```

Both web containers connect to a shared Docker network (`konote-proxy`) so the production Caddy can reach the dev instance. Each instance has its own databases, encryption keys, and volumes.

### Step 1: Add the dev DNS record

Add an A record for `konote-dev.yourdomain.ca` pointing to the same VPS IP. Follow the same process as [Step 7](#7-point-your-domain-to-the-vps).

### Step 2: Create the shared Docker network

```bash
sudo docker network create konote-proxy
```

### Step 3: Create the production override

The production instance needs a `docker-compose.override.yml` that connects its web and caddy containers to the shared network:

```bash
sudo nano /opt/konote/docker-compose.override.yml
```

```yaml
# Production override — connects Caddy and web to the shared proxy network
# so Caddy can reach both prod and dev web containers by container name.
# This file is automatically merged with docker-compose.yml when you run
# "docker compose up". You don't need to reference it explicitly.
services:
  web:
    networks:
      - frontend
      - backend
      - konote-proxy    # adds the shared network so Caddy can route to this container

  caddy:
    networks:
      - frontend
      - konote-proxy    # adds the shared network so Caddy can also reach the dev container

networks:
  konote-proxy:
    external: true      # "external" means this network already exists (created in Step 2)
```

Apply the override:

```bash
cd /opt/konote
sudo docker compose up -d
```

### Step 4: Update the production Caddyfile

Replace the Caddyfile with one that serves both domains. Use **explicit container names** (not service names) to avoid DNS conflicts between the two instances:

```bash
sudo nano /opt/konote/Caddyfile
```

```
konote.yourdomain.ca {
    reverse_proxy konote-web-1:8000

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()"
        -Server
    }

    encode gzip
}

konote-dev.yourdomain.ca {
    reverse_proxy konote-dev-web:8000

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()"
        -Server
    }

    encode gzip
}
```

> **Important:** Use `konote-web-1` (the container name), not `web` (the service name). Both instances define a `web` service, so Docker's DNS would resolve `web` ambiguously. Container names are unique.

### Step 5: Clone and configure the dev instance

```bash
# Clone to a separate directory
sudo git clone https://github.com/LogicalOutcomes/konote.git /opt/konote-dev
cd /opt/konote-dev
```

Generate new credentials (different from production):

```bash
echo "DEV_SECRET_KEY:"
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

echo "DEV_FIELD_ENCRYPTION_KEY:"
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

echo "DEV_POSTGRES_PASSWORD:"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

echo "DEV_AUDIT_POSTGRES_PASSWORD:"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Create the dev `.env`:

```bash
sudo nano /opt/konote-dev/.env
```

```ini
# KoNote Dev/Demo Instance
SECRET_KEY=PASTE_DEV_SECRET_KEY
FIELD_ENCRYPTION_KEY=PASTE_DEV_ENCRYPTION_KEY

# Main database
POSTGRES_USER=konote_dev
POSTGRES_PASSWORD=PASTE_DEV_POSTGRES_PASSWORD
POSTGRES_DB=konote_dev

# Audit database
AUDIT_POSTGRES_USER=audit_dev
AUDIT_POSTGRES_PASSWORD=PASTE_DEV_AUDIT_PASSWORD
AUDIT_POSTGRES_DB=konote_dev_audit

# Domain
DOMAIN=konote-dev.yourdomain.ca
ALLOWED_HOSTS=konote-dev.yourdomain.ca,localhost
CSRF_TRUSTED_ORIGINS=https://konote-dev.yourdomain.ca

# Auth and mode
AUTH_MODE=local
KONOTE_MODE=demo
DEMO_MODE=true

# Email (console backend -- demo doesn't need real email)
DEFAULT_FROM_EMAIL=KoNote Dev <noreply@konote.app>
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_PORT=587
EMAIL_USE_TLS=True
```

### Step 6: Create the dev docker-compose override

```bash
sudo nano /opt/konote-dev/docker-compose.override.yml
```

```yaml
# Dev instance override — gives each container a unique name, disables its own
# Caddy (production Caddy handles both domains), and uses separate database
# volumes so dev data is completely isolated from production.
services:
  web:
    container_name: konote-dev-web       # unique name so Caddy can address it directly
    ports: !reset []                     # removes the host port mapping from the base file
                                         # (Caddy reaches this container via Docker network instead)
    networks:
      - frontend
      - backend
      - konote-proxy                     # shared network so production Caddy can reach this container

  db:
    container_name: konote-dev-db
    volumes:
      - dev_pgdata:/var/lib/postgresql/data   # separate volume — dev data stays isolated from prod

  audit_db:
    container_name: konote-dev-audit-db
    volumes:
      - dev_audit_pgdata:/var/lib/postgresql/data
      - ./scripts/audit_db_init.sql:/docker-entrypoint-initdb.d/01-init.sql

  caddy:
    profiles:
      - disabled                         # disables this container — production Caddy handles both domains

  autoheal:
    container_name: konote-dev-autoheal

volumes:
  dev_pgdata:                            # separate named volumes prevent data mixing
  dev_audit_pgdata:

networks:
  konote-proxy:
    external: true                       # connects to the shared network created in Step 2
```

Key details:
- `ports: !reset []` removes the host port mapping (Caddy reaches it via Docker network)
- `caddy: profiles: [disabled]` disables the dev's own Caddy (production Caddy handles both domains)
- Separate volume names (`dev_pgdata`, `dev_audit_pgdata`) keep data isolated from production
- Unique container names prevent conflicts

### Step 7: Start the dev instance

```bash
cd /opt/konote-dev
sudo docker compose up -d --build
```

### Step 8: Reload production Caddy

```bash
cd /opt/konote
sudo docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### Step 9: Verify

```bash
# Check all containers
sudo docker compose -f /opt/konote/docker-compose.yml ps
sudo docker compose -f /opt/konote-dev/docker-compose.yml ps
```

You should see 9 containers total (5 prod + 4 dev).

Open `https://konote-dev.yourdomain.ca` in your browser. You should see the login page with **demo quick-login buttons** that let you switch between different roles without passwords.

> **Note:** Caddy provisions the dev certificate separately. If DNS is still propagating for the dev subdomain, the certificate may take a few minutes to appear. Caddy retries automatically.

---

## 15. Updating KoNote

When a new version is released:

### Before You Update

1. **Back up both databases** — in case the update introduces problems:

```bash
sudo /opt/konote/scripts/backup-vps.sh
```

2. **Note the current commit** — so you can roll back if needed:

```bash
cd /opt/konote
sudo git log --oneline -1
# Example output: a1b2c3d Fix dashboard layout
```

Save that commit hash (e.g., `a1b2c3d`). You'll need it if you want to undo the update.

### Apply the Update

**Recommended: Use the deploy script** (updates, rebuilds, and health-checks in one command):

```bash
# Production only
/opt/konote/deploy.sh

# Dev only
/opt/konote/deploy.sh --dev

# Both production and dev
/opt/konote/deploy.sh --all
```

The deploy script (`scripts/deploy.sh`) pulls `develop`, rebuilds the web container, restarts, and waits for the health check. For the dev instance, it also **auto-resets the database** if migrations fail — this is safe because the dev instance only has demo data (`DEMO_MODE=true`).

**Manual alternative** (if the deploy script is not installed yet):

```bash
cd /opt/konote

# Pull the latest code
sudo git pull origin main

# Rebuild and restart (migrations run automatically on startup)
sudo docker compose up -d --build
```

The entrypoint script handles database migrations automatically. Downtime is typically under 2 minutes.

### Verify the Update

1. Visit your KoNote URL — the login page should load
2. Log in and check a few pages (dashboard, a client page, a report)
3. Check container health: `sudo docker compose ps` — all should show "healthy"

### If Something Goes Wrong (Rollback)

If the update breaks your instance:

```bash
cd /opt/konote

# Revert to the previous commit
sudo git checkout a1b2c3d -- .
# (Replace a1b2c3d with the hash you saved before updating)

# Rebuild with the old code
sudo docker compose up -d --build
```

If the broken update ran database migrations (new tables or columns), you may also need to restore from the backup you took. See [Troubleshooting: Restore from backup](#restore-from-backup) below.

For detailed procedures, see the [Update and Rollback Guide](update-and-rollback.md).

### Dev Instance: Automatic Database Reset on Migration Failure

The dev instance uses `DEMO_MODE=true` and only contains demo data. When the deploy script detects a migration failure on the dev instance (e.g., because the dev database was created from an older branch), it automatically:

1. Stops the web container
2. Drops and recreates both databases (main + audit)
3. Restarts the web container (which auto-migrates and re-seeds demo data)

This means the dev instance **always comes back to a working state** after a deploy, even if the database schema is completely out of sync. Production never auto-resets — it fails loudly so you can investigate.

If you need to manually reset the dev database:

```bash
cd /opt/konote-dev
docker compose stop web
docker compose exec -T db psql -U konote_dev -d postgres \
    -c "DROP DATABASE IF EXISTS konote_dev;" \
    -c "CREATE DATABASE konote_dev OWNER konote_dev;"
docker compose exec -T audit_db psql -U audit_dev -d postgres \
    -c "DROP DATABASE IF EXISTS konote_dev_audit;" \
    -c "CREATE DATABASE konote_dev_audit OWNER audit_dev;"
docker compose up -d web
# Wait ~60s for migrations + seed to complete, then check health
docker compose ps
```

---

## 16. Troubleshooting

### "Cannot connect" or timeout when accessing the site

1. **Check containers are running:** `sudo docker compose ps`
2. **Check firewall:** `sudo ufw status` -- ports 80 and 443 must be open
3. **Check DNS:** `nslookup konote.yourdomain.ca` from your local machine -- must show VPS IP
4. **Check Caddy logs:** `sudo docker compose logs caddy` -- look for certificate errors

### "400 Bad Request" or "DisallowedHost"

Django is rejecting the request because the domain is not in `ALLOWED_HOSTS`. Common causes:

- The domain in `.env` doesn't match the URL you're visiting
- `localhost` is missing from `ALLOWED_HOSTS` (needed for Docker healthcheck)
- You're running two instances and the wrong one is receiving traffic (check Caddyfile uses explicit container names)

Fix: edit `.env`, update `ALLOWED_HOSTS`, then run `sudo docker compose up -d`.

### "502 Bad Gateway" from Caddy

The web container is not ready yet or has crashed:

```bash
sudo docker compose logs web
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

After fixing, restart: `sudo docker compose up -d`

### .env changes not taking effect

After editing `.env`, you must run:

```bash
sudo docker compose up -d
```

Do **not** use `docker compose restart` -- it does not re-read the `.env` file. Only `docker compose up -d` recreates containers with the new environment variables.

### Caddy cannot get HTTPS certificate

- DNS must point to the VPS **before** starting Caddy
- Port 80 must be open (Let's Encrypt uses HTTP-01 challenge)
- Old CNAME records must be deleted (they take priority over A records)
- If using Cloudflare: set proxy to **DNS only** (grey cloud)
- Check Caddy logs: `sudo docker compose logs caddy`

If you see "challenge failed" with "secondary validation" errors, this means some of Let's Encrypt's worldwide validators still see old DNS. Caddy retries every 60 seconds -- no action needed. This resolves within minutes to hours as DNS propagates.

### Container keeps restarting

Check what is failing:

```bash
sudo docker compose logs --tail 50 web
```

If you see "security check failed", the app is in production mode and a required setting is missing. Either fix the setting or temporarily set `KONOTE_MODE=demo` in `.env` to start with warnings instead of hard failures.

### Disk running low

```bash
# Check disk usage
df -h /

# Remove old Docker images
sudo docker system prune -f

# Check backup sizes
du -sh /opt/konote/backups/
```

### Restore from backup

If you need to restore a database from backup:

```bash
# Stop the web container (keep databases running)
sudo docker compose stop web

# Restore main database
gunzip -c /opt/konote/backups/main_2026-03-01_0200.sql.gz | \
  sudo docker compose exec -T db psql -U konote konote

# Restore audit database
gunzip -c /opt/konote/backups/audit_2026-03-01_0200.sql.gz | \
  sudo docker compose exec -T audit_db psql -U audit_writer konote_audit

# Restart the web container
sudo docker compose start web
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start KoNote | `cd /opt/konote && sudo docker compose up -d` |
| Stop KoNote | `cd /opt/konote && sudo docker compose down` |
| View logs | `cd /opt/konote && sudo docker compose logs -f web` |
| Restart after .env change | `cd /opt/konote && sudo docker compose up -d` |
| Rebuild after code update | `cd /opt/konote && sudo git pull && sudo docker compose up -d --build` |
| Create admin user | `sudo docker compose exec web python manage.py createsuperuser` |
| Run backup now | `sudo docker compose exec ops /usr/local/bin/ops-backup.sh` |
| Ops logs | `sudo docker compose logs --tail 50 ops` |
| Check container health | `sudo docker compose ps` |
| Check disk space | `df -h /` |
| View backup files | `ls -lh /opt/konote/backups/` |
| SSH to VPS | `ssh -i ~/.ssh/ovh_konote ubuntu@YOUR_VPS_IP` |
