# Security Review: KoNote Web Application

**Date:** 2026-03-07
**Scope:** Full codebase security review covering authentication, authorization, encryption, input validation, dependencies, infrastructure, and compliance.

---

## Executive Summary

**Overall Security Posture: STRONG**

KoNote demonstrates mature, well-implemented security across all areas reviewed. No critical or high-severity vulnerabilities were found. The application uses proper encryption for PII, comprehensive RBAC, rate-limited authentication, audit logging to a separate write-protected database, and well-configured security headers including CSP. The handful of medium-severity findings are configuration/documentation items rather than architectural flaws.

| Category | Rating | Summary |
|----------|--------|---------|
| Authentication | STRONG | Argon2 hashing, rate limiting, MFA, account lockout |
| Authorization (RBAC) | STRONG | Matrix-driven permissions, explicit deny default, DV safety blocks |
| Encryption & PII | STRONG | Fernet AES for all PII, per-tenant keys, key rotation support |
| Input Validation | STRONG | Django forms throughout, parameterised queries, no injection risks |
| Web Security (CSRF/XSS/CSP) | STRONG | CSP with nonces, CSRF hardened, autoescaping enforced |
| Infrastructure & Docker | STRONG | Non-root container, network isolation, log rotation |
| Audit & Compliance | STRONG | Separate write-protected audit DB, PHIPA consent enforcement |
| Dependencies | GOOD | Pinned ranges, no known CVEs, one version range to tighten |

---

## Findings Summary

### No Critical or High Vulnerabilities Found

### Medium Severity (5 findings)

| # | Finding | Location | Recommendation |
|---|---------|----------|----------------|
| M1 | `entrypoint.sh` checks `FERNET_KEY` but Django uses `FIELD_ENCRYPTION_KEY` | [entrypoint.sh](entrypoint.sh) line 10 | Rename to `FIELD_ENCRYPTION_KEY` to match settings and .env.example |
| M2 | CSV upload forms lack explicit file type validation | [apps/surveys/forms.py:219](apps/surveys/forms.py#L219), [apps/plans/views.py:1592](apps/plans/views.py#L1592) | Add `FileExtensionValidator(allowed_extensions=['csv'])` |
| M3 | Build settings contain a real-looking Fernet key | [konote/settings/build.py:9](konote/settings/build.py#L9) | Replace with obvious placeholder string |
| M4 | Ops container has Docker socket access | [docker-compose.yml:165](docker-compose.yml#L165) | Document risk; consider socket-proxy for high-threat environments |
| M5 | `weasyprint` version range too broad (`>=62.0,<69.0`) | [requirements.txt:38](requirements.txt#L38) | Tighten to `>=62.0,<64.0` |

### Low Severity (6 findings)

| # | Finding | Location | Recommendation |
|---|---------|----------|----------------|
| L1 | Deprecated decorators (`@minimum_role`, `@program_role_required`) still in use | [apps/auth_app/decorators.py](apps/auth_app/decorators.py) | Migrate to `@requires_permission` matrix |
| L2 | Custom fields don't warn when PII-indicating names lack `is_sensitive=True` | [apps/clients/models.py:734](apps/clients/models.py#L734) | Add validation warning for names containing SSN/SIN/address |
| L3 | Single `|safe` filter in consortia dashboard template | [templates/consortia/dashboard.html:185](templates/consortia/dashboard.html#L185) | Safe (json.dumps source), but consider JSON endpoint |
| L4 | `mark_safe()` in portal template tag | [apps/portal/templatetags/portal_tags.py:52](apps/portal/templatetags/portal_tags.py#L52) | Safe (static string), could use `format_html()` for consistency |
| L5 | No DRR for encryption key rotation procedures | — | Create `tasks/design-rationale/encryption-key-rotation.md` |
| L6 | Demo mode relies on `DEMO_MODE` env var for `@csrf_exempt` gate | [apps/auth_app/views.py:343](apps/auth_app/views.py#L343) | Verify never set to "true" in production (process check) |

---

## Detailed Review by Area

### 1. Authentication

**Rating: STRONG**

- **Password hashing**: Argon2 (primary) with PBKDF2 fallback — [base.py:196-200](konote/settings/base.py#L196)
- **Password policy**: 10-character minimum, common password check, similarity check, numeric-only rejection — [base.py:202-208](konote/settings/base.py#L202)
- **Rate limiting**: 5 attempts/minute on login, 10/min on Azure callback — [views.py:174](apps/auth_app/views.py#L174)
- **Account lockout**: IP-based, 5 failed attempts triggers 15-minute lockout — [views.py:20-45](apps/auth_app/views.py#L20)
- **MFA**: TOTP with backup codes, MFA secret encrypted at rest
- **Azure AD SSO**: Proper OIDC via Authlib, rate-limited callback
- **Session security**: Server-side (database), 30-minute timeout with activity reset, HTTPOnly + Secure + SameSite=Lax cookies
- **No hardcoded credentials**: All secrets from environment variables

### 2. Authorization (RBAC)

**Rating: STRONG**

- **Permission matrix**: Centralised in [permissions.py](apps/auth_app/permissions.py) with 83+ permission keys across 4 roles
- **Explicit deny default**: Unknown permissions return DENY — [permissions.py:486](apps/auth_app/permissions.py#L486)
- **Decorator enforcement**: `@requires_permission` validates permission keys at import time (catches typos)
- **DV safety**: Client access blocks enforced before permission matrix; "fail closed" pattern
- **Admin isolation**: `is_admin` grants instance config access but NOT client data access without program role
- **Middleware enforcement**: `ProgramAccessMiddleware` blocks cross-program access at request level
- **Executive tier**: Aggregate data only, no individual PII access

### 3. Encryption & PII

**Rating: STRONG**

- **Algorithm**: Fernet (AES-128-CBC + HMAC-SHA256) via cryptography library
- **Key management**: Master key required at startup (no fallback), per-tenant keys encrypted with master key (KEK pattern)
- **Key rotation**: Supported via comma-separated keys; management command with dry-run capability
- **Startup validation**: Django system check verifies encryption round-trip on every boot — [encryption.py:187-228](konote/encryption.py#L187)
- **Encrypted fields**: All PII across ClientFile (6 fields), User (email), ProgressNote (4 fields), Circle, Survey, Registration models
- **Property accessors**: Transparent encrypt/decrypt via Python properties; DecryptionError handled consistently
- **PII scrubbing for AI**: Two-pass approach (regex + known names) in [pii_scrub.py](apps/reports/pii_scrub.py)

### 4. Input Validation & Injection

**Rating: STRONG**

- **SQL injection**: All queries use Django ORM with parameterised queries. No raw SQL string formatting found. Audit lockdown command uses `psycopg.sql.Identifier()` for schema identifiers.
- **XSS**: Django autoescaping enforced. Only 1 `|safe` filter found (justified — json.dumps source). CSP with nonces blocks inline scripts.
- **CSRF**: Middleware enabled, `{% csrf_token %}` in all forms. One documented `@csrf_exempt` (emergency_logout) uses session-bound token with timing-safe comparison as compensating control.
- **Command injection**: No `eval()`, `exec()`, `os.system()`, or `subprocess(shell=True)` in production code.
- **CSV injection**: All CSV exports sanitised via `sanitise_csv_value()` — formula prefixes escaped.
- **Redirect validation**: `url_has_allowed_host_and_scheme()` used for all redirects.
- **File uploads**: CSV uploads decode as UTF-8 (implicit protection), but lack explicit `FileExtensionValidator` (M2).
- **No dangerous deserialisation**: Uses `json.loads()`, no pickle.

### 5. Web Security Headers

**Rating: STRONG**

- **Content Security Policy**: Tight defaults — `default-src 'self'`, `frame-src 'none'`, `object-src 'none'`, `form-action 'self'`, scripts require nonce — [base.py:262-275](konote/settings/base.py#L262)
- **HSTS**: 1-year with subdomains and preload — [production.py:119-121](konote/settings/production.py#L119)
- **X-Frame-Options**: DENY (with controlled exception for registration embed using CSP frame-ancestors)
- **X-Content-Type-Options**: nosniff
- **Referrer-Policy**: strict-origin-when-cross-origin
- **Permissions-Policy**: camera, microphone, geolocation, payment all denied (Caddy)
- **Server header**: Removed by Caddy

### 6. Multi-Tenancy Isolation

**Rating: STRONG**

- **Schema isolation**: django-tenants gives each agency its own PostgreSQL schema
- **Per-tenant encryption**: Each agency can have its own Fernet key (encrypted by master key)
- **Audit database**: Separate PostgreSQL database prevents schema pollution
- **Database routing**: `AuditRouter` + `TenantSyncRouter` ensure correct routing
- **No cross-tenant queries**: All querysets scoped via user's program roles and tenant schema

### 7. Infrastructure & Docker

**Rating: STRONG**

- **Non-root container**: `konote` user created and used — [Dockerfile:9,38](Dockerfile#L9)
- **Minimal base image**: `python:3.12-slim`
- **Network isolation**: Frontend/backend networks separated; databases on backend only
- **Port binding**: Django bound to 127.0.0.1 only (Caddy is the public interface)
- **Log rotation**: 10MB max, 3 files per service
- **Health checks**: All services (web, db, audit_db, ops) have health checks
- **Auto-healing**: autoheal container restarts unhealthy services
- **TLS**: Caddy auto-provisions Let's Encrypt certificates
- **Secrets**: All credentials from environment variables, never in compose file

### 8. Audit & Compliance

**Rating: STRONG**

- **Separate audit database**: Actions logged to dedicated PostgreSQL instance
- **Write protection**: `lockdown_audit_db` management command restricts to INSERT + SELECT only
- **ORM immutability**: `ImmutableAuditQuerySet` blocks `.update()` and `.delete()` at Python level
- **Comprehensive logging**: All state-changing requests, client record views, and failed access attempts (403s) captured
- **PHIPA consent enforcement**: `apply_consent_filter()` and `check_note_consent_or_403()` enforce cross-program clinical note visibility
- **Sensitive variable masking**: `SENSITIVE_VARIABLES_RE` hides secrets from Django error pages
- **Custom 403 handler**: Limits exception message length to prevent info leakage
- **Elevated export delay**: Bulk exports (100+ records) trigger 10-minute delay with admin notification

### 9. Dependencies

**Rating: GOOD**

- **Pinning strategy**: Range pins (`>=X.Y,<Z.0`) allow security patches while preventing breaking changes
- **No known CVEs**: All packages are current stable versions
- **Key packages**: Django 5.1, PostgreSQL 16, cryptography 43+, Argon2
- **One concern**: weasyprint range (`>=62.0,<69.0`) spans too many potential future versions (M5)

---

## PHIPA / PIPEDA Compliance Checklist

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| PII encrypted at rest | PASS | Fernet AES for all PII fields |
| Per-agency encryption keys | PASS | TenantKey model with KEK pattern |
| Audit trail for data access | PASS | Separate write-protected audit database |
| Cross-program consent | PASS | PHIPA consent filter on clinical notes |
| Session timeout | PASS | 30-minute idle timeout |
| Password strength | PASS | 10-char min, Argon2 hashing |
| Role-based access | PASS | Matrix-driven RBAC with 4 tiers |
| Data erasure capability | PASS | Erasure workflow in clients app |
| Breach notification readiness | PASS | Audit logs capture all access patterns |

---

## Recommended Actions (Prioritised)

### Do First (before next deploy)
1. **M1**: Fix `entrypoint.sh` to check `FIELD_ENCRYPTION_KEY` instead of `FERNET_KEY`

### Next Sprint
2. **M2**: Add `FileExtensionValidator` to CSV upload forms
3. **M3**: Replace build.py Fernet key with obvious placeholder
4. **M5**: Tighten weasyprint version range

### Ongoing
5. **L1**: Migrate deprecated decorators to `@requires_permission`
6. **L5**: Document key rotation procedures in a DRR
7. Keep Django and dependencies updated (security patches within pinned ranges)
8. Run periodic security audits using the existing `security_audit` management command

---

## Files Reviewed

**Settings & Configuration**: `konote/settings/base.py`, `production.py`, `development.py`, `test.py`, `build.py`
**Authentication**: `apps/auth_app/views.py`, `models.py`, `permissions.py`, `decorators.py`
**Middleware**: All 7 custom middleware files in `konote/middleware/`
**Encryption**: `konote/encryption.py`, `apps/tenants/models.py` (TenantKey)
**Access Control**: `apps/programs/access.py`, `apps/portal/middleware.py`
**Audit**: `apps/audit/models.py`, `konote/middleware/audit.py`, `lockdown_audit_db.py`
**Views**: Client, note, plan, event, survey, registration, admin, portal, report views
**Templates**: Searched all 2,464 templates for `|safe`, `mark_safe`, `autoescape off`
**Forms**: All form files across apps
**Infrastructure**: `Dockerfile`, `docker-compose.yml`, `Caddyfile`, `entrypoint.sh`
**Dependencies**: `requirements.txt`, `requirements-dev.txt`, `requirements-test.txt`

---

*Review conducted by Claude Code security analysis agents across 4 parallel workstreams. No code was modified during this review.*
