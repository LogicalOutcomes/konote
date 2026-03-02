# Project Tasks

## Flagged

- [ ] Contact Common Approach to position KoNote as a pilot CIDS implementer — early engagement for co-marketing and advance notice of spec changes — GK (CIDS-CA-OUTREACH1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)

## Active Work

_QA Round 8 Tier 1 complete — see Recently Done._

### Phase: P0 — Prosper Canada Requirements (March 31)

Items from `requirements-analysis.md` that must move from "Planned" to "Fully met" before deliverable deadline.

**Funder reporting (RP2, RP3):**
- [ ] Add partner report approval workflow — quality review, agency annotations, explicit publish step before sharing with partners (see tasks/funder-report-approval.md, plan: docs/plans/2026-02-20-funder-report-approval-design.md) (RPT-APPROVE1)

**Cross-agency rollup (RP4):**
- [ ] Build cross-agency data rollup for partners — waiting on requirements re: which metrics to aggregate — PB, GK reviews metric aggregation (SCALE-ROLLUP1)
- [ ] Build cross-agency reporting API — standardised endpoint per instance for Prosper Canada to consume published reports (plan: docs/plans/2026-02-20-cross-agency-reporting-api-design.md) (SCALE-API1)
- [ ] Build umbrella admin dashboard — central view for Prosper Canada to see instance health, published reports, and aggregate metrics across agencies (SCALE-DASH1)

**Multi-tenancy and central management (MA3, MA4):**
- [ ] Integrate django-tenants for schema-per-tenant multi-tenancy — PostgreSQL backend, shared/tenant app split, tenant model, domain model (see tasks/multi-tenancy-implementation-plan.md, Tasks 0-2) — PB (MT-CORE1)
- [ ] Implement per-tenant encryption keys — key table in shared schema, encrypted by master key, update encryption.py (see plan Task 3) — PB (MT-ENCRYPT1)
- [ ] Create consortium data model — Consortium, ConsortiumMembership, ProgramSharing, PublishedReport with program-level sharing granularity (see plan Task 4) — PB, GK reviews data model (MT-CONSORT1)
- [ ] Add consent_to_aggregate_reporting field and audit tenant_schema column (see plan Tasks 5-6) — PB (MT-CONSENT1)
- [ ] Validate existing features across tenant schemas — update test infrastructure, fix tenant-related test failures (see plan Tasks 7-8) — PB (MT-VALIDATE1)
- [ ] Build deploy script to automate infrastructure provisioning — Azure/OVHcloud resources, env vars, migrations, output a URL (plan: docs/plans/2026-02-20-deploy-script-design.md) (DEPLOY-SCRIPT1)
- [ ] Define managed service model — who handles infrastructure, backups, updates, support tiers, funding model (see tasks/hosting-cost-comparison.md, tasks/design-rationale/ovhcloud-deployment.md) (OPS-MANAGED1)

**Outcome tracking (G4):**
- [ ] Auto-update progress metrics when goal status changes — recalculate related metrics when a goal is marked achieved/abandoned (REQ-G4)

### Phase: Launch Readiness

- [ ] Run deployment protocol with [funder partner] — currently at Phase 0 (see tasks/deployment-protocol.md, tasks/hosting-cost-comparison.md) — SG (DEPLOY-PC1)
- [ ] Discuss data handling acknowledgement during permissions interview — plaintext backup opt-in, designate contact person (see docs/data-handling-acknowledgement.md, deployment-protocol.md Phase 1) — SG (DEPLOY-DHA1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — PB (OPS4)
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

### Phase: QA Round 8 — Tier 2 Fixes (see tasks/qa-action-plan-2026-03-01.md)

- [ ] Verify: language middleware — ref fix-log FG-S-2, fixed 2026-02-21 in QA-R7-TIER1, check if regressed or overridden (QA-R8-LANG1)
- [ ] Fix newly created client not searchable by other users — cross-role intake handoff (QA-R8-UX3)
- [ ] Fix quick note entry point unreachable — selector mismatch on client profile (QA-R8-UX4)
- [ ] Fix create form Tab order — Last Name gets focus before First Name, WCAG 1.3.2 (QA-R8-A11Y4)
- [ ] Fix excessive Tab presses to reach search results — filter controls blocking path, WCAG 2.4.3 (QA-R8-A11Y5)
- [ ] Fix checkbox touch target size for tablet — below WCAG 2.5.8 minimum 24px (QA-R8-A11Y6)
- [ ] Fix missing validation error + success confirmation on participant create (QA-R8-UX5)
- [ ] Fix mobile edit navigating to wrong form — opens New Participant instead of contact edit (QA-R8-UX6)
- [ ] Verify: offline fallback — ref fix-log entry 9, fixed 2026-02-21 Round 7 same-day, check if regressed (QA-R8-UX7)
- [ ] Add date presets + PDF export to executive dashboard (QA-R8-UX8)
- [ ] Fix French navigation — create participant + /clients/create/ URL broken in French (QA-R8-I18N1)
- [ ] Fix calendar feed URL generation failing silently (QA-R8-UX9)
- [ ] Fix form resubmission navigating to help page — broken redirect after POST (QA-R8-UX10)
- [ ] Fix /reports/funder/ returning 404 — funder report URL missing (QA-R8-UX11)
- [ ] Fix PM user management path missing — /manage/users/ not linked (QA-R8-UX12)
- [ ] Accessibility polish bundle — language toggle confirmation, breadcrumb targets, field visibility, icon labels (QA-R8-A11Y7)

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Data Quality

- [ ] Entry-time plausibility warnings — soft-flag unlikely values during data entry, prioritise financial metrics (see tasks/data-validation-design.md, financial subsection added 2026-02-20) (DQ1)
- [ ] Add second-tier "very unlikely" plausibility thresholds for financial metrics — tighter bounds beyond warn_max for edge case detection (DQ1-TIER2)
- [ ] Pre-report data quality checks — validate data quality before partner report export (see tasks/data-validation-design.md) (DQ2)

### Phase: Multi-Agency Scaling — remaining items after P0 (see tasks/design-rationale/multi-tenancy.md)

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

- [ ] Verify BLOCKER-10/12 data export against recent SEC3 work — routes may already exist (QA-R8-VERIFY1)
- [ ] Fix accent stripping in client list display — "Benoît" appears as "Benoit" (QA-R8-UX13)
- [ ] Fix profile tabs arrow key navigation — ArrowRight opens Actions dropdown instead of next tab (QA-R8-A11Y8)

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
- [ ] Add funder demographic profile dropdown with small-cell suppression — GK reviews reporting methodology (QA-R8-RPT1)
- [ ] Decide executive audit log access for PIPEDA 4.1.4 board accountability — GK reviews data access policy (QA-R8-PERM2)

## Recently Done

- [x] QA Round 8 Tier 1: removed dashboard search autofocus (credentials leaked into search bar after login redirect) — 2026-03-01 (QA-R8-SEC1)
- [x] QA Round 8 Tier 1: added regression test confirming demo buttons hidden when DEMO_MODE off — 2026-03-01 (QA-R8-SEC2)
- [x] QA Round 8 Tier 1: verified skip link correct in code (stale screenshot) — 2026-03-01 (QA-R8-A11Y1)
- [x] QA Round 8 Tier 1: moved language toggle after login form for WCAG 2.4.3 Tab order — 2026-03-01 (QA-R8-A11Y2)
- [x] QA Round 8 Tier 1: verified Actions dropdown ARIA pattern already correct in code (stale screenshot) — 2026-03-01 (QA-R8-A11Y3)
- [x] QA Round 8 Tier 1: verified 404→403 handling correct in code (stale screenshot) — 2026-03-01 (QA-R8-UX1)
- [x] QA Round 8 Tier 1: closed BUG-33 form data corruption — could not reproduce, fields use explicit name bindings — 2026-03-01 (QA-R8-UX2)
- [x] QA Round 8 Tier 1: verified admin nav hidden for executive role (stale screenshot) — 2026-03-01 (QA-R8-PERM1)
- [x] Build `export_agency_data` management command (Tier 2) — AES-256-GCM encryption, automatic model discovery, nested client-centric JSON, config files, Diceware passphrase, 20 tests — 2026-02-28 (SEC3)
- [x] Individual client data export from client profile (Tier 1) — PDF, CSV, JSON via SecureExportLink with audit trail, nonce dedup, permission gating — 2026-02-28 (QA-R7-PRIVACY1)
