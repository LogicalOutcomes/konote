# Messages Page UX Improvements (UX-MSG1)

## Problem

The Messages page ("My Messages" and per-client messages) is unclear about who is leaving a message.

- Each message card shows the **participant's name** as the most prominent element
- The actual sender appears in smaller text: "From [staff name] on [date]"
- At a glance, it looks like the **participant** wrote the message — but these are staff-to-staff messages about a participant
- Timestamps use only an absolute date/time format with no relative context
- There is no way to flag a message as urgent

## Proposed Fixes

### 1. Rework card layout to clarify roles

- Lead each card with **"Message from [Staff Name]"** as the heading
- Show the participant as context: **"Re: [Participant Name]"** or **"About: [Participant Name]"**
- This makes it immediately clear that a staff member wrote the message and who it's about

### 2. Improve timestamp readability

- Add relative time alongside the date (e.g., "Feb. 16, 2026, 3:04 p.m. — 2 hours ago")
- Use Django's `timesince` template filter or a lightweight JS helper for relative time

### 3. Add urgent flag

- Add `is_urgent` boolean field to `StaffMessage` model
- Add a checkbox or toggle on the "Leave Message" form: "Mark as urgent"
- Display urgent messages with a visual indicator (coloured border or badge)
- Sort urgent messages to the top of the list on "My Messages"

## Files Involved

- **Model**: `apps/communications/models.py` — `StaffMessage` class
- **Templates**: `templates/communications/my_messages.html`, `_message_card.html`, `leave_message.html`, `client_messages.html`
- **Views**: `apps/communications/views.py` — `my_messages`, `leave_message`
- **Form**: `apps/communications/forms.py` — message form (add urgent checkbox)
- **Migration**: new migration for `is_urgent` field
