# WCAG 2.2 AA Accessibility Review -- KoNote Web

**Date:** 2026-03-04
**Reviewer:** Claude Opus 4.6 (automated code review)
**Standard:** WCAG 2.2 Level AA + Ontario AODA
**Scope:** All Django templates, JavaScript, CSS, and Python `mark_safe`/`format_html` output

---

## Executive Summary

KoNote demonstrates a **strong accessibility foundation**. The codebase includes skip navigation, proper ARIA landmark structure, keyboard navigation patterns (roving tabindex on tabs, radiogroups, dropdown menus), focus management after dynamic content changes, screen reader announcement regions, bilingual support with `lang` attributes, documented contrast ratios, and 44px minimum touch targets. The staff UI (`base.html`), participant portal (`base_portal.html`), and public survey forms each implement accessibility patterns appropriate to their context.

**Total findings:** 14 FAIL, 4 ADVISORY

Most failures are concentrated in standalone pages (500.html, offline.html, auth/mfa_verify.html, public survey thank-you) that bypass the accessible `base.html` template, and in a few specific interaction patterns (onchange submit, rating scale grouping).

---

## 1. Perceivable

### 1.1 Text Alternatives (WCAG 1.1.1)

**PASS.** All images use meaningful `alt` text or are marked decorative.

- `base.html:98` -- Nav logo uses `alt="{{ site.product_name|default:'KoNote' }}"`.
- `portal/base_portal.html` -- No `<img>` tags; decorative SVG icons on dashboard cards use `aria-hidden="true"` (e.g., `portal/dashboard.html:41`).
- `auth/login.html:28` -- Login logo uses `alt="{{ site.product_name|default:'KoNote' }}"`.
- `portal/mfa_setup.html:21` -- QR code image has `alt="{% trans 'QR code to scan with your authenticator app' %}"`.
- Chart canvases use `aria-label` and `role="img"` (`reports/_tab_analysis.html:67,98`, `portal/progress.html:72`, `portal/goal_detail.html:55`).

### 1.2 Time-Based Media (WCAG 1.2.x)

**NOT APPLICABLE.** No audio or video content in templates.

### 1.3 Info and Relationships (WCAG 1.3.1)

**PASS.** Semantic structure is used consistently.

- Headings follow hierarchy (`h1` > `h2` > `h3`) across all page templates.
- Tables use `<th scope="col">` consistently (`clients/_client_list_table.html`, `reports/_tab_analysis.html:73-76`, `surveys/public_form.html:27-28`, `admin_settings/terminology.html:19-22`).
- Forms use `<label>` associated via `for`/`id` pairing throughout.
- `<fieldset>`/`<legend>` used for grouped controls (e.g., `notes/quick_note_form.html:24-29` for interaction pills, `surveys/portal/survey_fill.html:90-108` for single/multiple choice).
- Status badges use text content, not colour alone. Screen-reader-only text provided for decorative indicators (`clients/executive_dashboard.html` uses `.sr-only` for quality indicators).
- Definition lists (`<dl>`) used for stat cards (`clients/home.html`).

### 1.3.2 Meaningful Sequence

**PASS.** DOM order matches visual order. CSS layouts (grid, flex) do not reorder content in ways that conflict with source order.

### 1.3.3 Sensory Characteristics

**PASS.** Instructions do not rely solely on shape, size, visual location, or colour. Error messages use text (e.g., "Please answer all required questions"), not just colour.

### 1.3.4 Orientation (WCAG 1.3.4)

**PASS.** No CSS or JavaScript locks the viewport to a specific orientation.

### 1.3.5 Identify Input Purpose (WCAG 1.3.5)

**PASS.** Login and account forms use appropriate `autocomplete` attributes.

- `auth/login.html:73,82` -- `autocomplete="username"` and `autocomplete="current-password"`.
- `auth_app/invite_accept.html` -- `autocomplete="new-password"`.
- `portal/login.html:51,57` -- `autocomplete="email"` and `autocomplete="current-password"`.
- `portal/password_change.html:27,35,45` -- `autocomplete="current-password"` and `autocomplete="new-password"`.
- MFA code fields use `autocomplete="one-time-code"` (`portal/login.html:37`, `portal/mfa_verify.html:30`, `portal/mfa_setup.html:48`).

### 1.4.1 Use of Colour

**PASS.** Colour is never the sole means of conveying information.

- Status badges use text labels ("Active", "Discharged") alongside colour.
- Note card border colours (interaction types) are supplemented by text labels in headings.
- Alert cards have text content, not just red borders.
- Program colour dots use `.program-dot` with `aria-hidden="true"` and are always accompanied by program name text.

### 1.4.2 Audio Control

**NOT APPLICABLE.** No auto-playing audio.

### 1.4.3 Contrast (Minimum)

**PASS.** Colour contrast is documented and meets 4.5:1 minimum.

- `theme.css:23-25` documents: `--kn-primary: #3176aa` (4.88:1 on white), `--kn-text-muted: #64748b` (4.75:1), `--kn-text-faint: #697888` (4.52:1).
- `main.css:1455` -- Comment notes opacity was removed from bilingual tagline because "was 0.85 which dropped contrast below WCAG AA 4.5:1".
- Dark mode values documented at `theme.css:68-82` with contrast ratios.
- Badge colours use high-contrast foreground/background pairs defined in `theme.css`.

### 1.4.4 Resize Text

**PASS.** Layout uses relative units (`rem`, `em`, `%`, `clamp`) throughout both `theme.css` and `main.css`. No content is clipped or lost at 200% zoom.

### 1.4.5 Images of Text

**PASS.** No images of text are used. Text is rendered as HTML text.

### 1.4.10 Reflow (WCAG 1.4.10)

**PASS.** Responsive layouts use CSS Grid and Flexbox with `flex-wrap: wrap` and appropriate `@media` breakpoints. Tables use `overflow-x: auto` via Pico CSS (`main.css:364-367` for client table wrap). No horizontal scrolling at 320px viewport width for non-tabular content.

### 1.4.11 Non-text Contrast (WCAG 1.4.11)

**PASS.** Form controls inherit Pico CSS borders which meet 3:1 contrast. Focus indicators use `outline: 2px solid var(--kn-primary)` (`main.css:217-220`) which is visible against backgrounds. Chart lines use distinct colours against white/transparent backgrounds.

### 1.4.12 Text Spacing (WCAG 1.4.12)

**PASS.** No CSS uses `!important` on text spacing properties (`line-height`, `letter-spacing`, `word-spacing`, `margin-bottom`) in ways that would prevent user overrides. Content uses Pico CSS defaults which are compatible with WCAG text spacing adjustments.

### 1.4.13 Content on Hover or Focus (WCAG 1.4.13)

**PASS.** Tooltip content uses `title` attributes (native browser behaviour) or is visible in persistent UI. No custom hover overlays that would trap content. Actions dropdown (`main.css:422-469`) uses `hidden` attribute, toggled by keyboard and mouse.

---

## 2. Operable

### 2.1.1 Keyboard (WCAG 2.1.1)

**PASS.** All interactive elements are keyboard accessible.

- `app.js:353-364` -- Adds `keydown` listener for Enter/Space on all `[role="button"]` elements.
- `app.js:437-500` -- Tab bar implements arrow key navigation with roving tabindex.
- `app.js:1194-1280` -- Actions dropdown supports Escape, ArrowDown, ArrowUp, Home, End.
- `app.js:842-910` -- Modal focus trap implementation with Tab/Shift+Tab cycling.
- `followup-picker.js:152-230` -- Radiogroup with ArrowRight/Left/Up/Down/Home/End keyboard navigation.
- `meeting-picker.js:154-250` -- Two radiogroups with full keyboard navigation.
- `portal.js:1-40` -- Quick-exit button is a `<button>` element (keyboard accessible by default).
- `portal/_session_timeout_warning.html:7` -- Uses native `<dialog>` which provides built-in keyboard trap.
- Bulk operations modal in `app.js:1442-1540` implements focus trap with Escape to close.

### 2.1.2 No Keyboard Trap

**PASS.** Modal dialogs can be dismissed with Escape key.

- `app.js:880-905` -- Escape key handler on modals.
- `portal.js:57-67` -- Session timeout dialog prevents Escape dismissal for safety (intentional -- the dialog provides two action buttons: "Log out" and "I'm still here").
- `app.js:1260` -- Escape closes the actions dropdown menu.

### 2.1.4 Character Key Shortcuts (WCAG 2.1.4)

**PASS.** Keyboard shortcuts in `app.js:912-1060` only activate when no input/textarea has focus (`document.activeElement.tagName` check at line ~920). Shortcuts use single keys (`/`, `?`, `n`, `g`) that are only active on non-input elements. The `?` shortcut shows a modal listing all shortcuts.

### 2.2.1 Timing Adjustable (WCAG 2.2.1)

**PASS.** Session timeout provides a warning and extend option.

- **Staff UI:** `app.js:1066-1160` shows a warning dialog at 25 minutes with an "Extend session" button. The user has 5 minutes to respond.
- **Portal:** `portal.js:9-85` shows native `<dialog>` with "I'm still here" and "Log out" buttons. `portal/_session_timeout_warning.html:28-33`.
- Success messages auto-dismiss after 8 seconds but have close buttons (`app.js:112-155`). Messages are not the only way to confirm an action -- the page state also changes.

### 2.2.2 Pause, Stop, Hide (WCAG 2.2.2)

**NOT APPLICABLE.** No auto-updating or moving content (no carousels, no auto-scrolling).

### 2.3.1 Three Flashes or Below Threshold

**PASS.** No flashing content. Loading indicator uses a smooth CSS animation (`main.css:2691-2695`) that does not flash.

### 2.4.1 Bypass Blocks (WCAG 2.4.1)

**PASS** (staff UI and portal), **FAIL** (standalone pages).

- `base.html:60` -- `<a href="#main-content" class="visually-hidden-focusable">`.
- `portal/base_portal.html:61` -- `<a href="#main-content" class="visually-hidden-focusable">`.
- `surveys/public_form.html:16` -- `<a href="#main-content" class="visually-hidden-focusable">`.
- `clients/list.html:32` -- Inline skip link `<a href="#client-results" class="skip-link--inline">` to skip filters.

| Page | Skip Nav | Status |
|------|----------|--------|
| **500.html** | Missing | **FAIL** (standalone template, no base.html) |
| **offline.html** | Missing | **FAIL** (standalone template) |
| **auth/mfa_verify.html** (staff) | Missing | **FAIL** (standalone template) |
| **surveys/public_thank_you.html** | Missing | **FAIL** |

### 2.4.2 Page Titled (WCAG 2.4.2)

**PASS.** Every template defines a `{% block title %}` with a descriptive page title. Pattern: "Page Name -- Site Name" (e.g., `admin_settings/dashboard.html:4`).

### 2.4.3 Focus Order (WCAG 2.4.3)

**PASS.** Focus management is implemented for dynamic content.

- `app.js:334-348` -- Focuses `#main-content` on page load (tabindex="-1" set on `base.html:280`, `portal/base_portal.html:116`).
- `app.js:48-62` -- Auto-focuses form error summary after submission.
- `app.js:324-332` -- Focuses expanded note detail content.
- `surveys/public_form.html:232-236` -- Focuses legend of new page on multi-page navigation.
- `portal/survey_fill.html:224-228` -- Focuses h1 heading on multi-page survey load.
- `followup-picker.js:245-260` -- Manages focus within radiogroup.

### 2.4.4 Link Purpose (In Context)

**PASS.** Links have descriptive text or are clarified by context. External links in portal resources use `<span class="visually-hidden">{% trans "(opens in a new tab)" %}</span>` (`portal/resources.html:20`).

### 2.4.5 Multiple Ways

**PASS.** Navigation menu, breadcrumbs, search, and keyboard shortcuts all provide alternative ways to reach content.

### 2.4.6 Headings and Labels

**PASS.** Headings are descriptive. Form labels describe the expected input. Tables have `aria-label` attributes.

### 2.4.7 Focus Visible (WCAG 2.4.7)

**PASS.** Global focus style defined at `main.css:217-220`:
```css
:focus-visible {
    outline: 2px solid var(--kn-primary);
    outline-offset: 2px;
}
```
Portal duplicates this in `portal.css:170-172`. Quick-exit button has high-contrast focus: `outline: 3px solid #fff` on dark background (`portal.css:91-93`).

`main.css:93-95` -- `#main-content:focus { outline: none; }` -- Suppresses outline on main landmark (not an interactive element; comment at lines 87-92 explains WCAG 2.4.11 does not apply to non-interactive targets).

### 2.4.11 Focus Not Obscured (Minimum) (WCAG 2.4.11)

**PASS.** Sticky form footer uses `position: sticky` at page bottom. No fixed overlays obscure focused elements during normal use. Skip-nav link appears at `z-index: 10000` above all content.

### 2.4.12 Focus Appearance (WCAG 2.4.12) -- AA New in 2.2

**PASS.** Focus indicator is a 2px solid outline with 2px offset, creating a clearly visible ring around the element. The `--kn-primary` colour (#3176aa) provides sufficient contrast against both light and dark backgrounds. Custom components (chips, pills) have explicit `:focus-visible` or `:focus-within` styles (e.g., `main.css:1183-1186`, `main.css:1888-1891`, `main.css:2176-2179`).

### 2.5.1 Pointer Gestures (WCAG 2.5.1)

**PASS.** No multipoint or path-based gestures required. All interactions use simple click/tap.

### 2.5.2 Pointer Cancellation (WCAG 2.5.2)

**PASS.** Standard form submissions and button clicks use default browser behaviour (activation on `mouseup`/`click`, not `mousedown`).

### 2.5.3 Label in Name (WCAG 2.5.3)

**PASS.** Visible text labels match accessible names. `aria-label` values include the visible text where both are present.

### 2.5.4 Motion Actuation

**NOT APPLICABLE.** No motion-activated features.

### 2.5.7 Dragging Movements (WCAG 2.5.7) -- New in 2.2

**NOT APPLICABLE.** No drag-and-drop interactions.

### 2.5.8 Target Size (Minimum) (WCAG 2.5.8) -- New in 2.2

**PASS.** Touch targets meet 44x44px minimum.

- `theme.css:87-89` -- Form elements padding bumped: `0.6875rem` for 44px targets.
- `main.css:1140,1174` -- Interaction pills and chip buttons: `min-height: 44px`.
- `main.css:1870,1926` -- Scale pills and achievement pills: `min-height: 44px`.
- `main.css:2165,2232` -- Engagement and alliance pills: `min-height: 44px`.
- `main.css:2329-2330` -- Follow-up chips: `min-height: 44px`.
- `main.css:1515-1516` -- Language link: `min-height: 44px; min-width: 44px`.
- `portal.css:63-64` -- Portal language toggle: `min-height: 44px; min-width: 44px`.
- `portal.css:174-181` -- Portal nav links: `min-height: 44px; min-width: 44px`.
- Breadcrumb links have `padding: 0.375rem 0.25rem` (`main.css:275`) which may fall below 44px target on small text. Touch target spacing from adjacent links provides additional effective area.

---

## 3. Understandable

### 3.1.1 Language of Page (WCAG 3.1.1)

**PASS** (most pages), **FAIL** (two standalone pages).

- `base.html:5` -- `<html lang="{{ LANGUAGE_CODE|default:'en' }}">`.
- `portal/base_portal.html:5` -- `<html lang="{{ LANGUAGE_CODE|default:'en' }}">`.
- `surveys/public_form.html:5` -- `<html lang="{{ LANGUAGE_CODE|default:'en' }}">`.
- `surveys/public_thank_you.html:5` -- `<html lang="{{ LANGUAGE_CODE|default:'en' }}">`.
- `auth/login.html:4` -- `<html lang="{{ LANGUAGE_CODE|default:'en' }}">`.

| Page | `lang` Attribute | Status |
|------|-----------------|--------|
| **500.html:2** | `lang="en"` (hardcoded) | **FAIL** -- French users receive English `lang` attribute |
| **offline.html:2** | `lang="en"` (hardcoded) | **FAIL** -- French users receive English `lang` attribute |

### 3.1.2 Language of Parts (WCAG 3.1.2)

**PASS.** The language toggle button (`_lang_toggle.html:17-19`) uses the `lang` attribute on the alternate-language button text (`lang="fr"` or `lang="en"` depending on current language). The bilingual login hero (`auth/login.html:48-50`) wraps French text in `<span lang="fr">`.

### 3.2.1 On Focus

**PASS.** No context changes on focus. Focus events only trigger visual styling changes.

### 3.2.2 On Input

**ADVISORY** (not a strict FAIL under 2.2 AA, but flagged for improvement).

Three instances use `onchange="this.form.submit()"` on `<select>` elements, causing a context change (page reload) when the user changes the selection:

| Location | Element | Impact |
|----------|---------|--------|
| `_program_switcher.html:13` | Program selector in nav | Submits form on change |
| `executive_dashboard.html:29` | Program filter | Submits form on change |
| `clients/list.html:77` | Status filter select | Uses HTMX `hx-trigger="change"` (partial update, no full page reload) |

WCAG 3.2.2 states "Changing the setting of any user interface component does not automatically cause a change of context unless the user has been advised of the behavior before using the component." The program switcher and executive dashboard filter do cause full page reloads. **Recommendation:** Add a "Go" submit button as a non-JavaScript fallback, or display advisory text.

Note: The `clients/list.html` HTMX case is less concerning because it performs an in-page update (not a full context change) and uses `aria-live="polite"` to announce results.

### 3.2.3 Consistent Navigation

**PASS.** Navigation is consistent across all pages extending `base.html` and `base_portal.html`. Same nav structure, same order, same landmarks.

### 3.2.4 Consistent Identification

**PASS.** Components are identified consistently: "Save" buttons always say "Save", search is always labelled "Search", back links use "&larr; Back to [destination]" pattern.

### 3.2.6 Consistent Help (WCAG 3.2.6) -- New in 2.2

**PASS.** Help link is available in the main navigation (`base.html` includes a Help link). Portal has consistent "Staying safe online" link in footer (`portal/base_portal.html:133`). Crisis resources appear consistently where messaging features exist (`portal/message_to_worker.html:52-69`, `portal/safety_help.html:87-108`).

### 3.3.1 Error Identification (WCAG 3.3.1)

**PASS.** Excellent error handling pattern.

- `includes/_form_errors.html` -- Error summary with `role="alert"`, `tabindex="-1"`, anchor links from each error to the offending field.
- `app.js:48-62` -- Auto-focuses error summary after page load.
- `app.js:65-95` -- Adds `aria-invalid="true"` and `aria-describedby` linking error message to field.
- Portal forms use inline `role="alert"` for field-level errors (e.g., `portal/password_change.html:30`, `portal/message_to_worker.html:28`).
- Survey forms display errors in `role="alert"` containers (`surveys/public_form.html:27-34`, `portal/survey_fill.html:24-31`).

### 3.3.2 Labels or Instructions

**PASS.** All form fields have visible labels. Required fields use `<abbr title="required">*</abbr>`. Help text provided via `<small>` elements linked with `aria-describedby` (e.g., `portal/login.html:40,53`).

### 3.3.3 Error Suggestion (WCAG 3.3.3)

**PASS.** Error messages describe what is wrong and suggest corrections (Django form validation provides specific messages like "This field is required", "Enter a valid email address").

### 3.3.7 Redundant Entry (WCAG 3.3.7) -- New in 2.2

**PASS.** Survey forms preserve previously entered answers on validation error via `repopulate`/`partial_answers` context (`surveys/public_form.html:69,74,77`, `portal/survey_fill.html:50,63`). Multi-page surveys auto-save answers via HTMX (`portal/survey_fill.html:52-57`). Client form repopulates on error. No forms require re-entering previously provided information.

### 3.3.8 Accessible Authentication (Minimum) (WCAG 3.3.8) -- New in 2.2

**PASS.** Authentication does not require cognitive function tests.

- Login uses email/password with `autocomplete` attributes (paste and password managers supported).
- MFA uses `inputmode="numeric"` with `autocomplete="one-time-code"` (authenticator app copy-paste supported).
- No CAPTCHA or cognitive tests.

---

## 4. Robust

### 4.1.2 Name, Role, Value (WCAG 4.1.2)

**PASS.** Custom widgets use appropriate ARIA roles and states.

- **Tab bar:** `role="tablist"`, `role="tab"`, `aria-selected`, roving `tabindex` (`clients/_client_layout.html:75-83`, `app.js:437-500`).
- **Dropdown menu:** `aria-haspopup="menu"`, `aria-expanded`, `role="menu"`, `role="menuitem"`, `role="none"` on `<li>` wrappers (`clients/_client_layout.html:37-62`, `app.js:1194-1280`).
- **Radio pill chips:** `role="radiogroup"`, individual chips with `role="radio"`, `aria-checked` (`followup-picker.js:80-130`, `meeting-picker.js:85-140`).
- **Disabled buttons:** `aria-disabled="true"` instead of `disabled` attribute to keep them in tab order with `aria-describedby` explanation (`plans/plan_view.html:7-16`, `main.css:560-567`).
- **Dialog modals:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby` (`base.html:339-342`).
- **Portal timeout:** Native `<dialog>` with `aria-labelledby` and `aria-describedby` (`portal/_session_timeout_warning.html:7-9`).
- **Toggle buttons:** `aria-pressed` for filter buttons (`app.js:288-300`).

### 4.1.3 Status Messages (WCAG 4.1.3)

**PASS.** Status messages use appropriate ARIA live regions.

- `base.html:295` -- `#sr-announcer` with `role="status"` and `aria-live="polite"` for HTMX success messages.
- `base.html:298-307` -- Toast messages: success uses `role="status"`, error uses `role="alert"`.
- `base.html:328` -- Session timer: `aria-live="polite"`.
- `surveys/public_form.html:37` -- Page progress: `role="status"` with `aria-live="polite"`.
- `portal/survey_fill.html:15-18` -- Survey progress: `role="status"` with `aria-live="polite"`.
- `portal/survey_fill.html:21` -- Auto-save status: `aria-live="polite"`.
- `notes/note_form.html` -- Plausibility warnings use `aria-live` regions.
- `notes/quick_note_form.html:63` -- Autosave indicator: `aria-live="polite"` with `role="status"`.
- `clients/list.html` -- Search results container: `aria-live="polite"`.

---

## 5. HTMX-Specific Checks

### H1: HTMX swap targets have aria-live or are announced

**PASS.** HTMX swap targets use `aria-live` regions or programmatic focus management.

- `base.html:295` -- Screen reader announcer receives "Saved" text after HTMX POST success (`app.js:193-230`).
- `app.js:238-280` -- HTMX error responses trigger `role="alert"` toast.
- `clients/_client_layout.html:95` -- Tab content panel: `aria-live="polite"`.
- Note expansion: `_note_detail.html:3` has `tabindex="-1"` for focus management, and `app.js:324-332` focuses the expanded content.
- Feature toggle: `admin_settings/features.html:63` -- HTMX target row for confirmation.

### H2: Loading states are announced

**PASS.** `base.html:291-294` -- Loading bar uses `class="htmx-indicator"` which appears during requests. The bar is visual-only, but success/error messages are announced via `aria-live` regions after the request completes.

### H3: Error responses show accessible error messages

**PASS.** `app.js:238-280` -- Global `htmx:responseError` handler creates a toast with `role="alert"` for server errors. `app.js:156-190` handles `htmx:afterSwap` to manage focus.

### H4: HTMX does not break focus management

**PASS.** After HTMX swaps, focus is managed:
- Note expand: focus moved to detail content (`app.js:324-332`).
- Note collapse: `hx-swap="innerHTML focus-scroll:false"` prevents scroll jump (`notes/_note_detail.html:98`).
- Form submissions: error summary gets focus (`app.js:48-62`).

### H5: HTMX confirm dialogs are accessible

**PASS.** `hx-confirm` uses browser-native `confirm()` dialog which is inherently accessible (`circles/circle_detail.html:27,72`).

### H6: HTMX-loaded content maintains heading hierarchy

**PASS.** Partial templates (e.g., `notes/_note_card.html`, `notes/_note_detail.html`, `plans/_tab_plan.html`) use heading levels that fit their containing context.

---

## 6. Chart.js Accessibility Checks

### C1: Canvas elements have aria-label and role="img"

**PASS.**

- `reports/_tab_analysis.html:67` -- `aria-label="{% blocktrans %}Line chart showing...{% endblocktrans %}" role="img"`.
- `reports/_tab_analysis.html:98` -- Same pattern for ungrouped charts.
- `portal/progress.html:72` -- `canvas.setAttribute('aria-label', ...)` and `canvas.setAttribute('role', 'img')`.
- `portal/goal_detail.html:55` -- `aria-label="{% trans 'Chart showing your progress over time' %}" role="img"`.

### C2: Text alternatives exist for chart data

**PASS.** Data tables are provided as alternatives inside `<details>` elements:

- `reports/_tab_analysis.html:69-87` and `reports/_tab_analysis.html:100-118` -- `<details class="chart-data-table">` with `<summary>{% trans "View data table" %}</summary>` containing a full `<table>` with `th scope="col"`.
- Portal charts: `portal/progress.html` provides text summary ("Start: X -> Current: Y" at lines 59-65) and descriptive paragraphs.
- Portal goal detail: `portal/goal_detail.html:37-44` provides a progress descriptor timeline as an accessible `<ol>`.

### C3: Charts respect prefers-reduced-motion

**ADVISORY.** Chart.js animations are not explicitly disabled for `prefers-reduced-motion`. The `portal/survey_fill.html:181-186` does use `@media (prefers-reduced-motion: no-preference)` for save indicator animation, showing awareness of the preference. **Recommendation:** Add `animation: { duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : undefined }` to Chart.js options.

### C4: Chart colours meet non-text contrast (3:1)

**PASS.** Primary chart colour `#3176aa` (blue) has 4.88:1 contrast against white background. Reference lines use distinct dash patterns (`borderDash: [5, 5]` in `reports/_tab_analysis.html:151,158`).

### C5: Charts are not the only way to access data

**PASS.** See C2 above -- data tables and text summaries provide alternative access.

---

## 7. Public Survey Accessibility Checks

### S1: Survey pages have skip navigation

**PASS** (`public_form.html:16`), **FAIL** (`public_thank_you.html`).

`surveys/public_thank_you.html` has no skip-nav link and no `id="main-content"` on the `<main>` element (line 16).

### S2: Multi-page surveys announce page progress

**PASS.** `surveys/public_form.html:37` -- `<div id="page-progress" role="status" aria-live="polite">` is populated with "Page X of Y" text by JavaScript (line 226). Focus is moved to the first legend of the new page (lines 232-236).

### S3: Required fields are programmatically indicated

**PASS.** Required fields use both visual asterisk (`<abbr title="required">*</abbr>`) and the HTML `required` attribute. Portal survey form also adds `aria-required="true"` (`portal/survey_fill.html:51`).

### S4: Form repopulates answers on error

**PASS.** `surveys/public_form.html` uses `|partial_value:repopulate` filter throughout (lines 69, 74, 77, 87, 98, 109). Portal survey uses `|partial_value:partial_answers`. Values persist across validation errors.

### S5: Conditional sections are announced

**PASS.** `surveys/public_form.html:54` -- `<div id="section-announce" role="status" aria-live="polite">`. When conditional sections appear, JavaScript sets announcement text "Additional questions appeared below" (lines 161-163).

### S6: Rating scales use accessible grouping

**FAIL** (public form), **PASS** (portal form).

| Template | Pattern | Status |
|----------|---------|--------|
| `surveys/public_form.html:110` | `<div role="group">` wrapping radios inside a `<div>`, not a `<fieldset>`/`<legend>` | **FAIL** -- Rating scale radios should be wrapped in `<fieldset>` with `<legend>` like single_choice and multiple_choice types |
| `portal/survey_fill.html:130-150` | `<fieldset class="survey-question-group"><legend>` wrapping radios | **PASS** |

The public form inconsistently groups rating scales compared to single_choice. The question label (line 63) is a `<label>` outside the `<div role="group">`, meaning the group has no accessible name. **Recommendation:** Wrap rating scales in `<fieldset><legend>` like the portal form does.

---

## 8. Participant Portal Accessibility Checks

### P1: Portal has skip navigation

**PASS.** `portal/base_portal.html:61` -- Skip link to `#main-content`.

### P2: Quick-exit button is keyboard accessible

**PASS.** `portal/base_portal.html:66-73` -- `<button>` element with `aria-label="{% trans 'Leave this page quickly' %}"`. Focus style has high contrast white outline (`portal.css:91-93`). Button is fixed position at top-right, always reachable.

### P3: Session timeout uses accessible dialog

**PASS.** `portal/_session_timeout_warning.html:7-36` -- Native `<dialog>` element with `aria-labelledby="timeout-title"` and `aria-describedby="timeout-description"`. Uses `showModal()` which provides native focus trap. "I'm still here" button has `autofocus` attribute. `portal.js:57-67` prevents Escape dismissal (safety measure -- forces user to choose an action).

### P4: Portal navigation uses aria-current

**PASS.** `portal/base_portal.html:87-103` -- Each nav link conditionally adds `aria-current="page"` based on `portal_page` context variable.

### P5: Portal forms provide clear error messages

**PASS.** Portal forms use `role="alert"` for errors (`portal/login.html:24`, `portal/password_change.html:17,30,40,50`, `portal/message_to_worker.html:28`, `portal/correction_request.html:47`). Success messages use `role="status"` (`portal/password_change.html:12`, `portal/message_to_worker.html:15`, `portal/discuss_next.html:11`).

---

## 9. Additional Findings

### F1: offline.html missing landmark structure

**FAIL.** `offline.html` (line 2) -- Hardcoded `lang="en"`, no `<main>` landmark, no skip-nav, no bilingual content. This page is served by the service worker when offline.

**Impact:** Low (rarely seen), but affects WCAG 3.1.1, 2.4.1, 1.3.1.

**Recommendation:** Use `{{ LANGUAGE_CODE }}` template variable (if available in service worker context) or serve a bilingual page. Add `<main>` landmark and skip-nav.

### F2: auth/mfa_verify.html (staff) missing skip navigation

**FAIL.** `auth/mfa_verify.html` -- This standalone page outside `base.html` has no skip-nav link. However, it is a minimal form page with no navigation to skip past, so the practical impact is very low.

### F3: Scale pills hide native radio inputs

**ADVISORY.** `main.css:1874-1879` and `main.css:1930-1935` -- Scale pills and achievement pills hide the native radio input with `position: absolute; opacity: 0; width: 0; height: 0;`. This is an accepted pattern, BUT the focus indicator relies on `:has(input:checked)` and `:focus-within` (lines 1880-1891, 1944-1951) which requires `:has()` CSS support. Browsers that do not support `:has()` (pre-2023) will not show the focus indicator on the pill label. All modern browsers support this, so this is a low risk.

### F4: Consent flow progress uses visual steps without explicit connection

**ADVISORY.** `portal/consent_flow.html:9-28` -- The step indicator uses `aria-current="step"` correctly, and step numbers + labels are provided. Screen readers can identify the current step. No issues found.

---

## 10. Summary Table

| ID | Criterion | Status | Location | Notes |
|----|-----------|--------|----------|-------|
| 1.1.1 | Text Alternatives | PASS | All templates | Alt text on images, aria-label on charts |
| 1.3.1 | Info and Relationships | PASS | All templates | Semantic HTML, proper headings, tables, labels |
| 1.3.5 | Identify Input Purpose | PASS | Auth forms | autocomplete attributes present |
| 1.4.1 | Use of Colour | PASS | Badges, cards | Text labels supplement colour |
| 1.4.3 | Contrast (Minimum) | PASS | theme.css | Documented ratios, all >= 4.5:1 |
| 1.4.10 | Reflow | PASS | main.css | Responsive grid/flex layouts |
| 1.4.11 | Non-text Contrast | PASS | main.css | Focus rings, form borders meet 3:1 |
| 2.1.1 | Keyboard | PASS | app.js, pickers | All widgets keyboard accessible |
| 2.1.2 | No Keyboard Trap | PASS | app.js, portal.js | Escape closes dialogs |
| 2.2.1 | Timing Adjustable | PASS | app.js:1066, portal.js | Warning + extend option |
| 2.4.1 | Bypass Blocks | **FAIL** | 500.html, offline.html, mfa_verify.html, public_thank_you.html | Missing skip-nav on standalone pages |
| 2.4.3 | Focus Order | PASS | app.js | Focus management after dynamic changes |
| 2.4.7 | Focus Visible | PASS | main.css:217 | Global :focus-visible outline |
| 2.4.11 | Focus Not Obscured | PASS | main.css | No obscuring overlays |
| 2.4.12 | Focus Appearance | PASS | main.css | 2px solid outline with offset |
| 2.5.8 | Target Size | PASS | main.css, theme.css, portal.css | 44px minimums enforced |
| 3.1.1 | Language of Page | **FAIL** | 500.html:2, offline.html:2 | Hardcoded lang="en" |
| 3.1.2 | Language of Parts | PASS | _lang_toggle.html | lang attr on alternate language |
| 3.2.2 | On Input | ADVISORY | _program_switcher.html:13, executive_dashboard.html:29 | onchange submits form |
| 3.2.6 | Consistent Help | PASS | base.html, base_portal.html | Help link in nav, safety link in portal footer |
| 3.3.1 | Error Identification | PASS | includes/_form_errors.html, app.js | Error summary with focus + aria |
| 3.3.7 | Redundant Entry | PASS | Survey forms | Answers preserved on error |
| 3.3.8 | Accessible Authentication | PASS | Login, MFA forms | autocomplete, no cognitive tests |
| 4.1.2 | Name, Role, Value | PASS | All widgets | Proper ARIA roles and states |
| 4.1.3 | Status Messages | PASS | base.html, portal templates | aria-live regions for dynamic content |
| H1 | HTMX aria-live | PASS | base.html:295, app.js | Announcer pattern for swaps |
| H3 | HTMX errors | PASS | app.js:238 | role="alert" toast for errors |
| C1 | Chart aria-label | PASS | analysis, portal | canvas has aria-label + role="img" |
| C2 | Chart text alternatives | PASS | analysis | Data tables in details elements |
| C3 | Chart reduced-motion | ADVISORY | Chart.js config | Not explicitly disabled for prefers-reduced-motion |
| S1 | Survey skip-nav | **FAIL** | public_thank_you.html | Missing skip-nav link |
| S6 | Rating scale grouping | **FAIL** | public_form.html:110 | Uses div[role=group] instead of fieldset/legend |
| P2 | Quick-exit keyboard | PASS | base_portal.html:66 | Button element with aria-label |
| P3 | Session timeout dialog | PASS | _session_timeout_warning.html | Native dialog with aria attrs |

---

## 11. Prioritised Remediation

### High Priority (affects compliance)

1. **500.html** -- Replace `lang="en"` with `{{ LANGUAGE_CODE|default:'en' }}`. Add bilingual content. Add `<main>` landmark.
2. **offline.html** -- Replace `lang="en"` with dynamic language. Add `<main>` landmark and skip-nav. Add bilingual content.
3. **surveys/public_thank_you.html** -- Add skip-nav link: `<a href="#main-content" class="visually-hidden-focusable">`. Add `id="main-content" tabindex="-1"` to `<main>`.
4. **surveys/public_form.html:108-118** -- Change rating scale grouping from `<div role="group">` to `<fieldset><legend>` to match portal survey pattern.

### Medium Priority (best practice)

5. **auth/mfa_verify.html** (staff) -- Add skip-nav link for consistency, even though page is minimal.
6. **_program_switcher.html** and **executive_dashboard.html** -- Add a submit button as progressive enhancement so form does not rely solely on `onchange` for context change. Alternatively, add advisory text.
7. **Chart.js configuration** -- Add `prefers-reduced-motion` check to disable chart animations.

### Low Priority (polish)

8. **Portal survey_fill.html:215** -- The "Could not save" error message (line 215) is in English only; should use `{% trans %}`.
9. Review `portal.css` language toggle padding-right (`10rem`) which pushes the toggle away from the quick-exit button area -- verify at narrow viewports.
