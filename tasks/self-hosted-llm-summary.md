# Self-Hosted LLM Server — Summary for Colleagues

## What We're Building

A dedicated AI server hosted in Canada (OVHcloud data centre in Beauharnois, Quebec) that provides a shared open-source language model for several purposes:

1. **KoNote AI features** — processing participant feedback data (suggestion themes, outcome insights) without sending it to US cloud services
2. **Chat for staff** — organisations deploy their own OpenWebUI chat interface (like ChatGPT) that connects to this central model server
3. **Survey analysis** — a two-stage process for analysing open-ended survey responses while protecting participant privacy
4. **General analytical work** — document analysis, report drafting, data interpretation

## How It Works

The server runs **Ollama** (open-source LLM engine) with a model called **Qwen3.5-35B-A3B**. This model uses a "Mixture of Experts" architecture — it has the knowledge of a 35-billion-parameter model but only activates 3 billion parameters at a time, which makes it fast even without a GPU.

The server is intentionally lean: just the AI model engine and a secure web gateway. Nothing else runs on it. External systems (KoNote instances, OpenWebUI chat interfaces, analysis scripts) connect to it over the internet using an API key.

### Two-Stage Survey Analysis Pipeline

For survey qualitative analysis, we use a two-stage approach:

- **Stage 1 (self-hosted, in Canada):** The open-source model strips personally identifiable information from raw survey responses, cleans up the data, and structures it clearly. All of this happens on the Canadian server — raw data never leaves the country.

- **Stage 2 (frontier AI, de-identified data):** The cleaned, de-identified data is then sent to a high-quality commercial AI (like Claude) for deep thematic analysis, coding, and insight generation. Since the PII was already removed in Stage 1, there's no privacy concern.

This gives us both **data sovereignty** (raw data stays in Canada) and **high-quality analysis** (frontier AI handles the complex analytical work).

## Why Self-Hosted?

- **Data sovereignty:** Participant data stays in Canada, on Canadian servers. No US CLOUD Act exposure.
- **Privacy compliance:** Meets PHIPA, PIPEDA, and funder data handling requirements.
- **Fixed cost:** One monthly fee covers unlimited use across all agencies — no per-question charges.
- **Indigenous data sovereignty:** Supports OCAP principles for Indigenous-serving agencies where even de-identified data leaving agency infrastructure may be unacceptable.

## Hosting Costs (OVHcloud Canada)

All prices in Canadian dollars. OVHcloud prices in USD; converted at approximately 1 USD = 1.35 CAD.

| Server Tier | Specs | Monthly Cost (CAD) | Notes |
|-------------|-------|-------------------|-------|
| VPS-3 | 8 CPUs, 24 GB RAM | ~$23 | Minimum viable — model only, low concurrency |
| **VPS-4 (recommended)** | **12 CPUs, 48 GB RAM** | **~$40** | **Good headroom for concurrent requests** |
| VPS-5 | 16 CPUs, 64 GB RAM | ~$59 | For a larger model or heavy use |
| VPS-6 | 24 CPUs, 96 GB RAM | ~$79 | Maximum — largest model + heavy use |

### Cost Comparison

| Scenario | Monthly Cost (CAD) |
|----------|-------------------|
| Current (OpenRouter cloud API, 10 agencies) | ~$27–68 (usage-based, unpredictable) |
| **Self-hosted VPS-4 (recommended)** | **~$40 (fixed, unlimited)** |
| Self-hosted + off-site backup server | ~$51 |

The self-hosted option becomes cheaper than the cloud API at approximately 5 agencies and provides unlimited use.

## What Organisations Get

- **KoNote agencies:** Their participant data AI features run on this server instead of US cloud services. No configuration needed on their end — just an environment variable change.
- **OpenWebUI users:** Each organisation deploys their own chat interface (similar to ChatGPT) and points it at this central model. Their conversation data stays on their own infrastructure, not on the LLM server.
- **Evaluators/analysts:** Access to the two-stage survey analysis pipeline for qualitative research work.

## Key Design Decisions

- **Lean server:** The LLM server runs only the model engine and a web gateway. OpenWebUI chat instances are deployed separately by each organisation — this keeps the server simple and means each org controls their own chat data.
- **No GPU needed (yet):** The Mixture of Experts model architecture makes CPU-only inference practical. Interactive speed is acceptable (~2–5 words/second). Batch processing (overnight theme tagging) doesn't need speed at all.
- **Model can be swapped easily:** If a better open-source model is released, it's a single command to switch. No code changes required.
- **Commercial AI stays as a fallback:** The existing cloud AI path (OpenRouter) is kept in the code permanently. If the self-hosted model has issues, one environment variable re-enables cloud AI. Long-term, as open-source models improve, more features can move to self-hosted.

## Timeline

| When | What |
|------|------|
| Now | Architecture designed and documented |
| Before first agency deployment | Build validation-retry cycle for structured output reliability |
| At first deployment | Move batch-capable features to self-hosted; keep interactive features on cloud AI |
| After first agency is live | Collect real usage data |
| Every 6 months | Test latest open-source model against quality benchmarks |
| When quality conditions met | Switch all features to self-hosted by default |

## Questions for Discussion

See the full design rationale record at `tasks/design-rationale/self-hosted-llm-infrastructure.md` for detailed technical architecture, security design, and the complete list of review items.
