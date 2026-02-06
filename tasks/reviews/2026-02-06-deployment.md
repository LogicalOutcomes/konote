# Deployment Reliability Review

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

## Findings

**[HIGH-001] Missing .dockerignore file**
- Location: `.` (Root directory)
- Issue: No `.dockerignore` file exists in the repository.
- Impact: The `COPY . .` instruction in the `Dockerfile` will include the entire working directory in the image. This includes sensitive files like `.env`, the `.git` directory (containing full history), and local development artifacts (venv, __pycache__). This poses a significant security risk (secret leakage) and increases image size.
- Fix: Create a `.dockerignore` file listing `.git`, `.env`, `venv`, `__pycache__`, `*.pyc`, and other build artifacts. (Note: Do NOT exclude `*.mo` files as they are committed and required).
- Test: Build the image and inspect the filesystem: `docker run --rm -it <image_id> ls -la` to ensure `.git` and `.env` are absent.

**[MEDIUM-002] Audit Database Not Locked Down Automatically**
- Location: `entrypoint.sh`
- Issue: The `lockdown_audit_db` management command is not executed in `entrypoint.sh`.
- Impact: The `audit_writer` database user likely retains full privileges (including UPDATE and DELETE) on the audit database tables. This compromises the integrity of the audit trail, as a compromised application could modify or delete past audit logs.
- Fix: Add `python manage.py lockdown_audit_db` to `entrypoint.sh` immediately after the audit migrations.
- Test: Deploy the application and inspect the privileges of the `audit_writer` role in the audit database. It should only have INSERT and SELECT privileges on the `audit_log` table.

**[LOW-003] Testing Dependencies in Production Image**
- Location: `requirements.txt:23-24`
- Issue: `pytest` and `pytest-django` are included in the main `requirements.txt` file which is installed in the Dockerfile.
- Impact: Unnecessary packages increase the container image size and slightly expand the attack surface.
- Fix: Move testing dependencies to a separate `requirements-test.txt` or `requirements-dev.txt` and only install them in development/test environments or build stages.
- Test: Run `pip list` inside the built production container to verify `pytest` is not present.

## Deployment Runbook Gaps

The following critical procedures are missing from the deployment documentation:

- **Backup Procedure:** No documented steps for backing up the application and audit databases before running migrations.
- **Rollback Procedure:** No instructions on how to roll back a failed deployment or migration (e.g., restoring from backup, reverting image tag).
- **Key Rotation:** No procedure for rotating `SECRET_KEY` or `FIELD_ENCRYPTION_KEY` (which involves re-encrypting data).
- **Database Restore:** No verified steps for restoring the databases from backups in a disaster recovery scenario.

## Recommendations

1. **Create .dockerignore:** Immediately create a `.dockerignore` file to prevent sensitive data leakage.
2. **Automate Audit Lockdown:** Update `entrypoint.sh` to enforce audit database immutability on every startup.
3. **Optimize Dependencies:** Split requirements into base/production and dev/test to keep the production image lean.
4. **Document Recovery:** Create a "Disaster Recovery" runbook covering backup, restore, and rollback scenarios.
