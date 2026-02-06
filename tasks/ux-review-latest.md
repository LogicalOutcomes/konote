# KoNote2 UX Walkthrough Report

**Generated:** 2026-02-06 15:54:13  
**Command:** `pytest tests/ux_walkthrough/ -v`

## Summary

| Metric | This Run | Previous |
|--------|----------|----------|
| Pages visited | 37 | 133 (down 96) |
| Critical issues | 18 | 18 (same) |
| Warnings | 0 |
| Info items | 0 | 2 (down 2) |

## Critical Issues

- **[Front Desk (FR)] Home page** `/`
  Forbidden content found: 'Dashboard'

- **[Front Desk (FR)] Home page** `/`
  Forbidden content found: 'Filters'

- **[Front Desk (FR)] Home page** `/`
  Forbidden content found: 'Active'

- **[Front Desk (FR)] Home page** `/`
  Forbidden content found: 'Inactive'

- **[Front Desk (FR)] Home page** `/`
  Forbidden content found: 'Status'

- **[Front Desk (FR)] Home page** `/`
  Forbidden content found: 'Privacy'

- **[Front Desk (FR)] Home page** `/`
  Forbidden content found: 'Help'

- **[Front Desk (FR)] Client list** `/clients/`
  Forbidden content found: 'Filters'

- **[Front Desk (FR)] Client list** `/clients/`
  Forbidden content found: 'Active'

- **[Front Desk (FR)] Client list** `/clients/`
  Forbidden content found: 'Inactive'

- **[Front Desk (FR)] Client list** `/clients/`
  Forbidden content found: 'Status'

- **[Front Desk (FR)] Client list** `/clients/`
  Forbidden content found: 'Privacy'

- **[Front Desk (FR)] Client list** `/clients/`
  Forbidden content found: 'Help'

- **[Front Desk (FR)] Client detail** `/clients/1/`
  Forbidden content found: 'Active'

- **[Front Desk (FR)] Client detail** `/clients/1/`
  Forbidden content found: 'Privacy'

- **[Front Desk (FR)] Client detail** `/clients/1/`
  Forbidden content found: 'Help'

- **[Front Desk (FR)] Programs list** `/programs/`
  Forbidden content found: 'Privacy'

- **[Front Desk (FR)] Programs list** `/programs/`
  Forbidden content found: 'Help'

## Warning Issues

_No warning issues found._

## Info Issues

_No info issues found._

## Known Limitations

- Colour contrast not tested (requires browser rendering)
- Focus management after HTMX swaps not tested
- Visual layout / responsive behaviour not tested

## Per-Role Walkthrough Results

### Admin (no program)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Admin blocked from client detail (403) | `/clients/1/` | 403 | None |

### Direct Service

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Client list (Housing only) | `/clients/` | 200 | None |
| Direct access to Bob's profile (403) | `/clients/2/` | 403 | None |
| Access Jane's profile (own program) | `/clients/1/` | 200 | None |
| Search for Bob (should find no results) | `/clients/search/?q=Bob` | 200 | None |
| Client create form | `/clients/create/` | 200 | None |
| View new client profile | `/clients/3/` | 200 | None |
| Document intake session | `/notes/client/3/quick/` | 200 | None |
| Notes timeline after intake | `/notes/client/3/` | 200 | None |

### Front Desk

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Search for unknown client | `/clients/search/?q=Maria` | 200 | None |
| Can't create client (403) | `/clients/create/` | 403 | None |

### Program Manager

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Review new client | `/clients/3/` | 200 | None |
| Plan view (empty for new client) | `/plans/client/3/` | 200 | None |
| Create plan section | `/plans/client/3/sections/create/` | 200 | None |

### Front Desk (FR)

| Step | URL | Status | Issues |
|------|-----|--------|--------|
| Home page | `/` | 200 | 7 issue(s) |
| Client list | `/clients/` | 200 | 6 issue(s) |
| Client detail | `/clients/1/` | 200 | 3 issue(s) |
| Programs list | `/programs/` | 200 | 2 issue(s) |

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

## Recommendations

### Immediate (Critical)

1. Fix: Forbidden content found: 'Dashboard' on `/`
1. Fix: Forbidden content found: 'Filters' on `/`
1. Fix: Forbidden content found: 'Active' on `/`
1. Fix: Forbidden content found: 'Inactive' on `/`
1. Fix: Forbidden content found: 'Status' on `/`
1. Fix: Forbidden content found: 'Privacy' on `/`
1. Fix: Forbidden content found: 'Help' on `/`
1. Fix: Forbidden content found: 'Filters' on `/clients/`
1. Fix: Forbidden content found: 'Active' on `/clients/`
1. Fix: Forbidden content found: 'Inactive' on `/clients/`
1. Fix: Forbidden content found: 'Status' on `/clients/`
1. Fix: Forbidden content found: 'Privacy' on `/clients/`
1. Fix: Forbidden content found: 'Help' on `/clients/`
1. Fix: Forbidden content found: 'Active' on `/clients/1/`
1. Fix: Forbidden content found: 'Privacy' on `/clients/1/`
1. Fix: Forbidden content found: 'Help' on `/clients/1/`
1. Fix: Forbidden content found: 'Privacy' on `/programs/`
1. Fix: Forbidden content found: 'Help' on `/programs/`

---

_Generated by `tests/ux_walkthrough/` — automated UX walkthrough_
