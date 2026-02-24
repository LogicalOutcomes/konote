# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire before first agency deployment (see tasks/agency-permissions-interview.md) — SG (ONBOARD-APPROVE)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — SG (SEC3-Q1)
- [ ] Confirm standard report schema and configuration template with partner contact before building — SG (RPT-SCHEMA1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)

## Active Work

### Phase: Insights Metric Distributions (see tasks/design-rationale/insights-metric-distributions.md, tasks/insights-metrics-implementation.md)

- [ ] Phase 4: Achievement metric recording UI — dropdown in note form, tests (INSIGHTS-P4-RECORD)
- [ ] Phase 5: Workbench-to-report links, board summary template, translations, docs (INSIGHTS-P5-POLISH)

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

### Phase: Documentation & Website Updates

- [ ] Create deployment documentation for surveys and portal features (DOC-DEPLOY1)
- [ ] Update technical documentation in GitHub for surveys and portal architecture (DOC-TECH1)
- [ ] Update website feature list and marketing copy to include surveys and portal (WEB-FEAT1)
- [ ] Add Evidence section to website — adapt docs/evidence-outcome-measurement.md into a public-facing page explaining the research behind KoNote's outcome measurement approach (see tasks/web-evidence-prompt.md) (WEB-EVIDENCE1)

## Parking Lot

- [ ] Add PIPEDA compliance context to admin-erasure-requests page — show selected tier's consequences in plain language (see tasks/erasure-compliance-context.md) — GK approved 2026-02-24 (QA-PA-ERASURE1)
- [ ] PIPEDA data access request — guided manual checklist + 30-day tracking, not automated export (see tasks/pipeda-data-access-checklist.md) — GK approved 2026-02-24 (QA-R7-PRIVACY1)
- [ ] Note sharing toggle on client profile — binary On/Off, PM/admin only, hidden when agency sharing is off (see tasks/note-sharing-toggle.md) — GK approved 2026-02-24 (QA-R7-PRIVACY2)
- [ ] Privacy compliance banner + annual summary — event-driven pending-request banner on exec dashboard, one-line board report summary (see tasks/compliance-banner.md) — GK approved 2026-02-24 (QA-R7-EXEC-COMPLIANCE1)
- [ ] Seed groups-attendance test data with 8+ members and 12+ sessions — add to seed_demo_data or fixture (QA-PA-TEST1)
- [ ] Seed comm-my-messages populated state with actual messages — add to seed_demo_data (QA-PA-TEST2)
- [ ] Add axe-core pass to `/capture-page-states` — automated WCAG checks for screen reader/speech recognition coverage (T59)
- [ ] Verify BLOCKER-1 and BLOCKER-2 with manual keyboard/JAWS test — requires human testing with assistive tech (T50)
- [ ] DQ1 implementation: build threshold tuning feedback from day one — admin view of warnings triggered vs overridden per metric (DQ1-TUNE)
- [ ] DQ2 implementation: define severity tiers so the quality gate doesn't produce too many warnings that staff ignore (DQ2-TIERS)
- [ ] Add stress testing for 50+ concurrent users (QA-T15)
- [ ] Add legacy system import migration scenario test (QA-T16)
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
- [ ] Add deferred execution for Tier 3 erasure (24-hour delay) (ERASE-H8)
- [ ] Implement deployment workflow enhancements (see docs/plans/2026-02-05-deployment-workflow-design.md) (DEPLOY1)
- [ ] Separate "Scheduled Assessment" workflow for standardized instruments (PHQ-9, etc.) — partner reporting (ASSESS1)
- [ ] Metric cadence system — only prompt for metric values when due, configurable per metric (METRIC-CADENCE1)
- [ ] 90-day metric relevance check — prompt worker to confirm or change the chosen metric (METRIC-REVIEW1)
- [ ] Alliance Repair Guide — one-page printable guide for workers when participants rate low (ALLIANCE-GUIDE1)
- [ ] Participant-facing progress view — show descriptor timeline to participant in portal (PORTAL-PROGRESS1)
- [ ] Alliance prompt rotation — cycle 3-4 phrasings to prevent habituation (ALLIANCE-ROTATE1)
- [ ] Portal-based async alliance rating — post-session notification for participant self-rating (PORTAL-ALLIANCE1)

## Recently Done

- [x] Parking lot cleanup Phase 2 — UX polish: clipboard icon on empty states (QA-PA-ERASURE2), goal form breadcrumbs (QA-PA-GOAL3), status badge shape indicators + filter focus ring (A11Y-POLISH1), onboarding banner (QA-W19) — 2026-02-24
- [x] Parking lot cleanup Phase 1 — code hygiene (CODE-TIDY1, QA-W62), verification (QA-R7-BUG13, QA-R7-BUG21, SURVEY-LINK1, DEPLOY-VERIFY1), i18n (I18N-CSV1, I18N-STALE1 already clean, INSIGHTS-I18N1, SURVEY-I18N1 already translated) — 2026-02-24
- [x] Approve CIDS implementation plan — metadata fields, code list integration, CIDS-enriched reports, JSON-LD export; partner pathway confirmed — 2026-02-24 — SG/GK (CIDS-APPROVE1)
- [x] Insights Phase 3: executive dashboard program learning cards — trend direction, data completeness, feedback themes, 84 French translations, 14 tests — 2026-02-24 (INSIGHTS-P3-EXEC, INSIGHTS-I18N1)
- [x] PHIPA: add consent filtering to note search and qualitative_summary — program-level filtering prevents side-channel disclosure, 6 new tests — 2026-02-24 (PHIPA-SEARCH1, PHIPA-QUAL1)
- [x] Enforce PHIPA cross-program consent in views — note_detail, note_summary, event_list; fix fail-open bug; fix CONF9 interaction; shared banner include; 4 new tests; DRR created — 2026-02-22 (PHIPA-ENFORCE1)
- [x] Insights metric distributions Phases 0-2 — model fields, aggregation, distributions, achievements, trends, Two Lenses, data completeness, 50 tests, 10 review fixes (PR #23) — 2026-02-22 (INSIGHTS-P0-ADMIN, INSIGHTS-P1-MODEL, INSIGHTS-P1-AGG, INSIGHTS-P2-LAYOUT, INSIGHTS-P2-VIZ)
- [x] Approve band display labels — "More support needed" / "On track" / "Goals within reach" — 2026-02-22 — GK (INSIGHTS-LANG1)
- [x] QA Page Audit Tier 1 + Tier 2 — 500.html standalone, public view hardening, goal heading/onboarding/steps, attendance a11y, messages UX, leave-message required field, translations (PR #20) — 2026-02-22 (QA-PA-TIER1-2)
- [x] Fix suggestion theme linking in seed_demo_data — program-specific suggestions, removed blind fallback — 2026-02-22 (DEMO-FIX1)
- [x] Add quarterly date range presets to ad-hoc report form — optgroup dropdown with FY + quarters, i18n month names, 8 tests — 2026-02-22 (QA-R7-RPT-QUARTER1)
- [x] QA Round 7 Tier 2 — verified 8 items already implemented, fixed IMPROVE-3 (executive nav) and BUG-7 (log communication) — 2026-02-22 (QA-R7-TIER2)
- [x] Scenario YAML URL fixes — updated 7 files in konote-qa-scenarios repo from /admin/ to /manage/ paths (PR #14) — 2026-02-22 (QA-R7-YAML1)
- [x] Fix report generation page — duplicate template name in dropdown and HTMX period options 500 error (PR #14) — 2026-02-22 (BUG-RPT1)
- [x] Code review fixes for template-driven reporting — 12 issues (suppression, WCAG, XSS, race condition, tests) (PR #12) — 2026-02-22 (RPT-REVIEW1)
