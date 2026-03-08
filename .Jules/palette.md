## 2025-03-07 - Form Error Accessibility

**Learning:** While the global error linking script in `static/js/app.js` correctly added `aria-describedby` and `aria-invalid` to inputs based on `small.error` elements, it missed `small.badge-danger`. Throughout the app (70+ instances across forms, groups, programs, admin settings), `small.badge-danger` is heavily used for field-level errors, meaning screen reader users were not having these errors announced when navigating to the input.
**Action:** Always check the codebase for varied error class usage (`.error`, `.badge-danger`, `.form-error`, etc.) when implementing global accessibility enhancements for form validation.
