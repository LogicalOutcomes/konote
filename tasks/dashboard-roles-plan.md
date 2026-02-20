# Role-Based Dashboard Views — Implementation Plan

Task ID: DASH-ROLES1
Date: 2026-02-20
Build target: Today

---

## What Exists Today

**Two dashboards:**

1. **Home dashboard** (`/` via `apps/clients/urls_home.py::home()`) — template: `templates/clients/home.html`
   - Binary role logic: receptionist sees limited view, everyone else sees full clinical data
   - Shows: search bar, quick stats (active clients, alerts, notes, follow-ups), priority items, recently viewed, quick links
   - No differentiation between staff, PM, and executive

2. **Executive dashboard** (`/participants/executive/` via `apps/clients/dashboard_views.py::executive_dashboard()`) — template: `templates/clients/executive_dashboard.html`
   - De-identified aggregate metrics only (per-program: enrolment, notes, engagement, goals, intake, no-shows, portal adoption, suggestions, themes)
   - Exists but not integrated into the main home flow — users must navigate to it manually

**Role system:** `UserProgramRole` with 4 levels — receptionist (1), staff (2), program_manager (3), executive (4). Helper `_get_user_highest_role()` already exists.

---

## What We're Building

Enhance the home dashboard to show role-appropriate content automatically. No new URLs — the existing `/` route detects role and renders the right sections.

### Role → Dashboard Content

| Role | What They See | Key Difference from Today |
|------|-------------|--------------------------|
| **Receptionist** | Search, quick links, recent clients (no clinical data) | No change — already works |
| **Staff** | Their clients, their follow-ups, their recent notes, alerts for their caseload | Add "My Caseload" focus — filter stats to assigned clients |
| **Program Manager** | Program-wide overview: client counts, staff activity summary, flagged items, follow-up compliance | New PM section: program health at a glance |
| **Executive** | De-identified aggregate metrics inline on home (same data as executive dashboard) | Move executive dashboard content INTO the home page conditionally |

### Implementation Steps

#### Step 1 — Add role detection to home view

In `apps/clients/urls_home.py::home()`, after the existing `is_receptionist` check:

```python
highest_role = _get_user_highest_role(request.user)
is_pm = highest_role in ("program_manager", "executive")
is_executive = highest_role == "executive"
```

Pass `highest_role`, `is_pm`, `is_executive` to template context.

#### Step 2 — Staff view: "My Caseload" focus

For staff role, the existing dashboard already shows their data. Enhance with:

- **My follow-ups due** count (already computed, just make it prominent)
- **My recent notes** — last 5 notes by this user (already in context via `recent_notes` or add a quick query)
- **Clients needing attention** — clients in my programs with no note in 30+ days

No new queries needed — the existing view already filters by accessible clients.

#### Step 3 — PM view: program health section

Add a new template block `{% if is_pm %}` that shows:

- **Program summary cards** — for each program the PM manages:
  - Active client count
  - Notes this month (all staff)
  - Follow-ups overdue
  - Clients with no recent note (30+ days)
- **Staff activity** — notes per staff member this month (simple GROUP BY on ProgressNote.author)

Reuse the batch query pattern from `executive_dashboard()` in `dashboard_views.py` — those queries already exist, just need to be called from the home view for PMs.

#### Step 4 — Executive view: inline aggregate metrics

For executive role, render the existing executive dashboard data inline on the home page:

- Call the same data-fetching logic from `executive_dashboard()` (extract into a shared helper)
- Render a summary version on the home page (top-line cards + per-program stats)
- Keep the full `/participants/executive/` route as a detailed view

#### Step 5 — Template changes

In `templates/clients/home.html`, add conditional blocks:

```html
{% if is_executive %}
  {% include "clients/_dashboard_executive_summary.html" %}
{% elif is_pm %}
  {% include "clients/_dashboard_pm_summary.html" %}
{% else %}
  {# existing staff/receptionist view #}
{% endif %}
```

Create two new partial templates:
- `templates/clients/_dashboard_pm_summary.html` — PM program health cards
- `templates/clients/_dashboard_executive_summary.html` — executive aggregate metrics

#### Step 6 — Tests

Add to `tests/test_home_dashboard.py`:

- `test_pm_sees_program_summary` — PM gets `is_pm=True` in context, sees program health section
- `test_executive_sees_aggregate_metrics` — executive gets `is_executive=True`, sees de-identified summary
- `test_staff_does_not_see_pm_section` — staff user does not get PM content
- `test_receptionist_unchanged` — existing receptionist tests still pass

---

## Key Files to Change

| File | Change |
|------|--------|
| `apps/clients/urls_home.py` | Add role detection, PM data queries, executive data extraction |
| `apps/clients/dashboard_views.py` | Extract executive data logic into reusable helper |
| `templates/clients/home.html` | Add role-conditional blocks |
| `templates/clients/_dashboard_pm_summary.html` | New partial — PM program health cards |
| `templates/clients/_dashboard_executive_summary.html` | New partial — executive summary cards |
| `tests/test_home_dashboard.py` | Add PM and executive dashboard tests |

---

## What We're NOT Building

- No new URLs or pages — everything renders on `/`
- No funder-specific view (that's part of SCALE-ROLLUP1, waiting on Prosper requirements)
- No new JavaScript — server-rendered with existing Pico CSS cards
- No Chart.js additions — metrics are numeric summaries, not graphs
- No French translations needed if we reuse existing template strings

---

## Prompt for Implementation Session

```
Build role-based dashboard views (DASH-ROLES1). See tasks/dashboard-roles-plan.md for the full plan.

Branch: feat/dashboard-roles

Summary: Enhance the home dashboard (/) to show different content based on user role:
- Receptionist: no change (already limited)
- Staff: existing view (their clients, follow-ups, notes)
- PM: program health summary (client counts, staff activity, overdue follow-ups per program)
- Executive: inline aggregate metrics (move executive dashboard data to home page)

Key approach:
1. Add role detection to home() view using existing _get_user_highest_role()
2. Extract executive dashboard data logic into a reusable helper
3. Add PM data queries (reuse batch pattern from executive_dashboard())
4. Create 2 new partial templates (_dashboard_pm_summary.html, _dashboard_executive_summary.html)
5. Add conditional blocks in home.html
6. Add tests for PM and executive views

Files: apps/clients/urls_home.py, apps/clients/dashboard_views.py, templates/clients/home.html, tests/test_home_dashboard.py

Do NOT add French translations, Chart.js, or new URLs. Keep it simple — Pico CSS cards with server-rendered data.
```
