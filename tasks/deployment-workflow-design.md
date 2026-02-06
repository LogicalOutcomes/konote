# Task: Design the Nonprofit Deployment Workflow

## Context

KoNote is a client outcome management system for nonprofits. Organizations will deploy their own instance and go through three phases:

1. **Assessment** — Explore the demo to understand how KoNote works
2. **Customization** — Configure it for their organization (terminology, programs, roles, fields)
3. **Production** — Add real clients and begin actual use

The target users are **nonprofit staff, not developers**. The workflow must be simple, safe, and hard to mess up.

## Current State

- Demo mode creates 15 sample clients (DEMO-001 to DEMO-015) across 5 programs with plans, notes, events, and metrics
- Six demo users exist with differentiated roles:
  - demo-admin (system config), demo-manager (program_manager for 3 programs)
  - demo-worker-1 (mixed: program_manager + staff), demo-worker-2 (staff only)
  - demo-executive (dashboard only), demo-frontdesk (receptionist)
- Custom fields are seeded with Canadian nonprofit defaults
- Demo data is protected by `DEMO_MODE=True` environment variable

## Problems to Solve

### 1. Demo Data Lifecycle

When a nonprofit is ready to go live, what happens to the demo clients?

**Options to consider:**
- **Delete permanently** — Clean slate, but loses the reference examples
- **Archive/hide** — Keep for training, but clutters client lists
- **Separate "sandbox" mode** — Demo data only visible when toggled on
- **Export as templates** — Convert demo plans into reusable templates, then delete

**Questions:**
- Should demo clients ever appear in reports or metrics?
- How do we prevent accidental deletion of real clients vs. intentional deletion of demo clients?
- What about the demo users — delete them or keep for testing?

### 2. Role Customization

The demo includes four roles: Manager, Direct Service, Front Desk, Admin. Real organizations may need:
- Different role names (e.g., "Case Worker" instead of "Direct Service")
- Additional roles (e.g., "Volunteer", "Supervisor", "Intern")
- Different permission sets

**Questions:**
- How do we let orgs customize roles without breaking the permission system?
- Should we allow creating new roles, or just renaming existing ones?
- What's the minimum viable permission model for nonprofits?

### 3. The Transition Workflow

Design a clear path from demo → customization → production:

**Assessment Phase:**
- Deploy with demo data
- Explore as demo-manager, demo-worker-1, demo-worker-2, demo-frontdesk
- Understand the features before making decisions

**Customization Phase:**
- Set agency terminology (e.g., "Participant" instead of "Client")
- Configure programs for their services
- Adjust custom fields (archive unused, add new ones)
- Set up real staff user accounts
- Configure SSO if using Azure AD

**Production Phase:**
- Disable demo mode or archive demo data
- Add real clients
- Begin recording actual outcomes

**Questions:**
- Should there be a "Setup Wizard" that guides through customization?
- How do we signal that the org is "ready" to go live?
- What happens if they start adding real clients while demo data still exists?

### 4. Data Safety

Nonprofits handle sensitive client information. The deployment workflow must be:
- **Reversible** — Mistakes can be undone
- **Auditable** — Changes are logged
- **Clear** — Users understand what will happen before they do it

**Questions:**
- Should deleting demo data require confirmation or a waiting period?
- How do we prevent accidental deletion of real client data?
- Should there be a "demo mode" indicator visible in the UI?

## Deliverables

1. **Workflow diagram** — The three phases with clear transition points
2. **UI/UX design** — How users interact with demo data lifecycle (admin interface)
3. **Implementation plan** — What needs to be built, in what order
4. **Documentation** — Plain-language guide for nonprofit admins

## Constraints

- No command-line requirements for nonprofit staff
- Everything manageable through the web interface
- Works with both local auth and Azure SSO
- Must not accidentally mix demo and real data

## Reference Files

- Current demo seeding: `apps/admin_settings/management/commands/seed.py`
- Demo data creation: `apps/admin_settings/management/commands/seed_demo_data.py`
- Client model: `apps/clients/models.py`
- Role/permission system: `apps/auth_app/models.py`
- Admin dashboard: `templates/admin_settings/dashboard.html`

## Out of Scope (for now)

- Multi-tenancy (each org gets their own instance)
- Automated backup/restore through UI
- Migration from other systems
