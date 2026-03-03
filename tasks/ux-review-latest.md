# KoNote UX Walkthrough Report

**Generated:** 2026-03-02 23:22:06  
**Command:** `pytest tests/ux_walkthrough/ -v`

## Summary

| Metric | This Run | Previous |
|--------|----------|----------|
| Pages visited | 321 | 321 (same) |
| Critical issues | 24 | 1 (up 23) |
| Warnings | 7 |
| Info items | 8 | 29 (down 21) |

## Critical Issues

- **[Front Desk] Notes list (403)** `/notes/client/1/`
  Expected 403, got 301

- **[Front Desk] Plan section create (403)** `/plans/client/1/sections/create/`
  Expected 403, got 301

- **[Direct Service] Quick note form** `/notes/client/1/quick/`
  Expected 200, got 301

- **[Direct Service] Full note form** `/notes/client/1/new/`
  Expected 200, got 301

- **[Direct Service] Notes timeline** `/notes/client/1/`
  Expected 200, got 301

- **[Direct Service] Plan view** `/plans/client/1/`
  Expected 200, got 301

- **[Direct Service] Section create form** `/plans/client/1/sections/create/`
  Expected 200, got 301

- **[Direct Service] Events tab** `/events/client/1/`
  Expected 200, got 301

- **[Direct Service] Event create form** `/events/client/1/create/`
  Expected 200, got 301

- **[Direct Service] Alert create form** `/events/client/1/alerts/create/`
  Expected 200, got 301

- **[Direct Service] Client analysis** `/reports/client/1/analysis/`
  Expected 200, got 301

- **[Program Manager] Notes timeline** `/notes/client/1/`
  Expected 200, got 301

- **[Program Manager] Quick note form** `/notes/client/1/quick/`
  Expected 200, got 301

- **[Program Manager] Full note form** `/notes/client/1/new/`
  Expected 200, got 301

- **[Program Manager] Plan view (read-only)** `/plans/client/1/`
  Expected 200, got 301

- **[Program Manager] Section create form (403)** `/plans/client/1/sections/create/`
  Expected 403, got 301

- **[Program Manager] Events tab** `/events/client/1/`
  Expected 200, got 301

- **[Program Manager] Event create form (403)** `/events/client/1/create/`
  Expected 403, got 301

- **[Program Manager] Client analysis** `/reports/client/1/analysis/`
  Expected 200, got 301

- **[Admin+PM] Notes timeline** `/notes/client/1/`
  Expected 200, got 301

- **[Admin+PM] Plan view** `/plans/client/1/`
  Expected 200, got 301

- **[Direct Service] Notes timeline after intake** `/notes/client/3/`
  Expected 200, got 301

- **[Program Manager] Plan view (empty for new client)** `/plans/client/3/`
  Expected 200, got 301

- **[Program Manager] Create plan section (403)** `/plans/client/3/sections/create/`
  Expected 403, got 301

## Warning Issues

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  Expected form errors but none found (no .errorlist, .badge-danger, or .error elements)

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  Page has no <title> or title is empty

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  No <main> landmark element found

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  No <nav> element found on full page

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  No <html> element found

- **[Direct Service] Quick note submit** `/notes/client/1/quick/`
  Expected redirect to contain '/notes/client/1/', got '/notes/participant/1/quick/'

- **[Direct Service] Document intake session** `/notes/client/3/quick/`
  Expected redirect to contain '/notes/client/3/', got '/notes/participant/3/quick/'

## Info Issues

- **[Admin] Event types list (multiple)** `/manage/event-types/`
  "Court Hearing" button/link expected but not found for Admin

- **[Admin] Event types list (multiple)** `/manage/event-types/`
  "Hospital Visit" button/link expected but not found for Admin

- **[Admin] Custom field admin (populated)** `/participants/admin/fields/`
  "Referral Source" button/link expected but not found for Admin

- **[Admin] Custom field admin (populated)** `/participants/admin/fields/`
  "Housing Status" button/link expected but not found for Admin

- **[Admin] Program with staff** `/programs/3/`
  "Amir" button/link expected but not found for Admin

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  No headings found on page

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  No <meta name="viewport"> tag found

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  No skip navigation link found

## Known Limitations

- Colour contrast not tested (requires browser rendering)
- Focus management after HTMX swaps not tested
- Visual layout / responsive behaviour not tested

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
| Program form validation | `/programs/create/` | 200 | None |
| Programs list | `/programs/` | 200 | None |
| Create program form | `/programs/create/` | 200 | None |
| Submit new program | `/programs/create/` | 200 | None |
| Program detail | `/programs/3/` | 200 | None |
| Edit program form | `/programs/3/edit/` | 200 | None |
| Update program | `/programs/3/edit/` | 200 | None |
| Assign staff to program | `/programs/3/roles/add/` | 200 | None |
| Metric library | `/manage/metrics/` | 200 | None |
| Create metric form | `/manage/metrics/create/` | 200 | None |
| Submit new metric | `/manage/metrics/create/` | 200 | None |
| Edit metric form | `/manage/metrics/2/edit/` | 200 | None |
| Update metric | `/manage/metrics/2/edit/` | 200 | None |
| Toggle metric off | `/manage/metrics/2/toggle/` | 200 | None |
| Plan template list | `/manage/templates/` | 200 | None |
| Create template form | `/manage/templates/create/` | 200 | None |
| Submit new template | `/manage/templates/create/` | 200 | None |
| Template detail | `/manage/templates/1/` | 200 | None |
| Add section form | `/manage/templates/1/sections/create/` | 200 | None |
| Submit new section | `/manage/templates/1/sections/create/` | 200 | None |
| Add target form | `/manage/templates/sections/1/targets/create/` | 200 | None |
| Submit new target | `/manage/templates/sections/1/targets/create/` | 200 | None |
| Edit template form | `/manage/templates/1/edit/` | 200 | None |
| Update template | `/manage/templates/1/edit/` | 200 | None |
| Note template list | `/manage/note-templates/` | 200 | None |
| Create note template form | `/manage/note-templates/create/` | 200 | None |
| Submit new note template | `/manage/note-templates/create/` | 200 | None |
| Edit note template form | `/manage/note-templates/2/edit/` | 200 | None |
| Event types list | `/manage/event-types/` | 200 | None |
| Create event type form | `/manage/event-types/create/` | 200 | None |
| Submit new event type | `/manage/event-types/create/` | 200 | None |
| Edit event type form | `/manage/event-types/2/edit/` | 200 | None |
| Update event type | `/manage/event-types/2/edit/` | 200 | None |
| Event types list (multiple) | `/manage/event-types/` | 200 | 2 issue(s) |
| Custom field admin | `/participants/admin/fields/` | 200 | None |
| Create field group form | `/participants/admin/fields/groups/create/` | 200 | None |
| Submit new field group | `/participants/admin/fields/groups/create/` | 200 | None |
| Create field definition form | `/participants/admin/fields/create/` | 200 | None |
| Submit dropdown field | `/participants/admin/fields/create/` | 200 | None |
| Submit text field | `/participants/admin/fields/create/` | 200 | None |
| Custom field admin (populated) | `/participants/admin/fields/` | 200 | 2 issue(s) |
| Edit field definition form | `/participants/admin/fields/3/edit/` | 200 | None |
| User form password mismatch | `/manage/users/new/` | 200 | None |
| User list | `/manage/users/` | 200 | None |
| Create user form | `/manage/users/new/` | 200 | None |
| Submit new user | `/manage/users/new/` | 200 | None |
| Edit user form | `/manage/users/7/edit/` | 200 | None |
| Update user | `/manage/users/7/edit/` | 200 | None |
| Invite list | `/manage/users/invites/` | 200 | None |
| Create invite form | `/manage/users/invites/new/` | 200 | None |
| Submit new invite | `/manage/users/invites/new/` | 200 | None |
| Registration links list | `/manage/registration/` | 200 | None |
| Create registration link form | `/manage/registration/create/` | 200 | None |
| Submit new registration link | `/manage/registration/create/` | 200 | None |
| Pending submissions | `/manage/submissions/` | 200 | None |
| Audit log list | `/manage/audit/` | 200 | None |
| Audit log filtered | `/manage/audit/?date_from=2020-01-01&date_to=2030-12-31` | 200 | None |
| Diagnose charts | `/admin/settings/diagnose-charts/` | 200 | None |
| Start at dashboard | `/admin/settings/` | 200 | None |
| Enable events feature | `/admin/settings/features/` | 200 | None |
| Create first program | `/programs/create/` | 200 | None |
| Create first metric | `/manage/metrics/create/` | 200 | None |
| Create first event type | `/manage/event-types/create/` | 200 | None |
| Create first staff user | `/manage/users/new/` | 200 | None |
| Assign worker to program | `/programs/3/roles/add/` | 200 | None |
| Program with staff | `/programs/3/` | 200 | 1 issue(s) |
| Client detail without program role (403) | `/participants/1/` | 403 | None |
| Admin settings dashboard | `/admin/settings/` | 200 | None |
| Terminology settings | `/admin/settings/terminology/` | 200 | None |
| Feature toggles | `/admin/settings/features/` | 200 | None |
| Instance settings | `/admin/settings/instance/` | 200 | None |
| Metrics library | `/manage/metrics/` | 200 | None |
| Create metric form | `/manage/metrics/create/` | 200 | None |
| Programs list | `/programs/` | 200 | None |
| Create program form | `/programs/create/` | 200 | None |
| Program detail | `/programs/1/` | 200 | None |
| User list | `/manage/users/` | 200 | None |
| Create user form | `/manage/users/new/` | 200 | None |
| Invite list | `/manage/users/invites/` | 200 | None |
| Create invite form | `/manage/users/invites/new/` | 200 | None |
| Audit log | `/manage/audit/` | 200 | None |
| Registration links | `/manage/registration/` | 200 | None |
| Create registration link | `/manage/registration/create/` | 200 | None |
| Custom field admin | `/participants/admin/fields/` | 200 | None |
| Create field group | `/participants/admin/fields/groups/create/` | 200 | None |
| Create field definition | `/participants/admin/fields/create/` | 200 | None |
| Event types list | `/manage/event-types/` | 200 | None |
| Create event type | `/manage/event-types/create/` | 200 | None |
| Note templates | `/manage/note-templates/` | 200 | None |
| Export links management | `/reports/export-links/` | 200 | None |
| Diagnose charts | `/admin/settings/diagnose-charts/` | 200 | None |
| Pending submissions | `/manage/submissions/` | 200 | None |

### Direct Service

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin dashboard (403) | `/admin/settings/` | 403 | None |
| Form validation errors | `/notes/client/1/quick/` | 301 | 8 issue(s) |
| Home page | `/` | 200 | None |
| Client list | `/participants/` | 200 | None |
| Create client form | `/participants/create/` | 200 | None |
| Create client submit | `/participants/create/` | 200 | None |
| Client detail | `/participants/1/` | 200 | None |
| Edit client form | `/participants/1/edit/` | 200 | None |
| Edit client submit | `/participants/1/edit/` | 200 | None |
| Consent edit form | `/participants/1/consent/edit/` | 200 | None |
| Consent submit | `/participants/1/consent/` | 200 | None |
| Custom fields edit | `/participants/1/custom-fields/edit/` | 200 | None |
| Quick note form | `/notes/client/1/quick/` | 301 | 1 issue(s) |
| Quick note submit | `/notes/client/1/quick/` | 200 | 1 issue(s) |
| Full note form | `/notes/client/1/new/` | 301 | 1 issue(s) |
| Notes timeline | `/notes/client/1/` | 301 | 1 issue(s) |
| Note detail | `/notes/1/` | 200 | None |
| Plan view | `/plans/client/1/` | 301 | 1 issue(s) |
| Section create form | `/plans/client/1/sections/create/` | 301 | 1 issue(s) |
| Events tab | `/events/client/1/` | 301 | 1 issue(s) |
| Event create form | `/events/client/1/create/` | 301 | 1 issue(s) |
| Alert create form | `/events/client/1/alerts/create/` | 301 | 1 issue(s) |
| Client analysis | `/reports/client/1/analysis/` | 301 | 1 issue(s) |
| Programs list | `/programs/` | 200 | None |
| Client list (Housing only) | `/participants/` | 200 | None |
| Direct access to Bob's profile (403) | `/participants/2/` | 403 | None |
| Access Jane's profile (own program) | `/participants/1/` | 200 | None |
| Target history for Bob (403) | `/plans/targets/2/history/` | 403 | None |
| Search for Bob (should find no results) | `/participants/search/?q=Bob` | 200 | None |
| View new client profile | `/participants/3/` | 200 | None |
| Document intake session | `/notes/client/3/quick/` | 200 | 1 issue(s) |
| Notes timeline after intake | `/notes/client/3/` | 301 | 1 issue(s) |
| Search client list by note text | `/participants/?q=seemed+well` | 200 | None |
| Dedicated search by note text | `/participants/search/?q=seemed+well` | 200 | None |
| Search for other program's note content | `/participants/search/?q=vocational` | 200 | None |
| Group detail (other program, 403) | `/groups/2/` | 403 | None |
| Milestone edit (other program, 403) | `/groups/milestone/1/edit/` | 403 | None |
| Own program group (200) | `/groups/1/` | 200 | None |
| Session log (other program, 403) | `/groups/2/session/` | 403 | None |
| Target history (other program, 403) | `/plans/targets/2/history/` | 403 | None |

### Admin (FR)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin dashboard | `/admin/settings/` | 200 | None |
| Features | `/admin/settings/features/` | 200 | None |
| Instance settings | `/admin/settings/instance/` | 200 | None |
| Terminology | `/admin/settings/terminology/` | 200 | None |
| User list | `/manage/users/` | 200 | None |
| Metric library | `/manage/metrics/` | 200 | None |
| Programs list | `/programs/` | 200 | None |
| Event types | `/manage/event-types/` | 200 | None |
| Note templates | `/manage/note-templates/` | 200 | None |
| Custom fields | `/participants/admin/fields/` | 200 | None |
| Registration links | `/manage/registration/` | 200 | None |
| Audit log | `/manage/audit/` | 200 | None |

### Front Desk (FR)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page (FR) | `/` | 200 | None |
| Client detail (FR) | `/participants/1/` | 200 | None |
| Programs list (FR) | `/programs/` | 200 | None |
| Home page | `/` | 200 | None |
| Client list | `/participants/` | 200 | None |
| Client detail | `/participants/1/` | 200 | None |
| Programs list | `/programs/` | 200 | None |

### Front Desk

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page | `/` | 200 | None |
| Client list | `/participants/` | 200 | None |
| Search for client | `/participants/search/?q=Jane` | 200 | None |
| Client detail | `/participants/1/` | 200 | None |
| Custom fields display | `/participants/1/custom-fields/display/` | 200 | None |
| Custom fields edit | `/participants/1/custom-fields/edit/` | 200 | None |
| Consent display | `/participants/1/consent/display/` | 200 | None |
| Create client form | `/participants/create/` | 200 | None |
| Notes list (403) | `/notes/client/1/` | 301 | 1 issue(s) |
| Plan section create (403) | `/plans/client/1/sections/create/` | 301 | 1 issue(s) |
| Programs list | `/programs/` | 200 | None |
| Search for unknown client | `/participants/search/?q=Maria` | 200 | None |
| Create client form | `/participants/create/` | 200 | None |

### Program Manager

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page | `/` | 200 | None |
| Client list | `/participants/` | 200 | None |
| Client detail | `/participants/1/` | 200 | None |
| Notes timeline | `/notes/client/1/` | 301 | 1 issue(s) |
| Quick note form | `/notes/client/1/quick/` | 301 | 1 issue(s) |
| Full note form | `/notes/client/1/new/` | 301 | 1 issue(s) |
| Plan view (read-only) | `/plans/client/1/` | 301 | 1 issue(s) |
| Section create form (403) | `/plans/client/1/sections/create/` | 301 | 1 issue(s) |
| Target create form (403) | `/plans/sections/1/targets/create/` | 403 | None |
| Target metrics (403) | `/plans/targets/1/metrics/` | 403 | None |
| Section status (403) | `/plans/sections/1/status/` | 403 | None |
| Target status (403) | `/plans/targets/1/status/` | 403 | None |
| Target history | `/plans/targets/1/history/` | 200 | None |
| Metrics export form | `/reports/export/` | 200 | None |
| Funder report form | `/reports/funder-report/` | 200 | None |
| Events tab | `/events/client/1/` | 301 | 1 issue(s) |
| Event create form (403) | `/events/client/1/create/` | 301 | 1 issue(s) |
| Client analysis | `/reports/client/1/analysis/` | 301 | 1 issue(s) |
| Review new client | `/participants/3/` | 200 | None |
| Plan view (empty for new client) | `/plans/client/3/` | 301 | 1 issue(s) |
| Create plan section (403) | `/plans/client/3/sections/create/` | 301 | 1 issue(s) |

### Executive

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Executive dashboard | `/participants/executive/` | 200 | None |
| Client list redirect | `/participants/` | 200 | None |
| Client detail redirect | `/participants/1/` | 200 | None |
| Programs list | `/programs/` | 200 | None |
| Notes redirect | `/notes/client/1/` | 200 | None |

### Non-admin spot check

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin settings (403) | `/admin/settings/` | 403 | None |
| User list (403) | `/manage/users/` | 403 | None |

### Admin+PM

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Client detail | `/participants/1/` | 200 | None |
| Notes timeline | `/notes/client/1/` | 301 | 1 issue(s) |
| Plan view | `/plans/client/1/` | 301 | 1 issue(s) |
| Admin settings | `/admin/settings/` | 200 | None |
| User list | `/manage/users/` | 200 | None |

### Admin (no program)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin blocked from client detail (403) | `/participants/1/` | 403 | None |

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
| Admin | View metric library | `/manage/metrics/` | 200 | None |
| Admin | Open create metric form | `/manage/metrics/create/` | 200 | None |
| Admin | Create metric | `/manage/metrics/create/` | 200 | None |
| Admin | Open edit metric form | `/manage/metrics/2/edit/` | 200 | None |
| Admin | Edit metric saved | `/manage/metrics/2/edit/` | 200 | None |
| Admin | Toggle metric | `/manage/metrics/2/toggle/` | 200 | None |

### Plan Templates

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View plan template list | `/manage/templates/` | 200 | None |
| Admin | Open create template form | `/manage/templates/create/` | 200 | None |
| Admin | Create template | `/manage/templates/create/` | 200 | None |
| Admin | View template detail | `/manage/templates/1/` | 200 | None |
| Admin | Open add section form | `/manage/templates/1/sections/create/` | 200 | None |
| Admin | Create section | `/manage/templates/1/sections/create/` | 200 | None |
| Admin | Open add target form | `/manage/templates/sections/1/targets/create/` | 200 | None |
| Admin | Create target | `/manage/templates/sections/1/targets/create/` | 200 | None |
| Admin | Open edit template form | `/manage/templates/1/edit/` | 200 | None |
| Admin | Edit template saved | `/manage/templates/1/edit/` | 200 | None |

### Note Templates

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View note template list | `/manage/note-templates/` | 200 | None |
| Admin | Open create note template form | `/manage/note-templates/create/` | 200 | None |
| Admin | Create note template with section | `/manage/note-templates/create/` | 200 | None |
| Admin | Open edit note template form | `/manage/note-templates/2/edit/` | 200 | None |

### Event Types

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View event types list | `/manage/event-types/` | 200 | None |
| Admin | Open create event type form | `/manage/event-types/create/` | 200 | None |
| Admin | Create event type | `/manage/event-types/create/` | 200 | None |
| Admin | Open edit event type form | `/manage/event-types/2/edit/` | 200 | None |
| Admin | Edit event type saved | `/manage/event-types/2/edit/` | 200 | None |
| Admin | List shows multiple event types | `/manage/event-types/` | 200 | None |

### Custom Client Fields

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View custom field admin | `/participants/admin/fields/` | 200 | None |
| Admin | Open create field group form | `/participants/admin/fields/groups/create/` | 200 | None |
| Admin | Create field group | `/participants/admin/fields/groups/create/` | 200 | None |
| Admin | Open create field definition form | `/participants/admin/fields/create/` | 200 | None |
| Admin | Create dropdown field | `/participants/admin/fields/create/` | 200 | None |
| Admin | Create sensitive text field | `/participants/admin/fields/create/` | 200 | None |
| Admin | Fields visible in admin | `/participants/admin/fields/` | 200 | None |
| Admin | Open edit field definition form | `/participants/admin/fields/3/edit/` | 200 | None |

### User Management

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View user list | `/manage/users/` | 200 | None |
| Admin | Open create user form | `/manage/users/new/` | 200 | None |
| Admin | Create user | `/manage/users/new/` | 200 | None |
| Admin | Open edit user form | `/manage/users/7/edit/` | 200 | None |
| Admin | Edit user saved | `/manage/users/7/edit/` | 200 | None |

### Invite System

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View invite list | `/manage/users/invites/` | 200 | None |
| Admin | Open create invite form | `/manage/users/invites/new/` | 200 | None |
| Admin | Create invite link | `/manage/users/invites/new/` | 200 | None |

### Registration Links

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View registration links | `/manage/registration/` | 200 | None |
| Admin | Open create registration link form | `/manage/registration/create/` | 200 | None |
| Admin | Create registration link | `/manage/registration/create/` | 200 | None |
| Admin | View pending submissions | `/manage/submissions/` | 200 | None |

### Audit Logs

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View audit log | `/manage/audit/` | 200 | None |
| Admin | Filter audit log by date | `/manage/audit/?date_from=2020-01-01&date_to=2030-12-31` | 200 | None |
| Admin | Diagnose charts tool | `/admin/settings/diagnose-charts/` | 200 | None |

### Full Agency Setup

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | 1. Start at admin dashboard | `/admin/settings/` | 200 | None |
| Admin | 2. Enable events feature | `/admin/settings/features/` | 200 | None |
| Admin | 3. Create program | `/programs/create/` | 200 | None |
| Admin | 4. Create metric | `/manage/metrics/create/` | 200 | None |
| Admin | 5. Create event type | `/manage/event-types/create/` | 200 | None |
| Admin | 6. Create staff user | `/manage/users/new/` | 200 | None |
| Admin | 7. Assign staff to program | `/programs/3/roles/add/` | 200 | None |
| Admin | 8. Verify staff visible on program | `/programs/3/` | 200 | None |

### Admin in French

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin (FR) | Admin dashboard | `/admin/settings/` | 200 | None |
| Admin (FR) | Features | `/admin/settings/features/` | 200 | None |
| Admin (FR) | Instance settings | `/admin/settings/instance/` | 200 | None |
| Admin (FR) | Terminology | `/admin/settings/terminology/` | 200 | None |
| Admin (FR) | User list | `/manage/users/` | 200 | None |
| Admin (FR) | Metric library | `/manage/metrics/` | 200 | None |
| Admin (FR) | Programs list | `/programs/` | 200 | None |
| Admin (FR) | Event types | `/manage/event-types/` | 200 | None |
| Admin (FR) | Note templates | `/manage/note-templates/` | 200 | None |
| Admin (FR) | Custom fields | `/participants/admin/fields/` | 200 | None |
| Admin (FR) | Registration links | `/manage/registration/` | 200 | None |
| Admin (FR) | Audit log | `/manage/audit/` | 200 | None |

### Cross-Program Isolation

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin (no program) | Admin blocked from Jane (403) | `/participants/1/` | 403 | None |
| Direct Service | Client list (Housing only) | `/participants/` | 200 | None |
| Direct Service | Direct access to Bob (403) | `/participants/2/` | 403 | None |
| Direct Service | HTMX partial for Bob (403) | `/participants/2/custom-fields/display/` | 403 | None |
| Direct Service | Jane's profile (own program) | `/participants/1/` | 200 | None |
| Direct Service | Target history blocked | `/plans/targets/2/history/` | 403 | None |
| Direct Service | Search for Bob (no results expected) | `/participants/search/?q=Bob` | 200 | None |

### Morning Intake Flow

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Front Desk | Search for Maria (not found) | `/participants/search/?q=Maria` | 200 | None |
| Front Desk | Dana opens create form | `/participants/create/` | 200 | None |
| Direct Service | View Maria's profile | `/participants/3/` | 200 | None |
| Direct Service | Write intake note | `/notes/client/3/quick/` | 200 | None |
| Direct Service | Check notes timeline | `/notes/client/3/` | 301 | None |
| Program Manager | Review Maria's profile | `/participants/3/` | 200 | None |
| Program Manager | View empty plan | `/plans/client/3/` | 301 | None |
| Program Manager | Create plan section | `/plans/client/3/sections/create/` | 301 | None |

### Full French Workday

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Front Desk (FR) | Home page | `/` | 200 | None |
| Front Desk (FR) | Client list | `/participants/` | 200 | None |
| Front Desk (FR) | Client detail | `/participants/1/` | 200 | None |
| Front Desk (FR) | Programs list | `/programs/` | 200 | None |

### Client Note Search

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Direct Service | Client list search by note content | `/participants/?q=seemed+well` | 200 | None |
| Direct Service | Dedicated search by note content | `/participants/search/?q=seemed+well` | 200 | None |
| Direct Service | Note search isolation (no cross-program leak) | `/participants/search/?q=vocational` | 200 | None |

### Group Permission Leakage

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Direct Service | Group detail blocked | `/groups/2/` | 403 | None |
| Direct Service | Membership remove blocked | `/groups/member/1/remove/` | 403 | None |
| Direct Service | Milestone create blocked | `/groups/2/milestone/` | 403 | None |
| Direct Service | Milestone edit blocked | `/groups/milestone/1/edit/` | 403 | None |
| Direct Service | Outcome create blocked | `/groups/2/outcome/` | 403 | None |
| Direct Service | Own program group accessible | `/groups/1/` | 200 | None |
| Direct Service | Session log blocked | `/groups/2/session/` | 403 | None |
| Direct Service | Target history blocked | `/plans/targets/2/history/` | 403 | None |

## Recommendations

### Immediate (Critical)

1. Fix: Expected 403, got 301 on `/notes/client/1/`
1. Fix: Expected 403, got 301 on `/plans/client/1/sections/create/`
1. Fix: Expected 200, got 301 on `/notes/client/1/quick/`
1. Fix: Expected 200, got 301 on `/notes/client/1/new/`
1. Fix: Expected 200, got 301 on `/notes/client/1/`
1. Fix: Expected 200, got 301 on `/plans/client/1/`
1. Fix: Expected 200, got 301 on `/plans/client/1/sections/create/`
1. Fix: Expected 200, got 301 on `/events/client/1/`
1. Fix: Expected 200, got 301 on `/events/client/1/create/`
1. Fix: Expected 200, got 301 on `/events/client/1/alerts/create/`
1. Fix: Expected 200, got 301 on `/reports/client/1/analysis/`
1. Fix: Expected 200, got 301 on `/notes/client/1/`
1. Fix: Expected 200, got 301 on `/notes/client/1/quick/`
1. Fix: Expected 200, got 301 on `/notes/client/1/new/`
1. Fix: Expected 200, got 301 on `/plans/client/1/`
1. Fix: Expected 403, got 301 on `/plans/client/1/sections/create/`
1. Fix: Expected 200, got 301 on `/events/client/1/`
1. Fix: Expected 403, got 301 on `/events/client/1/create/`
1. Fix: Expected 200, got 301 on `/reports/client/1/analysis/`
1. Fix: Expected 200, got 301 on `/notes/client/1/`
1. Fix: Expected 200, got 301 on `/plans/client/1/`
1. Fix: Expected 200, got 301 on `/notes/client/3/`
1. Fix: Expected 200, got 301 on `/plans/client/3/`
1. Fix: Expected 403, got 301 on `/plans/client/3/sections/create/`

### Short-term (Warnings)

- Expected form errors but none found (no .errorlist, .badge-danger, or .error elements) (`/notes/client/1/quick/`)
- Page has no <title> or title is empty (`/notes/client/1/quick/`)
- No <main> landmark element found (`/notes/client/1/quick/`)
- No <nav> element found on full page (`/notes/client/1/quick/`)
- No <html> element found (`/notes/client/1/quick/`)
- Expected redirect to contain '/notes/client/1/', got '/notes/participant/1/quick/' (`/notes/client/1/quick/`)
- Expected redirect to contain '/notes/client/3/', got '/notes/participant/3/quick/' (`/notes/client/3/quick/`)

---

_Generated by `tests/ux_walkthrough/` — automated UX walkthrough_
