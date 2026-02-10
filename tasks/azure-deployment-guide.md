# Deploying KoNote on Azure (Canada)

Step-by-step guide to hosting KoNote on Microsoft Azure in a Canadian data centre. No command line required — everything is done through the Azure portal.

## Why Azure?

- **Canadian data residency** — host in Toronto (Canada Central) or Quebec City (Canada East)
- **Integrated with Azure AD** — your existing authentication setup works seamlessly
- **Managed services** — Microsoft handles server maintenance, security patches, backups
- **PIPEDA alignment** — data stays in Canada, simplifies compliance conversations

## What You'll Need

Before starting, gather these:

- [ ] An **Azure account** with permission to create resources (ask your IT admin if unsure)
- [ ] Your **Azure AD tenant ID** (you already have this from SSO setup)
- [ ] Your **FIELD_ENCRYPTION_KEY** (from your current deployment)
- [ ] About **1 hour** for initial setup
- [ ] A **credit card** for Azure billing (or an existing Azure subscription)

## Cost Estimate

| Resource | Size | Monthly Cost (CAD) |
|----------|------|-------------------|
| App Service (Linux) | B1 (Basic) | ~$17 |
| PostgreSQL Flexible Server | Burstable B1ms | ~$20 |
| PostgreSQL (audit database) | Burstable B1ms | ~$20 |
| Storage (backups) | 10 GB | ~$1 |
| **Total** | | **~$58/month** |

You can start smaller for testing, or scale up for larger agencies.

---

## Step 1: Create a Resource Group

A resource group is a folder that holds all your Azure resources together.

1. Go to [portal.azure.com](https://portal.azure.com)
2. Click **"Create a resource"** (top left, or search bar)
3. Search for **"Resource group"** and click **Create**
4. Fill in:
   - **Subscription**: Select your subscription
   - **Resource group name**: `KoNote-production` (or your agency name)
   - **Region**: `Canada Central` (Toronto) or `Canada East` (Quebec)
5. Click **Review + create**, then **Create**

**What just happened?** You created a container to hold all the KoNote components. Everything we create next goes in this folder.

---

## Step 2: Create the Main Database

KoNote needs a PostgreSQL database for client and note data.

1. In the Azure portal search bar, type **"Azure Database for PostgreSQL"**
2. Click **Create** → Select **Flexible server**
3. Fill in the **Basics** tab:
   - **Resource group**: Select `KoNote-production`
   - **Server name**: `KoNote-db` (must be globally unique — add your agency initials if taken)
   - **Region**: `Canada Central` (same as your resource group)
   - **PostgreSQL version**: `16`
   - **Workload type**: `Development` (can upgrade later)
   - **Compute + storage**: Click **Configure server**
     - Select **Burstable** → **B1ms** (1 vCore, 2 GB RAM)
     - Storage: **32 GB** (minimum)
     - Click **Save**
   - **Authentication method**: `PostgreSQL authentication only`
   - **Admin username**: `konoteadmin`
   - **Password**: Create a strong password and **save it somewhere safe**
4. Click **Next: Networking**
5. Under **Firewall rules**:
   - Select **"Allow public access from any Azure service within Azure"**
   - (We'll restrict this further after setup)
6. Click **Review + create**, then **Create**

**Wait 5-10 minutes** for the database to deploy.

**What just happened?** You created a managed PostgreSQL database server in Canada. Azure handles backups, updates, and security patches automatically.

---

## Step 3: Create the Audit Database

KoNote uses a separate database for audit logs (security best practice).

1. Once your database server is created, go to it in the portal
2. In the left menu, click **Databases**
3. Click **+ Add**
4. Name: `konote_audit`
5. Click **Save**

Also create the main application database:

1. Click **+ Add** again
2. Name: `KoNote`
3. Click **Save**

**What just happened?** You created two databases on your server — one for application data, one for audit logs. They're isolated from each other for security.

---

## Step 4: Create the App Service

The App Service runs your KoNote application.

1. In the Azure portal search bar, type **"App Services"**
2. Click **Create** → **Web App**
3. Fill in the **Basics** tab:
   - **Resource group**: Select `KoNote-production`
   - **Name**: `KoNote-app` (this becomes your URL: `KoNote-app.azurewebsites.net`)
   - **Publish**: `Docker Container`
   - **Operating System**: `Linux`
   - **Region**: `Canada Central`
   - **Pricing plan**: Click **Create new**
     - Name: `KoNote-plan`
     - **Sku and size**: Click **Change size** → Select **B1** (Basic) → Click **Apply**
4. Click **Next: Database** → Skip (we already created it)
5. Click **Next: Docker**
   - **Options**: `Single Container`
   - **Image Source**: `Docker Hub`
   - **Access Type**: `Public`
   - **Image and tag**: For now, enter `nginx:latest` (we'll change this later)
6. Click **Review + create**, then **Create**

**Wait 2-3 minutes** for the App Service to deploy.

**What just happened?** You created a web server that will run KoNote. It's currently running a placeholder — we'll connect your actual application next.

---

## Step 5: Configure Environment Variables

KoNote needs configuration values to connect to the database and encrypt data.

1. Go to your App Service (`KoNote-app`)
2. In the left menu, click **Configuration** (under Settings)
3. Click **+ New application setting** for each of these:

| Name | Value |
|------|-------|
| `DATABASE_URL` | `postgres://konoteadmin:YOUR_PASSWORD@konote-db.postgres.database.azure.com:5432/konote?sslmode=require` |
| `AUDIT_DATABASE_URL` | `postgres://konoteadmin:YOUR_PASSWORD@konote-db.postgres.database.azure.com:5432/konote_audit?sslmode=require` |
| `SECRET_KEY` | Generate a new one: 50+ random characters |
| `FIELD_ENCRYPTION_KEY` | Your existing encryption key (CRITICAL: use the same one!) |
| `ALLOWED_HOSTS` | `KoNote-app.azurewebsites.net` |
| `AUTH_MODE` | `azure` |
| `AZURE_CLIENT_ID` | Your existing Azure AD client ID |
| `AZURE_CLIENT_SECRET` | Your existing Azure AD client secret |
| `AZURE_TENANT_ID` | Your Azure AD tenant ID |
| `AZURE_REDIRECT_URI` | `https://KoNote-app.azurewebsites.net/auth/callback/` |
| `DEBUG` | `False` |

4. Click **Save** at the top
5. Click **Continue** when prompted to restart

**CRITICAL:** Use your existing `FIELD_ENCRYPTION_KEY` if you're migrating data. If you use a different key, existing encrypted data becomes unreadable.

**What just happened?** You told KoNote how to connect to the database, encrypt data, and authenticate users. These values are stored securely — they're not visible in your code.

---

## Step 6: Update Azure AD Redirect URI

Your Azure AD app needs to know about the new URL.

1. Go to [Azure Active Directory](https://portal.azure.com/#blade/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/Overview)
2. Click **App registrations** in the left menu
3. Find and click your KoNote app registration
4. Click **Authentication** in the left menu
5. Under **Redirect URIs**, click **Add URI**
6. Add: `https://KoNote-app.azurewebsites.net/auth/callback/`
7. Click **Save**

**What just happened?** You told Azure AD that it's okay to redirect users back to your new Azure-hosted URL after they sign in.

---

## Step 7: Deploy from GitHub

Connect your GitHub repository for automatic deployments.

1. Go to your App Service (`KoNote-app`)
2. In the left menu, click **Deployment Center**
3. Under **Source**, select **GitHub**
4. Click **Authorize** and sign in to GitHub
5. Select:
   - **Organization**: Your GitHub account
   - **Repository**: `KoNote-web`
   - **Branch**: `main`
6. Under **Build provider**, select **GitHub Actions**
7. Click **Save**

Azure will create a GitHub Actions workflow file in your repository. The first deployment will start automatically.

**Wait 5-10 minutes** for the build and deployment to complete.

**What just happened?** Azure set up automatic deployments. Every time you push to the `main` branch, Azure will automatically update your live application.

---

## Step 8: Run Database Migrations

After the first deployment, you need to set up the database tables.

1. Go to your App Service (`KoNote-app`)
2. In the left menu, click **SSH** (under Development Tools)
3. Click **Go →** to open a terminal
4. Run these commands:

```bash
cd /home/site/wwwroot
python manage.py migrate --database=default
python manage.py migrate --database=audit
```

You should see output like:
```
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth_app.0001_initial... OK
  ...
```

**What just happened?** You created all the database tables KoNote needs. This only needs to be done once (or when you upgrade to a new version with database changes).

---

## Step 9: Create Your First Admin User

1. Still in the SSH terminal, run:

```bash
python manage.py createsuperuser
```

2. Enter a username, display name, and password when prompted

**What just happened?** You created an administrator account that can configure KoNote settings.

---

## Step 10: Test Your Deployment

1. Open your browser and go to: `https://KoNote-app.azurewebsites.net`
2. You should see the KoNote login page
3. Click **Sign in with Microsoft** (or use your local admin account)
4. Verify you can access the dashboard

**Congratulations!** KoNote is now running on Azure in Canada.

---

## Post-Setup Security Checklist

After confirming everything works:

- [ ] **Restrict database firewall** — In your PostgreSQL server settings, remove public access and add only your App Service's outbound IPs
- [ ] **Enable Azure Defender** — Go to Microsoft Defender for Cloud and enable database protection
- [ ] **Set up backup alerts** — In PostgreSQL settings, verify automated backups are enabled (they should be by default)
- [ ] **Configure custom domain** (optional) — Add your own domain like `KoNote.youragency.ca`
- [ ] **Enable HTTPS only** — In App Service → Configuration → General settings, set "HTTPS Only" to On

---

## Migrating Data from Railway

If you have existing data on Railway:

1. **Export from Railway:**
   - Use `pg_dump` to export your database (Railway provides connection details)
   - Export both the main database and audit database

2. **Import to Azure:**
   - Use the Azure Cloud Shell or a local PostgreSQL client
   - Connect to your Azure PostgreSQL server
   - Use `pg_restore` to import the data

3. **Verify encryption key:**
   - You MUST use the same `FIELD_ENCRYPTION_KEY`
   - Test that you can view existing client names after migration

Detailed migration steps depend on your Railway setup — ask for help when you're ready to migrate.

---

## Troubleshooting

### "Application Error" on first load
- Check **Log stream** in App Service (left menu) for error details
- Usually a missing environment variable or database connection issue

### "Invalid redirect URI" on login
- Verify the redirect URI in Azure AD matches exactly: `https://KoNote-app.azurewebsites.net/auth/callback/`
- Check for trailing slashes — they matter!

### Database connection errors
- Verify the DATABASE_URL has the correct password
- Check that SSL mode is set to `require`
- Ensure the App Service can reach the database (firewall rules)

### Encrypted data shows "[decryption error]"
- You're using a different FIELD_ENCRYPTION_KEY than the one used to encrypt the data
- This is not recoverable without the original key

---

## Support

- **Azure documentation**: [docs.microsoft.com/azure](https://docs.microsoft.com/azure)
- **KoNote issues**: Check `tasks/` folder or create an issue on GitHub
- **Azure support**: Available through your Azure subscription (paid plans include support)
