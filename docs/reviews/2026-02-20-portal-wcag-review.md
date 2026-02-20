# Portal WCAG 2.2 AA Accessibility Review

**Date:** 2026-02-20
**Scope:** All 34 templates in `apps/portal/templates/portal/`, `static/css/portal.css`
**Standard:** WCAG 2.2 Level AA

## Summary

- **WCAG compliance level:** AA (after fixes below)
- **Critical issues:** 0
- **Major issues:** 3 (fixed)
- **Minor issues:** 2 (fixed)

The portal was already well-built for accessibility. Most WCAG 2.2 AA requirements were met from the start.

## What Was Already Good

- **Skip navigation** (`base_portal.html:36`) — Skip-to-content link with visible focus style
- **`lang` attribute** (`base_portal.html:5`) — Dynamic `{{ LANGUAGE_CODE }}` on `<html>`
- **Language toggle** — `lang` and `hreflang` attributes on both EN/FR buttons
- **Navigation landmarks** — `aria-label="Main navigation"`, `aria-label="Language selection"`
- **Form labels** — All inputs have associated `<label>` elements across all form templates
- **Error messages** — `role="alert"` on all error messages
- **Status messages** — `role="status"` and `aria-live="polite"` on success messages
- **Heading hierarchy** — h1 → h2 throughout, no levels skipped
- **SVG icons** — All decorative SVGs have `aria-hidden="true"`
- **Quick-exit button** — `aria-label`, visible focus indicator, keyboard accessible
- **Touch targets** — 44px minimum on nav links and card links
- **Form descriptions** — `aria-describedby` for help text on all form fields
- **Required fields** — Both `required` attribute and `aria-required="true"` on inputs
- **Session timeout** — Native `<dialog>` with `aria-labelledby` and `aria-describedby`
- **`<main>` landmark** — Present with `tabindex="-1"` for focus management
- **Footer** — `role="contentinfo"`
- **Survey forms** — `<fieldset>` + `<legend>` for radio/checkbox groups
- **Tables** — `scope="col"` on column headers, `aria-label` on data tables
- **Progress indicator** — `<progress>` element with `aria-label` and `aria-live`
- **Conditional content** — Design doc specifies `aria-live="polite"` for dynamic sections
- **Charts** — Canvas elements have `role="img"` and `aria-label`
- **Breadcrumbs** — `aria-label="Breadcrumb"` and `aria-current="page"`
- **Consent flow** — `aria-current="step"` on active step in progress indicator
- **Crisis resources** — Proper landmark with `aria-label="Crisis resources"`
- **Focus management** — Survey forms focus heading on page load for multi-page forms

## Issues Fixed

### Major

1. **Language toggle touch target below 44px** (WCAG 2.5.8 Target Size)
   - **File:** `static/css/portal.css:63`
   - **Was:** `min-height: 36px`
   - **Fix:** Changed to `min-height: 44px; min-width: 44px`

2. **Analytics card headers missing heading elements** (WCAG 1.3.1 Info and Relationships)
   - **File:** `apps/portal/templates/portal/analytics.html:12,30,50`
   - **Was:** `<header>{% trans "Accounts" %}</header>` — plain text in header
   - **Fix:** Wrapped in `<h2>` with `id`, added `aria-labelledby` to parent `<article>`

3. **Logout button missing focus-visible styles** (WCAG 2.4.7 Focus Visible)
   - **File:** `static/css/portal.css:164`
   - **Was:** Only `:hover` styles defined
   - **Fix:** Added `:focus-visible` with `outline: 2px solid` for keyboard users

### Minor

4. **Banner dismiss button lacked minimum touch target** (WCAG 2.5.8)
   - **File:** `static/css/portal.css` (new rule)
   - **Fix:** Added `.portal-banner-dismiss` with `min-height: 44px; min-width: 44px` and `:focus-visible` outline

5. **Survey thank-you scores table missing `<thead>`** (WCAG 1.3.1)
   - **File:** `apps/portal/templates/portal/survey_thank_you.html:14`
   - **Was:** Table had `<tbody>` only, no column headers
   - **Fix:** Added `<thead>` with `<th scope="col">` for Section and Score columns

## Not Issues (Verified)

- **Required field indicators** — `<abbr title="required" aria-hidden="true">*</abbr>` is hidden from screen readers because `required`/`aria-required="true"` conveys the same information. This is correct practice.
- **Colour contrast** — Portal uses Pico CSS defaults (high contrast) and `#0d7377` on white (4.6:1 — passes AA). Quick-exit button uses white on `#c62828` (5.4:1 — passes AA).
- **`<details>` elements** — Used for safety help page and crisis resources. These are natively accessible.
- **Inline styles on staff pages** — `style="font-size: 1rem"` on headings doesn't affect accessibility since the heading level is correct.
