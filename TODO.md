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

### Export Monitoring

Weekly accountability reports for admins. Requires working email configuration.

- [ ] Create weekly export summary email command (EXP2u)
- [ ] Document cron/scheduled task setup in runbook (EXP2w)

### Security Review Fixes (from SEC-REV1)

- [ ] Encrypt PlanTarget.name, .description, .status_reason fields + PlanTargetRevision equivalents (SEC-FIX1)
- [ ] Add MultiFernet key rotation support to konote/encryption.py (SEC-FIX2)
- [x] Change decryption error return from "[decryption error]" to empty string (SEC-FIX3)

### Privacy Review Fixes (from SEC-REV2)

- [ ] Create daily management command to alert admins about expired retention dates (PRIV-FIX1)
- [ ] Add Privacy Officer name/email to InstanceSettings and expose in templates (PRIV-FIX2)

### Accessibility Review Fixes (from SEC-REV3)

- [ ] Add data table alternatives for Chart.js charts (A11Y-FIX1)
- [ ] Add aria-live to session timer + "Extend Session" button (A11Y-FIX2)
- [ ] Add aria-describedby to full note form error messages (A11Y-FIX3)
- [x] Increase auto-dismiss delay from 3s to 8-10s (A11Y-FIX4)
- [x] Create 404.html and 500.html error pages extending base.html (A11Y-FIX5)

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

See [deployment workflow design](docs/plans/2026-02-05-deployment-workflow-design.md) for full details.

### Privacy & Security

- [ ] First-run setup wizard — guided initial configuration (SETUP1)
- [ ] Encrypted search optimisation (search hash field) for 2000+ client lists (PERF1)
- [ ] Bulk operations for discharge, assign (UX17)

## Recently Done

- [x] Fix 3 review bugs — AuditLog crash on metric import, group re-add constraint, ghost revisions — 2026-02-06 (QR-FIX4-6)
- [x] Fix 4 group view bugs — attendance name mismatch, membership form, role handling, demo separation — 2026-02-06 (QR-FIX1-3)
- [x] Client voice, qualitative progress, groups app (Phases A-D) — encrypted client_goal on targets, progress descriptors, engagement observation, 7-model groups app, 3 demo groups — 2026-02-06 (CV1-4)
- [x] Expand demo from 2 programs / 10 clients to 5 programs / 15 clients — 2026-02-06 (DEMO-EXP1)
- [x] Independent code reviews (security, privacy, accessibility, deployment) — 2026-02-06 (SEC-REV1-4)
- [x] Review quick fixes — .dockerignore, audit lockdown, split requirements, decryption error, auto-dismiss delay, error pages — 2026-02-06 (DEPLOY-FIX1-3, SEC-FIX3, A11Y-FIX4-5)
- [x] Demo Account Directory page + is_demo_context audit flag — 2026-02-06 (DEMO9, DEMO12)
- [x] Parking lot quick wins — aria-describedby, test deps, email errors, field rename — 2026-02-06 (UX-A11Y1, REV2-DEPS1, REV2-EMAIL2, DB-TERM1)
- [x] Fix 5 review follow-ups — erasure emails, tier validation, history ordering, French filters, phone tests — 2026-02-06 (REV2-EMAIL1, REV2-TEST1, REV2-ORDER1, TESTFIX1, TESTFIX2)
- [x] Review follow-ups — email warnings, SQL-optimised PM filtering, PIPEDA aging — 2026-02-06 (REV-W3, REV-W1, REV-PIPEDA1)

_Older completed tasks moved to [tasks/ARCHIVE.md](tasks/ARCHIVE.md)._

---

## What's Been Built (Reference)

For detailed history, see `tasks/ARCHIVE.md`. Summary of completed work:

| Area | What's Done |
|------|-------------|
| **Core app (Phases 1-8)** | Clients, plans, notes, events, charts, admin, security, UX |
| **Client voice & qualitative** | Client-goal fields, progress descriptors, engagement observation, qualitative summary |
| **Groups** | Service groups, activity groups, projects — session logs, attendance, highlights, milestones, outcomes |
| **Demo data** | 5 programs, 15 clients, 3 groups, cross-enrolments, approachable metrics |
| **Secure export** | Bug fix, audit logging, warnings, secure links, permission alignment |
| **French** | 636 system strings translated, bilingual login, language switcher |
| **Reporting** | Funder reports, aggregation, demographics, fiscal year, PDF exports |
| **Documentation** | Getting started, security ops, deployment guides (Azure, Railway, Elest.io) |
| **Registration** | Self-service public forms with duplicate detection and capacity limits |
| **Privacy** | Tiered client data erasure (anonymise/purge/delete), multi-PM approval, erasure codes, PDF receipts, PIPEDA compliance |
| **Accessibility** | WCAG 2.2 AA — semantic HTML, colour contrast, aria attributes |
| **Canadian localisation** | Postal codes, provinces, phone formats, date/currency by locale |
| **Roadmap A-F** | Market access, funder reporting, docs, registration, staff productivity — all complete |
