# Project Tasks

## Flagged

- [ ] Contact Common Approach to position KoNote as a pilot CIDS implementer — early engagement for co-marketing and advance notice of spec changes — GK (CIDS-CA-OUTREACH1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)
- [ ] Merge 3 open PRs: #222 (VPS provisioning docs), #224 (QA seed data), #225 (demo safeguards) (MERGE-OPEN-PRS)

## Active Work

### Phase: P0 — Requirements Analysis (March 31)

Items from `requirements-analysis.md` that need work before the deliverable deadline.

**Product code to build:**

- [ ] Write funder reporting dashboard design doc — waiting on funder reporting templates from Prosper Canada (expected March 2026), then: which metrics aggregate, how agencies publish data, how Prosper Canada views it — GK (DOC-RP4)
- [ ] Build funder reporting dashboard — read-only view where Prosper Canada sees aggregate outcome data published by individual agencies. Not individual participant records. Depends on DOC-RP4 (SCALE-ROLLUP1)

**Ops & business model:**

- [ ] Define managed service model — who handles infrastructure, backups, updates, support tiers, funding model (see tasks/hosting-cost-comparison.md, tasks/design-rationale/ovhcloud-deployment.md) (OPS-MANAGED1)

### Phase: Launch Readiness

- [ ] Run deployment protocol with [funder partner] — currently at Phase 0 (see tasks/deployment-protocol.md, tasks/hosting-cost-comparison.md) — SG (DEPLOY-PC1)
- [ ] Discuss data handling acknowledgement during permissions interview — plaintext backup opt-in, designate contact person (see docs/data-handling-acknowledgement.md, deployment-protocol.md Phase 1) — SG (DEPLOY-DHA1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
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

### Phase: Documentation & Website Updates

- [ ] Create deployment documentation for surveys and portal features (DOC-DEPLOY1)
- [ ] Update technical documentation in GitHub for surveys and portal architecture (DOC-TECH1)
- [ ] Document DV-safe mode and GATED clinical access for agency admins — configuration options, what staff see, two-person DV removal workflow — PR #147 (DOC-PERM1)
- [ ] Document per-field front desk access controls for agency admins — how to configure which contact fields receptionists can edit — PR #147 (DOC-PERM2)
- [ ] Document access tiers (3-tier RBAC model) for deployment runbook — what each tier controls, how to configure — PR #147 (DOC-PERM3)
- [ ] Add new features and capabilities to the web site as they are built (WEBSITE-UPDATE1)

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Data Quality

- [ ] Entry-time plausibility warnings — soft-flag unlikely values during data entry, prioritise financial metrics (see tasks/data-validation-design.md, financial subsection added 2026-02-20) (DQ1)
- [ ] Add second-tier "very unlikely" plausibility thresholds for financial metrics — tighter bounds beyond warn_max for edge case detection (DQ1-TIER2)
- [ ] Pre-report data quality checks — validate data quality before partner report export (see tasks/data-validation-design.md) (DQ2)

### Phase: Server Sharing — cost optimization, not a launch prerequisite (completed in PR #220)

Multiple agencies can deploy today on independent instances ($35–100/month each). Server sharing reduces per-agency costs to $4–10/month with walled database schemas per agency on one server.

Details: see [tasks/design-rationale/multi-tenancy.md](tasks/design-rationale/multi-tenancy.md) and Recently Done → Multi-Tenancy Infrastructure.

- [ ] Improve admin UI for self-service configuration — better guidance for terminology, metrics, templates (ADMIN-UX1)
- [ ] Align report-template.json "bins" field naming with DemographicBreakdown model's "bins_json" when building Phase 2 template automation (TEMPLATE-ALIGN1)

### Phase: Offline Field Collection (if requested by client)

- [ ] Deploy ODK Central on Canadian VM (Docker Compose) — ops task (FIELD-ODK-DEPLOY1)
- [ ] Circle Observation XLSForm — depends on circles in ODK (FIELD-ODK-FORM-CIR1)
- [ ] Push Circle/CircleMember Entity lists — depends on above (FIELD-ODK-CIRCLES1)
- [ ] Agency-facing documentation — ODK Collect setup, device loss protocol (FIELD-ODK-DOC1)

### Phase: Surveys Future Work

- [ ] Build shareable link channel for public survey links without login (SURVEY-LINK1)

## Parking Lot: Ready to Build

Scope is clear, just needs time. A session can pick these up without special approval.

_Empty — all items moved to Recently Done._

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

### Demo Mode Safeguards (PR #225 — open, code complete)

- [x] Restrict demo-admin to view-only for agency settings — demo users cannot POST to settings views — 2026-03-03 (DEMO-ADMIN-RO1)
- [x] Add persistent training-mode banner for demo sessions — amber banner on every page — 2026-03-03 (DEMO-BANNER1)
- [x] Visually separate demo buttons from real login — section labelled "Training Accounts" — 2026-03-03 (DEMO-LOGIN-UX1)
- [x] Audit demo logins — log demo login events with is_demo_context=True, excluded from PHIPA pipeline — 2026-03-03 (DEMO-AUDIT1)
- [x] Verify all reports/exports exclude is_demo=True — explicit filters on team meeting, dashboard aggregates — 2026-03-03 (DEMO-EXCLUDE1)

### Recently merged to develop (2026-03-02/03)

- [x] Add partner report approval workflow — preview, agency notes, explicit approve step before export — 2026-03-02 (RPT-APPROVE1)
- [x] Multi-tenancy infrastructure — django-tenants, per-agency encryption, consortium model, 12 tests — PR #220 — 2026-03-03 (MT-CORE1 thru MT-VALIDATE1)
- [x] Deploy script + VPS provisioning — scripts/deploy-konote-vps.sh, docs/plans/ — PR #217 — 2026-03-02 (DOC-MA5 + DEPLOY-SCRIPT1)
- [x] Add KoNote logo to navigation and social preview — 2026-03-02 (LOGO1)
- [x] Seed groups-attendance + comm-my-messages test data in scenario runner — PR #212 — 2026-03-02 (QA-PA-TEST1 + QA-PA-TEST2)
- [x] Write client-facing demo data engine guide — PR #213 — 2026-03-02 (DOC-DEMO1)
- [x] Add rate limit to portal login endpoint — Sentinel security fix — PR #214 — 2026-03-02 (SEC-RATELIMIT1)
- [x] Fix quick links contrast + login form a11y — PR #216 — 2026-03-02 (QA-R8-CONTRAST2)
- [x] Audit migration set schema fix — PR #223 — 2026-03-03 (MT-AUDIT-FIX1)
- [x] Accessibility sweep — ARIA roles, landmarks, templates, contrast, table headers, touch targets, polish — PR #208 — 2026-03-02 (AXE-ARIA1 thru QA-R8-A11Y7)
- [x] QA Round 8 Tier 2 — French nav verified, form resubmission false positive, /reports/funder/ redirect, executive dashboard presets + PDF — PRs #210, #211 — 2026-03-02 (QA-R8-I18N1, QA-R8-UX10, QA-R8-UX11, QA-R8-UX8)
- [x] Wave 1 parallel bug fixes — client search, tab order, mobile edit, skip links, quick note, calendar feed, PM nav, h1 headings — PRs #201–207 — 2026-03-02 (QA-R8-UX3 thru QA-R8-UX12)
