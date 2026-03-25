## 2024-03-08 - Added `.badge-danger` to form error linking logic
**Learning:** Django often renders form validation errors using custom classes (like `badge badge-danger`) instead of generic `.error` classes. The `linkErrorMessages()` function in `static/js/app.js` was missing these dynamic form errors, causing screen reader users to miss context when a form field failed validation. I updated the script to target both `.error` and `.badge-danger`.
**Action:** Always check the codebase for the actual class names used for error messages before assuming `.error` is sufficient for a11y linking scripts.

## 2025-03-10 - Add ARIA Labels to Copy Buttons
**Learning:** Many "Copy" buttons in the app use the `copy-btn` class but lack `aria-label`s. Screen readers might just read "Copy" out of context, which can be confusing (e.g., "Copy what?").
**Action:** Add descriptive `aria-label` attributes to these buttons (e.g., `aria-label="{% trans 'Copy calendar link' %}"`) to improve accessibility.

## 2025-03-10 - Add Contextual ARIA Labels to Action Buttons in Lists
**Learning:** Action buttons like "Approve" and "Dismiss" in dynamically generated lists (like survey assignments) lack context for screen readers when they don't explicitly reference the target item. A user tabbing through the page would hear "Approve, button", "Dismiss, button", etc., multiple times without knowing *what* is being approved.
**Action:** Always add descriptive `aria-label` attributes to generic action buttons inside iterative loops, using `{% blocktrans %}` to include the item's name dynamically (e.g., `aria-label="{% blocktrans with name=a.survey.name %}Approve {{ name }}{% endblocktrans %}"`).