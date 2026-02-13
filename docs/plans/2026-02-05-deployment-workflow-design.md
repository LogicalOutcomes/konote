# Deployment Workflow Design

**Date:** 2026-02-05
**Status:** Draft — awaiting approval
**Task:** [deployment-workflow-design.md](../../tasks/deployment-workflow-design.md)

## Summary

Nonprofits deploying KoNote move through three phases: Assessment → Customisation → Production. This design addresses how demo data, demo users, and role customisation work across these phases.

## Core Principle

**The user account determines data visibility.**

- Demo users see demo clients only
- Real users see real clients only
- No toggle, no mode switching — login determines everything

This eliminates the risk of staff accidentally mixing demo and real data.

## Design Decisions

### 1. Demo Data Stays Permanently

Demo clients (DEMO-001 through DEMO-005) remain in the system permanently as a training and demonstration sandbox.

**Rationale:**
- Nonprofits have 20-30% annual staff turnover; new hires need safe data to learn with
- Board members and funders often want system demonstrations
- Staff can test new workflows without risk to real client data
- Eliminates temptation to use real client data for training (privacy violation)

### 2. Login-Based Data Separation

| User type | Sees | Can create |
|-----------|------|------------|
| Demo user (`is_demo=True`) | Demo clients only | Demo clients only |
| Real user (`is_demo=False`) | Real clients only | Real clients only |

**Implementation:**
- Add `is_demo = BooleanField(default=False)` to User model
- Add `is_demo = BooleanField(default=False)` to ClientFile model
- Base client queryset filters: `client.is_demo == request.user.is_demo`
- Migrate existing DEMO-* clients to set `is_demo=True`
- Migrate existing demo-* users to set `is_demo=True`

### 3. Demo Users Mirror Real Roles

When an agency customises roles (renaming, adding, adjusting permissions), matching demo users should exist for testing and training.

**Seed demo users:**
- demo-admin — Administrator (system config, no client data)
- demo-manager — Program Manager (Employment, Housing, Kitchen only)
- demo-worker-1 — Lead Worker (program_manager for Employment, staff for Housing + Kitchen)
- demo-worker-2 — Direct Service (staff for Youth Drop-In, Newcomer, Kitchen)
- demo-executive — Executive (dashboard only, all 5 programs)
- demo-frontdesk — Front Desk (limited intake view, all 5 programs)

**When admin customises roles:**
- Renaming a role updates the demo user's display name (e.g., "Front Desk" → "Intake Clerk" makes demo-frontdesk display as "Demo Intake Clerk")
- Adding a new role prompts: "Create a demo account for this role?"
- Demo users inherit the same permission configuration as their real counterparts

### 4. Demo Content Uses Terminology Placeholders

Demo narrative content (progress notes, plan descriptions) should reflect the agency's configured terminology.

**Approach:** Store demo content as templates with placeholders:
- `{{term.client}}` → "participant", "client", "member", etc.
- `{{term.plan}}` → "care plan", "service plan", "support plan", etc.

**Rendering:** Placeholders resolve at display time using the agency's current terminology settings.

### 5. Demo Data Excluded from Reports

All aggregate statistics, funder reports, and exports exclude demo data by default.

**Implementation:**
- Create queryset manager: `ClientFile.objects.real()` → filters `is_demo=False`
- All report queries use `.real()` by default
- No option to include demo data in official reports

### 6. Visual Indicator for Demo Sessions

When logged in as a demo user, the UI displays a persistent banner:

> "You are logged in as Demo Front Desk. Changes affect demo data only."

This reinforces context without requiring users to remember a mode setting.

### 7. Demo Account Directory

Admin settings includes a "Demo Accounts" page:
- Lists all demo users with their roles
- "Log in as..." button for quick testing (bypasses password for admins only)
- Shows which demo users exist and which roles lack demo coverage

## Resolved: Admin Data Visibility

**Decision:** Admins see real data only. To view demo data, admins use "Log in as demo-admin."

**Rationale:** Keeps the model simple and consistent. One rule for everyone: your login determines your data. No special cases, no toggles.

## Deployment Phases (Revised)

### Phase 1: Assessment

Agency deploys KoNote with demo mode enabled:
- Demo clients and demo users are seeded
- Staff explore as demo-manager, demo-worker-1, demo-worker-2, demo-frontdesk, demo-executive
- Real user accounts may exist but see empty client list (no real clients yet)

### Phase 2: Customisation

Admin configures the system:
- Sets agency terminology (client → participant, etc.)
- Configures programs for their services
- Customises or adds roles; creates matching demo users
- Adjusts custom fields (archive unused, add new)
- Sets up real staff accounts via invites
- Configures SSO if using Azure AD

Demo users reflect customisations in real time for testing.

### Phase 3: Production

Staff begin real work:
- Add real clients (automatically visible only to real users)
- Demo data remains available for ongoing training
- No "flip the switch" moment — transition is gradual and natural

Phased rollout supported: one program can go live while another is still training.

## Implementation Plan

### Phase 1: Core Safety (Priority)

1. Add `is_demo` field to ClientFile model
2. Add `is_demo` field to User model
3. Create migration to set `is_demo=True` for existing DEMO-* clients
4. Create migration to set `is_demo=True` for existing demo-* users
5. Add `ClientFile.objects.real()` manager method
6. Update base client queryset to filter by `user.is_demo`
7. Add visual banner for demo user sessions
8. Update all report queries to use `.real()`

### Phase 2: Role Integration

9. Update demo user display names when roles are renamed
10. Add "Create demo account for this role?" prompt when creating roles
11. Create Demo Account Directory page in admin settings
12. Add "Log in as..." functionality for admins

### Phase 3: Content Polish

13. Convert demo narrative content to templates with terminology placeholders
14. Update demo seeding to use placeholder format
15. Add template rendering in progress note display

## Files to Modify

| File | Changes |
|------|---------|
| `apps/clients/models.py` | Add `is_demo` field, manager method |
| `apps/auth_app/models.py` | Add `is_demo` field |
| `apps/clients/views.py` | Filter queryset by user.is_demo |
| `apps/reports/views.py` | Use `.real()` for all queries |
| `templates/base.html` | Add demo session banner |
| `apps/admin_settings/views.py` | Demo account directory |
| `apps/admin_settings/management/commands/seed.py` | Set is_demo flags |
| `apps/admin_settings/management/commands/seed_demo_data.py` | Use terminology placeholders |

## Security Requirements

Based on expert security review. These are mandatory, not optional.

### Critical (Must Implement)

| Requirement | Description |
|-------------|-------------|
| **Impersonation guard** | "Log in as..." feature ONLY works for users where `is_demo=True`. Explicit check with test coverage. Reject impersonation of real users regardless of admin privileges. |
| **Immutable is_demo flag** | The `is_demo` field cannot be changed via admin UI or regular views. Set at creation only. Add to Django admin `readonly_fields`. |
| **Queryset enforcement** | Views cannot call `ClientFile.objects.all()`. Must use explicit `.real()` or `.demo()` manager methods. Consider raising error on unfiltered queries. |
| **is_demo from session only** | Never read is_demo from query params, form data, or cookies. Always derive from `request.user.is_demo`. |

### Important (Should Implement)

| Requirement | Description |
|-------------|-------------|
| **Full session termination** | Impersonation performs full logout → login as demo user. No preserved admin context. To return to admin, must re-authenticate. |
| **Audit log filtering** | Add `is_demo_context` field to audit entries. Default exports show real activity only. |
| **Demo author verification** | seed_demo_data.py must verify `author.is_demo == True` before creating demo content. Fail loudly if violated. |
| **Data egress checklist** | Document all client data output points (exports, reports, API, print views) and verify is_demo filtering on each. |
| **Impersonation audit logging** | Log every impersonation with original admin identity: "Admin Jane Smith logged in as demo-front-desk at 14:32." |

### Recommended

| Requirement | Description |
|-------------|-------------|
| **Disable direct demo login** | Demo users cannot log in directly with password. Only accessible via impersonation from admin session. |
| **Backup documentation** | Document that backups contain real PII. Provide `anonymise_real_clients` management command for creating test environments. |
| **Foreign key isolation** | Demo clients should reference demo configuration (Demo Program, demo authors) not real users or sensitive program names. |

### Accepted Risks

| Risk | Rationale |
|------|-----------|
| Demo data reveals system structure | Inherent to demo functionality. Agencies should avoid sensitive program names in demo data. |
| Shared encryption key for demo/real | Acceptable. Demo PII is synthetic; same code path simplifies implementation. |

## Out of Scope

- Multi-tenancy (each org gets their own instance)
- Automated backup/restore through UI
- Migration from other systems
- Demo data appearing in any official reports
