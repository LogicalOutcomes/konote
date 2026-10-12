---
role: principle
status: Draft - awaiting GK review
source: foundation-data-sovereignty.md (2026-03-14)
---

# Principle: Data Sovereignty & Rights

**Individual, Community, and National Data Ownership**

> **In plain language:** Your data belongs to you — not to KoNote, not to a tech company, and not to a foreign government. The system is built so that communities control their own data, individuals can see and correct their own records, and no one can combine data across agencies without explicit community consent.

---

## Core Principle

KoNote is designed so that data belongs to the people and communities it describes — not to KoNote, not to a hosting provider, and not to any government with a subpoena power that overrides Canadian law. This principle operates at three levels: individual participants own their personal information, communities own their collective data, and Canadian nonprofits retain sovereignty over where their data resides and who can access it.

The architecture enforces these principles **structurally** — not through policies that can be ignored, but through technical design that makes violation impossible. Schema-per-tenant isolation means cross-agency queries cannot happen, not that they are merely forbidden. Export-only data portability means no persistent external access channel exists, not that one exists but is discouraged. Self-hosted AI means participant data never leaves Canadian infrastructure, not that it leaves but is "anonymised first."

**The gap between "we promise not to" and "we built it so you can't" is where trust lives.**

## Three Levels of Sovereignty

### 1. Individual Rights

Participants have legally-recognised rights over their own records under PIPEDA and PHIPA:

- **Correction rights** — the right to amend inaccurate records
- **Access rights** — the right to see what is held about them, without a formal request
- **Erasure rights** — the right to have records removed, subject to clinical and legal constraints
- **Ongoing consent** — consent is a living state, not a one-time checkbox

These are not convenience features. They are structural implementations of legal rights, and the system is built so that exercising them does not depend on staff goodwill or administrative effort.

### 2. Community Data Sovereignty

Communities have collective rights over data about them, beyond individual rights. KoNote's architecture supports two major frameworks:

- **OCAP** (Ownership, Control, Access, Possession) — the First Nations principles of Indigenous data sovereignty.
- **EGAP** (Engagement, Governance, Access, Protection) — the Black community equivalent, alongside related frameworks from the Black Health Alliance. EGAP addresses the specific harms that data collection has inflicted on Black communities: surveillance, profiling, deficit narratives, and systemic exclusion.

Both frameworks reject the **multi-agency data lake** pattern: aggregating individual-level data across communities without community control. KoNote architecturally refuses this pattern. Cross-agency data combination is not a missing feature — it is a deliberately absent feature.

What *is* permitted: agencies can voluntarily publish de-identified aggregate reports to consortia or funders. One-way, community-initiated, no individual records.

### 3. Canadian Digital Sovereignty

Canadian nonprofit data should not be subject to foreign government subpoena powers that bypass Canadian judicial review:

- The **US CLOUD Act** allows US courts to compel US-incorporated companies to produce data regardless of where it is stored. This makes AWS, Azure, and Google Cloud unsuitable for PHIPA-class data.
- **Self-hosted AI** keeps participant data inside Canadian infrastructure. Cloud LLM APIs (OpenAI, Anthropic) are excluded for participant content.
- **No vendor lock-in** — agencies can move to a different hosting provider by copying files and restoring a backup. Data portability is a right, not a premium feature.

This is not anti-American sentiment. It is a legal risk calculation. US law enforcement regularly uses CLOUD Act powers, and the threshold for access is lower than Canadian courts require.

## Guiding Tests for Proposed Features

1. **Can a US government subpoena reach this data without Canadian judicial review?** If yes, reject.
2. **Does this combine individual-level data across agencies?** If yes, reject.
3. **Does this reduce a participant's ability to see, correct, or withdraw their information?** If yes, reject.
4. **Is consent treated as a one-time event or as a living state?** If one-time, reject.
5. **If this feature is removed, can agencies still leave with all their data?** If no, reject.

## When to Revisit

If Canada adopts legislation equivalent to EU GDPR adequacy agreements that provide enforceable protections against foreign government access, the US cloud restriction could be relaxed — but only if the legal protection is structural (treaty-level), not merely contractual (terms of service).

If Indigenous communities develop specific data governance standards for nonprofit service software beyond OCAP, incorporate them. If Black data governance frameworks produce concrete technical requirements, implement them.

The principles themselves — community ownership, individual rights, structural enforcement over policy promises — should not change. These are not implementation choices that might be superseded by better technology. They are values that the architecture exists to serve.

---

## Implementation DRRs

Specific, enforceable decisions that implement this principle:

- [individual-data-rights](../design-rationale/individual-data-rights.md) — correction, access, erasure workflows; append-only consent (NEW)
- [phipa-consent-enforcement](../design-rationale/phipa-consent-enforcement.md) — cross-program consent filtering
- [multi-tenancy](../design-rationale/multi-tenancy.md) — schema-per-tenant isolation
- [no-live-api-individual-data](../design-rationale/no-live-api-individual-data.md) — export-only, no live API for PII
- [cids-privacy-architecture](../design-rationale/cids-privacy-architecture.md) — three-layer compliance for aggregate reporting
- [data-access-residency-policy](../design-rationale/data-access-residency-policy.md) — access tiers by data sensitivity
- [encryption-key-rotation](../design-rationale/encryption-key-rotation.md) — per-tenant keys
- [ovhcloud-deployment](../design-rationale/ovhcloud-deployment.md) — Canadian hosting
- [self-hosted-llm-infrastructure](../design-rationale/self-hosted-llm-infrastructure.md) — in-country AI
- [ai-feature-toggles](../design-rationale/ai-feature-toggles.md) — cloud AI excluded for participant data

## Related Principles

- **Security by Default** — security is the *enforcement mechanism* for sovereignty. Security is the "how"; sovereignty is the "why."
- **Collaborative Practice** — the participant portal (access rights) is also a collaborative tool
- **Nonprofit Sustainability** — multi-tenancy serves both cost-sharing and sovereignty through the same architecture
