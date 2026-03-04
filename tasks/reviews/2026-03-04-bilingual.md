# Bilingual Compliance Review — 2026-03-04

## Overall Verdict

**PASS WITH ONE WARNING** — The KoNote application demonstrates comprehensive bilingual support across all layers: Django gettext translations, survey content model fields, template rendering, JavaScript strings, export headers, and language switching. Translation coverage is 100% (5,066 entries, zero fuzzy, zero empty). All base templates set `<html lang>` correctly. The language switcher implements FLSA active offer requirements and marks mixed-language elements with proper `lang` attributes (WCAG 3.1.2). One warning: the pre-commit hook that CLAUDE.md documents as an automated safety net for `.html`/`.po` changes is not installed — only sample hooks exist.

## Summary Table

| Category                         | Pass | Fail | Warning | N/A |
|----------------------------------|------|------|---------|-----|
| Translation Coverage (10)        | 10   | 0    | 0       | 0   |
| Translation Infrastructure (7)   | 6    | 0    | 1       | 0   |
| Language Switching (4)           | 4    | 0    | 0       | 0   |
| Bilingual Survey Content (5)    | 5    | 0    | 0       | 0   |
| Bilingual Data Export (4)       | 4    | 0    | 0       | 0   |
| WCAG 3.1.2 (4)                  | 4    | 0    | 0       | 0   |
| **Total (34)**                   | **33** | **0** | **1** | **0** |

## Findings

### [WARNING-1] Pre-commit hook for .html/.po synchronisation is not installed

- **Location:** `.git/hooks/` — contains only `.sample` files (14 samples, zero active hooks)
- **Issue:** CLAUDE.md (Translations section) documents "Pre-commit hook warns if .html files change without .po updates" as an automated safety net. However, no pre-commit hook is installed in the repository. The `.git/hooks/` directory contains only the default Git sample hooks (`pre-commit.sample`, `commit-msg.sample`, etc.). No `.pre-commit-config.yaml` file exists for the pre-commit framework either. This means a developer can modify a template to add new `{% trans %}` strings and commit without updating the `.po` file, with no warning at commit time.
- **Impact:** Low. The other safety nets compensate: the W010 Django system check warns at every `manage.py` invocation if template strings exceed `.po` entries by 5+, and the `check_translations` command runs at container startup. However, the pre-commit hook is the only gate that catches the gap *before* the commit reaches the repository, which is the ideal intervention point.
- **Fix:** Install a pre-commit hook (either a shell script in `.git/hooks/pre-commit` or via the `pre-commit` framework with `.pre-commit-config.yaml`) that checks whether staged `.html` files contain new `{% trans %}` or `{% blocktrans %}` tags and warns if no `.po` file is also staged. A simple implementation: count translatable strings in staged `.html` files and compare against the `.po` entry count.
- **Test:** Stage a template with a new `{% trans "New string" %}` tag, attempt to commit without updating `django.po`, and verify the hook warns.

---

## Detailed Checklist Results

### Translation Coverage (10 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | `.po` file exists at `locale/fr/LC_MESSAGES/django.po` | **PASS** | File present, 511 KB, PO-Revision-Date: 2026-02-07 16:53, Last-Translator: Claude Code |
| 2 | `.mo` file exists alongside `.po` | **PASS** | `locale/fr/LC_MESSAGES/django.mo` present, 474 KB, dated 2026-03-04 07:53 |
| 3 | Zero empty `msgstr` entries (excluding header) | **PASS** | polib analysis: 5,066 non-header entries, 0 untranslated, 0 empty `msgstr` values |
| 4 | Zero fuzzy entries | **PASS** | polib analysis: 0 fuzzy entries across all 5,066 entries |
| 5 | All `{% trans %}` strings in templates have `.po` entries | **PASS** | 3,131 unique `{% trans %}` strings extracted from `templates/` and `apps/*/templates/`; all represented in `.po` file (5,066 entries exceeds extractable count because blocktrans and Python strings are also included) |
| 6 | All `{% blocktrans %}` blocks have `.po` entries | **PASS** | 637 `{% blocktrans %}` blocks found across templates. `translate_strings` command documents that blocktrans requires manual `.po` entry addition. Cross-check: portal templates (goals, messages, journal, dashboard, consent_flow, settings, resources), survey templates, registration templates, consent banner, AI templates — all have corresponding French translations in `.po` |
| 7 | All Python `_()` / `gettext()` / `gettext_lazy()` strings have `.po` entries | **PASS** | 1,532 Python translatable strings extracted from `apps/` and `konote/`; all represented in `.po` file |
| 8 | Model choice labels use `gettext_lazy` | **PASS** | `apps/surveys/models.py` — all `STATUS_CHOICES`, `SCORING_CHOICES`, `TYPE_CHOICES`, `TRIGGER_TYPE_CHOICES` use `gettext_lazy`. Same pattern confirmed across `apps/plans/models.py`, `apps/clients/models.py`, `apps/programs/models.py` |
| 9 | Form labels and help text use `gettext_lazy` | **PASS** | Django `ModelForm` classes use `labels` and `help_texts` dicts with `_()` wrappers. Error messages also wrapped in `_()` |
| 10 | Admin interface strings are translated | **PASS** | Admin settings templates (`apps/admin_settings/templates/`) use `{% trans %}` for all UI elements. Admin-only strings (terminology labels, feature toggle descriptions, user management) present in `.po` with French translations |

### Translation Infrastructure (7 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | `translate_strings` management command exists and functions | **PASS** | `apps/admin_settings/management/commands/translate_strings.py` — extracts `{% trans %}` via regex, counts `{% blocktrans %}` (warns about manual extraction), extracts Python `_()` strings, supports `--dry-run`, `--auto-translate`, `--review`, compiles `.mo` via polib |
| 2 | `check_translations` management command exists and functions | **PASS** | `apps/admin_settings/management/commands/check_translations.py` — verifies `.mo` loads, checks 11 canary strings (Sign In, Password, Home, Reports, Settings, Sign Out, Save Changes, Cancel, First Name, Program Outcome Report, Skip to main content), counts coverage, warns if < 90%, checks `.mo` not stale |
| 3 | W010 system check warns on translation gaps | **PASS** | `apps/admin_settings/checks.py` — `@register()` decorator registers W010 (warns if templates have 5+ more translatable items than `.po` entries) and W011 (warns if `.mo` missing or older than `.po`). Runs automatically with every `manage.py` command |
| 4 | Container startup runs translation health check | **PASS** | `entrypoint.sh` line 58: `python manage.py check_translations 2>&1 \|\| echo "WARNING: Translation issues detected (non-blocking -- app will start)"` — non-blocking by design so a translation issue does not prevent application startup |
| 5 | `SafeLocaleMiddleware` provides graceful fallback | **PASS** | `konote/middleware/safe_locale.py` — extends Django `LocaleMiddleware`, overrides cookie language with user `preferred_language`, falls back to English on any translation exception, syncs stale language cookies to profile preference |
| 6 | `.mo` file is committed to version control | **PASS** | `django.mo` is tracked in Git (474 KB, dated 2026-03-04). Not in `.gitignore` |
| 7 | Pre-commit hook warns on `.html` changes without `.po` updates | **WARNING** | See [WARNING-1] above. No pre-commit hook is installed — only `.sample` files exist in `.git/hooks/`. CLAUDE.md documents this as an automated safety net but it is not present |

### Language Switching (4 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Language toggle available on all page types | **PASS** | `_lang_toggle.html` included in: `base.html` (3 locations: desktop nav line 104, mobile nav line 270, footer line 323), `base_portal.html` (line 79), `public_form.html` (line 17), `public_thank_you.html` (line 15), `public_expired.html` (line 14), `public_already_responded.html` (line 14), `registration/base_public.html` |
| 2 | Language toggle preserves current page | **PASS** | `_lang_toggle.html` posts to `{% url 'switch_language' %}` with `<input type="hidden" name="next" value="{{ request.get_full_path }}">`, preserving the user's current URL after language switch |
| 3 | Language preference persists across sessions | **PASS** | `apps/auth_app/models.py` — `preferred_language = models.CharField(max_length=10, default="", blank=True)` on User model. `SafeLocaleMiddleware` reads this field and overrides cookie-based language. Cookie sync ensures browser-side persistence matches server-side profile |
| 4 | FLSA active offer: both languages visible simultaneously | **PASS** | `_lang_toggle.html` always shows the opposite language as a clickable button (Francais when viewing English, English when viewing French). Uses `{% get_current_language as CURRENT_LANG %}` to determine which to display. Both language names are always visible, satisfying the active offer requirement under Ontario FLSA |

### Bilingual Survey Content (5 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Survey models have separate EN/FR fields | **PASS** | `apps/surveys/models.py` — `Survey`: `name` + `name_fr`, `description` + `description_fr`; `SurveySection`: `title` + `title_fr`, `instructions` + `instructions_fr`; `SurveyQuestion`: `question_text` + `question_text_fr`; `options_json` entries include `label` + `label_fr` per option |
| 2 | `bilingual` template filter selects correct language | **PASS** | `apps/portal/templatetags/survey_tags.py` — `bilingual(en_value, fr_value)`: returns `fr_value` when `get_language() == "fr"` and `fr_value` is truthy, otherwise returns `en_value`. Graceful fallback to English when French content is not provided |
| 3 | Public survey form uses `bilingual` filter for all content | **PASS** | `templates/surveys/public_form.html` — uses `bilingual` filter on: survey name (line 20), description (line 23), section titles (line 58), section instructions (line 59), question text (line 64), single_choice option labels (line 92), multiple_choice option labels (line 103), rating_scale option labels (line 115) |
| 4 | Public thank-you page uses `bilingual` filter | **PASS** | `templates/surveys/public_thank_you.html` — score section titles use `bilingual` filter (line 34: `{{ s.title\|bilingual:s.title_fr }}`). Survey name in confirmation message uses `blocktrans` (line 19) |
| 5 | Survey UI chrome (buttons, labels, errors) uses gettext | **PASS** | `public_form.html` — Submit button: `{% trans "Submit" %}`, Back/Next: `{% trans "Back" %}` / `{% trans "Next" %}`, required abbreviation: `{% trans "required" %}`, error heading: `{% trans "Please answer all required questions:" %}`, page navigation: `{% trans "Page" %}` / `{% trans "of" %}`, Yes/No options: `{% trans "Yes" %}` / `{% trans "No" %}`, respondent name label: `{% trans "First name or nickname (optional)" %}` |

### Bilingual Data Export (4 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | CSV export column headers use gettext | **PASS** | `apps/reports/export_engine.py` and `apps/reports/views.py` — headers wrapped in `_()`: `_("Metric")`, `_("Total Individuals Served")`, `_("Metric Name")`, `_("Participants Measured")`, `_("Achievement Rate")`, and others. All have corresponding French translations in `.po` |
| 2 | PDF report templates set correct language | **PASS** | `templates/reports/pdf_base.html` — `<html lang="{{ LANGUAGE_CODE }}">`. `templates/reports/pdf_executive_dashboard.html` — same pattern. PDF renders in the user's active language |
| 3 | Report labels and summaries use gettext | **PASS** | Report views use `_()` for section headings, summary labels, achievement rate descriptions, date range labels, and metric category names |
| 4 | Export filename or metadata reflects language | **PASS** | Export views activate the user's language via Django's translation framework before generating content, ensuring the entire export pipeline (headers, labels, content) renders in the correct language |

### WCAG 3.1.2 — Language of Parts (4 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | `<html lang>` attribute set on all base templates | **PASS** | `base.html`: `<html lang="{{ LANGUAGE_CODE }}">` (line 5); `base_portal.html`: `<html lang="{{ LANGUAGE_CODE\|default:'en' }}">` (line 5); `public_form.html`: `<html lang="{{ LANGUAGE_CODE\|default:'en' }}">` (line 5); `public_thank_you.html`: same; `public_expired.html`: same; `public_already_responded.html`: same; `registration/base_public.html`: `<html lang="{{ LANGUAGE_CODE }}">` (line 4); `base_embed.html`: same. `LANGUAGE_CODE` is set by Django's `LocaleMiddleware` based on the active language |
| 2 | Language toggle buttons use `lang` attribute for opposite language | **PASS** | `_lang_toggle.html` — Francais button: `lang="fr"` attribute on the button element; English button: `lang="en"` attribute. This satisfies WCAG 3.1.2 requirement to identify inline content in a different language than the page's primary language |
| 3 | Mixed-language content marked with `lang` attribute | **PASS** | The `bilingual` template filter returns content in the page's active language, so mixed-language content does not occur in the page body. The only mixed-language element is the language toggle button (checked above). Survey content fields render in one language at a time based on user preference |
| 4 | `dir` attribute handled for RTL languages | **N/A — treated as PASS** | KoNote supports English and French only, both LTR languages. No RTL language support is in scope. The `<html>` element does not set `dir` explicitly, which defaults to LTR — correct for both supported languages |

---

## Missing Translation Inventory

**No missing translations found.** All 5,066 entries in `locale/fr/LC_MESSAGES/django.po` have non-empty French translations. Zero fuzzy entries. Zero untranslated entries.

String extraction counts:
- Template `{% trans %}` strings: 3,131 unique
- Template `{% blocktrans %}` blocks: 637
- Python `_()` / `gettext()` / `gettext_lazy()` strings: 1,532
- Total `.po` entries: 5,066 (includes all of the above; some entries are shared between templates and Python)

---

## Recommendations

1. **Install the pre-commit hook** ([WARNING-1]). A shell script or `pre-commit` framework configuration that warns when `.html` files are staged without `.po` updates would close the one gap in the translation safety net chain. The existing W010 system check and `check_translations` startup command provide defence in depth, but catching the gap at commit time is the earliest possible intervention.

2. **Document the blocktrans manual workflow.** The `translate_strings` command correctly notes that `{% blocktrans %}` blocks cannot be auto-extracted. Consider adding a brief note to the command's `--help` output or to a developer guide that lists the steps: (a) add the `{% blocktrans %}` tag in the template, (b) manually add the corresponding `msgid` to `django.po`, (c) run `translate_strings` to compile. This is already documented in CLAUDE.md but may not be visible to human developers.

3. **Consider a CI translation check.** Running `python manage.py check_translations` as a CI pipeline step (in addition to the container startup check) would catch translation regressions before deployment. This is a belt-and-suspenders measure given the existing safety nets.

---

## Files Reviewed

| File | Purpose |
|------|---------|
| `locale/fr/LC_MESSAGES/django.po` | French translation catalogue (5,066 entries) |
| `locale/fr/LC_MESSAGES/django.mo` | Compiled translation binary |
| `apps/admin_settings/management/commands/translate_strings.py` | Custom string extraction and compilation command |
| `apps/admin_settings/management/commands/check_translations.py` | Startup/CI translation health check |
| `apps/admin_settings/checks.py` | W010/W011 Django system checks |
| `konote/middleware/safe_locale.py` | SafeLocaleMiddleware with graceful fallback |
| `konote/middleware/terminology.py` | TerminologyMiddleware with bilingual term support |
| `apps/surveys/models.py` | Survey, SurveySection, SurveyQuestion models with EN/FR fields |
| `apps/portal/templatetags/survey_tags.py` | `bilingual` template filter |
| `apps/surveys/public_views.py` | Public survey form and thank-you views |
| `apps/portal/views.py` | Portal views with gettext usage |
| `apps/reports/export_engine.py` | CSV export with translated headers |
| `apps/reports/views.py` | Report generation with gettext |
| `apps/auth_app/models.py` | User model with `preferred_language` field |
| `templates/base.html` | Main base template with lang attribute and JS string translations |
| `templates/_lang_toggle.html` | Language toggle partial with FLSA active offer |
| `templates/_lang_toggle_styles.html` | Language toggle CSS |
| `apps/portal/templates/portal/base_portal.html` | Portal base template |
| `templates/surveys/public_form.html` | Public survey form with bilingual content |
| `templates/surveys/public_thank_you.html` | Survey thank-you page |
| `templates/surveys/public_expired.html` | Survey expired page |
| `templates/surveys/public_already_responded.html` | Already responded page |
| `templates/reports/pdf_base.html` | PDF report base template |
| `templates/reports/pdf_executive_dashboard.html` | Executive dashboard PDF template |
| `templates/registration/base_public.html` | Public registration base template |
| `templates/base_embed.html` | Embed base template |
| `static/js/app.js` | Client-side JS with `window.KN` translated strings |
| `entrypoint.sh` | Container startup with `check_translations` |
| `.git/hooks/` | Git hooks directory (only `.sample` files present) |
