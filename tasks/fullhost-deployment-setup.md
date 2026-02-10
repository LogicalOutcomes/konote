# FullHost Deployment Setup (DEPLOY2)

Set up and test the FullHost one-click deployment for Canadian nonprofits.

## Background

FullHost is a Canadian-owned PaaS provider (based in Victoria, BC) with data centres in Montreal. This provides a Canadian data residency option for nonprofits who need to keep client data in Canada.

## Platform Details

- **Dashboard URL:** https://app.vap.fullhost.cloud/
- **Platform:** Jelastic/Virtuozzo Application Platform v.8.13.1
- **SSH Gateway:** gate.vap.fullhost.cloud (port 3022)
- **API Base URL:** https://app.vap.fullhost.cloud/1.0/

## Getting an API Token (For CLI/API Access)

If you want Claude Code to help deploy and manage environments via API:

1. Log in to https://app.vap.fullhost.cloud/
2. Click your **username/avatar** (top-right corner)
3. Go to **Settings** or **Account Settings**
4. Find **Access Tokens** or **API Tokens** section
5. Click **Generate** or **Create New Token**
6. Name it something like "Claude Code"
7. Copy the token value — you'll need this for API calls

**Alternative:** Authenticate via API using email + password (creates a 24-hour session):
```powershell
# Get a session token (Windows PowerShell)
$response = Invoke-RestMethod -Uri "https://app.vap.fullhost.cloud/1.0/users/authentication/rest/signin" -Method POST -Body @{login="your-email@example.com"; password="your-password"}
$session = $response.session
```

## Deployment Options

There are two ways to deploy KoNote to FullHost:

### Option A: JPS Manifest (One-Click Deploy)

Use the pre-built manifest for automated setup. See "Pre-Publication Checklist" below.

### Option B: Manual Deployment via API

Claude Code can deploy using the Jelastic REST API. This is useful for:
- Custom configurations
- Troubleshooting
- Updating existing environments

**Create a Docker environment with API:**
```powershell
# Example: Create KoNote environment
$body = @{
    session = "YOUR_SESSION_TOKEN"
    env = '{"shortdomain":"KoNote-prod","region":"default"}'
    nodes = '[{"nodeType":"docker","fixedCloudlets":4,"flexibleCloudlets":8,"docker":{"image":"ghcr.io/your-org/KoNote-web:latest"}}]'
}
Invoke-RestMethod -Uri "https://app.vap.fullhost.cloud/1.0/environment/control/rest/createenvironment" -Method POST -Body $body
```

**Set environment variables:**
```powershell
$body = @{
    session = "YOUR_SESSION_TOKEN"
    envName = "KoNote-prod"
    nodeId = "12345"  # Get from environment info
    vars = '{"DATABASE_URL":"postgres://...","SECRET_KEY":"..."}'
}
Invoke-RestMethod -Uri "https://app.vap.fullhost.cloud/1.0/environment/control/rest/addcontainerenvvars" -Method POST -Body $body
```

**Useful API endpoints:**
- `environment/control/rest/getenvs` — List all environments
- `environment/control/rest/startenv` — Start an environment
- `environment/control/rest/stopenv` — Stop an environment
- `environment/control/rest/getcontainerenvvars` — Get environment variables

**Files created:**
- `fullhost-manifest.jps` — JPS manifest for one-click deployment
- `docs/deploy-fullhost.md` — Step-by-step guide for non-technical users
- `docs/deploying-KoNote.md` — Updated with FullHost option
- `konote/wsgi.py` — Auto-detects FullHost environment
- `konote/settings/production.py` — Auto-allows FullHost domains

## Pre-Publication Checklist

### 1. Update GitHub Repository URL

The manifest currently references a placeholder repository. Update to the actual public repo.

**File:** `fullhost-manifest.jps`

```yaml
# Change this line:
baseUrl: https://raw.githubusercontent.com/konote/KoNote-web/main

# To your actual repository:
baseUrl: https://raw.githubusercontent.com/YOUR_ORG/KoNote-web/main
```

Also update the deploy button URLs in:
- `docs/deploying-KoNote.md` (line ~297)
- `docs/deploy-fullhost.md` (Step 2, Option A)

### 2. Create a FullHost Account

1. Go to [fullhost.com/cloud-paas](https://www.fullhost.com/cloud-paas/)
2. Click "Get Started" or "Try for Free"
3. Create an account (you'll receive $25 in free credits)

### 3. Test the JPS Manifest

**Option A: Direct URL Import**

1. Log in to [app.fullhost.cloud](https://app.fullhost.cloud)
2. Click **Import** in the top menu
3. Select the **URL** tab
4. Paste: `https://raw.githubusercontent.com/YOUR_ORG/KoNote-web/main/fullhost-manifest.jps`
5. Click **Import**

**Option B: File Upload**

1. Log in to FullHost dashboard
2. Click **Import** → **JPS** tab
3. Paste the contents of `fullhost-manifest.jps`
4. Click **Import**

### 4. Verify Deployment

After the manifest runs (~10 minutes):

- [ ] Application loads at the generated URL
- [ ] Login page appears
- [ ] Admin credentials work (email/password you entered)
- [ ] Can create a test client
- [ ] Can create a test note
- [ ] Audit log records the actions
- [ ] Environment variables are set correctly (check via SSH if needed)

### 5. Verify Environment Detection

Check that KoNote auto-detected FullHost:

1. In FullHost, click on the app container
2. Click **Web SSH** or **Terminal**
3. Run:
   ```bash
   cd /var/www/webroot/ROOT
   python manage.py shell -c "from django.conf import settings; print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)"
   ```
4. Confirm `.fullhost.cloud` is in the allowed hosts

### 6. Test the Deploy Button

Once the manifest works via direct import, test the deploy button:

1. Create a test markdown file with the button:
   ```markdown
   [![Deploy to FullHost](https://www.fullhost.com/deploy-button.svg)](https://app.fullhost.cloud/install?manifest=https://raw.githubusercontent.com/YOUR_ORG/KoNote-web/main/fullhost-manifest.jps)
   ```
2. Click the button
3. Verify it opens the FullHost installer with the KoNote manifest pre-loaded

### 7. Document Any Issues

If the manifest needs changes, update:
- `fullhost-manifest.jps`
- `docs/deploy-fullhost.md` (if steps change)
- This task file (lessons learned)

### 8. Clean Up Test Environment

After testing:
1. In FullHost, go to your test environment
2. Click **Settings** (gear icon)
3. Click **Delete Environment**
4. Confirm deletion

This stops billing for the test instance.

## Platform Limitations (Discovered 2026-02-04)

Testing via API revealed these constraints:

### What Does NOT Work

1. **Native Python node type** — FullHost returns "node type [python] currently not supported"
2. **Debian-based Docker images** — Returns "OS debian:13 not supported" (even for postgres:15, postgres:16)
3. **The existing JPS manifest** — Uses native `python` and `postgresql` nodes which aren't available

### What DOES Work

1. **Alpine-based Docker images** — `postgres:15-alpine` deploys successfully
2. **Docker containers in general** — Using `nodeType: docker` works
3. **API access** — Token with `environment/control` + `environment/deployment` permissions works

### Required Changes for FullHost Deployment

The JPS manifest has been rewritten to use Docker containers:

1. **Alpine-based Dockerfile created** — `Dockerfile.alpine` packages Python 3.12 + Django on Alpine Linux
2. **GitHub Actions workflow created** — `.github/workflows/docker-fullhost.yml` builds and pushes to ghcr.io
3. **JPS manifest updated** to use:
   - `nodeType: docker` with `docker.image: ghcr.io/gilliankerr/konote-redux:fullhost-latest`
   - `postgres:15-alpine` instead of native PostgreSQL
4. **PowerShell deployment script created** — `deploy-fullhost.ps1` for API-based deployment

### Implementation Status (2026-02-04)

The following files have been created/updated:

| File | Purpose |
|------|---------|
| `Dockerfile.alpine` | Alpine-based image for FullHost compatibility |
| `.github/workflows/docker-fullhost.yml` | GitHub Actions to build and push to ghcr.io |
| `fullhost-manifest.jps` | Rewritten for Docker containers |
| `deploy-fullhost.ps1` | PowerShell script for API deployment |
| `docs/deploy-fullhost.md` | Updated URLs to correct repository |

### Deployment Test Results (2026-02-06)

**Status: SUCCESSFUL** — App deploys, migrations run, login works.

**Test environment:** `konote-full.ca-east.onfullhost.cloud`

**What worked:**
- Docker image pulls from ghcr.io (public package)
- Both PostgreSQL databases initialise correctly
- Migrations run on both app and audit databases
- Audit database lockdown runs successfully
- Seed data loads (metrics, features, settings, templates)
- Security checks pass (all 6 checks)
- Login works, all pages load (Home, Clients, Programs, Admin)

**Bugs found and fixed:**
1. **Wrong repo name** — Manifest/script referenced `KoNote-Redux` (doesn't exist), fixed to `KoNote-Redux`
2. **ALLOWED_HOSTS missing 127.0.0.1** — FullHost health checks use `127.0.0.1:8000`, causing 400 errors. Fixed by adding `127.0.0.1,localhost` to ALLOWED_HOSTS
3. **Admin user creation crashes** — `User.objects.filter(email=...)` fails because email is encrypted. Fixed to use `filter(is_superuser=True)` and `create_superuser(username='admin', ...)`
4. **Startup wait too short** — 30 seconds wasn't enough for migrations + seed. Increased to 60 seconds

**Known limitations:**
- **SSL requires manual dashboard config** — Let's Encrypt addon fails (`tinyproxy` not in Alpine image). Users must enable Built-in SSL from Settings → Custom SSL → click yellow link
- **Login requires HTTPS** — Production settings enforce `CSRF_COOKIE_SECURE=True`. Login returns 403 over HTTP
- **API token can't delete environments** — Requires account password (safety feature). Delete from dashboard
- **API token can't bind SSL** — Requires `environment.Binder` permission not available in standard tokens

5. **HTTPS fix: Remove external IP from app container** — If the app node has a public/external IP, DNS resolves directly to the container (bypassing the SLB). Since the container has no SSL termination (only gunicorn on port 8000), HTTPS fails with "connection refused". Fix: detach the external IP via API (`detachextip`) or dashboard. Without it, DNS resolves to the SLB IPs which terminate SSL. Verified working 2026-02-06.

### Old Test Environments (Cleaned Up)

- `konote-test2` — Deleted from dashboard (was just a lone PostgreSQL)

### API Token Permissions Needed

When creating an API token, check these under **API Access**:
- `environment` → `control` (required)
- `environment` → `deployment` (required)
- `environment` → `export` (optional, for backups)
- `marketplace` → `installation` (optional, for JPS)
- `marketplace` → `jps` (optional, for JPS)

## Known Considerations

### Environment Variable: JELASTIC_ENVIRONMENT

The code assumes FullHost sets `JELASTIC_ENVIRONMENT`. If they use a different variable name, update:
- `konote/wsgi.py` (line ~35)
- `konote/settings/production.py` (line ~52)

### Database Initialisation

The JPS manifest creates two PostgreSQL databases but doesn't run the audit lockdown script. After deployment, agencies should run:

```bash
python manage.py lockdown_audit_db
```

Consider adding this to the `onInstall` actions in the manifest if it can run after migrations.

### Encryption Key Display

The manifest displays the encryption key in the success message. Verify this actually appears and is copyable. If not, consider alternative ways to surface this critical information.

### Custom Domain SSL

The manifest sets `ssl: true` which should enable automatic SSL. Verify this works with FullHost's default domain before documenting custom domain setup.

## Cost Estimate Verification

After running for a few days, compare actual FullHost charges against the documented estimate (~$23 CAD/month). Update `docs/deploy-fullhost.md` if significantly different.

## Publication Steps

Once testing is complete:

1. [ ] Update repository URL in manifest and docs
2. [ ] Commit all changes
3. [ ] Push to main branch
4. [ ] Test deploy button one more time from live repo
5. [ ] Mark this task complete in TODO.md

## Related Files

- [fullhost-manifest.jps](../fullhost-manifest.jps)
- [docs/deploy-fullhost.md](../docs/deploy-fullhost.md)
- [docs/deploying-KoNote.md](../docs/deploying-KoNote.md)
- [konote/wsgi.py](../konote/wsgi.py)
- [konote/settings/production.py](../konote/settings/production.py)
