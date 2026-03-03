# Updating and Rolling Back KoNote

This guide covers how to safely update your KoNote instance to a new version, verify the update worked, and roll back if something goes wrong.

**Applies to:** OVHcloud VPS (Docker Compose), any self-hosted Docker deployment

For Railway or Azure, see the platform-specific sections in [Deploying KoNote](deploying-konote.md).

---

## Before You Update

Every update should follow three steps: **back up → update → verify**. Don't skip the backup — it's your safety net.

### 1. Back Up Both Databases

```bash
# Run the backup script (creates timestamped compressed dumps)
sudo /opt/konote/scripts/backup-vps.sh

# Verify the backups were created
ls -lh /opt/konote/backups/
```

You should see two new `.sql.gz` files (one for the main database, one for the audit database).

### 2. Record the Current Version

```bash
cd /opt/konote
sudo git log --oneline -1
```

Write down or copy the commit hash (the short code at the start of the line, e.g., `a1b2c3d`). You'll need this if you have to roll back.

### 3. Check Container Health

```bash
sudo docker compose ps
```

All containers should show "healthy" or "running" before you proceed. If something is already broken, fix it before updating.

---

## Applying the Update

### Standard Update (Under 2 Minutes Downtime)

```bash
cd /opt/konote

# Pull the latest code
sudo git pull origin main

# Rebuild containers and restart
sudo docker compose up -d --build
```

The entrypoint script runs database migrations automatically during startup. Typical downtime is 1–2 minutes while the new container builds and starts.

### What Happens During the Update

1. `git pull` downloads new code (files change, but the running app is unaffected)
2. `docker compose up -d --build` rebuilds the Docker image and replaces the running container
3. The new container starts and runs `entrypoint.sh`, which:
   - Applies any pending database migrations
   - Runs seed data updates (new metrics, templates, etc.)
   - Runs startup security checks
   - Starts the web server

### When to Update

| Situation | Recommendation |
|-----------|---------------|
| **During business hours** | OK for minor updates (no database migrations). Check the release notes first. |
| **After hours** | Recommended for updates with database migrations. Staff won't notice 2 minutes of downtime. |
| **Emergency fix** | Update immediately regardless of time — security patches shouldn't wait. |

---

## Verifying the Update

After `docker compose up -d --build` completes:

### 1. Check Container Health

```bash
sudo docker compose ps
```

All containers should show "healthy" within 60 seconds. If the web container keeps restarting, check the logs.

### 2. Check the Logs

```bash
sudo docker compose logs --tail 30 web
```

Look for:
- `Starting gunicorn on port 8000` — app started successfully
- `Applied X migration(s)` — database changes were applied
- No `ERROR` or `CRITICAL` messages

### 3. Test the Application

1. Visit your KoNote URL — the login page should load
2. Log in with your admin account
3. Check a few pages: dashboard, a client profile, a report
4. If you have a dev/demo instance, update that too and test there first

### 4. Confirm the Version

```bash
cd /opt/konote
sudo git log --oneline -1
```

The commit hash should match the latest release.

---

## Rolling Back

If the update breaks your instance, you have two options depending on the severity.

### Option A: Code-Only Rollback (No Database Changes)

Use this when the update didn't include database migrations, or the migrations haven't run yet (container failed to start).

```bash
cd /opt/konote

# Revert to the previous commit
sudo git checkout <OLD_COMMIT_HASH> -- .
# Replace <OLD_COMMIT_HASH> with the hash you recorded before updating

# Rebuild with the old code
sudo docker compose up -d --build
```

### Option B: Full Rollback (Code + Database)

Use this when the update ran database migrations and those migrations caused problems (missing data, broken queries, etc.).

```bash
cd /opt/konote

# Step 1: Stop the web container (keep databases running)
sudo docker compose stop web

# Step 2: Restore the main database from backup
gunzip -c /opt/konote/backups/main_YYYY-MM-DD_0200.sql.gz | \
  sudo docker compose exec -T db psql -U konote konote
# Replace the filename with your actual backup file

# Step 3: Restore the audit database from backup
gunzip -c /opt/konote/backups/audit_YYYY-MM-DD_0200.sql.gz | \
  sudo docker compose exec -T audit_db psql -U audit_writer konote_audit

# Step 4: Revert the code
sudo git checkout <OLD_COMMIT_HASH> -- .

# Step 5: Rebuild and restart
sudo docker compose up -d --build
```

> **Warning:** A full rollback restores the database to the point of the backup. Any data entered between the backup and the rollback will be lost. This is why we recommend updating after hours — less data at risk.

### After Rolling Back

1. Verify the app is working (follow the verification steps above)
2. Report the issue — note what went wrong, which version caused it, and any error messages from `docker compose logs web`
3. Wait for a fix before trying the update again

---

## Updating the Dev Instance

If you're running a dev/demo instance alongside production (see [deploy-ovhcloud.md Section 14](deploy-ovhcloud.md#14-run-a-second-instance-devdemo)):

**Update dev first, test, then update production:**

```bash
# Update dev
cd /opt/konote-dev
sudo git pull origin main
sudo docker compose up -d --build

# Test dev instance thoroughly
# If everything looks good, update production:
cd /opt/konote
sudo git pull origin main
sudo docker compose up -d --build
```

This gives you a safe testing environment before touching production data.

---

## Railway Updates

Railway auto-deploys from GitHub when you merge to `main`. To roll back:

1. Go to your Railway project → **Deployments**
2. Find the last working deployment
3. Click the three dots (⋯) → **Rollback**
4. Railway redeploys the previous image

If the failed deployment ran database migrations, you may need to restore from a backup. Use the Railway CLI:

```bash
# Download the backup from Railway
railway run pg_dump $DATABASE_URL > rollback_main.sql

# Contact Railway support for point-in-time recovery (Pro plan)
```

## Azure Updates

Azure Container Apps auto-deploys when the CI/CD pipeline pushes a new image. To roll back:

```bash
# Redeploy the previous image (using a specific git commit SHA)
az containerapp update \
  --name konote-web \
  --resource-group KoNote-prod \
  --image konoteregistry.azurecr.io/konote:<previous-git-sha>
```

The CI/CD pipeline tags each image with its git commit SHA, so you can always point back to a known-good version.

For database restore, use Azure Portal → PostgreSQL server → **Point-in-time restore** (available within your retention window).

---

## Quick Reference

| Task | Command |
|------|---------|
| Back up before update | `sudo /opt/konote/scripts/backup-vps.sh` |
| Record current version | `cd /opt/konote && sudo git log --oneline -1` |
| Apply update | `cd /opt/konote && sudo git pull origin main && sudo docker compose up -d --build` |
| Check container health | `sudo docker compose ps` |
| Check logs | `sudo docker compose logs --tail 30 web` |
| Roll back code only | `sudo git checkout <hash> -- . && sudo docker compose up -d --build` |
| Roll back code + database | Stop web → restore backups → checkout old code → rebuild |
