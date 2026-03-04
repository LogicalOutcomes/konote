# Hosting Cost Comparison: Azure vs OVHcloud

*Last updated: 2026-03-04*

This document compares two hosting approaches for KoNote, both using Azure Key Vault for encryption key management. All prices are estimates in CAD unless noted. Verify current prices with provider pricing calculators before committing.

**Related:** [OVHcloud deployment architecture](design-rationale/ovhcloud-deployment.md) — full deployment stack, self-healing automation, backup strategy, and encryption key management.

---

## Assumptions

| Parameter | Value |
|-----------|-------|
| Participants per agency | ~200 |
| Visits per participant per month | ~2 |
| Notes per month per agency | ~400 |
| Notes with suggestions (~25%) | ~100 |
| Translation requests per month | ~50–100 (admin-initiated) |
| Metrics/targets AI calls per month | ~100–200 |
| Multi-tenancy status | Single-tenant now; schema-per-tenant planned (see TODO MT-CORE1) |
| Exchange rate used | 1 USD = 1.43 CAD (approximate) |

---

## Component Pricing Reference

### Azure Virtual Machines — Canada Central (Linux, pay-as-you-go)

| VM Size | vCPUs | RAM | Price (USD/hr) | Price (CAD/mo) |
|---------|-------|-----|----------------|----------------|
| B2s | 2 | 4 GB | ~$0.053 | ~$55 |
| B2ms | 2 | 8 GB | ~$0.083 | ~$87 |
| B4ms | 4 | 16 GB | ~$0.185 | ~$194 |
| D2as v5 | 2 | 8 GB | ~$0.096 | ~$100 |

*Source: [Azure Pricing Calculator](https://azure.microsoft.com/en-ca/pricing/calculator/), [CloudOptimo](https://costcalc.cloudoptimo.com/azure-pricing-calculator/vm/Standard-B4ms). Canada Central is typically 10–15% above cheapest US regions.*

### Azure Database for PostgreSQL — Flexible Server (pay-as-you-go)

| SKU | vCores | RAM | Price (USD/mo) | Price (CAD/mo) |
|-----|--------|-----|----------------|----------------|
| B1ms (Burstable) | 1 | 2 GB | ~$12 | ~$17 |
| B2s (Burstable) | 2 | 4 GB | ~$25 | ~$36 |
| B2ms (Burstable) | 2 | 8 GB | ~$50 | ~$72 |
| D2s v5 (General Purpose) | 2 | 8 GB | ~$100 | ~$143 |
| Storage | — | — | $0.115 USD/GiB/mo | $0.16 CAD/GiB/mo |

*KoNote requires 2 databases (main + audit). Burstable tier is appropriate for small agencies. Source: [Azure PostgreSQL pricing](https://azure.microsoft.com/en-ca/pricing/details/postgresql/flexible-server/), [Neon cost comparison](https://dev.to/bobur/cost-comparison-neon-vs-azure-database-for-postgresql-flexible-server-2lpp).*

### Azure Key Vault (Standard tier)

| Item | Price |
|------|-------|
| Secret operations | $0.03 USD per 10,000 operations |
| Key operations | $0.03 USD per 10,000 operations |
| Setup fee | None |
| Typical monthly cost | **~$1–5 CAD** |

*KoNote uses Key Vault for `FIELD_ENCRYPTION_KEY` storage. Low operation volume = negligible cost. Source: [Azure Key Vault pricing](https://azure.microsoft.com/en-us/pricing/details/key-vault/), [Infisical pricing guide](https://infisical.com/blog/azure-key-vault-pricing).*

### OVHcloud VPS — Beauharnois, QC (VPS 2026 range)

| Plan | vCores | RAM | Storage | Price (CAD/mo) |
|------|--------|-----|---------|----------------|
| VPS-1 | 4 | 8 GB | 75 GB NVMe | ~$11 |
| VPS-2 | 4 | 16 GB | 100 GB NVMe | ~$22 |
| VPS-3 | 8 | 24 GB | 200 GB NVMe | ~$30 |
| VPS-4 | 8 | 32 GB | 200 GB NVMe | ~$44 |
| VPS-6 | 24 | 96 GB | 400 GB NVMe | ~$105 |

*Prices estimated from VPSBenchmarks and OVHcloud configurator. Post-April 2026 pricing (VPS-1 base = US$7.60). All plans include unlimited traffic. OVH parent is French-incorporated (OVH Groupe SA) — not subject to US CLOUD Act. Source: [OVHcloud Canada VPS](https://www.ovhcloud.com/en-ca/vps/), [VPSBenchmarks](https://www.vpsbenchmarks.com/compare/ovhcloud).*

### AI API Costs (OpenRouter / Claude)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Use Case |
|-------|----------------------|------------------------|----------|
| Claude Haiku 4.5 | $1.00 USD | $5.00 USD | Translation |
| Claude Sonnet 4.5 | $3.00 USD | $15.00 USD | Metrics/targets generation |
| gpt-4o-mini (current) | $0.15 USD | $0.60 USD | Translation (current default) |

*Source: [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [OpenRouter pricing](https://openrouter.ai/pricing).*

### Self-Hosted LLM (Suggestion Theme Tagging)

| Item | Detail |
|------|--------|
| Model | Qwen3.5-35B-A3B (35B params, 3B active, MoE, Apache 2.0) |
| Runtime | Ollama, CPU-only, nightly batch |
| Hosting | OVHcloud Beauharnois VPS (shared endpoint) |
| Tokens per suggestion call | ~800 (prompt + suggestion + response) |
| Volume (10 agencies) | ~1,000 suggestions/month = ~800K tokens/month |
| Inference time (CPU) | ~1–2 hours/month |

*See [tasks/design-rationale/ai-feature-toggles.md](tasks/design-rationale/ai-feature-toggles.md) for full analysis.*

### Railway (Current Hosting — for comparison)

| Component | Price (USD/mo) | Price (CAD/mo) |
|-----------|----------------|----------------|
| Pro plan base | $5 | ~$7 |
| Django app (usage) | ~$15–25 | ~$21–36 |
| 2x PostgreSQL (usage) | ~$10–20 | ~$14–29 |
| **Total** | **~$30–50** | **~$42–72** |

*Railway hosts in US regions only. US-incorporated. Not appropriate for PHIPA data sovereignty requirements. Source: [Railway pricing](https://railway.app/pricing).*

---

## Scenario A: Azure Hosting (Canada Central)

KoNote application and databases on Azure Canada Central. Self-hosted LLM on OVHcloud (data sovereignty for participant suggestions). Azure Key Vault for encryption keys.

### Per-Agency Costs — Single Tenant

| Component | 1 Agency | Notes |
|-----------|----------|-------|
| Azure VM (B2s) | $55 | Django + Gunicorn + Caddy |
| Azure PostgreSQL x2 (B1ms) | $34 | Main + audit databases |
| PostgreSQL storage (20 GB) | $3 | 10 GB each, grows slowly |
| Azure Key Vault | $2 | Negligible operation volume |
| OpenRouter AI (translation) | $2 | ~100 calls/mo × gpt-4o-mini |
| OpenRouter AI (metrics/targets) | $5 | ~200 calls/mo × Sonnet 4.5 |
| OVHcloud VPS share (LLM) | $11 | 1/N share of shared VPS-1 |
| **Total per agency** | **~$112** | |

### Multi-Agency Scaling — Single Tenant (one VM + DB per agency)

| Component | 1 Agency | 5 Agencies | 10 Agencies |
|-----------|----------|------------|-------------|
| Azure VMs (B2s each) | $55 | $275 | $550 |
| Azure PostgreSQL x2 per agency (B1ms) | $34 | $170 | $340 |
| PostgreSQL storage | $3 | $15 | $30 |
| Azure Key Vault (shared) | $2 | $2 | $2 |
| OpenRouter AI (shared pool) | $7 | $35 | $70 |
| OVHcloud LLM VPS (shared) | $11 | $11 | $30 |
| **Total** | **$112** | **$508** | **$1,022** |
| **Per agency** | **$112** | **$102** | **$102** |

### Multi-Agency Scaling — Multi-Tenant (shared infrastructure)

*Requires django-tenants implementation (see TODO MT-CORE1). One VM + DB serves multiple agencies via schema-per-tenant.*

| Component | 1 Agency | 5 Agencies | 10 Agencies |
|-----------|----------|------------|-------------|
| Azure VM (B4ms shared) | $194 | $194 | $194 |
| Azure PostgreSQL x2 (B2ms shared) | $144 | $144 | $144 |
| PostgreSQL storage (100 GB) | $16 | $16 | $16 |
| Azure Key Vault (shared) | $2 | $2 | $2 |
| OpenRouter AI (shared pool) | $7 | $35 | $70 |
| OVHcloud LLM VPS (shared) | $11 | $11 | $30 |
| **Total** | **$374** | **$402** | **$456** |
| **Per agency** | **$374** | **$80** | **$46** |

---

## Scenario B: OVHcloud Hosting (Beauharnois, QC)

KoNote application, databases, and LLM all on OVHcloud VPS(es) in Beauharnois. Self-managed PostgreSQL via Docker. Azure Key Vault for encryption keys (only Azure dependency).

### Per-Agency Costs — Single Tenant

| Component | 1 Agency | Notes |
|-----------|----------|-------|
| OVHcloud VPS-2 | $22 | Django + PostgreSQL x2 + Caddy |
| Azure Key Vault | $2 | Encryption key management |
| OpenRouter AI (translation) | $2 | ~100 calls/mo × gpt-4o-mini |
| OpenRouter AI (metrics/targets) | $5 | ~200 calls/mo × Sonnet 4.5 |
| OVHcloud LLM VPS share | $11 | 1/N share of shared VPS-1 |
| Automated backups (OVH option) | $3 | Optional add-on |
| **Total per agency** | **~$45** | |

### Multi-Agency Scaling — Single Tenant (one VPS per agency)

| Component | 1 Agency | 5 Agencies | 10 Agencies |
|-----------|----------|------------|-------------|
| OVHcloud VPS-2 per agency | $22 | $110 | $220 |
| Azure Key Vault (shared) | $2 | $2 | $2 |
| OpenRouter AI (shared pool) | $7 | $35 | $70 |
| OVHcloud LLM VPS (shared) | $11 | $11 | $30 |
| Backup add-ons | $3 | $15 | $30 |
| **Total** | **$45** | **$173** | **$352** |
| **Per agency** | **$45** | **$35** | **$35** |

### Multi-Agency Scaling — Multi-Tenant (shared infrastructure)

*Requires django-tenants implementation (see TODO MT-CORE1). One larger VPS serves multiple agencies. LLM runs on the same or separate VPS.*

| Component | 1 Agency | 5 Agencies | 10 Agencies |
|-----------|----------|------------|-------------|
| OVHcloud VPS-3 (shared app + DB) | $30 | $30 | $30 |
| OVHcloud VPS-1 (LLM, shared) | $11 | $11 | $11 |
| Azure Key Vault (shared) | $2 | $2 | $2 |
| OpenRouter AI (shared pool) | $7 | $35 | $70 |
| Backup add-ons | $3 | $3 | $3 |
| **Total** | **$53** | **$81** | **$116** |
| **Per agency** | **$53** | **$16** | **$12** |

*At 10+ agencies, consider upgrading to VPS-4 ($44) for headroom. LLM VPS can stay on VPS-1 — the batch load is minimal.*

---

## Summary Comparison

**Supporting documents for technical review:**
- [OVHcloud deployment architecture](design-rationale/ovhcloud-deployment.md) — full stack, self-healing layers, backup strategy, encryption key management, automation roadmap
- [Self-hosted LLM infrastructure](design-rationale/self-hosted-llm-infrastructure.md) — Ollama endpoint, model selection, batch processing, provider consolidation path
- [Managed service plan](p0-managed-service-plan.md) — service model, support tiers, deployment protocol, scaling plan
- [Deployment guide](../docs/deploy-ovhcloud.md) — step-by-step OVHcloud VPS deployment (automated + manual paths)
- [Data access residency policy](design-rationale/data-access-residency-policy.md) — access tiers, Canadian residency requirements
- [Multi-tenancy architecture](design-rationale/multi-tenancy.md) — schema-per-tenant design for multi-agency hosting

### Per-Agency Monthly Cost (CAD)

| Scale | Azure Single-Tenant | Azure Multi-Tenant | OVH Single-Tenant | OVH Multi-Tenant |
|-------|--------------------|--------------------|--------------------|--------------------|
| 1 agency | $112 | $374* | $45 | $53* |
| 5 agencies | $102 | $80 | $35 | $16 |
| 10 agencies | $102 | $46 | $35 | $12 |

*\*Multi-tenant with 1 agency is more expensive due to the larger shared VM — cost advantage kicks in at 3+ agencies.*

### Total Monthly Cost (CAD)

| Scale | Azure Single-Tenant | Azure Multi-Tenant | OVH Single-Tenant | OVH Multi-Tenant |
|-------|--------------------|--------------------|--------------------|--------------------|
| 1 agency | $112 | $374 | $45 | $53 |
| 5 agencies | $508 | $402 | $173 | $81 |
| 10 agencies | $1,022 | $456 | $352 | $116 |

---

## AI Costs Breakdown (included in totals above)

These costs apply to both Azure and OVHcloud hosting scenarios.

### Translation (French)

| Model | Cost per call | Calls/mo (10 agencies) | Monthly (CAD) |
|-------|--------------|------------------------|---------------|
| gpt-4o-mini (current) | ~$0.001 | ~1,000 | ~$1.50 |
| Claude Haiku 4.5 | ~$0.005 | ~1,000 | ~$7 |

*Translation uses `TRANSLATE_API_BASE` env var. Currently defaults to gpt-4o-mini. Minimal cost either way.*

### Metrics/Targets Generation

| Model | Cost per call | Calls/mo (10 agencies) | Monthly (CAD) |
|-------|--------------|------------------------|---------------|
| Claude Sonnet 4.5 (via OpenRouter) | ~$0.03 | ~2,000 | ~$86 |
| Claude Haiku 4.5 | ~$0.005 | ~2,000 | ~$14 |

*Currently hardcoded to OpenRouter. Quality-sensitive — Sonnet recommended. At high volume, consider Haiku for routine calls and Sonnet for complex ones.*

### Suggestion Theme Tagging (Self-Hosted LLM)

| Item | Value |
|------|-------|
| Model | Qwen3.5-35B-A3B on Ollama |
| Hosting | OVHcloud VPS-1 ($11 CAD/mo shared) |
| Volume (10 agencies) | ~1,000 suggestions/month |
| CPU inference time | ~1–2 hours/month (nightly batch) |
| Per-agency cost (10 agencies) | ~$1.10 CAD/mo |
| API cost | $0 (self-hosted, Apache 2.0 licence) |

---

## Data Sovereignty Comparison

| Factor | Azure (Canada Central) | OVHcloud (Beauharnois, QC) |
|--------|----------------------|--------------------------|
| Parent company | Microsoft (US-incorporated) | OVH Groupe SA (French-incorporated) |
| US CLOUD Act exposure | **Yes** — US govt can compel disclosure | **No** — French parent not subject |
| Canadian law enforcement | Yes (normal, expected) | Yes (Sept 2025 Ontario court ruling) |
| Data residency | Canada Central (Toronto) | Beauharnois, QC |
| PHIPA compliance | Yes (Azure compliance docs) | Yes (self-managed compliance) |
| SOC 2 / ISO 27001 | Yes (Azure certifications) | Yes (OVHcloud certifications) |
| Managed services | Full PaaS (DB, Key Vault, monitoring) | VPS only — self-manage DB, backups |

### Azure Key Vault Dependency (Both Scenarios)

Both scenarios use Azure Key Vault for encryption key management. This introduces a limited Azure dependency:

- **Data at risk**: Only the encryption key itself, not participant data
- **CLOUD Act exposure**: Theoretical — US govt could compel Microsoft to reveal the encryption key, which would allow decryption of KoNote data stored elsewhere
- **Mitigation**: Key Vault access is authenticated and audited. The encryption key alone is useless without access to the encrypted database.
- **Alternative**: If zero Azure dependency is required, consider HashiCorp Vault (self-hosted on OVHcloud) or manual key custody with two-person split

---

## Operational Considerations

### Azure Hosting

| Pro | Con |
|-----|-----|
| Managed PostgreSQL (automated backups, patching, HA) | Higher cost (~2–3x OVHcloud) |
| Azure Monitor, alerts, diagnostics built in | US CLOUD Act exposure on all components |
| SLA-backed uptime (99.9%+) | Vendor lock-in risk |
| Easy scaling (resize VM, add replicas) | Overkill for small nonprofit workloads |

### OVHcloud Hosting

| Pro | Con |
|-----|-----|
| 60–70% lower cost than Azure | Self-managed PostgreSQL (backups, patching, monitoring) |
| No US CLOUD Act exposure on application data | No managed database service in BHS for PostgreSQL |
| Can run app + DB + LLM on one VPS | Single point of failure without HA setup |
| French data sovereignty (GDPR-aligned parent) | Less tooling than Azure (monitoring, alerting) |

### Self-Healing Automation (OVHcloud)

To address the self-managed operations gap, a 4-layer automated recovery stack is recommended:

1. **Docker HEALTHCHECK + autoheal** — auto-restart failed containers (~$0)
2. **UptimeRobot → OVHcloud API webhook** — reboot VPS on extended downtime (~$0)
3. **Preventive cron jobs** — nightly backups, log rotation, disk monitoring (~$0)
4. **Email alerts** — escalation to KoNote team on unrecoverable failures (~$0)

Total automation cost: ~$0 additional (uses free tiers of monitoring services).

---

## Recommendations

1. **For 1–3 agencies (launch phase)**: OVHcloud single-tenant is the clear winner at ~$45/agency/month vs ~$112 on Azure. Self-managed PostgreSQL is acceptable at this scale.

2. **For 5–10 agencies (growth phase)**: Implement multi-tenancy first (MT-CORE1), then OVHcloud multi-tenant brings costs to $12–16/agency/month — an order of magnitude cheaper than Azure single-tenant.

3. **Azure makes sense if**: The agency or funder requires Azure specifically, or if the operational burden of self-managing PostgreSQL is unacceptable.

4. **LLM hosting**: Keep on OVHcloud regardless of app hosting choice. The self-hosted Ollama VPS is $11 CAD/month shared across all agencies — negligible cost for complete data sovereignty on participant suggestions.

5. **Key Vault**: Use Azure Key Vault in both scenarios. The CLOUD Act exposure is limited to the encryption key only, and the operational simplicity of managed KMS outweighs the theoretical risk for KoNote's threat model.

---

## Technical Support Cost Estimates

The 4-layer self-healing automation (see [OVHcloud deployment DRR](design-rationale/ovhcloud-deployment.md)) eliminates most routine operational work. This section estimates the remaining human support burden at each scale.

### What Self-Healing Handles Automatically (~$0)

| Task | Before automation | After automation |
|------|-------------------|------------------|
| Container crash recovery | Manual SSH + restart | Autoheal restarts in 30–90 seconds |
| VPS-level outage | Manual detection + reboot | UptimeRobot triggers API reboot in 15–20 min |
| Nightly database backups | Manual cron setup per VPS | Ops sidecar runs automatically with `docker compose up` |
| Disk space monitoring | Manual checks | Hourly automated check with email alerts |
| Docker image cleanup | Manual | Weekly automated prune |
| Backup integrity verification | Manual monthly restore | Weekly automated test restore |
| Daily health status | Manual spot checks | Daily health report email at 7 AM |
| Log rotation | Manual logrotate config | Docker json-file driver with size limits |
| Dead man's switch (missed backups) | None | Healthchecks.io/UptimeRobot push monitor |
| OS security patches | Manual apt upgrade | unattended-upgrades (automatic) |

### Remaining Human Support Tasks

These are the tasks that still require a person. Estimated hours assume OVHcloud hosting with the full self-healing stack.

| Task | Frequency | Est. hours | Notes |
|------|-----------|------------|-------|
| Review health report emails | Daily (2 min) | 1 hr/mo | Scan for anomalies, mostly no action needed |
| Apply KoNote software updates | 1–2×/month | 1 hr/mo | `git pull` + `docker compose up -d --build` |
| Investigate escalation alerts | ~1×/month | 0.5 hr/mo | Layer 4 alerts that self-healing couldn't resolve |
| Respond to agency support requests | As needed | 1–2 hr/mo | Config changes, user account issues, questions |
| Quarterly security review | 1×/quarter | 1 hr/quarter | Check CVEs, review access logs, rotate secrets |
| Azure AD client secret renewal | 1×/year per agency | 0.5 hr/year | Calendar reminder set during deployment |
| VPS capacity review | 1×/quarter | 0.5 hr/quarter | Check resource usage trends, plan upgrades |
| **Total (1 agency)** | | **~4–5 hr/mo** | |
| **Total (5 agencies, single-tenant)** | | **~8–12 hr/mo** | Some tasks scale per-agency, others are fixed |
| **Total (10 agencies, multi-tenant)** | | **~10–15 hr/mo** | Multi-tenant reduces per-agency overhead |

### Tech Support Cost by Scale (CAD/month)

These costs supplement the infrastructure costs in the tables above. They represent the human operational burden.

| Scale | Support model | Fixed cost | Variable cost | Total support cost | Per agency |
|-------|--------------|------------|---------------|-------------------|------------|
| 1–2 agencies | KoNote team (internal) | $0 | Internal time (~5 hr/mo) | $0 (absorbed) | $0 |
| 3–5 agencies | KoNote team + freelance sysadmin on-call | $75/mo retainer | ~$75–125/hr if called | ~$75–150/mo | ~$15–30 |
| 5–10 agencies (single-tenant) | Freelance sysadmin retainer | $100–150/mo | ~$75–125/hr if called | ~$100–250/mo | ~$10–25 |
| 5–10 agencies (multi-tenant) | Freelance sysadmin retainer | $100/mo | ~$75–125/hr if called | ~$100–200/mo | ~$10–20 |
| 10+ agencies | Canadian MSP | $300–500/mo | Included in retainer | ~$300–500/mo | ~$30–50 |

**Key insight:** At 1–5 agencies with full self-healing, a freelance sysadmin on retainer (~$75–150/mo) is sufficient. The MSP option ($300–500/mo) is only justified at 10+ agencies or if 24/7 SLA coverage is contractually required.

**Freelance billing model:** The retainer covers availability (responding to Layer 4 escalation alerts within a few hours). The hourly rate ($75–125/hr) applies to actual incident work beyond the retainer — e.g., if a hardware failure requires 2 hours of SSH troubleshooting and backup restoration. In a typical month with full self-healing, the retainer is the only cost (0–1 incidents requiring human intervention).

### All-In Per-Agency Cost (Infrastructure + Support)

Combines infrastructure costs from Scenario B (OVHcloud) with tech support estimates above.

| Scale | Infrastructure/agency | Support/agency | **All-in/agency** |
|-------|----------------------|----------------|-------------------|
| 1 agency | $45 | $0 (internal) | **$45** |
| 3 agencies (single-tenant) | $35 | ~$25 | **~$60** |
| 5 agencies (single-tenant) | $35 | ~$20 | **~$55** |
| 5 agencies (multi-tenant) | $16 | ~$20 | **~$36** |
| 10 agencies (multi-tenant) | $12 | ~$15 | **~$27** |

### Further Automation Opportunities

These automations could reduce the remaining 4–5 hr/month further. See the [automation roadmap](design-rationale/ovhcloud-deployment.md#automation-roadmap-reducing-tech-support-further) in the OVHcloud deployment DRR for implementation details.

| Automation | Reduces | Est. savings | Complexity |
|-----------|---------|-------------|------------|
| GitOps auto-update (Watchtower or webhook) | Manual update deploys | 1 hr/mo | Medium |
| Automated Django security advisory checks | Manual CVE review | 0.25 hr/quarter | Low |
| Agency self-service admin portal | Config change requests | 0.5–1 hr/mo | High |
| Automated capacity alerts with upgrade recommendations | Manual capacity review | 0.5 hr/quarter | Low |
| Consolidated multi-agency health dashboard | Per-agency health report review | 0.5 hr/mo at 5+ agencies | Medium |

---

## Price Verification

These estimates should be verified before budget commitments:

- **Azure**: [Azure Pricing Calculator](https://azure.microsoft.com/en-ca/pricing/calculator/) — set region to Canada Central, currency to CAD
- **OVHcloud**: [OVHcloud Canada VPS](https://www.ovhcloud.com/en-ca/vps/) — prices displayed in CAD
- **OpenRouter**: [OpenRouter Pricing](https://openrouter.ai/pricing) — per-model token rates
- **Azure Key Vault**: [Key Vault Pricing](https://azure.microsoft.com/en-us/pricing/details/key-vault/)
