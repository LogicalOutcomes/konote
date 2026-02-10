# Deploy KoNote Web to Railway

This guide walks you through deploying KoNote Web to Railway — a hosting service that automatically builds and deploys your app from GitHub.

## What You'll Need

- **Railway account** (free to start): [railway.app](https://railway.app)
- **GitHub account** with this repository connected
- **Access to command line** (Windows PowerShell or CMD) to generate secret keys

---

## Step 1: Create a Railway Project

1. Go to [railway.app](https://railway.app) and sign in (use GitHub to sign in quickly)
2. Click **"New Project"** button in the top-right corner
3. Select **"Deploy from GitHub repo"**
4. Find and click **KoNote-web** in your list of repositories
5. Click **"Deploy"** — Railway will start building from your Dockerfile

This process takes 2–3 minutes. Your project will fail to start because we haven't set up the environment variables and databases yet. That's expected.

---

## Step 2: Add Two PostgreSQL Databases

KoNote Web needs **two separate PostgreSQL databases**:
- **Main database** (for app data: clients, programs, notes)
- **Audit database** (for immutable audit logs)

### Add the Main Database

1. In your Railway project, click the **"+ Add"** button near the top
2. Click **"Add from Marketplace"**
3. Search for **"PostgreSQL"** and click it
4. Click **"Add PostgreSQL"** to add it to your project
5. Wait 30 seconds for it to initialise — you'll see a green checkmark when ready

### Add the Audit Database

1. Click **"+ Add"** again
2. Click **"Add from Marketplace"**
3. Search for **"PostgreSQL"** again
4. Click **"Add PostgreSQL"** to add a second database
5. Wait for it to initialise

You now have two PostgreSQL databases. We'll configure them next.

---

## Step 3: Generate Secret Keys

You need two randomly-generated secret keys. We'll create these on your computer using Python.

**For SECRET_KEY:**

1. Open Windows PowerShell or Command Prompt
2. Paste this command and press Enter:

```
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the long text that appears. Save it somewhere — you'll need it in the next step.

**For FIELD_ENCRYPTION_KEY:**

1. In the same PowerShell or Command Prompt, paste this command and press Enter:

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy this text as well and save it.

**Example output** (yours will be different):

```
SECRET_KEY: 9q^-$mj2*v#@!&kb8$p-*gv5z&qk3*j#&j@8$%q
FIELD_ENCRYPTION_KEY: gAAAAABlabcdefgh1234567890abcdefgh1234567890abcdefgh1234567890=
```

---

## Step 4: Configure Environment Variables

In your Railway project, look for the **"Variables"** tab. We'll set up six environment variables:

### SECRET_KEY
1. Click in the **Variable** field and type `SECRET_KEY`
2. Click in the **Value** field and paste the long key you generated (the Django one)
3. Click **"Add Variable"**

### FIELD_ENCRYPTION_KEY
1. Click **"+ Add Variable"**
2. Type `FIELD_ENCRYPTION_KEY` in the Variable field
3. Paste the encryption key you generated in the Value field
4. Click **"Add Variable"**

### ALLOWED_HOSTS
1. Click **"+ Add Variable"**
2. Type `ALLOWED_HOSTS`
3. For now, paste: `*` (this means "allow all hosts" temporarily)
4. Click **"Add Variable"**

**Note:** Before going to production, you'll set ALLOWED_HOSTS to your actual domain (e.g., `myapp.railway.app` or your custom domain).

### AUTH_MODE
1. Click **"+ Add Variable"**
2. Type `AUTH_MODE`
3. Type `local` in the Value field (this uses username/password login; you can change to `azure` later for SSO)
4. Click **"Add Variable"**

### DATABASE_URL
This tells KoNote where to find the main database.

1. In the Railway dashboard, click on the **first PostgreSQL plugin** (it will have a name like `PostgreSQL` or `PostgreSQL_2`)
2. On the right side, look for a box with connection details — find the line that says **DATABASE_URL**
3. Click the **copy icon** (two overlapping squares) next to the DATABASE_URL value
4. Go back to the **main app** (click on the app name in the left panel, not the database)
5. Click **"+ Add Variable"**
6. Type `DATABASE_URL` in the Variable field
7. Paste the value in the Value field
8. Click **"Add Variable"**

### AUDIT_DATABASE_URL
This tells KoNote where to find the audit database.

1. In the Railway dashboard, click on the **second PostgreSQL plugin**
2. Find the **DATABASE_URL** value and copy it (same as above)
3. Go back to the **main app**
4. Click **"+ Add Variable"**
5. Type `AUDIT_DATABASE_URL` in the Variable field
6. Paste the database URL in the Value field
7. Click **"Add Variable"**

**You now have six variables set. You should see:**
- SECRET_KEY
- FIELD_ENCRYPTION_KEY
- ALLOWED_HOSTS
- AUTH_MODE
- DATABASE_URL
- AUDIT_DATABASE_URL

---

## Step 5: Deploy

1. In your Railway project, find the **main app** in the left panel
2. Look for the **"Deploy"** section at the top of the page
3. Click **"Redeploy"** (or if nothing is deployed yet, Railway will automatically start a fresh deployment)
4. Watch the **Build and Deploy logs** — they should appear on the right side

**What's happening:**
1. Railway builds the Docker image (2–3 minutes)
2. Runs database migrations (30 seconds)
3. Collects static files (JavaScript, CSS) (10 seconds)
4. Starts the web server

**When you're done:**
- You should see a green checkmark next to "Healthy"
- The **Logs** tab shows "Starting gunicorn on port..."

If deployment fails, see **Troubleshooting** below.

---

## Step 6: Verify the App Works

1. In your Railway project, look for a **"Domain"** section
2. You should see a URL like `KoNote-web-production-xxxx.up.railway.app`
3. Click it (or copy and paste into your browser)
4. You should see the **KoNote login page**

If you get an error page, check the **Logs** tab to see what went wrong.

---

## Step 7: Add a Custom Domain (Optional)

If you have your own domain (e.g., `outcomes.myorganisation.ca`), you can point it to Railway.

1. In your Railway project, find the **"Domain"** section
2. Click **"Add Custom Domain"**
3. Type your domain name (e.g., `outcomes.myorganisation.ca`)
4. Click **"Add Domain"**
5. Railway will give you instructions for your DNS provider (GoDaddy, Namecheap, Route53, etc.)
6. Follow those instructions to update your DNS records
7. It takes 5–30 minutes for the domain to start working

---

## Step 8: Set Up Azure AD SSO (Optional)

If your organisation uses Microsoft Azure AD (Office 365), users can sign in with their work credentials.

### Get Your App URL First

1. In Railway, find the **Domain** section
2. Copy the full URL (e.g., `https://outcomes.myorganisation.ca` or `https://KoNote-web-production-xxxx.up.railway.app`)

### Register Your App in Azure

1. Go to [portal.azure.com](https://portal.azure.com)
2. Click **"Azure Active Directory"** in the left menu
3. Click **"App registrations"**
4. Click **"New registration"**
5. Fill in:
   - **Name:** `KoNote Web` (or whatever you want)
   - **Supported account types:** "Accounts in this organizational directory only"
   - **Redirect URI:** Set to `Web` and paste: `https://your-app-url/auth/callback/` (replace `your-app-url` with your actual URL)
6. Click **"Register"**
7. On the next page, copy the **"Application (client) ID"** — save this

### Generate a Client Secret

1. In your app registration, click **"Certificates & secrets"** in the left menu
2. Click **"New client secret"**
3. Add a description (e.g., "Railway deployment")
4. Click **"Add"**
5. Immediately copy the **Value** (the long secret key) — you won't be able to see it again
6. Save it somewhere safe

### Get Your Tenant ID

1. Go back to **"Azure Active Directory"** (click the back arrow or left menu)
2. Click **"Properties"**
3. Copy the **"Tenant ID"** — save this

### Set Environment Variables in Railway

1. Go back to your Railway project
2. Click the **main app**
3. Click **"Variables"**
4. Click **"+ Add Variable"** and add:

| Variable | Value |
|----------|-------|
| `AUTH_MODE` | `azure` |
| `AZURE_CLIENT_ID` | Paste the Application ID |
| `AZURE_CLIENT_SECRET` | Paste the client secret value |
| `AZURE_TENANT_ID` | Paste the Tenant ID |
| `AZURE_REDIRECT_URI` | `https://your-app-url/auth/callback/` |

5. Click **"Redeploy"** to apply the changes

Users can now sign in with their work email address.

---

## Step 9: Monitoring and Logs

### View Logs

1. In your Railway project, click the **main app**
2. Click the **"Logs"** tab at the top
3. You'll see real-time output — errors, startup messages, HTTP requests

**Common log messages:**
- `"Starting gunicorn on port..."` — The app started successfully
- `"GET /auth/login/ 200 OK"` — A user loaded the login page
- `"ERROR: ..."` — Something went wrong

### Monitor Performance

1. Click the **"Metrics"** tab
2. You can see:
   - **CPU usage** — how hard the server is working
   - **Memory usage** — how much RAM it's using
   - **Network** — how much data is being sent/received

If the app is slow or crashing, look at these metrics.

### Set Up Restart Alerts (Optional)

If the app crashes, Railway will automatically restart it. To be notified:

1. Click **"Settings"** in your Railway project
2. Look for **"Notifications"**
3. Set up email or Slack notifications

---

## Troubleshooting

### Deployment Fails — "Build Error"

Check the **Logs** tab. Common causes:

**"ModuleNotFoundError: No module named..."**
- A Python package is missing from `requirements.txt`
- Solution: Add the package to requirements.txt, commit, and redeploy

**"ERROR: could not translate host name..."**
- The database URL is incorrect
- Solution: Copy DATABASE_URL directly from the PostgreSQL plugin (don't type it manually)

### App Starts But Won't Load — "502 Bad Gateway"

This usually means the app crashed shortly after starting.

1. Click **"Logs"**
2. Scroll up to see startup errors
3. Common causes:
   - Missing environment variables (check Variables tab)
   - Database migrations failed
   - SECRET_KEY or FIELD_ENCRYPTION_KEY invalid

### Login Page Loads But Can't Sign In

1. Check **Logs** for errors
2. Make sure `AUTH_MODE` is set correctly (`local` or `azure`)
3. If using Azure, verify AZURE_CLIENT_ID and AZURE_TENANT_ID are correct

### "ALLOWED_HOSTS Invalid" Error

1. Click **Variables**
2. Update ALLOWED_HOSTS to include your actual domain
3. Redeploy

Example: `myapp.railway.app,outcomes.myorganisation.ca`

---

## Scaling and Costs

**Starting price:** Railway's free plan gives you ~$5 worth of compute per month.

**For production use:**

1. Click **Settings** in your Railway project
2. Look for **"Plan"**
3. Upgrade to **"Pro"** (~$20/month for small organisations) to:
   - Remove usage limits
   - Get 24/7 uptime guarantee
   - Add multiple instances for higher traffic

**Database costs:**
- Each PostgreSQL database costs ~$10–15/month
- You have two databases (main + audit), so budget ~$25/month for databases

**Total estimated cost:** $45–50/month for a small organisation.

---

## Next Steps

### Back Up Your Data Regularly

1. Click the **PostgreSQL plugins** in your Railway project
2. In the Logs, find connection details
3. Use a PostgreSQL backup tool to download your data weekly

### Rotate Secrets Periodically

1. Every 90 days, regenerate SECRET_KEY and FIELD_ENCRYPTION_KEY
2. Update them in Railway Variables
3. Redeploy

### Monitor the Logs

1. Every week, check the **Logs** tab for errors
2. Look for "CRITICAL" or "ERROR" messages
3. Address them before they cause problems

### Document Your Setup

1. Keep a note of:
   - Your custom domain (if you have one)
   - Your Azure Tenant ID (if using SSO)
   - How many users you have
2. Update this file as you make changes

---

## Getting Help

- **Railway documentation:** [docs.railway.app](https://docs.railway.app)
- **Django documentation:** [docs.djangoproject.com](https://docs.djangoproject.com)
- **PostgreSQL documentation:** [postgresql.org/docs](https://www.postgresql.org/docs)

If something breaks, check the **Logs** first, then ask your development team.
