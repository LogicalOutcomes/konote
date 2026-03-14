# KoNote Deployment Guide

This page helps you find the right deployment document for your situation. **OVHcloud Beauharnois (QC) is the recommended hosting platform** for most agencies — it's 60-70% cheaper than Azure and provides stronger data sovereignty.

## Which Guide Do I Need?

| I want to... | Read this | Time |
|---|---|---|
| **Understand deployment options and costs** | [Deployment Planning skill](/deployment-planning) or `tasks/hosting-cost-comparison.md` | 10 min |
| **Deploy KoNote on OVHcloud (recommended)** | [deploy-ovhcloud.md](deploy-ovhcloud.md) | 45-90 min |
| **Deploy KoNote on Azure** | [deploy-azure.md](archive/deploy-azure.md) (archived — for agencies that require Azure) | 1-2 hrs |
| **Set up the self-hosted LLM server** | [llm-deployment-guide.md](llm-deployment-guide.md) (for AI assistants) | 30 min |
| **Update an existing instance** | `konote-ops/deployment/update-checklist.md` | 15 min |
| **Troubleshoot a deployment problem** | `konote-ops/deployment/runbook.md` | varies |
| **Migrate to a new VPS** | `konote-ops/deployment/vps-migration-runbook.md` | 2-4 hrs |
| **Understand the onboarding process** | `tasks/deployment-protocol.md` | 20 min |
| **Review cost assumptions** | `tasks/hosting-cost-comparison.md` (primary source) | 15 min |
| **See client-facing budget figures** | `konote-prosper-canada/deliverables/hosting-budget-scenarios.md` | 10 min |
| **Run cost scenarios** | `konote-prosper-canada/deliverables/tools/costing-model-calculator.html` (browser) | 5 min |

## Deployment Tiers

KoNote supports three deployment tiers. All maintain the same data isolation and encryption guarantees.

| Tier | Who | Monthly Cost | Key Feature |
|---|---|---|---|
| **1. Self-hosted** | Agencies with technical capacity | ~$15/mo (VPS only) | Cheapest. Secure by default via built-in encryption. |
| **2. Managed OVHcloud** (recommended) | Most agencies | ~$65-92/agency | LO manages infrastructure. Shared monitoring, isolated data. |
| **3. Azure** | Agencies requiring Azure | ~$77-169/agency | Azure managed services. Higher cost, US CLOUD Act trade-off. |

See the `/deployment-planning` skill for full tier descriptions and the cost source chain.

## Key Principles

- **Every agency's data is isolated.** Agencies never share a database, encryption key, or KoNote instance — even when sharing a VPS.
- **OVHcloud is preferred** for cost and data sovereignty. Azure is supported but not the default.
- **Cost figures live in `tasks/hosting-cost-comparison.md`** (primary source). All other cost docs derive from it via a documented source chain.

## Architecture Decisions

Major deployment decisions are recorded in Design Rationale Records (DRRs). Read these before proposing changes:

- `tasks/design-rationale/ovhcloud-deployment.md` — hosting stack, self-healing, backups
- `tasks/design-rationale/multi-tenancy.md` — schema-per-tenant isolation
- `tasks/design-rationale/data-access-residency-policy.md` — data sovereignty, CLOUD Act
- `tasks/design-rationale/self-hosted-llm-infrastructure.md` — AI hosting

Use the `design-rationale` skill to check proposals against these DRRs.
