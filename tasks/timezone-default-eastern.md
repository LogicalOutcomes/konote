# UX-TIME1 — Timezone default and local time handling

## Problem
Some screens show incorrect times. The expected behaviour is that KoNote defaults to Eastern Time and uses local time correctly when users enter or view date/time values.

## Decision / Scope
- Default application timezone is Eastern Time (`America/Toronto`).
- Date/time input should be interpreted from the user’s local context and stored in timezone-aware form.
- Displayed timestamps should be shown consistently in Eastern Time unless a future per-user timezone feature is introduced.

## Implementation Notes (MVP)
1. **Django settings**
   - Confirm `TIME_ZONE = "America/Toronto"`.
   - Keep `USE_TZ = True`.
2. **Storage**
   - Keep persisted timestamps timezone-aware (UTC in DB via Django standard behaviour).
3. **Forms and parsing**
   - Ensure datetime forms parse browser-provided local values safely and convert to aware datetimes before save.
   - Avoid mixing naive and aware datetimes in view/form logic.
4. **Templates / UI display**
   - Ensure displayed timestamps use Django timezone utilities and render in Eastern Time consistently.
5. **Tests**
   - Add/adjust tests that verify:
     - Saved values remain correct when entered from local/browser time input.
     - Rendered values show expected Eastern Time output.

## Acceptance Criteria
- A user entering a date/time in the UI sees the expected time after save.
- The same record displays the correct Eastern Time across participant detail, notes/events, and exports where applicable.
- No naive/aware datetime warnings/errors in tests.

## Out of Scope (for now)
- Per-user selectable timezone.
- Automatic browser timezone profile setting.
