# Project Tasks

## Flagged

- [ ] Decide product name — should web version be called "KoNote" (not "KoNote2"). See `tasks/naming-versioning.md` (NAME1)
- [ ] Update konote-website git remote URL — repo was renamed to `konote2-website` but local remote still points to old `konote2` name (NAME2)

## Active Work

### QA Round 2c — Verification

- [ ] Re-run QA scenarios after deploy to confirm all fixes visible in screenshots (QA-VERIFY2)

### Pre-Launch Checklist

The core app is feature-complete. These tasks prepare for production use.

- [ ] Verify email is configured — needed for export notifications, erasure alerts, and password resets (OPS3)
- [ ] Test backup restore from a real database dump (OPS4)

### Occasional Tasks

- [ ] Run UX walkthrough — `pytest tests/ux_walkthrough/ -v`, review report at `tasks/ux-review-latest.md` (UX-WALK1)
- [ ] French translation review — have a French speaker spot-check AI translations, especially new strings. Run `python manage.py check_translations` to see coverage stats (I18N-REV1)
- [ ] Redeploy to Railway — push to `main`, Railway auto-deploys. See `docs/deploy-railway.md` (OPS-RAIL1)
- [ ] Redeploy to FullHost — push to `main`, then trigger redeploy via API or dashboard. See `docs/deploy-fullhost.md` (OPS-FH1)
- [ ] Code review round — open Claude Code in VS Code, say "review the codebase for code quality, security, and consistency issues" — see `tasks/code-review-process.md` (REV1)
- [ ] **Full QA Suite** — Run after major releases or UI changes. Creates 4 reports. **Step 1:** `/run-scenario-server` here (captures scenario screenshots). **Step 2:** Switch to qa-scenarios, run `/run-scenarios` (evaluates scenarios, creates satisfaction report + improvement tickets). **Step 3:** Back here, run `/capture-page-states` (captures page screenshots). **Step 4:** Switch to qa-scenarios, run `/run-page-audit` (evaluates pages, creates page audit report + tickets). **Step 5 (optional):** Back here, run `/process-qa-report` (expert panel + action plan). All reports saved to `qa-scenarios/reports/` with date stamps. Takes ~6-9 hours total. (QA-FULL1)

## Coming Up

### Export Monitoring

Weekly accountability reports for admins. Requires working email configuration (OPS3).

- [ ] Create weekly export summary email command (EXP2u)
- [ ] Document cron/scheduled task setup in runbook (EXP2w)

## Roadmap — Future Extensions

### Phase G: Agency Content Translation

Build when agencies have custom programs/metrics they need in multiple languages. See `tasks/multilingual-strategy.md`.

**G.1: Translation Infrastructure**
- [ ] Create TranslatableMixin with `translations` JSONField (I18N10)
- [ ] Add mixin to Program, MetricDefinition, PlanTemplate (I18N11)
- [ ] Create Settings → Translations admin page (I18N12)
- [ ] Update templates to display translated content (I18N13)

**G.2: AI Translation Integration**
- [ ] Create Settings → Integrations page for API keys (I18N14)
- [ ] Add "Suggest translation" button with AI (I18N15)

**G.3: Self-Service Languages**
- [ ] Create Settings → Languages management page (I18N16)
- [ ] Extend translation command for any target language (I18N17)

### Bulk Import

Build after secure export is stable. See `tasks/secure-export-import-plan.md` for design.

- [ ] Create ImportBatch model for tracking (IMP1a)
- [ ] Add import_batch FK to ClientFile model (IMP1b)
- [ ] Create CSV upload form with validation (IMP1c)
- [ ] Implement formula injection sanitisation (IMP1d)
- [ ] Implement duplicate detection (IMP1e)
- [ ] Create preview page showing what will be created (IMP1f)
- [ ] Implement batch import with transaction wrapping (IMP1g)
- [ ] Create rollback functionality — creations only, not updates (IMP1h)
- [ ] Add audit logging for imports (IMP1i)
- [ ] Create import history page for admins (IMP1j)
- [ ] Document import validation rules (DOC-IMP1)

### Other Planned Extensions

- [ ] Field data collection integrations — KoBoToolbox, Forms, or other tools (FIELD1)

### Explicitly Out of Scope

- ~~Calendar/scheduling~~ → Recommend Calendly, Google Calendar, Microsoft Bookings
- ~~Full document storage~~ → Recommend Google Drive, SharePoint, Dropbox
- ~~Full offline PWA~~ → Paper forms acceptable; basic offline banner added (BUG-6)
- ~~Multi-tenancy~~ → Fork required for coalition implementations

## QA Backlog

From Round 2c expert panel — lower priority items. See `tasks/qa-action-plan-2026-02-08.md`.

- [ ] Add onboarding guidance for new users — help link or first-run banner, not full wizard (IMPROVE-7 → QA-W19)
- [ ] Reduce form tab stops — tabindex audit, skip non-essential fields. Not yet tested. (IMPROVE-6 → QA-W20)

## Parking Lot

### QA Scenarios — Parking Lot

From konote-qa-scenarios. These require test infrastructure or app features in this repo.

- [ ] Stress testing — simulate 50+ concurrent users to find performance bottlenecks and connection pool limits (QA-T15)
- [ ] Data migration scenario — test what happens when importing client data from a legacy system. Validates the Bulk Import feature (IMP1 series) once built (QA-T16)

### Erasure — Deferred Execution for Tier 3

- [ ] Add 24-hour delay before Tier 3 (full erasure) CASCADE delete executes — requires background task scheduler, see `tasks/erasure-hardening.md` section ERASE-H8 (ERASE-H8)

### Deployment Workflow Enhancements

See [deployment workflow design](docs/plans/2026-02-05-deployment-workflow-design.md) for full details.

### Privacy & Security

- [ ] First-run setup wizard — guided initial configuration (SETUP1)
- [ ] TOTP multi-factor authentication for local auth — see `tasks/mfa-implementation.md` (SEC2)
- [ ] Encrypted search optimisation (search hash field) for 2000+ client lists (PERF1)
- [ ] Bulk operations for discharge, assign (UX17)

## Recently Done

- [x] Fix BLOCKER-1 skip link conflict — implemented Option B (auto-focus main content, remove skip link) per expert panel consensus. Removed duplicate focus block, added aria-label, visible focus indicator. Both Playwright tests pass. Expert rationale: more efficient for screen reader users, satisfies WCAG 2.4.1 via programmatic focus — 2026-02-08 (QA-FIX1)
- [x] Playwright tests for BLOCKER-1/2 — BLOCKER-2 verified working (focus on #main-content, not footer), BLOCKER-1 code exists but conflicts with BLOCKER-2 fix (skip link not first Tab stop due to auto-focus). Automated tests at tests/test_blocker_a11y.py — 2026-02-08 (QA-VERIFY1)
- [x] QA Round 2c — Tier 1+2 fixes (6 bugs) — accent search (BUG-13), program French names with `name_fr` field + 33 template updates (BUG-11), untranslated French strings (BUG-8), home page button permission (BUG-12), audit filter CSS (BUG-3), IMPROVE-5 confirmed already fixed — 2026-02-08 (QA-W9 through QA-W18)
- [x] Fix BUG-7, BUG-9, BUG-10 from QA Round 2b — 404 after create (session flag bypass), language cookie path, autofocus on create form — 2026-02-08 (BUG-7, BUG-9, BUG-10)
- [x] Participant suggestion field + AI feedback insights — encrypted suggestion field on every note, staff-assigned priority (noted/worth exploring/important/urgent), AI insights now categorise participant feedback (request/suggestion/concern/praise) with verbatim quotes, recurring pattern detection, 3-item focus rule — 2026-02-08 (VOICE1)
- [x] QA process improvements — pre-flight check (W1), console capture (W2), duplicate screenshot detection (W3), action verification with retry (W4), DITL key_moments coverage (W5), report naming sequence suffix (W6), 404 fix + personalised flash message (W7), aria-live on messages (W8) — 2026-02-08 (QA-W1 through QA-W8)
- [x] QA Scenario Runner full coverage — 4 test users, 6 test clients, 7 action types (voice/dictate/intercept/tabs/back/screenshot), 5 new test classes + 2 updated (22 new scenarios), LLM evaluator prompt enhancements (cognitive/mechanical/completion checks) — 2026-02-08 (QA-DATA1-5, QA-ACT1-5, QA-TEST1-7, QA-EVAL1-3)
- [x] QA Infrastructure Phase 3 — CI/CD gate (QA-T11), satisfaction gap tracking (QA-T12), bidirectional ticket sync (QA-T14). GitHub Actions workflows, standalone scripts, JSON results serializer — 2026-02-08 (QA-T11, QA-T12, QA-T14)
- [x] Test isolation (QA-ISO1) + objective scoring (QA-T10) — fresh context per scenario, locale from persona, auto-login, prerequisite validation, axe-core/action-count/lang objective scores override LLM — 2026-02-08 (QA-ISO1, QA-T10)
- [x] Fix 14 pre-existing test failures + 4 errors — missing form fields, wrong assertions, missing DB declarations, template bugs, Playwright skip fix — 2026-02-07 (TEST-FIX1)
- [x] Fix language bleed on shared browser — clear cookie on logout, set cookie on login to match user preference — 2026-02-07 (BUG-4)
- [x] French translations complete — translated 93 remaining strings to Canadian French, 100% coverage (2146/2146 entries), .mo compiled, validation passed — 2026-02-07 (I18N-TRANS1)
_Older completed tasks moved to [tasks/ARCHIVE.md](tasks/ARCHIVE.md)._

---

## What's Been Built (Reference)

For detailed history, see `tasks/ARCHIVE.md`. Summary of completed work:

| Area | What's Done |
|------|-------------|
| **Core app (Phases 1-8)** | Clients, plans, notes, events, charts, admin, security, UX |
| **Client voice & qualitative** | Client-goal fields, progress descriptors, engagement observation, participant reflection, participant suggestion with priority, qualitative summary |
| **Groups** | Groups and projects — session logs, attendance, highlights, milestones, outcomes |
| **Confidential programs** | Isolation, guided setup, Django admin filtering, audit logging, small-cell suppression, DV-ready documentation |
| **Duplicate detection & merge** | Phone + name/DOB matching, cross-program dedup, admin merge tool with full data transfer |
| **Demo data** | 5 programs, 15 clients, 3 groups, cross-enrolments, approachable metrics |
| **Secure export** | Bug fix, audit logging, warnings, secure links, permission alignment |
| **French** | 2,146 system strings (100% translated), bilingual login, language switcher, translate_strings command |
| **Reporting** | Funder reports, aggregation, demographics, fiscal year, PDF exports, AI participant feedback (categorised with verbatim quotes) |
| **Documentation** | Getting started, security ops, deployment guides (Azure, Railway, Elest.io, FullHost) |
| **Registration** | Self-service public forms with duplicate detection and capacity limits |
| **Privacy** | Tiered client data erasure (anonymise/purge/delete), multi-PM approval, erasure codes, PDF receipts, PIPEDA compliance |
| **Accessibility** | WCAG 2.2 AA — semantic HTML, colour contrast, aria attributes |
| **Canadian localisation** | Postal codes, provinces, phone formats, date/currency by locale |
| **Deployment** | Railway (auto-deploy), FullHost (HTTPS verified), Docker Compose for Azure/Elest.io |
| **QA** | Scenario runner (22 scenarios, 7 action types), CI/CD gate, satisfaction tracking, inter-rater reliability, objective scoring |
| **Code review** | 74 tests added, CRITICAL/HIGH/MEDIUM fixes, admin_required, demo isolation, focus trap, i18n |
