# AI Feature Toggle Split — Design Rationale Record

Task ID: AI-TOGGLE1
Date: 2026-02-25
Status: Draft — GK reviews before implementation
Expert panel: Canadian Privacy & Health Information Specialist, Nonprofit Technology Governance Advisor, Data Sovereignty & AI Ethics Specialist, Software Architect

---

## Problem

KoNote currently has a single `ai_assist` boolean toggle that gates all AI features. Some agencies may not want to use AI at all; others are comfortable with AI that helps staff write better outcomes but do not want participant data sent to external AI services.

The current all-or-nothing toggle forces agencies into a false choice: accept all AI (including participant data processing) or lose access to tools that make the platform significantly more functional and CIDS-compliant.

## Two Categories of AI Use

The expert panel identified a fundamental distinction between two types of AI use:

### Category 1: Tools-only AI (`ai_assist_tools_only`)

Processes **only program metadata, taxonomy labels, and outcome descriptions**. Zero personal information is involved.

| Feature | What it does | Data sent to AI |
|---------|-------------|----------------|
| Metric suggestions | Suggest relevant metrics for a plan target | Target description + metric catalogue (program metadata) |
| Goal builder | Turn rough outcome text into SMART format | Draft outcome text (staff-written, no PII) |
| Target suggestions | Structure a goal with metrics | Program context + staff description (PII-scrubbed) |
| Narrative generation | Turn aggregate stats into outcome summary | Program name + date range + aggregate numbers |
| Note structure suggestions | Suggest sections for a progress note | Target name + description + metric names |
| CIDS categorisation | Map metrics/targets to CIDS taxonomy | Field names + metric definitions |

**Privacy classification:** None of these involve personal information under PIPEDA s.2 or personal health information under PHIPA s.4. They process institutional data about what an agency measures, not who they measure.

**Default: Enabled.** The platform is significantly less functional without these tools, and CIDS compliance depends on AI-assisted categorisation.

### Category 2: Participant-data AI (`ai_assist_participant_data`)

Processes **de-identified participant content** — survey responses, open-ended feedback, suggestion themes.

| Feature | What it does | Data sent to AI |
|---------|-------------|----------------|
| Outcome insights | Summarise themes from participant feedback | De-identified participant quotes and responses |
| Qualitative analysis | Identify patterns in open-ended responses | Scrubbed participant text |

**Privacy classification:** Even with name scrubbing, this is **de-identified personal information** under PIPEDA s.2 and potentially **personal health information** under PHIPA s.4 if it relates to health services. Context, small sample sizes, or distinctive phrasing can re-identify participants.

**Default: Disabled.** Agencies must make an intentional decision to enable this.

### Not in the toggle system: Translation

API-based French translation processes static UI strings ("Save", "Progress Note", etc.) — no personal information whatsoever. Bilingual service is legally required under the Official Languages Act and Ontario's French Language Services Act. Including translation in the AI toggle system creates a compliance trap: an agency that disables AI and doesn't provide manual translations violates the law.

**Translation stays outside the toggle system entirely.**

## Current Data Flow: Where Participant Data Goes and How It's Protected

This section traces exactly what happens today when participant data is sent to an external AI service. Only **one feature** currently does this: `generate_outcome_insights` (the Outcome Insights view on the reports page).

### What participant content is collected

The `collect_quotes()` function in [insights.py](apps/reports/insights.py) gathers up to 30 quotes from three sources:

1. **`client_words`** — what the participant said about their progress, recorded by the worker in a progress note (field on `ProgressNoteTarget`)
2. **`participant_reflection`** — the participant's own reflection on their session, recorded on the `ProgressNote`
3. **`participant_suggestion`** — the participant's response to "If you could change one thing about this program, what would it be?" (also on `ProgressNote`, with optional staff-assigned priority)

All three fields are **encrypted at rest** (Fernet/AES) in the database. They are decrypted in Python when read.

### Privacy gate: minimum sample size

Before collecting any quotes, the system checks whether the program has at least 15 enrolled participants. If fewer than 15, **no quotes are collected at all** — the function returns an empty list. This prevents small-group re-identification (e.g., a 3-person program where quotes are obviously attributable).

### What is scrubbed before sending to AI

The `scrub_pii()` function in [pii_scrub.py](apps/reports/pii_scrub.py) runs a two-pass scrub on every quote:

**Pass 1 — Structured PII patterns (regex):**
- Email addresses → `[EMAIL]`
- Canadian postal codes (K1A 0B1) → `[POSTAL CODE]`
- Social Insurance Numbers → `[SIN]`
- Street addresses (123 Main Street) → `[ADDRESS]`
- Phone numbers → `[PHONE]`

**Pass 2 — Known names (database lookup):**
- All client first names, last names, and preferred names for the program
- All active staff display names
- Names matched with word boundaries (avoids corrupting common words like "Hope" or "Grace")
- Matched names → `[NAME]`

### What is deliberately excluded from the AI payload

The code in `outcome_insights_view` ([ai_views.py:382-397](konote/ai_views.py)) applies **data minimisation**:

- **`note_id` is never sent to AI** — internal database IDs are stripped from the payload before it reaches the API. This prevents correlation if the AI provider were breached. A temporary `quote_source_map` is built in memory to reconnect AI-identified themes back to source notes, but this map is never persisted or transmitted.
- **Dates are excluded** (`include_dates=False`) — prevents temporal re-identification.
- **Only two fields per quote reach the AI:** the scrubbed text and the target name (a generic goal label like "Build Social Connections," not PII).

### Where the data goes

The scrubbed quotes are sent via HTTPS POST to one of two endpoints:

1. **OpenRouter API** (`https://openrouter.ai/api/v1/chat/completions`) — the default. Data transits over TLS. OpenRouter's privacy policy applies. The request includes an API key, model selection (Claude Sonnet 4), and the scrubbed content.
2. **Local/custom endpoint** — if `INSIGHTS_API_BASE` is configured (e.g., pointing to an Ollama instance), data goes there instead. This is the **existing infrastructure for a self-hosted model** — the code already supports it.

### What protections exist today

| Protection | Status | Detail |
|-----------|--------|--------|
| Encryption at rest (Fernet/AES) | Active | All three source fields are encrypted in the database |
| PII scrubbing (names, phones, emails, postal codes, SINs, addresses) | Active | Two-pass scrub before any data leaves the instance |
| Minimum sample size (15 participants) | Active | No quotes collected from small programs |
| Note ID exclusion | Active | Internal IDs never reach the AI provider |
| Date exclusion | Active | Dates stripped from program-level quotes |
| TLS in transit | Active | HTTPS to OpenRouter or local endpoint |
| Rate limiting | Active | 10 requests/hour per user for insights |
| Access control | Active | User must have active role in the program |
| Quote verification | Active | AI responses validated — cited quotes must be verbatim substrings of originals; hallucinated quotes are stripped |
| Safety prompt | Active | System prompt instructs AI to never ask for or reference identifying information |
| Audit trail | Partial | `InsightSummary` records who generated each cached result, but toggle changes are not yet audited |
| Self-hosted model support | Ready | `INSIGHTS_API_BASE` env var already routes to local Ollama |

### What is NOT protected (known gaps)

1. **Content re-identification risk** — Even after name scrubbing, distinctive phrasing or unusual situations described in participant quotes could identify someone in a small community. The 15-participant minimum helps but doesn't eliminate this risk.
2. **AI provider data retention** — OpenRouter and the underlying model provider (Anthropic) have their own data retention policies. KoNote does not control what happens to data after it reaches the API. This is the core reason the self-hosted LLM path is important.
3. **Toggle change audit** — Currently no audit log entry when `ai_assist` is toggled on or off. The DRR recommends adding this.
4. **No participant notification** — Participants are not currently informed whether AI processes their feedback. The DRR recommends adding a portal transparency statement.

### Goal builder: a borderline case

The goal builder (`suggest_target_view`, `goal_builder_chat`) scrubs participant words before sending them to AI. The input is what the staff member typed — often a paraphrase like "wants to make friends outside the group" rather than a verbatim participant quote. This is classified as **tools-only** because:

- The staff member controls what they type
- PII scrubbing runs before transmission
- The AI processes the worker's description of a goal area, not the participant's own recorded words
- Helper text should remind staff not to include identifying details (recommended in this DRR)

However, a staff member *could* paste a participant's exact words. The PII scrub catches names and structured identifiers but not the content itself. This is why the DRR recommends UI guardrails and prompt instructions for this specific feature.

## Toggle Design Decision

### Recommended: Two named toggles (Option C)

| Toggle Key | Admin Label | Description | Default | Depends On |
|-----------|------------|-------------|---------|------------|
| `ai_assist_tools_only` | "AI Tools (no participant data)" | AI helps staff write SMART outcomes, suggest metrics, categorise into CIDS, and generate narrative summaries from aggregate data. **No participant data is ever sent to AI.** | **Enabled** | — |
| `ai_assist_participant_data` | "AI Participant Insights" | AI summarises themes from participant feedback and open-ended responses. Individual responses are de-identified before processing, but content is sent to an external AI service. | Disabled | `ai_assist_tools_only` |

Three agency states:

| State | ai_assist_tools_only | ai_assist_participant_data | What works |
|-------|---------------------|---------------------------|------------|
| No AI | OFF | OFF (greyed out) | All features work manually, no AI calls made |
| Tools only (default) | **ON** | OFF | Metric suggestions, goal builder, CIDS mapping, narrative generation |
| Full AI | ON | ON | All above + theme summarisation from participant responses |

### Alternatives considered and rejected

**Option A: Two independent toggles (`ai_tools` + `ai_insights`)**
Rejected because the naming is vague ("tools" could mean anything) and there's no dependency relationship — an admin could enable insights without the base AI infrastructure.

**Option B: Three-level single toggle (`off` / `tools_only` / `full`)**
Rejected because it breaks the existing boolean toggle infrastructure. Every `{% if features.ai_assist %}` check would need rewriting. The dependency system already handles the two-toggle approach without migration effort.

## Admin UI Labelling

The admin UI must be crystal clear that tools-only means tools-only:

- The label includes "(no participant data)" explicitly in the feature name
- The description states in bold: "No participant data is ever sent to AI"
- The `when_on` / `when_off` impact descriptions make the distinction unmistakable
- When `ai_assist_tools_only` is off, `ai_assist_participant_data` is greyed out with "Requires: AI Tools"
- The word "AI" is used transparently — these features use AI, and that's stated honestly. The labelling makes it clear that the tools-only toggle involves no participant data.

## Anti-Patterns (Rejected)

| Approach | Why Rejected |
|----------|-------------|
| Including translation in the AI toggle system | Creates a legal compliance trap — bilingual service is mandatory under Official Languages Act and Ontario FLSA |
| Single three-level toggle | Breaks existing boolean toggle infrastructure, requires rewriting all template checks |
| Treating non-PII tools as a privacy concern | These process zero personal information — framing them as a privacy risk invites unnecessary governance friction from boards that blanket-ban "AI" |
| Enabling `ai_assist_participant_data` without confirmation step | Admin toggling features may not be the person who made the policy decision — governance nudge required |
| Hiding the "AI" label from tools-only features | Transparency requires calling AI what it is, even when benign — but labelling must be crystal clear about scope |
| Single `ai_assist` toggle for everything | Forces false choice: all AI or no AI. Agencies lose critical tools because of concerns about participant data |

## Additional Design Elements (for implementation)

### Confirmation modal for participant data toggle

When an admin enables `ai_assist_participant_data`, a confirmation modal appears:

> "Enabling this feature means de-identified participant responses will be sent to an external AI service for analysis. Individual names are removed, but response content is processed externally. Please confirm your agency has reviewed this with your privacy officer or board."

This is a governance nudge, not a legal gate. It ensures the decision is intentional.

### Audit logging

Log when `ai_assist_participant_data` is toggled: who, when, on/off. Use the existing `AuditLog` model (separate audit database). If a funder asks "who authorised AI processing of participant data?", the agency has a record.

### Participant-facing transparency

The participant portal should state the current AI posture:

- **If participant insights ON:** "This agency uses AI to summarise feedback themes. Your name is removed before processing. No individual responses are shared."
- **If participant insights OFF:** "This agency does not use AI to process your responses."

### UI guardrails on goal builder

The goal builder input should include helper text: "Describe the general goal area. Don't include names or identifying details." The AI prompt should instruct: "Do not reference specific situations described. Generate a general outcome statement."

### AI-suggested indicator

When AI generates a suggested target or metric, staff should see a small "AI-suggested" indicator — not as a warning, but as transparency. Preserves human agency in the decision.

## Future: Self-Hosted Open-Source LLM for Participant Suggestions

For agencies with heightened data sovereignty concerns (Indigenous communities under OCAP principles, newcomer-serving organisations), even de-identified data leaving the agency's infrastructure may be unacceptable.

### Scope: Participant suggestions only

The self-hosted LLM analyses the `participant_suggestion` field — the response to "If you could change one thing about this program, what would it be?"

**Why suggestions specifically:** Unlike `client_words` (clinical observations recorded by the worker) or `participant_reflection` (personal processing), suggestions are explicit communications directed at the agency — participants telling managers and executive directors what they want changed. This makes them a natural fit for AI-assisted theme aggregation: the LLM surfaces patterns from individual suggestions so program managers and EDs can see what participants are collectively asking for, without reading every note. This reframes the self-hosted LLM from a privacy accommodation into a **participant voice pipeline** — a direct channel from participants to agency leadership, with AI doing the aggregation that would otherwise require hours of manual review.

`client_words` and `participant_reflection` are not in scope for self-hosting. They remain on the existing OpenRouter path via the current insights feature.

**Output: qualitative theme tagging.** The LLM tags each suggestion with themes from a predefined list (e.g., "scheduling," "location," "peer support"). Tags are used only in aggregate reporting — never surfaced at the individual participant level. This avoids creating new personal health information records. Open-ended interpretation and sentiment analysis were considered and rejected (methodological risk, Campbell's Law concerns).

### Recommended model

**Qwen3.5-35B-A3B** (February 2026). 35B total parameters, 3B active per forward pass (Mixture-of-Experts with 256 experts, top-9 routing). Apache 2.0 licensed. Benchmarks above Qwen3-235B-A22B despite far lower compute requirements. The 3B active parameters make CPU inference viable — no GPU required at KoNote's volume.

Re-evaluate model choice at implementation time. The architecture is model-agnostic — swapping models in Ollama requires no code changes.

### Recommended hosting: OVHcloud Beauharnois, QC

**Host:** OVHcloud Beauharnois, Quebec (region `ca-east-bhs`). ~90,000 servers, powered by Quebec hydroelectricity.

**Why OVHcloud:** OVH Groupe SA is French-incorporated (Euronext Paris). OVH Canada (OVH Hébergement Inc.) is a Canadian subsidiary of the French parent. The US CLOUD Act applies to OVH US (a separate, independent subsidiary) but **not** to OVH Canada or OVH France. This provides meaningful protection against the specific threat KoNote addresses: US government access to Canadian health data.

**Why not US-incorporated providers:** The CLOUD Act applies to US-incorporated companies regardless of where their data centres are located. DigitalOcean (Toronto DC), AWS (Montreal DC), and Azure (Canada Central) are all subject to US government data requests even for data stored in Canada.

**Canadian court jurisdiction:** In September 2025, an Ontario court ordered OVH Canada to produce subscriber data for the RCMP. This demonstrates that Canadian authorities can compel OVH Canada to produce data. For KoNote's threat model, this is expected — Canadian law enforcement jurisdiction over Canadian data is normal. However, for agencies serving populations with concerns about Canadian law enforcement (e.g., undocumented newcomers), this risk profile is different and should be discussed during the Agency Permissions Interview.

### Architecture

- Self-host only for suggestion analysis (gated by the `ai_assist_participant_data` toggle)
- Keep Claude via OpenRouter for translation and `ai_assist_tools_only` features — no privacy benefit to self-hosting those, and Claude produces higher quality results for nuanced translation, SMART goal formulation, and CIDS taxonomy mapping
- **Shared inference endpoint:** one OVHcloud VPS serves all agencies (~$10–15 CAD/agency/month for 10 agencies). KoNote manages the infrastructure, not individual agencies. Separate processing queues per agency — no cross-agency data mixing.
- **Nightly batch processing** via cron/Celery with email alerts on failure. Not real-time per-note analysis.
- The existing `INSIGHTS_API_BASE` environment variable already routes to a local Ollama endpoint — near-zero code change for the routing itself

### Code constraint to address at implementation time

`collect_quotes()` in `insights.py` fills 30 shared slots with `client_words` first (lines 249–292). Suggestions only get remaining space (lines 337–354). In a program with 30+ substantive `client_words` entries, zero suggestions reach the LLM. A suggestions-only collection path is needed so suggestions aren't crowded out by other quote types.

### Cost estimate

| Tier | Monthly cost | Per-agency (10 agencies) | Notes |
|------|-------------|------------------------|-------|
| CPU-only shared VPS (64 GB RAM) | ~$100–150 CAD | ~$10–15 CAD | Recommended starting point |
| GPU cloud L4 (24 GB VRAM) | ~$634 CAD | ~$63 CAD | If available in BHS — verify with OVHcloud sales |
| Dedicated GPU (Scale-GPU-1, 2× L4) | ~$1,400–1,500 CAD | ~$140–150 CAD | Overkill at current volume |

### Capacity estimate (10 agencies × 200 participants × 2 visits/month)

- ~4,000 notes/month, ~25% have suggestions = **~1,000 suggestions/month**
- ~800 tokens per LLM call (system prompt + suggestion text + theme tag response)
- ~800K tokens/month total
- **~1–2 hours of CPU inference/month** via nightly batch
- Comfortable headroom on a single 64 GB RAM VPS

### Risks to monitor

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agency boards object to "AI reading participant suggestions" | Medium | High | Clear governance documentation, opt-in via toggle, aggregate-only output |
| CPU inference too slow at higher volumes | Low | Medium | Upgrade to GPU tier ($634/mo) or optimise batching |
| OVHcloud discontinues BHS services | Low | Medium | Architecture is provider-agnostic (any Ollama host works) |
| Qwen3.5-35B-A3B superseded by better model | High | Low | Swap model in Ollama, no code changes |
| Theme tags create new PHI obligations | Medium | High | Aggregate-only design — never surface at individual participant level |

### When to build

After the first agency deployment, when real data sovereignty requirements are articulated by a specific partner. Do not build speculatively. The toggle design and `INSIGHTS_API_BASE` routing already support the switch — implementation is primarily infrastructure setup, not application code.

## Migration Notes

1. Rename existing `ai_assist` toggle key to `ai_assist_tools_only` in `DEFAULT_FEATURES`
2. Change default from disabled to **enabled**
3. Add `ai_assist_participant_data` as new toggle with dependency on `ai_assist_tools_only`
4. Update `ai_views.py`: insights endpoint checks `ai_assist_participant_data` instead of `ai_assist`
5. Update all other AI view endpoints to check `ai_assist_tools_only`
6. Update templates referencing `features.ai_assist` to `features.ai_assist_tools_only`
7. Data migration: if an agency had `ai_assist = True`, set both new toggles to True to preserve their current behaviour

## GK Review Items

- [ ] Participant-facing transparency wording (portal statement)
- [ ] Confirmation modal text for `ai_assist_participant_data`
- [ ] Whether the tools-only default of "enabled" aligns with agency onboarding expectations
