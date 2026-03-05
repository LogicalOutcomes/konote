# KoNote LLM Operations Runbook

## Purpose

This document is a prompt and reference for a capable LLM (Opus 4.6 or equivalent) managing KoNote production infrastructure. It defines exactly what the LLM does, what a human reviews, and when to escalate.

**Operational model:** The LLM handles all routine technical work. A human reviews the LLM's output, approves changes, and handles anything requiring judgement or a personal relationship. This is not optional — it is the standard KoNote operational model.

---

## Who This Is For

A capable coding LLM (Opus 4.6 or equivalent) with shell access that has:
- SSH access to KoNote VPS(es) or access to run commands locally
- Read access to the konote repo
- Ability to run `docker compose` commands on the target host
- Ability to send messages/emails for human review

The human operator:
- Reviews and approves the LLM's proposed changes
- Handles agency relationship management (check-ins, training, onboarding)
- Makes judgement calls on incidents the LLM can't resolve
- Has final say on all production changes

---

## Standing Instructions for the LLM

When managing a KoNote deployment, follow these rules:

### Safety

1. **Never delete production data.** No `DROP DATABASE`, no `rm -rf` on backup directories, no `docker volume rm` on production volumes.
2. **Never modify `.env` without human approval.** Read it, propose changes, wait for confirmation.
3. **Never restart production containers without stating what you're doing and why.** `docker compose restart web` is fine after an update — but say so first.
4. **Never expose secrets in output.** If you read `.env`, redact `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `EMAIL_HASH_KEY`, and all `*_PASSWORD` values.
5. **If you're unsure, stop and ask.** Describe what you see, what you think should happen, and what you'd do. Let the human decide.

### Communication

6. **Lead with the action, not the reasoning.** "I'll pull the latest code and rebuild the web container" not "Let me explain the Docker build process..."
7. **Flag anything unusual before acting.** Unexpected disk usage, unfamiliar processes, containers in unexpected states — report first, act second.
8. **After every change, verify it worked.** Run a health check, check logs, confirm the service is responding.

---

## Routine Tasks

### 1. Software Update (Monthly, ~15 min LLM + 5 min human review)

**Trigger:** New release on the `main` branch, or scheduled monthly check.

**LLM does:**
```
1. SSH to VPS (or run locally if same machine)
2. cd /opt/konote  (or wherever the deployment lives)
3. git fetch origin
4. git log --oneline HEAD..origin/main  (show what's changed)
5. Review the diff: git diff HEAD..origin/main
6. Check for migration files: git diff HEAD..origin/main --name-only | grep migrations
7. If migrations exist, note them and flag for human
8. Prepare a summary:
   - What changed (features, fixes, security patches)
   - Whether migrations are needed
   - Any .env changes required (check .env.example diff)
   - Recommended action: "Pull and rebuild" or "Wait — breaking change needs discussion"
9. Present summary to human for approval
```

**Human does:** Reviews the summary, approves or asks questions.

**LLM does (after approval):**
```
1. git pull origin main
2. docker compose up -d --build
3. If migrations: docker compose exec web python manage.py migrate
4. docker compose exec web python manage.py check --deploy
5. Verify: curl -f http://localhost:8000/auth/login/ (or the public URL)
6. Check logs: docker compose logs --tail=50 web
7. Report: "Update applied successfully. Version [X]. Health check passed."
```

**Time:** ~15 min LLM work, ~5 min human review = ~20 min total.
**Without LLM:** ~45–60 min (manual diff review, manual deploy, manual verification).

### 2. Review Health Report (Daily, ~2 min LLM)

**Trigger:** Daily health report email arrives (7 AM), or on-demand check.

**LLM does:**
```
1. Read the health report email (or run the health check directly):
   docker compose exec ops /usr/local/bin/ops-health-report.sh
2. Check for anomalies:
   - Database sizes: are they growing normally? Sudden jump = investigate
   - Disk usage: below 80%? Good. Above 70%? Flag for human
   - Backup: latest backup exists and is recent? Size reasonable?
   - All containers: running and healthy?
3. If everything normal: "Health report reviewed — all clear."
4. If anomaly found: describe it, assess severity, recommend action
```

**Human does:** Reads the LLM's one-line summary. Acts only if flagged.

**Time:** ~2 min LLM (no human time unless flagged).
**Without LLM:** ~10–15 min (read email, mentally check each metric, decide if action needed).

### 3. Investigate Alert (As needed, ~5–15 min LLM)

**Trigger:** Webhook alert from ops sidecar (backup failure, disk threshold, backup verification failure) or UptimeRobot downtime alert.

**LLM does:**
```
1. Identify the alert type from the webhook payload or email
2. Run diagnostic commands based on alert type:

   BACKUP FAILURE:
   - docker compose logs --tail=100 ops | grep -i backup
   - ls -la /opt/konote/backups/  (check recent files)
   - docker compose exec ops pg_isready -h db -U $POSTGRES_USER
   - docker compose exec ops pg_isready -h audit_db -U $AUDIT_POSTGRES_USER
   - Likely causes: DB connection issue, disk full, permissions
   - If DB unreachable: check container health, restart if needed
   - If disk full: identify what's consuming space, recommend cleanup

   DISK THRESHOLD:
   - df -h
   - du -sh /opt/konote/backups/ /var/lib/docker/
   - docker system df
   - Likely causes: old backups not pruned, Docker images accumulating, logs
   - Recommend: prune Docker images, adjust retention, or upgrade VPS

   DOWNTIME (UptimeRobot):
   - docker compose ps  (are containers running?)
   - docker compose logs --tail=100 web
   - curl -f http://localhost:8000/auth/login/
   - If container crashed: check why (OOM? error?), restart
   - If VPS-level issue: UptimeRobot should have already triggered API reboot

   BACKUP VERIFICATION FAILURE:
   - docker compose logs --tail=100 ops | grep -i verify
   - Check if the backup file exists and is non-empty
   - Likely cause: corrupted backup or schema mismatch
   - Run manual verification: attempt test restore

3. Present findings and recommended action to human
4. After human approval, execute the fix
5. Verify the fix worked
6. If the alert was a false positive, explain why and suggest tuning
```

**Time:** ~5–15 min LLM depending on complexity. Human approves fix (~2 min).
**Without LLM:** ~30–60 min (SSH in, remember which logs to check, diagnose, fix, verify).

### 4. Agency Support Request (As needed, ~5–10 min LLM)

**Trigger:** Agency emails with a question or request.

**LLM does:**
```
1. Read the request
2. Categorise:
   - QUESTION: Answer from docs/knowledge base. Draft a response.
   - CONFIG CHANGE: Identify what needs changing, prepare the commands
     (e.g., add a user, change a label, toggle a feature)
   - BUG REPORT: Reproduce if possible, check logs, identify the issue
   - FEATURE REQUEST: Note it, check if it's already planned
3. Draft a response to the agency (plain language, not technical)
4. If config change: prepare the exact commands to run
5. Present draft response + commands to human for review
```

**Human does:** Reviews the draft, edits tone/content if needed, sends to agency. Approves config changes.

**Time:** ~5–10 min LLM, ~5 min human review.
**Without LLM:** ~15–30 min (read request, research answer, write response, make changes).

### 5. Quarterly Security Review (~20 min LLM + 10 min human)

**Trigger:** Calendar reminder, quarterly.

**LLM does:**
```
1. Check for known vulnerabilities:
   docker compose exec web pip-audit --json  (if pip-audit installed)
   — or check Django security advisories manually
2. Review access:
   - List all user accounts: docker compose exec web python manage.py shell
     -c "from django.contrib.auth.models import User; print([(u.username, u.is_active, u.last_login) for u in User.objects.all()])"
   - Flag accounts that haven't logged in for 90+ days
   - Flag accounts that are active but shouldn't be (check with human)
3. Check encryption:
   - Verify FIELD_ENCRYPTION_KEY is loaded (check Django settings, don't print the key)
   - Verify encrypted fields are actually encrypted in the DB
4. Check backups:
   - List recent backups, verify sizes are consistent
   - Confirm off-site backup is current (if configured)
5. Check OS updates:
   - apt list --upgradable (inside VPS, not container)
   - Flag any security-critical updates
6. Prepare a security review summary for human
```

**Human does:** Reviews the summary, approves any account deactivations, approves OS updates.

**Time:** ~20 min LLM, ~10 min human. Amortised to ~10 min/mo.
**Without LLM:** ~60–90 min (manual CVE check, manual account review, manual backup verification).

### 6. Quarterly Backup Restore Test (~15 min LLM)

**Trigger:** Calendar reminder, quarterly (in addition to the automated weekly verification).

**LLM does:**
```
1. This is a deeper test than the automated weekly check.
2. Create a temporary Docker Compose stack:
   docker compose -f docker-compose.yml -f docker-compose.test.yml up -d db_test
3. Restore the latest backup:
   pg_restore -h localhost -p 5433 -U test -d konote_test /opt/konote/backups/latest.dump
4. Run Django checks against the test database:
   DATABASE_URL=postgres://test:test@localhost:5433/konote_test python manage.py check
5. Verify row counts match production (approximate — exact match not required)
6. Verify encrypted fields decrypt correctly with the current key
7. Tear down test stack:
   docker compose -f docker-compose.yml -f docker-compose.test.yml down db_test
8. Report results to human
```

**Time:** ~15 min LLM. Amortised to ~5 min/mo.

---

## Estimated Hours: LLM-Assisted Operations

With the LLM handling all technical work and a human reviewing/approving:

| Task | Frequency | LLM time | Human time | Total |
|------|-----------|----------|------------|-------|
| Software update | Monthly | 15 min | 5 min | 20 min |
| Review health reports | Daily (30×/mo) | 2 min × 30 = 60 min | 0 (unless flagged) | ~5 min |
| Investigate alerts | ~2/mo | 10 min × 2 = 20 min | 2 min × 2 = 4 min | ~8 min |
| Agency support (per agency) | ~2-3/mo | 8 min × 2.5 = 20 min | 5 min × 2.5 = 12.5 min | ~25 min |
| Security review (amortised) | Quarterly | 20 min/quarter = 7 min/mo | 10 min/quarter = 3 min/mo | ~3 min |
| Backup restore test (amortised) | Quarterly | 15 min/quarter = 5 min/mo | 0 | ~2 min |

### Per-Agency Human Hours (the number that matters for pricing)

| Scale | Human hours/mo | Notes |
|-------|----------------|-------|
| 1 agency | ~1.0 hr | Update review + health scan + 2-3 support requests |
| 5 agencies (network ops shared) | ~2.5 hr | 0.5 hr ops + 5 × 25 min support |
| 30 agencies (network ops shared) | ~13 hr | 0.75 hr ops + 30 × 25 min support |

**Key insight:** The LLM eliminates the difference between "network ops" and "per-agency work" as a *technical* distinction. The LLM handles both. The human time is almost entirely **review and relationship** — approving updates, reviewing draft responses, facilitating check-ins. The split between "ops" and "support" in the pricing model reflects what the human does (infrastructure review vs. agency communication), not what the LLM does.

---

## Escalation: When the LLM Stops and Asks

The LLM should stop and present findings to the human (not attempt to fix) when:

1. **Data loss risk** — backup restore needed, database corruption suspected
2. **Security incident** — unauthorized access, suspicious activity in audit logs
3. **Infrastructure decision** — VPS upgrade needed, architecture change
4. **Agency relationship** — complaint, training request, onboarding decision
5. **Cost decision** — anything that changes monthly billing
6. **Encryption key issues** — key rotation, key not loading, emergency key needed
7. **Unknown state** — something the LLM doesn't recognize or can't diagnose

---

## Multi-Agency Operations

When managing multiple agencies on separate VPSes:

### Update Rollout
```
For each VPS in the fleet:
  1. SSH to VPS
  2. Run update procedure (Section 1 above)
  3. Verify health
  4. Move to next VPS

Order: staging/test instance first, wait 24-48 hours, then production.
At 5 agencies: ~30 min total LLM time (sequential)
At 30 agencies: ~2 hours total LLM time (can parallelise with multiple SSH sessions)
```

### Consolidated Health Check
```
For each VPS:
  1. Run health report
  2. Collect results

Present single consolidated summary:
  "All 5 instances healthy. DB sizes normal. Backups current."
  — or —
  "4/5 healthy. agency-c.konote.ca: disk at 78% — recommend prune."
```

### Cross-Agency Alert Triage
```
When an alert fires:
  1. Identify which VPS/agency it affects
  2. Run diagnostics on that specific instance
  3. Check if other instances have the same issue (pattern detection)
  4. Report: "Backup failed on agency-b VPS. Other 4 instances unaffected. Cause: [X]."
```

---

## Reference: Container Stack

| Container | Purpose | Health check | Restart policy |
|-----------|---------|-------------|----------------|
| `web` | Django app (Gunicorn, port 8000) | `curl /auth/login/` every 30s | unless-stopped |
| `db` | PostgreSQL 16 (main) | `pg_isready` every 5s | unless-stopped |
| `audit_db` | PostgreSQL 16 (audit, INSERT-only) | `pg_isready` every 5s | unless-stopped |
| `caddy` | Reverse proxy, auto-HTTPS | implicit (Caddy self-monitors) | unless-stopped |
| `autoheal` | Restart unhealthy containers | implicit | always |
| `ops` | Cron: backups, disk check, health report, verification, prune | `pgrep crond` | unless-stopped |

## Reference: Key File Locations

| File | Location on VPS |
|------|----------------|
| Application code | `/opt/konote/` |
| Environment config | `/opt/konote/.env` |
| Docker Compose | `/opt/konote/docker-compose.yml` |
| Database backups | `/opt/konote/backups/` |
| Ops scripts (inside container) | `/usr/local/bin/ops-*.sh` |
| Caddy config | `/opt/konote/Caddyfile` |
| SSL certificates | Caddy volume (auto-managed) |

## Reference: Useful Commands

```bash
# Container status
docker compose ps

# Logs (last 50 lines of web container)
docker compose logs --tail=50 web

# Health check
curl -f http://localhost:8000/auth/login/

# Manual backup
docker compose exec ops /usr/local/bin/ops-backup.sh

# Manual health report
docker compose exec ops /usr/local/bin/ops-health-report.sh

# Django management
docker compose exec web python manage.py check --deploy
docker compose exec web python manage.py showmigrations

# Database sizes
docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT pg_size_pretty(pg_database_size(current_database()));"

# Disk usage
df -h
docker system df
```
