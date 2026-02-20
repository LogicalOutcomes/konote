# Project Tasks

## Flagged

- [ ] Review requirements analysis doc with Sara before sending to client (docs/konote-requirements-analysis-draft.md) — GG (DOC-REQ1)
- [ ] Approve Agency Permissions Interview questionnaire before first agency deployment (see tasks/agency-permissions-interview.md) — GG (ONBOARD-APPROVE)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — GG (SEC3-Q1)
- [ ] Confirm standard report schema and configuration template with Claire (Prosper Canada) before building — SG (RPT-SCHEMA1)
- [ ] Review and approve multi-tenancy implementation plan with Sara and Prince before building — covers django-tenants integration, per-tenant encryption, consortium data model, and hybrid federation architecture (see tasks/prosper-canada/multi-tenancy-implementation-plan.md) — SG/PD (MT-APPROVE1)

## Active Work

### Phase: Launch Readiness

- [ ] Complete Agency Deployment Protocol with Prosper Canada — Phase 0 Discovery Call first (see tasks/prosper-canada/deployment-protocol.md) — SG (DEPLOY-PC1)
- [x] Define Prosper Canada configuration template — standard roles, metrics, terminology, plan templates for financial coaching agencies (see config_templates/prosper-canada/) — 2026-02-20 — GG (DEPLOY-TEMPLATE1)
- [ ] Follow up with Claire (Prosper Canada) for additional must-haves on feature comparison — SG (DEPLOY-PC2)
- [ ] Complete Agency Permissions Interview and signed Configuration Summary before first deployment — GG (ONBOARD-GATE)
- [ ] Verify production email configuration for exports, erasure alerts, and password resets — GG (OPS3)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — GG (OPS4)
- [ ] Document scheduled task setup for export monitoring in the runbook — GG (EXP2w)
- [ ] Enforce cross-program sharing consent (PHIPA) in views — consent flag already captured, need view-level enforcement (PHIPA-ENFORCE1)
- [ ] Build cross-agency data rollup for funders — waiting on requirements from Prosper Canada re: which metrics to aggregate (see tasks/prosper-canada/) — GG (SCALE-ROLLUP1)
- [ ] Build role-based dashboard views — coach, PM, and executive landing pages with role-specific data (see tasks/dashboard-roles-plan.md) — GG (DASH-ROLES1)

### Phase: Communication Modules — complete!

### Phase: AI Goal Builder (PR #145 follow-up)

- [x] Add French translations for 10 new strings in goal_form.html and _goal_builder.html — extract, translate, compile .po/.mo — 2026-02-18 (I18N-GB1)

### Phase: Suggestion Themes — Review Follow-up (PRs #147, #149) — complete!

### Phase: Near-Term Improvements — complete!

- [x] Fix report export 500 error — missing defaultdict import, suppressed-value type crashes in CSV generation, no error handling — 2026-02-18 (BUG-EXP1)

### Phase: Post-Housekeeping Verification

- [x] Run full test suite (`pytest -m "not browser and not scenario_eval"`) to verify PR #143 test fixes pass against current main — 2026-02-20 (VERIFY1)
- [ ] Fix 12 pre-existing test failures — 5 SQLite isolation ("no such table: users"), 2 SQLite/PG behavioural differences, 1 AI fixture mismatch, 1 stale .mo, 2 missing staticfiles dir, 1 missing QA file (TEST-PREEXIST1)

## Do Occasionally

Step-by-step commands for each task are in [tasks/recurring-tasks.md](tasks/recurring-tasks.md).

- [ ] **UX walkthrough** — run after UI changes. In Claude Code: `pytest tests/ux_walkthrough/ -v`, then review `tasks/ux-review-latest.md` and add fixes to TODO (UX-WALK1)
- [ ] **Code review** — run every 2–4 weeks or before a production deploy. Open Claude Code and paste the review prompt from [tasks/code-review-process.md](tasks/code-review-process.md) (REV1)
- [ ] **Full QA suite** — run after major releases or substantial UI changes. In Claude Code: `/run-scenario-server`, then `/capture-page-states` in konote-app; `/run-scenarios`, then `/run-page-audit` in konote-qa-scenarios (QA-FULL1)
- [ ] **French translation spot-check** — have a French speaker review key screens. Run `python manage.py check_translations` to verify .po file coverage (I18N-REV1)
- [ ] **Redeploy to Railway** — after merging to main. Push to `main` and Railway auto-deploys (OPS-RAIL1)

## Coming Up

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Data Quality

- [ ] Entry-time plausibility warnings — soft-flag unlikely values during data entry, prioritise financial metrics (see tasks/data-validation-design.md, financial subsection added 2026-02-20) (DQ1)
- [ ] Add second-tier "very unlikely" plausibility thresholds for financial metrics — tighter bounds beyond warn_max for edge case detection (DQ1-TIER2)
- [ ] Pre-report data quality checks — validate data quality before funder report export (see tasks/data-validation-design.md) (DQ2)
- [ ] Add funder report approval workflow — quality review, agency annotations, explicit publish step before sharing with funders (see tasks/funder-report-approval.md, plan: docs/plans/2026-02-20-funder-report-approval-design.md) (RPT-APPROVE1)

### Phase: Multi-Agency Scaling

- [ ] Integrate django-tenants for schema-per-tenant multi-tenancy — PostgreSQL backend, shared/tenant app split, tenant model, domain model (see tasks/prosper-canada/multi-tenancy-implementation-plan.md, Tasks 0-2) — GG (MT-CORE1)
- [ ] Implement per-tenant encryption keys — key table in shared schema, encrypted by master key, update encryption.py (see plan Task 3) — GG (MT-ENCRYPT1)
- [ ] Create consortium data model — Consortium, ConsortiumMembership, ProgramSharing, PublishedReport with program-level sharing granularity (see plan Task 4) — GG (MT-CONSORT1)
- [ ] Add consent_to_aggregate_reporting field and audit tenant_schema column (see plan Tasks 5-6) — GG (MT-CONSENT1)
- [ ] Validate existing features across tenant schemas — update test infrastructure, fix tenant-related test failures (see plan Tasks 7-8) — GG (MT-VALIDATE1)
- [ ] Build deploy script to automate Phase 2 infrastructure provisioning — Azure resources, env vars, migrations, output a URL (plan: docs/plans/2026-02-20-deploy-script-design.md) (DEPLOY-SCRIPT1)
- [ ] Define managed service model — who handles infrastructure, backups, updates, support tiers, funding model (see tasks/prosper-canada/managed-service-model.md) (OPS-MANAGED1)
- [ ] Build cross-agency reporting API — standardised endpoint per instance for Prosper Canada to consume published reports (plan: docs/plans/2026-02-20-cross-agency-reporting-api-design.md) (SCALE-API1)
- [ ] Build umbrella admin dashboard — central view for Prosper Canada to see instance health, published reports, and aggregate metrics across agencies (SCALE-DASH1)
- [ ] Improve admin UI for self-service configuration — better guidance for terminology, metrics, templates (ADMIN-UX1)
- [ ] Align report-template.json "bins" field naming with DemographicBreakdown model's "bins_json" when building Phase 2 template automation (TEMPLATE-ALIGN1)

### Phase: Participant View Improvements

- [ ] Add adjustable timeframe and date range controls to Participant analysis charts (see tasks/participant-view-improvements.md) — GG (CHART-TIME1)
- [ ] Add target filter to Notes section so staff can follow progress on a single target without reading every note (see tasks/participant-view-improvements.md) — GG (UX-NOTES-BY-TARGET1)

### Phase: Other Upcoming

- [ ] Permissions Phase 2 — remaining 10 items: discharge access transitions, consent model, DV-safe mode, GATED clinical access, group schedule vs roster, per-field front desk edit, SCOPED→PROGRAM rename, funder report key, alert escalation, dashboard split (see tasks/permissions-expert-panel-2026-02-09.md) (PERM-P3–12)

### Phase: Advanced Reporting

- [ ] Research typical nonprofit session reporting requirements (UNHCR, IRCC, CCIS, etc.) to design "Sessions by Participant" report (REP-REQ1)
- [ ] Build "Sessions by Participant" report template — count and type of sessions (Progress Note interactions) per participant (REP-SESS1)
- [ ] Expand report template system to support more flexible data exports across various modules (REP-FLEX1)
- [ ] Add "All Programs" option to report filters for organization-wide summaries (REP-ALL-PROGS1)
- [ ] Implement report preview on-screen before downloading PDF/CSV (REP-PREVIEW1)
- [ ] Research/Implement including data visuals (charts/graphs) in PDF reports (REP-PDF1)
- [ ] Redesign PDF report layout: merge title page with page 2 to eliminate redundant empty space (REP-PDF2)
- [ ] Define standardised report schema for Prosper Canada — 10-15 key metrics and demographic breakdowns shared across all partner agencies (RPT-SCHEMA1)

### Phase: Surveys QA Scenarios

- [ ] Add survey demo data to seed_demo_data — 2 active surveys, 1 draft, 1 response, 1 assignment, 1 trigger rule (see tasks/qa-survey-scenarios.md) (QA-SURV1)
- [ ] Create CSV test fixture for survey import at tests/fixtures/sample-survey-import.csv (QA-SURV2)
- [ ] Write 8 scenario YAML files (SCN-110 through SCN-117) in konote-qa-scenarios repo (see tasks/qa-survey-scenarios.md) (QA-SURV3)
- [ ] Add test methods for survey scenarios to tests/scenario_eval/test_scenario_eval.py (QA-SURV4)
- [ ] Update page-inventory.yaml in qa-scenarios repo with survey pages (QA-SURV5)

### Phase: Surveys Future Work

- [ ] Build shareable link channel for public survey links without login (SURVEY-LINK1)
- [ ] Build trigger rule management UI (rules currently created via Django admin) (SURVEY-RULES1)
- [ ] Implement auto-save / partial answers in the portal (SURVEY-AUTOSAVE1)
- [ ] Run `translate_strings` to extract and compile French translations for the new survey templates (SURVEY-I18N1)

### Phase: Documentation & Website Updates

- [ ] Create deployment documentation for surveys and portal features (DOC-DEPLOY1)
- [ ] Update technical documentation in GitHub for surveys and portal architecture (DOC-TECH1)
- [ ] Update website feature list and marketing copy to include surveys and portal (WEB-FEAT1)

### Phase: QA Round 6 — Design Tasks

- [x] Design /admin/ URL restructuring for PM self-service — move management pages to /manage/ so PMs can reach plan templates, note templates, event types (FG-2, PERMISSION-1/2/3, BUG-1 -> QA-W59)

### Phase: Pre-existing Test Failures — DONE

- [x] Fix `apply_setup` command tests (10 failures) — output format changed but tests not updated — 2026-02-18 (TEST-SETUP1)
- [x] Fix `translate_strings --no-translate` test — option does not exist — 2026-02-18 (TEST-TRANS1)
- [x] Fix portal session isolation test — accept 404 as valid denial — 2026-02-18 (TEST-PORTAL1)
- [x] Fix BLOCKER-1 a11y test — updated to expect skip link (WCAG best practice) — 2026-02-18 (TEST-A11Y1)

### Phase: AI Target Suggestion — Polish — complete!

### Phase: UX Fixes

**Persona for all text rewrites:** Write as if speaking to a nonprofit staff person (coordinator, coach, counsellor, front desk) across a variety of program types — not a data analyst or developer.

- [x] Fix Add Target form UX: auto-select or clarify "area of the plan", remove "Attendance & Wellbeing" placeholder, and change metric text from "how much progress have they made" to "how much progress have I made" — 2026-02-20 (UX-TARGET1)
- [x] Change "Add section only" link text to "Add Section" on plan view — 2026-02-20 (UX-SECTION1)
- [x] Remove "+ Add note" link in Notes tab, update wayfinding text to reference Actions menu — 2026-02-20 (UX-NOTES3)
- [x] Fix "server error occurred" when clicking "Shape this target" — metric catalogue key mismatch — 2026-02-20 (BUG-AI1)
- [x] Fix "error message" when clicking "Draft Report summary" — gettext_lazy proxies as JSON keys — 2026-02-20 (BUG-AI2)
## Parking Lot

- [ ] Add stress testing for 50+ concurrent users (QA-T15)
- [ ] Add legacy system import migration scenario test (QA-T16)
- [ ] Add onboarding guidance for new users (help link or first-run banner) (QA-W19)
- [ ] Implement multi-session testing for SCN-046 shared device scenario (QA-W55)
- [ ] Surveys — lightweight structured feedback collection from participants (see tasks/surveys-design.md) (SURVEY1)
- [ ] Add serious reportable events workflow and reporting (see tasks/serious-reportable-events.md) (SRE1)
- [ ] Build agency data offboarding command for secure departures and PIPEDA requests (SEC3)
- [ ] Add first-run setup wizard UI for guided initial configuration (SETUP1-UI)
- [ ] Add TOTP multi-factor authentication (see tasks/mfa-implementation.md) (SEC2)
- [ ] Optimize encrypted client search performance beyond ~2000 records (PERF1)
- [ ] Add bulk operations for discharge and assignment workflows (UX17)
- [ ] Re-add API-based auto-translation to translate_strings for production use (I18N-API1)
- [x] Document local PostgreSQL setup for security_audit and pytest workflows — 2026-02-20 (DEV-PG1)
- [ ] Add deferred execution for Tier 3 erasure (24-hour delay) (ERASE-H8)
- [ ] Implement deployment workflow enhancements (see docs/plans/2026-02-05-deployment-workflow-design.md) (DEPLOY1)
- [ ] Document scenario_loader cache lifetime if reused outside pytest (QA-W62)
- [x] Add basic smoke test for `translate_strings` command — removed dead test class but no replacement exists — 2026-02-20 (TEST-TRANS2)
- [ ] Tidy `import datetime as dt` placement in reports/views.py — cosmetic import ordering (CODE-TIDY1)
- [ ] Unify analysis chart quick-select links and date picker form into a single input mechanism (UX-CHART1)
- [ ] Add edge-case tests for invalid/inaccessible target IDs and 3m/6m timeframe paths (TEST-FILTER1)

## Recently Done

- [x] Rename original KoNote GitHub repo to KoNote Classic and add redirect — 2026-02-20 (REPO1)
- [x] Fix fiscal year dropdown showing English strings in French UI — wrapped with gettext, added 12 French translations — 2026-02-20 (BUG-FY1)
- [x] Define Prosper Canada configuration template — 8 fixture files covering terminology, metrics, plans, roles, report schema — 2026-02-20 (DEPLOY-TEMPLATE1)
- [x] Add financial metric plausibility subsection to data validation design — warn_min/warn_max for debt, income, savings, credit score — 2026-02-20 (DQ1-FIN)
- [x] Write implementation plans for RPT-APPROVE1, DEPLOY-SCRIPT1, SCALE-API1 — 2026-02-20
- [x] Build "Questions for You" portal feature — auto-save, multi-page, conditional sections, review page, dashboard badge — 2026-02-20 (PORTAL-Q1)
- [x] Redesign detailed notes form (Round 2) — auto-calc metrics, scale pills, two-lens layout (see docs/plans/2026-02-19-notes-form-redesign-v2.md) — 2026-02-19 (UX-NOTES2)
- [x] Improve Messages page clarity — sender-first cards, urgent flag, relative timestamps, focus management, French translations — 2026-02-19 (UX-MSG1)
- [x] Active batch — theme fixes (FIX1–6), near-term improvements (BUG-SW1, URL-CLEAN1/2, QA-W60/W61), dashboard text (UX-DASH1), PERF2 already done, VERIFY2 confirmed — 2026-02-18 (THEME-FIX1–6, BUG-SW1, URL-CLEAN1, URL-CLEAN2, QA-W60, QA-W61, PERF2, UX-DASH1, VERIFY2)
- [x] Use CSS custom property for error colour in `.ai-suggest-error` and `.gb-error` — replaced hardcoded `#dc3545` with theme tokens — 2026-02-18 (AI-CSS1)
- [x] Add `%(client)s` blocktrans msgids to .po file with French translations — 2026-02-18 (AI-I18N1)
- [x] Add `@require_POST` decorator to all 8 AI POST-only views — 2026-02-18 (AI-VIEWS1)
- [x] Add test coverage for `ai_enabled` in goal_create view context — one test with AI on, one with AI off — 2026-02-18 (TEST-GB1)
- [x] Git housekeeping — deleted 31+ stale branches, cleared 10 stashes, removed 3 worktrees, rebased and merged PR #136 (cleanup) and PR #143 (10 test fixes) — 2026-02-18 (HOUSEKEEP1)
- [x] Agency Onboarding Interview Pack — 12 refinements: session split, privacy opener, role name alignment, jargon removal, summaries, warmer scenarios, deployment checklists — 2026-02-18 (ONBOARD1–12)
- [x] Move PM management pages from /admin/ to /manage/ — new URL structure, middleware simplification, redirects from old URLs, 1795 tests pass — 2026-02-18 (QA-W59)
- [x] Fix test suite freezing — add Django @tag('slow') to BrowserTestBase so --exclude-tag=slow properly skips 70 Playwright tests — 2026-02-18 (TEST-FIX1)
- [x] UX walkthrough fixes — strengthen touch target CSS with !important overrides, add aria-label to submissions table; UX5/UX10/UX11 already done — 2026-02-17 (UX-WALK6)
- [x] Mobile touch targets WCAG fix — enforce 44px minimum with explicit padding on nav, breadcrumbs, tabs, buttons, selects at mobile breakpoints — 2026-02-17 (UX-WALK5)
- [x] Fix 3 failing scenario tests — empty prerequisite guard, Priya Sharma test client, logout dropdown fallback + crash guard — 2026-02-17 (QA-FIX1, QA-FIX2, QA-FIX3)
- [x] Add demo content for suggestion themes (11 themes, 29 links) and staff messages (7 messages) — 2026-02-17 (DEMO-SUG1)
