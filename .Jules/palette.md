## 2024-03-08 - Added `.badge-danger` to form error linking logic
**Learning:** Django often renders form validation errors using custom classes (like `badge badge-danger`) instead of generic `.error` classes. The `linkErrorMessages()` function in `static/js/app.js` was missing these dynamic form errors, causing screen reader users to miss context when a form field failed validation. I updated the script to target both `.error` and `.badge-danger`.
**Action:** Always check the codebase for the actual class names used for error messages before assuming `.error` is sufficient for a11y linking scripts.

## 2025-03-10 - Add ARIA Labels to Copy Buttons
**Learning:** Many "Copy" buttons in the app use the `copy-btn` class but lack `aria-label`s. Screen readers might just read "Copy" out of context, which can be confusing (e.g., "Copy what?").
**Action:** Add descriptive `aria-label` attributes to these buttons (e.g., `aria-label="{% trans 'Copy calendar link' %}"`) to improve accessibility.

## 2025-03-10 - Apply `aria-invalid` to forms with errors globally
**Learning:** We use `templates/includes/_form_field.html` a lot to render form fields. By injecting `aria-invalid="true"` alongside `aria-describedby` logic inside `apps/auth_app/templatetags/form_tags.py`, we can natively apply this accessibility standard to the entire project whenever there are validation errors, rather than explicitly hard-coding it into every individual form field template or relying on client-side JS.
**Action:** When updating template filters that process widget HTML (like `aria_describedby`), look for opportunities to apply related accessibility attributes directly (like `aria-invalid="true"`) to ensure broad, consistent coverage across the application.