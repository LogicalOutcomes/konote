# Phase 4 Prompt: Progress Notes

Copy this prompt into a new Claude Code conversation. Open the `KoNote-web` project folder first.

---

## Prompt

I'm building KoNote Web, a nonprofit client management system. Phases 1-3 are done (foundation, client/program CRUD, plans/targets/metrics). I need you to build **Phase 4: Progress Notes** — this is how staff record their work with clients.

### Context

- Read `TODO.md` for task status
- Read `C:\Users\gilli\.claude\plans\idempotent-cooking-walrus.md` for architecture
- Models in `apps/notes/models.py`: `ProgressNote`, `ProgressNoteTarget`, `MetricValue`, `ProgressNoteTemplate`, `ProgressNoteTemplateSection`, `ProgressNoteTemplateMetric`
- Plan targets and metrics are in `apps/plans/models.py`
- Use terminology: `{{ term.progress_note }}`, `{{ term.quick_note }}`, `{{ term.target }}`, `{{ term.metric }}`
- Stack: Django 5, HTMX, Pico CSS. No React.

### What to Build

**1. Quick Notes**
- Simple form: select client → text area → submit
- Creates a `ProgressNote` with `note_type="quick"` and the text in `notes_text`
- Available from the client detail Notes tab and from a "Quick Note" button on the home page
- Author and author_program set automatically from logged-in user

**2. Full Structured Notes**
- Form at `/clients/<id>/notes/new/`
- Step 1: Select a note template (or "blank note")
- Step 2: For each active plan target, show:
  - A text area for notes about this target
  - Metric inputs for each metric assigned to this target (with labels showing name, min/max, unit)
- Step 3: Optional summary text area
- Submit creates: one `ProgressNote`, multiple `ProgressNoteTarget` entries, and `MetricValue` records
- Support backdating: optional date picker if the session happened on a different day

**3. Progress Note Templates (Admin)**
- Admin UI at `/admin/settings/note-templates/`
- Create/edit templates with sections (name, type: basic or plan)
- For "basic" sections, assign specific metrics
- For "plan" sections, the form auto-includes the client's active plan targets
- Templates define the structure; actual notes fill in the values

**4. Notes Timeline View**
- On client detail Notes tab: show all notes in reverse chronological order
- Each note shows: date, author, type badge (quick/full), summary or first 200 chars
- Click to expand and see full note content, target entries, and metric values
- Use HTMX for expand/collapse without page reload
- Filter by: date range, author, note type

**5. Note Cancellation**
- Staff can cancel their own notes (within 24 hours); admins can cancel any note
- Cancelled notes show as struck-through with reason, but are never deleted
- Creates an audit log entry

### Design Guidance

- The full note form should feel like a guided workflow, not an overwhelming form
- Show one target at a time or use an accordion to keep it manageable
- Metric inputs should validate against min/max from the metric definition
- Show the metric definition (what it measures) as helper text below each input
- The timeline should be the default view when opening a client file

### Important Notes

- Staff role can create notes; Program Manager and Admin can also create notes
- All roles can view notes for clients in their assigned programs
- Commit after each major piece (quick notes, full notes, templates, timeline)
- Update `TODO.md` as tasks are completed
