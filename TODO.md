# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire before first agency deployment (see tasks/agency-permissions-interview.md) — SG (ONBOARD-APPROVE)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — SG (SEC3-Q1)
- [ ] Confirm standard report schema and configuration template with partner contact before building — SG (RPT-SCHEMA1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)

## Active Work

### Phase: Offline Field Collection (remaining items — code merged via PR #34)

- [ ] Deploy ODK Central on Canadian VM (Docker Compose) — ops task (FIELD-ODK-DEPLOY1)
- [ ] Circle Observation XLSForm — depends on circles in ODK (FIELD-ODK-FORM-CIR1)
- [ ] Push Circle/CircleMember Entity lists — depends on above (FIELD-ODK-CIRCLES1)
- [ ] Agency-facing documentation — ODK Collect setup, device loss protocol (FIELD-ODK-DOC1)

### Phase: Launch Readiness

- [ ] Complete Agency Deployment Protocol with [funder partner] — Phase 0 Discovery Call first (see tasks/deployment-protocol.md) — (DEPLOY-PC1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [ ] Complete Agency Permissions Interview and signed Configuration Summary before first deployment — SG (ONBOARD-GATE)
- [ ] Store signed Configuration Summary with each deployment so new admins can see what was decided and why — SG (DEPLOY-CONFIG-DOC1)
- [ ] Verify production email configuration for exports, erasure alerts, and password resets — PB (OPS3)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — PB (OPS4)
- [ ] Document scheduled task setup for export monitoring in the runbook — PB (EXP2w)
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

Blocked on infrastructure (dedicated sprint):
- [ ] GATED clinical access for PM — build justification UI + time-boxing; `client.view_clinical` must move from ALLOW to GATED (highest-priority Phase 2 item) — GK reviews (PERM-P6)
- [ ] Per-field front desk edit — build admin UI to configure which contact fields receptionist can edit (prerequisite for P5) (PERM-P8)
- [ ] DV-safe mode — hide address/emergency contact from front desk when DV flag set; blocked on PERM-P8 — GK reviews (PERM-P5)

### Phase: Advanced Reporting

- [x] Build "Sessions by Participant" report — duration/modality fields on ProgressNote, aggregation engine, CSV export, 26 tests — 2026-02-24 (REP-SESS1)
- [ ] Expand report template system to support more flexible data exports across various modules (REP-FLEX1)
- [x] Add "All Programs" option to report filters for organization-wide summaries — 2026-02-24 (REP-ALL-PROGS1)
- [x] Report preview on-screen before downloading — two preview views (template + ad-hoc), RBAC, print CSS, 33 tests — 2026-02-24 (REP-PREVIEW1)
- [x] Add data visualisations (charts/graphs) to PDF reports — matplotlib chart_utils.py, accessible colours, hatch patterns — 2026-02-24 (REP-PDF1)
- [x] Merge PDF title page with page 2 — compact header across all 6 PDF templates — 2026-02-24 (REP-PDF2)
- [ ] Define standardised report schema for [funder partner] — 10-15 key metrics and demographic breakdowns shared across all partner agencies (RPT-SCHEMA1)

### Phase: Surveys Future Work

- [ ] Build shareable link channel for public survey links without login (SURVEY-LINK1)

### Phase: Documentation & Website Updates

- [ ] Create deployment documentation for surveys and portal features (DOC-DEPLOY1)
- [ ] Update technical documentation in GitHub for surveys and portal architecture (DOC-TECH1)
- [ ] Update website feature list and marketing copy to include surveys and portal (WEB-FEAT1)
- [ ] Add Evidence section to website — adapt docs/evidence-outcome-measurement.md into a public-facing page explaining the research behind KoNote's outcome measurement approach (see tasks/web-evidence-prompt.md) (WEB-EVIDENCE1)

## Parking Lot

- [ ] Add axe-core pass to `/capture-page-states` — automated WCAG checks for screen reader/speech recognition coverage (T59)
- [ ] PIPEDA data export from client profile — "Export Data" action for Section 8 access requests, needs design for data categories and output format — GK reviews privacy workflow (QA-R7-PRIVACY1)
- [ ] Consent withdrawal workflow on client profile — wizard for PIPEDA consent withdrawal with data retention rules — GK reviews privacy/data retention (QA-R7-PRIVACY2)
- [ ] Executive compliance report — aggregate dashboard showing privacy request counts, processing times (no PII) — GK reviews reporting methodology (QA-R7-EXEC-COMPLIANCE1)
- [ ] Verify BLOCKER-1 and BLOCKER-2 with manual JAWS test — automated Playwright tests pass, manual assistive tech testing still needed (T50)
- [ ] DQ1 implementation: build threshold tuning feedback from day one — admin view of warnings triggered vs overridden per metric (DQ1-TUNE)
- [ ] DQ2 implementation: define severity tiers so the quality gate doesn't produce too many warnings that staff ignore (DQ2-TIERS)
- [ ] Add stress testing for 50+ concurrent users (QA-T15)
- [ ] Add legacy system import migration scenario test (QA-T16)
- [ ] Implement multi-session testing for SCN-046 shared device scenario (QA-W55)
- [ ] Add serious reportable events workflow and reporting (see tasks/serious-reportable-events.md) (SRE1)
- [ ] Build agency data offboarding command for secure departures and PIPEDA requests (SEC3)
- [ ] Add in-app configuration dashboard showing all active settings with decision rationale and change history (DEPLOY-CONFIG-UI1)
- [ ] Optimize encrypted client search performance beyond ~2000 records (PERF1)
- [ ] Seed groups-attendance test data with 8+ members and 12+ sessions — fix in qa-scenarios repo (QA-PA-TEST1)
- [ ] Seed comm-my-messages populated state with actual messages — fix in qa-scenarios repo (QA-PA-TEST2)
- [ ] Separate "Scheduled Assessment" workflow for standardized instruments (PHQ-9, etc.) — partner reporting (ASSESS1)
- [ ] Metric cadence system — only prompt for metric values when due, configurable per metric (METRIC-CADENCE1)
- [ ] 90-day metric relevance check — prompt worker to confirm or change the chosen metric (METRIC-REVIEW1)
- [ ] Alliance prompt rotation — cycle 3-4 phrasings to prevent habituation (ALLIANCE-ROTATE1)
- [ ] Portal-based async alliance rating — post-session notification for participant self-rating (PORTAL-ALLIANCE1)

## Recently Done

- [x] Verified: surveys already implemented — full apps/surveys/ with models, views, forms, tests, migrations — 2026-02-24 (SURVEY1)
- [x] Verified: first-run setup wizard already implemented — 8-step guided configuration in admin settings — 2026-02-24 (SETUP1-UI)
- [x] Verified: deployment workflow enhancements already implemented — is_demo flag, seed command, demo/real separation — 2026-02-24 (DEPLOY1)
- [x] Verified: participant-facing progress view already implemented — descriptor timeline in portal — 2026-02-24 (PORTAL-PROGRESS1)
- [x] Re-add API-based auto-translation to translate_strings — `--auto-translate` flag, OpenAI-compatible API, 21 tests (PR #63) — 2026-02-24 (I18N-API1)
- [x] Alliance Repair Guide — printable one-pager based on FIT principles, print CSS, help link in note form, 3 tests, GK reviews content (PR #62) — 2026-02-24 (ALLIANCE-GUIDE1)
- [x] Bulk operations for discharge and program assignment — checkboxes, sticky action bar, HTMX modals, 7 tests (PR #64) — 2026-02-24 (UX17)
- [x] Code review fixes (14 of 15 findings) — All Programs guard, age breakdown loop, aria-labels, PHIPA comment, export_type, permission tests, cross-program tests, audit log tests, role=grid removal, erasure badges, hardcoded URLs, ARIA state, modality null→default, innerHTML→HTMX, CSV string fix (PR #58) — 2026-02-24 (REVIEW-FIX1–15)
- [x] Parking lot + Advanced Reporting parallel cleanup (15 items in 7 agents, 2 waves) — 2026-02-24 (QA-PA-ERASURE1, QA-PA-ERASURE2, QA-R7-BUG13, QA-R7-BUG21, A11Y-POLISH1, QA-W19, DEPLOY-VERIFY1, CODE-TIDY1, QA-W62, I18N-STALE1, I18N-CSV1, REP-SESS1, REP-PREVIEW1, REP-PDF1, REP-PDF2)
- [x] PHIPA consent filtering for note search and qualitative summary — 3 tests (PR pending) — 2026-02-24 (PHIPA-SEARCH1, PHIPA-QUAL1)
