# Parallel Sprint Plan — Bug Fixes, Accessibility, Features

**Created:** 2026-03-02
**Goal:** Address as many open TODO.md items as possible using parallel agents with worktrees to avoid file conflicts.

## How This Works

Each **track** runs in its own git worktree (isolated copy of the repo) on its own branch. Tracks within the same wave have no file conflicts and can run simultaneously. After a wave's PRs merge, the next wave starts.

**Wave 1** runs 7 tracks in parallel (17 tasks).
**Wave 2** runs 1 large track after Wave 1 merges (9 tasks).
**Session 2** is a separate focused session for reports/funder features (3–4 tasks).
**Session 3** is demo mode safeguards (5 tasks).

**Total: 34 tasks.**

---

## Session 1, Wave 1 — Parallel Bug Fix Sprint

All tracks run simultaneously. Each gets its own worktree branch off `develop`.

### Track A: QA Scenarios Repo (3 tasks)
**Branch:** `fix/qa-r8b-scenarios`
**Repo:** `konote-qa-scenarios` (completely separate — zero conflict risk)
**Files:** `scenarios/periodic/SCN-035-funder-reporting.yaml`, test runner code

| ID | Task | Fix |
|---|---|---|
| QA-R8b-YAML1 | Fix SCN-035 YAML URL | Change `/reports/funder/` → `/reports/funder-report/` in scenario YAML |
| QA-R8b-TEST1 | Fix test runner interactive step execution | Clicks, form fills, HTMX not working — investigate conftest.py and state_capture.py |
| QA-R8b-TEST2 | Fix URL placeholder substitution | `{group_id}`, `{client_id}` appear literally — fix in conftest.py URL builder |

### Track B: Plans App — REQ-G4 (1 task)
**Branch:** `feat/g4-metric-auto-update`
**Files:** `apps/plans/models.py`, `apps/plans/signals.py` (new), `apps/plans/views.py`, `tests/test_plans.py`

| ID | Task | Fix |
|---|---|---|
| REQ-G4 | Auto-update progress metrics when goal status changes | Add post_save signal on PlanTarget status change → recalculate related MetricValue records. When a goal is marked achieved/abandoned, update linked progress metrics. Write tests. |

**Context:** PlanTarget has status field. PlanTargetMetric links targets to MetricDefinitions. MetricValue stores recorded values. The signal should fire when target.status changes and create/update the corresponding MetricValue.

### Track C: Client App Bundle (7 tasks)
**Branch:** `fix/client-app-bundle`
**Files:** `apps/clients/views.py`, `apps/clients/forms.py`, `apps/clients/helpers.py`, `apps/clients/matching.py`, `templates/clients/*.html`, `static/js/app.js` (tab navigation only)

Run these sequentially within the track (they share `apps/clients/views.py`):

| ID | Task | Fix |
|---|---|---|
| QA-R8-UX3 | Newly created client not searchable by other users | Check cache invalidation after client create. Encrypted search loads clients into Python — verify program-scoped queryset includes newly created records for all users with access. |
| QA-R8-A11Y4 | Create form Tab order — Last Name before First Name | Fix field order in `ClientFileForm.Meta.fields` or `field_order`. Remove any `tabindex` overrides in `templates/clients/form.html`. |
| QA-R8-UX5 | Missing validation error + success confirmation on create | Add `messages.success()` in `client_create` view. Ensure form errors render via `_form_errors.html` include. |
| QA-R8-UX6 | Mobile edit navigates to wrong form | Check edit button href in `templates/clients/detail.html`. Verify it points to `{% url 'clients:client_edit' client.id %}` not the create URL. |
| QA-R8-UX13 | Accent stripping — "Benoît" → "Benoit" | Fix `_strip_accents()` in views.py — it's used for search but should not affect display. Check that list template displays the original name, not the stripped version. |
| QA-R8-A11Y5 | Excessive Tab presses to reach search results | Add skip link or reduce focusable elements in search filter controls. Check `templates/clients/search.html`. |
| QA-R8-A11Y8 | Profile tabs arrow key — ArrowRight opens Actions dropdown | Add ARIA tab pattern JS to `static/js/app.js`: `role="tablist"`, `role="tab"`, ArrowLeft/Right to switch tabs. Check `templates/clients/detail.html` tab markup. |

### Track D: Events App (1 task)
**Branch:** `fix/calendar-feed-url`
**Files:** `apps/events/views.py`, `apps/events/urls.py`, `apps/events/models.py`, `templates/events/calendar_feed_settings.html`

| ID | Task | Fix |
|---|---|---|
| QA-R8-UX9 | Calendar feed URL generation failing silently | Add error handling and user feedback to `calendar_feed_settings()` view. Check token/UUID generation in model. |

### Track E: Auth/Admin — User Management (1 task)
**Branch:** `fix/pm-user-management`
**Files:** `apps/auth_app/admin_urls.py`, `apps/auth_app/admin_views.py`, `templates/auth_app/user_list.html`

| ID | Task | Fix |
|---|---|---|
| QA-R8-UX12 | PM user management path missing — `/manage/users/` not linked | Check if program managers have permission to see user list. If yes, add nav link. If no, decide whether PMs should have this access (may need to add to Flagged). |

### Track F: Notes App (2 tasks)
**Branch:** `fix/notes-app-bundle`
**Files:** `apps/notes/views.py`, `apps/notes/urls.py`, `templates/notes/*.html`

| ID | Task | Fix |
|---|---|---|
| QA-R8-UX4 | Quick note entry point unreachable — selector mismatch | Check `_quick_note_inline_buttons.html` and `templates/clients/detail.html` for broken selector or missing include. Fix the entry point link/button. |
| AXE-HEADING1 | Missing h1 on notes-detail page | Add `<h1>` to `templates/notes/note_detail_page.html`. |

### Track G: Verification Tasks (3 tasks)
**Branch:** `fix/verification-checks`
**Files:** Read-only investigation — may result in no code changes, or small fixes

| ID | Task | Fix |
|---|---|---|
| QA-R8-LANG1 | Verify language middleware — check if FG-S-2 fix regressed | Test French language switching. If working, close. If broken, fix in `konote/middleware.py`. |
| QA-R8-UX7 | Verify offline fallback — check if fix-log entry 9 regressed | Test offline/error states. If working, close. If broken, fix in `static/js/app.js` service worker or error handler. |
| QA-R8-VERIFY1 | Verify data export routes against recent SEC3 work | Check if `/participants/<id>/export/` routes exist from the SEC3 export work. If they do, close. If gaps remain, document what's needed. |

---

## Session 1, Wave 2 — Accessibility Sweep

Runs after Wave 1 PRs merge into develop. Single track because these tasks share `templates/base.html` and `static/css/`.

### Track H: Base Template + CSS + Page Accessibility (9 tasks)
**Branch:** `fix/accessibility-sweep`
**Files:** `templates/base.html`, `templates/includes/`, `static/css/main.css`, `static/css/theme.css`, various page templates

Run sequentially — many touch the same files:

| ID | Task | Fix |
|---|---|---|
| AXE-ARIA1 | Fix ARIA role violations (59 pages, 512 nodes) | Likely a shared component pattern. Check `base.html` nav structure, menu items, interactive elements. Add missing `role` attributes. |
| AXE-LANDMARK1 | Fix duplicate landmark regions (60 pages, 352 nodes) | Check `base.html` for multiple `<nav>`, `<main>`, `<footer>`. Add `aria-label` to distinguish multiple navs if needed. |
| AXE-TEMPLATE1 | Fix 4 pages missing base template wrapper | Ensure export-confirmation, plan-section-edit, public-survey-link, public-unsubscribe extend `base.html`. |
| AXE-CONTRAST1 | Fix colour contrast (11 pages, 257 nodes) | Audit CSS colour values against WCAG 4.5:1 ratio. Adjust in `main.css` and `theme.css`. Key pages: client-detail, dashboard-staff, plan-view, notes-list, events-list. |
| AXE-TABLE1 | Fix empty table headers (4 admin pages) | Add text or `aria-label` to `<th>` elements in event-types, terminology, user-list, programs-list templates. |
| QA-R8-A11Y6 | Fix checkbox touch target below 24px | Add `min-height: 44px; min-width: 44px` or padding to checkbox inputs in CSS. |
| QA-R8-A11Y7 | Accessibility polish bundle | Language toggle confirmation, breadcrumb targets, field visibility, icon labels. Multiple small fixes across templates. |
| QA-R8-I18N1 | Fix French navigation — create participant broken | Ensure nav links use `{% url %}` tags not hardcoded paths. Check French translations for "Create Participant" in `.po` file. |
| QA-R8-UX10 | Fix form resubmission → help page | Investigate which form(s) redirect to help page on POST. Fix redirect target in the relevant view. |

---

## Session 2 — Reports & Funder Features (separate session)

These tasks all touch `apps/reports/` and are interconnected. Run as a focused session.

### Track: Reports App
**Branch:** `feat/funder-report-approval`
**Files:** `apps/reports/models.py`, `apps/reports/views.py`, `apps/reports/urls.py`, `apps/reports/forms.py`, `templates/reports/*.html`, `apps/clients/dashboard_views.py`

| ID | Task | Fix |
|---|---|---|
| RPT-APPROVE1 | Partner report approval workflow (RP2/RP3) | New models (ReportApproval), views (quality review, preview, approve), templates. Read `tasks/funder-report-approval.md` and `docs/plans/2026-02-20-funder-report-approval-design.md` first. |
| QA-R8-UX11 | Fix `/reports/funder/` returning 404 | Check `apps/reports/urls.py` — actual route is `/reports/funder-report/`. Either add redirect or fix references. |
| QA-R8-UX8 | Add date presets + PDF export to executive dashboard | Date picker with presets in `apps/clients/dashboard_views.py`. PDF export endpoint in `apps/reports/`. Touches both apps. |
| DOC-RP4 | Funder reporting dashboard design doc | Write after Prosper Canada provides funder reporting templates. |

**Note on RP4:** The funder reporting templates from Prosper Canada will determine the scope. Once received, write `cross-agency-reporting-design.md`, then build SCALE-ROLLUP1. This may be a third session depending on timing.

---

## Session 3 — Demo Mode Safeguards (separate session)

These tasks touch login templates, base template (banner), middleware, and report queries. Run after accessibility sweep merges to avoid base.html conflicts.

### Track: Demo Mode
**Branch:** `feat/demo-mode-safeguards`
**Files:** `templates/auth/login.html`, `templates/base.html`, `konote/middleware.py`, `apps/admin_settings/`, report views

| ID | Task | Fix |
|---|---|---|
| DEMO-ADMIN-RO1 | Restrict demo-admin to view-only for agency settings | Check permissions in admin settings views — demo users can view but not POST. |
| DEMO-BANNER1 | Persistent training-mode banner | Amber banner on every page for demo sessions. Already partially exists in `base.html` lines 59-63 — may need enhancement. |
| DEMO-LOGIN-UX1 | Visually separate demo buttons from real login | Restyle demo login section in `templates/auth/login.html` with distinct colour/section. |
| DEMO-AUDIT1 | Audit demo logins | Log demo login events but exclude from PHIPA audit pipeline. |
| DEMO-EXCLUDE1 | Verify reports exclude is_demo=True records | Audit every report query, aggregate count, CSV/PDF export for demo data leakage. |

---

## Conflict Matrix

| Track | Key files | Conflicts with |
|---|---|---|
| A (QA scenarios) | qa-scenarios repo | Nothing (separate repo) |
| B (Plans) | apps/plans/ | Nothing |
| C (Clients) | apps/clients/, templates/clients/ | D if dashboard is in clients (resolved: UX8 → Session 2) |
| D (Events) | apps/events/ | Nothing |
| E (Auth) | apps/auth_app/ | Nothing |
| F (Notes) | apps/notes/, templates/notes/ | Nothing |
| G (Verification) | Read-only | Nothing |
| H (Accessibility) | templates/base.html, static/css/ | Session 3 (demo banner in base.html) |
| Session 2 (Reports) | apps/reports/, apps/clients/dashboard_views.py | Track C if run simultaneously (resolved: different waves) |
| Session 3 (Demo) | templates/base.html, middleware | Track H (resolved: runs after H merges) |

---

## Checklist Before Starting

- [ ] Pull latest develop: `git pull origin develop`
- [ ] Verify no 🔨 IN PROGRESS items in TODO.md that another session is working on
- [ ] Merge the `chore/todo-restructure-p0` PR first (TODO.md vocabulary updates)
- [ ] Have the parallel sprint prompt ready (see below)
