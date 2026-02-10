# Export Permission Alignment

## Problem

All export views currently check `is_admin`, which conflates two responsibilities:
- **System configuration** (admin's actual job)
- **Client data access** (program manager's actual job)

The rest of the codebase already enforces the right model:
- Middleware blocks admins without program roles from client data
- Executives are redirected to aggregate dashboards
- Program managers see only their programs' clients

But the export views bypass all of this with a simple `is_admin` check.

## Decision (from expert panel analysis)

| Role | See client files? | Create PII exports? | Create aggregate exports? | Download own exports? | Manage/revoke links? |
|------|------------------|--------------------|--------------------------|-----------------------|---------------------|
| Front Desk | Limited fields | No | No | N/A | No |
| Staff | Full records | No | No | N/A | No |
| Program Manager | Their program | Yes (their program) | Yes (their program) | Yes | No |
| Executive | No (dashboard) | No | No | No | No |
| Admin (no roles) | No | Only client_data_export | No | Yes (own only) | Yes |

**Key principles:**
1. Export creation follows existing data access — if you can see the data, you can export it
2. Only the creator can download an export (the link is a deferred download, not a sharing mechanism)
3. Admin manages/revokes links (system oversight) but doesn't gain data access through exports
4. `client_data_export` stays admin-only — it's a migration/audit tool, not a reporting tool
5. Executives see aggregate dashboards only — no exports containing individual client records

## Current State (what exists)

### Files that check `is_admin` for exports:
- `apps/reports/views.py` — `export_form()` line ~174
- `apps/reports/views.py` — `funder_report_form()` line ~524
- `apps/reports/views.py` — `client_data_export()` line ~542
- `apps/reports/views.py` — `download_export()` line ~775
- `apps/reports/views.py` — `manage_export_links()` line ~836
- `apps/reports/views.py` — `revoke_export_link()` line ~862

### Nav visibility:
- `templates/base.html` line ~56 — Reports link inside `{% if user.is_admin %}` block

### What already works correctly:
- `konote/middleware/program_access.py` — blocks admin from client pages, redirects executive to dashboard
- `konote/context_processors.py` — sets `is_admin_only` and `is_executive_only` template vars
- `apps/auth_app/decorators.py` — `@minimum_role()` decorator with ROLE_RANK
- `apps/programs/models.py` — UserProgramRole with program-scoped roles

## Changes Required

### PERM1: Allow program managers to create metrics exports

**File:** `apps/reports/views.py` — `export_form()`

**Current:** `if not request.user.is_admin: return HttpResponseForbidden(...)`

**Change to:**
```python
# Admin can export any program; program managers can export their programs
if not request.user.is_admin:
    if not UserProgramRole.objects.filter(
        user=request.user, role="program_manager"
    ).exists():
        return HttpResponseForbidden("You need program manager access to create exports.")
```

**Also:** Filter the program dropdown to show only programs the user manages (unless admin):
```python
if request.user.is_admin:
    programs = Program.objects.all()
else:
    programs = Program.objects.filter(
        userprogramrole__user=request.user,
        userprogramrole__role="program_manager",
    )
```

### PERM2: Allow program managers to create funder report exports

**File:** `apps/reports/views.py` — `funder_report_form()`

Same pattern as PERM1 — check for program_manager role, scope program dropdown.

### PERM3: Keep client_data_export admin-only

**No change needed.** This is the full PII dump for data migration. Admin-only is correct.

### PERM4: Change download_export to creator-only + admin

**File:** `apps/reports/views.py` — `download_export()`

**Current:** `if not request.user.is_admin: return HttpResponseForbidden(...)`

**Change to:**
```python
# Creator can always download their own export
# Admin can download any export (for client_data_export which only admin creates)
can_download = (
    request.user == link.created_by
    or request.user.is_admin
)
if not can_download:
    return HttpResponseForbidden("You do not have permission to download this export.")
```

### PERM5: Keep manage/revoke admin-only

**No change needed.** Managing and revoking links is system oversight — admin's job.

### PERM6: Show Reports nav link for program managers

**File:** `templates/base.html`

**Current:** Reports link is inside `{% if user.is_admin %}` block.

**Change:** Move the Reports link to show for both admins and program managers:
```html
{% if user.is_admin or user_highest_role == "program_manager" %}
<li><a href="/reports/export/">{% trans "Reports" %}</a></li>
{% endif %}
```

**Also requires:** Adding `user_highest_role` to context processor (or checking UserProgramRole).

### PERM7: Add `can_export` helper to User model or utility

**File:** `apps/auth_app/models.py` or `apps/reports/utils.py`

Create a reusable helper to avoid repeating permission logic:
```python
def can_create_export(user, export_type, program=None):
    """Check if user can create an export of the given type."""
    if export_type == "client_data":
        return user.is_admin
    if user.is_admin:
        return True
    if export_type in ("metrics", "funder_report"):
        if program:
            return UserProgramRole.objects.filter(
                user=user, role="program_manager", program=program
            ).exists()
        return UserProgramRole.objects.filter(
            user=user, role="program_manager"
        ).exists()
    return False
```

### PERM8: Update tests

**File:** `tests/test_secure_export.py` (update existing) + new tests

Tests needed:
- Program manager CAN access metrics export for their program
- Program manager CANNOT access metrics export for another program
- Program manager CAN download their own export link
- Program manager CANNOT download someone else's export link
- Executive CANNOT access any export creation views
- Staff/front desk CANNOT access any export creation views
- Admin CAN create client_data_export
- Admin CAN manage/revoke any link
- Admin CAN download client_data_export they created
- Program manager CANNOT access client_data_export

### PERM9: Update context processor for nav visibility

**File:** `konote/context_processors.py`

Add a template variable like `has_export_access` that is True for admins and program managers:
```python
has_export_access = (
    request.user.is_admin
    or UserProgramRole.objects.filter(
        user=request.user, role="program_manager"
    ).exists()
)
```

### PERM10: Document the permission model

**File:** `docs/security-operations.md` or new `docs/permission-model.md`

Document:
- The role hierarchy and what each role can access
- Why admin != data access
- Why executive != client files
- The export permission matrix (the table at the top of this file)

## Dependencies

- No model changes needed (roles and UserProgramRole already exist)
- No migrations needed
- No new dependencies
- Changes are backward-compatible (currently more restrictive, we're loosening for PMs)

## Order of Implementation

1. PERM7 first (helper function — everything else uses it)
2. PERM9 (context processor — nav needs it)
3. PERM6 (nav visibility)
4. PERM1 + PERM2 (export creation views)
5. PERM4 (download permission)
6. PERM8 (tests)
7. PERM10 (documentation)

PERM3 and PERM5 are "no change" — just verifying the current behaviour is correct.
