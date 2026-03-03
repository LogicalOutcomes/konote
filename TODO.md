# Project Tasks

## Flagged

- [ ] Contact Common Approach to position KoNote as a pilot CIDS implementer — early engagement for co-marketing and advance notice of spec changes — GK (CIDS-CA-OUTREACH1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)

## Active Work

_QA Round 8 Tier 1 complete — see Recently Done._

### Phase: P0 — Requirements Analysis (March 31)

Items from `requirements-analysis.md` that need work before the deliverable deadline. Grouped by type: product code, deployment automation, and cost optimization.

**Product code to build:**

- [x] Add partner report approval workflow — preview, agency notes, explicit approve step before export — 2026-03-02 (RPT-APPROVE1)
- [ ] Write funder reporting dashboard design doc — waiting on funder reporting templates from Prosper Canada (expected March 2026), then: which metrics aggregate, how agencies publish data, how Prosper Canada views it — GK (DOC-RP4)
- [ ] Build funder reporting dashboard — read-only view where Prosper Canada sees aggregate outcome data published by individual agencies. Not individual participant records. (SCALE-ROLLUP1)

**Deployment automation (ops scripting, not product code):**

- [ ] Write deploy script design doc — how provisioning is automated, target: new agency instance in hours not weeks (docs/plans/2026-02-20-deploy-script-design.md) — PB (DOC-MA5)
- [ ] Build deploy script to automate agency instance provisioning — server setup, DNS, SSL, Docker, initial configuration, output a URL (plan: docs/plans/2026-02-20-deploy-script-design.md) (DEPLOY-SCRIPT1)
- [ ] Define managed service model — who handles infrastructure, backups, updates, support tiers, funding model (see tasks/hosting-cost-comparison.md, tasks/design-rationale/ovhcloud-deployment.md) (OPS-MANAGED1)

### Phase: Launch Readiness

- [ ] Run deployment protocol with [funder partner] — currently at Phase 0 (see tasks/deployment-protocol.md, tasks/hosting-cost-comparison.md) — SG (DEPLOY-PC1)
- [ ] Discuss data handling acknowledgement during permissions interview — plaintext backup opt-in, designate contact person (see docs/data-handling-acknowledgement.md, deployment-protocol.md Phase 1) — SG (DEPLOY-DHA1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — PB (OPS4)
- [ ] Create AI-assisted admin toolkit decision documents (01-09) for agency setup — reformat deployment protocol into AI-consumable reference docs, test with [funder partner] dry run (see tasks/ai-assisted-admin-toolkit.md, docs/agency-setup-guide/). Document 10 (Data Responsibilities) is done — (DEPLOY-TOOLKIT1)
- [ ] Review and merge data handling acknowledgement PR #130 — expanded to cover encryption key custody, SharePoint/Google Drive responsibilities, exports, plaintext backups, staff departures. Wired into deployment protocol Phases 0/4/5. Needs legal review before first agency use (see docs/data-handling-acknowledgement.md) — SG (SEC3-AGREE1)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — SG (SEC3-Q1)
- [ ] Draft SaaS service agreement for LogicalOutcomes-managed agencies — data processing, security, SLAs, breach notification, termination, data export acknowledgement as schedule. Needs lawyer review (see tasks/saas-service-agreement.md) — SG (LEGAL-SaaS1)

## Do Occasionally

Step-by-step commands for each task are in [tasks/recurring-tasks.md](tasks/recurring-tasks.md).

- [ ] **UX walkthrough** — run after UI changes. In Claude Code: `pytest tests/ux_walkthrough/ -v`, then review `tasks/ux-review-latest.md` and add fixes to TODO (UX-WALK1)
- [ ] **Code review** — run every 2–4 weeks or before a production deploy. Open Claude Code and paste the review prompt from [tasks/code-review-process.md](tasks/code-review-process.md) (REV1)
- [ ] **Full QA suite** — run after major releases or substantial UI changes. Two pipelines (A then B), five sessions total — see [tasks/recurring-tasks.md](tasks/recurring-tasks.md) for full steps (QA-FULL1)
- [ ] **French translation spot-check** — have a French speaker review key screens. Run `python manage.py check_translations` to verify .po file coverage (I18N-REV1)
- [ ] **Redeploy to Railway** — after merging to main. Push to `main` and Railway auto-deploys (OPS-RAIL1)

## Coming Up

### Phase: QA Round 8 — Remaining Tier 2 Fixes (see tasks/qa-action-plan-2026-03-01.md)

- [ ] Fix checkbox touch target size for tablet — below WCAG 2.5.8 minimum 24px (QA-R8-A11Y6)
- [x] Add date presets + PDF export to executive dashboard — 2026-03-02 (QA-R8-UX8)
- [ ] Fix French navigation — create participant + /clients/create/ URL broken in French (QA-R8-I18N1)
- [ ] Fix form resubmission navigating to help page — broken redirect after POST (QA-R8-UX10)
- [x] Fix /reports/funder/ returning 404 — added permanent redirect to /reports/funder-report/ — 2026-03-02 (QA-R8-UX11)
- [ ] Accessibility polish bundle — language toggle confirmation, breadcrumb targets, field visibility, icon labels (QA-R8-A11Y7)

### Phase: Axe-core Accessibility Fixes (from page capture 2026-03-02, see axe-a11y-report.json)

- [ ] Fix systemic ARIA role violations — aria-required-children (CRITICAL, 59 pages, 512 nodes) + aria-allowed-role (MINOR, 59 pages, 546 nodes), likely a shared component or base template pattern (AXE-ARIA1)
- [ ] Fix duplicate landmark regions — landmark-unique (MODERATE, 60 pages, 352 nodes), likely duplicate nav or main landmarks in base template structure (AXE-LANDMARK1)
- [ ] Fix 4 pages missing base template wrapper — export-confirmation, plan-section-edit, public-survey-link, public-unsubscribe are missing title, lang attr, landmarks, and h1 (AXE-TEMPLATE1)
- [ ] Fix colour contrast failures — 11 pages, 257 nodes including client-detail, dashboard-staff, plan-view, notes-list, events-list, comm pages (AXE-CONTRAST1)
- [ ] Fix empty table headers on 4 admin pages — admin-event-types, admin-settings-terminology, admin-users, programs-list (AXE-TABLE1)

### Phase: Demo Mode Safeguards (from expert panel, see tasks/design-rationale/ovhcloud-deployment.md)

- [ ] Restrict demo-admin to view-only for agency settings — demo users with admin role can view but not modify terminology, feature toggles, or program config. Prevents configuration changes via demo sessions (DEMO-ADMIN-RO1)
- [ ] Add persistent training-mode banner for demo sessions — amber banner on every page: "Training Mode — changes here do not affect real participant records" (DEMO-BANNER1)
- [ ] Visually separate demo buttons from real login form — distinct section, labelled "Training Accounts," different styling so staff never accidentally click a demo button instead of signing in (DEMO-LOGIN-UX1)
- [ ] Audit demo logins — log demo login events (who, when, which demo user) for operational awareness, but exclude from PHIPA audit pipeline (DEMO-AUDIT1)
- [ ] Verify all reports and exports exclude is_demo=True records — check every report query, aggregate count, CSV/PDF export, and funder report for demo data leakage (DEMO-EXCLUDE1)

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Data Quality

- [ ] Entry-time plausibility warnings — soft-flag unlikely values during data entry, prioritise financial metrics (see tasks/data-validation-design.md, financial subsection added 2026-02-20) (DQ1)
- [ ] Add second-tier "very unlikely" plausibility thresholds for financial metrics — tighter bounds beyond warn_max for edge case detection (DQ1-TIER2)
- [ ] Pre-report data quality checks — validate data quality before partner report export (see tasks/data-validation-design.md) (DQ2)

### Phase: Server Sharing — cost optimization, not a launch prerequisite (see tasks/design-rationale/multi-tenancy.md)

Multiple agencies can deploy today on independent instances ($35–100/month each). Server sharing allows agencies to share a server while keeping data walled off, reducing costs to $4–10/agency/month. Worth doing when the network grows beyond 3–5 agencies.

- [ ] Integrate django-tenants for server sharing — multiple agencies on one server with walled-off database sections (see tasks/multi-tenancy-implementation-plan.md, Tasks 0-2) — PB (MT-CORE1)
- [ ] Implement per-agency encryption keys — separate encryption key per agency, encrypted by master key (see plan Task 3) — PB (MT-ENCRYPT1)
- [ ] Create cost-sharing group data model — which agencies share a server, program-level data sharing controls, published reports (see plan Task 4) — PB, GK reviews data model (MT-CONSORT1)
- [ ] Add consent_to_aggregate_reporting field and audit agency column (see plan Tasks 5-6) — PB (MT-CONSENT1)
- [ ] Validate existing features work across shared-server agencies — update test infrastructure, fix related test failures (see plan Tasks 7-8) — PB (MT-VALIDATE1)
- [ ] Improve admin UI for self-service configuration — better guidance for terminology, metrics, templates (ADMIN-UX1)
- [ ] Align report-template.json "bins" field naming with DemographicBreakdown model's "bins_json" when building Phase 2 template automation (TEMPLATE-ALIGN1)

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

_Empty — all items moved to Recently Done after Wave 1 sprint._

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

### Wave 2 Sprint — Accessibility Sweep (PR #208)

- [x] Fix ARIA role violations in nav dropdowns — menu pattern replaces incorrect listbox — 2026-03-02 (AXE-ARIA1)
- [x] Fix duplicate landmark regions — aria-labels on both nav elements — 2026-03-02 (AXE-LANDMARK1)
- [x] Fix public survey form accessibility — skip link, title, main.css — 2026-03-02 (AXE-TEMPLATE1)
- [x] Fix colour contrast failures — --kn-text-faint corrected to #697888, feedback badge darkened — 2026-03-02 (AXE-CONTRAST1)
- [x] Fix empty table headers on 8 admin pages — screen-reader "Actions" text — 2026-03-02 (AXE-TABLE1)
- [x] Fix checkbox/radio label touch targets — CSS :has() padding — 2026-03-02 (QA-R8-A11Y6)
- [x] Accessibility polish bundle — breadcrumb padding, aria-hidden on icons, link_embed consistency — 2026-03-02 (QA-R8-A11Y7)
- [x] Verified: French navigation uses {% url %} tags correctly — no hardcoded paths found — 2026-03-02 (QA-R8-I18N1)
- [x] Verified: form resubmission → help page is a QA false positive — no code path exists — 2026-03-02 (QA-R8-UX10)
- [x] Add axe-core accessibility smoke tests to CI — new a11y job in ci.yml — 2026-03-02 (CI-A11Y1)

### Wave 1 Sprint — Parallel Bug Fixes (PRs #201–#207, qa-scenarios #18)

- [x] Auto-update progress metrics when goal status changes — post_save signal on PlanTarget updates achievement_status — 2026-03-02 (REQ-G4)
- [x] Fix SCN-035 YAML URL — `/reports/funder/` → `/reports/funder-report/` in qa-scenarios repo — 2026-03-02 (QA-R8b-YAML1)
- [x] Fix test runner interactive step execution — duplicate screenshot detection, HTMX waits, select action handler — 2026-03-02 (QA-R8b-TEST1)
- [x] Fix URL placeholder substitution — pre-seed alert_id, recommendation_id, meeting_id, first-name client keys — 2026-03-02 (QA-R8b-TEST2)
- [x] Fix newly created client not searchable — search now queries all accessible programs when search query is present — 2026-03-02 (QA-R8-UX3)
- [x] Fix create form Tab order — added explicit field_order to ClientFileForm (First Name before Last Name) — 2026-03-02 (QA-R8-A11Y4)
- [x] Verified: validation error + success confirmation on participant create already working — 2026-03-02 (QA-R8-UX5)
- [x] Fix mobile edit — moved Edit to top of Actions dropdown menu — 2026-03-02 (QA-R8-UX6)
- [x] Verified: accent display correct — _strip_accents() only used for search, display preserves original — 2026-03-02 (QA-R8-UX13)
- [x] Fix excessive Tab presses — added "Skip to results" link on search/list pages — 2026-03-02 (QA-R8-A11Y5)
- [x] Fix profile tabs arrow key nav — WAI-ARIA roving tabindex pattern + keyboard handler — 2026-03-02 (QA-R8-A11Y8)
- [x] Fix quick note entry point — missing include + wrong hx-swap in notes tab — 2026-03-02 (QA-R8-UX4)
- [x] Fix missing h1 on notes-detail page — added `<h1>{% trans "Progress Note" %}</h1>` with French — 2026-03-02 (AXE-HEADING1)
- [x] Verified: language middleware not regressed — 24 tests pass, SafeLocaleMiddleware intact — 2026-03-02 (QA-R8-LANG1)
- [x] Verified: offline fallback not regressed — htmx error handlers + service worker + offline banner intact — 2026-03-02 (QA-R8-UX7)
- [x] Verified: data export routes exist — /reports/participant/<id>/export/ with PDF/CSV/JSON + SecureExportLink — 2026-03-02 (QA-R8-VERIFY1)
- [x] Fix calendar feed URL — added error handling, POST-Redirect-GET, improved success message — 2026-03-02 (QA-R8-UX9)
- [x] Fix PM user management nav — `/manage/` path was missing from nav_active context processor — 2026-03-02 (QA-R8-UX12)

### Phase: FHIR-Informed Data Foundations + CIDS Compliance (PR #131)

- [x] Add CIDS metadata fields + OrganizationProfile — 2026-02-27 (CIDS-META1 + CIDS-ORG1)
- [x] Import CIDS code lists + TaxonomyMapping model — 2026-02-27 (CIDS-CODES1)
- [x] Build admin UI for CIDS tagging — 2026-02-27 (CIDS-ADMIN1)
- [x] Add CIDS codes to reports + Standards Alignment appendix — 2026-02-27 (CIDS-ENRICH1)
- [x] Extend ClientProgramEnrolment into ServiceEpisode — 2026-02-27 (FHIR-EPISODE1)
- [x] Populate new ServiceEpisode fields from existing data — 2026-02-27 (FHIR-MIGRATE1)
- [x] Add achievement_status + first_achieved_at to PlanTarget — 2026-02-27 (FHIR-ACHIEVE1)
- [x] Add author_role to ProgressNote — 2026-02-27 (FHIR-ROLE1)
- [x] Build JSON-LD export + impact dimensions — 2026-02-27 (CIDS-EXPORT1 + CIDS-IMPACT1)
- [x] Review fix: on-hold visibility, translations, bulk transfer audit, form fix, regression test — 2026-02-27 (CIDS-REVIEW-FIX1)

### QA Round 8 Tier 1

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
