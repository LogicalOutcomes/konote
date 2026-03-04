# Project Tasks

## Flagged

- [ ] Contact Common Approach to position KoNote as a pilot CIDS implementer — early engagement for co-marketing and advance notice of spec changes — GK (CIDS-CA-OUTREACH1)
- [ ] Discuss: are the `convening-experts` and `review-session` commands useful for our workflow? Worth the time? How should we use them going forward? — GK (PROCESS-EXPERT-PANEL1)
- [ ] To go live with demo survey: run `python manage.py seed_demo_survey` on konote-dev (PR #239 and #240 are now merged). The survey will be accessible at `/s/demo-program-feedback/` and the website demo page will embed it automatically — PB (DEMO-SURVEY1)

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

### Phase: Launch Readiness

- [ ] Run deployment protocol with [funder partner] — currently at Phase 0 (see tasks/deployment-protocol.md, tasks/hosting-cost-comparison.md) — SG (DEPLOY-PC1)
- [ ] Discuss data handling acknowledgement during permissions interview — plaintext backup opt-in, designate contact person (see docs/data-handling-acknowledgement.md, deployment-protocol.md Phase 1) — SG (DEPLOY-DHA1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [ ] Review and merge data handling acknowledgement PR #130 — expanded to cover encryption key custody, SharePoint/Google Drive responsibilities, exports, plaintext backups, staff departures. Wired into deployment protocol Phases 0/4/5. Needs legal review before first agency use (see docs/data-handling-acknowledgement.md) — SG (SEC3-AGREE1)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — SG (SEC3-Q1)
- [ ] Draft SaaS service agreement for LogicalOutcomes-managed agencies — data processing, security, SLAs, breach notification, termination, data export acknowledgement as schedule. Needs lawyer review (see tasks/saas-service-agreement.md) — SG (LEGAL-SaaS1)

## Do Occasionally

Step-by-step commands for each task are in [tasks/recurring-tasks.md](tasks/recurring-tasks.md).

- [ ] **UX walkthrough** — run after UI changes. In Claude Code: `pytest tests/ux_walkthrough/ -v`, then review `tasks/ux-review-latest.md` and add fixes to TODO (UX-WALK1)
- [ ] **Quick code review** — run every 2–4 weeks or before a production deploy. Open Claude Code and paste the review prompt from [tasks/code-review-process.md](tasks/code-review-process.md) (REV1)
- [ ] **Deep code review (6 dimensions)** — run quarterly or before major releases. Uses structured checklists covering security, privacy, accessibility, deployment, AI governance, bilingual compliance. See [tasks/code-review-framework.md](tasks/code-review-framework.md) for prompts, or run all 6 with [tasks/deep-review-prompt.md](tasks/deep-review-prompt.md). Results go in private `konote-qa-scenarios/reviews/` repo. Latest: 2026-03-04 (REV-DEEP1)
- [ ] **Full QA suite** — run after major releases or substantial UI changes. Two pipelines (A then B), five sessions total — see [tasks/recurring-tasks.md](tasks/recurring-tasks.md) for full steps (QA-FULL1)
- [ ] **French translation spot-check** — have a French speaker review key screens. Run `python manage.py check_translations` to verify .po file coverage (I18N-REV1)
- [ ] **Redeploy to Railway** — after merging to main. Push to `main` and Railway auto-deploys (OPS-RAIL1)

## Coming Up

### Phase: Session 7 Prep — Admin UX & Configuration

- [ ] Pre-report data quality checks — validate data quality before partner report export (see tasks/data-validation-design.md) (DQ2)

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Server Sharing — cost optimization, not a launch prerequisite (completed in PR #220)

Multiple agencies can deploy today on independent instances ($35–100/month each). Server sharing reduces per-agency costs to $4–10/month with walled database schemas per agency on one server.

Details: see [tasks/design-rationale/multi-tenancy.md](tasks/design-rationale/multi-tenancy.md) and Recently Done → Multi-Tenancy Infrastructure.

- [x] Improve admin UI for self-service configuration — PR #252 — 2026-03-04 (ADMIN-UX1)

### Phase: Offline Field Collection (if requested by client)

- [ ] Deploy ODK Central on Canadian VM (Docker Compose) — ops task (FIELD-ODK-DEPLOY1)
- [ ] Circle Observation XLSForm — depends on circles in ODK (FIELD-ODK-FORM-CIR1)
- [ ] Push Circle/CircleMember Entity lists — depends on above (FIELD-ODK-CIRCLES1)
- [ ] Agency-facing documentation — ODK Collect setup, device loss protocol (FIELD-ODK-DOC1)

### Phase: Documentation & Website Updates

_All documentation tasks completed — see Recently Done._

## Parking Lot: Ready to Build

Scope is clear, just needs time. A session can pick these up without special approval.

- [ ] Fill 863 empty French translations in django.po — run `translate_strings --auto-translate` then review output (I18N-FILL1)

## Parking Lot: Needs Review

Not yet clear we should build these, or the design isn't settled. May be too complex, too risky, or not worth the effort. **Do not build without explicit user approval in the current conversation.**

- [ ] Add CIDS conformance badge and SHACL validation reporting — deferred, requires pyshacl dependency. Consider after first funder requests conformance certification (CIDS-VALIDATE1)
- [ ] Verify BLOCKER-1 and BLOCKER-2 with manual JAWS test — automated Playwright tests pass, manual assistive tech testing still needed. Do before launch. (T50)
- [ ] Consent withdrawal workflow on client profile — wizard for PIPEDA consent withdrawal with data retention rules — GK reviews privacy/data retention (QA-R7-PRIVACY2)
- [ ] DQ2 implementation: define severity tiers so the quality gate doesn't produce too many warnings that staff ignore (DQ2-TIERS)
- [ ] Add in-app configuration dashboard showing all active settings with decision rationale and change history (DEPLOY-CONFIG-UI1)
- [ ] Separate "Scheduled Assessment" workflow for standardized instruments (PHQ-9, etc.) — partner reporting (ASSESS1)
- [ ] Add stress testing for 50+ concurrent users — defer until a client is onboarded (QA-T15)
- [ ] Add legacy system import migration scenario test — defer until an import is needed (QA-T16)
- [ ] Implement multi-session testing for SCN-046 shared device scenario — defer until workflows stabilise (QA-W55)
- [ ] Optimize encrypted client search performance beyond ~2000 records — defer until a client approaches that scale (PERF1)
- [ ] Metric cadence system — only prompt for metric values when due, configurable per metric (METRIC-CADENCE1)
- [ ] 90-day metric relevance check — prompt worker to confirm or change the chosen metric (METRIC-REVIEW1)
- [ ] Alliance prompt rotation — cycle 3-4 phrasings to prevent habituation (ALLIANCE-ROTATE1)
- [ ] Portal-based async alliance rating — post-session notification for participant self-rating (PORTAL-ALLIANCE1)
- [ ] Self-hosted LLM infrastructure — Ollama VPS-4 on OVHcloud Beauharnois serving KoNote + OpenWebUI + survey analysis. Qwen3.5-35B-A3B (MoE). DRR complete — see tasks/design-rationale/self-hosted-llm-infrastructure.md — GK reviews (AI-SELFHOST1)

## Recently Done

### Session 8 — Admin UX Improvements

- [x] Admin dashboard reorganised with section headings + 4 new cards (metrics, plausibility, plan templates, org profile) — PR #252 — 2026-03-04 (ADMIN-UX1)
- [x] Contextual help added to 6 admin pages + SMS character counter — PR #252 — 2026-03-04 (ADMIN-UX1)
- [x] Metric library: category filter, help text, plausibility link — PR #252 — 2026-03-04 (ADMIN-UX1)

### Code Review Fixes

- [x] Fix export_agency_data.py to exclude demo data by default — added `--include-demo` flag — 2026-03-04 (SEC-EXPORT1)

### Session 7 — PR Cleanup + TODO Housekeeping

- [x] Merge PR #236 — DQ1-TIER2 thresholds + docs verification — 2026-03-03 (DQ1-TIER2)
- [x] Merge PR #239 — survey shareable links + 6 missing French translations — 2026-03-03 (SURVEY-LINK1)
- [x] Clean up TODO.md — mark completed parking lot items, archive old entries — 2026-03-03

### Session 6 — Data Quality + Documentation + AI Toggles

- [x] Add second-tier plausibility thresholds — model fields, JS two-click confirm, 17 tests — 2026-03-03 (DQ1-TIER2)
- [x] Verify docs: DOC-DEMO1, DOC-PERM1-3, QA-PA-TEST1-2 — all accurate — 2026-03-03
- [x] Implement two-tier AI feature toggle split — 2026-03-03 (AI-TOGGLE1)
- [x] Verified: note sharing toggle (6/7 checks pass) — 2026-03-03 (QA-R7-PRIVACY2)
- [x] Build SRE workflow — PR #243 merged — 2026-03-03 (SRE1)
- [x] Build plausibility tuning dashboard — PR #244 merged — 2026-03-03 (DQ1-TUNE)

### Session 5 — Small-Cell Suppression + Compliance Summary

- [x] Small-cell suppression with secondary suppression — 2026-03-03 (QA-R8-RPT1)
- [x] Compliance summary page for executives (no PII) — 2026-03-03 (QA-R8-PERM2, QA-R7-EXEC-COMPLIANCE1)

### Session 4 — Documentation & Cleanup

- [x] Admin toolkit docs (01-09), deployment docs, website updates — 2026-03-03 (DEPLOY-TOOLKIT1, DOC-DEPLOY1, DOC-TECH1, WEBSITE-UPDATE1)

_Older items archived to [tasks/ARCHIVE.md](tasks/ARCHIVE.md)._
