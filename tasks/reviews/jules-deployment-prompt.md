# Prompt to paste into Jules

Copy everything below the line into the Jules prompt box.

---

## Task: Deployment Reliability Review — Create Report

**DO NOT modify any application code.** Your only task is to create a single file:
`tasks/reviews/2026-02-06-deployment.md`

This file should contain a deployment reliability review report based on the analysis below.

## Role

You are a DevOps engineer specialising in Docker deployments for small
organisations. You understand that the teams deploying this software may
not have dedicated ops staff — the deployment must be resilient and
self-healing.

## Application Context

KoNote2 is deployed via Docker Compose to various hosting providers
(Azure, Railway, Elest.io, self-hosted). Each deployment is a single
agency instance.

**Deployment architecture:**
- Python 3.12-slim Docker image
- PostgreSQL 16 (two databases: app + audit)
- Gunicorn WSGI server (2 workers)
- WhiteNoise for static files
- Caddy as reverse proxy (optional)
- No Redis, no Celery, no async workers

**Startup sequence (entrypoint.sh):**
1. Run Django migrations (app database)
2. Run audit migrations (audit database)
3. Seed data (metrics, features, settings, templates)
4. Security check (blocks startup in production if critical issues found)
5. Start gunicorn

**Known deployment learnings:**
- Docker locale must be UTF-8 for French translations
- .po file compilation is fragile; .mo files are pre-compiled and committed
- SafeLocaleMiddleware falls back to English if translations fail
- Seed commands must never silently fail (use get_or_create, not guards)
- Entrypoint must be in railway.json watchPatterns

## Scope

**Files to review:**
- Dockerfile (and Dockerfile.alpine if present)
- docker-compose.yml
- docker-compose.demo.yml
- entrypoint.sh
- requirements.txt
- railway.json
- konote/settings/base.py (database config, security settings)
- konote/settings/production.py
- konote/settings/build.py
- konote/db_router.py
- seeds/ (all seed commands)
- apps/audit/management/commands/startup_check.py
- apps/audit/management/commands/lockdown_audit_db.py
- scripts/ (any deployment scripts)

## Checklist

### Container Security
- [ ] Non-root user configured (USER directive in Dockerfile)
- [ ] No secrets baked into image (check ENV, COPY, ARG directives)
- [ ] Base image is current and receives security updates
- [ ] Unnecessary packages not installed
- [ ] .dockerignore excludes sensitive files (.env, .git, venv)
- [ ] COPY . . does not include development/test files unnecessarily

### Startup Reliability
- [ ] Migrations run before app starts (order in entrypoint.sh)
- [ ] Migration failure blocks startup (set -e in entrypoint)
- [ ] Audit database migration runs separately
- [ ] Seed failure does not block startup (but warns loudly)
- [ ] Security check blocks startup in production mode
- [ ] Security check warns-only in demo mode
- [ ] Startup does not depend on external services being available

### Database Safety
- [ ] DATABASE_URL required (not optional with fallback)
- [ ] AUDIT_DATABASE_URL required (not optional with fallback)
- [ ] Connection timeouts configured
- [ ] Database router correctly routes audit models
- [ ] No migration creates irreversible data changes without backup warning

### Configuration Hygiene
- [ ] All required env vars use require_env() (fail loudly if missing)
- [ ] Optional env vars have safe defaults
- [ ] No default SECRET_KEY or FIELD_ENCRYPTION_KEY in code
- [ ] DEBUG defaults to False (not True)
- [ ] ALLOWED_HOSTS is not ['*'] in production

### Static Files
- [ ] collectstatic runs at build time (not startup)
- [ ] WhiteNoise configured for compressed static files
- [ ] Build settings (konote.settings.build) work without database

### Recovery
- [ ] Application recovers from temporary database outage
- [ ] Application recovers from temporary audit database outage
- [ ] Seed commands are idempotent (safe to run multiple times)
- [ ] No startup race conditions between migrations and seeds

### Hosting Provider Compatibility
- [ ] railway.json watchPatterns include all deployment-relevant files
- [ ] PORT environment variable respected (not hardcoded)
- [ ] Health check endpoint available (or Gunicorn responds to GET /)
- [ ] Logs go to stdout/stderr (no log files inside container)

## Output Format

Write the report in markdown with the following structure:

### Summary

| Category | Pass | Fail | Warning |
|----------|------|------|---------|
| Container Security | | | |
| Startup Reliability | | | |
| Database Safety | | | |
| Configuration Hygiene | | | |
| Static Files | | | |
| Recovery | | | |
| Hosting Compatibility | | | |

Deployment Reliable: Yes / No / With Fixes

### Findings

For each finding:
**[SEVERITY-NUMBER] Title**
- Location: file:line
- Issue: What is wrong
- Impact: What fails (startup crash? data loss? silent failure?)
- Fix: Specific change needed
- Test: How to verify

### Deployment Runbook Gaps
Items that should be documented but are not:
- Backup procedure before migration
- Rollback procedure if migration fails
- Key rotation steps
- Database restore procedure

### Recommendations
Improvements for deployment resilience
