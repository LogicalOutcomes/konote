# Foundation: Security by Default

**High Security for Non-Technical Operators**

Status: Foundation Principle
Created: 2026-03-14

> **In plain language:** KoNote is secure even if you don't have an IT team. Every security protection is built into the system and turned on by default — you can't accidentally make it insecure by misconfiguring a setting. If something goes wrong, the system blocks access rather than leaking data.

---

## Core Principle

Canadian nonprofits handle deeply sensitive personal information — mental health notes, domestic violence documentation, substance use records, immigration status — but typically lack dedicated IT security staff. KoNote's security model is therefore architectural, not configurable. Security is enforced by the structure of the code, not by policies that a non-technical admin might misconfigure.

The system should be secure even if the operator doesn't fully understand why. Every security control described below is on by default, cannot be turned off through the admin interface, and fails closed rather than open. If a control can't determine whether an action is safe, it denies the action.

---

## Design Decisions

### 1. Encryption at Rest — All PII Fields

Every field containing personally identifiable information is Fernet-encrypted (AES-128-CBC + HMAC-SHA256). This is not optional. Property accessors (`client.first_name`) handle encryption and decryption transparently — calling code never touches ciphertext directly. Per-tenant encryption keys mean one agency's key cannot decrypt another agency's data.

The system validates encryption key round-trip on every startup. If the key is missing, corrupt, or misconfigured, the application will not start. This makes key misconfiguration a loud, immediate failure rather than a silent data exposure.

**Anti-pattern:** Relying on database-level encryption alone (doesn't protect against SQL injection or backup theft) or making encryption opt-in per agency.

### 2. Role-Based Access Control — Permission Matrix as Single Source of Truth

Four roles (Front Desk, Direct Service, Program Manager, Executive) are governed by an explicit permission matrix defined in one place. Every permission key is validated at import time — a typo in a permission key raises an error, not a silent denial. Missing entries in the matrix default to DENY, not ALLOW.

The matrix is checked at three layers: view decorator, middleware, and template tag. This means a permission is enforced even if one layer is accidentally bypassed.

**Anti-pattern:** Role checks scattered across individual views where one missed check means a bypass.

### 3. Fail-Closed Consent Filtering

PHIPA cross-program consent filtering returns empty results on failure, not all results. If the consent check cannot determine whether sharing is permitted, it denies access. Two enforcement functions cover the two access patterns: `apply_consent_filter()` for list views (querysets), `check_note_consent_or_403()` for single-note views.

This means a bug in consent logic results in a staff member seeing too little data, not too much. Over-restriction is recoverable; over-exposure is not.

**Anti-pattern:** Fail-open consent (show everything unless explicitly blocked). One bug = full data exposure.

### 4. Immutable Audit Log — Separate Database

All state-changing requests, client record views, and failed access attempts are logged to a separate PostgreSQL database. The Django ORM raises `PermissionError` on update or delete attempts against audit records. The database role used for the audit connection is INSERT-only at the PostgreSQL level.

Separating the audit database from the application database means that a compromised application cannot alter its own evidence trail.

**Anti-pattern:** Audit logs in the same database as application data (compromised app = compromised audit trail).

### 5. Negative Access Lists for Safety

`ClientAccessBlock` is checked BEFORE role-based access. If a staff member is blocked from a client (conflict of interest, DV perpetrator on staff), no role can override it. Blocks have no time-based expiry — they must be manually cleared by a Program Manager or higher.

This exists because domestic violence scenarios require individual-level blocking that supersedes all role permissions. A Direct Service worker who is a client's abuser must never see that client's records, regardless of their role.

**Anti-pattern:** Relying on role restrictions alone. DV scenarios require individual-level blocking that overrides all roles.

### 6. Session Security

Sessions time out after 30 minutes of inactivity. Sessions are stored server-side — the cookie contains only an opaque token, never session data. All cookies are set with `HttpOnly`, `Secure`, and `SameSite` flags. Content Security Policy uses nonce-based script allowlisting, blocking inline script injection.

These defaults are tuned for the environments where KoNote is actually used: shared workstations in shelters, drop-in centres, and community agencies where a staff member may walk away from an unlocked screen.

**Anti-pattern:** Long session timeouts in shared-computer environments (staff workstations in shelters and community centres).

### 7. Rate Limiting and Account Lockout

Login attempts are limited to 5 per minute. Password reset requests are limited to 10 per minute. After 5 consecutive failed login attempts, the account is locked for a 15-minute cooldown period. Passwords are hashed with Argon2 (memory-hard, GPU-resistant).

These controls protect against brute-force attacks without requiring the operator to configure a WAF or external rate limiter.

**Anti-pattern:** No rate limiting on login endpoints. Brute-force attacks on weak passwords.

### 8. Two-Person Safety Rules

Certain actions require two people to complete:

- **Alert cancellation**: staff recommends, Program Manager approves
- **DV flag removal**: staff requests, Program Manager approves
- **Data erasure**: Program Manager requests, admin executes

No single person can make a safety-critical change. This protects against both human error and coercion — a staff member under pressure from a client's abuser cannot unilaterally remove a safety flag.

**Anti-pattern:** Any safety-critical action completable by one person. Human error or coercion becomes unrecoverable.

### 9. Secure Exports with Time-Limited Links

Exports use UUID-based links that expire after 24 hours. Admins can revoke an export link before it is downloaded. Elevated exports (100+ records) have a 10-minute delay with admin notification, giving time to intervene if the export was unauthorized. Export files are stored outside the web root and served through Django, not directly by the web server.

**Anti-pattern:** Direct file download URLs that never expire. Leaked links = permanent data exposure.

### 10. Demo Mode Isolation

Demo users see demo data only. Real users see real data only. Demo users cannot modify agency settings. The `is_demo` flag is enforced at middleware and query level, not just in the UI — even if a demo user crafts a direct API request, they cannot reach production data.

This allows agencies to trial KoNote and train new staff without risk of contaminating real records or exposing real client data during a demonstration.

**Anti-pattern:** Test accounts that can see real data, or demo data mixed into production queries.

---

## Anti-Patterns Summary

| Anti-pattern | Why it's rejected |
|---|---|
| Opt-in encryption | Nonprofits won't enable it; one missed field = PII exposure |
| Scattered role checks | One missed check = bypass |
| Fail-open consent | One bug = full data exposure |
| Audit in same database | Compromised app = compromised evidence |
| Role-only access control | DV scenarios need individual blocking |
| Long session timeouts | Shared computers in shelters/community centres |
| No rate limiting | Brute-force attacks on weak passwords |
| Single-person safety actions | Human error or coercion becomes unrecoverable |
| Permanent download links | Leaked links = permanent data exposure |
| Mixed demo/real data | Test activity contaminates production |

---

## The Guiding Test

Ask: **"If a nonprofit runs this with zero IT expertise, can they accidentally make it insecure?"**

If the answer is yes, the security control is not architectural enough.

---

## Connections to Other Foundations

- **Data Sovereignty**: Security controls are the enforcement layer for sovereignty principles. Encryption protects community ownership; RBAC enforces community control; the immutable audit trail proves compliance with data governance commitments.
- **Collaborative Practice**: Session security and CSP protect the participant portal. Accessible, secure design ensures that collaborative features don't introduce attack vectors. Two-person safety rules protect DV participants.
- **Nonprofit Sustainability**: Security must be zero-config to be affordable. Every control described here works without a dedicated IT team, which is the sustainability constraint in action.

---

## Related Implementation Decisions

- `access-tiers.md` — Three permission tiers with progressive access control
- `phipa-consent-enforcement.md` — Cross-program consent filtering rules
- `encryption-key-rotation.md` — Key rotation procedures and custody
- `ai-feature-toggles.md` — Participant data never sent to cloud AI

---

## When to Revisit

If the Canadian nonprofit sector develops shared security infrastructure (e.g., a nonprofit SOC service or sector-wide managed security), some operational controls could potentially be relaxed. The principle itself — security must be architectural, not configurable — should not change.
