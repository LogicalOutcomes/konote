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
    description: "Demo user cannot see real data via direct URL; real user cannot see demo data; is_demo flag enforced at middleware and ORM layer"
  - type: semgrep
    rule: demo-flag-must-filter-queries
    description: "Querysets on client-scoped models must respect is_demo filter outside allowlisted admin views"
  - type: codeowner
    paths: [apps/core/demo.py, apps/core/middleware.py]
---

# DRR: Demo Mode Isolation

**Parent Principle:** [Security by Default](../principles/security-by-default.md)

## Core Decision

KoNote supports demo accounts for trials, training, and sales conversations. Demo and real data **must never cross**:

- **Demo users see demo data only.** Real client records are invisible to them at every layer.
- **Real users see real data only.** Demo records are invisible in production queries.
- **Demo users cannot modify agency settings.** Terminology, feature toggles, and RBAC matrix changes are blocked.
- **The `is_demo` flag is enforced at three layers**: middleware (route-level), ORM queryset (data-level), and UI (visual confirmation that cannot be relied on alone). If the middleware is bypassed via direct API or URL manipulation, the ORM layer still blocks the cross-over.

This allows agencies to trial KoNote and train new staff without risk of contaminating real records or exposing real client data during a demonstration.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| UI-only separation (hiding real data via template logic) | URL/API manipulation defeats UI-only checks |
| Test accounts that can view real data "just for admins" | Admin accounts are the highest-value coercion target |
| Demo data mixed into production queries | Statistics, dashboards, and reports become unreliable |
| Disabling demo safeguards for "clean demos" | The safeguards ARE the demo feature; disabling them re-creates the hazard |
| Demo accounts sharing the same tenant schema as real data | Schema-level separation is the strongest isolation available |

## CI enforcement (detail)

1. **Django system check W012** (already implemented per project memory) validates the runtime floor for demo data and flags demo/real crossover. This DRR canonicalizes that check.
2. **Pytest** — (a) log in as demo user, attempt to fetch a real participant by known primary key via direct URL → expect 404, (b) log in as real user, attempt to fetch a demo participant → expect 404, (c) log in as demo user, attempt to POST to agency settings → expect 403.
3. **Semgrep rule** — any queryset on `ClientFile`, `ProgressNote`, `Goal`, etc. outside an allowlist of admin management paths must filter by `is_demo` (or go through a helper that does).
4. **CODEOWNERS** on the demo isolation core files.

## When to revisit

If KoNote introduces "staging" or "UAT" tenant modes distinct from demo, those need their own isolation guarantees. The demo/real separation remains load-bearing regardless.

## Related DRRs

- [multi-tenancy](multi-tenancy.md) — schema-per-tenant provides the outermost isolation layer
- [access-tiers](access-tiers.md) — role restrictions apply within both demo and real contexts
- [audit-log-isolation](audit-log-isolation.md) — demo user actions are still audited (separate retention is fine)
