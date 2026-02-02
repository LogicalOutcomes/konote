# Project Tasks

## Flagged

_Nothing flagged._

## Active Work

**Phase 5: Visualisation, Events & Audit**
- [ ] Create Chart.js progress charts (metrics over time) — (VIZ1)
- [ ] Create event type admin and event CRUD — (EVT1)
- [ ] Create alerts CRUD — (EVT2)
- [ ] Create client timeline view (notes + events combined) — (VIZ2)
- [ ] Create aggregate metrics export (CSV by program + date range for funder reporting) — (RPT1)
- [ ] Create audit log viewer with filtering and CSV export — (AUD1)

**Phase 6: Customisation Admin**
- [ ] Create terminology overrides admin UI — (CUST1)
- [ ] Create feature toggles admin UI — (CUST2)
- [ ] Create instance settings admin (branding, formats, timeouts) — (CUST3)
- [ ] Create user management admin (create, deactivate, assign roles) — (USR1)

**Phase 7: Hardening & Deployment**
- [ ] Lock down audit DB permissions at deploy time, not after all phases — (SEC1)
- [ ] Tune CSP and rate limiting for production — (SEC4)
- [ ] Create encryption key rotation management command — (SEC5)
- [ ] Write deployment guide for Azure — (DOC1)
- [ ] Write deployment guide for Elest.io — (DOC2)
- [ ] Write deployment guide for Railway — (DOC3)
- [ ] Write agency setup guide (first-run wizard) — (DOC4)
- [ ] Add pg_dump backup/restore documentation — (OPS2)

## Parking Lot

- [ ] PIPEDA/PHIPA consent workflow — block note entry until client consent recorded — (PRIV1)
- [ ] GDPR toolkit UI — data export, right to erasure, consent management — (GDPR1)
- [ ] French language support (bilingual UI) — (I18N1)
- [ ] Data import from existing systems (CSV) — (IMP1)
- [ ] Print/export progress reports to PDF — (RPT2)
- [ ] Mobile-responsive optimisation pass — (UI1)
- [ ] First-run setup wizard for new instances — (SETUP1)
- [ ] Automated backups documentation — (OPS1)
- [ ] Encrypted search optimisation (search hash field) for large client lists — (PERF1)

## Recently Done

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
