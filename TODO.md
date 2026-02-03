# Project Tasks

## Flagged

_Nothing flagged._

## Active Work

### Pre-Pilot Testing Fixes

- [ ] Fix test suite configuration error — (TEST2)
- [ ] Add CSV export for all client data — (EXP1)
- [ ] Add consent checkbox to note entry — (PRIV2)
- [ ] Create first-run setup wizard — (SETUP1)
- [ ] Mobile responsiveness pass — (UI1)
- [ ] Add backup automation examples to docs — (OPS1)
- [ ] Add client search filters (program, status, date) — (UX19)
- [ ] Add note auto-save / draft recovery — (UX21)
- [ ] Create "Quick Start for Staff" training doc — (DOC18)

## Roadmap — Prioritized Extensions

Based on usability review and expert panel analysis. See `tasks/usability-review-results.md` for full rationale.

### Phase A: Market Access (High Priority)

_All Phase A tasks complete._

### Phase B: Funder Reporting (High Priority)

- [x] Report aggregation functions — count, avg, min, max by grouping — (RPT3)
- [x] Demographic grouping in reports — age range, gender, geography — (RPT4)
- [x] Outcome achievement rate calculation — % clients meeting target — (RPT5)
- [x] Funder Report Template — draft export for funders (customise per funder) — (RPT6)
- [x] Fiscal year date range filter — April-March for Canadian nonprofits — (RPT7)

### Phase C: Documentation for Open-Source Adoption (High Priority)

See `tasks/documentation-improvement-plan.md` for full rationale.

- [x] Create getting-started.md — complete local dev setup guide — (DOC8)
- [x] Create security-operations.md — security tests, audit logs, key rotation — (DOC9)
- [x] Enhance README Quick Start — add key generation commands — (DOC10)
- [x] Add inline comments to .env.example — explain each variable — (DOC11)

**Phase C.2: Non-Developer Accessibility** — See `tasks/documentation-expert-review.md`

- [x] Add "What You'll Need" pre-flight checklist to getting-started.md — (DOC12)
- [x] Add "What just happened?" explanations after key generation steps — (DOC13)
- [x] Add expected output examples showing what success looks like — (DOC14)
- [x] Add glossary section: terminal, repository, migration, container — (DOC15)
- [x] Create "Before You Enter Real Data" checkpoint document — (DOC16)
- [x] Fix placeholders to obviously fake values like REPLACE_THIS — (DOC17)

### Phase E: Self-Service Registration (Medium Priority)

Public sign-up forms for programs — parents register kids for sports, adults sign up for classes. See `tasks/self-service-registration-design.md` for full design.

- [x] RegistrationLink model — shareable form config per program — (REG1)
- [x] Public registration form view — mobile-friendly, no login required — (REG2)
- [x] RegistrationSubmission model — pending entries awaiting review — (REG3)
- [x] Submission review UI — approve/reject/merge duplicates — (REG4)
- [x] Auto-approve option — skip staff review for low-risk programs — (REG5)
- [x] Duplicate detection — match by email/phone, flag for merge — (REG6)
- [x] Capacity limits and deadlines — close registration when full or past date — (REG7)
- [x] Iframe embed support — agencies can embed form on their own website — (REG8)

### Planned Extensions (Build When Requested)

These features are designed but deferred until agencies request them. See expert panel rationale in `tasks/field-data-decision.md`.

- [ ] Field data collection integrations — KoBoToolbox, Forms, or other tools — (FIELD1)
- [ ] CSV bulk client import — simpler alternative to tool-specific integrations — (IMP1)

### Explicitly Out of Scope

These features are intentionally excluded. See technical documentation for rationale.

- ~~Calendar/scheduling~~ → Recommend Calendly, Google Calendar, Microsoft Bookings
- ~~Full document storage~~ → Recommend Google Drive, SharePoint, Dropbox
- ~~Offline PWA~~ → Paper forms acceptable; integrations available when needed
- ~~Multi-tenancy~~ → Fork required for coalition implementations

## Parking Lot

- [ ] PIPEDA/PHIPA consent workflow — block note entry until client consent recorded — (PRIV1)
- [ ] GDPR toolkit UI — data export, right to erasure, consent management — (GDPR1)
- [ ] CSV export of all client data for migration to future systems — (EXP1)
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

- [x] Iframe embed support for registration forms — 2026-02-03 (REG8)
- [x] Phase E: Self-service registration complete (REG1–REG7) — 2026-02-03
- [x] Add "What You'll Need" pre-flight checklist to getting-started.md — 2026-02-03 (DOC12)
- [x] Add "What just happened?" explanations after key generation steps — 2026-02-03 (DOC13)
- [x] Add expected output examples showing what success looks like — 2026-02-03 (DOC14)
- [x] Add glossary section: terminal, repository, migration, container — 2026-02-03 (DOC15)
- [x] Create "Before You Enter Real Data" checkpoint document — 2026-02-03 (DOC16)
- [x] Fix placeholders to obviously fake values like REPLACE_THIS — 2026-02-03 (DOC17)
- [x] French UI translation — Django i18n setup + ~500 strings — 2026-02-03 (I18N1)
- [x] Document folder button — link to client folder in SharePoint/Google Drive — 2026-02-03 (DOC5)
- [x] Terminology override by language — extend model for fr/en terms — 2026-02-03 (I18N2)
- [x] Create getting-started.md — complete local dev setup with Docker option — 2026-02-03 (DOC8)
- [x] Create security-operations.md — security tests, audit logs, key rotation — 2026-02-03 (DOC9)
- [x] Enhance README Quick Start — add key generation commands — 2026-02-03 (DOC10)
- [x] Add inline comments to .env.example — explain each variable — 2026-02-03 (DOC11)
- [x] "What KoNote Is and Isn't" documentation page — set scope expectations — 2026-02-03 (DOC6)
- [x] Show custom fields in read-only mode by default with edit toggle — 2026-02-03 (UX12)
- [x] Add date-only toggle to event form — 2026-02-03 (UX13)
- [x] Style permission error pages with navigation and helpful text — 2026-02-03 (UX14)
- [x] Add status and program filters to client list page — 2026-02-03 (UX15)
- [x] Auto-dismiss success messages after 3 seconds; keep errors persistent — 2026-02-03 (UX16)
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
