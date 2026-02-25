# KoNote Permissions Matrix

> **Source of truth:** [permissions.py](../apps/auth_app/permissions.py)
> **Last updated:** 2026-02-25

---

## Roles Overview

| Role | Who It's For | Scope |
|------|-------------|-------|
| **Front Desk** | Reception staff who check people in | Operational only — names, contact, safety info |
| **Direct Service** | Counsellors, case workers, facilitators | Full clinical access to assigned clients/groups |
| **Program Manager** | Program leads, supervisors | Administrative view across their program(s) |
| **Executive** | Directors, board members, funders | Org-wide aggregate data only — no individual records |
| **Administrator** | System administrators | System configuration only — NO client data unless also assigned a program role |

---

## Quick Summary

| Capability | Front Desk | Direct Service | Program Manager | Executive | Administrator |
|---|:---:|:---:|:---:|:---:|:---:|
| **Clients & Intake** | | | | | |
| Check clients in/out | Yes | Scoped | — | — | — |
| See client names | Yes | Yes | Yes | — | — |
| See contact info | Yes | Yes | Yes | — | — |
| See safety info | Yes | Yes | Yes | — | — |
| See medications | — | Scoped | Yes | — | — |
| See clinical data | — | Scoped | Gated | — | — |
| Create new clients | Yes | Scoped | Scoped | — | — |
| Edit client records | — | Scoped | Scoped | — | — |
| Edit contact info (phone/email) | Yes | Scoped | — | — | — |
| Transfer between programs | — | Scoped | Scoped | — | — |
| View consent records | — | Scoped | Yes | — | — |
| Manage consent | — | Scoped | Scoped | — | — |
| View intake forms | — | Scoped | Yes | — | — |
| Edit intake forms | — | Scoped | — | — | — |
| **Groups** | | | | | |
| View group roster | — | Scoped | Yes | — | — |
| View group details | — | Scoped | Yes | — | — |
| Log group sessions | — | Scoped | — | — | — |
| Edit group config | — | — | Yes | — | — |
| Create new groups | — | Scoped | Yes | — | — |
| Add/remove group members | — | Scoped | Yes | — | — |
| Manage project milestones/outcomes | — | Scoped | Yes | — | — |
| View group attendance reports | — | Scoped | Yes | — | — |
| **Progress Notes** | | | | | |
| Read progress notes | — | Scoped | Gated | — | — |
| Write progress notes | — | Scoped | Scoped | — | — |
| Edit progress notes | — | Scoped | Scoped | — | — |
| **Plans** | | | | | |
| View plans | — | Scoped | Gated | — | — |
| Edit plans | — | Scoped | — | — | — |
| **Metrics & Insights** | | | | | |
| View individual metrics | — | Scoped | Yes | — | — |
| View aggregate metrics | — | Scoped | Yes | Yes | — |
| View outcome insights | — | Scoped | Yes | Yes (aggregate) | — |
| View suggestion themes | — | Scoped | Yes | Yes (summary) | — |
| Manage suggestion themes | — | — | Scoped | — | — |
| **Circles (Families & Networks)** | | | | | |
| View circles | — | Scoped | Yes | — | — |
| Create circles | — | Scoped | Yes | — | — |
| Edit circles / manage members | — | Scoped | Yes | — | — |
| **Meetings & Calendar** | | | | | |
| View meetings | — | Scoped | Yes | — | — |
| Schedule meetings | — | Scoped | Scoped | — | — |
| Edit meetings | — | Scoped | — | — | — |
| **Communications** | | | | | |
| View communication logs | — | Scoped | Yes | — | — |
| Log communications | — | Scoped | Scoped | — | — |
| **Staff Messaging** | | | | | |
| Leave messages for case workers | Yes | Yes | Yes | — | — |
| Read staff messages | — | Scoped | Yes | — | — |
| **Reports & Export** | | | | | |
| Generate program reports | — | — | Yes | Yes (view) | — |
| Generate funder reports | — | — | Yes | Yes | — |
| Export data extracts | — | — | Yes | — | — |
| View attendance reports | — | Scoped | Yes | Yes | — |
| **Events & Alerts** | | | | | |
| View events | — | Scoped | Yes | — | — |
| Create events | — | Scoped | — | — | — |
| View alerts | — | Scoped | Yes | — | — |
| Create alerts | — | Scoped | Yes | — | — |
| Cancel alerts | — | — | Yes | — | — |
| Recommend alert cancellation | — | Scoped | — | — | — |
| Review cancellation recommendations | — | — | Yes | — | — |
| **Custom Fields** | | | | | |
| View custom fields | Per field | Scoped | Yes | — | — |
| Edit custom fields | Per field | Scoped | — | — | — |
| **Destructive Actions** | | | | | |
| Delete notes | — | — | — | — | — |
| Delete clients | — | — | — | — | — |
| Delete plans | — | — | — | — | — |
| Manage data erasure | — | — | Scoped | — | — |
| **System Administration** | | | | | |
| **Manage users** | — | — | Scoped | — | Yes |
| **System settings** | — | — | — | — | Yes |
| **Manage programs** | — | — | Scoped | — | Yes |
| **View audit log** | — | — | Scoped | — | Yes |
| **Create/edit custom field definitions** | — | — | — | — | Yes |
| **Manage report templates** | — | — | — | — | Yes |
| **Manage note templates** | — | — | Scoped | — | Yes |
| **Manage plan templates** | — | — | Scoped | — | Yes |
| **Manage event types** | — | — | Scoped | — | Yes |
| **Manage outcome metrics** | — | — | Scoped | — | Yes |
| **Manage registration forms** | — | — | Scoped | — | Yes |
| **Merge duplicate clients** | — | — | — | — | Yes |
| **Send invitations** | — | — | — | — | Yes |
| **Configure terminology** | — | — | — | — | Yes |
| **Toggle features** | — | — | — | — | Yes |
| **Manage secure export links** | — | — | — | — | Yes |

**Legend:**
- **Yes** = Always allowed (within their program scope)
- **Scoped** = Only for their assigned clients/groups within their program
- **Gated** = Allowed with documented reason (just-in-time access via AccessGrant)
- **Per field** = Depends on each field's individual access setting
- **—** = Not allowed

**Note on Executive audit access:** Executives do not have access to the audit log. Under PIPEDA principle 4.4 (limiting use, disclosure, and retention), access to detailed audit trails — which may contain client identifiers and staff activity records — is restricted to those with an operational need. Executives who require oversight of audit activity should request aggregate compliance reports from an administrator.

---

## Key Rules

### Scoped Access (Direct Service)

"Scoped" means the person can only see data for clients and groups they are **assigned to** within their program. Phase 1 scopes to the whole program; Phase 2 will narrow this to specific group/client assignments.

### Gated Access (Program Manager — Clinical Safeguards)

At access tier 3 (Clinical Safeguards), program managers must provide a documented reason before viewing clinical data, progress notes, or plans. This creates an `AccessGrant` record with:
- **Reason** (supervision, complaint, safety, quality, intake)
- **Written justification**
- **Automatic expiry** (configurable, default 8 hours)

At access tiers 1–2, gated permissions are relaxed to "Yes" (the gate is open). This lets agencies adopt clinical safeguards gradually.

### Administrator Is Not a Program Role

Administrator (`is_admin=True`) is a **system-level flag**, not a program role. It grants access to configuration pages (users, settings, templates, terminology) but **not** to any client data.

If an admin also needs to see client records, they must be assigned a program role (e.g., Program Manager in Program A). Their client access follows the rules of that program role — the admin flag doesn't give them extra clinical access.

### Front Desk Contact Field Access (Per-Field)

Contact fields are individually configurable via `FieldAccessConfig`:

| Field | Default Access | Notes |
|-------|---------------|-------|
| Phone | Edit | Front desk updates phone numbers |
| Email | Edit (Tier 3: View only) | Tier 3 tightens email to view-only |
| Preferred name | View | Can see but not change |
| Birth date | Hidden | Not needed for front desk |

Custom field definitions also have a `front_desk_access` setting:
- **none** — Hidden from Front Desk (clinical/sensitive fields)
- **view** — Front Desk can see but not edit
- **edit** — Front Desk can see and edit

### DV-Safe Mode

When a client is flagged as DV-safe (`is_dv_safe=True`):
- Sensitive custom fields (address, emergency contact, employer) are hidden from Front Desk
- Only staff and above can enable DV-safe mode (unilateral)
- Removal requires **two-person rule**: staff requests removal with reason, PM approves or rejects

### Program Isolation

Every user only sees clients enrolled in programs where they have an active role. Confidential programs are invisible to staff in other programs.

### Negative Access Blocks

A `ClientAccessBlock` (for conflict of interest or safety reasons) **overrides all other access**. Even admins with program roles are blocked. This is checked first, before any other permission.

### Two-Person Safety Rule (Alerts)

A safety alert **cannot** be created and cancelled by the same person. Direct Service staff can create alerts and **recommend** cancellation, but only a Program Manager can approve the cancellation. This prevents a single worker from silently removing a safety flag.

| Action | Direct Service | Program Manager |
|---|---|---|
| Create alert | Yes (scoped) | Yes |
| Cancel alert | **No** — must recommend | Yes |
| Recommend cancellation | Yes (scoped) | No — cancels directly |
| Review recommendation | No | Yes |

### Consent Immutability

Consent records are **immutable after creation**. Once recorded, a consent record cannot be edited or deleted — it can only be **withdrawn** (which creates a new withdrawal record). To correct an error, withdraw the incorrect consent and record a new one. This preserves a complete audit trail required by PIPEDA and PHIPA.

### Executive Aggregate-Only

Executives see org-wide numbers and reports but **never** individual client names, records, or group rosters. They are redirected away from client/group detail pages.

### Client Transfers (`client.transfer`)

Transferring a participant between programs is a separate permission from editing client records. This allows organisations to control who can move people between service streams.

| Role | Access | Notes |
|------|--------|-------|
| **Front Desk** | Denied | Program transfers are staff/PM decisions |
| **Direct Service** | Scoped | Outreach and drop-in staff manage intake-to-program enrolment within their program |
| **Program Manager** | Scoped | PMs manage program enrolment for their programs |
| **Executive** | Denied | Executives don't manage individual enrolments |

The transfer form only shows programs the user has access to. Confidential program enrolments are preserved — the transfer does not reveal or modify enrolments in programs the user cannot see.

### Program Manager Admin Permissions

Program managers can manage configuration items for their own programs. These permissions are **scoped** — PMs can only create, edit, and delete items that belong to their program. Global items (created by administrators) are visible in read-only mode.

| Permission Key | What it controls | PM Access |
|---------------|-----------------|-----------|
| `template.plan.manage` | Plan templates (sections and targets) | Scoped — own program only |
| `template.note.manage` | Progress note templates (structure and sections) | Scoped — own program only |
| `event_type.manage` | Event types (intake, discharge, crisis, etc.) | Scoped — own program only |
| `metric.manage` | Outcome metrics (create, edit, enable/disable) | Scoped — own program only |
| `registration.manage` | Public registration links and pending submissions | Scoped — own program only |

**Important constraints:**
- PMs **cannot** edit global templates or metrics created by administrators — they can only view them
- PMs **cannot** change system-wide settings, terminology, or feature toggles
- PMs **cannot** elevate user roles (e.g., promote a front desk worker to staff) or create PM/executive/admin accounts
- When a PM creates a new item and manages only one program, the item is auto-assigned to that program

### Staff Messaging (`message.leave`, `message.view`)

Staff messaging allows team members to leave operational messages about participants (e.g., "Sarah called, wants to reschedule Tuesday").

| Role | Leave messages | Read messages |
|------|---------------|---------------|
| **Front Desk** | Yes | No |
| **Direct Service** | Yes | Scoped (own program) |
| **Program Manager** | Yes | Yes (full program) |
| **Executive** | No | No |

Messages are encrypted because they may contain participant names (PII). Each message is tied to a client file and optionally to a specific staff recipient.

### Circles (Families & Support Networks)

Circles represent families, households, or support networks. They are **cross-program** — a circle has no program assignment. Visibility is derived from membership: a user can see a circle if they have access to at least one enrolled member.

| Role | View | Create | Edit |
|------|------|--------|------|
| **Front Desk** | — | — | — |
| **Direct Service** | Scoped | Scoped | Scoped |
| **Program Manager** | Yes | Yes | Yes |
| **Executive** | — | — | — |

**DV safety:** If a `ClientAccessBlock` hides a member, and fewer than 2 visible enrolled participants remain, the entire circle is hidden. Non-participant member names (free text) are never counted toward visibility thresholds.

---

## Planned Changes (Future Phases)

| Permission | Current | Planned | Phase |
|---|---|---|---|
| Program Manager: view group session content | ALLOW | GATED | Phase 3 |
| Program Manager: view individual metrics | ALLOW | GATED | Phase 3 |
| Program Manager: view custom fields | ALLOW | GATED | Phase 3 |
| Front Desk: edit contact info | ALLOW (whole page) | PER_FIELD (individual fields) | Phase 2 |
| Direct Service: scoping | Program-wide | Assigned groups/clients only | Phase 2 |
