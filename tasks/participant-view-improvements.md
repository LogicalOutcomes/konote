# Participant View Improvements — User Feedback

## CHART-TIME1: Adjustable Timeframe on Analysis Charts

**Feedback:** In the Participant analysis charts, users cannot change the timeframe or specify start/end dates. Charts currently show all data from the beginning, which makes it hard to focus on recent progress or a specific period.

**Plan:**

1. **Add date range controls** to the participant analysis/stats page — a start date picker, end date picker, and optional quick-select buttons (e.g., "Last 30 days", "Last 3 months", "Last 6 months", "All time")
2. **Filter chart data server-side** — update the view to accept date range query parameters and filter the queryset accordingly before passing data to Chart.js
3. **Preserve selected range** — use URL query parameters so the selected timeframe persists on page reload and can be shared/bookmarked
4. **Default behaviour** — default to "All time" so current behaviour is unchanged for users who don't need filtering
5. **Update French translations** for any new UI strings

**Files likely affected:**
- `apps/plans/views.py` (or whichever view renders participant analysis)
- Participant analysis template (date picker controls)
- `static/js/app.js` or chart-related JS (re-render chart on date change)
- `locale/fr/LC_MESSAGES/django.po` (translations)

---

## UX-NOTES-BY-TARGET1: Filter or Group Notes by Target

**Feedback:** In the Notes section, notes are not broken down by target. For a participant with multiple targets, staff have to read every note in full to follow progress on any single target. This is time-consuming and error-prone.

**Plan:**

1. **Add target filter/grouping to the notes list** — either:
   - **Option A (filter):** Add a dropdown or pill filter above the notes list that lets users filter notes by a specific target (showing only notes that reference that target)
   - **Option B (grouped view):** Add a toggle to switch between "All notes" (current view) and "By target" (notes grouped under target headings)
   - **Recommendation:** Start with Option A (filter) as it's simpler and covers the core need. Option B can be added later if needed.
2. **Link notes to targets** — verify that the note model already associates entries with specific targets (via metrics/progress entries). If notes reference multiple targets, they should appear under each relevant target when filtered.
3. **"All targets" default** — the default view should show all notes (current behaviour), so nothing changes for users who don't need filtering
4. **Visual indicator** — when a note covers multiple targets, show a small tag or badge on each note indicating which target(s) it relates to
5. **Update French translations** for any new UI strings

**Files likely affected:**
- `apps/notes/views.py` (add target filter parameter)
- Notes list template (filter controls, target badges)
- `apps/notes/models.py` (verify target relationship on note entries)
- `locale/fr/LC_MESSAGES/django.po` (translations)
