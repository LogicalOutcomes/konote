## 2024-03-08 - Added `.badge-danger` to form error linking logic
**Learning:** Django often renders form validation errors using custom classes (like `badge badge-danger`) instead of generic `.error` classes. The `linkErrorMessages()` function in `static/js/app.js` was missing these dynamic form errors, causing screen reader users to miss context when a form field failed validation. I updated the script to target both `.error` and `.badge-danger`.
**Action:** Always check the codebase for the actual class names used for error messages before assuming `.error` is sufficient for a11y linking scripts.

## 2025-03-10 - Add ARIA Labels to Copy Buttons
**Learning:** Many "Copy" buttons in the app use the `copy-btn` class but lack `aria-label`s. Screen readers might just read "Copy" out of context, which can be confusing (e.g., "Copy what?").
**Action:** Add descriptive `aria-label` attributes to these buttons (e.g., `aria-label="{% trans 'Copy calendar link' %}"`) to improve accessibility.

## 2025-03-10 - Add Contextual ARIA Labels to Print Buttons
**Learning:** "Print" buttons often lack context when read by screen readers. Adding an `aria-label` that includes the object being printed (e.g. `aria-label="{% trans 'Print report' %}"`) makes the action clearer, similar to expanding "Read more" to "Read more about [Subject]". Since the `aria-label` contains the visible text "Print", it complies with WCAG 2.1 SC 2.5.3 (Label in Name).
**Action:** Ensure action buttons like "Print", "Download", or "Edit" have descriptive `aria-label`s that provide context on what the action applies to, while still including the visible text.
