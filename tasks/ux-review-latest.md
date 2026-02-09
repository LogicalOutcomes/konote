# KoNote2 UX Walkthrough Report

**Generated:** 2026-02-08 22:24:59  
**Command:** `pytest tests/ux_walkthrough/ -v`

## Summary

| Metric | This Run | Previous |
|--------|----------|----------|
| Pages visited | 326 | 326 (same) |
| Critical issues | 1 | 4 (down 3) |
| Warnings | 18 | 21 (down 3) |
| Info items | 216 | 37 (up 179) |

## Critical Issues

- **[Browser] Colour Contrast** `/clients/1/`
  [light] Client detail: Contrast violation (serious) on `.quick-info-section > .quick-info > .quick-info-item > dt`
  _Fix any of the following:
  Element has insufficient color contrast of 4.26 (foreground color: #64748b, background color: #ecf4f4, font size: 8.4pt (11.25px), font weight: normal). Expected contrast r_

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

- **[Direct Service] Target history for Bob (403)** `/plans/targets/2/history/`
  403 page has no links — user may be stuck

- **[Direct Service] Target history (other program, 403)** `/plans/targets/2/history/`
  403 page has no links — user may be stuck

- **[Browser] Focus Management** `/clients/3/`
  Custom fields: Focus lost after switching to edit mode
  _Focus on: None_

- **[Browser] Focus Management** `/plans/client/7/`
  Plan section: Focus lost after clicking Edit
  _Focus on: None_

- **[Browser] Responsive Layout** `/plans/client/3/`
  [mobile] Plan view: Horizontal overflow detected
  _scrollWidth=466, clientWidth=375 at 375x667_

## Info Issues

- **[Admin] Home page (find admin link)** `/`
  No skip navigation link found

- **[Admin] Admin settings dashboard** `/admin/settings/`
  No skip navigation link found

- **[Admin] Features page** `/admin/settings/features/`
  No skip navigation link found

- **[Admin] Enable custom fields** `/admin/settings/features/`
  No skip navigation link found

- **[Admin] Enable events** `/admin/settings/features/`
  No skip navigation link found

- **[Admin] Disable alerts** `/admin/settings/features/`
  No skip navigation link found

- **[Admin] Instance settings form** `/admin/settings/instance/`
  No skip navigation link found

- **[Admin] Save instance settings** `/admin/settings/instance/`
  No skip navigation link found

- **[Admin] Form validation — empty program name** `/programs/create/`
  No skip navigation link found

- **[Admin] Programs list** `/programs/`
  No skip navigation link found

- **[Admin] Create program form** `/programs/create/`
  No skip navigation link found

- **[Admin] Submit new program** `/programs/create/`
  No skip navigation link found

- **[Admin] Program detail** `/programs/3/`
  No skip navigation link found

- **[Admin] Edit program form** `/programs/3/edit/`
  No skip navigation link found

- **[Admin] Update program** `/programs/3/edit/`
  No skip navigation link found

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No headings found on page

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No <meta name="viewport"> tag found

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No skip navigation link found

- **[Admin] Assign staff to program** `/programs/3/roles/add/`
  No success message found after form submission

- **[Admin] Metric library** `/plans/admin/metrics/`
  No skip navigation link found

- **[Admin] Create metric form** `/plans/admin/metrics/create/`
  No skip navigation link found

- **[Admin] Submit new metric** `/plans/admin/metrics/create/`
  No skip navigation link found

- **[Admin] Edit metric form** `/plans/admin/metrics/2/edit/`
  No skip navigation link found

- **[Admin] Update metric** `/plans/admin/metrics/2/edit/`
  No skip navigation link found

- **[Admin] Plan template list** `/admin/templates/`
  No skip navigation link found

- **[Admin] Create template form** `/admin/templates/create/`
  No skip navigation link found

- **[Admin] Submit new template** `/admin/templates/create/`
  No skip navigation link found

- **[Admin] Template detail** `/admin/templates/1/`
  No skip navigation link found

- **[Admin] Add section form** `/admin/templates/1/sections/create/`
  No skip navigation link found

- **[Admin] Submit new section** `/admin/templates/1/sections/create/`
  No skip navigation link found

- **[Admin] Add target form** `/admin/templates/sections/1/targets/create/`
  No skip navigation link found

- **[Admin] Submit new target** `/admin/templates/sections/1/targets/create/`
  No skip navigation link found

- **[Admin] Edit template form** `/admin/templates/1/edit/`
  No skip navigation link found

- **[Admin] Update template** `/admin/templates/1/edit/`
  No skip navigation link found

- **[Admin] Note template list** `/admin/settings/note-templates/`
  No skip navigation link found

- **[Admin] Create note template form** `/admin/settings/note-templates/create/`
  No skip navigation link found

- **[Admin] Submit new note template** `/admin/settings/note-templates/create/`
  No skip navigation link found

- **[Admin] Edit note template form** `/admin/settings/note-templates/2/edit/`
  No skip navigation link found

- **[Admin] Event types list** `/events/admin/types/`
  No skip navigation link found

- **[Admin] Create event type form** `/events/admin/types/create/`
  No skip navigation link found

- **[Admin] Submit new event type** `/events/admin/types/create/`
  No skip navigation link found

- **[Admin] Edit event type form** `/events/admin/types/2/edit/`
  No skip navigation link found

- **[Admin] Update event type** `/events/admin/types/2/edit/`
  No skip navigation link found

- **[Admin] Event types list (multiple)** `/events/admin/types/`
  No skip navigation link found

- **[Admin] Event types list (multiple)** `/events/admin/types/`
  "Court Hearing" button/link expected but not found for Admin

- **[Admin] Event types list (multiple)** `/events/admin/types/`
  "Hospital Visit" button/link expected but not found for Admin

- **[Admin] Custom field admin** `/clients/admin/fields/`
  No skip navigation link found

- **[Admin] Create field group form** `/clients/admin/fields/groups/create/`
  No skip navigation link found

- **[Admin] Submit new field group** `/clients/admin/fields/groups/create/`
  No skip navigation link found

- **[Admin] Create field definition form** `/clients/admin/fields/create/`
  No skip navigation link found

- **[Admin] Submit dropdown field** `/clients/admin/fields/create/`
  No skip navigation link found

- **[Admin] Submit text field** `/clients/admin/fields/create/`
  No skip navigation link found

- **[Admin] Custom field admin (populated)** `/clients/admin/fields/`
  No skip navigation link found

- **[Admin] Custom field admin (populated)** `/clients/admin/fields/`
  "Referral Source" button/link expected but not found for Admin

- **[Admin] Custom field admin (populated)** `/clients/admin/fields/`
  "Housing Status" button/link expected but not found for Admin

- **[Admin] Edit field definition form** `/clients/admin/fields/3/edit/`
  No skip navigation link found

- **[Admin] Form validation — password mismatch** `/admin/users/new/`
  No skip navigation link found

- **[Admin] User list** `/admin/users/`
  No skip navigation link found

- **[Admin] Create user form** `/admin/users/new/`
  No skip navigation link found

- **[Admin] Submit new user** `/admin/users/new/`
  No skip navigation link found

- **[Admin] Edit user form** `/admin/users/7/edit/`
  No skip navigation link found

- **[Admin] Update user** `/admin/users/7/edit/`
  No skip navigation link found

- **[Admin] Invite list** `/auth/invites/`
  No skip navigation link found

- **[Admin] Create invite form** `/auth/invites/new/`
  No skip navigation link found

- **[Admin] Submit new invite** `/auth/invites/new/`
  No skip navigation link found

- **[Admin] Registration links list** `/admin/registration/`
  No skip navigation link found

- **[Admin] Create registration link form** `/admin/registration/create/`
  No skip navigation link found

- **[Admin] Submit new registration link** `/admin/registration/create/`
  No skip navigation link found

- **[Admin] Submit new registration link** `/admin/registration/create/`
  Table missing <caption> or aria-label

- **[Admin] Pending submissions** `/admin/submissions/`
  No skip navigation link found

- **[Admin] Audit log list** `/admin/audit/`
  No skip navigation link found

- **[Admin] Audit log filtered** `/admin/audit/?date_from=2020-01-01&date_to=2030-12-31`
  No skip navigation link found

- **[Admin] Diagnose charts** `/admin/settings/diagnose-charts/`
  No skip navigation link found

- **[Admin] Start at dashboard** `/admin/settings/`
  No skip navigation link found

- **[Admin] Enable events feature** `/admin/settings/features/`
  No skip navigation link found

- **[Admin] Create first program** `/programs/create/`
  No skip navigation link found

- **[Admin] Create first metric** `/plans/admin/metrics/create/`
  No skip navigation link found

- **[Admin] Create first event type** `/events/admin/types/create/`
  No skip navigation link found

- **[Admin] Create first staff user** `/admin/users/new/`
  No skip navigation link found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No headings found on page

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No <meta name="viewport"> tag found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No skip navigation link found

- **[Admin] Assign worker to program** `/programs/3/roles/add/`
  No success message found after form submission

- **[Admin] Program with staff** `/programs/3/`
  No skip navigation link found

- **[Admin] Program with staff** `/programs/3/`
  "Amir" button/link expected but not found for Admin

- **[Admin (FR)] Admin dashboard** `/admin/settings/`
  No skip navigation link found

- **[Admin (FR)] Features** `/admin/settings/features/`
  No skip navigation link found

- **[Admin (FR)] Instance settings** `/admin/settings/instance/`
  No skip navigation link found

- **[Admin (FR)] Terminology** `/admin/settings/terminology/`
  No skip navigation link found

- **[Admin (FR)] User list** `/admin/users/`
  No skip navigation link found

- **[Admin (FR)] Metric library** `/plans/admin/metrics/`
  No skip navigation link found

- **[Admin (FR)] Programs list** `/programs/`
  No skip navigation link found

- **[Admin (FR)] Event types** `/events/admin/types/`
  No skip navigation link found

- **[Admin (FR)] Note templates** `/admin/settings/note-templates/`
  No skip navigation link found

- **[Admin (FR)] Custom fields** `/clients/admin/fields/`
  No skip navigation link found

- **[Admin (FR)] Registration links** `/admin/registration/`
  No skip navigation link found

- **[Admin (FR)] Audit log** `/admin/audit/`
  No skip navigation link found

- **[Admin (FR)] Audit log** `/admin/audit/`
  Table missing <caption> or aria-label

- **[Front Desk (FR)] Home page (FR)** `/`
  No skip navigation link found

- **[Front Desk (FR)] Client detail (FR)** `/clients/1/`
  No skip navigation link found

- **[Front Desk (FR)] Programs list (FR)** `/programs/`
  No skip navigation link found

- **[Front Desk] Home page** `/`
  No skip navigation link found

- **[Front Desk] Client list** `/clients/`
  No skip navigation link found

- **[Front Desk] Search for client** `/clients/search/?q=Jane`
  No skip navigation link found

- **[Front Desk] Client detail** `/clients/1/`
  No skip navigation link found

- **[Front Desk] Programs list** `/programs/`
  No skip navigation link found

- **[Direct Service] Form validation — empty quick note** `/notes/client/1/quick/`
  No skip navigation link found

- **[Direct Service] Home page** `/`
  No skip navigation link found

- **[Direct Service] Client list** `/clients/`
  No skip navigation link found

- **[Direct Service] Create client form** `/clients/create/`
  No skip navigation link found

- **[Direct Service] Create client submit** `/clients/create/`
  No skip navigation link found

- **[Direct Service] Client detail** `/clients/1/`
  No skip navigation link found

- **[Direct Service] Edit client form** `/clients/1/edit/`
  No skip navigation link found

- **[Direct Service] Edit client submit** `/clients/1/edit/`
  No skip navigation link found

- **[Direct Service] Consent submit** `/clients/1/consent/`
  No skip navigation link found

- **[Direct Service] Quick note form** `/notes/client/1/quick/`
  No skip navigation link found

- **[Direct Service] Quick note submit** `/notes/client/1/quick/`
  No skip navigation link found

- **[Direct Service] Full note form** `/notes/client/1/new/`
  No skip navigation link found

- **[Direct Service] Notes timeline** `/notes/client/1/`
  No skip navigation link found

- **[Direct Service] Plan view (read-only)** `/plans/client/1/`
  No skip navigation link found

- **[Direct Service] Events tab** `/events/client/1/`
  No skip navigation link found

- **[Direct Service] Event create form** `/events/client/1/create/`
  No skip navigation link found

- **[Direct Service] Alert create form** `/events/client/1/alerts/create/`
  No skip navigation link found

- **[Direct Service] Client analysis** `/reports/client/1/analysis/`
  No skip navigation link found

- **[Direct Service] Programs list** `/programs/`
  No skip navigation link found

- **[Program Manager] Home page** `/`
  No skip navigation link found

- **[Program Manager] Client list** `/clients/`
  No skip navigation link found

- **[Program Manager] Client detail** `/clients/1/`
  No skip navigation link found

- **[Program Manager] Notes timeline** `/notes/client/1/`
  No skip navigation link found

- **[Program Manager] Quick note form** `/notes/client/1/quick/`
  No skip navigation link found

- **[Program Manager] Full note form** `/notes/client/1/new/`
  No skip navigation link found

- **[Program Manager] Plan view (editable)** `/plans/client/1/`
  No skip navigation link found

- **[Program Manager] Section create form** `/plans/client/1/sections/create/`
  No skip navigation link found

- **[Program Manager] Section create submit** `/plans/client/1/sections/create/`
  No skip navigation link found

- **[Program Manager] Target create form** `/plans/sections/1/targets/create/`
  No skip navigation link found

- **[Program Manager] Target create submit** `/plans/sections/1/targets/create/`
  No skip navigation link found

- **[Program Manager] Metrics export form** `/reports/export/`
  No skip navigation link found

- **[Program Manager] CMT export form** `/reports/cmt-export/`
  No skip navigation link found

- **[Program Manager] Events tab** `/events/client/1/`
  No skip navigation link found

- **[Program Manager] Event create form** `/events/client/1/create/`
  No skip navigation link found

- **[Program Manager] Client analysis** `/reports/client/1/analysis/`
  No skip navigation link found

- **[Executive] Executive dashboard** `/clients/executive/`
  No skip navigation link found

- **[Executive] Client list redirect** `/clients/`
  No skip navigation link found

- **[Executive] Client detail redirect** `/clients/1/`
  No skip navigation link found

- **[Executive] Programs list** `/programs/`
  No skip navigation link found

- **[Executive] Notes redirect** `/notes/client/1/`
  No skip navigation link found

- **[Admin] Admin settings dashboard** `/admin/settings/`
  No skip navigation link found

- **[Admin] Terminology settings** `/admin/settings/terminology/`
  No skip navigation link found

- **[Admin] Feature toggles** `/admin/settings/features/`
  No skip navigation link found

- **[Admin] Instance settings** `/admin/settings/instance/`
  No skip navigation link found

- **[Admin] Metrics library** `/plans/admin/metrics/`
  No skip navigation link found

- **[Admin] Create metric form** `/plans/admin/metrics/create/`
  No skip navigation link found

- **[Admin] Programs list** `/programs/`
  No skip navigation link found

- **[Admin] Create program form** `/programs/create/`
  No skip navigation link found

- **[Admin] Program detail** `/programs/1/`
  No skip navigation link found

- **[Admin] User list** `/admin/users/`
  No skip navigation link found

- **[Admin] Create user form** `/admin/users/new/`
  No skip navigation link found

- **[Admin] Invite list** `/auth/invites/`
  No skip navigation link found

- **[Admin] Create invite form** `/auth/invites/new/`
  No skip navigation link found

- **[Admin] Audit log** `/admin/audit/`
  No skip navigation link found

- **[Admin] Registration links** `/admin/registration/`
  No skip navigation link found

- **[Admin] Create registration link** `/admin/registration/create/`
  No skip navigation link found

- **[Admin] Custom field admin** `/clients/admin/fields/`
  No skip navigation link found

- **[Admin] Create field group** `/clients/admin/fields/groups/create/`
  No skip navigation link found

- **[Admin] Create field definition** `/clients/admin/fields/create/`
  No skip navigation link found

- **[Admin] Event types list** `/events/admin/types/`
  No skip navigation link found

- **[Admin] Create event type** `/events/admin/types/create/`
  No skip navigation link found

- **[Admin] Note templates** `/admin/settings/note-templates/`
  No skip navigation link found

- **[Admin] Client data export form** `/reports/client-data-export/`
  No skip navigation link found

- **[Admin] Export links management** `/reports/export-links/`
  No skip navigation link found

- **[Admin] Diagnose charts** `/admin/settings/diagnose-charts/`
  No skip navigation link found

- **[Admin] Pending submissions** `/admin/submissions/`
  No skip navigation link found

- **[Admin+PM] Client detail** `/clients/1/`
  No skip navigation link found

- **[Admin+PM] Notes timeline** `/notes/client/1/`
  No skip navigation link found

- **[Admin+PM] Plan view** `/plans/client/1/`
  No skip navigation link found

- **[Admin+PM] Admin settings** `/admin/settings/`
  No skip navigation link found

- **[Admin+PM] User list** `/admin/users/`
  No skip navigation link found

- **[Direct Service] Client list (Housing only)** `/clients/`
  No skip navigation link found

- **[Direct Service] Access Jane's profile (own program)** `/clients/1/`
  No skip navigation link found

- **[Direct Service] Search for Bob (should find no results)** `/clients/search/?q=Bob`
  No skip navigation link found

- **[Front Desk] Search for unknown client** `/clients/search/?q=Maria`
  No skip navigation link found

- **[Direct Service] Client create form** `/clients/create/`
  No skip navigation link found

- **[Direct Service] View new client profile** `/clients/3/`
  No skip navigation link found

- **[Direct Service] Document intake session** `/notes/client/3/quick/`
  No skip navigation link found

- **[Direct Service] Notes timeline after intake** `/notes/client/3/`
  No skip navigation link found

- **[Program Manager] Review new client** `/clients/3/`
  No skip navigation link found

- **[Program Manager] Plan view (empty for new client)** `/plans/client/3/`
  No skip navigation link found

- **[Program Manager] Create plan section** `/plans/client/3/sections/create/`
  No skip navigation link found

- **[Front Desk (FR)] Home page** `/`
  No skip navigation link found

- **[Front Desk (FR)] Client list** `/clients/`
  No skip navigation link found

- **[Front Desk (FR)] Client detail** `/clients/1/`
  No skip navigation link found

- **[Front Desk (FR)] Programs list** `/programs/`
  No skip navigation link found

- **[Direct Service] Search client list by note text** `/clients/?q=seemed+well`
  No skip navigation link found

- **[Direct Service] Dedicated search by note text** `/clients/search/?q=seemed+well`
  No skip navigation link found

- **[Direct Service] Search for other program's note content** `/clients/search/?q=vocational`
  No skip navigation link found

- **[Direct Service] Own program group (200)** `/groups/1/`
  No skip navigation link found

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "KoNote2" is 77x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <button> "" is 39x13px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Home" is 55x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Participants" is 91x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Info" is 48x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Plan1" is 69x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Progress Note1" is 128x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Events2" is 83x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Analysis" is 72x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Edit" is 343x36px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "← Back to List" is 75x18px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Export PDF" is 343x36px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <a> "Export All Data" is 343x36px (min 44x44)

- **[Browser] Responsive Layout** `/clients/5/`
  [mobile] Client detail: Touch target too small — <button> "✎ Edit" is 70x28px (min 44x44)

- **[Browser] Responsive Layout** `/clients/`
  [mobile] Client list: Touch target too small — <a> "KoNote2" is 77x38px (min 44x44)

- **[Browser] Responsive Layout** `/clients/`
  [mobile] Client list: Touch target too small — <button> "" is 39x13px (min 44x44)

- **[Browser] Responsive Layout** `/clients/`
  [mobile] Client list: Touch target too small — <select> "All statuses" is 309x41px (min 44x44)

- **[Browser] Responsive Layout** `/clients/`
  [mobile] Client list: Touch target too small — <select> "All Programs" is 309x41px (min 44x44)

- **[Browser] Responsive Layout** `/clients/`
  [mobile] Client list: Touch target too small — <a> "Clear filters" is 94x36px (min 44x44)

- **[Browser] Responsive Layout** `/clients/`
  [mobile] Client list: Touch target too small — <a> "Jane Doe" is 62x20px (min 44x44)

## Known Limitations

- Colour contrast, focus management, and responsive layout are tested via Playwright browser tests
- Colour contrast checks depend on CDN (axe-core) — require internet

## Per-Role Walkthrough Results

### Admin

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page (find admin link) | `/` | 200 | 1 issue(s) |
| Admin settings dashboard | `/admin/settings/` | 200 | 1 issue(s) |
| Features page | `/admin/settings/features/` | 200 | 1 issue(s) |
| Enable custom fields | `/admin/settings/features/` | 200 | 1 issue(s) |
| Enable events | `/admin/settings/features/` | 200 | 1 issue(s) |
| Disable alerts | `/admin/settings/features/` | 200 | 1 issue(s) |
| Instance settings form | `/admin/settings/instance/` | 200 | 1 issue(s) |
| Save instance settings | `/admin/settings/instance/` | 200 | 1 issue(s) |
| Program form validation | `/programs/create/` | 200 | 2 issue(s) |
| Programs list | `/programs/` | 200 | 1 issue(s) |
| Create program form | `/programs/create/` | 200 | 1 issue(s) |
| Submit new program | `/programs/create/` | 200 | 1 issue(s) |
| Program detail | `/programs/3/` | 200 | 1 issue(s) |
| Edit program form | `/programs/3/edit/` | 200 | 1 issue(s) |
| Update program | `/programs/3/edit/` | 200 | 1 issue(s) |
| Assign staff to program | `/programs/3/roles/add/` | 200 | 8 issue(s) |
| Metric library | `/plans/admin/metrics/` | 200 | 1 issue(s) |
| Create metric form | `/plans/admin/metrics/create/` | 200 | 1 issue(s) |
| Submit new metric | `/plans/admin/metrics/create/` | 200 | 1 issue(s) |
| Edit metric form | `/plans/admin/metrics/2/edit/` | 200 | 1 issue(s) |
| Update metric | `/plans/admin/metrics/2/edit/` | 200 | 1 issue(s) |
| Toggle metric off | `/plans/admin/metrics/2/toggle/` | 200 | None |
| Plan template list | `/admin/templates/` | 200 | 1 issue(s) |
| Create template form | `/admin/templates/create/` | 200 | 1 issue(s) |
| Submit new template | `/admin/templates/create/` | 200 | 1 issue(s) |
| Template detail | `/admin/templates/1/` | 200 | 1 issue(s) |
| Add section form | `/admin/templates/1/sections/create/` | 200 | 1 issue(s) |
| Submit new section | `/admin/templates/1/sections/create/` | 200 | 1 issue(s) |
| Add target form | `/admin/templates/sections/1/targets/create/` | 200 | 1 issue(s) |
| Submit new target | `/admin/templates/sections/1/targets/create/` | 200 | 1 issue(s) |
| Edit template form | `/admin/templates/1/edit/` | 200 | 1 issue(s) |
| Update template | `/admin/templates/1/edit/` | 200 | 1 issue(s) |
| Note template list | `/admin/settings/note-templates/` | 200 | 1 issue(s) |
| Create note template form | `/admin/settings/note-templates/create/` | 200 | 1 issue(s) |
| Submit new note template | `/admin/settings/note-templates/create/` | 200 | 1 issue(s) |
| Edit note template form | `/admin/settings/note-templates/2/edit/` | 200 | 1 issue(s) |
| Event types list | `/events/admin/types/` | 200 | 1 issue(s) |
| Create event type form | `/events/admin/types/create/` | 200 | 1 issue(s) |
| Submit new event type | `/events/admin/types/create/` | 200 | 1 issue(s) |
| Edit event type form | `/events/admin/types/2/edit/` | 200 | 1 issue(s) |
| Update event type | `/events/admin/types/2/edit/` | 200 | 1 issue(s) |
| Event types list (multiple) | `/events/admin/types/` | 200 | 3 issue(s) |
| Custom field admin | `/clients/admin/fields/` | 200 | 1 issue(s) |
| Create field group form | `/clients/admin/fields/groups/create/` | 200 | 1 issue(s) |
| Submit new field group | `/clients/admin/fields/groups/create/` | 200 | 1 issue(s) |
| Create field definition form | `/clients/admin/fields/create/` | 200 | 1 issue(s) |
| Submit dropdown field | `/clients/admin/fields/create/` | 200 | 1 issue(s) |
| Submit text field | `/clients/admin/fields/create/` | 200 | 1 issue(s) |
| Custom field admin (populated) | `/clients/admin/fields/` | 200 | 3 issue(s) |
| Edit field definition form | `/clients/admin/fields/3/edit/` | 200 | 1 issue(s) |
| User form password mismatch | `/admin/users/new/` | 200 | 2 issue(s) |
| User list | `/admin/users/` | 200 | 1 issue(s) |
| Create user form | `/admin/users/new/` | 200 | 1 issue(s) |
| Submit new user | `/admin/users/new/` | 200 | 2 issue(s) |
| Edit user form | `/admin/users/7/edit/` | 200 | 1 issue(s) |
| Update user | `/admin/users/7/edit/` | 200 | 2 issue(s) |
| Invite list | `/auth/invites/` | 200 | 1 issue(s) |
| Create invite form | `/auth/invites/new/` | 200 | 1 issue(s) |
| Submit new invite | `/auth/invites/new/` | 200 | 1 issue(s) |
| Registration links list | `/admin/registration/` | 200 | 1 issue(s) |
| Create registration link form | `/admin/registration/create/` | 200 | 1 issue(s) |
| Submit new registration link | `/admin/registration/create/` | 200 | 2 issue(s) |
| Pending submissions | `/admin/submissions/` | 200 | 1 issue(s) |
| Audit log list | `/admin/audit/` | 200 | 1 issue(s) |
| Audit log filtered | `/admin/audit/?date_from=2020-01-01&date_to=2030-12-31` | 200 | 1 issue(s) |
| Diagnose charts | `/admin/settings/diagnose-charts/` | 200 | 1 issue(s) |
| Start at dashboard | `/admin/settings/` | 200 | 1 issue(s) |
| Enable events feature | `/admin/settings/features/` | 200 | 1 issue(s) |
| Create first program | `/programs/create/` | 200 | 1 issue(s) |
| Create first metric | `/plans/admin/metrics/create/` | 200 | 1 issue(s) |
| Create first event type | `/events/admin/types/create/` | 200 | 1 issue(s) |
| Create first staff user | `/admin/users/new/` | 200 | 2 issue(s) |
| Assign worker to program | `/programs/3/roles/add/` | 200 | 8 issue(s) |
| Program with staff | `/programs/3/` | 200 | 2 issue(s) |
| Client detail without program role (403) | `/clients/1/` | 403 | None |
| Admin settings dashboard | `/admin/settings/` | 200 | 1 issue(s) |
| Terminology settings | `/admin/settings/terminology/` | 200 | 1 issue(s) |
| Feature toggles | `/admin/settings/features/` | 200 | 1 issue(s) |
| Instance settings | `/admin/settings/instance/` | 200 | 1 issue(s) |
| Metrics library | `/plans/admin/metrics/` | 200 | 1 issue(s) |
| Create metric form | `/plans/admin/metrics/create/` | 200 | 1 issue(s) |
| Programs list | `/programs/` | 200 | 1 issue(s) |
| Create program form | `/programs/create/` | 200 | 1 issue(s) |
| Program detail | `/programs/1/` | 200 | 1 issue(s) |
| User list | `/admin/users/` | 200 | 1 issue(s) |
| Create user form | `/admin/users/new/` | 200 | 1 issue(s) |
| Invite list | `/auth/invites/` | 200 | 1 issue(s) |
| Create invite form | `/auth/invites/new/` | 200 | 1 issue(s) |
| Audit log | `/admin/audit/` | 200 | 1 issue(s) |
| Registration links | `/admin/registration/` | 200 | 1 issue(s) |
| Create registration link | `/admin/registration/create/` | 200 | 1 issue(s) |
| Custom field admin | `/clients/admin/fields/` | 200 | 1 issue(s) |
| Create field group | `/clients/admin/fields/groups/create/` | 200 | 1 issue(s) |
| Create field definition | `/clients/admin/fields/create/` | 200 | 1 issue(s) |
| Event types list | `/events/admin/types/` | 200 | 1 issue(s) |
| Create event type | `/events/admin/types/create/` | 200 | 1 issue(s) |
| Note templates | `/admin/settings/note-templates/` | 200 | 1 issue(s) |
| Client data export form | `/reports/client-data-export/` | 200 | 1 issue(s) |
| Export links management | `/reports/export-links/` | 200 | 1 issue(s) |
| Diagnose charts | `/admin/settings/diagnose-charts/` | 200 | 1 issue(s) |
| Pending submissions | `/admin/submissions/` | 200 | 1 issue(s) |

### Direct Service

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin dashboard (403) | `/admin/settings/` | 403 | None |
| Form validation errors | `/notes/client/1/quick/` | 200 | 1 issue(s) |
| Home page | `/` | 200 | 1 issue(s) |
| Client list | `/clients/` | 200 | 1 issue(s) |
| Create client form | `/clients/create/` | 200 | 1 issue(s) |
| Create client submit | `/clients/create/` | 200 | 1 issue(s) |
| Client detail | `/clients/1/` | 200 | 1 issue(s) |
| Edit client form | `/clients/1/edit/` | 200 | 1 issue(s) |
| Edit client submit | `/clients/1/edit/` | 200 | 1 issue(s) |
| Consent edit form | `/clients/1/consent/edit/` | 200 | None |
| Consent submit | `/clients/1/consent/` | 200 | 1 issue(s) |
| Custom fields edit | `/clients/1/custom-fields/edit/` | 200 | None |
| Quick note form | `/notes/client/1/quick/` | 200 | 1 issue(s) |
| Quick note submit | `/notes/client/1/quick/` | 200 | 1 issue(s) |
| Full note form | `/notes/client/1/new/` | 200 | 1 issue(s) |
| Notes timeline | `/notes/client/1/` | 200 | 1 issue(s) |
| Note detail | `/notes/1/` | 200 | None |
| Plan view (read-only) | `/plans/client/1/` | 200 | 1 issue(s) |
| Section create (403) | `/plans/client/1/sections/create/` | 403 | None |
| Events tab | `/events/client/1/` | 200 | 1 issue(s) |
| Event create form | `/events/client/1/create/` | 200 | 1 issue(s) |
| Alert create form | `/events/client/1/alerts/create/` | 200 | 1 issue(s) |
| Client analysis | `/reports/client/1/analysis/` | 200 | 1 issue(s) |
| Programs list | `/programs/` | 200 | 1 issue(s) |
| Client list (Housing only) | `/clients/` | 200 | 1 issue(s) |
| Direct access to Bob's profile (403) | `/clients/2/` | 403 | None |
| Access Jane's profile (own program) | `/clients/1/` | 200 | 1 issue(s) |
| Target history for Bob (403) | `/plans/targets/2/history/` | 403 | 1 issue(s) |
| Search for Bob (should find no results) | `/clients/search/?q=Bob` | 200 | 1 issue(s) |
| Client create form | `/clients/create/` | 200 | 1 issue(s) |
| View new client profile | `/clients/3/` | 200 | 1 issue(s) |
| Document intake session | `/notes/client/3/quick/` | 200 | 1 issue(s) |
| Notes timeline after intake | `/notes/client/3/` | 200 | 1 issue(s) |
| Search client list by note text | `/clients/?q=seemed+well` | 200 | 1 issue(s) |
| Dedicated search by note text | `/clients/search/?q=seemed+well` | 200 | 1 issue(s) |
| Search for other program's note content | `/clients/search/?q=vocational` | 200 | 1 issue(s) |
| Group detail (other program, 403) | `/groups/2/` | 403 | None |
| Milestone edit (other program, 403) | `/groups/milestone/1/edit/` | 403 | None |
| Own program group (200) | `/groups/1/` | 200 | 1 issue(s) |
| Session log (other program, 403) | `/groups/2/session/` | 403 | None |
| Target history (other program, 403) | `/plans/targets/2/history/` | 403 | 1 issue(s) |

### Admin (FR)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin dashboard | `/admin/settings/` | 200 | 1 issue(s) |
| Features | `/admin/settings/features/` | 200 | 1 issue(s) |
| Instance settings | `/admin/settings/instance/` | 200 | 1 issue(s) |
| Terminology | `/admin/settings/terminology/` | 200 | 1 issue(s) |
| User list | `/admin/users/` | 200 | 1 issue(s) |
| Metric library | `/plans/admin/metrics/` | 200 | 1 issue(s) |
| Programs list | `/programs/` | 200 | 1 issue(s) |
| Event types | `/events/admin/types/` | 200 | 1 issue(s) |
| Note templates | `/admin/settings/note-templates/` | 200 | 1 issue(s) |
| Custom fields | `/clients/admin/fields/` | 200 | 1 issue(s) |
| Registration links | `/admin/registration/` | 200 | 1 issue(s) |
| Audit log | `/admin/audit/` | 200 | 2 issue(s) |

### Front Desk (FR)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page (FR) | `/` | 200 | 1 issue(s) |
| Client detail (FR) | `/clients/1/` | 200 | 1 issue(s) |
| Programs list (FR) | `/programs/` | 200 | 1 issue(s) |
| Home page | `/` | 200 | 1 issue(s) |
| Client list | `/clients/` | 200 | 1 issue(s) |
| Client detail | `/clients/1/` | 200 | 1 issue(s) |
| Programs list | `/programs/` | 200 | 1 issue(s) |

### Front Desk

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page | `/` | 200 | 1 issue(s) |
| Client list | `/clients/` | 200 | 1 issue(s) |
| Search for client | `/clients/search/?q=Jane` | 200 | 1 issue(s) |
| Client detail | `/clients/1/` | 200 | 1 issue(s) |
| Custom fields display | `/clients/1/custom-fields/display/` | 200 | None |
| Custom fields edit | `/clients/1/custom-fields/edit/` | 200 | None |
| Consent display | `/clients/1/consent/display/` | 200 | None |
| Create client (403) | `/clients/create/` | 403 | None |
| Notes list (403) | `/notes/client/1/` | 403 | None |
| Plan section create (403) | `/plans/client/1/sections/create/` | 403 | None |
| Programs list | `/programs/` | 200 | 1 issue(s) |
| Search for unknown client | `/clients/search/?q=Maria` | 200 | 1 issue(s) |
| Can't create client (403) | `/clients/create/` | 403 | None |

### Program Manager

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page | `/` | 200 | 1 issue(s) |
| Client list | `/clients/` | 200 | 1 issue(s) |
| Client detail | `/clients/1/` | 200 | 1 issue(s) |
| Notes timeline | `/notes/client/1/` | 200 | 1 issue(s) |
| Quick note form | `/notes/client/1/quick/` | 200 | 1 issue(s) |
| Full note form | `/notes/client/1/new/` | 200 | 1 issue(s) |
| Plan view (editable) | `/plans/client/1/` | 200 | 1 issue(s) |
| Section create form | `/plans/client/1/sections/create/` | 200 | 1 issue(s) |
| Section create submit | `/plans/client/1/sections/create/` | 200 | 1 issue(s) |
| Target create form | `/plans/sections/1/targets/create/` | 200 | 1 issue(s) |
| Target create submit | `/plans/sections/1/targets/create/` | 200 | 1 issue(s) |
| Target metrics | `/plans/targets/1/metrics/` | 200 | None |
| Section status | `/plans/sections/1/status/` | 200 | None |
| Target status | `/plans/targets/1/status/` | 200 | None |
| Target history | `/plans/targets/1/history/` | 200 | None |
| Metrics export form | `/reports/export/` | 200 | 1 issue(s) |
| CMT export form | `/reports/cmt-export/` | 200 | 1 issue(s) |
| Events tab | `/events/client/1/` | 200 | 1 issue(s) |
| Event create form | `/events/client/1/create/` | 200 | 1 issue(s) |
| Client analysis | `/reports/client/1/analysis/` | 200 | 1 issue(s) |
| Review new client | `/clients/3/` | 200 | 1 issue(s) |
| Plan view (empty for new client) | `/plans/client/3/` | 200 | 1 issue(s) |
| Create plan section | `/plans/client/3/sections/create/` | 200 | 1 issue(s) |

### Executive

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Executive dashboard | `/clients/executive/` | 200 | 1 issue(s) |
| Client list redirect | `/clients/` | 200 | 1 issue(s) |
| Client detail redirect | `/clients/1/` | 200 | 1 issue(s) |
| Programs list | `/programs/` | 200 | 1 issue(s) |
| Notes redirect | `/notes/client/1/` | 200 | 1 issue(s) |

### Non-admin spot check

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin settings (403) | `/admin/settings/` | 403 | None |
| User list (403) | `/admin/users/` | 403 | None |

### Admin+PM

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Client detail | `/clients/1/` | 200 | 1 issue(s) |
| Notes timeline | `/notes/client/1/` | 200 | 1 issue(s) |
| Plan view | `/plans/client/1/` | 200 | 1 issue(s) |
| Admin settings | `/admin/settings/` | 200 | 1 issue(s) |
| User list | `/admin/users/` | 200 | 1 issue(s) |

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
| Direct Service | Target history blocked | `/plans/targets/2/history/` | 403 | None |
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

## Browser-Based Findings

_Tested with Playwright (headless Chromium) + axe-core._

### Colour Contrast

- **[CRITICAL]** `/clients/1/` — [light] Client detail: Contrast violation (serious) on `.quick-info-section > .quick-info > .quick-info-item > dt`
  _Fix any of the following:
  Element has insufficient color contrast of 4.26 (foreground color: #64748b, background color: #ecf4f4, font size: 8.4pt (11.25px), font weight: normal). Expected contrast r_

### Focus Management

- **[WARNING]** `/clients/3/` — Custom fields: Focus lost after switching to edit mode
  _Focus on: None_

- **[WARNING]** `/plans/client/7/` — Plan section: Focus lost after clicking Edit
  _Focus on: None_

### Responsive Layout

- **[WARNING]** `/plans/client/3/` — [mobile] Plan view: Horizontal overflow detected
  _scrollWidth=466, clientWidth=375 at 375x667_

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "KoNote2" is 77x38px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <button> "" is 39x13px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Home" is 55x38px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Participants" is 91x38px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Info" is 48x38px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Plan1" is 69x38px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Progress Note1" is 128x38px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Events2" is 83x38px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Analysis" is 72x38px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Edit" is 343x36px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "← Back to List" is 75x18px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Export PDF" is 343x36px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <a> "Export All Data" is 343x36px (min 44x44)

- **[INFO]** `/clients/5/` — [mobile] Client detail: Touch target too small — <button> "✎ Edit" is 70x28px (min 44x44)

- **[INFO]** `/clients/` — [mobile] Client list: Touch target too small — <a> "KoNote2" is 77x38px (min 44x44)

- **[INFO]** `/clients/` — [mobile] Client list: Touch target too small — <button> "" is 39x13px (min 44x44)

- **[INFO]** `/clients/` — [mobile] Client list: Touch target too small — <select> "All statuses" is 309x41px (min 44x44)

- **[INFO]** `/clients/` — [mobile] Client list: Touch target too small — <select> "All Programs" is 309x41px (min 44x44)

- **[INFO]** `/clients/` — [mobile] Client list: Touch target too small — <a> "Clear filters" is 94x36px (min 44x44)

- **[INFO]** `/clients/` — [mobile] Client list: Touch target too small — <a> "Jane Doe" is 62x20px (min 44x44)

## Recommendations

### Immediate (Critical)

1. Fix: [light] Client detail: Contrast violation (serious) on `.quick-info-section > .quick-info > .quick-info-item > dt` on `/clients/1/`

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
- 403 page has no links — user may be stuck (`/plans/targets/2/history/`)
- 403 page has no links — user may be stuck (`/plans/targets/2/history/`)
- Custom fields: Focus lost after switching to edit mode (`/clients/3/`)
- Plan section: Focus lost after clicking Edit (`/plans/client/7/`)
- [mobile] Plan view: Horizontal overflow detected (`/plans/client/3/`)

---

_Generated by `tests/ux_walkthrough/` — automated UX walkthrough_
