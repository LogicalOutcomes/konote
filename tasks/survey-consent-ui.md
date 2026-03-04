# Survey Consent UI — Implementation Plan

**Status:** Parking Lot: Ready to Build
**ID:** SURV-CONSENT1
**Depends on:** Survey model already has `consent_text` and `consent_text_fr` fields (migration 0006)

## Context

The Survey model has `consent_text` and `consent_text_fr` TextFields added in PR #288, but no UI exists to set or display them. When an agency creates an anonymous survey that collects sensitive feedback, they need a consent gate so respondents understand how their data will be used before answering.

## Implementation Steps

### 1. Survey admin form — add consent text fields

**File:** `apps/surveys/forms.py`

Add `consent_text` and `consent_text_fr` to the SurveyForm's `Meta.fields` list. Use `Textarea` widget with 4 rows. Label: "Consent text (shown before the survey begins)".

### 2. Survey create/edit template — add consent textarea

**File:** `templates/surveys/admin/survey_form.html`

Add a collapsible section (or fieldset) for consent text. Include both EN and FR fields. Help text: "If provided, respondents must agree to this text before they can see the survey questions. Leave blank to skip the consent step."

### 3. Public survey view — consent gate

**File:** `apps/surveys/views.py` (public_survey_form view)

If `survey.consent_text` is non-empty:
1. On GET: render a consent page instead of the survey form
2. Consent page shows the consent text (FR if language is French), a checkbox "I have read and agree to the above", and a Continue button
3. On checkbox + Continue: set a session key `consent_given_{survey_link_pk}` = True, redirect to the actual survey form
4. Survey form view checks for the session key; if missing and consent_text exists, redirect back to consent page

### 4. SurveyResponse model — track consent

**File:** `apps/surveys/models.py`

Add `consent_given_at = DateTimeField(null=True, blank=True)` to SurveyResponse. Set it when the response is created and the survey had consent text. This provides an audit trail.

**Migration:** One new migration for the consent_given_at field.

### 5. French support

Use `survey.consent_text_fr` when `get_language() == "fr"` and the FR text is non-empty, otherwise fall back to `consent_text`.

### 6. Template for consent page

**File:** `templates/surveys/public_consent.html` (new)

Simple page: agency branding (if configured), consent text rendered as prose, checkbox + button. Styled with Pico CSS. Accessible: proper label for checkbox, focus management.

## Testing

- Unit test: survey with consent_text requires consent before form loads
- Unit test: survey without consent_text goes directly to form
- Unit test: consent_given_at is set on SurveyResponse when consent was required
- QA scenario: add to `konote-qa-scenarios/scenarios/portal/` if survey scenarios exist
