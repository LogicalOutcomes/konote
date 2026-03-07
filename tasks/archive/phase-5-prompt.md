# Phase 5 Prompt: Visualisation, Events & Audit

Copy this prompt into a new Claude Code conversation. Open the `KoNote-web` project folder first.

---

## Prompt

I'm building KoNote Web, a nonprofit client management system. Phases 1-4 are done (foundation, clients, plans, notes). I need you to build **Phase 5: Charts, Events & Audit Viewer**.

### Context

- Read `TODO.md` for task status
- Read `C:\Users\gilli\.claude\plans\idempotent-cooking-walrus.md` for architecture
- Event/alert models in `apps/events/models.py`, audit model in `apps/audit/models.py`
- Metric values are in `apps/notes/models.py` (`MetricValue` linked to `ProgressNoteTarget`)
- Chart.js is already included via CDN in `templates/base.html` (add `<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>` to the extra_scripts block)
- Stack: Django 5, HTMX, Pico CSS, Chart.js. No React.

### What to Build

**1. Progress Charts (Analysis Tab)**
- Add "Analysis" tab to client detail page
- For each metric assigned to the client's plan targets, show a line chart of values over time
- X-axis: date (from progress note timestamps), Y-axis: metric value
- Filter by: specific target, specific metric, date range
- Show min/max reference lines from metric definition
- Use Chart.js — pass data as JSON in a `<script>` block, no API endpoints needed
- View at `/clients/<id>/analysis/`

**2. Event Types (Admin)**
- Admin UI to manage event types: name, description, colour
- Seeded defaults: Intake, Discharge, Crisis, Referral, Follow-up

**3. Event CRUD**
- On client detail page, add events from a timeline or dedicated events section
- Event form: title, description, start date/time, optional end date/time, event type, optional link to a progress note
- Events show on the client timeline with coloured dots matching their event type

**4. Alerts**
- On client detail page, show active alerts as a warning banner at the top
- Alert form: content text
- Cancel alert with reason (never delete)
- Alerts visible to all staff who can access the client

**5. Client Timeline View**
- Combined chronological view of progress notes AND events for a client
- Each entry shows: date, type icon/badge, summary
- Click to expand details
- This becomes the primary way to see a client's journey at a glance
- Use the `.timeline` CSS classes already defined in `static/css/main.css`

**6. Aggregate Metrics Export (Funder Reporting)**
- Admin or Program Manager view at `/reports/export/`
- Form: select program, select metric(s), date range (start/end)
- Generates a CSV with columns: client record ID, metric name, value, date, author
- One row per metric value — funders can pivot/aggregate in Excel
- Include a summary row at the top: program name, date range, total clients, total data points
- This is the critical feature for funder accountability — agencies need to answer "how are our clients doing overall?"

**7. Audit Log Viewer (Admin only)**
- View at `/admin/audit/`
- Table showing: timestamp, user, action, resource type, resource ID
- Filter by: date range, user, action type, resource type
- CSV export button (generates and downloads a CSV file)
- Pagination (50 entries per page)
- Reads from the `audit` database via `AuditLog.objects.using("audit")`

### Design Guidance

- Charts should be simple and readable — one metric per chart, not too many on one page
- The timeline should clearly distinguish notes (pen icon) from events (calendar icon) from alerts (warning icon)
- Audit log should feel like a professional compliance tool — clean table, clear filters
- Use Chart.js "line" type with filled area for a clean look

### Important Notes

- Charts are read-only — no state changes, so no RBAC concerns beyond program access
- Audit viewer is admin-only
- Commit after each major piece (charts, events, alerts, timeline, audit)
- Update `TODO.md` as tasks are completed
