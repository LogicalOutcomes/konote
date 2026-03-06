# REFACTOR1: Extract Role String Constants

**Status:** Ready to build
**Branch:** `refactor/role-constants`
**PR target:** `develop`

## Background

The codebase has 400+ raw string literals like `"receptionist"`, `"staff"`, `"program_manager"` etc. scattered across views, models, commands, and tests. These should be constants in `apps/auth_app/constants.py`.

**Naming decision (expert panel, 2026-03-05):** Constants match DB values, not display labels. Rationale:
- DB values are migration-locked and stable; display labels have already changed once ("Receptionist" to "Front Desk") and may change again
- Mechanical find-and-replace is safer when constant names match the strings they replace
- `ROLE_RANK` already uses DB values as keys — one convention per file
- Follows Django `TextChoices` convention

## Step 1: Update `apps/auth_app/constants.py`

Add role constants with a comment block mapping to display labels:

```python
"""Shared constants for role-based access control."""

# Role constants - values match database/model choices.
# Display labels (shown in UI) are defined in UserProgramRole.ROLE_CHOICES.
#
#   ROLE_RECEPTIONIST    -> "Front Desk"
#   ROLE_STAFF           -> "Direct Service"
#   ROLE_PROGRAM_MANAGER -> "Program Manager"
#   ROLE_EXECUTIVE       -> "Executive"
#   ROLE_ADMIN           -> "Administrator"

ROLE_RECEPTIONIST = "receptionist"
ROLE_STAFF = "staff"
ROLE_PROGRAM_MANAGER = "program_manager"
ROLE_EXECUTIVE = "executive"
ROLE_ADMIN = "admin"

# Convenience sets
ALL_PROGRAM_ROLES = {ROLE_RECEPTIONIST, ROLE_STAFF, ROLE_PROGRAM_MANAGER, ROLE_EXECUTIVE}
CLIENT_ACCESS_ROLES = {ROLE_RECEPTIONIST, ROLE_STAFF, ROLE_PROGRAM_MANAGER}

# Higher number = more access.
# Executive has highest rank but no client data access.
ROLE_RANK = {
    ROLE_RECEPTIONIST: 1,
    ROLE_STAFF: 2,
    ROLE_PROGRAM_MANAGER: 3,
    ROLE_EXECUTIVE: 4,
}
```

## Step 2: Replace raw strings across Python files

Search for `"receptionist"`, `"staff"`, `"program_manager"`, `"executive"`, `"admin"` used as role comparisons and replace with the constants. Import from `apps.auth_app.constants`.

### Files to update (grep to confirm exact list):

**apps/auth_app/**
- `models.py` — role references in logic (NOT in ROLE_CHOICES tuples)
- `views.py`
- `admin_views.py`
- `invite_views.py`
- `decorators.py`
- `permissions.py`
- `checks.py`

**apps/programs/** — models, views, `access.py`

**apps/clients/, apps/plans/, apps/reports/** — any role string comparisons

**Management commands:**
- `validate_permissions.py`
- `security_audit.py`

**Tests** — all test files referencing role strings

### DO NOT touch:
- **Migrations** — never modify migration files
- **Templates** — role strings in templates are handled differently
- **`.po` files** — translation files
- **`GroupMembership` roles** — these are a different concept (group roles, not program roles)
- **`ROLE_CHOICES` tuples** in `models.py` — the first element of each tuple must stay as a raw string (Django stores this in DB)

### Replacement guidance:
- `if role == "receptionist":` -> `if role == ROLE_RECEPTIONIST:`
- `role="staff"` in queryset filters -> `role=ROLE_STAFF`
- `{"receptionist", "staff"}` sets -> use `CLIENT_ACCESS_ROLES` if it matches, otherwise build from constants
- `for role in ["receptionist", "staff", ...]` -> use `ALL_PROGRAM_ROLES` or explicit constant list
- `ROLE_RANK["executive"]` -> already handled by Step 1 (ROLE_RANK keys are now constants)

## Step 3: Run targeted tests

```bash
pytest tests/test_permissions_enforcement.py tests/test_clients.py tests/test_reports.py tests/test_exports.py -v
```

All tests should pass with no changes to test logic (only string replacements).

## Step 4: Commit and PR

- Branch: `refactor/role-constants`
- PR to `develop`
- Commit message: `refactor: extract role string constants into auth_app/constants.py`
