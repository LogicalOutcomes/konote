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

**No React, no Vue, no webpack, no npm.** Keep it simple.

## Key Conventions

- Use `{{ term.client }}` in templates — never hardcode terminology
- Use `{{ features.programs }}` to check feature toggles
- PII fields use property accessors: `client.first_name = "Jane"` (not `_first_name_encrypted`)
- All `/admin/*` routes are admin-only (enforced by RBAC middleware)
- Audit logs go to separate database: `AuditLog.objects.using("audit")`
- Canadian spelling: colour, centre, behaviour, organisation, **program** (never "programme" in English — "programme" is British/French only). French translations correctly use "programme".

## Development Rules (from expert review)

These rules apply to **every phase**. Do not skip them.

1. **Always create `forms.py`** — use Django `ModelForm` for validation. Never use raw `request.POST.get()` directly in views.
2. **Always extend the test suite** — when building views for a phase, add tests in `tests/` that cover the new views (permissions, form validation, happy path). Do not defer all testing to Phase 7.
3. **Always run and commit migrations** — after any model change, run `makemigrations` and `migrate`, then commit the migration files.
4. **Back up before migrating** — document/run `pg_dump` before applying migrations to a database with real data.
5. **Encrypted fields cannot be searched in SQL** — client search must load accessible clients into Python and filter in memory. This is acceptable up to ~2,000 clients. Document the ceiling.
6. **Cache invalidation** — after saving terminology, features, or settings, clear the relevant cache key. Prefer `post_save` signals over manual cache.delete() calls in views.
7. **HTMX error handling** — `app.js` must include a global `htmx:responseError` handler so network/server errors don't fail silently.

## Translations

After creating or modifying any template that uses `{% trans %}` or `{% blocktrans %}` tags:
1. Run `python manage.py translate_strings` — this extracts, auto-translates, and compiles
2. Commit both `locale/fr/LC_MESSAGES/django.po` and `django.mo`

**For `{% blocktrans %}` blocks** (strings with variables or plurals): `translate_strings` cannot auto-extract these from templates. If you add a new `{% blocktrans %}`, you must add the corresponding msgid to the .po file manually, then run `translate_strings` to auto-translate and compile it.

**Automated safety nets** (you don't need to remember these — they run automatically):
- Django system check (W010) warns if template string count exceeds .po entries
- Pre-commit hook warns if .html files change without .po updates
- Container startup runs `check_translations` (non-blocking)

Auto-translation uses any OpenAI-compatible API. Set these environment variables:
- `TRANSLATE_API_KEY` — required to enable (works with OpenAI, Open Router, Anthropic, Ollama)
- `TRANSLATE_API_BASE` — API base URL (default: `https://api.openai.com/v1`)
- `TRANSLATE_MODEL` — model name (default: `gpt-5`)

If `TRANSLATE_API_KEY` is not set, translation is skipped — empty strings will then cause `validate_translations.py` to fail (exit code 1).

Use `--no-translate` to skip auto-translation. Use `--dry-run` to preview changes.

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
| **Parking Lot** | Future tasks, not tied to current phase | Low-priority or waiting on prerequisites |
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
| Decisions, notes, changelog | `CHANGELOG.md` |
| How Claude manages tasks | `CLAUDE.md` (this section) |
| Completed tasks older than 30 days | `tasks/ARCHIVE.md` |

### How Claude Manages Tasks

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
