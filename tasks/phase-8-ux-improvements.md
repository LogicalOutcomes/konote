# Phase 8 — UX Improvements for Frontline Staff

Based on a UX review from the perspective of overworked nonprofit caseworkers.

## Implementation Order (by impact-to-effort)

### Quick wins (low effort, do first)

1. **UX5 — Fix N+1 queries** in `clients/views.py`
   - Add `prefetch_related("enrolments__program")` to `_get_accessible_clients`
   - Update loops in `client_list` and `client_search` to use cached enrolments
   - Result: 501 queries → 2 queries for 500 clients

2. **UX6 — Fix note collapse** in `templates/notes/_note_detail.html`
   - Replace `location.reload()` with HTMX call to return collapsed partial
   - Preserves scroll position

3. **UX7 — Add hx-confirm** to destructive actions
   - `_section.html` status change button
   - `_target.html` status change button
   - Program user removal

4. **UX9 — Autofocus search input** on `home.html`
   - Add `autofocus` attribute to search input

5. **UX10 — Select All for metrics** on `export_form.html`
   - Add JS "Select All / Deselect All" toggle above checkboxes

6. **UX11 — Fix error toast** in `app.js` and `base.html`
   - Add close button to toast element
   - Error toasts: no auto-dismiss
   - Success toasts: auto-dismiss after 3s

7. **UX8 — Admin nav dropdown** in `base.html`
   - Group admin items under an "Admin" dropdown using Pico's details/summary pattern

### Medium effort

8. **UX3 — Note form target selection**
   - Add checkboxes at top of `note_form.html`
   - JS to show/hide target accordions based on selection
   - All targets hidden by default until checked

9. **UX4 — Notes filtering and pagination**
   - Add filter form (date range, type, author) to `note_list.html`
   - Update `notes/views.py` to accept filter params
   - Add Django Paginator (25 notes per page)
   - HTMX-powered filter submission

10. **UX2 — HTMX client tabs**
    - Create partial templates for each tab (plan, notes, events, analysis)
    - Update views to detect `HX-Request` header and return partials
    - Update tab links to use hx-get with hx-push-url

11. **UX12 — Custom fields read-only mode**
    - Show values as text by default
    - Add "Edit" button to switch to form mode
    - HTMX swap between read and edit views

### Larger effort

12. **UX1 — Staff dashboard**
    - Recently viewed clients (session-tracked)
    - Clients not seen in 30+ days
    - Active alerts summary
    - Quick action buttons

13. **UX13–UX16** — Remaining moderate fixes
