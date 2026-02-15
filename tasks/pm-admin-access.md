# PM Admin Access — Phase Plan

**Goal:** Let Program Managers configure templates, event types, metrics, registrations, and team members for their own programs — without needing full admin access.

**Current state:** All admin views use `@admin_required` (binary `is_admin` check). PMs can't access any of them, even though the permission matrix already grants PMs `user.manage: SCOPED`, `program.manage: SCOPED`, and `audit.view: SCOPED`.

## Priority tiers

### High priority (core PM responsibilities)

| Feature | Current auth | New permission key | PM level |
|---------|-------------|-------------------|----------|
| Plan Templates | `@admin_required` | `template.plan.manage` | SCOPED |
| Note Templates | `@admin_required` | `template.note.manage` | SCOPED |
| Event Types | `@admin_required` | `event_type.manage` | SCOPED |

### Medium priority

| Feature | Current auth | New permission key | PM level |
|---------|-------------|-------------------|----------|
| Metrics | `@admin_required` | `metric.manage` | SCOPED |
| Registration Links | `@admin_required` | `registration.manage` | SCOPED |
| Team Members | `@admin_required` | `user.manage` (exists) | SCOPED (exists) |

### Keep admin-only

| Feature | Reason |
|---------|--------|
| Settings (terminology, features, instance) | Org-wide, affects all users |
| Report Templates | Funder compliance, cross-program |
| Merge Duplicates | Destructive, cross-program data operation |
| Invites | Elevation risk — PM could create invite with admin/PM role (keep admin-only for now) |

## Implementation pattern (same for each template/config feature)

Each feature follows the same five steps:

### 1. Add permission key to the matrix

In `apps/auth_app/permissions.py`, add the new key to all four roles:

- Receptionist: DENY
- Staff: DENY
- Program Manager: SCOPED
- Executive: DENY

Update the `permission_to_plain_english()` translations dict too.

### 2. Scope the model to programs

Currently PlanTemplate, ProgressNoteTemplate, EventType, and MetricDefinition are **global** (no program FK). To scope them for PM access:

- Add `owning_program = models.ForeignKey(Program, null=True, blank=True, on_delete=SET_NULL)` — named `owning_program` (not `program`) to avoid confusion with existing `program` FKs that mean "applied to program"
- `null=True` means existing records remain global (admin-created)
- PMs can only create/edit items where `owning_program` matches one of their programs
- Admin-created items (`owning_program=None`) are visible to all but only editable by admins
- Run `makemigrations` and `migrate`

This is the least disruptive approach — no data migration needed, existing templates keep working.

### 3. Replace decorator on views

Change `@admin_required` to `@requires_permission("new.key", allow_admin=True)`:

- `allow_admin=True` keeps admin access working exactly as before
- PMs get access through the permission matrix
- The decorator validates the key at import time

### 4. Scope querysets in views

In list/edit views, filter based on role:

- **Admins:** see everything (no filter)
- **PMs:** see items where `owning_program__in=user_programs` OR `owning_program=None` (read-only for global)
- Edit views: check that the item belongs to the PM's program before allowing changes

### 5. Update navigation (incrementally per feature)

As each feature lands, add its nav link using `{% has_permission "new.key" %}` so PMs can see and test their new access immediately — don't wait until the end.

## Team Members — special handling (PM-ADMIN2)

`user.manage: SCOPED` already exists in the matrix. The elevation constraint logic is already coded in `admin_views.py` lines 187–208 (`_PM_BLOCKED_ROLE_ASSIGNMENTS`), but never fires because `@admin_required` gates the whole file.

### What swapping the decorator activates

- PMs blocked from assigning `program_manager` or `executive` roles
- PMs blocked from elevating `receptionist` to `staff` (grants clinical access)

### Additional constraints needed

1. **`user_create` form** — `UserCreateForm` has an `is_admin` checkbox. Must enforce `is_admin = False` server-side for non-admin request users (not just hide the checkbox — server-side enforcement).
2. **`user_edit` form** — `UserEditForm` also has `is_admin`. Same fix: enforce server-side that non-admins cannot set `is_admin = True`.
3. **Invite views stay admin-only** — a PM could otherwise create an invite with `role="admin"` or `role="program_manager"`, bypassing elevation constraints entirely.
4. **Scope user list** — PMs see only users who share a program assignment.
5. **Scope user_edit/deactivate** — PMs can only modify users in their programs.

### What PMs can do

- Create staff/receptionist accounts in their program
- Deactivate users in their program
- Reset passwords for their program staff
- View user list filtered to their programs

## Registration — special handling

Registration links are already associated with programs (the link targets a specific program). The work is:

1. Add `registration.manage` permission key
2. Replace `@admin_required` with `@requires_permission("registration.manage", allow_admin=True)`
3. Filter links/submissions to the PM's programs

## Risks and considerations

- **Template visibility:** A PM in Program A should not be able to see or copy templates from Program B. Global (admin-created) templates are shared read-only.
- **Audit trail:** All template/config changes by PMs must be logged (already handled by AuditLog middleware if views use standard patterns).
- **Role elevation:** The `user.manage` constraint logic exists but needs hardening in `user_create` and `user_edit` forms — the `is_admin` field is the main gap.
- **Migration safety:** Adding nullable FKs is safe (no data loss, no backfill needed).
- **Invite bypass:** Invites stay admin-only to prevent elevation via invite link creation.

## Implementation order

| Step | ID | Task | Notes |
|------|----|------|-------|
| 1 | PM-ADMIN1 | Add all permission keys to matrix | Foundation — zero runtime impact |
| 2 | PM-ADMIN2 | Team Members (users + roles) | Highest day-to-day value; harden `is_admin` enforcement in create/edit forms |
| 3 | PM-ADMIN3 | Plan Templates + Note Templates | Similar pattern, batch them; add `owning_program` FK |
| 4 | PM-ADMIN4 | Event Types | Same pattern as templates |
| 5 | PM-ADMIN5 | Metrics | Less frequent PM task |
| 6 | PM-ADMIN6 | Registration Links | Already program-scoped |
| 7 | PM-ADMIN7 | Nav updates | Incremental — add links as each feature lands, final polish pass at end |
