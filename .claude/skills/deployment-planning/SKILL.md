---
name: deployment-planning
description: Use when anyone asks about KoNote hosting costs, deployment options, per-agency pricing, budget scenarios, cost assumptions, managed service model, Azure vs OVHcloud comparison, onboarding costs, or needs to update cost figures. Also use when a new developer or manager needs deployment context.
---

# Deployment Planning & Costing Reference

Answer questions about KoNote deployment options, hosting costs, and cost assumptions by reading the authoritative source documents listed below. Never guess figures — always read the current file.

## When to Use

- "How much does KoNote cost per agency?"
- "What are the hosting options?"
- "Why OVHcloud instead of Azure?"
- "Can you update the cost model for a new VPS price?"
- "What's the onboarding process for a new agency?"
- "Where's the costing calculator?"
- New developer/manager needs deployment context

## When NOT to Use

- **Running a deployment** — use `/deploy-to-vps` instead
- **Reviewing a code change against architectural decisions** — use the `design-rationale` skill instead (it has the full DRR review workflow)
- **Debugging a deployment failure** — use `konote-ops/deployment/runbook.md` directly

## Core Principle: Data Isolation

**Every agency's participant data is fully isolated.** Agencies never share a KoNote instance, database, or encryption key — even when they share hosting infrastructure. Multiple instances can run on the same VPS for cost and operational efficiency, but data never crosses instance boundaries.

This is enforced by:
- **Per-instance databases** — each agency has its own PostgreSQL databases (main + audit)
- **Per-agency encryption keys** — each agency's PII is encrypted with its own Fernet key, stored in a managed key service (Azure Key Vault or OVHcloud KMS)
- **Schema-per-tenant isolation** — when multi-tenancy is enabled, PostgreSQL schema boundaries prevent cross-agency queries (see `tasks/design-rationale/multi-tenancy.md`)
- **No shared participant tables** — row-level tenant isolation was explicitly rejected as an anti-pattern (one missed filter = data leak)

**This principle is non-negotiable.** Any deployment option that combines participant data across agencies violates PHIPA and KoNote's design rationale. See the `design-rationale` skill for the full DRR review process.

## Deployment Tiers

KoNote supports a range of deployment options, from bare-bones self-hosted to fully managed. All tiers maintain the same data isolation and encryption guarantees — the difference is who manages the infrastructure and what operational support is included.

### Tier 1: Self-Hosted (DIY)

**Who:** Nonprofits with technical capacity (or a volunteer/consultant) who want the lowest cost.

**What they get:** The open-source repo, deployment documentation, and Docker Compose stack. The agency deploys to their own VPS or server, manages their own backups, updates, and monitoring.

**Why it's secure enough:** KoNote's security is built into the application, not bolted on by the hosting layer:
- Fernet (AES-256) encryption on all PII fields at the application level
- Encryption key stored in a managed key service (not in `.env`)
- Docker healthchecks and autoheal for container recovery
- Caddy with automatic HTTPS (Let's Encrypt)
- Audit logs in a separate tamper-resistant database
- RBAC middleware enforcing role-based access on every request

**Cost:** VPS hosting only (~$15 CAD/mo for OVHcloud VPS-1). No LO support fees.

**Docs:** `docs/deploy-ovhcloud.md`, `docs/deploying-konote.md`

### Tier 2: Managed OVHcloud (Recommended)

**Who:** Most agencies. LO handles infrastructure; the agency focuses on using KoNote.

**What they get:** A fully hosted, maintained KoNote instance on OVHcloud Beauharnois (QC). LO provides setup, updates, backups, monitoring, and incident response.

**Shared infrastructure, isolated data:** Multiple agencies can run on the same bare VPS, sharing:
- Joint monitoring (UptimeRobot, health reports)
- 4-layer self-healing automation (Docker autoheal, VPS auto-reboot, preventive cron, human escalation)
- Shared LLM server for AI features (suggestions, translation)
- Operational efficiencies (one update cycle covers all instances on the VPS)

What is **never** shared: databases, encryption keys, application instances, participant data.

**Cost:** ~$92/agency/mo (5-agency network) to ~$65/agency/mo (30-agency network), Year 2+. See `hosting-budget-scenarios.md` for current figures.

**Docs:** `tasks/p0-managed-service-plan.md`, `tasks/deployment-protocol.md`

### Tier 3: Azure Hosting

**Who:** Agencies that require or prefer Azure — typically those with existing Microsoft agreements, Azure nonprofit grants, or specific compliance requirements.

**What they get:** Same KoNote application deployed on Azure VM with Azure-managed PostgreSQL, Azure Key Vault, and Azure Monitor. Higher cost but leverages the Azure ecosystem.

**Why choose Azure over OVHcloud:**
- Agency already has Azure nonprofit credits ($2,000 USD/year — often enough to cover KoNote hosting)
- Compliance requirements that specifically mandate a hyperscaler
- Preference for managed database services over self-managed PostgreSQL

**Trade-off:** Azure's parent company (Microsoft) is US-incorporated and subject to the US CLOUD Act. Data is in Canada (Toronto/Canada Central), but the corporate jurisdiction is American. See `tasks/design-rationale/data-access-residency-policy.md`.

**Cost:** ~$169/agency/mo (list price) or ~$77/agency/mo (with nonprofit grant). See `hosting-budget-scenarios.md`.

**Docs:** `docs/archive/deploy-azure.md` (archived but still accurate for Azure path)

### Optional Add-Ons (Any Tier)

| Service | Description | Availability |
|---------|-------------|-------------|
| **Penetration testing** | Third-party security audit of the agency's KoNote instance | On request, for agencies or networks willing to fund it |
| **Evaluation framework setup** | CIDS Full Tier configuration with impact model, counterfactuals, and reporting profiles | Per-program, requires evaluation interview (see `tasks/deployment-protocol.md` Interview 3) |
| **Self-hosted LLM** | Dedicated or shared Ollama server for AI suggestions and translation | Included in Tier 2; optional for Tier 1/3 |
| **Cross-agency reporting** | Aggregate reporting dashboard for funder networks (k>=5 cell suppression) | Requires consortium setup; see `tasks/design-rationale/cids-privacy-architecture.md` |

## Cross-Repo Paths

Files prefixed `konote-prosper-canada/` are in a **separate repo**. Locate it relative to the konote repo (typically `../konote-prosper-canada/` or search for it under the user's GitHub directory). Files prefixed `konote-ops/` are in the **private ops repo** (`../konote-ops/`).

## Document Inventory

Read the files relevant to the question. **Always start with the source-of-truth for the topic.**

### Cost & Pricing (read these for any cost question)

| File | Role | What it contains |
|------|------|-----------------|
| `tasks/hosting-cost-comparison.md` | **Primary source** — component pricing | Azure vs OVHcloud pricing tables, VPS tiers, AI costs, scenarios at 1/5/10 agencies, data sovereignty analysis |
| `tasks/p0-managed-service-plan.md` | Managed service model | What LO provides vs agency, support tiers, deployment protocol summary, scaling plan |
| `konote-prosper-canada/deliverables/costing-model.md` | Detailed scenarios | 5-agency and 30-agency network costing, support hour breakdowns, Azure vs OVHcloud per-agency |
| `konote-prosper-canada/deliverables/hosting-budget-scenarios.md` | Client-facing summary | Polished per-agency tables, onboarding costs, 3-year TCO, funding model options |

### Calculator (for running custom scenarios)

| File | How to use |
|------|-----------|
| `konote-prosper-canada/deliverables/tools/costing-model-calculator.py` | `python costing-model-calculator.py` — change assumptions at top of file, re-run for updated figures |
| `konote-prosper-canada/deliverables/tools/costing-model-calculator.html` | Open in browser — interactive version with sliders |

### Deployment Architecture & Rationale (DRRs)

| File | Governs |
|------|---------|
| `tasks/design-rationale/ovhcloud-deployment.md` | Full OVHcloud stack, 4-layer self-healing, backup strategy, encryption key management, VPS sizing, risk registry |
| `tasks/design-rationale/multi-tenancy.md` | Schema-per-tenant architecture — prerequisite for cost reduction at 5+ agencies |
| `tasks/design-rationale/data-access-residency-policy.md` | Canadian data residency, who can access production, CLOUD Act analysis |
| `tasks/design-rationale/self-hosted-llm-infrastructure.md` | Self-hosted LLM costing (Ollama + Qwen on shared VPS), why not cloud AI APIs |

### Deployment How-To Guides

| File | Purpose |
|------|---------|
| `docs/deploy-ovhcloud.md` | Step-by-step OVHcloud VPS deployment (16 steps, 45-90 min) |
| `docs/deploying-konote.md` | General deployment overview |
| `docs/deploy-dev-vps.md` | Dev/demo VPS setup |
| `docs/llm-deployment-guide.md` | Self-hosted LLM (Ollama) deployment |
| `docs/archive/deploy-azure.md` | Azure deployment (archived — for reference only) |

### Onboarding & Agreements

| File | Purpose |
|------|---------|
| `tasks/deployment-protocol.md` | 5-phase onboarding: Discovery -> Permissions -> Infrastructure -> Customisation -> Go-Live -> 30-Day Check-In |
| `tasks/deployment-workflow-design.md` | Workflow design for deployment process |
| `tasks/saas-service-agreement.md` | SaaS agreement template (required before first managed agency) |

### Operations (private repo)

| File | Purpose |
|------|---------|
| `konote-ops/deployment/runbook.md` | Deployment runbook, troubleshooting, checklists |
| `konote-ops/deployment/vps-migration-runbook.md` | VPS migration procedures |
| `konote-ops/deployment/hardening-guide.md` | VPS security hardening |
| `konote-ops/deployment/update-checklist.md` | Update verification checklist |
| `konote-ops/deployment/env-template.md` | Environment variable reference |

## Cost Source Chain

Cost data flows upstream to downstream. **When updating any cost file, reconcile from upstream first.**

```
tasks/hosting-cost-comparison.md          <-- PRIMARY SOURCE (component pricing)
        |
        v
tasks/p0-managed-service-plan.md          <-- managed service model
        |
        v
konote-prosper-canada/deliverables/costing-model.md    <-- detailed scenarios
        |
        v
konote-prosper-canada/deliverables/hosting-budget-scenarios.md  <-- client summary
konote-prosper-canada/deliverables/tools/costing-model-calculator.*  <-- calculator
```

Each file has a `<!-- COST_VERSION -->` header. Before updating, compare key values across the chain. If values don't match, reconcile upstream first, then cascade downstream.

**Cross-repo constraint:** `konote` and `konote-prosper-canada` cannot be updated in the same session. Note in the commit message which downstream files need updating.

## Quick Reference

### Per-Agency Monthly Cost (Year 2+, as of 2026-03-04)

| Network size | OVHcloud | Azure (list) | Azure (nonprofit grant) |
|---|---|---|---|
| 5 agencies | ~$92/agency | ~$169/agency | ~$77/agency |
| 30 agencies | ~$65/agency | ~$142/agency | ~$50/agency |

Key Vault is $2/agency/month (per-agency vault, not shared). These figures include Key Vault in the per-agency hosting cost.

**These figures change.** Always read `hosting-budget-scenarios.md` for current numbers.

### Why OVHcloud Over Azure

Read `tasks/design-rationale/ovhcloud-deployment.md` for the full analysis. Summary:
- **60-70% lower cost** than Azure
- **Not subject to US CLOUD Act** (OVH Groupe SA is French-incorporated)
- **Canadian data residency** (Beauharnois, QC data centre)
- **Exception:** Agencies with concerns about Canadian law enforcement may need Azure or a risk assessment

### Key Cost Assumptions

Read the `COST_VERSION` header in `tasks/hosting-cost-comparison.md` for current values. Key assumptions:
- ~200 participants/agency, ~2 visits/month
- All AI self-hosted (Qwen3.5 + NLLB-200) — $0 API costs
- Support at $100/hr, LLM-assisted (reduces human hours)
- Single-tenant currently; multi-tenant planned (would reduce hosting cost). Each agency has its own Azure Key Vault ($2/mo) for encryption key storage.

### Onboarding Cost

One-time per agency: $800-$2,200 depending on size. See `hosting-budget-scenarios.md` Section "One-Time Onboarding Costs".

## How to Update Cost Assumptions

1. Read `tasks/hosting-cost-comparison.md` (the primary source)
2. Make changes there first
3. Run `python konote-prosper-canada/deliverables/tools/costing-model-calculator.py` to regenerate figures
4. Update downstream files: `p0-managed-service-plan.md` -> `costing-model.md` -> `hosting-budget-scenarios.md`
5. Bump `COST_VERSION` date in each updated file
6. Note cross-repo updates needed in commit messages
