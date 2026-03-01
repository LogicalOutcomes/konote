# Project Tasks

## Flagged

- [ ] Contact Common Approach to position KoNote as a pilot CIDS implementer — early engagement for co-marketing and advance notice of spec changes — GK (CIDS-CA-OUTREACH1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)

## Active Work

### Phase: Launch Readiness

- [ ] Run deployment protocol with [funder partner] — currently at Phase 0 (see tasks/deployment-protocol.md, tasks/hosting-cost-comparison.md) — SG (DEPLOY-PC1)
- [ ] Discuss data handling acknowledgement during permissions interview — plaintext backup opt-in, designate contact person (see docs/data-handling-acknowledgement.md, deployment-protocol.md Phase 1) — SG (DEPLOY-DHA1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — PB (OPS4)
- [ ] Build cross-agency data rollup for partners — waiting on requirements re: which metrics to aggregate — PB, GK reviews metric aggregation (SCALE-ROLLUP1)
- [ ] Create AI-assisted admin toolkit decision documents (01-09) for agency setup — reformat deployment protocol into AI-consumable reference docs, test with [funder partner] dry run (see tasks/ai-assisted-admin-toolkit.md, docs/agency-setup-guide/). Document 10 (Data Responsibilities) is done — (DEPLOY-TOOLKIT1)
- [ ] Review and merge data handling acknowledgement PR #130 — expanded to cover encryption key custody, SharePoint/Google Drive responsibilities, exports, plaintext backups, staff departures. Wired into deployment protocol Phases 0/4/5. Needs legal review before first agency use (see docs/data-handling-acknowledgement.md) — GK (SEC3-AGREE1)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — SG (SEC3-Q1)
- [ ] Draft SaaS service agreement for LogicalOutcomes-managed agencies — data processing, security, SLAs, breach notification, termination, data export acknowledgement as schedule. Needs lawyer review (see tasks/saas-service-agreement.md) — GK (LEGAL-SaaS1)

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
- [ ] Define managed service model — who handles infrastructure, backups, updates, support tiers, funding model (see tasks/hosting-cost-comparison.md, tasks/design-rationale/ovhcloud-deployment.md) (OPS-MANAGED1)
- [ ] Build cross-agency reporting API — standardised endpoint per instance for [funder partner] to consume published reports (plan: docs/plans/2026-02-20-cross-agency-reporting-api-design.md) (SCALE-API1)
- [ ] Build umbrella admin dashboard — central view for [funder partner] to see instance health, published reports, and aggregate metrics across agencies (SCALE-DASH1)
- [ ] Improve admin UI for self-service configuration — better guidance for terminology, metrics, templates (ADMIN-UX1)
- [ ] Align report-template.json "bins" field naming with DemographicBreakdown model's "bins_json" when building Phase 2 template automation (TEMPLATE-ALIGN1)

### Phase: FHIR-Informed Data Foundations + CIDS Compliance — interleaved sequence, quick win for funders before heavier model work (see tasks/fhir-informed-data-modelling.md, tasks/cids-json-ld-export.md, tasks/design-rationale/fhir-informed-modelling.md)

- [x] Add CIDS metadata fields + OrganizationProfile — PR #131 (CIDS-META1 + CIDS-ORG1)
- [x] Import CIDS code lists + TaxonomyMapping model — PR #131 (CIDS-CODES1)
- [x] Build admin UI for CIDS tagging — PR #131 (CIDS-ADMIN1)
- [x] Add CIDS codes to reports + Standards Alignment appendix — PR #131 (CIDS-ENRICH1)
- [x] Extend ClientProgramEnrolment into ServiceEpisode — PR #131 (FHIR-EPISODE1)
- [x] Populate new ServiceEpisode fields from existing data — PR #131 (FHIR-MIGRATE1)
- [x] Add achievement_status + first_achieved_at to PlanTarget — PR #131 (FHIR-ACHIEVE1)
- [x] Add author_role to ProgressNote — PR #131 (FHIR-ROLE1)
- [x] Build JSON-LD export + impact dimensions — PR #131 (CIDS-EXPORT1 + CIDS-IMPACT1)
- [x] Review fix: on-hold visibility, translations, bulk transfer audit, form fix, regression test — 2026-02-27 (CIDS-REVIEW-FIX1)

### Phase: Offline Field Collection (if requested by client)

- [ ] Deploy ODK Central on Canadian VM (Docker Compose) — ops task (FIELD-ODK-DEPLOY1)
- [ ] Circle Observation XLSForm — depends on circles in ODK (FIELD-ODK-FORM-CIR1)
- [ ] Push Circle/CircleMember Entity lists — depends on above (FIELD-ODK-CIRCLES1)
- [ ] Agency-facing documentation — ODK Collect setup, device loss protocol (FIELD-ODK-DOC1)

### Phase: Surveys Future Work

- [ ] Build shareable link channel for public survey links without login (SURVEY-LINK1)

### Phase: Documentation & Website Updates

- [ ] Create deployment documentation for surveys and portal features (DOC-DEPLOY1)
- [ ] Update technical documentation in GitHub for surveys and portal architecture (DOC-TECH1)
- [ ] Write client-facing guide for demo data engine — how to use the admin UI, when to regenerate, how to write a profile JSON (see tasks/demo-data-engine-guide.md for internal reference) (DOC-DEMO1)
- [ ] Document DV-safe mode and GATED clinical access for agency admins — configuration options, what staff see, two-person DV removal workflow — PR #147 (DOC-PERM1)
- [ ] Document per-field front desk access controls for agency admins — how to configure which contact fields receptionists can edit — PR #147 (DOC-PERM2)
- [ ] Document access tiers (3-tier RBAC model) for deployment runbook — what each tier controls, how to configure — PR #147 (DOC-PERM3)
- [ ] Seed groups-attendance test data with 8+ members and 12+ sessions — re-seed after workflow changes, fix in qa-scenarios repo (QA-PA-TEST1)
- [ ] Seed comm-my-messages populated state with actual messages — re-seed after workflow changes, fix in qa-scenarios repo (QA-PA-TEST2)
- [ ] Add new features and capabilities to the web site as they are built (WEBSITE-UPDATE1)
- [ ] Use KoNote logos from `Logo/brand/` folder across app and website (see PR #100) — PB (LOGO1)

## Parking Lot: Ready to Build

Scope is clear, just needs time. A session can pick these up without special approval.

- [ ] Individual client data export from client profile (Tier 1) — "Export Client Data" action, staff chooses PDF or JSON, delivered via SecureExportLink. For PIPEDA requests, program transfers, and client data requests. Design approved (see tasks/agency-data-offboarding.md) — PR #143, GK reviews privacy workflow (QA-R7-PRIVACY1)
- [ ] Build `export_agency_data` management command (Tier 2) — AES-256-GCM encryption, automatic model discovery, HTML/JS decryptor, tiered access (self-hosted self-serve, SaaS via KoNote). Design complete (see tasks/agency-data-offboarding.md) (SEC3)
- [ ] Build HTML/JS AES-256-GCM decryptor — self-contained browser-based file, Web Crypto API, fully offline, CSP-locked. Ships with Tier 2 exports — PR #146 (SEC3-DECRYPT1)
- [ ] Add export coverage safety nets — Django system check + CI test to catch uncovered models automatically — PR #145 (SEC3-SAFETY1)
- [ ] Add automated backup reminder notifications — periodic reminders to agency contact person when a backup export is due — PR #144 (SEC3-REMIND1)
- [ ] Create data handling acknowledgement template — agency signs before plaintext exports are enabled (SEC3-AGREE1)

## Parking Lot: Needs Review

Not yet clear we should build these, or the design isn't settled. May be too complex, too risky, or not worth the effort. **Do not build without explicit user approval in the current conversation.**

- [ ] Add CIDS conformance badge and SHACL validation reporting — deferred, requires pyshacl dependency. Consider after first funder requests conformance certification (CIDS-VALIDATE1)
- [ ] Verify BLOCKER-1 and BLOCKER-2 with manual JAWS test — automated Playwright tests pass, manual assistive tech testing still needed. Do before launch. (T50)
- [ ] Consent withdrawal workflow on client profile — wizard for PIPEDA consent withdrawal with data retention rules — GK reviews privacy/data retention (QA-R7-PRIVACY2)
- [ ] Executive compliance report — aggregate dashboard showing privacy request counts, processing times (no PII) — GK reviews reporting methodology (QA-R7-EXEC-COMPLIANCE1)
- [ ] DQ1 implementation: build threshold tuning feedback from day one — admin view of warnings triggered vs overridden per metric (DQ1-TUNE)
- [ ] DQ2 implementation: define severity tiers so the quality gate doesn't produce too many warnings that staff ignore (DQ2-TIERS)
- [ ] Add serious reportable events workflow and reporting (see tasks/serious-reportable-events.md) (SRE1)
- [ ] Add in-app configuration dashboard showing all active settings with decision rationale and change history (DEPLOY-CONFIG-UI1)
- [ ] Separate "Scheduled Assessment" workflow for standardized instruments (PHQ-9, etc.) — partner reporting (ASSESS1)
- [ ] Split `ai_assist` toggle into `ai_assist_tools_only` (default enabled) and `ai_assist_participant_data` (default disabled) — see tasks/design-rationale/ai-feature-toggles.md — GK reviews (AI-TOGGLE1)
- [ ] Add stress testing for 50+ concurrent users — defer until a client is onboarded (QA-T15)
- [ ] Add legacy system import migration scenario test — defer until an import is needed (QA-T16)
- [ ] Implement multi-session testing for SCN-046 shared device scenario — defer until workflows stabilise (QA-W55)
- [ ] Optimize encrypted client search performance beyond ~2000 records — defer until a client approaches that scale (PERF1)
- [ ] Metric cadence system — only prompt for metric values when due, configurable per metric (METRIC-CADENCE1)
- [ ] 90-day metric relevance check — prompt worker to confirm or change the chosen metric (METRIC-REVIEW1)
- [ ] Alliance prompt rotation — cycle 3-4 phrasings to prevent habituation (ALLIANCE-ROTATE1)
- [ ] Portal-based async alliance rating — post-session notification for participant self-rating (PORTAL-ALLIANCE1)
- [ ] Self-hosted LLM for suggestion theme tagging — Qwen3.5-35B-A3B on OVHcloud Beauharnois, shared endpoint, nightly batch — see tasks/design-rationale/ai-feature-toggles.md for full analysis — GK reviews (AI-SELFHOST1)

## Recently Done

- [x] Document scheduled task setup for export monitoring in the runbook — added send_export_summary (weekly) and check_report_deadlines (daily) to docs/export-runbook.md — 2026-02-28 (EXP2w)
- [x] FHIR+CIDS full implementation (Sessions 1-5) — CIDS metadata, code lists, ServiceEpisode, achievement status, JSON-LD export — PR #131 to develop — 2026-02-27 (CIDS-META1 thru CIDS-IMPACT1)
- [x] Create data handling acknowledgement template — plain language template for agencies to sign before plaintext exports are enabled, integrated into deployment protocol Phases 1 and 4 (see docs/data-handling-acknowledgement.md) — 2026-02-27 (SEC3-AGREE1)
- [x] Write DRR: No live API for individual participant data — architectural decision record with anti-patterns, two-tier export model (see tasks/design-rationale/no-live-api-individual-data.md) — 2026-02-27 (SEC3-DRR1)
- [x] Resolve SEC3-Q1: who runs the export command — tiered model: self-hosted self-serve, SaaS via KoNote with SLA. Expert panel. Design unblocked — 2026-02-27 (SEC3-Q1)
- [x] Approve dual document integration design — SharePoint for staff documents (program-centric folders), Google Drive for participant portal (digital toolkit handoff). Expert panel reviewed. See tasks/design-rationale/document-integration.md — 2026-02-27 (DOC-INTEG1)
- [x] Backup restore verification — management command, Azure/Docker test scripts, 757-line runbook — 2026-02-26 (OPS4)
- [x] Fix demo login section layout — compressed demo user buttons into single grid, centred participant portal button — 2026-02-26 (UI1)
- [x] Approve Agency Permissions Interview questionnaire — approved with note re: custom roles beyond four defaults (see tasks/agency-permissions-interview.md) — 2026-02-26 (ONBOARD-APPROVE)
- [x] Validate CIDS implementation plan against CIDS 3.2.0 spec — GO with corrections, all decisions resolved 2026-02-25 (see tasks/cids-plan-validation.md) — 2026-02-25 (CIDS-APPROVE1)
- [x] Deploy and test config-aware demo data engine on Azure client instance — wrote agency profile JSON, built and pushed to ACR, redeployed container, generated 30 demo clients across 6 programs, verified end-to-end with Playwright — 2026-02-25 (DEMO-ENGINE-DEPLOY1)
- [x] GATED clinical access for PM — justification UI, time-boxed grants, configurable reasons + durations, admin views, 32 tests — 2026-02-25 (PERM-P6)
- [x] Per-field front desk edit — build admin UI to configure which contact fields receptionist can edit (prerequisite for P5) — 2026-02-25 (PERM-P8)
- [x] DV-safe mode — hide DV-sensitive fields from front desk when DV flag set; two-person removal, fail-closed, 28+5 tests — 2026-02-25 (PERM-P5)
- [x] Email verification fixes — export double-submit protection, erasure form radio hardening, 17 password reset tests (PR pending) — 2026-02-24 (OPS3)
- [x] Add axe-core pass to `/capture-page-states` — automated WCAG checks on every page+persona+state, standalone report, skip flag — 2026-02-25 (T59)
- [x] Verified: surveys already implemented — full apps/surveys/ with models, views, forms, tests, migrations — 2026-02-24 (SURVEY1)
- [x] Verified: first-run setup wizard already implemented — 8-step guided configuration in admin settings — 2026-02-24 (SETUP1-UI)
