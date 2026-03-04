# Deploying KoNote

This guide covers everything you need to get KoNote running — from local development to production. Choose your path:

| I want to... | Go to... |
|--------------|----------|
| Deploy to production | [Deploy to OVHcloud VPS](deploy-ovhcloud.md) (recommended) |
| Try KoNote locally | [Local Development (Docker)](#local-development-docker) |
| Understand hosting options | [Choosing a Hosting Platform](#choosing-a-hosting-platform) |
| Update or roll back a deployment | [Update and Rollback Guide](update-and-rollback.md) |
| Set up PDF reports | [PDF Report Setup](#pdf-report-setup) |
| Enable surveys | [Surveys Setup](#surveys-setup) |
| Enable the participant portal | [Participant Portal Setup](#participant-portal-setup) |
| Go live with real data | [Before You Enter Real Data](#before-you-enter-real-data) |

---

## Choosing a Hosting Platform

KoNote is designed to run on an **OVHcloud VPS** — a single virtual server running Docker Compose with built-in automated backups, health monitoring, and self-healing. This is the recommended deployment for all Canadian nonprofits.

### Recommended: OVHcloud VPS

| | |
|---|---|
| **Cost** | ~$22 CAD/month (single agency) |
| **Data residency** | Beauharnois, QC (Canadian soil, French company — not subject to US CLOUD Act) |
| **Setup** | Automated script or step-by-step guide |
| **Maintenance** | Built-in ops sidecar handles backups, disk monitoring, health reports, and Docker cleanup |
| **Key management** | OVHcloud KMS or Azure Key Vault for encryption key storage |

KoNote's Docker Compose stack includes 6 containers: web app, two PostgreSQL databases, Caddy (automatic HTTPS), autoheal (container recovery), and an ops sidecar (automated backups, disk checks, health emails). Everything runs on one VPS with no external dependencies.

**AI-assisted maintenance:** KoNote is designed to be maintained with AI tools like Claude Code. You don't need a sysadmin — your AI assistant can SSH into the VPS, check logs, restart containers, apply updates, and troubleshoot issues.

See the **[full OVHcloud deployment guide](deploy-ovhcloud.md)** for step-by-step instructions and an automated deploy script.

### Alternative: Azure

If your organisation's IT policy mandates Azure (common for government-funded nonprofits or those already using Microsoft 365 / Azure AD), KoNote can run on Azure Container Apps with Azure PostgreSQL.

**Be aware of the trade-offs:**
- **Higher cost** — ~$75–115 CAD/month vs ~$22/month on OVHcloud
- **No ops sidecar** — You lose the built-in backup automation, health reports, and self-healing. You'll need to configure Azure's equivalent services separately.
- **US CLOUD Act exposure** — Microsoft is a US company. Data in Azure Canada Central is still subject to US government data requests under the CLOUD Act.
- **More complex setup** — Azure Container Apps, PostgreSQL Flexible Server, Container Registry, firewall rules, and environment variables all require manual configuration.

**If you choose Azure, you'll need technical help.** The setup requires familiarity with Azure CLI, container registries, and PostgreSQL administration. Microsoft offers [$2,000 USD/year in Azure credits](https://nonprofit.microsoft.com) to eligible nonprofits through TechSoup — check if your organisation qualifies.

Azure auto-detection still works in KoNote's settings (via `WEBSITE_SITE_NAME` or `CONTAINER_APP_NAME` environment variables), and Azure AD SSO is fully supported.

### Any Docker-Capable VPS

KoNote's Docker Compose stack is portable. While OVHcloud is the tested and documented path, **any Linux VPS with Docker** will work — DigitalOcean, Linode, Hetzner, or a server in your own office. The key requirement is Docker Compose support and a public IP for Caddy's automatic HTTPS.

### Data Residency Considerations

If your organisation serves clients in Canada, you may have obligations under:

- **PIPEDA** (federal privacy law) — Generally allows data to be stored outside Canada, but you must protect it adequately
- **Provincial health privacy laws** (PHIPA in Ontario, HIA in Alberta, etc.) — May require health information to stay in Canada
- **Funder requirements** — Some government contracts specify Canadian hosting

**If in doubt:** Choose OVHcloud (Beauharnois, QC) for Canadian data residency without US CLOUD Act exposure.

---

## Is This Guide For Me?

**Yes.** This guide is written for nonprofit staff who aren't developers.

If you've ever:
- Installed WordPress or another web application
- Used Excel competently (formulas, sorting, multiple sheets)
- Followed step-by-step software instructions

...you have the skills to set up KoNote. Every step shows you exactly what to type and what to expect.

---

## Understanding Your Responsibility

KoNote stores sensitive client information. By running your own instance, you're taking on responsibility for protecting that data.

### What KoNote Does Automatically

When configured correctly, KoNote:

- **Encrypts client names, emails, birth dates, and phone numbers** — Even if someone accessed your database directly, they'd see scrambled text
- **Blocks common security mistakes** — The server won't start if critical security settings are missing
- **Logs who accesses what** — Every client view or change is recorded in a separate audit database
- **Restricts access by role** — Staff only see clients in their assigned programs

### What You Need to Do

| Your Responsibility | Why It Matters |
|---------------------|----------------|
| **Keep the encryption key safe** | If you lose it, all client data becomes unreadable — permanently |
| **Use HTTPS in production** | Without it, data travels unprotected over the internet |
| **Remove departed staff promptly** | Former employees shouldn't access client data |
| **Back up your data regularly** | Hardware fails; mistakes happen |

### When to Get Help

Consider engaging IT support if:
- Your organisation serves **vulnerable populations** (children, mental health clients, survivors of violence)
- You're subject to **specific regulatory requirements** (healthcare privacy laws, government contracts)
- You're **not comfortable** with the responsibility after reading this section

---

## Automatic Platform Detection

KoNote automatically detects its deployment environment and configures itself appropriately:

| Platform | How It's Detected | What's Auto-Configured |
|----------|-------------------|------------------------|
| **Docker Compose / OVHcloud VPS** | `DATABASE_URL` is set | Production settings, localhost allowed by default |
| **Azure App Service** | `WEBSITE_SITE_NAME` variable | Production settings, `.azurewebsites.net` domains allowed |
| **Azure Container Apps** | `CONTAINER_APP_NAME` variable | Production settings, `.azurecontainerapps.io` domains allowed |

This means you only need to set the **essential** variables — KoNote handles the rest.

### Essential Variables (All Platforms)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `AUDIT_DATABASE_URL` | PostgreSQL connection for audit logs |
| `SECRET_KEY` | Random string for session signing |
| `FIELD_ENCRYPTION_KEY` | Fernet key for PII encryption |

If something is missing, the startup check will tell you exactly what's wrong and give platform-specific hints on how to fix it.

For a complete list of all configuration options (exports, email, demo mode, AI features), see the comments in `.env.example`.

### Email Configuration

Email is needed for export notifications and the erasure approval workflow. Configure SMTP variables in `.env` — see `.env.example` for variable names and defaults. If not configured, exports and erasure still work but admin notifications fail silently.

### Messaging Configuration (Optional)

KoNote can send SMS and email reminders to clients. This is **optional** — the system works fully without it (staff can still log communications manually).

#### SMS (Twilio)

To enable SMS reminders, create a [Twilio](https://www.twilio.com/) account and add these variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `TWILIO_ACCOUNT_SID` | Your Twilio account SID | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Your Twilio auth token | (keep secret) |
| `TWILIO_FROM_NUMBER` | Your Twilio phone number | `+16135551234` |

**Cost:** Twilio charges ~$0.0079 USD per SMS in Canada. For 100 reminders/month, expect ~$1 CAD/month plus the $1.50 USD/month phone number fee.

#### Email (SMTP)

To enable email reminders, configure SMTP. Works with any provider (Google Workspace, Microsoft 365, Resend.com, Amazon SES).

| Variable | Description | Example |
|----------|-------------|---------|
| `EMAIL_HOST` | SMTP server | `smtp.resend.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP username | `resend` |
| `EMAIL_HOST_PASSWORD` | SMTP password or API key | (keep secret) |
| `DEFAULT_FROM_EMAIL` | Sender address | `noreply@youragency.ca` |

**Recommended providers for Canadian nonprofits:**
- **Resend.com** — Simple API, generous free tier (100 emails/day), no domain verification hassle
- **Google Workspace** — If you already use Gmail (use app-specific password)
- **Microsoft 365** — If you already use Outlook (use app password or OAuth)

See `.env.example` for the full list of messaging variables and defaults.

#### Demo Email Testing

Set `DEMO_EMAIL_BASE` in your environment to route all demo user emails to tagged addresses (e.g., `DEMO_EMAIL_BASE=you@gmail.com` sends demo emails to `you+demo-admin@gmail.com`). Useful for testing email delivery without real client addresses.

---

## Prerequisites

### All Platforms

| Software | What It Does | Where to Get It |
|----------|--------------|-----------------|
| **Git** | Downloads the KoNote code | [git-scm.com](https://git-scm.com/download/win) |
| **Python 3.12+** | Runs the application | [python.org](https://www.python.org/downloads/) |

### For Local Development

| Software | What It Does | Where to Get It |
|----------|--------------|-----------------|
| **Docker Desktop** | Runs databases automatically | [docker.com](https://www.docker.com/products/docker-desktop/) |

---

## Generating Security Keys

You'll need two unique keys for any deployment. Generate them on your computer:

```bash
# Generate SECRET_KEY (Django sessions)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate FIELD_ENCRYPTION_KEY (PII encryption)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Save both keys securely.** The `FIELD_ENCRYPTION_KEY` is especially critical — if you lose it, all encrypted client data is unrecoverable.

---

## Local Development (Docker)

Docker handles PostgreSQL, the web server, and all dependencies automatically. This is the recommended path for trying KoNote.

**Time estimate:** 30–45 minutes

### Step 1: Clone the Repository

```bash
git clone https://github.com/gilliankerr/KoNote.git
cd KoNote
```

### Step 2: Create Environment File

```bash
copy .env.example .env
```

### Step 3: Configure Environment Variables

Edit `.env` and add your generated keys:

```ini
SECRET_KEY=your-generated-secret-key-here
FIELD_ENCRYPTION_KEY=your-generated-encryption-key-here

POSTGRES_USER=konote
POSTGRES_PASSWORD=MySecurePassword123
POSTGRES_DB=konote

AUDIT_POSTGRES_USER=audit_writer
AUDIT_POSTGRES_PASSWORD=AnotherPassword456
AUDIT_POSTGRES_DB=konote_audit
```

### Step 4: Start the Containers

```bash
docker-compose up -d
```

Wait about 30 seconds for health checks to pass.

### Step 5: Run Migrations

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py migrate --database=audit
```

### Step 6: Create Your First Admin User

Every new KoNote instance needs an initial admin account. Since there are no users yet, you create one from the command line:

```bash
docker-compose exec web python manage.py createsuperuser
```

You'll be prompted for:
- **Username** — your login name (e.g., `admin` or your name)
- **Password** — minimum 8 characters (you'll be asked to confirm it)

This creates a user with full admin access. Once logged in, you can create additional users through the web interface using **invite links** (recommended) or direct user creation. See [Users & Roles](admin/users-and-roles.md) for details.

> **Demo mode shortcut:** If you set `DEMO_MODE=true` in your `.env`, the `seed` command (Step 7.5) automatically creates a `demo-admin` user with password `demo1234` — so you can skip this step and log in with that instead.

### Step 7: Access KoNote

Open **http://localhost:8000** and log in.

### Step 7.5: Load Seed Data

```bash
docker-compose exec web python manage.py seed
```

Creates the metrics library, default templates, event types, feature toggles, and intake fields. If `DEMO_MODE=true`, also creates 5 demo users (one per role) and 10 demo clients with sample data.

Idempotent — safe to run multiple times (uses `get_or_create`). Runs automatically via `entrypoint.sh` in Docker, but must be run manually for local development without Docker.

### Docker Commands Reference

| Command | Purpose |
|---------|---------|
| `docker-compose up -d` | Start all containers |
| `docker-compose down` | Stop all containers |
| `docker-compose logs web` | View application logs |
| `docker-compose down -v` | Stop and delete all data |

---

---

## PDF Report Setup

KoNote can generate PDF reports using WeasyPrint. This is optional — the app works fully without it.

### Quick Check

```bash
python manage.py shell -c "from apps.reports.pdf_utils import is_pdf_available; print('PDF available:', is_pdf_available())"
```

### Installation by Platform

**Linux (Ubuntu/Debian):**
```bash
sudo apt install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

**macOS:**
```bash
brew install pango gdk-pixbuf libffi
```

**Windows:** Requires GTK3 runtime. Install [MSYS2](https://www.msys2.org/), then:
```bash
pacman -S mingw-w64-x86_64-pango mingw-w64-x86_64-gdk-pixbuf2
```
Add `C:\msys64\mingw64\bin` to your PATH.

**Docker:** The Dockerfile should include:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0
```

### Working Without PDF

If you skip PDF setup:
- All features except PDF export work normally
- Users can still view reports in-browser
- CSV export is available
- Browser "Print to PDF" works as an alternative

---

## Surveys Setup

KoNote includes a built-in survey engine for collecting structured feedback from participants. Surveys are **disabled by default** — you need to turn on the feature toggle before anyone can create or respond to surveys.

### Feature Toggle

Enable surveys from the admin UI:

1. Go to **Admin → Settings → Features**
2. Turn on **Surveys**
3. Click **Save**

Once enabled, "Surveys" appears in the Admin/Manage dropdown and a "Surveys" tab appears on each participant's file.

No environment variables are required for surveys. The feature is entirely controlled by the `surveys` feature toggle in the database (`admin_settings_featuretoggles` table).

### Database Tables

Running `python manage.py migrate` creates these tables in the main database:

| Table | Purpose |
|-------|---------|
| `surveys` | Survey definitions (name, status, options) |
| `survey_sections` | Sections within a survey (grouping, scoring, conditions) |
| `survey_questions` | Individual questions with type, options, and ordering |
| `survey_trigger_rules` | Automatic assignment rules (event, enrolment, time, characteristic) |
| `survey_assignments` | Tracks which surveys are assigned to which participants |
| `survey_responses` | Completed survey submissions |
| `survey_answers` | Individual answers — text values are **Fernet-encrypted** at rest |
| `survey_links` | Shareable link tokens for public survey access |
| `survey_partial_answers` | In-progress answers for auto-save (encrypted) |

### Shareable Links (Public Survey Access)

Surveys can be completed through shareable links — public URLs that require no login. When you create a shareable link for a survey, KoNote generates a unique token-based URL.

**No additional setup is required** for shareable links beyond enabling the surveys feature. The public form is served at `/survey/<token>/` on the same domain as your KoNote instance.

If you use a custom domain, make sure both `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` include that domain — otherwise form submissions from shareable links will fail with a CSRF error.

### Trigger Rules

Trigger rules can automatically assign surveys when certain events occur (e.g., a participant is enrolled in a program, or a specific number of days have passed). Trigger rules are configured per-survey from the admin interface — no environment variables or code changes are needed.

### What to Know

- **Encryption:** Free-text answers (`SurveyAnswer.value` and `PartialAnswer.value`) are Fernet-encrypted at rest. Numeric values used for scoring are stored as plain integers for aggregation.
- **Survey data stays in the main database** — not the audit database. Audit log entries are created for survey-related actions (create, submit, assign) via the standard audit middleware.
- **Closing a survey** automatically deactivates all its trigger rules and prevents new responses, but preserves existing data.

---

## Participant Portal Setup

The participant portal is a separate, participant-facing interface where participants can view their goals, progress, journal entries, and surveys. It is **disabled by default**.

### Feature Toggle

Enable the portal from the admin UI:

1. Go to **Admin → Settings → Features**
2. Turn on **Participant Portal**
3. Click **Save**

Turning on the portal also makes sub-features available: **Journal**, **Messaging**, and **Resources** each have their own toggles that depend on the portal being enabled.

### Environment Variables

The portal works on a single domain without extra configuration. For production deployments where you want the portal on a separate subdomain (e.g., `my.outcomes.myagency.ca`), set these optional variables:

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `EMAIL_HASH_KEY` | **Yes** (production) | HMAC secret for hashing participant email addresses during login lookup. Must be a stable string — changing it invalidates all existing portal accounts. In demo mode, a placeholder is used automatically. |
| `PORTAL_DOMAIN` | No | Portal subdomain (e.g., `my.outcomes.myagency.ca`). When set, portal paths (`/my/`) are only accessible on this domain. |
| `STAFF_DOMAIN` | No | Staff subdomain (e.g., `outcomes.myagency.ca`). When set, staff paths are blocked on the portal domain and vice versa. |

**Single-domain setup (most deployments):** Leave `PORTAL_DOMAIN` and `STAFF_DOMAIN` blank. The portal runs at `/my/` on your main domain alongside the staff interface. No domain enforcement is applied.

**Split-domain setup (optional):** Set both `PORTAL_DOMAIN` and `STAFF_DOMAIN`. KoNote's `DomainEnforcementMiddleware` ensures portal paths are only reachable on the portal domain and staff paths are only reachable on the staff domain. Both domains must be in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

### Database Tables

Running `python manage.py migrate` creates these tables in the main database:

| Table | Purpose |
|-------|---------|
| `portal_participant_users` | Participant login accounts (encrypted email, HMAC hash, MFA, lockout) |
| `portal_invites` | Single-use invite tokens for participant onboarding |
| `portal_journal_entries` | Private journal entries written by participants (encrypted) |
| `portal_messages` | Messages from participants to staff (encrypted) |
| `portal_staff_notes` | Notes from staff visible in a participant's portal (encrypted) |
| `portal_correction_requests` | Participant requests to correct their recorded data (PHIPA/PIPEDA) |
| `portal_staff_assisted_login_tokens` | One-time tokens for in-person portal login |
| `portal_resource_links` | Program-level resource links (bilingual) |
| `portal_client_resource_links` | Per-participant resource links added by staff |

### Portal Invitations

Staff invite participants to the portal from the participant's detail page:

1. Open the participant's file
2. Click **Portal → Create Invite**
3. Optionally set a verbal verification code
4. Share the generated link with the participant

The invite link is valid for **7 days** and can only be used once. The participant creates their own email, display name, and password, then goes through a consent flow before reaching their dashboard.

### Multi-Factor Authentication

Participant portal accounts use **TOTP-based MFA** by default. Participants set up MFA during their first login. If a participant loses access to their authenticator app, staff can reset their MFA from the portal management page.

Account lockout activates after **5 failed login attempts** with a **15-minute lockout period**.

### What to Know

- **Encryption:** Portal models encrypt PII at rest — email addresses, journal entries, messages, staff notes, correction request descriptions, and TOTP secrets are all Fernet-encrypted. Email addresses are additionally HMAC-hashed for constant-time lookup.
- **Separate session:** The portal uses its own session key (`_portal_participant_id`). Participant sessions are completely separate from staff sessions — a participant cannot access the staff interface and vice versa.
- **Emergency logout:** The portal includes a panic/safety button that immediately destroys the session via `navigator.sendBeacon()`. This is designed for participants in unsafe situations (e.g., domestic violence).
- **Data isolation:** Every portal view scopes queries to the logged-in participant's client file. There is no way for one participant to see another's data.

---

## Before You Enter Real Data

Complete this checklist before entering any real client information.

### 1. Encryption Key Backup

- [ ] I have copied my `FIELD_ENCRYPTION_KEY` to a secure location (password manager, encrypted file)
- [ ] The backup is stored **separately** from my database backups
- [ ] I can retrieve the key without logging into KoNote

**Test yourself:** Close this document. Can you retrieve your encryption key from your backup? If not, fix that now.

### 2. Database Backups Configured

- [ ] I know how backups happen (manual, scheduled, or hosting provider automatic)
- [ ] I have tested restoring from a backup at least once
- [ ] Backups are stored in a different location than the database

### 2.5. Email Configured (Production)

- [ ] SMTP settings configured (see `.env.example` for variables)
- [ ] Test email works: `python manage.py sendtestemail admin@example.com`

### 2.6. Messaging Configured (Optional)

- [ ] If using SMS: Twilio credentials set (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`)
- [ ] If using email reminders: SMTP configured and tested
- [ ] Messaging profile set in Admin → Instance Settings (default: "Record keeping" — no messages sent)
- [ ] Safety-First mode is ON until you've verified messaging works correctly

### 3. User Accounts Set Up

- [ ] First admin user created via `python manage.py createsuperuser`
- [ ] Additional staff invited using **Admin → Users → Invite** (creates invite links they can use to set up their own accounts)
- [ ] All staff assigned to correct programs with correct roles
- [ ] Test users and demo accounts removed or disabled

### 3.5. Seed Data Loaded

- [ ] `python manage.py seed` has been run (automatic in Docker, manual for local dev)

### 4. Security Settings Verified

Run the deployment check:

```bash
# Docker:
docker-compose exec web python manage.py check --deploy

# Direct:
python manage.py check --deploy
```

You should see no errors about `FIELD_ENCRYPTION_KEY`, `SECRET_KEY`, or `CSRF`.

### 4.5. Audit Database Locked Down

- [ ] `python manage.py lockdown_audit_db` has been run
- [ ] Audit DB user has INSERT-only permissions (prevents tampering with audit records)

### 5. Final Sign-Off

- [ ] I have verified my encryption key is backed up and retrievable
- [ ] I understand that losing my encryption key means losing client PII
- [ ] My team has been trained on data entry procedures
- [ ] I know who to contact if something goes wrong

## Management Commands Reference

| Command | When | Purpose | Dry Run? |
|---------|------|---------|----------|
| `seed` | Automatic (startup) | Create metrics, features, settings, event types, templates, intake fields; demo data if `DEMO_MODE` | No |
| `startup_check` | Automatic (startup) | Validate encryption key, SECRET_KEY, middleware; block startup in production if critical checks fail | No |
| `cleanup_expired_exports` | Manual/cron (daily) | Remove expired export links and orphan files from disk | Yes (`--dry-run`) |
| `rotate_encryption_key` | Manual (as needed) | Re-encrypt all PII with a new Fernet key | Yes (`--dry-run`) |
| `check_translations` | Manual/CI | Validate .po/.mo files for duplicates, coverage, staleness | No (`--strict` for CI) |
| `security_audit` | Manual/CI | Audit encryption, RBAC, audit logging, configuration | Yes (`--json`, `--fail-on-warn`) |
| `lockdown_audit_db` | Manual (post-setup) | Restrict audit DB user to INSERT/SELECT only | No |
| `check_document_url` | Manual (after config) | Test document folder URL generation with a sample record ID | No (`--check-reachable`) |
| `diagnose_charts` | Manual (troubleshooting) | Diagnose why charts might be empty for a client | No |

---

### Translation Workflow

Pre-compiled `.mo` files are committed to the repository — no gettext system dependency needed in production. To update translations: edit `.po` → run `python manage.py compilemessages` locally → commit both `.po` and `.mo`.

---

## Troubleshooting

### "FIELD_ENCRYPTION_KEY not configured"

Generate and add a key to your `.env`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Database connection refused

1. Check PostgreSQL is running
2. Verify credentials in `DATABASE_URL` match your database setup
3. For Docker: ensure containers are up (`docker-compose ps`)

### Port 8000 already in use

Run on a different port:
```bash
python manage.py runserver 8080
```

### Container keeps restarting

Check logs for the error:
```bash
docker-compose logs web
```

Usually caused by missing environment variables.

---

## Glossary

| Term | What It Means |
|------|---------------|
| **Terminal** | A text-based window where you type commands |
| **Repository** | A folder containing all the code, stored on GitHub |
| **Clone** | Download a copy of code from GitHub to your computer |
| **Migration** | A script that creates database tables |
| **Container** | A self-contained package that runs the application |
| **Environment variables** | Settings stored in a `.env` file |
| **Encryption key** | A password used to scramble sensitive data |

---

## Next Steps

Once your deployment is running:

1. **[Admin Guide](admin/index.md)** — Configure your agency's settings
2. **[Using KoNote](using-KoNote.md)** — Train your staff
