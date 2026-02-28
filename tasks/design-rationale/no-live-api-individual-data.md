# No Live API for Individual Participant Data

**Date:** 2026-02-27
**Status:** Decided — GK
**Panels:** 3 expert panels (access model, encryption, brittleness/maintainability)

---

## What Was Requested

Potential users asked for API access to connect individual participant data from KoNote to another database within the same agency. They were not talking about aggregate data — they were asking for real-time access to individual client PII across systems.

## Why It Was Rejected

KoNote's security model is built on a core principle: **PII stays inside the encrypted boundary.** A live API that serves decrypted participant data to external systems fundamentally breaks this.

### 1. You're only as secure as the weakest link

Once data flows through an API into another database, KoNote's Fernet encryption, RBAC, PHIPA consent filtering, and audit logging no longer protect it. The receiving system's security becomes the ceiling — and KoNote has no control over that system.

### 2. Persistent attack surface

A live API means credentials exist somewhere that can query any individual's data at any time. If those credentials are compromised (leaked in a config file, stolen from the other system), the attacker gets real-time access to all participant PII. Compare this to an export, which is a one-time event that produces a file.

### 3. Consent model bypass

KoNote has careful cross-program PHIPA consent enforcement. A live API would need to replicate all of that logic perfectly, and any bug would be a privacy breach. More importantly, the *other system* has no concept of KoNote's consent model — once the data crosses the boundary, consent controls vanish.

### 4. Audit trail degradation

With automated API calls, you get thousands of access records that are impossible to meaningfully review. A deliberate export generates one auditable event per action.

### 5. Scope creep is inevitable

"We just need to connect one field" becomes "can we sync all notes nightly?" Agencies wouldn't be doing this maliciously — they'd be solving operational problems. But the effect is the same: a data pipeline that replicates decrypted PII outside the security perimeter.

## The Analogy

**Live API** = a hole in the wall that's always open.
**Export function** = a locked door that opens when an authorised person turns the key, and a camera records who walked through.

The users are asking for the hole. Give them the door.

## What to Offer Instead: Two-Tier Export Model

### Tier 1 — Individual Client Export

For PIPEDA data access requests, program transfers, or giving a client their own data.

- Staff initiates from the client profile ("Export Client Data")
- Delivered via **SecureExportLink** — time-limited HTTPS download (24h expiry, single-use, logged, revocable)
- No file-level encryption — the secure transport IS the protection (one person's data, limited blast radius)
- Staff chooses format:
  - **PDF** — human-readable, for giving to clients or printing
  - **JSON** — machine-readable nested structure, for importing into another CMS
- JSON includes human-readable labels alongside raw values (e.g., `"progress_descriptor": {"value": 3, "label": "Some progress"}`)

### Tier 2 — Full Agency Export

For agency offboarding, CMS migration, or key-loss insurance backup.

- Via Django management command (`export_agency_data`) — CLI only, no web endpoint
- **AES-256-GCM encryption** (not password-protected ZIP)
  - PBKDF2 key derivation (SHA-256, 600k+ iterations, random salt)
  - Salt and IV in file header with version byte
  - Self-contained HTML/JS browser-based decryptor (Web Crypto API, fully offline, CSP-locked)
  - Diceware passphrase communicated by phone — never email
- Full config + data (everything needed to reconstruct the instance)
- Automatic model discovery (exclusion list pattern — new models included by default)
- Dual JSON structure: flat files per model (machine import) + nested client-centric (human reading)

### Who Runs It

| Hosting model | Who runs the export | Backup cadence |
|---|---|---|
| Self-hosted | Agency's server admin (self-serve) | Agency decides; automated reminders |
| SaaS (Railway/Azure) | KoNote team on request | Annual vendor-risk export; automated reminders to agency contact |

SLA for SaaS: 5 business days routine, 48 hours for PIPEDA requests.

## Anti-Patterns — Do Not Build

| Anti-pattern | Why |
|---|---|
| **REST/GraphQL API for individual PII** | Persistent attack surface, consent bypass, audit degradation |
| **Bidirectional sync between KoNote and another system** | Same problems as API, plus introduces conflict resolution complexity and data integrity risks |
| **Automated scheduled PII transfers** (cron job pushing data to external system) | Creates a pipeline that replicates decrypted PII outside the security boundary without human oversight |
| **Webhook-based data push** (notify external system when client data changes) | Turns every write into an external data transmission; scope creep by design |
| **Shared database access** (giving another system read access to KoNote's database) | Bypasses application-level encryption, consent, and RBAC entirely |
| **FHIR API for individual clinical data** | FHIR is designed for interoperability between clinical systems with mutual trust and consent infrastructure. KoNote's agencies don't have that infrastructure. A FHIR API would be a sophisticated-looking version of the same hole in the wall. (CIDS JSON-LD export for *aggregate/program-level* data is different and is planned.) |

## What This DRR Does NOT Restrict

- **Aggregate/de-identified data sharing** — cross-agency reporting, funder reports, CIDS exports. These don't contain individual PII and are governed by separate consent (consent_to_aggregate_reporting).
- **The PIPEDA guided checklist** (already built) — staff-guided manual process for data access requests. Tracks the 30-day deadline and logs completion.
- **The export functions described above** — deliberate, auditable, human-initiated data exports.

## Future Considerations

If KoNote scales to 20+ SaaS agencies, the manual export process for Tier 2 may become a burden. At that point, consider a **self-service request portal** — a web-based workflow where an authorised agency admin requests an export, KoNote's system runs the command automatically, and the encrypted file is delivered via SecureExportLink. This reintroduces a web-initiated path but with proper controls (role-gated, audit-logged, encrypted output, time-limited link). Don't build this now.

## Related Documents

- `tasks/agency-data-offboarding.md` — SEC3 design (Tier 2 implementation details)
- `tasks/pipeda-data-access-checklist.md` — PIPEDA checklist design (already built)
- `tasks/design-rationale/phipa-consent-enforcement.md` — consent model and enforcement
- `tasks/design-rationale/data-access-residency-policy.md` — data access tiers
