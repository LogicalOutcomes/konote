# Deploying KoNote on OVHcloud VPS

This guide walks you through deploying KoNote on an OVHcloud VPS from scratch. It assumes:

- You have an OVHcloud VPS with Ubuntu 24.04 or 25.04 (fresh install)
- You have a domain name you can point to the VPS
- You are working from a Windows computer
- You have Claude Code available to help if you get stuck

**Time estimate:** 45-90 minutes for a first deployment.

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

When OVHcloud set up your VPS, they emailed you a **password** and the **VPS IP address**. The default username is `ubuntu` (not `root`).

### From Windows (PowerShell or Windows Terminal)

Open **PowerShell** or **Windows Terminal** and type:

```bash
ssh ubuntu@YOUR_VPS_IP
```

Replace `YOUR_VPS_IP` with the IP address from your OVHcloud email (e.g., `141.227.151.7`).

The first time you connect, you will see a message like:

```
The authenticity of host '141.227.151.7' can't be established.
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

Using an SSH key means you will not need to type your password every time. On your **local Windows machine** (not the VPS):

```powershell
# Generate a key with a descriptive name
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\ovh_konote

# Copy the public key to the VPS
type $env:USERPROFILE\.ssh\ovh_konote.pub | ssh ubuntu@YOUR_VPS_IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

After this, connect without a password:

```bash
ssh -i ~/.ssh/ovh_konote ubuntu@YOUR_VPS_IP
```

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
3. **Delete any existing CNAME records** for the same subdomain (e.g., if `konote` has a CNAME pointing to Railway or another host, delete it first). CNAME records take priority over A records and will block the new one.
4. Add a new record:
   - **Type:** A
   - **Name:** `konote` (or whatever subdomain you want, e.g., `konote` for `konote.yourdomain.ca`)
   - **Value:** Your VPS IP address (e.g., `141.227.151.7`)
   - **TTL:** 300 (5 minutes) or Auto
5. If using Cloudflare: set the **proxy status to DNS only** (grey cloud, not orange). Caddy handles HTTPS directly -- Cloudflare's proxy would interfere with Let's Encrypt certificate issuance.

> **Important:** If you previously hosted on Railway, Heroku, or another platform, you likely have old CNAME records. These **must be deleted** before adding A records. DNS rules give CNAME priority -- if both exist, the CNAME wins and your A record will be ignored.

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

You should see 5 containers, all with status "Up" or "Up (healthy)":

```
NAME                 SERVICE     STATUS
konote-web-1         web         Up (healthy)
konote-db-1          db          Up (healthy)
konote-audit_db-1    audit_db    Up (healthy)
konote-caddy-1       caddy       Up
konote-autoheal-1    autoheal    Up (healthy)
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

## 11. Set Up Backups

KoNote includes a backup script that dumps both databases nightly.

### Make the scripts executable

```bash
sudo chmod +x /opt/konote/scripts/backup-vps.sh
sudo chmod +x /opt/konote/scripts/disk-check.sh
```

### Create the backup directory

```bash
sudo mkdir -p /opt/konote/backups
```

### Test the backup manually

```bash
sudo /opt/konote/scripts/backup-vps.sh
```

You should see output showing both databases being backed up with file sizes.

> **Note:** The backup script runs `docker compose` commands which require `sudo`.

### Set up automated backups via cron

```bash
sudo crontab -e
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
sudo crontab -l
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
# Production override -- connects Caddy and web to the shared proxy network
# so Caddy can reach both prod and dev web containers by container name
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

```bash
cd /opt/konote

# Pull the latest code
sudo git pull origin main

# Rebuild and restart (migrations run automatically on startup)
sudo docker compose up -d --build
```

The entrypoint script handles database migrations automatically. Downtime is typically under 2 minutes.

### Update the dev instance too

```bash
cd /opt/konote-dev
sudo git pull origin main
sudo docker compose up -d --build
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
| Run backup now | `sudo /opt/konote/scripts/backup-vps.sh` |
| Check container health | `sudo docker compose ps` |
| Check disk space | `df -h /` |
| View backup files | `ls -lh /opt/konote/backups/` |
| SSH to VPS | `ssh -i ~/.ssh/ovh_konote ubuntu@YOUR_VPS_IP` |
