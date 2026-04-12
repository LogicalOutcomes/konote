---
drr: audit-log-isolation
status: Draft - awaiting GK review
parent_principle: security-by-default
blast_radius: high
source: foundation-security-by-default.md §4 (2026-03-14)
enforcement:
  - type: django-system-check
    id: audit_db_role_insert_only
    description: "Verify audit DB role has INSERT privilege only, not UPDATE or DELETE"
  - type: pytest
    file: tests/drr/test_audit_log_immutability.py
    description: "Assert ORM raises PermissionError on AuditLog.save() for existing records and on .delete()"
  - type: codeowner
    paths: [apps/audit/, konote/settings.py]
---

# DRR: Audit Log Isolation

**Parent Principle:** [Security by Default](../principles/security-by-default.md)

## Core Decision

All state-changing requests, client record views, and failed access attempts are logged to a **separate PostgreSQL database** (the "audit DB"). The audit DB is reachable only via a role that has `INSERT` privilege — not `UPDATE`, not `DELETE`. The Django ORM additionally raises `PermissionError` on any attempt to modify or delete an audit record through application code.

A compromised application cannot alter its own evidence trail. A compromised audit is worse than no audit.

## What this means in code

- Audit records route to the `audit` database via `AuditLog.objects.using("audit")`.
- The PostgreSQL role used for the audit connection has its grants limited to `INSERT` on audit tables. Running `UPDATE audit_log SET ... ` through psql with that role must fail at the database level.
- The `AuditLog` model (and any model in `apps.audit`) overrides `save()` and `delete()` to raise `PermissionError` for any call that is not the initial INSERT.
- Audit DB backups run on a separate schedule and are stored separately from application DB backups.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| Audit logs in the same database as application data | Compromised app = compromised evidence trail |
| Granting the audit role UPDATE or DELETE "just for migrations" | Migrations should not mutate historical audit records. Use append-only schema evolution. |
| Writing audit from the same DB connection as application queries | Transaction rollback could drop audit entries with the failed operation |
| Deleting "old" audit records to save space | Audit records are evidence; retention policy is a separate, documented decision with legal implications |

## CI enforcement (detail)

1. **Django system check** `audit_db_role_insert_only` runs on app boot. It connects as the audit role and attempts a dry-run `UPDATE`; if it succeeds, the check raises a critical error and the app refuses to start.
2. **Pytest** `tests/drr/test_audit_log_immutability.py` creates an `AuditLog` record, reloads it, mutates a field, and asserts `save()` raises `PermissionError`. Same for `delete()`.
3. **CODEOWNERS** — changes to `apps/audit/` or to the audit DB settings require review by a DRR steward.

## When to revisit

If the sector adopts an external tamper-evident logging service (e.g., a nonprofit-sector audit escrow) that can provide stronger integrity guarantees than separate-DB-plus-role isolation, the architecture could evolve. The principle — the audit trail cannot be altered by the application — must not change.

## Related DRRs

- [phipa-consent-enforcement](phipa-consent-enforcement.md) — consent events are recorded to the audit DB
- [two-person-safety-actions](two-person-safety-actions.md) — safety-critical actions emit audit events
- [access-tiers](access-tiers.md) — permission denials are audit events
