# Permissions Enforcement Wiring — Implementation Plan

**Created:** 2026-02-09
**Source:** Three expert panel reviews + enforcement gap analysis
**Goal:** Make `permissions.py` the actual single source of truth by wiring all enforcement layers to read from it.

---

## Background

`permissions.py` defines a 4-role × 40+ key matrix, but only 1 of 40+ permission checks actually reads from it. The rest are hardcoded: 29 `@programme_role_required("staff")`, 14 `@minimum_role("staff")`, 66 `@admin_required`, plus middleware and template checks. This means changing `permissions.py` has no effect on runtime behaviour for 97.5% of permissions.

This plan wires enforcement to the matrix AND applies the 8 matrix changes recommended by three expert panels.

---

## Concerns and Exclusions

**Included but dependency-blocked:**
- `alert.cancel → DENY` requires the recommend-cancellation workflow to exist first. The workflow is in this plan; the permission change comes after it.

**Excluded (deferred to Phase 2):**
- `privacy.access_request` key — the feature doesn't exist yet. Add key when feature is built. (Legal obligation — PIPEDA s. 8 — noted in Phase 2 roadmap.)
- `note.co_sign` key — supervision notes feature doesn't exist yet. Phase 3+.
- `consent.withdraw` as separate GATED key — needs GATED infrastructure (justification UI). Phase 2.
- `report.funder_report` as separate key — view logic handles PII stripping. Not needed.
- Splitting `consent.manage` into 3 keys — SCOPED + immutability is simpler and sufficient (Doc 3 override).
- `group.view_schedule` — Phase 2.
- Front Desk `client.edit → PER_FIELD` — Phase 2 (needs admin UI).
- Rename SCOPED → PROGRAM — Phase 2.
- PM `client.view_clinical → GATED` — Phase 2 (needs GATED UI).
- Discharge access transitions — Phase 2 (data model change, not permissions).

---

## Wave Structure (Efficiency-Optimised)

### Wave 1 — Foundation (3 parallel streams, no file overlap)

These three tasks touch completely different files and can be done simultaneously.

#### Stream 1A: Update permissions.py matrix
**File:** `apps/auth_app/permissions.py`

All matrix changes batched into one edit:

1. **Add `client.create`** to all 4 roles:
   - receptionist: ALLOW (front desk does intake)
   - staff: SCOPED (creates in own program, especially outreach)
   - program_manager: SCOPED (intake in smaller programs)
   - executive: DENY
   - Add plain English translation: "Create new client records"

2. **Add `client.edit_contact`** to all 4 roles:
   - receptionist: ALLOW (phone + email ONLY — not address or emergency contact)
   - staff: SCOPED
   - program_manager: DENY
   - executive: DENY
   - Add plain English translation: "Update client phone number and email"
   - Add comment: `# Narrow scope: phone + email only. Address and emergency contact require staff or higher (safety implications for DV). Replace with PER_FIELD in Phase 2.`

3. **Change staff `group.manage_members`**: DENY → SCOPED
   - Add comment: `# Facilitators manage own group rosters. All changes must create audit entry (PHIPA — group type reveals diagnosis).`

4. **Change PM `consent.manage`**: ALLOW → SCOPED
   - Add comment: `# PMs do intake in smaller programs. Consent records immutable after creation — can only withdraw and re-record.`

5. **Change PM `alert.create`**: DENY → ALLOW
   - Add comment: `# Supervisors should flag safety concerns when reviewing case files. No barriers to creating safety alerts.`

6. **Change staff `alert.cancel`**: SCOPED → DENY
   - Add comment: `# Two-person safety rule. Staff posts "recommend cancellation" with assessment; PM reviews and cancels. See alert recommendation workflow.`
   - NOTE: This value change is applied now in the matrix but enforcement is deferred to Wave 5 (needs recommend-cancellation workflow first, or staff will stop creating alerts).

7. **Change PM admin powers** to SCOPED:
   - `programme.manage`: DENY → SCOPED, comment: `# Own program only.`
   - `audit.view`: DENY → SCOPED, comment: `# QA oversight for own program.`
   - `user.manage`: DENY → SCOPED, comment: `# Own program team. CANNOT elevate roles (receptionist→staff) or create PM/executive accounts. Requires custom enforcement — see no-elevation constraint.`

8. **Executive admin documentation** (values stay DENY):
   - `user.manage`: add comment: `# DENY by default. Override to ALLOW for agencies where executive is operational ED (not board member).`
   - `settings.manage`: same comment pattern
   - `programme.manage`: same comment pattern

9. **Add enforcement-mechanism comments** to existing keys (examples):
   - `note.view` for staff: `# Enforced by @programme_role_required("staff"). Migrate to @requires_permission.`
   - `client.view_clinical` for receptionist: `# Enforced by get_visible_fields() via can_access().`
   - admin keys: `# Enforced by @admin_required (separate system — not matrix-driven).`

10. **Add "Confirmed correct" comments** from Document 3:
    - `group.view_roster` for receptionist: `# Confirmed: group type reveals diagnosis.`
    - `note.create/edit` for PM: `# Confirmed: managers don't write clinical notes.`
    - etc.

#### Stream 1B: Create `@requires_permission` decorator
**File:** `apps/auth_app/decorators.py`

Create the new decorator alongside the existing ones (don't delete old ones yet):

```python
def requires_permission(permission_key, get_programme_fn=None, get_client_fn=None):
    """Decorator: check permission matrix for the user's role in the relevant programme.

    Replaces @minimum_role and @programme_role_required. Reads from
    permissions.py via can_access() — changes to the matrix immediately
    affect enforcement.

    Args:
        permission_key: key like "note.create" from PERMISSIONS matrix
        get_programme_fn: function(request, *args, **kwargs) → Programme.
                          If None, uses user's highest role across all programs.
        get_client_fn: optional function for ClientAccessBlock check.
    """
```

Must handle:
- Determine user's role in relevant programme (reuse existing logic from `programme_role_required`)
- Call `can_access(role, permission_key)` from permissions.py
- DENY → 403 (render 403.html with message)
- ALLOW → proceed
- SCOPED → proceed (program-scoping already handled by middleware + programme lookup)
- GATED → future: check for documented justification. For now, treat as ALLOW with a log warning.
- PER_FIELD → future: delegate to field-level check. For now, treat as ALLOW with a log warning.
- Maintain ClientAccessBlock checking (from `programme_role_required`)
- Fail closed on any error (from `programme_role_required`)
- Validate that `permission_key` exists in the PERMISSIONS matrix at import time (catch typos early)
- Store `request.user_programme_role` for use in views (maintain compatibility)

Also add a helper for views that don't have a programme in the URL:

```python
def requires_permission_global(permission_key):
    """Like requires_permission but uses user's highest role across all programmes.
    For views like group_list, insights, etc. that aren't scoped to a single client.
    """
```

#### Stream 1C: Create `{% has_permission %}` template tag
**File:** `apps/auth_app/templatetags/permissions_tags.py` (NEW)
**File:** `apps/auth_app/templatetags/__init__.py` (NEW — empty)

```python
@register.simple_tag(takes_context=True)
def has_permission(context, permission_key):
    """Check if current user has permission. Returns True/False.

    Usage: {% load permissions_tags %}
           {% has_permission "note.view" as can_view_notes %}
           {% if can_view_notes %}<a href="...">Notes</a>{% endif %}
    """
```

Must handle:
- Get user's role(s) from the context (use same logic as context processor)
- Call `can_access(role, permission_key)`
- Return True if result is not DENY, False otherwise
- For users with multiple roles across programs, use highest role (most permissive)
- Handle unauthenticated users gracefully (return False)

---

### Wave 2 — Wire affected views (depends on Wave 1A + 1B)

All streams in Wave 2 touch different view files and can run simultaneously.
Each stream: swap hardcoded decorators to `@requires_permission` on the specific views affected by the 8 matrix changes.

#### Stream 2A: Client views
**File:** `apps/clients/views.py`

- `client_create`: currently `@minimum_role("staff")` → `@requires_permission("client.create")`
- `client_edit`: currently `@minimum_role("staff")` → keep for now (client.edit hasn't changed)
- Add new view or modify existing for contact-only edit → `@requires_permission("client.edit_contact")`
- `client_add_enrollment`: currently `@minimum_role("staff")` → `@requires_permission("client.edit")` (or leave, since client.edit for staff is still SCOPED)

#### Stream 2B: Group views
**File:** `apps/groups/views.py`

- Group member management views (add_member, remove_member): swap decorator to `@requires_permission("group.manage_members")`
- Verify HTMX roster change endpoints trigger audit logging

#### Stream 2C: Alert/event views
**File:** `apps/events/views.py`

- `alert_create`: swap to `@requires_permission("alert.create")` (enables PM to create alerts)
- `alert_cancel`: swap to `@requires_permission("alert.cancel")` — BUT defer this until Wave 5 (recommend-cancellation workflow must exist first)
- Other event views: swap while we're in the file

#### Stream 2D: Consent views
**Files:** Wherever consent views live (likely `apps/clients/views.py` or similar)

- Consent recording views: swap to `@requires_permission("consent.manage")`
- Add immutability enforcement: consent records cannot be edited after creation (model-level or form-level). Remove any update/edit capability. Only allow "withdraw and re-record."

#### Stream 2E: Executive-facing views (compliance priority)
**Files:** `apps/notes/views.py`, `apps/plans/views.py`, `apps/reports/views.py`, `apps/reports/pdf_views.py`, `apps/reports/insights_views.py`

These are the **compliance risk** — current decorators (`@minimum_role("staff")`) would allow executives (rank 4 > 2) but the matrix says DENY. The middleware compensates today, but a single enforcement point is safer.

- All note views: `@requires_permission("note.view")`, `@requires_permission("note.create")`, `@requires_permission("note.edit")`
- All plan views: same pattern
- Report views: `@requires_permission("report.programme_report")`, `@requires_permission("report.data_extract")`
- Insight views: `@requires_permission("metric.view_aggregate")` or appropriate key

#### Stream 2F: PM admin enforcement (custom logic)
**File:** `apps/auth_app/admin_views.py`

PM `user.manage: SCOPED` with no-elevation constraint. This is NOT a simple decorator swap — it requires custom view logic:

- PM can create/deactivate staff accounts within own program
- PM can reset passwords for own program staff
- PM CANNOT create PM or executive accounts
- PM CANNOT change receptionist → staff (grants clinical access)
- PM CANNOT change any role to PM or executive

Implementation: Add permission check in the user create/edit views that:
1. If user is PM (not admin), restrict available role choices
2. Block role changes that would elevate beyond staff
3. Filter user list to own program only

---

### Wave 3 — UI layer (depends on Wave 1C, partially on Wave 2)

#### Stream 3A: Update context processor
**File:** `konote/context_processors.py`

Update `user_roles()` to also expose permissions:
- Keep existing flags (`is_admin_only`, `has_program_roles`) for admin-specific UI
- Add `user_permissions` dict: for each permission key, the resolved level (using user's highest role)
- This lets templates access `user_permissions.note_view` etc.

#### Stream 3B: Update middleware
**File:** `konote/middleware/program_access.py`

- Replace hardcoded `is_executive_only()` redirect with matrix check: "does this user have any non-DENY permission for client-scoped resources?"
- If ALL client.* and note.* and plan.* etc. are DENY → redirect to executive dashboard
- This means if an agency grants executives `client.view_name: ALLOW`, the redirect stops automatically

#### Stream 3C: Add Django system check
**File:** `apps/auth_app/checks.py` (NEW) — register in `apps/auth_app/apps.py`

System check that:
1. Warns on any remaining `@minimum_role` or `@programme_role_required` usage in view files (W020)
2. Validates every permission key used in `@requires_permission` decorators exists in the matrix (E020)
3. Checks every key in the matrix is referenced by at least one `@requires_permission` decorator (W021 — dead key detection)

---

### Wave 4 — Template migration (depends on Wave 3A + 1C)

#### Stream 4A: Update base.html navigation
**File:** `templates/base.html`

Replace hardcoded boolean checks with `{% has_permission %}`:
- `{% if not is_admin_only and not is_executive_only %}` → `{% has_permission "client.view_name" as can_see_clients %}{% if can_see_clients %}`
- `{% if is_executive_only %}` → check appropriate permission
- `{% if features.groups and not is_executive_only and not is_receptionist_only %}` → `{% has_permission "group.view_roster" as can_see_groups %}{% if features.groups and can_see_groups %}`
- `{% if user.is_admin %}` → KEEP (admin is separate system)

#### Stream 4B: Update remaining templates
**Files:** ~10 other templates

- `templates/events/_tab_events.html`
- `templates/notes/_tab_notes.html`
- `templates/reports/_tab_analysis.html`
- `templates/programs/detail.html`
- `templates/programs/list.html`
- `templates/programs/_role_list.html`
- `templates/reports/_insights_basic.html`
- Any others using `is_executive_only` or `is_receptionist_only`

Each: replace boolean flag checks with `{% has_permission "key" %}` calls.

---

### Wave 5 — Feature work + remaining migration (depends on Wave 2)

#### Stream 5A: Alert recommend-cancellation workflow (NEW FEATURE)
**Files:** New model/view/template + `apps/events/` modifications

Build the workflow that unblocks `alert.cancel → DENY` for staff:
1. **Model:** Add `AlertRecommendation` (or field on existing alert model) — staff posts assessment text + "recommend cancel"
2. **View:** Staff sees "Recommend Cancellation" button (not "Cancel"). Submits assessment.
3. **Notification:** System notifies PM when a recommendation is posted (via existing notification mechanism or new one)
4. **PM view:** PM sees recommendations queue, can approve (cancel alert) or reject (add note)
5. After this ships, wire `alert.cancel` → `@requires_permission("alert.cancel")` (which now reads DENY for staff from the matrix)

#### Stream 5B: Migrate remaining ~35 views
**Files:** All remaining view files with `@minimum_role` or `@programme_role_required`

Systematic migration, batched by app. Each swap should be a no-behaviour-change commit (the matrix already has the values the hardcoded decorators enforce).

- `apps/clients/views.py` — remaining client views
- `apps/clients/erasure_views.py` — 5 erasure views (irreversible actions, highest priority in this batch)
- `apps/groups/views.py` — remaining group views
- `apps/notes/views.py` — any not done in Wave 2E
- `apps/plans/views.py` — any not done in Wave 2E
- `apps/events/views.py` — any not done in Wave 2C
- `apps/reports/pdf_views.py` — remaining
- `apps/reports/insights_views.py` — remaining

After each batch: run the system check (Wave 3C) to verify decreasing count of hardcoded decorators.

---

### Wave 6 — Verification + QA alignment (depends on Waves 4 + 5)

#### Stream 6A: Parametrized permission test
**File:** `tests/test_permissions_enforcement.py` (NEW)

The "ultimate source of truth test" — iterates permission keys and verifies enforcement matches matrix:
- For each permission key that maps to a URL, request as each role
- Assert: if `can_access(role, key)` returns DENY → response is 403
- Assert: if `can_access(role, key)` returns ALLOW/SCOPED → response is 200 (or redirect, not 403)
- This catches any remaining hardcoded checks that contradict the matrix

#### Stream 6B: Update QA personas
**Repo:** `konote-qa-scenarios` (external)

Only after enforcement is wired:
- Update all persona YAML files to match `permissions.py` values
- Fix DISC-1: receptionist CAN create clients
- Fix DISC-2/3: PM and executive admin powers match matrix
- Fix DISC-5: PM medication visibility reflected
- Note: DISC-4 is NOT a discrepancy (UI priority ≠ access right)

#### Stream 6C: Rewrite affected QA scenarios
**Repo:** `konote-qa-scenarios` (external)

- SCN-010 steps 2-4: Rewrite — receptionist CAN create clients (not 403)
- SCN-025 step 4: Rewrite — receptionist CAN edit phone/email
- SCN-070: Verify PM consent.manage SCOPED works correctly
- Add new scenarios for coverage gaps: client.view_safety boundary, group.manage_members for staff, alert.create for PM

---

## Dependency Map

```
Wave 1A (permissions.py) ──┐
Wave 1B (decorator)     ───┤──→ Wave 2 (wire views) ──→ Wave 3 (UI layer) ──→ Wave 4 (templates)
Wave 1C (template tag)  ───┘                        │                                    │
                                                    ├──→ Wave 5A (alert workflow)         │
                                                    ├──→ Wave 5B (remaining views)        │
                                                    │                                     │
                                                    └──→ Wave 6A (permission tests) ◄─────┘
                                                         Wave 6B (QA personas) ◄──── all waves done
                                                         Wave 6C (QA scenarios) ◄──── all waves done
```

## File Conflict Map

| File | Touched in | Safe to parallelise? |
|------|-----------|---------------------|
| `apps/auth_app/permissions.py` | Wave 1A only | Yes — single stream |
| `apps/auth_app/decorators.py` | Wave 1B only | Yes — single stream |
| `apps/auth_app/templatetags/` | Wave 1C only | Yes — new files |
| `apps/clients/views.py` | Wave 2A, 5B | Sequential (2A first) |
| `apps/groups/views.py` | Wave 2B, 5B | Sequential (2B first) |
| `apps/events/views.py` | Wave 2C, 5A, 5B | Sequential (2C → 5A → 5B) |
| `apps/notes/views.py` | Wave 2E, 5B | Sequential (2E first) |
| `apps/plans/views.py` | Wave 2E, 5B | Sequential (2E first) |
| `apps/reports/*.py` | Wave 2E, 5B | Sequential (2E first) |
| `apps/auth_app/admin_views.py` | Wave 2F only | Yes — single stream |
| `konote/context_processors.py` | Wave 3A only | Yes — single stream |
| `konote/middleware/program_access.py` | Wave 3B only | Yes — single stream |
| `templates/base.html` | Wave 4A only | Yes — single stream |
| `templates/**/*.html` | Wave 4B only | Yes — batched |

## Estimated Scope

| Wave | Streams | Files touched | New files |
|------|---------|--------------|-----------|
| 1 | 3 parallel | 2 modified | 2 new (templatetags) |
| 2 | 6 parallel | ~8 view files | 0 |
| 3 | 3 parallel | 2 modified | 1 new (checks.py) |
| 4 | 2 parallel | ~11 templates | 0 |
| 5 | 2 parallel | ~8 view files | 1-2 new (alert workflow) |
| 6 | 3 parallel | 0 in this repo (+ external) | 1 new (test file) |
