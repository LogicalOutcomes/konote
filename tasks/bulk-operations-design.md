# Bulk Operations — Redesign (BULK1)

## Summary

Replace the confusing checkbox + sticky-bar bulk operations on the participant list with dedicated wizard pages accessible from the **Manage** dropdown. Each operation gets its own page with a clear filter → select → confirm → done flow.

## Expert Panel Decision (2026-03-07)

Panel: Nonprofit Case Management UX Designer, PHIPA/Privacy Compliance Specialist, Django/HTMX Application Architect, Human Services Program Manager.

### Consensus

| Decision | Recommendation |
|----------|---------------|
| Operations at launch | Transfer Participants, Discharge Participants |
| Deferred (Phase 2) | Assign Staff |
| Location in UI | Manage dropdown, separated from config items by a divider |
| Interaction pattern | Wizard: Filter → Select → Confirm → Done |
| Default selection | "Select All" prominent; consent-flagged participants visually marked |
| Consent handling | Informational warnings at confirmation, not blocking |
| Audit | Individual log entry per participant per operation |
| Discharge reason | Mandatory dropdown field |
| Access control | Manager + Admin only (client.transfer permission) |
| Session storage | Server-side with 30-minute expiry |
| Technical pattern | Dedicated views, HTMX for filter refinement, transaction.atomic() |

### Why the old design was removed

The previous bulk operations (PR #64, UX17) used checkboxes on the regular participant list with a sticky action bar. Users found this confusing because:
- Checkboxes appeared on a page they use daily for normal work
- The sticky bar was easy to miss
- No clear task framing — felt like the list had changed

### Anti-patterns (do not re-introduce)

- Inline bulk controls on the participant list page
- Bulk operations that skip the confirmation step
- Single audit log entry for a batch (must be per-participant)
- Blocking on consent warnings (should be informational)

## GK Review

GK should review whether transfers should ever be blocked (not just warned) on consent grounds — e.g., transfers to external agencies vs. internal transfers.
