# Deployment Reliability Review — KoNote

**Date:** 2026-02-06
**External Reviewer:** Jules (Google AI coding agent)
**Internal Verification:** Claude Code (same session)

---

## Summary

| Category | Pass | Fail | Warning |
|----------|------|------|---------|
| Container Security | | X | |
| Startup Reliability | X | | |
| Database Safety | | | X |
| Configuration Hygiene | X | | |
| Static Files | X | | |
| Recovery | X | | |
| Hosting Compatibility | X | | |

**Deployment Reliable:** With Fixes

The Dockerfile is well-structured (non-root user, UTF-8 locale, build-time
collectstatic, `set -e` in entrypoint). The main gaps are a missing
.dockerignore and the audit lockdown command not being called automatically.

---

## Findings

### [HIGH-001] Missing .dockerignore File

- **Location:** Repository root (file does not exist)
- **Issue:** No `.dockerignore` file. The `COPY . .` at Dockerfile:28 copies
  the entire working directory into the image, including `.git/` (full repo
  history), `__pycache__/`, local dev files, and any `.env` present.
- **Impact:** Secret leakage risk (if `.env` exists locally during build),
  bloated image size, full git history exposed inside container.
- **Fix:** Create `.dockerignore` excluding `.git`, `.env`, `venv`,
  `__pycache__`, `*.pyc`, `tests/`, `tasks/`, `docs/`, `.vscode/`, etc.
- **Test:** Build image, run `docker run --rm <image> ls -la` to verify
  `.git` and `.env` are absent.

**Verification:** Confirmed. No `.dockerignore` exists in the repository.

### [MEDIUM-001] Audit Database Not Locked Down Automatically

- **Location:** `entrypoint.sh` (missing step), `apps/audit/management/commands/lockdown_audit_db.py` (command exists)
- **Issue:** The `lockdown_audit_db` management command exists but is never
  called in `entrypoint.sh`. The audit database retains full privileges
  (UPDATE, DELETE) instead of being restricted to INSERT-only.
- **Impact:** A compromised application could modify or delete audit logs,
  undermining the audit trail integrity.
- **Fix:** Add `python manage.py lockdown_audit_db` to `entrypoint.sh`
  after the audit migration step.
- **Test:** Deploy and inspect `audit_writer` role privileges in PostgreSQL.

**Verification:** Confirmed. `lockdown_audit_db.py` exists at the expected
path but is not referenced in `entrypoint.sh`.

### [LOW-001] Testing Dependencies in Production Image

- **Location:** `requirements.txt:30-31`
- **Issue:** `pytest>=9.0` and `pytest-django>=4.11` are in the main
  `requirements.txt` and get installed in the production Docker image.
- **Impact:** Unnecessary image bloat and slightly expanded attack surface.
  Not a direct security risk.
- **Fix:** Move to `requirements-dev.txt` and only install in dev/test.
- **Test:** `pip list` inside production container should not show pytest.

**Verification:** Confirmed.

---

## What Passed

The Dockerfile and deployment config have many things right:

- Non-root user (`konote`) configured at Dockerfile:9, 37
- UTF-8 locale set (Dockerfile:4-6) — critical for French translations
- `set -e` in entrypoint.sh — migration failures block startup
- collectstatic runs at build time, not startup (Dockerfile:31)
- Uses `konote.settings.build` for build-time commands (no DB needed)
- Seed failure warns but doesn't block startup (entrypoint.sh:22)
- Security check blocks startup in production mode (entrypoint.sh:29)
- PORT from environment variable (entrypoint.sh:32)
- Logs to stdout/stderr (gunicorn --error-logfile - --access-logfile -)
- railway.json watchPatterns include relevant files

---

## Deployment Runbook Gaps

These are documentation items the deploying agency needs:

- **Backup procedure** — Steps for `pg_dump` of both app and audit databases
  before running migrations
- **Rollback procedure** — How to revert a failed deployment (restore DB
  from backup, roll back Docker image tag)
- **Key rotation** — Steps for rotating `FIELD_ENCRYPTION_KEY` using
  MultiFernet (once implemented — see SEC-FIX2)
- **Database restore** — Verified steps for restoring from backup in a
  disaster recovery scenario

---

## Recommendations

1. **Create .dockerignore immediately** — prevents accidental secret/history leakage
2. **Add lockdown_audit_db to entrypoint** — enforce audit immutability on every startup
3. **Split requirements** — separate dev/test dependencies from production
4. **Create disaster recovery runbook** — backup, restore, rollback procedures

---

## Review Metadata

- **Framework:** `tasks/code-review-framework.md` Prompt D (Deployment)
- **Tool:** Jules (jules.google) — Gemini-powered code review agent
- **Repo:** github.com/gilliankerr/KoNote-Redux (public, main branch)
- **Previous reviews:** Security, Privacy, Accessibility (all 2026-02-06)
- **Next scheduled:** After infrastructure changes (Dockerfile, entrypoint, Docker Compose)
