# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire — must be finalised before first agency deployment. See `tasks/agency-permissions-interview.md` (ONBOARD-APPROVE)
- [ ] Decide who runs the export command — KoNote team only, or self-hosted agencies too? Shapes the entire SEC3 design. See `tasks/agency-data-offboarding.md` (SEC3-Q1)

## Active Work

### Pre-Launch Checklist

- [ ] Complete Agency Permissions Interview — signed Configuration Summary required before each new agency deployment (ONBOARD-GATE)
- [ ] Verify email is configured — needed for exports, erasure alerts, password resets (OPS3)
- [ ] Test backup restore from a real database dump (OPS4)

### UX Walkthrough

- [x] Re-run full UX walkthrough — 57/57 tests passing, 321 pages audited. Report at `tasks/ux-review-latest.md` (UX-RESTORE1) ✓
- [ ] Re-run UX walkthrough to confirm last contrast fix landed — `.filter-bar > summary` dark mode (UX-CONTRAST1)
- [ ] Fix focus management for HTMX edit forms — consent + custom fields still flagged after `hx-on::after-settle` fix (UX-FOCUS1)

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

- [ ] Local PostgreSQL for tests — `security_audit` and `pytest` need a running PostgreSQL. Document setup or add SQLite fallback for static-only checks (DEV-PG1)
- [ ] Deferred execution for Tier 3 erasure — 24-hour delay, see `tasks/erasure-hardening.md` (ERASE-H8)
- [ ] Deployment workflow enhancements — see `docs/plans/2026-02-05-deployment-workflow-design.md` (DEPLOY1)

## Recently Done

- [x] Remove duplicate user management URLs — consolidated under `admin_urls.py`, updated all templates/tests/nav — 2026-02-13 (URL-DEDUP1)
- [x] Replace hardcoded path in `preflight.py` with `settings.BASE_DIR`-relative path — 2026-02-13 (DEV-PREFLIGHT1)
- [x] Refactor `/capture-page-states` skill — already rewritten in prior session, verified complete — 2026-02-13 (SKILL-CAPTURE1)
- [x] Fix BUG-8 — French translation gaps (QA-W28) + Verify BUG-11 — program name_fr confirmed (QA-W29) — 2026-02-12
- [x] Auto-generate `.run-manifest.json` in `pytest_sessionfinish` — 2026-02-13 (QA-W34)
- [x] Add screenshot self-validation — file size, SHA-256 dedup, URL slug check — 2026-02-13 (QA-W35)
- [x] All critical/warning UX walkthrough issues fixed — 2026-02-13 (UX-RESTORE2)
- [x] Fix BUG-14 — `staff_a11y` preferred_language="en" in scenario runner — 2026-02-13 (QA-W27)
- [x] Fix TEST-5/6/7/8/9 — scenario runner click fallback, YAML fixes — 2026-02-13 (QA-W30–W33)
- [x] Re-sync permissions hash — note.create/note.edit DENY→SCOPED for PM — 2026-02-13
- [x] Full UX walkthrough restored — 57/57 tests passing, 321 pages — PR #64 (UX-RESTORE1)
_Older completed tasks: [tasks/ARCHIVE.md](tasks/ARCHIVE.md). Reference: [tasks/whats-been-built.md](tasks/whats-been-built.md). Recurring chores: [tasks/recurring-tasks.md](tasks/recurring-tasks.md)._
