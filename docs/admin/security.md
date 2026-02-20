# Security

Encryption, audit logs, data erasure, incident response, and backup/restore procedures.

---

## Backup and Restore

KoNote stores data in **two PostgreSQL databases**:
- **Main database** -- participants, programs, plans, notes
- **Audit database** -- immutable log of every change

### Critical: The Encryption Key

**If you lose `FIELD_ENCRYPTION_KEY`, all encrypted participant data is permanently unrecoverable.**

Store it separately from database backups:
- Password manager (1Password, Bitwarden)
- Azure Key Vault
- Encrypted file with restricted access

**Never store it:**
- In the same location as database backups
- In version control (Git)
- In plain text on shared drives

---

### Manual Backup

**Docker Compose:**
```bash
# Main database
docker compose exec db pg_dump -U konote konote > backup_main_$(date +%Y-%m-%d).sql

# Audit database
docker compose exec audit_db pg_dump -U audit_writer konote_audit > backup_audit_$(date +%Y-%m-%d).sql
```

**Plain PostgreSQL:**
```bash
pg_dump -h hostname -U konote -d konote > backup_main_$(date +%Y-%m-%d).sql
pg_dump -h hostname -U audit_writer -d konote_audit > backup_audit_$(date +%Y-%m-%d).sql
```

### Automated Backups

**Windows Task Scheduler:**

Save as `C:\KoNote\backup_KoNote.ps1`:

```powershell
$BackupDir = "C:\Backups\KoNote"
$KoNoteDir = "C:\KoNote\KoNote-web"
$Date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir -Force }

Set-Location $KoNoteDir

# Main database
docker compose exec -T db pg_dump -U konote konote | Out-File -FilePath "$BackupDir\backup_main_$Date.sql" -Encoding utf8

# Audit database
docker compose exec -T audit_db pg_dump -U audit_writer konote_audit | Out-File -FilePath "$BackupDir\backup_audit_$Date.sql" -Encoding utf8

# Clean up backups older than 30 days
Get-ChildItem -Path $BackupDir -Filter "backup_*.sql" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force
```

Schedule via Task Scheduler to run daily at 2:00 AM.

**Linux/Mac Cron:**

Save as `/home/user/backup_KoNote.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/KoNote"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

mkdir -p "$BACKUP_DIR"

docker compose -f /path/to/KoNote-web/docker-compose.yml exec -T db pg_dump -U konote konote > "$BACKUP_DIR/backup_main_$DATE.sql"
docker compose -f /path/to/KoNote-web/docker-compose.yml exec -T audit_db pg_dump -U audit_writer konote_audit > "$BACKUP_DIR/backup_audit_$DATE.sql"

# Clean up old backups
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +30 -delete
```

Add to crontab: `0 2 * * * /home/user/backup_KoNote.sh`

### Cloud Provider Backups

- **Railway:** Automatic daily backups (7 days retention). Restore via dashboard.
- **Azure:** Automatic backups. Configure retention in PostgreSQL server settings.
- **Elestio:** Configure via dashboard or use managed PostgreSQL.

### Restore from Backup

**Docker Compose:**
```bash
# Stop containers
docker compose down

# Remove old volumes (WARNING: deletes current data)
docker volume rm KoNote-web_pgdata KoNote-web_audit_pgdata

# Start fresh containers
docker compose up -d

# Wait 10 seconds, then restore
docker compose exec -T db psql -U konote konote < backup_main_2026-02-03.sql
docker compose exec -T audit_db psql -U audit_writer konote_audit < backup_audit_2026-02-03.sql
```

### Backup Retention Policy

| Type | Frequency | Retention |
|------|-----------|-----------|
| Daily | Every night | 30 days |
| Weekly | Every Monday | 90 days |
| Monthly | First of month | 1 year |

---

## Security Operations

### Quick Reference

| Task | Command |
|------|---------|
| Basic check | `python manage.py check` |
| Deployment check | `python manage.py check --deploy` |
| Security audit | `python manage.py security_audit` |
| Run security tests | `pytest tests/test_security.py tests/test_rbac.py -v` |

---

### Security Checks

KoNote runs security checks automatically. You can also run them explicitly:

```bash
python manage.py check --deploy
```

**Check IDs:**

| ID | Severity | What It Checks |
|----|----------|----------------|
| `KoNote.E001` | Error | Encryption key exists and valid |
| `KoNote.E002` | Error | Security middleware loaded |
| `KoNote.W001` | Warning | DEBUG=True in production |
| `KoNote.W002` | Warning | Session cookies not secure |
| `KoNote.W003` | Warning | CSRF cookies not secure |

Errors prevent server start. Warnings indicate security gaps.

---

### Security Audit

For deeper analysis:

```bash
python manage.py security_audit
```

This checks encryption, access controls, audit logging, and configuration.

**Categories:**
- `ENC` -- Encryption (key validity, ciphertext verification)
- `RBAC` -- Role-based access control
- `AUD` -- Audit logging
- `CFG` -- Configuration (DEBUG, cookies, middleware)

---

### Audit Logging

Every significant action is logged to a separate audit database.

**What gets logged:**
- Login/Logout (user, timestamp, IP, success/failure)
- Participant file views (who viewed which participant)
- Create/Update/Delete (what changed, old/new values)
- Exports (who exported what)
- Admin actions (settings changes, user management)

**View audit logs:**
1. Log in as Admin
2. Click **Manage** -> **Audit Logs**
3. Filter by date, user, or action type

**Query audit database directly:**
```sql
SELECT event_timestamp, user_display, action, resource_type
FROM audit_auditlog
ORDER BY event_timestamp DESC
LIMIT 20;
```

---

### Encryption Key Management

`FIELD_ENCRYPTION_KEY` encrypts all PII:
- Participant names (first, middle, last, preferred)
- Email addresses
- Phone numbers
- Dates of birth
- Sensitive custom fields

**Rotating the key:**

```bash
# 1. Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Rotate (re-encrypts all data)
python manage.py rotate_encryption_key --old-key="OLD" --new-key="NEW"

# 3. Update .env with new key
# 4. Restart application
# 5. Verify it works
# 6. Securely delete old key
```

**Rotation schedule:**
- Every 90 days (baseline)
- When staff with key access leave (immediately)
- After suspected security incident (immediately)

---

### Pre-Deployment Checklist

**Required:**
- [ ] `FIELD_ENCRYPTION_KEY` set to unique generated key
- [ ] `SECRET_KEY` set to unique generated key
- [ ] `DEBUG=False`
- [ ] `python manage.py check --deploy` passes

**Strongly recommended:**
- [ ] `SESSION_COOKIE_SECURE=True` (requires HTTPS)
- [ ] `CSRF_COOKIE_SECURE=True` (requires HTTPS)
- [ ] HTTPS configured
- [ ] Encryption key backed up separately from database
- [ ] All test users removed

---

### Incident Response

**Suspected data breach:**
1. Rotate encryption key immediately
2. Rotate SECRET_KEY (invalidates all sessions)
3. Review audit logs for unauthorized access
4. Document timeline
5. Notify affected parties per PIPEDA/GDPR (typically within 72 hours)

**Lost encryption key:**
- Encrypted PII fields are **permanently unrecoverable**
- Non-PII data (notes, metrics) remains accessible
- Consider this a data loss incident for compliance

**Suspicious login activity:**
```sql
SELECT event_timestamp, ip_address, metadata
FROM audit_auditlog
WHERE action = 'login_failed'
ORDER BY event_timestamp DESC;
```

---

## Data Retention

### Why Participants Can't Be Deleted (by Default)

KoNote intentionally **does not allow deleting participants through normal use**. This is a safety feature, not a limitation.

**Why this matters:**

| Concern | How KoNote handles it |
|---------|----------------------|
| Accidental deletion | Not possible -- there is no delete button in normal workflows |
| Audit trail | Participant history stays intact for compliance |
| Funder reporting | Historical data remains available for reporting |
| Data recovery | No need to restore backups for "oops" moments |

**Instead of deleting, use these approaches:**

| Scenario | What to do |
|----------|------------|
| Participant leaves program | **Discharge** them -- status changes to "Discharged" |
| Participant no longer active | Set status to **"Inactive"** |
| Entered by mistake | Mark as "Inactive" and add a note explaining the error |
| Participant requests data deletion (PIPEDA/GDPR) | Use the **Erase Client Data** workflow on the participant detail page. Requires multi-PM approval. See `docs/security-operations.md#erasure-workflow-security`. |

Discharged and inactive participants:
- Do not appear in active participant lists
- Remain searchable for historical reference
- Keep all notes, plans, and events intact
- Can be reactivated if the participant returns

**Exception -- legally required erasure:** For PIPEDA/GDPR right-to-erasure requests, KoNote provides a formal erasure workflow. This requires approval from all program managers for the participant's enrolled programs, permanently deletes the participant's data, and preserves an audit record with record counts only (no PII). See `docs/security-operations.md#erasure-workflow-security` for the full state machine and invariants.

### GDPR/PIPEDA Right to Erasure

Some privacy regulations require the ability to permanently delete personal data upon request.

**How it works:** Any staff member can request erasure from a participant's detail page. The request then requires approval from a program manager in each of the participant's enrolled programs. Once all approvals are received, the participant's data is permanently deleted and an audit record is preserved.

**Steps:**
1. Navigate to the participant's detail page and click **Erase Client Data**
2. Select a reason category and provide details (do not include participant names)
3. Submit the request -- program managers are notified by email
4. Each relevant program manager reviews and approves or rejects
5. Once all approvals are received, the data is permanently erased

**Important:** This action cannot be undone. Recovery requires a database backup. All erasure requests, approvals, and deletions are logged in the audit trail for PIPEDA compliance.

---

[Back to Admin Guide](index.md)
