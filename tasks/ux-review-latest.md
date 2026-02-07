# KoNote2 UX Walkthrough Report

**Generated:** 2026-02-07 12:29:47  
**Command:** `pytest tests/ux_walkthrough/ -v`

## Summary

| Metric | This Run | Previous |
|--------|----------|----------|
| Pages visited | 311 |
| Critical issues | 0 |
| Warnings | 13 |
| Info items | 20 | 5 (up 15) |

## Critical Issues

_No critical issues found._

## Warning Issues

- **[Admin] Form validation — empty program name** `/programs/create/`
  Expected form errors but none found (no .errorlist elements)

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  Page has no <title> or title is empty

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No <main> landmark element found

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No <nav> element found on full page

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No <html> element found

- **[Admin] Form validation — password mismatch** `/admin/users/new/`
  Expected form errors but none found (no .errorlist elements)

- **[Admin] Submit new user** `/admin/users/new/`
  Expected redirect to contain '/admin/users/', got '/auth/users/'

- **[Admin] Update user** `/admin/users/7/edit/`
  Expected redirect to contain '/admin/users/', got '/auth/users/'

- **[Admin] Create first staff user** `/admin/users/new/`
  Expected redirect to contain '/admin/users/', got '/auth/users/'

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  Page has no <title> or title is empty

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No <main> landmark element found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No <nav> element found on full page

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No <html> element found

## Info Issues

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No headings found on page

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No <meta name="viewport"> tag found

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No skip navigation link found

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No success message found after form submission

- **[Admin] Event types list (multiple)** `/events/admin/types/`
  "Court Hearing" button/link expected but not found for Admin

- **[Admin] Event types list (multiple)** `/events/admin/types/`
  "Hospital Visit" button/link expected but not found for Admin

- **[Admin] Custom field admin (populated)** `/clients/admin/fields/`
  "Referral Source" button/link expected but not found for Admin

- **[Admin] Custom field admin (populated)** `/clients/admin/fields/`
  "Housing Status" button/link expected but not found for Admin

- **[Admin] Submit new registration link** `/admin/registration/create/`
  Table missing <caption> or aria-label

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No headings found on page

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No <meta name="viewport"> tag found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No skip navigation link found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No success message found after form submission

- **[Admin] Program with staff** `/programs/3/`
  "Amir" button/link expected but not found for Admin

- **[Admin (FR)] Audit log** `/admin/audit/`
  Table missing <caption> or aria-label

- **[Browser] Focus Management** `/clients/1/`
  Consent: No consent edit button found

- **[Browser] Focus Management** `/clients/3/`
  Custom fields: No edit button found (may not have editable fields)

- **[Browser] Focus Management** `/notes/client/5/`
  Note expansion: No note card link found

- **[Browser] Focus Management** `/plans/client/7/`
  Plan section: No edit button found

- **[Browser] Focus Management** `/clients/search/`
  Search: No #client-search input found

## Known Limitations

- Colour contrast, focus management, and responsive layout are tested via Playwright browser tests
- Colour contrast checks depend on CDN (axe-core) — require internet

## Per-Role Walkthrough Results

### Admin

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page (find admin link) | `/` | 200 | None |
| Admin settings dashboard | `/admin/settings/` | 200 | None |
| Features page | `/admin/settings/features/` | 200 | None |
| Enable custom fields | `/admin/settings/features/` | 200 | None |
| Enable events | `/admin/settings/features/` | 200 | None |
| Disable alerts | `/admin/settings/features/` | 200 | None |
| Instance settings form | `/admin/settings/instance/` | 200 | None |
| Save instance settings | `/admin/settings/instance/` | 200 | None |
| Program form validation | `/programs/create/` | 200 | 1 issue(s) |
| Programs list | `/programs/` | 200 | None |
| Create program form | `/programs/create/` | 200 | None |
| Submit new program | `/programs/create/` | 200 | None |
| Program detail | `/programs/3/` | 200 | None |
| Edit program form | `/programs/3/edit/` | 200 | None |
| Update program | `/programs/3/edit/` | 200 | None |
| Assign staff to program | `/programs/3/roles/add/` | 200 | 8 issue(s) |
| Metric library | `/plans/admin/metrics/` | 200 | None |
| Create metric form | `/plans/admin/metrics/create/` | 200 | None |
| Submit new metric | `/plans/admin/metrics/create/` | 200 | None |
| Edit metric form | `/plans/admin/metrics/2/edit/` | 200 | None |
| Update metric | `/plans/admin/metrics/2/edit/` | 200 | None |
| Toggle metric off | `/plans/admin/metrics/2/toggle/` | 200 | None |
| Plan template list | `/admin/templates/` | 200 | None |
| Create template form | `/admin/templates/create/` | 200 | None |
| Submit new template | `/admin/templates/create/` | 200 | None |
| Template detail | `/admin/templates/1/` | 200 | None |
| Add section form | `/admin/templates/1/sections/create/` | 200 | None |
| Submit new section | `/admin/templates/1/sections/create/` | 200 | None |
| Add target form | `/admin/templates/sections/1/targets/create/` | 200 | None |
| Submit new target | `/admin/templates/sections/1/targets/create/` | 200 | None |
| Edit template form | `/admin/templates/1/edit/` | 200 | None |
| Update template | `/admin/templates/1/edit/` | 200 | None |
| Note template list | `/admin/settings/note-templates/` | 200 | None |
| Create note template form | `/admin/settings/note-templates/create/` | 200 | None |
| Submit new note template | `/admin/settings/note-templates/create/` | 200 | None |
| Edit note template form | `/admin/settings/note-templates/2/edit/` | 200 | None |
| Event types list | `/events/admin/types/` | 200 | None |
| Create event type form | `/events/admin/types/create/` | 200 | None |
| Submit new event type | `/events/admin/types/create/` | 200 | None |
| Edit event type form | `/events/admin/types/2/edit/` | 200 | None |
| Update event type | `/events/admin/types/2/edit/` | 200 | None |
| Event types list (multiple) | `/events/admin/types/` | 200 | 2 issue(s) |
| Custom field admin | `/clients/admin/fields/` | 200 | None |
| Create field group form | `/clients/admin/fields/groups/create/` | 200 | None |
| Submit new field group | `/clients/admin/fields/groups/create/` | 200 | None |
| Create field definition form | `/clients/admin/fields/create/` | 200 | None |
| Submit dropdown field | `/clients/admin/fields/create/` | 200 | None |
| Submit text field | `/clients/admin/fields/create/` | 200 | None |
| Custom field admin (populated) | `/clients/admin/fields/` | 200 | 2 issue(s) |
| Edit field definition form | `/clients/admin/fields/3/edit/` | 200 | None |
| User form password mismatch | `/admin/users/new/` | 200 | 1 issue(s) |
| User list | `/admin/users/` | 200 | None |
| Create user form | `/admin/users/new/` | 200 | None |
| Submit new user | `/admin/users/new/` | 200 | 1 issue(s) |
| Edit user form | `/admin/users/7/edit/` | 200 | None |
| Update user | `/admin/users/7/edit/` | 200 | 1 issue(s) |
| Invite list | `/auth/invites/` | 200 | None |
| Create invite form | `/auth/invites/new/` | 200 | None |
| Submit new invite | `/auth/invites/new/` | 200 | None |
| Registration links list | `/admin/registration/` | 200 | None |
| Create registration link form | `/admin/registration/create/` | 200 | None |
| Submit new registration link | `/admin/registration/create/` | 200 | 1 issue(s) |
| Pending submissions | `/admin/submissions/` | 200 | None |
| Audit log list | `/admin/audit/` | 200 | None |
| Audit log filtered | `/admin/audit/?date_from=2020-01-01&date_to=2030-12-31` | 200 | None |
| Diagnose charts | `/admin/settings/diagnose-charts/` | 200 | None |
| Start at dashboard | `/admin/settings/` | 200 | None |
| Enable events feature | `/admin/settings/features/` | 200 | None |
| Create first program | `/programs/create/` | 200 | None |
| Create first metric | `/plans/admin/metrics/create/` | 200 | None |
| Create first event type | `/events/admin/types/create/` | 200 | None |
| Create first staff user | `/admin/users/new/` | 200 | 1 issue(s) |
| Assign worker to program | `/programs/3/roles/add/` | 200 | 8 issue(s) |
| Program with staff | `/programs/3/` | 200 | 1 issue(s) |
| Client detail without program role (403) | `/clients/1/` | 403 | None |
| Admin settings dashboard | `/admin/settings/` | 200 | None |
| Terminology settings | `/admin/settings/terminology/` | 200 | None |
| Feature toggles | `/admin/settings/features/` | 200 | None |
| Instance settings | `/admin/settings/instance/` | 200 | None |
| Metrics library | `/plans/admin/metrics/` | 200 | None |
| Create metric form | `/plans/admin/metrics/create/` | 200 | None |
| Programs list | `/programs/` | 200 | None |
| Create program form | `/programs/create/` | 200 | None |
| Program detail | `/programs/1/` | 200 | None |
| User list | `/admin/users/` | 200 | None |
| Create user form | `/admin/users/new/` | 200 | None |
| Invite list | `/auth/invites/` | 200 | None |
| Create invite form | `/auth/invites/new/` | 200 | None |
| Audit log | `/admin/audit/` | 200 | None |
| Registration links | `/admin/registration/` | 200 | None |
| Create registration link | `/admin/registration/create/` | 200 | None |
| Custom field admin | `/clients/admin/fields/` | 200 | None |
| Create field group | `/clients/admin/fields/groups/create/` | 200 | None |
| Create field definition | `/clients/admin/fields/create/` | 200 | None |
| Event types list | `/events/admin/types/` | 200 | None |
| Create event type | `/events/admin/types/create/` | 200 | None |
| Note templates | `/admin/settings/note-templates/` | 200 | None |
| Client data export form | `/reports/client-data-export/` | 200 | None |
| Export links management | `/reports/export-links/` | 200 | None |
| Diagnose charts | `/admin/settings/diagnose-charts/` | 200 | None |
| Pending submissions | `/admin/submissions/` | 200 | None |

### Direct Service

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin dashboard (403) | `/admin/settings/` | 403 | None |
| Form validation errors | `/notes/client/1/quick/` | 200 | None |
| Home page | `/` | 200 | None |
| Client list | `/clients/` | 200 | None |
| Create client form | `/clients/create/` | 200 | None |
| Create client submit | `/clients/create/` | 200 | None |
| Client detail | `/clients/1/` | 200 | None |
| Edit client form | `/clients/1/edit/` | 200 | None |
| Edit client submit | `/clients/1/edit/` | 200 | None |
| Consent edit form | `/clients/1/consent/edit/` | 200 | None |
| Consent submit | `/clients/1/consent/` | 200 | None |
| Custom fields edit | `/clients/1/custom-fields/edit/` | 200 | None |
| Quick note form | `/notes/client/1/quick/` | 200 | None |
| Quick note submit | `/notes/client/1/quick/` | 200 | None |
| Full note form | `/notes/client/1/new/` | 200 | None |
| Notes timeline | `/notes/client/1/` | 200 | None |
| Note detail | `/notes/1/` | 200 | None |
| Plan view (read-only) | `/plans/client/1/` | 200 | None |
| Section create (403) | `/plans/client/1/sections/create/` | 403 | None |
| Events tab | `/events/client/1/` | 200 | None |
| Event create form | `/events/client/1/create/` | 200 | None |
| Alert create form | `/events/client/1/alerts/create/` | 200 | None |
| Client analysis | `/reports/client/1/analysis/` | 200 | None |
| Programs list | `/programs/` | 200 | None |
| Client list (Housing only) | `/clients/` | 200 | None |
| Direct access to Bob's profile (403) | `/clients/2/` | 403 | None |
| Access Jane's profile (own program) | `/clients/1/` | 200 | None |
| Search for Bob (should find no results) | `/clients/search/?q=Bob` | 200 | None |
| Client create form | `/clients/create/` | 200 | None |
| View new client profile | `/clients/3/` | 200 | None |
| Document intake session | `/notes/client/3/quick/` | 200 | None |
| Notes timeline after intake | `/notes/client/3/` | 200 | None |
| Search client list by note text | `/clients/?q=seemed+well` | 200 | None |
| Dedicated search by note text | `/clients/search/?q=seemed+well` | 200 | None |
| Search for other program's note content | `/clients/search/?q=vocational` | 200 | None |

### Admin (FR)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin dashboard | `/admin/settings/` | 200 | None |
| Features | `/admin/settings/features/` | 200 | None |
| Instance settings | `/admin/settings/instance/` | 200 | None |
| Terminology | `/admin/settings/terminology/` | 200 | None |
| User list | `/admin/users/` | 200 | None |
| Metric library | `/plans/admin/metrics/` | 200 | None |
| Programs list | `/programs/` | 200 | None |
| Event types | `/events/admin/types/` | 200 | None |
| Note templates | `/admin/settings/note-templates/` | 200 | None |
| Custom fields | `/clients/admin/fields/` | 200 | None |
| Registration links | `/admin/registration/` | 200 | None |
| Audit log | `/admin/audit/` | 200 | 1 issue(s) |

### Front Desk (FR)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page (FR) | `/` | 200 | None |
| Client detail (FR) | `/clients/1/` | 200 | None |
| Programs list (FR) | `/programs/` | 200 | None |
| Home page | `/` | 200 | None |
| Client list | `/clients/` | 200 | None |
| Client detail | `/clients/1/` | 200 | None |
| Programs list | `/programs/` | 200 | None |

### Front Desk

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page | `/` | 200 | None |
| Client list | `/clients/` | 200 | None |
| Search for client | `/clients/search/?q=Jane` | 200 | None |
| Client detail | `/clients/1/` | 200 | None |
| Custom fields display | `/clients/1/custom-fields/display/` | 200 | None |
| Custom fields edit | `/clients/1/custom-fields/edit/` | 200 | None |
| Consent display | `/clients/1/consent/display/` | 200 | None |
| Create client (403) | `/clients/create/` | 403 | None |
| Notes list (403) | `/notes/client/1/` | 403 | None |
| Plan section create (403) | `/plans/client/1/sections/create/` | 403 | None |
| Programs list | `/programs/` | 200 | None |
| Search for unknown client | `/clients/search/?q=Maria` | 200 | None |
| Can't create client (403) | `/clients/create/` | 403 | None |

### Program Manager

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page | `/` | 200 | None |
| Client list | `/clients/` | 200 | None |
| Client detail | `/clients/1/` | 200 | None |
| Notes timeline | `/notes/client/1/` | 200 | None |
| Quick note form | `/notes/client/1/quick/` | 200 | None |
| Full note form | `/notes/client/1/new/` | 200 | None |
| Plan view (editable) | `/plans/client/1/` | 200 | None |
| Section create form | `/plans/client/1/sections/create/` | 200 | None |
| Section create submit | `/plans/client/1/sections/create/` | 200 | None |
| Target create form | `/plans/sections/1/targets/create/` | 200 | None |
| Target create submit | `/plans/sections/1/targets/create/` | 200 | None |
| Target metrics | `/plans/targets/1/metrics/` | 200 | None |
| Section status | `/plans/sections/1/status/` | 200 | None |
| Target status | `/plans/targets/1/status/` | 200 | None |
| Target history | `/plans/targets/1/history/` | 200 | None |
| Metrics export form | `/reports/export/` | 200 | None |
| CMT export form | `/reports/cmt-export/` | 200 | None |
| Events tab | `/events/client/1/` | 200 | None |
| Event create form | `/events/client/1/create/` | 200 | None |
| Client analysis | `/reports/client/1/analysis/` | 200 | None |
| Review new client | `/clients/3/` | 200 | None |
| Plan view (empty for new client) | `/plans/client/3/` | 200 | None |
| Create plan section | `/plans/client/3/sections/create/` | 200 | None |

### Executive

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Executive dashboard | `/clients/executive/` | 200 | None |
| Client list redirect | `/clients/` | 200 | None |
| Client detail redirect | `/clients/1/` | 200 | None |
| Programs list | `/programs/` | 200 | None |
| Notes redirect | `/notes/client/1/` | 200 | None |

### Non-admin spot check

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin settings (403) | `/admin/settings/` | 403 | None |
| User list (403) | `/admin/users/` | 403 | None |

### Admin+PM

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Client detail | `/clients/1/` | 200 | None |
| Notes timeline | `/notes/client/1/` | 200 | None |
| Plan view | `/plans/client/1/` | 200 | None |
| Admin settings | `/admin/settings/` | 200 | None |
| User list | `/admin/users/` | 200 | None |

### Admin (no program)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin blocked from client detail (403) | `/clients/1/` | 403 | None |

## Scenario Walkthroughs

### Admin Dashboard

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | Home page — admin link visible | `/` | 200 | None |
| Admin | Admin dashboard loads | `/admin/settings/` | 200 | None |
| Direct Service | Non-admin blocked (403) | `/admin/settings/` | 403 | None |

### Feature Toggles

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View feature toggles | `/admin/settings/features/` | 200 | None |
| Admin | Enable custom fields | `/admin/settings/features/` | 200 | None |
| Admin | Enable events | `/admin/settings/features/` | 200 | None |
| Admin | Disable alerts | `/admin/settings/features/` | 200 | None |

### Instance Settings

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View instance settings | `/admin/settings/instance/` | 200 | None |
| Admin | Save instance settings | `/admin/settings/instance/` | 200 | None |

### Program Management

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View programs list | `/programs/` | 200 | None |
| Admin | Open create program form | `/programs/create/` | 200 | None |
| Admin | Create program | `/programs/create/` | 200 | None |
| Admin | View program detail | `/programs/3/` | 200 | None |
| Admin | Open edit program form | `/programs/3/edit/` | 200 | None |
| Admin | Edit program saved | `/programs/3/edit/` | 200 | None |
| Admin | Assign staff to program | `/programs/3/roles/add/` | 200 | None |

### Metric Library

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View metric library | `/plans/admin/metrics/` | 200 | None |
| Admin | Open create metric form | `/plans/admin/metrics/create/` | 200 | None |
| Admin | Create metric | `/plans/admin/metrics/create/` | 200 | None |
| Admin | Open edit metric form | `/plans/admin/metrics/2/edit/` | 200 | None |
| Admin | Edit metric saved | `/plans/admin/metrics/2/edit/` | 200 | None |
| Admin | Toggle metric | `/plans/admin/metrics/2/toggle/` | 200 | None |

### Plan Templates

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View plan template list | `/admin/templates/` | 200 | None |
| Admin | Open create template form | `/admin/templates/create/` | 200 | None |
| Admin | Create template | `/admin/templates/create/` | 200 | None |
| Admin | View template detail | `/admin/templates/1/` | 200 | None |
| Admin | Open add section form | `/admin/templates/1/sections/create/` | 200 | None |
| Admin | Create section | `/admin/templates/1/sections/create/` | 200 | None |
| Admin | Open add target form | `/admin/templates/sections/1/targets/create/` | 200 | None |
| Admin | Create target | `/admin/templates/sections/1/targets/create/` | 200 | None |
| Admin | Open edit template form | `/admin/templates/1/edit/` | 200 | None |
| Admin | Edit template saved | `/admin/templates/1/edit/` | 200 | None |

### Note Templates

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View note template list | `/admin/settings/note-templates/` | 200 | None |
| Admin | Open create note template form | `/admin/settings/note-templates/create/` | 200 | None |
| Admin | Create note template with section | `/admin/settings/note-templates/create/` | 200 | None |
| Admin | Open edit note template form | `/admin/settings/note-templates/2/edit/` | 200 | None |

### Event Types

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View event types list | `/events/admin/types/` | 200 | None |
| Admin | Open create event type form | `/events/admin/types/create/` | 200 | None |
| Admin | Create event type | `/events/admin/types/create/` | 200 | None |
| Admin | Open edit event type form | `/events/admin/types/2/edit/` | 200 | None |
| Admin | Edit event type saved | `/events/admin/types/2/edit/` | 200 | None |
| Admin | List shows multiple event types | `/events/admin/types/` | 200 | None |

### Custom Client Fields

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View custom field admin | `/clients/admin/fields/` | 200 | None |
| Admin | Open create field group form | `/clients/admin/fields/groups/create/` | 200 | None |
| Admin | Create field group | `/clients/admin/fields/groups/create/` | 200 | None |
| Admin | Open create field definition form | `/clients/admin/fields/create/` | 200 | None |
| Admin | Create dropdown field | `/clients/admin/fields/create/` | 200 | None |
| Admin | Create sensitive text field | `/clients/admin/fields/create/` | 200 | None |
| Admin | Fields visible in admin | `/clients/admin/fields/` | 200 | None |
| Admin | Open edit field definition form | `/clients/admin/fields/3/edit/` | 200 | None |

### User Management

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View user list | `/admin/users/` | 200 | None |
| Admin | Open create user form | `/admin/users/new/` | 200 | None |
| Admin | Create user | `/admin/users/new/` | 200 | None |
| Admin | Open edit user form | `/admin/users/7/edit/` | 200 | None |
| Admin | Edit user saved | `/admin/users/7/edit/` | 200 | None |

### Invite System

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View invite list | `/auth/invites/` | 200 | None |
| Admin | Open create invite form | `/auth/invites/new/` | 200 | None |
| Admin | Create invite link | `/auth/invites/new/` | 200 | None |

### Registration Links

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View registration links | `/admin/registration/` | 200 | None |
| Admin | Open create registration link form | `/admin/registration/create/` | 200 | None |
| Admin | Create registration link | `/admin/registration/create/` | 200 | None |
| Admin | View pending submissions | `/admin/submissions/` | 200 | None |

### Audit Logs

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View audit log | `/admin/audit/` | 200 | None |
| Admin | Filter audit log by date | `/admin/audit/?date_from=2020-01-01&date_to=2030-12-31` | 200 | None |
| Admin | Diagnose charts tool | `/admin/settings/diagnose-charts/` | 200 | None |

### Full Agency Setup

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | 1. Start at admin dashboard | `/admin/settings/` | 200 | None |
| Admin | 2. Enable events feature | `/admin/settings/features/` | 200 | None |
| Admin | 3. Create program | `/programs/create/` | 200 | None |
| Admin | 4. Create metric | `/plans/admin/metrics/create/` | 200 | None |
| Admin | 5. Create event type | `/events/admin/types/create/` | 200 | None |
| Admin | 6. Create staff user | `/admin/users/new/` | 200 | None |
| Admin | 7. Assign staff to program | `/programs/3/roles/add/` | 200 | None |
| Admin | 8. Verify staff visible on program | `/programs/3/` | 200 | None |

### Admin in French

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin (FR) | Admin dashboard | `/admin/settings/` | 200 | None |
| Admin (FR) | Features | `/admin/settings/features/` | 200 | None |
| Admin (FR) | Instance settings | `/admin/settings/instance/` | 200 | None |
| Admin (FR) | Terminology | `/admin/settings/terminology/` | 200 | None |
| Admin (FR) | User list | `/admin/users/` | 200 | None |
| Admin (FR) | Metric library | `/plans/admin/metrics/` | 200 | None |
| Admin (FR) | Programs list | `/programs/` | 200 | None |
| Admin (FR) | Event types | `/events/admin/types/` | 200 | None |
| Admin (FR) | Note templates | `/admin/settings/note-templates/` | 200 | None |
| Admin (FR) | Custom fields | `/clients/admin/fields/` | 200 | None |
| Admin (FR) | Registration links | `/admin/registration/` | 200 | None |
| Admin (FR) | Audit log | `/admin/audit/` | 200 | None |

### Cross-Program Isolation

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin (no program) | Admin blocked from Jane (403) | `/clients/1/` | 403 | None |
| Direct Service | Client list (Housing only) | `/clients/` | 200 | None |
| Direct Service | Direct access to Bob (403) | `/clients/2/` | 403 | None |
| Direct Service | HTMX partial for Bob (403) | `/clients/2/custom-fields/display/` | 403 | None |
| Direct Service | Jane's profile (own program) | `/clients/1/` | 200 | None |
| Direct Service | Search for Bob (no results expected) | `/clients/search/?q=Bob` | 200 | None |

### Morning Intake Flow

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Front Desk | Search for Maria (not found) | `/clients/search/?q=Maria` | 200 | None |
| Front Desk | Dana blocked from creating client | `/clients/create/` | 403 | None |
| Direct Service | Open create form | `/clients/create/` | 200 | None |
| Direct Service | View Maria's profile | `/clients/3/` | 200 | None |
| Direct Service | Write intake note | `/notes/client/3/quick/` | 200 | None |
| Direct Service | Check notes timeline | `/notes/client/3/` | 200 | None |
| Program Manager | Review Maria's profile | `/clients/3/` | 200 | None |
| Program Manager | View empty plan | `/plans/client/3/` | 200 | None |
| Program Manager | Create plan section | `/plans/client/3/sections/create/` | 200 | None |

### Full French Workday

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Front Desk (FR) | Home page | `/` | 200 | None |
| Front Desk (FR) | Client list | `/clients/` | 200 | None |
| Front Desk (FR) | Client detail | `/clients/1/` | 200 | None |
| Front Desk (FR) | Programs list | `/programs/` | 200 | None |

### Client Note Search

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Direct Service | Client list search by note content | `/clients/?q=seemed+well` | 200 | None |
| Direct Service | Dedicated search by note content | `/clients/search/?q=seemed+well` | 200 | None |
| Direct Service | Note search isolation (no cross-program leak) | `/clients/search/?q=vocational` | 200 | None |

## Browser-Based Findings

_Tested with Playwright (headless Chromium) + axe-core._

### Focus Management

- **[INFO]** `/clients/1/` — Consent: No consent edit button found

- **[INFO]** `/clients/3/` — Custom fields: No edit button found (may not have editable fields)

- **[INFO]** `/notes/client/5/` — Note expansion: No note card link found

- **[INFO]** `/plans/client/7/` — Plan section: No edit button found

- **[INFO]** `/clients/search/` — Search: No #client-search input found

## Recommendations

### Short-term (Warnings)

- Expected form errors but none found (no .errorlist elements) (`/programs/create/`)
- Page has no <title> or title is empty (`/programs/3/roles/add/`)
- No <main> landmark element found (`/programs/3/roles/add/`)
- No <nav> element found on full page (`/programs/3/roles/add/`)
- No <html> element found (`/programs/3/roles/add/`)
- Expected form errors but none found (no .errorlist elements) (`/admin/users/new/`)
- Expected redirect to contain '/admin/users/', got '/auth/users/' (`/admin/users/new/`)
- Expected redirect to contain '/admin/users/', got '/auth/users/' (`/admin/users/7/edit/`)
- Expected redirect to contain '/admin/users/', got '/auth/users/' (`/admin/users/new/`)
- Page has no <title> or title is empty (`/programs/3/roles/add/`)
- No <main> landmark element found (`/programs/3/roles/add/`)
- No <nav> element found on full page (`/programs/3/roles/add/`)
- No <html> element found (`/programs/3/roles/add/`)

---

_Generated by `tests/ux_walkthrough/` — automated UX walkthrough_
