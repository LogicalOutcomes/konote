# KoNote Web — Project Instructions

## What This Is

A secure, web-based Participant Outcome Management system for nonprofits. Agencies define desired outcomes with clients, record progress notes with metrics, and visualise progress over time. Each agency runs their own instance.

## Tech Stack

- **Backend**: Django 5, Python 3.12
- **Database**: PostgreSQL 16 (two databases: app + audit)
- **Frontend**: Server-rendered Django templates + HTMX + Pico CSS + Chart.js
- **Auth**: Azure AD SSO (primary) or local with Argon2
- **Encryption**: Fernet (AES) for PII fields
- **Deployment**: Docker Compose → OVHcloud VPS (recommended) or Azure

**No React, no Vue, no webpack, no npm.** Keep it simple.

## Key Conventions

- Use `{{ term.client }}` in templates — never hardcode terminology
- Use `{{ features.programs }}` to check feature toggles
- PII fields use property accessors: `client.first_name = "Jane"` (not `_first_name_encrypted`)
- All `/admin/*` routes are admin-only (enforced by RBAC middleware)
- Audit logs go to separate database: `AuditLog.objects.using("audit")`
- Canadian spelling: colour, centre, behaviour, organisation, **program** (never "programme" in English — "programme" is British/French only). French translations correctly use "programme".

## Git Workflow

**Branch model:** `main` is the production branch (deploy-ready). `develop` is the integration branch (all feature work merges here). `staging` is the testing branch — PB merges `develop` → `staging`, tests there, then merges into `main` for releases.

**Never commit to `main` directly** — PRs to `main` are handled by PB after staging review.

### Session Start (do this first, every time)

1. `git pull origin develop`
2. `git worktree prune` — remove stale worktree references
3. `git status` — if there are uncommitted changes you didn't make, **STOP and tell the user**. Do not stash, discard, or commit someone else's work.
4. Check the current branch: `git branch --show-current`. If not on `develop`, switch to it before creating a new branch.

### Working on a Task

1. Create a feature branch off `develop`: `git checkout -b feat/short-description` or `fix/` or `chore/`
2. **Commit after every edit.** Never leave uncommitted changes across tool calls.
3. When done: push, create PR to `develop`, merge immediately (`gh pr merge --merge` — never squash).
4. **After merging**, in the same step:
   - Delete the local branch: `git branch -d <branch-name>`
   - Pull develop: `git checkout develop && git pull origin develop`
   - If in a worktree, also pull develop in the main repo: `git -C /c/Users/gilli/GitHub/konote pull origin develop`

### Concurrent Session Safety (Worktrees)

Multiple sessions share one repo. Worktrees give each session an isolated directory so they don't overwrite each other's files.

**When to use worktrees:** When the user has another Claude Code session open on the same repo. If only one session is running, a regular branch off `develop` is simpler.

**Worktree cleanup is mandatory.** Sessions that create worktrees must clean them up before finishing:
1. Merge the PR (or confirm with user that unmerged work should be abandoned)
2. Remove the worktree: `git worktree remove <path>`
3. Delete the local worktree branch: `git branch -D worktree/session-*`
4. Pull develop in the main repo directory

**After merging a PR from a worktree session**, pull develop into BOTH the main repo directory (`/c/Users/gilli/GitHub/konote`) AND the worktree directory.

### Session End Checklist

Before finishing any session, verify:
1. `git status` — **no uncommitted changes**. If there are changes, commit them or ask the user what to do.
2. `git worktree list` — only the main repo and any active session worktrees should appear. Remove stale ones.
3. Main repo is on `develop` (not stranded on a feature branch).
4. All merged feature branches are deleted locally.

## Terminal Command Rules

- **Long-running commands** (pytest with Playwright, Django server, migrations): can take 1–5 minutes. If the terminal reports "Command is still running", **wait for the final output**. Do NOT run `echo`, `type`, or other polling commands — this causes an infinite loop.
- **Shell**: Claude Code uses bash. Use Unix syntax (`export VAR="value"`, forward slashes in paths).

## Consultation Gates — When to Involve GK (Gillian Kerr)

GK is the subject matter expert for evaluation, nonprofit data modelling, and program design. She is not involved in day-to-day development but must review specific types of changes:

| Change Type | GK Reviews? | Examples |
|-------------|------------|---------|
| **New data entities** (models representing real-world concepts) | Yes | Circle, Survey, any new entity type |
| **Changes to outcome models** (PlanTarget, MetricDefinition, ProgressNote structure) | Yes | Adding fields that affect how outcomes are tracked or reported |
| **Metric definitions and measurement methodology** | Yes | What gets measured, scale definitions, plausibility thresholds |
| **AI workflow design** (prompts, scoring logic, suggestion algorithms) | Yes | Goal builder prompts, report summary logic, suggestion themes |
| **Evaluation principles** (feedback-informed practice, strengths-based language) | Yes | Alliance rating approach, two-lens note design, template wording |
| UI changes, bug fixes, infrastructure, deployment, testing | No | |
| Translations, documentation, admin UI improvements | No | |

**How to flag for GK review:** Add "GK reviews [what]" to the task owner field in TODO.md. Do not wait for review on implementation — build it, then request review before merging.

## PHIPA Consent Enforcement

**If you're adding a view that queries `ProgressNote` and displays note content to staff:**

1. For **list views** (querysets): call `apply_consent_filter(notes_qs, client, user, user_program_ids, active_program_ids=active_ids)` from `apps/programs/access.py`
2. For **single-note views** (one note by ID): call `check_note_consent_or_403(note, client, user, active_ids)` from `apps/programs/access.py`

This ensures cross-program clinical notes are only visible when the agency or participant has enabled sharing. See `tasks/design-rationale/phipa-consent-enforcement.md` for the full enforcement matrix, deferred items, and anti-patterns.

**Exempt from consent filtering:** aggregate counts (dashboards), de-identified reports, plan views (already program-scoped), portal views (participant's own data).

## Cost File Reconciliation Protocol

Cost data lives in multiple files across two repos. Before updating any cost deliverable, reconcile the source chain.

### Source-of-truth chain (upstream → downstream)

```
tasks/hosting-cost-comparison.md (this repo)     ← component pricing source
        ↓
tasks/p0-managed-service-plan.md (this repo)     ← managed service model
        ↓
konote-prosper-canada/deliverables/costing-model.md        ← detailed scenarios
        ↓
konote-prosper-canada/deliverables/hosting-budget-scenarios.md  ← client-facing summary
konote-prosper-canada/deliverables/costing-model-calculator.*   ← interactive calculator
```

### Before updating any cost file

1. **Read the `<!-- COST_VERSION -->` header** in each file in the chain
2. **Compare key values** (LLM VPS cost, per-agency costs, ops hours) across files
3. **If any values don't match**, stop and reconcile from upstream to downstream before proceeding
4. **If you're changing a pricing decision** (e.g., VPS tier, model choice), update the upstream file first, then cascade downstream
5. **After updating**, bump the `date` and values in the `COST_VERSION` header

### Cross-repo updates

The konote-prosper-canada repo cannot be updated in the same session as konote. When updating cost files in one repo:
- Update the `COST_VERSION` header with the new values
- Note in the commit message which downstream files need updating
- Flag in TODO.md: "Sync cost files to konote-prosper-canada" with the specific values that changed

## Development Rules (from expert review)

These rules apply to **every phase**. Do not skip them.

1. **Always create `forms.py`** — use Django `ModelForm` for validation. Never use raw `request.POST.get()` directly in views.
2. **Always extend the test suite** — when building views for a phase, add tests in `tests/` that cover the new views (permissions, form validation, happy path). Do not defer all testing to Phase 7.
3. **Always run and commit migrations** — after any model change, run `makemigrations` and `migrate`, then commit the migration files.
4. **Back up before migrating** — document/run `pg_dump` before applying migrations to a database with real data.
5. **Encrypted fields cannot be searched in SQL** — client search must load accessible clients into Python and filter in memory. This is acceptable up to ~2,000 clients. Document the ceiling.
6. **Cache invalidation** — after saving terminology, features, or settings, clear the relevant cache key. Prefer `post_save` signals over manual cache.delete() calls in views.
7. **HTMX error handling** — `app.js` must include a global `htmx:responseError` handler so network/server errors don't fail silently.
8. **QA scenario coverage** — when adding a new URL route or page, check if the sister repo `konote-qa-scenarios` needs a new scenario or page inventory entry. See `konote-qa-scenarios/pages/page-inventory.yaml` for the current page list.

## Testing Strategy

Run **only the tests related to what you changed**, not the full suite. Map changed files to test files:

- Changed `apps/plans/` → run `pytest tests/test_plans.py`
- Changed `apps/clients/` → run `pytest tests/test_clients.py`
- Changed `apps/reports/` → run `pytest tests/test_exports.py`
- Changed a template only (no Python) → no tests needed unless it has logic
- Changed multiple apps → run each relevant test file

**Do NOT run the full test suite** on every PR. Save it for:
- End of day (once)
- Before a production deploy
- After merging a large or cross-cutting PR

Full suite command: `pytest -m "not browser and not scenario_eval"`

## Translations

After creating or modifying any template that uses `{% trans %}` or `{% blocktrans %}` tags:
1. Run `python manage.py translate_strings` — this extracts new strings and compiles
2. Fill in any empty French translations in `locale/fr/LC_MESSAGES/django.po` (Claude Code does this directly — no API key needed during development)
3. Run `python manage.py translate_strings` again to recompile
4. Commit both `locale/fr/LC_MESSAGES/django.po` and `django.mo`

**For `{% blocktrans %}` blocks** (strings with variables or plurals): `translate_strings` cannot auto-extract these from templates. If you add a new `{% blocktrans %}`, you must add the corresponding msgid to the .po file manually, then run `translate_strings` to compile it.

**Automated safety nets** (you don't need to remember these — they run automatically):
- Django system check (W010) warns if template string count exceeds .po entries
- Pre-commit hook warns if .html files change without .po updates
- Container startup runs `check_translations` (non-blocking)

Use `--dry-run` to preview changes.

## Task File: TODO.md

TODO.md is a **dashboard** — scannable at a glance. It is not a project plan, decision log, or reference guide.

### Format Rules

1. **One line per task, always.** If a task needs more detail, create a file in `tasks/`.
2. **Line format:** `- [ ] Task description — Owner (ID)`
   - Owner initials after an em dash, only if assigned
   - Task ID in parentheses at end of line
   - Use `[x]` for done, `[ ]` for to do
3. **Task IDs:** Claude generates short codes (category + number): `DOC1`, `UI1`, `REQ1`, etc.

### Sections (in this order)

| Section | Purpose | Rules |
|---------|---------|-------|
| **Flagged** | Decisions needed, blockers, deadlines | Remove flags when resolved. If empty, show "_Nothing flagged._" |
| **Active Work** | Tasks being worked on now | Grouped by phase. Include owner on every line. |
| **Coming Up** | Next phase of work | Can reference task detail files for phases not yet started |
| **Parking Lot: Ready to Build** | Scope is clear, just needs time | A session can pick these up without special approval |
| **Parking Lot: Needs Review** | Not yet clear we should build, or design isn't settled | **Never build without explicit user approval in the current conversation** |
| **Recently Done** | Last 5–10 completed tasks | Format: `- [x] Description — YYYY-MM-DD (ID)`. Move older items to `tasks/ARCHIVE.md`. |

### Language

- Use **"Phase"** not "Epic"
- Use **"Parking Lot"** not "Backlog"
- Use **"Waiting on"** not "Blocked"
- Use **"Flagged"** not "Impediments"
- Write task descriptions in plain language a non-developer can understand

### What Goes Where

| Content | Location |
|---------|----------|
| Task dashboard (one line per task) | `TODO.md` |
| Task detail, subtasks, context, notes | `tasks/*.md` |
| Phase prompts for Claude Code | `tasks/phase-*-prompt.md` — **delete when the phase PR merges** |
| Agent execution prompts (single-use) | `tasks/agent-prompts/` — **delete when the phase PR merges** |
| Review prompts, framework, and results | `konote-ops/reviews/` (private repo) |
| Design rationale for complex features | `tasks/design-rationale/*.md` |
| Decisions, notes, changelog | `CHANGELOG.md` |
| How Claude manages tasks | `CLAUDE.md` (this section) |
| Completed tasks older than 30 days | `tasks/ARCHIVE.md` |

### Design Rationale Records (DRRs)

Some features involve complex trade-offs (legal, privacy, data modelling, adoption risk) that were evaluated by expert panels. These decisions are preserved in `tasks/design-rationale/` so future sessions don't re-introduce designs that were already evaluated and rejected.

**Before modifying any feature that has a DRR**, read the corresponding file. These documents contain:
- **Anti-patterns** (things explicitly rejected, with reasons)
- **Decided trade-offs** (where competing concerns were weighed)
- **Graduated complexity paths** (when deferred features should be reconsidered)
- **Risk registries** (what can go wrong and how to monitor it)

**Do not override DRR decisions without explicit stakeholder approval.** If circumstances have changed, document why in the DRR before proceeding.

Current DRRs (read the file before modifying related features — all in `tasks/design-rationale/`):
- `circles-family-entity.md` — Circles (family/network entity)
- `multi-tenancy.md` — Multi-tenancy architecture
- `reporting-architecture.md` — Reporting system
- `executive-dashboard-redesign.md` — Executive dashboard UX
- `offline-field-collection.md` — Offline field collection (ODK Central)
- `phipa-consent-enforcement.md` — PHIPA cross-program consent
- `insights-metric-distributions.md` — Insights page & program reporting
- `bilingual-requirements.md` — Bilingual (EN/FR) requirements
- `ai-feature-toggles.md` — AI feature toggle split
- `ovhcloud-deployment.md` — OVHcloud deployment architecture
- `data-access-residency-policy.md` — Data access & residency policy
- `document-integration.md` — SharePoint + Google Drive integration
- `no-live-api-individual-data.md` — No live API for individual PII
- `self-hosted-llm-infrastructure.md` — Self-hosted LLM (Ollama/OVHcloud)
- `encryption-key-rotation.md` — Encryption key rotation procedures
- `access-tiers.md` — Access tiers, PERM-P5/P6/P8, and demographic visibility (DEMO-VIS1)
- `funder-reporting-profiles.md` — Funder reporting profiles (CIDS template-based reporting)

### How Claude Manages Tasks

- **Always `git pull origin develop` before reading or updating TODO.md.** The local copy goes stale after PRs merge on GitHub. Never trust the local file without pulling first. When the user asks for the to-do list, pull first — do not skip this step or assume the local copy is current. **After merging a PR that changes TODO.md, pull develop into the current working directory** (whether that's the main repo or a worktree) so the user sees the update immediately — do not wait to be asked.
- When user describes a task: create an ID, add one line to the right section in TODO.md
- When a task needs subtasks or context: create a detail file in `tasks/`
- When user asks about a task: read TODO.md for status, read `tasks/*.md` for detail
- When a task is completed: mark `[x]`, add completion date, move to Recently Done
- When Recently Done exceeds 10 items: move oldest to `tasks/ARCHIVE.md`
- When a task is blocked or needs a decision: add it to the Flagged section
- When a flag is resolved: remove it from Flagged
- Never put inline paragraphs, meeting notes, or decision detail in TODO.md
- **When completing a QA fix task**, update `qa/fix-log.json` in the same commit — add the fix description, finding_group, fixed_date, fixed_in (TODO ID or PR), and verified_date (null). This prevents the next `/process-qa-report` run from missing known fixes.

### Marking Work In Progress

- **Before starting a task**, mark it `🔨 IN PROGRESS` in TODO.md so other conversations don't duplicate the work
- Format: `- [ ] 🔨 Task description — Owner (ID)`
- **Before picking up a task**, check TODO.md first — if it's already marked 🔨, skip it
- When done, replace the 🔨 line with `[x]` and move to Recently Done as usual

### Parallel Work with Sub-Agents

- When a phase has **independent tasks** (no dependencies between them), use sub-agents to work on them in parallel
- Check TODO.md first to identify which tasks are independent vs. which depend on others
- Mark all tasks being worked on as 🔨 IN PROGRESS before launching agents
- Example: PROG1 (programs), CLI1 (clients), and FIELD1 (custom fields) can run in parallel because they don't depend on each other
