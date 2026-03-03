# SURVEY-LINK1 — Shareable Link Channel: Design & Implementation Plan

## Current State: Already Substantially Built

The shareable link channel is **already working** in production code. This document identifies **gaps** between the current implementation and the full design spec, then proposes targeted enhancements.

### What Already Works

| Feature | Status | Where |
|---|---|---|
| SurveyLink model (token, expiry, collect_name) | Done | `apps/surveys/models.py` (lines 364-402) |
| Public views (form + thank-you, no login) | Done | `apps/surveys/public_views.py` |
| URL routing at `/s/<token>/` | Done | `konote/urls.py` (lines 51-52) |
| Staff UI to create/manage links | Done | `templates/surveys/admin/survey_links.html` |
| All 6 question types rendered | Done | `templates/surveys/public_form.html` |
| Honeypot anti-spam | Done | Hidden `website` field in public form |
| Validation with error repopulation | Done | `public_views.py` (POST handler) |
| SurveyResponse with channel="link" | Done | `public_views.py` (line 100) |
| Bilingual page chrome (EN/FR toggle) | Done | Language toggle in template header |
| WCAG skip link | Done | Template line 16 |
| Optional name collection | Done | `link.collect_name` checkbox in admin |
| Token stored in response for tracing | Done | `response.token = link.token` |
| Expired/deactivated link handling (410 Gone) | Done | `public_views.py` (line 38-44) |

---

## Gap Analysis: Public Form vs. Portal Form

The portal survey form (`portal_survey_fill`) has several features that the public form currently lacks. These are the enhancements to implement.

### Gap 1: No Conditional Section Visibility (Priority: High)

**Problem:** The public form renders ALL active sections, ignoring `condition_question` and `condition_value` fields. If a survey has conditional sections (e.g., "Show Section C only if Q2 answer is 'Yes'"), public respondents see every section regardless.

**Portal implementation:** Uses `filter_visible_sections()` from `apps/portal/survey_helpers.py` to check each section's `condition_question_id` against current answers.

**Fix:**
- Import and call `filter_visible_sections()` in `public_views.py` during both GET (initial render) and POST (validation)
- On GET: render only unconditional sections (no answers yet, so conditionals are hidden)
- On POST: evaluate answers and show/hide conditional sections dynamically
- Add client-side JS to show/hide sections as the respondent answers trigger questions (progressive disclosure)
- On validation: only validate required fields in visible sections (matching portal behaviour)

**Complexity:** Medium — server-side logic exists, needs wiring + client-side enhancement

### Gap 2: No Multi-Page Support (Priority: Medium)

**Problem:** The public form renders all sections on a single scrolling page, ignoring `page_break` flags on sections. Long surveys (e.g., PHQ-9 with 4 sections) display as one long form.

**Portal implementation:** Uses `group_sections_into_pages()` to split sections into pages, with `?page=N` query parameter navigation and per-page validation.

**Approach options:**

**Option A — Server-side multi-page (match portal):** Requires storing in-progress answers between pages. The portal uses `PartialAnswer` tied to a `SurveyAssignment`, but public links have no assignment. Would need a new storage mechanism (session-based or a new model).

**Option B — Client-side multi-page (simpler):** Use JavaScript to show/hide page groups within a single `<form>`. All sections render in the HTML but only one page is visible at a time. "Next" button validates current page fields, "Previous" button navigates back. Final "Submit" sends everything in one POST. No server round-trips, no new models.

**Recommendation:** Option B (client-side). Simpler, no new models, works without JavaScript (falls back to single-page scroll), and avoids storing partial answers for anonymous respondents.

**Complexity:** Low-Medium — JS-only enhancement, form HTML already renders all sections

### Gap 3: No Bilingual Question/Option Text (Priority: High)

**Problem:** The public form template always displays `{{ question.question_text }}` and `{{ opt.label }}`, even when the respondent has toggled to French. The page chrome (title, buttons, error messages) is bilingual via `{% trans %}` tags, but the survey *content* is not.

**Portal implementation:** Likely has the same gap (needs verification), but the design doc specifies bilingual support for all text fields.

**Fix:**
- Create a template filter `bilingual` (or update existing `survey_tags.py`) that returns the FR variant when `LANGUAGE_CODE == "fr"` and the FR text is non-empty, falling back to EN
- Apply to: `question.question_text`, `section.title`, `section.instructions`, `opt.label`, `survey.name`, `survey.description`
- Pattern: `{{ question.question_text|bilingual:question.question_text_fr }}`

**Complexity:** Low — template filter + template updates only

### Gap 4: No Score Display on Thank-You Page (Priority: Low)

**Problem:** If `survey.show_scores_to_participant` is True, the portal thank-you page displays section scores. The public thank-you page never shows scores.

**Fix:**
- After creating the SurveyResponse, calculate section scores using `calculate_section_scores()`
- Store scores in session (keyed by token) and pass to thank-you template
- Or: recalculate from SurveyAnswer data on the thank-you page
- Display scores in a simple table matching the portal layout

**Complexity:** Low — helper function exists, just needs wiring

### Gap 5: No Copy-to-Clipboard in Staff UI (Priority: Low)

**Problem:** Staff have to manually select and copy the survey URL from a read-only text input. No "Copy" button.

**Fix:**
- Add a small "Copy" button next to each active link URL
- Use `navigator.clipboard.writeText()` with a fallback
- Show brief "Copied!" confirmation

**Complexity:** Low — 10 lines of inline JS

### Gap 6: No Response Count per Link (Priority: Low)

**Problem:** The links admin table doesn't show how many responses each link has generated. Staff can't tell which links are performing well.

**Fix:**
- Annotate the links queryset with `Count('survey__responses', filter=Q(survey__responses__token=F('token')))`
- Or: add a column that queries `SurveyResponse.objects.filter(token=link.token).count()`
- Display in the links table as a "Responses" column

**Complexity:** Low — one queryset annotation + one template column

### Gap 7: No Audit Trail for Public Submissions (Priority: Medium)

**Problem:** Portal submissions are logged to the audit database via `_audit_portal_event()`. Public link submissions are not audited.

**Fix:**
- After creating the SurveyResponse, log to audit DB:
  - Event: `public_survey_submitted`
  - Metadata: survey_id, link_token, response_id, is_anonymous
  - No PII (don't log respondent_name)
- Use the existing `AuditLog.objects.using("audit")` pattern

**Complexity:** Low — 5 lines of code

---

## Implementation Plan

### Phase 1 — Must-Have (feature parity with portal)

These close the functional gaps that would affect data quality or user experience:

| # | Task | Gap | Est. Lines |
|---|---|---|---|
| 1 | Add bilingual template filter for survey content | Gap 3 | ~15 (filter) + ~20 (template) |
| 2 | Add conditional section visibility (server-side) | Gap 1 | ~20 (view) |
| 3 | Add client-side conditional section show/hide | Gap 1 | ~30 (JS) |
| 4 | Validate only visible sections on POST | Gap 1 | ~10 (view) |
| 5 | Add audit trail for public submissions | Gap 7 | ~10 (view) |
| 6 | Add rate limiting (30/hour per IP on POST) | Anti-spam | ~2 (decorator) |

### Phase 2 — Nice-to-Have (UX polish)

These improve the staff and respondent experience but don't affect functionality:

| # | Task | Gap | Est. Lines |
|---|---|---|---|
| 7 | Client-side multi-page navigation | Gap 2 | ~60 (JS) + ~15 (template) |
| 8 | Score display on thank-you page | Gap 4 | ~20 (view) + ~15 (template) |
| 9 | Copy-to-clipboard button in staff UI | Gap 5 | ~10 (JS) + ~5 (template) |
| 10 | Response count column in links table | Gap 6 | ~5 (view) + ~5 (template) |

### Testing Plan

| Test | What it verifies |
|---|---|
| `test_public_survey_conditional_sections` | Hidden sections don't render; visible sections do |
| `test_public_survey_conditional_validation` | Required fields in hidden sections are not validated |
| `test_public_survey_bilingual_content` | FR question text shown when `?lang=fr` |
| `test_public_survey_multi_page_fallback` | Form works without JS (single-page scroll) |
| `test_public_survey_audit_trail` | Submission creates AuditLog entry in audit DB |
| `test_public_survey_rate_limit` | 30+ POSTs per hour from same IP are blocked |
| `test_public_survey_score_display` | Scores shown on thank-you when enabled |
| `test_public_survey_expired_link` | 410 response for expired/deactivated links |
| `test_public_survey_honeypot` | Bot submissions silently redirected, no data saved |

### Files to Modify

| File | Changes |
|---|---|
| `apps/surveys/public_views.py` | Conditional visibility, audit trail, score calculation |
| `apps/surveys/templatetags/survey_tags.py` | Add `bilingual` filter |
| `templates/surveys/public_form.html` | Bilingual content, conditional section attrs, multi-page JS |
| `templates/surveys/public_thank_you.html` | Score display |
| `templates/surveys/admin/survey_links.html` | Copy button, response count column |
| `apps/surveys/views.py` | Response count annotation in `survey_links` view |
| `tests/test_surveys.py` | New tests for all enhancements |

---

## Not In Scope

These are explicitly excluded from SURVEY-LINK1:

- **CAPTCHA** — honeypot + rate limiting (30/hr per IP) is sufficient. Add reCAPTCHA only if spam persists despite these measures.
- **Custom branding per link** — agencies use one brand. Not needed.
- **QR code generation** — can be done externally with the URL. Not a KoNote feature.
- **Email delivery of links** — depends on MSG-EMAIL-2WAY1 (future phase).
- **Link-to-client-file mapping** — shareable links are anonymous or name-only by design. Linking to client files is the portal channel's job.
- **Auto-save for public forms** — no PartialAnswer storage for anonymous respondents. Multi-page uses client-side state only.

---

## Decisions (Expert Panel Review — 2026-03-03)

Reviewed by: Web Accessibility Specialist, Privacy & Data Governance Analyst, Nonprofit Technology Consultant, Full-Stack Web Engineer.

| # | Question | Decision |
|---|---|---|
| 1 | Client-side vs. server-side multi-page | **Client-side (Option B).** No server-side paging. Progressive enhancement with JS, single-page scroll fallback without JS. |
| 2 | Conditional visibility without JS | **No-JS fallback shows all sections.** Server-side validation handles the rest. JS adds progressive disclosure. |
| 3 | Score display on public forms | **Yes, respect the existing `show_scores_to_participant` toggle.** Standard clinical practice for validated instruments. |
| 4 | Audit granularity — log IP? | **No.** PIPEDA 4.4 (Limiting Collection). Use infrastructure-layer rate limiting instead. |
| 5 | Multi-page ARIA patterns | **`role="group"` on page containers, `aria-live="polite"` status region for page count, focus to first heading on "Next".** Use `hidden` attribute (not `display:none`) for inactive pages. |
| 6 | Anonymous re-submission prevention | **Per-link option.** Add `single_response` boolean to SurveyLink (default False). Signed cookie after submission — soft control only. |
| 7 | `respondent_name_display` encryption | **Rename field label** to "First name or nickname (optional)", limit to 50 chars. No encryption needed — encryption breaks admin sorting. |
| 8 | Rate limiting | **Phase 1.** `@ratelimit(key="ip", rate="30/h", method="POST", block=True)` — django-ratelimit already installed and used in 4 other views. 30/hr threshold is community-friendly (shared devices at libraries/shelters). |

### Additional Recommendations from Panel

- Apply bilingual filter to **portal** survey templates too (same gap exists there)
- Add "Get Shareable Link" CTA on survey detail page (reduces 6-step flow to 2 clicks) — Phase 2
- Add progress indicator for surveys with 5+ questions (sticky top desktop, bottom mobile) — Phase 2
