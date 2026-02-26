# Design Rationale: OVHcloud Deployment Architecture

*Last updated: 2026-02-26*

## Context

KoNote handles PHIPA-protected health data for Ontario nonprofits. The current Railway hosting (US-incorporated, US data centres) does not meet data sovereignty requirements for production agency deployments. This document records the architectural decisions for hosting KoNote on OVHcloud Beauharnois, QC — including the full deployment stack, automated self-healing, backup strategy, and encryption key management.

**Related documents:**
- [Hosting cost comparison](../hosting-cost-comparison.md) — Azure vs OVHcloud pricing at 1, 5, and 10 agency scales
- [AI feature toggles DRR](ai-feature-toggles.md) — self-hosted LLM scope and rationale (PR #102)
- [Multi-tenancy DRR](multi-tenancy.md) — schema-per-tenant architecture for multi-agency hosting

## Decision: OVHcloud Beauharnois

### Why OVHcloud

| Factor | OVHcloud | Azure | Railway |
|--------|----------|-------|---------|
| Parent company | OVH Groupe SA (French) | Microsoft (US) | Railway (US) |
| US CLOUD Act | **Not subject** | Subject | Subject |
| Data centre | Beauharnois, QC | Toronto (Canada Central) | US only |
| Canadian LE jurisdiction | Yes (Sept 2025 Ontario ruling) | Yes | N/A |
| Cost (10 agencies, multi-tenant) | ~$116 CAD/mo total | ~$456 CAD/mo total | Not viable |

**Key rationale:** The US CLOUD Act applies to US-incorporated companies regardless of where their data centres are located. OVHcloud's parent (OVH Groupe SA) is French-incorporated and not subject to US government data requests for Canadian operations. Canadian law enforcement jurisdiction over Canadian data at OVHcloud is expected and acceptable for KoNote's threat model.

**Exception for populations with Canadian LE concerns:** Agencies serving undocumented newcomers or populations with specific concerns about Canadian law enforcement should evaluate whether the Sept 2025 Ontario court ruling (RCMP compelling OVH Canada to produce data) affects their risk profile.

### What Azure Key Vault Adds

Even in the OVHcloud scenario, Azure Key Vault is used for encryption key management (see [Encryption Key Management](#encryption-key-management) below). This introduces a limited Azure dependency:

- Only the `FIELD_ENCRYPTION_KEY` is stored in Azure — not participant data
- The key alone is useless without access to the encrypted database on OVHcloud
- If zero Azure dependency is required, alternatives exist (see below)

---

## Deployment Stack

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  OVHcloud VPS (Beauharnois, QC)                         │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  Caddy   │──│  Django   │──│ Postgres │  │ Postgres│  │
│  │ (ports   │  │ Gunicorn  │  │  (main)  │  │ (audit) │  │
│  │  80/443) │  │ (port     │  │          │  │         │  │
│  │          │  │  8000)    │  │          │  │         │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
│                                                         │
│  ┌──────────┐  ┌──────────────────────────────────────┐ │
│  │ Autoheal │  │ Cron: backups, log rotation, monitor │ │
│  └──────────┘  └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  OVHcloud VPS (Beauharnois, QC) — shared LLM endpoint   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Ollama (Qwen3.5-35B-A3B) — nightly batch only    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

External:
  ├── Azure Key Vault (encryption key storage)
  ├── OpenRouter API (translation + metrics/targets AI)
  ├── UptimeRobot (external uptime monitoring)
  └── Let's Encrypt (TLS via Caddy auto-HTTPS)
```

### Container Stack

The existing `docker-compose.yml` runs unmodified on OVHcloud. Four application containers plus two operational containers:

| Container | Image | Purpose | Existing? |
|-----------|-------|---------|-----------|
| `web` | KoNote Dockerfile | Django + Gunicorn (2 workers, port 8000) | Yes |
| `db` | postgres:16-alpine | Main application database | Yes |
| `audit_db` | postgres:16-alpine | Tamper-resistant audit log (INSERT-only after lockdown) | Yes |
| `caddy` | caddy:2-alpine | Reverse proxy, auto-HTTPS via Let's Encrypt | Yes |
| `autoheal` | willfarrell/autoheal | Restarts unhealthy containers automatically | **New** |
| `ollama` | ollama/ollama | Self-hosted LLM for suggestion theme tagging | **New** (separate VPS or same VPS) |

### Extended docker-compose.yml (OVHcloud additions)

The production `docker-compose.yml` needs two additions for OVHcloud deployment:

**1. Autoheal container** — monitors Docker HEALTHCHECK status and restarts failed containers:

```yaml
  autoheal:
    image: willfarrell/autoheal
    restart: always
    environment:
      - AUTOHEAL_CONTAINER_LABEL=all
      - AUTOHEAL_INTERVAL=30
      - AUTOHEAL_START_PERIOD=60
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

**2. HEALTHCHECK on the web container** — the web container currently relies on Railway's external health check (`/auth/login/`). For OVHcloud, add an internal Docker HEALTHCHECK:

```yaml
  web:
    # ... existing config ...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/auth/login/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

The `db` and `audit_db` containers already have `pg_isready` health checks.

### VPS Sizing

| Workload | Recommended VPS | Specs | Cost (CAD/mo) |
|----------|----------------|-------|---------------|
| 1 agency (app + DB) | VPS-2 | 4 vCores, 16 GB RAM, 100 GB NVMe | ~$22 |
| 5 agencies (multi-tenant) | VPS-3 | 8 vCores, 24 GB RAM, 200 GB NVMe | ~$30 |
| 10 agencies (multi-tenant) | VPS-3 or VPS-4 | 8 vCores, 24–32 GB RAM, 200 GB NVMe | ~$30–44 |
| LLM (shared, all agencies) | VPS-1 | 4 vCores, 8 GB RAM, 75 GB NVMe | ~$11 |

---

## Self-Healing Architecture

OVHcloud provides unmanaged VPS — no automatic container restarts, no managed health checks, no PaaS recovery. The self-healing stack compensates with four layers of automation.

### Layer 1: Docker Container Recovery (~$0)

**What it does:** Restarts individual containers that fail their health check.

**How it works:**
- Docker's built-in `restart: unless-stopped` policy handles process crashes
- `willfarrell/autoheal` sidecar container monitors HEALTHCHECK status every 30 seconds
- If a container reports unhealthy 3 times consecutively, autoheal restarts it
- This handles: Django OOM, PostgreSQL crash, Caddy config error, transient failures

**Covers:** ~80% of incidents (application-level failures)

### Layer 2: VPS-Level Recovery (~$0)

**What it does:** Reboots the entire VPS when containers can't self-recover.

**How it works:**
- [UptimeRobot](https://uptimerobot.com/) (free tier: 50 monitors, 5-minute interval) monitors the public HTTPS endpoint
- On 3 consecutive failures (15 minutes of downtime), UptimeRobot fires a webhook
- Webhook calls the [OVHcloud API](https://api.ovh.com/console/#/vps) `POST /vps/{serviceName}/reboot`
- VPS reboots → Docker starts → `restart: unless-stopped` brings up all containers → `entrypoint.sh` runs migrations and startup checks

**Implementation:** A small webhook relay (e.g., [Pipedream](https://pipedream.com/) free tier or a Cloudflare Worker) translates the UptimeRobot webhook into an authenticated OVHcloud API call.

**Covers:** ~15% of incidents (kernel panics, Docker daemon failures, disk full, network issues)

### Layer 3: Preventive Automation (~$0)

**What it does:** Prevents failures before they happen.

**Cron jobs on the VPS (added to the host, not inside containers):**

```cron
# Nightly PostgreSQL backup (both databases)
0 2 * * * /opt/konote/scripts/backup.sh >> /var/log/konote-backup.log 2>&1

# Nightly log rotation (prevent disk fill)
0 3 * * * /usr/sbin/logrotate /etc/logrotate.d/konote

# Disk usage check (alert if >80%)
0 * * * * /opt/konote/scripts/disk-check.sh

# Docker system prune (remove dangling images/containers weekly)
0 4 * * 0 docker system prune -f >> /var/log/docker-prune.log 2>&1

# Nightly LLM batch (suggestion theme tagging)
0 1 * * * /opt/konote/scripts/run-suggestion-batch.sh >> /var/log/konote-llm.log 2>&1
```

**backup.sh outline:**
```bash
#!/bin/bash
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
BACKUP_DIR=/opt/konote/backups

# Dump main database
docker compose exec -T db pg_dump -U $POSTGRES_USER $POSTGRES_DB \
  > $BACKUP_DIR/main_$TIMESTAMP.sql

# Dump audit database
docker compose exec -T audit_db pg_dump -U $AUDIT_POSTGRES_USER $AUDIT_POSTGRES_DB \
  > $BACKUP_DIR/audit_$TIMESTAMP.sql

# Compress
gzip $BACKUP_DIR/main_$TIMESTAMP.sql $BACKUP_DIR/audit_$TIMESTAMP.sql

# Retain 30 days of daily backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# Upload to off-site storage (e.g., OVHcloud Object Storage or separate VPS)
# rclone copy $BACKUP_DIR remote:konote-backups/ --max-age 1d
```

**disk-check.sh outline:**
```bash
#!/bin/bash
USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$USAGE" -gt 80 ]; then
  curl -s -X POST "https://hooks.example.com/alert" \
    -d "KoNote VPS disk usage at ${USAGE}%"
fi
```

**Covers:** ~4% of incidents (preventable failures: disk full, stale images, missed backups)

### Layer 4: Human Escalation (~$0)

**What it does:** Alerts the KoNote team when automated recovery fails.

**Channels:**
- **UptimeRobot email alerts** — sent when downtime is detected and again on recovery
- **Backup failure alerts** — backup.sh sends email/Slack on non-zero exit
- **Disk space alerts** — disk-check.sh sends alert above threshold
- **LLM batch failure alerts** — run-suggestion-batch.sh sends alert on failure

**Escalation path:**
1. Automated recovery handles the issue (Layers 1–3) → no human action needed
2. If still down after 15 minutes → UptimeRobot reboots VPS (Layer 2)
3. If still down after 30 minutes → email alert to KoNote team (Layer 4)
4. Human investigates via SSH

**What humans handle:** Hardware failure (OVHcloud support ticket), data corruption (restore from backup), security incident (incident response plan), capacity upgrade (resize VPS).

### Recovery Time Estimates

| Failure Type | Example | Recovery Method | Estimated Downtime |
|-------------|---------|-----------------|-------------------|
| Container crash | Django OOM | Autoheal restart | 30–90 seconds |
| Stuck container | Gunicorn deadlock | Autoheal restart | 30–90 seconds |
| Docker daemon failure | Daemon crash | UptimeRobot → VPS reboot | 15–20 minutes |
| VPS kernel panic | Kernel bug | UptimeRobot → VPS reboot | 15–20 minutes |
| Disk full | Logs not rotated | Preventive cron (shouldn't happen) | 0 (prevented) |
| Hardware failure | Disk failure | Human + OVHcloud support | 1–4 hours |
| Data corruption | DB corruption | Human + backup restore | 1–4 hours |

---

## Backup Strategy

### What Gets Backed Up

| Data | Method | Frequency | Retention |
|------|--------|-----------|-----------|
| Main PostgreSQL (app data) | `pg_dump` via cron | Nightly (2 AM ET) | 30 days |
| Audit PostgreSQL (audit log) | `pg_dump` via cron | Nightly (2 AM ET) | 90 days (compliance) |
| Docker volumes (pgdata) | Implicit in pg_dump | — | — |
| `.env` file | Manual backup | On change | Stored in password manager |
| `FIELD_ENCRYPTION_KEY` | Azure Key Vault | Always available | Key Vault versioning |

### Off-Site Backup Storage

On-VPS backups protect against application failures but not hardware failures. Off-site copies are essential.

**Options (in order of preference for data sovereignty):**
1. **Second OVHcloud VPS** — separate VPS in same or different OVHcloud region. `rsync` or `rclone` nightly. ~$11 CAD/mo.
2. **OVHcloud Object Storage** — S3-compatible, Beauharnois region. `rclone` nightly. Pay-per-GB (~$0.01/GB/mo).
3. **Encrypted local copy** — download to KoNote team workstation via automated script. $0.

**Anti-pattern: Do not use Azure Blob Storage or AWS S3 for backups.** This would reintroduce US CLOUD Act exposure on the full database dump, defeating the purpose of OVHcloud hosting.

### Backup Verification

- **Monthly test restore:** Restore the latest backup to a separate Docker Compose instance (`docker-compose.test.yml`) and verify data integrity
- **Backup monitoring:** If `backup.sh` exits non-zero, send alert via email or webhook
- **Size check:** Compare backup file size to previous day — alert on >50% change (could indicate corruption or data loss)

---

## Encryption Key Management

### Architecture

```
┌──────────────────────┐         ┌──────────────────────┐
│  OVHcloud VPS        │         │  Azure Key Vault      │
│                      │         │  (Canada Central)     │
│  Django app reads    │◄────────│  FIELD_ENCRYPTION_KEY  │
│  key at startup      │  HTTPS  │  stored as Secret     │
│  via Azure SDK       │         │                      │
│                      │         │  Access: Azure AD     │
│  Key cached in       │         │  service principal    │
│  process memory      │         │  (read-only)          │
└──────────────────────┘         └──────────────────────┘
```

### How It Works

1. **At container startup**, Django reads `FIELD_ENCRYPTION_KEY` from Azure Key Vault using the Azure Identity SDK
2. The key is cached in process memory for the lifetime of the Gunicorn workers
3. All Fernet encrypt/decrypt operations use the in-memory key — no per-operation Key Vault calls
4. Key Vault operations: ~2 per day (startup + any worker recycle) = negligible cost (~$1–5 CAD/mo)

### Access Control

- **Azure AD service principal** with `Key Vault Secrets User` role (read-only)
- Service principal credentials (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`) stored in `.env` on the VPS
- Key Vault access policy: deny all except the service principal
- Key Vault audit logging enabled (who accessed what, when)

### Key Custody

- **Primary:** Azure Key Vault (always available, versioned, audited)
- **Emergency backup:** Printed key stored in sealed envelope, held by two designated officers (executive director + board member). Neither person alone can access the key.
- **Key rotation:** Supported by Fernet (decrypt with old key, re-encrypt with new key). Schedule: annually or on personnel change.

### Alternative to Azure Key Vault

If zero Azure dependency is required:

| Alternative | Pros | Cons |
|-------------|------|------|
| HashiCorp Vault (self-hosted on OVHcloud) | No Azure dependency, full sovereignty | Operational overhead, another service to maintain |
| Manual key custody (`.env` file + sealed envelope) | Simple, no external dependency | No audit trail, no programmatic rotation |
| OVHcloud KMS (if available in BHS) | Same provider, no cross-provider dependency | Limited availability, less mature than Azure KV |

**Current recommendation:** Azure Key Vault. The CLOUD Act exposure is limited to the encryption key only, and the operational benefits (audit logging, versioning, access policies) outweigh the theoretical risk.

---

## LLM Integration (Suggestion Theme Tagging)

### Deployment Options

| Option | When to Use | Cost (CAD/mo) |
|--------|-------------|---------------|
| Ollama on separate VPS-1 | Default — isolates LLM from app | ~$11 (shared) |
| Ollama on same VPS | 1–3 agencies, cost-sensitive | $0 additional |

### Batch Processing

- **Schedule:** Nightly cron (1 AM ET), before backups (2 AM ET)
- **Scope:** Unprocessed `participant_suggestion` entries from all agencies
- **Volume:** ~1,000 suggestions/month across 10 agencies = ~1–2 hours CPU inference
- **Output:** Theme tags stored in app database (aggregate only, never individual-level)
- **Failure handling:** Log error, send alert, retry next night. Suggestions accumulate safely — no data loss.

### Multi-Agency Isolation

- Shared Ollama endpoint serves all agencies
- Each agency's suggestions are processed in separate batches — no cross-agency data mixing
- Suggestions are sent to the LLM one at a time — the model never sees data from multiple agencies in the same context window
- Agency ID is not sent to the LLM — only the suggestion text and theme list

---

## Multi-Agency Hosting

### Single-Tenant (Current Architecture)

Each agency gets its own VPS with its own Docker Compose stack. Simple but expensive at scale.

```
Agency A: VPS-2 ($22) → Docker Compose (web + db + audit_db + caddy)
Agency B: VPS-2 ($22) → Docker Compose (web + db + audit_db + caddy)
Agency C: VPS-2 ($22) → Docker Compose (web + db + audit_db + caddy)
Shared:   VPS-1 ($11) → Ollama (suggestion theme tagging)
```

### Multi-Tenant (Future — requires MT-CORE1)

All agencies share one VPS with schema-per-tenant isolation via django-tenants. One Docker Compose stack serves all agencies.

```
Shared:   VPS-3 ($30) → Docker Compose (web + db + audit_db + caddy)
                         └── Schema per tenant (agency_a, agency_b, agency_c)
Shared:   VPS-1 ($11) → Ollama (suggestion theme tagging)
```

**Prerequisites:**
- MT-CORE1: Integrate django-tenants for schema-per-tenant
- MT-ENCRYPT1: Per-tenant encryption keys (each agency's FIELD_ENCRYPTION_KEY in Key Vault)
- Caddy wildcard or multi-domain config for tenant routing

---

## Initial Deployment Checklist

For the first OVHcloud deployment (single agency):

1. **Provision VPS-2** on OVHcloud Canada (Beauharnois)
2. **Install Docker + Docker Compose** on the VPS
3. **Generate credentials:** `SECRET_KEY`, database passwords (via `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
4. **Create Azure Key Vault** in Canada Central, store `FIELD_ENCRYPTION_KEY`
5. **Create Azure AD service principal** with read-only Key Vault access
6. **Configure `.env`** with all environment variables (see `.env.example`)
7. **Set `DOMAIN`** in `.env` for Caddy auto-HTTPS
8. **Configure DNS** — point agency domain to VPS IP
9. **Deploy:** `docker compose up -d`
10. **Verify:** Health check passes, login works, demo data loads (if DEMO_MODE)
11. **Add autoheal container** to docker-compose.yml
12. **Set up cron jobs:** backup, log rotation, disk check
13. **Configure UptimeRobot** — monitor HTTPS endpoint, webhook to OVHcloud API
14. **Test backup/restore** — dump, restore to test instance, verify data
15. **Document:** VPS IP, domain, Key Vault name, service principal, backup location

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OVHcloud Beauharnois outage | Low | High (downtime) | UptimeRobot alerts, backup restore to new VPS |
| VPS hardware failure | Low | High (data loss if no off-site backup) | Nightly off-site backups, test monthly restore |
| OVHcloud discontinues BHS region | Very low | Medium | Architecture is provider-agnostic — migrate Docker Compose to any VPS |
| Azure Key Vault outage | Very low | Medium (can't restart) | Emergency key in sealed envelope, restart with env var fallback |
| Disk full | Medium | High (DB crash) | Preventive cron, disk alerts, log rotation |
| Unpatched vulnerability | Medium | High | Automated `apt upgrade` via `unattended-upgrades`, Docker image updates |
| LLM batch failure | Low | Low (suggestions queue) | Retry next night, alert on failure, no data loss |
| OVHcloud price increase | Medium | Low | VPS-1 increasing to US$7.60 (Apr 2026). Budget with 20% headroom. |

---

## Anti-Patterns

**Do not:**
- Store database backups on Azure Blob Storage or AWS S3 (reintroduces CLOUD Act exposure)
- Run PostgreSQL without Docker volumes (data loss on container recreation)
- Skip the autoheal container (silent failures with no recovery)
- Store `FIELD_ENCRYPTION_KEY` only in `.env` (single point of failure — use Key Vault)
- Run Ollama on the same VPS as a high-traffic multi-tenant deployment (resource contention)
- Send agency identifiers to the LLM endpoint (unnecessary data exposure)
- Use OVHcloud's built-in VPS backup feature as the only backup (no granular restore, no off-site copy)
