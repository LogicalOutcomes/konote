# DRR Enforcement — Implementation Plan for PB

**Status:** Draft. Awaiting GK + PB approval before work starts.
**Supersedes:** [tasks/drr-enforcement-tests-prompt.md](drr-enforcement-tests-prompt.md) (keep that file for reference; the scope there is too broad for a small team).
**Tracks:** TODO.md task **DRR-REST5** (umbrella ticket).
**Prerequisite PR:** #644 must merge to `develop` first — this plan depends on the nine new DRRs landing.

---

## Why this plan differs from the original prompt

The original prompt asks for ~30 enforcement artifacts (pytest files, Semgrep rules, system checks, pre-commit hooks), one PR per artifact. A four-expert panel review (security, PHIPA compliance, nonprofit sustainability, SRE) flagged three problems with that shape:

1. **Foundation gaps.** CI only runs on PRs to `main`, not `develop`, so no feature PR currently triggers any test. Test DBs are SQLite, but half the DRR enforcements require real PostgreSQL (role grants, two-connection transaction isolation). Writing the tests without fixing the foundation produces test files that can't actually run.

2. **Control vs sentinel conflation.** Some of what the original prompt calls "enforcement" is actually *missing controls*. E.g., the `AuditLog` model overrides `.update()`/`.delete()` at the Manager level but not at the instance level — the DRR promises the instance-level behaviour. That's a missing control, not a missing test. Writing a test first for a control that doesn't exist is backwards.

3. **Maintenance-to-value ratio.** Custom Semgrep rules are brittle: they rot after template refactors, produce false positives, and get silently muted. On a small team, a minimal set of reliable sensors beats a large set of noisy ones. The panel estimates ~60% of the Semgrep rules in the original prompt are low-ROI.

The revised plan below builds ~16 PRs instead of 30+, front-loads the foundation, favours `django-system-checks` (which run at every app boot, including production) over pytest (which runs only in CI) over Semgrep/pre-commit (easy to mute), and defers fuzzy rules to a scheduled LLM review workflow.

---

## Hierarchy of enforcement mechanisms (use this to decide)

When a DRR names a specific enforcement (e.g., "add a Semgrep rule") and a cheaper mechanism would achieve the same invariant, prefer the cheaper mechanism and amend the DRR. The hierarchy, most reliable to least:

1. **Django system check** registered in `apps/<app>/apps.py::ready()`. Runs on every `manage.py` invocation including `runserver`, `migrate`, container entrypoint. App refuses to start if check fails. Can't be bypassed. **Production sensor**, not just CI.
2. **Pytest against real PostgreSQL in CI.** Catches ORM-level regressions. Requires Phase 0 infra.
3. **Pre-commit hook.** Blocks bad commits locally. Easily bypassed (`--no-verify`) — so only use for guidance rails, not security controls.
4. **Semgrep rule.** High false-positive rate for KoNote's template-heavy codebase. Reserve for template-level patterns that genuinely fit regex (alt text, inline script nonce).
5. **Scheduled LLM review.** For fuzzy rules (terminology consistency, "did this PR respect DRR X"). Weekly Haiku workflow; covered in Phase 6.

---

## Phases

Each phase is intended to land as one or a small number of PRs. Phases are sequential where marked; parallel where noted.

### Phase 0 — Foundation (sequential, blocks everything)

**PR 0.1 — CI triggers on `develop`**
- **File:** [.github/workflows/ci.yml](../.github/workflows/ci.yml), line 9
- **Change:** `branches: [main]` → `branches: [develop, main]`
- **Rationale:** Every feature PR targets `develop`. Without this change, no enforcement added by later phases will actually gate any PR. A one-line change but the single highest-leverage fix in the whole plan.
- **Acceptance:** Open a trivial PR to `develop`; confirm `CI / test` check appears.

**PR 0.2 — Postgres service in CI**
- **File:** [.github/workflows/ci.yml](../.github/workflows/ci.yml)
- **Changes:**
  - Add a `services:` block to the `test` job with `postgres:16` (two logical databases — `konote_test` and `konote_audit_test` — created via a startup script or two services).
  - Update the `env:` block: switch `DATABASE_URL` and `AUDIT_DATABASE_URL` from `sqlite:///...` to the Postgres service URLs.
  - Optional: leave SQLite as a fallback for a `sqlite-smoke` job that runs fast, keep Postgres for the main gated suite.
- **Rationale:** DRR 1.1 and DRR 2.1 require PostgreSQL role grants and concurrent connections, which SQLite cannot simulate. This unblocks Phase 3.
- **Acceptance:** Existing test suite passes against PG in CI; `pytest` discovers two distinct DB aliases; a trivial "two-database" smoke test runs.
- **Note for PB:** Confirm that `django_tenants` + PG in CI is compatible with the current test settings. The public tenant setup (see `setup_public_tenant` and memory note in CLAUDE.md) needs `localhost` registered as a secondary domain — verify this runs cleanly in the new CI environment before layering on more tests.

---

### Phase 1 — Missing controls (can run in parallel, after Phase 0)

These are production code, not tests. Each closes an actual gap where the DRR promises behaviour the codebase doesn't yet deliver.

**PR 1.1 — `AuditLog` instance overrides**
- **File:** [apps/audit/models.py](../apps/audit/models.py)
- **Change:** Add `save()` and `delete()` overrides on the `AuditLog` class:
  - `save()` raises `PermissionError` unless `self.pk is None` (i.e., allow initial INSERT, block all subsequent saves).
  - `delete()` raises `PermissionError` unconditionally.
- **Rationale:** DRR `audit-log-isolation.md` §"What this means in code" promises this. The Manager/QuerySet overrides already exist (lines 6–38); the instance-level ones are missing.
- **Acceptance:** Unit test in same PR demonstrates `instance.save()` raises on an existing record and `instance.delete()` raises always. Use SQLite — this test is ORM-level and doesn't need PG.
- **PR size:** Small (~30 lines production + test).

**PR 1.2 — Two-person approval helper (stub)**
- **New file:** `apps/auth_app/two_person.py`
- **New file:** `apps/auth_app/models.py` (extend) — `ApprovalRecord` model with fields `action`, `requester_fk`, `approver_fk`, `created_at`, `approved_at`, `expires_at`
- **Constant:** `TWO_PERSON_APPROVAL_TTL_MINUTES = 15` (at module top — the DRR pins this value)
- **Function:** `require_two_person_approval(action: str, requester: User, approver: User) -> ApprovalRecord` raising `TwoPersonViolation`, `TwoPersonRoleError`, `TwoPersonExpired` per DRR `two-person-safety-actions.md`
- **Migration:** for `ApprovalRecord`
- **Rationale:** DRR names three protected actions (alert cancel, DV flag removal, participant erasure). Until the helper exists, the tests in Phase 3 can't be written, *and* the current codebase may be running these as one-person actions. This PR is a control, not a sentinel — so the helper function can be called but doesn't need to be wired into the three endpoints yet (that's Phase 3).
- **Acceptance:** Helper exists, unit tests cover the three exception paths, migration applied. Do NOT wire it into `events/views.py`, `clients/dv_views.py`, `clients/erasure_views.py` in this PR — that's Phase 3 when the Semgrep/pytest layer lands with it.
- **Note for PB:** If any of the three endpoints already does two-person enforcement via a different mechanism, flag that rather than duplicating — may want to refactor the existing code into this helper. Flag to GK before changing existing safety behaviour.

**PR 1.3 — Audit DB role grants (runbook change, not code)**
- **File:** [konote-ops](konote-ops) repo — `deployment/runbook.md` + deploy script (if applicable)
- **Change:** Document the SQL to create the `konote_audit_app` role with `INSERT`-only grants on audit tables, plus a separate `konote_audit_migrate` role with `CREATE`/`ALTER` (not `UPDATE`/`DELETE`) used only during deploys. Wire into deploy script so new VPS bootstraps the roles correctly.
- **Rationale:** The real security control. DRR says "running `UPDATE audit_log SET ...` through psql with that role must fail at the database level." That has to be true in *production*, not just CI. Without this, the system check in Phase 2 has nothing to verify against.
- **Acceptance:** Runbook documents role creation; deploy script applies it; manual verification on dev VPS that `psql` as `konote_audit_app` rejects `UPDATE audit_log SET ...`.
- **Note for PB:** This is two DBs — the existing `audit` database may not yet have role-separation at all. Check current state on the VPS first. If roles don't exist, Phase 2's system check would fail every boot — need to ship 1.3 before 2.1.

---

### Phase 2 — System checks (sequential within the phase, run after Phase 1)

System checks give the most value per line of code because they run on every app start, including production container boot. An app with a misconfigured audit DB role or weak session cookies literally cannot start.

**PR 2.1 — `audit_db_role_insert_only` check**
- **File:** `apps/audit/checks.py` (extend existing file)
- **Registration:** `apps/audit/apps.py::ready()`
- **Behaviour:** Connect as the audit DB role (via `DATABASES["audit"]`). Open a transaction, attempt `UPDATE audit_log SET ... WHERE 1=0` (no-op but parses as UPDATE). If the statement does not raise `InsufficientPrivilege`, emit `Error` severity with id `audit.E001`. Rollback. Repeat for `DELETE`.
- **Gotcha:** The check must not run when the audit DB is unavailable (e.g., during `makemigrations` with `--check`) — degrade to `Warning` if the connection itself fails, so local dev without audit DB doesn't explode.
- **Acceptance:** Unit test mocks a permissive role config, asserts check emits Error; integration test with correctly-configured PG role asserts check passes.
- **Note for PB:** This is the most important single artifact in the whole plan. If the audit role is misconfigured in production, everything downstream (audit immutability, PHIPA evidence) is undermined. Make sure the check runs in the Docker entrypoint before the app binds to port 8000.

**PR 2.2 — `session_security_defaults` check**
- **File:** `konote/checks.py` (new) or extend `apps/admin_settings/checks.py`
- **Registration:** `konote/apps.py::ready()` or equivalent
- **Assertions** (from DRR `session-security.md`):
  - `settings.SESSION_COOKIE_AGE <= 1800`
  - `settings.SESSION_COOKIE_HTTPONLY is True`
  - `settings.SESSION_COOKIE_SECURE is True` when `settings.DEBUG is False`
  - `settings.SESSION_COOKIE_SAMESITE in {"Lax", "Strict"}`
  - `"signed_cookies" not in settings.SESSION_ENGINE`
- **Severity:** Error on any failure.
- **Acceptance:** Unit tests for each branch (assert-fail when misconfigured, assert-pass when correct).

**PR 2.3 — `auth_hardening` check**
- **File:** `apps/auth_app/checks.py` (new or extend)
- **Registration:** `apps/auth_app/apps.py::ready()`
- **Assertions** (from DRR `rate-limiting-and-authentication.md`):
  - `settings.PASSWORD_HASHERS[0]` ends with `Argon2PasswordHasher`
  - `"django_ratelimit" in settings.INSTALLED_APPS`
  - Introspect `apps/auth_app/views.py::login_view` carries `@ratelimit(key="ip", rate="5/m", ...)`
  - Introspect same module for `_get_lockout_key` and `_increment_lockout_counter` (if missing, emit Error)
  - Introspect password-reset views carry `@ratelimit(rate="10/m")`
- **Note for PB:** Introspection via `ast` module is reliable but fragile if someone renames the functions. Add a comment in the check explaining which symbols it expects so future refactors surface the link.

**PR 2.4 — `consent_event_append_only` check**
- **File:** `apps/clients/checks.py` (new)
- **Registration:** `apps/clients/apps.py::ready()`
- **Assertions** (from DRR `individual-data-rights.md`):
  - `ConsentEvent.save` is overridden (inspect class dict)
  - Application DB role has no `DELETE` grant on `consent_event` table (same pattern as 2.1 — try a `DELETE WHERE 1=0`, expect `InsufficientPrivilege`)
- **Note for PB:** If `ConsentEvent` doesn't currently override `save()`, this check fails. Adding the override is a Phase 1-style control fix — see if it needs its own mini-PR before this check lands. Flag to GK before changing consent-event write semantics (she reviews data-integrity rules).

---

### Phase 3 — Pytest sensors (parallel with Phase 2 once Phase 0 done)

These are the core invariant tests. Each covers one DRR. Land after the corresponding Phase 1 control PR.

**PR 3.1 — `tests/drr/test_audit_log_immutability.py`**
- **Covers:** DRR 1.1, instance-level overrides landed in PR 1.1
- **Tests:**
  - Create AuditLog via `.objects.using("audit").create(...)`, reload, mutate, save → asserts `PermissionError`
  - Same for `.delete()`
  - Raw SQL path: open connection as audit role, attempt `UPDATE`, assert DB-level rejection
- **Bundle with PR 1.1** if reviewer capacity allows (control + sensor together is a coherent unit).

**PR 3.2 — `tests/drr/test_audit_transaction_isolation.py`**
- **Covers:** DRR 1.1 transaction-isolation invariant
- **Requires:** Phase 0.2 (real PG in CI)
- **Test shape:**
  - Open `transaction.atomic()` on `default`
  - Inside that block, `AuditLog.objects.using("audit").create(...)`
  - Raise to force rollback of `default` transaction
  - From a *fresh* connection (not the rolled-back one), re-query audit table — assert the record is present
- **Note for PB:** This test proves the audit connection is genuinely separate. To verify the test actually tests something, deliberately wire the audit connection to `default` (bad config), confirm the test fails loudly, revert.

**PR 3.3 — `tests/drr/test_session_security.py`**
- **Covers:** DRR `session-security.md`
- **Test shape:**
  - Using Django test `Client`, log in and fetch a protected page
  - Assert `Set-Cookie` carries `HttpOnly`, `Secure` (when not DEBUG), `SameSite=Lax`
  - Assert response has `Content-Security-Policy` with a nonce, and the rendered `<script>` in body uses the same nonce
  - Using `freezegun`, advance time past `SESSION_COOKIE_AGE`, assert session expired

**PR 3.4 — `tests/drr/test_rate_limiting.py`**
- **Covers:** DRR `rate-limiting-and-authentication.md`
- **Sub-tests:**
  - Login rate limit (6 attempts in 60s → 429)
  - Account lockout (5 bad + 1 correct still fails; after clock advance, correct succeeds)
  - Password reset limit (11 attempts in 60s → 429)
  - Timing-safe comparison unit test (`hmac.compare_digest` used for token-like variables)
- **Important:** Do NOT disable rate-limiting in the test env. That's what you're testing.
- **Note for PB:** Depending on how `django-ratelimit` caches, `freezegun` may not advance the lockout TTL cleanly. If it doesn't, consider a cache backend for tests that has a settable "now" — or shorten the TTL in test settings and actually wait (ugly but honest). Do not `cache.delete(lockout_key)` in the test to fake expiry — that defeats the test.

**PR 3.5 — `tests/drr/test_individual_rights.py`**
- **Covers:** DRR `individual-data-rights.md`
- **Sub-tests (a)–(e)** per the original prompt §2.1 — correction as amendment, consent immutability, consent no-delete, erasure requires two users, erasure strips PII.
- **Depends on:** PR 1.2 (two-person helper) for sub-test (d)

**PR 3.6 — `tests/drr/test_two_person_workflows.py` + `test_two_person_token_expiry.py`**
- **Covers:** DRR `two-person-safety-actions.md`
- **Depends on:** PR 1.2 (helper), plus wiring the helper into the three protected endpoints (`events/views.py`, `clients/dv_views.py`, `clients/erasure_views.py` / `erasure.py`)
- **Sub-tests per protected action:** single-user fails, same-user-approver fails, distinct valid approver succeeds with audit record; plus 15-minute expiry test.
- **Note for PB:** Wiring the helper into three existing endpoints is the riskiest part of this PR — each endpoint may have its own state machine that needs a waiting-for-approver state. Consider one PR per endpoint (so three PRs), plus a final PR with the tests covering all three. Flag to GK before changing erasure or DV flag workflows — those are policy-sensitive.

---

### Phase 4 — Amend DRRs and promote to Decided (PB + GK collaboration)

Once Phases 0–3 are in for a DRR, it's safe to:

1. Flip the relevant enforcement entries in the DRR frontmatter to `status: implemented`
2. If the DRR prescribes a Semgrep rule that Phase 5 drops, amend the DRR to remove the Semgrep entry and add a sentence: "Invariant enforced via <system check / pytest>; implementation mechanism may evolve."
3. Change DRR `status:` from `Draft - awaiting GK review` to `Decided`
4. Bump the "Change history" entry in `tasks/design-rationale/README.md`

**PR 4.x — One per DRR promoted.** Keep these tiny (frontmatter + README change) so GK can sign off without wading through code.

**GK consultation gate:** Each promotion needs GK's OK. Security + PHIPA DRRs have policy implications — don't promote without her sign-off, even if all tests are green.

---

### Phase 5 — Narrow Semgrep set (single PR)

After the panel review, drop Semgrep rules that duplicate system checks or pytests. Keep only the two template-level rules that genuinely fit regex:

- `.semgrep/no-image-without-alt.yml`
- `.semgrep/no-inline-scripts-without-nonce.yml`

Wire into `.github/workflows/semgrep.yml` running on every PR. Before merging, run against the whole repo and confirm zero existing violations (or, if any exist, fix them in the same PR or flag in TODO.md).

**Drop from the original prompt:**
- `timing-safe-token-comparison` — covered by PR 3.4 sub-test (d)
- `two-person-action-requires-approver` — fragile (depends on marker comments); covered by PR 3.6 + the helper's existence
- `demo-flag-must-filter-queries` — covered by PR 3.7 `test_demo_isolation.py` (add if needed) + schema-sync test
- `no-button-without-accessible-text` — existing `tests/test_accessibility_templates.py` likely covers; confirm before dropping
- `no-hardcoded-terminology-words` — move to Phase 6 LLM review (fuzzy rule)

**Note for PB:** If you think any of the dropped rules *are* worth keeping, push back. The panel's call was "cost of maintenance > value on a small team" — not "these are bad rules."

---

### Phase 6 — Scheduled LLM review (single PR)

**New file:** `.github/workflows/drr-compliance-review.yml`
- Schedule: weekly on `develop`, plus manual dispatch
- Job: spin up a workflow that uses the Anthropic Claude Haiku 4.5 API (or Sonnet Haiku, whichever is cheapest at the time — Haiku 4.5 is the current recommendation) to review the last week's merged PRs against the DRR corpus
- Output: open a GitHub issue if any PR appears to violate a DRR; comment on individual PRs if specific files seem suspect
- **Cost ceiling:** Set a per-run token cap so a runaway prompt can't burn budget

**Rules well-suited for LLM review:**
- Terminology consistency (are new template strings using `{{ term.client }}` / `{{ term.worker }}` etc.)
- "Did this PR respect the spirit of DRR X" — freeform architectural check
- Anti-patterns named in DRR tables but too fuzzy for regex

**Note for PB:** Gillian uses Kilocode for interactive work; for CI, a plain GitHub Actions workflow calling the Anthropic API directly is simpler than a Kilocode-based approach. Store `ANTHROPIC_API_KEY` in repo secrets.

---

### Phase 7 — Pre-commit hooks (optional, land when convenient)

Per panel recommendation, pre-commit is lowest-value. Only land if the friction cost for contributors is clearly lower than the signal benefit.

**Candidates:**
- `forbid-npm-package-json.sh` — blocks `package.json`, `package-lock.json`, `yarn.lock`, `node_modules/`. This is one shell script, zero false positives, genuinely useful as a stack guardrail. Keep.
- `dependency-ceiling.sh` — counts `requirements.txt` lines; if > 60, requires `[deps-approved]` in commit and a `CHANGELOG.md` change. Nicer idea than execution — the commit-marker convention adds friction for marginal value. **Defer** unless a near-breach prompts it.

Land the first, defer the second. Wire via `.pre-commit-config.yaml`. Document `pre-commit install` in the README or `scripts/setup.sh`.

---

## Open questions for Gillian / GK

Flag these before starting implementation:

1. **DRR governance change.** Phase 4 splits each DRR's "invariant" from its "current mechanism." Does GK need to approve this framing change to the DRR template itself? It touches Foundation: Security by Default's interpretation.

2. **DRR prescriptiveness.** Original prompt's ground rule #3 says "If the codebase diverges from the DRR, raise the discrepancy — fix the code or amend the DRR first." Phase 1 finds three such divergences (AuditLog instance overrides, two-person helper, audit DB role separation). Is it OK for PB to land these as "fix the code" without round-tripping to GK for each, or does she want to review?

3. **Consent event semantics.** Phase 2.4 may require adding `save()` override to `ConsentEvent`. That changes write semantics for a legally-sensitive model. Explicit GK approval before the PR?

4. **Two-person enforcement in live code.** Phase 3.6 wires `require_two_person_approval()` into three existing endpoints. At least one (DV flag removal) may currently be a one-person action. Confirm with GK before changing the workflow.

5. **Scheduled Haiku cost.** Phase 6 will cost roughly $1–5/week depending on PR volume. Acceptable?

---

## Order of operations recap

```
Phase 0.1 (CI on develop)          ← 1-line PR, ship first
Phase 0.2 (Postgres in CI)         ← unblocks PG-dependent tests
  ↓
Phase 1.1, 1.2, 1.3 (parallel)     ← missing controls
  ↓
Phase 2.1–2.4 (system checks)      ← highest-value sensors
Phase 3.1–3.6 (pytests)            ← in parallel with Phase 2 per DRR
  ↓
Phase 4 (amend + promote DRRs)     ← one per DRR, tiny PRs
Phase 5 (narrow Semgrep)           ← after Phases 2+3 are stable
Phase 6 (LLM review)               ← last, low priority
Phase 7.1 (npm/node pre-commit)    ← whenever
```

---

## Things to watch for / anti-patterns

- **Don't land a test for a control that doesn't exist.** If `AuditLog.save()` override isn't in place, don't write the test. Add the override first.
- **Don't skip tests.** `pytest.mark.skip` with no `status: planned` reason violates the DRR meta-check contract.
- **Don't mock the audit DB.** The whole point is connection isolation. Mocks hide the failure modes.
- **Don't weaken DRRs to match broken code.** If Phase 3.6 finds DV flag removal is one-person today, fix the code. Don't amend the DRR to say "DV flag removal is one-person."
- **Don't promote Draft → Decided without GK sign-off.** Even if every test is green.

---

## Handoff notes for PB

- This plan was drafted by Claude with a four-expert panel review (Security, PHIPA Compliance, Nonprofit Sustainability, SRE). Full panel transcript available on request — ping Gillian.
- If you disagree with any phase or want to reorder, flag before starting. The plan is a proposal, not a decree.
- TODO.md entry DRR-REST5 is the umbrella ticket. Create sub-tickets per PR if helpful (e.g., DRR-REST5-P0-1 for Phase 0.1).
- Gillian will handle DRR frontmatter changes (Phase 4) once you flag a DRR's enforcement is in place — that's a policy-layer edit she can own.
- Estimated calendar time at 1 dev-equivalent: 4–8 weeks depending on how much of Phase 1 surfaces existing code changes.
- Kill-switch: if Phase 2 system checks reveal that production is already misconfigured (e.g., audit role has UPDATE grants today), stop the plan and escalate. That's a live incident, not a roadmap item.
