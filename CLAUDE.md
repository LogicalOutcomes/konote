# KoNote Web — Project Instructions

## What This Is

A secure, web-based client outcome management system for nonprofits. Agencies define desired outcomes with clients, record progress notes with metrics, and visualise progress over time. Each agency runs their own instance.

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
- Canadian spelling: colour, centre, behaviour, organisation

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
