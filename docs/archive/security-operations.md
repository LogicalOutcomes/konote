# Security Operations Guide

KoNote includes automated security checks and comprehensive audit logging to help you protect client data and meet compliance requirements. This guide explains how to use these tools.

---

## Quick Reference

| Task | Command |
|------|---------|
| Basic security check | `python manage.py check` |
| Full deployment check | `python manage.py check --deploy` |
| Security audit | `python manage.py security_audit` |
| Detailed audit | `python manage.py security_audit --verbose` |
| Run security tests | `pytest tests/test_security.py tests/test_rbac.py -v` |

---

## Security Checks

KoNote runs security checks automatically with every `manage.py` command (runserver, migrate, etc.). You can also run them explicitly.

### Basic Check (Development)

```bash
python manage.py check
```

This runs Django's system checks plus KoNote's custom security checks. All checks must pass for the server to start.

**Expected output (success):**
```
System check identified no issues (0 silenced).
```

**Example failure:**
```
SystemCheckError: System check identified some issues:

ERRORS:
?: (KoNote.E001) FIELD_ENCRYPTION_KEY is not configured.
    HINT: Set FIELD_ENCRYPTION_KEY environment variable to a valid Fernet key.
```

### Deployment Check (Before Going Live)

```bash
python manage.py check --deploy
```

This adds deployment-specific checks for production security settings (HTTPS cookies, DEBUG mode, etc.).

### Check IDs and What They Mean

| ID | Severity | What It Checks | How to Fix |
|----|----------|----------------|------------|
| `KoNote.E001` | Error | Encryption key exists and is valid | Generate key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and add to `.env` |
| `KoNote.E002` | Error | Security middleware is loaded | Check `MIDDLEWARE` in settings includes `ProgramAccessMiddleware` and `AuditMiddleware` |
| `KoNote.W001` | Warning | DEBUG=True (deploy check only) | Set `DEBUG=False` in production |
| `KoNote.W002` | Warning | Session cookies not secure | Set `SESSION_COOKIE_SECURE=True` when using HTTPS |
| `KoNote.W003` | Warning | CSRF cookies not secure | Set `CSRF_COOKIE_SECURE=True` when using HTTPS |
| `KoNote.W004` | Warning | Argon2 not primary hasher | Add `Argon2PasswordHasher` first in `PASSWORD_HASHERS` |

**Errors (E)** prevent the server from starting.
**Warnings (W)** allow the server to start but indicate security gaps.

---

## Security Audit Command

For deeper security analysis, use the `security_audit` management command. This checks encryption, access controls, audit logging, configuration, and document storage.

### Basic Audit

```bash
python manage.py security_audit
```

**Example output:**
```
KoNote Security Audit
==================================================

[ENC] Encryption Checks
  [PASS] ENC001 Encryption key configured — Valid Fernet key
  [PASS] ENC002 Encryption round-trip successful
  [PASS] ENC003 No plaintext in encrypted fields — Scanned 147 records
  [PASS] ENC004 Sensitive custom fields encrypted — 2 sensitive fields checked

[RBAC] Access Control Checks
  [PASS] RBAC001 Non-admin users have program roles
  [PASS] RBAC002 No orphaned program enrolments
  [PASS] RBAC003 Role values valid

[AUD] Audit Log Checks
  [PASS] AUD001 Audit database accessible — 1,247 total entries
  [PASS] AUD002 Recent audit entries exist — 83 entries in last 24h
  [PASS] AUD003 Client view logging active — 412 view entries
  [PASS] AUD004 State-change logging active — 298 state-change entries

[CFG] Configuration Checks
  [WARN] CFG001 DEBUG disabled — DEBUG=True (should be False in production)
  [PASS] CFG002 SECRET_KEY not default
  [WARN] CFG003 Session cookies secure — SESSION_COOKIE_SECURE=False
  [WARN] CFG004 CSRF cookies secure — CSRF_COOKIE_SECURE=False
  [PASS] CFG005 Argon2 password hasher configured
  [PASS] CFG006 Security middleware in chain

--------------------------------------------------
Passed: 14, Warnings: 3

⚠ Security audit passed with warnings
```

### Verbose Mode

For detailed output including scanned records:

```bash
python manage.py security_audit --verbose
```

### Check Specific Categories

Run only certain check categories:

```bash
python manage.py security_audit --category=ENC,RBAC
```

Available categories:
- `ENC` — Encryption (key validity, ciphertext verification)
- `RBAC` — Role-based access control (user roles, enrolments)
- `AUD` — Audit logging (database access, recent entries)
- `CFG` — Configuration (DEBUG, cookies, middleware)
- `DOC` — Document storage (URL templates, domain allowlist)

### JSON Output (For Automation)

```bash
python manage.py security_audit --json
```

Outputs machine-readable JSON for CI/CD pipelines.

### Fail on Warnings (For CI)

```bash
python manage.py security_audit --fail-on-warn
```

Exits with code 1 if any warnings are present. Use this in CI pipelines to enforce strict security.

---

## Running Security Tests

KoNote includes automated tests that verify security properties. These tests create temporary data that is cleaned up automatically.

### Run All Security Tests

```bash
pytest tests/test_security.py tests/test_rbac.py tests/test_encryption.py -v
```

### What Each Test File Covers

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_security.py` | PII exposure | Client data not in database plaintext, encryption round-trip, ciphertext validation |
| `test_rbac.py` | 19 tests | Role permissions, front desk access control, program restrictions, admin-only routes |
| `test_htmx_errors.py` | 21 tests | Error responses, HTMX partials, form validation feedback |
| `test_encryption.py` | Key validation | Fernet key format, encrypt/decrypt functions |

### Example Test Run

```bash
pytest tests/test_security.py -v
```

**Expected output:**
```
tests/test_security.py::PIIExposureTest::test_client_name_not_in_database_plaintext PASSED
tests/test_security.py::PIIExposureTest::test_encrypted_field_contains_ciphertext PASSED
tests/test_security.py::PIIExposureTest::test_property_accessor_decrypts_correctly PASSED
tests/test_security.py::RBACBypassTest::test_staff_cannot_access_other_program PASSED
tests/test_security.py::RBACBypassTest::test_admin_route_blocked_for_staff PASSED
...
```

### Test Data

The test suite creates temporary users, programs, and clients to verify security properties. This data exists only during test execution and is automatically deleted afterward. It does not affect your real database.

---

## Audit Logging

Every significant action in KoNote is logged to a separate audit database. This provides an immutable record for compliance and incident investigation.

### What Gets Logged

| Action | Logged Data |
|--------|-------------|
| Login/Logout | User, timestamp, IP address, success/failure |
| Client view | Who viewed which client, when |
| Create/Update/Delete | What changed, old values, new values |
| Exports | Who exported what data |
| Admin actions | Settings changes, user management |

### Viewing Audit Logs

#### Through the Web Interface

1. Log in as an Admin
2. Click **Admin** in the navigation
3. Select **Audit Logs**
4. Use filters to narrow by date, user, or action type

#### Through the Database

Connect to the audit database and run queries:

```bash
# Connect to audit database (adjust credentials as needed)
psql -d konote_audit -U audit_writer
```

**Recent entries:**
```sql
SELECT event_timestamp, user_display, action, resource_type, resource_id
FROM audit_auditlog
ORDER BY event_timestamp DESC
LIMIT 20;
```

**Activity by a specific user:**
```sql
SELECT event_timestamp, action, resource_type, resource_id
FROM audit_auditlog
WHERE user_display = 'jsmith@agency.org'
ORDER BY event_timestamp DESC;
```

**Client record access in last 7 days:**
```sql
SELECT event_timestamp, user_display, resource_id
FROM audit_auditlog
WHERE action = 'view'
  AND resource_type = 'client'
  AND event_timestamp > NOW() - INTERVAL '7 days'
ORDER BY event_timestamp DESC;
```

**Failed login attempts:**
```sql
SELECT event_timestamp, ip_address, metadata
FROM audit_auditlog
WHERE action = 'login_failed'
ORDER BY event_timestamp DESC;
```

### Audit Database Security

The audit database is designed to be append-only:

- The `audit_writer` user should have INSERT permission only (no UPDATE or DELETE)
- This prevents tampering with audit records
- Configure this in PostgreSQL when setting up the audit database

---

## Encryption Key Management

### About the Encryption Key

`FIELD_ENCRYPTION_KEY` encrypts all personally identifiable information (PII) in the database:

- Client names (first, middle, last, preferred)
- Email addresses
- Phone numbers
- Dates of birth
- Custom fields marked as sensitive

The encryption uses Fernet (AES-128 in CBC mode with HMAC-SHA256 for authentication).

### Critical Warning

> **If you lose your encryption key, all encrypted client data is permanently unrecoverable.**

There is no backdoor, no recovery option, and no way to decrypt without the original key.

### Backing Up Your Key

Store your encryption key separately from database backups. Good options:

| Storage Method | Pros | Cons |
|----------------|------|------|
| Password manager (1Password, Bitwarden) | Easy access, encrypted | Requires subscription |
| Azure Key Vault / AWS Secrets Manager | Enterprise-grade, audit trail | Requires cloud setup |
| Encrypted USB drive in safe | Physical security, offline | Can be lost/damaged |
| Printed and locked away | Survives digital disasters | Vulnerable to physical access |

**Never store the key:**
- In the same backup location as your database
- In version control (Git)
- In plain text files on shared drives
- In email or chat messages

### Rotating the Encryption Key

If you suspect your key has been compromised, or as part of regular security hygiene:

```bash
# 1. Generate a new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Run the rotation command (re-encrypts all data with new key)
python manage.py rotate_encryption_key --old-key="YOUR_OLD_KEY" --new-key="YOUR_NEW_KEY"

# 3. Update your .env file with the new key
# 4. Restart the application
# 5. Verify the application works
# 6. Securely delete the old key
```

**Important:** Test key rotation in a staging environment first.

### Key Rotation Schedule

For compliance, consider rotating encryption keys:

- **Every 90 days** — Recommended baseline
- **When staff with key access leave** — Immediately
- **After a suspected security incident** — Immediately
- **When changing hosting providers** — During migration

---

## Pre-Deployment Security Checklist

Before deploying to production, verify all items:

### Required (Must Fix)

- [ ] `FIELD_ENCRYPTION_KEY` is set to a unique, generated key
- [ ] `SECRET_KEY` is set to a unique, generated key
- [ ] `DEBUG=False`
- [ ] `python manage.py check --deploy` passes with no errors
- [ ] `python manage.py security_audit` shows no FAIL results

### Strongly Recommended

- [ ] `SESSION_COOKIE_SECURE=True` (requires HTTPS)
- [ ] `CSRF_COOKIE_SECURE=True` (requires HTTPS)
- [ ] HTTPS is configured and working
- [ ] Encryption key is backed up in a secure location (not with database backups)
- [ ] Audit database user has INSERT-only permissions
- [ ] All test users/data removed from production database

### Verify After Deployment

- [ ] Login works correctly
- [ ] Client search returns expected results
- [ ] Audit logs are being created (check `/admin/audit/`)
- [ ] SSL certificate is valid (check browser padlock)

---

## Incident Response

### Suspected Data Breach

1. **Immediately rotate the encryption key** (see above)
2. **Rotate the SECRET_KEY** — this invalidates all user sessions
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
3. **Review audit logs** for unauthorized access patterns
4. **Document the timeline** — when discovered, what was accessed, response actions
5. **Notify affected parties** per PIPEDA/GDPR requirements (typically within 72 hours)
6. **Engage legal/compliance** if required by your organization

### Lost Encryption Key

If you've lost your encryption key and have no backup:

- Encrypted PII fields (names, emails, birth dates) are **permanently unrecoverable**
- Non-PII data (notes, metrics, program assignments) remains accessible
- You will need to re-enter client identifying information manually
- Consider this a data loss incident for compliance reporting purposes

### Suspicious Login Activity

1. Check audit logs for failed login attempts:
   ```sql
   SELECT event_timestamp, ip_address, metadata
   FROM audit_auditlog
   WHERE action = 'login_failed'
   ORDER BY event_timestamp DESC;
   ```
2. Look for patterns (many attempts from same IP, attempts on multiple accounts)
3. Consider implementing rate limiting if not already enabled
4. Block suspicious IP addresses at the firewall/reverse proxy level

---

## Privacy Compliance Support

KoNote's security features support compliance with privacy regulations including PIPEDA (Canada), PHIPA (Ontario health), and GDPR (EU). However, **compliance depends on how you configure and use the system**.

### Security Features That Support Compliance

| Feature | Supports |
|---------|----------|
| Field-level PII encryption | Data protection, breach mitigation |
| Role-based access control | Access limitation, need-to-know |
| Comprehensive audit logging | Accountability, incident investigation |
| Session timeout controls | Access security |
| Separate audit database | Log integrity, tamper resistance |

### What You Still Need to Do

KoNote provides technical controls, but compliance also requires:

- **Privacy policies** — Document what data you collect and why
- **Consent procedures** — Obtain and record client consent
- **Staff training** — Ensure staff understand privacy obligations
- **Breach response plan** — Know what to do if data is compromised
- **Data retention policies** — Define how long you keep data
- **Access request procedures** — How clients can see/correct their data

### Resources

- [Office of the Privacy Commissioner of Canada — PIPEDA](https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/)
- [Information and Privacy Commissioner of Ontario — PHIPA](https://www.ipc.on.ca/health/)
- [GDPR Official Text](https://gdpr-info.eu/)

> **Disclaimer:** This documentation describes KoNote's security features. It is not legal advice. Consult your privacy officer, legal counsel, or a qualified privacy professional to ensure your specific implementation meets your jurisdiction's requirements.

---

## Further Reading

- [Getting Started Guide](getting-started.md) — Local development setup
- [Technical Documentation](technical-documentation.md) — Architecture details
- [Backup & Restore](backup-restore.md) — Database backups, automation scripts, monitoring alerts
- [SECURITY.md](../SECURITY.md) — Security policy and vulnerability reporting
