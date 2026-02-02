# Project Tasks

## Flagged

- [ ] Phase prompts reference plan file `idempotent-cooking-walrus.md` — verify it exists or embed key decisions in CLAUDE.md — (FLAG1)
- [ ] Confirm Phase 1 migrations were generated and committed — (FLAG2)

## Active Work

**Pre-Phase 2: Foundation gaps (expert review)**
- [ ] Verify/generate Django migrations for all apps and commit migration files — (FIX1)
- [ ] Create basic test suite: RBAC enforcement + PII encryption tests — (TEST1)
- [ ] Add HTMX global error handler to app.js — (FIX2)
- [ ] Register all models in admin.py for debugging during development — (FIX3)

**Phase 2: Core Data — Programs & Clients**
- [ ] Create program CRUD views and templates — (PROG1)
- [ ] Create user-program role assignment UI — (PROG2)
- [ ] Create client file CRUD with encrypted PII — (CLI1)
- [ ] Create client-program enrolment UI — (CLI2)
- [ ] Create custom field definitions admin UI — (FIELD1)
- [ ] Create client detail values form (EAV) — (FIELD2)
- [ ] Create client search with HTMX — (CLI3)

## Coming Up

**Phase 3: Outcomes — Plans & Targets**
- [ ] Create plan section CRUD for client files — (PLAN1)
- [ ] Create plan target CRUD with status management — (PLAN2)
- [ ] Create metric assignment to targets — (PLAN3)
- [ ] Create plan template admin UI — (PLAN4)
- [ ] Create "apply template to client" flow — (PLAN5)
- [ ] Create target revision history view — (PLAN6)

**Phase 4: Progress Notes**
- [ ] Create quick note form — (NOTE1)
- [ ] Create full structured note form with target entries — (NOTE2)
- [ ] Create metric value recording per target — (NOTE3)
- [ ] Create progress note template admin UI — (NOTE4)
- [ ] Create notes timeline view for client file — (NOTE5)

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

- [x] Phase 1: Django project scaffold, settings, Docker — 2026-02-02 (FOUND1)
- [x] Phase 1: Security middleware (RBAC, audit, CSP, CSRF) — 2026-02-02 (FOUND2)
- [x] Phase 1: All data models (clients, plans, notes, events, metrics) — 2026-02-02 (FOUND3)
- [x] Phase 1: Azure AD + local auth with Argon2 — 2026-02-02 (FOUND4)
- [x] Phase 1: PII encryption utilities (Fernet) — 2026-02-02 (FOUND5)
- [x] Phase 1: Metric library seed data (24 metrics) — 2026-02-02 (FOUND6)
- [x] Phase 1: Base templates (Pico CSS, HTMX) — 2026-02-02 (FOUND7)
