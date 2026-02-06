# Project Tasks

## Flagged

- [ ] Decide product name — should web version  be called "KoNote" (not "KoNote2"). See `tasks/naming-versioning.md` (NAME1)

## Active Work

### Pre-Launch Checklist

The core app is feature-complete. These tasks prepare for production use.

- [ ] Verify email is configured — needed for export notifications, erasure alerts, and password resets (OPS3)
- [ ] Run full integration test pass — every role, every workflow (TEST3)
- [ ] Test backup restore from a real database dump (OPS4)
- [ ] Verify Railway deployment end-to-end with production-like config (OPS5)

### Occasional Tasks

- [ ] Run UX walkthrough — `pytest tests/ux_walkthrough/ -v`, review report at `tasks/ux-review-latest.md` (UX-WALK1)


## Coming Up

### Review Follow-ups (from 2026-02-05 session review)

_All items completed — see Recently Done._

### Export Monitoring

Weekly accountability reports for admins. Requires working email configuration.

- [ ] Create weekly export summary email command (EXP2u)
- [ ] Document cron/scheduled task setup in runbook (EXP2w)

### Independent Code Review

- [ ] Get independent code review from a third-party tool — e.g. Jules (jules.google.com) or GPT Codex — especially for security (SEC-REV1)

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
- ~~Offline PWA~~ → Paper forms acceptable; integrations available when needed
- ~~Multi-tenancy~~ → Fork required for coalition implementations

## Parking Lot

### Erasure — Deferred Execution for Tier 3

- [ ] Add 24-hour delay before Tier 3 (full erasure) CASCADE delete executes — requires background task scheduler, see `tasks/erasure-hardening.md` section ERASE-H8 (ERASE-H8)

### Deployment Workflow Enhancements

- [ ] Create Demo Account Directory page in admin settings — list all demo users and demo clients in one place so admins can manage them (DEMO9)
- [ ] Add `is_demo_context` flag to audit log entries — lets admins filter out demo activity from real audit trails (DEMO12)

See [deployment workflow design](docs/plans/2026-02-05-deployment-workflow-design.md) for full details.

### Privacy & Security

- [ ] First-run setup wizard — guided initial configuration (SETUP1)
- [ ] Encrypted search optimisation (search hash field) for 2000+ client lists (PERF1)
- [ ] Bulk operations for discharge, assign (UX17)

## Recently Done

- [x] Parking lot quick wins — aria-describedby on full note form, beautifulsoup4 to test-only, specific erasure email errors, rename receptionist_access → front_desk_access — 2026-02-06 (UX-A11Y1, REV2-DEPS1, REV2-EMAIL2, DB-TERM1)
- [x] Fix 5 review follow-ups — erasure email templates, tier validation test, history ordering, French filter tests, phone validation tests — 2026-02-06 (REV2-EMAIL1, REV2-TEST1, REV2-ORDER1, TESTFIX1, TESTFIX2)
- [x] Review follow-ups — email failure warnings, SQL-optimised PM filtering, 30-day PIPEDA aging indicator — 2026-02-06 (REV-W3, REV-W1, REV-PIPEDA1)
- [x] Independent security review docs — added review section, AI prompt template, and "Trust, But Verify" to security ops + README — 2026-02-06 (SEC-DOC1-3, SEC-WEB1)
- [x] Fix UX walkthrough issues — 500 error, heading structure, table accessibility, search page, 403 page, form validation — 2026-02-06 (UX-WALK1)
- [x] Erasure hardening — receipt access scoping, audit-before-erasure, download tracking, rejection emails, race condition fix, pagination, 78 tests — 2026-02-06 (ERASE-H1-H7)
- [x] Redesign erasure system — tiered anonymisation, erasure codes, PDF receipts, role restrictions, 72 tests — 2026-02-06 (ERASE-REDESIGN)
- [x] Fix footer links — correct GitHub URL, wire up privacy and help routes, fix help guide nav — 2026-02-06 (FOOT1)
- [x] Documentation refresh — security docs, feature lists, Getting Started guide, website — 2026-02-06 (DOC-REF1-3, WEB-REF1)
- [x] Erasure i18n — email templates, completion email, error messages, JS escaping for French — 2026-02-05 (ERASE-I18N1-3, ERASE-JS1)
- [x] Erasure review fixes — __str__, dead code, aria-labels, email template, 80+ French translations — 2026-02-05 (ERASE-REV2-6)
- [x] Erasure review fixes — email privacy, auth decorators, HTML — 2026-02-05 (ERASE-REV1)
- [x] Erase Client Data — multi-PM approval workflow, 49 tests, audit trail — 2026-02-05 (ERASE1-9)
- [x] French journey test suite — 69 tests covering all 16 areas of the French UX — 2026-02-05 (I18N4b)
- [x] i18n tooling — `find_untranslated.py` script + `update_translations.py` wrapper — 2026-02-05 (I18N-R5, I18N-R6)

_Older completed tasks moved to [tasks/ARCHIVE.md](tasks/ARCHIVE.md)._

---

## What's Been Built (Reference)

For detailed history, see `tasks/ARCHIVE.md`. Summary of completed work:

| Area | What's Done |
|------|-------------|
| **Core app (Phases 1-8)** | Clients, plans, notes, events, charts, admin, security, UX |
| **Secure export** | Bug fix, audit logging, warnings, secure links, permission alignment |
| **French** | 636 system strings translated, bilingual login, language switcher |
| **Reporting** | Funder reports, aggregation, demographics, fiscal year, PDF exports |
| **Documentation** | Getting started, security ops, deployment guides (Azure, Railway, Elest.io) |
| **Registration** | Self-service public forms with duplicate detection and capacity limits |
| **Privacy** | Tiered client data erasure (anonymise/purge/delete), multi-PM approval, erasure codes, PDF receipts, PIPEDA compliance |
| **Accessibility** | WCAG 2.2 AA — semantic HTML, colour contrast, aria attributes |
| **Canadian localisation** | Postal codes, provinces, phone formats, date/currency by locale |
| **Roadmap A-F** | Market access, funder reporting, docs, registration, staff productivity — all complete |
