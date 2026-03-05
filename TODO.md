# Project Tasks

## Flagged

- [ ] Contact Common Approach to position KoNote as a pilot CIDS implementer — early engagement for co-marketing and advance notice of spec changes — GK (CIDS-CA-OUTREACH1)
- [ ] To go live with demo survey: run `python manage.py seed_demo_survey` on konote-dev (PR #239 and #240 are now merged). The survey will be accessible at `/s/demo-program-feedback/` and the website demo page will embed it automatically — PB (DEMO-SURVEY1)

## Active Work

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
- [ ] **Redeploy to OVHcloud VPS** — after merging to main. SSH in and run `docker compose pull && docker compose up -d` (OPS-DEPLOY1)

## Coming Up

### Phase: Session 7 Prep — Admin UX & Configuration

- [ ] Pre-report data quality checks — validate data quality before partner report export (see tasks/data-validation-design.md) (DQ2)

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Server Sharing — cost optimization, not a launch prerequisite (completed in PR #220)

Multiple agencies can deploy today on independent OVHcloud VPS instances (~$22/month each). Server sharing reduces per-agency costs to $4–10/month with walled database schemas per agency on one server.

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

- [ ] Graduated privacy threshold (N=5 self-hosted, N=15 external) + focused theme analysis — managers type a question, AI searches suggestions for relevant patterns. Includes DRR updates. See [tasks/focused-theme-analysis.md](tasks/focused-theme-analysis.md) — GK approved (AI-FOCUSED-THEME1)
- [ ] Extract role string constants (ROLE_STAFF, ROLE_PROGRAM_MANAGER, etc.) into auth_app/constants.py — 400+ raw string literals across the codebase use "staff", "program_manager" etc. (REFACTOR1)
- [ ] Add smoke test for all-programs HTML export path (CHORE-RPT-TEST1)

## Parking Lot: Needs Review

Not yet clear we should build these, or the design isn't settled. May be too complex, too risky, or not worth the effort. **Do not build without explicit user approval in the current conversation.**

- [ ] Add CIDS conformance badge and SHACL validation reporting — deferred, requires pyshacl dependency. Consider after first funder requests conformance certification (CIDS-VALIDATE1)
- [ ] Verify BLOCKER-1 and BLOCKER-2 with manual JAWS test — automated Playwright tests pass, manual assistive tech testing still needed. Do before launch. (T50)
- [ ] DQ2 implementation: define severity tiers so the quality gate doesn't produce too many warnings that staff ignore (DQ2-TIERS)
- [ ] Add stress testing for 50+ concurrent users — defer until a client is onboarded (QA-T15)
- [ ] Add legacy system import migration scenario test — defer until an import is needed (QA-T16)
- [ ] Implement multi-session testing for SCN-046 shared device scenario — defer until workflows stabilise (QA-W55)
- [ ] Optimize encrypted client search performance beyond ~2000 records — defer until a client approaches that scale (PERF1)

## Recently Done

### Session 13 — Report Fixes & Cleanup

- [x] All-programs HTML export support — added template + view branch for HTML format — PR #337 — 2026-03-05 (RPT-HTML-ALLPROG1)
- [x] Simplified all-programs aggregation — consolidated 4 iterations into single pass — PR #337 — 2026-03-05 (RPT-SIMPLIFY1)
- [x] Extracted shared CSS partial + aggregation helper — ~240 lines deduped, isinstance guard fixed — 2026-03-05 (CHORE-RPT-CSS1, CHORE-RPT-FIX1)
- [x] Marked DOC-RP4, SCALE-ROLLUP1, OPS-MANAGED1, QA-R7-EXEC-COMPLIANCE1 as done — PR #336 — 2026-03-05

### Session 12 — TODO Cleanup

- [x] Funder reporting design doc — architecture in reporting-architecture DRR, cross-agency reporting plan, funder report approval design — 2026-03-05 (DOC-RP4)
- [x] Funder reporting dashboard — funder_report.py, consortia/publish.py, rollup aggregation, report templates, approval workflow, cell suppression — 2026-03-05 (SCALE-ROLLUP1)
- [x] Managed service model — defined in p0-managed-service-plan.md + ovhcloud-deployment DRR — 2026-03-05 (OPS-MANAGED1)
- [x] Executive compliance report — aggregate dashboard, privacy request counts, processing times (no PII) — 2026-03-05 (QA-R7-EXEC-COMPLIANCE1)

### Session 11 — Cleanup

- [x] Clean Railway/FullHost/Elestio references from ~24 historical task and plan files — updated active docs to OVHcloud, added archive banners to historical docs — 2026-03-04 (CHORE-HIST-CLEANUP1)
- [x] Self-hosted LLM infrastructure DRR — Ollama VPS-4, Qwen3.5-35B-A3B, OVHcloud Beauharnois — PR #237 — 2026-03-03 (AI-SELFHOST1)
- [x] In-app configuration overview dashboard — all active settings with decision rationale — PR #278 — 2026-03-04 (DEPLOY-CONFIG-UI1)
- [x] Metric rationale log + scheduled assessments — append-only rationale changelog, AI auto-generation, assessment-due detection, severity bands, assessment note form — PR #283 — 2026-03-04 (ASSESS1)
- [x] PR #283 review fixes — French rationale display, @require_POST on HTMX endpoints, audit logging for rationale changes, restored missing ai.py functions, 8 new view tests — PR #286 — 2026-03-04 (ASSESS1-FIX)
- [x] Updated konote-qa-scenarios page-inventory.yaml v2.3 — 6 new pages for assessments, rationale, config dashboard — 2026-03-04 (QA-PAGES1)

### Session 10 — Translations & Consent

- [x] Fill empty French translations in django.po — all 5,124 entries translated, 0 empty — 2026-03-04 (I18N-FILL1)
- [x] Consent withdrawal workflow — PIPEDA withdrawal with data retention, read-only enforcement, audit trail, 10 tests — 2026-03-04 (QA-R7-PRIVACY2)

### Session 9 — Metric Freshness & Alliance

- [x] Metric cadence system — configurable per-metric recording frequency, skips metrics not yet due — 2026-03-04 (METRIC-CADENCE1)
- [x] 90-day metric relevance check — HTMX banner prompts worker to confirm or change stale metrics — 2026-03-04 (METRIC-REVIEW1)
- [x] Alliance prompt rotation — cycles 3 prompt phrasings to prevent habituation — 2026-03-04 (ALLIANCE-ROTATE1)
- [x] Portal async alliance rating — post-session participant self-rating via portal, auto-created on note save — 2026-03-04 (PORTAL-ALLIANCE1)

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

_Older items archived to [tasks/ARCHIVE.md](tasks/ARCHIVE.md)._
