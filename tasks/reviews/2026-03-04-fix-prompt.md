# Deep Review Fix Prompt — 2026-03-04

**Purpose:** Address all 11 Medium findings from the deep code review using parallel agents. This prompt is designed to be pasted into a fresh Claude Code session.

**Estimated time:** ~15-20 minutes (4 agents in parallel + 1 sequential follow-up)

**Pre-requisites:** Run `git pull origin develop` before starting.

---

## Agent Grouping Strategy

Findings are grouped into 4 parallel agents with zero file conflicts, plus 3 deferred items that need discussion or are complex enough to handle separately.

| Agent | Findings | Files Touched |
|-------|----------|---------------|
| 1 — Settings & Encryption | SEC-M1, SEC-M3 | `base.py`, `encryption.py` |
| 2 — AI Governance | AI-M1, AI-M2, AI-L2 | `ai.py`, `ai_views.py`, `_insights_ai.html`, `app.js` |
| 3 — Accessibility | A11Y-M1, A11Y-M2 | 5 templates, `main.css` |
| 4 — Registration Privacy | PRIV-M2, PRIV-M3 | `registration/models.py`, migration |
| Deferred | SEC-M2, PRIV-M1, DEPLOY-M1 | Complex / needs discussion |

---

## Prompt

> **Phase 1 — Setup**
>
> 1. Run `git pull origin develop`
> 2. Create a feature branch: `git checkout -b fix/deep-review-2026-03-04`
> 3. Read `tasks/reviews/2026-03-04-deep-review.md` for context
> 4. Launch all 4 agents below in parallel
>
> ---
>
> ### AGENT 1 — Settings & Encryption (SEC-M1, SEC-M3)
>
> Two one-line fixes. Read each file, make the change, commit immediately.
>
> **Fix 1 — SEC-M1: EMAIL_HASH_KEY empty string default**
> - File: `konote/settings/base.py:329`
> - Current: `EMAIL_HASH_KEY = os.environ.get("EMAIL_HASH_KEY", "")`
> - Problem: If not set and `DEMO_MODE` is False, HMAC operations use an empty key, weakening portal email hash resistance.
> - Fix: Add validation after the assignment. If `EMAIL_HASH_KEY` is empty and `DEMO_MODE` is False, raise `ImproperlyConfigured`. The demo fallback `"demo-email-hash-key-not-for-production"` should remain for demo mode only.
> - Pattern to follow: Look at how `require_env("FIELD_ENCRYPTION_KEY")` works at line ~326. For EMAIL_HASH_KEY, we want the opposite pattern — allow empty in demo mode, require in production. Something like:
>   ```python
>   EMAIL_HASH_KEY = os.environ.get("EMAIL_HASH_KEY", "")
>   if not EMAIL_HASH_KEY:
>       if DEMO_MODE:
>           EMAIL_HASH_KEY = "demo-email-hash-key-not-for-production"
>       else:
>           raise ImproperlyConfigured(
>               "EMAIL_HASH_KEY must be set in production. "
>               "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
>           )
>   ```
> - Test: Verify the app still starts in demo mode. Verify that removing EMAIL_HASH_KEY with DEMO_MODE=False raises an error.
>
> **Fix 2 — SEC-M3: Dead variable in encryption self-test**
> - File: `konote/encryption.py:227`
> - Current: `_master_fernet = None` (assigns to a local variable — no effect)
> - Fix: Change to `_fernet = None` (the module-level cache variable)
> - Context: The `finally` block at line ~227 should clear the module-level `_fernet` cache after the system check self-test. The variable `_fernet` is defined at module level (around line 30) and is used as a cache by `_get_fernet()`. After the self-test, we want the cache cleared so the first real use re-initialises fresh.
> - This is a true one-line fix with zero risk.
>
> **Commit both fixes together** with message: `fix: EMAIL_HASH_KEY validation and encryption self-test cache reset (SEC-M1, SEC-M3)`
>
> ---
>
> ### AGENT 2 — AI Governance (AI-M1, AI-M2, AI-L2)
>
> Three fixes in the AI subsystem. Read all files first, then make changes.
>
> **Fix 1 — AI-M1: Remove note_id hallucination path (MEDIUM — most important fix)**
>
> The system prompt for `generate_outcome_insights` asks the AI to return `note_id` in `cited_quotes` and `supporting_quotes`, but note_id is deliberately excluded from the data sent to the AI. The AI fabricates IDs that are then used to generate links in the template.
>
> Files to read:
> - `konote/ai.py` — find the `generate_outcome_insights` function, specifically the system prompt (around line 467) where it defines the JSON output schema requesting `note_id`
> - `konote/ai_views.py` — find `outcome_insights_view`, specifically lines ~396-410 where `quote_source_map` is built but never injected back into the response
> - `templates/reports/_insights_ai.html` — lines ~51-53 and ~69-71 where `sq.note_id` is used to generate `{% url 'notes:note_detail' %}` links
>
> Two-part fix:
>
> **Part A — Remove `note_id` from AI prompt and validation:**
> 1. In `ai.py`, find the system prompt JSON schema in `generate_outcome_insights`. Remove `note_id` from the `cited_quotes` and `supporting_quotes` field lists. Keep `text` and `context`/`target_name`.
> 2. In `ai.py`, find the `validate_insights_response` function. If it references `note_id` in any validation logic, remove those references.
>
> **Part B — Remove `note_id` links from template:**
> 1. In `_insights_ai.html`, find the blocks that render `cited_quotes` (~line 51-53) and `supporting_quotes` (~line 69-71). Remove the `{% url 'notes:note_detail' sq.note_id %}` link wrapping. Display the quote text without a link to a specific note.
> 2. If there's a "View note" link text, remove it entirely.
>
> **Do NOT implement option (b) from the review** (injecting correct IDs from quote_source_map). That adds complexity. The simpler fix is to remove the note linking entirely — users can find the note through normal navigation.
>
> **Fix 2 — AI-M2: HTTPS enforcement for INSIGHTS_API_BASE**
> - File: `konote/ai.py` — find `_call_insights_api` function (around line 356-386)
> - Problem: If an operator sets `INSIGHTS_API_BASE=http://remote-server:11434/v1`, de-identified quotes transit over unencrypted HTTP.
> - Fix: After constructing the URL, check if it uses HTTP (not HTTPS) AND the host is not localhost/127.0.0.1/[::1]. If so, log a warning. Do not block the call — just warn.
>   ```python
>   from urllib.parse import urlparse
>   parsed = urlparse(url)
>   if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
>       logger.warning(
>           "INSIGHTS_API_BASE uses HTTP for remote host %s — "
>           "de-identified data will transit unencrypted. "
>           "Use HTTPS for production deployments.",
>           parsed.hostname,
>       )
>   ```
>
> **Fix 3 — AI-L2: Add HTTP 429 handling to HTMX error handler**
> - File: `static/js/app.js` — find the `htmx:responseError` handler (around line 238-251)
> - Problem: When rate limits are hit, users see a generic "Something went wrong" instead of guidance to wait.
> - Fix: Add a `status === 429` branch before the generic fallback:
>   ```javascript
>   } else if (status === 429) {
>       msg = window.KN?.i18n?.rate_limited || "Too many requests. Please wait a few minutes before trying again.";
>   ```
> - Also add the `rate_limited` key to the `window.KN.i18n` object in `base.html` (search for where other `window.KN` translations are defined) with `{% trans %}` wrapping for bilingual support.
> - After adding the `{% trans %}` string, run `python manage.py translate_strings` to extract and compile, then add the French translation to `locale/fr/LC_MESSAGES/django.po`.
>
> **Commit** with message: `fix: AI note_id hallucination, HTTPS enforcement, 429 UX (AI-M1, AI-M2, AI-L2)`
>
> ---
>
> ### AGENT 3 — Accessibility (A11Y-M1, A11Y-M2)
>
> Template-only fixes. No Python changes.
>
> **Fix 1 — A11Y-M1: Fix standalone pages missing skip nav + landmarks + lang**
>
> Four templates bypass `base.html` and lack WCAG 2.2 AA requirements. Fix each:
>
> **a) `templates/500.html`**
> - Replace `lang="en"` with `lang="{{ LANGUAGE_CODE|default:'en' }}"` (note: Django may not have context in 500 errors — check if `LANGUAGE_CODE` is available. If not, hardcode `lang="en"` but add a comment explaining why)
> - Add `<a href="#main-content" class="visually-hidden-focusable">{% trans "Skip to main content" %}</a>` after `<body>` (but note: if this is a minimal error page without the i18n template tags loaded, you may need `{% load i18n %}` at the top, or just use plain English "Skip to main content" with a comment)
> - Wrap the content in `<main id="main-content" tabindex="-1">`
> - Read the current file first to understand its structure
>
> **b) `templates/offline.html`** (service worker offline page)
> - Same fixes as 500.html: dynamic `lang`, skip nav, `<main>` landmark
> - This page may have even less Django context. Read it first.
>
> **c) `templates/auth/mfa_verify.html`** (staff MFA page)
> - Read the file — it may extend a base template or be standalone
> - If standalone: add skip nav link and `<main>` landmark
> - If it extends base.html, it may already have these (verify)
>
> **d) `templates/surveys/public_thank_you.html`**
> - Read the file — it likely has `<main>` but missing `id="main-content"` and `tabindex="-1"`
> - Add skip nav: `<a href="#main-content" class="visually-hidden-focusable">{% trans "Skip to main content" %}</a>`
> - Add `id="main-content" tabindex="-1"` to the `<main>` tag
>
> **Fix 2 — A11Y-M2: Rating scale fieldset/legend in public survey**
> - File: `templates/surveys/public_form.html` — around line 108-118
> - Problem: Rating scale radios use `<div role="group">` instead of `<fieldset><legend>`
> - Fix: Change the rating scale block to match the portal's pattern (`templates/portal/survey_fill.html:130-150`):
>   - Replace `<div role="group">` with `<fieldset class="survey-question-group">`
>   - Move the question label into `<legend>`
>   - Close with `</fieldset>` instead of `</div>`
> - Read both the public form and the portal form to see the exact patterns before editing.
>
> **Translations:** If any new `{% trans %}` strings were added, run `python manage.py translate_strings` and add French translations.
>
> **Commit** with message: `fix: standalone page accessibility and survey rating scale grouping (A11Y-M1, A11Y-M2)`
>
> ---
>
> ### AGENT 4 — Registration Privacy (PRIV-M2, PRIV-M3)
>
> Two privacy fixes to the registration model. Both require migrations.
>
> **Fix 1 — PRIV-M2: Migrate registration email hash to HMAC-SHA-256**
> - File: `apps/registration/models.py`
> - Problem: `RegistrationSubmission.email_hash` uses plain `hashlib.sha256()` while the portal uses keyed HMAC-SHA-256. Plain SHA-256 is reversible via rainbow tables.
> - Fix:
>   1. Read `apps/portal/models.py` to see how `compute_email_hash()` works with HMAC
>   2. In `apps/registration/models.py`, change the email hash computation to use `hmac.new(settings.EMAIL_HASH_KEY.encode(), email.encode(), hashlib.sha256).hexdigest()` — matching the portal's pattern
>   3. Create a data migration that rehashes all existing `email_hash` values:
>      - For each `RegistrationSubmission` with a non-empty `_email_encrypted` field:
>        - Decrypt the email
>        - Compute the new HMAC hash
>        - Update `email_hash`
>      - This is safe because the encrypted email is still stored — we're just updating the hash index
>   4. Run `python manage.py makemigrations registration` and `python manage.py migrate`
>
> **Fix 2 — PRIV-M3: Encrypt registration field_values**
> - File: `apps/registration/models.py`
> - Problem: `field_values` (JSONField) stores custom field responses in plaintext. These may contain sensitive information depending on agency configuration.
> - Fix:
>   1. Read the model to understand how `field_values` is used
>   2. Add an encrypted binary field `_field_values_encrypted` and a property accessor `field_values` that encrypts/decrypts JSON (serialize to string, then encrypt)
>   3. Follow the same pattern used by other encrypted fields in the codebase (read `apps/clients/models.py` for the pattern)
>   4. Create a data migration to encrypt existing plaintext values
>   5. Remove the old `field_values` JSONField (or rename to `_field_values_legacy` if needed for backward compatibility during migration)
>   6. Run `python manage.py makemigrations registration` and `python manage.py migrate`
>
> **Important:** Check `apps/registration/views.py` and `apps/registration/forms.py` (if they exist) to find all places that read/write `field_values` — the property accessor should make this transparent, but verify.
>
> **Commit** with message: `fix: HMAC email hash and encrypted field_values in registration (PRIV-M2, PRIV-M3)`
>
> ---
>
> ## Phase 2 — After All Agents Complete
>
> 1. Run the relevant tests:
>    ```
>    pytest tests/test_registration.py tests/test_auth.py tests/test_ai.py -v
>    ```
>    (If test files don't map exactly, search for relevant test files first)
>
> 2. Run `python manage.py translate_strings` to catch any new strings
>
> 3. Verify the app starts: `python manage.py check --deploy`
>
> 4. Push and create PR to `develop`:
>    ```
>    git push -u origin fix/deep-review-2026-03-04
>    gh pr create --base develop --title "fix: address deep review Medium findings" --body "..."
>    ```
>
> ---
>
> ## Deferred Items (Not in This PR)
>
> These items are more complex or need discussion before implementation:
>
> | ID | Finding | Why Deferred |
> |----|---------|-------------|
> | SEC-M2 | CSP `unsafe-inline` → nonce-based | Requires architectural change to how Chart.js is initialised. All inline `<script>` blocks must be extracted to external files or given nonces. Affects many templates. Should be its own PR with testing. |
> | PRIV-M1 | Communication retention expiry | Needs GK review — retention periods are an agency policy decision. The model change (adding `retention_expiry` field) is straightforward but the cleanup command needs policy input on defaults. |
> | DEPLOY-M1 | Complete `rotate_tenant_key` | Needs careful design — re-encrypting all tenant data in a migration is a high-risk operation. The interim fix is to document that the command must not be used without a companion re-encryption step. Add a prominent warning to the command's help text. |
>
> ## Low-Priority Items (Track in TODO.md)
>
> These 18 Low findings should be added to the Parking Lot in TODO.md for future sessions:
>
> SEC-L1 through SEC-L5, PRIV-L1, PRIV-L2, AI-L1, AI-L3, AI-L4, DEPLOY-L1 through DEPLOY-L3, A11Y-L1 through A11Y-L4, BILIN-L1
