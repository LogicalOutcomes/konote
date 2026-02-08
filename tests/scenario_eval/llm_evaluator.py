"""LLM-based satisfaction evaluator using Claude API.

Sends page state + persona description + satisfaction criteria to Claude
and receives structured satisfaction scores.
"""
import json
import os

from .score_models import DIMENSIONS, DimensionScore, StepEvaluation

# Default to Haiku for cost efficiency — still multimodal
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def get_api_client():
    """Get an Anthropic API client. Returns None if no API key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Fall back to translation API key if configured
        api_key = os.environ.get("TRANSLATE_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        return None


def build_evaluation_prompt(persona_desc, step, page_state_text,
                            context_from_previous=""):
    """Build the evaluation prompt for a single step.

    Args:
        persona_desc: Full persona description text.
        step: The step dict from the scenario YAML.
        page_state_text: Formatted page state from capture_to_evaluation_context.
        context_from_previous: What happened in previous steps.

    Returns:
        System prompt and user message strings.
    """
    criteria_list = "\n".join(
        f"  - {c}" for c in step.get("satisfaction_criteria", [])
    )
    frustration_list = "\n".join(
        f"  - {f}" for f in step.get("frustration_triggers", [])
    )

    system_prompt = """You are evaluating a web application from the perspective of a specific user persona. You must evaluate how satisfying the experience would be for THIS PARTICULAR PERSON, not for a generic user.

Score each dimension 1-5 where:
  1 = Completely fails, persona would be frustrated or stuck
  2 = Partially works but significant friction for this persona
  3 = Acceptable but not smooth — persona can proceed with effort
  4 = Good experience, minor issues only
  5 = Excellent, persona would be pleased

Be honest and critical. A page that "works" but confuses the persona should score 2-3, not 4.
Consider this persona's tech comfort, mental model, and behavioural modifiers.

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation outside the JSON."""

    user_message = f"""## Persona
{persona_desc}

## What they were trying to do
{step.get('intent', 'Unknown')}

## Context from previous steps
{context_from_previous or 'This is the first step — no prior context.'}

{page_state_text}

## Satisfaction Criteria (score each 1-5)
{criteria_list or '  (no specific criteria for this step)'}

## Known Frustration Triggers for this persona
{frustration_list or '  (none specified)'}

## Evaluation Dimensions (score each 1-5)
1. Clarity: Can this persona understand what they see?
2. Efficiency: How many actions to accomplish the goal?
3. Feedback: Does the system confirm what happened?
4. Error Recovery: Can they recover from mistakes?
5. Accessibility: Can this specific persona use it (perceive + operate)?
6. Language: Correct language, appropriate terminology?
7. Confidence: Would this persona feel confident they did the right thing?

## Required JSON Response Format
{{
  "dimension_scores": {{
    "clarity": {{"score": <1-5>, "reasoning": "<why>"}},
    "efficiency": {{"score": <1-5>, "reasoning": "<why>"}},
    "feedback": {{"score": <1-5>, "reasoning": "<why>"}},
    "error_recovery": {{"score": <1-5 or null if N/A>, "reasoning": "<why>"}},
    "accessibility": {{"score": <1-5>, "reasoning": "<why>"}},
    "language": {{"score": <1-5>, "reasoning": "<why>"}},
    "confidence": {{"score": <1-5>, "reasoning": "<why>"}}
  }},
  "criteria_scores": {{
    "<criterion text>": <1-5>,
    ...
  }},
  "overall_satisfaction": <1.0-5.0>,
  "one_line_summary": "<what this persona would say about this step>",
  "improvement_suggestions": [
    "<specific, actionable suggestion>",
    ...
  ]
}}"""

    return system_prompt, user_message


def evaluate_step(persona_desc, step, page_state_text,
                  context_from_previous="", model=None):
    """Evaluate a single step using the Claude API.

    Args:
        persona_desc: Full persona description text.
        step: The step dict from the scenario YAML.
        page_state_text: Formatted page state from capture_to_evaluation_context.
        context_from_previous: What happened in previous steps.
        model: Model ID to use (defaults to Haiku).

    Returns:
        StepEvaluation dataclass, or None if API is unavailable.
    """
    client = get_api_client()
    if not client:
        return None

    system_prompt, user_message = build_evaluation_prompt(
        persona_desc, step, page_state_text, context_from_previous
    )

    try:
        response = client.messages.create(
            model=model or DEFAULT_MODEL,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        # Parse the JSON response
        response_text = response.content[0].text.strip()
        # Handle markdown code blocks if the model wraps the JSON
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        data = json.loads(response_text)
        return _parse_evaluation_response(data, step)

    except Exception as e:
        # Return a placeholder evaluation with the error noted
        eval_result = StepEvaluation(
            scenario_id=step.get("id", "?"),
            step_id=step.get("id", 0),
            persona_id=step.get("actor", "?"),
            one_line_summary=f"LLM evaluation failed: {e}",
        )
        return eval_result


def _parse_evaluation_response(data, step):
    """Parse the JSON response from the LLM into a StepEvaluation."""
    eval_result = StepEvaluation(
        scenario_id="",  # Set by caller
        step_id=step.get("id", 0),
        persona_id=step.get("actor", ""),
    )

    # Parse dimension scores
    dim_scores = data.get("dimension_scores", {})
    for dim in DIMENSIONS:
        if dim in dim_scores:
            dim_data = dim_scores[dim]
            score = dim_data.get("score")
            if score is not None:
                score = float(score)
            eval_result.dimension_scores[dim] = DimensionScore(
                dimension=dim,
                score=score,
                reasoning=dim_data.get("reasoning", ""),
            )

    # Parse criteria scores
    eval_result.criteria_scores = data.get("criteria_scores", {})

    # Overall
    eval_result.overall_satisfaction = float(data.get("overall_satisfaction", 0))
    eval_result.one_line_summary = data.get("one_line_summary", "")
    eval_result.improvement_suggestions = data.get("improvement_suggestions", [])

    return eval_result


def format_persona_for_prompt(persona_data):
    """Format a persona YAML dict into a text description for the LLM prompt."""
    if not persona_data:
        return "Unknown persona"

    parts = [
        f"Name: {persona_data.get('name', 'Unknown')}",
        f"Role: {persona_data.get('title', persona_data.get('role', 'Unknown'))}",
        f"Agency: {persona_data.get('agency', 'Unknown')}",
        f"Tech comfort: {persona_data.get('tech_comfort', 'Unknown')}",
        f"Language: {persona_data.get('language', 'English')}",
        f"Device: {persona_data.get('device', 'Desktop')}",
    ]

    if persona_data.get("background"):
        parts.append(f"\nBackground: {persona_data['background']}")
    if persona_data.get("mental_model"):
        parts.append(f"\nMental model: {persona_data['mental_model']}")
    if persona_data.get("frustrations"):
        parts.append("\nGeneral frustrations:")
        for f in persona_data["frustrations"]:
            parts.append(f"  - {f}")
    if persona_data.get("under_pressure"):
        parts.append(f"\nUnder pressure: {persona_data['under_pressure']}")
    if persona_data.get("when_confused"):
        parts.append(f"\nWhen confused: {persona_data['when_confused']}")

    return "\n".join(parts)
