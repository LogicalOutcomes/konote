# KoNote Web Security

This document describes the security architecture and how to run security checks.

## Security Architecture

### PII Encryption

All personally identifiable information (PII) is encrypted at rest using **Fernet** (AES-128-CBC + HMAC-SHA256).

**Encrypted fields:**
- `ClientFile`: first_name, middle_name, last_name, preferred_name, birth_date
- `User`: email
- `ClientDetailValue`: value (when `is_sensitive=True`)
- `ProgressNote`: notes_text, summary, participant_reflection
- `ProgressNoteTarget`: notes
- `RegistrationSubmission`: first_name, last_name, email, phone

**How it works:**
- Raw storage uses `_field_name_encrypted` BinaryField
- Property accessors (`client.first_name`) handle encryption/decryption automatically
- Encryption key stored in `FIELD_ENCRYPTION_KEY` environment variable

**Limitation:** Encrypted fields cannot be searched in SQL. Client search loads records into Python and filters in memory. This is acceptable up to ~2,000 clients.

### Access Control (RBAC)

**Program-scoped access:** Users only see clients enrolled in their assigned programs.

**Role hierarchy:** `front_desk` < `staff` < `program_manager`

**Enforcement layers:**
1. **Middleware** (`ProgramAccessMiddleware`) — checks program overlap at URL level
2. **Decorators** (`@minimum_role`) — enforces role requirements
3. **View helpers** (`_get_accessible_clients()`) — filters data before rendering

**Admin users:** Have system configuration access only. They cannot access client data unless also assigned program roles.

### Audit Logging

**Separate database:** Audit logs are stored in a dedicated PostgreSQL database with INSERT-only permissions, preventing tampering.

**Logged events:**
- All POST/PUT/PATCH/DELETE requests
- Client record views (GET requests to `/clients/*`)
- Login and logout events
- Failed login attempts
- Erasure requests (create, approve, reject, cancel, execute)
- Export creation, download, and revocation

**Fields captured:** user_id, action, resource_type, resource_id, IP address, timestamp

---

## Automatic Startup Security Check

KoNote automatically runs security checks every time the application starts. This protects every deployment — Azure, Railway, Docker on a local network — without requiring the deployer to remember to run commands.

### KONOTE_MODE Environment Variable

| Mode | Behaviour |
|------|-----------|
| `production` (default) | **Blocks startup** if critical security checks fail |
| `demo` | **Warns loudly** but allows startup for evaluation |

**Critical checks (block startup in production mode):**
- Encryption key configured and not using default
- SECRET_KEY not using insecure default
- Security middleware (RBAC, Audit) in place

**Warning checks (logged but don't block):**
- DEBUG mode enabled
- Insecure cookie settings

### Demo Mode

For evaluation or testing, set `KONOTE_MODE=demo`:

```bash
# Docker Compose (easiest)
docker-compose -f docker-compose.demo.yml up

# Or set the environment variable
KONOTE_MODE=demo docker-compose up
```

Demo mode shows a clear warning banner:
```
=======================================================
  KoNote IS RUNNING IN DEMO MODE
=======================================================

  Security checks found 2 issue(s):
    - Using default encryption key (not safe for real data)
    - DEBUG=True (should be False in production)

  DO NOT use this instance for real client data.
  Set KONOTE_MODE=production when ready for production use.
=======================================================
```

### Production Mode

Production mode (the default) blocks startup if critical checks fail:
```
=======================================================
  STARTUP BLOCKED - CRITICAL SECURITY FAILURES
=======================================================

  2 critical check(s) failed:
    - Using default encryption key (not safe for real data)
    - Using insecure default SECRET_KEY

  Fix these issues before starting KoNote in production.
  For evaluation/demo, set KONOTE_MODE=demo
=======================================================
```

This ensures that a nonprofit cannot accidentally deploy KoNote with insecure settings.

---

## Running Security Checks

### 1. Security Audit Command (On-Demand)

Comprehensive security audit across encryption, RBAC, audit logging, and configuration.

```bash
# Full audit
python manage.py security_audit

# Verbose output (shows scanned records)
python manage.py security_audit --verbose

# Specific categories only
python manage.py security_audit --category=ENC,RBAC

# JSON output (for CI/CD)
python manage.py security_audit --json

# Fail on warnings (for CI/CD)
python manage.py security_audit --fail-on-warn
```

**Categories:**
- `ENC` — Encryption checks (key configured, round-trip works, no plaintext)
- `RBAC` — Access control checks (user roles, orphaned enrolments)
- `AUD` — Audit logging checks (database accessible, recent entries)
- `CFG` — Configuration checks (DEBUG, cookies, middleware)
- `DOC` — Document storage checks (URL template, domain allowlist)

### 2. Django System Checks (Automatic)

Security checks run automatically with every `manage.py` command.

```bash
# Basic checks
python manage.py check

# Include deployment checks
python manage.py check --deploy
```

**Check IDs:**
- `KoNote.E001` — FIELD_ENCRYPTION_KEY not configured (Error)
- `KoNote.E002` — Security middleware missing (Error)
- `KoNote.W001` — DEBUG=True (Warning, deploy only)
- `KoNote.W002` — SESSION_COOKIE_SECURE=False (Warning, deploy only)

### 3. Document URL Test (Utility)

Test document folder URL generation after configuring document storage.

```bash
# Basic test
python manage.py test_document_url

# Test with specific record ID
python manage.py test_document_url --record-id "REC-2024-042"

# Verify URL is reachable
python manage.py test_document_url --check-reachable
```

### 4. Security Test Suite

Automated tests that verify security properties.

```bash
# Security tests only
python manage.py test tests.test_security

# All tests including security
python manage.py test
```

**Security test files:**

| File | Coverage |
|------|----------|
| `tests/test_security.py` | PII exposure, encryption round-trip, ciphertext validation |
| `tests/test_rbac.py` | Role permissions, program restrictions, admin-only routes |
| `tests/test_encryption.py` | Fernet key format, encrypt/decrypt functions |
| `tests/test_export_permissions.py` | Role-based export access, program scoping, download permissions |
| `tests/test_erasure.py` | Erasure workflow, approval logic, deadlock detection, audit preservation |
| `tests/test_demo_data_separation.py` | Demo/real user isolation, queryset filtering |
| `tests/test_secure_export.py` | Elevated export delay, link expiry, download authorisation |
| `tests/test_canadian_localisation.py` | Canadian spelling, locale settings, currency formatting |

---

## Security Audit Schedule

| Check | Frequency | Run By |
|-------|-----------|--------|
| `security_audit` command | Weekly | Operations |
| `security_audit --json --fail-on-warn` | Every deploy | CI/CD |
| Full test suite | Every pull request | CI/CD |
| `check --deploy` | Every deploy | CI/CD |

---

## Deployment Checklist

Run before every deployment:

```bash
# 1. Security audit
python manage.py security_audit --fail-on-warn

# 2. Django checks
python manage.py check --deploy

# 3. Test suite
python manage.py test

# 4. Document URL (if configured)
python manage.py test_document_url --record-id "TEST-001"
```

---

## Incident Response

### Suspected Data Breach

1. **Run security audit:**
   ```bash
   python manage.py security_audit --verbose
   ```

2. **Check audit logs:**
   ```python
   from apps.audit.models import AuditLog
   # Recent entries
   AuditLog.objects.using("audit").order_by("-event_timestamp")[:100]
   # By user
   AuditLog.objects.using("audit").filter(user_id=123)
   # By action
   AuditLog.objects.using("audit").filter(action="view")
   ```

3. **Rotate encryption key if compromised** (see Key Rotation below)

4. **Notify affected parties** per PIPEDA requirements (Canada) within 72 hours

### Key Rotation

If the encryption key is compromised or needs rotation:

```bash
# 1. Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Dry run (verify counts)
python manage.py rotate_encryption_key --old-key <OLD> --new-key <NEW> --dry-run

# 3. Rotate (re-encrypts all data)
python manage.py rotate_encryption_key --old-key <OLD> --new-key <NEW>

# 4. Update environment variable
# Set FIELD_ENCRYPTION_KEY to the new key

# 5. Restart application
```

---

## Known Limitations

1. **Encrypted field search:** Cannot search PII in SQL. In-memory filtering works for ~2,000 clients.

2. **Audit log size:** Grows continuously. Plan for periodic archival of old entries.

3. **Admin privilege separation:** Admin users without program roles cannot access client data. This is by design.

4. **Document storage:** URLs link to external systems (SharePoint, Google Drive). Access control on the external system is separate from KoNote.

### Export Hardening

- **CSV injection protection:** All exported cell values are sanitised with a tab prefix if they start with `=`, `+`, `-`, or `@`. Enforced by `sanitise_csv_value()` in `apps/reports/csv_utils.py`.
- **Filename sanitisation:** Download filenames are restricted to `[A-Za-z0-9_.-]` via `sanitise_filename()` in `apps/reports/csv_utils.py`, preventing path traversal and Content-Disposition header injection.

---

## Security Contacts

For security issues, contact the instance administrator or [your organization's security team].

For vulnerabilities in KoNote itself, please report responsibly.
