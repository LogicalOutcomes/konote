# Phase 6 Prompt: Customisation Admin

Copy this prompt into a new Claude Code conversation. Open the `KoNote-web` project folder first.

---

## Prompt

I'm building KoNote Web, a nonprofit client management system. Phases 1-5 are done. I need you to build **Phase 6: Customisation Admin** — this is how agencies make the system their own without editing code.

### Context

- Read `TODO.md` for task status
- Read `C:\Users\gilli\.claude\plans\idempotent-cooking-walrus.md` for architecture
- Models in `apps/admin_settings/models.py`: `TerminologyOverride`, `FeatureToggle`, `InstanceSetting`
- Default terms are in `DEFAULT_TERMS` dict in that same file
- Context processors in `konote/context_processors.py` inject `term`, `features`, `site` into all templates
- These use a 5-minute cache — after saving changes, the cache must be cleared
- Stack: Django 5, HTMX, Pico CSS. No React.

### What to Build

**1. Terminology Overrides (`/admin/settings/terminology/`)**
- Show a table of all term keys with their current display values
- Left column: term key (e.g., "client", "target", "program")
- Right column: editable text input with current value
- "Save All" button updates all changed values
- Show a preview: "With these settings, the nav will say: [Participants] | [Services]" etc.
- Clear the terminology cache after saving (`cache.delete("terminology_overrides")`)

**2. Feature Toggles (`/admin/settings/features/`)**
- Show each feature as a card with:
  - Feature name (human-readable, derived from key)
  - Description of what it does
  - Toggle switch (on/off)
- Save via HTMX — toggle and auto-save without page reload
- Clear the feature toggles cache after saving
- Feature descriptions (hardcoded in the view, not the model):
  - `shift_summaries`: "Enable shift summary notes for staff handoffs"
  - `client_avatar`: "Show client photo/avatar on file pages"
  - `programs`: "Enable multi-program support with separate teams"
  - `plan_export_to_word`: "Allow exporting plans to Word documents"
  - `events`: "Enable event tracking on client timelines"
  - `alerts`: "Enable alert banners on client files"
  - `quick_notes`: "Enable quick notes (short notes without plan targets)"
  - `analysis_charts`: "Enable progress charts on the Analysis tab"

**3. Instance Settings (`/admin/settings/general/`)**
- Form with fields for each setting:
  - Product name (what appears in nav and page titles)
  - Logo URL (optional, displayed in nav if set)
  - Date format, Time format, Timestamp format
  - Session timeout (minutes)
  - Print header text, Print footer text
  - Default client tab (dropdown: notes, info, plan, analysis)
- Save button, clear cache after saving

**4. User Management (`/admin/settings/users/`)**
- List all users with: display name, username, role summary, status, last login
- Create user form (for local auth mode): username, display name, email, password, is_admin checkbox
- Edit user: change display name, email, is_admin, is_active
- Program role assignment: show which programs the user is assigned to with their role; add/remove assignments
- Deactivate user (set `is_active=False`) — never delete users (audit trail integrity)

**5. Settings Dashboard (`/admin/settings/`)**
- Landing page with cards linking to each settings section:
  - Terminology, Features, General Settings, Users, Programs, Metrics Library, Note Templates, Plan Templates
- Each card shows a brief description and item count

### Design Guidance

- The settings area should feel professional and easy to navigate
- Use cards/sections rather than dense forms
- Terminology preview is important — agencies need to see the effect before saving
- Feature toggles should be visually clear (on = green, off = grey)
- User management should make role assignments obvious at a glance

### Important Notes

- All settings pages are admin-only (RBAC middleware already handles this for `/admin/*` routes)
- After saving terminology or features, clear the relevant cache key
- Commit after each major piece (terminology, features, settings, users, dashboard)
- Update `TODO.md` as tasks are completed
