# Project Tasks

## Flagged

- [ ] Update konote-website git remote URL — repo renamed but local remote still points to old name (NAME2)

- [ ] Approve Agency Permissions Interview questionnaire — must be finalised before first agency deployment. See `tasks/agency-permissions-interview.md` (ONBOARD-APPROVE)
- [ ] Decide who runs the export command — KoNote team only, or self-hosted agencies too? Shapes the entire SEC3 design. See `tasks/agency-data-offboarding.md` (SEC3-Q1)

## Active Work

### QA Round 3 — Regressions

- [ ] Fix BUG-7 again — 404 after create participant still occurs (QA-W21)
- [ ] Fix BUG-9 again — French create form reverts to English (QA-W22)
- [ ] Fix BUG-8 again — "Safety concern noted" still in English on French dashboard (QA-W23)
- [ ] Fix BUG-11 again — "Housing Support" still English on French pages, `name_fr` may not be populated (QA-W24)
- [ ] Fix IMPROVE-5 — no confirmation message after creating a participant (QA-W25)
- [ ] Verify BUG-13 — accent search needs manual test both ways (QA-W26)
- [ ] Verify BLOCKER-1 + BLOCKER-2 — skip link and post-login focus need keyboard/JAWS testing (QA-W27)
- [ ] Fix BUG-3 — audit log filter dropdown still truncated (QA-W28)
- [ ] Fix IMPROVE-1 — Instance Settings and Demo Accounts cards still missing status text (QA-W29)

### Aggregate Export + Funder Rename

- [ ] Run `translate_strings` for new aggregate export strings (I18N-AGG1)
- [ ] Add tests for aggregate export path — verify executives get aggregate-only exports (TEST-AGG1)

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

- [ ] Rename original CoNote GitHub repo to "CoNote Classic" and add a redirect/link to this repo — (REPO1)
- [ ] Delete temp folders (Tempkonote-pushrepo/ and Tempkonote-push 2/) once OneDrive sync is complete (CLEANUP1)

### QA

- [ ] Stress testing — 50+ concurrent users (QA-T15)
- [ ] Data migration scenario — legacy system import (QA-T16)
- [ ] Add onboarding guidance for new users — help link or first-run banner (QA-W19)
- [ ] Reduce form tab stops — tabindex audit (QA-W20)

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

- [x] Decide product name — "KoNote" (not "KoNote2"). Renamed across all tasks/, qa/, CLAUDE.md, TODO.md — 2026-02-10 (NAME1)
- [x] Rename "programme" → "program" across 102 files + migration + .po cleanup — 2026-02-09 (SPELL1, RENAME-AGG1, DOC-AGG1, PERM-FU3)
- [x] Fix Progress Trend chart — apostrophe in JS string caused SyntaxError, used `escapejs` — 2026-02-09 (BUG-CHART1)
- [x] Permissions redesign Phase 1 — cross-program note leaks, field-level visibility, ClientAccessBlock, expanded matrix — 2026-02-08 (PERM-S1 through PERM-SYS1)
- [x] Front Desk permissions hardening — hide Groups nav, block clinical data on dashboard — 2026-02-08 (UI-PERM1)
- [x] Fix BLOCKER-1 skip link — auto-focus main content per expert panel consensus — 2026-02-08 (QA-FIX1)
- [x] Playwright tests for BLOCKER-1/2 — focus verification automated — 2026-02-08 (QA-VERIFY1)
- [x] QA Round 2c — 6 bug fixes: accent search, French names, untranslated strings, button permissions, audit CSS — 2026-02-08 (QA-W9 through QA-W18)
- [x] Fix BUG-7, BUG-9, BUG-10 — 404 after create, language cookie, autofocus — 2026-02-08 (BUG-7, BUG-9, BUG-10)
- [x] Participant suggestion field + AI feedback insights — encrypted suggestions, priority levels, categorised feedback — 2026-02-08 (VOICE1)
- [x] QA process improvements — pre-flight, console capture, duplicate detection, action verification, DITL coverage, report naming, 404 fix, aria-live — 2026-02-08 (QA-W1 through QA-W8)
_Older completed tasks: [tasks/ARCHIVE.md](tasks/ARCHIVE.md). Reference: [tasks/whats-been-built.md](tasks/whats-been-built.md). Recurring chores: [tasks/recurring-tasks.md](tasks/recurring-tasks.md)._
