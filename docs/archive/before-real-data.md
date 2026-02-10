# Before You Enter Real Data

A checkpoint to verify your KoNote setup is ready for actual client information.

**Why this matters:** Once you enter real client data, their names, emails, and personal information are encrypted with your `FIELD_ENCRYPTION_KEY`. If that key is lost and you don't have it backed up, that data is gone forever. This checklist ensures you're protected.

---

## Pre-Data Checklist

Complete these items before entering any real client information:

### 1. Encryption Key Backup

- [ ] I have copied my `FIELD_ENCRYPTION_KEY` to a secure location
- [ ] The backup is stored separately from my database backups
- [ ] I can access this backup without logging into KoNote

**Where to store it:**
- Password manager (1Password, Bitwarden, LastPass)
- Encrypted document on a separate drive
- Secure note in your organization's key management system

> **Test yourself:** Close this document. Can you retrieve your encryption key from your backup location? If not, fix that now.

---

### 2. Database Backups Configured

- [ ] I know how backups will happen (manual, scheduled, or hosting provider)
- [ ] I have tested restoring from a backup at least once
- [ ] Backups are stored in a different location than the database

**For Docker users:** See [Backup and Restore Guide](backup-restore.md)

**For hosted deployments:** Your provider (Railway, Azure, Elestio) likely handles backups automatically. Verify this in their dashboard.

---

### 3. User Accounts Set Up

- [ ] I have created accounts for all staff who will use KoNote
- [ ] Each user has the correct role (Admin, Case Manager, Front Desk)
- [ ] Test users and demo accounts have been removed or disabled

**Why this matters:** Front desk staff can only see limited client information. Case managers can see full details for their clients. Make sure roles are assigned correctly.

---

### 4. Security Settings Verified

Run this command to verify your security configuration:

```bash
# Docker users:
docker-compose exec web python manage.py check --deploy

# Manual setup:
python manage.py check --deploy
```

**Expected result:** You may see some warnings about HTTPS (that's okay for local development). You should NOT see any errors about:
- `FIELD_ENCRYPTION_KEY`
- `SECRET_KEY`
- `CSRF` settings

---

### 5. Test Data Cleared (Optional)

If you experimented with test clients during setup:

- [ ] Delete test clients, or
- [ ] Start fresh with `docker-compose down -v && docker-compose up -d` (Docker), or
- [ ] Recreate the database (Manual setup)

**Note:** Starting fresh means running migrations and creating your admin user again. Only do this if you haven't entered any data you want to keep.

---

## Quick Security Refresher

Before entering sensitive data, remember:

| What's Protected | How It's Protected |
|------------------|-------------------|
| Client names, emails, birth dates | Encrypted in database with `FIELD_ENCRYPTION_KEY` |
| User sessions | Protected by `SECRET_KEY` |
| Who changed what | Recorded in separate audit database |
| Screen access | Role-based permissions (Admin, Case Manager, Front Desk) |

**What's NOT encrypted:**
- Program names and descriptions
- Note text (the content of progress notes)
- Metric values and targets

If your organization requires note content to be encrypted, contact a developer to discuss options.

---

## Final Sign-Off

Before proceeding, confirm:

- [ ] I have verified my encryption key is backed up and retrievable
- [ ] I understand that losing my encryption key means losing client PII
- [ ] My team has been trained on data entry procedures
- [ ] I know who to contact if something goes wrong

---

## Ready to Go

Once you've completed this checklist:

1. **[Agency Setup Guide](agency-setup.md)** — Configure terminology, programs, and custom fields
2. **[Security Operations](security-operations.md)** — Ongoing security checks and audit logs

---

## Need Help?

- **Lost your encryption key?** If you haven't entered real data yet, generate a new one. If you have, contact a developer immediately.
- **Backup questions?** See [Backup and Restore Guide](backup-restore.md)
- **Security concerns?** See [SECURITY.md](../SECURITY.md) for reporting vulnerabilities
