# KoNote Code Review — 2026-03-02

**Scope:** Full codebase audit across all apps — security, code quality, consistency, test coverage, translation, and accessibility.
**Reviewed:** `apps/`, `tests/`, `templates/`, `locale/`, `static/js/app.js`
**Reviewer:** Claude Code (claude-sonnet-4-6)

---

## Critical Findings

### CR-1: `htmx.config.allowScriptTags = true` — XSS risk
**File:** `static/js/app.js` line 12
**Severity:** Critical
**Detail:** HTMX is globally configured to execute `<script>` tags injected via server responses. If any HTMX endpoint returns content that includes user-controlled text rendered without escaping (e.g., a participant name, note excerpt, or survey answer placed in a `<script>` block), that content will execute in the browser. Django's template engine auto-escapes by default, but this setting makes the application dependent on zero escaping mistakes across every HTMX partial — present and future.
**Recommendation:** Set `htmx.config.allowScriptTags = false;`. If inline scripts are genuinely needed in specific partials, scope them with `hx-target` and handle them explicitly rather than enabling globally.

---

### CR-2: `request.META.get("REMOTE_ADDR")` used directly in audit logs — proxy bypass
**Files and lines:**
- `apps/admin_settings/field_access_views.py` lines 51, 94
- `apps/auth_app/admin_views.py` lines 369, 393, 419
- `apps/notes/suggestion_views.py` line 45
- `apps/plans/views.py` lines 868, 1186

**Severity:** Critical
**Detail:** `konote/utils.py` defines `get_client_ip()` which correctly reads `X-Forwarded-For` first (needed behind Caddy / Azure reverse proxy) and falls back to `REMOTE_ADDR`. Eight call sites bypass this utility and read `REMOTE_ADDR` directly. Behind a reverse proxy, `REMOTE_ADDR` is always the proxy's IP — these audit log entries record `127.0.0.1` or the proxy address, not the actual user IP. This defeats IP-based audit trail forensics.
**Recommendation:** Replace all `request.META.get("REMOTE_ADDR", "")` in these files with `_get_client_ip(request)` (already imported in some files) or `get_client_ip(request)` from `konote.utils`.

---

## Important Findings

### IMP-1: `FeatureToggle.get_all_flags()` hits the database on every call — no internal cache
**File:** `apps/admin_settings/models.py` line 178
**Severity:** Important
**Detail:** `get_all_flags()` queries the database unconditionally on every invocation. There are 24 call sites across the codebase (grep: `get_all_flags`). Only one caller — `dashboard_views._get_feature_flags()` — wraps the result in a `cache.get`/`cache.set` with 300s TTL. Every other caller issues a fresh DB query per request. On high-traffic pages (client list, note list, program detail), this adds an extra DB round-trip per page load for every active user.
**Recommendation:** Add `cache.get` / `cache.set` inside `get_all_flags()` itself, using key `"feature_toggles"` (already used by the signals in `admin_settings/signals.py` for invalidation). The invalidation signals are already correct — the cache key just needs to be read from inside the model method.

---

### IMP-2: 839 missing French translations (~17% of strings)
**File:** `locale/fr/LC_MESSAGES/django.po`
**Severity:** Important
**Detail:** Of 4,853 total `msgid` entries, 839 have empty `msgstr ""` (approximately 17.3%). These strings will display in English to French-speaking users. Given that bilingual compliance is a legal requirement under the Official Languages Act and Ontario FLSA (documented in `tasks/design-rationale/bilingual-requirements.md`), incomplete translations are a compliance risk, not just a UX issue.
**Recommendation:** Run `python manage.py translate_strings` to identify which strings are missing. Prioritise user-facing strings (error messages, form labels, navigation) over internal admin strings. Fill missing translations and recompile.

---

### IMP-3: Multiple views use `request.POST.get()` directly instead of ModelForms
**Severity:** Important
**Detail:** The project convention requires ModelForms for all POST validation (CLAUDE.md rule 1). The following locations use raw `request.POST.get()` without form validation:

| File | View / Helper | Fields bypassing form validation |
|------|--------------|----------------------------------|
| `apps/clients/views.py` | `client_resume()` | `program_id` |
| `apps/clients/views.py` | `cross_program_sharing_toggle()` | `sharing` |
| `apps/plans/views.py` | `achievement_status_update()` | `achievement_status` |
| `apps/plans/views.py` | `goal_create()` | `custom_metric_name`, `custom_metric_definition`, `custom_metric_accepted`, `participant_words` |
| `apps/surveys/views.py` | `survey_questions()` | `required`, `include_comment`, `active` per question |
| `apps/surveys/views.py` | `survey_status()` | `status` |
| `apps/surveys/views.py` | `survey_links()` | `expires_days`, `collect_name`, `link_id` |
| `apps/notes/suggestion_views.py` | `_handle_status_update()` | `new_status` |
| `apps/notes/suggestion_views.py` | `_handle_link_notes()` | `note_ids` (list) |
| `apps/notes/suggestion_views.py` | `_handle_unlink()` | `link_id` |
| `apps/notes/suggestion_views.py` | `theme_status_update()` | `new_status` |
| `apps/registration/admin_views.py` | `submission_reject()` | `reason` |
| `apps/registration/admin_views.py` | `submission_merge()` | `client_id` |

The risk varies by field — `program_id` and `client_id` are particularly sensitive since they control access scoping. Most of these are behind `@admin_required` or `@login_required`, but missing validation still means malformed input can reach model `save()` without sanitisation.
**Recommendation:** Create lightweight forms (can be non-model forms using `forms.Form`) for each of these endpoints, even if they only validate type/allowlist values.

---

### IMP-4: `check_note_date` HTMX endpoint does not apply PHIPA consent filter
**File:** `apps/notes/views.py` around line 525
**Severity:** Important
**Detail:** `check_note_date` is an HTMX endpoint that validates whether a note date is in the future and, when applicable, returns metadata about any existing note on that date (author, timing). It queries `ProgressNote` without calling `apply_consent_filter()`. While it does not return note *content*, it does reveal that a note exists, who wrote it, and when — which is itself protected health information under PHIPA. A staff member from Program A without consent access to Program B's notes can use this endpoint to discover that a participant has a note from Program B on a given date.
**Recommendation:** Apply `apply_consent_filter()` (or at minimum scope the query to the user's active program IDs) before returning note metadata. See `apps/programs/access.py` for the filter function signature.

---

### IMP-5: N+1 query in `program_list()` — manager role lookup inside loop
**File:** `apps/programs/views.py` lines 44–60
**Severity:** Important
**Detail:** `program_list()` iterates over all programs and, for each program, fires two additional queries: one for the manager role (`UserProgramRole.objects.filter(program=program, role="program_manager", ...)`), and one for the active user count. With N programs this is 2N+1 queries per page load. As program count grows this will degrade noticeably.
**Recommendation:** Prefetch manager roles and user counts in a single query using `annotate(user_count=Count(...))` and `prefetch_related(Prefetch("userroleprogram_set", ...))` or a single `UserProgramRole` query grouped by program, then join in Python.

---

### IMP-6: British spelling "programme" in user-facing error message
**File:** `apps/clients/dashboard_views.py` lines 1044, 1048
**Severity:** Important
**Detail:** The project CLAUDE.md specifies Canadian spelling — "program" (never "programme" in English). Two `HttpResponseForbidden` messages in `dashboard_views.py` use "programme" in English user-facing text. These will be read by English-speaking users of Canadian agencies. (Note: "programme" in `.po` French translations is correct — only the English strings are wrong.)
**Recommendation:** Replace "programme" with "program" in the English strings at these lines.

---

### IMP-7: Incorrect ARIA roles on navigation dropdowns in `base.html`
**File:** `templates/base.html` lines 143, 145, 158, 160, 193, 195, 234, 236
**Severity:** Important (WCAG 2.2 AA — 4.1.2 Name, Role, Value)
**Detail:** Navigation dropdown patterns use:
- `<details class="dropdown" role="list">` — `<details>` is a disclosure widget; `role="list"` overrides its implicit role incorrectly. Screen readers will announce this as a list, not a disclosure button.
- `<ul role="listbox">` inside — `listbox` is an ARIA pattern for form select-like widgets with `aria-selected` items. Navigation menus should use `role="menu"` with `role="menuitem"` children, or simply `role="navigation"` with a plain `<ul>` (no role override needed).

**Recommendation:**
- Remove `role="list"` from `<details>` elements. Let the browser expose its native `details`/`summary` semantics, or switch to a `<button>` + `<ul>` pattern with `role="menu"` / `role="menuitem"`.
- Replace `<ul role="listbox">` with `<ul role="menu">` and add `role="menuitem"` to each `<li>` link.

---

### IMP-8: Duplicated note-creation logic between `quick_note_create()` and `quick_note_inline()`
**File:** `apps/notes/views.py`
**Severity:** Important (maintainability)
**Detail:** Both `quick_note_create()` and `quick_note_inline()` contain nearly identical code blocks for: (1) resolving follow-up auto-complete from a previous note, and (2) tagging circle members. When logic changes in one path (e.g., a new required field, a consent check, an audit event), the other path must be updated manually. This pattern has already caused divergence in similar situations elsewhere in the codebase.
**Recommendation:** Extract the shared logic into a private helper function (e.g., `_build_note_context(request, client, program)`) called by both views.

---

### IMP-9: Untranslated error strings in `auth_app/views.py` `_local_login()`
**File:** `apps/auth_app/views.py` lines 185, 216, 219, 224, 227, 229
**Severity:** Important
**Detail:** Several error strings returned to the user inside `_local_login()` are bare Python string literals not wrapped in `_()`. Examples: rate-limit error messages and account lockout messages. These will always display in English regardless of the user's language setting.
**Recommendation:** Wrap all user-facing string literals in `_()` (gettext). Run `python manage.py translate_strings` and add French translations.

---

## Nice-to-Have Findings

### NTH-1: Deprecated decorators `minimum_role` and `program_role_required` still present
**File:** `apps/auth_app/decorators.py`
**Severity:** Low
**Detail:** Both `minimum_role()` and `program_role_required()` are marked as deprecated in comments but are still imported and potentially in use. Dead code complicates future refactoring.
**Recommendation:** Grep for usages (`grep -r "minimum_role\|program_role_required" apps/`), remove any remaining call sites, then delete the deprecated functions from `decorators.py`.

---

### NTH-2: No dedicated tests for suggestion theme views
**File:** `apps/notes/suggestion_views.py`
**Severity:** Low
**Detail:** `suggestion_views.py` contains complex business logic for status transitions, note linking/unlinking, and theme management. The test suite covers permission enforcement on these views but does not appear to have a dedicated test file for the core business logic (status transition validation, link/unlink idempotency, audit log emission).
**Recommendation:** Add `tests/test_suggestion_themes.py` covering: happy path status transitions, invalid status rejection, link/unlink with valid and invalid note IDs, audit log emission on status change.

---

### NTH-3: `demo_portal_login()` does not call `session.cycle_key()` or set emergency logout token
**File:** `apps/portal/views.py`
**Severity:** Low
**Detail:** The production portal login (`portal_login()`) correctly calls `request.session.cycle_key()` (session fixation prevention) and `_set_emergency_logout_token()`. The demo portal login path (`demo_portal_login()`) skips both. Demo sessions are lower risk, but inconsistency in the auth pattern is worth noting for future security audits.
**Recommendation:** Add `request.session.cycle_key()` and `_set_emergency_logout_token(request)` to `demo_portal_login()` for consistency.

---

### NTH-4: `program_list()` shows all programs to all authenticated users without pagination
**File:** `apps/programs/views.py` line 34
**Severity:** Low
**Detail:** `Program.objects.all()` with no pagination or limit. For agencies with many programs this will grow without bound and could become slow in combination with the N+1 issue noted in IMP-5.
**Recommendation:** Add `order_by("name")` and consider Django's `Paginator` or a reasonable `.filter(status="active")` default.

---

## Summary Table

| ID | Severity | Area | File(s) | One-line description |
|----|----------|------|---------|----------------------|
| CR-1 | Critical | Security | `static/js/app.js:12` | `allowScriptTags=true` enables XSS via HTMX |
| CR-2 | Critical | Security | 8 locations (see above) | `REMOTE_ADDR` used directly; proxy IPs logged instead of real user IPs |
| IMP-1 | Important | Performance | `admin_settings/models.py:178` | `get_all_flags()` hits DB on every call — 24 callers, only 1 caches |
| IMP-2 | Important | Translation | `locale/fr/LC_MESSAGES/django.po` | 839 of 4,853 strings (~17%) missing French translation |
| IMP-3 | Important | Code quality | 13 locations (see above) | Raw `request.POST.get()` bypasses ModelForm validation |
| IMP-4 | Important | Security/PHIPA | `apps/notes/views.py:~525` | `check_note_date` reveals note metadata without PHIPA consent filter |
| IMP-5 | Important | Performance | `apps/programs/views.py:44–60` | N+1 query: 2N+1 DB hits in `program_list()` |
| IMP-6 | Important | Spelling | `apps/clients/dashboard_views.py:1044,1048` | British spelling "programme" in English user-facing strings |
| IMP-7 | Important | Accessibility | `templates/base.html:143,145,158,160,193,195,234,236` | Incorrect ARIA roles on nav dropdowns (`role="list"`, `role="listbox"`) |
| IMP-8 | Important | Maintainability | `apps/notes/views.py` | Duplicated note-creation logic in `quick_note_create` / `quick_note_inline` |
| IMP-9 | Important | Translation | `apps/auth_app/views.py:185,216,219,224,227,229` | Auth error strings not wrapped in `_()` — always display in English |
| NTH-1 | Low | Code quality | `apps/auth_app/decorators.py` | Deprecated decorators `minimum_role`, `program_role_required` still present |
| NTH-2 | Low | Testing | `apps/notes/suggestion_views.py` | No dedicated tests for suggestion theme business logic |
| NTH-3 | Low | Security | `apps/portal/views.py` | `demo_portal_login()` skips `session.cycle_key()` and emergency logout token |
| NTH-4 | Low | Performance | `apps/programs/views.py:34` | `program_list()` returns all programs with no pagination |

---

## Items Verified Clean

The following areas were checked and found to be correct with no issues:

- **AuditLog dual-database pattern:** All `AuditLog.objects` calls use `.using("audit")` — no violations found across any app.
- **PII encrypted field access:** All client PII accessed via property accessors (e.g., `client.first_name`), never directly via `_first_name_encrypted`. Consistent across all apps.
- **Demo isolation:** `get_client_queryset(user)` used consistently in all client list and search views. Demo users see only `is_demo=True` clients.
- **Cache invalidation signals:** `apps/admin_settings/signals.py` correctly invalidates `"feature_toggles"`, `"terminology_overrides_en"`, `"terminology_overrides_fr"`, and `"instance_settings"` cache keys on `post_save` and `post_delete` for all relevant models.
- **HTMX error handling:** `app.js` lines 238–256 include both `htmx:responseError` and `htmx:sendError` global handlers — errors are not silently swallowed.
- **Open redirect prevention:** `switch_program()` in `programs/views.py` validates `next_url` with `url_has_allowed_host_and_scheme()`.
- **CSRF on portal emergency logout:** `emergency_logout()` uses `@csrf_exempt` with a documented compensating control (session-bound HMAC token via `secrets.compare_digest`) — acceptable.
- **Session fixation on staff login:** Django's `login()` call handles session key rotation internally. `portal_login()` additionally calls `session.cycle_key()` explicitly.
- **RBAC middleware:** `@admin_required`, `@requires_permission()`, and `@login_required` decorators applied consistently on admin and management routes.
- **SQL injection:** No raw SQL queries found. All queries use Django ORM. Encrypted-field searches are done in Python (not SQL) as required.
- **PHIPA consent filtering on note list/detail:** `apply_consent_filter()` called in `note_list()`, `check_note_consent_or_403()` called in `note_detail()`. Portal and aggregate views correctly exempted.
- **Skip-to-content link:** Present in `base.html` — WCAG 2.4.1 satisfied.
- **`aria-current="page"`:** Correctly applied to active nav links in `base.html`.
