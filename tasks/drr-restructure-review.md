# Review: DRR / Principle Restructure

Reviewer: automated second-read (Claude, Opus 4.6)
Branch reviewed: `worktree/session-20260412-143934` (commit `181cbd4e drafts: split DRRs from principles; extract 7 new prescriptive DRRs`)
Scope: the split itself, coverage vs. the four original foundation docs, and enforcement-block soundness for the seven new prescriptive DRRs.

---

## 1. Executive summary

The split is the right call and the execution is largely competent. The principle docs read as principles, the new prescriptive DRRs each carry an `enforcement:` block, and the naming and cross-links are mostly consistent. Five issues rise above the rest:

1. **File paths in the enforcement blocks are wrong in five of the seven new DRRs.** `apps/accounts/`, `apps/alerts/`, `apps/dv_safety/`, `apps/core/`, and `konote/settings.py` do not exist in the repo. This is the single biggest defect — any developer trying to act on the enforcement block will be confused.
2. **Two legally-prescriptive areas are orphaned by the split.** WCAG 2.2 AA accessibility (Principle §9 of the old collaborative-practice foundation) and customisable terminology (`{{ term.client }}` templating) were prescriptive in the original and are now in neither a principle nor a DRR.
3. **Several enforcement blocks overclaim what the named rule can catch.** The clearest case is `no-silent-record-overwrite` on `ProgressNote`: any `.save()` on create would also hit this, so the rule as written is either false-positive-heavy or requires semantic judgement it cannot provide.
4. **Anti-patterns listed in prose outrun the enforcement block in almost every DRR.** The "Missing invariants" counts below are the second-most common defect after file paths.
5. **The meta-invariant "every DRR has `enforcement:`, CI fails if one doesn't" has no implementation.** Reading the README it sounds like a live property; nothing in the seven drafts builds the check that would make it true.

None of these are fatal; all are tractable in one revision pass.

---

## 2. Pass 1 — Coverage and clarity (per foundation doc)

### 2.1 `foundation-collaborative-practice.md`

**Lost content.** The original runs to nine numbered sections; the principle doc compresses them to five "Key Judgement Calls" bullets. Two substantive ideas have disappeared entirely:

- **Section 9 "Accessible by Design"** (WCAG 2.2 AA, semantic HTML, keyboard nav, screen readers, alt text). The original is explicit: *"Accessibility is not a separate checklist applied after development — it is a constraint on every template and component from the start. ... If the portal is inaccessible, that participant is excluded from the 'Ko' in KoNote."* The new principle doc mentions accessibility nowhere; no new DRR covers it; no existing DRR covers it (executive-dashboard-redesign touches dashboard a11y only). This is a legal obligation under AODA and it has no enforcement. It needs its own DRR.
- **Section 7 "Customisable Terminology"** — the original says *"All templates use `{{ term.client }}` rather than hardcoded words."* That is a grep-able rule (CLAUDE.md already treats it as one). It's now reduced to the bullet *"if the system doesn't speak the community's language, it isn't truly collaborative"* in the principle doc. The rule is not in any DRR. A `semgrep` rule that forbids hardcoded "client"/"participant"/"worker" in templates outside the terminology include would catch it.

Less-critical losses:

- Original Section 5 named the `SuggestionTheme` AI-categorisation pipeline as load-bearing. The principle doc references `insights-metric-distributions.md` for this, which is fine.
- The Anti-Patterns Summary table (9 rows) is entirely replaced by the shorter "Key Judgement Calls" list. Most are preserved conceptually, but *"Hardcoded terminology"* and *"Accessibility as post-launch polish"* drop through the gap along with their parent sections.

**Muddled split.** One genuinely testable invariant remains in the principle doc: *"Notes that omit participant voice are incomplete by design. The two-lens structure (Their Perspective / Your Observations) is load-bearing."* That is a form-validation rule — the `ProgressNote` model should require both fields, or the form should show an incompleteness indicator. This belongs in a DRR (or in whatever DRR owns `ProgressNote` shape).

**Cross-references.** The principle doc lists six implementation DRRs. Three of the nine original sections have matching DRRs (bilingual, survey-metric-unification, circles). Six do not (alliance rating, participant portal, goal builder, feedback-informed continuous improvement, strengths-based language, accessibility). At least the last two are prescriptive enough to deserve DRRs. `access-tiers.md` and `executive-dashboard-redesign.md` are listed but their link to the principle is weak — they implement sovereignty or security as much as collaboration.

**Clarity of the core principle.** The principle doc still reads well on its own — the "Ko" framing, the research basis, the four guiding questions, the "load-bearing" language all survive. A reader could stop here and understand what KoNote is. This section is the most successful of the four.

### 2.2 `foundation-data-sovereignty.md`

**Lost content.** The principle doc preserves most of the original. Specific losses:

- **Small-cell suppression (k≥5) as a mandatory, non-overridable rule.** Original: *"KoNote's small-cell suppression is mandatory, not optional — it cannot be overridden by staff, administrators, or funders."* That is a prescriptive rule. The principle doc mentions aggregate reports but drops the k≥5 requirement. It may already live in `cids-privacy-architecture.md` or `evaluation-microdata-export.md` (not reviewed here) — if so, the principle doc should reference them explicitly for this rule.
- **The `PublishedReport` model** as the structural boundary for consortium reporting — dropped. The principle doc describes the behaviour ("one-way, community-initiated, no individual records") without naming the enforcement mechanism.
- **The service-agreement / licensing clause** about ownership (*"this principle should be formalised in every service agreement"*) — dropped. Arguably this belongs elsewhere anyway (a legal/contracts repo), but the hook to it is now missing.

**Muddled split.** The "Canadian Digital Sovereignty" subsection of the principle doc contains one line that reads prescriptively: *"Cloud LLM APIs (OpenAI, Anthropic) are excluded for participant content."* That is an enforceable rule. It is already prescribed in `ai-feature-toggles.md`, so the principle doc should phrase it as a reference ("enforced by ai-feature-toggles") rather than a standalone rule.

**Cross-references.** Good. The DRR list at the bottom is comprehensive. `individual-data-rights.md` (new) is correctly linked.

**Clarity.** Strong. The three-levels structure (individual / community / national) carries well, and the "gap between 'we promise not to' and 'we built it so you can't'" framing is preserved verbatim — the single most quotable line in the original, retained.

### 2.3 `foundation-security-by-default.md`

**Lost content.** Moving ten sections into five new DRRs + five existing ones is the most ambitious split. What got lost or weakened:

- **Encryption at rest startup check.** Original: *"The system validates encryption key round-trip on every startup. If the key is missing, corrupt, or misconfigured, the application will not start."* The principle hub lists `encryption-key-rotation.md` as the implementation. That DRR was not re-examined here and may already own this rule — but if it doesn't, a prescriptive invariant has fallen through.
- **RBAC three-layer defence.** Original: *"The matrix is checked at three layers: view decorator, middleware, and template tag."* This is a specific, testable invariant. The principle hub points to `access-tiers.md`; if that DRR doesn't carry the three-layer rule forward, it's lost.
- **`ClientAccessBlock` specifics.** *"Checked BEFORE role-based access", "no role can override it", "no time-based expiry — must be manually cleared".* Same flag: verify `access-tiers.md` carries these three invariants.

These three items are the risk of the security split: they depend on pre-existing DRRs picking up the load. The restructure PR should include a verification pass on each.

**Muddled split.** The principle hub is clean — nothing prescriptive sneaks through.

**Cross-references.** The hub table is excellent; it names every decision and its implementing DRR. One oddity: *"Negative access lists (`ClientAccessBlock`)"* and *"RBAC permission matrix"* both point to `access-tiers.md`, which implies that single DRR now carries two distinct rules. That's fine but makes the access-tiers DRR load-bearing in a way it may not have been designed for — worth verifying it still reads coherently.

**Clarity / hub viability.** 62 lines, three commitments, one guiding test, and a table. It conveys the principle ("architectural, not configurable; fails closed; loud on misconfiguration"). It does not stand as richly alone as the collaborative-practice principle does — a developer reading only this hub learns *that* security is enforced but not *how*. Given the principle is "architectural, not configurable," I'd argue one concrete example ("encryption keys are validated on boot; if misconfigured the app refuses to start") would anchor the abstraction without re-introducing prescription. That would bring it to maybe 70 lines and substantially improve readability.

### 2.4 `foundation-nonprofit-sustainability.md`

**Lost content.** The cleanest extraction of the four.

- **Self-healing ops recovery-time table** (30–90 s, 15–20 min, prevention, escalation) — reduced to a bullet list in the principle doc. Not enforceable anyway, so appropriate.
- **Specific $ figures** ($26 CAD/month OVHcloud single-tenant, $13/agency at 10-agency scale, etc.) — dropped in favour of a pointer to `multi-tenancy.md` / `ovhcloud-deployment.md` / `hosting-cost-comparison.md`. Appropriate; those numbers move.
- **"Sector-Wide Learning" as a named section** — folded into "Built for Evaluation." Concepts preserved, label lost. Minor.

**Muddled split.** None material. The principle doc still mentions "~2,000 participants per agency, at which point the in-memory search... needs re-architecture" as a revisit trigger. That's a specific enough numeric threshold that it could arguably be an enforcement in a future DRR — but today it's a principle-level warning, which is fine.

**Cross-references.** Comprehensive list of 10 DRRs. Good.

**Clarity.** Strong. Three commitments, guiding tests, when-to-revisit — all readable standalone.

---

## 3. Pass 2 — Testability sufficiency (per new DRR)

### 3.1 `audit-log-isolation.md`

**Ambiguities.** The Django system check `audit_db_role_insert_only` is described as *"connects as the audit role and attempts a dry-run UPDATE; if it succeeds, the check raises a critical error."* That's implementable. But the DRR does not name the role, and `konote/settings.py` does not exist (see "File paths" below) — so the check will need to locate settings through the correct module path.

**Missing invariants.** Two anti-patterns are not covered by the enforcement block:

- *"Audit DB backups run on a separate schedule and are stored separately from application DB backups"* — stated in prose, no enforcement. This is an ops-time property and probably best handled by `codeowner` on the backup script plus a note in an ops runbook rather than a test, but the DRR should say so explicitly.
- *"Writing audit from the same DB connection as application queries — transaction rollback could drop audit entries"* — listed as anti-pattern, not tested. A pytest that opens a transaction, writes an audit record, rolls back the application transaction, and asserts the audit record *persists* would close this.

**Overclaimed enforcement.** None.

**Missing edge cases.** Migrations. The anti-pattern *"Granting the audit role UPDATE or DELETE 'just for migrations'"* is stated as rejected, but the DRR doesn't explain how migrations run at all. If the app role can't DDL, some other role must — but then that role is a coercion target. Either specify the migration role and its constraints (e.g., DDL-only, not DML), or say explicitly that schema migrations run via a separately-credentialed one-off session.

**File paths.** `apps/audit/` exists ✓. `konote/settings.py` is WRONG — it is a directory (`konote/settings/base.py`, `production.py`, etc.). The CODEOWNERS path will silently not match anything until corrected.

### 3.2 `session-security.md`

**Ambiguities.** `SESSION_COOKIE_SAMESITE` is pinned in prose to "Lax (or stricter)" but the Django system check description just says *"SameSite flags"* — the check should test for `SAMESITE != "None"` plus the other invariants. Also: "Secure flag in production" is implied but the check as described doesn't gate on environment.

**Missing invariants.** The anti-patterns list *"Inline `<script>` or `onclick="..."` attributes in templates"* but the Semgrep rule `no-inline-scripts-without-nonce` only covers `<script>` tags. Event-handler attributes (`onclick`, `onload`, `onsubmit`, etc.) are not covered. Either expand the rule to scan for inline event handlers, or split into a second rule.

**Overclaimed enforcement.** None.

**Missing edge cases.** SSO callback flow — during Azure AD redirect, the provider may set its own cookies or the callback may briefly transit through a less-hardened state-management cookie. The DRR should say whether SSO state cookies are in scope. HTMX responses: are CSP nonces regenerated per partial response? Worth a sentence.

**File paths.** `konote/settings.py` WRONG (directory). `apps/core/middleware.py` WRONG — no `apps/core/` exists; middleware lives at `konote/middleware/` (specifically `konote/middleware/session_timeout.py`). `**/templates/**/base*.html` is fine as a glob.

### 3.3 `rate-limiting-and-authentication.md`

**Ambiguities.** *"Rate-limit middleware installed"* — which one? The check is described as validating that it's installed without naming what "it" is. The settings module would have to be grepped for some specific middleware class name, which the DRR should pin. Similarly *"lockout policy configured"* — how? Via `django-axes`? A custom backend? Unspecified.

**Missing invariants.** The prose requires *"Timing-safe comparisons for authentication tokens, password reset tokens, and SSO assertions."* The enforcement block has no entry for this. A `semgrep` rule forbidding `==` / `!=` on anything named `*_token` or `assertion` in `apps/auth_app/`, and requiring `hmac.compare_digest`, would close the gap.

**Overclaimed enforcement.** None.

**Missing edge cases.** Lockout recovery. The anti-pattern *"Indefinite account lockout — DoS vector against legitimate users"* is stated, and 15 minutes is given — but a legitimate locked-out user may have a real emergency. What's the recovery path? Admin-triggered unlock? Automatic expiry only? Either is fine; the DRR should pick one. Also: the lockout is per-account — is there any protection against *distributed* credential-stuffing across many accounts? (The per-IP rate limit helps, but a botnet spreads IPs.)

**File paths.** `apps/accounts/views.py` and `apps/accounts/backends.py` are WRONG. The app is `apps/auth_app/` (`apps/auth_app/decorators.py`, `apps/auth_app/backends.py` if it has one, etc.). `konote/settings.py` WRONG (directory). This is the most confusing DRR for a developer acting on it because the named app doesn't exist.

### 3.4 `two-person-safety-actions.md`

**Ambiguities.** The DRR names a helper `require_two_person_approval(action, requester, approver)` and requires Semgrep to flag any protected action not calling it. That is testable — if the helper exists. The DRR does not say whether the helper already exists or must be created. Given that `apps/clients/erasure.py` exists, there may already be two-person logic; the DRR should either reference the existing helper by canonical import path or explicitly mark "helper to be created."

**Missing invariants.** One anti-pattern is uncovered: *"Approval request reusable across sessions (persistent link) — enables coercion at leisure; requests must be per-action and time-limited."* Time limits on approval tokens are prescriptive and testable, but the enforcement block does not mention them. A pytest that generates an approval request, waits past the token expiry (with a freezegun fixture), and asserts the approval is rejected would close this.

**Overclaimed enforcement.** None.

**Missing edge cases.** What if the only Program Manager is the requester? The DRR says no override — so the action waits. That's consistent with the principle, but worth stating: some agencies may have only one PM, which makes the two-person requirement a governance problem for them. The DRR implicitly accepts this; it could say so out loud.

**File paths.** `apps/alerts/views.py` WRONG — alert cancellation lives in `apps/events/` (see `apps/events/migrations/0003_alert_cancellation_recommendation.py`). `apps/dv_safety/` WRONG — DV logic is in `apps/clients/dv_views.py` and related migrations (`apps/clients/migrations/0029_add_dv_safe_fields.py`). `apps/clients/erasure.py` CORRECT ✓.

### 3.5 `demo-mode-isolation.md`

**Ambiguities.** *"The `is_demo` flag is enforced at three layers: middleware, ORM queryset, UI"* — but the Semgrep rule only covers ORM querysets, not middleware. Is the middleware layer exercised by the pytest? The test description covers middleware (direct URL manipulation expects 404) — OK. Fine.

**Missing invariants.** The anti-pattern *"Demo accounts sharing the same tenant schema as real data"* claims *"Schema-level separation is the strongest isolation available."* This contradicts the Core Decision, which describes row-level `is_demo` filtering, not schema-level separation. Either the architecture is row-level (in which case the anti-pattern's reasoning is wrong — we explicitly *do* share the schema) or it's schema-level (in which case the ORM filter is redundant belt-and-braces and the enforcement block should assert schema isolation, not row filtering). This needs clarification.

**Overclaimed enforcement.** The Semgrep rule says *"Querysets on `ClientFile`, `ProgressNote`, `Goal`, etc. must respect `is_demo`."* The *"etc."* is a hole — static rules need an enumerated list. Either list every demo-scoped model or use a marker (a mixin, a manager class) the rule can check for.

**Missing edge cases.** Shared reference data (CIDS codes, default terminologies, system-generated templates): demo uses production copies, or separate copies? If shared, is that fine? If a demo user creates a custom field that triggers a new reference value, does it leak into real tenants? Worth a sentence.

**File paths.** `apps/core/demo.py` WRONG (no `apps/core/`). The demo engine is at `apps/admin_settings/demo_engine.py` and `apps/admin_settings/management/commands/seed_demo_data.py`. `apps/core/middleware.py` WRONG (see §3.2).

### 3.6 `tech-stack-constraints.md`

**Ambiguities.** *"No JS frameworks in `INSTALLED_APPS`"* — `INSTALLED_APPS` is a Django setting for Python apps; JS frameworks would never appear there anyway. Probably meant: no JS framework packages in `requirements.txt` (React/Vue aren't Python packages, so this is a nonsensical check), or no JS tooling directories (`node_modules`, `src/` with React) in the tree. Reword to specify the intended check.

**Missing invariants.** *"Configuration over code for feature toggles — driven by environment variables, not code branches"* is in the prose but has no enforcement. Could be dropped from the enforcement block and kept as a principle, or enforced by a test that inspects `settings.FEATURE_FLAGS` and confirms each has a matching env var. Either is fine; current state is a dangling commitment.

**Overclaimed enforcement.** The `dependency-ceiling` pre-commit hook counts non-blank/non-comment lines in `requirements.txt`. It won't catch: constraint files, `-r requirements/base.txt` includes, `pyproject.toml` or `setup.py` dependencies listed elsewhere, or editable installs that pull transitive deps. As a heuristic it's fine, but the DRR should say "we count direct pins in requirements.txt only; transitive deps and other manifests are out of scope."

**Missing edge cases.** Exceptions for JS: the DRR says *"(Exception: if KoNote ever needs a tiny JS build step for a specific feature, the exception is defined here, not discovered in the diff.)"* — good stance, but today's codebase already ships `chart.js` (presumably a vendored file) and HTMX. The DRR should make clear that vendored static assets are permitted, the ban is on `npm`/`package.json`/build pipelines.

**File paths.** `requirements.txt`, `Dockerfile*`, `docker-compose*.yml` all exist at repo root. CORRECT ✓.

### 3.7 `individual-data-rights.md`

**Ambiguities.** The Django system check says *"verify `ConsentEvent` model overrides `save()` to reject updates after creation; verify no DELETE grant on the table."* Both are testable. But the DRR doesn't say which DB role is being checked for the DELETE grant — presumably the app role, but spell it out.

**Missing invariants.** The anti-pattern *"Formal access requests required for self-viewing — power asymmetry discourages rights exercise"* has no enforcement. That's a judgement call (you can't grep for "absence of a portal feature"), so it's probably best marked `llm-review` or `judgment-only` rather than left as an untestable anti-pattern. Similarly for *"Soft delete that leaves PII recoverable"*: the test covers a complete erasure scenario but doesn't scan the codebase for soft-delete implementations that might leave PII in place.

**Overclaimed enforcement.** The Semgrep rule `no-silent-record-overwrite` is described as *"forbid direct `.save()` on `ProgressNote` content fields outside the correction/amendment pipeline."* A plain `ProgressNote.save()` is called in the *create* path too — the rule can't distinguish create from update without semantic context. Either (a) narrow the rule to a specific helper that performs the update, e.g., "forbid `.save(update_fields=['body', 'content'])`" or equivalent, or (b) reclassify as `llm-review`. As currently written the Semgrep rule is either false-positive-heavy (flags all creates) or underspecified.

**Missing edge cases.** Amendments to amendments (is a correction to a correction allowed? versioned?). Consent withdrawal retroactivity — if a participant withdraws consent today, are yesterday's aggregate reports revised? (Probably not, but the DRR could say.)

**File paths.** `apps/clients/erasure.py` CORRECT ✓. `apps/clients/corrections.py` and `apps/clients/consent.py` do NOT exist as standalone files. The `ConsentEvent` model lives in `apps/clients/models.py` (inferred from migration `0034_consentevent.py`); there is no dedicated consent.py. Either create these files as the DRR implies and move the logic into them, or correct the CODEOWNERS paths to point at `apps/clients/models.py` and specific view modules.

---

## 4. Cross-cutting findings

### 4.1 Overlap and conflict

- **`two-person-safety-actions` vs `individual-data-rights` on erasure.** Ownership is clear once you read both (two-person owns the *mechanism*, individual-data-rights owns the *right*). The cross-link from individual-data-rights to two-person-safety-actions is present. Good.
- **`audit-log-isolation` vs everything else.** Every other DRR says "events are audited" without repeating the invariants. Correct shape.
- **`access-tiers.md` is load-bearing** — it is referenced as the implementation for both "RBAC permission matrix as single source of truth" and "Negative access lists (`ClientAccessBlock`)" from the security hub, and is also linked from `two-person-safety-actions` (role eligibility for approver) and `demo-mode-isolation` (role restrictions within demo). That existing DRR needs to be checked to confirm it now carries all three invariants — if it was written to cover just the three permission tiers, the extracted content may have dropped on the floor.
- **No active conflict.** No two DRRs disagree on a rule. Good.

### 4.2 Meta-invariant coverage

The README claim is: *"Every DRR must have an `enforcement:` front-matter block. CI uses this to gate PRs."* This meta-invariant is not itself enforced by the current drafts. Someone needs to build:

1. A pytest (or pre-commit check) that walks `tasks/design-rationale/*.md`, parses front-matter, and fails if `enforcement:` is missing or empty.
2. A complementary check that fails if anything in `tasks/design-rationale/` has `role: principle` or if anything in `tasks/principles/` has `drr:` or `enforcement:`.

Without both, the split is informal — a new DRR could be added tomorrow with no enforcement block and nothing would notice. This is a `[must-fix]` for the overall proposal to deliver what the README promises.

Separately: none of the seven new DRRs use `llm-review` or `judgment-only` despite several anti-patterns clearly needing semantic review (see §3.7 especially). Mark the judgement-dependent items explicitly as such — it isn't a failure mode, it's the right tool, and using it honestly will keep the automated rules from overclaiming.

### 4.3 Principle hub viability

`security-by-default.md` as a hub: the principle ("architectural, not configurable; fails closed; loud on misconfiguration") survives but thinly. The three-commitment framing + the guiding test do enough to convey why. The table of 10 implementation DRRs is the right hub shape. Adding one concrete example — *"e.g., the encryption key is validated on boot; if it's misconfigured the app refuses to start"* — would ground the abstraction without re-introducing prescription. As-is it is viable; with one anchor it becomes excellent.

The other three principles remain rich enough to read standalone. No viability concern.

---

## 5. Recommended revisions

**`[must-fix]`**

- Correct all file paths in enforcement blocks and prose to match the actual codebase. Specifically:
  - `konote/settings.py` → `konote/settings/` (it's a directory) in audit-log-isolation, session-security, rate-limiting-and-authentication.
  - `apps/accounts/views.py` + `apps/accounts/backends.py` → `apps/auth_app/...` in rate-limiting-and-authentication.
  - `apps/alerts/views.py` → `apps/events/...` (and identify the specific alert-cancellation view module) in two-person-safety-actions.
  - `apps/dv_safety/` → `apps/clients/dv_views.py` (and related) in two-person-safety-actions.
  - `apps/core/demo.py` → `apps/admin_settings/demo_engine.py` in demo-mode-isolation.
  - `apps/core/middleware.py` → `konote/middleware/` in session-security and demo-mode-isolation.
  - `apps/clients/corrections.py` + `apps/clients/consent.py` — either create these files (and put the logic in them), or point CODEOWNERS at `apps/clients/models.py` plus specific view modules, in individual-data-rights.
- Create the meta-check that enforces the split: a test that fails if any DRR lacks an `enforcement:` block, and a test that fails if principle and DRR frontmatter are swapped. Without this the README's promise is undelivered.
- Decide and document: does WCAG 2.2 AA accessibility get its own DRR, or is it explicitly out of scope? Right now it is prescriptive in the old foundation, non-existent in the new structure, and legally mandated by AODA. The current state is "silently dropped."
- Resolve the demo-mode-isolation contradiction: row-level `is_demo` filtering OR schema-level separation, not both described as the rule.
- Rewrite `no-silent-record-overwrite` to not flag `ProgressNote` creation — either narrow to specific update helpers, or reclassify as `llm-review`.

**`[should-fix]`**

- Add a DRR covering customisable terminology (`{{ term.client }}`-only templating, no hardcoded role words). Semgrep-enforceable.
- Add the "two-lens structure load-bearing" invariant to whichever DRR owns `ProgressNote` shape (a form-validation test).
- Fill gaps in enforcement blocks where prose lists an anti-pattern that the block doesn't catch:
  - audit-log-isolation: write-within-application-transaction test.
  - session-security: Semgrep rule for inline event-handler attributes (`onclick` etc.), not just `<script>`.
  - rate-limiting-and-authentication: Semgrep rule forbidding `==` / `!=` on `*_token` / `assertion`, requiring `hmac.compare_digest`.
  - two-person-safety-actions: pytest for approval-token time limits.
  - demo-mode-isolation: enumerate the protected models instead of "etc." in the Semgrep rule.
- Verify (in this PR) that `access-tiers.md`, `encryption-key-rotation.md`, `phipa-consent-enforcement.md`, and `no-live-api-individual-data.md` carry forward the specific invariants the security hub now relies on them for (three-layer RBAC, startup key round-trip, `ClientAccessBlock` semantics, etc.). If any gaps, amend those DRRs in the same PR.
- In individual-data-rights, reclassify the "formal access request" and "soft delete" anti-patterns as `llm-review` rather than leaving them as untestable anti-patterns.

**`[nice-to-have]`**

- Add one concrete example to `security-by-default.md` to anchor the principle. Keep it short.
- Reword the tech-stack-constraints pytest description — `INSTALLED_APPS` for JS frameworks doesn't parse.
- Document the migration-time exception pattern in audit-log-isolation (how schema migrations run without violating the INSERT-only rule).
- In demo-mode-isolation, add a sentence about shared reference data (CIDS codes, default templates) — shared or copied?
- Principle doc `collaborative-practice.md`: add a sentence indicating that the nine concrete mechanisms from the original foundation are now distributed across the listed DRRs and the principles of the new DRRs-to-be-written (accessibility, terminology). A reader comparing old and new shouldn't have to wonder where things went.

---

*End of review.*
