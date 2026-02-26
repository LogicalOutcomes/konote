# Backup and Restore Runbook

**Last updated:** February 2026 | **Applies to:** KoNote v1.x

This document tells you everything you need to back up, restore, and recover KoNote data. It is written for nonprofit staff and IT consultants — you do not need to be a developer to follow these steps.

---

## Quick Reference

| Task | Where to Find It |
|------|-------------------|
| Back up Azure databases | [Azure Automated Backups](#1-azure-automated-backups) |
| Back up Docker Compose databases | [Docker Compose Backup](#docker-compose-backup-commands) |
| Restore from Azure point-in-time | [Point-in-Time Restore](#point-in-time-restore-pitr) |
| Restore from a dump file | [Restore from Dump File](#restore-from-a-dump-file) |
| Back up the encryption key | [Encryption Key Management](#5-encryption-key-management) |
| Test a restore | [Testing Schedule](#6-testing-schedule) |
| Handle a disaster scenario | [Disaster Recovery Scenarios](#7-disaster-recovery-scenarios) |

---

## 1. Overview

### What Gets Backed Up

KoNote stores data in three places. **All three must be backed up** for a complete recovery:

| Component | What It Contains | How Critical |
|-----------|-----------------|--------------|
| **Main database** (`konote`) | Users, clients, programs, plans, notes, settings | Critical — this is all your program data |
| **Audit database** (`konote_audit`) | Append-only log of every data change | Critical — required for compliance |
| **Encryption key** (`FIELD_ENCRYPTION_KEY`) | The key that encrypts client names, birth dates, and clinical notes | **Catastrophically critical** — without it, encrypted data is permanently unrecoverable |

You also need your **environment configuration** (`.env` file, or environment variables in Railway/Azure) to redeploy.

### What Happens If You Lose the Encryption Key

**All encrypted client data becomes permanently unrecoverable.** There is no backdoor, no master key, no way to contact a vendor to get it back. This is by design — it protects client privacy — but it means you must treat the encryption key as seriously as you treat the data itself.

Encrypted fields include: client first/last/middle/preferred names, birth dates, email addresses, progress note content, participant reflections, and sensitive custom field values.

Unencrypted data (program names, metric scores, dates, settings) would still be accessible, but all personally identifiable information (PII) would be lost.

### Recovery Time and Recovery Point Objectives

These are recommendations for a typical nonprofit deployment:

| Metric | Recommendation | What It Means |
|--------|---------------|---------------|
| **RPO** (Recovery Point Objective) | 24 hours or less | You can afford to lose at most one day of data entry |
| **RTO** (Recovery Time Objective) | 4 hours | After a failure, you should be back online within 4 hours |

**How to achieve these targets:**
- **RPO of 24 hours:** Run daily automated backups (Azure does this automatically; Docker Compose needs a scheduled task)
- **RPO of 5 minutes (Azure only):** Use point-in-time restore, which captures changes continuously
- **RTO of 4 hours:** Keep your deployment scripts, environment variables, and encryption key readily accessible — not locked away where you can't find them in a crisis

---

## 2. Azure-Specific Procedures

If you are running KoNote on **Azure Container Apps** with **Azure Database for PostgreSQL Flexible Server**, Azure handles most backup work for you automatically.

### Azure Automated Backups

Azure Database for PostgreSQL Flexible Server automatically takes backups:

- **Full backup:** Once per week
- **Differential backup:** Twice per day
- **Transaction log backup:** Every 5 minutes
- **Default retention:** 7 days
- **Maximum retention:** 35 days
- **Storage:** Geo-redundant (copied to a second Azure region) if you enable it

You do not need to set up a cron job or scheduled task — this happens automatically from the moment the database is created.

#### How to Check That Backups Are Running

1. Sign in to the [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Database for PostgreSQL flexible servers**
3. Select your KoNote server (e.g., `konote-db`)
4. In the left menu, click **Backup and restore**
5. You should see a list of available restore points — if you see them, backups are working

#### How to Configure the Retention Period

The default retention is 7 days. For most nonprofits, **14 days** provides a good safety margin at minimal extra cost.

**Using the Azure Portal:**

1. Navigate to your PostgreSQL Flexible Server in the Azure Portal
2. In the left menu, click **Backup and restore**
3. Click **Backup settings** (or **Server parameters** depending on your portal version)
4. Change **Backup retention period (days)** to your desired value (7–35)
5. Click **Save**

**Using the Azure CLI:**

```powershell
az postgres flexible-server update `
    --resource-group your-resource-group `
    --name your-server-name `
    --backup-retention 14
```

#### How to Enable Geo-Redundant Backup

Geo-redundant backup copies your data to a second Azure region. If the entire Canada Central region goes down, your backup is safe in another region. This costs extra but is recommended for production.

**Note:** Geo-redundancy can only be set when the server is first created. If your server was created without it, you would need to create a new server and migrate data.

```powershell
# When creating a new server (cannot be changed later)
az postgres flexible-server create `
    --resource-group your-resource-group `
    --name your-server-name `
    --location canadacentral `
    --geo-redundant-backup Enabled `
    --backup-retention 14
```

### Point-in-Time Restore (PITR)

Point-in-time restore lets you restore your database to any moment within the retention period — down to the minute. This is the fastest way to recover from accidental data deletion or corruption.

**When to use PITR:**
- Someone accidentally deleted a batch of client records
- A bad data import corrupted records
- You want to see what the data looked like at a specific moment

#### PITR Using the Azure Portal

1. Sign in to the [Azure Portal](https://portal.azure.com)
2. Navigate to your PostgreSQL Flexible Server
3. In the left menu, click **Backup and restore**
4. Click **Restore**
5. Set the **Restore point** — pick a date and time just *before* the problem occurred
6. Under **Server name**, enter a new name (e.g., `konote-db-restored-20260226`)
   - Azure creates a *new* server — it does not overwrite the existing one
7. Choose the same **Resource group** and **Location** as your original server
8. Click **Review + create**, then **Create**
9. Wait for the new server to be provisioned (usually 15–30 minutes)

After the restore completes:
- Update your Container App's environment variables to point to the new database server
- Or migrate data from the restored server back to your original server

#### PITR Using the Azure CLI

```powershell
# Restore the main database server to a point in time
az postgres flexible-server restore `
    --resource-group your-resource-group `
    --name konote-db-restored `
    --source-server your-server-name `
    --restore-time "2026-02-25T14:30:00Z"

# Restore the audit database server (if separate)
az postgres flexible-server restore `
    --resource-group your-resource-group `
    --name konote-audit-restored `
    --source-server your-audit-server-name `
    --restore-time "2026-02-25T14:30:00Z"
```

**Notes:**
- The `--restore-time` is in UTC. Convert your local time to UTC first. (Eastern Standard Time is UTC−5; Eastern Daylight Time is UTC−4.)
- The restored server is a completely new server with a new connection string.
- You need to update firewall rules and connection strings after the restore.

**After restoring, remember to:**
1. Update your app's `DATABASE_URL` (and/or `AUDIT_DATABASE_URL`) to point to the restored server
2. Re-run audit lockdown: `python manage.py lockdown_audit_db`
3. Test the application to confirm it works

### Manual/On-Demand Backups (pg_dump Against Azure)

Sometimes you want a downloadable backup file — for example, before a major upgrade, or to keep a long-term archive beyond Azure's 35-day retention limit.

#### Connection String Format for Azure PostgreSQL

```
postgresql://<username>:<password>@<server-name>.postgres.database.azure.com:5432/<database-name>?sslmode=require
```

Example:

```
postgresql://konote_admin:YourPassword123@konote-db.postgres.database.azure.com:5432/konote?sslmode=require
```

#### Back Up Using pg_dump

You need `pg_dump` installed locally. It comes with PostgreSQL — install the PostgreSQL client tools if you don't have them.

**Back up the main database:**

```powershell
# Set your password so you don't have to type it interactively
$env:PGPASSWORD = "YourDatabasePassword"

# Dump the main database
pg_dump `
    --host=konote-db.postgres.database.azure.com `
    --port=5432 `
    --username=konote_admin `
    --dbname=konote `
    --format=custom `
    --file="backup_main_$(Get-Date -Format 'yyyy-MM-dd').dump"

# Clear the password from the environment
$env:PGPASSWORD = ""
```

**Back up the audit database:**

```powershell
$env:PGPASSWORD = "YourAuditDatabasePassword"

pg_dump `
    --host=konote-db.postgres.database.azure.com `
    --port=5432 `
    --username=audit_writer `
    --dbname=konote_audit `
    --format=custom `
    --file="backup_audit_$(Get-Date -Format 'yyyy-MM-dd').dump"

$env:PGPASSWORD = ""
```

**Why `--format=custom`?** The custom format (`.dump`) is compressed, supports parallel restore, and lets you restore individual tables. It's better than plain SQL for anything beyond small databases.

#### Storing Backups in Azure Blob Storage

After creating backup files, upload them to Azure Blob Storage for safe off-site storage:

```powershell
# Log in to Azure (if not already logged in)
az login

# Create a storage container (first time only)
az storage container create `
    --account-name yourstorageaccount `
    --name konote-backups `
    --auth-mode login

# Upload the main database backup
az storage blob upload `
    --account-name yourstorageaccount `
    --container-name konote-backups `
    --file "backup_main_$(Get-Date -Format 'yyyy-MM-dd').dump" `
    --name "main/backup_main_$(Get-Date -Format 'yyyy-MM-dd').dump" `
    --auth-mode login

# Upload the audit database backup
az storage blob upload `
    --account-name yourstorageaccount `
    --container-name konote-backups `
    --file "backup_audit_$(Get-Date -Format 'yyyy-MM-dd').dump" `
    --name "audit/backup_audit_$(Get-Date -Format 'yyyy-MM-dd').dump" `
    --auth-mode login
```

**Tip:** Set the storage container's access level to **Private** (no anonymous access). Use Azure RBAC to control who can read backups.

---

## 3. Docker Compose Procedures (Self-Hosted)

If you are running KoNote with Docker Compose on your own server, you are responsible for scheduling backups.

### Docker Compose Backup Commands

#### Back Up the Main Database

```powershell
# PowerShell (Windows)
docker compose exec -T db pg_dump -U $env:POSTGRES_USER konote | Out-File -FilePath "backup_main_$(Get-Date -Format 'yyyy-MM-dd').sql" -Encoding utf8
```

```bash
# Bash (Linux/Mac)
docker compose exec -T db pg_dump -U konote konote > backup_main_$(date +%Y-%m-%d).sql
```

#### Back Up the Audit Database

```powershell
# PowerShell (Windows)
docker compose exec -T audit_db pg_dump -U $env:AUDIT_POSTGRES_USER konote_audit | Out-File -FilePath "backup_audit_$(Get-Date -Format 'yyyy-MM-dd').sql" -Encoding utf8
```

```bash
# Bash (Linux/Mac)
docker compose exec -T audit_db pg_dump -U audit_writer konote_audit > backup_audit_$(date +%Y-%m-%d).sql
```

#### Back Up the Environment File

```powershell
# Copy .env to backup location (Windows)
Copy-Item .env "backup_env_$(Get-Date -Format 'yyyy-MM-dd').env"
```

#### Verify Backup Files

Check that the backup files were created and have reasonable sizes:

```powershell
# PowerShell — files should be larger than 1 KB
Get-ChildItem backup_*.sql | Select-Object Name, @{N='SizeKB';E={[math]::Round($_.Length/1KB,1)}}
```

```bash
# Bash
ls -lh backup_*.sql
```

If a backup file is 0 bytes or under 1 KB, something went wrong — check that the database container is running and that your credentials are correct.

### Automated Backup via Windows Task Scheduler

1. Create a PowerShell script (e.g., `C:\KoNote\backup_konote.ps1`):

```powershell
# KoNote Automated Backup Script
# Schedule this to run daily via Windows Task Scheduler

$BackupDir = "C:\Backups\KoNote"
$KoNoteDir = "C:\KoNote"  # Directory containing docker-compose.yml
$Date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile = "$BackupDir\backup_log.txt"

# Create backup directory if needed
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force
}

Add-Content -Path $LogFile -Value "=== Backup started: $Date ==="

try {
    Set-Location $KoNoteDir

    # Back up main database
    $MainBackup = "$BackupDir\backup_main_$Date.sql"
    docker compose exec -T db pg_dump -U konote konote | Out-File -FilePath $MainBackup -Encoding utf8
    Add-Content -Path $LogFile -Value "Main database: $MainBackup"

    # Back up audit database
    $AuditBackup = "$BackupDir\backup_audit_$Date.sql"
    docker compose exec -T audit_db pg_dump -U audit_writer konote_audit | Out-File -FilePath $AuditBackup -Encoding utf8
    Add-Content -Path $LogFile -Value "Audit database: $AuditBackup"

    # Verify file sizes
    $MainSize = (Get-Item $MainBackup).Length
    $AuditSize = (Get-Item $AuditBackup).Length

    if ($MainSize -lt 1024 -or $AuditSize -lt 1024) {
        throw "Backup files are suspiciously small (under 1 KB). Check database connection."
    }

    # Clean up backups older than 30 days
    Get-ChildItem -Path $BackupDir -Filter "backup_*.sql" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
        Remove-Item -Force

    Add-Content -Path $LogFile -Value "Backup completed successfully."
    Add-Content -Path $LogFile -Value ""

} catch {
    Add-Content -Path $LogFile -Value "ERROR: $_"
    Add-Content -Path $LogFile -Value ""
    exit 1
}
```

2. Open **Task Scheduler** (press Windows + R, type `taskschd.msc`, press Enter)
3. Click **Create Task** in the right panel
4. **General tab:** Name it `KoNote Daily Backup`, check **Run whether user is logged on or not** and **Run with highest privileges**
5. **Triggers tab:** Click New → On a schedule → Daily at 2:00 AM
6. **Actions tab:** Click New → Start a program → Program: `powershell.exe` → Arguments: `-ExecutionPolicy Bypass -File "C:\KoNote\backup_konote.ps1"`
7. **Settings tab:** Check **If the task fails, restart every 10 minutes** up to 3 times
8. Click OK and enter your Windows password when prompted

### Automated Backup via Cron (Linux)

Add this to your crontab (`crontab -e`):

```
# KoNote daily backup at 2:00 AM
0 2 * * * cd /opt/konote && docker compose exec -T db pg_dump -U konote konote > /backups/konote/backup_main_$(date +\%Y-\%m-\%d).sql && docker compose exec -T audit_db pg_dump -U audit_writer konote_audit > /backups/konote/backup_audit_$(date +\%Y-\%m-\%d).sql && find /backups/konote -name "backup_*.sql" -mtime +30 -delete
```

---

## 4. Restore Procedures

### Pre-Restore Checklist

Before you start any restore, confirm you have all of these:

- [ ] **Backup file(s)** — either `.sql` (plain text) or `.dump` (custom format)
- [ ] **Encryption key** — the `FIELD_ENCRYPTION_KEY` that was active when the backup was created
- [ ] **Target database is ready** — either empty (fresh) or you have confirmed it is OK to overwrite
- [ ] **Correct PostgreSQL version** — the `pg_restore` / `psql` client version should match or be newer than the server version (both should be PostgreSQL 16)
- [ ] **Environment variables** — you need `DATABASE_URL`, `AUDIT_DATABASE_URL`, `SECRET_KEY`, `FIELD_ENCRYPTION_KEY` at minimum

### Restore on Azure (Point-in-Time)

This is the fastest option for Azure deployments. See [Point-in-Time Restore (PITR)](#point-in-time-restore-pitr) above for full steps.

**Summary:**
1. Open Azure Portal → PostgreSQL Flexible Server → Backup and restore → Restore
2. Pick a restore point (date/time before the problem)
3. Azure creates a new database server (15–30 minutes)
4. Update your Container App's `DATABASE_URL` to point to the new server
5. Re-run `python manage.py lockdown_audit_db`
6. Run `python manage.py verify_backup_restore` (see [Post-Restore Verification](#post-restore-verification))

### Restore on Azure (From Dump File)

If you have a `.dump` file (from `pg_dump --format=custom`):

1. **Create a fresh database** (or confirm you can overwrite the existing one):

   ```powershell
   # Connect to the Azure PostgreSQL server
   $env:PGPASSWORD = "YourAdminPassword"

   psql `
       --host=konote-db.postgres.database.azure.com `
       --port=5432 `
       --username=konote_admin `
       --dbname=postgres `
       --command="DROP DATABASE IF EXISTS konote; CREATE DATABASE konote;"
   ```

2. **Restore the main database:**

   ```powershell
   pg_restore `
       --host=konote-db.postgres.database.azure.com `
       --port=5432 `
       --username=konote_admin `
       --dbname=konote `
       --no-owner `
       --no-privileges `
       --verbose `
       "backup_main_2026-02-25.dump"
   ```

3. **Restore the audit database:**

   ```powershell
   psql `
       --host=konote-db.postgres.database.azure.com `
       --port=5432 `
       --username=konote_admin `
       --dbname=postgres `
       --command="DROP DATABASE IF EXISTS konote_audit; CREATE DATABASE konote_audit;"

   pg_restore `
       --host=konote-db.postgres.database.azure.com `
       --port=5432 `
       --username=konote_admin `
       --dbname=konote_audit `
       --no-owner `
       --no-privileges `
       --verbose `
       "backup_audit_2026-02-25.dump"
   ```

4. **Re-run audit lockdown:**

   ```powershell
   python manage.py lockdown_audit_db
   ```

5. **Verify the restore** (see [Post-Restore Verification](#post-restore-verification))

If your backup is a `.sql` file (plain text) instead of a `.dump` file, use `psql` instead of `pg_restore`:

```powershell
psql `
    --host=konote-db.postgres.database.azure.com `
    --port=5432 `
    --username=konote_admin `
    --dbname=konote `
    --file="backup_main_2026-02-25.sql"
```

### Restore on Docker Compose

#### Step 1: Stop the Running Containers

```powershell
docker compose down
```

#### Step 2: Remove the Old Database Volumes

**This permanently deletes all current data. Only do this if you are sure you want to replace it with the backup.**

```powershell
docker volume rm konote_pgdata
docker volume rm konote_audit_pgdata
```

> **Note:** The volume names depend on the project name. If you cloned the repository into a folder called `konote-web`, the volumes may be called `konote-web_pgdata` and `konote-web_audit_pgdata`. Check with `docker volume ls | findstr konote`.

#### Step 3: Start the Database Containers

```powershell
docker compose up -d db audit_db
```

Wait about 10 seconds for the databases to initialise.

#### Step 4: Restore the Main Database

```powershell
# For .sql files (plain text):
Get-Content backup_main_2026-02-25.sql | docker compose exec -T db psql -U konote konote

# For .dump files (custom format):
docker compose exec -T db pg_restore -U konote -d konote --no-owner --no-privileges < backup_main_2026-02-25.dump
```

#### Step 5: Restore the Audit Database

```powershell
# For .sql files:
Get-Content backup_audit_2026-02-25.sql | docker compose exec -T audit_db psql -U audit_writer konote_audit

# For .dump files:
docker compose exec -T audit_db pg_restore -U audit_writer -d konote_audit --no-owner --no-privileges < backup_audit_2026-02-25.dump
```

#### Step 6: Start the Entire Stack

```powershell
docker compose up -d
```

#### Step 7: Re-Run Audit Lockdown

```powershell
docker compose exec web python manage.py lockdown_audit_db
```

#### Step 8: Verify the Restore

```powershell
docker compose exec web python manage.py verify_backup_restore
```

### Post-Restore Verification

After every restore, run the verification management command:

```powershell
python manage.py verify_backup_restore
```

This command checks:
- Database connectivity (both main and audit databases)
- Table counts (are the expected tables present?)
- Row counts for key tables (users, clients, programs)
- Encryption key validity (can the current key decrypt existing data?)
- Audit log integrity (are records present and sequential?)

**If verification fails on encrypted data:** You likely have the wrong `FIELD_ENCRYPTION_KEY`. Check that the key in your current environment matches the key that was active when the backup was created.

**Manual verification** (if the management command is not available):

```powershell
# Check the main database has data
python manage.py shell -c "from django.contrib.auth.models import User; print(f'Users: {User.objects.count()}')"
python manage.py shell -c "from apps.clients.models import ClientFile; print(f'Clients: {ClientFile.objects.count()}')"

# Check that encryption works (try to read a client name)
python manage.py shell -c "
from apps.clients.models import ClientFile
c = ClientFile.objects.first()
if c:
    print(f'First client decrypted OK: {c.first_name[:1]}***')
else:
    print('No clients in database')
"

# Check the audit database has records
python manage.py shell -c "
from apps.audit.models import AuditLog
print(f'Audit records: {AuditLog.objects.using(\"audit\").count()}')
"
```

### Re-Running Audit Lockdown After Restore

When you restore the audit database, PostgreSQL restores the data but may not preserve the permission restrictions that make the audit log tamper-resistant. You **must** re-run the lockdown command after every restore:

```powershell
python manage.py lockdown_audit_db
```

This command:
- Revokes UPDATE and DELETE privileges from the audit database user
- Grants only SELECT and INSERT (read and append)
- Grants USAGE on sequences (needed for auto-increment IDs)

If you skip this step, the audit log is still readable, but it is no longer tamper-resistant — the application user could theoretically modify or delete audit records.

---

## 5. Encryption Key Management

The `FIELD_ENCRYPTION_KEY` is a Fernet key — a Base64-encoded 256-bit value that looks something like:

```
tFE8M4TjWqJx7Kz9nB2pL1mR5vY6gH8dA3wE0iU4oS=
```

### How to Back Up the Key

Store the key in **at least two separate, secure locations** — never in the same place as your database backups:

| Storage Method | When to Use | Notes |
|---------------|-------------|-------|
| **Password manager** (1Password, Bitwarden) | Always — primary storage | Share with a trusted co-worker so it's accessible if you're unavailable |
| **Azure Key Vault** | Azure deployments | `az keyvault secret set --vault-name your-vault --name FIELD-ENCRYPTION-KEY --value "your-key"` |
| **Printed and sealed** | Additional precaution | Print the key, seal in an envelope, store in a locked safe or safety deposit box |

**Never store the key:**
- In the same backup location as database backups (if someone steals the backup, they get the key too)
- In version control (Git)
- In plain text on shared drives
- In email or chat messages

### How to Verify Your Key Is Correct

```powershell
# Check the key is set and valid
python manage.py check
```

If the key is missing or invalid, you will see error `KoNote.E001`. If you see "System check identified no issues," the key is valid and can encrypt/decrypt data.

### Key Rotation and Backups

KoNote supports key rotation using a comma-separated key format:

```
FIELD_ENCRYPTION_KEY=newKeyABC...,oldKeyXYZ...
```

When you rotate the key:
- The first key encrypts new data
- All listed keys are tried when decrypting (so old data still works)
- The `rotate_encryption_key` management command re-encrypts all existing data with the new key

**Important interaction with backups:**

| Scenario | What Happens |
|----------|-------------|
| You rotate the key, then restore a pre-rotation backup | The old key is needed. Set `FIELD_ENCRYPTION_KEY` to the old key (or comma-separated: `old,current`) |
| You rotate the key, then take a new backup | The new backup uses the new key. The old key is no longer needed for *this* backup |
| You have backups from different time periods with different keys | Label each backup with which key was active at that time |

**Best practice:** After every key rotation, take a fresh backup immediately. This ensures your most recent backup matches your current key.

**How to rotate:**

```powershell
# 1. Generate a new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Run rotation (re-encrypts all data — do a dry run first)
python manage.py rotate_encryption_key --old-key="YOUR_OLD_KEY" --new-key="YOUR_NEW_KEY" --dry-run
python manage.py rotate_encryption_key --old-key="YOUR_OLD_KEY" --new-key="YOUR_NEW_KEY"

# 3. Update FIELD_ENCRYPTION_KEY in your environment to the new key only
# 4. Restart the application
# 5. Take a fresh backup immediately
```

### What to Do If You Have a Backup But Lost the Key

This is a partial recovery only. You can recover:

- **All unencrypted data:** Program structures, outcome definitions, metric scores, dates, settings, user accounts (but not emails), group assignments
- **Audit log entries:** All audit records (action types, timestamps, user IDs) — but encrypted content within those records will be unreadable

You **cannot recover:**
- Client names, birth dates, preferred names
- Progress note content, participant reflections
- Sensitive custom field values
- User email addresses

**Steps for partial recovery:**

1. Restore the database as normal (see [Restore Procedures](#4-restore-procedures))
2. Generate a new encryption key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
3. Set `FIELD_ENCRYPTION_KEY` to the new key
4. The application will start, but any attempt to read encrypted fields will raise a `DecryptionError`
5. You can access unencrypted data through the Django admin or direct database queries
6. Encrypted fields will need to be re-entered manually from paper records or other sources

---

## 6. Testing Schedule

### Monthly Restore Test

**Do this once a month.** An untested backup is no backup at all.

#### Abbreviated Test Procedure

1. **Take a fresh backup** (or use last night's automated backup)

2. **Spin up a test database** — do NOT test on production:

   ```powershell
   # Start a temporary test database
   docker run -d --name konote-restore-test `
       -e POSTGRES_DB=konote_test `
       -e POSTGRES_USER=konote `
       -e POSTGRES_PASSWORD=testpassword `
       -p 5433:5432 `
       postgres:16-alpine

   # Wait for it to start
   Start-Sleep -Seconds 5
   ```

3. **Restore the backup into the test database:**

   ```powershell
   # For .sql files:
   Get-Content backup_main_2026-02-25.sql | docker exec -i konote-restore-test psql -U konote konote_test

   # For .dump files:
   docker exec -i konote-restore-test pg_restore -U konote -d konote_test --no-owner --no-privileges < backup_main_2026-02-25.dump
   ```

4. **Verify key data is present:**

   ```powershell
   docker exec konote-restore-test psql -U konote konote_test -c "SELECT count(*) FROM auth_user;"
   docker exec konote-restore-test psql -U konote konote_test -c "SELECT count(*) FROM clients_clientfile;"
   docker exec konote-restore-test psql -U konote konote_test -c "SELECT count(*) FROM notes_progressnote;"
   ```

5. **Test encryption** (set `DATABASE_URL` to point to the test database, then run):

   ```powershell
   python manage.py verify_backup_restore
   ```

6. **Clean up the test database:**

   ```powershell
   docker stop konote-restore-test
   docker rm konote-restore-test
   ```

7. **Record the result** — note the date, whether it passed, and any issues.

### What to Check After a Restore

| Check | How | Expected Result |
|-------|-----|-----------------|
| Users exist | `SELECT count(*) FROM auth_user;` | Same count as production |
| Clients exist | `SELECT count(*) FROM clients_clientfile;` | Same count as production |
| Programs exist | `SELECT count(*) FROM programs_program;` | Same count as production |
| Encryption works | `python manage.py verify_backup_restore` | "Encryption check passed" |
| Audit records exist | Query audit database: `SELECT count(*) FROM audit_log;` | Records present |
| Application starts | `python manage.py runserver` | No errors on startup |
| Login works | Open the app in a browser and sign in | Successful login |

---

## 7. Disaster Recovery Scenarios

### Scenario A: Database Corruption

**Symptoms:** Application errors mentioning "invalid page" or "relation does not exist." Database queries fail on specific tables.

**Recovery:**

1. **Azure:** Use point-in-time restore to the moment just before corruption was detected
   - See [Point-in-Time Restore (PITR)](#point-in-time-restore-pitr) for steps
   - Estimated recovery time: 15–30 minutes

2. **Docker Compose:** Restore from your most recent backup
   - See [Restore on Docker Compose](#restore-on-docker-compose) for steps
   - Estimated recovery time: 30–60 minutes (depends on backup size)

3. After restore, run `python manage.py lockdown_audit_db`
4. Run `python manage.py verify_backup_restore`

### Scenario B: Accidental Data Deletion

**Symptoms:** A staff member deleted client records, program data, or notes by mistake.

**Recovery:**

1. **Identify the time** the deletion occurred. Check with staff and look at audit logs:
   ```powershell
   python manage.py shell -c "
   from apps.audit.models import AuditLog
   recent = AuditLog.objects.using('audit').filter(action='DELETE').order_by('-timestamp')[:10]
   for log in recent:
       print(f'{log.timestamp} | {log.action} | {log.model_name} | User: {log.user_id}')
   "
   ```

2. **Azure:** Use PITR to restore to a point *before* the deletion. Choose a time 5–10 minutes before the deletion timestamp.

3. **Docker Compose:** Restore from the most recent backup taken *before* the deletion occurred.

4. After restore, re-run lockdown and verification.

**Note:** With PITR, you lose all changes made *after* the restore point. If staff entered new data between the deletion and your restore, that new data will also be lost. Consider restoring to a separate database and manually copying back only the deleted records if feasible.

### Scenario C: Complete Infrastructure Loss

**Symptoms:** Server/container is gone. Cloud resources are deleted or inaccessible. You need to rebuild from scratch.

**Recovery:**

1. **Provision new infrastructure:**
   - Azure: Redeploy Container App and PostgreSQL using your deployment scripts
   - Docker Compose: Set up Docker on a new server, copy your `docker-compose.yml` and `.env`

2. **Restore the encryption key** from your secure storage (password manager, Azure Key Vault, or sealed envelope)

3. **Restore both databases** from your most recent backup (off-site if the on-site backups were lost too)

4. **Set all environment variables** (`FIELD_ENCRYPTION_KEY`, `SECRET_KEY`, `DATABASE_URL`, `AUDIT_DATABASE_URL`, etc.)

5. **Run migrations** (in case the backup is from a slightly older schema version):
   ```powershell
   python manage.py migrate --database=default
   python manage.py migrate --database=audit
   ```

6. **Re-run audit lockdown:**
   ```powershell
   python manage.py lockdown_audit_db
   ```

7. **Verify the restore:**
   ```powershell
   python manage.py verify_backup_restore
   ```

8. **Update DNS** if the server address has changed

**Estimated recovery time:** 2–4 hours (most of the time is provisioning new infrastructure)

### Scenario D: Encryption Key Compromise

**Symptoms:** You suspect someone unauthorised has obtained the encryption key — for example, it was exposed in a log file, email, or Git commit.

**Recovery:**

1. **Rotate the key immediately** — this re-encrypts all PII with a new key:
   ```powershell
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   # Save the output — this is your new key

   python manage.py rotate_encryption_key --old-key="COMPROMISED_KEY" --new-key="NEW_KEY"
   ```

2. **Update the key** in all environments (`.env`, Azure Key Vault, Railway, etc.)

3. **Restart the application** to pick up the new key

4. **Take a fresh backup immediately** — so future restores use the new key

5. **Revoke access** to the old key wherever it was stored

6. **Investigate the exposure** — where was the key leaked? Remove it from logs, Git history, or any other location

7. **Notify your privacy officer** — depending on your jurisdiction and the nature of the exposure, you may have breach notification obligations

### Scenario E: Ransomware

**Symptoms:** Files or databases are encrypted by an attacker. Ransom demand is displayed.

**Recovery:**

1. **Do not pay the ransom.** There is no guarantee you will get your data back.

2. **Disconnect the affected system** from the network immediately to prevent lateral spread.

3. **Restore from an offline backup** — one that was not connected to the compromised system. This could be:
   - Azure Blob Storage backups (if the storage account was not also compromised)
   - A backup stored on a separate, disconnected drive
   - Azure PITR (if the PostgreSQL server itself was not compromised — Azure managed databases are typically isolated from the compute layer)

4. **Provision new infrastructure** — do not restore onto the compromised system. Set up fresh servers/containers.

5. **Change all credentials:**
   - Database passwords
   - `SECRET_KEY`
   - `FIELD_ENCRYPTION_KEY` (rotate it — the old key may be known to the attacker)
   - Azure AD / SSO credentials
   - Any API keys

6. **Restore both databases** to the new infrastructure

7. **Re-run lockdown and verification:**
   ```powershell
   python manage.py lockdown_audit_db
   python manage.py verify_backup_restore
   ```

8. **Investigate the attack vector** — how did the attacker get in? Patch the vulnerability before reconnecting.

9. **Notify stakeholders:**
   - Your privacy officer
   - Affected participants (if PII may have been exposed)
   - Your local privacy commissioner / Information and Privacy Commissioner of Ontario, as required by law
   - Law enforcement

---

## 8. Troubleshooting

### "Permission denied" on Audit Tables After Restore

**Error message:** `ERROR: permission denied for table audit_log`

**Cause:** The restore overwrote the database permissions. The audit lockdown needs to be re-applied.

**Fix:**

```powershell
python manage.py lockdown_audit_db
```

If this still fails, the database user may not have superuser privileges needed to grant/revoke:

```powershell
# Connect as the PostgreSQL superuser and grant permissions manually
psql -U postgres -d konote_audit -c "REVOKE ALL ON audit_log FROM audit_writer; GRANT SELECT, INSERT ON audit_log TO audit_writer; GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO audit_writer;"
```

### Encoding Issues (`UnicodeDecodeError` or Garbled Characters)

**Cause:** The backup was created or restored with the wrong character encoding.

**Fix:** Ensure both the backup and restore use UTF-8:

```powershell
# When backing up, specify encoding
pg_dump --encoding=UTF8 -U konote konote > backup.sql

# When restoring, set the client encoding
$env:PGCLIENTENCODING = "UTF8"
psql -U konote -d konote -f backup.sql
```

If you're on Windows and used `Out-File`, ensure you specified `-Encoding utf8`:

```powershell
docker compose exec -T db pg_dump -U konote konote | Out-File -FilePath backup.sql -Encoding utf8
```

### Version Mismatch Between pg_dump and Server

**Error message:** `pg_dump: server version: 16.x; pg_dump version: 15.x` or `pg_restore: unsupported version`

**Cause:** Your local `pg_dump` or `pg_restore` tool is a different version than the PostgreSQL server.

**Rule:** The client tool version should be **equal to or newer than** the server version.

**Fix:**

1. Check your current version: `pg_dump --version`
2. Check the server version: `psql -c "SELECT version();"`
3. If your local tools are older, install PostgreSQL 16 client tools:

   ```powershell
   # Windows — download from https://www.postgresql.org/download/windows/
   # Install client tools only (uncheck "PostgreSQL Server" during installation)

   # Linux (Debian/Ubuntu)
   sudo apt-get install postgresql-client-16
   ```

4. Alternatively, run `pg_dump` from inside the Docker container (which always has the matching version):

   ```powershell
   docker compose exec -T db pg_dump -U konote konote > backup.sql
   ```

### Restore Fails with "database konote already exists"

**Cause:** You're trying to restore into a database that already has data.

**Fix:** Either drop and recreate the database first, or use `--clean` to have `pg_restore` drop objects before recreating them:

```powershell
# Option 1: Drop and recreate (destroys all existing data)
psql -U postgres -c "DROP DATABASE IF EXISTS konote;"
psql -U postgres -c "CREATE DATABASE konote OWNER konote;"

# Option 2: Use --clean flag with pg_restore
pg_restore --clean --if-exists --no-owner --no-privileges -U konote -d konote backup.dump
```

### Encryption Errors After Restore (`DecryptionError`)

**Error message:** `DecryptionError: Decryption failed — possible key mismatch or data corruption`

**Cause:** The `FIELD_ENCRYPTION_KEY` in your current environment does not match the key that was used when the backup was created.

**Fix:**

1. Find the correct key for this backup — check your password manager and match the key to the backup date
2. If you used key rotation between the backup and now, you may need the old key
3. Set the correct key: update `FIELD_ENCRYPTION_KEY` in your `.env` file or environment variables
4. Restart the application and test again

If you truly cannot find the correct key, see [What to Do If You Have a Backup But Lost the Key](#what-to-do-if-you-have-a-backup-but-lost-the-key).

### Restore Seems to Work But Application Shows No Data

**Possible causes:**

1. **Wrong database:** Check that `DATABASE_URL` points to the database you just restored, not a different one
2. **Migrations not run:** If the backup is from an older version, run `python manage.py migrate` to update the schema
3. **Wrong database name:** Verify the database name matches (`konote` not `konote_test`)

```powershell
# Check which database the application is using
python manage.py shell -c "
from django.db import connections
print('Default DB:', connections['default'].settings_dict['NAME'])
print('Audit DB:', connections['audit'].settings_dict['NAME'])
"
```

### pg_restore Warnings About "role does not exist"

**Warning message:** `WARNING: role "konote_admin" does not exist`

**Cause:** The backup was created on a server with different role names. This is common when moving between Azure (which uses `konote_admin`) and Docker Compose (which uses `konote`).

**Fix:** These warnings are usually harmless. Use `--no-owner --no-privileges` to suppress them:

```powershell
pg_restore --no-owner --no-privileges -U konote -d konote backup.dump
```

---

## Appendix: Backup Retention Recommendations

| Backup Type | Frequency | Keep For | Notes |
|-------------|-----------|----------|-------|
| Daily automated | Every night | 30 days | Automated via Azure, Task Scheduler, or cron |
| Weekly snapshot | Every Monday | 90 days | Optional — provides longer recovery window |
| Monthly archive | First of month | 1 year | For compliance and audit requirements |
| Pre-upgrade | Before each upgrade | Until next upgrade succeeds | Always back up before running migrations |
| Post-key-rotation | Immediately after rotating key | Until the *next* post-rotation backup | Ensures backup matches current key |

**Storage locations:**
- **Primary:** Same platform (Azure automatic backups, or local backup directory)
- **Secondary:** Off-site cloud storage (Azure Blob Storage, separate storage account)
- **Encryption key:** Separate from database backups (password manager + sealed envelope)
