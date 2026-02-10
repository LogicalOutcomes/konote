# Security Review Report: KoNote Web

**Review Date:** 2026-02-03
**Reviewer:** Claude (automated security review)
**Review Type:** Comprehensive assessment against security-review-plan.md
**Codebase Version:** Current main branch

---

## Executive Summary

```
Gate Check Status: PASS
Maturity Score:    88/100
Production Ready:  Yes (with recommended fixes)
Critical Issues:   0
Important Issues:  3
Minor Issues:      4
```

**Overall Assessment:** The codebase demonstrates strong security fundamentals with proper encryption, RBAC enforcement, and audit logging. All gate checks pass. Three important issues should be addressed in the near term to improve defence in depth.

---

## Gate Check Results

| Gate | Status | Notes |
|------|--------|-------|
| G1 | ✓ PASS | No critical vulnerabilities found |
| G2 | ✓ PASS | All PII fields use `_*_encrypted` BinaryField pattern |
| G3 | ✓ PASS | `ProgramAccessMiddleware` enforces program-scoped access |
| G4 | ✓ PASS | `AuditMiddleware` logs to separate database via router |
| G5 | ✓ PASS | Session cookies: HttpOnly=True, Secure=True, SameSite=Lax |
| G6 | ✓ PASS | DEBUG=False in `production.py` |
| G7 | ✓ PASS | `FIELD_ENCRYPTION_KEY` loaded via `require_env()` |

---

## Section Scores

| Section | Score | Notes |
|---------|-------|-------|
| 1. Encryption & PII | 23/25 | Strong implementation; key rotation tested |
| 2. Access Control | 22/25 | RBAC enforced; one bypass path in reports |
| 3. Authentication | 13/15 | Rate limiting, Argon2; failed logins not audited |
| 4. Audit & Logging | 13/15 | Comprehensive coverage; missing failed auth logs |
| 5. OWASP & General | 17/20 | Good CSP; CDN scripts lack SRI |
| **Total** | **88/100** | |

---

## Findings

### Important (Should Fix Soon)

**[I1] XSS Risk in Chart Data Rendering**
- **Location:** [templates/reports/_tab_analysis.html:17](templates/reports/_tab_analysis.html#L17)
- **Issue:** Uses `{{ chart_data_json|safe }}` to inject JSON into a `<script>` tag. While `json.dumps()` escapes most characters, it does NOT escape `</script>` sequences. If a malicious user stores `</script><script>alert(1)</script>` in a target name or metric name, it could execute arbitrary JavaScript.
- **Impact:** Stored XSS if an attacker can control target/metric names (requires staff or admin access).
- **Fix:** Use Django's `json_script` template tag instead:
  ```html
  {{ chart_data_json|json_script:"chart-data" }}
  <script>
  const chartData = JSON.parse(document.getElementById('chart-data').textContent);
  </script>
  ```
- **Test:** Create a target with name `</script><script>alert('XSS')</script>` and verify it renders safely.

**[I2] Admin Bypass in Reports Access Control**
- **Location:** [apps/reports/views.py:158-159](apps/reports/views.py#L158-L159)
- **Issue:** The `_get_client_or_403` function in reports allows admins (`user.is_admin`) to access client data directly without checking program roles. This contradicts the RBAC model documented in CLAUDE.md which states admins without program roles should NOT access client data.
- **Impact:** Admin-only users can view client analysis data they shouldn't have access to.
- **Fix:** Remove the admin bypass and require program role overlap:
  ```python
  def _get_client_or_403(request, client_id):
      client = get_object_or_404(ClientFile, pk=client_id)
      user = request.user
      # Remove: if user.is_admin: return client
      user_program_ids = set(
          UserProgramRole.objects.filter(user=user, status="active")
          .values_list("program_id", flat=True)
      )
      # ... rest of function
  ```
- **Test:** Create an admin user with no program roles, attempt to access `/reports/client/<id>/analysis/`, verify 403 response.

**[I3] Failed Authentication Attempts Not Audited**
- **Location:** [apps/auth_app/views.py:42-44](apps/auth_app/views.py#L42-L44)
- **Issue:** When login fails due to invalid credentials, no audit log entry is created. Only successful logins are logged via `_audit_login()`.
- **Impact:** Cannot detect brute-force attacks or credential stuffing attempts via audit trail.
- **Fix:** Add audit logging for failed login attempts:
  ```python
  except User.DoesNotExist:
      _audit_failed_login(request, username)
      error = "Invalid username or password."
  ```
- **Test:** Attempt login with invalid credentials, verify audit log contains a failed login entry.

---

### Minor (Continuous Improvement)

**[M1] CDN Scripts Without Subresource Integrity (SRI)**
- **Location:** [templates/base.html:91-93](templates/base.html#L91-L93)
- **Issue:** HTMX and Chart.js are loaded from CDNs without SRI hashes. If a CDN is compromised, malicious code could be injected.
- **Improvement:** Add integrity attributes:
  ```html
  <script src="https://unpkg.com/htmx.org@2.0.4"
          integrity="sha384-..."
          crossorigin="anonymous"></script>
  ```

**[M2] No Custom 500 Error Page**
- **Location:** N/A (file does not exist)
- **Issue:** No `templates/500.html` found. In production, Django's default 500 page may expose less information, but a custom page provides better user experience and ensures no accidental information leakage.
- **Improvement:** Create a simple `templates/500.html` that shows a friendly error message without technical details.

**[M3] Audit Middleware Only Logs Successful Requests**
- **Location:** [konote/middleware/audit.py:30](konote/middleware/audit.py#L30)
- **Issue:** The condition `response.status_code < 400` means 403/404/500 responses are not logged. While this reduces noise, it also means access denials aren't captured.
- **Improvement:** Consider logging 403 responses specifically to track unauthorized access attempts:
  ```python
  if response.status_code == 403:
      self._log_access_denied(request, response)
  ```

**[M4] Demo Login Bypasses Rate Limiting**
- **Location:** [apps/auth_app/views.py:120-148](apps/auth_app/views.py#L120-L148)
- **Issue:** The `demo_login` view doesn't have rate limiting. While it requires `DEMO_MODE=True`, if enabled in production by mistake, it could be abused.
- **Improvement:** Add `@ratelimit` decorator to `demo_login` view, or ensure DEMO_MODE is never enabled in production via deployment checks.

---

## Detailed Section Analysis

### Section 1: Encryption & PII Protection (23/25)

**Encryption at Rest (9/10)**
- ✓ All PII fields use `_field_encrypted` BinaryField + property accessor
- ✓ Custom fields with `is_sensitive=True` are encrypted ([models.py:171-178](apps/clients/models.py#L171-L178))
- ✓ No PII in plaintext in logs (logging configured to WARNING level)
- ✓ Fernet key from `FIELD_ENCRYPTION_KEY` environment variable
- ✓ No hardcoded keys found
- ○ Could not verify cache doesn't store PII (no caching implementation found)

**Encryption in Transit (5/5)**
- ✓ HSTS enabled: `SECURE_HSTS_SECONDS = 31536000` ([production.py:12](konote/settings/production.py#L12))
- ✓ `SECURE_PROXY_SSL_HEADER` configured for reverse proxy
- ✓ No outbound API calls found that would need certificate validation

**Key Management (5/5)**
- ✓ `rotate_encryption_key` command exists and is documented
- ✓ Command has dry-run mode for safe testing
- ✓ Command validates keys before modifying data
- ✓ Key not exposed in error messages (returns generic `[decryption error]`)

**Error Handling (4/5)**
- ✓ Decryption errors return safe marker `[decryption error]`
- ✓ No `[decryption error]` string found in templates
- ✓ Form validation errors use cleaned_data, not raw input
- ✓ DEBUG=False in production
- ○ No custom 500 error page (M2)

### Section 2: Access Control & RBAC (22/25)

**Program-Scoped Access (8/10)**
- ✓ Middleware covers `/clients/<id>` and `/notes/client/<id>` patterns
- ✓ Middleware covers `/notes/<id>` by looking up client from note
- ✓ Admins without program roles blocked from client routes
- ✓ Client list views filter by user's accessible programs
- ✗ Admin bypass in reports view (I2)

**Role Hierarchy (5/5)**
- ✓ `ROLE_RANK` defines: front_desk < staff < program_manager
- ✓ `@minimum_role` decorator enforces role requirements
- ✓ Highest role stored in `request.user_program_role`

**Edge Cases (5/5)**
- ✓ Client in multiple programs: middleware checks intersection
- ✓ User with multiple roles: `max()` with `ROLE_RANK` key
- ✓ Removed program role: `status="active"` filter in queries
- ✓ New enrolment: no caching, queries run fresh

**Attack Scenario Testing (4/5)**
- ✓ IDOR protection: middleware validates program overlap
- ✓ Vertical escalation: `@minimum_role` decorator enforces
- ✓ Direct URL: middleware intercepts before view
- ○ API endpoints follow same pattern (HTMX uses same views)

### Section 3: Authentication & Sessions (13/15)

**Login Security (3/5)**
- ✓ Rate limiting: `@ratelimit(key="ip", rate="5/m")`
- ✓ Generic error messages: "Invalid username or password"
- ✗ Failed login attempts NOT logged (I3)
- ○ No account lockout mechanism (rate limit provides some protection)

**Session Security (5/5)**
- ✓ HttpOnly=True, Secure=True, SameSite=Lax
- ✓ Session timeout: 30 minutes (`SESSION_COOKIE_AGE = 1800`)
- ✓ Session invalidated on logout (Django default)
- ✓ Server-side sessions (`SESSION_ENGINE = "django.contrib.sessions.backends.db"`)

**Password Security (5/5)**
- ✓ Argon2 hasher (primary)
- ✓ Minimum 10 characters
- ✓ Common password check enabled
- ✓ Username similarity check enabled

### Section 4: Audit & Logging (13/15)

**Audit Coverage (4/5)**
- ✓ All POST/PUT/PATCH/DELETE logged by middleware
- ✓ Login events logged
- ✓ Logout events logged
- ✗ Failed authentication NOT logged (I3)
- ✓ Data exports logged with metadata

**Audit Integrity (5/5)**
- ✓ `lockdown_audit_db` command restricts to INSERT + SELECT
- ✓ Separate database configured via `DATABASE_ROUTERS`
- ✓ `AuditRouter` prevents cross-database writes
- ✓ Command is idempotent (safe to run multiple times)

**Audit Content (4/5)**
- ✓ Captures: user ID, display name, IP address
- ✓ Captures: action, resource type, resource ID
- ✓ Captures: timestamp, HTTP status
- ○ Old/new values not captured by middleware (would need signals)
- ✓ Graceful degradation: exceptions caught in middleware

### Section 5: OWASP & General Security (17/20)

**A02: Cryptographic Failures (3/4)**
- ✓ Fernet uses AES-128-CBC + HMAC-SHA256 (strong)
- ✓ No MD5/SHA1 for security purposes
- ○ `random` used in seed_demo_data.py (acceptable for demo data only)
- ✓ No sensitive data in URLs

**A03: Injection (4/4)**
- ✓ All queries use Django ORM
- ✓ Raw SQL in `lockdown_audit_db.py` uses config values, not user input
- ✓ No `eval()` or `exec()` with user input
- ✓ Template auto-escaping enabled (except one `|safe` usage - I1)

**A04: Insecure Design (4/4)**
- ✓ Principle of least privilege: role-based access
- ✓ Defence in depth: middleware + view checks
- ✓ Fail securely: 403 on permission errors

**A05: Security Misconfiguration (4/4)**
- ✓ DEBUG=False in production
- ✓ SECRET_KEY from environment
- ✓ ALLOWED_HOSTS from environment
- ✓ CSP headers configured comprehensively

**A08: Software and Data Integrity (2/4)**
- ✓ CSRF protection enabled
- ✓ CSRF tokens in all forms (35 templates verified)
- ○ CDN scripts lack SRI (M1)
- ○ No verification of third-party dependencies

---

## Recommendations

1. **Address Important Issues First:** Fix I1 (XSS), I2 (admin bypass), and I3 (failed login logging) before the next deployment.

2. **Add Failed Authentication Logging:** Create `_audit_failed_login()` function to log failed attempts with IP address and attempted username (not password).

3. **Consider Account Lockout:** After N failed attempts from an IP or for a username, implement temporary lockout or CAPTCHA challenge.

4. **Vendor CDN Assets:** Download HTMX and Chart.js to `/static/js/vendor/` to eliminate CDN dependency and enable CSP tightening.

5. **Add SRI Hashes:** If continuing to use CDNs, add integrity attributes to script tags.

6. **Create Error Pages:** Add `templates/404.html` and `templates/500.html` for better user experience and security.

7. **Log 403 Responses:** Consider modifying audit middleware to log access denied events for security monitoring.

---

## Regression Tests Needed

| Finding | Test Description | Suggested Location |
|---------|------------------|-------------------|
| I1 | Test that `</script>` in target names renders safely | tests/test_reports.py |
| I2 | Test that admin without program roles gets 403 on client analysis | tests/test_rbac.py |
| I3 | Test that failed login creates audit log entry | tests/test_auth.py |

---

## Comparison to Previous Review

This is the first formal security review using this plan format. Future reviews should track:
- Total findings by severity (baseline: 0 Critical, 3 Important, 4 Minor)
- Time to remediate Important issues
- Maturity score trend (baseline: 88/100)

---

## Review Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Reviewer | Claude (automated) | 2026-02-03 | — |
| Developer | | | |
| (Optional) Security Lead | | | |

---

*Report generated by Claude Code security review agent following tasks/security-review-plan.md*
