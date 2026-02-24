# I18N Process Improvements — from Bilingual DRR Review

**Date:** 2026-02-24
**Source:** Expert panel review of `tasks/design-rationale/bilingual-requirements.md` (PR #36)
**DRR:** `tasks/design-rationale/bilingual-requirements.md`

---

## Context

The bilingual requirements DRR review identified several gaps between what the DRR documents as best practice and what the codebase actually does today. These are code and process changes, not documentation changes.

---

## Task 1: Resolve ~147 fuzzy PO entries (I18N-FUZZY1)

**What:** The `django.po` file has ~147 entries marked `#, fuzzy`. These are strings where the English source changed but the French translation wasn't updated. Unlike empty strings (which show English fallback), fuzzy strings display the **old French translation** — which may now be wrong or misleading.

**Why it matters:** A button that says "Save" in English but "Soumettre" (Submit) in French because the English was changed from "Submit" to "Save" but the fuzzy translation wasn't updated — this actively misleads Francophone users.

**Steps:**
1. Run `python manage.py check_translations` to get current fuzzy count
2. Open `locale/fr/LC_MESSAGES/django.po`
3. Search for `#, fuzzy` entries
4. For each fuzzy entry:
   - Read the current `msgid` (English source)
   - Check if the existing `msgstr` (French) still matches the current English meaning
   - If yes: remove the `#, fuzzy` flag (keep the translation)
   - If no: update the `msgstr` to match the new English meaning, then remove the flag
5. Run `python manage.py translate_strings` to recompile
6. Commit both `.po` and `.mo`

**Prompt for next session:**
```
Read tasks/i18n-process-improvements.md for context. Work on Task 1: resolve fuzzy PO entries.

Open locale/fr/LC_MESSAGES/django.po and search for all #, fuzzy entries. For each one, check whether the existing French translation still matches the current English msgid. If it does, remove the fuzzy flag. If it doesn't, update the French translation and remove the fuzzy flag. Use Canadian French conventions per the terminology table in tasks/design-rationale/bilingual-requirements.md.

After resolving all fuzzy entries, run python manage.py translate_strings to recompile, then commit.
```

---

## Task 2: Verify active offer compliance for language toggle (I18N-ACTIVE-OFFER1)

**What:** Under Ontario's FLSA, designated agencies must make an "active offer" of French services — the French option must be visible and accessible without the user having to search for it. The language toggle in KoNote needs to meet this standard: visible on every page, keyboard-accessible, and not buried in a menu.

**Why it matters:** If a Francophone user has to dig through settings or footer links to find the language switch, the agency using KoNote fails their active offer obligation.

**Steps:**
1. Check where the language toggle currently lives in the UI (which template, which position)
2. Verify it's visible on every authenticated page without scrolling
3. Verify it's keyboard-accessible (can Tab to it, Enter activates it)
4. Verify it has appropriate `aria-label` for screen readers
5. If any of these fail, fix them
6. Check that switching languages preserves the current page (doesn't redirect to home)

**Prompt for next session:**
```
Read tasks/i18n-process-improvements.md for context. Work on Task 2: verify active offer compliance for the language toggle.

Check the base template(s) to find where the language toggle is rendered. Verify it appears on every authenticated page, is keyboard-accessible, has an aria-label, and is visible without scrolling. If it's buried in a footer or settings page, move it to the header/nav area. Run the app locally and test the toggle works correctly in both directions (EN→FR, FR→EN) without losing the current page context.
```

---

## Task 3: Add insights-metric-distributions DRR to CLAUDE.md list (I18N-DRR-LIST1)

**What:** During the review, we noticed that `tasks/design-rationale/insights-metric-distributions.md` exists on disk but is missing from the "Current DRRs:" list in CLAUDE.md. This means future sessions won't know to read it before modifying insights/reporting features.

**Steps:**
1. Add the missing DRR entry to the "Current DRRs:" list in CLAUDE.md, after the existing entries
2. Format: `- \`tasks/design-rationale/insights-metric-distributions.md\` — Insights page & program reporting. Distributions not averages, three data layers, client-centred page hierarchy, Campbell's Law safeguards.`
3. Commit

**Prompt for next session:**
```
Read tasks/i18n-process-improvements.md for context. Work on Task 3: add the insights-metric-distributions DRR to the CLAUDE.md DRR list.

Open CLAUDE.md and find the "Current DRRs:" list. Add an entry for tasks/design-rationale/insights-metric-distributions.md. Read the DRR first to write an accurate one-line description. Commit.
```

---

## Task 4: Clean up ~628 stale PO entries (I18N-STALE1 — already in Parking Lot)

**What:** This task already exists in TODO.md as I18N-STALE1. The DRR review confirmed it's still relevant. ~628 entries in `django.po` reference strings no longer in the codebase. They bloat the file and make coverage metrics misleading (the ~84% figure includes stale entries in the denominator).

**Note:** This is a larger task. The `translate_strings` command could be enhanced to detect stale entries by comparing .po msgids against extracted template/Python strings. For now, manual cleanup or a script would work.

**Prompt for next session:**
```
Read tasks/i18n-process-improvements.md for context. Work on Task 4: clean up stale PO entries.

Run python manage.py translate_strings --dry-run to see what strings are currently extracted from templates and Python files. Then open locale/fr/LC_MESSAGES/django.po and identify entries whose msgid doesn't appear in any template or Python file. Remove those stale entries. Run translate_strings to recompile, then run check_translations to verify coverage improved. Commit.

This is a large task — if there are too many to review individually, consider writing a small script that compares extracted strings against .po entries and outputs the stale ones.
```
