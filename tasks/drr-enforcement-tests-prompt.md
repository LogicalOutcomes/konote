# Prompt: Build the enforcement tests named by the new DRRs

## Context

PR #644 landed nine DRRs in the new prescriptive format (`tasks/design-rationale/`). Each DRR declares an `enforcement:` block listing the pytest files, Django system checks, Semgrep rules, pre-commit hooks, and CODEOWNERS entries that are supposed to catch violations. Most of those enforcement mechanisms **do not exist yet** — the DRRs describe the rule; this PR builds the rule.

Until this work is done, the new DRRs are architecturally sound but operationally unenforced. They remain in `Status: Draft` until each has at least one real enforcement mechanism wired up.

Read these before starting:

- [tasks/design-rationale/README.md](design-rationale/README.md) — the DRR directory and the `status: implemented|planned` convention.
- [tests/drr/test_drr_metadata.py](../tests/drr/test_drr_metadata.py) — already-shipped meta-check. It parametrizes over every DRR and asserts that any pytest/codeowner path marked `status: implemented` actually resolves. **When you finish each test below, add `status: implemented` to the corresponding enforcement entry in the DRR front-matter** — that locks the entry against future path regressions.
- [tasks/drr-restructure-review.md](drr-restructure-review.md) and [tasks/drr-restructure-revision-prompt.md](drr-restructure-revision-prompt.md) for the why.

## Non-negotiable ground rules

1. **Each enforcement mechanism lands in its own PR.** Ten tests in one PR is a rubber-stamp review. Small PRs per test keep the reviewer honest.
2. **When you finish a test, mark it `status: implemented` in the DRR frontmatter in the same commit.** The meta-check (`tests/drr/test_drr_metadata.py::test_drr_enforcement_paths_exist`) will then enforce the path — so a future rename breaks CI loudly.
3. **Do not invent behaviour.** If a DRR specifies a value (30 minutes, 5 attempts, 60 deps, 15 minutes approval TTL), use that exact value. If the codebase diverges from the DRR, raise the discrepancy before writing the test — fix the code or amend the DRR first.
4. **Use real DB + Playwright where the DRR implies it** (audit transaction rollback needs two real connections; session cookie flags need a real HTTP response). Mocks hide the failure modes these tests are meant to catch. See `conftest.py` and `tests/test_a11y_ci.py` for the existing real-browser/real-DB pattern.
5. **No skips without a `status: planned` reason.** If the test cannot be implemented today (e.g., waiting on a helper function to be created), raise the blocker — do not ship a test that skips silently.
6. **Follow KoNote git workflow** (see `CLAUDE.md`): feature branch off `develop`, PR to `develop`, merge with `gh pr merge --merge` (never squash), pull develop into main repo + worktree after merge.

## The enforcement surface to build

Each section below is scoped to one DRR. Work through them in the suggested priority (security DRRs first — the security engineer on the review panel flagged these as higher risk if left as IOUs). For each, the section names:

- **What:** the enforcement mechanism (pytest / Semgrep rule / system check / pre-commit hook)
- **Where:** the file path declared in the DRR frontmatter
- **Shape:** what the test/rule must assert, grounded in the specific values the DRR pins
- **Verification:** how you know it works (what test output or dry-run proves it fails on the right input)

### Priority 1 — Security DRRs (highest blast radius)

#### 1.1 `audit-log-isolation.md` — two pytests + one system check

**System check** `audit_db_role_insert_only` (declared in DRR; add to `apps/audit/checks.py`, register via `apps/audit/apps.py`'s `ready()`).

- Connect as the audit DB role (settings: `DATABASES["audit"]`).
- Attempt a dry-run `UPDATE` against an audit table in a transaction that is immediately rolled back.
- If the UPDATE succeeds (did not raise `InsufficientPrivilege` or equivalent), return `Error` severity with id `audit.E001`.
- The check must also confirm no `DELETE` grant.
- Run on every app boot.

**Pytest** `tests/drr/test_audit_log_immutability.py`

- Create an `AuditLog` record via `AuditLog.objects.using("audit").create(...)`.
- Reload by primary key, mutate any field, call `.save(using="audit")`.
- Assert this raises `PermissionError` (the model's overridden `save()` should raise for any save that is not the initial INSERT).
- Same pattern for `.delete()`.
- Also: exercise the path where an attempt is made via raw SQL through the audit connection; assert the database rejects it.

**Pytest** `tests/drr/test_audit_transaction_isolation.py`

- Open an application-side transaction on `default`.
- From inside that transaction, write to `AuditLog.objects.using("audit")`.
- Raise an exception to force rollback of the application transaction.
- Re-read the audit table from a fresh connection; assert the audit record is present.
- This proves the audit writes use a separate connection — if they don't, the audit record rolls back with the application.

**Verification.** Intentionally wire the audit connection to the `default` database (bad config). The transaction-isolation test must fail with a clear message. Revert the misconfiguration, the test must pass.

#### 1.2 `session-security.md` — one pytest + one system check + one Semgrep rule

**System check** `session_security_defaults` in `konote/checks.py` or `apps/admin_settings/checks.py`.

- Assert `settings.SESSION_COOKIE_AGE <= 1800`.
- Assert `settings.SESSION_COOKIE_HTTPONLY is True`.
- Assert `settings.SESSION_COOKIE_SECURE is True` when `settings.DEBUG is False`.
- Assert `settings.SESSION_COOKIE_SAMESITE in {"Lax", "Strict"}` (not `"None"`).
- Assert `settings.SESSION_ENGINE` does not contain `signed_cookies`.
- Return `Error` severity on any failure; the app must refuse to start.

**Pytest** `tests/drr/test_session_security.py`

- Using `Client()` (or `APIClient`), log in a test user and fetch a protected page.
- Assert the response sets a session cookie and that the `Set-Cookie` header carries `HttpOnly`, `Secure` (when not DEBUG), and `SameSite=Lax` (or stricter).
- Assert the response includes a `Content-Security-Policy` header and that it names a nonce (`'nonce-<value>'`).
- Assert a rendered `<script>` tag in the body carries `nonce="<same value>"`.
- Then fake inactivity past `SESSION_COOKIE_AGE`: advance `freezegun` (already in requirements-test.txt), hit a protected endpoint, assert redirect to login.

**Semgrep rule** `no-inline-scripts-without-nonce` in `.semgrep/no-inline-scripts-without-nonce.yml` (create the `.semgrep/` directory).

- Target: `**/templates/**/*.html`.
- Pattern 1: `<script>...</script>` and `<script>...` without `nonce=` attribute.
- Pattern 2: any of `onclick=`, `onload=`, `onsubmit=`, `onchange=`, `onerror=`, `onmouseover=`, `onmouseout=`, `onfocus=`, `onblur=`, `onkeydown=`, `onkeyup=`, `onkeypress=` as an element attribute (not inside a `{{ }}` expression).
- Allow: `<script src="..." nonce="..."></script>`.
- Severity: ERROR.
- Wire into CI (see §6 on wiring below).

**Verification.** Add a deliberately-bad template under `tests/fixtures/a11y_negatives/` with an `onclick=` and run Semgrep locally — must fail. Remove, re-run, must pass.

#### 1.3 `rate-limiting-and-authentication.md` — one pytest + one system check + one Semgrep rule

**System check** `auth_hardening` in `apps/auth_app/checks.py`.

- Assert `settings.PASSWORD_HASHERS[0]` ends with `Argon2PasswordHasher`.
- Assert `"django_ratelimit"` is in `settings.INSTALLED_APPS`.
- Introspect `apps/auth_app/views.py::login_view`: must carry a `@ratelimit` decorator with `key="ip"` and `rate="5/m"`.
- Introspect same module for the lockout helpers (`_get_lockout_key`, `_increment_lockout_counter`); fail if either is missing.
- Assert the password-reset views carry `@ratelimit(..., rate="10/m", ...)` per the DRR.

**Pytest** `tests/drr/test_rate_limiting.py`

- **(a) Rate limiting.** Use `Client()` to POST 6 login attempts to `/auth/login/` with wrong credentials, each within 60 seconds. Assert the 6th returns HTTP 429.
- **(b) Account lockout.** Submit 5 bad logins for the same username, then a 6th with the correct password. Assert the 6th still fails. Advance the cache clock 15 minutes (via `freezegun` + clearing the lockout key is *not* permitted — prove the expiry works by waiting). Assert the next correct login succeeds.
- **(c) Password reset rate limit.** POST 11 requests to the password-reset endpoint within 60 seconds. Assert the 11th returns 429.
- **(d) Timing-safe comparison.** Write a unit test that instantiates the token-comparison helper (wherever the DRR's timing-safe rule applies — see §1.3 Semgrep) and confirm it uses `hmac.compare_digest`.

**Semgrep rule** `timing-safe-token-comparison` in `.semgrep/timing-safe-token-comparison.yml`.

- Target: `apps/auth_app/**/*.py`.
- Pattern: `$VAR == $OTHER` where `$VAR` is a variable whose name matches `*_token`, `*_assertion`, or `*_secret` (and same for `!=`).
- Exception: explicit `# noqa: timing-safe` comment on the line.
- Severity: ERROR.

**Verification.** Add a deliberately-bad line in a test fixture: `if user_token == expected_token:`. Semgrep must flag it. Replace with `hmac.compare_digest`. Must pass.

#### 1.4 `two-person-safety-actions.md` — two pytests + one Semgrep rule + one helper

**Helper to create:** `apps/auth_app/two_person.py` (new module).

- Function `require_two_person_approval(action: str, requester: User, approver: User) -> ApprovalRecord`.
- Raises `TwoPersonViolation` if `requester.id == approver.id`.
- Raises `TwoPersonRoleError` if the `approver`'s role is below the minimum named for `action` (see table in DRR; PM+ for alert-cancel and DV-flag-removal, Admin for erasure).
- Raises `TwoPersonExpired` if the approval request is older than `TWO_PERSON_APPROVAL_TTL_MINUTES = 15`.
- Writes an `AuditLog` entry with both `requester.id` and `approver.id` to the audit DB.
- Returns the created `ApprovalRecord` on success.
- Model: add `apps/auth_app/models.py::ApprovalRecord` (or a dedicated `apps/auth_app/two_person_models.py`) with fields `action`, `requester_fk`, `approver_fk`, `created_at`, `approved_at`, `expires_at = created_at + 15 min`.

**Pytest** `tests/drr/test_two_person_workflows.py`

For each of the three protected actions (alert cancel, DV flag removal, participant erasure):

- **(a) Single-user attempt fails.** Call the completion endpoint as the requester only; assert the action does not complete (redirect to a "waiting for approver" state or HTTP 403 per the endpoint's existing behaviour).
- **(b) Same-user approver fails.** Create an approval request where `requester.id == approver.id`; call the completion endpoint; assert `TwoPersonViolation`.
- **(c) Distinct valid approver succeeds.** Create the request, approve with a different user of correct role, complete the action. Assert the action state updated AND an audit record was written with both user IDs.

**Pytest** `tests/drr/test_two_person_token_expiry.py`

- Create an approval request for each of the three protected actions.
- Advance `freezegun` clock past 15 minutes from creation.
- Attempt to complete with a valid approver.
- Assert `TwoPersonExpired` is raised AND no state mutation occurred AND no success audit record was written.

**Semgrep rule** `two-person-action-requires-approver` in `.semgrep/two-person-action-requires-approver.yml`.

- Target paths: `apps/events/views.py` (alert functions), `apps/clients/dv_views.py` (DV flag removal), `apps/clients/erasure_views.py`, `apps/clients/erasure.py` (+ any future view under a `# two-person: <action>` comment).
- Pattern: within a function marked by `# two-person: <action>` (a marker comment to be placed on the def line), if there is no call to `require_two_person_approval(...)` before the state-mutation (`.save()` or `.delete()` on a domain model), flag the function.
- Severity: ERROR.
- This requires `# two-person:` marker comments to be added to the three existing completion endpoints as part of the helper-creation PR.

**Verification.** Write a deliberately-bad test fixture that performs a state-mutation without the helper; Semgrep must flag it. Remove, re-run, must pass.

#### 1.5 `demo-mode-isolation.md` — one pytest + one Semgrep rule

**Pytest** `tests/drr/test_demo_isolation.py`

- **(a) Demo → real via direct URL.** Log in as a demo user. Look up a real `ClientFile` PK (not owned by the demo user's agency). GET `/participants/<pk>/`. Assert HTTP 404 (not 403 — 403 leaks existence).
- **(b) Real → demo via direct URL.** Log in as a real user. Look up a demo `ClientFile` PK. GET `/participants/<pk>/`. Assert HTTP 404.
- **(c) Demo → settings POST.** Log in as a demo user. POST to `/admin/settings/<agency>/terminology/`. Assert HTTP 403.
- **(d) Enumerated-model coverage.** For every model listed in the DRR's `demo-flag-must-filter-queries` enumeration (`ClientFile`, `ConsentEvent`, `ClientDetailValue`, `ClientAccessBlock`, `ProgressNote`, `ProgressNoteTarget`, `PlanTarget`, `PlanTargetRevision`, `SurveyAssignment`, `SurveyResponse`, `SurveyAnswer`, `CorrectionRequest`, `StaffPortalNote`, `ClientResourceLink`, `Circle`), assert that either the model defines an `is_demo` field OR traverses `client_file__is_demo` / `created_by__is_demo`. If a listed model fails this, the DRR list is stale — fail loud.

**Semgrep rule** `demo-flag-must-filter-queries` in `.semgrep/demo-flag-must-filter-queries.yml`.

- Target: all `apps/**/*.py` excluding the allowlist (`apps/admin_settings/demo_engine.py`, `apps/admin_settings/management/commands/seed_demo_data.py`).
- Pattern: `<MODEL>.objects.<method>(...)` or `<MODEL>.objects` chain, where `<MODEL>` is one of the enumerated demo-scoped models.
- Require the chain to contain one of `.filter(is_demo=...)`, `.filter(client_file__is_demo=...)`, `.filter(created_by__is_demo=...)`, or `.using_demo_filter(...)` (helper to be created).
- Severity: ERROR.
- The rule must accept a `# noqa: demo-filter` comment with a reason when the queryset is intentionally unscoped (e.g., admin-only bulk export).

**Verification.** Find one existing queryset in the allowlist path and copy it to a non-allowlist module; Semgrep must flag. Revert.

### Priority 2 — Data-rights and privacy DRR

#### 2.1 `individual-data-rights.md` — one pytest + one system check

**System check** `consent_event_append_only` in `apps/clients/checks.py`.

- Assert the `ConsentEvent` model class has overridden `save()` to raise `PermissionError` on any save of a previously-persisted instance.
- Assert the application DB role has no `DELETE` grant on the `consent_event` table (connect + `pg_has_role` / `has_table_privilege` lookup).

**Pytest** `tests/drr/test_individual_rights.py`

- **(a) Correction as amendment.** Create a `ProgressNote`; file a `CorrectionRequest` against it; apply the correction through the existing workflow; assert the original `ProgressNote` row is unchanged AND an amendment record linked to the original exists.
- **(b) Consent immutability.** Create a `ConsentEvent`. Mutate a field. Call `.save()`. Assert `PermissionError`.
- **(c) Consent no-delete.** Attempt `consent_event.delete()`. Assert `PermissionError`.
- **(d) Erasure requires two users.** Call the erasure endpoint as a single Program Manager. Assert the action routes to the two-person workflow and does not complete.
- **(e) Erasure strips PII.** Complete the erasure with Admin approval. Re-fetch the client record and every related model in the DRR's enumerated list; assert no field contains reconstructable identity data (name, DOB, contact, etc.). Assert the anonymised aggregate row is still present for statistics.

The two `llm-review` entries in the DRR do not require test files — they're reviewer instructions. No action here beyond keeping the wording current.

### Priority 3 — Demo mode (covered under 1.5) and UX DRRs

#### 3.1 `accessibility-requirements.md` — two Semgrep rules (pytests already exist)

The three pytest files (`tests/test_a11y_ci.py`, `tests/test_accessibility_templates.py`, `tests/test_blocker_a11y.py`) are already shipped and marked `status: implemented`. Only the Semgrep rules need building.

**Semgrep rule** `no-image-without-alt` in `.semgrep/no-image-without-alt.yml`.

- Target: `**/templates/**/*.html`.
- Pattern: `<img ...>` without an `alt=` attribute.
- Allow: `<img alt=""...>` (explicit empty alt for decorative images).
- Allow: a `{# a11y-exception: <reason> #}` comment on the preceding line.
- Severity: ERROR.

**Semgrep rule** `no-button-without-accessible-text` in `.semgrep/no-button-without-accessible-text.yml`.

- Target: `**/templates/**/*.html`.
- Pattern 1: `<button>...</button>` with no text content (only whitespace or element-only) and no `aria-label` or `aria-labelledby` attribute.
- Pattern 2: `<a role="button" ...>...</a>` or `<a hx-post|hx-get|hx-put|hx-delete=...>...</a>` with empty text and no `aria-label`.
- Severity: ERROR.

**Verification.** Add a bad fixture (`<img src="x.png">` and `<button></button>`). Both rules must flag. Remove, must pass.

#### 3.2 `customisable-terminology.md` — one pytest + one Semgrep rule

**Pytest** `tests/drr/test_terminology_substitution.py`

- Build a non-default terminology configuration: `term.client = "member"`, `term.worker = "coach"`, `term.plan = "pathway"`, `term.goal = "milestone"`.
- Using Django's test client, render the canonical page set: login, dashboard (`/`), participant list (`/participants/`), a single participant detail, note detail (you'll need fixtures to seed these), goal detail, portal dashboard (`/my/`), portal goals (`/my/goals/`).
- For each response body, assert the default words (`client`, `clients`, `participant`, `participants`, `member` in some cases, `worker`, `counsellor`, `plan`, `goal`, `pathway`) do not appear as standalone words — use word-boundary regex, ignore substrings (e.g., `Clientele` should not be flagged, but `Client` should).
- Scope: assert only the terminology-swapped words appear, i.e., `member`, `coach`, `pathway`, `milestone`.

**Semgrep rule** `no-hardcoded-terminology-words` in `.semgrep/no-hardcoded-terminology-words.yml`.

- Target: `**/templates/**/*.html`.
- Pattern: any of the forbidden words appearing as rendered text (outside `{{ }}` / `{% %}` / HTML comments). Case-insensitive. Match on word boundaries.
- Allow: a `{# terminology-exception: <reason> #}` comment on the preceding line.
- Severity: WARNING (not ERROR — terminology is a long-standing gradual cleanup; upgrade to ERROR once the existing corpus is clean).

### Priority 4 — Tech stack constraints

#### 4.1 `tech-stack-constraints.md` — one pytest + two pre-commit hooks

**Pre-commit hook** `forbid-npm-package-json` in `.pre-commit-hooks/forbid-npm-package-json.sh` (or `.pre-commit-config.yaml` local hook).

- Runs on every commit.
- Scans the staged files for any name matching `package.json`, `package-lock.json`, `yarn.lock`, or any directory named `node_modules`.
- Exits non-zero on any match.

**Pre-commit hook** `dependency-ceiling` in `.pre-commit-hooks/dependency-ceiling.sh`.

- Counts non-blank, non-comment lines in `requirements.txt`.
- If `> 60`:
  - Check `git log -1 --format=%B` for the marker `[deps-approved]`.
  - Check that `CHANGELOG.md` was modified in the same commit.
  - If either missing, exit non-zero with an explanation.

**Pytest** `tests/drr/test_stack_constraints.py`

- Glob the repo for any file named `Dockerfile*`; for each, read the `FROM` line; assert it matches `alpine` or `python:*-alpine`.
- Glob for `webpack.config.*`, `vite.config.*`, `rollup.config.*`, `parcel.config.*` anywhere under the repo; assert zero results.
- Glob for any `package.json` or `node_modules/` — assert zero results.
- Re-count `requirements.txt` non-blank non-comment lines; assert ≤ 60 (belt-and-braces with the pre-commit hook).

**Verification.** Create a bogus `package.json` at the repo root; the hook must block the commit. Remove, must pass. Same for an `ALPINE` miss in a Dockerfile (use `FROM debian:bookworm`).

### Priority 5 — Meta-hygiene (small, do whenever)

#### 5.1 Demo-mode schema-sync check (mentioned in demo-mode-isolation.md)

**Pytest** `tests/drr/test_demo_model_coverage.py`

- Inspect Django's app registry for every concrete model with an `is_demo` BooleanField OR a FK to a model that has one.
- Compare that set against the enumerated list in `demo-mode-isolation.md`'s Semgrep-rule description.
- If the lists diverge, fail with the diff so the DRR can be updated.

This closes the "new model added, DRR list becomes stale" hole that the revision prompt's S2 asked for. Not in the original DRR — the revision explicitly softened the claim — but once this pytest exists, the DRR language can be tightened to promise it.

## Wiring into CI

Tests run under the existing pytest config (`pytest.ini`). Pre-commit hooks go in `.pre-commit-config.yaml` (create it — the DRR already references it). Semgrep rules go in a new top-level `.semgrep/` directory; add a GitHub Actions workflow (`.github/workflows/semgrep.yml`) that runs `semgrep --config .semgrep/ --error` on every PR. (Pattern: see the existing `.github/workflows/` for how other checks are wired.)

Pre-commit hooks must also be installed by default for new contributors — add a `make install-dev-hooks` target or `scripts/setup.sh` invocation.

Each of the three enforcement surfaces (pytest, Semgrep, pre-commit) should fail the PR on violation. None of them should block on WARNING — reserve WARNING for the terminology rule during its gradual-cleanup window.

## Completion signal

When every section above is done:

- `pytest tests/drr/ -v` reports all parametrized tests pass with no skips.
- Every DRR frontmatter in `tasks/design-rationale/` has `status: implemented` on every enforcement entry whose mechanism now exists.
- `tests/drr/test_drr_metadata.py::test_drr_enforcement_paths_exist` verifies every declared path resolves (you'll see this pass because of the `status: implemented` flags you added).
- The nine DRRs can be promoted from `Status: Draft` to `Status: Decided` in one final PR.
- `tasks/design-rationale/README.md` — bump the "Change history" entry with the completion date.

## What NOT to do

- Don't mock the audit DB. The test is meaningless without two real PostgreSQL connections.
- Don't disable rate-limiting in the test environment just to make the test fast — it's what you're testing.
- Don't add `pytest.mark.skip` to any test you can't finish. Either ship it working or defer to a new task.
- Don't weaken the DRR to match the code. If the code is wrong (e.g., DV flag removal is a one-person action today), fix the code first.
- Don't ship Semgrep rules without running them against the entire current codebase and confirming zero existing violations — or flagging the violations as follow-up in TODO.md.
- Don't promote any DRR from `Draft` to `Decided` until GK has reviewed it (Consultation Gate in `CLAUDE.md`).
