# Documentation Update & Housekeeping Session

**Task IDs:** DOC-UPDATE1 (docs), HOUSE1 (housekeeping)
**Estimated agents:** 4 parallel (see bottom for grouping)

---

## Context

A large batch of features was shipped between Feb 10-16, 2026. The documentation has not kept up. This session updates all user-facing, admin, and technical docs to match the current state of the app, and cleans up miscellaneous housekeeping items.

**Before starting:** Run `git branch --show-current` and create `feat/docs-update-and-cleanup` from main.

---

## Part 1: Documentation Gaps

### A. Features missing from `docs/using-konote.md` (staff guide)

These features exist in the app but are not documented for staff:

1. **Staff messaging** — Leave and view messages on client files, unread badge in nav, "My Messages" page. Added in commit `7b4dc06`. Look at `apps/communications/views.py` for the messaging views and `templates/communications/` for the templates.

2. **Client transfer** — Dedicated transfer page with audit logging, requires `client.transfer` permission. Added in commit `7a2f690`. Look at `apps/clients/views.py` for the transfer view.

3. **Actions dropdown consolidation** — The "Actions" and "+ New" dropdowns were merged into a single Actions menu. Changed in commit `78b4ace`. Check the client detail template for the current layout.

4. **Meeting form improvements** — Location is now a proper dropdown (not a datalist), time slots are configurable. Fixed in commit `3904419`.

5. **Last-contact column** — The participant list now shows when each client was last contacted. Added in commit `7b4dc06`.

### B. Features missing from `docs/administering-konote.md` (admin guide)

1. **PM Admin Access** — Program managers can now manage their own program's templates, event types, metrics, registration links, and team members. 8 tasks completed. Look at `apps/admin_settings/views.py` and the PM nav menu for what's available.

2. **Staff portal management** — Invite flow, manage/revoke access, reset MFA for portal users. Added in commit `7b4dc06`. Look at `apps/portal/views.py`.

3. **Automated meeting reminders** — `send_reminders` management command sends reminders for meetings in the next 36 hours. Added in commit `7a2f690`. Document how to set up as a cron job / scheduled task.

4. **Weekly export summary email** — `send_export_summary` management command queries last 7 days of exports and emails a digest to admins. Added in commit `09ec4f2`. Document how to schedule.

5. **System health banners** — The staff meeting dashboard shows warnings when SMS or email services have recent failures. Added in commit `7b4dc06`. Look at `apps/communications/models.py` for `SystemHealthCheck`.

6. **Apply setup command** — `python manage.py apply_setup config.json` creates a full agency configuration from a JSON file. Already documented in `tasks/setup-wizard-design.md` but not in admin docs. Reference `apps/admin_settings/management/commands/apply_setup.py`.

7. **Setup wizard UI** — (if completed by the SETUP1-UI agent) — web-based multi-step form for initial configuration. Check if views/templates exist before documenting.

### C. Features missing from `docs/help.md` (quick reference)

1. Staff messaging (My Messages page, unread badges)
2. Client transfer (where to find it, who can do it)
3. Portal staff management (inviting portal users)
4. Meeting reminders (how they work, what staff see)

### D. Updates to `docs/index.md`

The "What's New" section needs these additions:
- Staff messaging and My Messages
- Client transfer workflow
- PM admin self-service (manage own program's config)
- Portal staff management
- Automated meeting reminders
- Weekly export summary emails
- System health monitoring banners
- Setup wizard (if completed)

The Quick Links section should add:
- Staff: [Staff Messaging](using-KoNote.md#staff-messaging)
- Staff: [Client Transfer](using-KoNote.md#transferring-a-client)
- Admins: [PM Admin Access](administering-KoNote.md#program-manager-administration)
- Admins: [Automated Reminders](administering-KoNote.md#automated-reminders)

### E. Updates to `docs/permissions-matrix.md`

Add the new permissions:
- `client.transfer` — who can transfer clients between programs
- PM admin permissions (template_edit, event_type_edit, metric_edit, registration_edit, team_edit)

### F. Updates to `docs/security-operations.md`

- Update the audit log section to note that PMs now see only entries for their assigned programs (merged in PR #88)
- Org-wide entries (login events, settings changes) are only visible to admins

### G. Updates to `docs/technical-documentation.md`

- Add new management commands: `send_reminders`, `send_export_summary`, `apply_setup`
- Add `apps/communications/` app overview (models, views)
- Add portal staff management section
- Update URL structure section if new routes were added

---

## Part 2: Housekeeping & Cleanup

### A. `.gitignore` additions

Add these missing entries:
```
.pytest_cache/
```
(Currently `__pycache__/` is ignored but `.pytest_cache/` is not)

### B. TODO.md corrections

1. **Remove AUDIT-SCOPE1** from Parking Lot — it was merged via PR #88 on 2026-02-16. Add to Recently Done: `- [x] Review and merge fix/audit-log-pm-scoping — fixes PM audit log scoping bug — 2026-02-16 (AUDIT-SCOPE1)`

2. **Remove CLEANUP1** from Parking Lot — temp folders deleted on 2026-02-16. Add to Recently Done: `- [x] Delete temporary push folders and junk files (C:Tempkonote-push, _ul, NUL) — 2026-02-16 (CLEANUP1)`

3. **Update PERF2** — if the dashboard optimization agent completed, move to Recently Done with completion date.

4. **Update SETUP1-UI** — if the setup wizard agent completed, move to Recently Done.

5. **Archive overflow** — if Recently Done exceeds 10 items, move oldest to `tasks/ARCHIVE.md`.

### C. Stale branch cleanup

Run `git branch -r --merged origin/main` to find remote branches that are already merged and can be deleted. Clean up any that are no longer needed:
```bash
# List merged remote branches (excluding main)
git branch -r --merged origin/main | grep -v main | grep -v HEAD

# For each one, delete with:
# git push origin --delete branch-name
```
**Ask before deleting** — list them and confirm with the user.

### D. Check for orphaned files

Look for files that might be leftover from refactoring:
- Any `.pyc` files committed to git (should all be gitignored)
- Any `*.orig` or `*.bak` files
- Empty `__init__.py` files in directories that no longer have Python modules
- Unused template files (templates that aren't referenced by any view)

### E. Translation coverage check

Run `python manage.py check_translations` to verify that all new template strings have French translations. The recent features added many new strings — some may be missing from `locale/fr/LC_MESSAGES/django.po`.

---

## Part 3: How to Structure the Work

### Recommended parallel agents:

| Agent | Scope | Type |
|-------|-------|------|
| **Agent 1** | Update `using-konote.md` and `help.md` — staff-facing docs (Parts 1A, 1C) | Coding — read the actual views/templates to write accurate docs |
| **Agent 2** | Update `administering-konote.md`, `index.md`, `permissions-matrix.md` — admin-facing docs (Parts 1B, 1D, 1E) | Coding — read views and management commands for accuracy |
| **Agent 3** | Update `security-operations.md` and `technical-documentation.md` — technical docs (Parts 1F, 1G) | Coding — read code to document accurately |
| **Agent 4** | All housekeeping tasks (Part 2A-E) | Mixed — .gitignore, TODO.md, branch cleanup, translations |

### Rules for all agents:

- **Read the actual code** before writing docs — don't guess what features do
- Canadian spelling (colour, organisation, centre, behaviour)
- Use **plain language** a non-developer can understand
- Match the existing tone and format of each document
- Use `{% trans %}` tag references where noting translatable strings
- WCAG 2.2 AA: ensure docs mention accessibility features where relevant
- Don't remove existing content — only add or update
- Commit each agent's work separately with clear commit messages
- End commit messages with: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
