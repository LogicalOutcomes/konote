# Deployment Review -- 2026-03-04

## Overall Verdict

**PASS WITH WARNINGS** -- The deployment stack is well-engineered with strong security defaults, a resilient startup sequence, comprehensive ops sidecar automation, and proper separation of concerns. Three warnings require attention: a baked-in demo Fernet key in `docker-compose.demo.yml`, the `COPY . .` directive pulling in seed data with realistic PII-like patterns, and a key rotation command that updates the key but does not re-encrypt existing data. No blockers for production deployment.

## Summary Table

| Category                  | Pass | Fail | Warning | N/A |
|---------------------------|------|------|---------|-----|
| Container Security (6)    |  4   |  0   |   2     |  0  |
| Startup Reliability (13)  | 13   |  0   |   0     |  0  |
| Database Safety (8)       |  7   |  0   |   1     |  0  |
| Configuration Hygiene (8) |  8   |  0   |   0     |  0  |
| Static Files (3)          |  3   |  0   |   0     |  0  |
| Recovery (6)              |  5   |  0   |   1     |  0  |
| Hosting Compatibility (6) |  6   |  0   |   0     |  0  |
| **Total (50)**            | **46** | **0** | **4** | **0** |

## Findings

### Container Security

**[CS-1] Non-root user -- PASS**
- Location: `Dockerfile:9,38` / `Dockerfile.alpine:30,63`
- Evidence: Both Dockerfiles create a dedicated `konote` group/user and switch to `USER konote` before the `CMD` instruction. The entrypoint runs as non-root.

**[CS-2] No baked secrets in production image -- WARNING**
- Location: `docker-compose.demo.yml:23-24`
- Issue: The demo compose file bakes a known Fernet key (`ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=`) and a demo SECRET_KEY directly into the file. While the demo file carries clear warnings ("NOT SECURE", "do not use for real client data"), the same key appears in `konote/settings/build.py:9` as a build-time default, and `startup_check.py:191` explicitly checks for it as an insecure key.
- Impact: Low. The demo file is clearly labelled. The `startup_check` command would block this key in production mode. The build settings key never reaches runtime.
- Fix: No action needed for production. Consider rotating the demo Fernet key value periodically so it does not become a well-known constant if the repo becomes public.

**[CS-3] Current base image -- PASS**
- Location: `Dockerfile:1` / `Dockerfile.alpine:5,22` / `Dockerfile.ops:1`
- Evidence: `python:3.12-slim` (Debian-based), `python:3.12-alpine` (Alpine variant), `alpine:3.21` (ops). All are current stable releases. `postgres:16-alpine` in compose files is also current.

**[CS-4] No unnecessary packages -- PASS**
- Location: `Dockerfile:14-22`
- Evidence: Packages are limited to WeasyPrint runtime dependencies (`libpango`, `libcairo`, `libgdk-pixbuf`, `libffi-dev`, `shared-mime-info`) plus `curl` for healthchecks. The `--no-install-recommends` flag is used. `rm -rf /var/lib/apt/lists/*` cleans the cache. The Alpine Dockerfile uses `--no-cache` and a multi-stage build that excludes build tools from the final image.

**[CS-5] .dockerignore excludes sensitive files -- PASS**
- Location: `.dockerignore:6-7`
- Evidence: `.env`, `.env.*`, `.vscode/`, `.idea/`, `.claude/`, `tests/`, `docs/`, `tasks/`, `*.md` are all excluded. This prevents environment files and secrets from being copied into the image.

**[CS-6] COPY does not include secrets -- WARNING**
- Location: `Dockerfile:29` (`COPY . .`)
- Issue: The `COPY . .` directive copies the entire project into the image. While `.dockerignore` excludes `.env` files, the `seeds/demo_client_fields.py` file contains realistic-looking PII data (phone numbers, email addresses, emergency contacts). These are clearly demo data with `@example.com` addresses and `555-` phone numbers, but the pattern of realistic-looking personal data in the container image is worth noting.
- Impact: Very low. The data is clearly fictional demo content (example.com emails, 555 numbers). No real PII is present.
- Fix: No immediate action needed. If the repo goes public, consider whether the demo data directory should be excluded from production images.

### Startup Reliability

**[SR-1] set -e present -- PASS**
- Location: `entrypoint.sh:2`
- Evidence: `set -e` is the first statement, ensuring any non-zero exit code halts the script. This is critical because `startup_check` must be able to block startup.

**[SR-2] App migrations before seeds -- PASS**
- Location: `entrypoint.sh:13-14` (migrate_default), then `entrypoint.sh:44-45` (seed)
- Evidence: `migrate_default` runs at line 13, `migrate` (tenant schemas) at line 19, seeds at line 45. Correct order.

**[SR-3] Audit migrations before audit commands -- PASS**
- Location: `entrypoint.sh:34` (migrate_audit), then `entrypoint.sh:37-38` (lockdown_audit_db)
- Evidence: `migrate_audit` runs first, then `lockdown_audit_db` checks for the audit_log table's existence before applying permissions. Correct sequencing.

**[SR-4] Tenant migrations after app migrations -- PASS**
- Location: `entrypoint.sh:13` (migrate_default), then `entrypoint.sh:19` (migrate = migrate_schemas)
- Evidence: `migrate_default` applies all migrations to the public schema first, then `migrate` (which django-tenants overrides as `migrate_schemas`) applies tenant-app migrations to non-public tenant schemas. Correct order.

**[SR-5] Ghost healer before migrate -- PASS**
- Location: `apps/tenants/management/commands/migrate_default.py:285-317`
- Evidence: The `handle()` method calls `_remove_ghost_tenant_migrations()` before `super().handle()` (Django's migrate). Ghost records are removed first, then migrate runs with clean state.

**[SR-6] 5 phases in order -- PASS**
- Location: `apps/tenants/management/commands/migrate_default.py:82-279,285-461`
- Evidence: Phase 1 (physical detection of missing columns/tables, lines 117-188), Phase 2 (dependency propagation, lines 212-241), Phase 3 (bulk removal, lines 245-252), Phase 4 (consistency pre-flight, lines 260-279), Phase 5 (auto-fake duplicates, lines 345-452). All five phases execute in order within `handle()`.

**[SR-7] Phase 5 auto-fake handles duplicates -- PASS**
- Location: `apps/tenants/management/commands/migrate_default.py:345-452`
- Evidence: Phase 5 catches both `DuplicateColumn`/`DuplicateTable` errors (via `psycopg.errors`) and `InconsistentMigrationHistory` errors. For duplicate schema, it verifies ALL checkable operations exist before faking. For missing dependencies, it auto-fakes them. Safety limit of 50 iterations prevents infinite loops.

**[SR-8] Seed failures don't abort startup -- PASS**
- Location: `entrypoint.sh:45`
- Evidence: `python manage.py seed 2>&1 || echo "WARNING: Seed failed..."`. The `|| echo` prevents `set -e` from killing the script on seed failure. Same pattern for `merge_duplicate_themes` (line 53) and `lockdown_audit_db` (line 38).

**[SR-9] Security check blocks prod startup -- PASS**
- Location: `entrypoint.sh:65` / `apps/audit/management/commands/startup_check.py:114-147`
- Evidence: `startup_check` is called without error suppression (no `|| echo`), so `set -e` will halt the script if it exits non-zero. In production mode (`_handle_production_mode`), critical failures cause `sys.exit(1)` which blocks startup. Critical checks include: database URLs, encryption key validity (including insecure key detection), secret key, and security middleware.

**[SR-10] Demo mode warns visibly -- PASS**
- Location: `apps/audit/management/commands/startup_check.py:84-112`
- Evidence: In demo mode, `_handle_demo_mode` prints a large banner: "KoNote IS RUNNING IN DEMO MODE" with "DO NOT use this instance for real client data" warning. It always exits 0 (allows startup) but makes the security posture unmistakable in logs.

**[SR-11] Translation check non-blocking -- PASS**
- Location: `entrypoint.sh:58`
- Evidence: `python manage.py check_translations 2>&1 || echo "WARNING: Translation issues detected (non-blocking -- app will start)"`. Failure is caught and logged but does not stop startup. The command itself also does `sys.exit(0)` for warnings in non-strict mode (`check_translations.py:246`).

**[SR-12] Gunicorn starts only after all steps -- PASS**
- Location: `entrypoint.sh:68-76`
- Evidence: Gunicorn (`exec gunicorn ...`) is the last statement in the script. All migrations, seeds, checks, and tenant setup run sequentially before it. The `exec` replaces the shell process with gunicorn (correct for signal handling).

**[SR-13] No external service calls during startup -- PASS**
- Location: Full `entrypoint.sh` review
- Evidence: No `curl`, `wget`, or API calls to external services appear in the startup sequence. All operations target the local database or filesystem. The `check_translations` command reads local `.mo`/`.po` files only.

### Database Safety

**[DB-1] DATABASE_URL required -- PASS**
- Location: `konote/settings/base.py:165`
- Evidence: `require_env("DATABASE_URL")` raises `ImproperlyConfigured` if not set. No fallback value.

**[DB-2] AUDIT_DATABASE_URL required -- PASS**
- Location: `konote/settings/base.py:170`
- Evidence: `require_env("AUDIT_DATABASE_URL")` raises `ImproperlyConfigured` if not set. No fallback value.

**[DB-3] Connection timeouts configured -- PASS**
- Location: `konote/settings/base.py:176-179`
- Evidence: `connect_timeout = 10` is set for all PostgreSQL backends in the `OPTIONS` dict. This prevents indefinite hangs on DB connection failures.

**[DB-4] DB router routes audit models correctly -- PASS**
- Location: `konote/db_router.py:31-57`
- Evidence: `AuditRouter.db_for_read()` and `db_for_write()` return `"audit"` for `app_label == "audit"`. `allow_migrate()` returns `db == "audit"` for audit app and `False` for non-audit apps targeting the audit DB. Cross-database relations are correctly restricted.

**[DB-5] DB router routes tenant models -- PASS**
- Location: `konote/settings/base.py:186-193`
- Evidence: `DATABASE_ROUTERS` lists `AuditRouter` first (returns definitively for audit), then `django_tenants.routers.TenantSyncRouter` (handles tenant/shared app routing). The comment explains why AuditRouter must come first.

**[DB-6] TenantSyncRouter with migrate_default -- PASS**
- Location: `apps/tenants/management/commands/migrate_default.py:296-310`
- Evidence: `migrate_default` temporarily removes `TenantSyncRouter` from `DATABASE_ROUTERS` so all migrations can apply to the public schema. It restores the original router list in a `finally` block, ensuring cleanup even on errors.

**[DB-7] No irreversible migrations without warning -- PASS**
- Location: `seeds/` and management commands review
- Evidence: No data-destructive migrations were found in the startup sequence. The seed command uses `get_or_create` for idempotency. The demo cleanup only deletes `is_demo=True` records.

**[DB-8] Backup command with retry -- WARNING**
- Location: `scripts/ops-backup.sh:44-52` / `scripts/backup-vps.sh` (no retry)
- Issue: The ops sidecar backup (`ops-backup.sh`) has a single retry with 60-second delay (`dump_with_retry`). However, the standalone `backup-vps.sh` script does NOT have retry logic -- it relies on `set -euo pipefail` and would fail on the first `pg_dump` error.
- Impact: Medium. The ops sidecar is the primary backup mechanism for OVHcloud deployments and has retry. The standalone script is a secondary/legacy tool. Azure backups use a separate PowerShell script which also lacks retry.
- Fix: Add `dump_with_retry` pattern to `backup-vps.sh` for consistency. The Azure backup script prompts interactively so retry is less critical there.

### Configuration Hygiene

**[CH-1] require_env() for required vars -- PASS**
- Location: `konote/settings/base.py:17-25`
- Evidence: `require_env()` raises `ImproperlyConfigured` with a helpful message. Used for `SECRET_KEY` (line 32), `DATABASE_URL` (line 165), `AUDIT_DATABASE_URL` (line 170), and `FIELD_ENCRYPTION_KEY` (line 326).

**[CH-2] Safe defaults for optional vars -- PASS**
- Location: `konote/settings/base.py` (multiple lines)
- Evidence: `AUTH_MODE` defaults to `"local"` (line 37). `DEMO_MODE` defaults to empty/false (line 40). `OPENROUTER_API_KEY` defaults to `""` (line 386). `EMAIL_BACKEND` defaults to console (line 358). All optional vars use `os.environ.get()` with safe defaults.

**[CH-3] No default SECRET_KEY -- PASS**
- Location: `konote/settings/base.py:32`
- Evidence: `SECRET_KEY = require_env("SECRET_KEY")` -- no fallback. The `build.py` file sets a build-time-only default (`"build-only-not-for-runtime"`) that is never used at runtime. `startup_check.py:208-217` additionally checks for known insecure patterns.

**[CH-4] No default FIELD_ENCRYPTION_KEY -- PASS**
- Location: `konote/settings/base.py:326`
- Evidence: `FIELD_ENCRYPTION_KEY = require_env("FIELD_ENCRYPTION_KEY")` -- no fallback. `startup_check.py:190-194` also checks for the known dev/demo default key and blocks production if found.

**[CH-5] DEBUG defaults False -- PASS**
- Location: `konote/settings/base.py:33` / `konote/settings/production.py:24`
- Evidence: `DEBUG = False` in both base and production settings. There is no `os.environ.get("DEBUG")` that could be set to True. `startup_check.py:243-247` additionally warns if DEBUG is True.

**[CH-6] ALLOWED_HOSTS not ['*'] -- PASS**
- Location: `konote/settings/production.py:90-128`
- Evidence: `ALLOWED_HOSTS` starts as the parsed `ALLOWED_HOSTS` env var. Platform-specific domains are appended for Railway, Azure, and Elestio. If nothing is configured, it falls back to `["localhost", "127.0.0.1"]` -- never `["*"]`. The `build.py` file uses `["*"]` but that is only active during `collectstatic`.

**[CH-7] AI_API_KEY optional -- PASS**
- Location: `konote/settings/base.py:386`
- Evidence: `OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")`. Empty default, AI features are hidden when the key is empty.

**[CH-8] OLLAMA_BASE_URL optional -- PASS**
- Location: Full settings review
- Evidence: No `OLLAMA_BASE_URL` was found in settings files. Based on the DRR (`self-hosted-llm-infrastructure.md` mentioned in CLAUDE.md), Ollama integration appears to use `OPENROUTER_API_KEY` or is configured via separate env vars not enforced in settings. The absence of a required OLLAMA variable is correct -- it is optional infrastructure.

### Static Files

**[SF-1] collectstatic at build time -- PASS**
- Location: `Dockerfile:32` / `Dockerfile.alpine:54`
- Evidence: `RUN python manage.py collectstatic --noinput --settings=konote.settings.build` runs during the Docker build, not at startup. Static files are baked into the image.

**[SF-2] WhiteNoise configured -- PASS**
- Location: `konote/settings/base.py:104,311-315`
- Evidence: `whitenoise.middleware.WhiteNoiseMiddleware` is in MIDDLEWARE (line 104). `STORAGES` uses `whitenoise.storage.CompressedManifestStaticFilesStorage` (line 313). WhiteNoise is positioned before TenantMainMiddleware so static files are served without requiring tenant resolution.

**[SF-3] Build settings work without DB -- PASS**
- Location: `konote/settings/build.py:6-9,17-26`
- Evidence: Build settings set SQLite in-memory databases, a dummy SECRET_KEY, and a dummy FIELD_ENCRYPTION_KEY. No real database connection is required during `collectstatic`. All `require_env` calls are satisfied by `os.environ.setdefault()` before importing base settings.

### Recovery

**[RC-1] DB outage leads to clean exit + restart -- PASS**
- Location: `docker-compose.yml:12,48-52`
- Evidence: `restart: unless-stopped` on the web container. `depends_on` with `condition: service_healthy` for both databases ensures the web container waits for healthy databases before starting. If the DB goes down after startup, gunicorn will return 500s and the healthcheck (`curl -f http://localhost:8000/auth/login/`) will fail, triggering Docker's restart policy. The `autoheal` service (lines 112-121) provides an additional self-healing layer.

**[RC-2] Audit DB outage leads to clean exit -- PASS**
- Location: `docker-compose.yml:48-52` / `entrypoint.sh:34`
- Evidence: The web container depends on `audit_db: condition: service_healthy`. If audit_db is unhealthy at startup, the web container will not start. If `migrate_audit` fails during startup, `set -e` halts the script. The `lockdown_audit_db` failure is caught with `|| echo` (non-blocking) because the audit table might not exist yet on first boot.

**[RC-3] Seeds idempotent -- PASS**
- Location: `apps/admin_settings/management/commands/seed.py` (throughout)
- Evidence: All seed operations use `get_or_create` (metrics line 97, feature toggles line 169, instance settings line 219, programs lines 286-330). Demo data cleanup (`_cleanup_old_demo_data` line 226) only deletes `is_demo=True` records. Re-running seed is safe at any time.

**[RC-4] No startup race conditions -- PASS**
- Location: `docker-compose.yml:48-52` / `entrypoint.sh` (sequential)
- Evidence: Docker Compose healthchecks ensure databases are ready before web starts. Within the entrypoint, all operations are sequential (no background processes or `&`). The web container runs a single gunicorn process with `exec` (PID 1). The ops sidecar has its own database readiness check (`ops-entrypoint.sh:55-66`).

**[RC-5] Key rotation safe if interrupted -- WARNING**
- Location: `apps/auth_app/management/commands/rotate_encryption_key.py:142`
- Evidence: The key rotation command wraps all work in `transaction.atomic()` (line 142), so interruption would roll back the entire transaction cleanly -- no records would be left in a half-encrypted state. However, `apps/tenants/management/commands/rotate_tenant_key.py:62-68` updates the tenant key record BEFORE re-encrypting data. The command explicitly states "existing encrypted data must be re-encrypted separately using a data migration command (not yet implemented)" (line 73-75). This means if the tenant key is rotated, existing encrypted data becomes unreadable until a separate re-encryption step is run.
- Impact: Medium. The per-field `rotate_encryption_key` command is safe (atomic). The per-tenant `rotate_tenant_key` command has an incomplete workflow -- it saves the new key but leaves data encrypted with the old key.
- Fix: Either (a) implement the data re-encryption step within `rotate_tenant_key` wrapped in a transaction, or (b) document clearly that `rotate_tenant_key` must not be used without the companion data migration command.

**[RC-6] Tenant provisioning idempotent -- PASS**
- Location: `apps/tenants/management/commands/setup_public_tenant.py:87-91`
- Evidence: `setup_public_tenant` checks `AgencyDomain.objects.filter(domain=domain).exists()` and exits immediately if already registered. It also handles the edge case where the Agency exists but the domain does not (lines 95-107). `provision_tenant` uses `Agency.save()` which would fail on duplicate schema_name (unique constraint), making it safe against double-provisioning.

### Hosting Compatibility

**[HC-1] railway.json watchPatterns -- PASS**
- Location: `railway.json:12`
- Evidence: `watchPatterns` restricts deploys to `**/*.py`, `**/*.html`, `**/*.css`, `**/*.js`, `**/*.po`, `**/*.mo`, `requirements.txt`, `Dockerfile`, `entrypoint.sh`. Changes to markdown, docs, or tasks will not trigger a deploy. This prevents unnecessary deployments.

**[HC-2] PORT env var respected -- PASS**
- Location: `entrypoint.sh:68`
- Evidence: `PORT=${PORT:-8000}` uses the platform-provided PORT or defaults to 8000. Gunicorn binds to `0.0.0.0:$PORT` (line 70). Railway, Azure, and other platforms inject PORT automatically.

**[HC-3] Health check endpoint -- PASS**
- Location: `konote/middleware/health_check.py:22-23` / `railway.json:8`
- Evidence: `HealthCheckMiddleware` intercepts `GET /health/` and returns a 200 "ok" response BEFORE tenant resolution middleware runs. This is critical because health probes from Railway/Docker arrive on internal IPs that are not registered as tenant domains. Railway uses `/auth/login/` as the healthcheck path (which requires tenant resolution to succeed), while the Docker compose healthcheck also uses `/auth/login/` (line 43). The `/health/` endpoint serves as a backup for load balancers and internal probes.

**[HC-4] Logs to stdout/stderr -- PASS**
- Location: `konote/settings/base.py:391-422` / `entrypoint.sh:70-76`
- Evidence: Django logging uses `StreamHandler` which outputs to stderr. Gunicorn is configured with `--error-logfile -` and `--access-logfile -` (dash = stdout/stderr). Ops sidecar cron jobs redirect to `/proc/1/fd/1` (container stdout). Docker logging driver (`json-file` with max-size 10m, 3 files) is configured in compose.

**[HC-5] OVHcloud scripts no hardcoded credentials -- PASS**
- Location: `scripts/deploy-konote-vps.sh`, `scripts/backup-vps.sh`, `scripts/ops-backup.sh`
- Evidence: `deploy-konote-vps.sh` generates all credentials locally using `secrets.token_urlsafe()` and `Fernet.generate_key()` (lines 237-241). Credentials are transmitted through the SSH tunnel and written to `.env` on the VPS (line 356). No passwords or keys are hardcoded. The `.env` file is locked down to `chmod 600` owned by root (lines 417-418). Backup scripts read credentials from environment variables / `.env` file.

**[HC-6] Azure ALLOWED_HOSTS prefers custom domain -- PASS**
- Location: `konote/settings/production.py:102-107`
- Evidence: For Azure App Service, both the custom site name and `.azurewebsites.net` wildcard are added. The `_split_csv_env("ALLOWED_HOSTS")` is processed first (line 90-92), so an explicitly set custom domain takes precedence. For Azure Container Apps, `.azurecontainerapps.io` is added (line 111). `setup_public_tenant.py:22-40` also has logic to prefer custom domains over `.azurecontainerapps.io` when picking the tenant domain.

## Deployment Runbook Gaps

1. **Tenant key rotation workflow incomplete.** `rotate_tenant_key` saves a new encryption key but does not re-encrypt existing data. The command output mentions this gap but there is no companion command yet. A runbook step for key rotation would currently leave an agency with unreadable encrypted data.

2. **No documented restore procedure.** The ops sidecar creates and verifies backups, but there is no management command or script for restoring from backup. The `ops-backup-verify.sh` script demonstrates the restore workflow (pg_restore into a temp DB) but this is a verification step, not a production restore procedure.

3. **No migration rollback guidance.** The ghost healer handles forward-only recovery well, but there is no documented procedure for rolling back a bad migration that has already been applied. For a small-ops team, a "how to roll back" section would reduce downtime during incidents.

4. **Backup-vps.sh lacks retry.** Unlike the ops sidecar's `ops-backup.sh`, the standalone `backup-vps.sh` script has no retry logic for transient database failures.

## Recommendations

1. **Low effort / High value:** Add retry logic to `scripts/backup-vps.sh` to match the ops sidecar's `dump_with_retry` pattern. This is a 5-line change that prevents backup failures from transient database issues.

2. **Medium effort / High value:** Complete the `rotate_tenant_key` command to include data re-encryption within an atomic transaction, or create a companion `re_encrypt_tenant_data` command. Until this is done, document that `rotate_tenant_key` must not be used in production.

3. **Medium effort / Medium value:** Create a `restore_backup` management command or script that automates the restore-from-dump workflow, including pre-flight checks (backup file exists, target DB is empty or confirmed for overwrite) and post-restore verification.

4. **Low effort / Low value:** Consider adding `seeds/` to `.dockerignore` for production images. The demo data files are harmless but unnecessary in production containers, and removing them slightly reduces image size.

5. **Low effort / Medium value:** The `docker-compose.yml` healthcheck uses `/auth/login/` (line 43) which requires tenant resolution. If the tenant domain is not yet registered (first boot), this healthcheck may fail during the startup window before `setup_public_tenant` completes. Consider changing the compose healthcheck to `/health/` which bypasses tenant resolution, or increase the `start_period` to accommodate first-boot setup time.

## Files Reviewed

| File | Lines | Notes |
|------|-------|-------|
| `Dockerfile` | 43 | Main Debian-based image |
| `Dockerfile.alpine` | 68 | Alpine variant for FullHost |
| `Dockerfile.ops` | 44 | Ops sidecar (Alpine, cron-based) |
| `docker-compose.yml` | 187 | Production compose with web, db, audit_db, caddy, autoheal, ops |
| `docker-compose.demo.yml` | 67 | Demo compose with baked credentials |
| `entrypoint.sh` | 77 | Startup sequence (migrations, seeds, checks, gunicorn) |
| `requirements.txt` | 46 | Pinned with range constraints |
| `railway.json` | 14 | Dockerfile builder, healthcheck, watchPatterns |
| `Caddyfile` | 18 | Reverse proxy with security headers |
| `.dockerignore` | 36 | Excludes .env, tests, docs, IDE files |
| `konote/settings/base.py` | 423 | Shared settings, require_env, security defaults |
| `konote/settings/production.py` | 183 | Platform auto-detection, HSTS, CSRF origins |
| `konote/settings/build.py` | 27 | Build-time settings (SQLite, dummy keys) |
| `konote/db_router.py` | 58 | AuditRouter + NoOpTenantRouter |
| `seeds/demo_client_fields.py` | 203 | Demo client custom field values |
| `seeds/metric_library.json` | 469 | Metric definitions (EN + FR) |
| `seeds/sample_setup_config.json` | 282 | Sample agency configuration |
| `seeds/demo_data_profile_example.json` | 114 | Demo data generation profile |
| `apps/admin_settings/management/commands/seed.py` | 667 | Master seed command |
| `apps/audit/management/commands/startup_check.py` | 263 | Production security gate |
| `apps/audit/management/commands/lockdown_audit_db.py` | 82 | Audit DB write protection |
| `apps/audit/management/commands/migrate_audit.py` | 31 | Audit DB migration bypass |
| `apps/tenants/management/commands/migrate_default.py` | 461 | Ghost healer + 5-phase migration |
| `apps/tenants/management/commands/setup_public_tenant.py` | 127 | Single-tenant bootstrap |
| `apps/tenants/management/commands/provision_tenant.py` | 144 | Multi-tenant provisioning |
| `apps/tenants/management/commands/rotate_tenant_key.py` | 76 | Per-tenant key rotation |
| `apps/auth_app/management/commands/rotate_encryption_key.py` | 229 | Field-level key rotation (atomic) |
| `apps/admin_settings/management/commands/check_translations.py` | 474 | Translation health check |
| `apps/notes/management/commands/merge_duplicate_themes.py` | 116 | Theme deduplication |
| `konote/middleware/health_check.py` | 25 | /health/ endpoint |
| `scripts/audit_db_init.sql` | 53 | Audit DB role setup |
| `scripts/backup-vps.sh` | 90 | Standalone VPS backup (no retry) |
| `scripts/backup-azure.ps1` | 259 | Azure backup with blob upload |
| `scripts/deploy-konote-vps.sh` | 604 | Automated VPS deployment |
| `scripts/ops-entrypoint.sh` | 118 | Ops sidecar startup (msmtp, crontab) |
| `scripts/ops-backup.sh` | 102 | Ops backup with retry + dead man's switch |
| `scripts/ops-backup-verify.sh` | 81 | Weekly backup restore verification |
| `scripts/ops-disk-check.sh` | 24 | Disk usage alerting |
| `scripts/ops-docker-prune.sh` | 20 | Weekly Docker cleanup |
| `scripts/ops-health-report.sh` | 103 | Daily health email/log |
| `scripts/disk-check.sh` | 38 | Standalone disk check (legacy) |
