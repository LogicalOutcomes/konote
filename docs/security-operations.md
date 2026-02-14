# Security Operations Guide

**Last updated:** February 2026 | **Applies to:** KoNote v1.x

> **Disclaimer:** This document describes KoNote's security features and how to operate them. It is not legal advice. Consult your privacy officer or legal counsel for your specific compliance requirements.

This guide is for IT staff, managed service providers, and technical consultants who are setting up, maintaining, or troubleshooting a KoNote deployment. For a non-technical overview, see the [Security Overview](security-overview.md). For technical architecture details, see [Security Architecture](security-architecture.md).

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

For the full list of check IDs and what they mean, see [Security Architecture — System Check IDs](security-architecture.md#2-system-check-ids).

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

## Audit Logging

Every significant action in KoNote is logged to a separate audit database. This provides a record for compliance and incident investigation.

### What Gets Logged

| Action | Logged Data |
|--------|-------------|
| Login/Logout | User, timestamp, IP address, success/failure |
| Client view | Who viewed which client, when |
| Create/Update/Delete | What changed, old values, new values |
| Exports | Who exported what data, recipient |
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

The audit database should be configured as append-only to prevent tampering:

- Configure the `audit_writer` database user with INSERT permission only (no UPDATE or DELETE)
- This is a configuration step during deployment — it is not enforced automatically by the application
- Verify this by attempting an UPDATE or DELETE as `audit_writer` — it should be denied by PostgreSQL

---

## Key Management

### Critical Warning

> **If you lose your encryption key, all encrypted data is permanently unrecoverable.**

This includes:
- Client names and birth dates
- Progress notes and clinical content
- Any custom fields marked "sensitive"

There is no backdoor, no recovery option, no "forgot password" flow. The data is gone.

This is why we recommend Standard Protection for most agencies — your hosting provider maintains the key alongside your application, and key loss is extremely unlikely as long as you maintain access to your hosting account.

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
4. You would need to notify the Privacy Commissioner and affected clients, as this constitutes a loss of personal information under PIPEDA

**Prevention is the only cure.**

### Recommendation

**Most agencies should choose Standard Protection** unless they have:
- A specific regulatory requirement for external key management
- IT staff or consultants who can maintain key backup procedures
- A documented succession plan that includes key recovery

The goal is protection that will actually be maintained, not theoretical maximum security that fails in practice.

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

**Do not rotate your encryption key unless you have a specific reason.** Key rotation re-encrypts every encrypted field in the database, which carries its own risks. An error during rotation could result in data loss.

**When to rotate:**

- **When staff with key access leave the organisation** — Immediately
- **After a suspected security incident** — Immediately
- **When changing hosting providers** — During migration

**How to rotate:**

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
2. Navigate to **Microsoft Entra ID** (formerly Azure Active Directory) > **Security** > **Authentication methods**
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
| **PIPEDA** | Not explicitly required, but the Privacy Commissioner increasingly considers MFA a reasonable safeguard for sensitive data |
| **PHIPA** | Not explicitly required, but recommended for health data |
| **SOC 2** | Typically expected for access to sensitive systems |
| **WCAG 2.2** | MFA flows must be accessible (no CAPTCHA, support assistive technology) |

For agencies serving vulnerable populations (health, housing, youth services), MFA is considered a best practice even when not legally mandated. Azure AD SSO is the simplest way to meet this expectation.

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
- [ ] Audit database user (`audit_writer`) has INSERT-only permissions
- [ ] All test users/data removed from production database
- [ ] Data processing agreement in place with hosting provider

### Verify After Deployment

- [ ] Login works correctly
- [ ] Client search returns expected results
- [ ] Audit logs are being created (check `/admin/audit/`)
- [ ] SSL certificate is valid (check browser padlock)

---

## Incident Response

### Suspected Data Breach

1. **Immediately rotate the encryption key** (see Key Management above)
2. **Rotate the SECRET_KEY** — this invalidates all user sessions
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
3. **Review audit logs** for unauthorised access patterns
4. **Document the timeline** — when discovered, what was accessed, response actions
5. **Notify the Privacy Commissioner and affected individuals as soon as feasible** — PIPEDA's Breach of Security Safeguards Regulations require notification when there is a real risk of significant harm. There is no fixed deadline, but "as soon as feasible" is the legal standard, and delays must be justified.
6. **Engage legal/compliance** if required by your organisation

### Lost Encryption Key

If you've lost your encryption key and have no backup:

- Encrypted PII fields (names, emails, birth dates) are **permanently unrecoverable**
- Encrypted progress note content is **permanently unrecoverable**
- Non-encrypted data (metric values, program assignments, dates) remains accessible
- You will need to re-enter client identifying information manually
- This constitutes a loss of personal information — notify the Privacy Commissioner and affected clients as required under PIPEDA

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

## Further Reading

- [Security Overview](security-overview.md) — Non-technical summary for boards and funders
- [Security Architecture](security-architecture.md) — Technical details for developers and security reviewers
- [Independent Review Guide](independent-review.md) — How to verify KoNote's security claims
- [PIA Template Answers](pia-template-answers.md) — Pre-written answers for Privacy Impact Assessments
- [Deploying KoNote](deploying-KoNote.md) — Deployment options and setup
- [Administering KoNote](administering-KoNote.md) — Day-to-day administration
