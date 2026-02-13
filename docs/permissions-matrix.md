# KoNote Permissions Matrix

> **Source of truth:** [permissions.py](../apps/auth_app/permissions.py)
> **Last updated:** 2026-02-13

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
| See clinical data | — | Scoped | Yes | — | — |
| Create new clients | Yes | Scoped | Scoped | — | — |
| Edit client records | — | Scoped | — | — | — |
| Edit contact info (phone/email) | Yes | Scoped | — | — | — |
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
| Read progress notes | — | Scoped | Yes | — | — |
| Write progress notes | — | Scoped | Scoped | — | — |
| Edit progress notes | — | Scoped | Scoped | — | — |
| **Plans** | | | | | |
| View plans | — | Scoped | Yes | — | — |
| Edit plans | — | Scoped | — | — | — |
| **Metrics** | | | | | |
| View individual metrics | — | Scoped | Yes | — | — |
| View aggregate metrics | — | Scoped | Yes | Yes | — |
| View outcome insights | — | Scoped | Yes | Yes (aggregate) | — |
| **Meetings & Calendar** | | | | | |
| View meetings | — | Scoped | Yes | — | — |
| Schedule meetings | — | Scoped | Scoped | — | — |
| Edit meetings | — | Scoped | — | — | — |
| **Communications** | | | | | |
| View communication logs | — | Scoped | Yes | — | — |
| Log communications | — | Scoped | Scoped | — | — |
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
| **View audit log** | — | — | Scoped | Yes | Yes |
| **Create/edit custom field definitions** | — | — | — | — | Yes |
| **Manage funder profiles** | — | — | — | — | Yes |
| **Manage note templates** | — | — | — | — | Yes |
| **Manage plan templates** | — | — | — | — | Yes |
| **Manage event types** | — | — | — | — | Yes |
| **Manage registration forms** | — | — | — | — | Yes |
| **Merge duplicate clients** | — | — | — | — | Yes |
| **Send invitations** | — | — | — | — | Yes |
| **Configure terminology** | — | — | — | — | Yes |
| **Toggle features** | — | — | — | — | Yes |
| **Manage secure export links** | — | — | — | — | Yes |

**Legend:**
- **Yes** = Always allowed (within their program scope)
- **Scoped** = Only for their assigned clients/groups within their program
- **Per field** = Depends on each field's individual access setting
- **—** = Not allowed

---

## Key Rules

### Scoped Access (Direct Service)

"Scoped" means the person can only see data for clients and groups they are **assigned to** within their program. Phase 1 scopes to the whole program; Phase 2 will narrow this to specific group/client assignments.

### Administrator Is Not a Program Role

Administrator (`is_admin=True`) is a **system-level flag**, not a program role. It grants access to configuration pages (users, settings, templates, terminology) but **not** to any client data.

If an admin also needs to see client records, they must be assigned a program role (e.g., Program Manager in Program A). Their client access follows the rules of that program role — the admin flag doesn't give them extra clinical access.

### Front Desk Custom Field Access

Each custom field definition has a `front_desk_access` setting:
- **none** — Hidden from Front Desk (clinical/sensitive fields)
- **view** — Front Desk can see but not edit
- **edit** — Front Desk can see and edit

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

---

## Planned Changes (Future Phases)

| Permission | Current | Planned | Phase |
|---|---|---|---|
| Program Manager: view clinical data | ALLOW | GATED (requires documented reason) | Phase 3 |
| Program Manager: view notes | ALLOW | GATED | Phase 3 |
| Program Manager: view plans | ALLOW | GATED | Phase 3 |
| Program Manager: view group session content | ALLOW | GATED | Phase 3 |
| Program Manager: export data | DENY | Request-only (requires admin approval) | Phase 3 |
| Direct Service: scoping | Program-wide | Assigned groups/clients only | Phase 2 |
