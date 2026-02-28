# Suggestion Tracking & Consolidation — Design Doc (UX-INSIGHT6)

## Problem

Suggestions are recorded per-note with a priority tag, and surfaced in Outcome Insights. But there's no way to:

- See the same suggestion recurring across multiple participants
- Mark a suggestion as "addressed" or "in progress"
- Track whether action was taken on feedback
- Close the feedback loop (participant suggests → staff records → PM reviews → action taken)

Staff can scroll through individual suggestion quotes in Outcome Insights, but for a program with 50+ suggestions per quarter, this becomes unmanageable. There's no consolidation, no status tracking, and no way for leadership to know whether feedback is being acted on.

## Goals

1. Let program managers group similar suggestions into **themes** (e.g., "Evening availability", "Childcare support")
2. Track the status of each theme: open → in progress → addressed (or won't do)
3. Surface active themes in Outcome Insights and the Executive Dashboard
4. Preserve participant privacy — theme names are staff-created summaries, not direct quotes

## Non-Goals (for now)

- AI-assisted auto-grouping of suggestions (Phase 2 — see Future section)
- Participant-facing feedback ("Your suggestion was addressed") — requires portal integration
- Linking to external issue trackers (Jira, Trello, etc.)

---

## Data Model

### SuggestionTheme

Represents a recurring theme identified by staff from participant suggestions.

| Field | Type | Notes |
|-------|------|-------|
| `id` | AutoField | PK |
| `program` | FK → Program | Which program this theme belongs to |
| `name` | CharField(200) | Staff-created label, e.g., "Evening availability" |
| `description` | TextField (blank) | Optional context about the theme |
| `status` | CharField | `open` / `in_progress` / `addressed` / `wont_do` |
| `priority` | CharField | `noted` / `important` / `urgent` (inherited from highest-priority linked suggestion) |
| `addressed_note` | TextField (blank) | What was done about it (filled when status changes to addressed) |
| `created_by` | FK → User | Who created the theme |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |

### SuggestionLink

Links a progress note's suggestion to a theme.

| Field | Type | Notes |
|-------|------|-------|
| `id` | AutoField | PK |
| `theme` | FK → SuggestionTheme | Which theme this belongs to |
| `progress_note` | FK → ProgressNote | The note containing the suggestion |
| `auto_linked` | BooleanField | `False` for manual links, `True` for future AI-assisted links |
| `linked_by` | FK → User (nullable) | Who linked it (null if auto-linked) |
| `linked_at` | DateTimeField | Auto |

### Indexes

- `SuggestionTheme`: `(program, status)` — for filtering active themes per program
- `SuggestionLink`: `(theme_id)` — for counting linked suggestions per theme
- `SuggestionLink`: `(progress_note_id)` — unique constraint to prevent duplicate links

---

## Permissions

| Action | Roles |
|--------|-------|
| View themes | All staff with program access |
| Create / edit themes | Program manager, admin |
| Link suggestions to themes | Program manager, admin |
| Change theme status | Program manager, admin |
| Delete themes | Admin only |

Executives can see theme summaries (name, count, status) but not individual linked suggestion text — the same privacy gate as quotes in Outcome Insights.

---

## Views & URLs

All under the existing `/reports/` or a new `/admin/suggestions/` namespace:

| URL | View | Description |
|-----|------|-------------|
| `/admin/suggestions/` | `theme_list` | List all themes for user's programs, filterable by status/program |
| `/admin/suggestions/create/` | `theme_create` | Create a new theme |
| `/admin/suggestions/<id>/` | `theme_detail` | View theme with linked suggestions, update status |
| `/admin/suggestions/<id>/link/` | `theme_link` | HTMX: link an unlinked suggestion to this theme |
| `/admin/suggestions/<id>/unlink/<link_id>/` | `theme_unlink` | HTMX: remove a link |

### Theme List Page

- Grouped by status (open first, then in_progress, then addressed)
- Each card shows: theme name, program, suggestion count, priority badge, last updated
- Filter bar: by program, by status
- "Create Theme" button (PM/admin only)

### Theme Detail Page

- Theme name, description, status, priority
- Status change buttons (open → in_progress → addressed) with optional note
- List of linked suggestion quotes (requires note.view permission)
- "Link more suggestions" section showing unlinked suggestions from the same program
- Unlinked suggestions shown as a searchable/scrollable list with checkboxes

### Linking Workflow

1. PM opens a theme detail page
2. Below the linked suggestions, they see "Unlinked suggestions from this program" — a list of suggestion quotes that aren't linked to any theme yet
3. They check boxes next to relevant suggestions and click "Link selected"
4. HTMX updates the linked list without a full page reload

---

## Integration Points

### Outcome Insights

In `_insights_basic.html`, after the existing suggestion section:

```
Active Themes
┌─────────────────────────────────────────────────┐
│ Evening availability (7 suggestions) — Important │
│ Status: In Progress                              │
├─────────────────────────────────────────────────┤
│ Childcare support (4 suggestions) — Noted        │
│ Status: Open                                     │
└─────────────────────────────────────────────────┘
View all themes →
```

Only shown if themes exist for the program. Links to theme detail page.

### Executive Dashboard

Replace current per-program suggestion count with theme-based summary:

- "3 active suggestion themes (1 important)" instead of "18 suggestions (5 important)"
- Clicking links to the theme list filtered by that program

### Progress Note Form

When saving a note with a suggestion priority set:

- After save, show a toast/banner: "This suggestion has been recorded. A Program Manager can group it with similar feedback."
- No auto-linking at this stage (Phase 1 is manual only)

---

## Phase 1: Manual Linking (build first)

- Create the two models and migrations
- Build the theme CRUD views (list, create, detail)
- Build the linking UI (checkboxes on theme detail page)
- Add theme summary to Outcome Insights
- Add theme summary to Executive Dashboard
- Theme priority auto-updates to match highest-priority linked suggestion

**Depends on:** Nothing — can be built independently.

## Phase 2: AI-Assisted Linking (future)

- When a new suggestion is saved, use semantic similarity to find matching themes
- Show a suggestion: "This looks similar to the theme 'Evening availability'. Link it?"
- Staff confirms or dismisses — the AI doesn't auto-link without approval
- Uses the same embedding infrastructure as the AI summary feature
- Set `auto_linked=True` on AI-suggested links for tracking accuracy

**Depends on:** AI infrastructure (already partially built for Outcome Insights AI summary).

---

## Privacy Considerations

- **Theme names** are staff-created plain text — not encrypted, not participant-identifying
- **Linked suggestion text** comes from `ProgressNote.participant_suggestion` which is Fernet-encrypted — only decrypted when a user with `note.view` permission views the theme detail page
- **Executive view** shows theme name + count only, never individual suggestion text
- **Audit logging**: theme creation, status changes, and linking actions are logged to the audit database
- **Minimum participant threshold**: theme summaries in Outcome Insights follow the same `MIN_PARTICIPANTS_FOR_QUOTES` gate as individual quotes

## Open Questions

1. Should themes be cross-program? (e.g., "Evening availability" might apply to multiple programs) — **Recommendation: start with per-program, consider cross-program later**
2. Should addressed themes be archived or remain visible? — **Recommendation: keep visible with a filter, auto-collapse after 90 days**
3. Should there be a "merge themes" feature for when two themes turn out to be the same? — **Recommendation: defer to Phase 2**
