# Parking Lot Cleanup — Implementation Plan

**Created:** 2026-02-24
**Status:** Ready for implementation (start after outstanding PRs are merged)

## Overview

Clear 22 actionable items from the parking lot and Coming Up in one coordinated push. Items are grouped into 6 bundles by file area to minimise merge conflicts when running parallel sessions. Bundles 1–3 and 5 can run simultaneously as sub-agents. Bundle 6 (PIPEDA privacy) runs after Bundles 1 and 4.

INSIGHTS-I18N1 (from Active Work) and SURVEY-I18N1 + SURVEY-LINK1 (from Coming Up) are included because they fit naturally into existing bundles.

---

## Items Deferred (Need More Information)

These 21 items stay in the parking lot — they need GK review, design work, or prerequisites that aren't ready yet:

| ID | Reason to Defer |
|---|---|
| SEC3 | Blocked by SEC3-Q1 flag (GK decision on who can run the command) |
| SRE1 | No design file exists — needs requirements gathering |
| DQ1-TUNE | Depends on DQ1 being built first (Coming Up) |
| DQ2-TIERS | Depends on DQ2 being built first (Coming Up) |
| SURVEY1 | Core feature is built (10 models, 15 templates, views, trigger engine). Remaining work tracked as SURVEY-LINK1 and SURVEY-I18N1 |
| SETUP1-UI | Design depends on Claude skill integration (future) |
| DEPLOY-CONFIG-UI1 | Logically follows SETUP1-UI |
| METRIC-CADENCE1 | Future feature — insights not mature enough yet |
| METRIC-REVIEW1 | Depends on insights system maturity |
| ALLIANCE-GUIDE1 | Content and design needed from GK |
| ALLIANCE-ROTATE1 | Depends on alliance system maturity |
| PORTAL-PROGRESS1 | Depends on portal + insights integration |
| PORTAL-ALLIANCE1 | Depends on portal + alliance integration |
| ASSESS1 | Needs partner reporting requirements first |
| PERF1 | Premature — only needed at >2,000 clients |
| UX17 | Needs design for which workflows get bulk operations |
| QA-T15 | Infrastructure/load testing task, not a code change |
| QA-T16 | Needs real legacy data format to test against |
| QA-W55 | Infrastructure/test task for shared device scenario |
| I18N-API1 | Needs API key and cost decision |
| DEPLOY1 | Mostly process documentation, not code |

---

## Bundle 1: Template/UX Polish

**Files touched:** Templates in `templates/clients/erasure/`, `templates/plans/`, `templates/clients/`, `templates/base.html` area. No model or migration changes.

**Can run in parallel with:** Bundles 2, 3, 5

### Task 1.1 — QA-PA-ERASURE2: Replace decorative circular element on erasure empty state

**What:** The erasure request empty state uses a decorative circular CSS element. Replace it with a static icon (Pico CSS built-in or inline SVG) for a cleaner look.

**Files:**
- `templates/clients/erasure/erasure_pending_list.html` — replace the CSS circle with a static icon
- `templates/clients/erasure/erasure_history.html` — same if it has a similar empty state

**Effort:** Small (15 min)

### Task 1.2 — QA-PA-GOAL3: Add breadcrumbs to goal creation form

**What:** Add a breadcrumb trail (Participants > [Name] > Plan > Add a Goal) to help new users orient themselves.

**Files:**
- `templates/plans/goal_form.html` — add `<nav aria-label="breadcrumb">` above the heading
- `apps/plans/views.py` — pass client name and plan URL to the template context (if not already available)

**Effort:** Small (30 min)

### Task 1.3 — A11Y-POLISH1: Accessibility polish (status dropdown + colour indicator)

**What:** Two remaining a11y improvements from QA Round 7 (IMPROVE-9/10/11/12/13 bundle):
1. Status dropdown auto-opens on Tab focus (keyboard navigation)
2. Colour-only status indicators get a text or icon supplement (WCAG 1.4.1)

**Source:** `tasks/qa-action-plan-2026-02-21.md`, item 13

**Files:**
- `templates/clients/client_list.html` or similar list view — status indicator markup
- `static/css/` or inline styles — dropdown behaviour on focus
- Any participant list templates that show coloured status badges

**Effort:** Medium (1–2 hours)

### Task 1.4 — QA-W19: Add onboarding help link or first-run banner

**What:** Add a lightweight help link or dismissible first-run banner so new users know where to start. Not a full onboarding wizard — just a "Need help getting started?" link to documentation or a brief guide.

**Files:**
- `templates/dashboard/` or `templates/base.html` — add a dismissible banner or help link
- `apps/auth_app/models.py` — possibly add `has_dismissed_onboarding` boolean (or use localStorage in JS for simplicity)
- `static/js/app.js` — banner dismiss logic (if using localStorage approach)

**Decision during implementation:** Use localStorage (simpler, no migration) unless there's a reason to persist server-side.

**Effort:** Small–medium (1 hour)

---

## Bundle 2: Verification Tasks

**Files touched:** Possibly none (verify and close) or small targeted fixes. These are investigative — run the check, record the result, close the item or create a targeted fix.

**Can run in parallel with:** Bundles 1, 3, 5

### Task 2.1 — QA-R7-BUG13: Verify accented character preservation

**What:** Check that accented characters (é, è, ê, ç, etc.) survive the full create → save → display cycle for client names and notes. May be a test data issue rather than a real bug.

**How to verify:**
1. Create a test client with accented name (e.g., "Marie-Ève Côté")
2. Save and reload the client profile
3. Check the name displays correctly in list views, detail views, and PDF exports
4. If the issue is in Fernet encryption/decryption, check `apps/clients/encryption.py`

**Outcome:** Close if working, or create a targeted fix with the specific file and line.

**Effort:** Small (30 min)

### Task 2.2 — QA-R7-BUG21: Verify form data preservation after validation error

**What:** Check that if a user fills out the create-participant form and hits a validation error, the form re-renders with their data preserved (not blank).

**How to verify:**
1. Go to create participant form
2. Fill in several fields, leave a required field blank
3. Submit — form should show validation error AND preserve entered data
4. Check `apps/clients/views.py` — the create view should pass the bound form back to the template

**Outcome:** Close if working, or fix the view to pass the bound form instance.

**Effort:** Small (30 min)

### Task 2.3 — SURVEY-LINK1: Verify shareable link channel is complete

**What:** The TODO lists "Build shareable link channel for public survey links without login" but the code appears to already be built:
- `apps/surveys/public_views.py` — full public form display, submission, thank-you page
- `apps/surveys/views.py` `survey_links()` — admin creates/deactivates links
- `apps/surveys/models.py` `SurveyLink` — model with token, expiry, collect_name fields
- `templates/surveys/public_form.html`, `public_expired.html`, `public_thank_you.html` — public templates
- `templates/surveys/admin/survey_links.html` — admin link management

**How to verify:**
1. Confirm all the above files exist and are wired into URLs
2. Check that `SurveyLink` generates a unique token on creation
3. Verify the public form works end-to-end (create link → open in browser → submit → thank you)
4. If everything works, close SURVEY-LINK1 as already done

**Outcome:** Likely close as already implemented. If gaps found, document what's missing.

**Effort:** Small (20 min)

### Task 2.4 — DEPLOY-VERIFY1: Verify deploy-azure.md reference

**What:** The deployment protocol references `docs/deploy-azure.md` but this file doesn't exist. Either create it or update the reference.

**Finding:** `docs/deploy-azure.md` does not exist. The reference is in `tasks/phase-7-prompt.md`.

**Fix:** Update the reference to point to the correct deployment documentation (likely `docs/deployment.md` or similar), or remove the stale reference.

**Files:**
- `tasks/phase-7-prompt.md` — update or remove the reference

**Effort:** Tiny (10 min)

---

## Bundle 3: i18n Cleanup + Insights Translations

**Files touched:** `locale/fr/LC_MESSAGES/django.po`, `locale/fr/LC_MESSAGES/django.mo`, `apps/admin_settings/management/commands/translate_strings.py`, `apps/reports/views.py` (CSV comment rows only). No template or model changes.

**Can run in parallel with:** Bundles 1, 2, 5

### Task 3.1 — I18N-STALE1: Clean up ~628 stale PO entries

**What:** The `.po` file contains ~628 `msgid` entries that no longer appear in any template or Python file. These add noise and slow down translators.

**Approach:**
1. Run `translate_strings --dry-run` to see current state
2. Write a script or use `msgattrib --only-fuzzy --no-obsolete` to identify stale entries
3. Cross-reference each msgid against the codebase (grep for the string in templates and Python files)
4. Remove entries confirmed as stale
5. Run `translate_strings` to recompile

**Safety:** Keep a backup of the `.po` file before editing. Stale entries are marked `#~ ` (obsolete) by `msgmerge` — these are safe to remove. Active entries that simply moved files are NOT stale.

**Files:**
- `locale/fr/LC_MESSAGES/django.po` — remove stale entries
- `locale/fr/LC_MESSAGES/django.mo` — recompile

**Effort:** Medium (1–2 hours)

### Task 3.2 — I18N-CSV1: Translate CSV comment rows

**What:** CSV export comment rows (e.g., `# Program:`, `# Date Range:`, `# Total Participants:`) are hardcoded in English. Wrap them in `_()` for translation.

**Decision:** Use static translations (not agency terminology). The comment prefix `#` is a CSV convention — Excel and LibreOffice treat these as comment rows. Agency terminology (`{{ term.client }}`) is for the UI, not data exports.

**Files:**
- `apps/reports/views.py` — wrap ~6-8 comment row strings in `_()` (lines ~646-649, ~773-776, and any other CSV export functions)
- `locale/fr/LC_MESSAGES/django.po` — add French translations for the new strings
- `locale/fr/LC_MESSAGES/django.mo` — recompile

**Effort:** Small (30 min)

### Task 3.3 — INSIGHTS-I18N1: Extract and translate French strings for metric distributions

**What:** The metric distribution templates (Phases 0–2, recently merged) have ~25-30 new translatable strings, including several `{% blocktrans %}` blocks that need manual .po file entries.

**Approach:**
1. Run `python manage.py translate_strings` to extract new `{% trans %}` strings
2. Manually add `{% blocktrans %}` msgids to `django.po`
3. Translate all new entries to French
4. Run `translate_strings` again to compile
5. Verify the insights pages render correctly in French

**Files:**
- `locale/fr/LC_MESSAGES/django.po` — add ~25-30 new French translations
- `locale/fr/LC_MESSAGES/django.mo` — recompile

**Effort:** Medium (1–2 hours)

### Task 3.4 — SURVEY-I18N1: Extract and translate French strings for survey templates

**What:** The survey templates (admin, public form, results) need French translations extracted and compiled. Similar workflow to INSIGHTS-I18N1.

**Approach:**
1. Run `python manage.py translate_strings` to extract new `{% trans %}` strings from survey templates
2. Manually add any `{% blocktrans %}` msgids to `django.po`
3. Translate all new survey entries to French
4. Run `translate_strings` again to compile
5. Verify the survey pages render correctly in French

**Files:**
- `locale/fr/LC_MESSAGES/django.po` — add French translations for survey strings
- `locale/fr/LC_MESSAGES/django.mo` — recompile

**Effort:** Medium (1 hour)

**Order within bundle:** Do 3.1 (stale cleanup) first, then 3.2, 3.3, and 3.4. Cleaning stale entries first means fewer entries to scan when adding new ones.

---

## Bundle 4: Security

**Files touched:** `apps/auth_app/` (models, views, forms, templates), `apps/clients/erasure.py`, `apps/clients/erasure_views.py`, `requirements.txt`. Heaviest bundle — run with focused attention, not in parallel with other bundles that touch the same apps.

**Run after:** Bundles 1–3 and 5 are done (or at least after Bundle 1 is done, since it also touches client templates but different ones)

### Task 4.1 — SEC2: TOTP Multi-Factor Authentication

**What:** Add TOTP (authenticator app) support for local password authentication. Azure AD users already get MFA through Microsoft.

**Design:** See `tasks/mfa-implementation.md` — Option 2 (TOTP for Local Auth)

**Subtasks:**

1. **Add dependencies** — `django-otp>=1.3.0`, `qrcode>=7.4.0` to `requirements.txt`
2. **Add MFA fields to User model** — `mfa_enabled`, `mfa_secret`, `mfa_backup_codes` in `apps/auth_app/models.py`; run `makemigrations` + `migrate`
3. **Create MFA setup view** — Profile > Security > Enable MFA. Display QR code, verify 6-digit code to confirm.
   - `apps/auth_app/views.py` — `mfa_setup`, `mfa_disable` views
   - `apps/auth_app/forms.py` — `MFASetupForm`, `MFAVerifyForm`
   - `templates/auth_app/mfa_setup.html` — QR code display + confirmation
4. **Add MFA verification to login flow** — after password check, redirect to MFA code entry if `mfa_enabled`
   - `apps/auth_app/views.py` — modify login view
   - `templates/auth_app/mfa_verify.html` — 6-digit code entry form
5. **Admin controls** — admin can require MFA for specific roles, reset a user's MFA
6. **Backup codes** — generate 10 one-time codes on setup, display once
7. **Tests** — setup flow, login with MFA, backup codes, admin reset
8. **Documentation** — update `docs/security-operations.md`

**Files:**
- `apps/auth_app/models.py` — MFA fields
- `apps/auth_app/views.py` — setup, verify, disable views
- `apps/auth_app/forms.py` — MFA forms
- `apps/auth_app/urls.py` — new routes
- `templates/auth_app/mfa_setup.html` — new
- `templates/auth_app/mfa_verify.html` — new
- `requirements.txt` — new dependencies
- `docs/security-operations.md` — documentation
- `tests/test_auth.py` — new tests

**Effort:** Large (4–6 hours)

### Task 4.2 — ERASE-H8: Deferred Execution for Tier 3 Erasure

**What:** Add a 24-hour delay before Tier 3 (full delete) erasure executes. Tiers 1 and 2 (anonymise) remain immediate. During the 24-hour window, any PM or admin can cancel.

**Design:** See `tasks/erasure-hardening.md`, ERASE-H8 section — simplified approach (no background scheduler).

**Subtasks:**

1. **Add field** — `scheduled_execution_at` (DateTimeField, nullable) on `ErasureRequest` model
2. **Modify Tier 3 approval flow** — instead of executing immediately, set `scheduled_execution_at = now + 24h` and status = `"scheduled"`
3. **Add cancel view** — PM or admin can cancel a scheduled erasure (sets status back to `"cancelled"`)
4. **Management command** — `execute_pending_erasures` processes requests past their scheduled time. Designed to run via cron daily.
5. **Template updates** — show "Scheduled for [datetime]" and "Cancel" button on the erasure detail page when status is `"scheduled"`
6. **Tests** — scheduling, cancellation, management command execution, permission checks
7. **Email notification** — notify requester when erasure is scheduled (with the 24h window info) and when it executes

**Files:**
- `apps/clients/models.py` — add field + new status choice
- `apps/clients/erasure.py` — modify Tier 3 execution path
- `apps/clients/erasure_views.py` — cancel view, modify approval view
- `apps/clients/management/commands/execute_pending_erasures.py` — new command
- `templates/clients/erasure/erasure_request_detail.html` — scheduled state UI
- `tests/test_erasure.py` — new tests

**Effort:** Large (3–4 hours)

---

## Bundle 5: Code Hygiene

**Files touched:** `apps/reports/views.py` (import order only), possibly a docs file. Trivial changes, no risk.

**Can run in parallel with:** Everything

### Task 5.1 — CODE-TIDY1: Tidy import ordering in reports/views.py

**What:** `import datetime as dt` placement is inconsistent. Move to the top with other standard library imports, following the project's import convention (stdlib → Django → third-party → local apps).

**Files:**
- `apps/reports/views.py` — reorder imports

**Effort:** Tiny (5 min)

### Task 5.2 — QA-W62: Document scenario_loader cache lifetime

**What:** The `scenario_loader` utility (used in QA test scenarios) may cache data. Document its cache lifetime and behaviour if reused outside pytest.

**Files:**
- Likely a docstring addition in the scenario loader module, or a note in `tasks/recurring-tasks.md`
- Check `tests/` or the qa-scenarios repo for the loader implementation

**Effort:** Tiny (15 min)

---

## Bundle 6: PIPEDA Privacy & Compliance (GK-approved 2026-02-24)

**Files touched:** `apps/clients/` (models, views, templates), `templates/dashboard/`, `templates/clients/erasure/`. New model (`DataAccessRequest`) requires migration.

**Can run after:** Bundles 1–5 (touches client templates and models that overlap with Bundle 1 and 4)

**Expert panel context:** Two rounds of expert review. Round 2 stress-tested for brittleness, maintenance burden, and usability by poorly trained staff at small agencies. All four designs were simplified from Round 1 recommendations.

### Task 6.1 — QA-PA-ERASURE1: Erasure page compliance context (30 min)

**What:** Add plain-language text to the erasure approval page showing what the selected tier does. One sentence per tier, shown only for the tier being approved. No comparison table, no legal citations.

**Design file:** `tasks/erasure-compliance-context.md`

**Files:**
- `templates/clients/erasure/erasure_request_detail.html` — conditional text block above approval buttons
- `locale/fr/LC_MESSAGES/django.po` — French translations

**Effort:** Small (30 min)

### Task 6.2 — QA-R7-PRIVACY1: PIPEDA data access checklist + 30-day tracking (3-4 hours)

**What:** Guided manual process for PIPEDA Section 8 data access requests. A checklist page tells staff what to gather (not an automated export). Includes request logging and 30-day countdown on admin dashboard.

**Key design decision:** Expert panel recommended against automated PDF export — it goes stale silently every time a feature is added, creating a false sense of compliance. A static checklist is zero-maintenance and PIPEDA-compliant.

**Design file:** `tasks/pipeda-data-access-checklist.md`

**Files:**
- `apps/clients/models.py` — new `DataAccessRequest` model (lightweight: date, method, deadline, completion)
- `apps/clients/views.py` or new `data_access_views.py` — log request, checklist page, mark complete
- `templates/clients/data_access_request.html` — checklist page
- `templates/clients/data_access_log.html` — request logging form
- Dashboard template — pending request banner with days remaining
- Migration file
- `tests/test_clients.py` — permission checks, deadline calculation, audit logging

**Note on alerts/flags:** Checklist includes alerts as a line item with safety withholding note: "Review alerts before including — you may withhold safety-related notes under PIPEDA s.9(1) if disclosure could threaten safety."

**Effort:** Medium (3-4 hours)

### Task 6.3 — QA-R7-PRIVACY2: Note sharing toggle (2 hours)

**What:** Binary On/Off toggle on client profile controlling cross-program note sharing. Uses existing `cross_program_sharing` field and `apply_consent_filter()` — no new models or migrations needed.

**Design file:** `tasks/note-sharing-toggle.md`

**Key decisions:**
- UI shows computed binary (On/Off), not the three-state model
- PM or admin only (frontline workers cannot change this)
- Hidden entirely when agency-level sharing feature is off
- Label: "Share notes across programs" — no legal terminology

**Files:**
- `templates/clients/_tab_info.html` — toggle UI
- `apps/clients/views.py` — HTMX endpoint for toggle POST
- `apps/clients/forms.py` — simple toggle form
- `tests/test_cross_program_security.py` — permission and audit tests

**Effort:** Small (2 hours)

### Task 6.4 — QA-R7-EXEC-COMPLIANCE1: Privacy compliance banner (2 hours)

**What:** Event-driven banner on executive dashboard showing pending privacy requests. Not a permanent dashboard card — appears only when action is needed. Plus a one-line annual summary for board reports.

**Design file:** `tasks/compliance-banner.md`

**Key decision:** Expert panel rejected a permanent 4-metric card — executives habituate to "0 requests" and stop looking. Event-driven visibility matches how compliance actually works at small agencies.

**Files:**
- Executive dashboard view — add pending counts to context
- Executive dashboard template — conditional banner block
- `apps/reports/export_engine.py` — compliance summary helper for annual report line

**Dependencies:** Banner for erasure requests can be built now. Banner for data access requests depends on Task 6.2 being built first.

**Effort:** Small (2 hours)

---

## Execution Plan

### Phase 1 — Parallel Quick Wins (Bundles 2, 3, 5)

Run three sub-agents simultaneously:

| Agent | Bundle | Items | Est. Time |
|---|---|---|---|
| Agent A | Bundle 5 (Code Hygiene) | CODE-TIDY1, QA-W62 | 20 min |
| Agent B | Bundle 2 (Verification) | QA-R7-BUG13, QA-R7-BUG21, SURVEY-LINK1, DEPLOY-VERIFY1 | 1.5 hours |
| Agent C | Bundle 3 (i18n) | I18N-STALE1, I18N-CSV1, INSIGHTS-I18N1, SURVEY-I18N1 | 4 hours |

**Merge order:** Agent A first (tiny, no conflicts), then B, then C.

### Phase 2 — Template/UX Polish (Bundle 1)

Run after Phase 1 merges (Bundle 1 doesn't conflict with Phase 1, but keeping it sequential reduces merge complexity):

| Agent | Bundle | Items | Est. Time |
|---|---|---|---|
| Agent D | Bundle 1 (UX Polish) | QA-PA-ERASURE2, QA-PA-GOAL3, A11Y-POLISH1, QA-W19 | 3 hours |

### Phase 3 — Security (Bundle 4)

Run last — heaviest bundle, benefits from a clean codebase:

| Agent | Bundle | Items | Est. Time |
|---|---|---|---|
| Agent E | Bundle 4a (SEC2 — MFA) | SEC2 | 5 hours |
| Agent F | Bundle 4b (ERASE-H8) | ERASE-H8 | 4 hours |

SEC2 and ERASE-H8 touch different files and can run in parallel within Bundle 4.

### Phase 4 — PIPEDA Privacy & Compliance (Bundle 6)

Run after Phase 3 (Bundle 6 touches client models/templates that overlap with Bundle 4):

| Agent | Bundle | Items | Est. Time |
|---|---|---|---|
| Agent G | Bundle 6a (ERASURE1 + PRIVACY2) | QA-PA-ERASURE1, QA-R7-PRIVACY2 | 2.5 hours |
| Agent H | Bundle 6b (PRIVACY1 + COMPLIANCE1) | QA-R7-PRIVACY1, QA-R7-EXEC-COMPLIANCE1 | 5 hours |

6a and 6b can run in parallel — ERASURE1 touches erasure templates while PRIVACY1 touches client views. COMPLIANCE1's data-access-request banner depends on PRIVACY1's model, so they're in the same agent.

---

## Dependencies

| Task | Depends On |
|---|---|
| 3.2 (I18N-CSV1) | Nothing |
| 3.3 (INSIGHTS-I18N1) | Nothing |
| 3.1 (I18N-STALE1) | Should run before 3.2 and 3.3 (cleaner baseline) |
| 4.1 (SEC2) | Nothing |
| 4.2 (ERASE-H8) | Nothing |
| 6.1 (QA-PA-ERASURE1) | Nothing |
| 6.2 (QA-R7-PRIVACY1) | Nothing |
| 6.3 (QA-R7-PRIVACY2) | Nothing |
| 6.4 (QA-R7-EXEC-COMPLIANCE1) | 6.2 (data access request model needed for full banner) |
| All others | Nothing |

Bundles 1–5 are independent of each other. Bundle 6 should run after Bundles 1 and 4 (overlapping client files).

---

## Testing Strategy

| Bundle | Test Files | Run Command |
|---|---|---|
| Bundle 1 | `tests/test_plans.py`, `tests/test_clients.py` | `pytest tests/test_plans.py tests/test_clients.py` |
| Bundle 2 | Manual verification (no new tests) | — |
| Bundle 3 | `python manage.py translate_strings` + manual French check | — |
| Bundle 4a (SEC2) | `tests/test_auth.py` | `pytest tests/test_auth.py` |
| Bundle 4b (ERASE-H8) | `tests/test_erasure.py` | `pytest tests/test_erasure.py` |
| Bundle 5 | None (cosmetic) | — |

| Bundle 6a (ERASURE1 + PRIVACY2) | `tests/test_erasure.py`, `tests/test_cross_program_security.py` | `pytest tests/test_erasure.py tests/test_cross_program_security.py` |
| Bundle 6b (PRIVACY1 + COMPLIANCE1) | `tests/test_clients.py` | `pytest tests/test_clients.py` |

After all bundles merge: run full suite `pytest -m "not browser and not scenario_eval"` once.

---

## Post-Cleanup

After all 20 items are done:
- Move completed items from parking lot to Recently Done in TODO.md
- Overflow older Recently Done items to `tasks/ARCHIVE.md`
- The 21 deferred items remain in the parking lot with clear "why" annotations
