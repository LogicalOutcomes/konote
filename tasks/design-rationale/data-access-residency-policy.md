# Design Rationale: Data Access Residency Policy

*Last updated: 2026-02-26*
*Status: DRAFT — needs GK review and team decision*

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

## Open Questions — Need Team Decision

These questions don't have clear legal answers. The team needs to decide based on risk tolerance and practicality.

### Q1: Is VPN-from-Canada sufficient, or do we require actual residency?

A Canadian VPN exit node means the SSH connection originates from a Canadian IP, but the person and their device are still physically in another jurisdiction.

| Option | Pros | Cons |
|--------|------|------|
| **Actual Canadian residency required** | Strongest position for agency agreements; no ambiguity; device is in Canadian jurisdiction | Limits hiring pool; hard to verify continuously |
| **VPN-from-Canada acceptable** | Broader hiring pool; technically the connection is "from Canada" | Doesn't address foreign subpoena risk on the individual; device is in foreign jurisdiction; agencies may not accept this |

**Recommendation:** Require actual Canadian residency for Tier 1. The foreign subpoena risk and agency agreement language both attach to the *person and their device*, not the IP address.

### Q2: What about temporary travel?

A Canadian-resident team member travelling abroad for two weeks still has production credentials on their laptop.

| Option | Pros | Cons |
|--------|------|------|
| **Revoke access during travel** | Eliminates risk entirely | Operationally disruptive; single-person teams can't do this |
| **Accept the risk for short trips (<30 days)** | Practical; the person is still Canadian-resident | Device is temporarily in foreign jurisdiction |
| **Require encrypted device + VPN during travel** | Reasonable middle ground | Doesn't address foreign subpoena risk during the trip |

**Recommendation:** Accept short-term travel (<30 days) with encrypted device and VPN. Document the policy so it's a conscious decision, not an oversight.

### Q3: How do we handle the freelance sysadmin retainer?

The OVHcloud DRR recommends a freelance sysadmin on retainer for early growth (Option 2 in the second-level support section). That person would have Tier 1 access.

**Requirement:** The retainer agreement must specify:
- Individual is Canadian-resident
- SSH access originates from Canada
- No subcontracting of access to non-Canadian parties
- Compliance with the agency's data-sharing agreement terms
- Notification if residency status changes

### Q4: What about the MSP option?

When KoNote scales to 5+ agencies, the OVHcloud DRR suggests transitioning to a Canadian MSP. The same residency requirements apply to MSP personnel who access KoNote infrastructure.

**Requirement:** The MSP contract must specify:
- MSP is Canadian-incorporated
- Personnel with access to KoNote systems are Canadian-resident
- Logs and monitoring data stay in Canada
- MSP will not use offshore NOC (Network Operations Centre) staff for KoNote systems

## Implementation Checklist

Once the team decides on the open questions, these are the concrete steps:

- [ ] Add residency requirements to contractor/freelancer agreement templates
- [ ] Add residency clause to agency data-sharing agreement templates
- [ ] Document which team members currently hold Tier 1 and Tier 2 access
- [ ] Review CI/CD pipeline for Tier 2 mitigations (deploy service accounts, synthetic staging data)
- [ ] Add to the Agency Permissions Interview: "Do you require all personnel with data access to be Canadian-resident?" (some agencies may have stricter requirements than our baseline)
- [ ] Add to the deployment runbook: access tier classification for each credential

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
