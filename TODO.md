# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire before first agency deployment (see tasks/agency-permissions-interview.md) — GK (ONBOARD-APPROVE)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — GK (SEC3-Q1)
- [ ] Confirm standard report schema and configuration template with funder contact before building — SG (RPT-SCHEMA1)
- [ ] Approve CIDS implementation plan with project lead before building — covers metadata fields, code list integration, CIDS-enriched reports, and full JSON-LD export; confirm funder consumption pathway and whether to engage Common Approach as pilot implementer (see tasks/cids-json-ld-export.md) — SG/GK (CIDS-APPROVE1)

## Active Work

### Phase: Launch Readiness

- [ ] Complete Agency Deployment Protocol with [funder partner] — Phase 0 Discovery Call first (see tasks/deployment-protocol.md) — (DEPLOY-PC1)
- [x] Define [funder partner] configuration template — standard roles, metrics, terminology, plan templates for financial coaching agencies (see config_templates/) — 2026-02-20 — (DEPLOY-TEMPLATE1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [ ] Complete Agency Permissions Interview and signed Configuration Summary before first deployment — SG (ONBOARD-GATE)
- [ ] Store signed Configuration Summary with each deployment so new admins can see what was decided and why — SG (DEPLOY-CONFIG-DOC1)
- [ ] Verify production email configuration for exports, erasure alerts, and password resets — PB (OPS3)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — PB (OPS4)
- [ ] Document scheduled task setup for export monitoring in the runbook — PB (EXP2w)
- [ ] Enforce cross-program sharing consent (PHIPA) in views — consent flag already captured, need view-level enforcement — PB (PHIPA-ENFORCE1)
- [ ] Build cross-agency data rollup for funders — waiting on requirements re: which metrics to aggregate — PB, GK reviews metric aggregation (SCALE-ROLLUP1)
- [x] Build role-based dashboard views — coach, PM, and executive landing pages with role-specific data (see tasks/dashboard-roles-plan.md) — 2026-02-20 — (DASH-ROLES1)
- [ ] Create AI-assisted admin toolkit decision documents (01-09) for agency setup — reformat deployment protocol into AI-consumable reference docs, test with [funder partner] dry run (see tasks/ai-assisted-admin-toolkit.md, docs/agency-setup-guide/) — (DEPLOY-TOOLKIT1)

### Phase: Communication Modules — complete!

### Phase: AI Goal Builder (PR #145 follow-up)

- [x] Add French translations for 10 new strings in goal_form.html and _goal_builder.html — extract, translate, compile .po/.mo — 2026-02-18 (I18N-GB1)

### Phase: Suggestion Themes — Review Follow-up (PRs #147, #149) — complete!

### Phase: Near-Term Improvements — complete!

- [x] Fix report export 500 error — missing defaultdict import, suppressed-value type crashes in CSV generation, no error handling — 2026-02-18 (BUG-EXP1)

### Phase: Post-Housekeeping Verification

- [x] Run full test suite (`pytest -m "not browser and not scenario_eval"`) to verify PR #143 test fixes pass against current main — 2026-02-20 (VERIFY1)
- [x] Fix 6 pre-existing test failures — SQLite isolation, fixture mismatch, stale .mo, missing QA file — 2026-02-21 (TEST-PREEXIST1)

## Do Occasionally

Step-by-step commands for each task are in [tasks/recurring-tasks.md](tasks/recurring-tasks.md).

- [ ] **UX walkthrough** — run after UI changes. In Claude Code: `pytest tests/ux_walkthrough/ -v`, then review `tasks/ux-review-latest.md` and add fixes to TODO (UX-WALK1)
- [ ] **Code review** — run every 2–4 weeks or before a production deploy. Open Claude Code and paste the review prompt from [tasks/code-review-process.md](tasks/code-review-process.md) (REV1)
- [ ] **Full QA suite** — run after major releases or substantial UI changes. Two pipelines (A then B), five sessions total — see [tasks/recurring-tasks.md](tasks/recurring-tasks.md) for full steps (QA-FULL1)
- [ ] **French translation spot-check** — have a French speaker review key screens. Run `python manage.py check_translations` to verify .po file coverage (I18N-REV1)
- [ ] **Redeploy to Railway** — after merging to main. Push to `main` and Railway auto-deploys (OPS-RAIL1)

## Coming Up

### Phase: QA Round 7 — Tier 2 Fixes (see tasks/qa-action-plan-2026-02-21.md)

- [ ] Fix keyboard tab order and quick note reachability on create-participant form and client profile (BLOCKER-5 remaining + IMPROVE-9/10) (QA-R7-A11Y1)
- [ ] Fix French receptionist: client search returns no results for R2 + missing create button for R2-FR (QA-R7-FRDESK1)
- [ ] Add "Log Communication" to client profile Actions dropdown — pre-fill client name (QA-R7-COMM1)
- [ ] Fix calendar feed URL generation — POST handler fails silently (QA-R7-CAL1)
- [ ] Add success confirmation message after phone number update (QA-R7-BUG4)
- [ ] Verify /manage/ note templates and event types pages exist + add funder profile selector to report form (QA-R7-ADMIN1)
- [ ] Hide admin dropdown in nav for executive role (QA-R7-NAV1)
- [ ] Accessibility polish: status dropdown auto-open on Tab, aria-live on search results, colour-only status indicators (IMPROVE-11/12/13) (QA-R7-A11Y2)
- [ ] Fix settings page 404 for staff role — verify correct URL path (QA-R7-ROUTE1)
- [ ] Build scoped user management view for PMs — manage staff in own programme via /manage/ (QA-R7-PM-USERS1)
- [ ] Build scoped audit log view for PMs — programme-filtered, plain language, filterable (QA-R7-PM-AUDIT1)

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Data Quality

- [ ] Entry-time plausibility warnings — soft-flag unlikely values during data entry, prioritise financial metrics (see tasks/data-validation-design.md, financial subsection added 2026-02-20) (DQ1)
- [ ] Add second-tier "very unlikely" plausibility thresholds for financial metrics — tighter bounds beyond warn_max for edge case detection (DQ1-TIER2)
- [ ] Pre-report data quality checks — validate data quality before funder report export (see tasks/data-validation-design.md) (DQ2)
- [ ] Add funder report approval workflow — quality review, agency annotations, explicit publish step before sharing with funders (see tasks/funder-report-approval.md, plan: docs/plans/2026-02-20-funder-report-approval-design.md) (RPT-APPROVE1)

### Phase: Multi-Agency Scaling — start after first single-tenant agency is live (see tasks/design-rationale/multi-tenancy.md)

- [ ] Integrate django-tenants for schema-per-tenant multi-tenancy — PostgreSQL backend, shared/tenant app split, tenant model, domain model (see tasks/multi-tenancy-implementation-plan.md, Tasks 0-2) — PB (MT-CORE1)
- [ ] Implement per-tenant encryption keys — key table in shared schema, encrypted by master key, update encryption.py (see plan Task 3) — PB (MT-ENCRYPT1)
- [ ] Create consortium data model — Consortium, ConsortiumMembership, ProgramSharing, PublishedReport with program-level sharing granularity (see plan Task 4) — PB, GK reviews data model (MT-CONSORT1)
- [ ] Add consent_to_aggregate_reporting field and audit tenant_schema column (see plan Tasks 5-6) — PB (MT-CONSENT1)
- [ ] Validate existing features across tenant schemas — update test infrastructure, fix tenant-related test failures (see plan Tasks 7-8) — PB (MT-VALIDATE1)
- [ ] Build deploy script to automate Phase 2 infrastructure provisioning — Azure resources, env vars, migrations, output a URL (plan: docs/plans/2026-02-20-deploy-script-design.md) (DEPLOY-SCRIPT1)
- [ ] Define managed service model — who handles infrastructure, backups, updates, support tiers, funding model (see tasks/managed-service-model.md) (OPS-MANAGED1)
- [ ] Build cross-agency reporting API — standardised endpoint per instance for [funder partner] to consume published reports (plan: docs/plans/2026-02-20-cross-agency-reporting-api-design.md) (SCALE-API1)
- [ ] Build umbrella admin dashboard — central view for [funder partner] to see instance health, published reports, and aggregate metrics across agencies (SCALE-DASH1)
- [ ] Improve admin UI for self-service configuration — better guidance for terminology, metrics, templates (ADMIN-UX1)
- [ ] Align report-template.json "bins" field naming with DemographicBreakdown model's "bins_json" when building Phase 2 template automation (TEMPLATE-ALIGN1)

### Phase: CIDS Compliance (Common Approach Data Standard) — waiting on CIDS-APPROVE1

- [ ] Add CIDS metadata fields to MetricDefinition, Program, and PlanTarget — optional fields for IRIS+ codes, SDG goals, sector codes (see tasks/cids-json-ld-export.md Phase 1) — (CIDS-META1)
- [ ] Create OrganizationProfile model for CIDS BasicTier org metadata — legal name, sector, province (Phase 1) — (CIDS-ORG1)
- [ ] Import CIDS code lists (17 lists) via management command from codelist.commonapproach.org with version tracking (Phase 2) — (CIDS-CODES1)
- [ ] Build admin UI for CIDS tagging — dropdowns on program and metric forms, integrate into config template system (Phase 2) — (CIDS-ADMIN1)
- [ ] Add CIDS codes to existing CSV/PDF funder reports + "Standards Alignment" appendix page — quick win, no new format needed (Phase 2.5) — (CIDS-ENRICH1)
- [ ] Build JSON-LD export with basic SHACL validation — new format option alongside CSV/PDF, aggregate only (Phase 3) — (CIDS-EXPORT1)
- [ ] Compute CIDS impact dimensions (scale, depth, duration) from existing KoNote data — no new data entry (Phase 4) — (CIDS-IMPACT1)
- [ ] Add CIDS conformance badge and detailed validation reporting (Phase 5) — (CIDS-VALIDATE1)

### Phase: Participant View Improvements — complete!

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
- [ ] Define standardised report schema for [funder partner] — 10-15 key metrics and demographic breakdowns shared across all partner agencies (RPT-SCHEMA1)

### Phase: Demo Data Quality

- [ ] Fix suggestion theme linking in seed_demo_data — make suggestions program-specific and remove blind fallback that links irrelevant notes to themes (see tasks/demo-data-suggestion-fix.md) — (DEMO-FIX1)

### Phase: Surveys QA Scenarios

- [x] Add survey demo data to seed_demo_data — 3 surveys, trigger rule, shareable link, assignments, responses — 2026-02-21 (QA-SURV1)
- [x] Create CSV test fixture for survey import at tests/fixtures/sample-survey-import.csv — 2026-02-21 (QA-SURV2)
- [x] Write 8 scenario YAML files (SCN-110 through SCN-117) in konote-qa-scenarios repo — 2026-02-21 (QA-SURV3)
- [x] Add test methods for survey scenarios to tests/scenario_eval/test_scenario_eval.py — 2026-02-21 (QA-SURV4)
- [x] Update page-inventory.yaml in qa-scenarios repo with survey pages — 2026-02-21 (QA-SURV5)

### Phase: Surveys Future Work

- [ ] Build shareable link channel for public survey links without login (SURVEY-LINK1)
- [x] Build trigger rule management UI — /manage/surveys/<id>/rules/ and /manage/surveys/<id>/rules/new/ — 2026-02-20 (SURVEY-RULES1)
- [x] Implement auto-save / partial answers in the portal — PartialAnswer model + portal_survey_autosave view — 2026-02-20 (SURVEY-AUTOSAVE1)
- [ ] Run `translate_strings` to extract and compile French translations for the new survey templates (SURVEY-I18N1)

### Phase: Documentation & Website Updates

- [ ] Create deployment documentation for surveys and portal features (DOC-DEPLOY1)
- [ ] Update technical documentation in GitHub for surveys and portal architecture (DOC-TECH1)
- [ ] Update website feature list and marketing copy to include surveys and portal (WEB-FEAT1)
- [ ] Add Evidence section to website — adapt docs/evidence-outcome-measurement.md into a public-facing page explaining the research behind KoNote's outcome measurement approach (see tasks/web-evidence-prompt.md) (WEB-EVIDENCE1)
- [x] Validate academic citations in docs/evidence-outcome-measurement.md — verified 23 references, fixed 6 errors — 2026-02-20 (DOC-REFCHECK1)

### Phase: QA Round 6 — Design Tasks

- [x] Design /admin/ URL restructuring for PM self-service — move management pages to /manage/ so PMs can reach plan templates, note templates, event types (FG-2, PERMISSION-1/2/3, BUG-1 -> QA-W59)

### Phase: Pre-existing Test Failures — DONE

- [x] Fix `apply_setup` command tests (10 failures) — output format changed but tests not updated — 2026-02-18 (TEST-SETUP1)
- [x] Fix `translate_strings --no-translate` test — option does not exist — 2026-02-18 (TEST-TRANS1)
- [x] Fix portal session isolation test — accept 404 as valid denial — 2026-02-18 (TEST-PORTAL1)
- [x] Fix BLOCKER-1 a11y test — updated to expect skip link (WCAG best practice) — 2026-02-18 (TEST-A11Y1)

### Phase: AI Target Suggestion — Polish — complete!

### Phase: UX Fixes — complete!

- [x] Fix Add Target form UX: auto-select or clarify "area of the plan", remove "Attendance & Wellbeing" placeholder, and change metric text from "how much progress have they made" to "how much progress have I made" — 2026-02-20 (UX-TARGET1)
- [x] Change "Add section only" link text to "Add Section" on plan view — 2026-02-20 (UX-SECTION1)
- [x] Remove "+ Add note" link in Notes tab, update wayfinding text to reference Actions menu — 2026-02-20 (UX-NOTES3)
- [x] Fix "server error occurred" when clicking "Shape this target" — metric catalogue key mismatch — 2026-02-20 (BUG-AI1)
- [x] Fix "error message" when clicking "Draft Report summary" — gettext_lazy proxies as JSON keys — 2026-02-20 (BUG-AI2)

### Phase: UX + QA Round 7 Fixes — complete!

- [x] Permission fix: calendar feed settings missing access control — 2026-02-21 (PERMISSION-1)
- [x] Fix 403 page: remove raw exception display, add role-specific messages — 2026-02-21 (BUG-3)
- [x] ARIA tablist on client profile tabs with arrow key navigation — 2026-02-21 (BUG-14)
- [x] Form validation ARIA: novalidate + custom errors with aria-describedby — 2026-02-21 (BUG-16)
- [x] Group creation pre-selects program for single-program users — 2026-02-21 (BUG-22)
- [x] Executive dashboard date range filter and CSV export — 2026-02-21 (BUG-9/10)
- [x] Offline fallback page — 2026-02-21 (BUG-17)
- [x] Dismissable priority items on dashboard (localStorage, daily reset) — 2026-02-21 (BUG-19)
- [x] Form labels: "sort_order" → "Display order", "status_reason" → "Why is this being changed?" — 2026-02-21 (UX-LABEL1, UX-LABEL2)
- [x] Replace location.reload() with HTMX cancel on plan status forms — 2026-02-21 (UX-RELOAD1)
- [x] Template dropdown shows section count in full note form — 2026-02-21 (UX-DROPDOWN1)
- [x] Duplicate note date warning via HTMX — 2026-02-21 (UX-DUPENOTE1)
- [x] Enhanced post-save message with target/metric counts — 2026-02-21 (UX-POSTSAVE1)
- [x] Template preview on note form — 2026-02-21 (UX-PREVIEW1)
- [x] "Create New" button in empty search results + result count — 2026-02-21 (IMPROVE-2, IMPROVE-8)
- [x] Hidden programs notice on client profile — 2026-02-21 (IMPROVE-5)
- [x] Front desk orientation card on home page — 2026-02-21 (UX-FRONTDESK1)
- [x] Task-oriented dashboard: quick links moved up, action-oriented headings — 2026-02-21 (UX-TASKDASH1, BUG-18)

### Phase: QA Round 7 — Tier 1 Fixes (see tasks/qa-action-plan-2026-02-21.md)

- [ ] Fix language persistence — build UserLanguageMiddleware so user profile preferred_language is authoritative, not cookie/session (affects 22 scenarios) (QA-R7-BUG1)
- [ ] Verify /manage/ routes cover PM self-service — check if BLOCKER-1 is a scenario YAML issue, update qa-scenarios if needed (QA-R7-BLKR1)
- [ ] Add skip-to-content link to base template — WCAG 2.4.1 Level A requirement (QA-R7-BUG15)
- [ ] Fix notes URL returning 404 instead of 403 for receptionist — add explicit permission check before queryset filter (QA-R7-BUG2)
- [ ] Fix htmx:syntax:error messages on create-participant page — audit all hx-* attributes (QA-R7-BUG20)
## Parking Lot

- [ ] PIPEDA data export from client profile — "Export Data" action for Section 8 access requests, needs design for data categories and output format — GK reviews privacy workflow (QA-R7-PRIVACY1)
- [ ] Consent withdrawal workflow on client profile — wizard for PIPEDA consent withdrawal with data retention rules — GK reviews privacy/data retention (QA-R7-PRIVACY2)
- [ ] Executive compliance report — aggregate dashboard showing privacy request counts, processing times (no PII) — GK reviews reporting methodology (QA-R7-EXEC-COMPLIANCE1)
- [ ] Add quarterly date range presets (Q1-Q4) and custom date range to funder report form (QA-R7-RPT-QUARTER1)
- [ ] Verify accented character preservation through create/save/display cycle — may be test data issue, needs manual check (QA-R7-BUG13)
- [ ] Verify form data preservation after validation error on create-participant — medium confidence, may be test artefact (QA-R7-BUG21)
- [ ] DQ1 implementation: build threshold tuning feedback from day one — admin view of warnings triggered vs overridden per metric (DQ1-TUNE)
- [ ] DQ2 implementation: define severity tiers so the quality gate doesn't produce too many warnings that staff ignore (DQ2-TIERS)
- [ ] Verify deploy-azure.md reference in deployment protocol still resolves — may have been moved or renamed (DEPLOY-VERIFY1)
- [ ] Add stress testing for 50+ concurrent users (QA-T15)
- [ ] Add legacy system import migration scenario test (QA-T16)
- [ ] Add onboarding guidance for new users (help link or first-run banner) (QA-W19)
- [ ] Implement multi-session testing for SCN-046 shared device scenario (QA-W55)
- [ ] Surveys — lightweight structured feedback collection from participants (see tasks/surveys-design.md) (SURVEY1)
- [ ] Add serious reportable events workflow and reporting (see tasks/serious-reportable-events.md) (SRE1)
- [ ] Build agency data offboarding command for secure departures and PIPEDA requests (SEC3)
- [ ] Add in-app configuration dashboard showing all active settings with decision rationale and change history (DEPLOY-CONFIG-UI1)
- [ ] Add first-run setup wizard UI for guided initial configuration (SETUP1-UI)
- [ ] Add TOTP multi-factor authentication (see tasks/mfa-implementation.md) (SEC2)
- [ ] Optimize encrypted client search performance beyond ~2000 records (PERF1)
- [ ] Add bulk operations for discharge and assignment workflows (UX17)
- [ ] Re-add API-based auto-translation to translate_strings for production use (I18N-API1)
- [ ] Translate CSV comment rows (# Program, # Date Range, etc.) — needs design decision on whether to use agency custom terminology or static translations (I18N-CSV1)
- [ ] Clean up ~628 stale PO entries in django.po no longer referenced in code (I18N-STALE1)
- [x] Document local PostgreSQL setup for security_audit and pytest workflows — 2026-02-20 (DEV-PG1)
- [ ] Add deferred execution for Tier 3 erasure (24-hour delay) (ERASE-H8)
- [ ] Implement deployment workflow enhancements (see docs/plans/2026-02-05-deployment-workflow-design.md) (DEPLOY1)
- [ ] Document scenario_loader cache lifetime if reused outside pytest (QA-W62)
- [x] Add basic smoke test for `translate_strings` command — removed dead test class but no replacement exists — 2026-02-20 (TEST-TRANS2)
- [ ] Tidy `import datetime as dt` placement in reports/views.py — cosmetic import ordering (CODE-TIDY1)
- [ ] Separate "Scheduled Assessment" workflow for standardized instruments (PHQ-9, etc.) — funder reporting (ASSESS1)
- [ ] Metric cadence system — only prompt for metric values when due, configurable per metric (METRIC-CADENCE1)
- [ ] 90-day metric relevance check — prompt worker to confirm or change the chosen metric (METRIC-REVIEW1)
- [ ] Alliance Repair Guide — one-page printable guide for workers when participants rate low (ALLIANCE-GUIDE1)
- [ ] Participant-facing progress view — show descriptor timeline to participant in portal (PORTAL-PROGRESS1)
- [ ] Alliance prompt rotation — cycle 3-4 phrasings to prevent habituation (ALLIANCE-ROTATE1)
- [ ] Portal-based async alliance rating — post-session notification for participant self-rating (PORTAL-ALLIANCE1)

## Recently Done

- [x] UX + QA Round 7 fixes — 18 items: accessibility (ARIA tablist, form validation), dashboard (task-oriented layout, dismissable items, executive date range/export), notes UX (template preview, duplicate warning, post-save counts), front desk orientation, hidden programs notice, label improvements, HTMX cancel — 2026-02-21 (see Phase: UX + QA Round 7 Fixes above)
- [x] Unify analysis chart quick-select and date picker into single form control — 2026-02-21 (UX-CHART1)
- [x] Accessibility fixes: aria-labels on audit table, notes error container, mobile touch targets — 2026-02-21 (A11Y-UX1)
- [x] Add survey demo data and scenario test stubs — 2026-02-21 (QA-SURV1, QA-SURV2, QA-SURV4)
- [x] Fix fiscal year dropdown showing English strings in French UI — 2026-02-20 (BUG-FY1)
- [x] Build "Questions for You" portal feature — auto-save, multi-page, conditional sections — 2026-02-20 (PORTAL-Q1)
- [x] Redesign detailed notes form (Round 2) — auto-calc metrics, scale pills, two-lens layout — 2026-02-19 (UX-NOTES2)
- [x] Move PM management pages from /admin/ to /manage/ — 2026-02-18 (QA-W59)
- [x] Fix test suite freezing — skip Playwright tests with --exclude-tag=slow — 2026-02-18 (TEST-FIX1)
- [x] Mobile touch targets WCAG fix — enforce 44px minimum — 2026-02-17 (UX-WALK5)
