# SaaS Service Agreement — LogicalOutcomes Managed KoNote

**Task ID:** LEGAL-SaaS1
**Status:** Not started — needs lawyer review before use
**Date:** 2026-02-27

---

## What This Is

A service agreement between LogicalOutcomes and agencies for whom LogicalOutcomes hosts and operates a KoNote instance. Required under PIPEDA Principle 1, s. 4.1.3: when an organisation transfers personal information to a third party for processing, it must use contractual or other means to provide a comparable level of protection.

This is **not** needed for self-hosted agencies (they operate KoNote themselves — no third-party processing).

## Why It's Needed Before First Managed Agency

Without this agreement, LogicalOutcomes is processing personal information (including highly sensitive participant data) on behalf of agencies with no documented terms. If there's a breach, a PIPEDA complaint, or a dispute, there's no written record of who is responsible for what.

## Recommended Contents

The following elements should be included. A lawyer should draft the actual language.

### 1. Parties and Scope

- LogicalOutcomes as data processor / service provider
- The agency as data controller (the "organisation" under PIPEDA)
- Scope: hosting, operating, and maintaining a KoNote instance on the agency's behalf
- Clarify that the agency remains accountable for the personal information (PIPEDA Principle 1)

### 2. Data Processing

- What personal information LogicalOutcomes processes (participant PII, staff accounts)
- Purpose limitation — LogicalOutcomes processes data only to operate the service, not for its own purposes
- No sale, sharing, or secondary use of agency data
- LogicalOutcomes staff access: limited to what's necessary for operations (infrastructure, troubleshooting, running exports on request). No access to decrypted participant data except when running an export at the agency's request.

### 3. Data Residency

- All data stored in Canada (Azure Canada Central, Toronto)
- Database backups stored in Canada
- No transfer of data outside Canada without written consent
- Reference: PIPEDA does not prohibit cross-border transfers but requires comparable protection. Canadian-only storage is a stronger position and matches agency expectations.

### 4. Security Measures

- Encryption at rest (Fernet / AES-128-CBC for PII fields, plus hosting provider's storage encryption)
- Encryption in transit (HTTPS / TLS)
- Role-based access control within the application
- Audit logging to a separate, locked-down database
- Authentication (Azure AD SSO or local with Argon2)
- Infrastructure security (Azure security defaults, network isolation, managed database)
- Encryption key management (stored separately from database, at least two people have access)

### 5. Backup and Recovery

- Database backups: frequency, retention period, storage location
- Encryption key backup: stored separately, retrievable
- Recovery time objective (RTO) and recovery point objective (RPO) if LogicalOutcomes is willing to commit to these
- Backup restore testing: how often, who verifies

### 6. Breach Notification

- LogicalOutcomes notifies the agency within [X hours] of discovering a breach
- The agency is responsible for notifying the Privacy Commissioner and affected individuals (as the accountable organisation under PIPEDA s. 10.1)
- LogicalOutcomes assists with breach investigation and response
- LogicalOutcomes maintains breach records as required by s. 10.3

### 7. Data Export and Portability

- Agency can request a full encrypted export at any time (Tier 2 — AES-256-GCM)
- SLA for routine exports: 5 business days
- SLA for PIPEDA data access requests: 48 hours
- Annual vendor-risk export included (one full export per year so the agency can demonstrate they aren't locked in)
- Plaintext export available if the agency signs the Data Export Acknowledgement (see [docs/data-handling-acknowledgement.md](../docs/data-handling-acknowledgement.md))
- Individual client exports available via the web interface (Tier 1 — SecureExportLink)

### 8. Service Levels

- Uptime commitment (if LogicalOutcomes is willing to offer one)
- Planned maintenance windows
- Support response times
- Escalation path

### 9. Termination and Data Return

- Either party can terminate with [X days] written notice
- Upon termination:
  - LogicalOutcomes produces a final encrypted export (AES-256-GCM)
  - Passphrase communicated by phone (not email)
  - Agency confirms receipt
  - LogicalOutcomes deletes all data (database, backups, encryption key) within [X days] of confirmed receipt
  - LogicalOutcomes provides written confirmation of deletion
- Audit log entries preserved separately per legal retention requirements before deletion

### 10. Subprocessors

- List of subprocessors (Azure, any monitoring tools, email providers)
- LogicalOutcomes notifies the agency before adding a new subprocessor
- All subprocessors must store data in Canada (or the agency consents in writing)

### 11. Schedules / Appendices

- **Schedule A: Data Export Acknowledgement** — the signed [data-handling-acknowledgement.md](../docs/data-handling-acknowledgement.md) (only if the agency opts in to plaintext exports)
- **Schedule B: Security Measures** — detailed technical description of safeguards
- **Schedule C: Subprocessor List** — current subprocessors with locations

---

## Process

1. **Draft** — GK drafts the recommended contents (this file serves as input)
2. **Legal review** — a lawyer reviews and drafts the actual agreement language
3. **Internal review** — LogicalOutcomes team reviews for operational feasibility (can we actually commit to these SLAs?)
4. **Template** — finalise a reusable template that can be customised per agency
5. **First use** — sign with [funder partner] during or before Phase 4 of deployment

## Related

- [docs/data-handling-acknowledgement.md](../docs/data-handling-acknowledgement.md) — plaintext export acknowledgement (Schedule A)
- [tasks/agency-data-offboarding.md](agency-data-offboarding.md) — export system design (Tier 1 + Tier 2)
- [tasks/design-rationale/no-live-api-individual-data.md](design-rationale/no-live-api-individual-data.md) — why no live API for individual PII
- [tasks/design-rationale/data-access-residency-policy.md](design-rationale/data-access-residency-policy.md) — data access tiers and residency requirements
- [tasks/hosting-cost-comparison.md](hosting-cost-comparison.md) — hosting models and cost structure
