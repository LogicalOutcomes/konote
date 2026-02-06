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

## Key Management

### Critical Warning

> **If you lose your encryption key, all encrypted data is permanently unrecoverable.**

This includes:
- Client names and birth dates
- Progress notes and clinical content
- Any custom fields marked "sensitive"

There is no backdoor, no recovery option, no "forgot password" flow. The data is gone.

### Why This Matters for Nonprofits

Small nonprofits typically have:
- High staff turnover
- Limited IT expertise
- No documented key management procedures
- A "bus factor" of 1 (one person knows everything)

**For most small nonprofits, the risk of losing the encryption key is higher than the risk of a sophisticated database breach.**

This is not a reason to skip encryption — it's a reason to plan for key management.

### Protection Levels

During first-run setup, agencies must choose their protection level:

#### Standard Protection (Recommended for most agencies)

**How it works:** Encryption key stored in hosting platform's environment variables.

**Protects against:**
- Database breaches (attacker gets ciphertext)
- Backup exposure
- Casual access by unauthorised staff

**Does NOT protect against:**
- Hosting provider with legal compulsion (CLOUD Act)
- Hosting provider staff with malicious intent

**Key recovery:** Hosting provider can help recover if account access is maintained.

**Choose this if:** You trust your hosting provider and want protection without key management burden.

#### Enhanced Protection

**How it works:** Encryption key stored separately from hosting platform (external key vault, or agency-managed secret).

**Protects against:**
- All of Standard, plus:
- Hosting provider access (they don't have the key)

**Key recovery:** Agency is solely responsible. If key is lost, data is unrecoverable.

**Choose this if:** You have IT support, documented procedures, and a specific need for CLOUD Act protection.

### Key Backup Requirements

**For Standard Protection:**
- Document that the key is in the hosting platform's environment variables
- Ensure at least two people have access to the hosting account
- Record the hosting provider and account in your succession documentation

**For Enhanced Protection:**
- Store a paper copy of the key in a fireproof safe or safety deposit box
- Document the key location in your succession plan (but not the key itself)
- Test key recovery annually: can you retrieve it?
- Consider giving a sealed copy to your accountant or lawyer

### What to Document During Setup

Create a "KoNote Security Configuration" document (store securely, not in KoNote itself):

```
KoNote Security Configuration
==============================
Date configured: ____________
Configured by: ____________

Protection level: [ ] Standard  [ ] Enhanced

Encryption key location:
  [ ] Hosting platform environment variables (Standard)
  [ ] External location: ____________ (Enhanced)

Key backup location (Enhanced only):
  Primary: ____________
  Secondary: ____________

People with access to key/hosting:
  1. ____________
  2. ____________

Annual review date: ____________
```

### What Happens If Key Is Lost

1. All encrypted fields display `[decryption error]`
2. Client names, notes, and sensitive fields are permanently unreadable
3. You may need to rebuild client records from paper files or external sources
4. This may constitute a PIPEDA compliance issue (failure to maintain records)

**Prevention is the only cure.**

### Recommendation

**Most agencies should choose Standard Protection** unless they have:
- A specific regulatory requirement for external key management
- IT staff or consultants who can maintain key backup procedures
- A documented succession plan that includes key recovery

The goal is protection that will actually be maintained, not theoretical maximum security that fails in practice.

---

## Encrypted Fields

KoNote uses Fernet encryption (AES-128 in CBC mode with HMAC-SHA256 for authentication) to protect sensitive data at the application level.

### What Is Encrypted

| Data | Model | Fields |
|------|-------|--------|
| **Client identity** | ClientFile | first_name, middle_name, last_name, preferred_name, birth_date |
| **Custom fields marked sensitive** | ClientDetailValue | value (when field definition has `is_sensitive=True`) |
| **Progress note content** | ProgressNote | notes_text, summary, participant_reflection |
| **Target notes within progress notes** | ProgressNoteTarget | notes |

### What Is NOT Encrypted

- Metric values (numeric/categorical data without identifying information)
- Program names, outcome definitions, target descriptions
- Dates, timestamps, status fields
- User accounts (except email addresses)

Metric values are intentionally not encrypted because:
- They are numeric or categorical (e.g., "3", "improved", "yes/no")
- Without client identity, metric values are not personally identifiable
- Client identity is already encrypted
- Encrypting metrics would break reporting and aggregation queries

If an agency uses free-text metrics containing clinical content, they should use custom fields marked "sensitive" instead.

### Search Limitations

Encrypted fields cannot be searched via SQL. This means:
- Client search loads accessible clients into Python and filters in memory
- This is acceptable for up to approximately 2,000 clients
- Progress note content search is not supported (search by date, client, or status instead)

---

## Encryption Key Management

### About the Encryption Key

`FIELD_ENCRYPTION_KEY` encrypts all personally identifiable information (PII) in the database:

- Client names (first, middle, last, preferred)
- Email addresses
- Phone numbers
- Dates of birth
- Custom fields marked as sensitive
- Progress note content, summaries, and participant reflections
- Target notes within progress notes

The encryption uses Fernet (AES-128 in CBC mode with HMAC-SHA256 for authentication).

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

## Authentication Security

KoNote supports two authentication modes. Each has different multi-factor authentication (MFA) options.

### Which Authentication Mode Should You Use?

| Situation | Recommended Auth | MFA Available? |
|-----------|-----------------|----------------|
| Agency uses Microsoft 365 | Azure AD SSO | Yes — built-in and free through Azure |
| Agency doesn't use Microsoft 365 | Local password | Not yet — strong passwords enforced |
| Development, demos, trials | Local password | Not needed |

### Azure AD SSO (Recommended for Production)

If your agency uses Microsoft 365, use Azure AD SSO. This gives you:

- **Multi-factor authentication** — configured in Azure, not in KoNote
- **Conditional access policies** — restrict logins by location, device, or risk level
- **Centralised user management** — add/remove users through your existing Microsoft admin
- **Audit logging through Azure** — in addition to KoNote's own audit logs

#### How It Works

1. A user clicks "Sign in with Microsoft" on the KoNote login page
2. They are redirected to Microsoft's login page
3. Microsoft handles password verification and MFA (SMS, authenticator app, security key, etc.)
4. The user is redirected back to KoNote, now authenticated

#### Enabling MFA for Azure AD Users

MFA is configured in Azure, not in KoNote. To enable it:

1. Sign in to the [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID** (formerly Azure Active Directory) → **Security** → **Authentication methods**
3. Enable MFA for all users or specific security groups
4. Configure allowed authentication methods (authenticator app is recommended)

Once enabled, all users signing into KoNote through Microsoft will be prompted for MFA. No changes are needed in KoNote itself.

#### Azure AD Setup for KoNote

To connect KoNote to your Azure AD:

1. Create an **App Registration** in Microsoft Entra ID
2. Set the redirect URI to your KoNote instance (e.g., `https://konote.youragency.ca/auth/callback`)
3. Copy the Application (client) ID and Directory (tenant) ID
4. Create a client secret
5. Add the following environment variables to KoNote:
   - `AZURE_AD_CLIENT_ID` — your Application (client) ID
   - `AZURE_AD_CLIENT_SECRET` — your client secret
   - `AZURE_AD_TENANT_ID` — your Directory (tenant) ID

See the [Azure Deployment Guide](../tasks/azure-deployment-guide.md) for detailed setup instructions.

### Local Password Authentication

Local auth is suitable for:

- Development and testing environments
- Small agencies without Microsoft 365
- Demos and trials
- Agencies evaluating KoNote before committing to Azure AD

#### Security Measures for Local Auth

Even without MFA, KoNote enforces strong security for local passwords:

| Measure | Detail |
|---------|--------|
| **Password hashing** | Argon2id — the strongest available algorithm |
| **Minimum length** | 12 characters required |
| **Common password check** | Django's built-in validator rejects known weak passwords |
| **Session timeout** | Automatic logout after 8 hours of inactivity |
| **Failed login logging** | All failed attempts recorded in audit log with IP address |

#### When Local Auth Is Not Enough

Consider upgrading to Azure AD SSO if:

- Your agency handles health data (PHIPA) or data about vulnerable populations
- A funder or regulator requires MFA
- You need conditional access (e.g., block logins from outside Canada)
- You want centralised user provisioning and deprovisioning

### Future: TOTP for Local Auth

For agencies that need MFA but don't have Microsoft 365, a future update will add TOTP (Time-based One-Time Password) support for local authentication. This will work with authenticator apps like Google Authenticator, Microsoft Authenticator, or Authy.

This feature is not yet implemented. If your agency needs MFA now, Azure AD SSO is the recommended path.

### MFA and Compliance

| Standard | MFA Requirement |
|----------|-----------------|
| **PIPEDA** | Not explicitly required, but "appropriate safeguards" expected |
| **PHIPA** | Not explicitly required, but recommended for health data |
| **SOC 2** | Typically expected for access to sensitive systems |
| **WCAG 2.2** | MFA flows must be accessible (no CAPTCHA, support assistive technology) |

For agencies serving vulnerable populations (health, housing, youth services), MFA is considered a best practice even when not legally mandated. Azure AD SSO is the simplest way to meet this expectation.

---

## Role-Based Export Permissions

KoNote separates system administration from data access. Being an "admin" gives you control over system configuration (programs, users, settings) — it does **not** automatically grant access to client records or reports.

### Permission Matrix

| Action | Front Desk | Staff | Program Manager | Executive | Admin |
|--------|:----------:|:-----:|:---------------:|:---------:|:-----:|
| See client records | Limited fields | Full records | Their programs | No (dashboard only) | No (config only) |
| Create metrics export | No | No | Their programs | No | Any program |
| Create CMT export | No | No | Their programs | No | Any program |
| Create client data export | No | No | No | No | Yes |
| Download own export | N/A | N/A | Yes | N/A | Yes |
| Download others' exports | No | No | No | No | Yes |
| Manage/revoke export links | No | No | No | No | Yes |

### Design Rationale

**Why program managers can export (not just admins):**
Program managers already see client data through the application. Export creation follows existing data access — if you can see the data, you can export it. Requiring an admin to generate every funder report creates an unnecessary bottleneck.

**Why exports are scoped to programs:**
A program manager for "Youth Services" should not be able to export data from "Housing Support." The program dropdown only shows programs the user manages. This is enforced server-side by the form's queryset.

**Why client_data_export stays admin-only:**
This is a full PII dump designed for data migration and audit purposes — not day-to-day reporting. It contains all client fields across all programs.

**Why executives can't export:**
Executives see aggregate dashboards only. They do not have access to individual client records, so they should not be able to export them.

**Why only the creator can download:**
Export links are deferred downloads, not a sharing mechanism. The creator generated the data from their own program scope. Sharing the download with others would bypass program scoping.

### How It Works in Code

- `can_create_export(user, export_type, program)` — central permission check in `apps/reports/utils.py`
- `get_manageable_programs(user)` — returns programs available for export forms
- `has_export_access` — template context variable controlling nav visibility
- Form querysets filter programs server-side (not just in the UI)
- All exports are audit logged with the creator, recipient, and link ID

### Test Coverage

Permission tests live in `tests/test_export_permissions.py` and verify:
- Each role gets the correct access/denial for each export type
- Program scoping prevents cross-program exports
- Download permissions enforce creator-only + admin access
- Manage/revoke views remain admin-only
- The `has_export_access` context variable is set correctly per role

---

## Export Data Protection

### CSV Injection Protection

| Aspect | Detail |
|--------|--------|
| **What's protected** | Exported CSV files opened in spreadsheet applications |
| **Invariant** | No cell value starts with `=`, `+`, `-`, or `@` without a tab prefix |
| **Enforcement** | `sanitise_csv_value()` and `sanitise_csv_row()` in `apps/reports/csv_utils.py` |
| **Failure mode** | Without sanitisation, a malicious value like `=HYPERLINK("http://evil.com")` could execute when opened in Excel |
| **Verification** | Export a CSV and inspect raw file — dangerous characters are tab-prefixed |
| **Configuration required** | None (automatic) |

### Filename Sanitisation

| Aspect | Detail |
|--------|--------|
| **What's protected** | Download filenames in HTTP `Content-Disposition` headers |
| **Invariant** | Download filenames contain only `[A-Za-z0-9_.-]` |
| **Enforcement** | `sanitise_filename()` in `apps/reports/csv_utils.py` |
| **Failure mode** | Path traversal or Content-Disposition header injection |
| **Verification** | Download an export and confirm the filename contains only permitted characters |
| **Configuration required** | None (automatic) |

### Elevated Export Monitoring

| Aspect | Detail |
|--------|--------|
| **What's protected** | Large or sensitive data exports (bulk client data, progress notes) |
| **Invariant** | Exports with 100+ clients or including progress notes cannot be downloaded for `ELEVATED_EXPORT_DELAY_MINUTES` (default: 10) |
| **Enforcement** | `SecureExportLink.is_elevated` flag in `apps/reports/models.py`; delay checked at download time |
| **Failure mode** | Without delay, a compromised account could exfiltrate bulk data before detection |
| **Verification** | Check Manage Export Links page (`/reports/export-links/`) for elevated status |
| **Configuration required** | `ELEVATED_EXPORT_DELAY_MINUTES` env var (optional, default 10); email configuration for admin notifications |

### Individual Client Export

Staff-level users can export a single client's data directly (no deferred link). This supports PIPEDA data portability requirements.

| Aspect | Detail |
|--------|--------|
| **Permission** | Staff or above, for clients in their assigned programmes |
| **Delivery** | Direct download (not a deferred export link) |
| **Selectable sections** | Plans, notes, metrics, events, custom fields |
| **Audit** | Logged as a client data export with user, client ID, and selected sections |

### Export Recipient Tracking

| Aspect | Detail |
|--------|--------|
| **What's protected** | Accountability for data leaving the system |
| **Invariant** | Every export form requires declaring who receives the data (self, colleague, funder, other) |
| **Enforcement** | Required field on export creation form; stored on `SecureExportLink` model and in audit log |
| **Failure mode** | Without tracking, there is no record of why data was exported or who it was shared with |
| **Verification** | Check audit log or Manage Export Links page for recipient field |
| **Configuration required** | None (automatic) |

For operational procedures (setup, cron, troubleshooting), see `docs/export-runbook.md`.

---

## Erasure Workflow Security

### State Machine

```
Request created (by staff+)
  → Pending approval (all PMs for client's programmes notified by email)
    → Each PM: approve or reject
      → If any PM rejects → Request rejected (all parties notified)
      → If all PMs approve → Erasure executed
        → RegistrationSubmission PII scrubbed
        → ClientFile CASCADE deleted (notes, plans, events, alerts, enrolments, metrics, custom fields)
        → ErasureRequest updated (status=approved, client_file=NULL)
        → Audit log written (counts only, no PII)
        → All parties notified by email
```

### Key Invariants

- **Self-approval prevention:** Requester cannot self-approve their own erasure request.
- **Single rejection rule:** One rejection = entire request rejected.
- **Deadlock detection:** If requester is the only active PM for remaining programmes, `is_deadlocked()` returns `True` — admin can approve as fallback.
- **Non-destructive audit:** `ErasureRequest` survives via `on_delete=SET_NULL`; stores `client_pk`, `client_record_id`, `data_summary` (counts only), `programs_required`, `requested_by_display`.
- **What auditors see after erasure:** `ErasureRequest` record with reason, all approval records (who, when, which programme), `data_summary` with record counts — no PII.
- **Email notifications:** Best-effort (failures logged, do not block erasure).

### Enforcement Files

| File | Purpose |
|------|---------|
| `apps/clients/erasure.py` | Core erasure logic and execution |
| `apps/clients/erasure_views.py` | Request, approval, and rejection views |
| `apps/clients/models.py` | `ErasureRequest` and `ErasureApproval` models |

---

## Demo and Real Data Separation

| Aspect | Detail |
|--------|--------|
| **What's protected** | Real client data from demo user access (and vice versa) |
| **Invariant** | Demo users never see real clients; real users never see demo clients |
| **Enforcement** | `get_client_queryset(user)` in `apps/clients/views.py` filters on `user.is_demo`; `ClientFileManager.real()` / `.demo()` queryset methods |
| **Failure mode** | If `is_demo` were read from request params instead of user object, an attacker could bypass. Prevented — flag is read from authenticated user only. |
| **Verification** | Log in as demo user, confirm no real clients visible; log in as real user, confirm no demo clients visible |
| **Configuration required** | `DEMO_MODE=true` to create demo users/clients via seed command |

---

## Registration Security

| Aspect | Detail |
|--------|--------|
| **Cryptographic slug** | `secrets.token_urlsafe(8)` — resistant to enumeration |
| **Rate limiting** | 5 submissions per hour per session |
| **PII encryption** | `RegistrationSubmission` encrypts `first_name`, `last_name`, `email`, `phone` using same Fernet as `ClientFile` |
| **Duplicate detection** | SHA-256 hash of lowercase email (`email_hash` field, indexed). No decryption needed. |
| **Consent** | Registration form requires consent checkbox. Consent timestamp stored on record. |
| **Configuration required** | None (automatic). Admin creates registration links via Admin → Registration Links. |

---

## Independent Security Review

KoNote2 is open-source software that handles sensitive client information. Any agency considering adoption — or already using KoNote2 — can get an **independent security review** at any time, no vendor permission needed. This is a key advantage over proprietary case management tools where you have to trust the vendor's claims.

### What You Can Verify

These are the specific claims we make that a third-party review can confirm:

1. **Encryption at rest** — All client names, notes, and outcome ratings are encrypted using Fernet (AES-128-CBC with HMAC). The encrypted fields are stored as ciphertext in the database — a database breach alone does not expose client data.

2. **Key management options** — Agencies can either:
   - Manage their own encryption key (set `FIELD_ENCRYPTION_KEY` themselves)
   - Use a hosting-managed key (provider sets it during deployment)
   - Either way, the key never touches the codebase

3. **Audit logging** — Every data access, export, and admin action is logged to a separate audit database. Logs cannot be modified through the application.

4. **Role-based access control** — Four roles (receptionist, staff, program manager, admin) with server-side enforcement. No client-side-only checks.

5. **Export controls** — Elevated exports require admin approval, have time delays, and generate audit entries.

6. **Demo/real data separation** — Demo users never see real client data and vice versa, enforced at the query level.

### How to Do a Review

#### Option 1: AI-Powered Code Review (Free, Fast)

Use an AI code review tool to scan the entire codebase. Recommended tools:

- **Jules** (jules.google.com) — Google's AI code agent
- **GPT Codex** — OpenAI's code review tool
- **Claude Code** — Anthropic's CLI tool (what built this software)

Any of these can review the full codebase in minutes and produce a detailed security report. See the **AI Review Prompt** below for a ready-made prompt you can copy and paste.

#### Option 2: Professional Penetration Test (Paid, Thorough)

Hire a security firm to do a full penetration test. The open-source codebase means they have white-box access — far more thorough than black-box testing.

#### Option 3: Internal IT Review

If your agency has IT staff, they can clone the repo and review the security architecture directly.

### AI Review Prompt

Copy and paste this prompt into any AI code review tool (Claude Code, GPT Codex, Jules, etc.) after pointing it at the KoNote2 repository:

> You are reviewing an open-source Django web application called KoNote2 that stores sensitive client information for nonprofit social service agencies. Please conduct a security-focused code review and produce a report covering:
>
> **1. Encryption Implementation**
> - Are client names, notes, and ratings actually encrypted at rest?
> - What encryption algorithm is used? Is it current and appropriate?
> - How is the encryption key managed? Could it be accidentally exposed?
> - Are there any fields containing PII that are NOT encrypted?
>
> **2. Authentication & Authorization**
> - Are role-based access controls enforced server-side (not just in templates)?
> - Can a lower-privilege user access higher-privilege endpoints?
> - Is the Azure AD SSO integration implemented securely?
> - Are local passwords hashed with a strong algorithm?
>
> **3. Data Export Security**
> - Are exports protected against unauthorized access?
> - Do secure download links expire properly?
> - Is there CSV injection protection?
> - Are exports logged in the audit trail?
>
> **4. Audit Logging**
> - Is the audit log stored separately from application data?
> - Can audit entries be modified or deleted through the application?
> - Are all sensitive operations logged?
>
> **5. Common Vulnerabilities (OWASP Top 10)**
> - SQL injection
> - Cross-site scripting (XSS)
> - Cross-site request forgery (CSRF)
> - Insecure direct object references
> - Security misconfiguration
>
> **6. Privacy Compliance**
> - Does the application support PIPEDA requirements (data portability, consent)?
> - Is there proper data separation between demo and production data?
>
> Please flag any issues found as Critical, High, Medium, or Low severity, and provide specific file paths and line numbers where possible.

### Re-Reviewing After Updates

Agencies can re-run their review after any update to verify nothing has regressed. Because the code is public, every change is visible and auditable.

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
3. **Review audit logs** for unauthorised access patterns
4. **Document the timeline** — when discovered, what was accessed, response actions
5. **Notify affected parties** per PIPEDA/GDPR requirements (typically within 72 hours)
6. **Engage legal/compliance** if required by your organisation

### Lost Encryption Key

If you've lost your encryption key and have no backup:

- Encrypted PII fields (names, emails, birth dates) are **permanently unrecoverable**
- Encrypted progress note content is **permanently unrecoverable**
- Non-encrypted data (metric values, program assignments, dates) remains accessible
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
| Progress note encryption | Clinical content protection |
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

- [Deploying KoNote](deploying-konote.md) — Deployment options and setup
- [Technical Documentation](technical-documentation.md) — Architecture details
- [Administering KoNote](administering-konote.md) — Day-to-day administration
