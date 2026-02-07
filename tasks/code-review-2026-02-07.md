# Code Review — 2026-02-07

**Branch:** develop (commit 9ffe0b0)
**Scope:** Full codebase — security, code quality, test coverage, translation, accessibility

---

## Overall Assessment

The codebase is in strong shape. Encryption is consistently implemented through property accessors, RBAC middleware provides robust program-scoped access control, the tiered erasure system is well-designed with race condition protection, and there are 1,000+ tests. No raw SQL anywhere. CSRF, XSS, and session security are all solid.

The findings below are real but exist at the edges — places where newer features didn't fully inherit established patterns. Nothing is catastrophic, but the high-severity items should be fixed before the next production deploy.

---

## CRITICAL — Fix Before Next Deploy

### SEC-1. Demo/Real Data Isolation Bypass in Client Views

**Risk:** A demo user who guesses a real client's ID could view or edit their custom fields and consent records (or vice versa).

**Problem:** 5 HTMX endpoints use `get_object_or_404(ClientFile, pk=client_id)` instead of filtering through `get_client_queryset(request.user)` first.

| View | File | Line | Action |
|------|------|------|--------|
| `client_custom_fields_display` | `apps/clients/views.py` | 408 | Read fields |
| `client_custom_fields_edit` | `apps/clients/views.py` | 417 | Edit fields form |
| `client_consent_display` | `apps/clients/views.py` | 512 | Read consent |
| `client_consent_edit` | `apps/clients/views.py` | 527 | Edit consent form |
| `client_consent_save` | `apps/clients/views.py` | 550 | **Write** consent |

**Fix:** Replace `get_object_or_404(ClientFile, pk=client_id)` with `get_object_or_404(get_client_queryset(request.user), pk=client_id)` in each view.

### SEC-2. Missing @admin_required on 6 Registration Submission Views

**Risk:** Any logged-in user (including front desk staff) could view, approve, reject, or merge registration submissions. Currently mitigated by URL-pattern middleware, but fragile.

| View | File | Line |
|------|------|------|
| `submission_list` | `apps/registration/admin_views.py` | 164 |
| `submission_detail` | `apps/registration/admin_views.py` | 200 |
| `submission_approve` | `apps/registration/admin_views.py` | 241 |
| `submission_reject` | `apps/registration/admin_views.py` | 266 |
| `submission_waitlist` | `apps/registration/admin_views.py` | 293 |
| `submission_merge` | `apps/registration/admin_views.py` | 314 |

**Fix:** Add `@admin_required` below `@login_required` on all six views (matching the link management views in the same file).

### SEC-3. Demo Data Bypass in Plan Template Views

Same pattern as SEC-1 but in plan admin views.

| View | File | Line |
|------|------|------|
| `template_apply_list` | `apps/plans/admin_views.py` | 279 |
| `template_apply` | `apps/plans/admin_views.py` | 298 |

**Fix:** Use `get_client_queryset(request.user)` before `get_object_or_404`.

### SEC-4. Submission Merge Also Bypasses Demo Filtering

| View | File | Line |
|------|------|------|
| `submission_merge` | `apps/registration/admin_views.py` | 330 |

**Fix:** Use `get_client_queryset(request.user).get(pk=client_id)`.

---

## HIGH — Fix Soon

### QUAL-1. "cancel" Audit Action Not in ACTION_CHOICES

Two views write `action="cancel"` but it's not in `AuditLog.ACTION_CHOICES` (`apps/audit/models.py:12-25`). Audit filters built from the choices list will miss these entries.

- `apps/notes/views.py:534` — note cancellation
- `apps/events/views.py:214` — alert cancellation

**Fix:** Add `("cancel", _("Cancel"))` to `ACTION_CHOICES` and create a migration.

### QUAL-2. `_get_client_ip()` Duplicated in 6 Files

Identical function copied into:
- `apps/auth_app/views.py:23`
- `apps/reports/views.py:39`
- `apps/programs/views.py:284`
- `apps/clients/erasure_views.py:32`
- `apps/clients/merge_views.py:24`
- `konote/middleware/audit.py:156`

**Fix:** Extract to a shared utility (e.g. `konote/utils.py`), import everywhere.

### QUAL-3. `admin_required` Decorator Duplicated in 4 Files

Four independent copies, with inconsistent translation:
- `apps/auth_app/admin_views.py:20`
- `apps/admin_settings/views.py:13` (only one that translates the error)
- `apps/registration/admin_views.py:45`
- `apps/programs/views.py:29`

**Fix:** Move to `apps/auth_app/decorators.py` (where `minimum_role` already lives), import everywhere. Use `@functools.wraps` and translate the error message.

### QUAL-4. Dead Code in app.js — Duplicate Function Definitions

`initAutoSave` and `setupAutoSave` are defined twice in the same scope. The first definitions (lines 459-486) are dead code, shadowed by the second definitions (lines 512-543).

**Fix:** Delete lines 459-486 in `static/js/app.js`.

### TEST-1. `rotate_encryption_key` Has No Tests

This management command re-encrypts all PII fields. A bug here could make all client data permanently unreadable. Highest-risk untested code in the project.

**Fix:** Write tests covering key rotation, data re-encryption verification, and rollback on failure.

### TEST-2. Account Lockout Logic Has No Tests

The brute-force protection (5 attempts = 15-min lockout) in `apps/auth_app/views.py:36-51` has zero coverage.

**Fix:** Test reaching threshold, being blocked, and clearing on success.

---

## MEDIUM — Address During Normal Development

### Translation Gaps

| ID | What | File(s) |
|----|------|---------|
| I18N-1 | PDF templates entirely untranslated (25-40+ strings each) | `templates/reports/pdf_client_progress.html`, `pdf_funder_report.html`, `pdf_cmt_report.html` |
| I18N-2 | PDF base template hardcoded to `lang="en-CA"` | `templates/reports/pdf_base.html` |
| I18N-3 | Retention alert email untranslated | `templates/email/expired_retention_alert.html` |
| I18N-4 | ~20 JavaScript strings not translatable | `static/js/app.js` |
| I18N-5 | Form labels not translated | `apps/notes/forms.py:151,182,186`, `apps/events/forms.py:48,51,78,96`, `apps/clients/forms.py:41-56` |
| I18N-6 | CSV export headers not translated | `apps/reports/pdf_views.py:371-447` |
| I18N-7 | Hardcoded "Clients" in notes breadcrumbs | `apps/notes/views.py:224,293,407,547,613` |
| I18N-8 | Access denied messages inconsistently translated | Multiple files (see QUAL-3 — consolidating the decorator fixes this) |
| I18N-9 | `privacy.html` breaks sentences across multiple `{% trans %}` tags | `templates/pages/privacy.html:59,71,75,79` |
| I18N-10 | "client" hardcoded in keyboard shortcut description | `templates/base.html:196` |

### Accessibility Gaps

| ID | What | File(s) |
|----|------|---------|
| A11Y-1 | Missing `scope` on `<th>` elements | `privacy.html`, `help.html`, `_note_detail.html`, PDF templates |
| A11Y-2 | Modal focus trap missing | `templates/base.html:187`, `static/js/app.js:604-623` |

### Code Quality

| ID | What | File(s) |
|----|------|---------|
| QUAL-5 | `LANGUAGE_COOKIE_SECURE = True` in dev (language switcher won't persist over HTTP) | `konote/settings/base.py:206` |
| QUAL-6 | Raw `request.POST.get()` in group views (no Django form) | `apps/groups/views.py:218,227,276-280` |
| QUAL-7 | Duplicated custom field context logic in client_detail | `apps/clients/views.py:288-314` vs helper at `351-402` |
| QUAL-8 | Inline admin checks should use decorator | `apps/clients/views.py:691+`, `apps/events/views.py:35+`, `apps/audit/views.py:20+` |

### Test Gaps

| ID | What | Risk |
|----|------|------|
| TEST-3 | Metric CSV import — 140 lines of parsing, no tests | High |
| TEST-4 | Audit log views — no dedicated tests | High |
| TEST-5 | Group session logging — no happy-path tests | High |
| TEST-6 | 12 of 16 management commands untested | Mixed |
| TEST-7 | Note search (encrypted in-memory) — no tests | Medium |
| TEST-8 | Qualitative summary view — no tests | Medium |
| TEST-9 | Plan/event/group forms — no validation tests | Medium |
| TEST-10 | Middleware (audit, safe locale, terminology) — no direct tests | Medium |

---

## Recommended Fix Order

**Immediate (before next deploy):**
1. SEC-1 — Demo isolation bypass in 5 client views (5 one-line changes)
2. SEC-2 — Add @admin_required to 6 registration views (6 one-line changes)
3. SEC-3 — Demo isolation in 2 plan views (2 one-line changes)
4. SEC-4 — Demo isolation in submission merge (1 one-line change)

**Next session:**
5. QUAL-1 — Add "cancel" to audit ACTION_CHOICES
6. QUAL-2 + QUAL-3 — Consolidate _get_client_ip and admin_required (reduces duplication across 10 files)
7. QUAL-4 — Delete dead code in app.js
8. TEST-1 — Write tests for rotate_encryption_key
9. TEST-2 — Write tests for account lockout

**Ongoing:**
10. Translation gaps (I18N-1 through I18N-10) — batch by area
11. Accessibility fixes (A11Y-1, A11Y-2)
12. Remaining test gaps as features are touched
