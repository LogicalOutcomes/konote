# Prompt to paste into Jules

Copy everything below the line into the Jules prompt box.

---

## Task: Security Code Review — Create Report

**DO NOT modify any application code.** Your only task is to create a single file:
`tasks/reviews/2026-02-06-security.md`

This file should contain a security review report based on the analysis below.

## Role

You are a senior application security engineer conducting a white-box security
review. You have expertise in Django security, OWASP Top 10, and healthcare
data protection.

## Application Context

KoNote2 is a Django 5 web application that stores sensitive client information
(names, dates of birth, progress notes, outcome ratings) for nonprofit social
service agencies in Canada. Each agency runs its own instance.

**Threat model:**
- PRIMARY THREAT: Unauthorised access by authenticated users who should not
  see certain clients (program-scoped data isolation failure)
- SECONDARY THREAT: External attacker exploiting web vulnerabilities
  (injection, XSS, CSRF, authentication bypass)
- TERTIARY THREAT: Data exposure through infrastructure compromise
  (database breach mitigated by field-level encryption)
- OUT OF SCOPE: Physical access, social engineering, denial of service

**Key architectural decisions:**
- All PII encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256)
- Encryption key loaded from environment variable, never in code
- RBAC enforced at middleware level (ProgramAccessMiddleware) — users only
  access clients in their assigned programs
- Audit logs stored in a separate database with INSERT-only permissions
- Authentication via Azure AD SSO (primary) or local Argon2 (fallback)
- Server-rendered Django templates + HTMX (no JavaScript framework)
- CSP headers restrict script and style sources

## Scope

**Read these files first (critical path):**
- konote/encryption.py
- konote/middleware/program_access.py
- konote/middleware/audit.py
- konote/settings/base.py
- konote/settings/production.py
- apps/auth_app/views.py
- apps/auth_app/models.py
- apps/clients/models.py
- apps/clients/views.py
- apps/clients/forms.py

**Then review these (high priority):**
- apps/notes/views.py
- apps/notes/models.py
- apps/plans/views.py
- apps/reports/views.py
- apps/reports/csv_utils.py
- apps/clients/erasure_views.py
- apps/programs/models.py
- konote/db_router.py
- konote/urls.py
- static/js/app.js

**Out of scope:** venv/, locale/, docs/, .mo files, migration files (unless
they contain data manipulation logic)

## Checklist

### Gate Checks (all must pass — any failure = FAIL verdict)

| Gate | Requirement |
|------|-------------|
| G1 | No Critical vulnerabilities found |
| G2 | All PII fields use _*_encrypted BinaryField + property accessor |
| G3 | ProgramAccessMiddleware in MIDDLEWARE and enforcing on all client routes |
| G4 | AuditMiddleware logging to separate "audit" database |
| G5 | Session cookies: HttpOnly=True, Secure=True, SameSite=Lax |
| G6 | DEBUG=False in production settings |
| G7 | FIELD_ENCRYPTION_KEY loaded from environment (not hardcoded) |

### OWASP Top 10 Checks

For each, note: PASS / FAIL / NOT APPLICABLE, with file:line evidence.

- A01 Broken Access Control: Can User A access Client X in User B's program?
- A02 Cryptographic Failures: Any weak algorithms? Key exposed in logs/errors?
- A03 Injection: Any raw SQL with user input? Any eval/exec? Template |safe
  with user data?
- A04 Insecure Design: Does failure grant access? Is least privilege applied?
- A05 Security Misconfiguration: ALLOWED_HOSTS, CSP, security headers?
- A06 Vulnerable Components: Check requirements.txt versions against known CVEs
- A07 Auth Failures: Rate limiting on login? Generic error messages?
  Session fixation?
- A08 Data Integrity: CSRF on all forms? SRI on CDN scripts?

### RBAC-Specific Attack Scenarios

Test each scenario by tracing the code path:

1. IDOR: Staff user calls GET /clients/999/ where client 999 is in a different
   program — is this blocked? Where?
2. Vertical escalation: Front desk user submits POST to a staff-only endpoint —
   is this blocked? Where?
3. Admin bypass: Admin user (no program roles) tries to access /clients/123/ —
   is this blocked? Where?
4. Executive bypass: Executive-only user tries to access individual client
   data — is this blocked? Where?
5. HTMX abuse: Can an attacker craft an HTMX request that bypasses middleware?
6. Note access via ID: User accesses /notes/456/ for a note belonging to a
   client in another program — is this blocked?

### Encryption Checks

1. List every model field that stores PII — is it encrypted?
2. Search for any PII logged to stdout/stderr (check logger.* calls)
3. Check if form validation errors echo back submitted PII
4. Check if [decryption error] marker could appear in user-facing templates
5. Verify key rotation command works without data loss (review the code path)

## Output Format for the Report File

Write the report in markdown with the following structure:

### Executive Summary
Gate Check Status: PASS / FAIL
Production Ready: Yes / No / With Fixes
Critical Issues: count
High Issues: count
Medium Issues: count
Low Issues: count

### Gate Check Results Table
(one row per gate, status + evidence)

### Findings

For each finding:

**[SEVERITY-NUMBER] Title**
- Location: file.py:line_number
- Issue: What is wrong
- Impact: What an attacker could achieve
- Fix: Specific code change needed
- Test: How to verify the fix works

### Regression Tests Needed
Table of findings that need automated tests added

### Recommendations
Improvements that are not findings but would strengthen the security posture
