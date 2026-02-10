# KoNote2 Web — Azure Deployment Guide

This guide walks you through deploying KoNote2 Web to Microsoft Azure. We'll use Azure Container Apps to run the application and Azure Database for PostgreSQL to store your data.

**Time estimate:** 1–2 hours for first-time setup (depending on Azure experience and confirmation times from IT/security).

---

## Prerequisites

Before starting, you'll need:

- An **Azure subscription** (with sufficient permissions to create resources)
- A **domain name** (to configure SSL/TLS certificates and Azure AD)
- **Azure CLI** installed on your computer ([install here](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows)), *or*
- Access to the **Azure Portal** in your web browser (if you prefer to use the graphical interface)
- A **GitHub account** with access to the KoNote2 Web repository
- **Docker Desktop** installed locally (for testing locally before deploy)
- A text editor to manage environment variables

---

## Step 1: Create an Azure Resource Group

A resource group is a container that holds all the resources for your application (databases, app service, networking, etc.). Think of it as a project folder.

### Option A: Using Azure Portal (graphical)

1. Go to [portal.azure.com](https://portal.azure.com) and log in.
2. Click "Create a resource" or search for "Resource Group".
3. Fill in:
   - **Resource Group name:** e.g., `KoNote2-prod` or `KoNote2-nonprofit-name`
   - **Region:** Choose the Azure region closest to your users (e.g., `Canada Central` for Canadian nonprofits)
4. Click "Review + create", then "Create".
5. Wait for the resource group to be created (usually < 1 minute).

### Option B: Using Azure CLI

Open a terminal/command prompt and run:

```bash
az group create --name KoNote2-prod --location canadacentral
```

Replace `KoNote2-prod` with your preferred resource group name. Replace `canadacentral` with your region of choice.

---

## Step 2: Create Two Azure PostgreSQL Databases

KoNote2 Web needs two separate PostgreSQL databases:
1. **KoNote2** — main application database (stores clients, outcomes, notes, etc.)
2. **konote_audit** — read-only audit log database (for security and compliance)

### Why two databases?

The audit database is intentionally read-only and isolated. This prevents accidental or malicious tampering with the audit trail—even if someone gains access to the main database, they cannot modify the audit logs.

### Create the Databases

#### Option A: Using Azure Portal

1. In the Azure Portal, search for "Azure Database for PostgreSQL — Flexible Server".
2. Click "Create".
3. **Project details:**
   - **Resource Group:** Select the one you created in Step 1.
   - **Server name:** `KoNote2-db` (this must be globally unique, so Azure may ask you to use something like `KoNote2-db-abc123`)
   - **Region:** Same as your resource group.
   - **PostgreSQL version:** 16 (match your docker-compose.yml)
4. **Administrator account:**
   - **Admin username:** `konote`
   - **Password:** Generate a strong password. Save it in a secure location (password manager).
5. Click "Review + create", then "Create".
6. Wait for deployment (5–10 minutes).
7. Once done, **repeat steps 1–6 for the second database:**
   - Server name: `KoNote2-audit-db`
   - Admin username: `audit_writer`
   - Password: Generate a different strong password. Save it.

#### Option B: Using Azure CLI

```bash
# Main database
az postgres flexible-server create \
  --resource-group KoNote2-prod \
  --name KoNote2-db \
  --location canadacentral \
  --admin-user konote \
  --admin-password <YOUR_STRONG_PASSWORD> \
  --version 16

# Audit database
az postgres flexible-server create \
  --resource-group KoNote2-prod \
  --name KoNote2-audit-db \
  --location canadacentral \
  --admin-user audit_writer \
  --admin-password <YOUR_STRONG_AUDIT_PASSWORD> \
  --version 16
```

Replace `<YOUR_STRONG_PASSWORD>` and `<YOUR_STRONG_AUDIT_PASSWORD>` with strong passwords you generate.

### Create the Databases Within Each Server

Once each PostgreSQL server is created, you need to create the actual databases (`KoNote2` and `konote_audit`).

#### Option A: Using Azure Portal

1. Go to your first PostgreSQL server (`KoNote2-db`).
2. In the left menu, click "Databases".
3. Click "+ Add".
4. **Database name:** `konote`
5. Click "Save".
6. Repeat for the audit server (`KoNote2-audit-db`):
   - Database name: `konote_audit`

#### Option B: Using Azure CLI

```bash
az postgres flexible-server db create \
  --resource-group KoNote2-prod \
  --server-name KoNote2-db \
  --database-name konote

az postgres flexible-server db create \
  --resource-group KoNote2-prod \
  --server-name KoNote2-audit-db \
  --database-name konote_audit
```

### Configure Firewall Rules (Allow Container App to Connect)

You'll need to allow your Azure Container App to connect to these databases. For now, you can create a broad rule and tighten it later once you know your app's IP.

#### Option A: Using Azure Portal

1. Go to your PostgreSQL server.
2. In the left menu, click "Networking".
3. Under "Firewall rules", click "+ Add current client IP" (or "+ Add a firewall rule").
4. For Azure services:
   - **Rule name:** `Allow Azure Services`
   - **Start IP:** `0.0.0.0`
   - **End IP:** `0.0.0.0`
   - This allows Azure services (like Container App) to connect.
5. Click "Save".
6. Repeat for the audit database.

#### Option B: Using Azure CLI

```bash
# For main database
az postgres flexible-server firewall-rule create \
  --resource-group KoNote2-prod \
  --name KoNote2-db \
  --rule-name allow-azure-services \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# For audit database
az postgres flexible-server firewall-rule create \
  --resource-group KoNote2-prod \
  --name KoNote2-audit-db \
  --rule-name allow-azure-services \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

---

## Step 3: Create an Azure Container Registry (Optional but Recommended)

An Azure Container Registry is where Docker images are stored. This is optional—you can also push images directly to Docker Hub—but it's recommended for security (keep images within Azure).

### Option A: Using Azure Portal

1. Search for "Container Registries".
2. Click "Create".
3. **Details:**
   - **Resource Group:** Select your resource group.
   - **Registry name:** `KoNote2registry` (must be lowercase, no hyphens; Azure adds a unique suffix)
   - **Region:** Same as your resource group.
   - **SKU:** Basic (sufficient for most nonprofits)
4. Click "Review + create", then "Create".
5. Once created, go to your registry and note the **Login server** (e.g., `KoNote2registry.azurecr.io`).

### Option B: Using Azure CLI

```bash
az acr create \
  --resource-group KoNote2-prod \
  --name KoNote2registry \
  --sku Basic
```

---

## Step 4: Prepare Your Docker Image

Before deploying to Azure, you'll build a Docker image of KoNote2 Web locally and push it to a registry.

### Step 4a: Generate Encryption Keys (locally)

Open a terminal and run:

```bash
# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate FIELD_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save both keys somewhere secure (you'll need them for environment variables in Step 5).

### Step 4b: Build the Docker Image

In the KoNote2 Web repository root directory, run:

```bash
docker build -t KoNote2:latest .
```

This reads the `Dockerfile` and builds an image called `KoNote2` with the tag `latest`. The build process:
1. Starts with Python 3.12
2. Installs dependencies from `requirements.txt`
3. Copies your application code
4. Creates a non-root user for security
5. Collects static files (CSS, JavaScript, images)

### Step 4c: Push to a Container Registry

If you created an Azure Container Registry (Step 3), authenticate and push:

```bash
# Log in to Azure Container Registry
az acr login --name KoNote2registry

# Tag the image with your registry's login server
docker tag KoNote2:latest KoNote2registry.azurecr.io/KoNote2:latest

# Push to the registry
docker push KoNote2registry.azurecr.io/KoNote2:latest
```

**Alternative:** If you're using Docker Hub instead:

```bash
docker tag KoNote2:latest <your-dockerhub-username>/KoNote2:latest
docker push <your-dockerhub-username>/KoNote2:latest
```

---

## Step 5: Create an Azure Container App

Azure Container Apps is a managed service that runs your Docker container. Think of it as a lightweight alternative to Kubernetes—it handles scaling and networking for you.

### Option A: Using Azure Portal

1. Search for "Container Apps".
2. Click "Create Container App".
3. **Basics tab:**
   - **Resource Group:** Select your resource group.
   - **Container App name:** `KoNote2-web` or `KoNote2-app`
   - **Region:** Same as your resource group.
   - **Container Apps Environment:** Create new. This takes a minute.
     - **Name:** `KoNote2-env`
4. **Container tab:**
   - **Image source:** Select "Azure Container Registry" (if you pushed to ACR) or "Docker Hub" (if you pushed to Docker Hub).
   - **Select image:** Browse and select `KoNote2:latest`.
   - **CPU and memory:**
     - **CPU:** 0.5 cores
     - **Memory:** 1 Gi
     - (Upgrade later if needed; this is sufficient for small nonprofits.)
   - **Environment variables:** You'll add these in the next step.
5. **Ingress tab:**
   - **Ingress:** Enable
   - **Ingress traffic:** Accept traffic from anywhere
   - **Target port:** 8000 (matches your Dockerfile EXPOSE)
6. Click "Review + create", then "Create".

### Option B: Using Azure CLI

```bash
az containerapp create \
  --name KoNote2-web \
  --resource-group KoNote2-prod \
  --environment KoNote2-env \
  --image KoNote2registry.azurecr.io/KoNote2:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server KoNote2registry.azurecr.io \
  --cpu 0.5 \
  --memory 1Gi
```

Once created, note the Container App's **URL** (e.g., `https://KoNote2-web.yellowplant-abc123.canadacentral.azurecontainerapps.io`). You'll use this to configure environment variables.

---

## Step 6: Configure Environment Variables

Environment variables tell Django how to run (database URLs, secret keys, authentication mode, etc.).

### Gather Your Values

Before setting environment variables, collect these values:

| Variable | Value | Source |
|----------|-------|--------|
| `SECRET_KEY` | (generated in Step 4a) | Your secure location |
| `FIELD_ENCRYPTION_KEY` | (generated in Step 4a) | Your secure location |
| `DATABASE_URL` | `postgresql://konote:<PASSWORD>@<SERVER_NAME>.postgres.database.azure.com:5432/konote` | From Step 2 (main DB) |
| `AUDIT_DATABASE_URL` | `postgresql://audit_writer:<AUDIT_PASSWORD>@<SERVER_NAME_AUDIT>.postgres.database.azure.com:5432/konote_audit` | From Step 2 (audit DB) |
| `DJANGO_SETTINGS_MODULE` | `konote.settings.production` | Fixed |
| `AUTH_MODE` | `azure` (for Azure AD) or `local` | Your choice |
| `AZURE_CLIENT_ID` | (if using Azure AD) | Step 8 |
| `AZURE_CLIENT_SECRET` | (if using Azure AD) | Step 8 |
| `AZURE_TENANT_ID` | (if using Azure AD) | Step 8 |
| `AZURE_REDIRECT_URI` | `https://<YOUR_DOMAIN>/auth/callback/` | Your domain |
| `ALLOWED_HOSTS` | `your-domain.com,www.your-domain.com` | Your domain(s) |

### Example DATABASE_URL

If your main PostgreSQL server is named `KoNote2-db` (Azure appends a suffix), the full server name is shown in the Azure Portal under "Server name". Let's say it's `KoNote2-db-xyz123.postgres.database.azure.com`:

```
postgresql://konote:YourStrongPassword@konote-db-xyz123.postgres.database.azure.com:5432/konote
```

### Set Environment Variables in Container App

#### Option A: Using Azure Portal

1. Go to your Container App.
2. In the left menu, click "Containers" or "Secrets".
3. Click "Edit and deploy".
4. Under "Containers", select your container.
5. Scroll to "Environment variables".
6. Add each variable:
   - Click "+ Add".
   - **Name:** e.g., `SECRET_KEY`
   - **Value:** Paste your value.
   - Check "Secure" for sensitive values (SECRET_KEY, FIELD_ENCRYPTION_KEY, passwords).
7. Click "Save" and then "Create".

#### Option B: Using Azure CLI

```bash
az containerapp update \
  --name KoNote2-web \
  --resource-group KoNote2-prod \
  --set-env-vars \
    DJANGO_SETTINGS_MODULE=konote.settings.production \
    DATABASE_URL="postgresql://konote:PASSWORD@konote-db-xyz123.postgres.database.azure.com:5432/konote" \
    AUDIT_DATABASE_URL="postgresql://audit_writer:AUDIT_PASSWORD@KoNote2-audit-db-xyz123.postgres.database.azure.com:5432/konote_audit" \
    AUTH_MODE=local \
    ALLOWED_HOSTS="your-domain.com,www.your-domain.com"
```

For sensitive variables, use `--secrets`:

```bash
az containerapp update \
  --name KoNote2-web \
  --resource-group KoNote2-prod \
  --secrets \
    SECRET_KEY="your-key-here" \
    FIELD_ENCRYPTION_KEY="your-key-here"
```

---

## Step 7: Run Initial Migrations and Seed Data

Once your Container App is running with environment variables set, you need to:
1. Run database migrations (create tables, indexes, etc.)
2. Seed initial data (organisations, roles, etc.)
3. Lock down the audit database (make it read-only)

### Create an Azure Container Instance for One-Time Tasks

Container Apps don't have an easy way to run one-time commands like migrations. Instead, we'll use an Azure Container Instance.

#### Option A: Using Azure Portal

1. Search for "Container Instances".
2. Click "Create".
3. **Project details:**
   - **Resource Group:** Your resource group.
   - **Container name:** `KoNote2-migrate`
   - **Region:** Same as your resource group.
   - **Image source:** "Azure Container Registry" or "Docker Hub".
   - **Image:** `KoNote2:latest`
   - **OS type:** Linux
4. **Advanced tab:**
   - **Environment variables:** Add the same variables from Step 6.
   - **Command override:**
     ```
     /bin/bash -c "python manage.py migrate --database=default && python manage.py migrate --database=audit && python manage.py seed_data && python manage.py lockdown_audit_db"
     ```
5. **Size:** CPU: 1, Memory: 1 GB
6. Click "Review + create", then "Create".
7. Once it finishes (1–3 minutes), you can delete it.

#### Option B: Using Azure CLI

```bash
az container create \
  --resource-group KoNote2-prod \
  --name KoNote2-migrate \
  --image KoNote2registry.azurecr.io/KoNote2:latest \
  --environment-variables \
    DATABASE_URL="postgresql://..." \
    AUDIT_DATABASE_URL="postgresql://..." \
    SECRET_KEY="..." \
    FIELD_ENCRYPTION_KEY="..." \
  --command-line "/bin/bash -c 'python manage.py migrate --database=default && python manage.py migrate --database=audit && python manage.py seed_data && python manage.py lockdown_audit_db'"
```

### Verify Migrations Completed

1. Go to the Azure Portal.
2. Find your Container Instance.
3. Click "Containers" and review the logs.
4. Look for messages like `"Applying auth.0001_initial: OK"` and `"Operations to perform... 0 migrations."` (for the second run).
5. If successful, delete the Container Instance.

---

## Step 8: Set Up Azure AD Single Sign-On (SSO)

If you want users to log in with their Microsoft/Azure AD credentials (recommended for enterprise nonprofits), follow this section. Otherwise, skip to Step 9.

### Why Azure AD SSO?

- Users log in with their Microsoft account (no separate password).
- Integrates with your organization's identity system.
- Better security (multi-factor authentication can be required).

### Register an Application in Azure AD

1. Go to [portal.azure.com](https://portal.azure.com).
2. Search for "Azure Active Directory".
3. In the left menu, click "App registrations".
4. Click "+ New registration".
5. **Register an application:**
   - **Name:** `KoNote2 Web`
   - **Supported account types:** "Accounts in this organisational directory only" (if internal) or "Multitenant" (if external users).
   - **Redirect URI (optional):**
     - **Platform:** Web
     - **URI:** `https://your-domain.com/auth/callback/` (match your Container App's domain)
6. Click "Register".
7. You'll see an overview page. **Save these values:**
   - **Application (client) ID** ← Store as `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** ← Store as `AZURE_TENANT_ID`

### Create a Client Secret

1. In your app registration, go to "Certificates & secrets" (left menu).
2. Click "+ New client secret".
3. **Add a client secret:**
   - **Description:** `KoNote2 Web deployment`
   - **Expires:** Choose a period (e.g., 24 months; set a calendar reminder to renew it).
4. Click "Add".
5. **Immediately copy and save the secret value** (you won't see it again). ← Store as `AZURE_CLIENT_SECRET`

### Configure Redirect URIs

1. Go to "Authentication" (left menu).
2. Under "Platform configurations", click "Web".
3. Add your redirect URI (if not already there):
   - `https://your-domain.com/auth/callback/`
4. Click "Save".

### Update Container App Environment Variables

Go back to your Container App and update:

```
AUTH_MODE=azure
AZURE_CLIENT_ID=<from app registration>
AZURE_CLIENT_SECRET=<from client secret>
AZURE_TENANT_ID=<from app registration>
AZURE_REDIRECT_URI=https://your-domain.com/auth/callback/
```

---

## Step 9: Configure Your Domain and SSL Certificate

Your Container App currently has a generated Azure domain (e.g., `KoNote2-web.yellowplant-abc123.azurecontainerapps.io`). To use your own domain, you need to:

1. Point your domain's DNS to Azure.
2. Set up an SSL certificate (HTTPS).

### Option A: Using Azure Portal

1. Go to your Container App.
2. Click "Custom domains" (left menu).
3. Click "+ Add custom domain".
4. **Domain configuration:**
   - **Domain:** Enter your domain (e.g., `KoNote2.yournonprofit.ca`).
5. Azure will provide DNS validation instructions.
6. Update your DNS provider (GoDaddy, Google Domains, etc.) with the CNAME record Azure provides.
7. Return to the Azure Portal and click "Validate".
8. Azure automatically provisions an SSL certificate (usually within 5 minutes).

### Option B: Using Your Existing SSL Certificate (Advanced)

If you already have an SSL certificate, you can upload it. This is beyond the scope of this guide—consult your domain registrar or IT team.

---

## Step 10: Verify Your Deployment

Once everything is set up, test that your application works:

1. Go to your domain (or Container App URL if not using a custom domain).
2. You should see the KoNote2 Web login page.
3. If using local auth:
   - Create a test user in the Django admin panel (`/admin/`).
   - Try logging in.
4. If using Azure AD SSO:
   - Click "Login with Microsoft".
   - You should be redirected to Microsoft login, then back to your app.
5. If login works, you're ready to go. If not, check the container logs:
   - Go to "Containers" → "Log stream" in your Container App.
   - Look for error messages.

---

## Step 11: Set Up Monitoring and Backups

Your KoNote2 instance is now live. To keep it running reliably, set up monitoring and backups.

### Enable Database Backups

Azure PostgreSQL automatically backs up your data daily. To configure:

1. Go to your PostgreSQL server.
2. Click "Server parameters" (left menu).
3. Look for backup-related settings (e.g., `backup_retention_days`).
4. Increase the retention period if needed (default is 7 days; consider 30 days for compliance).

### Enable Application Insights (Optional but Recommended)

Application Insights monitors your app's performance and errors.

#### Using Azure Portal

1. Search for "Application Insights".
2. Click "Create".
3. **Basics:**
   - **Resource Group:** Your resource group.
   - **Name:** `KoNote2-insights`
   - **Region:** Same as your resource group.
4. Click "Review + create", then "Create".
5. Once created, go to your Container App.
6. Click "Monitoring" or "Insights" (left menu).
7. Link your Application Insights resource.

### Monitor Container App Health

1. Go to your Container App.
2. Click "Monitoring" (left menu).
3. View:
   - **CPU and memory usage**
   - **Restart counts**
   - **HTTP request rates**
4. Set up **alerts** (e.g., alert if CPU > 80% for 5 minutes).

---

## Step 12: Ongoing Maintenance

### Check Logs Regularly

1. Go to your Container App.
2. Click "Containers" (left menu) → "Log stream".
3. Watch for errors, warnings, or unusual patterns.

### Update the Application

When you have new code to deploy:

1. Test locally with Docker Compose (see `README.md`).
2. Build a new Docker image: `docker build -t KoNote2:v1.2.0 .`
3. Push to your registry: `docker push KoNote2registry.azurecr.io/KoNote2:v1.2.0`
4. Update your Container App to use the new image tag.
5. Run migrations (if needed) using the Container Instance method (Step 7).

### Renew Azure AD Client Secret

If you created an Azure AD client secret (Step 8), mark your calendar 30 days before it expires:

1. Go to your app registration.
2. Click "Certificates & secrets".
3. Check the expiry date.
4. Before expiry, create a new secret and update your environment variables.

### Database Maintenance

- Monitor database size and upgrade if approaching limits.
- Review PostgreSQL slow query logs for performance issues.
- Plan for data archival if your audit log grows very large.

---

## Troubleshooting

### "Container won't start" or "Connection refused"

- Check environment variables (especially DATABASE_URL and AUDIT_DATABASE_URL).
- Verify firewall rules on PostgreSQL allow Azure services.
- Check container logs: Go to Container App → Containers → Log stream.

### "Database connection failed"

- Verify server names and passwords are correct in DATABASE_URL and AUDIT_DATABASE_URL.
- Test connectivity from your local machine using `psql`:
  ```bash
  psql -h <server-name>.postgres.database.azure.com -U konote -d konote
  ```
- Check PostgreSQL firewall rules (Step 2).

### "Static files not loading" (CSS/images broken)

- Ensure the Dockerfile's `collectstatic` command ran successfully.
- Check if `ALLOWED_HOSTS` includes your domain.
- Verify Azure CDN or Caddy configuration if you set up a reverse proxy.

### "Azure AD login not working"

- Verify AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID are set correctly.
- Check AZURE_REDIRECT_URI matches your registered app in Azure AD.
- Review app registration permissions—add "User.Read" if needed.

### "Migrations failed"

- Check Container Instance logs (Step 7).
- Verify both database URLs are correct and databases exist.
- Ensure the audit database firewall allows your IP.

---

## Support and Additional Resources

- **Azure Documentation:** [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- **PostgreSQL on Azure:** [Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/azure/postgresql/)
- **Django Deployment:** [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- **KoNote2 Web Repository:** Check `README.md` for local development setup.

---

**Last updated:** 2026-02-02
