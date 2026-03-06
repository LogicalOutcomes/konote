# Self-Hosted LLM Infrastructure — Design Rationale Record

Task ID: AI-SELFHOST1
Date: 2026-03-03
Status: Approved — design complete, deployment is ops work
Related: [AI feature toggles DRR](ai-feature-toggles.md), [OVHcloud deployment DRR](ovhcloud-deployment.md), [Data access residency policy](data-access-residency-policy.md)

---

## Problem

KoNote's current AI integration routes participant data (scrubbed quotes, suggestion themes) through OpenRouter to Anthropic's Claude API. Even with PII scrubbing, this sends de-identified participant content to US-incorporated cloud services — a data sovereignty concern for agencies subject to PHIPA, OCAP, or funder data handling requirements.

Beyond KoNote, LogicalOutcomes needs a general-purpose LLM inference endpoint for:

1. **KoNote suggestion theme tagging** — nightly batch processing of participant suggestions across all agencies
2. **KoNote outcome insights** — on-demand qualitative analysis of scrubbed participant quotes
3. **OpenWebUI connections** — external OpenWebUI instances at multiple organisations connect to this central model server
4. **Survey qualitative analysis** — two-stage pipeline: PII stripping and data cleanup (self-hosted), then deep thematic analysis (frontier LLM API)
5. **General analytical work** — document analysis, report drafting, data interpretation

This is a **lean shared inference endpoint** — one VPS running Ollama + Caddy, serving multiple KoNote deployments, external OpenWebUI instances, and analytical workloads. OpenWebUI is deployed separately by each organisation, not on this server.

## Decision: Shared Ollama VPS on OVHcloud Beauharnois

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  OVHcloud VPS-4 (Beauharnois, QC) — Lean LLM Endpoint       │
│  12 vCPUs, 48 GB RAM, 300 GB NVMe                            │
│                                                              │
│  ┌──────────┐  ┌───────────┐                                 │
│  │  Caddy   │  │  Ollama   │                                 │
│  │ (reverse │──│ (LLM      │                                 │
│  │  proxy,  │  │  engine)  │                                 │
│  │  TLS,    │  │  :11434   │                                 │
│  │  auth)   │  │           │                                 │
│  │  :80/443 │  │           │                                 │
│  └──────────┘  └───────────┘                                 │
│                                                              │
│  Primary model: qwen3.5:35b-a3b (MoE, 3B active / 35B total)│
│  Backup model:  qwen3.5:27b (dense, 27B — higher quality)   │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Cron: nightly theme batch, log rotation, disk check     │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

External clients (all connect via HTTPS to llm.example.com):
  ├── KoNote Instance A  →  INSIGHTS_API_BASE=https://llm.example.com/v1
  ├── KoNote Instance B  →  INSIGHTS_API_BASE=https://llm.example.com/v1
  ├── OpenWebUI (org 1)  →  OLLAMA_BASE_URL=https://llm.example.com
  ├── OpenWebUI (org 2)  →  OLLAMA_BASE_URL=https://llm.example.com
  ├── Survey PII stage   →  API calls to https://llm.example.com/v1
  └── Survey analysis    →  API calls to Claude API (de-identified data)
```

### Why a Shared Server (Not Per-Agency)

| Factor | Per-agency LLM | Shared LLM server |
|--------|---------------|-------------------|
| Cost (10 agencies, CAD/mo) | ~$400 (10 × VPS-4) | **~$40** (1 × VPS-4) |
| Model updates | Update 10 servers | **Update 1 server** |
| Utilisation | ~1% each (nightly batch) | **~10–20%** (aggregated) |
| Data isolation | Complete | **Per-request isolation** (see below) |
| Blast radius | 1 agency affected | All agencies affected |

The shared model wins on cost and operations. The blast radius risk is mitigated by the fact that the LLM server is a non-critical convenience — if it goes down, KoNote instances continue to function; AI features degrade gracefully to manual operation.

### Data Isolation on the Shared Server

- Each KoNote instance sends suggestions one at a time — the model never sees data from multiple agencies in the same context window
- Agency identifiers are **never sent** to the LLM — only scrubbed text and theme lists
- Ollama does not persist conversation history between requests
- No cross-agency data mixing is possible at the model level
- External OpenWebUI instances are deployed separately by each organisation — they connect to this endpoint but their data stays on their own infrastructure

---

## Model Selection: Qwen3.5-35B-A3B

### Why This Model

The Qwen3.5-35B-A3B is a **Mixture of Experts (MoE)** model released February 24, 2026 by Alibaba's Qwen team. It has 35 billion total parameters but activates only **3 billion per forward pass**, making it exceptionally fast on CPU while retaining the knowledge of a much larger model.

| Factor | Qwen3.5-35B-A3B | Qwen3.5-27B (dense) | Llama 3.3 70B | Mistral Small 3.2 24B |
|--------|-----------------|---------------------|---------------|----------------------|
| Architecture | **MoE (3B active)** | Dense (27B active) | Dense (70B active) | Dense (24B active) |
| MMLU-Pro | 85.3 | 86.1 | ~82 | ~78 |
| GPQA Diamond | 84.2 | 85.5 | ~75 | ~72 |
| RAM needed (Q4) | **~20 GB** | ~16 GB | ~42 GB | ~14 GB |
| CPU inference speed | **Fast** (3B active) | Slow (27B active) | Very slow (70B) | Moderate (24B) |
| Context window | 262K tokens | 262K tokens | 128K tokens | 128K tokens |
| Licence | Apache 2.0 | Apache 2.0 | Llama licence | Apache 2.0 |

**Key benchmarks for our use cases:**

- **MMLU-Pro 85.3** — strong general knowledge, important for survey analysis and qualitative coding
- **GPQA Diamond 84.2** — graduate-level reasoning, relevant for nuanced thematic analysis
- **SWE-bench 69.2** — not our primary use but shows strong instruction-following
- **262K context window** — can process long survey responses and multiple quotes in a single call
- **Surpasses Qwen3-235B-A22B** — a model with 7× more active parameters. Architecture + training quality > parameter count.

### Model Provenance Note

Qwen3.5-35B-A3B is developed by Alibaba's Qwen team (China) and released under the Apache 2.0 licence. **No data of any kind flows to Alibaba during inference** — the model weights are downloaded once and run entirely on the Canadian VPS. The Apache 2.0 licence imposes no data obligations, usage restrictions, or reporting requirements. This is equivalent to using any other open-source software (like PostgreSQL or Linux).

However, some Canadian funders and nonprofit boards may have concerns about using a model from a Chinese tech company, regardless of the technical facts. If model provenance is a concern for a specific agency or funder, **Llama 3.3** (Meta, US) and **Mistral Small 3.2** (Mistral AI, France) are drop-in alternatives available via Ollama. The model swap is a single command with no code changes.

### Why MoE for CPU Inference

OVHcloud VPS instances have no GPU. All inference runs on CPU. The MoE architecture is the critical differentiator:

- **Dense 27B model:** every token activates all 27B parameters → CPU must process 27B weights per token → slow
- **MoE 35B model:** every token activates only 3B parameters → CPU processes 3B weights per token → **~9× less compute per token** despite higher total knowledge

This means the 35B-A3B runs approximately as fast as a 3B dense model while delivering 35B-class quality. On CPU, this translates to **usable interactive response times** (~2–5 tokens/second on 12 vCPUs) rather than the ~0.5 tokens/second you'd get from a dense 27B.

### Backup Model: Qwen3.5-27B

Ollama can host multiple models. The dense 27B model serves as a backup for tasks where quality matters more than speed:

- Survey analysis reports with long turnaround (overnight batch)
- Complex thematic coding requiring deeper reasoning
- Comparison runs (check whether the MoE model produces comparable results)

Both models fit in 48 GB RAM. Ollama loads the requested model on demand and unloads inactive models from memory.

### Upgrade Path: Qwen3.5-122B-A10B

If quality demands increase, the 122B-A10B model (10B active parameters, 122B total) offers significantly better agentic and reasoning performance:

- MMLU-Pro: 86.7 (vs 85.3)
- GPQA Diamond: 86.8 (vs 84.2)
- Best-in-class tool use (BFCL-V4: 72.2)

This model requires ~65 GB RAM at Q4 quantization → upgrade to VPS-6 (96 GB, ~$79 CAD/mo).

---

## VPS Sizing

### Recommended: VPS-4

| Component | RAM Usage |
|-----------|-----------|
| Qwen3.5-35B-A3B (Q4_K_M) | ~20 GB |
| KV cache (262K context, active request) | ~2–4 GB |
| Caddy + OS overhead | ~2 GB |
| **Headroom for burst** | **~22 GB free** |
| **Total available** | **48 GB** |

The 22 GB headroom accommodates:
- Multiple concurrent inference requests (each adds ~1–2 GB KV cache)
- Occasional loading of the backup 27B model (~16 GB; the 35B model is unloaded)
- Burst traffic from multiple external OpenWebUI instances

### VPS Specs and Cost

All prices in CAD (converted from USD at 1 USD ≈ 1.35 CAD; verify current rate at time of purchase).

| Tier | vCPUs | RAM | Storage | Cost (CAD/mo) | Use Case |
|------|-------|-----|---------|---------------|----------|
| VPS-3 | 8 | 24 GB | 200 GB | ~$23 | Minimum viable (35B-A3B only, low concurrency) |
| **VPS-4** | **12** | **48 GB** | **300 GB** | **~$40** | **Recommended (35B-A3B + headroom for concurrent requests)** |
| VPS-5 | 16 | 64 GB | 350 GB | ~$59 | Upgrade (122B-A10B or heavy concurrent use) |
| VPS-6 | 24 | 96 GB | 400 GB | ~$79 | Maximum (122B-A10B + heavy concurrent use) |

**Start with VPS-4.** Upgrade to VPS-5/6 only if quality requirements or concurrency demand it.

### Cost in Context

| Scenario | Monthly cost (CAD) |
|----------|-------------------|
| OpenRouter API (current, 10 agencies) | ~$27–68 (usage-based, unpredictable) |
| Self-hosted VPS-4 (10 agencies + external OpenWebUI) | **~$40** (fixed, unlimited inference) |
| Self-hosted VPS-4 + off-site backup VPS | ~$51 |

The self-hosted option becomes **cheaper than cloud API** at ~5 agencies and provides **unlimited inference** with no per-token cost.

---

## Container Stack

### docker-compose.yml for the LLM VPS

This is a lean deployment — just the inference engine and reverse proxy. No OpenWebUI on this server.

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    restart: unless-stopped
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_NUM_PARALLEL=2          # concurrent requests
      - OLLAMA_MAX_LOADED_MODELS=1     # save RAM — load one model at a time
      - OLLAMA_KEEP_ALIVE=10m          # unload model after 10 min idle
    healthcheck:
      test: ["CMD-SHELL", "ollama list || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s              # model loading takes time

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config

  autoheal:
    image: willfarrell/autoheal
    restart: always
    environment:
      - AUTOHEAL_CONTAINER_LABEL=all
      - AUTOHEAL_INTERVAL=30
      - AUTOHEAL_START_PERIOD=120
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

volumes:
  ollama_data:
  caddy_data:
  caddy_config:
```

### Caddyfile

```caddyfile
# Ollama API — for KoNote instances, OpenWebUI connections, and scripts
llm.example.com {
    # Require API key for all requests
    @api {
        header Authorization "Bearer {env.LLM_API_KEY}"
    }
    handle @api {
        reverse_proxy ollama:11434
    }
    # Reject requests without valid API key
    respond "Unauthorized" 401
}
```

### Initial Model Pull

After first deployment:

```bash
# Pull the primary model
docker compose exec ollama ollama pull qwen3.5:35b-a3b

# Optionally pull the backup model (will download but not load into RAM)
docker compose exec ollama ollama pull qwen3.5:27b
```

---

## KoNote Integration

### Existing Code — Already Compatible

The current `_call_insights_api()` function in [ai.py](../../konote/ai.py) already supports a custom endpoint:

```python
insights_base = getattr(settings, "INSIGHTS_API_BASE", "")
if insights_base:
    api_key = getattr(settings, "INSIGHTS_API_KEY", "")
    model = getattr(settings, "INSIGHTS_MODEL", "llama3")
    url = f"{insights_base.rstrip('/')}/chat/completions"
```

### KoNote `.env` Configuration

Each KoNote instance points to the shared LLM server:

```env
# Self-hosted LLM (replaces OpenRouter for participant data features)
INSIGHTS_API_BASE=https://llm.example.com/v1
INSIGHTS_API_KEY=<shared-api-key>
INSIGHTS_MODEL=qwen3.5:35b-a3b

# OpenRouter still used for tools-only features (metrics, goals, narratives)
OPENROUTER_API_KEY=<key>
```

### Dual-Provider Architecture

After this change, KoNote uses **two AI providers**:

| Feature Category | Provider | Data Sent | Why |
|-----------------|----------|-----------|-----|
| **Tools-only** (metrics, goals, narratives, CIDS) | OpenRouter (Claude Sonnet) | Program metadata only (no PII) | Higher quality for structured generation; no privacy concern |
| **Participant data** (insights, themes, suggestions) | **Self-hosted Ollama** | Scrubbed quotes (de-identified) | Data stays in Canada; no external transmission |

This is the architecture the [AI feature toggles DRR](ai-feature-toggles.md) anticipated: `ai_assist_participant_data` routes to the self-hosted endpoint while `ai_assist_tools_only` continues using OpenRouter.

### Code Change Required

Currently, both tools-only and participant-data features share `_call_openrouter()` as the default. Only `_call_insights_api()` (used by outcome insights) checks `INSIGHTS_API_BASE`.

**To implement the dual-provider split:**
1. The tools-only AI functions (`suggest_metrics`, `improve_outcome`, `generate_narrative`, etc.) continue calling `_call_openrouter()` — no change needed
2. The participant-data function (`generate_outcome_insights`) already calls `_call_insights_api()` which already checks `INSIGHTS_API_BASE` — no change needed
3. The nightly batch script (new) calls `_call_insights_api()` — uses `INSIGHTS_API_BASE` automatically

**No code changes to ai.py are required.** The dual-provider split is already built into the architecture. Setting the `INSIGHTS_API_BASE` environment variable is the only configuration needed.

---

## Nightly Batch Processing

### Suggestion Theme Tagging

A new management command processes untagged participant suggestions in nightly batches:

```
Schedule:  1:00 AM ET (before backups at 2:00 AM)
Scope:     All KoNote instances on this server (multi-tenant) or called per-instance
Volume:    ~1,000 suggestions/month across 10 agencies = ~1–2 hours CPU inference
Output:    Theme tags stored in app database
Failure:   Log error, alert, retry next night — suggestions accumulate safely
```

### Batch Script

```bash
#!/bin/bash
# /opt/llm-server/scripts/run-theme-batch.sh
# Called by cron at 1 AM ET

LOG=/var/log/llm-batch.log
echo "$(date) — Starting theme batch" >> "$LOG"

# Verify Ollama is healthy
if ! curl -sf http://localhost:11434/api/tags > /dev/null; then
    echo "$(date) — ERROR: Ollama not responding" >> "$LOG"
    # Send alert (email/webhook)
    exit 1
fi

# Ensure model is loaded
docker compose exec -T ollama ollama pull qwen3.5:35b-a3b >> "$LOG" 2>&1

# Call each KoNote instance's batch endpoint
# (Each instance runs its own management command via SSH or API)
# OR: if multi-tenant, run locally:
# docker compose -f /opt/konote/docker-compose.yml exec -T web \
#   python manage.py process_suggestion_themes --batch-size=50

echo "$(date) — Theme batch complete" >> "$LOG"
```

### Survey Qualitative Analysis — Two-Stage Pipeline

Survey qualitative analysis uses a two-stage pipeline that leverages each model's strengths:

```
┌───────────────────────────────────────────────────────┐
│  Stage 1: PII Stripping & Data Cleanup (Self-hosted)  │
│  Model: Qwen3.5-35B-A3B on LLM VPS                   │
│  Data: Raw survey responses (may contain PII)         │
│  Output: De-identified, structured, quality-checked   │
│  Location: All processing in Canada                   │
└───────────────────┬───────────────────────────────────┘
                    │  De-identified structured data only
                    ▼
┌───────────────────────────────────────────────────────┐
│  Stage 2: Deep Qualitative Analysis (Frontier LLM)    │
│  Model: Claude API (or equivalent frontier model)     │
│  Data: Clean, de-identified, structured responses     │
│  Output: Thematic analysis, coding, insights          │
│  Location: API call — no PII leaves Canada            │
└───────────────────────────────────────────────────────┘
```

**Stage 1 — Self-hosted (PII stripping and data cleanup):**

1. Read raw CSV/spreadsheet of open-ended survey responses
2. Strip PII: names, locations, contact details, identifying context
3. Clean and standardise text (fix encoding, remove duplicates, normalise whitespace)
4. Quality assessment: flag responses that are too short, off-topic, or gibberish
5. Structure output as clean JSON with response ID, cleaned text, quality flag

This is the stage where data sovereignty matters — raw survey responses may contain participant-identifying content. The self-hosted model processes this in Canada and the raw data never leaves the VPS.

**Stage 2 — Frontier LLM API (deep analysis):**

1. Receive de-identified structured data from Stage 1
2. Thematic coding: identify themes, patterns, and categories across responses
3. Generate narrative summaries of findings
4. Produce coded output suitable for evaluation reports

This stage benefits from the frontier model's superior reasoning, nuanced understanding, and structured output quality. Since Stage 1 has already stripped all PII, the de-identified data can safely be sent to an external API.

**Why two stages?** A single self-hosted model could do both, but the quality of deep qualitative analysis from an open-source model running on CPU does not match frontier models. By splitting the pipeline, the self-hosted model handles the privacy-sensitive work (what it must do), and the frontier model handles the analytical work (what it does best). The result is both data-sovereign and high-quality.

---

## External OpenWebUI Connections

### Architecture: OpenWebUI Deployed Separately

OpenWebUI instances are **not hosted on the LLM VPS**. Each organisation deploys its own OpenWebUI instance (on their own server, workstation, or cloud) and configures it to connect to the central Ollama endpoint:

```
Organisation A's server                  LLM VPS (Beauharnois)
┌──────────────────────┐                ┌──────────────────────┐
│  OpenWebUI           │ ──HTTPS──────→ │  Caddy → Ollama      │
│  (own data, own auth)│                │  llm.example.com     │
└──────────────────────┘                └──────────────────────┘

Organisation B's workstation
┌──────────────────────┐                        │
│  OpenWebUI           │ ──HTTPS────────────────┘
│  (own data, own auth)│
└──────────────────────┘
```

**OpenWebUI connection configuration:**

```env
OLLAMA_BASE_URL=https://llm.example.com
# API key passed via OpenWebUI's "Connection" settings in the admin panel
```

### Benefits of Separate Deployment

| Factor | OpenWebUI on LLM VPS | OpenWebUI deployed separately |
|--------|---------------------|------------------------------|
| VPS resource usage | Consumes RAM and CPU | **Zero — VPS is lean** |
| Data ownership | Conversations stored on shared server | **Conversations stay with each org** |
| Auth management | LO manages all accounts | **Each org manages their own** |
| Scaling | More orgs = more VPS load | **VPS only handles inference** |
| Availability | VPS down = chat down | **OpenWebUI still works with local models as fallback** |

### Important: OpenWebUI is NOT for Participant Data

Regardless of where OpenWebUI is deployed, it has:
- **No PII scrubbing pipeline**
- **No PHIPA consent enforcement**
- **No encryption at rest** for conversations (by default)

**Staff must not paste participant-identifying information into OpenWebUI.** This should be communicated during onboarding and reinforced with a system prompt:

> "You are an assistant for nonprofit staff. Never ask for client names, dates of birth, or identifying information. If a user shares identifying information, remind them to use de-identified data only."

### Data Retention Guidance (for each org's OpenWebUI)

Each organisation is responsible for their own OpenWebUI data, but LogicalOutcomes should recommend:

| Setting | Recommendation | Rationale |
|---------|---------------|-----------|
| Conversation retention | 90 days | Long enough for staff reference, short enough to limit PII exposure |
| Purge mechanism | Cron job or OpenWebUI admin setting | Automated — don't rely on manual cleanup |
| Acceptable use policy | Required before access | Staff must understand no participant data in chat |

**Accidental PII incident procedure (recommended for each org):**
1. Staff reports (or admin discovers) participant-identifying content in a conversation
2. Admin deletes the specific conversation immediately via OpenWebUI admin panel
3. Admin documents the incident (date, what was exposed, how it was discovered)
4. Remind staff of the acceptable use policy

---

## Security Architecture

### Network Security

```
Internet (KoNote instances, OpenWebUI instances, scripts)
    │
    ▼
┌──────────┐
│  Caddy   │ ← TLS termination, API key enforcement
│  :443    │
└────┬─────┘
     │  (internal Docker network only)
     └── ollama:11434      ← NOT exposed to internet
```

- Ollama listens only on the Docker internal network
- Caddy is the sole entry point — handles TLS (Let's Encrypt) and API key authentication
- All clients (KoNote, OpenWebUI, scripts) authenticate with a `Bearer` token checked by Caddy

### API Key Management

| Secret | Where Stored | Who Has It |
|--------|-------------|------------|
| `LLM_API_KEY` (Caddy checks this) | `.env` on LLM VPS | KoNote instances, OpenWebUI instances (in their connection settings) |
| VPS SSH key | Team workstations | Canadian-resident team members only |

### Firewall Rules (Optional Hardening)

Two approaches — choose one, not both:

**Option A: IP-restricted (if all client IPs are known)**

```bash
# Only allow traffic from known KoNote VPS IPs and office IPs
ufw default deny incoming
ufw allow ssh
ufw allow from <konote-vps-1-ip> to any port 443
ufw allow from <konote-vps-2-ip> to any port 443
ufw allow from <office-ip> to any port 443
ufw enable
```

**Option B: Open with API key auth (relying on Caddy)**

```bash
# Allow all HTTPS traffic — Caddy enforces API key auth
ufw default deny incoming
ufw allow ssh
ufw allow 80/tcp    # Caddy HTTP → HTTPS redirect
ufw allow 443/tcp   # Caddy HTTPS with API key check
ufw enable
```

Option A is more secure (two layers: firewall + API key). Option B is simpler when client IPs change or are unknown.

### Data Residency

| Data | Location | Residency |
|------|----------|-----------|
| Model weights | OVHcloud Beauharnois, QC | Canada |
| Inference input/output | In-memory only (not persisted by Ollama) | Canada |
| OpenWebUI conversations | Each org's own infrastructure | Per org — not on this VPS |
| KoNote participant data | KoNote VPS (also Beauharnois) | Canada |
| Survey Stage 1 (raw responses) | Processed on LLM VPS, in-memory | Canada |
| Survey Stage 2 (de-identified) | Sent to frontier LLM API | No PII — safe for external API |
| Model updates (downloads) | Ollama registry (US-hosted) | Transit only — model weights are not personal data |

**All personal data stays in Canada.** Model weights are open-source software, not personal data — downloading them from a US registry does not create a CLOUD Act exposure.

---

## Operational Procedures

### Monitoring

| Check | Method | Frequency |
|-------|--------|-----------|
| Ollama health | Docker HEALTHCHECK + autoheal | Every 30s |
| Public endpoint | UptimeRobot on `https://llm.example.com/v1/models` | Every 5 min |
| Disk usage | Cron script (alert >80%) | Hourly |
| Batch success | Cron script exit code + alert | Nightly |

### Model Updates

When a new Qwen3.5 release is available:

```bash
# Pull new model version
docker compose exec ollama ollama pull qwen3.5:35b-a3b

# Verify it loads
docker compose exec ollama ollama run qwen3.5:35b-a3b "Hello, respond with OK"

# Update INSIGHTS_MODEL in KoNote .env files if tag changed
```

Model updates do not require downtime — Ollama swaps the model in memory on next request.

### Backup

The LLM VPS has **minimal backup requirements**:

| Data | Backup? | Why |
|------|---------|-----|
| Model weights | No | Re-downloadable from Ollama registry |
| Docker volumes | No | Can be rebuilt from scratch in <15 min |
| `.env` + Caddyfile | Yes | Store in password manager |

**Recovery procedure:** Provision new VPS → `docker compose up` → `ollama pull`. Total recovery: ~15 minutes. The lean stack has no state to restore.

### Cron Jobs

```cron
# Nightly suggestion theme batch (before KoNote backups)
0 1 * * * /opt/llm-server/scripts/run-theme-batch.sh >> /var/log/llm-batch.log 2>&1

# Disk usage check
0 * * * * /opt/llm-server/scripts/disk-check.sh

# Log rotation
0 3 * * * /usr/sbin/logrotate /etc/logrotate.d/llm-server

# Docker prune (weekly)
0 4 * * 0 docker system prune -f >> /var/log/docker-prune.log 2>&1
```

---

## Deployment Checklist

1. **Provision VPS-4** on OVHcloud Canada (Beauharnois) — 12 vCPUs, 48 GB RAM, 300 GB NVMe
2. **Install Docker + Docker Compose** on the VPS
3. **Configure DNS** — point `llm.example.com` to VPS IP
4. **Generate LLM_API_KEY** — `openssl rand -hex 32`
5. **Create `.env`** with `LLM_API_KEY`
6. **Create `Caddyfile`** (see above)
7. **Create `docker-compose.yml`** (see above)
8. **Deploy:** `docker compose up -d`
9. **Pull primary model:** `docker compose exec ollama ollama pull qwen3.5:35b-a3b`
10. **Verify Ollama:** `curl -H "Authorization: Bearer $LLM_API_KEY" https://llm.example.com/v1/models`
11. **Configure KoNote instances:** set `INSIGHTS_API_BASE`, `INSIGHTS_API_KEY`, `INSIGHTS_MODEL` in each `.env`
12. **Test end-to-end:** trigger outcome insights from a KoNote instance, verify it uses the self-hosted model
13. **Set up cron jobs:** theme batch, disk check, log rotation
14. **Configure UptimeRobot** — monitor `https://llm.example.com/v1/models`
15. **Distribute API key** to organisations running OpenWebUI instances (for their connection settings)
16. **Document:** VPS IP, domain, API key location

---

## Scaling Considerations

### Concurrent Request Handling

Ollama processes requests sequentially by default. With `OLLAMA_NUM_PARALLEL=2`, it can handle 2 concurrent requests. For higher concurrency:

| Approach | Concurrency | Trade-off |
|----------|------------|-----------|
| `OLLAMA_NUM_PARALLEL=1` | 1 request at a time | Fastest per-request, queue others |
| `OLLAMA_NUM_PARALLEL=2` | 2 concurrent | Slightly slower per-request, better throughput |
| `OLLAMA_NUM_PARALLEL=4` | 4 concurrent | Needs more RAM for KV caches |

**Start with 2.** The primary workload (nightly batch) is sequential anyway. Interactive use from external OpenWebUI instances is low-volume.

### When to Upgrade

| Signal | Action |
|--------|--------|
| External clients report slow responses | Increase `OLLAMA_NUM_PARALLEL` or upgrade VPS |
| Batch processing exceeds 4 hours | Upgrade to VPS-5 (more vCPUs) |
| Quality complaints on theme tagging | Switch to 27B dense or 122B-A10B model |
| Many concurrent OpenWebUI connections | Increase `OLLAMA_NUM_PARALLEL` |
| RAM usage consistently >85% | Upgrade VPS tier |

---

## Provider Consolidation Path: Eliminating OpenRouter

### The Goal

Long-term, KoNote should run **all AI features on the self-hosted Ollama endpoint**, eliminating the OpenRouter dependency entirely. This gives agencies a single, truthful claim: "No data of any kind is sent to any external AI service."

### Batch vs Interactive Split

The key insight is that most tools-only features don't need interactive speed — they can run as overnight batch jobs on the self-hosted model.

| Function | Category | Current Provider | Can Batch? | Notes |
|----------|----------|-----------------|------------|-------|
| `suggest_metrics()` | Tools-only | OpenRouter | **Yes** | Pre-compute for each target against metric catalogue |
| `generate_narrative()` | Tools-only | OpenRouter | **Yes** | Report summaries, generated before report is viewed |
| CIDS categorisation | Tools-only | OpenRouter | **Yes** | Map metrics/targets to taxonomy codes |
| FHIR metadata enrichment | Tools-only | OpenRouter | **Yes** | Enrich service episodes, plan targets |
| French translation | Tools-only | OpenRouter | **Yes** | `translate_strings` management command, already batch |
| Outcome insights + themes | Participant data | Self-hosted | **Yes** | Already planned as nightly batch |
| `suggest_target()` | Tools-only | OpenRouter | No | Staff enters participant words, waits for structured goal |
| `improve_outcome()` | Tools-only | OpenRouter | No | Staff enters draft, waits for SMART version |
| `build_goal_chat()` | Tools-only | OpenRouter | No | Multi-turn conversation, staff waiting each turn |
| `suggest_note_structure()` | Tools-only | OpenRouter | No | Staff clicks button, waits for note sections |

**7 of 10 AI functions can move to self-hosted immediately** — they run overnight and no one is waiting. Only 4 interactive functions need real-time response speed.

### Validation-Retry Cycle

Currently, all AI functions make a single call and return `None` on failure. Adding a validation-retry cycle would significantly improve structured output reliability with any model:

```
Attempt 1: Call model → parse JSON → validate fields
  If valid: return result (most requests stop here)
  If invalid: build error message listing specific failures
Attempt 2: Re-prompt with "Your response had errors: [X].
            Return corrected JSON only." → parse → validate
  If valid: return result
  If still invalid: return None (graceful failure)
```

**Estimated reliability with current open-source MoE models:**
- First-attempt structured output success: ~75–85% (vs ~95%+ for Claude Sonnet)
- After one retry with error feedback: ~92–97%
- Net effect: comparable reliability, ~25% of requests take 2x latency

This pattern is useful regardless of provider — it makes both OpenRouter and self-hosted paths more resilient. It also provides a defence-in-depth layer: the retry validation can include a PII scan on model responses, catching any identifying content that leaked through the input scrubbing.

**Build this before the first agency deployment.** It's a prerequisite for consolidation and independently valuable.

### Trigger Conditions for Full Consolidation

Test every 6 months with the latest open-source MoE model:

| Condition | How to Test | Target |
|-----------|-------------|--------|
| Structured output first-attempt success | Run 50 test prompts against self-hosted model | >85% |
| Structured output with one retry | Same test, with validation-retry | >95% |
| Interactive response speed | Median response time for 200-token generation | <30 seconds |
| Staff satisfaction | Usage metrics or survey from deployed agencies | No decline after switch |

When **all four conditions are met**, consolidate by removing `OPENROUTER_API_KEY` from the default `.env` template and routing all functions through `INSIGHTS_API_BASE`.

### Keep the OpenRouter Code Path

Consolidation should be **operational** (no agency configures OpenRouter by default) rather than **architectural** (removing the code). The `OPENROUTER_API_KEY` and `_call_openrouter()` path in `ai.py` should remain permanently:

- Costs near zero to maintain (a few lines of code)
- Provides an instant fallback if a model version disappoints
- Allows specific agencies to opt into cloud AI if they choose
- One environment variable to re-enable

### Model Swap Process

When a better open-source model is released:

```bash
# Pull new model
docker compose exec ollama ollama pull <new-model-tag>

# Update KoNote .env files
INSIGHTS_MODEL=<new-model-tag>

# No code changes needed — same OpenAI-compatible API
```

The MoE architecture trend (more knowledge in fewer active parameters per year) suggests models released in 2027–2028 with 1–2B active parameters could match current Claude Sonnet quality on structured output tasks.

### Recommended Sequence

| When | Action |
|------|--------|
| **Now** | Document this path (done) |
| **Before first deployment** | Build validation-retry cycle in `ai.py` |
| **At first deployment** | Move batch-capable functions to self-hosted; keep interactive on OpenRouter |
| **After first agency is live** | Collect real usage data on AI feature frequency and speed tolerance |
| **Every 6 months** | Test latest MoE model against trigger conditions |
| **When conditions met** | Switch default to self-hosted only; keep OpenRouter as documented fallback |

---

## Alternatives Considered

### GPU VPS / Dedicated GPU Server

OVHcloud offers GPU instances (T4, L40S, H100) in their Public Cloud, but:

| Factor | GPU Instance | CPU VPS |
|--------|-------------|---------|
| Cost (CAD/mo) | ~$500–2,000+ | **~$40** |
| Speed | ~30–50 tokens/sec | ~2–5 tokens/sec |
| Availability | Limited regions | **Beauharnois available** |

**Rejected for now.** The MoE model on CPU provides acceptable speed for batch processing and low-concurrency interactive use. GPU becomes relevant only if real-time speed for many concurrent users becomes a requirement.

### Dedicated Inference API (Groq, Together, etc.)

Cloud inference APIs offer fast, cheap inference but reintroduce data sovereignty concerns — same issue as OpenRouter. Rejected for participant data workloads.

### Running Ollama on the Same VPS as KoNote

The [OVHcloud DRR](ovhcloud-deployment.md) lists this as an anti-pattern for high-traffic multi-tenant deployments. For 1–3 agencies, it's acceptable but limits future growth. The shared dedicated VPS is the right architecture for a multi-purpose inference server.

---

## Anti-Patterns

| Approach | Why Rejected |
|----------|-------------|
| Running LLM on the same VPS as a busy KoNote instance | Resource contention — inference and database both CPU/RAM-hungry |
| Hosting OpenWebUI on the LLM VPS | Wastes VPS resources, centralises data unnecessarily — each org deploys their own OpenWebUI pointing to this endpoint |
| Exposing Ollama directly to the internet without Caddy | No TLS, no auth, no rate limiting |
| Using a US-hosted inference API for participant data | Defeats the data sovereignty purpose |
| Sending agency identifiers to the LLM | Unnecessary data exposure — only send the text |
| Pasting participant-identifying data into OpenWebUI | OpenWebUI has no PII scrubbing — staff must not paste identifying data |
| Doing deep qualitative analysis entirely on self-hosted model | Open-source model quality doesn't match frontier models for nuanced thematic analysis — use two-stage pipeline instead |
| Skipping the API key on the Ollama endpoint | Any internet scanner could send inference requests |
| Using the largest possible model for all tasks | Diminishing returns — 35B-A3B quality is excellent; 122B-A10B is only marginally better at 3× the RAM |
| GPU VPS at current scale | $500+/mo for speed improvements that don't matter for nightly batch processing |

---

## GK Review Items

- [x] Confirm the two-stage survey pipeline meets quality needs — **Approved.** Two-stage approach (Qwen strips PII, Claude does analysis) confirmed.
- [ ] Review OpenWebUI acceptable use guidelines for staff — deferred to OpenWebUI project, not a KoNote blocker
- [ ] Confirm VPS-4 sizing is appropriate for expected workload — deferred to deployment, will be confirmed via testing
- [ ] Review whether survey analysis outputs need the same privacy controls as KoNote insights — deferred to deployment assessment
- [ ] Choose subdomain on logicaloutcomes.net — use a non-obvious, hard-to-guess subdomain (not `llm.`). Decided during deployment.

---

## Graduated Privacy Threshold (Added 2026-03-05, AI-FOCUSED-THEME1)

The N=5 privacy threshold for AI theme processing **only applies when `INSIGHTS_API_BASE` is configured** (self-hosted LLM). If an agency routes through OpenRouter (no `INSIGHTS_API_BASE`), the N=15 threshold still applies.

| Participant Count | Self-hosted (`INSIGHTS_API_BASE` set) | External (OpenRouter) |
|---|---|---|
| < 5 | No AI theme processing | No AI theme processing |
| 5–14 | AI processing allowed; verbatim text suppressed in UI | No AI theme processing |
| 15+ | Full processing + verbatim display | Full processing + verbatim display |

**Rationale:** Self-hosted processing keeps de-identified data within Canadian infrastructure, reducing re-identification risk enough to lower the threshold from 15 to 5. The verbatim text suppression for 5–14 provides an additional privacy layer.

**Deployment note:** This threshold difference must be documented in ops deployment instructions. Agencies expecting the N=5 threshold must have `INSIGHTS_API_BASE` configured.
