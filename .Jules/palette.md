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

## 2025-02-28 - Missing ARIA labels on progress elements
**Learning:** Found that `<progress>` elements used for CIDS coverage tracking in report and program templates were missing `aria-label` attributes. Without these labels, screen reader users would only hear the value and max limits without knowing what the progress bar represents.
**Action:** Added `aria-label` attributes to `<progress>` elements in `templates/reports/cids_coverage_dashboard.html`, `templates/reports/cids_export_status.html`, and `templates/programs/evaluation/framework_detail.html` to clearly describe the tracked metric, ensuring compliance with accessibility standards (WCAG 4.1.2 Name, Role, Value).
