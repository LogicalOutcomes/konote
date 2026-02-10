# Deploying KoNote

This guide covers everything you need to get KoNote running — from local development to cloud production. Choose your path:

| I want to... | Go to... |
|--------------|----------|
| Choose a hosting platform | [Choosing a Hosting Platform](#choosing-a-hosting-platform) |
| Check if my nonprofit qualifies for free Azure | [Checking Nonprofit Eligibility](#checking-nonprofit-eligibility-for-azure-credits) |
| Try KoNote locally | [Local Development (Docker)](#local-development-docker) |
| Deploy to Railway | [Deploy to Railway](#deploy-to-railway) |
| Deploy to Azure | [Deploy to Azure](#deploy-to-azure) |
| Deploy to Elestio | [Deploy to Elestio](#deploy-to-elestio) |
| Deploy to FullHost | [Deploy to FullHost](#deploy-to-fullhost) |
| Set up PDF reports | [PDF Report Setup](#pdf-report-setup) |
| Go live with real data | [Before You Enter Real Data](#before-you-enter-real-data) |

---

## Choosing a Hosting Platform

Not sure which platform is right for your organisation? This section compares your options based on cost, ease of setup, data residency, and scaling.

### Quick Comparison

| Platform | Monthly Cost (CAD) | Setup Difficulty | Canadian Data | Security Certifications |
|----------|-------------------|------------------|---------------|------------------------|
| **Railway** | $35–55 | Easy | No (US servers) | SOC 2 Type II, HIPAA |
| **Azure** | $75–115 | Hard | Yes (Canada Central) | SOC 2, ISO 27001, HIPAA, 90+ |
| **Elestio** | $50–80 | Medium | No (EU/US servers) | SOC 2 Type 1, ISO 27001 |
| **FullHost** | $23–45 | Easy | Yes (Montreal) | None documented |

### Cost Breakdown (200 Clients, 5–10 Staff)

These estimates assume light usage — a small nonprofit with staff working mostly 9–5 weekdays.

#### Railway (~$35–55/month)
| Resource | Cost |
|----------|------|
| Web app (Starter plan) | $5–15 |
| PostgreSQL (main) | $15–20 |
| PostgreSQL (audit) | $15–20 |

**Pros:** Simplest setup, auto-deploys from GitHub, scales down overnight
**Cons:** US servers only, less enterprise support

#### Azure (~$75–115/month)
| Resource | Cost |
|----------|------|
| Container App (0.5 vCPU, 1 GB) | $15–40 |
| PostgreSQL Flexible (main) | $20–25 |
| PostgreSQL Flexible (audit) | $20–25 |
| Database storage (32 GB × 2) | $10 |
| Container Registry (Basic) | $7 |

**Pros:** Canadian data centres, enterprise-grade, Azure AD integration, nonprofit credits available
**Cons:** Most complex setup, higher base cost

**Nonprofit discount:** Microsoft offers $2,000 USD/year (~$2,700 CAD) in Azure credits through [Microsoft for Nonprofits](https://nonprofit.microsoft.com). If you qualify, Azure could be nearly free for 2+ years of KoNote hosting. See [Checking Nonprofit Eligibility](#checking-nonprofit-eligibility-for-azure-credits) below.

#### Elestio (~$50–80/month)
| Resource | Cost |
|----------|------|
| Docker Compose service | $25–40 |
| Managed PostgreSQL (main) | $15–20 |
| Managed PostgreSQL (audit) | $15–20 |

**Pros:** Docker Compose native, auto-deploys from GitHub, good documentation
**Cons:** No Canadian servers, fixed pricing (no scale-to-zero), smaller ecosystem

#### FullHost (~$23–45/month)
| Resource | Cost |
|----------|------|
| App server (2 reserved + ~2 dynamic cloudlets) | $8 |
| Main database (2 reserved + ~1 dynamic cloudlet) | $5.50 |
| Audit database (2 reserved + ~1 dynamic cloudlet) | $5.50 |
| Storage (2 GB) | $0.40 |
| SSL via Shared Load Balancer | Included |

**Pros:** Canadian data centre (Montreal), lowest cost, pay-per-use cloudlets, one-click deploy, free trial ($25 credits)
**Cons:** No security certifications (SOC 2, ISO 27001), smaller provider, Jelastic platform may be unfamiliar

### How to Choose

**Choose Railway if:**
- You want the simplest possible setup
- You're comfortable with US-based servers
- You want costs to scale down when not in use

**Choose Azure if:**
- You need Canadian data residency AND security certifications (health data, government contracts)
- You already use Microsoft 365 / Azure AD
- You want enterprise support and SLAs
- You qualify for Microsoft nonprofit credits (potentially free)

**Choose Elestio if:**
- You want a balance of simplicity and features
- You prefer Docker Compose workflows
- Predictable monthly billing is important

**Choose FullHost if:**
- You need Canadian data residency at the lowest cost
- You don't have funder/regulatory requirements for certified providers
- You want pay-per-use pricing
- You prefer a smaller, Canadian provider

### Data Residency Considerations

If your organisation serves clients in Canada, you may have obligations under:

- **PIPEDA** (federal privacy law) — Generally allows data to be stored outside Canada, but you must protect it adequately
- **Provincial health privacy laws** (PHIPA in Ontario, HIA in Alberta, etc.) — May require health information to stay in Canada
- **Funder requirements** — Some government contracts specify Canadian hosting

**If in doubt:** Choose Azure (Canada Central region) or FullHost for Canadian data residency.

### Security Certifications

Security certifications matter if your organisation:
- Handles health information (PHIPA in Ontario, HIA in Alberta, etc.)
- Has government contracts that specify certified vendors
- Needs to demonstrate compliance to funders, boards, or auditors

| Certification | What It Means |
|---------------|---------------|
| **SOC 2 Type II** | Independent auditors verified security controls work over time (6–12 months) |
| **SOC 2 Type 1** | Security controls exist, but not yet tested over time |
| **ISO 27001** | International standard for information security management |
| **HIPAA** | US health data standard (relevant if serving US clients) |

**Platform certifications:**

- **Azure** — Most comprehensive: SOC 2, ISO 27001, HIPAA, FedRAMP, and [90+ certifications](https://learn.microsoft.com/en-us/azure/compliance/)
- **Railway** — [SOC 2 Type II, SOC 3, HIPAA attestation](https://trust.railway.com/)
- **Elestio** — [SOC 2 Type 1, ISO 27001](https://elest.io/security-and-compliance) (working toward Type II)
- **FullHost** — No documented certifications (smaller Canadian provider)

**What this means in practice:**

If your funder or regulator requires a certified hosting provider, FullHost may not qualify — even though it offers Canadian data residency. In that case, Azure is the best choice (Canadian data + enterprise certifications).

For most small nonprofits without specific certification requirements, FullHost's lower cost and Canadian location may outweigh the lack of formal certifications.

### Scaling Models Explained

| Model | How It Works | Best For |
|-------|--------------|----------|
| **Auto-scaling (Railway, Azure)** | Adds/removes capacity based on traffic; you pay for actual usage | Variable traffic, cost-conscious |
| **Pay-per-use cloudlets (FullHost)** | Resources flex within limits; charged hourly for what you use | Predictable but variable workloads |
| **Fixed VMs (Elestio)** | You pick a size, pay hourly whether used or not | Stable, predictable workloads |

For a 200-client nonprofit with predictable 9–5 usage, any model works fine. Auto-scaling mainly saves money overnight and weekends.

### Checking Nonprofit Eligibility for Azure Credits

Microsoft offers **$2,000 USD/year (~$2,700 CAD)** in Azure credits to eligible nonprofits — enough to cover 2+ years of KoNote hosting.

#### Who Qualifies

To be eligible, your organisation must be:

- **A registered nonprofit** with legal charitable status (in Canada: CRA-registered charity or qualified donee)
- **Mission-based** — operating for community/public benefit, not commercial purposes
- **Non-discriminatory** in services and hiring

#### Who Does NOT Qualify

- Government organisations
- Schools and universities (separate program exists)
- Healthcare organisations (hospitals, clinics)
- Professional associations or unions
- Political organisations

#### How to Check and Apply

1. Go to [nonprofit.microsoft.com](https://nonprofit.microsoft.com/)
2. Click **Get Started** or **Join**
3. Enter your organisation's legal name and registration number
4. Microsoft verifies against nonprofit databases (takes 2–10 business days)
5. Once approved, activate your Azure grant at the [Azure grant activation page](https://learn.microsoft.com/en-us/industry/nonprofit/microsoft-for-nonprofits/claim-activate-nonprofit-azure-grant)

#### Important Notes

- **Annual renewal required** — Credits expire after 12 months and must be renewed
- **Usage requirements** — Microsoft may check that you're actively using their services
- **Employee must apply** — IT consultants cannot apply on behalf of a nonprofit

#### If You Don't Qualify

| Situation | Best Option |
|-----------|-------------|
| Need Canadian data + certifications | Azure at full price (~$75–115/month) |
| Need Canadian data, no certification requirement | FullHost (~$23–45/month) |
| No Canadian data requirement | Railway (~$35–55/month) |

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

KoNote automatically detects which platform it's running on and configures itself appropriately:

| Platform | How It's Detected | What's Auto-Configured |
|----------|-------------------|------------------------|
| **Railway** | `RAILWAY_ENVIRONMENT` variable | Production settings, `.railway.app` domains allowed |
| **Azure App Service** | `WEBSITE_SITE_NAME` variable | Production settings, `.azurewebsites.net` domains allowed |
| **Elestio** | `ELESTIO_VM_NAME` variable | Production settings, `.elest.io` domains allowed |
| **Docker/Self-hosted** | `DATABASE_URL` is set | Production settings, localhost allowed by default |

This means you only need to set the **essential** variables for each platform — KoNote handles the rest.

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
git clone https://github.com/your-org/KoNote-web.git
cd KoNote-web
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

This creates a user with full admin access. Once logged in, you can create additional users through the web interface using **invite links** (recommended) or direct user creation. See [User Management](administering-konote.md#user-management) for details.

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

## Deploy to Railway

Railway automatically builds and deploys from GitHub. Best for small organisations wanting simple cloud hosting.

**Estimated cost:** ~$45–50/month (app + two databases)

### Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select **KoNote-web**
4. Click **Deploy**

### Step 2: Add PostgreSQL Databases

KoNote needs **two** PostgreSQL databases (main + audit).

1. Click **+ Add** → **Add from Marketplace** → **PostgreSQL**
2. Wait for it to initialise
3. Repeat to add a second PostgreSQL database

### Step 3: Configure Environment Variables

In your Railway project, click **Variables** on your app service and add:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Your generated key |
| `FIELD_ENCRYPTION_KEY` | Your generated key |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (use your first database's name) |
| `AUDIT_DATABASE_URL` | `${{Postgres-XXXX.DATABASE_URL}}` (use your second database's name) |
| `DEMO_MODE` | `true` (recommended — loads sample data for evaluation) |

**Note:** The `${{ServiceName.DATABASE_URL}}` syntax tells Railway to pull the URL from your Postgres service. Check your database service names in the Railway dashboard.

**Password requirements:** When you create your admin account, use at least 10 characters. KoNote enforces this — shorter passwords will be rejected.

Optional variables (auto-detected, only set if needed):
- `ALLOWED_HOSTS` — Auto-includes `.railway.app` domains
- `AUTH_MODE` — Defaults to `local`, set to `azure` for SSO
- `KONOTE_MODE` — Set to `production` for strict security checks (blocks startup if SECRET_KEY or encryption key are missing)

### Step 4: Redeploy

Click **Redeploy** and wait for the build to complete (~60 seconds). The container automatically runs database migrations, seeds sample data, runs security checks, and starts the web server — no manual steps needed.

### Step 5: Create Your First Admin User

The container automatically runs migrations and seed data, but you still need an admin account to log in.

**If `DEMO_MODE=true`** (recommended for evaluation): The seed process creates a `demo-admin` user with password `demo1234`. You can log in immediately — skip to Step 6.

**For production (no demo mode):** Use the Railway CLI to create your admin:

```bash
railway run python manage.py createsuperuser
```

You'll be prompted for a username and password. This creates a user with full admin access. Once logged in, you can invite additional staff through the web interface. See [User Management](administering-konote.md#user-management).

### Step 6: Verify

Click the generated domain (e.g., `KoNote-web-production-xxxx.up.railway.app`). You should see the login page.

If `DEMO_MODE` is `true`, you'll see demo login buttons for six sample users (one per role: admin, program manager, case worker, front desk, auditor, and a demo user). These are pre-loaded with sample clients and data so you can explore the system immediately.

### Step 7: HTTPS

Railway handles HTTPS automatically — no certificate setup needed. Your `.railway.app` domain and any custom domains you add are served over HTTPS by default.

**Note:** Login requires HTTPS (the app sets secure cookies). This works out of the box on Railway.

### Adding a Custom Domain

1. In Railway, find **Domain** section
2. Click **Add Custom Domain**
3. Enter your domain (e.g., `outcomes.myorg.ca`)
4. Follow DNS instructions from Railway
5. Update `ALLOWED_HOSTS` to include your domain

Railway automatically provisions an SSL certificate for custom domains.

### Moving to Production Use

Your KoNote instance comes pre-loaded with demo users and sample data so you can explore how everything works. When your organisation is ready to use it for real:

1. **Create real staff accounts** — Go to Admin → Users and invite your team. These are regular (non-demo) accounts.
2. **Real staff never see demo data** — Demo clients and demo users are completely separate. Your real staff will see an empty client list, ready for your actual clients.
3. **You don't need to delete demo data** — It stays invisible to real users. The demo login buttons on the login page remain available for training purposes.
4. **Optionally disable demo logins** — If you no longer want the demo login buttons on the login page, set `DEMO_MODE` to `false` in Railway Variables and redeploy.

### Enable Automatic Backups

Railway's PostgreSQL databases support point-in-time recovery on paid plans. To protect your data:

1. In Railway, click on each PostgreSQL service (main and audit)
2. Check the **Backups** tab for available options
3. Railway Pro plans include automatic daily backups with 7-day retention

**Also recommended:**
- Periodically download a manual backup of both databases
- Store your `FIELD_ENCRYPTION_KEY` separately from backups — you need both to restore encrypted data
- Test restoring from a backup at least once before going live

### Azure AD SSO (Optional)

To let users log in with Microsoft credentials:

1. Register an app in [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
2. Set redirect URI to `https://your-domain/auth/callback/`
3. Create a client secret
4. Add to Railway variables:
   - `AUTH_MODE=azure`
   - `AZURE_CLIENT_ID=...`
   - `AZURE_CLIENT_SECRET=...`
   - `AZURE_TENANT_ID=...`
   - `AZURE_REDIRECT_URI=https://your-domain/auth/callback/`

---

## Deploy to Azure

Azure Container Apps provides enterprise-grade hosting with Azure AD integration.

**Time estimate:** 1–2 hours

### Step 1: Create Resource Group

```bash
az group create --name KoNote-prod --location canadacentral
```

### Step 2: Create PostgreSQL Databases

```bash
# Main database
az postgres flexible-server create \
  --resource-group KoNote-prod \
  --name KoNote-db \
  --location canadacentral \
  --admin-user konote \
  --admin-password <YOUR_PASSWORD> \
  --version 16

# Audit database
az postgres flexible-server create \
  --resource-group KoNote-prod \
  --name KoNote-audit-db \
  --location canadacentral \
  --admin-user audit_writer \
  --admin-password <YOUR_AUDIT_PASSWORD> \
  --version 16
```

Create the databases:

```bash
az postgres flexible-server db create \
  --resource-group KoNote-prod \
  --server-name KoNote-db \
  --database-name konote

az postgres flexible-server db create \
  --resource-group KoNote-prod \
  --server-name KoNote-audit-db \
  --database-name konote_audit
```

### Step 3: Create Container Registry

```bash
az acr create \
  --resource-group KoNote-prod \
  --name KoNoteregistry \
  --sku Basic
```

### Step 4: Build and Push Docker Image

```bash
docker build -t KoNote:latest .
az acr login --name KoNoteregistry
docker tag KoNote:latest KoNoteregistry.azurecr.io/KoNote:latest
docker push KoNoteregistry.azurecr.io/KoNote:latest
```

### Step 5: Create Container App

```bash
az containerapp create \
  --name KoNote-web \
  --resource-group KoNote-prod \
  --environment KoNote-env \
  --image KoNoteregistry.azurecr.io/KoNote:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server KoNoteregistry.azurecr.io \
  --cpu 0.5 \
  --memory 1Gi
```

### Step 6: Configure Environment Variables

In Azure Portal, go to your Container App → Containers → Environment variables. Add:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Your generated key |
| `FIELD_ENCRYPTION_KEY` | Your generated key |
| `DATABASE_URL` | `postgresql://konote:PASSWORD@konote-db.postgres.database.azure.com:5432/konote` |
| `AUDIT_DATABASE_URL` | `postgresql://audit_writer:PASSWORD@KoNote-audit-db.postgres.database.azure.com:5432/konote_audit` |

Optional (auto-detected):
- `ALLOWED_HOSTS` — Auto-includes `.azurewebsites.net` domains; add custom domains if needed
- `AUTH_MODE` — Defaults to `local`, set to `azure` for Azure AD SSO

### Step 7: Run Migrations

Create a temporary Azure Container Instance to run migrations:

```bash
az container create \
  --resource-group KoNote-prod \
  --name KoNote-migrate \
  --image KoNoteregistry.azurecr.io/KoNote:latest \
  --environment-variables DATABASE_URL="..." AUDIT_DATABASE_URL="..." SECRET_KEY="..." FIELD_ENCRYPTION_KEY="..." \
  --command-line "/bin/bash -c 'python manage.py migrate && python manage.py migrate --database=audit'"
```

Delete the container after it completes.

### Step 8: Create Your First Admin User

Create a temporary container to run the admin creation command:

```bash
az container create \
  --resource-group KoNote-prod \
  --name KoNote-admin \
  --image KoNoteregistry.azurecr.io/KoNote:latest \
  --environment-variables DATABASE_URL="..." SECRET_KEY="..." FIELD_ENCRYPTION_KEY="..." \
  --command-line "/bin/bash -c 'python manage.py createsuperuser --username admin'"
```

You'll be prompted for a password. Delete the container after it completes.

Once logged in, you can invite additional staff through the web interface using invite links. See [User Management](administering-konote.md#user-management).

### Step 9: Configure Custom Domain

1. Go to Container App → Custom domains
2. Add your domain
3. Follow Azure's DNS validation instructions
4. Azure automatically provisions an SSL certificate

---

## Deploy to Elestio

Elestio runs Docker Compose applications with managed services.

### Step 1: Create Service

1. Log in to [elest.io](https://elest.io)
2. Create a new **Docker Compose** service
3. Paste your `docker-compose.yml` content

### Step 2: Configure Environment Variables

Add these in the Elestio dashboard:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Your generated key |
| `FIELD_ENCRYPTION_KEY` | Your generated key |
| `DATABASE_URL` | `postgresql://konote:konote@db:5432/konote` |
| `AUDIT_DATABASE_URL` | `postgresql://audit_writer:audit_pass@audit_db:5432/konote_audit` |

Optional (auto-detected):
- `ALLOWED_HOSTS` — Auto-includes `.elest.io` domains; add custom domains if needed
- `AUTH_MODE` — Defaults to `local`, set to `azure` for Azure AD SSO

### Step 3: Connect GitHub Repository

1. Go to Repository settings in Elestio
2. Connect to your GitHub account
3. Select the `KoNote-web` repository
4. Choose the `main` branch

### Step 4: Run Initial Setup

In the Elestio console, run:

```bash
python manage.py migrate
python manage.py migrate --database=audit
python manage.py seed
python manage.py lockdown_audit_db
```

KoNote auto-detects Elestio and uses production settings automatically.

### Step 5: Create Your First Admin User

In the Elestio console, run:

```bash
python manage.py createsuperuser
```

Enter a username and password when prompted. This creates the initial admin account. Once logged in, you can invite additional staff through the web interface. See [User Management](administering-konote.md#user-management).

### Step 6: Configure Domain and TLS

1. Point your domain's DNS to Elestio's IP
2. In Elestio, add your custom domain
3. Enable HTTPS enforcement

---

## Deploy to FullHost

FullHost is a Canadian hosting provider using the Jelastic platform. It offers pay-per-use "cloudlet" pricing and Canadian data residency (Montreal data centre).

**Estimated cost:** ~$23–45 CAD/month (see [detailed pricing](deploy-fullhost.md#understanding-costs))
**Free trial:** $25 in credits (no credit card required)

For complete step-by-step instructions, see the **[FullHost Deployment Guide](deploy-fullhost.md)**.

### Quick Start: One-Click Deploy

1. Go to [fullhost.com/cloud-paas](https://www.fullhost.com/cloud-paas/) and create a free account
2. Click the deploy button (in the [FullHost guide](deploy-fullhost.md#step-2-deploy-konote2))
3. Fill in: organisation name, admin email, admin password, client term
4. Click **Install** and wait 5–10 minutes
5. **Save the encryption key** shown on the success screen

That's it — you'll have a working KoNote instance at a URL like `https://konote2-abc123.jls-can1.cloudjiffy.net`.

### Why FullHost?

- **Canadian data residency** — Montreal data centre satisfies PIPEDA and provincial requirements
- **Lowest cost option** — ~$23/month for a small nonprofit
- **One-click deploy** — No command line required
- **Pay-per-use** — Cloudlets scale with actual usage

### FullHost-Specific Notes

- **Cloudlets:** FullHost charges by "cloudlets" (128 MB RAM + 200 MHz CPU). Your environment scales automatically within the limits you set.
- **Reserved cloudlets:** Minimum guaranteed resources (~$1.50/month each)
- **Dynamic cloudlets:** Additional capacity used only during activity (~$2.50/month each)
- **SSL:** Provided free through the Shared Load Balancer with Let's Encrypt (do NOT add an external IP to the app container — it breaks SSL)

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

1. **[Administering KoNote](administering-KoNote.md)** — Configure your agency's settings
2. **[Using KoNote](using-KoNote.md)** — Train your staff
