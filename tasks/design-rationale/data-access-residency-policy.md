# Design Rationale: Data Access Residency Policy

*Last updated: 2026-02-26*
*Status: Decided — GK reviewed 2026-03-02*

## Context

KoNote handles PHIPA-protected health data hosted on Canadian infrastructure (OVHcloud Beauharnois). The team hires people outside Canada. This document defines which roles require Canadian residency based on their level of access to participant data, and why.

**Related documents:**
- [OVHcloud deployment DRR](ovhcloud-deployment.md) — hosting architecture, self-healing, backup strategy
- [Multi-tenancy DRR](multi-tenancy.md) — schema-per-tenant architecture

## The Core Principle

**The dividing line is data access, not job title.** Anyone who can reach participant data — directly or indirectly — should be Canadian-resident. Anyone who only touches code, documentation, or design (with no production credentials) is lower risk regardless of location.

## Why Residency Matters (Even Though the Law Doesn't Explicitly Require It)

Canadian data sovereignty law (PHIPA, PIPEDA, Ontario FIPPA) regulates **where data is stored and processed** and **which corporate jurisdictions can compel its disclosure**. There is no statute that says "the sysadmin must be Canadian." However, residency matters for practical and contractual reasons:

| Concern | Detail |
|---------|--------|
| **Foreign subpoena risk** | A US-resident contractor could be compelled by a US court to produce data they have access to, even if that data is stored in Canada. The risk is narrow (requires the individual to be specifically targeted) but real. |
| **Agency data agreements** | Most Ontario health-data sharing agreements require that personal health information is accessed only from within Canada. A maintainer SSHing in from another country could put the agency in breach of their own agreements. |
| **PHIPA breach notification** | If a non-Canadian team member's device is compromised, the jurisdictional complexity of breach response increases — which privacy commissioner has authority, which notification laws apply, which courts have jurisdiction. |
| **Funder and accreditation expectations** | Funders and accreditation bodies may ask "who has access to the data and where are they?" A clean answer ("all data-access personnel are Canadian-resident") simplifies compliance conversations. |
| **Insurance and liability** | Cyber liability insurance policies may have territorial conditions on who accesses covered systems. |

## Access Tiers

### Tier 1: Direct Data Access — Canadian Residency Required

These roles can see, query, or extract participant data. The person holding any of these credentials **must be a Canadian resident**.

| Access Type | Examples | Why It's Tier 1 |
|-------------|----------|-----------------|
| SSH access to production VPS | Sysadmin, DevOps, on-call support | Full access to filesystem, DB, backups, logs with PII |
| Database credentials (production) | DBA, data migration specialist | Can query participant records directly |
| Backup access | Backup operator, disaster recovery | Backups contain full database dumps including PII |
| Django admin (production) | Application admin | Can view/edit participant records through the UI |
| Log access (production) | Support, debugging | Application logs may contain PII in error traces |
| Encryption key access | Key custodian | Can decrypt PII fields if combined with database access |

### Tier 2: Indirect Data Access — Canadian Residency Strongly Recommended

These roles don't routinely access participant data but could encounter it in edge cases.

| Access Type | Examples | Why It's Tier 2 |
|-------------|----------|-----------------|
| CI/CD pipeline with deploy credentials | DevOps engineer who can push to production | Could inject code that exfiltrates data; deploy credentials may include DB access |
| Staging environment with realistic data | QA tester, developer | If staging uses anonymised copies of production data, PII exposure is possible |
| Error monitoring tools (Sentry, etc.) | Developer on-call | Error payloads may include PII from request context |

**Mitigation if non-Canadian:** Remove production credentials from CI/CD (use a separate deploy service account). Use synthetic data in staging (never copies of production). Strip PII from error payloads before they reach monitoring tools.

### Tier 3: No Data Access — No Residency Requirement

These roles never touch production systems or participant data. **No residency requirement.**

| Access Type | Examples | Why It's Tier 3 |
|-------------|----------|-----------------|
| GitHub repository (code only) | Developer, contributor | Code doesn't contain participant data |
| Documentation, design, UX | Technical writer, designer | No system access |
| Local development with synthetic data | Developer | Demo data engine generates fake data; no production connection |
| Website, marketing, communications | Content creator | No access to the application |
| Project management tools | PM, coordinator | Task tracking, not data access |

## Resolved Questions — GK Decision 2026-03-02

These questions were raised as risk-mitigation considerations. After review, GK decided that **no personnel residency requirements are needed**. The rationale:

- Canadian privacy law (PHIPA, PIPEDA) regulates **where data is stored** and **which corporate jurisdictions can compel disclosure** — neither statute requires personnel to be Canadian residents
- The foreign subpoena risk for individual contractors is narrow (requires the individual to be specifically targeted) and theoretical
- Data sovereignty is already addressed by hosting choices: OVHcloud Beauharnois (French-incorporated parent, not subject to US CLOUD Act) and Azure Canada Central
- Contractual safeguards in the SaaS service agreement (data processing terms, breach notification) provide the relevant legal protections
- Imposing residency requirements would limit the hiring pool without a corresponding legal benefit

### Q1: VPN-from-Canada vs actual residency?
**Decision:** Neither required. No personnel residency requirement.

### Q2: Temporary travel policy?
**Decision:** No restriction. Personnel may travel freely. Standard device security practices (encrypted devices, strong authentication) apply regardless of location.

### Q3: Freelance sysadmin retainer?
**Decision:** No residency requirement. The retainer agreement should include standard data-processing terms (confidentiality, compliance with applicable privacy law, notification of security incidents) but not a residency clause.

### Q4: MSP requirements?
**Decision:** No residency requirement for MSP personnel. The MSP contract should include standard data-processing terms. Preference for Canadian-incorporated MSPs where available, but not a hard requirement.

## Implementation Checklist

- [ ] Document which team members currently hold Tier 1 and Tier 2 access
- [ ] Review CI/CD pipeline for Tier 2 mitigations (deploy service accounts, synthetic staging data)
- [ ] Add to the Agency Permissions Interview: "Do you require all personnel with data access to be Canadian-resident?" (some agencies may have stricter requirements than our baseline — respect their choice)
- [ ] Add to the deployment runbook: access tier classification for each credential
- [ ] Include standard data-processing terms in contractor and MSP agreements (confidentiality, privacy compliance, incident notification)

## AI Data Flow and Residency

KoNote's three-tier AI architecture (see [AI Feature Toggles DRR](ai-feature-toggles.md#three-tier-ai-architecture-added-2026-03-07)) has different residency implications for each tier:

| AI Tier | Data type | Where processed | Residency implication |
|---------|-----------|----------------|----------------------|
| **Tier 1 — Operational** (self-hosted) | Scrubbed participant content | Canadian VPS (Ollama) | No cross-border transfer |
| **Tier 2 — Tools** (cloud API) | Program metadata only | Cloud API provider | No participant data crosses the border |
| **Tier 3 — Evaluation** (external LLM) | Program documentation, aggregate stats | External LLM platform | Evaluator-controlled; non-PII only |
| **Translation** | Static UI strings | Cloud API provider | No personal information |

**Key principle:** Participant data (even scrubbed) never leaves the Canadian VPS. Only institutional metadata and non-PII program documentation are processed by external AI services.

For agencies with heightened data sovereignty concerns (Indigenous communities under OCAP principles), Tier 2 tools can be disabled via `ai_assist_tools_only`, and Tier 3 is entirely optional.

## Anti-Patterns

**Do not:**
- Assume VPN-from-Canada is equivalent to Canadian residency — it addresses IP geolocation but not legal jurisdiction over the person or device
- Give production credentials to anyone without checking their access tier first
- Use real production data in staging environments accessible to non-Canadian personnel
- Assume "no one will ask" — agency audits, funder reviews, and privacy commissioners do ask about personnel access
- Treat this policy as optional for "trusted" people — the policy exists precisely so trust isn't the only safeguard
- Store this policy only internally — agencies need to see it (or a summary) in their data-sharing agreements

## References

- **PHIPA (Personal Health Information Protection Act, 2004)** — Ontario legislation governing health information. Does not explicitly require personnel residency but requires custodians to protect against unauthorized access, which includes jurisdictional risk.
- **PIPEDA (Personal Information Protection and Electronic Documents Act)** — Federal privacy law. Section 4.7 requires organizations to protect personal information with appropriate safeguards. Accountability extends to third parties processing data.
- **US CLOUD Act (Clarifying Lawful Overseas Use of Data Act, 2018)** — Allows US courts to compel US-incorporated companies *and US persons* to produce data regardless of where it's stored. This is the primary risk for non-Canadian personnel.
- **Sept 2025 Ontario court ruling (RCMP / OVH Canada)** — Confirmed Canadian law enforcement can compel Canadian-hosted providers to produce data. This is expected and acceptable for KoNote's threat model.
