# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire before first agency deployment (see tasks/agency-permissions-interview.md) — GK (ONBOARD-APPROVE)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — GK (SEC3-Q1)
- [ ] Confirm standard report schema and configuration template with partner contact before building — SG (RPT-SCHEMA1)
- [ ] Approve CIDS implementation plan with project lead before building — covers metadata fields, code list integration, CIDS-enriched reports, and full JSON-LD export; confirm partner consumption pathway and whether to engage Common Approach as pilot implementer (see tasks/cids-json-ld-export.md) — SG/GK (CIDS-APPROVE1)
- [ ] Approve band display labels and clinical thresholds for insights metric distributions — hard blocker on Phase 2 template work (see tasks/design-rationale/insights-metric-distributions.md, Phase 0) — GK (INSIGHTS-LANG1)
- [ ] Discuss: are Design Rationale Records (DRRs) working well as a practice? Should we keep using them, change the format, or retire them? — GK (PROCESS-DRR1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)

## Active Work

### Phase: Insights Metric Distributions (see tasks/design-rationale/insights-metric-distributions.md, tasks/insights-metrics-implementation.md)

- [ ] Phase 0: GK language review — band labels, clinical thresholds, achievement examples, Two Lenses wording — HARD BLOCKER on Phase 2 (INSIGHTS-P0-LANG)
- [x] Phase 0: Update MetricDefinition admin form with new fields (metric_type, thresholds, achievement options, targets) — 2026-02-24 (INSIGHTS-P0-ADMIN)
- [ ] Phase 0: Configure at least one test program with achievement metrics for development (INSIGHTS-P0-SEED)
- [x] Phase 1: Add metric_type, threshold, achievement, and target fields to MetricDefinition model — 2026-02-24 (INSIGHTS-P1-MODEL)
- [x] Phase 1: Build metric aggregation functions — distributions, achievement rates, trends, Two Lenses, data completeness — 2026-02-24 (INSIGHTS-P1-AGG)
- [ ] Phase 2: Restructure insights page — participant voice to Section 2, progressive disclosure with smart auto-expand (INSIGHTS-P2-LAYOUT)
- [ ] Phase 2: Add summary cards, distribution bars, achievement bars with journey context, CSS (INSIGHTS-P2-VIZ)
- [ ] Phase 3: Update executive dashboard — program cards with trend direction, data completeness, feedback themes (INSIGHTS-P3-EXEC)
- [ ] Phase 4: Achievement metric recording UI — dropdown in note form, tests (INSIGHTS-P4-RECORD)
- [ ] Phase 5: Workbench-to-report links, board summary template, translations, docs (INSIGHTS-P5-POLISH)

### Phase: Launch Readiness

- [ ] Complete Agency Deployment Protocol with [funder partner] — Phase 0 Discovery Call first (see tasks/deployment-protocol.md) — (DEPLOY-PC1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [ ] Complete Agency Permissions Interview and signed Configuration Summary before first deployment — SG (ONBOARD-GATE)
- [ ] Store signed Configuration Summary with each deployment so new admins can see what was decided and why — SG (DEPLOY-CONFIG-DOC1)
- [ ] Incorporate logo from KoNote Classic repo into the web app branding — PB (UI-LOGO1)
- [ ] Verify production email configuration for exports, erasure alerts, and password resets — PB (OPS3)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — PB (OPS4)
- [ ] Document scheduled task setup for export monitoring in the runbook — PB (EXP2w)
- [ ] Enforce cross-program sharing consent (PHIPA) in views — consent flag already captured, need view-level enforcement — PB (PHIPA-ENFORCE1)
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

- [x] Fix groups-attendance: replace "--" with "N/R" (aria-label) + rename "Rate" to "Attendance Rate" — 2026-02-24 (QA-PA-ATTEND1)
- [x] Fix groups-attendance "1 sessions" pluralization — blocktrans count syntax — 2026-02-24 (QA-PA-ATTEND2)
- [x] Improve comm-my-messages empty state — distinguish "no messages yet" from "all read", add guidance text — 2026-02-24 (QA-PA-MSG1)
- [x] Add required-field indicator to comm-leave-message textarea — asterisk + aria-required — 2026-02-24 (QA-PA-MSG2)
- [x] Add onboarding context to plan-goal-create — collapsible explainer for new users — 2026-02-24 (QA-PA-GOAL1)
- [x] Add step indicator ("Step 1 of 2") to goal creation wizard — 2026-02-24 (QA-PA-GOAL2)
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

### Phase: CIDS Compliance (Common Approach Data Standard) — waiting on CIDS-APPROVE1

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

- [ ] Research typical nonprofit session reporting requirements (UNHCR, IRCC, CCIS, etc.) to design "Sessions by Participant" report (REP-REQ1)
- [ ] Build "Sessions by Participant" report template — count and type of sessions (Progress Note interactions) per participant (REP-SESS1)
- [ ] Expand report template system to support more flexible data exports across various modules (REP-FLEX1)
- [ ] Add "All Programs" option to report filters for organization-wide summaries (REP-ALL-PROGS1)
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

- [ ] Create custom styled 500.html template — bilingual, branded fallback for all unhandled errors (QA-PA-500)
- [ ] Fix public unsubscribe page returning 500 — CASL compliance, must work before any agency enables email (depends on QA-PA-500) (QA-PA-BLOCKER4)
- [ ] Fix public survey link page returning 500 — community members see raw error from email/flyer links (depends on QA-PA-500) (QA-PA-BLOCKER3)
- [ ] Fix plan-goal-create heading "Add Target" → "Add Goal" — terminology migration artifact, 5-min fix (QA-PA-BUG1)

## Parking Lot

- [ ] Add PIPEDA compliance context to admin-erasure-requests page — explain what gets deleted vs. retained — GK reviews privacy/data retention (QA-PA-ERASURE1)
- [ ] Replace decorative circular element on erasure empty state with static icon — cosmetic, low priority (QA-PA-ERASURE2)
- [ ] Add breadcrumbs to plan-goal-create (Participants > Name > Plan > Add Goal) — navigation aid for new users (QA-PA-GOAL3)
- [ ] PIPEDA data export from client profile — "Export Data" action for Section 8 access requests, needs design for data categories and output format — GK reviews privacy workflow (QA-R7-PRIVACY1)
- [ ] Consent withdrawal workflow on client profile — wizard for PIPEDA consent withdrawal with data retention rules — GK reviews privacy/data retention (QA-R7-PRIVACY2)
- [ ] Executive compliance report — aggregate dashboard showing privacy request counts, processing times (no PII) — GK reviews reporting methodology (QA-R7-EXEC-COMPLIANCE1)
- [ ] Verify accented character preservation through create/save/display cycle — may be test data issue, needs manual check (QA-R7-BUG13)
- [ ] Verify form data preservation after validation error on create-participant — medium confidence, may be test artefact (QA-R7-BUG21)
- [ ] Accessibility polish: status dropdown auto-open on Tab, colour-only status indicator fix (remaining from QA-R7-A11Y2) (A11Y-POLISH1)
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
- [ ] Add deferred execution for Tier 3 erasure (24-hour delay) (ERASE-H8)
- [ ] Implement deployment workflow enhancements (see docs/plans/2026-02-05-deployment-workflow-design.md) (DEPLOY1)
- [ ] Document scenario_loader cache lifetime if reused outside pytest (QA-W62)
- [ ] Tidy `import datetime as dt` placement in reports/views.py — cosmetic import ordering (CODE-TIDY1)
- [ ] Separate "Scheduled Assessment" workflow for standardized instruments (PHQ-9, etc.) — partner reporting (ASSESS1)
- [ ] Metric cadence system — only prompt for metric values when due, configurable per metric (METRIC-CADENCE1)
- [ ] 90-day metric relevance check — prompt worker to confirm or change the chosen metric (METRIC-REVIEW1)
- [ ] Alliance Repair Guide — one-page printable guide for workers when participants rate low (ALLIANCE-GUIDE1)
- [ ] Participant-facing progress view — show descriptor timeline to participant in portal (PORTAL-PROGRESS1)
- [ ] Alliance prompt rotation — cycle 3-4 phrasings to prevent habituation (ALLIANCE-ROTATE1)
- [ ] Portal-based async alliance rating — post-session notification for participant self-rating (PORTAL-ALLIANCE1)

## Recently Done

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
