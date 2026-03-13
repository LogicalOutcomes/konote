# AI Provider Configuration Guide

**Last updated:** March 2026 | **Audience:** Agency operators, IT staff, managed service providers

This guide explains how KoNote uses AI, what data is involved, and how to choose and configure your AI provider. For the full privacy implications, see the [Privacy Policy Template](privacy-policy-template.md), Section 7.

---

## How KoNote Uses AI

KoNote has two categories of AI features, controlled by separate on/off switches in **Admin > Settings > Features**:

| Category | Toggle Name | What It Does | Data Involved |
|----------|-------------|-------------|---------------|
| **Tools-only AI** | *AI Assist (Tools Only)* | Suggests metrics, improves goal wording, generates metric rationales | Program metadata only — metric names, goal descriptions, program names. **No participant information.** |
| **Participant-data AI** | *AI Assist (Participant Data)* | Generates outcome insights narratives, theme analysis, focused summaries from progress notes | De-identified excerpts from progress notes (names, addresses, phone numbers, and other PII are scrubbed before sending) |

Both are **off by default**. An administrator must explicitly enable each one.

---

## Your Two Provider Options

### Option A: Cloud Provider (OpenRouter)

OpenRouter routes requests to a hosted AI model (default: Anthropic Claude Sonnet). Data is sent to US-based servers.

**Best for:**
- Agencies that want the highest quality AI output
- Agencies comfortable with de-identified data leaving Canada
- Quick setup (just add an API key)

**Data residency:** US (OpenRouter → Anthropic infrastructure)

**What leaves your server:**
- Tools-only: metric names, goal descriptions, program names (no PII)
- Participant-data (if enabled): de-identified note excerpts with all names, addresses, phone numbers, emails, SIN numbers, and postal codes removed before sending

**What never leaves your server:** client names, dates of birth, contact information, full case records, unprocessed notes, database credentials, encryption keys.

### Option B: Self-Hosted Provider (Ollama)

Run an AI model on your own server. All data stays on infrastructure you control.

**Best for:**
- Agencies that require all data to remain in Canada
- Agencies with strict PIPEDA/PHIPA data residency requirements
- Agencies willing to manage an additional server

**Data residency:** On your server (Canadian VPS recommended)

**What leaves your server:** Nothing — all AI processing happens locally.

**Trade-offs:**
- Requires a separate VPS (~$55 CAD/month for a VPS with 8 vCPU, recommended model: Qwen3.5-35B-A3B)
- Output quality may be lower than cloud models for complex narrative tasks
- You are responsible for keeping the model server running and updated

---

## Configuration

### Configuring OpenRouter (Cloud)

Add these to your `.env` file:

```bash
# Required — your OpenRouter API key
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional — override the default model (default: anthropic/claude-sonnet-4-20250514)
# OPENROUTER_MODEL=anthropic/claude-sonnet-4-20250514

# Optional — your site URL shown in OpenRouter dashboard
# OPENROUTER_SITE_URL=https://konote.youragency.ca
```

**To get an API key:** Sign up at [openrouter.ai](https://openrouter.ai), add a payment method, and create an API key. Costs are usage-based (typically under $5/month for a small agency).

After adding the key, restart the web container:
```bash
docker compose up -d web
```

Then enable "AI Assist (Tools Only)" in **Admin > Settings > Features**. If you also want participant-data insights, enable "AI Assist (Participant Data)" as well.

### Configuring Self-Hosted Ollama

If you want participant-data AI features to run on your own server instead of OpenRouter, set up an Ollama instance and configure KoNote to use it.

**Step 1: Set up the Ollama server**

See the [Self-Hosted LLM Infrastructure](../tasks/design-rationale/self-hosted-llm-infrastructure.md) design document for detailed VPS sizing and Docker Compose configuration. In brief:

1. Provision a VPS with at least 8 vCPU and 16 GB RAM (OVHcloud B2-15 or equivalent)
2. Install Docker and deploy Ollama with a reverse proxy (Caddy recommended for automatic HTTPS)
3. Pull the recommended model: `docker exec ollama ollama pull qwen3.5:35b-a3b`
4. Secure the endpoint with HTTPS and a bearer token

**Step 2: Configure KoNote**

Add these to your `.env` file:

```bash
# The base URL of your Ollama instance (must use HTTPS for remote hosts)
INSIGHTS_API_BASE=https://llm.youragency.ca/v1

# Bearer token for authentication (must match Caddy's basicauth or header config)
INSIGHTS_API_KEY=your-bearer-token-here

# The model name as registered in Ollama
INSIGHTS_MODEL=qwen3.5:35b-a3b

# Security: only allow connections to this host
INSIGHTS_ALLOWED_HOSTS=llm.youragency.ca
```

After updating `.env`, restart the web container:
```bash
docker compose up -d web
```

**Note:** You still need `OPENROUTER_API_KEY` for tools-only features (metric suggestions, goal improvement) — those use OpenRouter regardless of the insights provider. Only participant-data features (outcome insights, theme analysis) route through the self-hosted provider.

### Mixed Configuration (Recommended)

The recommended setup for Canadian agencies with data residency requirements:

| Feature | Provider | Data Residency |
|---------|----------|---------------|
| Metric suggestions | OpenRouter (cloud) | US — acceptable, no PII involved |
| Goal improvement | OpenRouter (cloud) | US — acceptable, no PII involved |
| Metric rationale generation | OpenRouter (cloud) | US — acceptable, no PII involved |
| Outcome insights (narrative drafts) | Ollama (self-hosted) | Canada — on your VPS |
| Theme analysis (focused summaries) | Ollama (self-hosted) | Canada — on your VPS |

This gives the best quality for tools-only features (where no participant data is involved) while keeping all participant-related data processing in Canada.

---

## Security Safeguards

KoNote enforces several safety measures regardless of which provider you choose:

1. **PII scrubbing** — Before any participant data reaches the AI provider, KoNote removes client names, staff names, email addresses, phone numbers, SIN numbers, postal codes, and street addresses.

2. **Safety prompt** — Every AI request includes an instruction that the model must never ask for, guess, or reference any client identifying information.

3. **HTTPS enforcement** — Remote Ollama endpoints must use HTTPS. KoNote refuses to connect over plain HTTP to non-localhost addresses.

4. **Host allowlist** — The `INSIGHTS_ALLOWED_HOSTS` setting restricts which servers KoNote will send data to, preventing accidental misconfiguration.

5. **Feature toggles** — Both AI categories are off by default. Enabling participant-data AI requires a separate, deliberate toggle.

6. **Audit logging** — AI feature usage is logged in the audit database.

---

## Disabling AI

To disable all AI features:

1. Go to **Admin > Settings > Features**
2. Turn off "AI Assist (Tools Only)" and "AI Assist (Participant Data)"

No AI requests will be made. Existing data (notes, metrics, goals) is unaffected — AI features are purely additive.

To completely remove the API key:
1. Remove `OPENROUTER_API_KEY` from your `.env` file
2. Restart the web container: `docker compose up -d web`

---

## Cost Estimates

| Provider | Approximate Monthly Cost | Notes |
|----------|--------------------------|-------|
| **OpenRouter (tools-only)** | $2–$5 CAD | Usage-based; small agencies with < 100 active clients |
| **OpenRouter (tools + insights)** | $5–$15 CAD | More tokens used for narrative generation |
| **Self-hosted Ollama VPS** | ~$55 CAD/month | Fixed cost for VPS, regardless of usage |
| **Self-hosted + OpenRouter tools** | ~$57–$60 CAD/month | Recommended for data residency compliance |

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| AI features don't appear in the UI | Feature toggles are off | Enable in Admin > Settings > Features |
| "AI features unavailable" message | Missing `OPENROUTER_API_KEY` | Add the key to `.env` and restart |
| Insights return empty or error | Ollama server unreachable | Check `INSIGHTS_API_BASE` URL and that the Ollama container is running |
| "INSIGHTS_API_BASE must use HTTPS" in logs | Plain HTTP to remote host | Configure HTTPS on your Ollama reverse proxy |
| "Host not in INSIGHTS_ALLOWED_HOSTS" in logs | Host mismatch | Add the hostname to `INSIGHTS_ALLOWED_HOSTS` in `.env` |

For detailed operational procedures, see the [LLM Operations Runbook](llm-operations-runbook.md).
