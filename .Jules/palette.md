## 2024-03-08 - Added `.badge-danger` to form error linking logic
**Learning:** Django often renders form validation errors using custom classes (like `badge badge-danger`) instead of generic `.error` classes. The `linkErrorMessages()` function in `static/js/app.js` was missing these dynamic form errors, causing screen reader users to miss context when a form field failed validation. I updated the script to target both `.error` and `.badge-danger`.
**Action:** Always check the codebase for the actual class names used for error messages before assuming `.error` is sufficient for a11y linking scripts.

## 2025-03-10 - Add ARIA Labels to Copy Buttons
**Learning:** Many "Copy" buttons in the app use the `copy-btn` class but lack `aria-label`s. Screen readers might just read "Copy" out of context, which can be confusing (e.g., "Copy what?").
**Action:** Add descriptive `aria-label` attributes to these buttons (e.g., `aria-label="{% trans 'Copy calendar link' %}"`) to improve accessibility.

## 2024-05-24 - Screen Reader Compatibility for HTML Entities
**Learning:** Decorative HTML entities like `&larr;` (left arrow), `&rarr;` (right arrow), and `&times;` (multiply/close icon) are read aloud by screen readers, creating confusing navigation text like "leftwards arrow Back to sign in" instead of just "Back to sign in".
**Action:** Always wrap decorative HTML entities in a `<span aria-hidden="true">` to hide them from assistive technologies while keeping them visible on screen.

## 2025-03-11 - Add Empty State Styles to Portal
**Learning:** Many pages in the portal application render empty states inside `<article class="portal-empty-state">` blocks. However, the corresponding styling for `.portal-empty-state` was completely missing from `portal.css`, which left these states looking like unstyled text blocks and failing to guide users who have no content yet.
**Action:** When creating new layouts (like the portal application), ensure that foundational components like empty states are properly styled to avoid "broken" looking pages for new users.

## 2025-03-11 - Add Empty State Styles with A11y to Portal
**Learning:** Many pages in the portal application render empty states inside `<article class="portal-empty-state">` blocks. However, the corresponding styling for `.portal-empty-state` was completely missing from `portal.css`. Also, when using CSS pseudo-elements to add an emoji icon (like `content: "\1F4CB"`), screen readers will try to read it. Using the `/ ""` syntax (`content: "\1F4CB" / ""`) ensures it stays decorative and prevents it from being read aloud.
**Action:** When adding empty state CSS with emojis or icons using `::before`, always include `/ ""` to avoid screen readers announcing decorative visuals.

## 2025-03-27 - Add `.portal-field-error` to form error linking logic
**Learning:** The participant portal application uses its own specific CSS classes for form validation errors, specifically `.portal-field-error`. The global `linkErrorMessages()` script in `static/js/app.js` (which automatically manages `aria-describedby` and `aria-invalid` attributes) was not targeting this class. This resulted in a disjointed experience for screen reader users in the portal, as form errors were not properly linked to their corresponding input fields.
**Action:** When working on generic global utility scripts for accessibility (like linking form errors), ensure all variants of form error classes used across different sub-applications (like the portal) are included in the element selectors.