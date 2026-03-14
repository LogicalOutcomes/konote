# Foundation: Nonprofit Sustainability

**Affordable, Simple, and Evaluation-Ready**

Status: Foundation Principle
Created: 2026-03-14

> **In plain language:** KoNote is designed to be affordable for small nonprofits and simple enough to run without a dedicated IT team. It uses a deliberately simple tech stack, heals itself when things go wrong, and is built so that the data you collect actually feeds evaluation, reporting, and sector-wide learning — not just a filing cabinet.

---

## Core Principle

KoNote exists because nonprofits doing critical community work shouldn't need enterprise budgets or dedicated IT teams to track outcomes effectively. Every architectural choice — from the tech stack to the hosting model to the deployment automation — is made with a cost-conscious, non-technical operator in mind. The system must be cheap enough that a small agency can afford it, simple enough that it can be maintained by a generalist, and evaluation-ready so that the data collected actually improves programs and satisfies funders.

This principle is not about austerity — it is about fitness for context. Nonprofits operate with constrained budgets, high staff turnover, and limited technical capacity. A system that requires a dedicated DevOps engineer, a JavaScript build pipeline, or $500/month in cloud hosting is not a viable tool for a 5-person agency running employment programs. KoNote's architecture treats these constraints as design requirements, not limitations to work around later.

---

## Minimal Tech Stack

### 1. No JavaScript Frameworks

Django server-rendered templates + HTMX + Pico CSS. No React, Vue, webpack, npm, or Node.js. The frontend is HTML that Django renders and HTMX makes interactive. This means: no JavaScript build pipeline, no node_modules (0 bytes vs 300+ MB), no transpilation, no bundling.

**Why:** Every added build tool is a maintenance burden. React introduces 100+ transitive dependencies. Each dependency is a potential security vulnerability and a point of failure during upgrades. Nonprofits don't need a SPA — they need forms that work.

**Anti-pattern:** "Let's use React for a richer UI." The marginal UX improvement doesn't justify the 10x increase in build complexity, dependency surface, and required expertise.

### 2. 46 Dependencies Total

The entire production stack is 46 Python packages. Compare to a typical Django + React project: 500+. Fewer dependencies = faster builds, simpler security scanning, fewer upgrade conflicts. Every dependency must justify its presence — there is no "add it now, evaluate it later."

### 3. Alpine-Based Containers

All Docker images use Alpine Linux (5-20 MB vs 300+ MB for Debian/Ubuntu). The ops sidecar (Dockerfile.ops) is 21 MB. Builds take seconds, not minutes. Smaller images mean faster deployments, less disk usage, and a smaller attack surface.

### 4. Configuration Over Code

~60 environment variables control deployment. Feature toggles (demo mode, auth mode, AI provider) work without code changes. `.env.example` is the documentation. An agency can switch from local auth to Azure SSO, enable or disable AI features, or change their terminology — all by editing environment variables. No code deployments required for configuration changes.

---

## Cost-Conscious Hosting

### 1. OVHcloud Over Azure

Single-tenant hosting costs ~$26 CAD/month on OVHcloud vs ~$132/month on Azure. Multi-tenant at 10 agencies: ~$13/agency/month vs ~$46/agency/month. OVHcloud is 60-70% cheaper because it's unmanaged VPS — the self-healing automation (described below) makes this safe. *(These figures are illustrative — for current pricing, see `tasks/hosting-cost-comparison.md`.)*

**Why not Azure/AWS by default?** Managed cloud services are priced for organisations that value convenience over cost. Nonprofits value cost over convenience. An unmanaged VPS with good automation is cheaper AND more transparent — you can see exactly what's running and why.

### 2. Multi-Tenancy for Cost Sharing

Schema-per-tenant (django-tenants) lets multiple agencies share one server without sharing data. PostgreSQL enforces isolation at the schema level. One VPS serves 1-100 agencies. Cost per agency drops as more join. No agency can see another's data, but they share compute, storage, and operational overhead.

### 3. Shared AI Server

One OVHcloud VPS (~$40 CAD/month) running Ollama serves all agencies. Qwen3.5-35B (MoE, only 3B active parameters per token) handles nightly theme processing. Cost per agency at 10 agencies: ~$4/month vs $27-68/month per-agency with cloud APIs. *(For current model selection and costs, see `tasks/hosting-cost-comparison.md`.)*

**Anti-pattern:** Per-agency AI deployment. At $400/month per agency for a dedicated LLM instance, AI features become inaccessible to small organisations. Shared infrastructure with tenant-level data isolation makes AI affordable for everyone.

---

## Self-Healing Operations

Nonprofits can't afford 24/7 ops staff. The system heals itself:

| Layer | Mechanism | Recovery Time |
|---|---|---|
| 1 | Docker restart policies + autoheal container | 30-90 seconds |
| 2 | UptimeRobot -> OVHcloud API webhook -> VPS reboot | 15-20 minutes |
| 3 | Ops sidecar cron (backups, disk monitoring, health reports) | Prevention |
| 4 | Email alerts to KoNote team | Escalation |

Operational burden: ~1-5 hours/month per agency (mostly reviewing reports), down from 10-15 hours without automation. The deploy script (`deploy.sh`) handles git pull, container rebuild, health checks, and migration failure detection in one command.

**Anti-pattern:** Requiring a sysadmin on-call. Nonprofits don't have one. The system must recover from common failures without human intervention.

---

## Managed Service Model

KoNote can be deployed in three models, each appropriate for different organisational capacities:

- **Self-managed**: Agency runs their own VPS. Docker Compose deployment, no vendor lock-in. Requires some technical comfort but no dedicated IT staff — the automation handles the hard parts.
- **Managed service**: A network or intermediary hosts multiple agencies. Published pricing at 10-agency scale: ~$15/agency/month (infrastructure) + support costs. The intermediary handles deployment and monitoring; agencies focus on service delivery.
- **Consortium**: Multiple agencies share infrastructure and aggregate reporting. Each agency retains data sovereignty — they choose what to publish and what stays private. Shared infrastructure reduces costs; shared reporting increases sector learning.

**Anti-pattern:** Pricing models that are affordable only at enterprise scale. KoNote must be affordable for a 5-person agency. If the cheapest option requires 50+ users to break even, small agencies are excluded by design.

---

## Built for Evaluation, Not Retrofitted

The system is designed so that an initial evaluation assessment feeds directly into how KoNote is configured. Data collection is not an afterthought bolted onto case management — it is built into the structure of every interaction. This section connects directly to the collaborative practice foundation — the evaluation pipeline starts with collaborative goal-setting (see Foundation: Collaborative Practice) and ends with sector-wide learning.

### 1. Evaluation Framework to Program Setup

The EvaluationFramework model stores the program's theory of change, outcome chain, and risk analysis. This feeds which metrics are configured, what measurement schedule is used, and what reporting structure applies. Configuration follows from evaluation design, not the reverse.

### 2. Metric Definitions with Full Metadata

Each metric carries standardised instrument info (PHQ-9, GAD-7), scoring bands, directionality, CIDS alignment, IRIS+ codes, SDG goals. A metric is not just a number field — it is an evaluation instrument with provenance and rationale. When a funder asks "what are you measuring and why?", the answer is embedded in the metric definition itself.

### 3. The Pipeline

Evaluation assessment -> metric configuration -> daily data collection (progress notes with structured observations) -> automatic aggregation (insights, trends, suggestion themes) -> executive dashboards -> funder reports -> consortium publishing -> sector-wide learning.

Each step feeds the next. Data collected in a progress note today appears in tonight's theme analysis, tomorrow's dashboard, and next quarter's funder report — without anyone re-entering it. In practice, this pipeline is iterative: metrics are refined after initial data collection, instruments may be replaced, and funder requirements change mid-grant. The architecture supports this through version-tracked metric definitions with append-only rationale logs.

### 4. CIDS Alignment

Metrics, programs, and demographics map to Common Approach (CIDS) taxonomy codes for sector-wide comparability. This matters at scale: when 50 agencies use KoNote and all map to CIDS, the sector can say "across Ontario, 68% of employment programs report positive outcomes for SDG 8." That's policy-level impact built from individual progress notes.

Classification happens through admin-facing batch workflows, not during frontline note-taking. The worker writing a note should never need to know what CIDS code applies — that mapping is the evaluation lead's job, done once per metric. This division of labour is deliberate: frontline staff focus on the participant relationship; the evaluator (or evaluation lead) configures frameworks, selects instruments, and manages taxonomy alignment.

**Anti-pattern:** Outcome tools that collect data but don't connect to evaluation methodology. Data without a theory of change is just noise. If a metric doesn't trace back to an outcome in the evaluation framework, it shouldn't exist. Equally: asking case workers to do taxonomy classification during a session is an anti-pattern — it burdens frontline staff with work that belongs to the evaluation function.

---

## Sector-Wide Learning

KoNote contributes to the broader nonprofit sector through:

- **CIDS exports**: Standardised data that can be compared across agencies using Common Approach codes. Agencies that use KoNote speak the same measurement language, even if their programs differ.
- **Consortium reporting**: De-identified aggregate snapshots published voluntarily by each agency. No agency is forced to share — but the infrastructure makes sharing easy when they choose to.
- **Funder reporting profiles**: Structured templates aligned to funder requirements (e.g., IRIS+, SDGs). Reporting is a configuration task, not a data entry task.
- **Open source**: The software itself is a contribution. Other nonprofits can adopt, adapt, and improve it. No vendor lock-in, no proprietary data formats.

**Anti-pattern:** Proprietary platforms where data format is vendor-locked and cross-agency comparison requires buying the same product. The sector learns faster when data is interoperable and tools are shared.

---

## Anti-Patterns Summary

| Anti-pattern | Why it's rejected |
|---|---|
| React / JavaScript framework | 10x build complexity for marginal UX gain |
| Enterprise cloud hosting (Azure/AWS default) | 3-5x cost; not necessary for this scale |
| Per-agency AI deployment | $400/month vs $4/month shared |
| 24/7 ops staff requirement | Nonprofits don't have one; automate instead |
| Enterprise-only pricing | Small agencies excluded |
| Outcome tools without evaluation methodology | Data without theory of change is noise |
| Proprietary data formats | Vendor lock-in; sector can't learn from each other |

---

## Connections to Other Foundations

- **Collaborative Practice**: The evaluation pipeline starts with collaborative goal-setting and ends with sector-wide learning. The minimal tech stack keeps the interface simple enough for participants to use alongside staff during sessions.
- **Data Sovereignty**: Multi-tenancy serves both cost sharing AND data sovereignty — same architecture, dual purpose. The shared AI server maintains data isolation while making AI affordable.
- **Security by Default**: Self-healing ops and Alpine containers reduce the attack surface. Fewer dependencies mean fewer security vulnerabilities to patch. The sustainability constraint ("no dedicated IT") forces security to be architectural.

---

## Related Implementation Decisions

These existing Design Rationale Records contain the detailed implementation specifics for features shaped by this principle:

- **`multi-tenancy.md`** — Schema-per-tenant architecture that enables cost sharing without data sharing.
- **`ovhcloud-deployment.md`** — Self-healing deployment, backup strategy, and monitoring on unmanaged VPS.
- **`self-hosted-llm-infrastructure.md`** — Shared Ollama server with tenant-level data isolation.
- **`reporting-architecture.md`** — Template-driven reporting that connects evaluation frameworks to funder requirements.
- **`cids-privacy-architecture.md`** — Three-layer compliance model for sector reporting without compromising participant privacy.
- **`funder-reporting-profiles.md`** — Funder-specific report templates configured through admin workflows.
- **`cids-batch-classification-workflow.md`** — Admin-facing taxonomy classification that keeps CIDS complexity away from frontline staff.
- **`cids-metadata-assignment.md`** — When metadata gets assigned (creation vs. deferred), balancing data quality with workflow simplicity.
- **`bilingual-requirements.md`** — EN/FR as a legal requirement, not an optional feature. Bilingual support is part of the sustainability commitment to Canadian nonprofits.

---

## When to Revisit

This foundation principle should be revisited if:

- Nonprofit sector IT capacity significantly increases (shared SOC services, managed hosting co-ops emerge), in which case some simplification choices could be relaxed.
- The scale exceeds ~2,000 participants per agency, at which point the in-memory search (required by field-level encryption) needs re-architecture.
- Managed cloud pricing drops to parity with unmanaged VPS, removing the cost advantage of self-hosting.
- A JavaScript framework emerges that is genuinely zero-config, zero-dependency, and maintenance-free (this has not happened in 15 years of JavaScript frameworks).

The principle — affordable for small agencies with minimal IT — should not change. The specific implementation choices (OVHcloud, Alpine, 46 dependencies) may evolve, but the constraints they serve are permanent features of the nonprofit sector.
