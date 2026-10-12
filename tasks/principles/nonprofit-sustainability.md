---
role: principle
status: Draft - awaiting GK review
source: foundation-nonprofit-sustainability.md (2026-03-14)
---

# Principle: Nonprofit Sustainability

**Affordable, Simple, and Evaluation-Ready**

> **In plain language:** KoNote is designed to be affordable for small nonprofits and simple enough to run without a dedicated IT team. It uses a deliberately simple tech stack, heals itself when things go wrong, and is built so that the data you collect actually feeds evaluation, reporting, and sector-wide learning — not just a filing cabinet.

---

## Core Principle

KoNote exists because nonprofits doing critical community work shouldn't need enterprise budgets or dedicated IT teams to track outcomes effectively. Every architectural choice — from the tech stack to the hosting model to the deployment automation — is made with a cost-conscious, non-technical operator in mind.

This is not about austerity. It is about **fitness for context**. Nonprofits operate with constrained budgets, high staff turnover, and limited technical capacity. A system that requires a dedicated DevOps engineer, a JavaScript build pipeline, or $500/month in cloud hosting is not a viable tool for a 5-person agency running employment programs. KoNote's architecture treats these constraints as design requirements, not limitations to work around later.

## Three Commitments

### 1. Minimal Complexity

Every added dependency, build tool, framework, and configuration layer is a maintenance burden that someone must carry. For a 5-person nonprofit, that burden falls on someone who is not primarily an engineer. The system is therefore built with **deliberately fewer moving parts** than a modern SaaS stack would recommend.

The specific constraints that implement this commitment (no JS framework, limited Python dependency count, Alpine base images) are enforced in `tech-stack-constraints.md`.

### 2. Cost-Conscious Hosting

Managed cloud services are priced for organisations that value convenience over cost. Nonprofits value cost over convenience. An unmanaged VPS with good automation is cheaper AND more transparent — you can see exactly what's running and why.

Multi-tenancy (schema-per-tenant) enables cost sharing without data sharing: one server can host 1-100 agencies, with PostgreSQL schema isolation ensuring no cross-agency access. Cost per agency drops as more join; the same architecture that reduces cost also enforces data sovereignty.

See `multi-tenancy.md`, `ovhcloud-deployment.md`, `self-hosted-llm-infrastructure.md` for the specific hosting decisions.

### 3. Self-Healing Operations

Nonprofits cannot afford 24/7 ops staff. The system must recover from common failures without human intervention:

- Docker restart policies and autoheal container for transient failures
- External uptime monitoring with API-triggered reboot for harder failures
- Cron-based backups, disk monitoring, health reporting
- Email alerts as the human escalation path of last resort

This is not a feature — it is a precondition for the system being usable by the intended operator.

## Built for Evaluation, Not Retrofitted

Data collection is not an afterthought bolted onto case management. It is built into the structure of every interaction, and it is designed to **feed evaluation**, not just filing.

The pipeline is: evaluation framework → metric configuration → daily data collection (progress notes with structured observations) → automatic aggregation (insights, themes) → executive dashboards → funder reports → consortium publishing → sector-wide learning. Each step feeds the next without re-entry.

This shapes several decisions:

- **Evaluation framework first.** The `EvaluationFramework` model (theory of change, outcome chain, risk analysis) configures what metrics exist and how they're measured. Configuration follows evaluation design, not the reverse.
- **Metrics carry full metadata.** Instrument, scoring bands, directionality, CIDS alignment, IRIS+ codes, SDG goals. A metric is an evaluation instrument, not just a number field.
- **CIDS alignment.** Metrics, programs, and demographics map to Common Approach taxonomy for sector-wide comparability. This matters at scale: when 50 agencies use KoNote, the sector can say "across Ontario, 68% of employment programs report positive outcomes for SDG 8."
- **Division of labour.** Frontline staff focus on the participant relationship. Taxonomy classification, metric configuration, and reporting structure are the evaluation lead's job — not the case worker's during a session.

## Managed Service Model

KoNote can be deployed in three models:

- **Self-managed** — agency runs its own VPS. Automation handles the hard parts.
- **Managed service** — an intermediary hosts multiple agencies. ~$15/agency/month infrastructure at 10-agency scale, plus support.
- **Consortium** — multiple agencies share infrastructure and aggregate reporting. Each retains data sovereignty.

**Anti-pattern:** pricing models affordable only at enterprise scale. KoNote must be affordable for a 5-person agency. If the cheapest option requires 50+ users to break even, small agencies are excluded by design.

## Guiding Tests for Proposed Features

1. **Can a 5-person agency run this without dedicated IT staff?** If no, the feature is misaligned.
2. **Does this increase the dependency surface, the build pipeline, or the operational burden?** If yes, the cost has to be argued for — not assumed.
3. **Does this connect to an evaluation framework, or is it data collection without purpose?** If it doesn't trace back to an outcome, it shouldn't exist.
4. **Does this make the cheapest tier viable for small agencies?** If it raises the floor, reject.

## When to Revisit

This principle should be revisited if:

- Nonprofit sector IT capacity significantly increases (shared SOC services, managed hosting co-ops emerge).
- The scale exceeds ~2,000 participants per agency, at which point the in-memory search (required by field-level encryption) needs re-architecture.
- Managed cloud pricing drops to parity with unmanaged VPS, removing the cost advantage of self-hosting.

The principle — affordable for small agencies with minimal IT — should not change. The specific implementation choices may evolve, but the constraints they serve are permanent features of the nonprofit sector.

---

## Implementation DRRs

- [tech-stack-constraints](../design-rationale/tech-stack-constraints.md) — no JS framework, dependency ceiling, Alpine base images (NEW)
- [multi-tenancy](../design-rationale/multi-tenancy.md) — schema-per-tenant for cost sharing + sovereignty
- [ovhcloud-deployment](../design-rationale/ovhcloud-deployment.md) — unmanaged VPS, self-healing, backup
- [self-hosted-llm-infrastructure](../design-rationale/self-hosted-llm-infrastructure.md) — shared Ollama, tenant isolation
- [reporting-architecture](../design-rationale/reporting-architecture.md) — template-driven reporting connecting evaluation to funders
- [cids-privacy-architecture](../design-rationale/cids-privacy-architecture.md) — three-layer compliance for sector reporting
- [funder-reporting-profiles](../design-rationale/funder-reporting-profiles.md) — funder-specific templates (Parking Lot)
- [cids-batch-classification-workflow](../design-rationale/cids-batch-classification-workflow.md) — admin-facing classification, not frontline
- [cids-metadata-assignment](../design-rationale/cids-metadata-assignment.md) — metadata at creation vs. deferred
- [bilingual-requirements](../design-rationale/bilingual-requirements.md) — bilingual as legal requirement

## Related Principles

- **Collaborative Practice** — the evaluation pipeline starts with collaborative goal-setting and ends with sector-wide learning
- **Data Sovereignty** — multi-tenancy serves both cost sharing AND schema isolation
- **Security by Default** — fewer dependencies = fewer security vulnerabilities; zero-config security is also zero-cost security
