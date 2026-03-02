# P0 Deliverable: Multi-Tenancy Implementation Plan

**Requirement IDs:** MA3 (central management), MA4 (agency provisioning), MA5 (tenant isolation)
**Deliverable type:** Costed implementation plan (not live code by March 31)
**Date:** 2026-03-02
**Source documents:** tasks/design-rationale/multi-tenancy.md (DRR), tasks/hosting-cost-comparison.md, tasks/design-rationale/ovhcloud-deployment.md

---

## Executive Summary

KoNote's multi-tenancy architecture is fully designed and ready to build. Using `django-tenants` (schema-per-tenant isolation via PostgreSQL), each agency gets its own database schema within a shared infrastructure — combining strong data isolation with low per-agency cost.

This document presents the implementation plan, effort estimates, cost model, and timeline. All architectural decisions have been made through expert panel review (see multi-tenancy DRR).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Shared Infrastructure (one VPS or Azure instance)           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  PostgreSQL Database                                 │    │
│  │                                                     │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │  public   │  │ agency_a │  │ agency_b │  ...     │    │
│  │  │ (shared)  │  │ (tenant) │  │ (tenant) │          │    │
│  │  │           │  │          │  │          │          │    │
│  │  │ Agency    │  │ Client   │  │ Client   │          │    │
│  │  │ Consortium│  │ Plan     │  │ Plan     │          │    │
│  │  │ TenantKey │  │ Note     │  │ Note     │          │    │
│  │  │ AuditLog  │  │ Report   │  │ Report   │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Django   │  │  Caddy   │  │ Autoheal │                  │
│  │ Gunicorn  │  │ (HTTPS)  │  │          │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

**How it works:**
- `django-tenants` middleware reads the subdomain from each request (e.g., `agency-a.konote.ca`)
- PostgreSQL `SET search_path` routes all queries to the correct schema
- Application code is unchanged — no `tenant_id` filters needed anywhere
- Each agency's data is isolated at the database level, not the application level

**Why this approach:**
- PostgreSQL schema boundaries prevent cross-tenant data leaks (unlike row-level filtering where a missed `.filter()` = data breach)
- Existing KoNote code needs minimal changes — middleware handles tenant routing automatically
- `django-tenants` is mature, used in healthcare SaaS, well-maintained

---

## Implementation Tasks

### Task 0: Switch Local Development to PostgreSQL

**What:** Replace SQLite with PostgreSQL for local development via Docker Compose.

**Why:** `django-tenants` requires PostgreSQL schemas, which SQLite doesn't support. This is a prerequisite for all other tasks.

**Work:**
- Create `docker-compose.dev.yml` with PostgreSQL 16 (main + audit databases)
- Update `settings.py` to use PostgreSQL in all environments
- Update developer setup docs
- Migrate existing demo/seed data

**Effort:** 1–2 days
**Risk:** Low — Docker Compose setup is well understood

### Task 1: Install django-tenants and Configure Shared/Tenant App Split

**What:** Install `django-tenants`, define which Django apps live in the shared schema vs tenant schemas.

**Work:**
- Install `django-tenants` package
- Create `Agency` model (tenant) and `AgencyDomain` model in a new `tenants` app
- Split `INSTALLED_APPS` into `SHARED_APPS` and `TENANT_APPS`
- Configure `DATABASE_ROUTERS` and middleware
- Create initial migration that sets up the public schema

**Shared apps:** tenants, users (TBD — may need to be tenant-scoped), admin
**Tenant apps:** clients, plans, notes, reports, programs, portal, surveys, communications

**Effort:** 2–3 days
**Risk:** Medium — the shared/tenant split requires careful analysis of model relationships. Foreign keys cannot cross the schema boundary.

### Task 2: Tenant Middleware and Domain Routing

**What:** Configure `django-tenants` middleware to route requests by subdomain.

**Work:**
- Add `TenantMainMiddleware` to middleware stack
- Configure Caddy for wildcard subdomains (`*.konote.ca`)
- Set up `*.localhost` for local development (works in modern browsers without DNS changes)
- Create management command to provision a new tenant (create schema, run migrations, set domain)

**Effort:** 1–2 days
**Risk:** Low — standard django-tenants configuration

### Task 3: Per-Tenant Encryption Keys

**What:** Each agency gets its own Fernet encryption key, stored in a shared-schema table and encrypted by the master key from Azure Key Vault.

**Work:**
- Create `TenantKey` model in shared schema (tenant FK, encrypted_key, created_at, rotated_at)
- Update `encryption.py` to resolve the current tenant's key instead of using a single env var
- Implement key generation during tenant provisioning
- Add key rotation management command
- Fallback: existing single-tenant data uses the master key directly (backward compatible)

**Effort:** 2–3 days
**Risk:** Medium — encryption changes must be tested thoroughly. Key loss = permanent data loss.

### Task 4: Consortium Data Model

**What:** Create the models that enable cross-agency data sharing for funder reporting.

**Models (shared schema — `tenants` app):**
- `Consortium` — represents a funder/network that multiple agencies report to (name, description, created_by)

**Models (tenant schema — new `consortia` app):**
- `ConsortiumMembership` — links an agency to a consortium (consortium FK, joined_at, is_active)
- `ProgramSharing` — per-program sharing consent (program FK, consortium FK, metrics shared, date_from)
- `PublishedReport` — aggregate report snapshot published to a consortium (report_template FK, period, data_json, published_by, published_at)

**Key design decisions (from DRR):**
- Sharing is per-program, not per-agency — one agency may share youth program data with Funder A but not addiction services data
- `PublishedReport` stores aggregate output only — never individual participant records
- `Consortium` model lives in the `tenants` app (shared schema) because it's cross-tenant by definition

**Effort:** 2–3 days
**Risk:** Low for model creation. GK reviews the data model before implementation.

### Task 5: Consent and Audit Fields

**What:** Add consent tracking and audit context for multi-tenant operation.

**Work:**
- Add `consent_to_aggregate_reporting` boolean to program enrolment (opt-in per client per program)
- Add `tenant_schema` string column to audit database tables (identifies which agency generated each audit entry)
- Update audit log middleware to populate `tenant_schema` automatically

**Effort:** 1–2 days
**Risk:** Low — additive fields, non-breaking migration

### Task 6: Tenant Provisioning Command

**What:** A management command that creates a new agency tenant end-to-end.

**What it does:**
1. Creates PostgreSQL schema
2. Runs all tenant migrations
3. Generates per-tenant encryption key (Task 3)
4. Creates admin user
5. Loads default configuration (terminology, feature toggles)
6. Sets up domain routing
7. Outputs the agency URL

**Effort:** 1–2 days
**Risk:** Low — assembles pieces from Tasks 1–5

### Task 7: Test Infrastructure Update

**What:** Update pytest configuration so tests run in a tenant context.

**Work:**
- Create `tenant` pytest fixture that provisions a test tenant with schema
- Update `conftest.py` to use tenant-aware database setup
- Fix tests that assume a single-tenant context
- Add tenant isolation tests (verify queries don't leak across schemas)

**Effort:** 3–5 days (most variable task — depends on how many tests need updating)
**Risk:** Medium — this is the most time-consuming task because every test must work in a tenant context

### Task 8: Validate Existing Features

**What:** Run the full application in a multi-tenant configuration and verify everything works.

**Work:**
- Provision 2–3 test tenants with demo data
- Run full test suite across tenants
- Verify: client search, progress notes, reports, portal, surveys, communications
- Fix any tenant-related failures
- Run QA scenarios against a multi-tenant instance

**Effort:** 2–3 days
**Risk:** Medium — unknown unknowns may surface

---

## Effort Summary

| Task | Description | Effort | Dependencies |
|------|-------------|--------|-------------|
| 0 | PostgreSQL for local dev | 1–2 days | None |
| 1 | django-tenants + app split | 2–3 days | Task 0 |
| 2 | Middleware + domain routing | 1–2 days | Task 1 |
| 3 | Per-tenant encryption keys | 2–3 days | Task 1 |
| 4 | Consortium data model | 2–3 days | Task 1 |
| 5 | Consent + audit fields | 1–2 days | Task 1 |
| 6 | Provisioning command | 1–2 days | Tasks 1–5 |
| 7 | Test infrastructure | 3–5 days | Tasks 1–6 |
| 8 | Validate existing features | 2–3 days | Task 7 |
| **Total** | | **15–25 developer days** | |

**Calendar time:** 4–6 weeks with one developer (PB), accounting for review cycles and unforeseen issues.

**Tasks 2, 3, 4, 5 can run in parallel** after Task 1 is complete, reducing calendar time to ~3–4 weeks if resources allow.

---

## Cost Model

### Infrastructure Cost (from hosting-cost-comparison.md)

| Scale | OVHcloud Multi-Tenant | Azure Multi-Tenant |
|-------|----------------------|-------------------|
| 1 agency | $53 CAD/mo | $374 CAD/mo |
| 5 agencies | $81 CAD/mo ($16/agency) | $402 CAD/mo ($80/agency) |
| 10 agencies | $116 CAD/mo ($12/agency) | $456 CAD/mo ($46/agency) |

**Recommendation:** OVHcloud for cost-sensitive deployments, Azure when the agency or funder requires it. Both paths are supported.

### Development Cost

At an estimated developer rate of $100–150/hr:
- **15–25 days × 8 hours = 120–200 hours**
- **Estimated cost: $12,000–$30,000 CAD** (one-time)
- Payback period at 10 agencies on OVHcloud: infrastructure savings vs single-tenant cover the development cost within 6–12 months

---

## Sequencing

The multi-tenancy DRR states: "Do not start building multi-tenancy until the first agency is live on a single-tenant deployment."

**Current status:** OVHcloud deployment is in progress (another session). Once the first agency is live and the deployment protocol is validated, multi-tenancy work can begin.

**Recommended sequence:**
1. First agency live on OVHcloud single-tenant (in progress)
2. Validate deployment protocol and onboarding process with real usage
3. Begin Task 0 (PostgreSQL for local dev) — can start any time
4. Tasks 1–8 on a feature branch, merged to develop when Task 8 passes
5. Second agency provisioned as first real tenant

---

## Risk Registry

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Key loss (master or tenant key) | Low | Critical — permanent data loss | Key Vault backup, sealed envelope custody, key backup verification in go-live checklist |
| Test suite breakage during migration | High | Medium — 2–5 days of fix work | Task 7 explicitly budgets for this |
| Cross-schema FK issues | Medium | Medium — requires model refactoring | Analyse foreign key graph before starting Task 1 |
| Performance at 10+ tenants | Low | Low — PostgreSQL handles schemas well | Monitor query times, add connection pooling if needed |

---

## What This Plan Demonstrates (for P0)

- **MA3 (central management):** Consortium model enables cross-agency oversight. Provisioning command automates agency setup.
- **MA4 (agency provisioning):** Management command provisions a new agency in minutes — schema, encryption, config, domain.
- **MA5 (tenant isolation):** PostgreSQL schema-per-tenant provides database-level isolation. Per-tenant encryption keys mean one compromised agency doesn't expose others.
