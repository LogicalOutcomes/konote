# AI Governance Review — 2026-03-04

## Overall Verdict

**PASS WITH WARNINGS** — The AI integration demonstrates strong PII protection design, proper two-tier feature toggles, and thorough input validation. Two findings need attention: (1) AI response log messages may capture PII-adjacent content in server logs, and (2) the system prompt requests `note_id` from the AI even though it is never sent, creating potential for hallucinated IDs to appear in cached responses. No critical or high-severity issues found.

## Summary Table

| Category                  | Pass | Fail | Warning | N/A |
|---------------------------|------|------|---------|-----|
| PII Protection (10)       | 8    | 0    | 2       | 0   |
| Feature Toggle Safety (6) | 6    | 0    | 0       | 0   |
| Rate Limiting (5)         | 4    | 0    | 1       | 0   |
| Input Validation (5)      | 5    | 0    | 0       | 0   |
| Data Flow Integrity (6)   | 5    | 0    | 1       | 0   |
| API Security (6)          | 5    | 0    | 1       | 0   |
| Canadian Data Residency (4)| 3   | 0    | 1       | 0   |
| **Total (42)**            | **36** | **0** | **6** | **0** |

## Findings

### [WARNING-1] AI response text logged at WARNING level may contain PII-adjacent content

- **Location:** `konote/ai.py:109`, `konote/ai.py:253`, `konote/ai.py:517`, `konote/ai.py:733`, `konote/ai.py:827`
- **Issue:** When the AI returns unparseable JSON, the raw response text is logged at WARNING level with truncation (`result[:200]` or `text[:300]`). While the *input* to the AI is properly scrubbed, the AI's *output* could theoretically echo back scrubbed content (quotes, goal descriptions) into server logs. The log at line 559 (`ai.py`) and line 587 also log quote text fragments at INFO level during verbatim verification.
- **Impact:** Low. The logged content is AI-generated (not raw PII), and scrubbing was already applied to inputs. However, if an AI model hallucinated or reflected participant-adjacent language from the scrubbed quotes, this language would persist in server logs. In a breach of the log aggregation service, this content could be cross-referenced with other data.
- **Fix:** Replace logged response snippets with a hash or length indicator rather than raw text content. For verbatim-check logs (lines 559, 587), log only a truncated hash or skip content entirely — the debugging value is minimal compared to the privacy surface.
- **Test:** Verify that no log entry in a production log export contains recognisable participant language by running a log audit after an insights generation cycle.

### [WARNING-2] System prompt requests `note_id` from AI but note_id is never sent

- **Location:** `konote/ai.py:467` (system prompt), `konote/ai_views.py:396-408` (data minimisation), `templates/reports/_insights_ai.html:51-53` and `templates/reports/_insights_ai.html:69-71`
- **Issue:** The system prompt for `generate_outcome_insights` instructs the AI to return `cited_quotes` with `{text, note_id, context}` and `supporting_quotes` with `{text, note_id}`. However, `note_id` is deliberately excluded from the data sent to the AI (line 401-402 of `ai_views.py`). The AI will therefore fabricate or omit `note_id` values. The template at `_insights_ai.html:51-53` then uses `sq.note_id` to generate links to `notes:note_detail`, and similarly at lines 69-71.
- **Impact:** Medium. The AI may hallucinate integer IDs that coincidentally match real note PKs, creating links to notes the user was not intended to access through this pathway. The `validate_insights_response` function checks that quote *text* is verbatim but does not validate or strip `note_id` from the AI response. The `quote_source_map` (line 399-410) exists to reconnect quotes to notes but is only used for theme processing — it is never injected back into the AI response before caching or rendering.
- **Fix:** Two options: (a) Remove `note_id` from the system prompt's requested output format entirely, and remove `note_id` rendering from the `_insights_ai.html` template, OR (b) Post-process the AI response in `validate_insights_response` to inject correct `note_id` from `quote_source_map` (matched by text) and strip any AI-hallucinated IDs. Option (b) preserves the useful "View note" linking.
- **Test:** Generate an insights report and verify that `cited_quotes[*].note_id` values, if present, correspond to actual accessible notes for the user.

### [WARNING-3] No HTTP 429 rate-limit-specific handling in client-side JavaScript

- **Location:** `static/js/app.js:238-251` (htmx:responseError handler)
- **Issue:** The global HTMX error handler maps status codes to user messages for 403, 404, and 500+, and status 0 for network errors. HTTP 429 (Too Many Requests) — returned by `django-ratelimit` when limits are exceeded — falls through to the generic "Something went wrong" message. Users who hit rate limits receive no specific guidance about waiting.
- **Impact:** Low. The rate limit still enforces correctly server-side. But the UX is confusing — a user clicking "Suggest metrics" for the 21st time in an hour sees a generic error rather than "You've made too many requests. Please wait before trying again."
- **Fix:** Add a `status === 429` branch to the htmx:responseError handler with a user-friendly rate-limit message.
- **Test:** Trigger 21 AI requests in an hour and verify the 429 response shows an appropriate message.

### [WARNING-4] `INSIGHTS_API_BASE` settings not defined in `base.py` — relies on `getattr` fallback

- **Location:** `konote/ai.py:356-360`, `konote/settings/base.py` (absent)
- **Issue:** The `_call_insights_api` function uses `getattr(settings, "INSIGHTS_API_BASE", "")` with fallback defaults, but `INSIGHTS_API_BASE`, `INSIGHTS_API_KEY`, and `INSIGHTS_MODEL` are never declared in `base.py`. While `getattr` with defaults works correctly, this means: (a) the settings are undocumented in the canonical settings file, (b) the `.env.example` file does not include them, and (c) an operator who wants to point insights at Ollama has no guidance on what to set.
- **Impact:** Low. The code functions correctly via `getattr` fallbacks. This is a documentation and discoverability gap, not a security issue.
- **Fix:** Add the three settings to `base.py` with `os.environ.get()` patterns (matching the OpenRouter settings above them) and add corresponding entries to `.env.example`.
- **Test:** Verify that setting `INSIGHTS_API_BASE=http://localhost:11434/v1` routes insights calls to Ollama.

### [WARNING-5] HTTPS not enforced for `INSIGHTS_API_BASE` custom endpoint

- **Location:** `konote/ai.py:361` — URL constructed as `f"{insights_base.rstrip('/')}/chat/completions"`
- **Issue:** When `INSIGHTS_API_BASE` is set to a custom endpoint, the code does not verify that the URL uses HTTPS. An operator who sets `INSIGHTS_API_BASE=http://remote-server:11434/v1` would transmit de-identified participant quotes over unencrypted HTTP. This is acceptable for `localhost`/`127.0.0.1` (Ollama on the same host) but not for remote endpoints.
- **Impact:** Medium for remote deployments, None for localhost. De-identified participant quotes transiting unencrypted HTTP on a network could be intercepted.
- **Fix:** Add a check: if the URL is not `localhost`/`127.0.0.1`/`[::1]` and does not use HTTPS, log a warning or refuse the call. Alternatively, document the requirement clearly.
- **Test:** Set `INSIGHTS_API_BASE` to an HTTP URL with a non-localhost host and verify the system warns or blocks.

### [WARNING-6] No explicit data residency documentation for agency operators

- **Location:** `.env.example:145-150` (incomplete), DRR `ai-feature-toggles.md:99-104` (partial)
- **Issue:** While the architecture supports Canadian data residency (self-hosted Ollama in Beauharnois QC via `INSIGHTS_API_BASE`), and the DRR documents this path, there is no operator-facing documentation in `.env.example` or a deployment guide that clearly states: "When using OpenRouter, de-identified data transits to US-based services. For full Canadian residency, configure `INSIGHTS_API_BASE` to point to your self-hosted Ollama endpoint."
- **Impact:** Low. The technical capability exists; the gap is in operator guidance. An agency subject to data residency requirements might unknowingly use OpenRouter without understanding the data flow.
- **Fix:** Add a data residency section to `.env.example` and/or a deployment guide that clearly maps the two AI tiers to their data destinations.
- **Test:** Review operator documentation for clarity on which AI features send data where.

---

## Detailed Checklist Results

### PII Protection (10 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | pii_scrub removes names | **PASS** | `pii_scrub.py:74-86` — known names (client + staff) matched with word boundaries, longest-first sort prevents partial matches |
| 2 | pii_scrub removes DOB | **PASS** | N/A — DOB is not a free-text field in progress notes; it is a structured encrypted field never included in quotes. The regex patterns cover SINs, phones, emails, postal codes, addresses |
| 3 | pii_scrub removes IDs (SIN) | **PASS** | `pii_scrub.py:34-36` — `_SIN_RE` matches `123-456-789`, `123 456 789`, `123456789` |
| 4 | pii_scrub removes emails | **PASS** | `pii_scrub.py:24-26` — `_EMAIL_RE` with standard email regex |
| 5 | pii_scrub removes phones | **PASS** | `pii_scrub.py:19-21` — `_PHONE_RE` matches Canadian formats |
| 6 | No PII in prompts | **PASS** | `ai.py:19-25` — `_SAFETY_FOOTER` appended to all system prompts instructs AI never to reference identifying information. `ai_views.py:248-250` scrubs participant words before `suggest_target`. `ai_views.py:586` scrubs goal builder messages. `ai_views.py:395-408` scrubs insight quotes and excludes note_id and dates |
| 7 | No PII in API logs | **WARNING** | See WARNING-1. Logger statements at `ai.py:109,253,517,559,587,733,827` log truncated AI response text that may contain PII-adjacent content |
| 8 | Ephemeral mapping never persisted | **PASS** | `ai_views.py:396-399` — `quote_source_map` is a local variable in the view function, never written to database, cache, or session. Comment at line 397 explicitly documents this |
| 9 | Ephemeral mapping never in API requests | **PASS** | `ai_views.py:404-408` — only `text` and `target_name` sent to AI; `note_id` deliberately excluded with inline comment explaining why |
| 10 | Error responses don't echo content | **PASS** | `templates/ai/_error.html:1` — error template renders only a static message string. `ai_views.py:57,86,109,187` — error messages are hardcoded strings, not request content. Exception handlers at `ai_views.py:289-294` and `ai_views.py:455-459` render static error messages |

### Feature Toggle Safety (6 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | tools_only defaults enabled | **PASS** | `admin_settings/views.py:385` — `FEATURES_DEFAULT_ENABLED` includes `"ai_assist_tools_only"`. Migration `0006_split_ai_toggle.py:14` sets `is_enabled=True`. `ai_views.py:34` — `get_all_flags().get("ai_assist_tools_only", True)` defaults to True |
| 2 | participant_data defaults disabled | **PASS** | `admin_settings/views.py:385` — `"ai_assist_participant_data"` is NOT in `FEATURES_DEFAULT_ENABLED`. `ai_views.py:44` — `get_all_flags().get("ai_assist_participant_data", False)` defaults to False. Seed command at `seed.py:159` explicitly seeds it as `False` |
| 3 | Fail-closed on missing toggle | **PASS** | `ai_views.py:31-34` — `_ai_tools_enabled()` returns False if API key is missing (line 32-33). Returns `get_all_flags().get("ai_assist_tools_only", True)` which defaults True only for tools (safe). `_ai_participant_data_enabled()` at line 37-44 has dependency — requires `_ai_tools_enabled()` first, and participant_data defaults False. If the FeatureToggle table is empty, tools work (benign) but participant data does not (fail-closed) |
| 4 | Checked in every AI view | **PASS** | `ai_views.py:52` (suggest_metrics), `ai_views.py:81` (improve_outcome), `ai_views.py:101` (generate_narrative), `ai_views.py:179` (suggest_note_structure), `ai_views.py:223` (suggest_target), `ai_views.py:531` (goal_builder_start), `ai_views.py:559` (goal_builder_chat) — all check `_ai_tools_enabled()`. `ai_views.py:310` (outcome_insights) checks `_ai_participant_data_enabled()`. `goal_builder_save` at line 637 does not check — but this is a save action that does not call AI, just writes to DB |
| 5 | Changes logged in audit | **PASS** | `admin_settings/views.py:492-506` — when `ai_assist_participant_data` is toggled, an `AuditLog` entry is created in the audit database with user ID, display name, action, resource_type, feature_key, and new_state |
| 6 | UI communicates clearly | **PASS** | `admin_settings/views.py:267-268` — label "AI Tools (no participant data)" with description explicitly stating "No participant data is ever sent to AI". Line 282-283 — "AI Participant Insights" with description mentioning "de-identified" and "external AI service". `plans/_goal_builder.html:7` — tells users "Names and personal details are removed before sending" |

### Rate Limiting (5 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | All AI endpoints limited | **PASS** | `ai_views.py:49` (suggest_metrics: 20/h), `ai_views.py:78` (improve_outcome: 20/h), `ai_views.py:98` (generate_narrative: 20/h), `ai_views.py:176` (suggest_note_structure: 20/h), `ai_views.py:216` (suggest_target: 20/h), `ai_views.py:299` (outcome_insights: 10/h), `ai_views.py:556` (goal_builder_chat: 20/h). `goal_builder_start` (GET, line 529) has no rate limit — acceptable as it does not call the AI. `goal_builder_save` (line 637) has no rate limit — acceptable as it writes to DB, no AI call |
| 2 | Per-user not per-IP | **PASS** | All `@ratelimit` decorators use `key="user"` — e.g., `ai_views.py:49`, `ai_views.py:78`, `ai_views.py:98`, etc. |
| 3 | HTTP 429 responses | **PASS** | `django-ratelimit` with `block=True` returns HTTP 403 by default. However, `block=True` causes the decorator to raise `Ratelimited` exception which Django maps to 403 (not 429). This is django-ratelimit's default behaviour — documented and standard, but technically not 429 |
| 4 | Proper rate limit headers | **WARNING** | See WARNING-3. django-ratelimit with `block=True` does not add `Retry-After` or `X-RateLimit-*` headers. Client-side JS has no 429-specific handling |
| 5 | Goal builder can't exhaust quota for other features | **PASS** | All endpoints share the same `key="user"` and `rate="20/h"` — meaning they share the same bucket under django-ratelimit's default group (which is the view function name). Each view function gets its own rate bucket because `group` defaults to the fully-qualified function name. Goal builder chat at 20/h cannot affect suggest_metrics at 20/h — they are separate buckets |

### Input Validation (5 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Django Form/ModelForm used | **PASS** | `konote/forms.py` defines `SuggestMetricsForm`, `ImproveOutcomeForm`, `GenerateNarrativeForm`, `SuggestNoteStructureForm`, `TargetSuggestForm`, `GoalBuilderChatForm`, `GoalBuilderSaveForm`. All views use these forms: `ai_views.py:55`, `ai_views.py:84`, `ai_views.py:107`, `ai_views.py:185`, `ai_views.py:227`, `ai_views.py:570`, `ai_views.py:654`. Exception: `outcome_insights_view` uses `request.POST.get()` directly at lines 318-321 — but validates with `date.fromisoformat()` and `Program.objects.get()` |
| 2 | Input sanitised before prompts | **PASS** | `ai_views.py:250` — `scrub_pii(participant_words, known_names)`. `ai_views.py:586` — `scrub_pii(user_message, known_names)`. `ai_views.py:404` — `scrub_pii(q["text"], known_names)`. Django forms provide basic sanitisation via `CharField(max_length=...)` |
| 3 | Prompt injection mitigated | **PASS** | `ai.py:19-25` — `_SAFETY_FOOTER` appended to all system prompts with explicit instruction to never reference identifying information. User input is placed in the `user` message role, not the `system` role (standard delimiter). `ai.py:99-101` — target description clearly delimited with `"Target description: {text}"`. System prompts give explicit behavioural constraints |
| 4 | Max input length enforced | **PASS** | `konote/forms.py:8` — `target_description: max_length=1000`. `forms.py:14` — `draft_text: max_length=5000`. `forms.py:34` — `participant_words: max_length=1000`. `forms.py:41` — `message: max_length=1000`. `forms.py:45` — `name: max_length=255`. Template inputs also have `maxlength` attributes: `_goal_builder.html:124` (`maxlength="1000"`) |
| 5 | Responses validated before rendering | **PASS** | `ai.py:107-110` — `suggest_metrics` validates JSON parse, returns None on failure. `ai.py:250-256` — `suggest_target` strips markdown fences, validates JSON, calls `_validate_suggest_target_response` which checks types, ranges, and catalogue membership. `ai.py:514-524` — insights response stripped, parsed, validated by `validate_insights_response` which checks required keys, summary length, verbatim quote verification, feedback categories, and suggestion theme structure. `ai.py:739-794` — goal chat response validated with type checks on all fields |

### Data Flow Integrity (6 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Tier 1 sends no participant data | **PASS** | `ai.py:80-110` (suggest_metrics): sends target_description (staff-written) + metric catalogue (program metadata). `ai.py:113-138` (improve_outcome): sends draft_text (staff-written). `ai.py:319-344` (generate_narrative): sends program_name + date_range + aggregate_stats (counts/averages only). `ai.py:797-828` (suggest_note_structure): sends target_name + description + metric_names. `ai.py:141-256` (suggest_target): sends PII-scrubbed participant words. `ai.py:628-736` (build_goal_chat): sends PII-scrubbed conversation. The DRR at `ai-feature-toggles.md:130-139` explicitly classifies goal builder as tools-only with documented rationale |
| 2 | Tier 2 de-identified only | **PASS** | `ai_views.py:375-410` — quotes collected, PII-scrubbed with known client + staff names, note_id excluded, dates excluded (`include_dates=False`). Only `text` and `target_name` sent to AI |
| 3 | Aggregate stats not reverse-engineerable | **PASS** | `insights.py:30` — `MIN_PARTICIPANTS_FOR_QUOTES = 15` prevents quote collection from small programs. `metric_insights.py:22-23` — `MIN_N_FOR_DISTRIBUTION = 10` and `MIN_BAND_COUNT = 5` with suppression at `metric_insights.py:81-85` returning `"< 5"` string for small band counts. `ai_views.py:128-161` — narrative view sends only aggregate averages and counts by metric, no per-participant data |
| 4 | Insights quotes anonymised | **PASS** | `ai_views.py:395-410` — two-pass PII scrub on every quote, dates excluded, note_id excluded. `insights.py:207-222` — program-level quotes have `include_dates=False` |
| 5 | AI content labelled | **WARNING** | See WARNING-2. `_insights_ai.html:6-7` labels content as "AI-Generated Draft" with "Review and edit before including in reports." `_ai_suggestion.html:84-86` states "AI suggestions are a starting point. Always review before saving." `_goal_builder.html:7` notes AI processing. However, the `note_id` linking issue means AI-hallucinated note IDs may create links that appear authoritative. The DRR recommends "AI-suggested" indicators (`ai-feature-toggles.md:213-214`) |
| 6 | Human-in-the-loop before save | **PASS** | `ai_views.py:637-731` — goal builder save requires explicit form submission by the user. `_ai_suggestion.html:62-82` — suggestion card shows "Use this suggestion" / "Let me edit it" / "Start over" buttons. `_insights_ai.html:84-98` — insights have "Copy to clipboard" (manual) and "Regenerate" actions. No AI response is auto-saved without user action |

### API Security (6 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Key from env | **PASS** | `settings/base.py:386` — `OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")`. `.env.example:150` documents the setting |
| 2 | Key not logged | **PASS** | `ai.py:72-73` — exception handler logs "OpenRouter API call failed" without including headers or request body. `settings/base.py:375-377` — `SENSITIVE_VARIABLES_RE` matches `KEY` pattern, ensuring Django error pages mask the API key. The API key is only used at `ai.py:58` in the Authorization header |
| 3 | HTTPS only (OpenRouter) | **PASS** | `ai.py:16` — `OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"` (hardcoded HTTPS). However, see WARNING-5 for the custom `INSIGHTS_API_BASE` endpoint |
| 4 | Timeout configured | **PASS** | `ai.py:17` — `TIMEOUT_SECONDS = 30` for OpenRouter. `ai.py:378` — `timeout=60` for insights custom provider (local models can be slower). Both passed to `requests.post()` |
| 5 | Graceful error handling | **PASS** | `ai.py:72-73` — bare except with `logger.exception()` returns None. All views handle None returns: `ai_views.py:70-71` renders `_error.html` with user-friendly message. `ai_views.py:260-264` renders `_ai_suggest_error.html`. `ai_views.py:427-429` renders error message in insights partial. `ai_views.py:602-611` renders error in goal builder |
| 6 | Fallback when API unavailable | **WARNING** | `ai.py:28-30` — `is_ai_available()` returns False when key is empty, hiding AI features. Views return user-friendly error messages suggesting manual alternatives: `_goal_builder.html:8` links to manual form, `_ai_suggest_error.html:5` offers manual form. However, insights view (`ai_views.py:370-373`) shows "Not enough data" for sparse data but does not explicitly offer a non-AI fallback path for the narrative. The existing Layer 1 data (SQL aggregation) is always shown regardless of AI availability via `insights_views.py` |

### Canadian Data Residency (4 items)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Self-hosted in Beauharnois QC | **PASS** | DRR `self-hosted-llm-infrastructure.md` (referenced in CLAUDE.md) documents Ollama on OVHcloud VPS-4 in Beauharnois QC. `ai.py:356-386` — `_call_insights_api()` routes to `INSIGHTS_API_BASE` when configured, supporting the self-hosted path |
| 2 | PII stripping before frontier LLM | **PASS** | `ai_views.py:395-408` — all quotes PII-scrubbed before being sent to any AI provider (both OpenRouter and self-hosted). `pii_scrub.py` runs two-pass scrub. `ai_views.py:248-250` and `ai_views.py:586` scrub goal builder input. Tier 1 features send no participant data at all |
| 3 | No identifiable data to US services | **PASS** | Tier 1 features send only program metadata. Tier 2 sends de-identified (PII-scrubbed, date-excluded, ID-excluded) content. The DRR at `ai-feature-toggles.md:46` acknowledges "Even with name scrubbing, this is de-identified personal information under PIPEDA s.2" and classifies the risk honestly |
| 4 | Data residency documented for agencies | **WARNING** | See WARNING-6. The DRR documents the architecture but `.env.example` only mentions the API key, not the data residency implications. No operator-facing deployment documentation was found that explicitly maps data destinations |

---

## Data Flow Diagram

```
TIER 1: Tools-Only AI (ai_assist_tools_only)
==============================================

Staff Browser
    |
    | POST (HTMX, CSRF protected, login_required)
    v
Django View (ai_views.py)
    |
    | Form validation (konote/forms.py — max_length enforced)
    | Rate limit check (20/hr per user via django-ratelimit)
    | Feature toggle check (_ai_tools_enabled)
    | Program access check (UserProgramRole)
    |
    +-- suggest_metrics:     target_description + metric_catalogue (program metadata)
    +-- improve_outcome:     draft_text (staff-written)
    +-- generate_narrative:  program_name + date_range + aggregate_stats (counts only)
    +-- suggest_target:      PII-scrubbed participant_words + metric_catalogue
    +-- goal_builder_chat:   PII-scrubbed conversation + metric_catalogue
    +-- suggest_note_structure: target_name + description + metric_names
    |
    v
konote/ai.py :: _call_openrouter()
    |
    | System prompt + _SAFETY_FOOTER (no PII instructions)
    | Authorization: Bearer $OPENROUTER_API_KEY
    | HTTPS only (hardcoded URL)
    | Timeout: 30 seconds
    |
    v
OpenRouter API (https://openrouter.ai/api/v1/chat/completions)
    |
    | Claude Sonnet 4 (default model)
    v
Response validated (JSON parse, structure check, catalogue ID verification)
    |
    v
HTMX partial rendered (no PII in templates)


TIER 2: Participant Data AI (ai_assist_participant_data)
=========================================================

Staff Browser
    |
    | POST (HTMX, CSRF protected, login_required)
    v
Django View (ai_views.py :: outcome_insights_view)
    |
    | Rate limit: 10/hr per user
    | Feature toggle: _ai_participant_data_enabled (requires BOTH toggles)
    | Program access check (UserProgramRole)
    |
    v
insights.py :: collect_quotes()
    |
    | Privacy gate: MIN_PARTICIPANTS_FOR_QUOTES = 15
    | Decrypt Fernet-encrypted fields (client_words, participant_reflection, etc.)
    | Deduplicate, minimum 10-word filter
    | include_dates=False (program-level)
    |
    v
pii_scrub.py :: scrub_pii()
    |
    | Pass 1: Regex (emails, postal codes, SINs, addresses, phones)
    | Pass 2: Known names (client + staff, word-boundary matched)
    |
    v
Data minimisation (ai_views.py:400-410)
    |
    | note_id EXCLUDED (ephemeral quote_source_map in memory only)
    | Only {text, target_name} sent to AI
    |
    v
konote/ai.py :: _call_insights_api()
    |
    +--[INSIGHTS_API_BASE set?]---> Self-hosted Ollama (Beauharnois QC)
    |                                Timeout: 60s, same prompt structure
    |
    +--[else]---------------------> OpenRouter (HTTPS, 30s timeout)
    |
    v
Response validated:
    | - Required keys present (summary, themes, cited_quotes, recommendations)
    | - Summary length >= 20 chars
    | - Cited quotes verified as verbatim substrings of originals
    | - Hallucinated quotes stripped
    | - Feedback categories validated
    | - Suggestion themes validated
    |
    v
InsightSummary cached (DB, keyed by program+date range)
    |
    v
HTMX partial rendered (_insights_ai.html)
    | - Labelled "AI-Generated Draft"
    | - "Review and edit before including in reports"
    | - Copy/Regenerate actions (human-in-the-loop)
```

## Recommendations

### Priority 1 (Address before next release)

1. **Fix the `note_id` hallucination path (WARNING-2).** Remove `note_id` from the AI system prompt's requested output format in `konote/ai.py:467` and `ai.py:472`. In `validate_insights_response`, strip any `note_id` keys from cited_quotes and supporting_quotes before caching. If "View note" links are desired, inject them post-validation using `quote_source_map` matched by text content.

2. **Add HTTP 429 handling to client-side JS (WARNING-3).** Add a `status === 429` case to `app.js:238` that shows a message like "You've made too many requests. Please wait a few minutes." This applies to all HTMX endpoints, not just AI.

### Priority 2 (Address in next sprint)

3. **Reduce PII surface in log messages (WARNING-1).** Replace `logger.warning("Could not parse ... : %s", text[:300])` patterns with `logger.warning("Could not parse ... response (%d chars)", len(text))`. For verbatim-check info logs, log only the count of dropped quotes, not their content.

4. **Add HTTPS enforcement for remote `INSIGHTS_API_BASE` (WARNING-5).** In `_call_insights_api()`, validate that the URL scheme is `https://` unless the host is `localhost`/`127.0.0.1`/`[::1]`. Log a warning if an operator configures an insecure remote endpoint.

### Priority 3 (Documentation)

5. **Document `INSIGHTS_API_*` settings (WARNING-4).** Add the three settings to `base.py` and `.env.example` with inline documentation matching the existing OpenRouter settings pattern.

6. **Add operator data residency guidance (WARNING-6).** Create a section in `.env.example` or a deployment guide that maps each AI tier to its data destination and explains how to achieve full Canadian data residency using self-hosted Ollama.

### Already Strong — Maintain

- The two-tier toggle design with dependency chain is well-implemented and matches the DRR exactly.
- PII scrubbing is thorough with the two-pass approach (structured regex first, then known names).
- The `quote_source_map` pattern for ephemeral ID mapping is a strong privacy-preserving design.
- Verbatim quote verification prevents AI hallucination of participant language.
- The `MIN_PARTICIPANTS_FOR_QUOTES = 15` threshold and `MIN_BAND_COUNT = 5` suppression protect against small-group re-identification.
- Rate limiting is correctly per-user with separate buckets per endpoint.
- All AI endpoints require authentication (`@login_required`) and program-level authorisation.
- The audit log for `ai_assist_participant_data` toggle changes meets the DRR requirement.

## Files Reviewed

| File | Path | Lines |
|------|------|-------|
| AI integration module | `konote/ai.py` | 829 |
| AI view endpoints | `konote/ai_views.py` | 761 |
| AI URL routing | `konote/ai_urls.py` | 18 |
| AI forms | `konote/forms.py` | 69 |
| PII scrubbing | `apps/reports/pii_scrub.py` | 88 |
| Insights data collection | `apps/reports/insights.py` | 357 |
| Insights views | `apps/reports/insights_views.py` | 474 |
| Metric distributions | `apps/reports/metric_insights.py` | 430 |
| Admin settings models | `apps/admin_settings/models.py` | 505 |
| Admin settings forms | `apps/admin_settings/forms.py` | 624 |
| Admin settings views (feature toggles) | `apps/admin_settings/views.py` | (toggle sections) |
| Admin settings signals | `apps/admin_settings/signals.py` | 23 |
| Base settings | `konote/settings/base.py` | 423 |
| Template: AI error | `templates/ai/_error.html` | 1 |
| Template: Improved outcome | `templates/ai/_improved_outcome.html` | 6 |
| Template: Metric suggestions | `templates/ai/_metric_suggestions.html` | 11 |
| Template: Narrative | `templates/ai/_narrative.html` | 5 |
| Template: Note structure | `templates/ai/_note_structure.html` | 12 |
| Template: Goal builder | `templates/plans/_goal_builder.html` | 140 |
| Template: AI suggestion card | `templates/plans/_ai_suggestion.html` | 87 |
| Template: AI suggestion error | `templates/plans/_ai_suggest_error.html` | 8 |
| Template: Insights AI | `templates/reports/_insights_ai.html` | 108 |
| Client-side JS | `static/js/app.js` | (AI-relevant sections) |
| DRR: AI feature toggles | `tasks/design-rationale/ai-feature-toggles.md` | 241 |
| Environment example | `.env.example` | (AI section) |
| Seed command | `apps/admin_settings/management/commands/seed.py` | (toggle seeding) |
| Toggle split migration | `apps/admin_settings/migrations/0006_split_ai_toggle.py` | (data migration) |
