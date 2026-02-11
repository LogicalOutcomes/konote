"""Objective scoring for dimensions that can be measured without an LLM.

Replaces subjective LLM scoring with measurable metrics for:
- Accessibility: axe-core violation count and severity
- Efficiency: number of user actions required per step
- Language: document lang attribute vs persona's expected language
"""
from .score_models import DimensionScore


def normalise_language_to_code(lang_description):
    """Convert a descriptive language string to an ISO 639-1 code.

    Examples:
        "English"                                      -> "en"
        "French (primary), reads English"              -> "fr"
        "English and Somali"                           -> "en"
        "English and French (bilingual, prefers ...)"  -> "en"
        "fr"                                           -> "fr"
        "en-CA"                                        -> "en-ca"
    """
    text = lang_description.lower().strip()
    # Already an ISO code (2-3 chars, optionally with region)
    if len(text) <= 6 and (len(text) <= 3 or "-" in text):
        return text
    # "French (primary)" at the start means French is the main language
    if text.startswith("french"):
        return "fr"
    # Everything else defaults to English
    return "en"


def get_persona_language(persona_data):
    """Extract the expected language code from persona data.

    Checks persona.test_user.language first (ISO code like 'fr'),
    then normalises the descriptive persona.language field
    (e.g. "French (primary), reads English" -> 'fr').

    Returns:
        Language code string, e.g. 'en', 'fr'.
    """
    if not persona_data:
        return "en"
    # Prefer test_user.language — already an ISO code when present
    test_user = persona_data.get("test_user", {})
    iso_lang = test_user.get("language", "")
    if iso_lang:
        return iso_lang.lower().strip()
    # Fall back to the descriptive language field and normalise it
    lang = persona_data.get("language", "").strip()
    if not lang:
        return "en"
    return normalise_language_to_code(lang)


# Impact weights for axe-core violations
_AXE_IMPACT_WEIGHTS = {
    "critical": 3,
    "serious": 2,
    "moderate": 1,
    "minor": 0.5,
}


def score_accessibility(capture):
    """Score accessibility 1-5 based on axe-core violations.

    Scoring:
        0 weighted violations       = 5.0
        0.5-2 weighted violations   = 4.0
        2.1-5 weighted violations   = 3.0
        5.1-10 weighted violations  = 2.0
        10+ weighted violations     = 1.0

    Args:
        capture: StepCapture with axe_violations and axe_violation_count.

    Returns:
        DimensionScore for the accessibility dimension.
    """
    if not capture.axe_violations and capture.axe_violation_count == 0:
        return DimensionScore(
            dimension="accessibility",
            score=5.0,
            reasoning="No axe-core violations detected.",
        )

    # Calculate weighted violation score
    weighted = 0.0
    details = []
    for v in capture.axe_violations:
        impact = v.get("impact", "minor")
        weight = _AXE_IMPACT_WEIGHTS.get(impact, 0.5)
        nodes = v.get("nodes_count", 1)
        weighted += weight * nodes
        details.append(f"{v.get('description', 'unknown')} ({impact}, {nodes} nodes)")

    # Convert weighted score to 1-5
    if weighted <= 0:
        score = 5.0
    elif weighted <= 2:
        score = 4.0
    elif weighted <= 5:
        score = 3.0
    elif weighted <= 10:
        score = 2.0
    else:
        score = 1.0

    detail_str = "; ".join(details[:5])  # Cap at 5 for readability
    if len(details) > 5:
        detail_str += f" (+{len(details) - 5} more)"

    return DimensionScore(
        dimension="accessibility",
        score=score,
        reasoning=f"axe-core: {capture.axe_violation_count} violations "
                  f"(weighted {weighted:.1f}). {detail_str}",
    )


def count_user_actions(actions):
    """Count user-facing actions in a step's action list.

    Counts: goto, fill, click, press, type, clear
    Ignores: wait, set_viewport, set_network, login_as, etc. (test infra)

    Args:
        actions: List of action dicts from a scenario step.

    Returns:
        int count of user-facing actions.
    """
    user_action_keys = {"goto", "fill", "click", "press", "type", "clear"}
    count = 0
    for action in actions:
        if not isinstance(action, dict):
            continue
        for key in action:
            if key in user_action_keys:
                count += 1
    return count


def score_efficiency(action_count):
    """Score efficiency 1-5 based on number of user actions.

    Fewer actions to accomplish a goal = higher efficiency.
    Scoring:
        1-2 actions  = 5.0  (streamlined)
        3-4 actions  = 4.0  (good)
        5-6 actions  = 3.0  (acceptable)
        7-9 actions  = 2.0  (cumbersome)
        10+ actions  = 1.0  (too many steps)

    Args:
        action_count: Number of user-facing actions in this step.

    Returns:
        DimensionScore for the efficiency dimension.
    """
    if action_count <= 2:
        score = 5.0
    elif action_count <= 4:
        score = 4.0
    elif action_count <= 6:
        score = 3.0
    elif action_count <= 9:
        score = 2.0
    else:
        score = 1.0

    return DimensionScore(
        dimension="efficiency",
        score=score,
        reasoning=f"{action_count} user actions in this step.",
    )


def score_language(capture, expected_lang):
    """Score language correctness 1-5 based on document lang attribute.

    Compares the document's lang attribute against the persona's expected
    language. Handles base language matching (e.g., 'fr' matches 'fr-CA').

    Scoring:
        Exact match          = 5.0
        Base language match   = 4.0  (e.g., 'fr' vs 'fr-CA')
        Lang not set          = 3.0  (can't verify)
        Wrong language        = 1.0

    Args:
        capture: StepCapture with document_lang.
        expected_lang: Expected language code (e.g., 'en', 'fr', 'fr-CA').

    Returns:
        DimensionScore for the language dimension.
    """
    doc_lang = (capture.document_lang or "").lower().strip()
    expected = (expected_lang or "en").lower().strip()

    if not doc_lang:
        return DimensionScore(
            dimension="language",
            score=3.0,
            reasoning="Document lang attribute not set — cannot verify language.",
        )

    # Exact match
    if doc_lang == expected:
        return DimensionScore(
            dimension="language",
            score=5.0,
            reasoning=f"Document lang '{doc_lang}' matches expected '{expected}'.",
        )

    # Base language match (e.g., 'fr' matches 'fr-ca', 'en' matches 'en-ca')
    doc_base = doc_lang.split("-")[0]
    expected_base = expected.split("-")[0]
    if doc_base == expected_base:
        return DimensionScore(
            dimension="language",
            score=4.0,
            reasoning=f"Document lang '{doc_lang}' matches base language "
                      f"'{expected_base}' (expected '{expected}').",
        )

    # Wrong language
    return DimensionScore(
        dimension="language",
        score=1.0,
        reasoning=f"Document lang '{doc_lang}' does not match "
                  f"expected '{expected}'.",
    )


def compute_objective_scores(capture, actions=None, expected_lang=None):
    """Compute all objective dimension scores for a step.

    Args:
        capture: StepCapture from the step.
        actions: List of action dicts for efficiency scoring (optional).
        expected_lang: Expected language code for the persona (optional).

    Returns:
        Dict of dimension name -> DimensionScore for objectively scored
        dimensions.
    """
    scores = {}

    # Accessibility — always available if axe was run
    scores["accessibility"] = score_accessibility(capture)

    # Efficiency — only if actions are provided
    if actions is not None:
        action_count = count_user_actions(actions)
        scores["efficiency"] = score_efficiency(action_count)

    # Language — only if expected language is known
    if expected_lang:
        scores["language"] = score_language(capture, expected_lang)

    return scores
