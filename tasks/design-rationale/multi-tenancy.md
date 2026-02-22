# Design Rationale Record: Multi-Tenancy Architecture

**Feature:** Schema-per-tenant multi-tenancy using django-tenants, with per-tenant encryption and consortium data model
**Status:** Decided. Implementation starts after first single-tenant agency deployment is live.
**Date:** 2026-02-21
**Implementation plan:** `tasks/prosper-canada/multi-tenancy-implementation-plan.md`

---

## Keyword Index

django-tenants, schema-per-tenant, multi-tenancy, PostgreSQL schemas, tenant isolation,
per-tenant encryption, master key, TenantKey, Fernet, key rotation, key loss,
consortium, ConsortiumMembership, ProgramSharing, PublishedReport, aggregate reporting,
cell suppression, n<5, de-identification, PIPEDA, PHIPA,
shared schema, public schema, SHARED_APPS, TENANT_APPS, Agency model, AgencyDomain,
audit database, tenant_schema column, localhost subdomains, local development,
SQLite to PostgreSQL migration, consent_to_aggregate_reporting

---

## The Decision

KoNote will use **schema-per-tenant multi-tenancy** via the `django-tenants` library. Each agency gets its own PostgreSQL schema within a shared database. A shared (public) schema holds tenant metadata, consortium definitions, and per-tenant encryption keys.

**This decision was made after:**
- Expert panel review (Software Architect, Nonprofit Technology Strategist, Privacy & Compliance Specialist, Systems Thinker) on 2026-02-20
- Code review panel that identified and resolved 11 issues
- Stakeholder review on 2026-02-21

**Sequencing condition:** Do not start building multi-tenancy until the first agency is live on a single-tenant deployment. The deployment protocol, config templates, and onboarding process must be validated with real usage first. This avoids adding infrastructure complexity before the product workflow is proven.

---

## Why Schema-Per-Tenant (Not the Alternatives)

Three approaches were evaluated:

| Approach | How it works | Verdict |
|----------|-------------|---------|
| **Separate deployments** | Each agency gets its own database, app server, and domain. Completely isolated. | Works for 2-5 agencies. Doesn't scale to 10-20. Each deployment needs its own backups, updates, monitoring. Operational burden grows linearly. |
| **Shared database, row-level isolation** | One database, every table has a `tenant_id` column. Queries filter by tenant. | Cheapest to run, but one missed filter = data leak between agencies. For encrypted PII under PHIPA, this risk is unacceptable. Every query, every view, every report must remember to filter. |
| **Schema-per-tenant** (chosen) | One database, each agency gets its own PostgreSQL schema. `django-tenants` handles routing automatically. | Strong isolation (schemas are database-level boundaries), but shared infrastructure (one database server, one app deployment, shared updates). Middleware sets the schema per request — application code doesn't need to know about tenants. |

**Why schema-per-tenant won:**
- Isolation is enforced by PostgreSQL, not by application code — a missed filter can't leak data
- `django-tenants` is mature (used in healthcare SaaS, well-maintained, good documentation)
- Existing KoNote code needs minimal changes — middleware handles tenant routing
- Shared infrastructure keeps costs low for 10-20 agencies
- Per-tenant encryption keys mean one compromised agency doesn't expose others

---

## Anti-Patterns

### DO NOT use row-level tenant isolation for this system

Shared-table multi-tenancy (adding `tenant_id` to every table) is cheaper and simpler for some applications. It is not appropriate for KoNote because:
- PII is Fernet-encrypted at the field level. If a query accidentally crosses tenant boundaries, it returns encrypted data that can't be decrypted (wrong key) — but the *existence* of records is leaked, which is itself a PHIPA violation
- Every query would need tenant filtering. One missed `.filter(tenant=current_tenant)` in any view, report, or management command = cross-tenant data exposure
- The test suite would need to verify tenant isolation on every single query — massive testing burden

### DO NOT store tenant encryption keys in environment variables

It's tempting to use `TENANT_A_KEY=xxx, TENANT_B_KEY=yyy` in env vars. This doesn't scale:
- Adding a new agency requires restarting the application to load new env vars
- Key rotation requires coordinated env var updates across all deployment environments
- No audit trail for key access

The chosen approach (keys in a shared-schema database table, encrypted by a master key from env var) scales to N tenants without restarts.

### DO NOT build multi-tenancy before the first agency is live

The deployment protocol, configuration templates, and onboarding workflow must be validated with a real agency on a simple single-tenant deployment first. Reasons:
- If the onboarding process has problems, you want to debug them without multi-tenancy complexity in the way
- The first deployment proves the product works; multi-tenancy is infrastructure, not product
- Prince needs to understand the full codebase before adding tenant middleware that affects every request

### DO NOT put Consortium model in the consortia app

`django-tenants` manages models at the **app level** — all models in a SHARED_APPS app go to the public schema, all models in a TENANT_APPS app go to tenant schemas. You cannot split one app across schemas. The `Consortium` model must be in the shared schema (it's cross-tenant by definition), so it lives in the `tenants` app alongside `Agency` and `AgencyDomain`. The `consortia` app (tenant-scoped) holds `ConsortiumMembership`, `ProgramSharing`, and `PublishedReport`.

A future developer might think "Consortium belongs in the consortia app." It doesn't, and moving it there will break schema routing.

---

## Key Technical Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Library | `django-tenants` | Mature, PostgreSQL-native, schema-level isolation, healthcare/SaaS track record |
| Encryption | Per-tenant keys in shared DB table, encrypted by master env var key | Scales to N tenants, supports per-tenant offboarding (delete key = data is unrecoverable), no restart needed for new tenants |
| Existing data migration | First tenant gets the master key as its tenant key | No re-encryption needed. Backward compatible. Fallback path in `_get_tenant_fernet()` handles the transition. |
| Consortium sharing granularity | Per-program, not per-agency | Different programs within one agency may be funded by different funders. An agency shares its "Financial Coaching" data with a funder but not its "Youth Services" data. |
| User model scope | Per-tenant | Each agency has its own users. Funder users access aggregate data via consortium dashboard, not by logging into tenant schemas. |
| Audit database | Stays separate, add `tenant_schema` string column | Already append-only in a separate database. Foreign keys across databases don't work. String column is simpler and survives tenant deletion. |
| De-identification threshold | Suppress cells where n < 5 | Standard threshold used in Canadian health data reporting to prevent re-identification. |
| Local dev tenant resolution | `*.localhost` subdomains | Works in all modern browsers without DNS or hosts file changes. `agency1.localhost:8000` resolves to `127.0.0.1` automatically. |

---

## Risk Registry

### Key Loss (CRITICAL)
**What:** The master encryption key (env var) is lost or the TenantKey database table is corrupted.
**Consequence:** All encrypted PII across all tenants is permanently unrecoverable.
**Mitigation:** Master key must be backed up in a secure location separate from the database. TenantKey table must be included in database backups. Key backup verification must be part of the go-live checklist for every agency.

### Local Dev Complexity (LOW but permanent)
**What:** Developers must run PostgreSQL via Docker for all local work. SQLite no longer works.
**Consequence:** Higher setup friction. Docker Desktop must be running during development.
**Mitigation:** `docker-compose.dev.yml` is provided in the plan. Document clearly in developer onboarding.

### Test Suite Breakage During Migration (MEDIUM, one-time)
**What:** Existing tests fail because they don't set up tenant context.
**Consequence:** 2-5 days of work fixing tests after Task 1-6.
**Mitigation:** Plan Task 7 explicitly budgets for this. A `tenant` pytest fixture in `conftest.py` handles most cases.

---

## Sequencing

```
1. Deploy first agency on single-tenant (validate product + onboarding)
         |
         v
2. Task 0: Switch local dev to PostgreSQL
         |
         v
3. Tasks 1-6: Build multi-tenancy (on feature branch)
         |
         v
4. Task 7: Validate — run full test suite, fix failures
         |
         v
5. Deploy second agency as first real tenant
```

---

## Explicitly Deferred (from implementation plan)

| Feature | Why deferred | When to build |
|---------|-------------|---------------|
| Federation API endpoint | Additive — just a view | When a second consortium or standalone instance needs it |
| Consortium dashboard UI | Consumer of data | After report data model is validated with real data |
| Data sharing agreement workflow | Process layer | Before first production consortium |
| Re-consent workflow | Can be manual initially | Before second consortium onboarding |
| Report approval UI | Basic field exists | After report generation logic is built |

---

## Expert Panel Source

Panel convened 2026-02-20: Software Architect, Nonprofit Technology Strategist, Privacy & Compliance Specialist, Systems Thinker. Followed by code review that identified and resolved 11 issues. Full implementation plan at `tasks/prosper-canada/multi-tenancy-implementation-plan.md`.
