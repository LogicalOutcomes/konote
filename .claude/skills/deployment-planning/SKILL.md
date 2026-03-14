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
- Single-tenant currently; multi-tenant planned (would reduce hosting cost)

### Onboarding Cost

One-time per agency: $800-$2,200 depending on size. See `hosting-budget-scenarios.md` Section "One-Time Onboarding Costs".

## How to Update Cost Assumptions

1. Read `tasks/hosting-cost-comparison.md` (the primary source)
2. Make changes there first
3. Run `python konote-prosper-canada/deliverables/tools/costing-model-calculator.py` to regenerate figures
4. Update downstream files: `p0-managed-service-plan.md` -> `costing-model.md` -> `hosting-budget-scenarios.md`
5. Bump `COST_VERSION` date in each updated file
6. Note cross-repo updates needed in commit messages
