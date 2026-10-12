---
role: principle
status: Draft - awaiting GK review
source: foundation-security-by-default.md (2026-03-14)
note: "This principle is a hub. All 10 specific security decisions have been extracted into dedicated, enforceable DRRs. This document retains only the guiding principle itself."
---

# Principle: Security by Default

**High Security for Non-Technical Operators**

> **In plain language:** KoNote is secure even if you don't have an IT team. Every security protection is built into the system and turned on by default — you can't accidentally make it insecure by misconfiguring a setting. If something goes wrong, the system blocks access rather than leaking data.

---

## Core Principle

Canadian nonprofits handle deeply sensitive personal information — mental health notes, domestic violence documentation, substance use records, immigration status — but typically lack dedicated IT security staff. KoNote's security model is therefore **architectural, not configurable**. Security is enforced by the structure of the code, not by policies that a non-technical admin might misconfigure.

Three commitments follow from this:

1. **On by default.** Every security control is enabled when the system is installed. No toggles in the admin UI to disable them.
2. **Fails closed.** If a control cannot determine whether an action is safe, it denies the action. Over-restriction is recoverable; over-exposure is not.
3. **Loud on misconfiguration.** When a security-critical setting is wrong (missing key, missing migration, malformed matrix), the application refuses to start — rather than running in an insecure state silently.

For example: the encryption key is validated on every boot by decrypting a sample record. If the key is missing, corrupt, or misconfigured, the application refuses to start. Misconfiguration becomes a loud, immediate failure — not a silent data exposure. That pattern (fail-closed, fail-loud, architectural) is the template every security DRR in the table below follows.

## The Guiding Test

Ask of any proposed feature or configuration:

> **"If a nonprofit runs this with zero IT expertise, can they accidentally make it insecure?"**

If the answer is yes, the security control is not architectural enough. Rework it until the answer is no.

## When to Revisit

If the Canadian nonprofit sector develops shared security infrastructure (e.g., a nonprofit SOC service or sector-wide managed security), some operational controls could potentially be relaxed. The principle itself — security must be architectural, not configurable — should not change.

---

## Implementation DRRs

The 10 prescriptive decisions that previously lived in this document have been extracted into dedicated DRRs. Each of those DRRs is independently enforceable by CI:

| Decision | Implementation DRR |
|---|---|
| Encryption at rest for all PII | [encryption-key-rotation](../design-rationale/encryption-key-rotation.md) |
| RBAC permission matrix as single source of truth | [access-tiers](../design-rationale/access-tiers.md) |
| Fail-closed consent filtering | [phipa-consent-enforcement](../design-rationale/phipa-consent-enforcement.md) |
| Immutable audit log in separate database | [audit-log-isolation](../design-rationale/audit-log-isolation.md) (NEW) |
| Negative access lists (`ClientAccessBlock`) | [access-tiers](../design-rationale/access-tiers.md) |
| Session security (timeout, cookies, CSP) | [session-security](../design-rationale/session-security.md) (NEW) |
| Rate limiting and account lockout | [rate-limiting-and-authentication](../design-rationale/rate-limiting-and-authentication.md) (NEW) |
| Two-person safety rules | [two-person-safety-actions](../design-rationale/two-person-safety-actions.md) (NEW) |
| Time-limited secure export links | [no-live-api-individual-data](../design-rationale/no-live-api-individual-data.md) |
| Demo mode isolation | [demo-mode-isolation](../design-rationale/demo-mode-isolation.md) (NEW) |

## Related Principles

- **Data Sovereignty** — security controls are the enforcement layer for sovereignty principles
- **Collaborative Practice** — session security and CSP protect the participant portal; two-person rules protect DV participants
- **Nonprofit Sustainability** — security must be zero-config to be affordable
