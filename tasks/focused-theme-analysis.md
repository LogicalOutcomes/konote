# Focused Theme Analysis — Task Prompt

Task ID: AI-FOCUSED-THEME1
Date: 2026-03-05
Status: Ready to build
Related: [Self-hosted LLM DRR](design-rationale/self-hosted-llm-infrastructure.md), [AI feature toggles DRR](design-rationale/ai-feature-toggles.md)

---

## Context

KoNote's suggestion theme system currently works **bottom-up only**: the AI looks at all participant suggestions and decides what themes emerge. Program managers have no way to ask a **top-down question** like "Are there any themes relating to opening hours?" or "What are participants saying about transportation?"

This feature adds a **focused analysis** mode where managers type a question and the AI searches existing suggestions for relevant patterns.

## What to Build

### 1. Focused Analysis UI

Add a "Ask a Question" input to the **Suggestion Themes list page** (not the Insights page — this is a themes feature, not a reporting feature).

**UI elements:**
- Text input with placeholder: "e.g., Are there any themes about scheduling or opening hours?"
- "Analyse" button
- Results appear below in an HTMX partial

**Where it lives:** `templates/notes/suggestions/theme_list.html` — add a section above the theme list, gated on `features.ai_assist_participant_data`.

### 2. Backend: Focused Analysis View

New HTMX endpoint in `apps/notes/suggestion_views.py`:

```
POST /suggestions/themes/focused-analysis/
```

**Flow:**
1. Validate the question (non-empty, max 500 chars)
2. Check `features.ai_assist_participant_data` is enabled
3. Check privacy gate — use `MIN_PARTICIPANTS_FOR_THEME_PROCESSING` (5, not 15)
4. Collect suggestions for the program using the same `collect_quotes()` pipeline, same PII scrubbing
5. Build a focused prompt including the manager's question and the scrubbed suggestions
6. Call `_call_insights_api()` (routes to self-hosted Ollama via `INSIGHTS_API_BASE`)
7. Parse and validate the AI response
8. Return an HTMX partial with the results

### 3. AI Prompt Design

The prompt should instruct the model to:
- Search the provided suggestions for content relevant to the manager's question
- Group relevant suggestions into sub-themes if there are distinct patterns
- Provide a summary paragraph describing what participants are saying about this topic
- Report how many suggestions (out of total) are relevant
- If nothing relevant is found, say so clearly

**Important:** The prompt should NOT return verbatim quotes. It should return:
- A synthesised summary (always)
- Sub-theme names with counts (if multiple patterns found)
- A relevance count ("7 of 23 suggestions relate to this topic")

This avoids the verbatim display issue for small programs entirely — the focused analysis always returns synthesised content.

### 4. Response Format

```json
{
  "relevant_count": 7,
  "total_count": 23,
  "summary": "Several participants expressed frustration with current opening hours...",
  "sub_themes": [
    {
      "name": "Evening Hours",
      "description": "Participants who work during the day want evening sessions...",
      "count": 4
    },
    {
      "name": "Weekend Access",
      "description": "Two participants specifically mentioned needing weekend availability...",
      "count": 3
    }
  ],
  "suggestion": "Consider creating a theme for 'Schedule Flexibility' to track this ongoing pattern."
}
```

### 5. "Create Theme from This" Action

If the analysis finds something meaningful, show a button: **"Create Theme from This"**

Clicking it:
- Pre-fills the theme creation form with the AI-suggested theme name and description
- Sets `source="ai_generated"`
- After creation, runs the Tier 1 auto-link to connect matching suggestions to the new theme

This connects the exploratory analysis back to the persistent theme tracking system.

### 6. Results Are Ephemeral

Focused analysis results are **not saved**. They're a one-time exploration tool. If the manager wants to track an emerging pattern, they use "Create Theme from This" to make it persistent.

No caching, no history, no database table for analysis results.

### 7. Privacy Gates

Same graduated model as the main theme system:

| Participant Count | Focused Analysis Available? | Results Show |
|---|---|---|
| < 5 | No | — |
| 5–14 | Yes (self-hosted only) | Synthesised summary + counts only (no verbatim quotes) |
| 15+ | Yes | Synthesised summary + counts (same — focused analysis never shows verbatim quotes) |

**Note:** Focused analysis ALWAYS returns synthesised content, never verbatim quotes, regardless of program size. This is by design — the value is in pattern identification, not quote retrieval.

### 8. Rate Limiting

Use the existing rate limit (10 requests/hour per user for insights). Focused analysis counts against the same limit.

### 9. Audit Logging

Log each focused analysis to the audit database:
- Who ran it
- Which program
- The question asked (but NOT the suggestions or results — those are ephemeral)
- Participant count at time of analysis
- Timestamp

## Privacy Gate Update (Do This First)

**This task also includes the graduated privacy threshold change decided in the expert panel review (2026-03-05).**

### Update `apps/reports/insights.py`:

Add a new constant:
```python
MIN_PARTICIPANTS_FOR_THEME_PROCESSING = 5   # AI can analyze (self-hosted only)
MIN_PARTICIPANTS_FOR_QUOTES = 15            # Verbatim quotes shown in UI (unchanged)
```

### Update `apps/notes/theme_engine.py`:

`_check_privacy_gate()` should use `MIN_PARTICIPANTS_FOR_THEME_PROCESSING` (5) instead of `MIN_PARTICIPANTS_FOR_QUOTES` (15), **but only when the insights endpoint is self-hosted** (`INSIGHTS_API_BASE` is configured). If `INSIGHTS_API_BASE` is not set (agency is using OpenRouter), the threshold remains 15.

```python
def _check_privacy_gate(program):
    if getattr(settings, "DEMO_MODE", False):
        return True

    from apps.reports.insights import (
        MIN_PARTICIPANTS_FOR_QUOTES,
        MIN_PARTICIPANTS_FOR_THEME_PROCESSING,
    )

    # Use lower threshold only when self-hosted LLM is configured
    is_self_hosted = bool(getattr(settings, "INSIGHTS_API_BASE", ""))
    threshold = (
        MIN_PARTICIPANTS_FOR_THEME_PROCESSING if is_self_hosted
        else MIN_PARTICIPANTS_FOR_QUOTES
    )

    participant_count = ...  # existing query
    return participant_count >= threshold
```

### Update theme detail template (`_linked_list.html`):

For programs with 5–14 participants:
- Show theme name, description, status, priority (AI-synthesised, not attributable)
- Show linked suggestion **count** only
- Suppress verbatim suggestion text — replace with "Content not shown for small programs"
- Suppress link dates

### Update the self-hosted LLM DRR:

Add a section documenting that the N=5 threshold **only applies when `INSIGHTS_API_BASE` is configured** (self-hosted). If an agency is still routing through OpenRouter, the N=15 threshold applies. This must also be noted in the deployment instructions (ops repo).

### Update the AI feature toggles DRR:

Add a note to the "minimum sample size" section explaining the graduated model:
- N < 5: no AI theme processing
- N 5–14: AI theme processing (self-hosted only), verbatim quotes suppressed
- N 15+: full display

## Files to Create or Modify

| File | Action |
|---|---|
| `apps/reports/insights.py` | Add `MIN_PARTICIPANTS_FOR_THEME_PROCESSING = 5` |
| `apps/notes/theme_engine.py` | Update `_check_privacy_gate()` to use graduated threshold |
| `apps/notes/suggestion_views.py` | Add `focused_analysis_view()` |
| `apps/notes/urls.py` | Add URL for focused analysis |
| `templates/notes/suggestions/theme_list.html` | Add "Ask a Question" input |
| `templates/notes/suggestions/_focused_results.html` | New partial for results |
| `templates/notes/suggestions/_linked_list.html` | Suppress verbatim text for 5–14 |
| `konote/ai.py` | Add `generate_focused_analysis()` prompt |
| `tests/test_suggestions.py` | Tests for focused analysis + graduated privacy gate |
| `tasks/design-rationale/self-hosted-llm-infrastructure.md` | Document N=5 self-hosted-only rule |
| `tasks/design-rationale/ai-feature-toggles.md` | Document graduated threshold model |
| `locale/fr/LC_MESSAGES/django.po` | French translations for new strings |

## Testing

- Test focused analysis with mock AI response (don't need real LLM for unit tests)
- Test privacy gate at N=4, N=5, N=14, N=15 with and without `INSIGHTS_API_BASE`
- Test that verbatim quotes are suppressed in theme detail for 5–14 programs
- Test rate limiting applies
- Test audit log entry is created
- Test "Create Theme from This" pre-fills the form correctly

## Not in Scope

- Saving analysis history (keep it ephemeral)
- Multi-program analysis (one program at a time)
- Comparing analysis results across time periods
- Auto-generating themes without manager confirmation
