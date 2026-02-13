# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire — must be finalised before first agency deployment. See `tasks/agency-permissions-interview.md` (ONBOARD-APPROVE)
- [ ] Decide who runs the export command — KoNote team only, or self-hosted agencies too? Shapes the entire SEC3 design. See `tasks/agency-data-offboarding.md` (SEC3-Q1)

## Active Work

### QA Round 4 Remaining

- [ ] Fix BUG-8 — French translation gaps, untranslated system strings in French UI (BUG-8 → QA-W28)
- [ ] Verify BUG-11 — confirm program `name_fr` translations fully populated for PM2-FR scenarios (BUG-11 → QA-W29)

### Pre-Launch Checklist

- [ ] Complete Agency Permissions Interview — signed Configuration Summary required before each new agency deployment (ONBOARD-GATE)
- [ ] Verify email is configured — needed for exports, erasure alerts, password resets (OPS3)
- [ ] Test backup restore from a real database dump (OPS4)

### UX Walkthrough

- [x] Re-run full UX walkthrough — 57/57 tests passing, 321 pages audited. Report at `tasks/ux-review-latest.md` (UX-RESTORE1) ✓

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

- [x] Fix suppression total leak in funder report — when any demographic cell is suppressed, total now reads "suppressed" instead of recomputing (leaked `total − visible_sum`). PIPEDA compliance — PR #64 (PRIV-SUPP1)
- [x] Fix browser test: consent form toggle — expand collapsed `<details>` before clicking edit button — PR #64 (UX-BT1)
- [x] Fix browser test: responsive layout — persist login across viewports, handle anonymous→logged-in context — PR #64 (UX-BT2)
- [x] Add funder profile cross-validation in FunderReportForm — ensures selected funder profile is linked to selected program — PR #64 (FUNDER-VAL1)
- [x] Add Funder Profiles link to admin nav dropdown in base.html — PR #64 (NAV-FUNDER1)
- [x] Full UX walkthrough restored — 57/57 tests passing (17 admin, 10 roles, 20 scenarios, 10 browser), 321 pages, 8 critical / 17 warnings / 39 info — PR #64 (UX-RESTORE1)
- [x] Fix BUG-14 — `staff_a11y` preferred_language="en" in scenario runner — 2026-02-13 (QA-W27)
- [x] Fix TEST-5/6/7/8/9 — scenario runner click fallback, mobile hamburger helper, YAML fixes for SCN-035, SCN-047, SCN-048 — 2026-02-13 (QA-W30–W33)
- [x] Re-sync permissions hash — `note.create`/`note.edit` DENY→SCOPED for PM already in persona files, updated hash in `permissions-sync.yaml` — 2026-02-13
- [x] Fix CAL-001 preflight — executive persona now checks `/clients/executive/` with `.stat-card` selector — 2026-02-11 (SMOKE-1)
- [x] Bulk-add persona field to 15 scenario YAMLs in qa-scenarios — 2026-02-11 (SMOKE-2)
- [x] Fix BUG-9 — skip .mo validation when user has saved language preference; add LANGUAGE_COOKIE_SECURE=False to test settings — 2026-02-11 (SMOKE-3) (partially fixed — `/reports/insights/` still shows `lang="fr"`, see BUG-14)
- [x] Fix BUG-7 — wrap client + enrollment creation in transaction.atomic() — 2026-02-11 (SMOKE-4)
- [x] Fix TEST-2 — CAL-005 now submits Insights filter form before checking data table — 2026-02-11 (SMOKE-5)
- [x] Fix TEST-4 — switch_user preserves locale/Accept-Language headers + console listeners for multi-persona scenarios — 2026-02-11 (SMOKE-6)
- [x] Permissions enforcement wiring complete (Waves 1–6) — decorator, template tag, all views migrated, parametrized test, QA personas updated — 2026-02-10 (WIRE-1A through WIRE-6C)
- [x] Fix TEST-5 — QA runner now resolves `{client_id}` etc. from previous step URLs instead of navigating to literal placeholders — 2026-02-10 (QA-W21, QA-W25)
- [x] Fix BUG-11 — program `name_fr` field + `translated_name` property, seed data with French names, 33 templates updated — 2026-02-10 (QA-W24)
- [x] Fix BUG-13 — accent-insensitive search using NFKD normalization ("Benoit" finds "Benoît") — 2026-02-10 (QA-W26)
_Older completed tasks: [tasks/ARCHIVE.md](tasks/ARCHIVE.md). Reference: [tasks/whats-been-built.md](tasks/whats-been-built.md). Recurring chores: [tasks/recurring-tasks.md](tasks/recurring-tasks.md)._
