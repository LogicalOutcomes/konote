# Fix Demo Data: Suggestion Theme Linking (DEMO-FIX1)

## Problem

The executive dashboard shows suggestion themes with incorrectly linked suggestions. For example, the "Take-home portions for families" theme in Community Kitchen displays:
- "I think having a buddy system would help new people feel less alone at the start"
- "I wish there was a way to check in between sessions when things get really hard"

Neither suggestion has anything to do with take-home portions or families.

## Root Cause

Two issues in `apps/admin_settings/management/commands/seed_demo_data.py`:

### 1. Generic suggestion pool (lines 639-645)

The 5 `PARTICIPANT_SUGGESTIONS` are program-agnostic. They rotate across all programs by `note_idx % 5`. Whether a given program's notes happen to contain suggestions that match its themes' keywords is luck of the draw.

### 2. Blind fallback linking (lines 3303-3315)

When keyword matching finds zero matches for a theme, the code links the first 2 notes from the program's pool regardless of content:

```python
if not linked_notes and notes_with_suggestions:
    for fallback_note in notes_with_suggestions[:2]:
```

This produces visibly wrong demo data.

## Fix

### Step 1: Program-specific suggestion pools

Replace the single `PARTICIPANT_SUGGESTIONS` list with a `PROGRAM_SUGGESTIONS` dict. Each program gets 3-5 suggestions that relate to its themes:

- **Supported Employment**: evening hours, peer mentoring, job interview prep
- **Housing Stability**: maintenance response, tenant rights, move-in supplies
- **Youth Drop-In**: activity variety, homework space, later hours, food options
- **Newcomer Connections**: buddy pairing, childcare, language practice
- **Community Kitchen**: take-home portions, dietary options, recipe sharing, kitchen safety

### Step 2: Fix suggestion assignment in note creation (~line 1591)

When creating notes for a program, pick suggestions from that program's pool instead of the generic list. Fall back to the generic list only for programs not in the dict.

### Step 3: Remove or improve the fallback

Option A (preferred): Remove the fallback entirely. A theme with 0 linked suggestions is better than a theme with wrong ones. The seed can log a warning if a theme has no matches.

Option B: Keep the fallback but only link notes whose suggestion text has at least one word in common with the theme name or description (loose relevance check).

### Step 4: Verify

After re-seeding, check all 11 themes on the executive dashboard to confirm linked suggestions are relevant to their themes.

## Files to Change

- `apps/admin_settings/management/commands/seed_demo_data.py` — suggestion pool, note creation, theme linking
- No model changes needed
- No migration needed
