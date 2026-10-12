---
drr: rate-limiting-and-authentication
status: Draft - awaiting GK review
parent_principle: security-by-default
blast_radius: high
source: foundation-security-by-default.md §7 (2026-03-14)
enforcement:
  - type: django-system-check
    id: auth_hardening
    description: "Verify Argon2PasswordHasher first in PASSWORD_HASHERS, django_ratelimit installed, @ratelimit decorators on login/password-reset views, account-lockout helper wired into login_view"
  - type: pytest
    file: tests/drr/test_rate_limiting.py
    description: "Assert 6th login attempt within 1 minute is rate-limited; 5 consecutive failures lock the account for 15 minutes"
  - type: semgrep
    rule: timing-safe-token-comparison
    description: "In apps/auth_app/, forbid ==/!= comparisons on variables named *_token, *_assertion, or *_secret; require hmac.compare_digest"
  - type: codeowner
    paths: [apps/auth_app/views.py, apps/auth_app/decorators.py, konote/settings/]
---

# DRR: Rate Limiting and Authentication

**Parent Principle:** [Security by Default](../principles/security-by-default.md)

## Core Decision

KoNote protects against brute-force authentication attacks architecturally — without requiring the operator to configure a WAF, external rate limiter, or custom middleware.

Specific requirements:

- **Password hashing: Argon2** (memory-hard, GPU-resistant). `Argon2PasswordHasher` must be first in `PASSWORD_HASHERS`.
- **Login rate limit: 5 attempts per minute** per IP (via `@ratelimit(key="ip", rate="5/m", method="POST", block=True)` on `apps/auth_app/views.py::login_view`).
- **Password reset rate limit: 10 requests per minute** per IP (same decorator on reset-request views).
- **Account lockout: 5 consecutive failed login attempts → 15-minute cooldown** for the requesting IP. Implemented with the per-IP counter in `apps/auth_app/views.py` (`LOCKOUT_THRESHOLD`, `_get_lockout_key`, `_increment_lockout_counter`, `_clear_lockout_counter`). Lockout recovery path: automatic expiry after 15 minutes; administrators may clear the cache key manually if a genuine user is affected.
- **Timing-safe comparisons** for authentication tokens, password reset tokens, and SSO assertions. Any `==` or `!=` comparison on a variable matching `*_token`, `*_assertion`, or `*_secret` is forbidden; use `hmac.compare_digest` instead.

These controls are active by default. They cannot be disabled through the admin UI.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| No rate limiting on login | Brute-force attacks on weak passwords |
| PBKDF2 or bcrypt as primary hasher in 2026+ | Argon2 is the current best practice for password hashing; Argon2 resists GPU attacks better than PBKDF2 |
| Rate limit on IP only (not username) | Credential-stuffing attacks distribute by IP; per-username limits catch them |
| Indefinite account lockout on failure | Denial-of-service vector against legitimate users; 15 min is the balance |
| Configurable-away rate limits in admin UI | Operator can weaken security under pressure |

## CI enforcement (detail)

1. **Django system check** `auth_hardening` validates `PASSWORD_HASHERS[0]` is Argon2, that `django_ratelimit` is in `INSTALLED_APPS`, that `apps/auth_app/views.py::login_view` has the `@ratelimit` decorator, and that the lockout helpers (`_get_lockout_key` / `_increment_lockout_counter`) are referenced from `login_view`.
2. **Pytest** simulates: (a) 6 login attempts within 60 seconds → 6th is rate-limited with 429, (b) 5 consecutive failed logins → lockout cache key set and correct password is rejected for 15 minutes, (c) 11 password-reset requests within 60 seconds → 11th is rate-limited.
3. **Semgrep rule** `timing-safe-token-comparison` scans `apps/auth_app/` for `==` / `!=` against any variable whose name matches `*_token`, `*_assertion`, or `*_secret`, and flags the comparison; `hmac.compare_digest` is required.
4. **CODEOWNERS** on auth-related files (`apps/auth_app/views.py`, `apps/auth_app/decorators.py`) and the settings package.

## When to revisit

If Azure AD SSO becomes the sole auth path for all tenants and local password login is removed entirely, the password-hashing requirement becomes moot — but the rate limiting on SSO callbacks and session-establishment endpoints still applies.

## Related DRRs

- [session-security](session-security.md) — once authenticated, session security takes over
- [audit-log-isolation](audit-log-isolation.md) — failed login attempts are audited
- [access-tiers](access-tiers.md) — after auth, RBAC governs what's accessible
