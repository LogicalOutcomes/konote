# Security Review Agent Prompt

You are conducting a **security review** for KoNote Web, a Django-based nonprofit case management system that handles sensitive client data (PII).

## Context

- **Tech stack:** Django 5, Python 3.12, PostgreSQL, HTMX
- **Encryption:** Fernet (AES-128-CBC + HMAC-SHA256) for PII fields
- **Access control:** Program-scoped RBAC via middleware
- **Audit:** Separate database with INSERT-only permissions
- **Auth:** Azure AD SSO or local with Argon2

## Your Task

1. Review the codebase against `tasks/security-review-plan.md`
2. Complete all Gate Checks (pass/fail)
3. Score each section of the maturity assessment
4. Document findings by severity
5. Provide production readiness verdict

## Files to Review (Priority Order)

**Critical — Read These First:**
```
konote/encryption.py
apps/clients/models.py
konote/middleware/program_access.py
apps/auth_app/views.py
apps/audit/models.py
konote/middleware/audit.py
konote/settings/base.py
```

**High Priority:**
```
apps/auth_app/models.py
apps/clients/views.py
apps/notes/views.py
apps/clients/forms.py
apps/programs/models.py
konote/db_router.py
```

**Medium Priority:**
```
apps/audit/management/commands/lockdown_audit_db.py
apps/clients/admin.py
templates/notes/*.html
static/js/app.js
```

## Gate Checks (All Must Pass)

| Gate | Check |
|------|-------|
| G1 | No Critical vulnerabilities found |
| G2 | All PII fields use encryption |
| G3 | RBAC middleware enabled and enforced |
| G4 | Audit logging functional |
| G5 | Session cookies secure (HttpOnly, Secure, SameSite) |
| G6 | DEBUG=False in production settings |
| G7 | Encryption key from environment variable |

**If ANY gate fails, verdict is FAIL regardless of maturity score.**

## Maturity Scoring

Score each section based on the checklist in `tasks/security-review-plan.md`:

| Section | Max Points |
|---------|------------|
| 1. Encryption & PII Protection | 25 |
| 2. Access Control & RBAC | 25 |
| 3. Authentication & Sessions | 15 |
| 4. Audit & Logging | 15 |
| 5. OWASP & General Security | 20 |
| **Total** | **100** |

**Passing threshold: 85/100**

## Attack Scenarios to Test

Don't just review code — consider these attack vectors:

1. **IDOR:** Can user in Program A access client in Program B?
2. **Vertical escalation:** Can front desk user access staff features?
3. **Authentication bypass:** Session fixation, cookie tampering?
4. **Encryption oracle:** Does `[decryption error]` leak information?
5. **Audit bypass:** Can any action avoid logging?
6. **HTMX abuse:** Can HTMX be used to bypass access controls?

## Output Format

### Executive Summary

```
Gate Check Status: PASS / FAIL
Maturity Score: XX/100
Production Ready: Yes / No / With Fixes
Critical Issues: X
Important Issues: X
Minor Issues: X
```

### Gate Check Results

| Gate | Status | Notes |
|------|--------|-------|
| G1 | ✓/✗ | |
| G2 | ✓/✗ | |
| ... | | |

### Section Scores

| Section | Score | Notes |
|---------|-------|-------|
| 1. Encryption & PII | X/25 | |
| 2. Access Control | X/25 | |
| 3. Authentication | X/15 | |
| 4. Audit & Logging | X/15 | |
| 5. OWASP & General | X/20 | |
| **Total** | **X/100** | |

### Findings

#### Critical (Must Fix)

**[C1] Title**
- **Location:** file.py:123
- **Issue:** Description of the vulnerability
- **Impact:** What an attacker could do
- **Fix:** How to remediate
- **Test:** How to verify the fix

#### Important (Should Fix)

**[I1] Title**
- **Location:** file.py:456
- **Issue:** Description
- **Impact:** Consequence
- **Fix:** Remediation

#### Minor (Nice to Have)

**[M1] Title**
- **Location:** file.py:789
- **Issue:** Description
- **Improvement:** Suggested enhancement

### Recommendations

Improvements for future development.

### Regression Tests Needed

| Finding | Test Description | Suggested Location |
|---------|------------------|-------------------|
| C1 | Test that... | tests/test_security.py |

## Rules

**DO:**
- Read every file in the critical priority list
- Check actual code, not just patterns
- Test RBAC with specific scenarios
- Verify encryption for ALL PII fields
- Look for PII leakage in templates, logs, errors
- Score objectively against the checklist

**DON'T:**
- Assume middleware catches everything
- Skip files because they "probably" are secure
- Mark style issues as Critical
- Give vague feedback without file:line references
- Pass a section without checking every item
- Say "looks good" without evidence
