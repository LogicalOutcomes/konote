# Project Tasks

## Flagged

- [ ] Decide product name — should web version be called "KoNote" (not "KoNote2"). See `tasks/naming-versioning.md` (NAME1)

## Active Work

### Pre-Launch Checklist

The core app is feature-complete. These tasks prepare for production use.

- [ ] Verify email is configured — needed for export notifications, erasure alerts, and password resets (OPS3)
- [ ] Test backup restore from a real database dump (OPS4)

### Occasional Tasks

- [ ] Run UX walkthrough — `pytest tests/ux_walkthrough/ -v`, review report at `tasks/ux-review-latest.md` (UX-WALK1)
- [ ] Redeploy to Railway — push to `main`, Railway auto-deploys. See `docs/deploy-railway.md` (OPS-RAIL1)
- [ ] Redeploy to FullHost — push to `main`, then trigger redeploy via API or dashboard. See `docs/deploy-fullhost.md` (OPS-FH1)

## Coming Up

### Export Monitoring

Weekly accountability reports for admins. Requires working email configuration (OPS3).

- [ ] Create weekly export summary email command (EXP2u)
- [ ] Document cron/scheduled task setup in runbook (EXP2w)

### Erasure Hardening

Expert-panel recommendations from `tasks/erasure-hardening.md`. High-priority items first.

- [ ] Scope PDF receipt access — only requester + approvers can download (ERASE-H1)
- [ ] Write audit log before erasure executes — guarantees record even if delete crashes (ERASE-H2)
- [ ] Track receipt downloads in audit log (ERASE-H3)
- [ ] Notify requester when erasure request is rejected (ERASE-H4)
- [ ] Deduplicate build_data_summary call in erasure flow (ERASE-H5)
- [ ] Fix erasure code race condition (ERASE-H6)
- [ ] Add pagination to erasure history view (ERASE-H7)

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

- [ ] Multi-role staff program selector — UI for staff with roles in both Standard and Confidential programs (CONF9)
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
- [ ] TOTP multi-factor authentication for local auth — see `tasks/mfa-implementation.md` (SEC2)
- [ ] Encrypted search optimisation (search hash field) for 2000+ client lists (PERF1)
- [ ] Bulk operations for discharge, assign (UX17)

## Recently Done

- [x] Duplicate merge tool — admin-only side-by-side comparison, transfers notes/events/plans/enrolments/fields, 32 tests — 2026-02-06 (MATCH4)
- [x] Phase H complete — confidential programs, duplicate detection, merge tool, DV documentation — 2026-02-06 (CONF1-8, MATCH1-6)
- [x] Translation reliability — `translate_strings` command, startup detection, CLAUDE.md workflow rule — 2026-02-06 (I18N-CMD1)
- [x] Full integration test pass — 1,000+ tests passing — 2026-02-06 (TEST3)
- [x] FullHost deployment verified — HTTPS working via Let's Encrypt, demo data live — 2026-02-06 (OPS5, OPS-FH2)
- [x] French translation hardening — 108 unwrapped strings, Help/Privacy pages, demo banner — 2026-02-06 (I18N-FIX2-3)
- [x] Security, privacy, accessibility review fixes — encrypted PlanTarget fields, MultiFernet rotation, aria-live, data tables — 2026-02-06 (SEC-FIX1-2, PRIV-FIX1-2, A11Y-FIX1-3)
- [x] Client voice, qualitative progress, groups app (Phases A-D) — 2026-02-06 (CV1-4)
_Older completed tasks moved to [tasks/ARCHIVE.md](tasks/ARCHIVE.md)._

---

## What's Been Built (Reference)

For detailed history, see `tasks/ARCHIVE.md`. Summary of completed work:

| Area | What's Done |
|------|-------------|
| **Core app (Phases 1-8)** | Clients, plans, notes, events, charts, admin, security, UX |
| **Client voice & qualitative** | Client-goal fields, progress descriptors, engagement observation, qualitative summary |
| **Groups** | Service groups, activity groups, projects — session logs, attendance, highlights, milestones, outcomes |
| **Confidential programs** | Isolation, guided setup, Django admin filtering, audit logging, small-cell suppression, DV-ready documentation |
| **Duplicate detection & merge** | Phone + name/DOB matching, cross-program dedup, admin merge tool with full data transfer |
| **Demo data** | 5 programs, 15 clients, 3 groups, cross-enrolments, approachable metrics |
| **Secure export** | Bug fix, audit logging, warnings, secure links, permission alignment |
| **French** | 1,110+ system strings translated, bilingual login, language switcher, translate_strings command |
| **Reporting** | Funder reports, aggregation, demographics, fiscal year, PDF exports |
| **Documentation** | Getting started, security ops, deployment guides (Azure, Railway, Elest.io, FullHost) |
| **Registration** | Self-service public forms with duplicate detection and capacity limits |
| **Privacy** | Tiered client data erasure (anonymise/purge/delete), multi-PM approval, erasure codes, PDF receipts, PIPEDA compliance |
| **Accessibility** | WCAG 2.2 AA — semantic HTML, colour contrast, aria attributes |
| **Canadian localisation** | Postal codes, provinces, phone formats, date/currency by locale |
| **Deployment** | Railway (auto-deploy), FullHost (HTTPS verified), Docker Compose for Azure/Elest.io |
