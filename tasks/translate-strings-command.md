# Task: Build `translate_strings` Command + Startup Detection (I18N-CMD1)

## Problem

French translations keep silently breaking. The pattern repeats:
1. New template gets `{% trans %}` tags
2. Nobody adds strings to the `.po` file (because `makemessages` needs gettext, which isn't on Windows)
3. Nobody notices until a French user sees English
4. Manual fix applied, but nothing prevents the next occurrence

Two expert panels agreed: the root cause is a **workflow gap + silent failures**, not a tooling gap. Past fixes addressed specific breakages but never closed the feedback loop.

## Solution: Three-Layer Defence

```
LAYER 1 — Prevention (nice-to-have, not relied upon)
  CLAUDE.md rule + template comments reminding to run translate_strings

LAYER 2 — Detection (the real safety net)
  Expand check_translations startup command to detect missing strings
  Runs automatically at every deploy via entrypoint.sh
  Logs clear WARNING with exact fix command

LAYER 3 — Remediation (the fix)
  translate_strings command: extract + add to .po + compile .mo
  One command fixes everything
```

The key insight: **don't rely on anyone remembering to run the command. Rely on the startup check to catch and report the gap automatically.**

---

## Part 1: The Management Command

### File: `apps/admin_settings/management/commands/translate_strings.py`

**What it does (3 phases):**

```
$ python manage.py translate_strings

KoNote Translation Sync
========================

[1/3] Extracting strings...
      Templates: 1,847 strings from 124 files
      Python:      315 strings from 29 files
      Total unique: 1,623 strings

[2/3] Comparing with django.po (1,111 existing entries)...
      ✓ 1,096 already translated
      + 15 new strings added to .po (empty translation)
      ⚠ 3 existing strings with empty translation
      ℹ 12 strings in .po not found in code (possibly stale)

[3/3] Compiling django.mo...
      ✓ Compiled 1,126 entries

Summary: 18 strings need French translations.
```

**Flags:**
- No flags = extract + add missing + compile (default, always safe)
- `--dry-run` = show what would change, don't touch files
- `--translate` = future AI translation (prints "not yet configured" for now)

### String extraction logic

**Templates** — scan `templates/**/*.html`:
```python
# Regex for {% trans "string" %} and {% trans 'string' %}
pattern = r"""\{%[-\s]*trans\s+['"](.+?)['"]\s*[-]?%\}"""
```
- Handles single and double quotes
- Handles `{%-` and `-%}` whitespace trimming variants
- **Skips** `{% blocktrans %}` blocks (already in .po, regex unreliable for these)
- **Skips** `{% comment %}...{% endcomment %}` blocks

**Python files** — scan `apps/**/*.py` (skip migrations, `__pycache__`, tests):
```python
# Regex for _("string"), gettext("string"), gettext_lazy("string")
pattern = r"""(?:gettext_lazy|gettext|_)\(\s*['"](.+?)['"]\s*\)"""
```

**Known limitations (acceptable for this codebase):**
- Won't extract `{% blocktrans %}` — already in .po from earlier `makemessages` runs
- Won't extract multi-line Python string concatenation — not used in this codebase
- Won't extract `ngettext` or `pgettext` — not used in this codebase

### Adding missing strings to .po

- Use `polib` to load the .po file
- For each extracted string not in .po: create a new entry with empty `msgstr`
- Check for duplicate msgid entries before writing (error if found)
- Write to temp file first, then replace atomically (crash safety)

### Compiling .mo

- Use `polib` to save as .mo (no gettext needed)
- This replaces `python manage.py compilemessages` on Windows

---

## Part 2: Startup Detection (the safety net)

### File: `apps/admin_settings/management/commands/check_translations.py` (MODIFY existing)

**Add a new check** to the existing command — a lightweight extraction comparison:

1. Quick-scan templates for `{% trans %}` string count
2. Compare against .po entry count
3. If template strings > .po entries by more than a threshold (e.g., 5): warn

```
[WARN] Template files contain ~1,847 translatable strings but django.po
       has only 1,111 entries. Run: python manage.py translate_strings
```

**This check already runs at every deploy** via `startup_check` in `entrypoint.sh`. No new wiring needed — just add the check to the existing command.

**Why lightweight (count-based) instead of full extraction:**
- Startup needs to be fast (~60s already for migrations + seed + checks)
- Full regex extraction of 124 files adds unnecessary time
- A count comparison catches the common failure (new page with many untranslated strings)
- The full extraction lives in `translate_strings` for when you actually fix things

---

## Part 3: CLAUDE.md Rule (backup, not primary)

Add to CLAUDE.md under a new section:

```markdown
## Translations

After creating or modifying any template that uses `{% trans %}` tags:
1. Run `python manage.py translate_strings` to extract new strings and compile
2. Add French translations for any empty `msgstr` entries in the .po file
3. Commit both `locale/fr/LC_MESSAGES/django.po` and `django.mo`

If you see a startup warning about missing translations, run `translate_strings` to fix it.
```

---

## Files to Create/Modify

| File | Action | What |
|---|---|---|
| `apps/admin_settings/management/commands/translate_strings.py` | **Create** | The extraction + compilation command (~250 lines) |
| `apps/admin_settings/management/commands/check_translations.py` | **Modify** | Add lightweight extraction count check |
| `requirements-dev.txt` | **Edit** | Add `polib>=1.2.0` |
| `CLAUDE.md` | **Edit** | Add Translations section |

## Dependencies

- `polib>=1.2.0` — already installed locally, add to requirements-dev.txt
- No `anthropic` dependency needed yet (deferred to Phase G)
- No gettext needed anywhere

## Verification Steps

After building, run in this order:

1. `python manage.py translate_strings --dry-run` — should show current extraction counts and any gaps
2. `python manage.py translate_strings` — should add any missing entries and compile .mo
3. `python scripts/validate_translations.py` — should pass (no duplicates, .mo fresh)
4. `python manage.py check_translations` — should pass (canary strings translated, no count gap warning)
5. Create a test: add a new `{% trans "Test string XYZ" %}` to any template, run `translate_strings`, verify it appears in .po

## Why This Will Stick (Unlike Past Fixes)

| Past failure pattern | How this plan breaks it |
|---|---|
| Nobody remembers to run a command | Startup check detects and warns automatically — no memory needed |
| Failures are silent | Warning shows up in deploy logs every time the app starts |
| Fix is multi-step (makemessages + translate + compilemessages) | One command does everything |
| Tooling doesn't work on Windows (no gettext) | Regex + polib — pure Python, no system dependencies |
| CLAUDE.md rules get buried | CLAUDE.md rule is backup; primary detection is the startup check |
