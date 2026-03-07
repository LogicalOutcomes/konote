# Parallel Sprint Prompt — Session 1

Paste this into a new Claude Code session in the KoNote repo.

---

## Prompt

Read `tasks/parallel-sprint-plan.md` for the full plan. You are executing **Session 1: Wave 1** — a parallel bug fix sprint across 7 tracks, each in its own worktree.

**Before starting:**
1. `git pull origin develop`
2. Read `TODO.md` — mark all tasks you're about to work on as 🔨 IN PROGRESS
3. Commit the TODO.md update to develop (this is the one exception to "never commit to develop" — it's just marking work in progress)

**Wave 1 — launch all 7 tracks as parallel agents, each in its own worktree:**

### Track A: QA Scenarios (konote-qa-scenarios repo)
Branch: `fix/qa-r8b-scenarios` in `/c/Users/gilli/GitHub/konote-qa-scenarios`
- QA-R8b-YAML1: Fix SCN-035 YAML — change `/reports/funder/` → `/reports/funder-report/` in `scenarios/periodic/SCN-035-funder-reporting.yaml`
- QA-R8b-TEST1: Fix test runner interactive step execution — clicks and form fills not working, duplicate screenshots. Investigate `tests/scenario_eval/conftest.py` and `state_capture.py`.
- QA-R8b-TEST2: Fix URL placeholder substitution — `{group_id}`, `{client_id}` appear literally in URLs (affects SCN-075, SCN-076, SCN-084). Fix in conftest.py URL builder.
Commit each fix separately. Push and create PR → main.

### Track B: Plans App — REQ-G4
Branch: `feat/g4-metric-auto-update` off develop
Files: `apps/plans/`
- REQ-G4: Add a Django post_save signal on PlanTarget. When a target's status changes (e.g., to achieved or abandoned), auto-update the linked MetricValue records. Read `apps/plans/models.py` first to understand PlanTarget → PlanTargetMetric → MetricValue relationships. Create `apps/plans/signals.py` if it doesn't exist. Register in `apps/plans/apps.py`. Add tests in `tests/test_plans.py`. Run `pytest tests/test_plans.py` to verify.
Push and create PR → develop.

### Track C: Client App Bundle
Branch: `fix/client-app-bundle` off develop
Files: `apps/clients/`, `templates/clients/`
Do these sequentially, committing after each:
1. **QA-R8-UX3**: Fix newly created client not searchable by other users. Check `apps/clients/views.py` client search — likely a cache or queryset scoping issue. The encrypted search loads clients into Python — verify the queryset includes newly created records for all users with program access.
2. **QA-R8-A11Y4**: Fix create form Tab order — Last Name gets focus before First Name. Fix `field_order` in `ClientFileForm` or the field order in `templates/clients/form.html`. WCAG 1.3.2.
3. **QA-R8-UX5**: Add validation error display + success confirmation on participant create. Add `messages.success()` to `client_create` view. Ensure form errors render.
4. **QA-R8-UX6**: Fix mobile edit navigating to wrong form. Check edit button href in `templates/clients/detail.html` — should use `{% url 'clients:client_edit' %}`.
5. **QA-R8-UX13**: Fix accent stripping — "Benoît" appears as "Benoit" in client list. The `_strip_accents()` function in views.py is for search, not display. Ensure the list template shows the original encrypted name, not the stripped version.
6. **QA-R8-A11Y5**: Fix excessive Tab presses to reach search results. Add skip link or reduce focusable elements in filter controls. Check `templates/clients/search.html`.
7. **QA-R8-A11Y8**: Fix profile tabs arrow key nav — ArrowRight opens Actions dropdown instead of next tab. Add ARIA tablist pattern: `role="tablist"` on container, `role="tab"` on each tab, ArrowLeft/Right JS in `static/js/app.js`.
Run `pytest tests/test_clients.py` after all fixes. Push and create PR → develop.

### Track D: Events App
Branch: `fix/calendar-feed-url` off develop
Files: `apps/events/`
- QA-R8-UX9: Fix calendar feed URL generation failing silently. Check `calendar_feed_settings()` view in `apps/events/views.py`. Add error handling and user feedback. Check token/UUID generation in the model.
Run related tests. Push and create PR → develop.

### Track E: Auth/Admin
Branch: `fix/pm-user-management` off develop
Files: `apps/auth_app/`
- QA-R8-UX12: PM user management path missing — `/manage/users/` not linked. Check `apps/auth_app/admin_urls.py` and `admin_views.py`. Check if program managers have `permission.admin_users`. If yes, add nav link. If the permission doesn't exist, create it. Check `templates/base.html` admin navigation section — but do NOT modify base.html structure, only add a link if the permission check passes.
Push and create PR → develop.

### Track F: Notes App
Branch: `fix/notes-app-bundle` off develop
Files: `apps/notes/`, `templates/notes/`
1. **QA-R8-UX4**: Fix quick note entry point unreachable — selector mismatch on client profile. Check `templates/notes/_quick_note_inline_buttons.html` and how it's included in `templates/clients/detail.html`. Fix the broken selector or missing include.
2. **AXE-HEADING1**: Fix missing h1 on notes-detail page. Add `<h1>` to `templates/notes/note_detail_page.html`.
Push and create PR → develop.

### Track G: Verification Tasks
Branch: `fix/verification-checks` off develop
Files: Various — read-only investigation, small fixes if needed
1. **QA-R8-LANG1**: Test French language switching. Run the app or check `tests/test_language_switching.py`. If the fix from FG-S-2 still works, mark as verified. If broken, fix in `konote/middleware.py`.
2. **QA-R8-UX7**: Test offline/error state handling. Check `static/js/app.js` for the `htmx:responseError` handler. If working, mark as verified.
3. **QA-R8-VERIFY1**: Check if `/participants/<id>/export/` routes exist from the SEC3 export work (PR that added `export_agency_data`). If routes exist and work, mark as verified. Document any gaps.
Push and create PR → develop (even if only verification notes, add to a VERIFICATION.md or update fix-log).

---

**After all 7 tracks complete:**
1. Review each PR
2. Merge all PRs into develop (use `--merge`, never squash)
3. Pull develop: `git pull origin develop`
4. Update TODO.md — mark completed tasks as `[x]` with date, move to Recently Done
5. Proceed to Wave 2 (accessibility sweep) — this is Track H in the plan, a single sequential track

**Wave 2 — Track H: Accessibility Sweep**
Create branch `fix/accessibility-sweep` off develop. Run these sequentially:
- AXE-ARIA1: Fix ARIA role violations in base template and shared components
- AXE-LANDMARK1: Fix duplicate landmark regions in base template
- AXE-TEMPLATE1: Fix 4 pages missing base template wrapper (export-confirmation, plan-section-edit, public-survey-link, public-unsubscribe)
- AXE-CONTRAST1: Fix colour contrast failures in CSS (11 pages)
- AXE-TABLE1: Fix empty table headers on 4 admin pages
- QA-R8-A11Y6: Fix checkbox touch target size below WCAG 2.5.8 minimum
- QA-R8-A11Y7: Accessibility polish bundle (language toggle, breadcrumbs, field visibility, icon labels)
- QA-R8-I18N1: Fix French navigation — ensure nav links use `{% url %}` tags not hardcoded paths
- QA-R8-UX10: Fix form resubmission navigating to help page — investigate which form, fix redirect

Push and create PR → develop.

---

## Session 2 Prompt (Reports & Funder Features — run separately)

Read `tasks/parallel-sprint-plan.md` Session 2 section. You are building the partner report approval workflow and fixing related report issues.

Branch: `feat/funder-report-approval` off develop.

**Before coding, read these design docs:**
- `tasks/funder-report-approval.md`
- `docs/plans/2026-02-20-funder-report-approval-design.md`

Tasks (do sequentially — all in `apps/reports/`):
1. **QA-R8-UX11**: Fix `/reports/funder/` returning 404. The actual URL is `/reports/funder-report/`. Either add a redirect from the old URL or update references.
2. **RPT-APPROVE1**: Build partner report approval workflow — new ReportApproval model, quality review view, preview + annotation view, approve + publish view. Follow the design doc. This is RP2/RP3 from the requirements analysis.
3. **QA-R8-UX8**: Add date presets (Last 30/90/365 days, This year, Custom) and PDF export button to executive dashboard. Dashboard views are in `apps/clients/dashboard_views.py`, PDF export goes in `apps/reports/`.

Run `pytest tests/test_reports.py` after each task. Push and create PR → develop.

If Prosper Canada has provided their funder reporting templates by now, also write `cross-agency-reporting-design.md` (DOC-RP4) to begin scoping the RP4 funder dashboard.

---

## Session 3 Prompt (Demo Mode Safeguards — run after Session 1 Wave 2 merges)

Read `tasks/parallel-sprint-plan.md` Session 3 section. You are implementing demo mode safeguards from the expert panel review.

Branch: `feat/demo-mode-safeguards` off develop.

**Read first:** `tasks/design-rationale/ovhcloud-deployment.md` (Demo Mode Safeguards section).

Tasks (do sequentially):
1. **DEMO-ADMIN-RO1**: Restrict demo-admin to view-only for agency settings. Demo users with admin role can view but not modify terminology, feature toggles, or program config. Add permission check in admin settings views.
2. **DEMO-BANNER1**: Enhance persistent training-mode banner. Check `templates/base.html` lines 59-63 for existing demo banner. Make it amber, persistent on every page: "Training Mode — changes here do not affect real participant records."
3. **DEMO-LOGIN-UX1**: Visually separate demo buttons from real login form. In `templates/auth/login.html`, create a distinct "Training Accounts" section with different styling.
4. **DEMO-AUDIT1**: Log demo login events (who, when, which demo user) for operational awareness. Exclude from PHIPA audit pipeline. Add to `apps/audit/`.
5. **DEMO-EXCLUDE1**: Audit every report query, aggregate count, CSV/PDF export, and funder report for demo data leakage. Verify all filter on `is_demo=True`. Fix any that don't.

Run full test suite when done. Push and create PR → develop.
