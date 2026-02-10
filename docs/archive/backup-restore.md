# Backup and Restore Guide for KoNote Web

## What You Need to Know

KoNote Web stores data in **two PostgreSQL databases**:

1. **Main database** (`konote`) — application data including users, clients, programs, plans, notes, and settings
2. **Audit database** (`konote_audit`) — append-only log of every data change (required for compliance)

Additionally, client information (names, emails, birth dates) is encrypted using the **FIELD_ENCRYPTION_KEY**. If you lose this key, encrypted data cannot be recovered.

## Critical: The Encryption Key

**If you lose `FIELD_ENCRYPTION_KEY`, all encrypted client data is unrecoverable.**

### Where the Key Lives

- **Docker Compose**: stored in your `.env` file (or environment variables)
- **Railway**: stored in environment variables (Railway dashboard)
- **Azure**: stored in environment variables or Azure Key Vault

### How to Back Up the Encryption Key

Store the encryption key in a **separate, secure location** — not alongside your database backups:

1. **Password manager** (1Password, Bitwarden, LastPass) — recommended
2. **Azure Key Vault** (for Azure deployments)
3. **Vault application** on your local machine
4. **Encrypted file** with restricted access (Windows: `Encrypting File System`; Mac/Linux: GPG)

**Never store it in plain text on shared drives or unencrypted USB sticks.**

### How to Check Your Current Key

If you need to verify the key is set:

```bash
# Docker Compose
cat .env | grep FIELD_ENCRYPTION_KEY

# Railway — via CLI
railway run echo $FIELD_ENCRYPTION_KEY

# Azure — via CLI
az keyvault secret show --vault-name <vault-name> --name FIELD_ENCRYPTION_KEY
```

---

## Backup Methods

### Option 1: Docker Compose (Local Development/Self-Hosted)

Use `pg_dump` to back up both databases. Docker Compose makes this simple because the database is in a container.

#### Back Up the Main Database

```bash
docker compose exec db pg_dump -U konote konote > backup_main_$(date +\%Y-\%m-\%d).sql
```

This creates a file like `backup_main_2026-02-02.sql` in your current directory.

**What this does:**
- Connects to the `db` container
- Runs `pg_dump` as the `konote` user
- Exports the `konote` database to a `.sql` file
- Filename includes today's date

#### Back Up the Audit Database

```bash
docker compose exec audit_db pg_dump -U audit_writer konote_audit > backup_audit_$(date +\%Y-\%m-\%d).sql
```

This creates `backup_audit_2026-02-02.sql`.

#### Verify Your Backups

Check that both files were created and contain data:

```bash
# List files by size (should be more than 1 KB)
ls -lh backup_*.sql

# Quick check — first 20 lines should show SQL comments and structure
head -20 backup_main_2026-02-02.sql
```

---

### Option 2: Railway (Cloud-Hosted)

Railway provides built-in database backups. You can also use `railway run` to back up manually.

#### Use Railway's Built-In Backups (Recommended)

1. Log into the [Railway dashboard](https://railway.app)
2. Select your KoNote project
3. Click the **Postgres** service (main database)
4. Scroll down to **Backups** — Railway automatically keeps daily backups for 7 days
5. To restore: click the backup and select **Restore**

**Advantages:**
- Automatic, no manual work
- Stored securely on Railway infrastructure
- Easy one-click restore

**Disadvantages:**
- Limited to 7 days of backups (longer retention costs extra)

#### Manual Backup with railway run

If you need a downloadable copy:

```bash
# Set up Railway CLI on your machine first
brew install railway  # Mac
# or: sudo apt-get install railway  # Linux
# or: download from https://github.com/railwayapp/cli

# Log in
railway login

# Link to your project directory
cd /path/to/KoNote-web
railway link

# Backup main database
railway run pg_dump -U $DB_USER -d $DATABASE -h $DB_HOST > backup_main_railway_$(date +%Y-%m-%d).sql

# Backup audit database — note: you may need the separate audit database credentials
railway run pg_dump -U $AUDIT_USER -d $AUDIT_DATABASE -h $AUDIT_HOST > backup_audit_railway_$(date +%Y-%m-%d).sql
```

---

### Option 3: Plain PostgreSQL (Any Hosting)

If you're running PostgreSQL directly on a server (not Docker Compose), use `pg_dump` with network connection details.

#### Back Up the Main Database

```bash
pg_dump -h hostname_or_ip -U konote -d konote > backup_main_$(date +%Y-%m-%d).sql
```

Replace:
- `hostname_or_ip` — database server address (e.g., `db.example.com` or `192.168.1.10`)
- `konote` — your database username
- Port 5432 is assumed; if different, add `-p 5433`

**You will be prompted for the password.** Enter the database password.

#### Back Up the Audit Database

```bash
pg_dump -h hostname_or_ip -U audit_writer -d konote_audit > backup_audit_$(date +%Y-%m-%d).sql
```

---

### Option 4: Azure (Azure Database for PostgreSQL)

Azure provides managed PostgreSQL with automated backups.

#### Use Azure's Built-In Backups (Recommended)

1. Open the [Azure portal](https://portal.azure.com)
2. Navigate to **Azure Database for PostgreSQL servers**
3. Select your KoNote server
4. Under **Backup** — Azure automatically retains backups for 7 days
5. To restore: click **Restore** and choose a backup point

#### Manual Backup with Azure CLI

```bash
# Get your server name and resource group
az postgres server list --output table

# Back up the main database
az postgres server backup create \
  --resource-group your-resource-group \
  --server-name your-server-name \
  --backup-name "KoNote-main-$(date +%Y-%m-%d)"
```

---

## Restore from Backup

Before restoring, **verify you have**:
- The backup file (`.sql`)
- The encryption key (`FIELD_ENCRYPTION_KEY`)
- Write access to the target database

### Restore to Docker Compose (Fresh Database)

If your database is corrupted or you're setting up a test environment:

#### Step 1: Stop the Container (if Running)

```bash
docker compose down
```

#### Step 2: Remove the Old Volume (Data)

**Warning: This deletes all data in the database. Make sure your backup is safe first.**

```bash
docker volume rm KoNote-web_pgdata        # Main database
docker volume rm KoNote-web_audit_pgdata  # Audit database
```

#### Step 3: Start the Containers

```bash
docker compose up -d
```

Docker will recreate the containers and volumes.

#### Step 4: Restore the Main Database

Wait 10 seconds for the database to initialise, then:

```bash
docker compose exec -T db psql -U konote konote < backup_main_2026-02-02.sql
```

The `-T` flag disables pseudo-terminal allocation (required for piped input).

#### Step 5: Restore the Audit Database

```bash
docker compose exec -T audit_db psql -U audit_writer konote_audit < backup_audit_2026-02-02.sql
```

#### Step 6: Verify the Restore

Connect to the restored database:

```bash
docker compose exec db psql -U konote konote

# Inside psql, check table counts
SELECT count(*) FROM public.auth_user;
\q
```

If you see data (count > 0), the restore succeeded.

---

### Restore to a Fresh PostgreSQL Instance

If you're migrating to a new server:

#### Step 1: Create the Databases

```bash
psql -U postgres

CREATE DATABASE konote;
CREATE DATABASE konote_audit;

CREATE USER konote WITH PASSWORD 'your-password';
CREATE USER audit_writer WITH PASSWORD 'your-password';

GRANT ALL PRIVILEGES ON DATABASE konote TO konote;
GRANT ALL PRIVILEGES ON DATABASE konote_audit TO audit_writer;

\q
```

#### Step 2: Restore the Main Database

```bash
psql -U konote -d konote < backup_main_2026-02-02.sql
```

#### Step 3: Restore the Audit Database

```bash
psql -U audit_writer -d konote_audit < backup_audit_2026-02-02.sql
```

#### Step 4: Verify

```bash
psql -U konote -d konote -c "SELECT count(*) FROM public.auth_user;"
```

---

### Restore to Railway

If your Railway database is corrupted:

1. Log into [Railway dashboard](https://railway.app)
2. Select your KoNote project
3. Click the **Postgres** service
4. Scroll to **Backups**
5. Click the backup you want to restore
6. Click **Restore** — confirm the action
7. Railway will restore the database (this takes a few minutes)

**Note:** Restoring a database in Railway replaces all current data. Test on a separate project first if unsure.

---

## Automated Backups

### Option 1: Windows Task Scheduler (Windows Servers)

If you're running KoNote on Windows (not using WSL):

#### Create a Backup Script

Save this as `C:\KoNote\backup_KoNote.ps1`:

```powershell
# KoNote Backup Script for Windows
# Run this with Task Scheduler

$BackupDir = "C:\Backups\KoNote"
$KoNoteDir = "C:\KoNote\KoNote-web"  # Adjust to your installation path
$Date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile = "$BackupDir\backup_log.txt"

# Create backup directory if it doesn't exist
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force
}

# Start logging
Add-Content -Path $LogFile -Value "=== Backup started: $Date ==="

try {
    # Change to KoNote directory (required for docker compose)
    Set-Location $KoNoteDir

    # Main database backup
    $MainBackup = "$BackupDir\backup_main_$Date.sql"
    docker compose exec -T db pg_dump -U konote konote | Out-File -FilePath $MainBackup -Encoding utf8
    Add-Content -Path $LogFile -Value "Main database backed up: $MainBackup"

    # Audit database backup
    $AuditBackup = "$BackupDir\backup_audit_$Date.sql"
    docker compose exec -T audit_db pg_dump -U audit_writer konote_audit | Out-File -FilePath $AuditBackup -Encoding utf8
    Add-Content -Path $LogFile -Value "Audit database backed up: $AuditBackup"

    # Verify backups have content (more than 1 KB)
    $MainSize = (Get-Item $MainBackup).Length
    $AuditSize = (Get-Item $AuditBackup).Length

    if ($MainSize -lt 1024 -or $AuditSize -lt 1024) {
        throw "Backup files are suspiciously small. Check database connection."
    }

    # Clean up backups older than 30 days
    Get-ChildItem -Path $BackupDir -Filter "backup_*.sql" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
        Remove-Item -Force

    Add-Content -Path $LogFile -Value "Backup completed successfully: $Date"
    Add-Content -Path $LogFile -Value ""

} catch {
    Add-Content -Path $LogFile -Value "ERROR: $_"
    Add-Content -Path $LogFile -Value ""
    exit 1
}
```

#### Set Up Task Scheduler

1. Press **Windows + R**, type `taskschd.msc`, press Enter
2. In the right panel, click **Create Task** (not "Create Basic Task")
3. **General tab:**
   - Name: `KoNote Daily Backup`
   - Check **Run whether user is logged on or not**
   - Check **Run with highest privileges**
4. **Triggers tab:**
   - Click **New**
   - Begin the task: **On a schedule**
   - Daily, at 2:00 AM
   - Click OK
5. **Actions tab:**
   - Click **New**
   - Action: **Start a program**
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\KoNote\backup_KoNote.ps1"`
   - Click OK
6. **Settings tab:**
   - Check **If the task fails, restart every:** 10 minutes, up to 3 times
   - Click OK
7. Enter your Windows password when prompted

#### Verify It Works

Run the task manually first:

1. In Task Scheduler, right-click the task
2. Click **Run**
3. Check `C:\Backups\KoNote\backup_log.txt` for results
4. Verify `.sql` files were created

---

### Option 2: Cron Job (Linux/Mac or WSL on Windows)

If you're running KoNote on a Linux server or WSL (Windows Subsystem for Linux):

#### Create a Backup Script

Save this as `/home/user/backup_KoNote.sh`:

```bash
#!/bin/bash

# Backup directory
BACKUP_DIR="/backups/KoNote"
mkdir -p "$BACKUP_DIR"

# Date for filename
DATE=$(date +%Y-%m-%d_%H-%M-%S)

# Log file
LOG_FILE="$BACKUP_DIR/backup_log.txt"

echo "=== Backup started: $DATE ===" >> "$LOG_FILE"

# Main database backup
# Note: -T flag is required for non-interactive (cron) execution
docker compose -f /path/to/KoNote-web/docker-compose.yml exec -T db pg_dump -U konote konote > "$BACKUP_DIR/backup_main_$DATE.sql"

if [ $? -ne 0 ]; then
    echo "ERROR: Main database backup failed" >> "$LOG_FILE"
    exit 1
fi

# Audit database backup
docker compose -f /path/to/KoNote-web/docker-compose.yml exec -T audit_db pg_dump -U audit_writer konote_audit > "$BACKUP_DIR/backup_audit_$DATE.sql"

if [ $? -ne 0 ]; then
    echo "ERROR: Audit database backup failed" >> "$LOG_FILE"
    exit 1
fi

# Verify backups have content (more than 1 KB)
MAIN_SIZE=$(stat -f%z "$BACKUP_DIR/backup_main_$DATE.sql" 2>/dev/null || stat --printf="%s" "$BACKUP_DIR/backup_main_$DATE.sql")
if [ "$MAIN_SIZE" -lt 1024 ]; then
    echo "ERROR: Main backup file is too small" >> "$LOG_FILE"
    exit 1
fi

# Clean up backups older than 30 days
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +30 -delete

echo "Backup completed successfully: $DATE" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
```

#### Make It Executable

```bash
chmod +x /home/user/backup_KoNote.sh
```

#### Schedule with Cron

```bash
crontab -e
```

Add this line to run backups daily at 2:00 AM:

```
0 2 * * * /home/user/backup_KoNote.sh 2>&1
```

#### Verify Cron Is Running

```bash
# Check cron logs (Linux)
tail -f /var/log/syslog | grep CRON

# Check cron logs (Mac)
log stream --predicate 'process == "cron"'
```

### Option 2: Railway Backups (Automatic)

Railway automatically backs up PostgreSQL databases daily. You don't need to configure anything.

- **Retention**: 7 days (paid plans may offer longer)
- **Restore**: One click in the Railway dashboard

### Option 3: Azure Backups (Automatic)

Azure Database for PostgreSQL automatically backs up daily.

- **Retention**: 7 days (configurable, up to 35 days for additional cost)
- **Restore**: Via Azure portal or Azure CLI

---

### Option 4: Copy Backups to Cloud Storage (Off-Site)

Storing backups only on your server is risky — if the server fails, you lose both the data and the backups. Copy backups to cloud storage for disaster recovery.

#### Azure Blob Storage (Windows PowerShell)

Add this to your Windows backup script after creating the `.sql` files:

```powershell
# Upload to Azure Blob Storage
# First, install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows

$StorageAccount = "your-storage-account"
$Container = "KoNote-backups"

# Upload main backup
az storage blob upload `
    --account-name $StorageAccount `
    --container-name $Container `
    --file $MainBackup `
    --name "main/backup_main_$Date.sql" `
    --auth-mode login

# Upload audit backup
az storage blob upload `
    --account-name $StorageAccount `
    --container-name $Container `
    --file $AuditBackup `
    --name "audit/backup_audit_$Date.sql" `
    --auth-mode login

Add-Content -Path $LogFile -Value "Uploaded to Azure Blob Storage"
```

**Setup steps:**

1. In Azure Portal, create a **Storage Account**
2. Create a **Container** named `KoNote-backups`
3. Set **Access level** to Private
4. Run `az login` once on the server to authenticate

#### Amazon S3 (Linux/Mac)

Add this to your cron backup script after creating the `.sql` files:

```bash
# Upload to S3
# First, install AWS CLI: pip install awscli && aws configure

S3_BUCKET="your-bucket-name"

aws s3 cp "$BACKUP_DIR/backup_main_$DATE.sql" "s3://$S3_BUCKET/main/backup_main_$DATE.sql"
aws s3 cp "$BACKUP_DIR/backup_audit_$DATE.sql" "s3://$S3_BUCKET/audit/backup_audit_$DATE.sql"

echo "Uploaded to S3" >> "$LOG_FILE"

# Optional: Delete S3 backups older than 90 days
aws s3 ls "s3://$S3_BUCKET/main/" | while read -r line; do
    BACKUP_DATE=$(echo "$line" | awk '{print $1}')
    FILE_NAME=$(echo "$line" | awk '{print $4}')
    if [[ $(date -d "$BACKUP_DATE" +%s) -lt $(date -d "90 days ago" +%s) ]]; then
        aws s3 rm "s3://$S3_BUCKET/main/$FILE_NAME"
    fi
done
```

#### Google Cloud Storage (Linux/Mac)

```bash
# Upload to Google Cloud Storage
# First, install gsutil: https://cloud.google.com/storage/docs/gsutil_install

GCS_BUCKET="gs://your-bucket-name"

gsutil cp "$BACKUP_DIR/backup_main_$DATE.sql" "$GCS_BUCKET/main/"
gsutil cp "$BACKUP_DIR/backup_audit_$DATE.sql" "$GCS_BUCKET/audit/"

echo "Uploaded to Google Cloud Storage" >> "$LOG_FILE"
```

---

### Option 5: Backup Monitoring and Alerts

Know immediately when backups fail.

#### Email Alerts (Windows PowerShell)

Add this to the end of your Windows backup script:

```powershell
# Email notification on failure
# Requires: An SMTP server or email service

function Send-BackupAlert {
    param($Subject, $Body)

    $SmtpServer = "smtp.office365.com"  # Or your email provider
    $SmtpPort = 587
    $From = "backups@yourorg.ca"
    $To = "admin@yourorg.ca"
    $Username = "backups@yourorg.ca"
    $Password = "REPLACE_WITH_APP_PASSWORD"  # Use app password, not main password

    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $Credential = New-Object System.Management.Automation.PSCredential($Username, $SecurePassword)

    Send-MailMessage -From $From -To $To -Subject $Subject -Body $Body `
        -SmtpServer $SmtpServer -Port $SmtpPort -UseSsl -Credential $Credential
}

# In your catch block, add:
# Send-BackupAlert -Subject "KoNote Backup FAILED" -Body "Backup failed at $Date. Check $LogFile for details."
```

#### Email Alerts (Linux/Mac)

Add this to your cron backup script:

```bash
# Email notification on failure
# Requires: mailutils or sendmail installed

ADMIN_EMAIL="admin@yourorg.ca"

send_alert() {
    local subject="$1"
    local body="$2"
    echo "$body" | mail -s "$subject" "$ADMIN_EMAIL"
}

# Add this after any error:
# send_alert "KoNote Backup FAILED" "Backup failed at $DATE. Check $LOG_FILE for details."
```

#### Slack/Teams Webhook Alerts

For instant team notification:

```bash
# Slack webhook (add to backup script)
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

send_slack_alert() {
    local message="$1"
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"$message\"}" \
        "$SLACK_WEBHOOK"
}

# On failure:
# send_slack_alert "🚨 KoNote backup failed at $DATE. Check server logs."

# On success (optional, for peace of mind):
# send_slack_alert "✅ KoNote backup completed: $DATE"
```

```powershell
# Teams webhook (Windows PowerShell)
$TeamsWebhook = "https://outlook.office.com/webhook/YOUR/WEBHOOK/URL"

function Send-TeamsAlert {
    param($Message)
    $Body = @{ text = $Message } | ConvertTo-Json
    Invoke-RestMethod -Uri $TeamsWebhook -Method Post -Body $Body -ContentType "application/json"
}

# On failure:
# Send-TeamsAlert "🚨 KoNote backup failed at $Date. Check server logs."
```

#### Simple Health Check (Monitor Backup Recency)

Create a script that checks if backups are recent. Run this weekly or use a monitoring service.

**Windows PowerShell:**

```powershell
# Check if backups are fresh (run weekly via Task Scheduler)
$BackupDir = "C:\Backups\KoNote"
$MaxAge = 2  # Alert if no backup in last 2 days

$LatestBackup = Get-ChildItem -Path $BackupDir -Filter "backup_main_*.sql" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $LatestBackup) {
    Send-BackupAlert -Subject "KoNote: NO BACKUPS FOUND" -Body "No backup files exist in $BackupDir"
    exit 1
}

$Age = (Get-Date) - $LatestBackup.LastWriteTime

if ($Age.Days -ge $MaxAge) {
    Send-BackupAlert -Subject "KoNote: STALE BACKUP" `
        -Body "Latest backup is $($Age.Days) days old: $($LatestBackup.Name)"
    exit 1
}

Write-Host "Backup health check passed. Latest: $($LatestBackup.Name)"
```

**Linux/Mac:**

```bash
#!/bin/bash
# Check if backups are fresh

BACKUP_DIR="/backups/KoNote"
MAX_AGE_DAYS=2
ADMIN_EMAIL="admin@yourorg.ca"

LATEST=$(find "$BACKUP_DIR" -name "backup_main_*.sql" -mtime -$MAX_AGE_DAYS | head -1)

if [ -z "$LATEST" ]; then
    echo "No recent backup found" | mail -s "KoNote: STALE BACKUP" "$ADMIN_EMAIL"
    exit 1
fi

echo "Backup health check passed"
```

---

## Backup Retention Policy

We recommend keeping backups for at least **30 days** to recover from data corruption or user errors.

### Suggested Strategy

| Backup Type | Frequency | Retention | Notes |
|-------------|-----------|-----------|-------|
| **Daily backups** | Every night | 30 days | Automated via cron or Railway |
| **Weekly** | Every Monday | 90 days | Keep one per week for long-term recovery |
| **Monthly** | First of month | 1 year | Compliance and audit trail |

Example cron job for 30-day retention:

```bash
# In backup script, after backing up:
find /backups/KoNote -name "backup_*.sql" -mtime +30 -delete
```

---

## Testing Your Backups

**Untested backups are useless.** Verify your backups work:

### Test on Docker Compose (Recommended)

1. Make a copy of your backup files to a test directory
2. Create a separate Docker Compose file for testing (don't use the production one):

```yaml
# docker-compose.test.yml
services:
  db_test:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=konote_test
      - POSTGRES_USER=konote
      - POSTGRES_PASSWORD=konote
    ports:
      - "5433:5432"

  audit_db_test:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=konote_audit_test
      - POSTGRES_USER=audit_writer
      - POSTGRES_PASSWORD=audit_pass
    ports:
      - "5434:5432"
```

3. Start the test databases:

```bash
docker compose -f docker-compose.test.yml up -d
```

4. Restore your backups:

```bash
docker compose -f docker-compose.test.yml exec -T db_test psql -U konote konote_test < backup_main_2026-02-02.sql
docker compose -f docker-compose.test.yml exec -T audit_db_test psql -U audit_writer konote_audit_test < backup_audit_2026-02-02.sql
```

5. Verify the data:

```bash
docker compose -f docker-compose.test.yml exec db_test psql -U konote konote_test -c "SELECT count(*) FROM public.auth_user;"
```

6. Clean up:

```bash
docker compose -f docker-compose.test.yml down -v
```

---

## Troubleshooting

### "pg_dump: command not found"

**Docker Compose:** `pg_dump` is inside the container. Use `docker compose exec db pg_dump ...`

**Plain PostgreSQL:** Install PostgreSQL client tools:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# Mac (Homebrew)
brew install postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### "password authentication failed"

Check your username and password:

- **Docker Compose main DB**: username `konote`, password `konote` (or check `docker-compose.yml`)
- **Docker Compose audit DB**: username `audit_writer`, password `audit_pass`
- **Railway**: Use `railway run` — credentials come from environment
- **Azure**: Check Azure portal for connection string

### "database does not exist"

Verify the database name:

```bash
# Docker Compose
docker compose exec db psql -U konote -l
```

This lists all databases. Look for `konote` and `konote_audit`.

### Restore Takes a Long Time

Large databases (100+ MB) can take several minutes to restore. This is normal. Monitor progress:

```bash
# In another terminal, watch the file size grow
watch -n 1 'du -sh /path/to/backup/file'
```

### Lost the Encryption Key

**Data encrypted with a lost key cannot be recovered.**

If you have database backups made before the key was lost, and you still have a copy of the old key, restore from that backup. Otherwise:

1. Consult your team's access control procedures
2. If running on Azure or Railway, check if they have access logs or key rotation history
3. Consider declaring the encrypted data as compromised and implementing access controls

---

## Checklist: Before Going to Production

- [ ] Test backup script on a non-production machine
- [ ] Test restore on a separate database instance
- [ ] Document your backup schedule and retention policy
- [ ] Store encryption key in a secure vault (not with backups)
- [ ] Set up automated backups (cron, Railway, or Azure)
- [ ] Enable backups on Railway or Azure if using those services
- [ ] Verify backups appear in logs/dashboards
- [ ] Brief your team on where backups are stored and how to restore
- [ ] Create a runbook for emergency restore (this document + site-specific details)

---

## Questions?

For database-specific issues, see:
- PostgreSQL docs: https://www.postgresql.org/docs/16/
- Railway backups: https://docs.railway.app/databases/postgresql
- Azure PostgreSQL: https://learn.microsoft.com/en-us/azure/postgresql/
