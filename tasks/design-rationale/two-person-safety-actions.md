---
drr: two-person-safety-actions
status: Draft - awaiting GK review
parent_principle: security-by-default
blast_radius: high
source: foundation-security-by-default.md §8 (2026-03-14)
enforcement:
  - type: pytest
    file: tests/drr/test_two_person_workflows.py
    description: "Assert alert cancellation, DV flag removal, and data erasure each require two distinct user IDs to complete"
  - type: pytest
    file: tests/drr/test_two_person_token_expiry.py
    description: "Approval requests for alert cancel, DV flag removal, and erasure are rejected when the approval token is older than TWO_PERSON_APPROVAL_TTL_MINUTES (15 minutes) — see Core Decision"
  - type: semgrep
    rule: two-person-action-requires-approver
    description: "Any view or management command that completes one of the protected actions must accept and validate a distinct approver_id"
  - type: codeowner
    paths: [apps/events/views.py, apps/clients/dv_views.py, apps/clients/erasure.py, apps/clients/erasure_views.py]
---

# DRR: Two-Person Safety Actions

**Parent Principle:** [Security by Default](../principles/security-by-default.md)

## Core Decision

Certain actions are safety-critical: an error, coercion, or compromised account must not be sufficient to complete them. Three classes of action require **two distinct people** to execute — a requester and a separate approver:

| Action | Requester | Approver |
|---|---|---|
| Alert cancellation | Any staff | Program Manager or higher |
| DV (domestic violence) flag removal | Any staff | Program Manager or higher |
| Participant data erasure | Program Manager | Admin |

No single person — regardless of role — can complete any of these actions alone. The requester and approver must have distinct user IDs. The action is recorded to the audit log with both identities.

This protects against both **human error** (a single slip doesn't cause irreversible harm) and **coercion** (a staff member under pressure from a client's abuser cannot unilaterally remove a safety flag).

**Approval tokens are time-limited.** Each approval request carries a token (or equivalent server-side expiry stamp) that is valid for **`TWO_PERSON_APPROVAL_TTL_MINUTES = 15`** from the moment the requester files it. After 15 minutes the approval must be re-requested. This matches the session-inactivity and account-lockout cadence and narrows the window for leisure-coercion against an approver who is later confronted with a stale request.

**Implementation anchor.** Alert cancellation uses the existing `recommend_cancel` / `review_cancel_recommendation` pair in `apps/events/views.py` (see `alert_cancel` and `alert_recommend_cancel`). DV-flag removal lives in `apps/clients/dv_views.py`. Participant erasure lives in `apps/clients/erasure.py` + `apps/clients/erasure_views.py`. A shared helper — `require_two_person_approval(action, requester, approver)` — is to be created in `apps/auth_app/decorators.py` (or a new `apps/auth_app/two_person.py`) and adopted by all three workflows; the Semgrep rule below enforces adoption.

**Governance note.** If the only Program Manager is the requester, the action waits until a second PM (or higher) is available. Agencies with a single PM accept this as a governance trade-off; the rule is architectural, not configurable.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| Any of these actions completable by one user | Human error or coercion becomes unrecoverable |
| Approver field accepting the requester's own user ID | Defeats the purpose |
| "Emergency override" bypass for admins | Admins are exactly the accounts most worth coercing; no bypass |
| Approval via an "accept all pending" batch action | Removes the per-action deliberation that is the control |
| Approval request reusable across sessions (persistent link) | Enables coercion at leisure; requests must be per-action and time-limited |

## CI enforcement (detail)

1. **Pytest** `tests/drr/test_two_person_workflows.py` — for each of the three workflows: (a) attempt to complete as a single user → expect failure, (b) complete with requester == approver → expect failure, (c) complete with distinct requester and approver of appropriate roles → expect success AND audit record with both IDs.
2. **Pytest** `tests/drr/test_two_person_token_expiry.py` — file an approval request, fast-forward time past `TWO_PERSON_APPROVAL_TTL_MINUTES`, attempt to complete the approval → expect rejection. Covers all three workflows.
3. **Semgrep rule** scans `apps/events/views.py`, `apps/clients/dv_views.py`, and `apps/clients/erasure*.py` (plus any future view that performs one of the protected actions) and flags any completion path that does not call `require_two_person_approval(action, requester, approver)`.
4. **CODEOWNERS** on the implementing files.

## When to revisit

If KoNote adds additional safety-critical actions (e.g., deleting or transferring a consortium, rotating tenant encryption keys), they should be added to this DRR's enforcement table rather than invented fresh. The list of protected actions is expected to grow; the two-person pattern itself should not be weakened.

## Related DRRs

- [individual-data-rights](individual-data-rights.md) — erasure workflow is one of the three protected actions here
- [audit-log-isolation](audit-log-isolation.md) — both identities are recorded
- [access-tiers](access-tiers.md) — role eligibility for approver is governed by RBAC
