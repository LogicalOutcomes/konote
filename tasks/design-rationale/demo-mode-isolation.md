---
drr: demo-mode-isolation
status: Draft - awaiting GK review
parent_principle: security-by-default
blast_radius: high
source: foundation-security-by-default.md §10 + CLAUDE.md memory "feedback_demo_data_safeguards" (2026-03-14)
enforcement:
  - type: django-system-check
    id: W012_demo_data_safeguards
    description: "Existing W012 check — runtime floor for demo data, demo/real crossover detection"
  - type: pytest
    file: tests/drr/test_demo_isolation.py
    description: "Demo user cannot see real data via direct URL; real user cannot see demo data; is_demo flag enforced at ORM layer and request-access layer"
  - type: semgrep
    rule: demo-flag-must-filter-queries
    description: "Querysets touching ClientFile, ConsentEvent, ClientDetailValue, ClientAccessBlock, ProgressNote, ProgressNoteTarget, PlanTarget, PlanTargetRevision, SurveyAssignment, SurveyResponse, SurveyAnswer, CorrectionRequest, StaffPortalNote, ClientResourceLink, or Circle must filter by is_demo (or traverse client_file__is_demo / created_by__is_demo) outside an allowlist of admin management commands"
  - type: codeowner
    paths: [apps/admin_settings/demo_engine.py, apps/admin_settings/management/commands/seed_demo_data.py, apps/admin_settings/checks.py]
---

# DRR: Demo Mode Isolation

**Parent Principle:** [Security by Default](../principles/security-by-default.md)

## Core Decision

KoNote supports demo accounts for trials, training, and sales conversations inside the same tenant schema. Demo and real data **must never cross**:

- **Demo users see demo data only.** Real client records are invisible to them at every layer.
- **Real users see real data only.** Demo records are invisible in production queries.
- **Demo users cannot modify agency settings.** Terminology, feature toggles, and RBAC matrix changes are blocked.
- **Row-level `is_demo` filtering is the authoritative isolation boundary.** Demo users and real users share the tenant schema (schema-per-tenant already provides the outer boundary — see [multi-tenancy](multi-tenancy.md)); the separation between demo and real data is enforced by the `is_demo` boolean on `User` and `ClientFile`, and every demo-scoped model joins or filters to one of those.
- **The `is_demo` filter is enforced at two layers**: the ORM queryset (data-level; the Semgrep rule above forbids querysets on demo-scoped models that skip the filter) and request-level access checks on sensitive endpoints (views that look up a record by primary key verify the caller's `is_demo` matches the record's `is_demo` before returning it). UI visibility is a convenience; it is not the boundary.

This allows agencies to trial KoNote and train new staff without risk of contaminating real records or exposing real client data during a demonstration.

**Shared reference data** (CIDS taxonomy codes, default terminology packs, system-generated templates, small-cell thresholds) is not scoped by `is_demo` — it is read-only catalog data, shared across demo and real contexts. Demo seeding copies *from* the shared reference data; it never writes back to it. Custom-field definitions a demo user creates are scoped to the demo user's agency and carry `is_demo=True` on their usage rows, so they cannot leak into real-tenant reports.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| UI-only separation (hiding real data via template logic) | URL/API manipulation defeats UI-only checks |
| Test accounts that can view real data "just for admins" | Admin accounts are the highest-value coercion target |
| Demo data mixed into production queries | Statistics, dashboards, and reports become unreliable |
| Disabling demo safeguards for "clean demos" | The safeguards ARE the demo feature; disabling them re-creates the hazard |
| Relying on UI-layer filtering alone (hiding real data via template logic) | URL/API manipulation defeats UI-only checks — the ORM `is_demo` filter is the boundary, not the template |

## CI enforcement (detail)

1. **Django system check W012** (already implemented — see `apps/admin_settings/checks.py`) validates the runtime floor for demo data and flags demo/real crossover. This DRR canonicalises that check.
2. **Pytest** `tests/drr/test_demo_isolation.py` — (a) log in as demo user, attempt to fetch a real participant by known primary key via direct URL → expect 404, (b) log in as real user, attempt to fetch a demo participant → expect 404, (c) log in as demo user, attempt to POST to agency settings → expect 403.
3. **Semgrep rule** `demo-flag-must-filter-queries` — any queryset on the enumerated demo-scoped models (see front-matter: `ClientFile`, `ConsentEvent`, `ClientDetailValue`, `ClientAccessBlock`, `ProgressNote`, `ProgressNoteTarget`, `PlanTarget`, `PlanTargetRevision`, `SurveyAssignment`, `SurveyResponse`, `SurveyAnswer`, `CorrectionRequest`, `StaffPortalNote`, `ClientResourceLink`, `Circle`) must either filter directly by `is_demo=` / `client_file__is_demo=` / `created_by__is_demo=`, or go through a helper that does. The allowlist is the admin-management module `apps/admin_settings/demo_engine.py` and the `seed_demo_data` command — these modules intentionally traverse both sides. When a new demo-scoped model is added, it MUST be added to this list in the same PR (a pytest in `tests/drr/test_drr_metadata.py` compares the list in the front-matter against the set of models with an `is_demo` field or FK to a model that has one).
4. **CODEOWNERS** on the demo engine, seed command, and W012 check module.

## When to revisit

If KoNote introduces "staging" or "UAT" tenant modes distinct from demo, those need their own isolation guarantees. The demo/real separation remains load-bearing regardless.

## Related DRRs

- [multi-tenancy](multi-tenancy.md) — schema-per-tenant provides the outermost isolation layer
- [access-tiers](access-tiers.md) — role restrictions apply within both demo and real contexts
- [audit-log-isolation](audit-log-isolation.md) — demo user actions are still audited (separate retention is fine)
