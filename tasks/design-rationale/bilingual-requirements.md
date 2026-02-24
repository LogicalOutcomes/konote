# Bilingual Requirements — Design Rationale Record

**Feature:** English–French bilingual interface for all user-facing content
**Status:** Approved — standing requirement, not a phase-gated feature
**Date:** 2026-02-24
**Task ID:** I18N-DRR1
**Related files:** `CLAUDE.md` (Translations section), `locale/fr/LC_MESSAGES/django.po`, `apps/admin_settings/management/commands/translate_strings.py`, `apps/admin_settings/management/commands/check_translations.py`, `konote/middleware/safe_locale.py`

---

## Keyword Index

bilingual, French, English, official languages, i18n, l10n, translation, django.po, django.mo, translate_strings, blocktrans, trans tag, .po file, .mo file, polib, SafeLocaleMiddleware, language cookie, preferred_language, WCAG 3.1.1, Official Languages Act, French Language Services Act, FLSA, Ontario, AODA, funder requirements, nonprofit, Claude translation, API translation, gettext, compilemessages, check_translations, canary strings, translation coverage, deferred translation, string extraction

---

## How to Use This Document

This record exists because AI coding assistants (including Claude) have a persistent tendency to deprioritise translation work — suggesting it be deferred, skipped, or done in a "polish" phase. This document explains why that is not acceptable for KoNote and establishes the rules that every development session must follow.

**Rules for future sessions:**
1. Read this document before suggesting that translation work be deferred or deprioritised
2. Every template change that adds or modifies user-facing text **must** include French translations in the same commit
3. If a proposed change skips translations "to save time" or "for a later pass," it violates this DRR — do not proceed without explicit stakeholder approval
4. Translation is not polish. It is a functional requirement with legal, contractual, and accessibility dimensions.

---

## Why Bilingual Is Non-Negotiable

KoNote is built for Canadian nonprofits. In Canada, bilingual service delivery is not a courtesy — it is a legal obligation, a funder expectation, and an accessibility requirement. The rationale has four independent legs. Any one of them alone would be sufficient.

### 1. Federal Official Languages Act (R.S.C., 1985, c. 31; modernised 2023)

Canada's Official Languages Act establishes English and French as equal official languages. The 2023 modernisation (Bill C-13) strengthened obligations for digital services and extended protections to organisations that deliver services on behalf of federal institutions.

**How this applies to KoNote:**
- Nonprofits that receive federal funding (Employment and Social Development Canada, Immigration Refugees and Citizenship Canada, Canadian Heritage, etc.) are often contractually required to deliver services in both official languages.
- When a nonprofit delivers a federally funded program, the software it uses to manage that program is part of the service delivery infrastructure. A unilingual English case management system means unilingual English service records — which means a Francophone participant's file is maintained in a language they cannot read.
- Federal funders increasingly audit digital tools as part of official languages compliance reviews.

**Practical impact:** An agency using KoNote to deliver an IRCC-funded settlement program in Ottawa (a designated bilingual region) must be able to operate the system in French. If KoNote cannot do this, the agency cannot use KoNote for that program.

### 2. Ontario French Language Services Act (R.S.O. 1990, c. F.32)

Ontario's FLSA requires government agencies and designated organisations in 26 designated areas to provide services in French. Over 250 nonprofit organisations in Ontario have sought FLSA designation — meaning they have a legal obligation to serve Francophone communities in French.

**How this applies to KoNote:**
- KoNote's initial deployment targets Ontario nonprofits. Many operate in designated areas (Ottawa, Toronto, Sudbury, Hamilton, etc.) where roughly 80% of Ontario's Francophone population lives.
- FLSA-designated agencies must provide services in French "of comparable quality" to English services. A system where French translations are incomplete, stale, or missing for key screens fails this standard.
- Even non-designated agencies in Ontario serve Francophone participants. A case management system that only works properly in English creates a two-tier service experience.

### 3. Funder and Partner Requirements

Beyond legal obligations, bilingualism is a practical market requirement:

- **United Way / Centraide** operates bilingually across Canada. Funded agencies are expected to demonstrate bilingual capacity.
- **Ontario Trillium Foundation** has an explicit French Language Services Policy requiring funded organisations to consider Francophone community needs.
- **Provincial ministries** (e.g., Ontario Ministry of Children, Community and Social Services) include bilingual service delivery in contribution agreements.
- **Common Approach / CIDS** (which KoNote plans to support — see `tasks/cids-json-ld-export.md`) operates bilingually and expects compliant tools to do the same.

**Practical impact:** When KoNote is evaluated for adoption by a funder-affiliated agency, "Is it available in French?" is a yes/no gating question. "We'll add French later" is functionally the same answer as "No."

### 4. WCAG 2.2 AA / AODA Accessibility

WCAG Success Criterion 3.1.1 requires that the default human language of each page be programmatically determinable. WCAG 3.1.2 requires that the language of each passage or phrase be identifiable when it differs from the page language.

**How this applies to KoNote:**
- KoNote commits to WCAG 2.2 AA compliance (see CLAUDE.md).
- A page served with `lang="fr"` that contains untranslated English strings violates SC 3.1.2 — screen readers will attempt to pronounce English text with French phonetics, producing incomprehensible output.
- AODA (Accessibility for Ontarians with Disabilities Act) requires WCAG 2.0 Level AA for Ontario organisations. Incomplete translations are an accessibility failure, not just a localisation gap.

---

## Anti-Patterns: DO NOT Do These Things

### DO NOT defer translations to a "polish" or "cleanup" phase

**What it looks like:** A feature is built with `{% trans %}` tags in templates but French translations are left empty in the .po file. A task is created: "Add French translations for Feature X." The task sits in Coming Up or Parking Lot.

**Why it seems like a good idea:** "Let's get the feature working first, then translate." It feels efficient — focus on functionality, handle presentation later.

**Why it is rejected:**

1. **Translation debt compounds.** Every untranslated string is a line item that someone must return to. Context is lost — the developer who wrote the string has moved on. The translator must re-read the template, understand the UI context, and craft an appropriate translation. This takes 3-5x longer than translating at the time of writing.

2. **Deferred translations never get done.** In a nonprofit project with limited development cycles, there is always a higher-priority task than "go back and translate 30 strings from three weeks ago." The backlog grows. Coverage drops. The French interface degrades from "good" to "embarrassing" to "unusable."

3. **It creates a broken product for Francophone users.** A French-speaking caseworker who switches to French and sees half the interface in English and half in French has a worse experience than if the entire interface were in English. Mixed-language interfaces are confusing, unprofessional, and signal that French users are an afterthought.

4. **It violates WCAG 3.1.2.** A `lang="fr"` page with English strings is an accessibility failure, not a cosmetic issue.

**The rule:** Every commit that adds or changes user-facing text must include the corresponding French translation. No exceptions. No "I'll come back to it." The translation is part of the feature, not an add-on.

*Source: Observed pattern across 8+ development sessions where Claude suggested deferring translation work. Each time, the deferred strings accumulated and required a dedicated cleanup session.*

---

### DO NOT treat translation as a low-priority task

**What it looks like:** A development session has three tasks: build a new view, write tests, add translations. When time is short, translations are the first thing cut. Or: Claude generates a TODO item like "Extract and translate French strings (~25-30 new strings)" and places it in Coming Up rather than completing it as part of the current work.

**Why it seems like a good idea:** Tests verify correctness. The view delivers functionality. Translations are "just text." If something has to give, translations seem like the lowest-risk thing to skip.

**Why it is rejected:** Translations are a functional requirement (see the four legal/contractual/accessibility reasons above). Shipping a feature without translations is like shipping a feature without form validation — it works for some users but fails for others. The question is not "is this important enough to do?" but "for whom does the product break if we skip this?"

**The rule:** Translation has equal priority with tests. A feature is not complete until it has tests AND translations.

---

### DO NOT use machine translation services without human review for clinical/legal UI text

**What it looks like:** Piping all .po file entries through Google Translate or DeepL and committing the output directly.

**Why it seems like a good idea:** Fast, cheap, covers everything.

**Why it is rejected for certain categories of text:**

1. **Clinical terminology.** Terms like "progress note," "outcome," "discharge," and "assessment" have specific French equivalents in Canadian social services ("note d'évolution," "résultat," "congé," "évaluation"). Machine translation may produce technically correct but contextually wrong terms — e.g., "résultat" (correct in evaluation context) vs. "issue" (correct in litigation context).

2. **Legal/privacy text.** PIPEDA consent language, PHIPA disclosures, and data retention notices must use precise terminology. A mistranslation in a consent form could have legal consequences.

3. **Terminology overrides.** KoNote's terminology system (`{{ term.client }}`) allows agencies to customise terms. The French equivalents of these custom terms must match the agency's own French usage, not a machine's guess.

**What IS acceptable:** Using Claude (which understands Canadian French conventions and social services context) for initial translations, then applying human review for clinical/legal strings. Claude's translations are significantly better than generic machine translation for this domain because it can be given context about the application, the sector, and Canadian French norms.

**The rule:** Claude-generated translations are the primary workflow. An API-based translation service is the backup for when Claude is unavailable. All clinical, legal, and privacy-related strings should be flagged for human review during periodic translation spot-checks (see `I18N-REV1` in TODO.md).

---

### DO NOT add user-facing text without wrapping it in translation tags

**What it looks like:** A template contains `<h2>Program Overview</h2>` instead of `<h2>{% trans "Program Overview" %}</h2>`.

**Why it happens:** Developer forgets, or doesn't realise the text is user-facing, or thinks "this is just a heading, it doesn't need translation."

**Why it is rejected:** Every piece of text that a user reads must be translatable. Headings, button labels, error messages, help text, placeholder text, empty-state messages, confirmation dialogs, navigation labels — all of it.

**The rule:** If a human reads it, wrap it in `{% trans %}` or `{% blocktrans %}`. If you're unsure whether something is user-facing, it probably is. The `translate_strings` extraction command and the W010 system check will catch many gaps, but prevention is better than detection.

---

### DO NOT create separate "English version" and "French version" templates

**What it looks like:** `client_list_en.html` and `client_list_fr.html`, or `{% if LANGUAGE_CODE == 'fr' %}` conditionals to show different content blocks.

**Why it seems like a good idea:** "The French layout needs to be different because French text is longer."

**Why it is rejected:** Two templates means every future change must be made twice. Within a month, the templates diverge. Django's i18n framework exists specifically to avoid this. Use `{% trans %}` and `{% blocktrans %}` for text substitution. Use CSS (not template conditionals) to handle text-length differences.

**The rule:** One template per view. Language switching is handled by Django's translation framework, not by template branching.

---

## Decided Trade-offs

### Claude-generated translations vs. professional human translation

- **Chosen:** Claude as primary translator, with periodic human review
- **Alternative:** Professional translation agency for all strings
- **Trade-off:** Professional translation is more accurate but costs $0.15-0.25/word, creates a bottleneck (2-5 day turnaround), and is impractical for a project that adds 10-50 strings per development session
- **Reason:** Claude understands Canadian French norms, social services terminology, and can translate in the same commit as the code change. The translation-per-commit workflow is only possible with an AI translator. Professional translation would force batch translation (the anti-pattern above).
- **Mitigation:** Periodic human review (I18N-REV1), canary string verification (check_translations command), and the pre-commit hook ensure translations stay healthy
- **Domains:** Cost, Workflow, Quality

### translate_strings custom command vs. standard Django makemessages/compilemessages

- **Chosen:** Custom `translate_strings` management command using `polib`
- **Alternative:** Standard `django-admin makemessages` + `compilemessages` (requires GNU gettext)
- **Trade-off:** Custom command cannot extract `{% blocktrans %}` blocks automatically (regex limitation)
- **Reason:** GNU gettext is not reliably available on Windows development environments. The project owner develops on Windows. A pure-Python solution (polib) eliminates a system dependency that has caused setup failures in the past. The `blocktrans` limitation is manageable — these blocks are less common and can be added manually.
- **Mitigation:** CLAUDE.md documents the blocktrans manual-add requirement. The W010 system check catches gaps.
- **Domains:** Developer Experience, Cross-platform

### Translation API backup vs. Claude-only workflow

- **Chosen:** Claude as primary, with a deferred API integration (I18N-API1) for production use
- **Alternative:** API-first (DeepL or Google Translate) for all translations
- **Trade-off:** No automated translation when Claude is unavailable (e.g., a non-AI-assisted developer contributing)
- **Reason:** During development, Claude is always present (it's the development tool). An API adds cost, latency, and a dependency. But for production scenarios (e.g., a self-hosted agency adding custom terminology), an API fallback is needed.
- **Mitigation:** The I18N-API1 parking lot item tracks this. When built, it should be a fallback in the `translate_strings` command — attempt Claude-style contextual translation first, fall back to API.
- **Domains:** Cost, Resilience, Self-service

### Translate at commit time vs. translate at deploy time

- **Chosen:** Translate at commit time (translations are in version control)
- **Alternative:** Translate dynamically at runtime or during CI/CD
- **Trade-off:** Translations must be maintained as part of the codebase
- **Reason:** Runtime translation adds latency and a point of failure. Version-controlled translations are reviewable, testable, and cacheable. The .po/.mo files are the source of truth — not an API response.
- **Mitigation:** Pre-commit hook ensures .po and .mo stay in sync. check_translations verifies coverage at startup.
- **Domains:** Reliability, Auditability

---

## Technical Approach

### How Translation Works in KoNote

KoNote uses Django's standard i18n framework with custom tooling to make it work smoothly on Windows and with AI-assisted development.

**The translation pipeline:**

```
1. Developer adds text to template:
   <h2>{% trans "Program Overview" %}</h2>

2. Developer runs: python manage.py translate_strings
   → Extracts all {% trans %} strings from templates
   → Extracts all _() / gettext() strings from Python files
   → Adds new entries to locale/fr/LC_MESSAGES/django.po
   → Compiles django.po → django.mo

3. Developer (Claude) fills in French translations in django.po:
   msgid "Program Overview"
   msgstr "Aperçu du programme"

4. Developer runs: python manage.py translate_strings
   → Recompiles django.mo with the new translations

5. Developer commits both django.po and django.mo
```

**For `{% blocktrans %}` blocks** (strings with variables or plurals):

```
1. Developer adds blocktrans to template:
   {% blocktrans count count=items %}
     {{ count }} item
   {% plural %}
     {{ count }} items
   {% endblocktrans %}

2. Developer manually adds the msgid to django.po:
   msgid "%(count)s item"
   msgid_plural "%(count)s items"
   msgstr[0] "%(count)s élément"
   msgstr[1] "%(count)s éléments"

3. Developer runs: python manage.py translate_strings
   → Compiles the updated .po file
```

### Quality Assurance

| Check | When It Runs | What It Catches |
|-------|-------------|----------------|
| W010 system check | Every `manage.py` command | Template strings that aren't in the .po file |
| W011 system check | Every `manage.py` command | Missing or stale .mo file |
| Pre-commit hook | Every `git commit` | .po changed without recompiling .mo |
| `check_translations` command | Container startup, manual | Corrupted .mo, missing canary strings, coverage <90% |
| I18N-REV1 recurring task | Periodically (manual) | Mistranslations, awkward phrasing, terminology drift |

### SafeLocaleMiddleware

The custom `SafeLocaleMiddleware` handles edge cases that Django's built-in `LocaleMiddleware` does not:

- **User preference override:** Uses the `preferred_language` field on the user model, not just the cookie. Prevents language "bleed" on shared browsers (BUG-4).
- **Graceful degradation:** If the .mo file is corrupted or missing, falls back to English with a logged warning instead of crashing.
- **WCAG compliance:** Always sets the `lang` attribute on the response to match the user's actual language, even if translations are incomplete (BUG-14).

---

## Risk Registry

### Translation Debt Accumulation (HIGH — primary risk)

**What:** Translations fall behind as new features are added. Coverage drops below 90%. The French interface becomes increasingly broken.

**Consequence:** Francophone users cannot use the system effectively. Agencies in designated bilingual areas cannot adopt KoNote. Funder compliance audits fail.

**Mitigation:**
- The "translate in the same commit" rule prevents accumulation
- W010 system check warns when template strings exceed .po entries
- `check_translations --strict` fails the build when coverage drops below 90%
- Pre-commit hook prevents committing template changes without .po updates

**Monitor:** Run `python manage.py check_translations` weekly. Track the number of empty msgstr entries over time. If the count trends upward across 3+ sessions, investigate which sessions are skipping translations.

### Translation Quality Drift (MEDIUM)

**What:** Claude-generated translations are grammatically correct but use incorrect terminology for the social services sector, or drift from Canadian French norms toward European French.

**Consequence:** Francophone staff find the interface awkward or confusing. Terms don't match what they use in their practice. Trust in the tool decreases.

**Mitigation:**
- Canary strings in `check_translations` verify critical terms (e.g., "Sign In" → "Connexion," not "Se connecter")
- I18N-REV1 recurring task schedules periodic human review
- CLAUDE.md instructs Claude to use Canadian French conventions
- The terminology override system (`{{ term.client }}`) lets agencies customise key terms in both languages

**Monitor:** During human review sessions, count terminology corrections. If >5% of reviewed strings need terminology fixes (not just phrasing preferences), add more domain-specific translation guidance to CLAUDE.md.

### blocktrans Extraction Gap (MEDIUM)

**What:** The `translate_strings` command cannot auto-extract `{% blocktrans %}` strings from templates. A developer adds a new `blocktrans` block but forgets to manually add the msgid to the .po file.

**Consequence:** The string appears untranslated in the French interface. The W010 system check may not catch it (it counts blocktrans blocks but cannot verify individual msgids).

**Mitigation:**
- CLAUDE.md documents the manual-add requirement
- W010 counts blocktrans blocks and warns if the count increases without corresponding .po additions
- Code review should check for new blocktrans blocks

**Monitor:** After each session that adds templates, verify blocktrans coverage by switching to French and visually checking new screens.

### Developer Bypasses Pre-commit Hook (LOW)

**What:** A developer uses `git commit --no-verify` to skip the pre-commit hook and commits out-of-sync .po/.mo files.

**Consequence:** The deployed .mo file doesn't include recent translations. Strings appear untranslated until someone recompiles.

**Mitigation:**
- Container startup runs `check_translations` (catches stale .mo)
- W011 system check warns if .mo is older than .po
- CI/CD should include `check_translations --strict` (not yet implemented)

**Monitor:** If translations appear missing in production that exist in the .po file, check .mo compilation date.

### Loss of AI Translation Capability (LOW)

**What:** Claude Code is unavailable (service outage, licensing change, discontinued) and no human French translator is on the team.

**Consequence:** New features cannot be translated. The French interface stalls at the last-translated version.

**Mitigation:**
- I18N-API1 (parking lot) implements an API-based translation fallback in `translate_strings`
- The .po file format is standard GNU gettext — any translation tool or service can work with it
- A freelance Canadian French translator can be engaged for ~$0.15-0.25/word
- The existing translated corpus (4,100+ strings) provides terminology reference for any future translator

**Monitor:** If Claude becomes unavailable for >2 development sessions, prioritise I18N-API1.

---

## Graduated Complexity Path

### Level 1: Current State (implemented)

- Django i18n framework with `{% trans %}` and `{% blocktrans %}` tags
- Custom `translate_strings` command (pure Python, no system dependencies)
- `check_translations` command with canary strings and coverage reporting
- Pre-commit hook for .po/.mo sync
- SafeLocaleMiddleware with user preference override
- Claude-generated translations in development workflow
- ~84% coverage (4,100+ strings, ~650 untranslated)

**Current priority:** Reach and maintain 95%+ coverage. Clean up ~628 stale entries (I18N-STALE1). Complete translations for insights/metrics templates (INSIGHTS-I18N1).

### Level 2: API Translation Fallback (build when triggered)

**Trigger:** A non-AI-assisted developer needs to add translations, OR Claude becomes unavailable for >2 sessions, OR a self-hosted agency needs to translate custom terminology without developer assistance.

**Scope:** Add `--auto-translate` flag to `translate_strings` that calls a translation API (DeepL preferred for Canadian French quality) for empty msgstr entries. Include a `--review` flag that marks API-translated strings as fuzzy for human review.

**Prerequisite:** API key management infrastructure exists (environment variable or admin settings).

### Level 3: Agency Self-Service Translation (build when triggered)

**Trigger:** Multi-tenant deployment (see `tasks/design-rationale/multi-tenancy.md`) where agencies customise terminology and need those customisations translated.

**Scope:** Admin UI for reviewing and editing translations of custom terminology. Preview of how terms appear in both languages. Integration with the terminology override system.

**Prerequisite:** Multi-tenancy implemented. At least one Francophone agency actively using the system.

### Level 4: Additional Languages (build when triggered)

**Trigger:** An agency serves a community where a third language is dominant (e.g., Arabic, Mandarin, Cree) and requests interface translation.

**Scope:** Add a third language to `LANGUAGES` in settings. Extend `translate_strings` to handle multiple target languages. Add language selector to user preferences.

**Prerequisite:** Level 2 (API fallback) implemented — manual translation of 4,000+ strings into a third language is not feasible without automation. Community review process established for the new language.

---

## Translation Standards for Claude Sessions

When Claude is translating strings in a development session, these standards apply:

### Canadian French Conventions

- Use Canadian French ("courriel" not "e-mail," "connexion" not "login," "téléverser" not "uploader")
- Follow Office québécois de la langue française (OQLF) recommendations where they exist
- Use "vous" (formal) for all UI text, never "tu"
- Use inclusive writing where practical (e.g., "les participant·e·s" or "les personnes participantes") — follow the agency's preference if known

### Social Services Terminology

| English | French | Notes |
|---------|--------|-------|
| Participant | Participant(e) | Not "client" unless agency terminology overrides |
| Progress note | Note d'évolution | Not "note de progrès" (calque) |
| Outcome | Résultat | In evaluation context |
| Discharge | Congé | Not "décharge" (legal context) |
| Assessment | Évaluation | Not "estimation" |
| Case worker | Intervenant(e) | Not "travailleur de cas" (calque) |
| Intake | Accueil / Admission | Context-dependent |
| Program | Programme | Standard in both languages |
| Goal | Objectif | Not "but" (too informal for case plans) |

### What Gets Translated

| Content Type | Translate? | Notes |
|-------------|-----------|-------|
| Template text (headings, labels, buttons) | Yes | `{% trans %}` or `{% blocktrans %}` |
| Form field labels and help text | Yes | In forms.py via `_()` or in template |
| Error messages | Yes | Both form validation and server errors |
| Email subject lines and body text | Yes | Via `_()` in Python |
| Admin settings labels | Yes | Staff-facing, not just admin |
| Help text and onboarding content | Yes | Critical for adoption |
| Placeholder text | Yes | Visible to users |
| PDF report text | Yes | Via `_()` in report generation code |
| URL slugs | No | Keep English for consistency |
| Log messages | No | Developer-facing, not user-facing |
| Code comments | No | Developer-facing |
| API error codes | No | Machine-readable |
| Database field names | No | Internal |

---

## References

- [Official Languages Act (R.S.C., 1985, c. 31)](https://laws-lois.justice.gc.ca/eng/acts/o-3.01/page-1.html)
- [Action Plan for Official Languages 2023–2028](https://www.canada.ca/en/canadian-heritage/services/official-languages-bilingualism/official-languages-action-plan/2023-2028.html)
- [Federal language laws: Modernization and new obligations](https://www.canada.ca/en/canadian-heritage/campaigns/canadians-official-languages-act.html)
- [Ontario French Language Services Act — Designation Guide](https://www.ontario.ca/page/user-guide-designation-organizations-under-french-language-services-act)
- [Ontario Trillium Foundation — French Language Services Policy](https://otf.ca/who-we-are/our-policies/french-language-services-policy)
- [Treasury Board — Official Languages Requirements Checklist](https://www.canada.ca/en/treasury-board-secretariat/services/treasury-board-submissions/official-languages-requirements-appendix.html)
- [WCAG 2.2 — Success Criterion 3.1.1 Language of Page](https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html)
- [WCAG 2.2 — Success Criterion 3.1.2 Language of Parts](https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html)
