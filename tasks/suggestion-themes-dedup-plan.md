# Fix: Duplicate Suggestion Theme Categories on Dashboard & Insights

## Problem
Executive Dashboard and Insights reports show duplicate theme categories
(e.g., "Recipe variety and dietary options" appears twice — once with count 2,
once with count 0). Categories should never repeat; that's the whole point of
grouping suggestions into themes.

## Root Cause
The `SuggestionTheme` model has **no unique constraint on (program, name)**.
Multiple records with the same name can exist for the same program. The AI
engine (`process_ai_themes`) does a `name__iexact` check before creating, but
the manual form (`SuggestionThemeForm`) has zero duplicate checking. Even the
AI path is fragile — whitespace differences or race conditions can slip through.

## Expert Panel Consensus
A panel of 4 specialists (Software Engineer, Root Cause Analyst, Systems
Thinker, UX Designer) agreed on a layered approach:
- **Display layer** (P0): Deduplicate in views so users see correct output now
- **Data cleanup** (P1): Management command to merge existing duplicates
- **Prevention** (P1): Form validation + AI engine hardening
- **Database constraint** (P2): Belt-and-suspenders unique constraint

## Implementation Plan

Working directory: `.worktrees/fix-suggestions-reports/` (branch `fix/suggestions-reports`)

### Step 1: Deduplicate in `_batch_top_themes()` (dashboard_views.py)
**File:** `apps/clients/dashboard_views.py` lines 405-454

After fetching themes, group by `(program_id, lower(name))`:
- Sum `link_count` across duplicates
- Keep the highest priority (lowest PRIORITY_RANK value)
- Keep the most recent `updated_at`
- Use the `pk` and `name` from the kept record

This ensures the Executive Dashboard never shows the same category twice.

### Step 2: Deduplicate in insights view (insights_views.py)
**File:** `apps/reports/insights_views.py` lines 113-128

For both `active_themes` and `addressed_themes` querysets, add Python-side
deduplication that groups by `lower(name)`, summing link counts and keeping
highest priority. Apply this before passing to the template.

### Step 3: Add duplicate name validation to SuggestionThemeForm
**File:** `apps/notes/forms.py` — `SuggestionThemeForm` class

Add a `clean_name()` method that:
1. Strips whitespace and collapses multiple spaces
2. Checks for existing theme with same name (case-insensitive) in the same program
3. Excludes the current instance (for edits)
4. Returns a helpful error: "A theme called 'X' already exists in this program."

### Step 4: Harden AI engine name matching
**File:** `apps/notes/theme_engine.py` — `process_ai_themes()` function

- Normalize `theme_name` before lookup: strip, collapse whitespace
- When matched theme has status "addressed": reopen it to "open" (the AI is
  finding new suggestions for that category, so it's active again)
- Log when a theme is reopened

### Step 5: Data cleanup management command
**New file:** `apps/notes/management/commands/merge_duplicate_themes.py`

For each program, find themes with duplicate names (case-insensitive):
- Keep the oldest (lowest pk) as the canonical record
- Move all SuggestionLinks from duplicates to the keeper (ignore_conflicts=True)
- Recalculate priority on the keeper
- Delete the duplicates
- Log every merge action to stdout

Support `--dry-run` flag. Run against the actual database before adding a
unique constraint.

### Step 6: Database migration — unique constraint
**New migration** in `apps/notes/migrations/`

Add `UniqueConstraint(fields=["program", "name"], name="unique_theme_name_per_program")`.
The data migration in Step 5 must be run first to ensure no duplicates exist.

For cross-database compatibility (SQLite dev + PostgreSQL prod), this is a
plain field-level constraint (not using Lower()). Application-level
normalization (strip + collapse spaces in form and AI engine) ensures names
are consistent before hitting the constraint.

### Step 7: Tests
- Test that `_batch_top_themes()` deduplicates by name
- Test that insights view deduplicates active themes
- Test that `SuggestionThemeForm` rejects duplicate names
- Test that `process_ai_themes()` reopens addressed themes
- Test the management command merges correctly

### Step 8: Run existing tests
Run the full test suite to ensure no regressions.

## Files Changed
| File | Change |
|------|--------|
| `apps/clients/dashboard_views.py` | Deduplicate in `_batch_top_themes()` |
| `apps/reports/insights_views.py` | Deduplicate active + addressed themes |
| `apps/notes/forms.py` | Add `clean_name()` to `SuggestionThemeForm` |
| `apps/notes/theme_engine.py` | Normalize names, reopen addressed themes |
| `apps/notes/management/commands/merge_duplicate_themes.py` | New: cleanup command |
| `apps/notes/migrations/NNNN_*.py` | New: unique constraint migration |
| `tests/test_dashboard_suggestions.py` | New test for dedup |
| `apps/notes/tests/test_suggestion_themes.py` | New tests for form + engine |
