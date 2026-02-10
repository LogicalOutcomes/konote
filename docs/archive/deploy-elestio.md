# Deploying KoNote2 Web to Elest.io

This guide walks you through deploying KoNote2 Web on **Elest.io**, a cloud hosting platform that runs Docker applications.

**What you'll learn:**
- How to set up a new Elest.io service
- How to configure two PostgreSQL databases (one for the app, one for audit logs)
- How to set environment variables securely
- How to run initial setup commands
- How to set up a custom domain with HTTPS
- How to maintain your deployment

---

## Prerequisites

Before you start, you'll need:

1. **An Elest.io account** — sign up at [https://elest.io](https://elest.io)
2. **Your GitHub repository** connected to Elest.io (or a way to push your code there)
3. **The following information ready:**
   - A secure `SECRET_KEY` (Django's secret key for the app)
   - A `FIELD_ENCRYPTION_KEY` (for encrypting sensitive client information)
   - Your custom domain name (e.g., `KoNote2.myorganisation.ca`)
   - Your authentication method: `azure` (Azure AD SSO) or `local` (username/password)
   - If using Azure AD: your Azure Client ID, Client Secret, and Tenant ID

**About encryption keys:**

Generate these commands in Python (on your computer) to create secure keys:

```python
# Generate SECRET_KEY
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())

# Generate FIELD_ENCRYPTION_KEY
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Keep these keys safe — store them in a password manager. You'll need them in step 3.

---

## Step 1: Create a New Service on Elest.io

1. Log in to your Elest.io dashboard
2. Click **Create a New Service** (or **New**)
3. Choose **Docker Compose**
4. Give your service a name (e.g., "KoNote2-web")
5. Click **Create**

Elest.io will take you to the service configuration page.

---

## Step 2: Upload the Docker Compose Configuration

Your KoNote2 Web repository includes a `docker-compose.yml` file that defines everything the app needs:
- The web application container (with gunicorn)
- Two PostgreSQL databases (main app + audit)
- Caddy (the reverse proxy for HTTPS)

**In the Elest.io dashboard:**

1. Look for the **Docker Compose** editor (usually a code editor panel)
2. Clear the default template and paste the contents of your `docker-compose.yml` file from the repository
3. Click **Save**

The `docker-compose.yml` includes all the services needed. Elest.io will use this configuration to build and run your application.

---

## Step 3: Configure Environment Variables

Environment variables are how you pass secrets and settings to the application without putting them in code.

**In the Elest.io dashboard:**

1. Look for the **Environment** or **Env Variables** section
2. Add each of these variables. For each one, click **Add** and enter the name and value:

### Required Variables

| Variable Name | What It Is | Example |
|---|---|---|
| `SECRET_KEY` | Django's secret key (from step 1 Prerequisites) | `django-insecure-...` |
| `FIELD_ENCRYPTION_KEY` | Key for encrypting client PII (from Prerequisites) | `gAAAAABl...` |
| `DATABASE_URL` | Connection string for the main app database | `postgresql://konote:konote@db:5432/konote` |
| `AUDIT_DATABASE_URL` | Connection string for the audit database | `postgresql://audit_writer:audit_pass@audit_db:5432/konote_audit` |
| `DJANGO_SETTINGS_MODULE` | Tells Django to use production settings | `konote.settings.production` |
| `ALLOWED_HOSTS` | Domain names the app will accept requests for (comma-separated) | `KoNote2.myorganisation.ca` |
| `AUTH_MODE` | Authentication method: `azure` or `local` | `local` |

### Optional Variables (Only if Using Azure AD)

If you're using Azure AD for single sign-on, also add:

| Variable Name | What It Is |
|---|---|
| `AZURE_CLIENT_ID` | Your Azure app's client ID |
| `AZURE_CLIENT_SECRET` | Your Azure app's client secret |
| `AZURE_TENANT_ID` | Your Azure organisation's tenant ID |
| `AZURE_REDIRECT_URI` | Where Azure redirects after login (e.g., `https://KoNote2.myorganisation.ca/auth/callback/`) |

---

## Step 4: Set Up PostgreSQL Databases

KoNote2 Web uses **two separate PostgreSQL databases**:
- **Main database** (`KoNote2`): stores clients, outcomes, notes, and all business data
- **Audit database** (`konote_audit`): stores an immutable record of all changes for compliance and legal protection

**Option A: Use Managed PostgreSQL on Elest.io (Recommended)**

1. In the Elest.io dashboard, click **Add Service** or **Services**
2. Choose **PostgreSQL** from the marketplace
3. Create two PostgreSQL instances:
   - First instance:
     - Name: `db` (or `KoNote2-db`)
     - Database: `konote`
     - User: `konote`
     - Password: generate a secure password
   - Second instance:
     - Name: `audit_db` (or `KoNote2-audit-db`)
     - Database: `konote_audit`
     - User: `audit_writer`
     - Password: generate a different secure password

4. After creating both databases, Elest.io will provide connection strings. Update your `DATABASE_URL` and `AUDIT_DATABASE_URL` environment variables with these strings.

**Option B: Use Databases in docker-compose.yml (Simpler for Testing)**

The `docker-compose.yml` file already includes PostgreSQL definitions for both databases. If you use this approach:
- The main database is called `db` with credentials `konote:konote`
- The audit database is called `audit_db` with credentials `audit_writer:audit_pass`
- The environment variables in `docker-compose.yml` will automatically connect the app to these databases

This is simpler for testing but less flexible for production. For production, use Option A (managed PostgreSQL).

---

## Step 5: Connect Your GitHub Repository

Elest.io can deploy directly from your GitHub repository, so that every time you push code, it automatically rebuilds and redeploys.

**In the Elest.io dashboard:**

1. Look for **Repository** or **Git** settings
2. Click **Connect to GitHub** (or similar)
3. Authorize Elest.io to access your GitHub account
4. Select the repository `KoNote2-web`
5. Choose the branch you want to deploy (usually `main` or `develop`)
6. Click **Connect**

Elest.io will now:
- Watch your repository for changes
- Automatically rebuild the Docker image when you push code
- Redeploy the application

---

## Step 6: Run Initial Setup Commands

Before the app can run, you need to:
1. Create the database tables (Django migration)
2. Set up the audit database
3. Lock down the audit database so old records can't be deleted

**In the Elest.io dashboard:**

1. Find the **Console** or **Terminal** section for your `web` service
2. Run these commands in order (copy and paste each one):

```bash
# Create tables in the main database
python manage.py migrate --settings=konote.settings.production

# Create tables in the audit database
python manage.py migrate --database=audit --settings=konote.settings.production

# Lock down the audit database (prevent accidental deletes)
python manage.py lockdown_audit_db --settings=konote.settings.production
```

After each command, you should see "OK" or success messages. If you see errors:
- Check that your `DATABASE_URL` and `AUDIT_DATABASE_URL` are correct
- Make sure both PostgreSQL services are running
- Check the service logs for more details

---

## Step 7: Set Up a Custom Domain and TLS (HTTPS)

Your app will be accessible at an Elest.io subdomain by default (e.g., `KoNote2-web-12345.elest.io`). To use your own domain with HTTPS:

**Step 7A: Point Your Domain to Elest.io**

1. In your domain registrar (the company where you bought your domain):
   - Create an `A` record pointing to the IP address Elest.io provides
   - Or create a `CNAME` record pointing to your Elest.io subdomain
   - Elest.io will tell you which one to use

2. Wait 5–15 minutes for DNS to update (check with a DNS checker tool)

**Step 7B: Configure TLS on Elest.io**

1. In the Elest.io dashboard, find the **Domains** or **TLS** section
2. Add your custom domain (e.g., `KoNote2.myorganisation.ca`)
3. Elest.io will automatically generate a free TLS certificate (using Let's Encrypt)
4. Enable HTTPS and set it to **enforce** (redirect HTTP to HTTPS)

**Step 7C: Update Environment Variables**

1. Go back to **Environment** variables
2. Update `ALLOWED_HOSTS` to include your new domain:
   ```
   KoNote2.myorganisation.ca,www.KoNote2.myorganisation.ca
   ```
3. If using Azure AD, update `AZURE_REDIRECT_URI`:
   ```
   https://KoNote2.myorganisation.ca/auth/callback/
   ```
4. Redeploy the app (Elest.io may do this automatically)

Your app is now accessible at `https://KoNote2.myorganisation.ca`.

---

## Step 8: Verify Your Deployment

Test that the app is working:

1. **Open the login page:**
   - Go to `https://KoNote2.myorganisation.ca/auth/login/`
   - You should see the KoNote2 login screen
   - The HTTPS lock icon should appear in your browser

2. **Check the health check:**
   - Elest.io periodically checks if the app is healthy
   - Look in the Elest.io dashboard under **Health** — it should show "Healthy"
   - If not healthy, check the logs for errors

3. **Test login:**
   - Log in with your credentials (depends on your `AUTH_MODE`)
   - After logging in, you should see the dashboard

4. **Check the database:**
   - In the Elest.io console, run:
   ```bash
   python manage.py dbshell --settings=konote.settings.production
   ```
   - Type `\dt` to see tables — you should see `clients`, `outcomes`, `notes`, etc.
   - Type `\q` to exit

If you see errors, check:
- **Logs tab** — look for error messages
- **Environment variables** — make sure they're all set and have no typos
- **Database connectivity** — verify `DATABASE_URL` and `AUDIT_DATABASE_URL` are correct

---

## Step 9: Ongoing Maintenance

### Viewing Logs

Logs show you what the app is doing and alert you to problems.

1. In the Elest.io dashboard, click on your service
2. Go to the **Logs** tab
3. Look for errors (usually marked in red)

Common issues:
- `Connection refused` — database isn't running
- `No such table` — migrations haven't run
- `Invalid SECRET_KEY` — check your `SECRET_KEY` environment variable

### Backup Your Databases

PostgreSQL has a backup tool. To back up your databases regularly:

1. In the Elest.io console, run:

```bash
# Backup the main database
pg_dump -h <DATABASE_HOST> -U konote -d konote > backup-main-$(date +%Y%m%d).sql

# Backup the audit database
pg_dump -h <AUDIT_DATABASE_HOST> -U audit_writer -d konote_audit > backup-audit-$(date +%Y%m%d).sql
```

Replace `<DATABASE_HOST>` and `<AUDIT_DATABASE_HOST>` with the hostnames from your environment variables (they'll look like `db-123.postgres.elestio.cloud`).

2. Download these files and store them somewhere safe (like an encrypted cloud drive)

3. Set up a monthly reminder to back up

### Restarting the App

If something goes wrong, you can restart the app without losing data:

1. In the Elest.io dashboard, find your `web` service
2. Click **Restart** (or **Redeploy**)
3. Wait 1–2 minutes for the app to come back online

### Updating the App

When you push new code to GitHub:

1. Elest.io automatically rebuilds and redeploys
2. Wait for the build to finish (check the **Build** tab)
3. Test the new version at `https://KoNote2.myorganisation.ca`

If a build fails:
- Check the **Build Logs** for error messages
- Common issues: missing dependencies in `requirements.txt`, syntax errors in Python code
- Fix the code, push again, and Elest.io will retry

### Monitoring Performance

KoNote2 Web uses Gunicorn (the Python web server) with 3 workers by default. Each worker can handle requests concurrently.

- **Slow app?** Check if you have many concurrent users. You can increase workers in the `docker-compose.yml`
- **Out of memory?** PostgreSQL or Gunicorn might need more resources. Contact Elest.io support to increase your service's memory

### Scaling Up (When You Have Many Users)

As your organisation grows, you may need:

1. **More app workers:** Edit `docker-compose.yml`, increase `--workers` in the gunicorn command
2. **More database resources:** Use Elest.io's managed PostgreSQL and request more CPU/memory
3. **Multiple app instances:** Deploy multiple copies of the `web` service behind a load balancer (ask Elest.io support)

---

## Troubleshooting

### "502 Bad Gateway" Error

This means the web app isn't responding.

**Fixes to try:**
1. Check the **Logs** tab — look for error messages
2. Ensure `DATABASE_URL` and `AUDIT_DATABASE_URL` are correct
3. Restart the service
4. Check that both PostgreSQL services are running

### "Connection refused" in Logs

The app can't reach the database.

**Fixes to try:**
1. Verify PostgreSQL is running (check the database service in Elest.io)
2. Check that `DATABASE_URL` and `AUDIT_DATABASE_URL` are correct (copy and paste them exactly)
3. Make sure usernames and passwords match what you set in PostgreSQL
4. If using managed PostgreSQL, make sure the network firewall allows connections from your app

### "No such table" Error

Migrations haven't run yet.

**Fixes to try:**
1. In the console, run:
   ```bash
   python manage.py migrate --settings=konote.settings.production
   python manage.py migrate --database=audit --settings=konote.settings.production
   ```
2. Restart the app

### "ALLOWED_HOSTS" Error

The app is rejecting requests to your domain.

**Fixes to try:**
1. Check your `ALLOWED_HOSTS` environment variable — make sure your domain is in the list
2. It should look like: `KoNote2.myorganisation.ca,www.KoNote2.myorganisation.ca`
3. Redeploy after updating

---

## Getting Help

If you get stuck:

1. **Check Elest.io documentation:** [https://elest.io/docs](https://elest.io/docs)
2. **Check Django documentation:** [https://docs.djangoproject.com](https://docs.djangoproject.com)
3. **Check PostgreSQL documentation:** [https://www.postgresql.org/docs](https://www.postgresql.org/docs)
4. **Contact Elest.io support** through your dashboard

---

## Summary

Congratulations! Your KoNote2 Web deployment is complete. Here's what you've set up:

- A web application running in a Docker container
- Two PostgreSQL databases (main app + audit)
- A reverse proxy (Caddy) for HTTPS
- A custom domain with automatic TLS certificates
- Monitoring and logging
- Backup procedures

You can now log in at `https://KoNote2.myorganisation.ca` and start using KoNote2 Web with your organisation.
