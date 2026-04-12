---
drr: individual-data-rights
status: Draft - awaiting GK review
parent_principle: data-sovereignty
blast_radius: high
source: foundation-data-sovereignty.md §§"Individual Participant Rights" (2026-03-14)
enforcement:
  - type: pytest
    file: tests/drr/test_individual_rights.py
    description: "CorrectionRequest model exists and appends (not overwrites); ConsentEvent rejects UPDATE/DELETE at ORM layer; erasure requires two-person workflow"
  - type: django-system-check
    id: consent_event_append_only
    description: "Verify ConsentEvent model overrides save() to reject updates after creation; verify no DELETE grant on the table"
  - type: semgrep
    rule: no-silent-record-overwrite
    description: "Forbid direct overwrites of ProgressNote content fields; corrections must route through CorrectionRequest + amendment"
  - type: codeowner
    paths: [apps/clients/corrections.py, apps/clients/consent.py, apps/clients/erasure.py]
---

# DRR: Individual Data Rights (PIPEDA / PHIPA)

**Parent Principle:** [Data Sovereignty & Rights](../principles/data-sovereignty.md)

## Core Decision

Participants have four legally-recognised rights over their own records. KoNote implements each as a structural feature, not a process that depends on staff goodwill:

### 1. Correction

Participants can request corrections through the portal. The `CorrectionRequest` model supports both informal (discuss next session) and formal (written request) paths. Corrections are **appended as amendments** — the original record is preserved with an amendment notation, not silently overwritten. This protects both the participant's right to accuracy and the clinical record's integrity.

### 2. Access

The participant portal is the self-service implementation of PIPEDA's access right. Participants view their own goals, notes, and progress without filing a formal request. This is a **structural implementation of a legal right**, not a convenience feature. Making participants submit formal requests with a 30-day response window creates a power asymmetry that discourages people from exercising their rights.

### 3. Erasure

A two-person workflow: Program Manager requests, Admin approves. (See [two-person-safety-actions](two-person-safety-actions.md) for the approval mechanism.) PII is stripped; the anonymised record is retained for aggregate statistics. **Irreversible by design** — prevents accidental or coerced reversal. Once approved, no one (including developers, hosting admins, or the agency itself) can reconstruct the individual's identity from remaining data.

### 4. Ongoing Consent

The `ConsentEvent` model is **append-only**: grant and withdraw events with reasons and timestamps. Consent is never a single checkbox at intake that covers everything forever. Cross-program sharing is per-client configurable. Consent to aggregate reporting is explicit opt-in, not opt-out.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| Silent overwrite of corrected records | Destroys clinical record integrity; breaks audit trail |
| Formal access requests required for self-viewing | Power asymmetry discourages rights exercise |
| Single-person erasure | Coercion and error risk are unrecoverable |
| One-time blanket consent at intake | Violates meaningful-consent requirement under PIPEDA/PHIPA |
| Consent as an overwritten boolean ("client_consents = True/False") | Loses the history of grants and withdrawals required by law |
| "Soft delete" that leaves PII recoverable | Participant exercised erasure; PII recovery defeats the right |

## CI enforcement (detail)

1. **Pytest** — (a) create a correction request, apply it, assert original record is preserved + amendment appended, (b) attempt to UPDATE a `ConsentEvent` after creation → expect `PermissionError`, (c) attempt erasure with a single user → expect failure (routes to two-person workflow), (d) complete erasure, confirm no PII-bearing field contains reconstructable data.
2. **Django system check** validates `ConsentEvent.save()` raises on post-creation updates and that the DB role has no DELETE grant on `consent_event`.
3. **Semgrep rule** `no-silent-record-overwrite` forbids direct `.save()` on `ProgressNote` content fields outside the correction/amendment pipeline.
4. **CODEOWNERS** on the implementing files.

## When to revisit

If PIPEDA or provincial privacy legislation is amended in ways that change the scope of these rights (e.g., adds data-portability-on-demand or removes the informal path for corrections), update this DRR. The structural-rather-than-procedural implementation should not change.

## Related DRRs

- [two-person-safety-actions](two-person-safety-actions.md) — erasure uses the two-person mechanism
- [phipa-consent-enforcement](phipa-consent-enforcement.md) — consent state recorded here is filtered at query time
- [audit-log-isolation](audit-log-isolation.md) — correction, erasure, and consent changes are audited
- [no-live-api-individual-data](no-live-api-individual-data.md) — access rights are served via portal, not live API
