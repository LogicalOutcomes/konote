# Project Tasks

## Flagged

- [ ] **HIGH PRIORITY:** Regenerate demo data on konote-dev VPS — run `python manage.py generate_demo_data --force` inside the web container. PRs #583, #584, #588 fixed demo data that was too sparse for reports (3 clients instead of 10, notes outside current FY, inconsistent filtering). Data won't be fixed until regenerated. — PB (OPS-DEMO1)
- [ ] To go live with demo survey: run `python manage.py seed_demo_survey` on konote-dev (PR #239 and #240 are now merged). The survey will be accessible at `/s/demo-program-feedback/` and the website demo page will embed it automatically — PB (DEMO-SURVEY1)
- [ ] Add LTE QA scenarios to sister repo — register the 7 new LTE routes in `konote-qa-scenarios/pages/page-inventory.yaml` (lte_list, lte_submit, lte_detail, lte_cancel, lte_flag_concerns, lte_download, lte_resolve_review) and write 3 scenarios: happy path, small-population block, OCAP program without community signoff. Must be done in a separate session in the `konote-qa-scenarios` repo. — (LTE-QA1)

## Active Work

### Phase: Launch Readiness

- [ ] Run deployment protocol with [funder partner] — currently at Phase 0 (see tasks/deployment-protocol.md, tasks/hosting-cost-comparison.md) — SG (DEPLOY-PC1)
- [ ] Discuss data handling acknowledgement during permissions interview — plaintext backup opt-in, designate contact person (see docs/data-handling-acknowledgement.md, deployment-protocol.md Phase 1) — SG (DEPLOY-DHA1)
- [ ] Follow up with [funder contact] for additional must-haves on feature comparison — (DEPLOY-PC2)
- [ ] Review and merge data handling acknowledgement PR #130 — expanded to cover encryption key custody, SharePoint/Google Drive responsibilities, exports, plaintext backups, staff departures. Wired into deployment protocol Phases 0/4/5. Needs legal review before first agency use (see docs/data-handling-acknowledgement.md) — SG (SEC3-AGREE1)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — SG (SEC3-Q1)
- [ ] Draft SaaS service agreement for LogicalOutcomes-managed agencies — data processing, security, SLAs, breach notification, termination, data export acknowledgement as schedule. Needs lawyer review (see tasks/saas-service-agreement.md) — SG (LEGAL-SaaS1)

### Phase: Deep Review Fixes (2026-03-06)

_All deep review fix tasks completed — see Recently Done._

### Phase: DRR Restructure Follow-up (2026-04-12)

- [ ] GK reviews DRR/principle restructure (7 new prescriptive DRRs extracted from 4 foundation docs, plus accessibility-requirements and customisable-terminology) before `develop` → `staging` → `main` promotion. Touches evaluation principles per Consultation Gates in CLAUDE.md — GK (DRR-REST1)
- [ ] Retrofit `access-tiers.md` with enforcement-block frontmatter covering the three-layer RBAC check (view decorator + middleware + template tag), `ClientAccessBlock`-checked-before-role, and no-time-based-expiry on `ClientAccessBlock`. These invariants moved from `foundation-security-by-default.md` and must be owned by access-tiers now. — (DRR-REST2)
- [ ] Amend `no-live-api-individual-data.md` with enforcement-block frontmatter covering: 10-minute export delay + admin notification for 100+ record exports, exports served through Django (not nginx/Caddy static file), time-limited UUID download links. Currently only the 24h expiry is named explicitly. — (DRR-REST3)
- [ ] Write `note-shape-invariants.md` DRR (or extend an existing DRR) to cover the two-lens (Their Perspective / Your Observations) form-validation rule referenced from `principles/collaborative-practice.md`. — (DRR-REST4)
- [ ] Build the enforcement tests, Semgrep rules, Django system checks, and pre-commit hooks named by the new security, accessibility, and terminology DRRs before promoting them from Draft to Decided. Scope and per-file prompt at [tasks/drr-enforcement-tests-prompt.md](tasks/drr-enforcement-tests-prompt.md). Blocks moving the 9 new DRRs off Draft status. — (DRR-REST5)

## Do Occasionally

Step-by-step commands for each task are in [tasks/recurring-tasks.md](tasks/recurring-tasks.md).

- [ ] **UX walkthrough** — run after UI changes. In Claude Code: `pytest tests/ux_walkthrough/ -v`, then review `tasks/ux-review-latest.md` and add fixes to TODO (UX-WALK1)
- [ ] **Quick code review** — run every 2–4 weeks or before a production deploy. Open Claude Code and paste the review prompt from [tasks/code-review-process.md](tasks/code-review-process.md) (REV1)
- [ ] **Deep code review (6 dimensions)** — run quarterly or before major releases. Uses structured checklists covering security, privacy, accessibility, deployment, AI governance, bilingual compliance. See [tasks/code-review-framework.md](tasks/code-review-framework.md) for prompts, or run all 6 with [tasks/deep-review-prompt.md](tasks/deep-review-prompt.md). Results go in private `konote-ops/reviews/` repo. Latest: 2026-03-06 (REV-DEEP1)
- [ ] **Full QA suite** — run after major releases or substantial UI changes. Two pipelines (A then B), five sessions total — see [tasks/recurring-tasks.md](tasks/recurring-tasks.md) for full steps (QA-FULL1)
- [ ] **French translation spot-check** — have a French speaker review key screens. Run `python manage.py check_translations` to verify .po file coverage (I18N-REV1)
- [ ] **Review demo presentation materials** — before any Common Approach presentation, review `demo.html` and linked HTML reports (funder portfolio dashboard, multi-program report, program outcome dashboard, evaluation framework editor, CIDS working document) for accuracy and current data. Check links aren't broken. (DEMO-PRES1)
- [ ] **Redeploy to OVHcloud VPS** — after merging to main. SSH in and run `docker compose pull && docker compose up -d` (OPS-DEPLOY1)

## Coming Up

### Phase: Goal Workflow Redesign (see tasks/goal-workflow-redesign.md)

**Phase A — Fix the blockers**
- [ ] Create dedicated `goal_create_from_suggestion` save endpoint (HTMX POST, no client-side form) with error handling (soft failure returns form, hard failure returns error card) — (GW-R1)
- [ ] Auto-create sections silently using priority chain: match existing > match program-wide > AI suggestion > "General" — (GW-R2)
- [ ] Rename "Shape this target" button to "Suggest a goal" with sparkle icon — (GW-R3)

**Phase B — Suggestion card polish**
- [ ] Demote "Suggested area" to secondary line on card — (GW-R4)
- [ ] Default custom metric to included; remove Include/Skip from card; show in success message — (GW-R5)
- [ ] Rename "Let me edit it" to "Let me review first" — (GW-R6)
- [ ] Hide entry points after suggestion loads; "Start over" restores them — (GW-R7)
- [ ] Store suggestion in server-side session, pass reference token to client — (GW-R19)
- [ ] Animated loading bar with text rotation for AI wait — (GW-T5)

**Phase C — Form improvements ("Let me review first" path)**
- [ ] Reorder form: participant words > goal name > description (collapsible) > metrics > section (last) — (GW-R8)
- [ ] Section picker: pre-select most recent; pre-fill AI suggestion; auto-create if empty — (GW-R9)
- [ ] Add reassurance near submit: "You can revise this goal later" — (GW-R10)
- [ ] Unify AI/non-AI form HTML into single form, remove SYNC duplication — (GW-T4)

**Phase D — Entry point tuning**
- [ ] Conditional layout: quick pick first if 3+ common goals, AI first otherwise — (GW-R11)
- [ ] Increase textarea to rows=3 with CSS min-height — (GW-R12)
- [ ] Move onboarding hint to contextual help icon on entry point — (GW-R13)
- [ ] Persistent participant-words blockquote throughout flow — (GW-R21)
- [ ] Quick pick prompts for participant's words after selection — (GW-R22)
- [ ] Relabel metric tiers with clinical language — (GW-R23)
- [ ] Add "Why this suggestion" collapsible with AI reasoning — (GW-R24)

**Phase E — Accessibility fixes**
- [ ] Fix aria-label: "AI-suggested goal" not "target" — (GW-R14)
- [ ] Add aria-label to custom metric pre block — (GW-R15)
- [ ] Change #form-announce to aria-live="assertive" — (GW-R16)
- [ ] Add "Saving your goal..." screen reader announcement — (GW-R17)
- [ ] Add hx-sync="this:abort" to shape button — (GW-R18)

**Phase F — Program setup (longer-term)** — GK reviews domain section templates
- [ ] Pre-seed programs with domain section templates at program setup — (GW-R20)

### Phase: Session 7 Prep — Admin UX & Configuration

- [ ] Pre-report data quality checks — validate data quality before partner report export (see tasks/data-validation-design.md) (DQ2)

### Phase: Evaluation Planning & CIDS Full Tier

- [ ] Review draft evaluation protocol for CIDS Full Tier metadata — evaluator-led process covering services, activities, risks, counterfactuals, stakeholder definitions (see tasks/cids-evaluation-protocol.md) — GK reviews draft (EVAL-PROTOCOL1)
- [ ] Review draft LLM-assisted evaluation planning prompt — structured conversation guide for evaluators to use with a more capable LLM (see tasks/cids-evaluation-planning-prompt.md) — GK reviews draft (EVAL-PROMPT1)
- [x] Create literature review brief template — standalone template at `docs/literature-review-brief-template.md` covering comparable programs, counterfactual evidence, risk factors, measurement instruments, cultural safety, and sources — cross-referenced from evaluation export guide — GK reviews template — 2026-04-10 (EVAL-LITREV1)
- [x] Turn evaluation planning and post-export enrichment designs into an implementation-ready spec with models, API payloads, and screens (see tasks/design-rationale/cids-privacy-architecture.md) — 2026-03-07 (EVAL-ENRICH-SPEC1)
- [x] Build Evaluation Framework editor UI in KoNote (see tasks/wireframes/evaluation-framework-editor.html) — PR #422, deployed and validated on dev VPS — 2026-03-07 (EVAL-EDITOR1)

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Offline Field Collection (if requested by client)

- [ ] Deploy ODK Central on Canadian VM (Docker Compose) — ops task (FIELD-ODK-DEPLOY1)
- [ ] Circle Observation XLSForm — depends on circles in ODK (FIELD-ODK-FORM-CIR1)
- [ ] Push Circle/CircleMember Entity lists — depends on above (FIELD-ODK-CIRCLES1)
- [ ] Agency-facing documentation — ODK Collect setup, device loss protocol (FIELD-ODK-DOC1)

### Phase: Evaluation Export Governance & Documentation (see tasks/eval-export-governance.md)

**Simplified scope (2026-04-09):** The original plan had 11 tasks. The governance list + permission-audit list + dashboard card were merged into a single GOV1 deliverable; GOV4 + GOV5 were combined into one history+banner task; and DOC1–4 were collapsed into a single doc task that leads with the ED one-pager. Pipeline tests (GOV7) stay standalone because the de-identification code is safety-critical.

**Code & UI:** ✅ All done — see Recently Done.

**Documentation:** ✅ Done — see Recently Done.

### Phase: Longitudinal Trajectory Export (LTE) — see tasks/phase-lte-prompt.md

Implementation complete (11 of 13 tasks done, see Recently Done). Remaining work is QA scenarios in the sister repo and GK's pre-merge review. DRR: `tasks/design-rationale/evaluation-microdata-export.md`.

- [ ] Register new LTE routes in `konote-qa-scenarios/pages/page-inventory.yaml` and add scenarios (happy path, floor block, OCAP without signoff) — follow-up session in the konote-qa-scenarios repo (LTE-QA1)
- [ ] GK reviews completed LTE implementation before merge — verifies demographic suppression, fuzzing correctness, community governance gating — GK (LTE-GKREVIEW1)

### Phase: Documentation & Website Updates

_All documentation tasks completed — see Recently Done._

## Parking Lot: Ready to Build

Scope is clear, just needs time. A session can pick these up without special approval.

- [ ] Extract shared custom field utilities (form builder, save helper, context builder) to reduce duplication between staff and portal views — (REFACTOR2)

## Parking Lot: Needs Review

Not yet clear we should build these, or the design isn't settled. May be too complex, too risky, or not worth the effort. **Do not build without explicit user approval in the current conversation.**

- [ ] Add CIDS conformance badge and SHACL validation reporting — `validate_cids_jsonld` management command now works (pyshacl installed as test dep). Consider adding badge UI after first funder requests conformance certification (CIDS-VALIDATE1)
- [ ] Verify BLOCKER-1 and BLOCKER-2 with manual JAWS test — automated Playwright tests pass, manual assistive tech testing still needed. Do before launch. (T50)
- [ ] DQ2 implementation: define severity tiers so the quality gate doesn't produce too many warnings that staff ignore (DQ2-TIERS)
- [ ] Add stress testing for 50+ concurrent users — defer until a client is onboarded (QA-T15)
- [ ] Add legacy system import migration scenario test — defer until an import is needed (QA-T16)
- [ ] Implement multi-session testing for SCN-046 shared device scenario — defer until workflows stabilise (QA-W55)
- [ ] Optimize encrypted client search performance beyond ~2000 records — defer until a client approaches that scale (PERF1)

## Recently Done

- [x] Evaluation export documentation bundle — ED-facing one-pager (`docs/evaluation-export-guide.md`) + cross-references in admin reporting guide, help page, and agency permissions interview (Section 7.4) — 2026-04-10 (EVAL-DOCS)
- [x] Pipeline test suite for `deidentify.py` — 75 safety-critical tests covering consent filtering, PII stripping, study IDs, age bands, geography, k-anonymity, population thresholds, suppression ceiling, CSV format, full integration — 2026-04-10 (EVAL-GOV7)
- [x] Wire up `is_evaluation_exportable` custom field groups — form dynamically queries `CustomFieldGroup.is_evaluation_exportable` and adds QI column checkboxes; 2 tests — 2026-04-10 (EVAL-GOV6)
- [x] Export history view with agreement-expiry banner — lists past evaluation exports with evaluator info, status (active/expired/revoked), expired agreement warning banner; nav entry; 8 tests — 2026-04-10 (EVAL-GOV-HISTORY)
- [x] Decommission old VPS (141.227.151.7) — new Canadian VPS stable after 5+ weeks, old Swiss instance cancelled in OVH control panel — 2026-04-09 (OPS-DECOM1)
- [x] Longitudinal Trajectory Export (LTE) implementation — small-population evaluation tier with new `report.evaluation_export_small_population` permission, `LTEExportGrant` model + signal, "no privacy officer = no LTE" gate, `LTEExportRequestForm` with structured preconditions (REB, DSA, evaluator credentials, community governance, acknowledgement), `LTESmallPopulationPipeline` subclassing `DeidentificationPipeline` with demographic suppression and metric/session/hours fuzzing, 5-business-day review-and-cancel window with flag-freeze/resume, distributed admin oversight via signed "Flag concerns" email tokens, post-hoc privacy officer review with agency-wide rate limit, distinct `longitudinal_trajectory_export` audit category, LTE CSV output with PROGRAM EVALUATION warning header, `tests/test_lte.py` end-to-end coverage, `docs/lte-privacy-officer-guide.md` + admin reporting guide section, 146 French translations — 2026-04-09 (LTE-PERM1, LTE-FORM1, LTE-PIPE1, LTE-WINDOW1, LTE-OVERSIGHT1, LTE-REVIEW1, LTE-AUDIT1, LTE-OUT1, LTE-TEST1, LTE-DOC1, LTE-I18N1)
- [x] Evaluator Export grant audit UI — new `EvaluationExportGrant` model + `post_save` signal keeping the `User.evaluation_export_granted` cache in sync, `EvaluationExportGrantForm` enforcing a substantive reason (≥15 chars, blocklist), three admin views (list / create / revoke) at `/manage/users/evaluation-export/` with immutable audit logging, nav entry in both admin and PM dropdowns, Django admin `readonly_fields` block on direct flag edits, demo seed routed through the grant model, 24 French translations, and ~25 new tests — 2026-04-09 (EVAL-GOV1)
- [x] Migrate KoNote from Swiss VPS to Canadian VPS — new OVH VPS at 148.113.191.63, Canadian data residency confirmed — 2026-03-06 (OPS-MIGRATE1)
- [x] Close Evaluator Export admin bypass — removed `is_admin` bypass in `can_create_evaluation_export` + nav check, added missing Team Members link to admin menu, wired `seed_eval_export_demo` into container-startup orchestrator with Casey/Morgan/Eva granted, added fast-path short-circuit, hoisted `EVAL_EXPORT_GRANTEES` constant, added regression tests (`EvaluatorExportPermissionTest` in `tests/test_export_permissions.py`), wrote EVAL-GOV1 implementation prompt — PRs #617, #622, #623, #624 — 2026-04-09 (EVAL-GOV-BYPASS1)
- [x] De-identified evaluation microdata export — 10-step de-identification pipeline with k-anonymity (k=5), pseudonymous IDs, generalised demographics, population thresholds, enhanced audit trail, preview/confirm flow, permission-gated nav — 2026-04-07 (EVAL-EXPORT1)
- [x] Insights quality & language features — DQ1: practice signal contextual sentence + month count in summary bar; CONF1: raised theme auto-link threshold from 2→3 words; LANG1: EN/FR language detection on quotes, AI prompt language awareness, FR pills on mixed-language Insights pages — PR #595 — 2026-04-03 (INSIGHTS-DQ1, INSIGHTS-CONF1, INSIGHTS-LANG1)
- [x] Dashboard & Insights enrichment — FHIR metadata features: program summary sentences, practice indicators, goal source distribution on Insights; stale episodes attention signal on Dashboard; batch query optimization; simplified both pages (removed funder stats, cohort comparison, cross-tab, dashboard bloat — 8 sections → 5 on Insights, ~20 rows → ~8 per program card) — PRs #529-#533 — 2026-03-16 (ENRICH1)
- [x] Expand accessibility tests to cover portal flow (dashboard, journal, goals) and report/chart flow (outcome insights) — axe-core tests in test_a11y_ci.py — 2026-03-12 (REV26-A11Y1)
- [x] AI provider configuration guide for operators — docs/ai-provider-guide.md covering cloud vs self-hosted, data residency, configuration, costs — 2026-03-12 (REV26-AI4)
- [x] Data retention schedule + breach response workflow — docs/retention-schedule.md and docs/breach-response-workflow.md, with cross-references from privacy-policy-template.md and security-operations.md — 2026-03-12 (REV26-PRIV1)
- [x] CIDS Full Tier + Evaluation Framework deployed to dev VPS — PR #422 merged, migration dependency fix PR #423, all exports pass SHACL validation, coverage dashboard live at 8/14 classes, evaluation framework CRUD working end-to-end — 2026-03-07 (CIDS-DEPLOY1)
- [x] Translation catalog cleanup — filled 16 remaining empty French entries, 0 empty remain — PR #414 — 2026-03-07 (REV26-I18N2)
- [x] Tenant provisioning + backup recovery resumability — --skip-to, --dry-run, --pre-restore, --full, transaction wrapping, expanded encryption checks — PR #414 — 2026-03-07 (REV26-DEP3)
- [x] Extract role string constants into auth_app/constants.py — 5 PRs merged, 107 files updated — 2026-03-07 (REFACTOR1)
- [x] Add smoke test for all-programs HTML export path — PR #340 — 2026-03-07 (CHORE-RPT-TEST1)
- [x] Deep review follow-up hardening pass — AI scrubber expanded, focused analysis and note-structure flows scrubbed, insecure remote insights HTTP blocked, Docker build inputs tightened, tenant-key rotation disabled, `/health/` healthcheck wired, production startup fails closed on public-tenant bootstrap, French survey/export fixes landed, public survey page-step validation improved, registration intake/review audit coverage added — 2026-03-06 (REV26-SEC1, REV26-DEP1, REV26-DEP2, REV26-AI1, REV26-AI2, REV26-AI3, REV26-I18N1)
- [x] Graduated privacy threshold + focused theme analysis — N=5 self-hosted / N=15 external, Ask a Question UI, AI-powered suggestion search, DRR updates — 2026-03-05 (AI-FOCUSED-THEME1)

### Session 13 — Report Fixes & Cleanup

- [x] Server Sharing phase completed — multi-tenant infrastructure, admin UI self-service config — PR #220, #252 — 2026-03-04 (ADMIN-UX1)
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
