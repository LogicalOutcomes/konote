# Permissions Discrepancy Report

**Date:** 2026-02-09
**Source of truth:** `konote-web/apps/auth_app/permissions.py`
**Compared against:** `qa-scenarios/personas/*.yaml` + 5 permission-testing scenarios

---

## Issues in permissions.py itself

These are gaps or problems in the source of truth that need decisions.

### PERM-1: Missing `client.create` permission key (DECISION NEEDED)

permissions.py defines 34 permission keys per role. **None of them is `client.create`.**

This is the most-tested permission boundary in the QA scenarios (SCN-010 steps 2-4, SCN-025). Staff create clients daily. Whether receptionists can create clients is a critical design decision that affects intake workflows at every agency.

**Current state in code:** No `client.create` key exists. The closest keys are `intake.view: DENY` and `intake.edit: DENY` for receptionist, and `client.edit: DENY`.

**What the QA scenarios assume:**
- SCN-010 step 3: R1 (receptionist) tries `/clients/create/` and **expects a 403** — receptionists CANNOT create
- SCN-010 step 4: DS1 (staff) goes to `/clients/create/` and **expects success** — staff CAN create

**Recommendation:** Add `client.create` to all 4 roles in permissions.py:

```python
"client.create": DENY,      # receptionist — staff handles intake
"client.create": SCOPED,    # staff — within own program
"client.create": DENY,      # program_manager — staff responsibility
"client.create": DENY,      # executive
```

### PERM-2: Executive admin permissions are all DENY (CONFIRM INTENT)

permissions.py says:
```python
"executive": {
    "user.manage": DENY,
    "settings.manage": DENY,
    "programme.manage": DENY,
    "audit.view": ALLOW,   # Board oversight
}
```

This means executives can view the audit log but **cannot manage users, settings, or programs**. In practice, an Executive Director (E1 — Margaret Whitfield) would typically be the one who:
- Creates or deactivates user accounts (new hire, termination)
- Configures program settings
- Has full system admin access

If the intent is that executives use a separate admin account or delegate to IT, that's fine — but it should be documented. If the intent is that the `executive` role IS the admin role, then `user.manage`, `settings.manage`, and `programme.manage` should be ALLOW.

**Question for konote-web:** Is there a separate `admin` role not listed in permissions.py? Or is `executive` intended to be the top role without admin powers?

### PERM-3: Program Manager admin permissions are all DENY (CONFIRM INTENT)

permissions.py says:
```python
"program_manager": {
    "user.manage": DENY,
    "settings.manage": DENY,
    "programme.manage": DENY,
    "audit.view": DENY,
}
```

This means a Program Manager (PM1 — Morgan Tremblay) **cannot**:
- Manage users (she supervises 8 staff)
- Configure program settings (she owns the Housing Support program)
- View the audit log (she needs it for QA oversight)

This seems too restrictive. In nonprofit agencies, PMs typically configure their own programs and manage their team's accounts. If a PM can't do these things, who does? The ED? IT?

**Question for konote-web:** Should `programme.manage` be SCOPED (own program only) for program managers? Should `audit.view` be SCOPED?

### PERM-4: No `report.funder_report` vs `report.programme_report` distinction

permissions.py has:
```python
"report.programme_report": ALLOW,  # for PM and executive
"report.data_extract": DENY,       # for PM and executive
```

But the persona YAML distinguishes between `reports` (programme outcome reports) and `funder_reports` (aggregate, no PII). The QA scenarios test that funder reports strip PII for executives. There's no separate permission key for funder reports in permissions.py.

**Recommendation:** Either:
- Add `report.funder_report` as a separate key (if funder reports have different access rules)
- Or document that `report.programme_report` covers both, with PII stripping handled by the view logic rather than a permission check

---

## Critical discrepancies: persona YAML vs permissions.py

These are cases where the persona files say one thing and permissions.py says another. **The persona files need to be updated to match permissions.py** (or permissions.py needs to change first — see above).

### DISC-1: Receptionist `client_create` — persona says YES, scenario says NO

| Source | Says |
|--------|------|
| **Persona YAML** (R1, R2, R2-FR) | `pages.client_create: true`, `action_access.create_client: true` |
| **SCN-010 step 2** | *"Dana does not see a 'Create' button (correct)"* |
| **SCN-010 step 3** | R1 expects 403 at `/clients/create/` |
| **permissions.py** | No `client.create` key exists |

The persona and the scenario contradict each other. Blocked until PERM-1 is resolved.

### DISC-2: PM1 has 4 admin powers the code denies

| Permission | permissions.py | PM1 persona |
|-----------|---------------|-------------|
| `audit.view` | DENY | `audit_log: true` |
| `user.manage` | DENY | `manage_users: true` |
| `settings.manage` | DENY | `settings: true` (program config) |
| `programme.manage` | DENY | `manage_programs: true` |

**Impact:** SCN-070 step 5 has PM1 accessing `/reports/` — that's fine (`report.programme_report: ALLOW`). But if any future scenario has PM1 configuring programs or managing users, it will hit a 403 that the persona doesn't expect.

Blocked until PERM-3 is resolved.

### DISC-3: E1/E2 have 3 admin powers the code denies

| Permission | permissions.py | E1/E2 persona |
|-----------|---------------|---------------|
| `user.manage` | DENY | `manage_users: true` |
| `settings.manage` | DENY | `admin: true` |
| `programme.manage` | DENY | `manage_programs: true` |

`audit.view: ALLOW` is correctly reflected in both (`audit_log: true`).

**Impact:** SCN-070 step 6 has E1 accessing the audit log — that works. But the persona says E1 can manage users and programs, which the code denies. The `action_access.export_data: true` in the persona also has no matching `report.data_extract: ALLOW` — permissions.py says DENY.

Blocked until PERM-2 is resolved.

### DISC-4: PM1 `case_notes_detail` hidden but `note.view: ALLOW`

PM1 persona hides `case_notes_detail` in `fields_hidden`. But permissions.py says `note.view: ALLOW` for program managers. These contradict: if PM1 can view notes, case note detail shouldn't be hidden. If PM1 shouldn't see note detail, `note.view` should be GATED or SCOPED with a note.

### DISC-5: PM1 `client.view_medications: ALLOW` not in persona fields

permissions.py gives PM1 `client.view_medications: ALLOW`. The persona's `fields_visible` list doesn't include medications. Minor but the persona should reflect this since medication visibility reveals diagnosis.

---

## Coverage gaps: permission keys with no QA scenario coverage

These permissions exist in permissions.py but no scenario explicitly tests them. Not all need scenarios — but the ones marked "should test" represent real user actions.

| Permission key | Who has it | Should test? | Why |
|---------------|-----------|-------------|-----|
| `client.view_safety` | R: ALLOW, S: ALLOW, PM: ALLOW, E: DENY | Yes | Safety info shown to receptionist is a data boundary. Executive seeing it is a violation. |
| `client.view_medications` | R: DENY, S: SCOPED, PM: ALLOW, E: DENY | Yes | Medications reveal diagnosis. Key privacy boundary. |
| `attendance.check_in` | R: ALLOW, S: SCOPED, PM: DENY, E: DENY | No | Tested implicitly by receptionist workflows. |
| `attendance.view_report` | R: DENY, S: SCOPED, PM: ALLOW, E: ALLOW | No | Tested implicitly by PM1 report scenarios. |
| `group.edit` | R: DENY, S: DENY, PM: ALLOW, E: DENY | Yes | PM configuring groups is a core PM task. No scenario covers it. |
| `group.manage_members` | R: DENY, S: DENY, PM: ALLOW, E: DENY | Yes | Same as above. |
| `alert.view/create/cancel` | Varies | Yes | Safety alerts are critical. No scenario tests alert permissions. |
| `event.view/create` | R: DENY, S: SCOPED, PM: ALLOW/DENY, E: DENY | Low | Events are supplementary. |
| `consent.view/manage` | R: DENY, S: SCOPED, PM: ALLOW, E: DENY | Partial | SCN-010 step 6 checks consent indicator. SCN-070 tests withdrawal. But no scenario tests receptionist DENIED from consent. |
| `intake.view/edit` | R: DENY, S: SCOPED, PM: ALLOW/DENY, E: DENY | Yes | Intake forms contain clinical history. Receptionist denied access is a privacy boundary. |
| `custom_field.view/edit` | R: PER_FIELD, S: SCOPED, PM: ALLOW/DENY, E: DENY | Low | PER_FIELD is interesting but edge-case. |
| `note.delete` | All: DENY | No | Correctly denied for all roles. Cancel, don't delete. |
| `client.delete` | All: DENY | No | Admin-only erasure. Tested conceptually in SCN-070. |
| `plan.delete` | All: DENY | No | Archive, don't delete. |

---

## Scenario-specific permission issues

### SCN-010: Morning Intake

- **Step 3 conflict:** See DISC-1. Scenario expects 403 for R1 at `/clients/create/` but persona says `client_create: true`.
- **Step 6:** DS1 checks consent status. `consent.view: SCOPED` in permissions.py for staff — this is correct. No issue.

### SCN-025: Quick Lookup (R2)

- **Step 2:** Tests that R2's profile view hides clinical data. Consistent with `client.view_clinical: DENY` in permissions.py. No issue.
- **Step 3:** R2 tries `/clients/{id}/notes/`. `note.view: DENY` for receptionist. Consistent. No issue.
- **Step 4:** R2 updates email. `client.edit: DENY` for receptionist in permissions.py. But the scenario expects success for contact info changes. **This is a problem:** permissions.py has a single `client.edit: DENY` for receptionist, but the persona and scenario say receptionists CAN edit contact info. Either permissions.py needs a finer-grained `client.edit_contact` key, or the scenario is wrong.

### SCN-042: Multi-Program Client

- **Step 1 (PM1):** `note.view: ALLOW` for PM — correct, PM1 sees both programs' notes.
- **Step 2 (DS1):** `note.view: SCOPED` for staff — correct, DS1 sees only Housing Support.
- **Step 3 (R1):** `note.view: DENY` for receptionist — correct, R1 sees no notes.
- **Step 4 (DS1):** URL manipulation test. Server-side enforcement. No permission issue.
- **Step 5 (PM1):** PM1 views enrolments. `client.view_name: ALLOW` — correct.
- No issues found.

### SCN-049: Shared Device Handoff

- **Step 4:** R1 session should show receptionist permissions. This tests session isolation, not permission definitions. No issue.
- **Step 6:** R1 should not see staff-level action buttons. Consistent with `note.create: DENY`, `note.edit: DENY` for receptionist. No issue.

### SCN-070: Consent Withdrawal

- **Step 1-5 (PM1):** `consent.manage: ALLOW`, `report.programme_report: ALLOW` — consistent. But `report.data_extract: DENY` in permissions.py while the persona says `export_data: true`. **Conflict:** PM1 scenario expects export to work, but permissions.py denies data extract. This needs clarification — is the privacy export a different permission from `report.data_extract`?
- **Step 6 (E1):** `audit.view: ALLOW` for executive — consistent. No issue.

---

## New permission key needed: `client.edit_contact`

SCN-025 step 4 expects receptionist to edit contact info (email, phone). But permissions.py says `client.edit: DENY` for receptionist. The scenarios and personas both assume receptionists can update phone numbers and emails — this is a core front-desk function.

**Recommendation:** Split `client.edit` into:
```python
"client.edit_contact": ALLOW,   # receptionist — phone, email, address
"client.edit_clinical": DENY,   # receptionist — diagnosis, notes, plans
"client.edit": DENY,            # receptionist — general edit (keep as catch-all)
```

Or add `client.edit_contact` alongside the existing `client.edit`:
```python
"client.edit_contact": ALLOW,   # receptionist can update phone/email/address
"client.edit": DENY,            # receptionist cannot edit other fields
```

---

## Summary of decisions needed from konote-web

| ID | Question | Options |
|----|----------|---------|
| PERM-1 | Add `client.create` to permissions.py? | Yes (receptionist DENY, staff SCOPED) or No (handled by view logic) |
| PERM-2 | Should executives manage users/settings/programs? | Add admin role, or change to ALLOW, or keep DENY and document who does admin |
| PERM-3 | Should PMs manage own program and view audit log? | SCOPED for `programme.manage` + `audit.view`, or keep DENY |
| PERM-4 | Separate `report.funder_report` from `report.programme_report`? | Add key, or document PII stripping is view logic |
| PERM-5 | Add `client.edit_contact` for receptionists? | Yes (ALLOW for receptionist), or rewrite SCN-025 step 4 |
| PERM-6 | Is the privacy data export (SCN-070) a different permission from `report.data_extract`? | Add `privacy.export` key, or use `report.data_extract: ALLOW` for PM |

Once these 6 decisions are made in permissions.py, I'll update all persona YAML files and scenarios in this repo to match.
