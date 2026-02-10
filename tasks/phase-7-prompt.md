# Phase 7 Prompt: Hardening & Deployment

Copy this prompt into a new Claude Code conversation. Open the `KoNote-web` project folder first.

---

## Prompt

I'm building KoNote Web, a nonprofit client management system. Phases 1-6 are done (all features built). I need you to do **Phase 7: Security Hardening & Deployment Guides**.

### Context

- Read `TODO.md` for task status
- Read `C:\Users\gilli\.claude\plans\idempotent-cooking-walrus.md` for architecture
- The app uses Django 5, PostgreSQL (two databases: app + audit), Docker Compose, Caddy for TLS
- Auth: Azure AD SSO or local with Argon2
- PII encrypted with Fernet, audit logs in separate INSERT-only database
- Deployable to: Azure (production), Elest.io (EU/GDPR), Railway (dev/prototype)

### What to Build

**1. Audit DB Permission Lockdown**
- Create a SQL script `scripts/lockdown_audit_db.sql` that:
  - REVOKEs UPDATE and DELETE on `audit_log` from `audit_writer`
  - GRANTs SELECT on `audit_log` to `audit_reader`
  - Verifies permissions are correct
- Create a Django management command `lockdown_audit` that runs this SQL
- Add to the deployment checklist

**2. Automated Security Tests**
- Create `tests/test_security.py` with tests for:
  - RBAC: Staff user cannot access `/admin/*` routes (expect 403)
  - RBAC: Staff in Program A cannot GET `/clients/<id>/` for a client only in Program B (expect 403)
  - RBAC: Admin can access all clients regardless of program
  - PII encryption: Create a client, then query the raw database — `_first_name_encrypted` should not contain the plaintext
  - Session: Unauthenticated requests to protected URLs redirect to `/auth/login/`
  - CSRF: POST without CSRF token returns 403
  - Rate limiting: 6th login attempt within 1 minute returns 429
- Use Django's `TestCase` and `Client` for all tests
- Run with: `python manage.py test tests/`

**3. CSP and Rate Limit Tuning**
- Review all templates for inline scripts/styles that violate CSP
- Add nonces if needed, or refactor inline code to external files
- Adjust rate limits based on realistic usage:
  - Login: 5/min/IP (already set)
  - API endpoints: 60/min/user
  - Export endpoints: 5/min/user
- Document the rate limits in a comment block in `konote/settings/base.py`

**4. Deployment Guide: Azure**
- Create `docs/deploy-azure.md`
- Step-by-step for a non-developer:
  - Create Azure App Service (Linux, Python 3.12)
  - Create Azure Database for PostgreSQL (two databases)
  - Configure Azure Key Vault for secrets
  - Register Azure AD app for SSO
  - Set environment variables
  - Deploy via GitHub Actions or Azure CLI
  - Run migrations and seed data
  - Verify audit DB lockdown
  - Set up custom domain and TLS

**5. Deployment Guide: Elest.io**
- Create `docs/deploy-elestio.md`
- Step-by-step:
  - Create Elest.io service using Docker Compose
  - Configure environment variables
  - Set AUTH_MODE=local (or integrate with external IdP)
  - GDPR considerations: data residency, retention settings
  - Verify TLS and security headers

**6. Deployment Guide: Railway**
- Create `docs/deploy-railway.md`
- Step-by-step:
  - Create Railway project from GitHub repo
  - Add PostgreSQL plugin (x2 for app + audit)
  - Set environment variables
  - The `railway.json` handles build/deploy commands automatically
  - Verify the app starts and runs migrations

**7. Agency Setup Guide**
- Create `docs/agency-setup.md`
- What a new agency does after deployment:
  - First admin logs in and creates their account
  - Set terminology for their organisation
  - Enable/disable features
  - Set up programs
  - Enable metrics from the library
  - Create plan and note templates
  - Invite staff and assign to programs
  - Create first client file

### Important Notes

- Write guides in plain language — the audience is nonprofit staff, not developers
- Use numbered steps with screenshots described in alt text
- Include "What success looks like" after each major step
- Commit docs and tests separately
- Update `TODO.md` as tasks are completed
