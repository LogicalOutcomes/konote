# Prompt: Review the Permissions Redesign Plan

Copy everything below the line into a new Claude Code conversation.

---

## Task

I need you to critically review and stress-test my permissions redesign plan for KoNote, a case management system for Canadian nonprofits serving vulnerable populations (mental health, addictions, housing, domestic violence). Small agencies, 5-15 staff, mixed technical literacy.

**Your job:** Find holes, contradictions, things that won't work in practice, things I've missed, and things that are over-engineered. Be blunt. I'm tired and I need someone to tell me what's wrong, not what's right.

## What's Been Done (Already Committed)

1. **New `@program_role_required()` decorator** — checks user's role in the SPECIFIC program for a resource, not their highest role across all programs. This fixed the critical security hole where Front Desk in Program A + Staff in Program B could access Program A's clinical data.

2. **9 group views updated** — `group_detail`, `group_edit`, `session_log`, `membership_add`, `membership_remove`, `milestone_create`, `milestone_edit`, `outcome_create`, `attendance_report` now use program-specific role checking. `group_list` and `group_create` kept with `@minimum_role("staff")` because they don't operate on a specific group resource.

3. **Note views left unchanged** — Expert panel concluded notes are client-scoped (not program-scoped). The middleware's "circle of care" model is correct for Canadian nonprofits: all clinical staff serving a shared client see all notes across all programs for coordination and safety.

4. **Event/alert views blocked** — Added `@minimum_role("staff")` to `event_list`, `event_create`, `alert_create`, `alert_cancel`. These contain sensitive clinical info (safety concerns, risk assessments).

5. **Central permissions matrix** — Created `apps/auth_app/permissions.py` with 4 roles x 28 permissions. Includes `client.view_safety` (ALLOW for Front Desk — allergies, emergency contacts, medical alerts) separate from `client.view_clinical` (DENY for Front Desk — diagnosis, treatment, notes).

6. **Validation command** — `python manage.py validate_permissions` checks all roles have all permission keys defined.

## What's NOT Done Yet

These are planned but not built:
- Program Report (aggregate-only, PDF, for funders/board/donors)
- Data Extract rename and restriction (admin-only, warning banner)
- Permission review screen (plain-language CAN/CANNOT after role changes)
- Privacy settings dashboard (matrix showing who can see what)
- Admin access oversight (immutable audit log, auto-expiry for temp access)

## Key Decisions Made During Implementation

1. **Safety vs. clinical data split**: Front Desk MUST see allergies, emergency contacts, medical alerts (could save a life). Front Desk CANNOT see diagnosis, treatment plans, session notes.

2. **Administrator governance**: Board quarterly reviews are unrealistic (boards don't read 50-page packages). Real accountability comes from: immutable audit log (evidence exists for investigations/audits), auto-expiry for temp admin access, mandatory reason field. NOT from: email notifications to all staff (toxic surveillance), quarterly board reports (nobody reads them), administrator codes of conduct (checkbox theatre).

3. **Permission display**: Expert panel recommended a dashboard matrix (rows = data types, columns = roles, checkmarks for allowed) plus a configuration checklist organized by data type with warnings about risky configurations. Show by data type, not by role — that's how administrators think.

## The Plan

Read the full plan at: `C:\Users\gilli\.claude\plans\sequential-gliding-kahan.md`

Also read:
- `apps/auth_app/permissions.py` — the actual permissions matrix
- `apps/auth_app/decorators.py` — the decorators including `program_role_required`
- `apps/groups/views.py` — to see how the decorator is applied
- `apps/events/views.py` — to see the minimum_role fix
- `tasks/permissions-phase1-implementation.md` — tracking document

## What I Want You to Interrogate

Use the convening-experts skill. Convene a panel that includes at least a privacy lawyer (PIPEDA/PHIPA), a nonprofit ED who's used case management systems, and a Django security specialist. Have them stress-test:

1. **Does the safety/clinical split make sense?** What about information that's ambiguous — e.g., "client is in a DV shelter" (is that safety info or clinical info? Front Desk needs to know for mail handling, but it also reveals the reason for service).

2. **Is the circle-of-care model for notes correct?** The expert panel said yes, but I'm not 100% sure. If a client is in Youth Program (counselling for sexual abuse) AND Adult Housing Program, should the housing worker see the counselling notes? The panel said yes for safety/coordination. But what about client consent?

3. **What about the administrator who IS the only staff member?** In a 3-person agency (ED + 2 staff), the ED does everything — admin, clinical work, reporting. The entire governance model breaks down. What do we actually do?

4. **Is the permissions matrix complete?** Are there data types or actions we've missed? What about: intake forms, consent records, billing/invoicing, staff supervision notes, incident reports?

5. **What happens when someone's role changes?** If Sam moves from Staff to Front Desk (e.g., light duties after injury), do they lose access to all the notes they wrote? Can they still see their own notes? What about notes about them if they're also receiving services from the agency (dual relationship)?

6. **Is the Program Report actually useful?** Will funders accept a PDF with just aggregate numbers? Or will they demand the individual-level data anyway? If so, have we just created busywork?

7. **What about the front desk seeing the client list at all?** The current system shows all client names to Front Desk. But in a DV shelter, even knowing someone is a client is sensitive. Should the client list be filtered differently for Front Desk?

8. **Export/data extract governance**: The plan says admin-only for now, dual authorization later. But what does "dual authorization" actually look like in a 5-person agency? Who's the second authorizer?

9. **Are we solving the right problem?** The original issue was: AI-built software didn't ask "should this person see this?" Maybe the deeper fix isn't permissions code — it's a design review process that asks domain questions before building features.

10. **What's the minimum viable permissions system?** We have 28 permission keys across 4 roles. Is this too complex for Phase 1? Could we ship with just 3 tiers (Front Desk / Clinical Staff / Admin) and 5 data categories instead of 28 individual permissions?

Be ruthless. I'd rather hear problems now than discover them after deployment with real client data.
