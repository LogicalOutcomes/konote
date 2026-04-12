---
drr: rate-limiting-and-authentication
status: Draft - awaiting GK review
parent_principle: security-by-default
blast_radius: high
source: foundation-security-by-default.md §7 (2026-03-14)
enforcement:
  - type: django-system-check
    id: auth_hardening
    description: "Verify Argon2PasswordHasher first in PASSWORD_HASHERS, rate-limit middleware installed, lockout policy configured"
  - type: pytest
    file: tests/drr/test_rate_limiting.py
    description: "Assert 6th login attempt within 1 minute is rate-limited; 5 consecutive failures lock the account for 15 minutes"
  - type: codeowner
    paths: [apps/accounts/views.py, apps/accounts/backends.py, konote/settings.py]
---

# DRR: Rate Limiting and Authentication

**Parent Principle:** [Security by Default](../principles/security-by-default.md)

## Core Decision

KoNote protects against brute-force authentication attacks architecturally — without requiring the operator to configure a WAF, external rate limiter, or custom middleware.

Specific requirements:

- **Password hashing: Argon2** (memory-hard, GPU-resistant). `Argon2PasswordHasher` must be first in `PASSWORD_HASHERS`.
- **Login rate limit: 5 attempts per minute** per IP and per username (whichever trips first).
- **Password reset rate limit: 10 requests per minute** per IP.
- **Account lockout: 5 consecutive failed login attempts → 15-minute cooldown** for that account.
- **Timing-safe comparisons** for authentication tokens, password reset tokens, and SSO assertions.

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

1. **Django system check** `auth_hardening` validates `PASSWORD_HASHERS[0]` is Argon2, confirms the rate-limiting middleware is installed, and confirms the lockout backend is configured.
2. **Pytest** simulates: (a) 6 login attempts within 60 seconds → 6th is rate-limited with 429, (b) 5 consecutive failed logins → account is locked and correct password is rejected for 15 minutes, (c) 11 password-reset requests within 60 seconds → 11th is rate-limited.
3. **CODEOWNERS** on auth-related files.

## When to revisit

If Azure AD SSO becomes the sole auth path for all tenants and local password login is removed entirely, the password-hashing requirement becomes moot — but the rate limiting on SSO callbacks and session-establishment endpoints still applies.

## Related DRRs

- [session-security](session-security.md) — once authenticated, session security takes over
- [audit-log-isolation](audit-log-isolation.md) — failed login attempts are audited
- [access-tiers](access-tiers.md) — after auth, RBAC governs what's accessible
