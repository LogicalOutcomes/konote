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

## Recently Done

- [x] Review and merge fix/audit-log-pm-scoping — fixes PM audit log scoping bug — 2026-02-16 (AUDIT-SCOPE1)
- [x] Delete temporary push folders and junk files (C:\Temp\konote-push, _ul, NUL) — 2026-02-16 (CLEANUP1)
- [x] Fix portal nav: add missing links (Milestones, Journal, Messages), restore Leave quickly spacing, register feature toggles — 2026-02-15 (PORTAL-FIX1)
- [x] Update UX walkthrough report with browser-based findings, remove consent checkbox from quick notes — 2026-02-15 (UX-WALK2)
- [x] Portal staff management — invite flow, manage/revoke/reset MFA views, demo seed data, portal section on client info tab — 2026-02-15 (PORTAL1)
- [x] Apply setup management command — `apply_setup` reads JSON config and creates settings, terminology, features, programs, templates, custom fields, metrics; sample config for Youth Services agency; 16 tests — 2026-02-15 (SETUP1)
- [x] Staff messaging — leave/view messages on client files, unread badge, My Messages page — 2026-02-15 (UXP-RECEP)
- [x] Team activity report — PM meeting prep view showing notes, comms, and meetings by staff — 2026-02-15 (UXP-TEAM)
- [x] Last-contact column on participant list for PM oversight — 2026-02-15 (UXP-CONTACT)
- [x] Weekly export summary email command — `send_export_summary` queries last 7 days of exports and emails digest to admins — 2026-02-15 (EXP2u)
