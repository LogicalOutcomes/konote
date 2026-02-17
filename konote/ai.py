"""
OpenRouter AI integration — PII-free helper functions.

These functions only receive metadata (metric definitions, target descriptions,
program names, aggregate stats). Client PII never reaches this module.
"""
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_SECONDS = 30

# Shared safety instruction appended to all system prompts
_SAFETY_FOOTER = (
    "\n\nIMPORTANT: You are a nonprofit outcome-tracking assistant. "
    "Never ask for, guess, or reference any client identifying information "
    "(names, dates of birth, addresses, or record IDs). "
    "Work only with the program context and metrics provided."
)


def is_ai_available():
    """Return True if the OpenRouter API key is configured."""
    return bool(getattr(settings, "OPENROUTER_API_KEY", ""))


def _call_openrouter(system_prompt, user_message=None, max_tokens=1024, messages=None):
    """
    Low-level POST to OpenRouter.  Returns the response text, or None on
    any failure (network, auth, timeout, malformed response).

    For single-turn calls, pass user_message (string).
    For multi-turn calls, pass messages (list of {"role": ..., "content": ...}).
    """
    if not is_ai_available():
        return None

    if messages is not None:
        api_messages = [
            {"role": "system", "content": system_prompt + _SAFETY_FOOTER},
        ] + messages
    else:
        api_messages = [
            {"role": "system", "content": system_prompt + _SAFETY_FOOTER},
            {"role": "user", "content": user_message},
        ]

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", ""),
                "X-Title": "KoNote",
            },
            json={
                "model": getattr(settings, "OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514"),
                "messages": api_messages,
                "max_tokens": max_tokens,
            },
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("OpenRouter API call failed")
        return None


# ── Public functions ────────────────────────────────────────────────


def suggest_metrics(target_description, metric_catalogue):
    """
    Given a plan target description and the full metric catalogue,
    return a ranked list of suggested metrics.

    Args:
        target_description: str — the staff-written target/goal text
        metric_catalogue: list of dicts with keys id, name, definition, category

    Returns:
        list of dicts {metric_id, name, reason} or None on failure
    """
    system = (
        "You help nonprofit workers choose outcome metrics for client plan targets. "
        "You will receive a target description and a catalogue of available metrics. "
        "Return a JSON array of the 3–5 most relevant metrics, ranked by relevance. "
        "Each item: {\"metric_id\": <int>, \"name\": \"<name>\", \"reason\": \"<1 sentence>\"}. "
        "Return ONLY the JSON array, no other text."
    )
    user_msg = (
        f"Target description: {target_description}\n\n"
        f"Available metrics:\n{json.dumps(metric_catalogue, indent=2)}"
    )
    result = _call_openrouter(system, user_msg)
    if result is None:
        return None
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not parse metric suggestions: %s", result[:200])
        return None


def improve_outcome(draft_text):
    """
    Improve a rough outcome statement into a clear, measurable one.

    Args:
        draft_text: str — the staff-written draft outcome

    Returns:
        str — improved outcome text, or None on failure
    """
    system = (
        "You help nonprofit workers write clear, measurable outcome statements "
        "using the SMART framework (Specific, Measurable, Achievable, Relevant, "
        "Time-bound). Rewrite the draft into a professional outcome statement. "
        "Return only the improved text, no explanation."
    )
    return _call_openrouter(system, f"Draft outcome: {draft_text}")


def generate_narrative(program_name, date_range, aggregate_stats):
    """
    Turn aggregate program metrics into a professional outcome summary.

    Args:
        program_name: str
        date_range: str — e.g. "January 2026 – March 2026"
        aggregate_stats: list of dicts {metric_name, average, count, unit}

    Returns:
        str — narrative paragraph, or None on failure
    """
    system = (
        "You write concise, professional program outcome summaries for "
        "Canadian nonprofits. "
        "Given a program name, date range, and aggregated metric data, write a "
        "single paragraph (3–5 sentences) summarising client outcomes. "
        "Use Canadian English spelling (colour, centre). "
        "Do not invent data — only reference the numbers provided."
    )
    user_msg = (
        f"Program: {program_name}\n"
        f"Period: {date_range}\n\n"
        f"Aggregate metrics:\n{json.dumps(aggregate_stats, indent=2)}"
    )
    return _call_openrouter(system, user_msg, max_tokens=512)


def _call_insights_api(system_prompt, user_message, max_tokens=2048):
    """Call the insights AI provider — OpenRouter or local Ollama.

    Checks for INSIGHTS_API_BASE first (Ollama or any OpenAI-compatible endpoint).
    Falls back to the standard OpenRouter integration.

    Returns:
        str — response text, or None on failure.
    """
    insights_base = getattr(settings, "INSIGHTS_API_BASE", "")
    if insights_base:
        # Local / custom provider (Ollama, etc.)
        api_key = getattr(settings, "INSIGHTS_API_KEY", "")
        model = getattr(settings, "INSIGHTS_MODEL", "llama3")
        url = f"{insights_base.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt + _SAFETY_FOOTER},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": max_tokens,
                },
                timeout=60,  # Local models can be slower
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            logger.exception("Insights API call failed (custom provider)")
            return None
    else:
        # Fall back to OpenRouter
        return _call_openrouter(system_prompt, user_message, max_tokens)


def generate_outcome_insights(program_name, date_range, structured_data, quotes):
    """Generate a report-ready narrative draft from qualitative outcome data.

    Args:
        program_name: str
        date_range: str — e.g. "2025-10-01 to 2026-01-31"
        structured_data: dict — output from get_structured_insights()
        quotes: list of dicts — PII-scrubbed quotes with text, target_name, note_id

    Returns:
        dict {summary, themes, cited_quotes, recommendations} or None on failure.
    """
    system = (
        "You write concise program report drafts for Canadian nonprofits. "
        "You will receive program outcome data including descriptor trends, "
        "engagement patterns, and participant quotes. Write a narrative summary "
        "that helps staff understand service patterns and outcomes.\n\n"
        "RULES — follow these exactly:\n"
        "- Use ONLY the numbers provided. Never calculate new statistics.\n"
        "- Report explicit counts: '3 of 20 participants mentioned...' not "
        "'participants frequently...'\n"
        "- Your narrative MUST be consistent with the descriptor trend data.\n"
        "- Quote participant words VERBATIM only. Never paraphrase.\n"
        "- If trends are flat or declining, report that honestly.\n"
        "- Rank themes by frequency. Only report the top 3.\n"
        "- If the most frequent theme appears in fewer than 3 quotes, "
        "say 'no dominant themes emerged.'\n"
        "- Use Canadian English spelling (colour, centre).\n\n"
        "PARTICIPANT FEEDBACK — this is critical:\n"
        "Read the quotes carefully for actionable feedback. Categorise what "
        "participants are saying into these categories:\n"
        "- 'request': things participants are asking for or need\n"
        "- 'suggestion': ideas participants have for improving the program\n"
        "- 'concern': things participants are unhappy about or struggling with "
        "in the program/service itself (not personal life struggles). "
        "Never use the word 'complaint' — frame all critical feedback as "
        "concerns or unmet needs.\n"
        "- 'praise': things participants appreciate about the program\n"
        "Each finding must include a short description AND at least one "
        "verbatim supporting quote. Only include categories that have evidence "
        "in the quotes — do not invent feedback.\n"
        "Some quotes have source='suggestion' — these are direct responses to "
        "'If you could change one thing about this program, what would it be?' "
        "and may include a staff-assigned priority. Pay special attention to these.\n\n"
        "RECURRING PATTERNS — important:\n"
        "Pay special attention to feedback that individually appears minor but "
        "recurs across multiple participants. Surface these as findings with "
        "accurate counts. A low-priority item mentioned by 5+ participants is "
        "more actionable than a high-priority item mentioned once.\n\n"
        "FOCUS: Return at most 3 participant_feedback items in the main list, "
        "prioritised by: (1) any urgent/safety items, (2) highest-frequency "
        "recurring patterns, (3) highest staff-rated priority. Quality over "
        "quantity — 3 actionable findings are better than 10 vague ones.\n\n"
        "Return a JSON object with these keys:\n"
        "- summary: 2-3 paragraphs of narrative text\n"
        "- themes: array of 3-5 theme strings with counts\n"
        "- cited_quotes: array of {text, note_id, context} — verbatim only\n"
        "- participant_feedback: array of objects (max 3), each with:\n"
        "    - category: one of 'request', 'suggestion', 'concern', 'praise'\n"
        "    - finding: 1 sentence describing the feedback\n"
        "    - count: how many participants expressed this\n"
        "    - supporting_quotes: array of {text, note_id} — verbatim only\n"
        "- recommendations: 1 paragraph of staff observations based on the "
        "feedback above\n\n"
        "Return ONLY the JSON object, no other text."
    )

    user_msg = (
        f"Program: {program_name}\n"
        f"Period: {date_range}\n\n"
        f"Descriptor trends (percentages by month):\n"
        f"{json.dumps(structured_data.get('descriptor_trend', []), indent=2)}\n\n"
        f"Current descriptor distribution:\n"
        f"{json.dumps(structured_data.get('descriptor_distribution', {}), indent=2)}\n\n"
        f"Engagement distribution:\n"
        f"{json.dumps(structured_data.get('engagement_distribution', {}), indent=2)}\n\n"
        f"Total notes: {structured_data.get('note_count', 0)}\n"
        f"Total participants: {structured_data.get('participant_count', 0)}\n\n"
        f"Participant quotes (PII-scrubbed, verbatim):\n"
        f"{json.dumps(quotes, indent=2)}"
    )

    result = _call_insights_api(system, user_msg, max_tokens=2048)
    if result is None:
        return None

    # Strip markdown fences if present
    text = result.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not parse outcome insights response: %s", text[:300])
        return None

    # Validate response structure
    validated = validate_insights_response(parsed, quotes)
    if validated is None:
        return None
    return validated


def validate_insights_response(response, original_quotes):
    """Validate AI response: check structure, verify quotes are verbatim.

    Returns:
        The response dict if valid, or None if validation fails.
    """
    required_keys = {"summary", "themes", "cited_quotes", "recommendations"}
    if not isinstance(response, dict):
        logger.warning("Insights response is not a dict")
        return None

    missing = required_keys - set(response.keys())
    if missing:
        logger.warning("Insights response missing keys: %s", missing)
        return None

    if not isinstance(response["summary"], str) or len(response["summary"]) < 20:
        logger.warning("Insights summary is too short or not a string")
        return None

    # Verify cited quotes are verbatim substrings of provided quotes
    original_texts = {q["text"] for q in original_quotes}
    if isinstance(response.get("cited_quotes"), list):
        verified_quotes = []
        for cq in response["cited_quotes"]:
            if not isinstance(cq, dict) or "text" not in cq:
                continue
            # Check if the quoted text is a substring of any provided quote
            is_verbatim = any(cq["text"] in orig for orig in original_texts)
            if is_verbatim:
                verified_quotes.append(cq)
            else:
                logger.info("AI quote not verbatim, skipping: %s", cq["text"][:80])
        response["cited_quotes"] = verified_quotes

    # Ensure themes is a list
    if not isinstance(response.get("themes"), list):
        response["themes"] = []

    # Validate participant_feedback — optional key (older cached responses won't have it)
    valid_categories = {"request", "suggestion", "concern", "complaint", "praise"}
    if isinstance(response.get("participant_feedback"), list):
        verified_feedback = []
        for item in response["participant_feedback"]:
            if not isinstance(item, dict):
                continue
            if item.get("category") not in valid_categories:
                continue
            if not item.get("finding"):
                continue
            # Verify supporting quotes are verbatim
            if isinstance(item.get("supporting_quotes"), list):
                verified_sq = []
                for sq in item["supporting_quotes"]:
                    if not isinstance(sq, dict) or "text" not in sq:
                        continue
                    is_verbatim = any(sq["text"] in orig for orig in original_texts)
                    if is_verbatim:
                        verified_sq.append(sq)
                    else:
                        logger.info("Feedback quote not verbatim, skipping: %s", sq.get("text", "")[:80])
                item["supporting_quotes"] = verified_sq
            else:
                item["supporting_quotes"] = []
            # Only keep feedback items that still have at least one verified quote
            if item["supporting_quotes"]:
                verified_feedback.append(item)
        response["participant_feedback"] = verified_feedback
    else:
        response["participant_feedback"] = []

    return response


def build_goal_chat(messages, program_name, metric_catalogue, existing_sections):
    """
    Multi-turn conversational goal builder.

    Sends the full conversation history to the AI along with program context.
    The AI guides the worker (and participant) through defining a measurable goal.

    Args:
        messages: list of {"role": "user"|"assistant", "content": str}
                  — PII-scrubbed conversation history
        program_name: str — the program this goal belongs to
        metric_catalogue: list of dicts {id, name, definition, category}
        existing_sections: list of str — names of existing plan sections

    Returns:
        dict {message, questions, draft} or None on failure.
        draft (when present): {name, description, client_goal, metric, suggested_section}
    """
    system = (
        "You are a goal-setting facilitator for a Canadian nonprofit. "
        "A caseworker (and possibly the participant they work with) is defining "
        "a new goal for the participant's plan. Guide them through a conversation "
        "to create a well-structured, measurable goal.\n\n"
        "YOUR ROLE:\n"
        "- Ask clarifying questions to understand what the participant wants to achieve\n"
        "- After 1–2 rounds of questions, present a structured draft goal\n"
        "- Refine the draft based on feedback until the worker is satisfied\n"
        "- Use warm, professional language — you may be read aloud to participants\n"
        "- Use Canadian English spelling (colour, centre, programme is NOT used)\n\n"
        "TECHNICAL REQUIREMENTS — every goal must have:\n"
        "- A concise target name (under 80 characters)\n"
        "- A SMART description (Specific, Measurable, Achievable, Relevant, Time-bound)\n"
        "- The participant's own words — how they would describe this goal themselves\n"
        "- A measurable metric on a 1–5 scale with clear descriptors for each level\n"
        "- A suggested plan section (from the existing sections, or a new one)\n\n"
        "METRIC RULES:\n"
        "- Check the provided metric catalogue FIRST. If an existing metric fits well, "
        "use it (set existing_metric_id to its id).\n"
        "- Only suggest a custom metric when no existing one is a good match.\n"
        "- Custom metrics MUST have a 1–5 scale with a clear descriptor for each level "
        "(e.g., '1 = No housing leads\\n2 = Actively searching\\n...').\n"
        "- The metric must produce meaningful data when tracked over time in progress notes.\n\n"
        f"PROGRAM: {program_name}\n\n"
        f"EXISTING PLAN SECTIONS: {json.dumps(existing_sections) if existing_sections else 'None yet — suggest a new section name.'}\n\n"
        f"AVAILABLE METRICS:\n{json.dumps(metric_catalogue, indent=2) if metric_catalogue else 'No metrics in the library yet.'}\n\n"
        "RESPONSE FORMAT — always return a JSON object:\n"
        "{\n"
        '  "message": "Your conversational response to the worker/participant",\n'
        '  "questions": ["Optional clarifying questions — omit if presenting a draft"],\n'
        '  "draft": null or {\n'
        '    "name": "Concise target name",\n'
        '    "description": "SMART outcome statement",\n'
        '    "client_goal": "How the participant would say it in their own words",\n'
        '    "metric": {\n'
        '      "existing_metric_id": null or integer,\n'
        '      "name": "Metric name",\n'
        '      "definition": "1 = Level 1 descriptor\\n2 = Level 2\\n3 = Level 3\\n4 = Level 4\\n5 = Level 5",\n'
        '      "min_value": 1,\n'
        '      "max_value": 5,\n'
        '      "unit": "score"\n'
        "    },\n"
        '    "suggested_section": "Section name"\n'
        "  }\n"
        "}\n\n"
        "Return ONLY the JSON object, no other text. "
        "Include a draft as soon as you have enough information (usually after 1–2 exchanges). "
        "Update the draft each time the worker provides feedback."
    )

    result = _call_openrouter(system, max_tokens=1024, messages=messages)
    if result is None:
        return None

    # Strip markdown fences if present
    text = result.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not parse goal builder response: %s", text[:300])
        return None

    return _validate_goal_chat_response(parsed, metric_catalogue)


def _validate_goal_chat_response(response, metric_catalogue):
    """Validate the structure of a goal builder AI response.

    Returns the response dict if valid, or None if validation fails.
    """
    if not isinstance(response, dict):
        logger.warning("Goal builder response is not a dict")
        return None

    if "message" not in response or not isinstance(response["message"], str):
        logger.warning("Goal builder response missing 'message' string")
        return None

    # Ensure questions is a list (or absent)
    if "questions" in response and not isinstance(response["questions"], list):
        response["questions"] = []

    # Validate draft structure if present
    draft = response.get("draft")
    if draft is not None:
        if not isinstance(draft, dict):
            response["draft"] = None
        else:
            # Required draft fields
            for key in ("name", "description", "client_goal"):
                if not isinstance(draft.get(key), str):
                    draft[key] = ""

            # Validate metric sub-object
            metric = draft.get("metric")
            if isinstance(metric, dict):
                # Validate existing_metric_id against catalogue
                eid = metric.get("existing_metric_id")
                if eid is not None:
                    catalogue_ids = {m["id"] for m in metric_catalogue} if metric_catalogue else set()
                    if eid not in catalogue_ids:
                        metric["existing_metric_id"] = None
                # Ensure required metric fields
                for key in ("name", "definition"):
                    if not isinstance(metric.get(key), str):
                        metric[key] = ""
                if not isinstance(metric.get("min_value"), (int, float)):
                    metric["min_value"] = 1
                if not isinstance(metric.get("max_value"), (int, float)):
                    metric["max_value"] = 5
                if not isinstance(metric.get("unit"), str):
                    metric["unit"] = "score"
            else:
                draft["metric"] = None

            if not isinstance(draft.get("suggested_section"), str):
                draft["suggested_section"] = ""

    return response


def suggest_note_structure(target_name, target_description, metric_names):
    """
    Suggest a progress note structure for a given plan target.

    Args:
        target_name: str
        target_description: str
        metric_names: list of str — names of metrics assigned to the target

    Returns:
        list of dicts {section, prompt} or None on failure
    """
    system = (
        "You help nonprofit workers write structured progress notes. "
        "Given a plan target and its metrics, suggest 3–5 note sections. "
        "Each section has a title and a one-sentence prompt for what to write. "
        "Return a JSON array: [{\"section\": \"<title>\", \"prompt\": \"<guidance>\"}]. "
        "Return ONLY the JSON array, no other text."
    )
    user_msg = (
        f"Target: {target_name}\n"
        f"Description: {target_description}\n"
        f"Metrics: {', '.join(metric_names)}"
    )
    result = _call_openrouter(system, user_msg)
    if result is None:
        return None
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not parse note structure: %s", result[:200])
        return None
