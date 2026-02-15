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

### Phase: Communication Modules (see tasks/messaging-calendar-plan.md)

- [ ] Native appointment tracking — Meeting model, create/edit forms, staff dashboard, status transitions (MSG-MTG1)
- [ ] iCal calendar feed — private feed URL per staff, .ics generation, "Add to Calendar" button, no PII in feed (MSG-CAL1)
- [ ] Communication log — quick-log buttons ("Logged a Call", "Logged a Text"), full log form, timeline integration (MSG-LOG1)
- [ ] Consent and contact fields — SMS/email consent checkboxes, CASL date tracking, phone staleness indicator, preferred language (MSG-CONSENT1)
- [ ] Outbound email reminders — send appointment reminders via agency's existing Microsoft 365 or Google Workspace SMTP (MSG-EMAIL-OUT1)
- [ ] Outbound SMS reminders — send appointment reminders via Swift SMS Gateway (Canadian) or Twilio, plain-language error messages on meeting card (MSG-SMS1)
- [ ] Two-way email integration — Microsoft Graph API and Gmail API for send/receive tied to participant timeline, OAuth2 admin consent flow (MSG-EMAIL-2WAY1)
- [ ] Automated reminder cron — management command to send reminders for meetings in next 36 hours, retry on failure, system health tracking (MSG-AUTO1)
- [ ] System health banners — yellow/red banners on staff dashboard for SMS/email failures, alert email to admin after 24h outage (MSG-HEALTH1)
- [ ] Feature toggles for communication modules — enable/disable email, SMS, and appointments independently per agency (MSG-TOGGLE1)

### Phase: Other Upcoming

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
- [ ] Implement multi-session testing for SCN-046 shared device scenario (QA-W55)
- [ ] Add front desk message-taking route and permission model (UXP-RECEP)
- [ ] Add PM team meeting view grouped by staff with safe access utility (UXP-TEAM)
- [ ] Participant portal — separate login for participants to view progress and enter data (PORTAL1)
- [ ] Surveys — lightweight structured feedback collection from participants (SURVEY1)
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

- [x] Fixed 14 pre-existing test failures across plan permissions, login/auth, language switching, export — 2026-02-15 (TEST-FIX1)
- [x] Added audit database declarations to 41 test classes across 18 files — 2026-02-15 (TEST-FIX2)
- [x] Tabindex audit: all 10 usages are appropriate tabindex="-1", no cleanup needed — 2026-02-15 (QA-W20)
- [x] Session review: fixed 5 broken tests, added 3 PM permission tests, updated stale comments — 2026-02-15 (REV-FIX1)
- [x] Added compose email feature with CASL consent, preview, and audit logging — 2026-02-15 (MSG-EMAIL1)
- [x] Replaced meeting date/time picker with accessible chip-based UI — 2026-02-15 (UX-MEET2)
- [x] Renamed Reviews to Approvals and streamlined recommendation queue — 2026-02-15 (UX-REVIEW3)
- [x] Hidden stats row from Front Desk on home dashboard — 2026-02-15 (UX-DASH1)
- [x] Reordered contact fields and fixed select_other naming collisions — 2026-02-15 (DATA-FIX1)
- [x] Added Documents section to help page — 2026-02-15 (HELP-DOC1)
