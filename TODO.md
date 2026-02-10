# Project Tasks

## Flagged

- [ ] Approve Agency Permissions Interview questionnaire — must be finalised before first agency deployment. See `tasks/agency-permissions-interview.md` (ONBOARD-APPROVE)
- [ ] Decide who runs the export command — KoNote team only, or self-hosted agencies too? Shapes the entire SEC3 design. See `tasks/agency-data-offboarding.md` (SEC3-Q1)

## Active Work

### QA Round 3 — Regressions

- [ ] Fix BUG-7 / IMPROVE-5 — QA false positive: app code is fixed (unit tests pass for admin + staff), but QA runner navigates to literal `{client_id}` instead of resolved ID (TEST-5). Fix the QA test runner to resolve URL variables from previous steps (QA-W21, QA-W25)
- [ ] Reframe BUG-8 — "Safety concern noted" is user-entered alert content (test data), not a translatable UI string. QA runner detecting test fixture language, not an app bug. Close or fix QA seed data (QA-W23)
- [ ] Verify BLOCKER-1 + BLOCKER-2 — skip link and post-login focus need keyboard/JAWS testing (QA-W27)

### Aggregate Export + Funder Rename

_All tasks complete — section can be removed on next cleanup._

### Pre-Launch Checklist

- [ ] Complete Agency Permissions Interview — signed Configuration Summary required before each new agency deployment (ONBOARD-GATE)
- [ ] Verify email is configured — needed for exports, erasure alerts, password resets (OPS3)
- [ ] Test backup restore from a real database dump (OPS4)

## Coming Up

### Permissions Enforcement Wiring — See `tasks/permissions-enforcement-wiring.md`

**Wave 1 — Foundation (3 parallel streams)**
- [ ] Update permissions.py — add `client.create`, `client.edit_contact`, change 5 values (WIRE-1A)
- [ ] Create `@requires_permission` decorator in decorators.py (WIRE-1B)
- [ ] Create `{% has_permission %}` template tag (WIRE-1C)

**Wave 2 — Wire affected views (6 parallel streams)**
- [ ] Wire client views — client_create, contact edit (WIRE-2A)
- [ ] Wire group views — manage_members + HTMX audit trail (WIRE-2B)
- [ ] Wire alert/event views — alert.create (WIRE-2C)
- [ ] Wire consent views — consent.manage + immutability enforcement (WIRE-2D)
- [ ] Wire executive-facing views — notes, plans, reports (WIRE-2E)
- [ ] Add PM no-elevation constraint — user.manage: SCOPED (WIRE-2F)

**Wave 3 — UI layer (3 parallel streams)**
- [ ] Update context processor — expose `user_permissions` dict (WIRE-3A)
- [ ] Update middleware — replace `is_executive_only()` redirect with matrix check (WIRE-3B)
- [ ] Add Django system check — warn on hardcoded decorators, validate permission keys (WIRE-3C)

**Wave 4 — Template migration (2 parallel streams)**
- [ ] Update base.html nav — replace role checks with `{% has_permission %}` (WIRE-4A)
- [ ] Update ~10 other templates — same pattern (WIRE-4B)

**Wave 5 — Feature work (2 parallel streams)**
- [ ] Build alert recommend-cancellation workflow — unblocks alert.cancel → DENY (WIRE-5A)
- [ ] Migrate remaining ~35 views — systematic decorator swap (WIRE-5B)

**Wave 6 — Verification + QA (3 parallel streams)**
- [ ] Parametrized permission enforcement test (WIRE-6A)
- [ ] Update QA personas to match permissions.py (WIRE-6B)
- [ ] Rewrite affected QA scenarios (WIRE-6C)

### Permissions Follow-up

- [ ] Extract `_get_program_from_client` to access.py — duplicated in 3 views (PERM-FU5)

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

- [x] Translate strings + fix aggregate export test — 14 portal strings translated, test record_id fix, .mo compiled — 2026-02-10 (I18N-AGG1)
- [x] Verify aggregate export tests — 9/9 pass: executive CSV has no record IDs, no author names, aggregate headers only — 2026-02-10 (TEST-AGG1)
- [x] Fix BUG-11 — program `name_fr` field + `translated_name` property, seed data with French names, 33 templates updated — 2026-02-10 (QA-W24)
- [x] Fix BUG-13 — accent-insensitive search using NFKD normalization ("Benoit" finds "Benoît") — 2026-02-10 (QA-W26)
- [x] Fix BUG-3 — audit log filter dropdown CSS min-width increased from 0 to 12rem — 2026-02-10 (QA-W28)
- [x] Fix IMPROVE-1 — Instance Settings and Demo Accounts cards now show status text — 2026-02-10 (QA-W29)
- [x] Update konote-website git remote URL — repo renamed to konote-website — 2026-02-10 (NAME2)
- [x] Fix BUG-9 regression — French create form: added name_fr to QA programs, set preferred_language on French user, comprehensive form test — 2026-02-10 (QA-W22)
- [x] Decide product name — "KoNote" (not "KoNote2"). Renamed across all tasks/, qa/, CLAUDE.md, TODO.md — 2026-02-10 (NAME1)
- [x] Rename "programme" → "program" across 102 files + migration + .po cleanup — 2026-02-09 (SPELL1, RENAME-AGG1, DOC-AGG1, PERM-FU3)
_Older completed tasks: [tasks/ARCHIVE.md](tasks/ARCHIVE.md). Reference: [tasks/whats-been-built.md](tasks/whats-been-built.md). Recurring chores: [tasks/recurring-tasks.md](tasks/recurring-tasks.md)._
