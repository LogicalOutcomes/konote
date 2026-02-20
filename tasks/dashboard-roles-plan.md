# Role-Based Dashboard Views — Implementation Plan

Task ID: DASH-ROLES1
Date: 2026-02-20
Reviewed: 2026-02-20 — verified against codebase, corrections applied (see Review Notes below)
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

**Role system:** `UserProgramRole` with 4 levels — receptionist (1), staff (2), program_manager (3), executive (4). Two helpers exist:
- `_get_user_highest_role(user)` — returns highest *client-access* role. **Excludes executive** (returns `None` for executive-only users).
- `_get_user_highest_role_any(user)` — returns highest role **including executive**. Use this for dashboard role detection.

Both are in `apps/auth_app/decorators.py`. The home view already imports and calls `_get_user_highest_role()` at line 48.

**Batch query helpers** (already extracted in `dashboard_views.py` lines 156–489):
`_batch_enrolment_stats()`, `_batch_notes_this_week()`, `_batch_engagement_quality()`, `_batch_goal_completion()`, `_batch_intake_pending()`, `_batch_no_show_rate()`, `_batch_group_attendance()`, `_batch_portal_adoption()`, `_batch_top_themes()`, `_batch_suggestion_counts()`. These are ready to reuse for both PM and executive inline views.

**Feature flags:** Executive dashboard uses `_get_feature_flags()` (cached 300s) to conditionally show alerts, events, portal metrics. The inline summary must pass these flags to the template too.

**Existing home view context** (passed to template): `is_receptionist`, `active_count`, `total_count`, `active_alerts`, `alert_count`, `notes_today_count`, `needs_attention`, `needs_attention_count`, `pending_follow_ups`, `follow_up_count`, `accessible_programs`, `can_create`.

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

In `apps/clients/urls_home.py::home()`, after the existing `is_receptionist` check (line 48):

> **Bug fix vs. plan v1:** The original plan used `_get_user_highest_role()`, which **excludes executives** (returns `None` for executive-only users). Must use `_get_user_highest_role_any()` instead.

```python
from apps.auth_app.decorators import _get_user_highest_role_any

# existing line (keep):
user_role = _get_user_highest_role(request.user)
is_receptionist = user_role == "receptionist"

# new: detect PM and executive using the inclusive helper
highest_role_any = _get_user_highest_role_any(request.user)
is_executive = highest_role_any == "executive"
is_pm = highest_role_any == "program_manager" and not is_executive
```

**Role precedence:** Executive > PM > Staff > Receptionist. A user with both PM and executive roles sees the executive view. `is_pm` is only true for users whose *highest* role is program_manager.

Pass `highest_role_any`, `is_pm`, `is_executive` to template context.

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

Create a helper in `dashboard_views.py`:

```python
def _get_pm_summary_data(user, program_ids, base_clients):
    """Fetch PM program health metrics for inline display on home page."""
    enrolment_stats = _batch_enrolment_stats(program_ids)
    notes_week_map = _batch_notes_this_week(program_ids)
    # ... reuse other batch helpers as needed ...
    return {"program_stats": [...], ...}
```

Call from `home()` only when `is_pm` is True to avoid extra queries for other roles.

#### Step 4 — Executive view: inline aggregate metrics

For executive role, render the existing executive dashboard data inline on the home page:

- Call the same data-fetching logic from `executive_dashboard()` (extract into a shared helper)
- Render a summary version on the home page (top-line cards + per-program stats)
- Keep the full `/participants/executive/` route as a detailed view
- **Must pass feature flags** — the executive dashboard conditionally shows alerts, events, portal metrics based on `_get_feature_flags()`. The inline version needs these too.

Create a helper in `dashboard_views.py`:

```python
def _get_executive_inline_data(user, program_ids, base_clients):
    """Fetch executive summary metrics for inline display on home page."""
    flags = _get_feature_flags()
    # ... reuse batch helpers from executive_dashboard() ...
    return {"total_active": ..., "program_stats": [...], "flags": flags}
```

Call from `home()` only when `is_executive` is True.

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

Add to `tests/test_home_dashboard.py` (which already has `HomeDashboardPermissionsTest` with receptionist/staff tests):

- `test_pm_sees_program_summary` — PM gets `is_pm=True` in context, sees program health section
- `test_executive_sees_aggregate_metrics` — executive gets `is_executive=True`, sees de-identified summary
- `test_pm_gets_only_assigned_programs` — PM only sees stats for programs they manage, not all programs
- `test_executive_only_user_detected` — user with *only* executive role (no staff/PM) is correctly identified
- `test_staff_does_not_see_pm_section` — staff user does not get PM content
- `test_receptionist_unchanged` — existing receptionist tests still pass (4 tests already exist)

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
- French translations: only needed if new partials introduce new `{% trans %}` strings. Reusing strings already in executive_dashboard.html avoids translation work. If any new strings are added, run `python manage.py translate_strings` per CLAUDE.md rules.

---

## Review Notes (2026-02-20)

**Verified against codebase.** All file paths and function names confirmed accurate.

### Corrections Applied

| # | Issue | Fix |
|---|-------|-----|
| 1 | **Role detection bug** — plan used `_get_user_highest_role()` which excludes executives (returns `None` for executive-only users) | Switched to `_get_user_highest_role_any()` throughout |
| 2 | **Feature flags missing** — executive dashboard conditionally shows alerts/events/portal metrics via `_get_feature_flags()` | Added flag-passing requirement to Step 4 and helpers |
| 3 | **Role overlap undefined** — plan didn't say what happens for users with both PM + executive roles | Added precedence rule: executive > PM > staff > receptionist |
| 4 | **Translation claim too strong** — "no translations needed" was only true if reusing exact existing strings | Qualified the statement with conditions |

### Verified as Accurate

- Home view at `apps/clients/urls_home.py::home()` (line 14) — `is_receptionist` check at line 48
- Executive dashboard at `apps/clients/dashboard_views.py::executive_dashboard()` (line 514)
- 10 batch query helpers already extracted (lines 156–489) — ready to reuse
- `UserProgramRole` model at `apps/programs/models.py` with correct role choices
- `ROLE_RANK` constant at `apps/auth_app/constants.py`
- Existing tests in `tests/test_home_dashboard.py` (4 tests: receptionist/staff coverage)
- Template structure supports new conditional blocks

### Added to Plan

- 2 additional tests: `test_pm_gets_only_assigned_programs`, `test_executive_only_user_detected`
- Helper function signatures for `_get_pm_summary_data()` and `_get_executive_inline_data()`
- Existing home view context variable list (for reference during implementation)

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
1. Add role detection to home() view — IMPORTANT: use _get_user_highest_role_any() (not _get_user_highest_role()) because the original helper excludes executives
2. Extract executive dashboard data logic into _get_executive_inline_data() helper — include feature flags
3. Create _get_pm_summary_data() helper — reuse batch queries from dashboard_views.py
4. Create 2 new partial templates (_dashboard_pm_summary.html, _dashboard_executive_summary.html)
5. Add conditional blocks in home.html (executive > PM > staff > receptionist precedence)
6. Add 6 tests: PM summary, executive metrics, PM program scope, executive-only user detection, staff exclusion, receptionist unchanged

Files: apps/clients/urls_home.py, apps/clients/dashboard_views.py, templates/clients/home.html, tests/test_home_dashboard.py

IMPORTANT notes:
- Use _get_user_highest_role_any() for role detection (the original _get_user_highest_role() returns None for executive-only users)
- Pass feature flags from _get_feature_flags() when rendering executive inline data
- Use terminology variables ({{ term.client }}) in new templates, never hardcode
- Do NOT add Chart.js, new URLs, or new JavaScript. Pico CSS cards with server-rendered data.
```
