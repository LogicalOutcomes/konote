# Project Tasks

## Flagged

_Nothing flagged._

## Active Work

### Code Review Fixes

_All code review items complete._

### Phase 8 — UX Improvements for Frontline Staff

- [ ] Show custom fields in read-only mode by default with edit toggle — (UX12)
- [ ] Add date-only toggle to event form — (UX13)
- [ ] Style permission error pages with navigation and helpful text — (UX14)
- [ ] Add status and program filters to client list page — (UX15)
- [ ] Auto-dismiss success messages after 3 seconds; keep errors persistent — (UX16)

## Roadmap — Prioritized Extensions

Based on usability review and expert panel analysis. See `tasks/usability-review-results.md` for full rationale.

### Phase A: Market Access (High Priority)

- [ ] French UI translation — Django i18n setup + ~500 strings — (I18N1)
- [ ] Document folder button — link to client folder in SharePoint/Google Drive — (DOC5) — see `tasks/document-access-plan.md`
- [ ] "What KoNote Is and Isn't" documentation page — set scope expectations — (DOC6)
- [ ] Terminology override by language — extend model for fr/en terms — (I18N2)

### Phase B: Funder Reporting (High Priority)

- [ ] Report aggregation functions — count, avg, min, max by grouping — (RPT3)
- [ ] Demographic grouping in reports — age range, gender, geography — (RPT4)
- [ ] Outcome achievement rate calculation — % clients meeting target — (RPT5)
- [ ] United Way CMT export template — pre-built format — (RPT6)
- [ ] Fiscal year date range filter — April-March for Canadian nonprofits — (RPT7)

### Phase C: Field Data Collection (Medium Priority)

- [ ] KoBoToolbox import API endpoint — POST /api/field-import/ — (FIELD1)
- [ ] SharePoint Lists webhook receiver — Power Automate integration — (FIELD2)
- [ ] Field data import documentation — setup guides for KoBoToolbox/SharePoint — (DOC7)

### Explicitly Out of Scope

These features are intentionally excluded. See technical documentation for rationale.

- ~~Calendar/scheduling~~ → Recommend Calendly, Google Calendar, Microsoft Bookings
- ~~Full document storage~~ → Recommend Google Drive, SharePoint, Dropbox
- ~~Offline PWA~~ → Use KoBoToolbox or paper forms for field work
- ~~Multi-tenancy~~ → Fork required for coalition implementations

## Parking Lot

- [ ] PIPEDA/PHIPA consent workflow — block note entry until client consent recorded — (PRIV1)
- [ ] GDPR toolkit UI — data export, right to erasure, consent management — (GDPR1)
- [ ] Data import from existing systems (CSV) — (IMP1)
- [ ] Mobile-responsive optimisation pass — (UI1)
- [ ] First-run setup wizard for new instances — (SETUP1)
- [ ] Automated backups documentation — (OPS1)
- [ ] Encrypted search optimisation (search hash field) for large client lists — (PERF1)
- [ ] Bulk operations for discharge, assign, export — (UX17)
- [ ] Keyboard shortcuts and command palette — (UX18)
- [ ] Client search by program, status, date, case manager — (UX19)
- [ ] Merge home search and client list into single unified page — (UX20)
- [ ] Note auto-save / draft recovery — (UX21)

## Recently Done

- [x] Harden startup: raise ImproperlyConfigured if secrets missing; remove hardcoded fallbacks — 2026-02-02 (CR1)
- [x] Fix CSS bug: `align-items: centre` → `center` — 2026-02-02 (CR8)
- [x] Add encryption ceiling note to agency-setup.md — 2026-02-02 (CR5)
- [x] Add `role="alert"` and `aria-live="polite"` to templates (18 files) — 2026-02-02 (CR9)
- [x] Create ModelForm classes for login, feature toggle, custom fields, AI endpoints — 2026-02-02 (CR4)
- [x] Add tests for auth views, plan CRUD, and AI endpoints (60 tests) — 2026-02-02 (CR6)
- [x] Code review: DEBUG, CSRF, migrations, empty states verified — 2026-02-02 (CR2, CR3, CR7, CR10)
- [x] Staff dashboard with recent clients, alerts, quick stats, needs-attention list — 2026-02-02 (UX1)
- [x] HTMX-powered client detail tabs (no full page reloads) — 2026-02-02 (UX2)
- [x] Target selection checkboxes on note form — 2026-02-02 (UX3)
- [x] Notes list filtering (type, date, author) and pagination — 2026-02-02 (UX4)
- [x] Fix N+1 queries in client search/list with prefetch_related — 2026-02-02 (UX5)
- [x] Fix note collapse to use HTMX instead of location.reload() — 2026-02-02 (UX6)
- [x] Add hx-confirm to destructive plan actions — 2026-02-02 (UX7)
- [x] Group admin nav items under dropdown menu — 2026-02-02 (UX8)
- [x] Autofocus search input on home page — 2026-02-02 (UX9)
- [x] Select All / Deselect All for metric export checkboxes — 2026-02-02 (UX10)
- [x] Error toasts persist until dismissed; added close button — 2026-02-02 (UX11)
- [x] PDF exports: individual client progress reports + bulk funder reports (WeasyPrint) — 2026-02-02 (RPT2)
- [x] Phase 7: Audit DB lockdown, CSP tuning, rate limiting, key rotation command, deployment guides (Azure, Elest.io, Railway), agency setup guide, backup/restore docs — 2026-02-02 (SEC1, SEC4, SEC5, SEED1, DOC1, DOC2, DOC3, DOC4, OPS2)
- [x] Phase 6: Terminology, feature toggles, instance settings, user management admin UIs, cache invalidation signals — 2026-02-02 (CUST1, CUST2, CUST3, USR1)
- [x] Phase 5: Charts, events, alerts, combined timeline, funder report export, audit log viewer — 2026-02-02 (VIZ1, EVT1, EVT2, VIZ2, RPT1, AUD1)
- [x] Phase 4: Quick notes, full structured notes, metric recording, templates admin, timeline, cancellation — 2026-02-02 (NOTE1–NOTE5)
- [x] Phase 3: Plan sections, targets, metrics, templates, apply-to-client, revision history — 2026-02-02 (PLAN1–PLAN6)
- [x] Phase 2: Program CRUD, role assignment, client CRUD, enrolment, custom fields, search — 2026-02-02 (PROG1–CLI3)
- [x] Create theme.css with design tokens (swappable per agency) — 2026-02-02 (DES1)
- [x] Replace badge colours with semantic token classes — 2026-02-02 (DES2)
- [x] Redesign login page with wordmark and brand colour — 2026-02-02 (DES3)
- [x] Add skip-nav, aria-live regions, branded focus style — 2026-02-02 (A11Y1)
- [x] Create empty state, loading bar, and toast patterns — 2026-02-02 (DES4)
- [x] Move login inline styles to CSS class — 2026-02-02 (DES5)
- [x] Generate Django migrations for all 8 apps — 2026-02-02 (FIX1)
- [x] Create test suite: 15 tests for RBAC + PII encryption — 2026-02-02 (TEST1)
- [x] Add HTMX global error handler + toast to app.js — 2026-02-02 (FIX2)
- [x] Register all models in admin.py (8 apps) + enable Django admin — 2026-02-02 (FIX3)
- [x] Phase 1: Django project scaffold, settings, Docker — 2026-02-02 (FOUND1)
- [x] Phase 1: Security middleware (RBAC, audit, CSP, CSRF) — 2026-02-02 (FOUND2)
- [x] Phase 1: All data models (clients, plans, notes, events, metrics) — 2026-02-02 (FOUND3)
- [x] Phase 1: Azure AD + local auth with Argon2 — 2026-02-02 (FOUND4)
- [x] Phase 1: PII encryption utilities (Fernet) — 2026-02-02 (FOUND5)
- [x] Phase 1: Metric library seed data (24 metrics) — 2026-02-02 (FOUND6)
- [x] Phase 1: Base templates (Pico CSS, HTMX) — 2026-02-02 (FOUND7)
