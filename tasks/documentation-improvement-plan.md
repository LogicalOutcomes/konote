# Documentation Improvement Plan

**Goal:** Make KoNote adoption-ready for organizations cloning from a public GitHub repository.

**Problem:** The current documentation is deployment-ready but development-unfriendly. Organizations can deploy to Railway/Azure/Elestio, but struggle with local setup, environment configuration, and security testing.

---

## Proposed Documentation Structure

### Three New/Enhanced Files

| File | Purpose | Priority |
|------|---------|----------|
| **README.md** (enhanced) | Quick overview + links to detailed guides | High |
| **docs/getting-started.md** (new) | Complete local development setup | High |
| **docs/security-operations.md** (new) | Security testing, audits, and key management | High |

---

## 1. README.md Enhancements

The current README has a Quick Start section, but it's missing critical details that cause the `KoNote.E001` error and other setup failures.

### Current Gap
```
4. **Create environment file**
   Copy `.env.example` to `.env` and configure:
   SECRET_KEY=your-secret-key
   FIELD_ENCRYPTION_KEY=your-fernet-key
```

This tells you *what* to set but not *how* to generate the values.

### Proposed Changes

1. **Add key generation commands directly in Quick Start:**
   ```markdown
   4. **Create environment file**

      Copy the example file:
      ```bash
      copy .env.example .env   # Windows
      # cp .env.example .env   # macOS/Linux
      ```

      Generate required keys:
      ```bash
      # Generate SECRET_KEY
      python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

      # Generate FIELD_ENCRYPTION_KEY (required for PII encryption)
      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
      ```

      Paste both values into your `.env` file.
   ```

2. **Add troubleshooting callout:**
   ```markdown
   > ⚠️ **Getting `KoNote.E001` error?** Your encryption key is missing or invalid.
   > See [Getting Started Guide](docs/getting-started.md#environment-configuration) for detailed setup.
   ```

3. **Add link to new security operations guide:**
   ```markdown
   | [Security Operations](docs/security-operations.md) | Run security checks, view audit logs, rotate keys |
   ```

4. **Update Documentation table** to include new guides

---

## 2. docs/getting-started.md (New File)

A comprehensive guide for first-time local setup. Target audience: Someone cloning the repo who has never worked with Django before.

### Proposed Structure

```markdown
# Getting Started with KoNote

This guide walks you through setting up KoNote for local development on Windows, macOS, or Linux.

## Prerequisites

### Required Software
- Python 3.12 or higher
- PostgreSQL 16 or higher
- Git

### Windows-Specific Setup
[Instructions for installing Python, PostgreSQL on Windows]

### macOS-Specific Setup
[Instructions using Homebrew]

### Linux-Specific Setup
[Instructions for Ubuntu/Debian]

## Step 1: Clone the Repository

## Step 2: Create Virtual Environment

## Step 3: Install Dependencies

## Step 4: Set Up PostgreSQL

### Create the Main Database
### Create the Audit Database
### Create Database Users

## Step 5: Environment Configuration

### Required Variables (Will Not Start Without These)

| Variable | Purpose | How to Generate |
|----------|---------|-----------------|
| `SECRET_KEY` | Django session security | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `FIELD_ENCRYPTION_KEY` | Encrypts client PII (names, emails, DOB) | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DATABASE_URL` | Main database connection | `postgresql://username:password@localhost:5432/konote` |
| `AUDIT_DATABASE_URL` | Audit log database connection | `postgresql://username:password@localhost:5432/konote_audit` |

### Optional Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AUTH_MODE` | `local` or `azure` | `local` |
| `DEBUG` | Show detailed errors | `True` in development |
| `ALLOWED_HOSTS` | Domains that can access | `localhost,127.0.0.1` |

### Complete .env Example
[Full example with all variables filled in]

## Step 6: Run Migrations

## Step 7: Create Initial User

## Step 8: Start the Server

## Step 9: Verify Your Setup

### Expected Behaviour
- Login page loads at http://localhost:8000
- You can log in with your superuser
- No errors in the terminal

### Run Security Checks
```bash
python manage.py check
```
All checks should pass. If you see `KoNote.E001`, your encryption key is missing.

## Troubleshooting

### KoNote.E001: FIELD_ENCRYPTION_KEY not configured
**Cause:** Your `.env` file is missing or has an empty `FIELD_ENCRYPTION_KEY`.
**Fix:** Generate a key and add it to `.env`:
[command]

### KoNote.E002: Security middleware missing
**Cause:** Custom middleware not in settings.
**Fix:** This shouldn't happen with default settings. Check `konote/settings/development.py`.

### Database connection refused
**Cause:** PostgreSQL not running or wrong credentials.
**Fix:** [steps]

### Module not found errors
**Cause:** Virtual environment not activated or dependencies not installed.
**Fix:** [steps]

## Next Steps

- [Agency Setup Guide](agency-setup.md) — Configure terminology, features, and programs
- [Security Operations](security-operations.md) — Run security audits and understand audit logs
- [Technical Documentation](technical-documentation.md) — Architecture deep dive
```

---

## 3. docs/security-operations.md (New File)

A practical guide for running security checks, understanding audit logs, and managing encryption keys.

### Proposed Structure

```markdown
# Security Operations Guide

KoNote includes automated security checks and comprehensive audit logging. This guide explains how to use them.

## Security Checks

KoNote runs security checks automatically with every `manage.py` command. You can also run them explicitly.

### Quick Check (Development)
```bash
python manage.py check
```

### Full Security Check (Before Deployment)
```bash
python manage.py check --deploy
```

### Security Audit Command
```bash
python manage.py security_audit
python manage.py security_audit --verbose  # Detailed output
```

## Understanding Check Results

### Check IDs and What They Mean

| ID | Severity | Meaning | How to Fix |
|----|----------|---------|------------|
| `KoNote.E001` | Error | Encryption key missing or invalid | Generate and add `FIELD_ENCRYPTION_KEY` to `.env` |
| `KoNote.E002` | Error | Security middleware not loaded | Check `MIDDLEWARE` in settings |
| `KoNote.W001` | Warning | DEBUG=True (deploy only) | Set `DEBUG=False` in production |
| `KoNote.W002` | Warning | Cookies not secure (deploy only) | Set `SESSION_COOKIE_SECURE=True` |
| `KoNote.W003` | Warning | CSRF cookie not secure | Set `CSRF_COOKIE_SECURE=True` |
| `KoNote.W004` | Warning | Argon2 not primary hasher | Add Argon2 to `PASSWORD_HASHERS` |

### Example: Passing Check
```
System check identified no issues (0 silenced).
```

### Example: Failing Check
```
SystemCheckError: System check identified some issues:

ERRORS:
?: (KoNote.E001) FIELD_ENCRYPTION_KEY is not configured.
    HINT: Set FIELD_ENCRYPTION_KEY environment variable to a valid Fernet key.
```

## Running Security Tests

KoNote has automated security tests that verify RBAC, encryption, and audit logging.

### Run All Security Tests
```bash
pytest tests/test_security.py tests/test_rbac.py tests/test_encryption.py -v
```

### What Each Test File Covers

| File | What It Tests |
|------|---------------|
| `test_security.py` | CSRF, headers, session security, input validation |
| `test_rbac.py` | Role permissions, program access, admin restrictions |
| `test_encryption.py` | PII field encryption, key validation |

### Example Output
[Show what passing tests look like]

## Audit Logging

Every significant action in KoNote is logged to a separate audit database.

### What Gets Logged
- User logins and logouts
- Client record views and edits
- Note creation and modification
- Permission changes
- Administrative actions

### Viewing Audit Logs

#### Through the Web Interface
1. Log in as an Admin
2. Go to Admin Settings → Audit Logs
3. Filter by date, user, or action type

#### Through the Database
```sql
-- Connect to audit database
psql -d konote_audit

-- Recent audit entries
SELECT timestamp, user_email, action, details
FROM audit_auditlog
ORDER BY timestamp DESC
LIMIT 20;

-- Actions by a specific user
SELECT timestamp, action, details
FROM audit_auditlog
WHERE user_email = 'staff@example.com'
ORDER BY timestamp DESC;

-- Client record access
SELECT timestamp, user_email, details
FROM audit_auditlog
WHERE action = 'client.view'
ORDER BY timestamp DESC;
```

### Audit Log Retention
[How long logs are kept, archival procedures]

## Encryption Key Management

### About the Encryption Key

`FIELD_ENCRYPTION_KEY` encrypts all personally identifiable information (PII) in the database:
- Client names (first, last, preferred)
- Email addresses
- Phone numbers
- Dates of birth
- Custom fields marked as sensitive

**⚠️ CRITICAL:** If you lose this key, encrypted data is unrecoverable.

### Backing Up Your Key

Store your encryption key separately from database backups:
- Password manager (1Password, Bitwarden)
- Azure Key Vault / AWS Secrets Manager
- Encrypted USB drive in a safe

Never store the key:
- In the same location as database backups
- In version control (Git)
- In plain text on shared drives

### Rotating the Encryption Key

If you suspect your key has been compromised:

```bash
# 1. Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Run rotation command (re-encrypts all data)
python manage.py rotate_encryption_key --old-key="YOUR_OLD_KEY" --new-key="YOUR_NEW_KEY"

# 3. Update .env with new key
# 4. Restart application
# 5. Securely delete old key
```

### Key Rotation Schedule

For compliance, rotate encryption keys:
- Every 90 days (recommended)
- Immediately after any staff with key access leaves
- After any suspected security incident

## Pre-Deployment Security Checklist

Before going to production, verify:

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` is unique and not in version control
- [ ] `FIELD_ENCRYPTION_KEY` is backed up securely
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] HTTPS is configured
- [ ] Audit database is on separate server or has restricted access
- [ ] `python manage.py check --deploy` passes with no errors
- [ ] `python manage.py security_audit` shows no critical issues

## Incident Response

### Suspected Data Breach

1. Immediately rotate `FIELD_ENCRYPTION_KEY`
2. Rotate `SECRET_KEY` (invalidates all sessions)
3. Review audit logs for unauthorized access
4. Notify affected parties per PIPEDA/GDPR requirements
5. Document timeline and response actions

### Lost Encryption Key

If you've lost your encryption key and have no backup:
- Encrypted PII fields are unrecoverable
- You'll need to re-enter client information manually
- Consider this a data loss incident for compliance purposes

## Further Reading

- [Technical Documentation](technical-documentation.md) — Security architecture details
- [Backup & Restore](backup-restore.md) — Database backup procedures
- [SECURITY.md](../SECURITY.md) — Security policy and vulnerability reporting
```

---

## Implementation Plan

### Phase 1: Critical (Do First)

| Task | File | Est. Lines |
|------|------|------------|
| Create getting-started.md | `docs/getting-started.md` | ~350 |
| Create security-operations.md | `docs/security-operations.md` | ~300 |
| Update README Quick Start | `README.md` | ~30 changes |
| Add inline comments to .env.example | `.env.example` | ~20 |

### Phase 2: Polish

| Task | File |
|------|------|
| Add troubleshooting section to deployment guides | `docs/deploy-*.md` |
| Cross-link all documentation | All docs |
| Add "Expected Output" sections | New guides |

---

## Success Criteria

A new developer should be able to:

1. Clone the repository
2. Follow `docs/getting-started.md` without external help
3. Have a working local environment in under 30 minutes
4. Run `python manage.py check` with no errors
5. Run security tests and understand the output
6. Know where to find help when something goes wrong

---

## Decisions Made

1. **Docker-based local development:** Yes, include as an alternative path for users who prefer containers over manual PostgreSQL setup.

2. **Test fixtures documentation:** Brief overview only. A one-paragraph explanation of what the test database contains (sample users, programs, clients) is enough. Detailed field-by-field documentation is developer-focused and can be added later if requested.

3. **Compliance mapping:** High-level principles with disclaimer. Include a "Privacy Compliance Support" section that:
   - Lists KoNote's security features
   - Maps them to general privacy principles (not specific PIPEDA sections)
   - Explicitly states this is not legal advice
   - Links to official guidance (Office of the Privacy Commissioner of Canada)
   - Recommends consulting privacy officers for jurisdiction-specific requirements
