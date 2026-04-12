# Prompt: Revise the DRR / Principle restructure per review findings

## Context

A previous session split KoNote's four foundation documents into a `tasks/principles/` folder (philosophy) and seven new prescriptive DRRs in `tasks/design-rationale/`. A review (`tasks/drr-restructure-review.md` on branch `worktree/session-20260412-151658`) identified defects. Your job is to implement the revisions.

The draft DRRs live on branch `worktree/session-20260412-143934` in worktree `C:/Users/gilli/GitHub/konote/.worktrees/session-20260412-143934/`. Work in that worktree (or a fresh worktree off that branch) — do not touch `main` or `develop`.

The review document is at `tasks/drr-restructure-review.md` on this branch (`worktree/session-20260412-151658`). Read it in full before starting.

## Non-negotiable ground rules

1. **Verify every file path before writing it into a DRR.** The biggest defect in the drafts is invented paths. For every `paths:` entry under `codeowner` and every path named in prose, run `ls` or `Glob` against the real codebase and confirm it exists. If it doesn't, find the real equivalent — do not guess.
2. **Do not invent enforcement mechanisms.** If a rule is genuinely judgement-dependent (e.g., "no power-asymmetric access workflows"), reclassify it as `llm-review` or `judgment-only` rather than attaching a Semgrep rule that cannot deliver.
3. **Commit after each DRR edit.** Do not leave uncommitted changes across tool calls. Follow KoNote's git workflow (see CLAUDE.md) — feature branch off the existing draft branch, commit each file, PR to `develop`.
4. **Do not change decided values.** The review explicitly says "assume rule values are correct." Don't change 30 minutes to 60, 5 attempts to 10, etc. You're fixing clarity and enforcement, not policy.
5. **Do not delete the four `foundation-*.md` files yet.** The review said they stay until GK approves the restructure. Leave them alone.

## Canonical path map (use these, not the draft's invented paths)

The draft DRRs reference paths that do not exist. Use these real paths:

| Draft (wrong) | Real path |
|---|---|
| `konote/settings.py` | `konote/settings/` (directory: `base.py`, `production.py`, `development.py`, `test.py`, `build.py`) |
| `apps/accounts/views.py` | `apps/auth_app/` — check specific view module with `Glob` before pinning |
| `apps/accounts/backends.py` | `apps/auth_app/` (look for the actual auth backend file) |
| `apps/alerts/views.py` | alert cancellation lives in `apps/events/` — find the specific view with `Grep` |
| `apps/dv_safety/` | `apps/clients/dv_views.py` (+ DV-related fields in `apps/clients/models.py` and migrations `0029_add_dv_safe_fields.py`, `0030_seed_dv_sensitive_defaults.py`) |
| `apps/core/demo.py` | `apps/admin_settings/demo_engine.py` (+ `apps/admin_settings/management/commands/seed_demo_data.py`) |
| `apps/core/middleware.py` | `konote/middleware/` (specifically `konote/middleware/session_timeout.py` for session timeout; `konote/middleware/audit.py` for audit middleware) |
| `apps/clients/corrections.py` | file does not exist — `CorrectionRequest` is in `apps/clients/models.py`; views are likely in `apps/clients/views.py` or a dedicated file. Confirm with `Grep "CorrectionRequest"`. |
| `apps/clients/consent.py` | file does not exist — `ConsentEvent` is in `apps/clients/models.py` (see migration `0034_consentevent.py`). Confirm with `Grep "ConsentEvent"`. |
| `apps/clients/erasure.py` | EXISTS — keep as-is. |

Use `Glob` / `Grep` for anything not listed. Do not pin a path you haven't confirmed.

## Must-fix revisions (blockers)

### M1. Correct all wrong file paths in the seven new DRRs

For each file below, open it, find the `codeowner` `paths:` block in the front-matter, and replace wrong paths with the real ones per the table above. Also search the body of each DRR for the same wrong paths in prose and correct them.

- `tasks/design-rationale/audit-log-isolation.md` — fix `konote/settings.py`
- `tasks/design-rationale/session-security.md` — fix `konote/settings.py`, `apps/core/middleware.py`
- `tasks/design-rationale/rate-limiting-and-authentication.md` — fix `apps/accounts/views.py`, `apps/accounts/backends.py`, `konote/settings.py`
- `tasks/design-rationale/two-person-safety-actions.md` — fix `apps/alerts/views.py`, `apps/dv_safety/`
- `tasks/design-rationale/demo-mode-isolation.md` — fix `apps/core/demo.py`, `apps/core/middleware.py`
- `tasks/design-rationale/individual-data-rights.md` — fix `apps/clients/corrections.py`, `apps/clients/consent.py`
- `tasks/design-rationale/tech-stack-constraints.md` — paths are correct; leave alone

### M2. Build the meta-invariant check

The README in `tasks/design-rationale/README.md` promises: *"Every DRR must have an `enforcement:` front-matter block. CI uses this to gate PRs."* This is not enforced. Implement it:

1. Create `tests/drr/__init__.py` and `tests/drr/test_drr_metadata.py`.
2. The test walks `tasks/design-rationale/*.md` (excluding `README.md` and any `foundation-*.md` still present). For each file, parses YAML front-matter. Fails if:
   - Missing `enforcement:` block, OR
   - `enforcement:` is empty, OR
   - The file has `role: principle` (principles belong in `tasks/principles/`).
3. Similarly walk `tasks/principles/*.md` (excluding `README.md`). Fail if any file has `drr:` or `enforcement:` frontmatter keys.
4. Run locally (or on VPS per project conventions in `MEMORY.md`), confirm it passes on the current drafts, commit.

### M3. Resolve the demo-mode-isolation contradiction

In `tasks/design-rationale/demo-mode-isolation.md`, the Core Decision describes row-level `is_demo` filtering but one of the anti-patterns says *"Demo accounts sharing the same tenant schema as real data — Schema-level separation is the strongest isolation available."* These are inconsistent. Pick one:

- If the real architecture is row-level filtering (most likely — check `apps/auth_app/migrations/0003_add_is_demo_field.py` and `apps/clients/migrations/0002_add_is_demo_field.py`), rewrite the anti-pattern to match: *"Relying on UI-layer filtering alone — schema-sharing is fine, but row-level `is_demo` enforcement must be at ORM + middleware layers."*
- If schema-level separation is actually used for demo, rewrite the Core Decision to describe that and drop the ORM filter language.

Check the code before deciding. `Grep "is_demo"` in `apps/` will show you the actual pattern.

### M4. Narrow or reclassify `no-silent-record-overwrite`

In `tasks/design-rationale/individual-data-rights.md`, the Semgrep rule `no-silent-record-overwrite` as described flags any `ProgressNote.save()`, which includes normal creation. Choose one:

- **Option A (preferred if feasible):** narrow the rule to forbid `.save(update_fields=['body', 'content', ...])` or some specific update pattern. Check how notes are actually updated in the code first (`Grep "ProgressNote.*save"` in `apps/notes/`).
- **Option B:** Reclassify the enforcement entry as `type: llm-review` and rewrite the description to explain what a reviewer should check for semantically.

Do not leave it as-is.

### M5. Decide the accessibility question and write or document the decision

WCAG 2.2 AA was prescriptive in `foundation-collaborative-practice.md` §9 ("Accessible by Design") and is now silently dropped. AODA makes it a legal obligation. Two options:

- **Option A:** Write a new DRR `tasks/design-rationale/accessibility-requirements.md` with `parent_principle: collaborative-practice`. Enforcement likely combines: pytest that runs an axe-core scan against key templates (see existing `tests/test_a11y_ci.py` and `tests/test_accessibility_templates.py`), semgrep rule forbidding `<img>` without `alt=`, `<button>` without accessible text, and `role="..."` without validation. CODEOWNERS on templates.
- **Option B:** If the existing DRRs (`executive-dashboard-redesign.md`) plus existing tests already cover this, write a short DRR that documents the *enforcement* surface (point to the existing pytest, the existing templates tests) and makes the coverage explicit. Link it from `tasks/principles/collaborative-practice.md` under Implementation DRRs.

Check `tests/test_a11y_ci.py` and `tests/test_accessibility_templates.py` first — they may already provide the enforcement hook.

## Should-fix revisions (strongly recommended in same PR)

### S1. Add a DRR for customisable terminology

Create `tasks/design-rationale/customisable-terminology.md` with `parent_principle: collaborative-practice`. Core decision: templates must use `{{ term.client }}`, `{{ term.worker }}`, etc., never hardcoded role words. Enforcement:

- `semgrep` rule scanning `**/templates/**/*.html` for hardcoded occurrences of `client`, `participant`, `member`, `worker`, `counsellor`, `coach`, `plan`, `goal`, `pathway` outside terminology includes. Expect false positives; pair with an allowlist comment like `{# terminology-exception: reason #}`.
- `pytest` that renders a canonical template set with a non-default terminology configuration and asserts the hardcoded words do not appear.
- `codeowner` on the terminology module.

Link from `tasks/principles/collaborative-practice.md`.

### S2. Fill the enforcement gaps in the existing drafts

For each DRR, add the missing enforcement entry described. Quote-level specifics:

**`audit-log-isolation.md`** — add a pytest entry for transaction rollback:

```yaml
  - type: pytest
    file: tests/drr/test_audit_transaction_isolation.py
    description: "Audit writes persist even when the surrounding application transaction rolls back (separate connection)"
```

**`session-security.md`** — extend the Semgrep rule to cover inline event-handler attributes:

```yaml
  - type: semgrep
    rule: no-inline-scripts-without-nonce
    description: "Block <script>...</script> without a nonce, and inline event-handler attributes (onclick, onload, onsubmit, onchange, etc.) in templates"
```

**`rate-limiting-and-authentication.md`** — add a timing-safe-comparison rule:

```yaml
  - type: semgrep
    rule: timing-safe-token-comparison
    description: "In apps/auth_app/, forbid ==/!= comparisons on variables named *_token, *_assertion, or *_secret; require hmac.compare_digest"
```

**`two-person-safety-actions.md`** — add a pytest for approval-token time limits:

```yaml
  - type: pytest
    file: tests/drr/test_two_person_token_expiry.py
    description: "Approval requests for alert cancel, DV flag removal, and erasure are rejected when the approval token is older than N minutes (pin N in the DRR body)"
```

Pick N (probably 15 minutes to match lockout cadence, or 60 minutes). Put the value in the DRR body so the test can be written against a named constant.

**`demo-mode-isolation.md`** — enumerate the protected models in the Semgrep rule. Replace the `"etc."` with an explicit list. Likely candidates (verify with `Grep`): `ProgressNote`, `Client`, `Plan`, `PlanTarget`, `Goal`, `ClientFile`, `ConsentEvent`, `CorrectionRequest`, `SurveyResponse`, `PublishedReport`. Or define a mixin (`DemoScopedModel`) and have the rule check that all models inheriting from it are filtered — discuss in the DRR.

**`tech-stack-constraints.md`** — rewrite the pytest description to drop the confusing `INSTALLED_APPS` reference:

```yaml
  - type: pytest
    file: tests/drr/test_stack_constraints.py
    description: "Assert every Dockerfile starts FROM alpine or python:*-alpine; no webpack/vite/rollup/parcel config files exist; no package.json anywhere; requirements.txt is ≤60 direct deps"
```

### S3. Verify the four existing security DRRs carry the extracted invariants

The security principle hub now depends on `encryption-key-rotation.md`, `access-tiers.md`, `phipa-consent-enforcement.md`, and `no-live-api-individual-data.md` to carry invariants that used to live in `foundation-security-by-default.md`. Open each and confirm they now cover:

- **`encryption-key-rotation.md`:** startup round-trip check (app refuses to start on bad key), Fernet algorithm pin, per-tenant keys. If missing, add them.
- **`access-tiers.md`:** three-layer RBAC check (view decorator + middleware + template tag), `ClientAccessBlock` checked before role, `ClientAccessBlock` has no time-based expiry and requires Program Manager+ to clear. If any are missing, add them to the enforcement block.
- **`phipa-consent-enforcement.md`:** fail-closed behaviour on consent-check error, both helpers (`apply_consent_filter`, `check_note_consent_or_403`). Likely already covered — just verify.
- **`no-live-api-individual-data.md`:** time-limited export links (24h UUID), 10-minute delay + admin notification for 100+ record exports, exports served through Django not web server. Verify.

If any are missing, either amend those DRRs in the same PR or open a follow-up task and flag in `TODO.md`.

### S4. Reclassify untestable anti-patterns as `llm-review`

In `tasks/design-rationale/individual-data-rights.md`, two anti-patterns cannot be caught by static rules:

- *"Formal access requests required for self-viewing"* — absence of a feature; only semantic review can catch.
- *"Soft delete that leaves PII recoverable"* — requires understanding what "recoverable" means in context.

Add an `llm-review` entry to the enforcement block describing what a reviewer should look for, and remove any implication that the existing rules catch these.

### S5. Add a concrete example to `security-by-default.md`

Open `tasks/principles/security-by-default.md`. In the "Core Principle" section, add one short paragraph grounding the abstraction. Example:

> For example: the encryption key is validated on every boot; if it's missing, corrupt, or misconfigured, the application refuses to start. This makes misconfiguration a loud, immediate failure — not a silent data exposure. That pattern (fail-closed, fail-loud, architectural) is the template every security DRR in the table below follows.

Do not re-introduce prescription — one anchor, then point to the DRRs for the rules.

## Nice-to-have revisions (optional, good if time)

### N1. Document the migration-time exception in audit-log-isolation

Add a short "Migrations" subsection explaining how schema migrations run against the audit DB without violating the INSERT-only constraint (e.g., a separately-credentialed one-off DDL role used only during deploys).

### N2. Shared reference data note in demo-mode-isolation

Add one sentence to the Core Decision or to When to Revisit addressing whether shared reference data (CIDS codes, default terminologies, system templates) is copied into the demo scope or shared — and if shared, how leakage from demo creation is prevented.

### N3. Bridge note in collaborative-practice principle

In `tasks/principles/collaborative-practice.md`, add a short paragraph after "Key Judgement Calls" explaining that the nine concrete mechanisms from the original foundation (alliance rating, portal, goal builder, two-lens structure, feedback themes, strengths-based language, terminology, bilingual, accessibility) are now distributed across the Implementation DRRs list — and for each, name which DRR (or "see S1/M5 above" if not yet written). This helps a reader diffing old and new see where each idea went.

### N4. Reclassify low-value `codeowner` entries

Several DRRs list `codeowner` over broad paths. Review whether they genuinely need SME sign-off or are there defensively. `tech-stack-constraints.md` CODEOWNERS on `requirements.txt` is load-bearing; `session-security.md` CODEOWNERS on every `base*.html` may be overreach. Trim what's excessive.

## Output and verification

When you are done, the branch should have:

1. Seven revised DRRs with correct file paths and complete enforcement blocks.
2. One new DRR (`customisable-terminology.md`) and — depending on §M5 — possibly a second (`accessibility-requirements.md`).
3. One new meta-test (`tests/drr/test_drr_metadata.py`) that enforces the split.
4. One principle doc (`security-by-default.md`) with a concrete example added.
5. Optionally: the bridge note in `collaborative-practice.md`.

Before opening the PR, run:

```bash
# Verify the meta-check passes
pytest tests/drr/test_drr_metadata.py -v

# Walk every file path named in any DRR enforcement block and confirm it exists
# (Script this — grep the frontmatter across tasks/design-rationale/*.md, resolve paths, stat each.)
```

**PR target is `develop`** (per KoNote git workflow). PR description should link back to `tasks/drr-restructure-review.md` and list which `[must-fix]` / `[should-fix]` / `[nice-to-have]` items were done. If any `[must-fix]` items were skipped, say why.

**Flag GK review** by adding a TODO entry per KoNote conventions (see CLAUDE.md "Consultation Gates") — this touches evaluation principles, so GK should review the final structure before `develop` → `staging` → `main` promotion.

## What NOT to do

- Don't rewrite the principle docs substantively. They read well; the issues are in the DRRs.
- Don't split any DRR further. Seven is the agreed count; adding one for accessibility (M5 option A) and one for terminology (S1) is explicitly sanctioned by the review.
- Don't change rule *values* (30 min, 5 attempts, 15 min lockout, 60 deps, k≥5). These are assumed correct.
- Don't delete `foundation-*.md` — those stay until GK approves.
- Don't work on `develop` or `main` directly.
