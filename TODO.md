# Project Tasks

## Flagged

- [ ] Decide product name — should web version be called "KoNote" (not "KoNote2"). See `tasks/naming-versioning.md` (NAME1)

## Active Work

### Pre-Launch Checklist

The core app is feature-complete. These tasks prepare for production use.

- [ ] Verify email is configured — needed for export notifications, erasure alerts, and password resets (OPS3)
- [x] Run full integration test pass — 901 tests, 1 false-positive fix — 2026-02-06 (TEST3)
- [ ] Test backup restore from a real database dump (OPS4)

### Occasional Tasks

- [ ] Run UX walkthrough — `pytest tests/ux_walkthrough/ -v`, review report at `tasks/ux-review-latest.md` (UX-WALK1)
- [ ] Redeploy to Railway — push to `main`, Railway auto-deploys. See `docs/deploy-railway.md` (OPS-RAIL1)
- [ ] Redeploy to FullHost — push to `main`, then trigger redeploy via API or dashboard. See `docs/deploy-fullhost.md` (OPS-FH1)

## Coming Up

### Export Monitoring

Weekly accountability reports for admins. Requires working email configuration.

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

### Phase H: Cross-Program Client Matching & Confidential Programs

Prevent duplicate client records across programs while protecting sensitive program privacy. See `tasks/cross-program-client-matching.md` for full design (4 expert panels).

**H.1: Foundation — Confidential Program Isolation**
- [x] Add `is_confidential` field to Program model + migration — 2026-02-06 (CONF1)
- [x] Create guided setup question in program create/edit admin UI — 2026-02-06 (CONF2)
- [x] Filter confidential data from views — enrolment display, edit form unenrolment bug, PDF export, registration links, group views — 2026-02-06 (CONF3)

**H.2: Duplicate Detection (Standard Programs)**
- [x] Add phone number as first-class encrypted field on ClientFile — 2026-02-06 (MATCH1)
- [x] Build phone-based duplicate detection on client create form — HTMX endpoint, banner UI — 2026-02-06 (MATCH2)
- [x] Add name + DOB secondary matching as fallback when phone unavailable — 2026-02-06 (MATCH3)

**H.3: Merge Tool (Standard Programs)**
- [ ] Build duplicate merge tool for Standard program admins — side-by-side comparison, merged record keeps all data (MATCH4)

**H.4: Confidential Program Hardening (Required Before DV Use)**
- [ ] 🔨 Filter confidential client records from Django admin for superusers without confidential access (CONF4)
- [ ] 🔨 Add immutable audit logging for all confidential record access — who, when, what, which record (CONF5)
- [ ] 🔨 Aggregate reports use small-cell suppression — show "< 10" when confidential program has fewer than 10 clients (CONF6)
- [x] Create `tests/test_confidential_isolation.py` — isolation, matching, registration, groups, phone field — 2026-02-06 (CONF7)

**H.5: DV Readiness & Documentation**
- [x] Ship PIA (Privacy Impact Assessment) template pre-filled from agency configuration — 2026-02-06 (MATCH5)
- [ ] Write user-facing documentation on confidential programs and matching (MATCH6)
- [ ] Add annual security review checklist for confidential program filtering (CONF8)

**H.6: Multi-Role Staff (Nice-to-Have)**
- [ ] Build role selector for staff with roles in both Standard and Confidential programs (CONF9)

### Other Planned Extensions

- [ ] Field data collection integrations — KoBoToolbox, Forms, or other tools (FIELD1)

### Explicitly Out of Scope

- ~~Calendar/scheduling~~ → Recommend Calendly, Google Calendar, Microsoft Bookings
- ~~Full document storage~~ → Recommend Google Drive, SharePoint, Dropbox
- ~~Offline PWA~~ → Paper forms acceptable; integrations available when needed
- ~~Multi-tenancy~~ → Fork required for coalition implementations

## Parking Lot

### Translation Hardening

- [ ] Wrap 106 unwrapped strings across 10 apps in `_()` and add French translations — see `scripts/check_untranslated.py` for full list (I18N-FIX2)

### Erasure — Deferred Execution for Tier 3

- [ ] Add 24-hour delay before Tier 3 (full erasure) CASCADE delete executes — requires background task scheduler, see `tasks/erasure-hardening.md` section ERASE-H8 (ERASE-H8)

### FullHost SSL Issue

- [ ] Resolve FullHost HTTPS — Built-In SSL is enabled but port 443 is intermittent. Contact FullHost support or try Let's Encrypt add-on. HTTP works, but login requires HTTPS (`CSRF_COOKIE_SECURE=True`) (OPS-FH2)

### Deployment Workflow Enhancements

See [deployment workflow design](docs/plans/2026-02-05-deployment-workflow-design.md) for full details.

### Privacy & Security

- [ ] First-run setup wizard — guided initial configuration (SETUP1)
- [ ] TOTP multi-factor authentication for local auth — see `tasks/mfa-implementation.md` (SEC2)
- [ ] Encrypted search optimisation (search hash field) for 2000+ client lists (PERF1)
- [ ] Bulk operations for discharge, assign (UX17)

## Recently Done

- [x] Name + DOB secondary duplicate detection — fallback matching when phone unavailable, single-pass iterator, brittleness fixes (hx-params removal, date parsing, race condition prevention), 12 new tests — 2026-02-06 (MATCH3)
- [x] Cross-program client matching Phase H.1 + H.2 — confidential program isolation, phone field, duplicate detection, security fixes (edit form bug, PDF export, registration links, group views), test suite — 2026-02-06 (CONF1-3, MATCH1-2, CONF7)
- [x] Verify deployment end-to-end with production-like config — FullHost tested, HTTPS working, demo data live — 2026-02-06 (OPS5)
- [x] Lock in .mo translation strategy — commit .mo to git, no compilation in Docker, freshness check in validate_translations.py — 2026-02-06 (I18N-FIX1)
- [x] Fix 4 UX walkthrough crashes + 6 test failures — 2026-02-06 (UX-FIX1)
- [x] Add translation lint script to catch unwrapped user-facing strings — 2026-02-06 (I18N-LINT1)
- [x] Security, privacy, accessibility review fixes — encrypted PlanTarget fields, MultiFernet rotation, aria-live timer, data tables for charts, Privacy Officer settings, retention expiry alerts — 2026-02-06 (SEC-FIX1-2, PRIV-FIX1-2, A11Y-FIX1-3)
- [x] Fix 3 review bugs — AuditLog crash on metric import, group re-add constraint, ghost revisions — 2026-02-06 (QR-FIX4-6)
- [x] Fix 4 group view bugs — attendance name mismatch, membership form, role handling, demo separation — 2026-02-06 (QR-FIX1-3)
- [x] Client voice, qualitative progress, groups app (Phases A-D) — encrypted client_goal on targets, progress descriptors, engagement observation, 7-model groups app, 3 demo groups — 2026-02-06 (CV1-4)
- [x] Expand demo from 2 programs / 10 clients to 5 programs / 15 clients — 2026-02-06 (DEMO-EXP1)
- [x] Independent code reviews (security, privacy, accessibility, deployment) — 2026-02-06 (SEC-REV1-4)
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
