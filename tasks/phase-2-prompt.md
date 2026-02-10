# Phase 2 Prompt: Core Data — Programs & Clients

Copy this prompt into a new Claude Code conversation. Open the `KoNote-web` project folder first.

---

## Prompt

I'm building a nonprofit client management system called KoNote Web. Phase 1 (foundation) is done — Django 5 project with PostgreSQL, Docker, security middleware, and all data models. I need you to build **Phase 2: Programs & Client Management**.

### Context

- Read `TODO.md` for the full task list
- Read the plan at `C:\Users\gilli\.claude\plans\idempotent-cooking-walrus.md` for architecture details
- The project uses **Django 5, server-rendered templates, HTMX, Pico CSS** — no React, no npm
- All PII fields on `ClientFile` are encrypted via `konote/encryption.py` (Fernet). Use the property accessors (e.g., `client.first_name = "Jane"`) — never write to `_first_name_encrypted` directly
- RBAC middleware at `konote/middleware/program_access.py` already enforces program-scoped access. Views just need `@login_required`
- Terminology is dynamic — use `{{ term.client }}` in templates, never hardcode "Client"
- Feature toggles are available as `{{ features.programs }}` in templates

### What to Build

**1. Program Management (Admin only)**
- File: `apps/programs/views.py` and `apps/programs/urls.py`
- Templates: `templates/programs/list.html`, `templates/programs/form.html`
- List all programs with colour dots and status badges
- Create/edit program form (name, description, colour picker, status)
- Restrict to admin users only (`if not request.user.is_admin: return 403`)

**2. User-Program Role Assignment (Admin only)**
- On the program detail/edit page, show assigned users with their roles
- Form to add a user to a program with role selection (Staff / Program Manager)
- Form to remove a user from a program (set status to "removed")

**3. Client File CRUD**
- File: `apps/clients/views.py` and `apps/clients/urls.py`
- Templates: `templates/clients/list.html`, `templates/clients/detail.html`, `templates/clients/form.html`
- Client list: show name, record ID, status, enrolled programs. Filter by user's accessible programs (non-admins only see their program's clients)
- Client detail: tabbed view with Info, Plan, Notes, Analysis tabs (only Info tab functional in this phase — others show "Coming in Phase X")
- Create/edit client: form for first name, last name, middle name, birth date, record ID, status
- Enrol client in programs via checkboxes on the form

**4. Custom Fields**
- Admin UI to manage `CustomFieldGroup` and `CustomFieldDefinition` (in `apps/clients/models.py`)
- On the client detail Info tab, render custom field groups with their fields
- Save values to `ClientDetailValue` — use `set_value()` / `get_value()` methods which handle encryption for sensitive fields

**5. Client Search (HTMX)**
- On the home page (`templates/clients/home.html`), the search input already has HTMX attributes
- Create a view that returns a partial HTML fragment of matching clients
- Search across decrypted first_name and last_name (note: encrypted fields can't be searched in SQL — load accessible clients and filter in Python, with pagination)

### Important Notes

- Run `python manage.py makemigrations` and `python manage.py migrate` if you change any models
- Commit after each major piece (programs, clients, custom fields, search)
- Keep forms simple — Pico CSS styles forms automatically with `<label>` + `<input>` pairs
- Use HTMX `hx-get`, `hx-post`, `hx-target` for dynamic interactions instead of full page reloads where it makes sense
- Test that non-admin users cannot access program management pages
- Test that a staff user assigned to Program A cannot see clients only in Program B
