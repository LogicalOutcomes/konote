# Foundation: Data Sovereignty & Rights

**Individual, Community, and National Data Ownership**

Status: Foundation Principle
Created: 2026-03-14

> **In plain language:** Your data belongs to you — not to KoNote, not to a tech company, and not to a foreign government. The system is built so that communities control their own data, individuals can see and correct their own records, and no one can combine data across agencies without explicit community consent.

---

## Core Principle

KoNote is designed so that data belongs to the people and communities it describes — not to KoNote, not to a hosting provider, and not to any government with a subpoena power that overrides Canadian law. This principle operates at three levels: individual participants own their personal information, communities own their collective data, and Canadian nonprofits retain sovereignty over where their data resides and who can access it.

The architecture enforces these principles structurally — not through policies that can be ignored, but through technical design that makes violation impossible. Schema-per-tenant isolation means cross-agency queries cannot happen, not that they are merely forbidden. Export-only data portability means no persistent external access channel exists, not that one exists but is discouraged. Self-hosted AI means participant data never leaves Canadian infrastructure, not that it leaves but is "anonymised first." The gap between "we promise not to" and "we built it so you can't" is where trust lives.

---

## Individual Participant Rights

### 1. Correction Rights (PHIPA/PIPEDA)

Participants can request corrections to their records through the portal. The `CorrectionRequest` model supports both informal paths ("I'll bring it up next session") and formal written requests. Staff must respond within the regulatory timeline. Corrections are appended — the original record is preserved with an amendment notation, not silently overwritten. This protects both the participant's right to accuracy and the clinical record's integrity.

### 2. Data Access

PIPEDA gives Canadians the right to see what information is held about them. The participant portal makes this self-service — participants view their own goals, notes, and progress without making a formal access request. This is not a convenience feature. It is a structural implementation of a legal right. The alternative — requiring participants to submit formal requests and wait 30 days — creates a power asymmetry that discourages people from exercising their rights.

### 3. Erasure Workflow

Erasure uses a two-person process: a Program Manager requests it, an admin approves it. PII is stripped and the anonymised record is retained for aggregate statistics. The process is irreversible by design — this prevents accidental or coerced reversal. Once erasure is approved, no one (including KoNote developers, hosting administrators, or the agency itself) can reconstruct the individual's identity from remaining data. The two-person requirement prevents a single compromised or pressured account from erasing records to cover up harm.

### 4. Consent as Ongoing

The `ConsentEvent` model is append-only: it records grant and withdraw events with reasons and timestamps. Consent is never a single checkbox at intake that covers everything forever. Cross-program sharing is per-client configurable. Consent to aggregate reporting is explicit opt-in.

**Anti-pattern: one-time blanket consent at intake.** Many systems collect a single signature at enrollment and treat it as permanent, irrevocable permission for all data uses. This violates the spirit of PIPEDA's meaningful consent requirement. KoNote treats consent as a living state that participants can change at any time, with each change recorded and enforced structurally through the PHIPA consent filtering layer.

---

## Community Data Sovereignty

This is where KoNote's design philosophy diverges most sharply from conventional SaaS platforms. Data about communities has historically been extracted, combined, and used in ways those communities never consented to and often cannot see. KoNote's architecture is built to make that pattern structurally impossible.

### 1. OCAP Principles (First Nations)

The First Nations principles of **Ownership, Control, Access, and Possession** (OCAP) are the most developed framework for Indigenous data sovereignty. KoNote's architecture supports OCAP through:

- **Ownership**: Each agency or community owns its data in an isolated schema. KoNote (the software) has no claim on the data. The licensing model is designed to ensure that data belongs to the agency, not to KoNote or its developers — this principle should be formalised in every service agreement.
- **Control**: Communities control what data is collected (custom fields, configurable demographics), who sees it (role-based access with granular permissions), and whether it is shared (export-only — no live API, no automatic reporting to external bodies).
- **Access**: The community has full access through the admin interface and export functions. Data portability is a right, not a premium feature. Full agency export is available to every agency regardless of pricing tier.
- **Possession**: Schema-per-tenant means the community's data is physically separated at the database level. No cross-agency queries are possible — not restricted by policy, but prevented by architecture. Data stays in Canadian data centres (OVHcloud Beauharnois, QC).

**Anti-pattern: multi-agency data lakes where community data is combined with other agencies' data without community control.** Many platforms aggregate data across clients into a single database, then offer "insights" that the contributing communities cannot review, correct, or withdraw from. This directly violates OCAP's ownership and control principles.

### 2. Black Data Governance (EGAP)

The **EGAP Framework** — **Engagement, Governance, Access, and Protection** — is the Black community equivalent of OCAP. Where OCAP centres First Nations data sovereignty, EGAP addresses the specific harms that data collection has inflicted on Black communities: surveillance, profiling, deficit narratives, and systemic exclusion. Alongside EGAP, related frameworks (the Black Health Alliance's position papers, the Us/We approach) emphasise that data about Black communities has historically been used to justify funding cuts, target neighbourhoods for policing, and reinforce deficit narratives rather than support empowerment.

KoNote's architecture supports EGAP through:

- **Engagement**: Community-controlled demographic fields are optional and self-identified. Agencies configure their own intake forms and choose which demographic categories to collect. No external body dictates what identity data must be gathered — the community decides what's relevant to their services and their people.
- **Governance**: Agency-level settings, RBAC with program-scoped access, and feature toggles give the community control over how their data is used internally. No data leaves the instance without deliberate community action. Aggregate reporting requires explicit opt-in (`consent_to_aggregate_reporting`), not opt-out.
- **Access**: Full export capability ensures the community can retrieve all their data at any time. The participant portal provides individual-level access. Admin dashboards provide community-level visibility. Data portability is a right, not a premium feature.
- **Protection**: Mandatory small-cell suppression (k>=5) prevents re-identification in small populations. All PII is encrypted at rest with per-tenant keys. No cross-agency data combination is possible. The export-only model means no external system can pull data without deliberate community action.

**Anti-pattern: automatic demographic disaggregation that exposes small community populations.** A report showing "2 Black youth in Program X had declining outcomes" identifies those individuals to anyone familiar with the program. KoNote's small-cell suppression is mandatory, not optional — it cannot be overridden by staff, administrators, or funders.

### 3. The Intentional Absence of Multi-Agency Combination

KoNote deliberately does NOT combine individual-level data across agencies. This is not a missing feature — it is a design principle. Cross-agency data combination:

- **Violates OCAP** — the community loses control of how their data is used once it enters a combined dataset
- **Enables surveillance patterns** — tracking individuals across service touchpoints creates a profile that no single agency intended to build
- **Undermines trust** — participants consented to share information with their agency, not to be tracked across every service they access
- **Concentrates power** — whoever controls the combined dataset has analytical power over all participating communities, with none of the accountability

**What IS permitted:** agencies can voluntarily publish de-identified aggregate reports to a consortium or funder. These are one-way, community-initiated, and contain no individual records. The `PublishedReport` model enforces this boundary. An agency can share "we served 45 youth and 78% showed improvement" without sharing who those youth are or any details that could identify them.

---

## Canadian Digital Sovereignty

### 1. Independence from US Tech Giants

KoNote uses OVHcloud (French parent company, not subject to US CLOUD Act), self-hosted Ollama for AI processing of participant data (not OpenAI/Anthropic APIs), and open-source software throughout the stack. This is not anti-American sentiment — it is a legal risk calculation. The US CLOUD Act allows US courts to compel any US-incorporated company, or any US person, to produce data regardless of where it is stored. Hosting participant data on AWS, Azure, or Google Cloud means a US court can order its disclosure without Canadian judicial oversight.

**Anti-pattern: building on AWS/Azure/Google Cloud where a US government subpoena can compel data disclosure without Canadian judicial review.** The risk is not theoretical — US law enforcement regularly uses CLOUD Act powers, and the threshold for access is lower than Canadian courts require.

### 2. Data Residency

All participant data is hosted in Beauharnois, QC. The `data-access-residency-policy` DRR establishes the access tier framework for anyone with SSH, database, or encryption key access. The hosting choice is deliberate: OVHcloud's Beauharnois data centre is operated by a French-incorporated company with no US subsidiary that could be compelled under the CLOUD Act.

### 3. No Vendor Lock-In

Docker Compose deployment works on any Linux VPS. Django and PostgreSQL are open-source. An agency can move to a different hosting provider by copying files and restoring a database backup. The full agency export produces a self-contained encrypted archive that includes everything needed to reconstruct the instance.

**Anti-pattern: proprietary platforms that hold data hostage when contracts end.** Many SaaS platforms make it technically difficult or contractually expensive to extract your own data. KoNote treats data portability as a right — the export function exists from day one, not as an afterthought when a client threatens to leave.

### 4. AI Sovereignty

Participant data never leaves the self-hosted LLM server (Ollama on the Canadian VPS). The `ai-feature-toggles` DRR enforces a strict split: Tier 1 (operational AI touching participant content) runs self-hosted; Tier 2 (tools-only AI processing program metadata, no PII) may use cloud APIs; Tier 3 (evaluation) is external and non-PII only. Agencies with heightened sovereignty concerns can disable cloud AI tiers entirely.

**Anti-pattern: sending participant data to cloud AI APIs for "AI-powered insights."** Once participant data reaches an external LLM provider's servers, it is subject to that provider's jurisdiction, retention policies, and training practices — regardless of what their terms of service promise today.

---

## Anti-Patterns Summary

| Anti-pattern | Why it is rejected |
|---|---|
| Multi-agency data lake | Violates OCAP; enables surveillance; concentrates power |
| Live API for individual PII | Persistent attack surface; bypasses consent model |
| Hosting on US cloud (AWS/Azure/GCP) | US CLOUD Act subpoena risk without Canadian judicial oversight |
| Blanket one-time consent | Consent must be ongoing, specific, and revocable |
| Automatic demographic disaggregation | Small-cell exposure; re-identification risk for marginalised communities |
| Proprietary platform lock-in | Community loses ability to leave with their data |
| Cloud AI APIs for participant data | Data leaves Canadian jurisdiction; sovereignty lost |

---

## Connections to Other Foundations

- **Collaborative Practice**: The participant portal (data access rights) is also a collaborative tool. Consent as ongoing aligns with the two-lens note design — participants are partners, not subjects. Bilingual design supports francophone communities' sovereignty over their service experience.
- **Security by Default**: Encryption, RBAC, and fail-closed consent are the *enforcement mechanisms* for the sovereignty principles described here. Security is the "how"; sovereignty is the "why."
- **Nonprofit Sustainability**: Multi-tenancy for cost sharing is also schema isolation for data sovereignty. The same architecture serves both purposes — affordable AND sovereign.

---

## Related Implementation Decisions

These DRRs implement specific aspects of the principles described above:

- `data-access-residency-policy.md` — Access tiers by data sensitivity level
- `no-live-api-individual-data.md` — Export-only model, no live API for individual PII
- `phipa-consent-enforcement.md` — Cross-program consent filtering
- `cids-privacy-architecture.md` — Three-layer compliance for cross-agency aggregate reporting
- `multi-tenancy.md` — Schema-per-tenant isolation
- `encryption-key-rotation.md` — Per-tenant encryption keys
- `self-hosted-llm-infrastructure.md` — Self-hosted AI for data sovereignty
- `ovhcloud-deployment.md` — Canadian hosting architecture
- `ai-feature-toggles.md` — Three-tier AI split (self-hosted vs. cloud)
- `access-tiers.md` — RBAC and demographic visibility controls

---

## When to Revisit

If Canada adopts legislation equivalent to EU GDPR adequacy agreements that provide enforceable protections against foreign government access, the US cloud restriction could be relaxed — but only if the legal protection is structural (treaty-level), not merely contractual (terms of service).

If Indigenous communities develop specific data governance standards for nonprofit service software beyond OCAP, incorporate them. If Black data governance frameworks produce concrete technical requirements, implement them.

The principles themselves — community ownership, individual rights, structural enforcement over policy promises — should not change. These are not implementation choices that might be superseded by better technology. They are values that the architecture exists to serve.
