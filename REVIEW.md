# Code Review Rules for KoNote

## Privacy & Consent

- Any view that queries `ProgressNote` and displays note content to staff **must** apply PHIPA consent filtering. List views: `apply_consent_filter()`. Single-note views: `check_note_consent_or_403()`. See `tasks/design-rationale/phipa-consent-enforcement.md`.
- PII fields use encrypted property accessors (`client.first_name`, not `_first_name_encrypted`). Never query encrypted fields in SQL — filter in Python.
- Audit log writes must use the audit database: `AuditLog.objects.using("audit")`.

## Forms & Validation

- Always use Django `ModelForm` in `forms.py` for validation. Never use raw `request.POST.get()` directly in views.

## Templates & Frontend

- Use `{{ term.client }}` for terminology — never hardcode "client", "participant", etc.
- Use `{{ features.programs }}` for feature toggles.
- No React, Vue, webpack, or npm. Server-rendered Django templates + HTMX + Pico CSS only.
- HTMX responses must have global `htmx:responseError` handling so errors don't fail silently.
- Checkboxes must be **inside** the `<label>` tag (Pico CSS requirement). Use `{% include "includes/_form_field.html" %}` in form loops.

## Accessibility

- WCAG 2.2 AA: semantic HTML, colour contrast, alt text, keyboard navigation.

## Translations

- New or modified templates with user-visible text must use `{% trans %}` or `{% blocktrans %}` tags.
- Check that corresponding French translations exist in `locale/fr/LC_MESSAGES/django.po`.

## Spelling

- Canadian English: colour, centre, behaviour, organisation, but **-ize** not -ise (organize, optimize, analyze). Use "program" not "programme" in English.

## Design Rationale

- Before approving changes to features covered by a Design Rationale Record (`tasks/design-rationale/`), check that the PR does not re-introduce a rejected anti-pattern.

## Testing & QA

- New or changed views should have corresponding tests (permissions, form validation, happy path).
- New URL routes should have a matching entry in `konote-qa-scenarios/pages/page-inventory.yaml`.
- Migrations must be included when models change.

## Admin Routes

- All `/admin/*` routes are admin-only, enforced by RBAC middleware. New admin routes must follow this pattern.
