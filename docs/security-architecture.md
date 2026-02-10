# Security Architecture

**Last updated:** February 2026 | **Applies to:** KoNote v1.x

This document describes KoNote's security architecture in technical detail. It is intended for developers, security reviewers, and penetration testers. For operational guidance, see the [Security Operations Guide](security-operations.md). For a non-technical overview, see the [Security Overview](security-overview.md).

---

## 1. Encryption Implementation

KoNote uses Fernet encryption from Python's `cryptography` library for application-level PII encryption.

**Algorithm details:**

- **Cipher:** AES-128-CBC for confidentiality
- **Authentication:** HMAC-SHA256 for tamper detection
- **Key:** 256-bit total (128-bit AES key + 128-bit HMAC key), base64-encoded
- **Key source:** `FIELD_ENCRYPTION_KEY` environment variable
- **Implementation:** `konote/encryption.py` -- lazy-initialised `Fernet` instance, shared across the process

Fernet tokens include a timestamp in each ciphertext block. This timestamp is part of the Fernet specification but is not used for at-rest encryption (no time-based expiry is enforced on stored data).

### AES-128 Justification

Fernet uses AES-128 by design -- this is part of the Fernet specification and cannot be changed without abandoning the library. AES-128 is approved by NIST (SP 800-131A Rev. 2) and has no known practical vulnerabilities. AES-256 offers additional margin against theoretical future attacks (including quantum computing via Grover's algorithm), but this is not a realistic threat model for a nonprofit case management tool. Implementing a custom AES-256 scheme would introduce the risk of implementation errors -- incorrect IV handling, missing authentication, padding oracle vulnerabilities -- which is a greater practical danger than the theoretical weakness of AES-128.

### Encrypted Fields

| Model | Fields | Purpose |
|-------|--------|---------|
| `ClientFile` | `first_name`, `middle_name`, `last_name`, `preferred_name`, `birth_date` | Client identity |
| `ClientDetailValue` | `value` (when field definition has `is_sensitive=True`) | Sensitive custom fields |
| `ProgressNote` | `notes_text`, `summary`, `participant_reflection` | Clinical content |
| `ProgressNoteTarget` | `notes` | Target-specific notes |
| `RegistrationSubmission` | `first_name`, `last_name`, `email`, `phone` | Registration PII |

**Storage pattern:** Each encrypted field is stored as a `BinaryField` (e.g. `_first_name_encrypted`). A Python `@property` accessor handles transparent encryption on write and decryption on read:

```python
@property
def first_name(self):
    return decrypt_field(self._first_name_encrypted)

@first_name.setter
def first_name(self, value):
    self._first_name_encrypted = encrypt_field(value)
```

### What Is NOT Encrypted (and Why)

- **Metric values** -- Numeric or categorical data (e.g. "3", "improved", "yes/no"). Without client identity (which is encrypted), metric values are not personally identifiable. Encrypting them would break reporting and aggregation queries.
- **Program names, outcome definitions, target descriptions** -- Organisational data, not PII.
- **Dates, timestamps, status fields** -- Required for database queries and filtering.
- **User accounts** -- Except email addresses, which are encrypted.

### Search Limitations

- Encrypted fields cannot be searched via SQL -- the database sees only ciphertext.
- Client search loads accessible clients into Python memory and filters there (`get_client_queryset()` in `apps/clients/views.py`).
- This approach is acceptable up to approximately 2,000 clients per agency.
- Progress note content search is not supported. Search by date, client, or status instead.

---

## 2. System Check IDs

KoNote registers custom Django system checks that run on every `manage.py` command, including server startup.

| ID | Severity | What It Checks | How to Fix |
|----|----------|----------------|------------|
| `KoNote.E001` | Error | Encryption key exists and is valid Fernet key | Generate key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and set `FIELD_ENCRYPTION_KEY` in `.env` |
| `KoNote.E002` | Error | Security middleware is loaded | Verify `MIDDLEWARE` in settings includes `ProgramAccessMiddleware` and `AuditMiddleware` |
| `KoNote.W001` | Warning | `DEBUG=True` (deploy check only) | Set `DEBUG=False` in production |
| `KoNote.W002` | Warning | Session cookies not marked secure | Set `SESSION_COOKIE_SECURE=True` when using HTTPS |
| `KoNote.W003` | Warning | CSRF cookies not marked secure | Set `CSRF_COOKIE_SECURE=True` when using HTTPS |
| `KoNote.W004` | Warning | Argon2 not the primary password hasher | Add `Argon2PasswordHasher` as first entry in `PASSWORD_HASHERS` |

**Errors (E)** prevent the server from starting. **Warnings (W)** allow startup but indicate security gaps.

Run checks explicitly with `python manage.py check` (basic) or `python manage.py check --deploy` (deployment-specific checks included).

---

## 3. Security Test Suite

| File | Test Count | What It Covers |
|------|-----------|----------------|
| `test_security.py` | PII exposure tests | Client data not in database plaintext, encryption round-trip, ciphertext validation |
| `test_rbac.py` | 19 tests | Role permissions, front desk access control, program restrictions, admin-only routes |
| `test_htmx_errors.py` | 21 tests | Error responses, HTMX partials, form validation feedback |
| `test_encryption.py` | Key validation tests | Fernet key format, encrypt/decrypt functions, unicode round-trip, memoryview handling |

Run all security tests:

```bash
pytest tests/test_security.py tests/test_rbac.py tests/test_encryption.py -v
```

Test data is temporary -- created during test execution, automatically deleted afterward. Tests use `override_settings(FIELD_ENCRYPTION_KEY=...)` with a freshly generated key, so they do not interact with real data or require a configured environment.

---

## 4. Role-Based Access Control (RBAC)

### Permission Matrix

| Action | Front Desk | Staff | Program Manager | Executive | Admin |
|--------|:----------:|:-----:|:-----------------:|:---------:|:-----:|
| See client records | Limited fields | Full records | Their programs | No (dashboard only) | No (config only) |
| Create metrics export | No | No | Their programs | No | Any program |
| Create funder report export | No | No | Their programs | No | Any program |
| Create client data export | No | No | No | No | Yes |
| Download own export | N/A | N/A | Yes | N/A | Yes |
| Download others' exports | No | No | No | No | Yes |
| Manage/revoke export links | No | No | No | No | Yes |

### Design Rationale

- **Program managers can export** because they already see the data -- export follows existing access, not elevated access. Requiring an admin to generate every funder report creates an unnecessary bottleneck.
- **Exports are scoped to programs** -- a PM for "Youth Services" cannot export from "Housing Support." The program dropdown only shows programs the user manages. This is enforced server-side by the form's queryset, not just in the UI.
- **`client_data_export` stays admin-only** -- this is a full PII dump for data migration and audit purposes, not day-to-day reporting.
- **Executives see aggregate dashboards only** -- no access to individual client records.
- **Only the creator can download their export link** -- export links are deferred downloads, not a sharing mechanism. Sharing with others would bypass program scoping.

### Implementation References

| Component | Location |
|-----------|----------|
| Central permission check | `can_create_export(user, export_type, program)` in `apps/reports/utils.py` |
| Program scoping for forms | `get_manageable_programs(user)` in `apps/reports/utils.py` |
| Nav visibility control | `has_export_access` template context variable |
| Server-side queryset filtering | Form querysets in export views |
| Audit logging | All exports logged with creator, recipient, and link ID |
| Permission tests | `tests/test_export_permissions.py` |

RBAC is enforced by two middleware classes:

- `konote.middleware.program_access.ProgramAccessMiddleware` -- enforces program-level access control
- `konote.middleware.audit.AuditMiddleware` -- logs all data access to the audit database

Both are verified as present by `KoNote.E002` and by `ConfigurationDriftTest` in `tests/test_security.py`.

---

## 5. Export Data Protection

### CSV Injection Protection

- **Invariant:** No cell value starts with `=`, `+`, `-`, or `@` without a tab prefix
- **Enforcement:** `sanitise_csv_value()` and `sanitise_csv_row()` in `apps/reports/csv_utils.py`
- **Mechanism:** Values beginning with formula-trigger characters are prefixed with a tab character (`\t`), causing spreadsheet applications to treat them as text rather than formulas
- **Threat:** Without sanitisation, a malicious value like `=HYPERLINK("http://evil.com")` could execute when opened in Excel or LibreOffice Calc

### Filename Sanitisation

- **Invariant:** Download filenames contain only `[A-Za-z0-9_.-]`
- **Enforcement:** `sanitise_filename()` in `apps/reports/csv_utils.py`
- **Mechanism:** `re.sub(r"[^A-Za-z0-9_.\-]", "", raw_name)` strips all disallowed characters; returns `"export"` if result would be empty
- **Threat:** Path traversal (`../../etc/passwd`) and `Content-Disposition` header injection

### Elevated Export Monitoring

- **Invariant:** Exports with 100+ clients or including progress notes cannot be downloaded for `ELEVATED_EXPORT_DELAY_MINUTES` (default: 10 minutes)
- **Enforcement:** `SecureExportLink.is_elevated` flag in `apps/reports/models.py`; delay checked at download time
- **Purpose:** A compromised account cannot exfiltrate bulk data before detection. The delay window allows administrators to notice and revoke the export link.

### Export Recipient Tracking

- **Invariant:** Every export form requires declaring who receives the data (self, colleague, funder, other)
- **Enforcement:** Required field on export creation form; stored on `SecureExportLink` model and written to the audit log
- **Purpose:** Provides accountability for data leaving the system. Supports PIPEDA's accountability principle.

### Individual Client Export

- Staff-level users can export a single client's data directly (no deferred link)
- Supports PIPEDA data portability requirements
- Selectable sections: plans, notes, metrics, events, custom fields
- Audit logged with user, client ID, and selected sections

---

## 6. Erasure Workflow

### State Machine

```
Request created (by staff+)
  -> Pending approval (all PMs for client's programs notified by email)
    -> Each PM: approve or reject
      -> If any PM rejects -> Request rejected (all parties notified)
      -> If all PMs approve -> Erasure executed
        -> RegistrationSubmission PII scrubbed
        -> ClientFile CASCADE deleted (notes, plans, events, alerts, enrolments, metrics, custom fields)
        -> ErasureRequest updated (status=approved, client_file=NULL)
        -> Audit log written (counts only, no PII)
        -> All parties notified by email
```

### Erasure Tiers

The system supports three tiers of erasure, determined at request time:

| Tier | Name | What Happens | When Available |
|------|------|-------------|----------------|
| 1 | Anonymise | Strip all PII, keep service records intact | Always |
| 2 | Anonymise + Purge | Strip PII and blank all narrative content | Always |
| 3 | Full Erasure | CASCADE delete (only tombstone survives) | After retention period expires |

### Key Invariants

- **Self-approval prevention:** Requester cannot self-approve their own erasure request. Enforced in `record_approval()` in `apps/clients/erasure.py`.
- **Single rejection rule:** One rejection = entire request rejected.
- **Deadlock detection:** If the requester is the only active PM for all remaining unapproved programs, `is_deadlocked()` returns `True`. An admin can then approve as a fallback.
- **Non-destructive audit:** `ErasureRequest` survives deletion via `on_delete=SET_NULL`. It stores `client_pk`, `client_record_id`, `data_summary` (record counts only), `programs_required`, and `requested_by_display`.
- **Audit-first execution:** The audit log entry is written before the data is deleted. If audit logging fails, erasure does not proceed.
- **What auditors see after erasure:** `ErasureRequest` record with reason, all `ErasureApproval` records (who, when, which program), and `data_summary` with record counts -- no PII.
- **Email notifications:** Best-effort (failures are logged but do not block erasure).
- **Concurrency control:** `record_approval()` uses `select_for_update()` to prevent concurrent double-execution of the same erasure.

### Enforcement Files

| File | Purpose |
|------|---------|
| `apps/clients/erasure.py` | Core erasure logic: tier dispatch, PII scrubbing, cascade deletion, deadlock detection |
| `apps/clients/erasure_views.py` | Request creation, approval, and rejection views |
| `apps/clients/models.py` | `ErasureRequest` and `ErasureApproval` models |

---

## 7. CSRF Protection

Django enables CSRF protection by default via `CsrfViewMiddleware`. KoNote uses HTMX for dynamic interactions, which requires explicit CSRF token handling:

- The CSRF token is included in HTMX requests via the `hx-headers` attribute or Django's `{% csrf_token %}` template tag
- All HTMX POST requests include the CSRF token in the `X-CSRFToken` header
- Django's `CsrfViewMiddleware` validates the token on every POST request
- CSRF cookie security: configurable via `CSRF_COOKIE_SECURE` (should be `True` in production with HTTPS; checked by `KoNote.W003`)

---

## 8. Demo/Real Data Separation

- **Invariant:** Demo users never see real clients; real users never see demo clients
- **Enforcement:** `get_client_queryset(user)` in `apps/clients/views.py` filters on `user.is_demo`; `ClientFileManager.real()` and `.demo()` provide scoped queryset methods
- **Security property:** The `is_demo` flag is read from the authenticated user object, not from request parameters. This prevents client-side bypass -- an attacker cannot toggle demo mode by manipulating form data or query strings.
- **Configuration:** `DEMO_MODE=true` environment variable triggers creation of demo users and clients via the seed command

---

## 9. Registration Security

- **Cryptographic slug:** `secrets.token_urlsafe(8)` generates a 48-bit random value in `apps/registration/models.py`. Resistant to enumeration at small scale (approximately 2.8 x 10^14 possible values).
- **Rate limiting:** 5 submissions per hour per session. Prevents automated form submission abuse.
- **PII encryption:** `RegistrationSubmission` encrypts `first_name`, `last_name`, `email`, and `phone` using the same Fernet implementation as `ClientFile` (see Section 1).
- **Duplicate detection:** SHA-256 hash of lowercase email stored in `email_hash` field (indexed). Duplicate checking happens against the hash -- no decryption required. This allows the system to detect duplicate registrations without exposing email addresses in the database.
- **Consent:** Registration form requires a consent checkbox. The consent timestamp is stored on the `RegistrationSubmission` record.
- **Configuration:** Admin creates registration links via Admin -> Registration Links. No additional configuration required.

---

## 10. Areas for Future Improvement

This section documents known security gaps. They are listed here for transparency, not because they represent imminent risks.

- **Content Security Policy (CSP):** Not yet implemented. A basic CSP blocking inline scripts would provide defence-in-depth against XSS. Django templates and HTMX interactions would need `nonce`-based or `hash`-based script allowlisting.

- **Login rate limiting:** Failed logins are logged to the audit database (with IP address) but not rate-limited at the application level. Azure AD provides its own rate limiting for SSO deployments. Local-auth deployments should consider reverse-proxy-level rate limiting (e.g. `limit_req` in nginx or equivalent in Caddy/Traefik).

- **TOTP for local auth:** Multi-factor authentication is available through Azure AD SSO but not yet implemented for local password authentication. Agencies requiring MFA without Microsoft 365 should use Azure AD SSO until TOTP support is added.
