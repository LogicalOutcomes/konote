# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire — must be finalised before first agency deployment. See `tasks/agency-permissions-interview.md` (ONBOARD-APPROVE)
- [ ] Decide who runs the export command — KoNote team only, or self-hosted agencies too? Shapes the entire SEC3 design. See `tasks/agency-data-offboarding.md` (SEC3-Q1)

## Active Work

### Pre-Launch Checklist

- [ ] Complete Agency Permissions Interview — signed Configuration Summary required before each new agency deployment (ONBOARD-GATE)
- [ ] Verify email is configured — needed for exports, erasure alerts, password resets (OPS3)
- [ ] Test backup restore from a real database dump (OPS4)

### Do Occasionally

- [ ] Run UX walkthrough — `pytest tests/ux_walkthrough/ -v`, review report at `tasks/ux-review-latest.md` (UX-WALK1)
- [ ] French translation review — have a French speaker spot-check AI translations, especially new strings. Run `python manage.py check_translations` to see coverage stats (I18N-REV1)
- [ ] Redeploy to Railway — push to `main`, Railway auto-deploys. See `docs/deploy-railway.md` (OPS-RAIL1)
- [ ] Redeploy to FullHost — push to `main`, then trigger redeploy via API or dashboard. See `docs/deploy-fullhost.md` (OPS-FH1)
- [ ] Code review round — open Claude Code in VS Code, say "review the codebase for code quality, security, and consistency issues" — see `tasks/code-review-process.md` (REV1)
- [ ] **Full QA Suite** — Run after major releases or UI changes. Creates 4 reports. **Step 1:** `/run-scenario-server` here (captures scenario screenshots). **Step 2:** Switch to qa-scenarios, run `/run-scenarios` (evaluates scenarios, creates satisfaction report + improvement tickets). **Step 3:** Back here, run `/capture-page-states` (captures page screenshots). **Step 4:** Switch to qa-scenarios, run `/run-page-audit` (evaluates pages, creates page audit report + tickets). **Step 5 (optional):** Back here, run `/process-qa-report` (expert panel + action plan). All reports saved to `qa-scenarios/reports/` with date stamps. (QA-FULL1)

## Coming Up

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

### Safety & Reporting

- [ ] Serious Reportable Events — add a predefined list of reportable events relevant to Canadian nonprofits (e.g., critical incidents, use of force, medical emergencies, abuse/neglect disclosures, death, elopement). When flagged on a client event, it would be auditable, trigger notification to manager and executive, and appear in a dedicated report. See `tasks/serious-reportable-events.md` (SRE1)

### Privacy & Security

- [ ] Agency data offboarding command — CLI-only secure export for agency departures and PIPEDA requests. See `tasks/agency-data-offboarding.md` (SEC3)
- [ ] First-run setup wizard — guided initial configuration (SETUP1)
- [ ] TOTP multi-factor authentication — see `tasks/mfa-implementation.md` (SEC2)
- [ ] Encrypted search optimisation for 2000+ client lists (PERF1)
- [ ] Bulk operations for discharge, assign (UX17)

### Infrastructure

- [ ] Deferred execution for Tier 3 erasure — 24-hour delay, see `tasks/erasure-hardening.md` (ERASE-H8)
- [ ] Deployment workflow enhancements — see `docs/plans/2026-02-05-deployment-workflow-design.md` (DEPLOY1)

## Recently Done

- [x] Fix CAL-001 preflight — executive persona now checks `/clients/executive/` with `.stat-card` selector — 2026-02-11 (SMOKE-1)
- [x] Bulk-add persona field to 15 scenario YAMLs in qa-scenarios — 2026-02-11 (SMOKE-2)
- [x] Fix BUG-9 — skip .mo validation when user has saved language preference; add LANGUAGE_COOKIE_SECURE=False to test settings — 2026-02-11 (SMOKE-3)
- [x] Fix BUG-7 — wrap client + enrollment creation in transaction.atomic() — 2026-02-11 (SMOKE-4)
- [x] Fix TEST-2 — CAL-005 now submits Insights filter form before checking data table — 2026-02-11 (SMOKE-5)
- [x] Fix TEST-4 — switch_user preserves locale/Accept-Language headers + console listeners for multi-persona scenarios — 2026-02-11 (SMOKE-6)
- [x] Permissions enforcement wiring complete (Waves 1–6) — decorator, template tag, all views migrated, parametrized test, QA personas updated — 2026-02-10 (WIRE-1A through WIRE-6C)
- [x] Fix TEST-5 — QA runner now resolves `{client_id}` etc. from previous step URLs instead of navigating to literal placeholders — 2026-02-10 (QA-W21, QA-W25)
- [x] Fix BUG-11 — program `name_fr` field + `translated_name` property, seed data with French names, 33 templates updated — 2026-02-10 (QA-W24)
- [x] Fix BUG-13 — accent-insensitive search using NFKD normalization ("Benoit" finds "Benoît") — 2026-02-10 (QA-W26)
_Older completed tasks: [tasks/ARCHIVE.md](tasks/ARCHIVE.md). Reference: [tasks/whats-been-built.md](tasks/whats-been-built.md). Recurring chores: [tasks/recurring-tasks.md](tasks/recurring-tasks.md)._
