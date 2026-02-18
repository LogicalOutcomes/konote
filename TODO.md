# Project Tasks

## Flagged

- [ ] Review requirements analysis doc with Sophie before sending to client (docs/konote-requirements-analysis-draft.md) — GG (DOC-REQ1)
- [ ] Approve Agency Permissions Interview questionnaire before first agency deployment (see tasks/agency-permissions-interview.md) — GG (ONBOARD-APPROVE)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — GG (SEC3-Q1)

## Active Work

### Phase: Launch Readiness

- [ ] Complete Agency Permissions Interview and signed Configuration Summary before first deployment — GG (ONBOARD-GATE)
- [ ] Verify production email configuration for exports, erasure alerts, and password resets — GG (OPS3)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — GG (OPS4)
- [ ] Document scheduled task setup for export monitoring in the runbook — GG (EXP2w)

### Phase: Communication Modules — complete!

### Phase: QA Round 6 Fixes

- [ ] 🔨 Fix receptionist over-permission on meetings page — add permission check to /events/meetings/ view (PERMISSION-5 -> QA-W56)
- [ ] 🔨 Fix language middleware — refactor to make user profile preference authoritative, resolving session contamination (BUG-24, BUG-14 -> QA-W57)
- [ ] 🔨 Translate alert text "Safety concern noted" for French interface (IMPROVE-8 -> QA-W58)

## Do Occasionally

Step-by-step commands for each task are in [tasks/recurring-tasks.md](tasks/recurring-tasks.md).

- [ ] **UX walkthrough** — run after UI changes. In Claude Code: `pytest tests/ux_walkthrough/ -v`, then review `tasks/ux-review-latest.md` and add fixes to TODO (UX-WALK1)
- [ ] **Code review** — run every 2–4 weeks or before a production deploy. Open Claude Code and paste the review prompt from [tasks/code-review-process.md](tasks/code-review-process.md) (REV1)
- [ ] **Full QA suite** — run after major releases or substantial UI changes. In Claude Code: `/run-scenario-server`, then `/capture-page-states` in konote-app; `/run-scenarios`, then `/run-page-audit` in konote-qa-scenarios (QA-FULL1)
- [ ] **French translation spot-check** — have a French speaker review key screens. Run `python manage.py check_translations` to verify .po file coverage (I18N-REV1)
- [ ] **Redeploy to Railway** — after merging to main. Push to `main` and Railway auto-deploys (OPS-RAIL1)

## Coming Up

### Phase: Post-Launch Communication Enhancements

- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (see tasks/messaging-calendar-plan.md Phase 6) (MSG-EMAIL-2WAY1)

### Phase: Other Upcoming

- [ ] Agency Onboarding Interview Pack — 12 refinements including session split, privacy prerequisites, plain-language wording, deployment checklist (see tasks/agency-permissions-interview.md) (ONBOARD1–12)
- [ ] Permissions Phase 2 — remaining 10 items: discharge access transitions, consent model, DV-safe mode, GATED clinical access, group schedule vs roster, per-field front desk edit, SCOPED→PROGRAM rename, funder report key, alert escalation, dashboard split (see tasks/permissions-expert-panel-2026-02-09.md) (PERM-P3–12)

### Phase: QA Round 6 — Design Tasks

- [ ] Design /admin/ URL restructuring for PM self-service — move management pages to /manage/ so PMs can reach plan templates, note templates, event types (FG-2, PERMISSION-1/2/3, BUG-1 -> QA-W59)

### Phase: UX Fixes

**Persona for all text rewrites:** Write as if speaking to a nonprofit staff person (coordinator, coach, counsellor, front desk) across a variety of program types — not a data analyst or developer.

- [ ] Build "Questions for You" portal feature — depends on SURVEY1, adds SurveyAssignment + PartialAnswer models, auto-save, dashboard card (see tasks/portal-questions-design.md) (PORTAL-Q1)

## Parking Lot

- [ ] Rename original KoNote GitHub repo to KoNote Classic and add redirect/link to this repo (REPO1)
- [ ] Add stress testing for 50+ concurrent users (QA-T15)
- [ ] Add legacy system import migration scenario test (QA-T16)
- [ ] Add onboarding guidance for new users (help link or first-run banner) (QA-W19)
- [ ] Implement multi-session testing for SCN-046 shared device scenario (QA-W55)
- [ ] Surveys — lightweight structured feedback collection from participants (see tasks/surveys-design.md) (SURVEY1)
- [ ] Add serious reportable events workflow and reporting (see tasks/serious-reportable-events.md) (SRE1)
- [ ] Build agency data offboarding command for secure departures and PIPEDA requests (SEC3)
- [ ] Add first-run setup wizard UI for guided initial configuration (SETUP1-UI)
- [ ] Add TOTP multi-factor authentication (see tasks/mfa-implementation.md) (SEC2)
- [ ] Optimize encrypted client search performance beyond ~2000 records (PERF1)
- [ ] Optimise executive dashboard queries — reduce N+1 per-program loop with prefetching or aggregation (PERF2)
- [ ] Add bulk operations for discharge and assignment workflows (UX17)
- [ ] Re-add API-based auto-translation to translate_strings for production use (I18N-API1)
- [ ] Document local PostgreSQL setup for security_audit and pytest workflows (DEV-PG1)
- [ ] Add deferred execution for Tier 3 erasure (24-hour delay) (ERASE-H8)
- [ ] Implement deployment workflow enhancements (see docs/plans/2026-02-05-deployment-workflow-design.md) (DEPLOY1)
- [ ] Audit all views for missing permission checks — PERMISSION-5 revealed nav hides link but view is unguarded (QA-W60)

## Recently Done

- [x] Mobile touch targets WCAG fix — enforce 44px minimum with explicit padding on nav, breadcrumbs, tabs, buttons, selects at mobile breakpoints — 2026-02-17 (UX-WALK5)
- [x] Fix 3 failing scenario tests — empty prerequisite guard, Priya Sharma test client, logout dropdown fallback + crash guard — 2026-02-17 (QA-FIX1, QA-FIX2, QA-FIX3)
- [x] Add demo content for suggestion themes (11 themes, 29 links) and staff messages (7 messages) — 2026-02-17 (DEMO-SUG1)
- [x] Remove blue border/outline around page — permanent fix, removed fragile :focus-visible on main content — 2026-02-17 (UI-FIX1)
- [x] Suggestion tracking system — SuggestionTheme/SuggestionLink models, CRUD + linking UI, Outcome Insights integration, Executive Dashboard theme counts, contextual toast on note save, 23 tests — 2026-02-17 (UX-INSIGHT6)
- [x] Plan UX fixes — HTMX Back-button cache fix, reworded view-only message, disabled Edit Plan button with tooltip, editable-plans filter and badge on participant list — 2026-02-17 (UX-PLAN1, UX-PLAN2, UX-PLAN3)
- [x] Dark mode WCAG AA contrast — breadcrumbs, add-link, tab-count badges — 2026-02-17 (UX-WALK3, UX-WALK4)
- [x] Insights & Suggestions Batch — template-driven chart interpretations, suggestion highlights on exec dashboard, suggestion tracking design doc, portal questions design doc — 2026-02-17 (UX-INSIGHT4, UX-INSIGHT5, UX-INSIGHT6, PORTAL-Q1)
- [x] UX Batch 3 — button sizing, dynamic terminology, staff contact info, chart descriptions, suggestion count fix, export delay wording, configurable Leave Quickly URL — 2026-02-17 (UX-MSG1, UX-MSG2, UX-PROG2, UX-INSIGHT2, UX-INSIGHT3, UX-EXPORT1, UX-SAFETY1)
- [x] UX Batch 2 — hx-confirm on plan actions, scroll position preservation, autofocus search, calendar sync rewrite — 2026-02-17 (UX6, UX7, UX9, UX-CAL1)
- [x] UX text rewrites (already on main) — Executive Overview intro, Need More Details, Programs subtitle, Insights intro, Approvals intro — 2026-02-17 (UX-DASH1, UX-DASH2, UX-PROG1, UX-INSIGHTS1, UX-ALERT1)
