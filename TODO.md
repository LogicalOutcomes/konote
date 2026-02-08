# Project Tasks

## Flagged

- [ ] Decide product name — should web version be called "KoNote" (not "KoNote2"). See `tasks/naming-versioning.md` (NAME1)
- [ ] Update konote-website git remote URL — repo was renamed to `konote2-website` but local remote still points to old `konote2` name (NAME2)
_Nothing flagged._

## Active Work

### Code Review Remaining (from 2026-02-07 review — see `tasks/code-review-2026-02-07.md`)

_All review items complete. 74 new tests added. Pre-existing test failures fixed._

### Scenario Evaluation Fixes (updated 2026-02-08 — see `qa/2026-02-08-improvement-tickets.md`)

_All 2026-02-08 evaluation items fixed. Re-run scenarios to verify._

**Fixed (2026-02-08):**
- [x] Skip-to-content link — improved CSS, added `clip-path` for robustness — 2026-02-08 (BLOCKER-1)
- [x] Focus after login — JS auto-focuses `<main>` on page load — 2026-02-08 (BLOCKER-2)
- [x] Executive redirect — `_login_redirect()` sends executives to aggregate dashboard — 2026-02-08 (BUG-5)
- [x] Language preference — moved middleware after auth, overrides cookie with user profile — 2026-02-08 (BUG-4)
- [x] Offline banner — `role="alert"` banner with "Try again" button — 2026-02-08 (BUG-6)
- [x] Audit log "Auth" → "Account", filter grid widened — 2026-02-08 (BUG-3b)
- [x] Settings cards — all 6 now show summary stats — 2026-02-08 (IMPROVE-1b)

**Fixed (confirmed by 2026-02-08 eval):**
- [x] Search "no results" shows correct empty state — 2026-02-07 (BUG-1)
- [x] Create buttons hidden for roles without permission — 2026-02-07 (BUG-2)
- [x] Audit log badges show "Created"/"Logged in", IP hidden behind toggle — 2026-02-07 (BUG-3)
- [x] Pre-select program when user has only one — 2026-02-07 (IMPROVE-2)
- [x] 403 page warmer language — 2026-02-07 (IMPROVE-3)
- [x] Dashboard "last updated" timestamp — 2026-02-07 (IMPROVE-4)
- [x] 4 of 6 settings cards now show summary stats — 2026-02-07 (IMPROVE-1)

### Pre-Launch Checklist

The core app is feature-complete. These tasks prepare for production use.

- [ ] Verify email is configured — needed for export notifications, erasure alerts, and password resets (OPS3)
- [ ] Test backup restore from a real database dump (OPS4)

### Occasional Tasks

- [ ] Run UX walkthrough — `pytest tests/ux_walkthrough/ -v`, review report at `tasks/ux-review-latest.md` (UX-WALK1)
- [ ] French translation review — have a French speaker spot-check AI translations, especially new strings. Run `python manage.py check_translations` to see coverage stats (I18N-REV1)
- [ ] Redeploy to Railway — push to `main`, Railway auto-deploys. See `docs/deploy-railway.md` (OPS-RAIL1)
- [ ] Redeploy to FullHost — push to `main`, then trigger redeploy via API or dashboard. See `docs/deploy-fullhost.md` (OPS-FH1)
- [ ] Code review round — open Claude Code in VS Code, say "review the codebase for code quality, security, and consistency issues" — see `tasks/code-review-process.md` (REV1)
- [ ] Scenario QA evaluation — persona-based satisfaction scoring against a live test server. Slow (~60s), run sparingly after major UX changes. Run `/run-scenario-server` in this repo to capture screenshots and page state (no API key needed), then open the `konote-qa-scenarios` repo in a separate VS Code window and run `/run-scenarios` there for Claude to evaluate the results. See `tasks/scenario-eval-howto.md` (QA-SCEN1)

## Coming Up

### Export Monitoring

Weekly accountability reports for admins. Requires working email configuration (OPS3).

- [ ] Create weekly export summary email command (EXP2u)
- [ ] Document cron/scheduled task setup in runbook (EXP2w)

### QA Infrastructure (Phase 3) — from konote-qa-scenarios

Tasks from the QA holdout repo that require code changes in this repo. Scenario data and persona definitions stay in `konote-qa-scenarios`.

- [x] Automate objective scoring dimensions — axe-core for accessibility, action count for efficiency, doc lang for language. Objective scores override LLM for these 3 dimensions — 2026-02-08 (QA-T10)
- [x] CI/CD gate — GitHub Actions workflow runs scenarios on push to main, `qa_gate.py` fails build on BLOCKER scores — 2026-02-08 (QA-T11)
- [x] Track satisfaction gap over time — `track_satisfaction.py` appends to history JSON, `chart_satisfaction.py` generates trend table, target < 1.0 gap — 2026-02-08 (QA-T12)
- [x] Bidirectional ticket status — GitHub Actions workflow parses `QA:` in commit messages, syncs issues to konote-qa-scenarios via `gh` CLI — 2026-02-08 (QA-T14)

### QA Scenario Runner Update — Full Coverage (see `tasks/qa-scenario-runner-update-plan.md`)

_All scenario runner tasks complete._

**Test Data (scenario_runner.py `_create_test_data`):**
- [x] Add DS1c test user (`staff_adhd`, Casey with ADHD) for SCN-058 — 2026-02-08 (QA-DATA1)
- [x] Add DS4 test user (`staff_voice`, Riley Chen) for SCN-059 — 2026-02-08 (QA-DATA2)
- [x] Add PM1 test user (`program_mgr`, Morgan Tremblay, cross-program) for SCN-035, SCN-042, SCN-070 — 2026-02-08 (QA-DATA3)
- [x] Add E2 test user (`admin2`, Kwame Asante) for SCN-030 — 2026-02-08 (QA-DATA4)
- [x] Add test clients: Benoit Tremblay, Sofia Garcia, Priya Sharma, Li Wei, Fatima Hassan, Derek Williams — 2026-02-08 (QA-DATA5)

**New Action Types (scenario_runner.py `_execute_actions`):**
- [x] `voice_command` — Dragon "Click [text]" to click-by-text, "Go to [field]" to focus-by-label — 2026-02-08 (QA-ACT1)
- [x] `dictate` — Dragon dictation to `keyboard.type()` — 2026-02-08 (QA-ACT2)
- [x] `intercept_network` — `page.route()` to mock error responses — 2026-02-08 (QA-ACT3)
- [x] `close_tab` / `open_new_tab` — tab management for shared-device scenarios — 2026-02-08 (QA-ACT4)
- [x] `go_back` + `screenshot` — page.go_back() alias and explicit named capture — 2026-02-08 (QA-ACT5)

**New Test Classes (test_scenario_eval.py):**
- [x] Add CAL-004 and CAL-005 to TestCalibrationScenarios — 2026-02-08 (QA-TEST1)
- [x] Add TestDailyScenarios: SCN-015, SCN-020, SCN-025 — 2026-02-08 (QA-TEST2)
- [x] Add TestPeriodicScenarios: SCN-030, SCN-035 — 2026-02-08 (QA-TEST3)
- [x] Add TestCrossRoleScenarios: SCN-040, SCN-042 — 2026-02-08 (QA-TEST4)
- [x] Add TestEdgeCaseScenarios: SCN-045, SCN-046, SCN-049, SCN-070 — 2026-02-08 (QA-TEST5)
- [x] Add TestAccessibilityMicro: SCN-051 through SCN-059, SCN-061, SCN-062 — 2026-02-08 (QA-TEST6)
- [x] Add DITL-DS1 and DITL-R1 to TestDayInTheLife — 2026-02-08 (QA-TEST7)

**LLM Evaluator (llm_evaluator.py):**
- [x] Include `cognitive_load_checks` in prompt when present — 2026-02-08 (QA-EVAL1)
- [x] Include `mechanical_checks` in prompt when present — 2026-02-08 (QA-EVAL2)
- [x] Include `task_completion_criteria` in prompt when present — 2026-02-08 (QA-EVAL3)

**Inter-Rater Reliability:**
- [x] CAL-006 inter-rater reliability automation — runs CAL-001 to CAL-005 with variant configs, computes ICC(2,1) and agreement metrics — 2026-02-08 (QA-IRR1)

## Roadmap — Future Extensions

### Phase G: Agency Content Translation

Build when agencies have custom programs/metrics they need in multiple languages. See `tasks/multilingual-strategy.md`.

**G.1: Translation Infrastructure**
- [ ] Create TranslatableMixin with `translations` JSONField (I18N10)
- [ ] Add mixin to Program, MetricDefinition, PlanTemplate (I18N11)
- [ ] Create Settings → Translations admin page (I18N12)
- [ ] Update templates to display translated content (I18N13)

**G.2: AI Translation Integration**
- [ ] Create Settings → Integrations page for API keys (I18N14)
- [ ] Add "Suggest translation" button with AI (I18N15)

**G.3: Self-Service Languages**
- [ ] Create Settings → Languages management page (I18N16)
- [ ] Extend translation command for any target language (I18N17)

### Bulk Import

Build after secure export is stable. See `tasks/secure-export-import-plan.md` for design.

- [ ] Create ImportBatch model for tracking (IMP1a)
- [ ] Add import_batch FK to ClientFile model (IMP1b)
- [ ] Create CSV upload form with validation (IMP1c)
- [ ] Implement formula injection sanitisation (IMP1d)
- [ ] Implement duplicate detection (IMP1e)
- [ ] Create preview page showing what will be created (IMP1f)
- [ ] Implement batch import with transaction wrapping (IMP1g)
- [ ] Create rollback functionality — creations only, not updates (IMP1h)
- [ ] Add audit logging for imports (IMP1i)
- [ ] Create import history page for admins (IMP1j)
- [ ] Document import validation rules (DOC-IMP1)

### Other Planned Extensions

- [ ] Field data collection integrations — KoBoToolbox, Forms, or other tools (FIELD1)

### Explicitly Out of Scope

- ~~Calendar/scheduling~~ → Recommend Calendly, Google Calendar, Microsoft Bookings
- ~~Full document storage~~ → Recommend Google Drive, SharePoint, Dropbox
- ~~Full offline PWA~~ → Paper forms acceptable; basic offline banner added (BUG-6)
- ~~Multi-tenancy~~ → Fork required for coalition implementations

## Parking Lot

### QA Scenarios — Parking Lot

From konote-qa-scenarios. These require test infrastructure or app features in this repo.

- [ ] Stress testing — simulate 50+ concurrent users to find performance bottlenecks and connection pool limits (QA-T15)
- [ ] Data migration scenario — test what happens when importing client data from a legacy system. Validates the Bulk Import feature (IMP1 series) once built (QA-T16)
- [x] Screenshot naming improvement — URL slug appended to filenames (e.g., `SCN-005_step1_DS1b_clients.png`) for route traceability — 2026-02-08 (QA-T20)

### Erasure — Deferred Execution for Tier 3

- [ ] Add 24-hour delay before Tier 3 (full erasure) CASCADE delete executes — requires background task scheduler, see `tasks/erasure-hardening.md` section ERASE-H8 (ERASE-H8)

### Deployment Workflow Enhancements

See [deployment workflow design](docs/plans/2026-02-05-deployment-workflow-design.md) for full details.

### QA Test Isolation

- [x] Test isolation for scenario runner — fresh browser context per scenario, locale from persona data, auto-login, prerequisite validation — 2026-02-08 (QA-ISO1)

### Privacy & Security

- [ ] First-run setup wizard — guided initial configuration (SETUP1)
- [ ] TOTP multi-factor authentication for local auth — see `tasks/mfa-implementation.md` (SEC2)
- [ ] Encrypted search optimisation (search hash field) for 2000+ client lists (PERF1)
- [ ] Bulk operations for discharge, assign (UX17)

## Recently Done

- [x] QA Scenario Runner full coverage — 4 test users, 6 test clients, 7 action types (voice/dictate/intercept/tabs/back/screenshot), 5 new test classes + 2 updated (22 new scenarios), LLM evaluator prompt enhancements (cognitive/mechanical/completion checks) — 2026-02-08 (QA-DATA1-5, QA-ACT1-5, QA-TEST1-7, QA-EVAL1-3)
- [x] QA Infrastructure Phase 3 — CI/CD gate (QA-T11), satisfaction gap tracking (QA-T12), bidirectional ticket sync (QA-T14). GitHub Actions workflows, standalone scripts, JSON results serializer — 2026-02-08 (QA-T11, QA-T12, QA-T14)
- [x] Test isolation (QA-ISO1) + objective scoring (QA-T10) — fresh context per scenario, locale from persona, auto-login, prerequisite validation, axe-core/action-count/lang objective scores override LLM — 2026-02-08 (QA-ISO1, QA-T10)
- [x] Fix 14 pre-existing test failures + 4 errors — missing form fields, wrong assertions, missing DB declarations, template bugs, Playwright skip fix — 2026-02-07 (TEST-FIX1)
- [x] Fix language bleed on shared browser — clear cookie on logout, set cookie on login to match user preference — 2026-02-07 (BUG-4)
- [x] French translations complete — translated 93 remaining strings to Canadian French, 100% coverage (2146/2146 entries), .mo compiled, validation passed — 2026-02-07 (I18N-TRANS1)
- [x] Code review MEDIUM remaining — admin_required decorator across all views (QUAL8), translated access denied messages (I18N-8), modal focus trap (A11Y-2), 20 JS strings translatable (I18N-4), 29 audit log view tests (TEST-4) — 2026-02-07
- [x] Code review MEDIUM fixes — QUAL5-7, A11Y-1, I18N-1/2/3/5/6/7/9/10: dev cookie fix, group forms, dedup client fields, scope on th, PDF/email/form/CSV translations, breadcrumbs, privacy.html blocktrans — 2026-02-07
- [x] Code review HIGH fixes — audit "cancel" action, consolidated `_get_client_ip()` and `admin_required`, dead JS code removed, encryption key rotation + lockout tests — 2026-02-07 (QUAL1-4, TEST1-2)
- [x] Code review CRITICAL fixes — demo/real data isolation in client HTMX views, admin_required on registration views, plan template + submission merge bypasses — 2026-02-07 (SEC1-4)
- [x] Per-Program Roles cleanup — audit logging, dead code removal, ROLE_RANK constants, help.html blocktrans, admin notices, query caching — 2026-02-07 (ROLE1-8)
- [x] Demo site setup — merged to main, registration link seeded, GitHub Pages verified, live demo tested — 2026-02-07 (DEMO1-4)
- [x] CONF9 follow-ups — logger.exception() for audit, flash message on context switch, request-level cache for needs_program_selector, soft-filter vs hard-boundary docs — 2026-02-07 (CONF9a-d)
_Older completed tasks moved to [tasks/ARCHIVE.md](tasks/ARCHIVE.md)._

---

## What's Been Built (Reference)

For detailed history, see `tasks/ARCHIVE.md`. Summary of completed work:

| Area | What's Done |
|------|-------------|
| **Core app (Phases 1-8)** | Clients, plans, notes, events, charts, admin, security, UX |
| **Client voice & qualitative** | Client-goal fields, progress descriptors, engagement observation, qualitative summary |
| **Groups** | Service groups, activity groups, projects — session logs, attendance, highlights, milestones, outcomes |
| **Confidential programs** | Isolation, guided setup, Django admin filtering, audit logging, small-cell suppression, DV-ready documentation |
| **Duplicate detection & merge** | Phone + name/DOB matching, cross-program dedup, admin merge tool with full data transfer |
| **Demo data** | 5 programs, 15 clients, 3 groups, cross-enrolments, approachable metrics |
| **Secure export** | Bug fix, audit logging, warnings, secure links, permission alignment |
| **French** | 2,146 system strings (100% translated), bilingual login, language switcher, translate_strings command |
| **Reporting** | Funder reports, aggregation, demographics, fiscal year, PDF exports |
| **Documentation** | Getting started, security ops, deployment guides (Azure, Railway, Elest.io, FullHost) |
| **Registration** | Self-service public forms with duplicate detection and capacity limits |
| **Privacy** | Tiered client data erasure (anonymise/purge/delete), multi-PM approval, erasure codes, PDF receipts, PIPEDA compliance |
| **Accessibility** | WCAG 2.2 AA — semantic HTML, colour contrast, aria attributes |
| **Canadian localisation** | Postal codes, provinces, phone formats, date/currency by locale |
| **Deployment** | Railway (auto-deploy), FullHost (HTTPS verified), Docker Compose for Azure/Elest.io |
