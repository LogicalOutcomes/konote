---
drr: tech-stack-constraints
status: Draft - awaiting GK review
parent_principle: nonprofit-sustainability
blast_radius: medium
source: foundation-nonprofit-sustainability.md §§1-3 (2026-03-14)
enforcement:
  - type: pre-commit-hook
    id: forbid-npm-package-json
    description: "Fail if package.json, package-lock.json, yarn.lock, or node_modules/ appear anywhere in the repo"
  - type: pre-commit-hook
    id: dependency-ceiling
    description: "Fail if requirements.txt exceeds 60 non-blank, non-comment lines without an accompanying CHANGELOG note"
  - type: pytest
    file: tests/drr/test_stack_constraints.py
    description: "Assert every Dockerfile starts FROM alpine or python:*-alpine; no webpack/vite/rollup/parcel config files exist; no package.json anywhere; requirements.txt is <=60 direct deps"
  - type: codeowner
    paths: [requirements.txt, Dockerfile*, docker-compose*.yml]
---

# DRR: Tech Stack Constraints

**Parent Principle:** [Nonprofit Sustainability](../principles/nonprofit-sustainability.md)

## Core Decision

KoNote's tech stack is constrained by design. Every added framework, dependency, and build tool is a maintenance burden that a small nonprofit ultimately carries. The ceiling is architectural, not advisory.

Specific constraints:

1. **No JavaScript framework.** No React, Vue, Angular, Svelte, or SPA patterns. No `package.json`, no `node_modules`, no webpack/vite/rollup, no `npm install` in the build pipeline. Server-rendered Django templates + HTMX + Pico CSS + vanilla JS only.
2. **Python dependency ceiling: 60 packages** in `requirements.txt` (production). The current count is ~46. Additions beyond 60 require a DRR amendment with explicit justification.
3. **Alpine-based container images.** Docker images must use Alpine (or `python:*-alpine`) as their base. This keeps image size small (5-20 MB vs 300+ MB for Debian), builds fast, and attack surface narrow.
4. **Configuration over code for feature toggles.** Demo mode, auth mode, AI provider, terminology — driven by environment variables, not code branches.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| "Let's add React for a richer dashboard" | 10x build complexity for marginal UX gain; introduces 100+ transitive deps |
| Quietly adding a heavy dependency "because we need it" | Every dep must justify its presence; adding 3 utility libs to avoid writing 20 lines is a bad trade |
| Debian/Ubuntu base images | 10-50x larger than Alpine; larger attack surface; slower deploys |
| Build-time code generation frameworks (GraphQL codegen, Prisma) | Adds a build step; adds a schema layer that must be kept in sync |
| Hard-coding feature toggles in Python | An agency needs to redeploy to change configuration |

## CI enforcement (detail)

1. **Pre-commit `forbid-npm-package-json`** — scans the repo for any file named `package.json`, `package-lock.json`, `yarn.lock`, or any `node_modules/` directory. Fails the commit if found. (Exception: if KoNote ever needs a tiny JS build step for a specific feature, the exception is defined here, not discovered in the diff.)
2. **Pre-commit `dependency-ceiling`** — counts non-blank, non-comment lines in `requirements.txt`. Fails at >60 unless the commit message contains `[deps-approved]` and `CHANGELOG.md` has an entry explaining the new dependency.
3. **Pytest** — asserts every `Dockerfile*` file at the repo root includes a base image matching `FROM alpine` or `FROM python:*-alpine`; asserts no `webpack.config.*`, `vite.config.*`, `rollup.config.*`, or `parcel.config.*` file exists anywhere; asserts no `package.json` anywhere; re-checks that `requirements.txt` has ≤60 direct pins (belt-and-braces with the pre-commit hook). Vendored static assets (e.g., `chart.js`, `htmx.min.js` placed directly under `static/`) are permitted — the ban is on build tooling, not on bundled JS files.

   **Scope note.** The `dependency-ceiling` hook counts non-blank, non-comment lines in `requirements.txt` only. Constraint files, `-r requirements/base.txt` includes, `pyproject.toml` / `setup.py` dependency declarations, and editable / transitive deps are explicitly out of scope; they are not measured and not forbidden, but adding them is still governed by the principle of "every dep must justify its presence."
4. **CODEOWNERS** — changes to `requirements.txt`, `Dockerfile*`, or `docker-compose*.yml` require DRR steward review.

## When to revisit

The numeric ceilings (60 deps, Alpine base) are guardrails, not dogma. They should be revisited if:

- A new Python dep unlocks substantial capability that would otherwise require much more code (the code-vs-dep trade-off shifted).
- The Alpine ecosystem loses support for a required library; switching to `python:*-slim` may become necessary.
- Nonprofit sector capacity grows to the point where a richer frontend stack becomes sustainable (no evidence yet).

The *principle* — deliberately constrained complexity — should not change.

## Related DRRs

- [ovhcloud-deployment](ovhcloud-deployment.md) — deployment architecture that the constraints support
- [self-hosted-llm-infrastructure](self-hosted-llm-infrastructure.md) — shared infrastructure model
- [multi-tenancy](multi-tenancy.md) — schema-per-tenant with minimal dep surface
