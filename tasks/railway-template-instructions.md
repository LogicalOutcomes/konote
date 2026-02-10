# Railway Template Creation Instructions (DEPLOY1)

## Problem

The current Railway deployment requires users to manually add two PostgreSQL databases and configure environment variables. This leads to:

- Orphaned databases (users create extras by mistake)
- Misconfigured variable references
- Confusion about which database is which

## Solution

Create a Railway Template that provisions everything automatically:

- KoNote app service
- KoNote-DB (main database)
- KoNote-Audit-DB (audit database)
- Pre-wired environment variable references

Users click one button, enter two secrets, done.

## Why Two Databases?

The separate audit database provides:

1. **Tamper resistance** — if main database credentials are compromised, audit logs remain protected
2. **Separate retention** — audit logs can be kept longer than operational data
3. **Compliance** — PIPEDA and similar regulations value demonstrable audit trail integrity

The docker-compose.yml already implements this correctly. Railway needs to match it.

## Steps to Create the Template

### Step 1: Create a fresh Railway project

1. Go to [railway.app](https://railway.app) → **New Project** → **Empty Project**
2. Name it something like "KoNote Template Source"

### Step 2: Add the three services

**Add the app:**

1. Click **+ Add** → **GitHub Repo** → select `KoNote-web`
2. Click on the service → **Settings** → rename to `KoNote`

**Add main database:**

1. Click **+ Add** → **Database** → **PostgreSQL**
2. Click on it → **Settings** → rename to `KoNote-DB`

**Add audit database:**

1. Click **+ Add** → **Database** → **PostgreSQL**
2. Click on it → **Settings** → rename to `KoNote-Audit-DB`

### Step 3: Configure environment variables

Click on **KoNote** service → **Variables** → add these:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `${{KoNote-DB.DATABASE_URL}}` |
| `AUDIT_DATABASE_URL` | `${{KoNote-Audit-DB.DATABASE_URL}}` |
| `SECRET_KEY` | _(leave blank — user provides at deploy time)_ |
| `FIELD_ENCRYPTION_KEY` | _(leave blank — user provides at deploy time)_ |
| `DJANGO_SETTINGS_MODULE` | `konote.settings.production` |

### Step 4: Test the deployment

1. Temporarily add test values for `SECRET_KEY` and `FIELD_ENCRYPTION_KEY`
2. Verify the app deploys and connects to both databases
3. Check the health endpoint works
4. Remove the test secrets before publishing

### Step 5: Publish as template

1. Click project name (top left) → **Settings** → **General**
2. Scroll to **Publish as Template**
3. Fill in:
   - **Name:** KoNote Participant Outcome Management
   - **Description:** Secure client outcome tracking for nonprofits. Includes app + main database + separate audit database for compliance.
   - **Icon:** Choose something appropriate
4. Mark `SECRET_KEY` and `FIELD_ENCRYPTION_KEY` as **required user input**
5. Add helpful descriptions for each required variable
6. Click **Publish**

### Step 6: Get the deploy button

After publishing, Railway provides:

1. A template URL (e.g., `https://railway.app/template/xxxxx`)
2. A deploy button you can add to the README:

```markdown
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/xxxxx)
```

## After Template is Created

Update `docs/deploying-KoNote.md` to replace the manual steps with:

```markdown
### Deploy to Railway (Recommended)

1. Click the Deploy button below
2. Enter your `SECRET_KEY` and `FIELD_ENCRYPTION_KEY` when prompted
3. Click **Deploy**

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/xxxxx)

That's it. Railway creates your app and both databases automatically.
```

## References

- [Railway Database Reference Variables](https://blog.railway.com/p/database-reference-variables)
- [Railway Variables Documentation](https://docs.railway.com/guides/variables)
- [Railway Templates Guide](https://docs.railway.com/guides/templates)
