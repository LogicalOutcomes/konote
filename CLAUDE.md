# KoNote Web — Project Instructions

## What This Is

A secure, web-based Participant Outcome Management system for nonprofits. Agencies define desired outcomes with clients, record progress notes with metrics, and visualise progress over time. Each agency runs their own instance.

## Tech Stack

- **Backend**: Django 5, Python 3.12
- **Database**: PostgreSQL 16 (two databases: app + audit)
- **Frontend**: Server-rendered Django templates + HTMX + Pico CSS + Chart.js
- **Auth**: Azure AD SSO (primary) or local with Argon2
- **Encryption**: Fernet (AES) for PII fields
- **Deployment**: Docker Compose → Azure / Elest.io / Railway
- **Railway CLI**: `C:\Tools\railway.exe` (v4.29.0) — linked to project "KoNote", production environment

**No React, no Vue, no webpack, no npm.** Keep it simple.

## Key Conventions

- Use `{{ term.client }}` in templates — never hardcode terminology
- Use `{{ features.programs }}` to check feature toggles
- PII fields use property accessors: `client.first_name = "Jane"` (not `_first_name_encrypted`)
- All `/admin/*` routes are admin-only (enforced by RBAC middleware)
- Audit logs go to separate database: `AuditLog.objects.using("audit")`
- Canadian spelling: colour, centre, behaviour, organisation, **program** (never "programme" in English — "programme" is British/French only). French translations correctly use "programme".

## Git Workflow

**Pull main before doing anything.** At the very start of every session — before reading task files, before making decisions, before creating a branch — run `git pull origin main`. Worktrees and local copies go stale when other sessions merge PRs. If you skip this step, you will make decisions based on missing files and outdated plans.

**Branch before working.** `main` has branch protection — never commit directly to it.

1. **At the start of every task**, run `git pull origin main`, then check the current branch with `git branch --show-current`
2. If on `main`, create a feature branch before making any changes: `git checkout -b fix/short-description` or `git checkout -b feat/short-description`
3. Branch naming: `fix/` for bug fixes, `feat/` for new features, `chore/` for cleanup/config
4. Commit frequently on the feature branch
5. When work is done, push and create a PR to merge into `main`

**Never commit to `main` directly.** If you accidentally do, stop and move the commit to a new branch before continuing.

### Concurrent Session Safety

**Multiple Claude Code conversations sharing one repo directory WILL destroy each other's work.** When one session runs `git checkout`, it overwrites files on disk — wiping uncommitted edits from all other sessions.

**Rules:**
- **One session actively editing code at a time.** Do not run two Claude Code conversations that do git operations on the same repo simultaneously.
- **If parallel work is needed**, use `git worktree add` to give each session its own directory.
- **Verify branch immediately before every commit** — in the SAME Bash call as the commit, not in a separate tool call. Another session can switch the branch in the gap between calls.
- **Never leave edits uncommitted across multiple tool calls.** Edit then commit then next edit. Do not batch.
- **After merging a PR from a worktree session**, pull main into BOTH the main repo directory (`/c/Users/gilli/GitHub/konote`) AND the worktree directory. The user works from the worktree and needs to see changes there immediately.

## Terminal Command Rules

- **Long-running commands** (pytest with Playwright, Django server, migrations): these can take 1–5 minutes. If the terminal reports "Command is still running", **wait for the final output**. Do NOT run `echo`, `type`, or other polling commands to check status — this causes an infinite loop. The terminal will return output automatically when the command finishes.
- **PowerShell is the default shell** on this project. Use `$env:VAR = "value"` to set environment variables, not `set VAR=value` (that's CMD syntax).

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

## Development Rules (from expert review)

These rules apply to **every phase**. Do not skip them.

1. **Always create `forms.py`** — use Django `ModelForm` for validation. Never use raw `request.POST.get()` directly in views.
2. **Always extend the test suite** — when building views for a phase, add tests in `tests/` that cover the new views (permissions, form validation, happy path). Do not defer all testing to Phase 7.
3. **Always run and commit migrations** — after any model change, run `makemigrations` and `migrate`, then commit the migration files.
4. **Back up before migrating** — document/run `pg_dump` before applying migrations to a database with real data.
5. **Encrypted fields cannot be searched in SQL** — client search must load accessible clients into Python and filter in memory. This is acceptable up to ~2,000 clients. Document the ceiling.
6. **Cache invalidation** — after saving terminology, features, or settings, clear the relevant cache key. Prefer `post_save` signals over manual cache.delete() calls in views.
7. **HTMX error handling** — `app.js` must include a global `htmx:responseError` handler so network/server errors don't fail silently.

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
| Phase prompts for Claude Code | `tasks/phase-*-prompt.md` |
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

Current DRRs:
- `tasks/design-rationale/circles-family-entity.md` — Circles (family/network entity). Covers relationship modelling, privacy, adoption risk, data model decisions from two expert panels.
- `tasks/design-rationale/multi-tenancy.md` — Multi-tenancy architecture. Covers schema-per-tenant vs. alternatives, per-tenant encryption, consortium model, sequencing condition (after first single-tenant deployment).
- `tasks/design-rationale/reporting-architecture.md` — Reporting system (canonical). Template-driven + ad-hoc paths, aggregation rules, period picker, consortium pipeline, privacy safeguards. Defers to multi-tenancy.md for suppression thresholds and consent.
- `tasks/design-rationale/executive-dashboard-redesign.md` — Executive dashboard UX. Stats grid, program cards, accessibility. Monitoring only — does not produce exportable files.
- `tasks/design-rationale/offline-field-collection.md` — Offline field collection via ODK Central. PII tiers, program profiles, sync architecture, device loss protocol, iOS limitations. Three expert panels (16 perspectives).
- `tasks/design-rationale/phipa-consent-enforcement.md` — PHIPA cross-program consent enforcement. Enforcement matrix (which views need filtering), anti-patterns (rejected approaches like custom managers, middleware), deferred work (search, qualitative summary), fail-closed design.
- `tasks/design-rationale/insights-metric-distributions.md` — Insights page & program reporting. Distributions not averages, three data layers (outcomes/goals/qualitative), client-centred page hierarchy, Campbell's Law safeguards, band display labels.
- `tasks/design-rationale/bilingual-requirements.md` — Bilingual (EN/FR) requirements. Why translation is non-negotiable (Official Languages Act, Ontario FLSA, funder requirements, WCAG 3.1.2). Anti-patterns (deferring translations, treating them as low-priority). Technical approach (Claude + API backup). Translation standards for Claude sessions.
- `tasks/design-rationale/ai-feature-toggles.md` — AI feature toggle split. Two-tier design: `ai_assist_tools_only` (no participant data, default enabled) vs `ai_assist_participant_data` (de-identified participant content, default disabled). Anti-patterns (including translation in toggles, single three-level toggle). Future path: self-hosted open-source LLM for participant data.
- `tasks/design-rationale/ovhcloud-deployment.md` — OVHcloud Beauharnois deployment architecture. Full stack (Docker Compose, Caddy, PostgreSQL x2), 4-layer self-healing automation, backup strategy, Azure Key Vault for encryption keys, LLM integration, multi-agency hosting. Anti-patterns (US cloud backups, missing autoheal, single-point key storage).
- `tasks/design-rationale/data-access-residency-policy.md` — Data access residency policy. Three access tiers (direct data access, indirect, no data access). Canadian residency required for Tier 1 (SSH, DB, backups). Open questions on VPN-from-Canada, temporary travel, contractor/MSP requirements. Anti-patterns (VPN as residency substitute, production data in non-Canadian staging).
- `tasks/design-rationale/document-integration.md` — Dual document integration (SharePoint + Google Drive). SharePoint for staff-side internal documents (program-centric folders), Google Drive for participant portal working documents (digital toolkit handoff). Link-broker-only architecture, PHIPA compliance, discharge ownership transfer, operational setup guides. Anti-patterns (storing document contents, OAuth at launch, cross-program URL copying, client names in folder paths).

### How Claude Manages Tasks

- **Always `git pull origin main` before reading or updating TODO.md.** The local copy goes stale after PRs merge on GitHub. Never trust the local file without pulling first. When the user asks for the to-do list, pull first — do not skip this step or assume the local copy is current. **After merging a PR that changes TODO.md, pull main into the current working directory** (whether that's the main repo or a worktree) so the user sees the update immediately — do not wait to be asked.
- When user describes a task: create an ID, add one line to the right section in TODO.md
- When a task needs subtasks or context: create a detail file in `tasks/`
- When user asks about a task: read TODO.md for status, read `tasks/*.md` for detail
- When a task is completed: mark `[x]`, add completion date, move to Recently Done
- When Recently Done exceeds 10 items: move oldest to `tasks/ARCHIVE.md`
- When a task is blocked or needs a decision: add it to the Flagged section
- When a flag is resolved: remove it from Flagged
- Never put inline paragraphs, meeting notes, or decision detail in TODO.md

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
