# KoNote2 UX Walkthrough Report

**Generated:** 2026-02-09 10:38:45  
**Command:** `pytest tests/ux_walkthrough/ -v`

## Summary

| Metric | This Run | Previous |
|--------|----------|----------|
| Pages visited | 326 | 326 (same) |
| Critical issues | 207 | 205 (up 2) |
| Warnings | 14 | 14 (same) |
| Info items | 20 | 20 (same) |

## Critical Issues

- **[Admin] Home page (find admin link)** `/`
  Server error (500) — view crashed

- **[Admin] Admin settings dashboard** `/admin/settings/`
  Server error (500) — view crashed

- **[Direct Service] Admin dashboard (403)** `/admin/settings/`
  Expected 403, got 500

- **[Admin] Features page** `/admin/settings/features/`
  Server error (500) — view crashed

- **[Admin] Enable custom fields** `/admin/settings/features/`
  Server error (500) after POST

- **[Admin] Enable events** `/admin/settings/features/`
  Server error (500) after POST

- **[Admin] Disable alerts** `/admin/settings/features/`
  Server error (500) after POST

- **[Admin] Instance settings form** `/admin/settings/instance/`
  Server error (500) — view crashed

- **[Admin] Save instance settings** `/admin/settings/instance/`
  Server error (500) after POST

- **[Admin] Form validation — empty program name** `/programs/create/`
  POST form missing CSRF token (action: /i18n/switch/)

- **[Admin] Programs list** `/programs/`
  Server error (500) — view crashed

- **[Admin] Create program form** `/programs/create/`
  Server error (500) — view crashed

- **[Admin] Submit new program** `/programs/create/`
  Server error (500) after POST

- **[Admin] Program detail** `/programs/3/`
  Server error (500) — view crashed

- **[Admin] Edit program form** `/programs/3/edit/`
  Server error (500) — view crashed

- **[Admin] Update program** `/programs/3/edit/`
  Server error (500) after POST

- **[Admin] Metric library** `/plans/admin/metrics/`
  Server error (500) — view crashed

- **[Admin] Create metric form** `/plans/admin/metrics/create/`
  Server error (500) — view crashed

- **[Admin] Submit new metric** `/plans/admin/metrics/create/`
  Server error (500) after POST

- **[Admin] Edit metric form** `/plans/admin/metrics/2/edit/`
  Server error (500) — view crashed

- **[Admin] Update metric** `/plans/admin/metrics/2/edit/`
  Server error (500) after POST

- **[Admin] Plan template list** `/admin/templates/`
  Server error (500) — view crashed

- **[Admin] Create template form** `/admin/templates/create/`
  Server error (500) — view crashed

- **[Admin] Submit new template** `/admin/templates/create/`
  Server error (500) after POST

- **[Admin] Template detail** `/admin/templates/1/`
  Server error (500) — view crashed

- **[Admin] Add section form** `/admin/templates/1/sections/create/`
  Server error (500) — view crashed

- **[Admin] Submit new section** `/admin/templates/1/sections/create/`
  Server error (500) after POST

- **[Admin] Add target form** `/admin/templates/sections/1/targets/create/`
  Server error (500) — view crashed

- **[Admin] Submit new target** `/admin/templates/sections/1/targets/create/`
  Server error (500) after POST

- **[Admin] Edit template form** `/admin/templates/1/edit/`
  Server error (500) — view crashed

- **[Admin] Update template** `/admin/templates/1/edit/`
  Server error (500) after POST

- **[Admin] Note template list** `/admin/settings/note-templates/`
  Server error (500) — view crashed

- **[Admin] Create note template form** `/admin/settings/note-templates/create/`
  Server error (500) — view crashed

- **[Admin] Submit new note template** `/admin/settings/note-templates/create/`
  Server error (500) after POST

- **[Admin] Edit note template form** `/admin/settings/note-templates/2/edit/`
  Server error (500) — view crashed

- **[Admin] Event types list** `/events/admin/types/`
  Server error (500) — view crashed

- **[Admin] Create event type form** `/events/admin/types/create/`
  Server error (500) — view crashed

- **[Admin] Submit new event type** `/events/admin/types/create/`
  Server error (500) after POST

- **[Admin] Edit event type form** `/events/admin/types/2/edit/`
  Server error (500) — view crashed

- **[Admin] Update event type** `/events/admin/types/2/edit/`
  Server error (500) after POST

- **[Admin] Event types list (multiple)** `/events/admin/types/`
  Server error (500) — view crashed

- **[Admin] Custom field admin** `/clients/admin/fields/`
  Server error (500) — view crashed

- **[Admin] Create field group form** `/clients/admin/fields/groups/create/`
  Server error (500) — view crashed

- **[Admin] Submit new field group** `/clients/admin/fields/groups/create/`
  Server error (500) after POST

- **[Admin] Create field definition form** `/clients/admin/fields/create/`
  Server error (500) — view crashed

- **[Admin] Submit dropdown field** `/clients/admin/fields/create/`
  Server error (500) after POST

- **[Admin] Submit text field** `/clients/admin/fields/create/`
  Server error (500) after POST

- **[Admin] Custom field admin (populated)** `/clients/admin/fields/`
  Server error (500) — view crashed

- **[Admin] Edit field definition form** `/clients/admin/fields/3/edit/`
  Server error (500) — view crashed

- **[Admin] Form validation — password mismatch** `/admin/users/new/`
  POST form missing CSRF token (action: /i18n/switch/)

- **[Admin] User list** `/admin/users/`
  Server error (500) — view crashed

- **[Admin] Create user form** `/admin/users/new/`
  Server error (500) — view crashed

- **[Admin] Submit new user** `/admin/users/new/`
  Server error (500) after POST

- **[Admin] Edit user form** `/admin/users/7/edit/`
  Server error (500) — view crashed

- **[Admin] Update user** `/admin/users/7/edit/`
  Server error (500) after POST

- **[Admin] Invite list** `/auth/invites/`
  Server error (500) — view crashed

- **[Admin] Create invite form** `/auth/invites/new/`
  Server error (500) — view crashed

- **[Admin] Submit new invite** `/auth/invites/new/`
  Server error (500) after POST

- **[Admin] Registration links list** `/admin/registration/`
  Server error (500) — view crashed

- **[Admin] Create registration link form** `/admin/registration/create/`
  Server error (500) — view crashed

- **[Admin] Submit new registration link** `/admin/registration/create/`
  Server error (500) after POST

- **[Admin] Pending submissions** `/admin/submissions/`
  Server error (500) — view crashed

- **[Admin] Audit log list** `/admin/audit/`
  Server error (500) — view crashed

- **[Admin] Audit log filtered** `/admin/audit/?date_from=2020-01-01&date_to=2030-12-31`
  Server error (500) — view crashed

- **[Admin] Diagnose charts** `/admin/settings/diagnose-charts/`
  Server error (500) — view crashed

- **[Admin] Start at dashboard** `/admin/settings/`
  Server error (500) — view crashed

- **[Admin] Enable events feature** `/admin/settings/features/`
  Server error (500) after POST

- **[Admin] Create first program** `/programs/create/`
  Server error (500) after POST

- **[Admin] Create first metric** `/plans/admin/metrics/create/`
  Server error (500) after POST

- **[Admin] Create first event type** `/events/admin/types/create/`
  Server error (500) after POST

- **[Admin] Create first staff user** `/admin/users/new/`
  Server error (500) after POST

- **[Admin] Program with staff** `/programs/3/`
  Server error (500) — view crashed

- **[Admin (FR)] Admin dashboard** `/admin/settings/`
  Server error (500) — view crashed

- **[Admin (FR)] Features** `/admin/settings/features/`
  Server error (500) — view crashed

- **[Admin (FR)] Instance settings** `/admin/settings/instance/`
  Server error (500) — view crashed

- **[Admin (FR)] Terminology** `/admin/settings/terminology/`
  Server error (500) — view crashed

- **[Admin (FR)] User list** `/admin/users/`
  Server error (500) — view crashed

- **[Admin (FR)] Metric library** `/plans/admin/metrics/`
  Server error (500) — view crashed

- **[Admin (FR)] Programs list** `/programs/`
  Server error (500) — view crashed

- **[Admin (FR)] Event types** `/events/admin/types/`
  Server error (500) — view crashed

- **[Admin (FR)] Note templates** `/admin/settings/note-templates/`
  Server error (500) — view crashed

- **[Admin (FR)] Custom fields** `/clients/admin/fields/`
  Server error (500) — view crashed

- **[Admin (FR)] Registration links** `/admin/registration/`
  Server error (500) — view crashed

- **[Admin (FR)] Audit log** `/admin/audit/`
  Server error (500) — view crashed

- **[Front Desk (FR)] Home page (FR)** `/`
  Server error (500) — view crashed

- **[Front Desk (FR)] Client detail (FR)** `/clients/1/`
  Server error (500) — view crashed

- **[Front Desk (FR)] Programs list (FR)** `/programs/`
  Server error (500) — view crashed

- **[Front Desk] Home page** `/`
  Server error (500) — view crashed

- **[Front Desk] Client list** `/clients/`
  Server error (500) — view crashed

- **[Front Desk] Search for client** `/clients/search/?q=Jane`
  Server error (500) — view crashed

- **[Front Desk] Client detail** `/clients/1/`
  Server error (500) — view crashed

- **[Front Desk] Create client (403)** `/clients/create/`
  Expected 403, got 500

- **[Front Desk] Notes list (403)** `/notes/client/1/`
  Expected 403, got 500

- **[Front Desk] Plan section create (403)** `/plans/client/1/sections/create/`
  Expected 403, got 500

- **[Front Desk] Programs list** `/programs/`
  Server error (500) — view crashed

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  POST form missing CSRF token (action: /i18n/switch/)

- **[Direct Service] Home page** `/`
  Server error (500) — view crashed

- **[Direct Service] Client list** `/clients/`
  Server error (500) — view crashed

- **[Direct Service] Create client form** `/clients/create/`
  Server error (500) — view crashed

- **[Direct Service] Create client submit** `/clients/create/`
  Server error (500) after POST

- **[Direct Service] Client detail** `/clients/1/`
  Server error (500) — view crashed

- **[Direct Service] Edit client form** `/clients/1/edit/`
  Server error (500) — view crashed

- **[Direct Service] Edit client submit** `/clients/1/edit/`
  Server error (500) after POST

- **[Direct Service] Consent submit** `/clients/1/consent/`
  Server error (500) after POST

- **[Direct Service] Quick note form** `/notes/client/1/quick/`
  Server error (500) — view crashed

- **[Direct Service] Quick note submit** `/notes/client/1/quick/`
  Server error (500) after POST

- **[Direct Service] Full note form** `/notes/client/1/new/`
  Server error (500) — view crashed

- **[Direct Service] Notes timeline** `/notes/client/1/`
  Server error (500) — view crashed

- **[Direct Service] Plan view (read-only)** `/plans/client/1/`
  Server error (500) — view crashed

- **[Direct Service] Section create (403)** `/plans/client/1/sections/create/`
  Expected 403, got 500

- **[Direct Service] Events tab** `/events/client/1/`
  Server error (500) — view crashed

- **[Direct Service] Event create form** `/events/client/1/create/`
  Server error (500) — view crashed

- **[Direct Service] Alert create form** `/events/client/1/alerts/create/`
  Server error (500) — view crashed

- **[Direct Service] Client analysis** `/reports/client/1/analysis/`
  Server error (500) — view crashed

- **[Direct Service] Programs list** `/programs/`
  Server error (500) — view crashed

- **[Program Manager] Home page** `/`
  Server error (500) — view crashed

- **[Program Manager] Client list** `/clients/`
  Server error (500) — view crashed

- **[Program Manager] Client detail** `/clients/1/`
  Server error (500) — view crashed

- **[Program Manager] Notes timeline** `/notes/client/1/`
  Server error (500) — view crashed

- **[Program Manager] Quick note form** `/notes/client/1/quick/`
  Server error (500) — view crashed

- **[Program Manager] Full note form** `/notes/client/1/new/`
  Server error (500) — view crashed

- **[Program Manager] Plan view (editable)** `/plans/client/1/`
  Server error (500) — view crashed

- **[Program Manager] Section create form** `/plans/client/1/sections/create/`
  Server error (500) — view crashed

- **[Program Manager] Section create submit** `/plans/client/1/sections/create/`
  Server error (500) after POST

- **[Program Manager] Target create form** `/plans/sections/1/targets/create/`
  Server error (500) — view crashed

- **[Program Manager] Target create submit** `/plans/sections/1/targets/create/`
  Server error (500) after POST

- **[Program Manager] Target metrics** `/plans/targets/1/metrics/`
  Server error (500) on HTMX partial

- **[Program Manager] Section status** `/plans/sections/1/status/`
  Server error (500) on HTMX partial

- **[Program Manager] Target status** `/plans/targets/1/status/`
  Server error (500) on HTMX partial

- **[Program Manager] Target history** `/plans/targets/1/history/`
  Server error (500) on HTMX partial

- **[Program Manager] Metrics export form** `/reports/export/`
  Server error (500) — view crashed

- **[Program Manager] CMT export form** `/reports/cmt-export/`
  Server error (500) — view crashed

- **[Program Manager] Events tab** `/events/client/1/`
  Server error (500) — view crashed

- **[Program Manager] Event create form** `/events/client/1/create/`
  Server error (500) — view crashed

- **[Program Manager] Client analysis** `/reports/client/1/analysis/`
  Server error (500) — view crashed

- **[Executive] Executive dashboard** `/clients/executive/`
  Server error (500) — view crashed

- **[Executive] Client list redirect** `/clients/`
  Server error (500) on redirect follow

- **[Executive] Client detail redirect** `/clients/1/`
  Server error (500) on redirect follow

- **[Executive] Programs list** `/programs/`
  Server error (500) — view crashed

- **[Executive] Notes redirect** `/notes/client/1/`
  Server error (500) on redirect follow

- **[Admin] Client detail without program role (403)** `/clients/1/`
  Expected 403, got 500

- **[Non-admin spot check] Admin settings (403)** `/admin/settings/`
  Expected 403, got 500

- **[Non-admin spot check] User list (403)** `/admin/users/`
  Expected 403, got 500

- **[Admin] Admin settings dashboard** `/admin/settings/`
  Server error (500) — view crashed

- **[Admin] Terminology settings** `/admin/settings/terminology/`
  Server error (500) — view crashed

- **[Admin] Feature toggles** `/admin/settings/features/`
  Server error (500) — view crashed

- **[Admin] Instance settings** `/admin/settings/instance/`
  Server error (500) — view crashed

- **[Admin] Metrics library** `/plans/admin/metrics/`
  Server error (500) — view crashed

- **[Admin] Create metric form** `/plans/admin/metrics/create/`
  Server error (500) — view crashed

- **[Admin] Programs list** `/programs/`
  Server error (500) — view crashed

- **[Admin] Create program form** `/programs/create/`
  Server error (500) — view crashed

- **[Admin] Program detail** `/programs/1/`
  Server error (500) — view crashed

- **[Admin] User list** `/admin/users/`
  Server error (500) — view crashed

- **[Admin] Create user form** `/admin/users/new/`
  Server error (500) — view crashed

- **[Admin] Invite list** `/auth/invites/`
  Server error (500) — view crashed

- **[Admin] Create invite form** `/auth/invites/new/`
  Server error (500) — view crashed

- **[Admin] Audit log** `/admin/audit/`
  Server error (500) — view crashed

- **[Admin] Registration links** `/admin/registration/`
  Server error (500) — view crashed

- **[Admin] Create registration link** `/admin/registration/create/`
  Server error (500) — view crashed

- **[Admin] Custom field admin** `/clients/admin/fields/`
  Server error (500) — view crashed

- **[Admin] Create field group** `/clients/admin/fields/groups/create/`
  Server error (500) — view crashed

- **[Admin] Create field definition** `/clients/admin/fields/create/`
  Server error (500) — view crashed

- **[Admin] Event types list** `/events/admin/types/`
  Server error (500) — view crashed

- **[Admin] Create event type** `/events/admin/types/create/`
  Server error (500) — view crashed

- **[Admin] Note templates** `/admin/settings/note-templates/`
  Server error (500) — view crashed

- **[Admin] Client data export form** `/reports/client-data-export/`
  Server error (500) — view crashed

- **[Admin] Export links management** `/reports/export-links/`
  Server error (500) — view crashed

- **[Admin] Diagnose charts** `/admin/settings/diagnose-charts/`
  Server error (500) — view crashed

- **[Admin] Pending submissions** `/admin/submissions/`
  Server error (500) — view crashed

- **[Admin+PM] Client detail** `/clients/1/`
  Server error (500) — view crashed

- **[Admin+PM] Notes timeline** `/notes/client/1/`
  Server error (500) — view crashed

- **[Admin+PM] Plan view** `/plans/client/1/`
  Server error (500) — view crashed

- **[Admin+PM] Admin settings** `/admin/settings/`
  Server error (500) — view crashed

- **[Admin+PM] User list** `/admin/users/`
  Server error (500) — view crashed

- **[Admin (no program)] Admin blocked from client detail (403)** `/clients/1/`
  Expected 403, got 500

- **[Direct Service] Client list (Housing only)** `/clients/`
  Server error (500) — view crashed

- **[Direct Service] Direct access to Bob's profile (403)** `/clients/2/`
  Expected 403, got 500

- **[Direct Service] HTMX partial for Bob's custom fields** `/clients/2/custom-fields/display/`
  Expected 403, got 500

- **[Direct Service] Access Jane's profile (own program)** `/clients/1/`
  Server error (500) — view crashed

- **[Direct Service] Jane's profile (own program)** `/clients/1/`
  Expected 200, got 500

- **[Direct Service] Target history for Bob (403)** `/plans/targets/2/history/`
  Expected 403, got 500

- **[Direct Service] Search for Bob (should find no results)** `/clients/search/?q=Bob`
  Server error (500) — view crashed

- **[Front Desk] Search for unknown client** `/clients/search/?q=Maria`
  Server error (500) — view crashed

- **[Front Desk] Can't create client (403)** `/clients/create/`
  Expected 403, got 500

- **[Direct Service] Client create form** `/clients/create/`
  Server error (500) — view crashed

- **[Direct Service] View new client profile** `/clients/3/`
  Server error (500) — view crashed

- **[Direct Service] Document intake session** `/notes/client/3/quick/`
  Server error (500) after POST

- **[Direct Service] Notes timeline after intake** `/notes/client/3/`
  Server error (500) — view crashed

- **[Program Manager] Review new client** `/clients/3/`
  Server error (500) — view crashed

- **[Program Manager] Plan view (empty for new client)** `/plans/client/3/`
  Server error (500) — view crashed

- **[Program Manager] Create plan section** `/plans/client/3/sections/create/`
  Server error (500) after POST

- **[Front Desk (FR)] Home page** `/`
  Server error (500) — view crashed

- **[Front Desk (FR)] Client list** `/clients/`
  Server error (500) — view crashed

- **[Front Desk (FR)] Client detail** `/clients/1/`
  Server error (500) — view crashed

- **[Front Desk (FR)] Programs list** `/programs/`
  Server error (500) — view crashed

- **[Direct Service] Search client list by note text** `/clients/?q=seemed+well`
  Server error (500) — view crashed

- **[Direct Service] Dedicated search by note text** `/clients/search/?q=seemed+well`
  Server error (500) — view crashed

- **[Direct Service] Search for other program's note content** `/clients/search/?q=vocational`
  Server error (500) — view crashed

- **[Direct Service] Group detail (other program, 403)** `/groups/2/`
  Expected 403, got 500

- **[Direct Service] Membership remove (other program)** `/groups/member/1/remove/`
  Expected 403, got 500

- **[Direct Service] Milestone create (other program)** `/groups/2/milestone/`
  Expected 403, got 500

- **[Direct Service] Milestone edit (other program, 403)** `/groups/milestone/1/edit/`
  Expected 403, got 500

- **[Direct Service] Outcome create (other program)** `/groups/2/outcome/`
  Expected 403, got 500

- **[Direct Service] Own program group (200)** `/groups/1/`
  Server error (500) — view crashed

- **[Direct Service] Own program group** `/groups/1/`
  Expected 200, got 500

- **[Direct Service] Session log (other program, 403)** `/groups/2/session/`
  Expected 403, got 500

- **[Direct Service] Target history (other program, 403)** `/plans/targets/2/history/`
  Expected 403, got 500

## Warning Issues

- **[Admin] Form validation — empty program name** `/programs/create/`
  Expected form errors but none found (no .errorlist elements)

- **[Admin] Form validation — empty program name** `/programs/create/`
  <html> element missing lang attribute

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

- **[Admin] Form validation — password mismatch** `/admin/users/new/`
  <html> element missing lang attribute

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  Page has no <title> or title is empty

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No <main> landmark element found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No <nav> element found on full page

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No <html> element found

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  Expected form errors but none found (no .errorlist elements)

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  <html> element missing lang attribute

## Info Issues

- **[Admin] Form validation — empty program name** `/programs/create/`
  No skip navigation link found

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No headings found on page

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No <meta name="viewport"> tag found

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No skip navigation link found

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No success message found after form submission

- **[Admin] Form validation — password mismatch** `/admin/users/new/`
  No skip navigation link found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No headings found on page

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No <meta name="viewport"> tag found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No skip navigation link found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No success message found after form submission

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  No skip navigation link found

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

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "KoNote2" is 77x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Sign In" is 61x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/`
  [mobile] Client list: Touch target too small — <a> "KoNote2" is 77x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/`
  [mobile] Client list: Touch target too small — <a> "Sign In" is 61x38px (min 44x44)

## Known Limitations

- Colour contrast, focus management, and responsive layout are tested via Playwright browser tests
- Colour contrast checks depend on CDN (axe-core) — require internet

## Per-Role Walkthrough Results

### Admin

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page (find admin link) | `/` | 500 | 1 issue(s) |
| Admin settings dashboard | `/admin/settings/` | 500 | 1 issue(s) |
| Features page | `/admin/settings/features/` | 500 | 1 issue(s) |
| Enable custom fields | `/admin/settings/features/` | 500 | 1 issue(s) |
| Enable events | `/admin/settings/features/` | 500 | 1 issue(s) |
| Disable alerts | `/admin/settings/features/` | 500 | 1 issue(s) |
| Instance settings form | `/admin/settings/instance/` | 500 | 1 issue(s) |
| Save instance settings | `/admin/settings/instance/` | 500 | 1 issue(s) |
| Program form validation | `/programs/create/` | 500 | 4 issue(s) |
| Programs list | `/programs/` | 500 | 1 issue(s) |
| Create program form | `/programs/create/` | 500 | 1 issue(s) |
| Submit new program | `/programs/create/` | 500 | 1 issue(s) |
| Program detail | `/programs/3/` | 500 | 1 issue(s) |
| Edit program form | `/programs/3/edit/` | 500 | 1 issue(s) |
| Update program | `/programs/3/edit/` | 500 | 1 issue(s) |
| Assign staff to program | `/programs/3/roles/add/` | 200 | 8 issue(s) |
| Metric library | `/plans/admin/metrics/` | 500 | 1 issue(s) |
| Create metric form | `/plans/admin/metrics/create/` | 500 | 1 issue(s) |
| Submit new metric | `/plans/admin/metrics/create/` | 500 | 1 issue(s) |
| Edit metric form | `/plans/admin/metrics/2/edit/` | 500 | 1 issue(s) |
| Update metric | `/plans/admin/metrics/2/edit/` | 500 | 1 issue(s) |
| Toggle metric off | `/plans/admin/metrics/2/toggle/` | 200 | None |
| Plan template list | `/admin/templates/` | 500 | 1 issue(s) |
| Create template form | `/admin/templates/create/` | 500 | 1 issue(s) |
| Submit new template | `/admin/templates/create/` | 500 | 1 issue(s) |
| Template detail | `/admin/templates/1/` | 500 | 1 issue(s) |
| Add section form | `/admin/templates/1/sections/create/` | 500 | 1 issue(s) |
| Submit new section | `/admin/templates/1/sections/create/` | 500 | 1 issue(s) |
| Add target form | `/admin/templates/sections/1/targets/create/` | 500 | 1 issue(s) |
| Submit new target | `/admin/templates/sections/1/targets/create/` | 500 | 1 issue(s) |
| Edit template form | `/admin/templates/1/edit/` | 500 | 1 issue(s) |
| Update template | `/admin/templates/1/edit/` | 500 | 1 issue(s) |
| Note template list | `/admin/settings/note-templates/` | 500 | 1 issue(s) |
| Create note template form | `/admin/settings/note-templates/create/` | 500 | 1 issue(s) |
| Submit new note template | `/admin/settings/note-templates/create/` | 500 | 1 issue(s) |
| Edit note template form | `/admin/settings/note-templates/2/edit/` | 500 | 1 issue(s) |
| Event types list | `/events/admin/types/` | 500 | 1 issue(s) |
| Create event type form | `/events/admin/types/create/` | 500 | 1 issue(s) |
| Submit new event type | `/events/admin/types/create/` | 500 | 1 issue(s) |
| Edit event type form | `/events/admin/types/2/edit/` | 500 | 1 issue(s) |
| Update event type | `/events/admin/types/2/edit/` | 500 | 1 issue(s) |
| Event types list (multiple) | `/events/admin/types/` | 500 | 1 issue(s) |
| Custom field admin | `/clients/admin/fields/` | 500 | 1 issue(s) |
| Create field group form | `/clients/admin/fields/groups/create/` | 500 | 1 issue(s) |
| Submit new field group | `/clients/admin/fields/groups/create/` | 500 | 1 issue(s) |
| Create field definition form | `/clients/admin/fields/create/` | 500 | 1 issue(s) |
| Submit dropdown field | `/clients/admin/fields/create/` | 500 | 1 issue(s) |
| Submit text field | `/clients/admin/fields/create/` | 500 | 1 issue(s) |
| Custom field admin (populated) | `/clients/admin/fields/` | 500 | 1 issue(s) |
| Edit field definition form | `/clients/admin/fields/3/edit/` | 500 | 1 issue(s) |
| User form password mismatch | `/admin/users/new/` | 500 | 4 issue(s) |
| User list | `/admin/users/` | 500 | 1 issue(s) |
| Create user form | `/admin/users/new/` | 500 | 1 issue(s) |
| Submit new user | `/admin/users/new/` | 500 | 1 issue(s) |
| Edit user form | `/admin/users/7/edit/` | 500 | 1 issue(s) |
| Update user | `/admin/users/7/edit/` | 500 | 1 issue(s) |
| Invite list | `/auth/invites/` | 500 | 1 issue(s) |
| Create invite form | `/auth/invites/new/` | 500 | 1 issue(s) |
| Submit new invite | `/auth/invites/new/` | 500 | 1 issue(s) |
| Registration links list | `/admin/registration/` | 500 | 1 issue(s) |
| Create registration link form | `/admin/registration/create/` | 500 | 1 issue(s) |
| Submit new registration link | `/admin/registration/create/` | 500 | 1 issue(s) |
| Pending submissions | `/admin/submissions/` | 500 | 1 issue(s) |
| Audit log list | `/admin/audit/` | 500 | 1 issue(s) |
| Audit log filtered | `/admin/audit/?date_from=2020-01-01&date_to=2030-12-31` | 500 | 1 issue(s) |
| Diagnose charts | `/admin/settings/diagnose-charts/` | 500 | 1 issue(s) |
| Start at dashboard | `/admin/settings/` | 500 | 1 issue(s) |
| Enable events feature | `/admin/settings/features/` | 500 | 1 issue(s) |
| Create first program | `/programs/create/` | 500 | 1 issue(s) |
| Create first metric | `/plans/admin/metrics/create/` | 500 | 1 issue(s) |
| Create first event type | `/events/admin/types/create/` | 500 | 1 issue(s) |
| Create first staff user | `/admin/users/new/` | 500 | 1 issue(s) |
| Assign worker to program | `/programs/3/roles/add/` | 200 | 8 issue(s) |
| Program with staff | `/programs/3/` | 500 | 1 issue(s) |
| Client detail without program role (403) | `/clients/1/` | 500 | 1 issue(s) |
| Admin settings dashboard | `/admin/settings/` | 500 | 1 issue(s) |
| Terminology settings | `/admin/settings/terminology/` | 500 | 1 issue(s) |
| Feature toggles | `/admin/settings/features/` | 500 | 1 issue(s) |
| Instance settings | `/admin/settings/instance/` | 500 | 1 issue(s) |
| Metrics library | `/plans/admin/metrics/` | 500 | 1 issue(s) |
| Create metric form | `/plans/admin/metrics/create/` | 500 | 1 issue(s) |
| Programs list | `/programs/` | 500 | 1 issue(s) |
| Create program form | `/programs/create/` | 500 | 1 issue(s) |
| Program detail | `/programs/1/` | 500 | 1 issue(s) |
| User list | `/admin/users/` | 500 | 1 issue(s) |
| Create user form | `/admin/users/new/` | 500 | 1 issue(s) |
| Invite list | `/auth/invites/` | 500 | 1 issue(s) |
| Create invite form | `/auth/invites/new/` | 500 | 1 issue(s) |
| Audit log | `/admin/audit/` | 500 | 1 issue(s) |
| Registration links | `/admin/registration/` | 500 | 1 issue(s) |
| Create registration link | `/admin/registration/create/` | 500 | 1 issue(s) |
| Custom field admin | `/clients/admin/fields/` | 500 | 1 issue(s) |
| Create field group | `/clients/admin/fields/groups/create/` | 500 | 1 issue(s) |
| Create field definition | `/clients/admin/fields/create/` | 500 | 1 issue(s) |
| Event types list | `/events/admin/types/` | 500 | 1 issue(s) |
| Create event type | `/events/admin/types/create/` | 500 | 1 issue(s) |
| Note templates | `/admin/settings/note-templates/` | 500 | 1 issue(s) |
| Client data export form | `/reports/client-data-export/` | 500 | 1 issue(s) |
| Export links management | `/reports/export-links/` | 500 | 1 issue(s) |
| Diagnose charts | `/admin/settings/diagnose-charts/` | 500 | 1 issue(s) |
| Pending submissions | `/admin/submissions/` | 500 | 1 issue(s) |

### Direct Service

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin dashboard (403) | `/admin/settings/` | 500 | 1 issue(s) |
| Form validation errors | `/notes/client/1/quick/` | 500 | 4 issue(s) |
| Home page | `/` | 500 | 1 issue(s) |
| Client list | `/clients/` | 500 | 1 issue(s) |
| Create client form | `/clients/create/` | 500 | 1 issue(s) |
| Create client submit | `/clients/create/` | 500 | 1 issue(s) |
| Client detail | `/clients/1/` | 500 | 1 issue(s) |
| Edit client form | `/clients/1/edit/` | 500 | 1 issue(s) |
| Edit client submit | `/clients/1/edit/` | 500 | 1 issue(s) |
| Consent edit form | `/clients/1/consent/edit/` | 200 | None |
| Consent submit | `/clients/1/consent/` | 500 | 1 issue(s) |
| Custom fields edit | `/clients/1/custom-fields/edit/` | 200 | None |
| Quick note form | `/notes/client/1/quick/` | 500 | 1 issue(s) |
| Quick note submit | `/notes/client/1/quick/` | 500 | 1 issue(s) |
| Full note form | `/notes/client/1/new/` | 500 | 1 issue(s) |
| Notes timeline | `/notes/client/1/` | 500 | 1 issue(s) |
| Note detail | `/notes/1/` | 200 | None |
| Plan view (read-only) | `/plans/client/1/` | 500 | 1 issue(s) |
| Section create (403) | `/plans/client/1/sections/create/` | 500 | 1 issue(s) |
| Events tab | `/events/client/1/` | 500 | 1 issue(s) |
| Event create form | `/events/client/1/create/` | 500 | 1 issue(s) |
| Alert create form | `/events/client/1/alerts/create/` | 500 | 1 issue(s) |
| Client analysis | `/reports/client/1/analysis/` | 500 | 1 issue(s) |
| Programs list | `/programs/` | 500 | 1 issue(s) |
| Client list (Housing only) | `/clients/` | 500 | 1 issue(s) |
| Direct access to Bob's profile (403) | `/clients/2/` | 500 | 1 issue(s) |
| Access Jane's profile (own program) | `/clients/1/` | 500 | 1 issue(s) |
| Target history for Bob (403) | `/plans/targets/2/history/` | 500 | 1 issue(s) |
| Search for Bob (should find no results) | `/clients/search/?q=Bob` | 500 | 1 issue(s) |
| Client create form | `/clients/create/` | 500 | 1 issue(s) |
| View new client profile | `/clients/3/` | 500 | 1 issue(s) |
| Document intake session | `/notes/client/3/quick/` | 500 | 1 issue(s) |
| Notes timeline after intake | `/notes/client/3/` | 500 | 1 issue(s) |
| Search client list by note text | `/clients/?q=seemed+well` | 500 | 1 issue(s) |
| Dedicated search by note text | `/clients/search/?q=seemed+well` | 500 | 1 issue(s) |
| Search for other program's note content | `/clients/search/?q=vocational` | 500 | 1 issue(s) |
| Group detail (other program, 403) | `/groups/2/` | 500 | 1 issue(s) |
| Milestone edit (other program, 403) | `/groups/milestone/1/edit/` | 500 | 1 issue(s) |
| Own program group (200) | `/groups/1/` | 500 | 1 issue(s) |
| Session log (other program, 403) | `/groups/2/session/` | 500 | 1 issue(s) |
| Target history (other program, 403) | `/plans/targets/2/history/` | 500 | 1 issue(s) |

### Admin (FR)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin dashboard | `/admin/settings/` | 500 | 1 issue(s) |
| Features | `/admin/settings/features/` | 500 | 1 issue(s) |
| Instance settings | `/admin/settings/instance/` | 500 | 1 issue(s) |
| Terminology | `/admin/settings/terminology/` | 500 | 1 issue(s) |
| User list | `/admin/users/` | 500 | 1 issue(s) |
| Metric library | `/plans/admin/metrics/` | 500 | 1 issue(s) |
| Programs list | `/programs/` | 500 | 1 issue(s) |
| Event types | `/events/admin/types/` | 500 | 1 issue(s) |
| Note templates | `/admin/settings/note-templates/` | 500 | 1 issue(s) |
| Custom fields | `/clients/admin/fields/` | 500 | 1 issue(s) |
| Registration links | `/admin/registration/` | 500 | 1 issue(s) |
| Audit log | `/admin/audit/` | 500 | 1 issue(s) |

### Front Desk (FR)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page (FR) | `/` | 500 | 1 issue(s) |
| Client detail (FR) | `/clients/1/` | 500 | 1 issue(s) |
| Programs list (FR) | `/programs/` | 500 | 1 issue(s) |
| Home page | `/` | 500 | 1 issue(s) |
| Client list | `/clients/` | 500 | 1 issue(s) |
| Client detail | `/clients/1/` | 500 | 1 issue(s) |
| Programs list | `/programs/` | 500 | 1 issue(s) |

### Front Desk

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page | `/` | 500 | 1 issue(s) |
| Client list | `/clients/` | 500 | 1 issue(s) |
| Search for client | `/clients/search/?q=Jane` | 500 | 1 issue(s) |
| Client detail | `/clients/1/` | 500 | 1 issue(s) |
| Custom fields display | `/clients/1/custom-fields/display/` | 200 | None |
| Custom fields edit | `/clients/1/custom-fields/edit/` | 200 | None |
| Consent display | `/clients/1/consent/display/` | 200 | None |
| Create client (403) | `/clients/create/` | 500 | 1 issue(s) |
| Notes list (403) | `/notes/client/1/` | 500 | 1 issue(s) |
| Plan section create (403) | `/plans/client/1/sections/create/` | 500 | 1 issue(s) |
| Programs list | `/programs/` | 500 | 1 issue(s) |
| Search for unknown client | `/clients/search/?q=Maria` | 500 | 1 issue(s) |
| Can't create client (403) | `/clients/create/` | 500 | 1 issue(s) |

### Program Manager

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page | `/` | 500 | 1 issue(s) |
| Client list | `/clients/` | 500 | 1 issue(s) |
| Client detail | `/clients/1/` | 500 | 1 issue(s) |
| Notes timeline | `/notes/client/1/` | 500 | 1 issue(s) |
| Quick note form | `/notes/client/1/quick/` | 500 | 1 issue(s) |
| Full note form | `/notes/client/1/new/` | 500 | 1 issue(s) |
| Plan view (editable) | `/plans/client/1/` | 500 | 1 issue(s) |
| Section create form | `/plans/client/1/sections/create/` | 500 | 1 issue(s) |
| Section create submit | `/plans/client/1/sections/create/` | 500 | 1 issue(s) |
| Target create form | `/plans/sections/1/targets/create/` | 500 | 1 issue(s) |
| Target create submit | `/plans/sections/1/targets/create/` | 500 | 1 issue(s) |
| Target metrics | `/plans/targets/1/metrics/` | 500 | 1 issue(s) |
| Section status | `/plans/sections/1/status/` | 500 | 1 issue(s) |
| Target status | `/plans/targets/1/status/` | 500 | 1 issue(s) |
| Target history | `/plans/targets/1/history/` | 500 | 1 issue(s) |
| Metrics export form | `/reports/export/` | 500 | 1 issue(s) |
| CMT export form | `/reports/cmt-export/` | 500 | 1 issue(s) |
| Events tab | `/events/client/1/` | 500 | 1 issue(s) |
| Event create form | `/events/client/1/create/` | 500 | 1 issue(s) |
| Client analysis | `/reports/client/1/analysis/` | 500 | 1 issue(s) |
| Review new client | `/clients/3/` | 500 | 1 issue(s) |
| Plan view (empty for new client) | `/plans/client/3/` | 500 | 1 issue(s) |
| Create plan section | `/plans/client/3/sections/create/` | 500 | 1 issue(s) |

### Executive

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Executive dashboard | `/clients/executive/` | 500 | 1 issue(s) |
| Client list redirect | `/clients/` | 500 | 1 issue(s) |
| Client detail redirect | `/clients/1/` | 500 | 1 issue(s) |
| Programs list | `/programs/` | 500 | 1 issue(s) |
| Notes redirect | `/notes/client/1/` | 500 | 1 issue(s) |

### Non-admin spot check

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin settings (403) | `/admin/settings/` | 500 | 1 issue(s) |
| User list (403) | `/admin/users/` | 500 | 1 issue(s) |

### Admin+PM

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Client detail | `/clients/1/` | 500 | 1 issue(s) |
| Notes timeline | `/notes/client/1/` | 500 | 1 issue(s) |
| Plan view | `/plans/client/1/` | 500 | 1 issue(s) |
| Admin settings | `/admin/settings/` | 500 | 1 issue(s) |
| User list | `/admin/users/` | 500 | 1 issue(s) |

### Admin (no program)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin blocked from client detail (403) | `/clients/1/` | 500 | 1 issue(s) |

## Scenario Walkthroughs

### Admin Dashboard

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | Home page — admin link visible | `/` | 500 | None |
| Admin | Admin dashboard loads | `/admin/settings/` | 500 | None |
| Direct Service | Non-admin blocked (403) | `/admin/settings/` | 500 | None |

### Feature Toggles

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View feature toggles | `/admin/settings/features/` | 500 | None |
| Admin | Enable custom fields | `/admin/settings/features/` | 500 | None |
| Admin | Enable events | `/admin/settings/features/` | 500 | None |
| Admin | Disable alerts | `/admin/settings/features/` | 500 | None |

### Instance Settings

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View instance settings | `/admin/settings/instance/` | 500 | None |
| Admin | Save instance settings | `/admin/settings/instance/` | 500 | None |

### Program Management

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View programs list | `/programs/` | 500 | None |
| Admin | Open create program form | `/programs/create/` | 500 | None |
| Admin | Create program | `/programs/create/` | 500 | None |
| Admin | View program detail | `/programs/3/` | 500 | None |
| Admin | Open edit program form | `/programs/3/edit/` | 500 | None |
| Admin | Edit program saved | `/programs/3/edit/` | 500 | None |
| Admin | Assign staff to program | `/programs/3/roles/add/` | 200 | None |

### Metric Library

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View metric library | `/plans/admin/metrics/` | 500 | None |
| Admin | Open create metric form | `/plans/admin/metrics/create/` | 500 | None |
| Admin | Create metric | `/plans/admin/metrics/create/` | 500 | None |
| Admin | Open edit metric form | `/plans/admin/metrics/2/edit/` | 500 | None |
| Admin | Edit metric saved | `/plans/admin/metrics/2/edit/` | 500 | None |
| Admin | Toggle metric | `/plans/admin/metrics/2/toggle/` | 200 | None |

### Plan Templates

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View plan template list | `/admin/templates/` | 500 | None |
| Admin | Open create template form | `/admin/templates/create/` | 500 | None |
| Admin | Create template | `/admin/templates/create/` | 500 | None |
| Admin | View template detail | `/admin/templates/1/` | 500 | None |
| Admin | Open add section form | `/admin/templates/1/sections/create/` | 500 | None |
| Admin | Create section | `/admin/templates/1/sections/create/` | 500 | None |
| Admin | Open add target form | `/admin/templates/sections/1/targets/create/` | 500 | None |
| Admin | Create target | `/admin/templates/sections/1/targets/create/` | 500 | None |
| Admin | Open edit template form | `/admin/templates/1/edit/` | 500 | None |
| Admin | Edit template saved | `/admin/templates/1/edit/` | 500 | None |

### Note Templates

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View note template list | `/admin/settings/note-templates/` | 500 | None |
| Admin | Open create note template form | `/admin/settings/note-templates/create/` | 500 | None |
| Admin | Create note template with section | `/admin/settings/note-templates/create/` | 500 | None |
| Admin | Open edit note template form | `/admin/settings/note-templates/2/edit/` | 500 | None |

### Event Types

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View event types list | `/events/admin/types/` | 500 | None |
| Admin | Open create event type form | `/events/admin/types/create/` | 500 | None |
| Admin | Create event type | `/events/admin/types/create/` | 500 | None |
| Admin | Open edit event type form | `/events/admin/types/2/edit/` | 500 | None |
| Admin | Edit event type saved | `/events/admin/types/2/edit/` | 500 | None |
| Admin | List shows multiple event types | `/events/admin/types/` | 500 | None |

### Custom Client Fields

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View custom field admin | `/clients/admin/fields/` | 500 | None |
| Admin | Open create field group form | `/clients/admin/fields/groups/create/` | 500 | None |
| Admin | Create field group | `/clients/admin/fields/groups/create/` | 500 | None |
| Admin | Open create field definition form | `/clients/admin/fields/create/` | 500 | None |
| Admin | Create dropdown field | `/clients/admin/fields/create/` | 500 | None |
| Admin | Create sensitive text field | `/clients/admin/fields/create/` | 500 | None |
| Admin | Fields visible in admin | `/clients/admin/fields/` | 500 | None |
| Admin | Open edit field definition form | `/clients/admin/fields/3/edit/` | 500 | None |

### User Management

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View user list | `/admin/users/` | 500 | None |
| Admin | Open create user form | `/admin/users/new/` | 500 | None |
| Admin | Create user | `/admin/users/new/` | 500 | None |
| Admin | Open edit user form | `/admin/users/7/edit/` | 500 | None |
| Admin | Edit user saved | `/admin/users/7/edit/` | 500 | None |

### Invite System

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View invite list | `/auth/invites/` | 500 | None |
| Admin | Open create invite form | `/auth/invites/new/` | 500 | None |
| Admin | Create invite link | `/auth/invites/new/` | 500 | None |

### Registration Links

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View registration links | `/admin/registration/` | 500 | None |
| Admin | Open create registration link form | `/admin/registration/create/` | 500 | None |
| Admin | Create registration link | `/admin/registration/create/` | 500 | None |
| Admin | View pending submissions | `/admin/submissions/` | 500 | None |

### Audit Logs

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | View audit log | `/admin/audit/` | 500 | None |
| Admin | Filter audit log by date | `/admin/audit/?date_from=2020-01-01&date_to=2030-12-31` | 500 | None |
| Admin | Diagnose charts tool | `/admin/settings/diagnose-charts/` | 500 | None |

### Full Agency Setup

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin | 1. Start at admin dashboard | `/admin/settings/` | 500 | None |
| Admin | 2. Enable events feature | `/admin/settings/features/` | 500 | None |
| Admin | 3. Create program | `/programs/create/` | 500 | None |
| Admin | 4. Create metric | `/plans/admin/metrics/create/` | 500 | None |
| Admin | 5. Create event type | `/events/admin/types/create/` | 500 | None |
| Admin | 6. Create staff user | `/admin/users/new/` | 500 | None |
| Admin | 7. Assign staff to program | `/programs/3/roles/add/` | 200 | None |
| Admin | 8. Verify staff visible on program | `/programs/3/` | 500 | None |

### Admin in French

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin (FR) | Admin dashboard | `/admin/settings/` | 500 | None |
| Admin (FR) | Features | `/admin/settings/features/` | 500 | None |
| Admin (FR) | Instance settings | `/admin/settings/instance/` | 500 | None |
| Admin (FR) | Terminology | `/admin/settings/terminology/` | 500 | None |
| Admin (FR) | User list | `/admin/users/` | 500 | None |
| Admin (FR) | Metric library | `/plans/admin/metrics/` | 500 | None |
| Admin (FR) | Programs list | `/programs/` | 500 | None |
| Admin (FR) | Event types | `/events/admin/types/` | 500 | None |
| Admin (FR) | Note templates | `/admin/settings/note-templates/` | 500 | None |
| Admin (FR) | Custom fields | `/clients/admin/fields/` | 500 | None |
| Admin (FR) | Registration links | `/admin/registration/` | 500 | None |
| Admin (FR) | Audit log | `/admin/audit/` | 500 | None |

### Cross-Program Isolation

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Admin (no program) | Admin blocked from Jane (403) | `/clients/1/` | 500 | None |
| Direct Service | Client list (Housing only) | `/clients/` | 500 | None |
| Direct Service | Direct access to Bob (403) | `/clients/2/` | 500 | None |
| Direct Service | HTMX partial for Bob (403) | `/clients/2/custom-fields/display/` | 500 | 1 issue(s) |
| Direct Service | Jane's profile (own program) | `/clients/1/` | 500 | 1 issue(s) |
| Direct Service | Target history blocked | `/plans/targets/2/history/` | 500 | None |
| Direct Service | Search for Bob (no results expected) | `/clients/search/?q=Bob` | 500 | None |

### Morning Intake Flow

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Front Desk | Search for Maria (not found) | `/clients/search/?q=Maria` | 500 | None |
| Front Desk | Dana blocked from creating client | `/clients/create/` | 500 | None |
| Direct Service | Open create form | `/clients/create/` | 500 | None |
| Direct Service | View Maria's profile | `/clients/3/` | 500 | None |
| Direct Service | Write intake note | `/notes/client/3/quick/` | 500 | None |
| Direct Service | Check notes timeline | `/notes/client/3/` | 500 | None |
| Program Manager | Review Maria's profile | `/clients/3/` | 500 | None |
| Program Manager | View empty plan | `/plans/client/3/` | 500 | None |
| Program Manager | Create plan section | `/plans/client/3/sections/create/` | 500 | None |

### Full French Workday

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Front Desk (FR) | Home page | `/` | 500 | None |
| Front Desk (FR) | Client list | `/clients/` | 500 | None |
| Front Desk (FR) | Client detail | `/clients/1/` | 500 | None |
| Front Desk (FR) | Programs list | `/programs/` | 500 | None |

### Client Note Search

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Direct Service | Client list search by note content | `/clients/?q=seemed+well` | 500 | None |
| Direct Service | Dedicated search by note content | `/clients/search/?q=seemed+well` | 500 | None |
| Direct Service | Note search isolation (no cross-program leak) | `/clients/search/?q=vocational` | 500 | None |

### Group Permission Leakage

| Role | Step | URL | Status | Issues |
|------|------|-----|--------|--------|
| Direct Service | Group detail blocked | `/groups/2/` | 500 | None |
| Direct Service | Membership remove blocked | `/groups/member/1/remove/` | 500 | 1 issue(s) |
| Direct Service | Milestone create blocked | `/groups/2/milestone/` | 500 | 1 issue(s) |
| Direct Service | Milestone edit blocked | `/groups/milestone/1/edit/` | 500 | None |
| Direct Service | Outcome create blocked | `/groups/2/outcome/` | 500 | 1 issue(s) |
| Direct Service | Own program group accessible | `/groups/1/` | 500 | 1 issue(s) |
| Direct Service | Session log blocked | `/groups/2/session/` | 500 | None |
| Direct Service | Target history blocked | `/plans/targets/2/history/` | 500 | None |

## Browser-Based Findings

_Tested with Playwright (headless Chromium) + axe-core._

### Focus Management

- **[INFO]** `/clients/1/` — Consent: No consent edit button found

- **[INFO]** `/clients/3/` — Custom fields: No edit button found (may not have editable fields)

- **[INFO]** `/notes/client/5/` — Note expansion: No note card link found

- **[INFO]** `/plans/client/7/` — Plan section: No edit button found

- **[INFO]** `/clients/search/` — Search: No #client-search input found

### Responsive Layout

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "KoNote2" is 77x38px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Sign In" is 61x38px (min 44x44)

- **[INFO]** `/clients/` — [mobile] Client list: Touch target too small — <a> "KoNote2" is 77x38px (min 44x44)

- **[INFO]** `/clients/` — [mobile] Client list: Touch target too small — <a> "Sign In" is 61x38px (min 44x44)

## Recommendations

### Immediate (Critical)

1. Fix: Server error (500) — view crashed on `/`
1. Fix: Server error (500) — view crashed on `/admin/settings/`
1. Fix: Expected 403, got 500 on `/admin/settings/`
1. Fix: Server error (500) — view crashed on `/admin/settings/features/`
1. Fix: Server error (500) after POST on `/admin/settings/features/`
1. Fix: Server error (500) after POST on `/admin/settings/features/`
1. Fix: Server error (500) after POST on `/admin/settings/features/`
1. Fix: Server error (500) — view crashed on `/admin/settings/instance/`
1. Fix: Server error (500) after POST on `/admin/settings/instance/`
1. Fix: POST form missing CSRF token (action: /i18n/switch/) on `/programs/create/`
1. Fix: Server error (500) — view crashed on `/programs/`
1. Fix: Server error (500) — view crashed on `/programs/create/`
1. Fix: Server error (500) after POST on `/programs/create/`
1. Fix: Server error (500) — view crashed on `/programs/3/`
1. Fix: Server error (500) — view crashed on `/programs/3/edit/`
1. Fix: Server error (500) after POST on `/programs/3/edit/`
1. Fix: Server error (500) — view crashed on `/plans/admin/metrics/`
1. Fix: Server error (500) — view crashed on `/plans/admin/metrics/create/`
1. Fix: Server error (500) after POST on `/plans/admin/metrics/create/`
1. Fix: Server error (500) — view crashed on `/plans/admin/metrics/2/edit/`
1. Fix: Server error (500) after POST on `/plans/admin/metrics/2/edit/`
1. Fix: Server error (500) — view crashed on `/admin/templates/`
1. Fix: Server error (500) — view crashed on `/admin/templates/create/`
1. Fix: Server error (500) after POST on `/admin/templates/create/`
1. Fix: Server error (500) — view crashed on `/admin/templates/1/`
1. Fix: Server error (500) — view crashed on `/admin/templates/1/sections/create/`
1. Fix: Server error (500) after POST on `/admin/templates/1/sections/create/`
1. Fix: Server error (500) — view crashed on `/admin/templates/sections/1/targets/create/`
1. Fix: Server error (500) after POST on `/admin/templates/sections/1/targets/create/`
1. Fix: Server error (500) — view crashed on `/admin/templates/1/edit/`
1. Fix: Server error (500) after POST on `/admin/templates/1/edit/`
1. Fix: Server error (500) — view crashed on `/admin/settings/note-templates/`
1. Fix: Server error (500) — view crashed on `/admin/settings/note-templates/create/`
1. Fix: Server error (500) after POST on `/admin/settings/note-templates/create/`
1. Fix: Server error (500) — view crashed on `/admin/settings/note-templates/2/edit/`
1. Fix: Server error (500) — view crashed on `/events/admin/types/`
1. Fix: Server error (500) — view crashed on `/events/admin/types/create/`
1. Fix: Server error (500) after POST on `/events/admin/types/create/`
1. Fix: Server error (500) — view crashed on `/events/admin/types/2/edit/`
1. Fix: Server error (500) after POST on `/events/admin/types/2/edit/`
1. Fix: Server error (500) — view crashed on `/events/admin/types/`
1. Fix: Server error (500) — view crashed on `/clients/admin/fields/`
1. Fix: Server error (500) — view crashed on `/clients/admin/fields/groups/create/`
1. Fix: Server error (500) after POST on `/clients/admin/fields/groups/create/`
1. Fix: Server error (500) — view crashed on `/clients/admin/fields/create/`
1. Fix: Server error (500) after POST on `/clients/admin/fields/create/`
1. Fix: Server error (500) after POST on `/clients/admin/fields/create/`
1. Fix: Server error (500) — view crashed on `/clients/admin/fields/`
1. Fix: Server error (500) — view crashed on `/clients/admin/fields/3/edit/`
1. Fix: POST form missing CSRF token (action: /i18n/switch/) on `/admin/users/new/`
1. Fix: Server error (500) — view crashed on `/admin/users/`
1. Fix: Server error (500) — view crashed on `/admin/users/new/`
1. Fix: Server error (500) after POST on `/admin/users/new/`
1. Fix: Server error (500) — view crashed on `/admin/users/7/edit/`
1. Fix: Server error (500) after POST on `/admin/users/7/edit/`
1. Fix: Server error (500) — view crashed on `/auth/invites/`
1. Fix: Server error (500) — view crashed on `/auth/invites/new/`
1. Fix: Server error (500) after POST on `/auth/invites/new/`
1. Fix: Server error (500) — view crashed on `/admin/registration/`
1. Fix: Server error (500) — view crashed on `/admin/registration/create/`
1. Fix: Server error (500) after POST on `/admin/registration/create/`
1. Fix: Server error (500) — view crashed on `/admin/submissions/`
1. Fix: Server error (500) — view crashed on `/admin/audit/`
1. Fix: Server error (500) — view crashed on `/admin/audit/?date_from=2020-01-01&date_to=2030-12-31`
1. Fix: Server error (500) — view crashed on `/admin/settings/diagnose-charts/`
1. Fix: Server error (500) — view crashed on `/admin/settings/`
1. Fix: Server error (500) after POST on `/admin/settings/features/`
1. Fix: Server error (500) after POST on `/programs/create/`
1. Fix: Server error (500) after POST on `/plans/admin/metrics/create/`
1. Fix: Server error (500) after POST on `/events/admin/types/create/`
1. Fix: Server error (500) after POST on `/admin/users/new/`
1. Fix: Server error (500) — view crashed on `/programs/3/`
1. Fix: Server error (500) — view crashed on `/admin/settings/`
1. Fix: Server error (500) — view crashed on `/admin/settings/features/`
1. Fix: Server error (500) — view crashed on `/admin/settings/instance/`
1. Fix: Server error (500) — view crashed on `/admin/settings/terminology/`
1. Fix: Server error (500) — view crashed on `/admin/users/`
1. Fix: Server error (500) — view crashed on `/plans/admin/metrics/`
1. Fix: Server error (500) — view crashed on `/programs/`
1. Fix: Server error (500) — view crashed on `/events/admin/types/`
1. Fix: Server error (500) — view crashed on `/admin/settings/note-templates/`
1. Fix: Server error (500) — view crashed on `/clients/admin/fields/`
1. Fix: Server error (500) — view crashed on `/admin/registration/`
1. Fix: Server error (500) — view crashed on `/admin/audit/`
1. Fix: Server error (500) — view crashed on `/`
1. Fix: Server error (500) — view crashed on `/clients/1/`
1. Fix: Server error (500) — view crashed on `/programs/`
1. Fix: Server error (500) — view crashed on `/`
1. Fix: Server error (500) — view crashed on `/clients/`
1. Fix: Server error (500) — view crashed on `/clients/search/?q=Jane`
1. Fix: Server error (500) — view crashed on `/clients/1/`
1. Fix: Expected 403, got 500 on `/clients/create/`
1. Fix: Expected 403, got 500 on `/notes/client/1/`
1. Fix: Expected 403, got 500 on `/plans/client/1/sections/create/`
1. Fix: Server error (500) — view crashed on `/programs/`
1. Fix: POST form missing CSRF token (action: /i18n/switch/) on `/notes/client/1/quick/`
1. Fix: Server error (500) — view crashed on `/`
1. Fix: Server error (500) — view crashed on `/clients/`
1. Fix: Server error (500) — view crashed on `/clients/create/`
1. Fix: Server error (500) after POST on `/clients/create/`
1. Fix: Server error (500) — view crashed on `/clients/1/`
1. Fix: Server error (500) — view crashed on `/clients/1/edit/`
1. Fix: Server error (500) after POST on `/clients/1/edit/`
1. Fix: Server error (500) after POST on `/clients/1/consent/`
1. Fix: Server error (500) — view crashed on `/notes/client/1/quick/`
1. Fix: Server error (500) after POST on `/notes/client/1/quick/`
1. Fix: Server error (500) — view crashed on `/notes/client/1/new/`
1. Fix: Server error (500) — view crashed on `/notes/client/1/`
1. Fix: Server error (500) — view crashed on `/plans/client/1/`
1. Fix: Expected 403, got 500 on `/plans/client/1/sections/create/`
1. Fix: Server error (500) — view crashed on `/events/client/1/`
1. Fix: Server error (500) — view crashed on `/events/client/1/create/`
1. Fix: Server error (500) — view crashed on `/events/client/1/alerts/create/`
1. Fix: Server error (500) — view crashed on `/reports/client/1/analysis/`
1. Fix: Server error (500) — view crashed on `/programs/`
1. Fix: Server error (500) — view crashed on `/`
1. Fix: Server error (500) — view crashed on `/clients/`
1. Fix: Server error (500) — view crashed on `/clients/1/`
1. Fix: Server error (500) — view crashed on `/notes/client/1/`
1. Fix: Server error (500) — view crashed on `/notes/client/1/quick/`
1. Fix: Server error (500) — view crashed on `/notes/client/1/new/`
1. Fix: Server error (500) — view crashed on `/plans/client/1/`
1. Fix: Server error (500) — view crashed on `/plans/client/1/sections/create/`
1. Fix: Server error (500) after POST on `/plans/client/1/sections/create/`
1. Fix: Server error (500) — view crashed on `/plans/sections/1/targets/create/`
1. Fix: Server error (500) after POST on `/plans/sections/1/targets/create/`
1. Fix: Server error (500) on HTMX partial on `/plans/targets/1/metrics/`
1. Fix: Server error (500) on HTMX partial on `/plans/sections/1/status/`
1. Fix: Server error (500) on HTMX partial on `/plans/targets/1/status/`
1. Fix: Server error (500) on HTMX partial on `/plans/targets/1/history/`
1. Fix: Server error (500) — view crashed on `/reports/export/`
1. Fix: Server error (500) — view crashed on `/reports/cmt-export/`
1. Fix: Server error (500) — view crashed on `/events/client/1/`
1. Fix: Server error (500) — view crashed on `/events/client/1/create/`
1. Fix: Server error (500) — view crashed on `/reports/client/1/analysis/`
1. Fix: Server error (500) — view crashed on `/clients/executive/`
1. Fix: Server error (500) on redirect follow on `/clients/`
1. Fix: Server error (500) on redirect follow on `/clients/1/`
1. Fix: Server error (500) — view crashed on `/programs/`
1. Fix: Server error (500) on redirect follow on `/notes/client/1/`
1. Fix: Expected 403, got 500 on `/clients/1/`
1. Fix: Expected 403, got 500 on `/admin/settings/`
1. Fix: Expected 403, got 500 on `/admin/users/`
1. Fix: Server error (500) — view crashed on `/admin/settings/`
1. Fix: Server error (500) — view crashed on `/admin/settings/terminology/`
1. Fix: Server error (500) — view crashed on `/admin/settings/features/`
1. Fix: Server error (500) — view crashed on `/admin/settings/instance/`
1. Fix: Server error (500) — view crashed on `/plans/admin/metrics/`
1. Fix: Server error (500) — view crashed on `/plans/admin/metrics/create/`
1. Fix: Server error (500) — view crashed on `/programs/`
1. Fix: Server error (500) — view crashed on `/programs/create/`
1. Fix: Server error (500) — view crashed on `/programs/1/`
1. Fix: Server error (500) — view crashed on `/admin/users/`
1. Fix: Server error (500) — view crashed on `/admin/users/new/`
1. Fix: Server error (500) — view crashed on `/auth/invites/`
1. Fix: Server error (500) — view crashed on `/auth/invites/new/`
1. Fix: Server error (500) — view crashed on `/admin/audit/`
1. Fix: Server error (500) — view crashed on `/admin/registration/`
1. Fix: Server error (500) — view crashed on `/admin/registration/create/`
1. Fix: Server error (500) — view crashed on `/clients/admin/fields/`
1. Fix: Server error (500) — view crashed on `/clients/admin/fields/groups/create/`
1. Fix: Server error (500) — view crashed on `/clients/admin/fields/create/`
1. Fix: Server error (500) — view crashed on `/events/admin/types/`
1. Fix: Server error (500) — view crashed on `/events/admin/types/create/`
1. Fix: Server error (500) — view crashed on `/admin/settings/note-templates/`
1. Fix: Server error (500) — view crashed on `/reports/client-data-export/`
1. Fix: Server error (500) — view crashed on `/reports/export-links/`
1. Fix: Server error (500) — view crashed on `/admin/settings/diagnose-charts/`
1. Fix: Server error (500) — view crashed on `/admin/submissions/`
1. Fix: Server error (500) — view crashed on `/clients/1/`
1. Fix: Server error (500) — view crashed on `/notes/client/1/`
1. Fix: Server error (500) — view crashed on `/plans/client/1/`
1. Fix: Server error (500) — view crashed on `/admin/settings/`
1. Fix: Server error (500) — view crashed on `/admin/users/`
1. Fix: Expected 403, got 500 on `/clients/1/`
1. Fix: Server error (500) — view crashed on `/clients/`
1. Fix: Expected 403, got 500 on `/clients/2/`
1. Fix: Expected 403, got 500 on `/clients/2/custom-fields/display/`
1. Fix: Server error (500) — view crashed on `/clients/1/`
1. Fix: Expected 200, got 500 on `/clients/1/`
1. Fix: Expected 403, got 500 on `/plans/targets/2/history/`
1. Fix: Server error (500) — view crashed on `/clients/search/?q=Bob`
1. Fix: Server error (500) — view crashed on `/clients/search/?q=Maria`
1. Fix: Expected 403, got 500 on `/clients/create/`
1. Fix: Server error (500) — view crashed on `/clients/create/`
1. Fix: Server error (500) — view crashed on `/clients/3/`
1. Fix: Server error (500) after POST on `/notes/client/3/quick/`
1. Fix: Server error (500) — view crashed on `/notes/client/3/`
1. Fix: Server error (500) — view crashed on `/clients/3/`
1. Fix: Server error (500) — view crashed on `/plans/client/3/`
1. Fix: Server error (500) after POST on `/plans/client/3/sections/create/`
1. Fix: Server error (500) — view crashed on `/`
1. Fix: Server error (500) — view crashed on `/clients/`
1. Fix: Server error (500) — view crashed on `/clients/1/`
1. Fix: Server error (500) — view crashed on `/programs/`
1. Fix: Server error (500) — view crashed on `/clients/?q=seemed+well`
1. Fix: Server error (500) — view crashed on `/clients/search/?q=seemed+well`
1. Fix: Server error (500) — view crashed on `/clients/search/?q=vocational`
1. Fix: Expected 403, got 500 on `/groups/2/`
1. Fix: Expected 403, got 500 on `/groups/member/1/remove/`
1. Fix: Expected 403, got 500 on `/groups/2/milestone/`
1. Fix: Expected 403, got 500 on `/groups/milestone/1/edit/`
1. Fix: Expected 403, got 500 on `/groups/2/outcome/`
1. Fix: Server error (500) — view crashed on `/groups/1/`
1. Fix: Expected 200, got 500 on `/groups/1/`
1. Fix: Expected 403, got 500 on `/groups/2/session/`
1. Fix: Expected 403, got 500 on `/plans/targets/2/history/`

### Short-term (Warnings)

- Expected form errors but none found (no .errorlist elements) (`/programs/create/`)
- <html> element missing lang attribute (`/programs/create/`)
- Page has no <title> or title is empty (`/programs/3/roles/add/`)
- No <main> landmark element found (`/programs/3/roles/add/`)
- No <nav> element found on full page (`/programs/3/roles/add/`)
- No <html> element found (`/programs/3/roles/add/`)
- Expected form errors but none found (no .errorlist elements) (`/admin/users/new/`)
- <html> element missing lang attribute (`/admin/users/new/`)
- Page has no <title> or title is empty (`/programs/3/roles/add/`)
- No <main> landmark element found (`/programs/3/roles/add/`)
- No <nav> element found on full page (`/programs/3/roles/add/`)
- No <html> element found (`/programs/3/roles/add/`)
- Expected form errors but none found (no .errorlist elements) (`/notes/client/1/quick/`)
- <html> element missing lang attribute (`/notes/client/1/quick/`)

---

_Generated by `tests/ux_walkthrough/` — automated UX walkthrough_
