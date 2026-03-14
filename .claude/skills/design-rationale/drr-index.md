# DRR Keyword Index

All files live in `tasks/design-rationale/`. Read the full DRR before making judgements — this index helps you find which DRRs are relevant, not replace reading them.

## Start Here: Foundation Principles

For any proposal, **always check the relevant foundation first**, then drill into implementation decisions.

| Foundation | Covers | Read when proposal involves... |
|---|---|---|
| `foundation-collaborative-practice.md` | Two-lens notes, alliance, portal, feedback, strengths-based language, bilingual by design, accessible by design | Note design, participant-facing features, UX, feedback, goal-setting, bilingual/French, accessibility/WCAG |
| `foundation-data-sovereignty.md` | OCAP, Black data governance, Canadian sovereignty, no cross-agency combination | Data sharing, cross-agency features, community data, demographics, hosting location, AI providers |
| `foundation-security-by-default.md` | Encryption, RBAC, audit, fail-closed, session security | Auth, permissions, exports, logging, error handling, new roles or access paths |
| `foundation-nonprofit-sustainability.md` | Minimal tech stack, cost, self-healing ops, evaluation-driven config | New dependencies, frameworks, hosting changes, deployment, pricing, metric/evaluation architecture |

## Quick Lookup by Topic (Implementation Decisions)

| If the proposal involves... | Read these DRRs |
|---|---|
| **API, REST, GraphQL, webhook, sync, integration, CRM, real-time data** | `no-live-api-individual-data.md`, `cids-privacy-architecture.md`, `data-access-residency-policy.md` |
| **FHIR, HL7, health data, EHR/EMR, clinical interoperability** | `fhir-informed-modelling.md`, `no-live-api-individual-data.md` |
| **Family, household, relationships, circles, network, dependents** | `circles-family-entity.md` |
| **Multi-tenancy, schema isolation, cross-agency, shared database** | `multi-tenancy.md`, `data-access-residency-policy.md` |
| **Permissions, roles, access tiers, front desk, executive, gated access** | `access-tiers.md`, `phipa-consent-enforcement.md` |
| **Consent, PHIPA, cross-program notes, clinical note visibility** | `phipa-consent-enforcement.md`, `access-tiers.md` |
| **AI, LLM, machine learning, suggestions, scoring, prompts** | `ai-feature-toggles.md`, `self-hosted-llm-infrastructure.md` |
| **Encryption, key rotation, PII, decryption, Fernet** | `encryption-key-rotation.md`, `no-live-api-individual-data.md` |
| **Reports, dashboards, funder reporting, executive view, exports** | `reporting-architecture.md`, `insights-metric-distributions.md`, `funder-reporting-profiles.md`, `executive-dashboard-redesign.md` |
| **CIDS, Common Approach, indicators, taxonomy, classification** | `cids-privacy-architecture.md`, `cids-batch-classification-workflow.md`, `cids-metadata-assignment.md`, `funder-reporting-profiles.md` |
| **Surveys, questionnaires, instruments, PHQ-9, standardised tools** | `survey-metric-unification.md`, `insights-metric-distributions.md` |
| **Offline, field work, mobile, ODK, data collection** | `offline-field-collection.md` |
| **Deployment, hosting, VPS, Docker, OVHcloud, infrastructure** | `ovhcloud-deployment.md`, `self-hosted-llm-infrastructure.md` |
| **Bilingual, French, translation, Official Languages Act** | `foundation-collaborative-practice.md`, `bilingual-requirements.md` |
| **Accessibility, WCAG, a11y, screen reader, keyboard navigation** | `foundation-collaborative-practice.md` |
| **EGAP, Black data governance, Black communities, anti-Black racism** | `foundation-data-sovereignty.md`, `multi-tenancy.md` |
| **Documents, SharePoint, Google Drive, file storage, attachments** | `document-integration.md` |
| **Data export, data portability, migration, offboarding** | `no-live-api-individual-data.md`, `cids-privacy-architecture.md` |
| **Data residency, Canadian hosting, foreign access, subpoena risk** | `data-access-residency-policy.md`, `ovhcloud-deployment.md` |
| **Metrics, outcomes, progress notes, scoring, measurement** | `survey-metric-unification.md`, `insights-metric-distributions.md`, `cids-metadata-assignment.md` |
| **Data sovereignty, OCAP, Indigenous data, community ownership** | `foundation-data-sovereignty.md`, `multi-tenancy.md`, `no-live-api-individual-data.md` |
| **Participant portal, collaborative features, alliance rating** | `foundation-collaborative-practice.md`, `insights-metric-distributions.md` |
| **Cost, pricing, tech stack, dependencies, frameworks** | `foundation-nonprofit-sustainability.md`, `ovhcloud-deployment.md`, `self-hosted-llm-infrastructure.md` |

## DRR Status Reference

| Status | Meaning |
|---|---|
| **Foundation Principle** | Core design philosophy. Governs multiple implementation decisions. |
| **Decided** | Approved and enforced. Do not override without stakeholder approval. |
| **Implemented** | Decided AND built. Code exists — check implementation before modifying. |
| **Approved** | Reviewed by expert panel, awaiting implementation. |
| **Draft** | Under development. Decisions may change — still read before building. |
| **Parking Lot** | Not yet clear we should build. Do not implement without explicit approval. |

## Full DRR Inventory (26 files)

### Foundation Principles (4)

| File | Scope |
|---|---|
| `foundation-collaborative-practice.md` | The "Ko" — documentation WITH participants, two-lens notes, alliance, feedback, bilingual by design, accessible by design |
| `foundation-data-sovereignty.md` | Individual, community (OCAP, EGAP), and national data ownership |
| `foundation-security-by-default.md` | High security for non-technical operators — encryption, RBAC, immutable audit, fail-closed |
| `foundation-nonprofit-sustainability.md` | Affordable tech stack, self-healing ops, evaluation-driven configuration |

### Implementation Decisions (22)

| File | Status | Scope |
|---|---|---|
| `access-tiers.md` | Decided | Three permission tiers, PERM-P5/P6/P8, demographic visibility |
| `ai-feature-toggles.md` | Decided | Two-tier AI split (tools-only vs. participant data) |
| `bilingual-requirements.md` | Decided | EN/FR translation, legal obligations, tooling |
| `cids-batch-classification-workflow.md` | Draft | Admin-facing batch AI classification for reporting taxonomies |
| `cids-metadata-assignment.md` | Draft | When metadata gets assigned (creation vs. deferred) |
| `cids-privacy-architecture.md` | Decided | Three-layer compliance (metadata / aggregate / exemplar) |
| `circles-family-entity.md` | Decided | Family/network entity, 6+ anti-patterns |
| `data-access-residency-policy.md` | Decided | Canadian residency by data access level |
| `document-integration.md` | Decided | SharePoint + Google Drive integration |
| `encryption-key-rotation.md` | Decided | Master/tenant key rotation procedures |
| `executive-dashboard-redesign.md` | Approved | Dashboard UX with accessibility focus |
| `fhir-informed-modelling.md` | Decided | FHIR concepts without FHIR compliance |
| `funder-reporting-profiles.md` | Parking Lot | Template-based funder reporting |
| `insights-metric-distributions.md` | Decided | Outcome Insights page, metric aggregation |
| `multi-tenancy.md` | Decided | Schema-per-tenant via django-tenants |
| `no-live-api-individual-data.md` | Decided | No live API for PII — export-only model |
| `offline-field-collection.md` | Decided | ODK Central for offline field collection |
| `ovhcloud-deployment.md` | Decided | OVHcloud VPS architecture, self-healing |
| `phipa-consent-enforcement.md` | Decided | Cross-program clinical note consent filtering |
| `reporting-architecture.md` | Decided | Template-driven vs. ad-hoc reporting |
| `self-hosted-llm-infrastructure.md` | Decided | Shared Ollama VPS, data isolation |
| `survey-metric-unification.md` | Decided | Surveys and metrics as one construct |
