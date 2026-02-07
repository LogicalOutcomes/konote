# KoNote2 UX Walkthrough Report

**Generated:** 2026-02-06 18:45:14  
**Command:** `pytest tests/ux_walkthrough/ -v`

## Summary

| Metric | This Run | Previous |
|--------|----------|----------|
| Pages visited | 139 | 139 (same) |
| Critical issues | 0 |
| Warnings | 0 |
| Info items | 0 |

## Critical Issues

_No critical issues found._

## Warning Issues

_No warning issues found._

## Info Issues

_No info issues found._

## Known Limitations

- Colour contrast not tested (requires browser rendering)
- Focus management after HTMX swaps not tested
- Visual layout / responsive behaviour not tested

## Per-Role Walkthrough Results

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

### Direct Service

| Step | URL | Status | Issues |
|------|-----|--------|--------|
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

### Admin

| Step | URL | Status | Issues |
|------|-----|--------|--------|
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

## Recommendations

---

_Generated by `tests/ux_walkthrough/` — automated UX walkthrough_
