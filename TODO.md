# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire — must be finalised before first agency deployment. See `tasks/agency-permissions-interview.md` (ONBOARD-APPROVE)
- [ ] Decide who runs the export command — KoNote team only, or self-hosted agencies too? Shapes the entire SEC3 design. See `tasks/agency-data-offboarding.md` (SEC3-Q1)

## Active Work

### Messaging & Calendar UX Polish — See `tasks/messaging-ux-polish.md`

All UXP tasks complete — committed as `21bb390`.

### Pre-Launch Checklist

- [ ] Complete Agency Permissions Interview — signed Configuration Summary required before each new agency deployment (ONBOARD-GATE)
- [ ] Verify email is configured — needed for exports, erasure alerts, password resets. See `.env.example` for Resend.com (recommended) and M365 setup. Set `DEMO_EMAIL_BASE` to test with demo users (OPS3)
- [ ] Test backup restore from a real database dump (OPS4)

### UX Walkthrough

- [x] Re-run full UX walkthrough — 57/57 tests passing, 321 pages audited. Report at `tasks/ux-review-latest.md` (UX-RESTORE1) ✓
- [x] Fix heading level skip (h1→h3) on Events tab — changed `<h3>` to `<h2>` in quick-log templates (UX-HEAD1) ✓

### Do Occasionally

- [ ] Run UX walkthrough — `pytest tests/ux_walkthrough/ -v`, review report at `tasks/ux-review-latest.md` (UX-WALK1)
- [ ] French translation review — have a French speaker spot-check AI translations, especially new strings. Run `python manage.py check_translations` to see coverage stats (I18N-REV1)
- [ ] Redeploy to Railway — push to `main`, Railway auto-deploys. See `docs/deploy-railway.md` (OPS-RAIL1)
- [ ] Redeploy to FullHost — push to `main`, then trigger redeploy via API or dashboard. See `docs/deploy-fullhost.md` (OPS-FH1)
- [ ] Code review round — open Claude Code in VS Code, say "review the codebase for code quality, security, and consistency issues" — see `tasks/code-review-process.md` (REV1)
- [ ] **Full QA Suite** — Run after major releases or UI changes. See below for commands. (QA-FULL1)

### Full QA Suite Commands

> **Using Kilo Code instead of Claude Code?** The `/slash-commands` are Claude Code conventions (`.claude/commands/`). Kilo Code doesn't read those files. See the **Kilo Code alternatives** below.

> **⚠️ Long-running commands:** Steps 1 and 3 run Playwright browser tests (101+ tests, ~2–5 minutes). When you run `execute_command`, the terminal will report "Command is still running" — this is normal. **Wait for the terminal update with the final output. Do NOT run echo/polling commands to check status.** The test results will appear automatically when the command finishes.

| Step | Repo | Claude Code | Kilo Code Alternative |
|------|------|------------|-----------------------|
| 1. Capture scenario screenshots | konote-app | `/run-scenario-server` | Run in PowerShell (takes ~2–5 min, wait for completion): `$env:SCENARIO_HOLDOUT_DIR = "C:\Users\gilli\OneDrive\Documents\GitHub\konote-qa-scenarios"; pytest tests/scenario_eval/ -v --no-llm` |
| 2. Evaluate scenarios | qa-scenarios | `/run-scenarios` | Tell Kilo: "Read `.claude/commands/run-scenarios.md` and follow those instructions" |
| 3. Capture page screenshots | konote-app | `/capture-page-states` | Tell Kilo: "Read `.claude/commands/capture-page-states.md` and follow those instructions" |
| 4. Evaluate pages | qa-scenarios | `/run-page-audit` | Tell Kilo: "Read `.claude/commands/run-page-audit.md` and follow those instructions" |
| 5. Process findings | konote-app | `/process-qa-report` | Tell Kilo: "Read `.claude/commands/process-qa-report.md` and follow those instructions" |

Subset runs (PowerShell, in this repo):
```powershell
$env:SCENARIO_HOLDOUT_DIR = "C:\Users\gilli\OneDrive\Documents\GitHub\konote-qa-scenarios"
# Calibration only
pytest tests/scenario_eval/ -v --no-llm -k "calibration"
# Smoke test (6 scenarios)
pytest tests/scenario_eval/ -v --no-llm -k "smoke"
# Single scenario
pytest tests/scenario_eval/ -v --no-llm -k "SCN_010"
```

### QA Round 5 Fixes — See `tasks/qa-action-plan-2026-02-13a.md`

All Tier 1 and Tier 2 tickets complete. Tier 3 deferred (TEST-19 multi-session, IMPROVE-12 research).

## Coming Up

### Documentation Catch-Up — New Features

All docs lagged behind recent feature work (messaging, calendar, meetings, consent, alert safety workflow, funder profiles, export hardening). Each task below is independent — can be done in any order.

#### Permissions & RBAC

- [x] Update permissions matrix doc — 13 rows added, 6 fixes, two-person safety + consent immutability rules — 2026-02-13 (DOC-PERM1)

#### KoNote Website (konote-website repo)

- [x] Update features.html — added messaging, meetings/calendar, consent cards; removed scheduling caveat; two-person safety rule — 2026-02-13 (DOC-WEB1)
- [ ] Fix website footer — change `KoNote-Redux` repo link to current `KoNote` repo URL across all pages (DOC-WEB2)
- [ ] Update website README — fix old repo reference, add `evidence.html` and `demo.html` to structure section (DOC-WEB3)

#### App Documentation (docs/ folder)

- [ ] Update docs/index.md "What's New" — add messaging/communications, meetings/calendar with iCal feed, consent management with withdrawal tracking, alert safety workflow (two-person rule), funder profiles with small-cell suppression (DOC-INDEX1)
- [ ] Update using-KoNote.md — add staff guide sections for: logging communications (quick-log + full form), scheduling meetings, using calendar feed (iCal), recommending alert cancellation, viewing communication history on timeline (DOC-USER1)
- [ ] Update administering-KoNote.md — add admin sections for: messaging settings and feature toggles (SMS, email), calendar feed token management, communication channel configuration, funder profile setup (DOC-ADMIN1)
- [ ] Update technical-documentation.md — add Communication and Meeting models, consent fields on ClientFile, new permission keys (meeting.*, communication.*, alert.recommend_cancel, alert.review_cancel_recommendation), messaging services layer (DOC-TECH1)
- [ ] Update deploying-KoNote.md — add Twilio account setup for SMS, SMTP configuration for email (Google Workspace / M365), env vars for messaging features. Fix case mismatch: docs/index.md references `deploying-KoNote.md` — verify filename consistency (DOC-DEPLOY1)

#### Cross-Cutting

- [ ] Create CHANGELOG.md — user-facing release notes summarising what's changed, grouped by feature area. Agencies need this to know what's new between updates (DOC-CHANGE1)

### QA Scenario Coverage: New Features — See `tasks/qa-new-feature-scenarios.md`

7 new scenarios (SCN-080 through SCN-086) covering messaging, meetings, calendar, consent guardrails, permission enforcement, and funder reporting. Scenarios go in konote-qa-scenarios repo; test methods go here.

- [ ] Write SCN-085 — front desk denied messaging/meetings (QA-SCN1)
- [ ] Write SCN-080 — staff logs a phone call via quick-log (QA-SCN2)
- [ ] Write SCN-083 — staff sets up calendar feed (QA-SCN3)
- [ ] Write SCN-081 — staff schedules meeting and sends reminder (QA-SCN4)
- [ ] Write SCN-082 — PM reviews meeting dashboard and updates status (QA-SCN5)
- [ ] Write SCN-084 — consent/messaging interaction with consent blocks (QA-SCN6)
- [ ] Write SCN-086 — funder report with small-cell suppression (QA-SCN7)
- [ ] Add test methods for SCN-080–086 in tests/scenario_eval/test_scenario_eval.py (QA-SCN8)
- [x] Verify seed_demo_data has prerequisite data for new scenarios — 2026-02-13 (QA-SCN10)

### Messaging, Meetings & Calendar

See `tasks/messaging-calendar-plan.md` (phase-by-phase build) and `tasks/messaging-modules-architecture.md` (modular toggle system, Safety-First mode, deployment docs)

- [ ] Phase 0: Consultant setup — Twilio account, email SMTP (Google Workspace or M365), Railway cron, handoff runbook (MSG-P0)
- [x] Phase 1 (Wave 1): Meeting model, forms, views, URLs, templates, iCal feed — 2026-02-13 (MSG-P1)
- [x] Phase 2A (Wave 1): Communication model + forms scaffold — views/templates in Wave 2 — 2026-02-13 (MSG-P2A)
- [x] Phase 3 (Wave 1): Consent & contact fields on ClientFile — email, phone staleness, CASL consent, preferred language — 2026-02-13 (MSG-P3)
- [x] Phase 2B-J (Wave 2): Communication log views, quick-log buttons, timeline integration — 2026-02-13 (MSG-P2B)
- [x] Phase 4A-C (Wave 2): Settings, Twilio/SMTP config, services layer — 2026-02-13 (MSG-P4A)
- [x] Phase 4D-K (Wave 3): Send preview, feature toggles, health banners, unsubscribe, messaging settings — 2026-02-13 (MSG-P4B)
- [ ] Safe-to-contact fields — structured channel safety, code name, review date on ClientFile (MSG-MOD2)
- [ ] Composed messages — staff can write follow-ups/check-ins from client page, preview before send (MSG-MOD3)
- [ ] Bulk messaging — send to program group with consent-filtered recipient list (MSG-MOD4)
- [ ] Phase 5 (Wave 4): Automated reminders — only after manual send proven in production (MSG-P5)


### Agency Onboarding — See `tasks/agency-permissions-interview.md`

- [ ] Split interview into two sessions — Session A (60 min) and Session B (45 min) (ONBOARD1)
- [ ] Add privacy prerequisites to prep sheet (ONBOARD2)
- [ ] Add missing scenarios — referral call, transfer, multi-site, portal, emergency (ONBOARD3)
- [ ] Create one-page recording sheet (ONBOARD4)
- [ ] Update admin section for scoped admin tiers (ONBOARD5)
- [ ] Fix jargon — "scoped" → "limited to", safer language for DV contexts (ONBOARD6)
- [ ] Add breach notification, data retention, and PHIPA questions to Session A (ONBOARD7)
- [ ] Add warm-up question and "what system do you use now?" to opening (ONBOARD8)
- [ ] Create deployment checklist template — verifiable gate for each new agency (ONBOARD9)
- [ ] Create visual one-page summary template — quick-reference for agency ED and board (ONBOARD10)
- [ ] Add version number and date to questionnaire header (ONBOARD11)
- [ ] Document pre-populate workflow — consultant fills recording tables from prep sheet before meeting (ONBOARD12)

### Nav & Permission Fixes

- [x] Extract duplicated audit scoping block into `_scoped_audit_qs` helper + exempt `/admin/audit/` from admin-only middleware — 2026-02-13 (NAV-FIX1)
- [ ] Add test: PM only sees audit entries for their own programs (scoped filtering) (NAV-FIX2)
- [ ] Fix pre-existing `meeting.create` test failure — view uses `@requires_permission("event.create")` but matrix key is `meeting.create` (NAV-FIX3)

### Permissions Phase 2

- [ ] Scoped admin tiers — setup / people / full. See `tasks/agency-permissions-interview.md` (PERM-P12)
- [ ] Discharge access transitions — read-only then restricted. PHIPA compliance (PERM-P6)
- [ ] Privacy access request workflow — PIPEDA s. 8 (PERM-P7)
- [ ] Front Desk `client.edit` → PER_FIELD — admin UI for field-level control (PERM-P8)
- [ ] DV-safe Front Desk interface — search-only mode per program (PERM-P1)
- [ ] `group.view_schedule` — separate from `group.view_roster` (PERM-P9)
- [ ] Consent model expansion — scope, grantor, date, withdrawal (PERM-P2)
- [ ] PM `client.view_clinical` → GATED — requires justification UI (PERM-P10)
- [ ] Rename SCOPED → PROGRAM + split `note.edit_own`/`note.edit_any` (PERM-P11)
- [ ] Data extract governance — logging + board-designate visibility (PERM-P3)
- [ ] Role transition audit trail — deactivate old, create new (PERM-P4)
- [ ] Reposition Program Report as supervision tool (PERM-P5)

### Export Monitoring

- [ ] Create weekly export summary email command (EXP2u)
- [ ] Document cron/scheduled task setup in runbook (EXP2w)



## Parking Lot

### Repository Housekeeping

- [ ] Rename original KoNote GitHub repo to "KoNote Classic" and add a redirect/link to this repo — (REPO1)
- [ ] Delete temp folders (Tempkonote-pushrepo/ and Tempkonote-push 2/) once OneDrive sync is complete (CLEANUP1)

### QA

- [ ] Stress testing — 50+ concurrent users (QA-T15)
- [ ] Data migration scenario — legacy system import (QA-T16)
- [ ] Add onboarding guidance for new users — help link or first-run banner (QA-W19)
- [ ] Reduce form tab stops — tabindex audit (QA-W20)
### QA Backlog

- [ ] Implement multi-session testing for SCN-046 shared device test (TEST-19 → QA-W55)
- [ ] Dashboard cognitive load evaluation for ADHD users — research task (IMPROVE-12 → QA-W57)

### Messaging UX — Deferred

- [ ] Front desk message-taking — separate route, `communication.take_message` permission, notification to assigned worker. Requires `primary_worker` field on ClientFile. See `tasks/messaging-ux-polish.md` (UXP-RECEP)
- [ ] Team meeting view for PMs — `?team=true` on meeting list, grouped by staff. Requires `get_accessible_client_ids` utility for DV safety (UXP-TEAM)
- [ ] Actionable health banners — admin-specific guidance and links on SMS/email health warnings (UXP-HEALTH)
- [ ] Last-contact date on participant list — sortable column for PM oversight (UXP-CONTACT)

### Safety & Reporting

- [ ] Serious Reportable Events — add a predefined list of reportable events relevant to Canadian nonprofits (e.g., critical incidents, use of force, medical emergencies, abuse/neglect disclosures, death, elopement). When flagged on a client event, it would be auditable, trigger notification to manager and executive, and appear in a dedicated report. See `tasks/serious-reportable-events.md` (SRE1)

### Privacy & Security

- [ ] Agency data offboarding command — CLI-only secure export for agency departures and PIPEDA requests. See `tasks/agency-data-offboarding.md` (SEC3)
- [ ] First-run setup wizard — guided initial configuration (SETUP1)
- [ ] TOTP multi-factor authentication — see `tasks/mfa-implementation.md` (SEC2)
- [ ] Encrypted search optimisation for 2000+ client lists (PERF1)
- [ ] Bulk operations for discharge, assign (UX17)

### Infrastructure

- [ ] Re-add API-based auto-translation to `translate_strings` — for production use when Claude Code isn't available. Support Anthropic API with `ANTHROPIC_API_KEY` env var (I18N-API1)
- [ ] Local PostgreSQL for tests — `security_audit` and `pytest` need a running PostgreSQL. Document setup or add SQLite fallback for static-only checks (DEV-PG1)
- [ ] Deferred execution for Tier 3 erasure — 24-hour delay, see `tasks/erasure-hardening.md` (ERASE-H8)
- [ ] Deployment workflow enhancements — see `docs/plans/2026-02-05-deployment-workflow-design.md` (DEPLOY1)

## Recently Done

- [x] **Permissions & audit scoping** — extracted `_scoped_audit_qs` helper, exempted `/admin/audit/` from admin-only middleware, improved 403 page, participant detail redesign, QA scenario coverage — PR #73 merged 2026-02-13 (NAV-FIX1)
- [x] **Session review fixes** — DRY email logic in seed.py, heading accessibility fix (h3→h2), simplified save(), test RBAC corrections — 2026-02-13 (REV-FIX1)
- [x] **Demo email support** — `DEMO_EMAIL_BASE` env var for tagged demo emails, Resend.com docs in .env.example — 2026-02-13 (EMAIL1)
- [x] **UXP1-6 — Messaging/calendar UX polish** — nav link, success toast, date formats, button split, timeline filtering, direction toggle, consent indicator, translations — 2026-02-13 (UXP1-6)
- [x] **QA Round 5 — all Tier 1 + Tier 2 tickets** (25 tickets) — 2026-02-13 (QA-W36–W54)
  - BUG-16+18: Search before filters on /clients/ (QA-W36)
  - BLOCKER-1+IMPROVE-10: HTMX loading indicator + aria-live for search (QA-W37)
  - BLOCKER-2: /settings/ redirect to /admin/settings/ (QA-W38)
  - BUG-15+20: Executive audit log access + nav visibility (QA-W39)
  - BUG-17+23: Form error summary with role="alert" + focus management (QA-W40, W43)
  - BUG-22: Touch target 24x24px minimum (QA-W44)
  - BUG-19: Fixed hx-vals quote conflict in insights template (QA-W45)
  - BUG-14: Verified lang="fr" fix (QA-W46)
  - IMPROVE-9: aria-live success announcements for HTMX forms (QA-W47)
  - IMPROVE-8: Post-login focus verified (QA-W48)
  - IMPROVE-11: Role-aware 403 page (QA-W49)
  - BUG-21: Executive test user programme assignments fixed (QA-W50)
  - TEST-10: SCN-059 login URL fixed (QA-W41)
  - TEST-20: URL template variable resolution in runner (QA-W42)
  - TEST-15: Language reset between scenarios (QA-W51)
  - TEST-17+18: SCN-058 selectors fixed (QA-W52)
  - TEST-14: SCN-062 prerequisite clients verified (QA-W53)
  - TEST-16: SCN-050 tab counts verified correct (QA-W54)
  - BUG-8+11: French translations extracted, 26 new strings (QA-W56)
- [x] Fix dark mode contrast on filter-bar summary — 2026-02-13 (UX-CONTRAST1)
- [x] Fix HTMX focus management for consent + custom fields edit forms — 2026-02-13 (UX-FOCUS1)
- [x] Remove duplicate user management URLs — 2026-02-13 (URL-DEDUP1)
- [x] Replace hardcoded path in `preflight.py` — 2026-02-13 (DEV-PREFLIGHT1)
- [x] Auto-generate `.run-manifest.json` in `pytest_sessionfinish` — 2026-02-13 (QA-W34)
_Older completed tasks: [tasks/ARCHIVE.md](tasks/ARCHIVE.md). Reference: [tasks/whats-been-built.md](tasks/whats-been-built.md). Recurring chores: [tasks/recurring-tasks.md](tasks/recurring-tasks.md)._
