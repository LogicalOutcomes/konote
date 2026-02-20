# Messages Page UX Redesign (UX-MSG1)

**Date:** 2026-02-19
**Status:** Approved
**Task:** TODO.md UX-MSG1

## Problem

The Messages page ("My Messages" and per-client messages) is unclear about who left a message. The participant's name appears as the most prominent element, making it look like the participant wrote the message — but these are staff-to-staff messages *about* a participant.

Additional issues: timestamps lack relative context, and there is no way to flag a message as urgent.

## Design Decisions

### 1. Card Layout Rework

**Current hierarchy (My Messages):** Participant name (bold link) > "From [staff] on [date]" (small) > content > Mark as Read button.

**New hierarchy:**
1. Sender name as a heading (`<h2>` on My Messages, `<h3>` on Client Messages)
2. "About: [Participant Name]" as secondary context, linked to their profile
3. Timestamp (relative + absolute)
4. Message content
5. Mark as Read button

**"For you" vs "for team" distinction:**
- Direct messages (for a specific person): full-opacity card, normal weight
- Broadcast messages (for any worker): "Team" text label, slightly muted styling

**Template changes:**
- Extract the My Messages inline card into a new partial `_my_message_card.html`
- Keep `_message_card.html` for the per-client context (it already has better structure)
- Both use `<article>` with proper heading levels

### 2. Relative Timestamps

- Server renders the absolute date inside a `<time datetime="..." title="Feb. 19, 2026, 3:04 p.m.">` element
- A lightweight vanilla JS function (~15 lines) in `app.js` updates `<time>` elements with relative text ("2 hours ago") every 60 seconds
- Fallback: if JS doesn't run, the absolute date is still visible
- Screen readers get the semantic `datetime` attribute; hover shows absolute time via `title`

### 3. Urgent Flag

**Model:** Add `is_urgent = BooleanField(default=False)` to `StaffMessage`.

**Form:** Add "Mark as urgent" checkbox to the leave-message form (`StaffMessageForm`).

**Visual treatment:**
- Left coloured border using `--kn-urgent` CSS variable (works in light and dark mode)
- "Urgent" text label alongside the border (not colour alone — WCAG 1.4.1)

**Sorting:**
- My Messages: sort urgent-first, then by date (`.order_by("-is_urgent", "-created_at")`)
- Client Messages: keep chronological order (timeline matters more)

### 4. Focus Management

After "Mark as Read" HTMX swap, move focus to the next unread `<article>`. This supports keyboard triage workflows where staff process multiple messages in sequence.

## Files to Change

| File | Change |
|------|--------|
| `apps/communications/models.py` | Add `is_urgent` field to `StaffMessage` |
| `apps/communications/forms.py` | Add `is_urgent` checkbox to `StaffMessageForm` |
| `apps/communications/views.py` | Update `my_messages` query ordering; pass `is_urgent` to template |
| `templates/communications/my_messages.html` | Rework card layout, use new partial |
| `templates/communications/_my_message_card.html` | New partial for My Messages card |
| `templates/communications/_message_card.html` | Add heading level, urgent indicator, timestamp |
| `templates/communications/leave_message.html` | Add urgent checkbox |
| `templates/communications/client_messages.html` | Minor heading level adjustment |
| `static/css/main.css` | Add `--kn-urgent`, `.message-urgent`, team/direct styles |
| `static/js/app.js` | Add relative timestamp updater function |
| New migration | For `is_urgent` field |
| `locale/fr/LC_MESSAGES/django.po` | French translations for new strings |

## Deferred

- Acknowledgement/supervisor visibility — future enhancement
- Filter controls for urgent/unread/team — not needed until message volume warrants it
- Push notifications for urgent messages — alert fatigue risk
