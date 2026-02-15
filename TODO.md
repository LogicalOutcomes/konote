# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire before first agency deployment (see tasks/agency-permissions-interview.md) — GG (ONBOARD-APPROVE)
- [ ] Decide who can run the secure offboarding export command (KoNote team only vs self-hosted agencies) to finalize SEC3 design (see tasks/agency-data-offboarding.md) — GG (SEC3-Q1)

## Active Work

### Phase: Launch Readiness

- [ ] Complete Agency Permissions Interview and signed Configuration Summary before first deployment — GG (ONBOARD-GATE)
- [ ] Verify production email configuration for exports, erasure alerts, and password resets — GG (OPS3)
- [ ] Test backup restore from a production-like database dump and capture runbook notes — GG (OPS4)
- [ ] Build weekly export summary email command — GG (EXP2u)
- [ ] Document scheduled task setup for export monitoring in the runbook — GG (EXP2w)

## Do Occasionally

Step-by-step commands for each task are in [tasks/recurring-tasks.md](tasks/recurring-tasks.md).

- [ ] **UX walkthrough** — run after UI changes. In Claude Code: `pytest tests/ux_walkthrough/ -v`, then review `tasks/ux-review-latest.md` and add fixes to TODO (UX-WALK1)
- [ ] **Code review** — run every 2–4 weeks or before a production deploy. Open Claude Code and paste the review prompt from [tasks/code-review-process.md](tasks/code-review-process.md) (REV1)
- [ ] **Full QA suite** — run after major releases or substantial UI changes. In Claude Code: `/run-scenario-server`, then `/capture-page-states` in konote-app; `/run-scenarios`, then `/run-page-audit` in konote-qa-scenarios (QA-FULL1)
- [ ] **French translation spot-check** — have a French speaker review key screens. Run `python manage.py check_translations` to verify .po file coverage (I18N-REV1)
- [ ] **Redeploy to Railway** — after merging to main. Push to `main` and Railway auto-deploys (OPS-RAIL1)

## Coming Up

- [ ] Messaging module — consultant setup (Twilio, SMTP, cron), then safe-to-contact fields, composed messages, bulk messaging (see tasks/messaging-calendar-plan.md) (MSG-P0)
- [ ] Agency Onboarding Interview Pack — 12 refinements including session split, privacy prerequisites, plain-language wording, deployment checklist (see tasks/agency-permissions-interview.md) (ONBOARD1–12)
- [ ] Permissions Phase 2 — scoped admin tiers, discharge access transitions, consent model, DV-safe mode (see tasks/permissions-expert-panel-2026-02-09.md) (PERM-P1–12)
- [ ] PM Admin Access — let PMs manage templates, event types, metrics, registrations, and team members for their own programs (see tasks/pm-admin-access.md) (PM-ADMIN1–8)
  - [ ] Add permission keys to matrix for all six feature areas (PM-ADMIN1)
  - [ ] Replace @admin_required with @requires_permission on Team Members views + enforce elevation constraint (PM-ADMIN2)
  - [ ] Scope Plan Templates to programs and open to PMs (PM-ADMIN3)
  - [ ] Scope Note Templates to programs and open to PMs (PM-ADMIN4)
  - [ ] Scope Event Types to programs and open to PMs (PM-ADMIN5)
  - [ ] Scope Metrics to programs and open to PMs (PM-ADMIN6)
  - [ ] Scope Registration Links to programs and open to PMs (PM-ADMIN7)
  - [ ] Update navigation to show PM-accessible admin items based on permissions (PM-ADMIN8)

## Parking Lot

- [ ] Rename original KoNote GitHub repo to KoNote Classic and add redirect/link to this repo (REPO1)
- [ ] Delete temporary push folders after OneDrive sync completion (CLEANUP1)
- [ ] Add stress testing for 50+ concurrent users (QA-T15)
- [ ] Add legacy system import migration scenario test (QA-T16)
- [ ] Add onboarding guidance for new users (help link or first-run banner) (QA-W19)
- [ ] Reduce form tab stops with tabindex audit and cleanup (QA-W20)
- [ ] Implement multi-session testing for SCN-046 shared device scenario (QA-W55)
- [ ] Add front desk message-taking route and permission model (UXP-RECEP)
- [ ] Add PM team meeting view grouped by staff with safe access utility (UXP-TEAM)
- [ ] Add actionable admin health banners for SMS/email warnings (UXP-HEALTH)
- [ ] Add sortable last-contact date on participant list for PM oversight (UXP-CONTACT)
- [ ] Add serious reportable events workflow and reporting (see tasks/serious-reportable-events.md) (SRE1)
- [ ] Build agency data offboarding command for secure departures and PIPEDA requests (SEC3)
- [ ] Add first-run setup wizard for guided initial configuration (SETUP1)
- [ ] Add TOTP multi-factor authentication (see tasks/mfa-implementation.md) (SEC2)
- [ ] Optimize encrypted client search performance beyond ~2000 records (PERF1)
- [ ] Add bulk operations for discharge and assignment workflows (UX17)
- [ ] Re-add API-based auto-translation to translate_strings for production use (I18N-API1)
- [ ] Document local PostgreSQL setup for security_audit and pytest workflows (DEV-PG1)
- [ ] Add deferred execution for Tier 3 erasure (24-hour delay) (ERASE-H8)
- [ ] Implement deployment workflow enhancements (see docs/plans/2026-02-05-deployment-workflow-design.md) (DEPLOY1)

## Recently Done

- [x] Translated 25 new strings and fixed plural counting in translate_strings — 2026-02-15 (I18N-ALERT1)
- [x] Clarified export report privacy wording — 2026-02-14 (EXP-PRIV2)
- [x] Clarified Reviews menu scope as alert-cancellation recommendations only — 2026-02-14 (UX-REVIEW2)
- [x] Refreshed calendar view usability and layout — 2026-02-14 (CAL-UI1)
- [x] Improved meeting create form clarity for required date/time fields — 2026-02-14 (UX-MEET1)
- [x] Fixed Schedule Meeting button visibility and contrast states — 2026-02-14 (UX-MEET3)
- [x] Restricted Program Manager audit visibility to assigned-program scope — 2026-02-14 (PERM-AUD2)
- [x] Removed Executive audit log access and route visibility — 2026-02-14 (PERM-AUD1)
- [x] Limited Program Manager client-data export to program-scoped records — 2026-02-14 (EXP-SCOPE1)
- [x] Added Other (please specify) support for Province/Territory selections — 2026-02-14 (FORM-PROV1)
- [x] Added secondary email and phone fields for participant contact details — 2026-02-14 (UX-CONTACT2)
