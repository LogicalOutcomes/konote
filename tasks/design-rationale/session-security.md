---
drr: session-security
status: Draft - awaiting GK review
parent_principle: security-by-default
blast_radius: high
source: foundation-security-by-default.md §6 (2026-03-14)
enforcement:
  - type: django-system-check
    id: session_security_defaults
    description: "Verify SESSION_COOKIE_AGE <= 1800, SESSION_ENGINE is server-side, cookies have HttpOnly/Secure/SameSite flags"
  - type: pytest
    file: tests/drr/test_session_security.py
    description: "Assert inactivity timeout, cookie flags, CSP nonce headers on rendered responses"
  - type: semgrep
    rule: no-inline-scripts-without-nonce
    description: "Block <script>...</script> without a nonce, and inline event-handler attributes (onclick, onload, onsubmit, onchange, etc.) in templates"
  - type: codeowner
    paths: [konote/settings/, konote/middleware/session_timeout.py, "**/templates/**/base*.html"]
---

# DRR: Session Security

**Parent Principle:** [Security by Default](../principles/security-by-default.md)

## Core Decision

KoNote's session and browser-security defaults are tuned for the environments where it is actually used: **shared workstations in shelters, drop-in centres, and community agencies** where a staff member may walk away from an unlocked screen. The defaults cannot be weakened through the admin UI.

Specific requirements:

- **Idle session timeout: 30 minutes.** `SESSION_COOKIE_AGE` must be ≤ 1800 seconds.
- **Server-side session storage.** The cookie carries only an opaque token. Session data never travels in the cookie.
- **Cookie flags.** Every session cookie is set with `HttpOnly`, `Secure`, and `SameSite=Lax` (or stricter).
- **Content Security Policy.** Nonce-based script allowlisting is in effect on every rendered page. Inline scripts without a server-generated nonce are blocked by the browser.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| 8-hour or "remember me" session durations | Shared computers; walk-away risk |
| Client-side session storage (signed cookies carrying session data) | Cookie theft = full session state exposure |
| Inline `<script>` or `onclick="..."` attributes in templates | Undermines CSP; re-introduces XSS attack surface |
| `SameSite=None` on the session cookie without Secure | CSRF on shared networks |
| Configurable timeout via admin UI | Operator can accidentally weaken security; violates architectural principle |

## CI enforcement (detail)

1. **Django system check** `session_security_defaults` runs on boot and refuses to start if: `SESSION_COOKIE_AGE > 1800`, `SESSION_COOKIE_HTTPONLY` is False, `SESSION_COOKIE_SECURE` is False in production, `SESSION_COOKIE_SAMESITE` is `"None"`, or `SESSION_ENGINE` uses `signed_cookies`.
2. **Pytest** renders a protected page and asserts the response sets the session cookie with the correct flags and includes a CSP header with a nonce.
3. **Semgrep rule** scans all templates and flags (a) any `<script>` tag that does not carry `nonce="{{ request.csp_nonce }}"` or equivalent, AND (b) any inline event-handler attribute (`onclick`, `onload`, `onsubmit`, `onchange`, `onerror`, `onmouseover`, etc.) on any element. Both patterns undermine CSP and must be rewritten as external or nonce-bearing scripts.
4. **CODEOWNERS** — the `konote/settings/` package, `konote/middleware/session_timeout.py`, and base templates require review.

## When to revisit

If KoNote gains a meaningful non-shared-workstation user base (e.g., individual clinicians on personal devices) AND the shared-workstation use case is no longer dominant, per-user session duration could become configurable — but only as an *upper bound* that the admin cannot loosen above the architectural default.

## Related DRRs

- [rate-limiting-and-authentication](rate-limiting-and-authentication.md) — complementary: prevents brute-force; this DRR prevents session theft
- [audit-log-isolation](audit-log-isolation.md) — session events are audited
