# Phase 3 Prompt: Outcomes — Plans & Targets

Copy this prompt into a new Claude Code conversation. Open the `KoNote-web` project folder first.

---

## Prompt

I'm building KoNote Web, a nonprofit client management system. Phases 1-2 are done (foundation + client/program CRUD). I need you to build **Phase 3: Plans & Targets** — this is the core feature users love most.

### Context

- Read `TODO.md` for task status
- Read `C:\Users\gilli\.claude\plans\idempotent-cooking-walrus.md` for architecture
- Models already exist in `apps/plans/models.py`: `PlanSection`, `PlanTarget`, `PlanTargetRevision`, `MetricDefinition`, `PlanTargetMetric`, `PlanTemplate`, `PlanTemplateSection`, `PlanTemplateTarget`
- The metric library (24 pre-built metrics) is seeded via `python manage.py seed`
- Use `{{ term.target }}` (not "Target"), `{{ term.section }}` (not "Section"), `{{ term.plan }}` (not "Plan") in all templates
- Stack: Django 5, server-rendered templates, HTMX, Pico CSS. No React.

### What to Build

**1. Plan View on Client Detail Page**
- Add a "Plan" tab to the client detail page at `/clients/<id>/`
- Show all plan sections for this client, each containing its targets
- Each target shows: name, description, status badge, assigned metrics
- Active targets shown by default; completed/deactivated collapsed under a toggle

**2. Plan Section CRUD**
- Add section: name, optional program assignment, sort order
- Edit section: inline editing via HTMX (click name to edit)
- Change section status (active/completed/deactivated) with reason dialog

**3. Plan Target CRUD (the key feature)**
- Add target within a section: name, description
- Edit target: inline or modal form
- Change target status with reason (dialog: "Why is this {{ term.target }} being completed/deactivated?")
- **Every edit creates a `PlanTargetRevision`** — save the old values before updating
- Assign metrics to targets: show a searchable list of enabled `MetricDefinition` records. Checkboxes to add/remove.

**4. Metric Library Browser**
- Admin page at `/admin/settings/metrics/` to browse all metrics by category
- Toggle `is_enabled` per metric (agency chooses which metrics they use)
- Create custom metrics: name, definition, category, min/max, unit
- Categories: Mental Health, Housing, Employment, Substance Use, Youth, General, Custom

**5. Plan Templates**
- Admin page to create/edit plan templates (name, description, sections with targets)
- On client plan tab: "Apply Template" button opens a dialog listing available templates
- Applying a template copies its sections and targets into the client's plan
- Template application should not overwrite existing plan data — it adds to it

**6. Target Revision History**
- On target detail/edit view, show revision history (who changed what, when)
- Read from `PlanTargetRevision` ordered by `-created_at`

### Design Guidance

- Keep the plan view clean and scannable — this is what users interact with most
- Use indentation to show hierarchy: Section → Targets → Metrics
- Use colour-coded status badges (active=green, completed=blue, deactivated=grey)
- Use HTMX for adding/editing targets without full page reloads
- Sort order matters — allow drag-to-reorder if simple, otherwise use up/down arrows

### Important Notes

- Commit after each major piece (plan view, sections, targets, metrics, templates)
- Update `TODO.md` as tasks are completed
- The RBAC middleware already restricts access by program. Staff can only add notes (Phase 4), not modify plan structure. Program Managers and Admins can modify plans.
