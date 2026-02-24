# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire before first agency deployment (see tasks/agency-permissions-interview.md) — GK (ONBOARD-APPROVE)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — GK (SEC3-Q1)
- [ ] Confirm standard report schema and configuration template with partner contact before building — SG (RPT-SCHEMA1)
- [ ] Discuss: are Design Rationale Records (DRRs) working well as a practice? Should we keep using them, change the format, or retire them? — GK (PROCESS-DRR1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)
- [ ] Discuss: Should GK design insights/reports pages as HTML mockups (in a `mockups/` folder) to iterate on layout without PRs? Developer would translate approved mockups into Django templates — PB (PROCESS-MOCKUPS1)

## Active Work

### Phase: Offline Field Collection (PR #34 — Prince reviewing)

- [x] App skeleton, models, ODK client, sync command — 2026-02-24 (FIELD-ODK-APP1, SYNC1)
- [x] XLSForms for attendance and visit notes — 2026-02-24 (FIELD-ODK-FORM-ATT1, FORM-VIS1)
- [x] Admin UI, feature toggle, settings — 2026-02-24 (FIELD-ODK-ADMIN1)
- [x] App user mapping, pull submissions, dedup — 2026-02-24 (FIELD-ODK-USERS1, IMPORT1)
- [x] Four PII tiers with scope control — 2026-02-24 (FIELD-ODK-TIERS1)
- [x] Sync status dashboard — 2026-02-24 (FIELD-ODK-DASH1)
- [x] Tests (43 tests), two code reviews — 2026-02-24 (FIELD-ODK-TEST1)
- [x] French translations — 2026-02-24 (FIELD-ODK-I18N1)
- [ ] Deploy ODK Central on Canadian VM (Docker Compose) — ops task (FIELD-ODK-DEPLOY1)
- [ ] Circle Observation XLSForm — depends on circles in ODK (FIELD-ODK-FORM-CIR1)
- [ ] Push Circle/CircleMember Entity lists — depends on above (FIELD-ODK-CIRCLES1)
- [ ] Agency-facing documentation — ODK Collect setup, device loss protocol (FIELD-ODK-DOC1)

### Phase: Insights Metric Distributions (see tasks/design-rationale/insights-metric-distributions.md, tasks/insights-metrics-implementation.md)

- [x] Phase 5: Workbench-to-report links, board summary template, translations, docs — 2026-02-24 (INSIGHTS-P5-POLISH)

### Phase: Launch Readiness

- [ ] Complete Agency Deployment Protocol with [funder partner] — Phase 0 Discovery Call first (see tasks/deployment-protocol.md) — (DEPLOY-PC1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [ ] Complete Agency Permissions Interview and signed Configuration Summary before first deployment — SG (ONBOARD-GATE)
- [ ] Store signed Configuration Summary with each deployment so new admins can see what was decided and why — SG (DEPLOY-CONFIG-DOC1)
- [ ] Verify production email configuration for exports, erasure alerts, and password resets — PB (OPS3)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — PB (OPS4)
- [ ] Document scheduled task setup for export monitoring in the runbook — PB (EXP2w)
- [x] Add program-level filtering to note search — consent filter in `_find_clients_with_matching_notes` + tests (PR #38) — 2026-02-24 — PB (PHIPA-SEARCH1)
- [x] Add consent filter to qualitative_summary view — cross-program consent enforcement + tests (PR #38) — 2026-02-24 — PB (PHIPA-QUAL1)
- [ ] Build cross-agency data rollup for partners — waiting on requirements re: which metrics to aggregate — PB, GK reviews metric aggregation (SCALE-ROLLUP1)
- [ ] Create AI-assisted admin toolkit decision documents (01-09) for agency setup — reformat deployment protocol into AI-consumable reference docs, test with [funder partner] dry run (see tasks/ai-assisted-admin-toolkit.md, docs/agency-setup-guide/) — (DEPLOY-TOOLKIT1)

## Do Occasionally

Step-by-step commands for each task are in [tasks/recurring-tasks.md](tasks/recurring-tasks.md).

- [ ] **UX walkthrough** — run after UI changes. In Claude Code: `pytest tests/ux_walkthrough/ -v`, then review `tasks/ux-review-latest.md` and add fixes to TODO (UX-WALK1)
- [ ] **Code review** — run every 2–4 weeks or before a production deploy. Open Claude Code and paste the review prompt from [tasks/code-review-process.md](tasks/code-review-process.md) (REV1)
- [ ] **Full QA suite** — run after major releases or substantial UI changes. Two pipelines (A then B), five sessions total — see [tasks/recurring-tasks.md](tasks/recurring-tasks.md) for full steps (QA-FULL1)
- [ ] **French translation spot-check** — have a French speaker review key screens. Run `python manage.py check_translations` to verify .po file coverage (I18N-REV1)
- [ ] **Redeploy to Railway** — after merging to main. Push to `main` and Railway auto-deploys (OPS-RAIL1)

## Coming Up

### Phase: QA Round 7 — Tier 2 Fixes (see tasks/qa-action-plan-2026-02-21.md)

- [x] Verify 8 items already implemented (BUG-4, BUG-8, BUG-11, IMPROVE-12/13, BLOCKER-2/3/5) — 2026-02-22 (QA-R7-TIER2-VERIFY)
- [x] Hide admin dropdown in nav for executive role (IMPROVE-3) — 2026-02-22 (QA-R7-NAV1)
- [x] Add "Log Communication" to client profile Actions dropdown (BUG-7) — 2026-02-22 (QA-R7-COMM1)
- [x] Add quarterly date range presets to ad-hoc report form (IMPROVE-4) — 2026-02-22 (QA-R7-RPT-QUARTER1)

### Phase: QA Round 7 — Page Audit Tier 2 (see tasks/qa-action-plan-2026-02-21-page-audit.md)

- [x] Fix groups-attendance: replace "--" with "N/R" (aria-label) + rename "Rate" to "Attendance Rate" — screen reader a11y — 2026-02-22 (QA-PA-ATTEND1)
- [x] Fix groups-attendance "1 sessions" pluralization — Django pluralize filter + French blocktrans — 2026-02-22 (QA-PA-ATTEND2)
- [x] Improve comm-my-messages empty state — distinguish "no messages yet" from "all read", add guidance text — 2026-02-22 (QA-PA-MSG1)
- [x] Add required-field indicator to comm-leave-message textarea — asterisk + aria-required — 2026-02-22 (QA-PA-MSG2)
- [x] Add onboarding context to plan-goal-create — collapsible 1-2 sentence explainer for new users — 2026-02-22 (QA-PA-GOAL1)
- [x] Add step indicator ("Step 1 of 2") to goal creation wizard — helps DS1c (ADHD) track progress — 2026-02-22 (QA-PA-GOAL2)
- [ ] Seed groups-attendance test data with 8+ members and 12+ sessions — fix in qa-scenarios repo (QA-PA-TEST1)
- [ ] Seed comm-my-messages populated state with actual messages — fix in qa-scenarios repo (QA-PA-TEST2)

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Data Quality

- [ ] Entry-time plausibility warnings — soft-flag unlikely values during data entry, prioritise financial metrics (see tasks/data-validation-design.md, financial subsection added 2026-02-20) (DQ1)
- [ ] Add second-tier "very unlikely" plausibility thresholds for financial metrics — tighter bounds beyond warn_max for edge case detection (DQ1-TIER2)
- [ ] Pre-report data quality checks — validate data quality before partner report export (see tasks/data-validation-design.md) (DQ2)
- [ ] Add partner report approval workflow — quality review, agency annotations, explicit publish step before sharing with partners (see tasks/funder-report-approval.md, plan: docs/plans/2026-02-20-funder-report-approval-design.md) (RPT-APPROVE1)

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

### Phase: CIDS Compliance (Common Approach Data Standard) — approved 2026-02-24

- [ ] Add CIDS metadata fields to MetricDefinition, Program, and PlanTarget — optional fields for IRIS+ codes, SDG goals, sector codes (see tasks/cids-json-ld-export.md Phase 1) — (CIDS-META1)
- [ ] Create OrganizationProfile model for CIDS BasicTier org metadata — legal name, sector, province (Phase 1) — (CIDS-ORG1)
- [ ] Import CIDS code lists (17 lists) via management command from codelist.commonapproach.org with version tracking (Phase 2) — (CIDS-CODES1)
- [ ] Build admin UI for CIDS tagging — dropdowns on program and metric forms, integrate into config template system (Phase 2) — (CIDS-ADMIN1)
- [ ] Add CIDS codes to existing CSV/PDF partner reports + "Standards Alignment" appendix page — quick win, no new format needed (Phase 2.5) — (CIDS-ENRICH1)
- [ ] Build JSON-LD export with basic SHACL validation — new format option alongside CSV/PDF, aggregate only (Phase 3) — (CIDS-EXPORT1)
- [ ] Compute CIDS impact dimensions (scale, depth, duration) from existing KoNote data — no new data entry (Phase 4) — (CIDS-IMPACT1)
- [ ] Add CIDS conformance badge and detailed validation reporting (Phase 5) — (CIDS-VALIDATE1)

### Phase: Other Upcoming

- [ ] Permissions Phase 2 — remaining 10 items: discharge access transitions, consent model, DV-safe mode, GATED clinical access, group schedule vs roster, per-field front desk edit, SCOPED→PROGRAM rename, partner report key, alert escalation, dashboard split (see tasks/permissions-expert-panel-2026-02-09.md) (PERM-P3–12)

### Phase: Advanced Reporting

- [x] Research typical nonprofit session reporting requirements (IRCC, CFPB, Employment Ontario, United Way) — key gap: need duration and modality fields on notes (see konote-prosper-canada/tasks/session-reporting-research.md) — 2026-02-24 (REP-REQ1)
- [ ] Build "Sessions by Participant" report template — count and type of sessions (Progress Note interactions) per participant (see konote-prosper-canada/tasks/session-reporting-research.md for field requirements) (REP-SESS1)
- [ ] Expand report template system to support more flexible data exports across various modules (REP-FLEX1)
- [x] Add "All Programs" option to report filters for organization-wide summaries — 2026-02-24 (REP-ALL-PROGS1)
- [ ] Implement report preview on-screen before downloading PDF/CSV (REP-PREVIEW1)
- [ ] Research/Implement including data visuals (charts/graphs) in PDF reports (REP-PDF1)
- [ ] Redesign PDF report layout: merge title page with page 2 to eliminate redundant empty space (REP-PDF2)
- [ ] Define standardised report schema for [funder partner] — 10-15 key metrics and demographic breakdowns shared across all partner agencies (RPT-SCHEMA1)

### Phase: Demo Data Quality

_Nothing pending._

### Phase: Surveys Future Work

- [ ] Build shareable link channel for public survey links without login (SURVEY-LINK1)
- [ ] Run `translate_strings` to extract and compile French translations for the new survey templates (SURVEY-I18N1)

### Phase: Documentation & Website Updates

- [ ] Create deployment documentation for surveys and portal features (DOC-DEPLOY1)
- [ ] Update technical documentation in GitHub for surveys and portal architecture (DOC-TECH1)
- [ ] Update website feature list and marketing copy to include surveys and portal (WEB-FEAT1)
- [ ] Add Evidence section to website — adapt docs/evidence-outcome-measurement.md into a public-facing page explaining the research behind KoNote's outcome measurement approach (see tasks/web-evidence-prompt.md) (WEB-EVIDENCE1)

### Phase: QA Round 7 — Page Audit Tier 1 (see tasks/qa-action-plan-2026-02-21-page-audit.md)

- [x] Create custom styled 500.html template — standalone, bilingual, branded fallback for all unhandled errors — 2026-02-22 (QA-PA-500)
- [x] Fix public unsubscribe page returning 500 — CASL compliance, safety net for import/token errors — 2026-02-22 (QA-PA-BLOCKER4)
- [x] Fix public survey link page returning 500 — try/except renders "survey unavailable" instead of raw 500 — 2026-02-22 (QA-PA-BLOCKER3)
- [x] Fix plan-goal-create heading "Add Target" → "Add a Goal" — terminology migration artifact — 2026-02-22 (QA-PA-BUG1)

## Parking Lot

- [ ] Add PIPEDA compliance context to admin-erasure-requests page — explain what gets deleted vs. retained — GK reviews privacy/data retention (QA-PA-ERASURE1)
- [ ] PIPEDA data export from client profile — "Export Data" action for Section 8 access requests, needs design for data categories and output format — GK reviews privacy workflow (QA-R7-PRIVACY1)
- [ ] Consent withdrawal workflow on client profile — wizard for PIPEDA consent withdrawal with data retention rules — GK reviews privacy/data retention (QA-R7-PRIVACY2)
- [ ] Executive compliance report — aggregate dashboard showing privacy request counts, processing times (no PII) — GK reviews reporting methodology (QA-R7-EXEC-COMPLIANCE1)
- [ ] Verify accented character preservation through create/save/display cycle — may be test data issue, needs manual check (QA-R7-BUG13)
- [ ] Verify form data preservation after validation error on create-participant — medium confidence, may be test artefact (QA-R7-BUG21)
- [ ] Accessibility polish: status dropdown auto-open on Tab, colour-only status indicator fix (remaining from QA-R7-A11Y2) (A11Y-POLISH1)
- [ ] DQ1 implementation: build threshold tuning feedback from day one — admin view of warnings triggered vs overridden per metric (DQ1-TUNE)
- [ ] DQ2 implementation: define severity tiers so the quality gate doesn't produce too many warnings that staff ignore (DQ2-TIERS)
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
- [ ] Add deferred execution for Tier 3 erasure (24-hour delay) (ERASE-H8)
- [ ] Implement deployment workflow enhancements (see docs/plans/2026-02-05-deployment-workflow-design.md) (DEPLOY1)
- [ ] Document scenario_loader cache lifetime if reused outside pytest (QA-W62)
- [ ] Separate "Scheduled Assessment" workflow for standardized instruments (PHQ-9, etc.) — partner reporting (ASSESS1)
- [ ] Metric cadence system — only prompt for metric values when due, configurable per metric (METRIC-CADENCE1)
- [ ] 90-day metric relevance check — prompt worker to confirm or change the chosen metric (METRIC-REVIEW1)
- [ ] Alliance Repair Guide — one-page printable guide for workers when participants rate low (ALLIANCE-GUIDE1)
- [ ] Participant-facing progress view — show descriptor timeline to participant in portal (PORTAL-PROGRESS1)
- [ ] Alliance prompt rotation — cycle 3-4 phrasings to prevent habituation (ALLIANCE-ROTATE1)
- [ ] Portal-based async alliance rating — post-session notification for participant self-rating (PORTAL-ALLIANCE1)

## Recently Done

- [x] Insights Phase 5 — workbench-to-report links, board summary PDF, CLAUDE.md DRR reference, French translation sweep (100% coverage) — 2026-02-24 (INSIGHTS-P5-POLISH)
- [x] Replace erasure empty state circle with shield icon — a11y, reusable pattern — 2026-02-24 (QA-PA-ERASURE2)
- [x] Add breadcrumbs to goal creation page — Participants > Name > Plan > Add a Goal — 2026-02-24 (QA-PA-GOAL3)
- [x] Verify deploy-azure.md reference — file moved to docs/archive/deploy-azure.md; updated phase-7-prompt.md reference — 2026-02-24 (DEPLOY-VERIFY1)
- [x] Tidy `import datetime as dt` placement in reports/views.py — cosmetic import ordering — 2026-02-24 (CODE-TIDY1)
- [x] Approve CIDS implementation plan — metadata fields, code list integration, CIDS-enriched reports, JSON-LD export; partner pathway confirmed — 2026-02-24 — SG/GK (CIDS-APPROVE1)
- [x] PHIPA consent filtering for note search and qualitative summary — program-level filter + tests (PR #38) — 2026-02-24 — PB (PHIPA-SEARCH1, PHIPA-QUAL1)
- [x] All Programs report filter — "__all__" sentinel in MetricExportForm + FunderReportForm, multi-program aggregation, RBAC-scoped, 18 tests — 2026-02-24 (REP-ALL-PROGS1)
- [x] Executive dashboard metric indicators — trend direction, data completeness, urgent themes per program card, batch query, 2 tests — 2026-02-24 (INSIGHTS-P3-EXEC)
- [x] French translations — all 54 remaining empty strings translated and compiled — 2026-02-24 (INSIGHTS-I18N1)
- [x] Achievement metric seed data + recording UI — 3 achievement metrics in library, demo data for 9 clients, radio pill UI in note form with validation + CSS + tests — 2026-02-24 (INSIGHTS-P0-SEED, INSIGHTS-P4-RECORD)
- [x] Offline Field Collection — full feature: models, ODK client, sync command, admin UI, 4 PII tiers, 43 tests, 2 code reviews, French translations (PR #34) — 2026-02-24 (FIELD-ODK-APP1–TEST1)
- [x] Approve four-tier PII model for offline field devices — 2026-02-24 — GK (FIELD-ODK-GK1)
- [x] Circles Lite Phase 1 — full feature: models, views, templates, nav, sidebar, note tagging, intake, tests, translations — 2026-02-24 (CIRCLES-1–9)
- [x] Enforce PHIPA cross-program consent in views — note_detail, note_summary, event_list; fix fail-open bug; fix CONF9 interaction; shared banner include; 4 new tests; DRR created — 2026-02-22 (PHIPA-ENFORCE1)
- [x] Insights metric distributions Phases 0-2 — model fields, aggregation, distributions, achievements, trends, Two Lenses, data completeness, 50 tests, 10 review fixes (PR #23) — 2026-02-22 (INSIGHTS-P0-ADMIN, INSIGHTS-P1-MODEL, INSIGHTS-P1-AGG, INSIGHTS-P2-LAYOUT, INSIGHTS-P2-VIZ)
- [x] Approve band display labels — "More support needed" / "On track" / "Goals within reach" — 2026-02-22 — GK (INSIGHTS-LANG1)
- [x] QA Page Audit Tier 1 + Tier 2 — 500.html standalone, public view hardening, goal heading/onboarding/steps, attendance a11y, messages UX, leave-message required field, translations (PR #20) — 2026-02-22 (QA-PA-TIER1-2)
- [x] Fix suggestion theme linking in seed_demo_data — program-specific suggestions, removed blind fallback — 2026-02-22 (DEMO-FIX1)
- [x] Add quarterly date range presets to ad-hoc report form — optgroup dropdown with FY + quarters, i18n month names, 8 tests — 2026-02-22 (QA-R7-RPT-QUARTER1)
- [x] QA Round 7 Tier 2 — verified 8 items already implemented, fixed IMPROVE-3 (executive nav) and BUG-7 (log communication) — 2026-02-22 (QA-R7-TIER2)
- [x] Scenario YAML URL fixes — updated 7 files in konote-qa-scenarios repo from /admin/ to /manage/ paths (PR #14) — 2026-02-22 (QA-R7-YAML1)
- [x] QA Round 7 Tier 1 — language persistence, skip-to-content verified, notes 403 fixed, htmx syntax fixed — 2026-02-21 (QA-R7-TIER1)
- [x] Fix report generation page — duplicate template name in dropdown and HTMX period options 500 error (PR #14) — 2026-02-22 (BUG-RPT1)
- [x] Code review fixes for template-driven reporting — 12 issues (suppression, WCAG, XSS, race condition, tests) (PR #12) — 2026-02-22 (RPT-REVIEW1)
- [x] Aggregation engine + consortium metric locking for ad-hoc export form — 2026-02-22 (RPT-AGG1)
- [x] UX + QA Round 7 fixes — 18 items: accessibility, dashboard, notes UX, front desk, label improvements — 2026-02-21
- [x] Unify analysis chart quick-select and date picker into single form control — 2026-02-21 (UX-CHART1)
- [x] Accessibility fixes: aria-labels on audit table, notes error container, mobile touch targets — 2026-02-21 (A11Y-UX1)
