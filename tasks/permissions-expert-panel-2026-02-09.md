# Expert Panel: Permissions Matrix Critical Review

**Date:** 2026-02-09
**Source of truth:** `konote-web/apps/auth_app/permissions.py`
**Panel:** Privacy Lawyer (PIPEDA/PHIPA), Nonprofit Operations Director, Security Architect, Clinical Social Worker (RSW)

## Immediate changes to permissions.py

| # | Change | Keys | Receptionist | Staff | PM | Executive | Rationale |
|---|--------|------|-------------|-------|-----|-----------|-----------|
| 1 | Add `client.create` | New | ALLOW | SCOPED | DENY | DENY | PIPEDA 4.3: collection requires permission. Receptionist intake is standard. |
| 2 | Add `client.edit_contact` | New | ALLOW | SCOPED | DENY | DENY | #1 write operation at front desk. Currently blocked by `client.edit: DENY`. |
| 3 | Add `privacy.access_request` | New | DENY | DENY | ALLOW | ALLOW | PIPEDA s. 8 obligation. Separate from `report.data_extract`. |
| 4 | Add `consent.withdraw` | New | DENY | DENY | GATED | DENY | Consent withdrawal triggers legal obligations. Higher bar than routine consent. |
| 5 | Add `note.co_sign` | New | DENY | DENY | ALLOW | DENY | Clinical supervision workflow. PM reviews without editing. |
| 6 | Change executive admin | Modify | - | - | - | ALLOW x3 | `user.manage`, `settings.manage`, `programme.manage` all DENY→ALLOW. |
| 7 | Change PM admin (scoped) | Modify | - | - | SCOPED x3 | - | `programme.manage`, `audit.view`, `user.manage` DENY→SCOPED. No role elevation. |

## Comments to add in permissions.py

- `client.view_safety` → cite PHIPA s. 30(2): "reasonably necessary for the purpose"
- `client.create` → cite PIPEDA Principle 4.3: collection requires identified purpose
- `privacy.access_request` → cite PIPEDA s. 8: individual right of access
- `client.view_clinical` for PM → add: `# ALLOW (Phase 1). MUST become GATED in Phase 2.`
- `user.manage` for PM → add: `# SCOPED: own program team. Cannot elevate roles.`

## Deferred to Phase 2

- `report.funder_report` separate key (view logic handles it for now)
- `client.transfer` permission (model as edit for now)
- `plan.template_edit` for PM (operational, not compliance)
- `alert.escalate` (low frequency)
- PM clinical access GATED (requires time-boxing infrastructure)
- `consent.modify_scope` (real need, not urgent)
- `dashboard.view_individual` vs `dashboard.view_aggregate` (view logic for now)

## Key insight: consent.manage should be split (3 actions)

| Action | Current key | Proposed key | Bar |
|--------|------------|-------------|-----|
| Record consent at intake | `consent.manage` | `consent.record` (or keep `consent.manage`) | Routine |
| Change sharing scope | `consent.manage` | `consent.modify_scope` (Phase 2) | Medium |
| Withdraw consent / trigger deletion | `consent.manage` | `consent.withdraw` | GATED + supervisor |

## Safety/medications boundary: CONFIRMED CORRECT

- `client.view_safety: ALLOW` for receptionist = duty of care (seizures, allergies, staff alerts)
- `client.view_medications: DENY` for receptionist = medications reveal diagnosis
- Panel unanimous: this is the right line. Add PHIPA s. 30(2) citation.

## PM role elevation constraint

When `user.manage: SCOPED` is implemented for PM:
- PM can create/deactivate staff accounts within own program
- PM can reset passwords for own program staff
- PM CANNOT create PM or executive accounts
- PM CANNOT change a receptionist to staff (grants clinical access)
- Enforcement: application logic, not just permissions.py (needs a `user.manage.no_elevation` flag or separate `user.elevate_role: DENY`)
