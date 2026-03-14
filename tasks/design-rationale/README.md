# KoNote Design Rationale

This directory contains the architectural decisions that govern KoNote's design. If you're new to the project, start with the **Foundation Principles** — they explain *why* KoNote works the way it does. Then consult the implementation decisions when you're modifying a specific feature.

## How to Use This Directory

1. **Before proposing a new feature:** Read the relevant foundation principle, then check the implementation decisions it references.
2. **Before modifying existing code:** Find the implementation decision that governs that feature. If one exists, read it before changing anything.
3. **If you think a decision should change:** Document the new evidence, flag for GK (subject-matter expert) review, and update the DRR *before* implementing.

Use `/design-rationale` in Claude Code to automatically check a proposal against all DRRs.

---

## Foundation Principles

These 4 documents capture KoNote's core design philosophy. **Read these first.**

| Document | What it covers |
|---|---|
| [Collaborative Practice](foundation-collaborative-practice.md) | The "Ko" in KoNote — documentation WITH participants, two-lens notes, alliance rating, feedback-informed improvement, strengths-based language |
| [Data Sovereignty & Rights](foundation-data-sovereignty.md) | Participant and community data ownership, OCAP principles, Black data governance, Canadian digital sovereignty, intentional absence of cross-agency data combination |
| [Security by Default](foundation-security-by-default.md) | High security for non-technical operators — encryption, RBAC, immutable audit, fail-closed consent, session security |
| [Nonprofit Sustainability](foundation-nonprofit-sustainability.md) | Minimal tech stack, affordable hosting, self-healing ops, evaluation-driven configuration, managed service model |

---

## Implementation Decisions by Topic

These are detailed decisions with expert panel findings and anti-patterns. Grouped by the foundation principle they support.

### Collaborative Practice

| Document | Status | Scope | See also |
|---|---|---|---|
| [insights-metric-distributions.md](insights-metric-distributions.md) | Decided | Outcome Insights page, metric aggregation, suggestion themes | Sustainability |
| [survey-metric-unification.md](survey-metric-unification.md) | Decided | Surveys and metrics as one construct | Sustainability |
| [circles-family-entity.md](circles-family-entity.md) | Decided | Family/network entity, 6+ anti-patterns | |

### Data Sovereignty & Privacy

| Document | Status | Scope | See also |
|---|---|---|---|
| [data-access-residency-policy.md](data-access-residency-policy.md) | Decided | Canadian residency requirements by data access level | Security |
| [no-live-api-individual-data.md](no-live-api-individual-data.md) | Decided | No live API for PII — export-only model | Security |
| [phipa-consent-enforcement.md](phipa-consent-enforcement.md) | Decided | Cross-program clinical note consent filtering | Security, Collab |
| [cids-privacy-architecture.md](cids-privacy-architecture.md) | Decided | Three-layer compliance for CIDS reporting | Sustainability |
| [encryption-key-rotation.md](encryption-key-rotation.md) | Decided | Master/tenant key rotation procedures | Security |

### Security & Access Control

| Document | Status | Scope | See also |
|---|---|---|---|
| [access-tiers.md](access-tiers.md) | Decided | Three permission tiers, PERM-P5/P6/P8, demographic visibility | Sovereignty |
| [ai-feature-toggles.md](ai-feature-toggles.md) | Decided | Two-tier AI split (tools-only vs. participant data) | Sovereignty, Sustainability |

### Evaluation & Reporting

| Document | Status | Scope | See also |
|---|---|---|---|
| [reporting-architecture.md](reporting-architecture.md) | Decided | Template-driven vs. ad-hoc reporting | Sovereignty |
| [funder-reporting-profiles.md](funder-reporting-profiles.md) | Parking Lot | Template-based funder reporting configuration | |
| [executive-dashboard-redesign.md](executive-dashboard-redesign.md) | Approved | Dashboard UX with accessibility focus | Collab |
| [cids-batch-classification-workflow.md](cids-batch-classification-workflow.md) | Draft | Batch AI classification for reporting taxonomies | |
| [cids-metadata-assignment.md](cids-metadata-assignment.md) | Draft | When metadata gets assigned (creation vs. deferred) | |

### Infrastructure & Deployment

| Document | Status | Scope | See also |
|---|---|---|---|
| [ovhcloud-deployment.md](ovhcloud-deployment.md) | Decided | OVHcloud VPS architecture, self-healing, backup | Sovereignty |
| [self-hosted-llm-infrastructure.md](self-hosted-llm-infrastructure.md) | Decided | Shared Ollama VPS, data isolation model | Sovereignty |
| [multi-tenancy.md](multi-tenancy.md) | Decided | Schema-per-tenant via django-tenants | Sovereignty, Sustainability |

### Interoperability & Integration

| Document | Status | Scope | See also |
|---|---|---|---|
| [fhir-informed-modelling.md](fhir-informed-modelling.md) | Decided | FHIR concepts without FHIR compliance | |
| [bilingual-requirements.md](bilingual-requirements.md) | Decided | EN/FR translation, legal obligations | Collab, Sustainability |
| [document-integration.md](document-integration.md) | Decided | SharePoint + Google Drive integration | |
| [offline-field-collection.md](offline-field-collection.md) | Decided | ODK Central for offline field collection | |

---

## Status Key

| Status | Meaning |
|---|---|
| **Decided** | Approved and enforced. Do not override without stakeholder approval. |
| **Implemented** | Decided AND built. Check implementation before modifying. |
| **Approved** | Reviewed by expert panel, awaiting implementation. |
| **Draft** | Under development. Decisions may change — still read before building. |
| **Parking Lot** | Not yet clear we should build. Do not implement without explicit approval. |
