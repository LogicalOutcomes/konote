# Project Tasks

## Flagged

- [ ] Contact Common Approach to position KoNote as a pilot CIDS implementer — early engagement for co-marketing and advance notice of spec changes — GK (CIDS-CA-OUTREACH1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)

## Active Work

### Phase: P0 — Requirements Analysis (March 31)

Items from `requirements-analysis.md` that need work before the deliverable deadline.

**Product code to build:**

- [ ] Write funder reporting dashboard design doc — waiting on funder reporting templates from Prosper Canada (expected March 2026), then: which metrics aggregate, how agencies publish data, how Prosper Canada views it — GK (DOC-RP4)
- [ ] Build funder reporting dashboard — read-only view where Prosper Canada sees aggregate outcome data published by individual agencies. Not individual participant records. Depends on DOC-RP4 (SCALE-ROLLUP1)

**Ops & business model:**

- [ ] Define managed service model — who handles infrastructure, backups, updates, support tiers, funding model (see tasks/hosting-cost-comparison.md, tasks/design-rationale/ovhcloud-deployment.md) (OPS-MANAGED1)

### Phase: Session 7 — Compliance, Safety, Data Quality

- [ ] Executive compliance report — aggregate dashboard showing privacy request counts, processing times (no PII) — GK reviews reporting methodology (QA-R7-EXEC-COMPLIANCE1)
- [ ] Add serious reportable events workflow and reporting (see tasks/serious-reportable-events.md) (SRE1)
- [ ] DQ1 implementation: build threshold tuning feedback from day one — admin view of warnings triggered vs overridden per metric (DQ1-TUNE)

### Phase: Launch Readiness

- [ ] Run deployment protocol with [funder partner] — currently at Phase 0 (see tasks/deployment-protocol.md, tasks/hosting-cost-comparison.md) — SG (DEPLOY-PC1)
- [ ] Discuss data handling acknowledgement during permissions interview — plaintext backup opt-in, designate contact person (see docs/data-handling-acknowledgement.md, deployment-protocol.md Phase 1) — SG (DEPLOY-DHA1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [x] Create AI-assisted admin toolkit decision documents (01-09) for agency setup — reformat deployment protocol into AI-consumable reference docs, test with [funder partner] dry run (see tasks/ai-assisted-admin-toolkit.md, docs/agency-setup-guide/). Document 10 (Data Responsibilities) is done — 2026-03-03 (DEPLOY-TOOLKIT1)
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

### Phase: Session 7 Prep — Admin UX & Configuration

- [ ] Improve admin UI for self-service configuration — better guidance for terminology, metrics, templates (ADMIN-UX1)
- [ ] Add in-app configuration dashboard showing all active settings with decision rationale and change history (DEPLOY-CONFIG-UI1)

### Phase: Data Quality

- [ ] Add second-tier "very unlikely" plausibility thresholds for financial metrics — tighter bounds beyond warn_max for edge case detection (DQ1-TIER2)
- [ ] Pre-report data quality checks — validate data quality before partner report export (see tasks/data-validation-design.md) (DQ2)

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Server Sharing — cost optimization, not a launch prerequisite (completed in PR #220)

Multiple agencies can deploy today on independent instances ($35–100/month each). Server sharing reduces per-agency costs to $4–10/month with walled database schemas per agency on one server.

Details: see [tasks/design-rationale/multi-tenancy.md](tasks/design-rationale/multi-tenancy.md) and Recently Done → Multi-Tenancy Infrastructure.

- [x] Align report-template.json "bins" field naming with DemographicBreakdown model's "bins_json" — renamed ParsedBreakdown.bins to bins_json — 2026-03-03 (TEMPLATE-ALIGN1)

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
- [ ] DQ2 implementation: define severity tiers so the quality gate doesn't produce too many warnings that staff ignore (DQ2-TIERS)
- [ ] Separate "Scheduled Assessment" workflow for standardized instruments (PHQ-9, etc.) — partner reporting (ASSESS1)
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

### Session 6 — Verification & TODO Cleanup

- [x] Verified: DV-safe mode & GATED clinical access doc accurate — dv_views.py implements DV toggle (Tier 2+), permissions.py has GATED access check for note.view/plan.view — 2026-03-03 (DOC-PERM1)
- [x] Verified: per-field front desk access doc accurate — field_access_views.py exists with 3 access levels (Hidden/View only/View and edit), Tier 2+ only — 2026-03-03 (DOC-PERM2)
- [x] Verified: access tiers doc accurate — 3-tier model implemented across 10 files, tier capabilities and front desk defaults match — 2026-03-03 (DOC-PERM3)
- [x] Verified: demo data engine guide accurate — management command accepts all listed flags, admin UI exists, profile JSON schema matches seeds/demo_data_profile_example.json — 2026-03-03 (DOC-DEMO1)
- [x] Verified: groups attendance seed data — 1 Group, 8 memberships, 12 sessions, 96 attendance records in scenario_runner.py and test_page_capture.py — 2026-03-03 (QA-PA-TEST1)
- [x] Verified: staff messages seed data — 8 StaffMessage objects across 4 personas (DS1, DS1b, DS2, PM1) in scenario_runner.py and test_page_capture.py — 2026-03-03 (QA-PA-TEST2)
- [x] Verified: note sharing toggle (6/7 checks pass) — toggle sets consent/restrict, UI shows binary ON/OFF, hidden when agency sharing off, confirmation on OFF, PM/Admin UI only, audit logged. Gap: no dedicated toggle endpoint tests in test_cross_program_security.py yet — 2026-03-03 (QA-R7-PRIVACY2)

### Session 5 — Small-Cell Suppression + Compliance Summary

- [x] Add configurable suppression threshold to ReportTemplate (5 or 10) — 2026-03-03 (QA-R8-RPT1)
- [x] Add secondary (complementary) suppression to prevent derivation by subtraction — 2026-03-03 (QA-R8-RPT1)
- [x] Remove n=50 floor for demographic grouping (small-cell suppression handles privacy) — 2026-03-03 (QA-R8-RPT1)
- [x] Build compliance summary page for executives (aggregate audit metrics, no PII) — 2026-03-03 (QA-R8-PERM2)
- [x] Update reporting-architecture DRR with suppression and compliance decisions — 2026-03-03 (QA-R8-RPT1, QA-R8-PERM2)

### Session 4 — Documentation & Cleanup

- [x] Create 9 admin toolkit decision documents (01-09) in docs/agency-setup-guide/ — 2026-03-03 (DEPLOY-TOOLKIT1)
- [x] Add surveys and portal deployment docs to deploying-konote.md — 2026-03-03 (DOC-DEPLOY1)
- [x] Add surveys and portal technical architecture to technical-documentation.md — 2026-03-03 (DOC-TECH1)
- [x] Update konote-website with new features, security, and FAQ — 2026-03-03 (WEBSITE-UPDATE1)
- [x] Align ParsedBreakdown.bins field naming to bins_json — 2026-03-03 (TEMPLATE-ALIGN1)

_Older items archived to [tasks/ARCHIVE.md](tasks/ARCHIVE.md) on 2026-03-03._
