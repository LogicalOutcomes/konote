# Accessibility Review Report: KoNote

**Date:** 2026-02-06
**External Reviewer:** Jules (Google AI coding agent)
**Internal Verification:** Claude Code (same session)
**Standard:** WCAG 2.2 Level AA

---

## Summary

| Category | Issues Found | Critical | High | Medium | Low |
|----------|-------------|----------|------|--------|-----|
| Perceivable | 1 | 0 | 1 | 0 | 0 |
| Operable | 2 | 0 | 1 | 1 | 0 |
| Understandable | 1 | 0 | 0 | 1 | 0 |
| Robust | 1 | 0 | 0 | 0 | 1 |
| **Total** | **5** | **0** | **2** | **2** | **1** |

**WCAG 2.2 AA Compliant:** With Fixes (after verified findings)

The application has a strong accessibility foundation. Most findings are
about dynamic content (charts, session timer, auto-dismiss) rather than
structural HTML issues.

---

## Findings

### [HIGH-001] Charts Lack Data Table Alternative

- **WCAG Criterion:** 1.1.1 Non-text Content (Level A)
- **Location:** `templates/reports/_tab_analysis.html:12`
- **Issue:** Chart.js canvases have `aria-label` and `role="img"` providing a
  summary (e.g., "Line chart showing Substance Use over time for Goal X"),
  but actual data points (dates and values) are not available to screen readers.
- **Impact:** Blind users cannot access client progress data in charts.
- **Fix:** Add a visually hidden `<table>` or a `<details>` element containing
  the raw data points for each chart.
- **Test:** Use screen reader to verify data points can be navigated.

**Jules' severity:** CRITICAL — Downgraded to HIGH.
**Rationale:** The `aria-label` provides meaningful context (metric name, target
name, chart type). This is better than no alternative at all. A data table
would complete the picture.

### [HIGH-002] Session Timeout Warning Not Announced to Screen Readers

- **WCAG Criterion:** 2.2.1 Timing Adjustable (Level A) / 4.1.3 Status Messages (Level AA)
- **Location:** `static/js/app.js:694-763`
- **Issue:** Session timer updates visual counter and CSS classes (warning,
  critical) but does not announce changes via `aria-live`. When session
  expires, page silently reloads. No option to extend session.
- **Impact:** Screen reader users may be unexpectedly logged out while writing
  long notes, losing unsaved work.
- **Fix:**
  1. Wrap countdown text in `aria-live="polite"` (switch to "assertive" at
     critical threshold).
  2. Add "Extend Session" button that appears at warning threshold.
- **Test:** Wait for timeout threshold, verify screen reader announcement.

**Verification:** Confirmed. Timer element has no `aria-live` attribute.
Code at line 722 just calls `window.location.reload()` with no warning.

### [MEDIUM-001] Full Note Form Errors Not Linked to Inputs

- **WCAG Criterion:** 1.3.1 Info and Relationships / 3.3.1 Error Identification
- **Location:** `templates/notes/note_form.html`
- **Issue:** Error messages use `role="alert"` (good) but input fields don't
  include `aria-describedby` pointing to the error element. Screen reader users
  navigating to a field won't hear its error.
- **Impact:** Screen reader users may miss field-specific errors on the full
  note form.
- **Fix:** Add `aria-describedby="error-id"` to inputs that have errors,
  matching the pattern already used in `quick_note_form.html`.
- **Test:** Submit form with validation errors, inspect HTML for aria-describedby.

**Note:** Quick note form already implements this correctly. Full note form
needs the same treatment.

### [MEDIUM-002] Success Messages Auto-Dismiss Too Quickly

- **WCAG Criterion:** 2.2.1 Timing Adjustable (Level A)
- **Location:** `static/js/app.js:22` (`AUTO_DISMISS_DELAY = 3000`)
- **Issue:** Success notifications disappear after 3 seconds.
- **Impact:** Users with reading disabilities or screen magnification may miss
  the message.
- **Fix:** Increase to 8-10 seconds, or add a close button and let users
  dismiss manually.
- **Test:** Trigger success message, verify it stays visible long enough.

**Verification:** Confirmed. Line 22 sets `AUTO_DISMISS_DELAY = 3000`.

### [LOW-001] Missing 404 and 500 Error Pages

- **WCAG Criterion:** 3.2.3 Consistent Navigation (Level AA)
- **Location:** `templates/` (missing files)
- **Issue:** `404.html` and `500.html` do not exist. Django falls back to
  default error pages without site navigation or styling.
- **Impact:** Users encountering errors lose navigation context.
- **Fix:** Create `404.html` and `500.html` extending `base.html`.
- **Test:** Force a 404 (visit non-existent URL), check it uses site layout.

**Verification:** Confirmed. `403.html` exists but 404 and 500 do not.

---

## Findings Rejected After Verification

### role="grid" on Static Tables (Jules MEDIUM-001)

**Rejected.** `role="grid"` is used on 30+ tables across the codebase.
This is a Pico CSS convention for responsive table styling. Removing it
may break Pico's responsive layout. In practice, modern screen readers
(NVDA, JAWS, VoiceOver) handle `role="grid"` on data tables without
significant issues. Recommend testing with actual screen readers before
changing.

### Autofocus on Login Page (Jules LOW-002)

**Rejected.** `autofocus` on the username field of a login page is expected
behaviour and the logical first interactive element. WCAG does not prohibit
autofocus — it requires logical focus order, which this satisfies.

---

## Recommendations

1. **Chart data tables** — Add hidden data tables for all Chart.js canvases
2. **Session timer aria-live** — Announce countdown at warning and critical
3. **Extend session option** — Add button to reset session timer
4. **Increase auto-dismiss** — Change from 3s to 8-10s
5. **Error pages** — Create 404.html and 500.html extending base.html
6. **Full note form aria-describedby** — Match quick_note_form pattern

---

## Review Metadata

- **Framework:** `tasks/code-review-framework.md` Prompt C (Accessibility)
- **Tool:** Jules (jules.google) — Gemini-powered code review agent
- **Repo:** github.com/gilliankerr/KoNote-Redux (public, main branch)
- **Previous reviews:** Security (2026-02-06), Privacy (2026-02-06)
- **Next scheduled:** Before each release or after template/CSS changes
