# i18n Reliability Hardening Plan

**Source:** Expert panel review (2026-02-05) after recurring translation failures.

## Problem Statement

The i18n system has failed three times in different ways — duplicate .po entries, missing .mo compilation, and missing LOCALE_PATHS. Every failure mode is **silent**: the page shows English instead of French, and nobody notices until a French-speaking user reports it.

## Root Cause Pattern

The system has no closed feedback loop. SafeLocaleMiddleware prevents crashes (good) but also prevents detection (bad). Each past fix addressed one symptom without adding a guardrail against the next variant.

## Tasks

### P0 — Immediate (I18N-R1, I18N-R2)

**I18N-R1: Ensure `*.mo` files are included in Docker image builds**
- Currently only `*.po` may be tracked for deploy triggers
- If someone commits only the .po, a deploy could use a stale .mo
- Verify Docker build copies both .po and .mo into the image

**I18N-R2: Fix SafeLocaleMiddleware canary string**
- Currently tests `gettext("Sign In")` — but "Sign In" → "Connexion" exists in Django's own French catalog
- This means the test passes even when the PROJECT catalog isn't loaded (exactly what happened with missing LOCALE_PATHS)
- Fix: test a string that only exists in our .po file, like `"Participant Outcome Management"`
- If it comes back in English, raise an error (which the middleware catches and logs)

### P1 — Short-term (I18N-R3, I18N-R4)

**I18N-R3: Create `check_translations` management command**
- Activate French, test 5-10 project-specific strings
- Verify they return French, not English
- Run in CI and optionally in entrypoint.sh
- This single check would have caught ALL three past failures

**I18N-R4: Git pre-commit hook**
- Compare .po and .mo timestamps
- Block commit if .po is newer than .mo (means someone forgot to recompile)
- Simple and prevents the most common failure

### P2 — Medium-term (I18N-R5, I18N-R6)

**I18N-R5: Template string extraction script (makemessages-lite)**
- Walk all templates, extract `{% trans "..." %}` and `{% blocktrans %}` strings
- Compare against the .po file
- Report any strings in templates that aren't in the .po
- Can't use Django's `makemessages` because gettext isn't installed locally
- Use Python/regex parsing instead

**I18N-R6: `update_translations` wrapper command**
- Single command that runs the full workflow:
  1. Extract new strings (I18N-R5)
  2. Validate .po for duplicates (existing script)
  3. Compile .mo with polib
  4. Stage both files for commit
- Reduces multi-step workflow to one command for a non-developer

## Expert Panel Members

- **Django Backend Engineer** — i18n internals, middleware, translation loading
- **DevOps/CI Engineer** — build pipeline safety, automated guardrails
- **Systems Thinker** — root cause patterns, feedback loops
- **Localization Specialist** — translation workflow for small teams

## Key Insight

> "A `check_translations` command that runs in CI and tests real French strings would have caught every past incident — duplicates, missing .mo, missing LOCALE_PATHS, and any future variant. This is the single highest-value guardrail." — Systems Thinker
