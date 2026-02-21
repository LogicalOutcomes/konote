"""Tests for LLM evaluator enrichments (scoring_instruction + task_outcome)."""
from unittest import TestCase

from .llm_evaluator import build_evaluation_prompt, format_persona_for_prompt


class TestScoringInstructionInPrompt(TestCase):
    """Persona scoring_instruction should appear in the evaluation prompt."""

    def test_scoring_instruction_injected(self):
        persona_desc = "Name: Casey\nRole: Staff\n\nPERSONA-SPECIFIC SCORING RULE (you MUST apply this):\nPenalise pages with >5 competing elements."
        step = {"intent": "Create a note", "satisfaction_criteria": []}
        page_state = "URL: /notes/add/\nTitle: New Note"

        _, user_msg = build_evaluation_prompt(persona_desc, step, page_state)
        self.assertIn("PERSONA-SPECIFIC SCORING RULE", user_msg)

    def test_no_scoring_instruction_still_works(self):
        persona_desc = "Name: Casey\nRole: Staff"
        step = {"intent": "Create a note", "satisfaction_criteria": []}
        page_state = "URL: /notes/add/\nTitle: New Note"

        system_prompt, user_msg = build_evaluation_prompt(persona_desc, step, page_state)
        # Should not crash and should still have dimensions
        self.assertIn("clarity", user_msg)


class TestTaskOutcomeInPrompt(TestCase):
    """The prompt should request task_outcome in the JSON response."""

    def test_prompt_requests_task_outcome(self):
        persona_desc = "Name: Casey"
        step = {"intent": "Create a note", "satisfaction_criteria": []}
        page_state = "URL: /notes/add/"

        system_prompt, user_msg = build_evaluation_prompt(persona_desc, step, page_state)
        self.assertIn("task_outcome", user_msg)
        self.assertIn("independent", user_msg)
        self.assertIn("assisted", user_msg)
        self.assertIn("abandoned", user_msg)
        self.assertIn("error_unnoticed", user_msg)

    def test_system_prompt_mentions_task_outcome(self):
        persona_desc = "Name: Casey"
        step = {"intent": "Create a note", "satisfaction_criteria": []}
        page_state = "URL: /notes/add/"

        system_prompt, _ = build_evaluation_prompt(persona_desc, step, page_state)
        self.assertIn("task_outcome", system_prompt)


class TestFormatPersonaWithScoringInstruction(TestCase):
    """format_persona_for_prompt should include scoring_instruction."""

    def test_includes_scoring_instruction(self):
        persona = {
            "name": "Casey",
            "role": "Staff",
            "title": "Outreach Worker",
            "scoring_instruction": "Penalise pages with more than 5 competing visual elements.",
        }
        result = format_persona_for_prompt(persona)
        self.assertIn("PERSONA-SPECIFIC SCORING RULE", result)
        self.assertIn("Penalise pages with more than 5 competing visual elements.", result)

    def test_no_scoring_instruction_omits_section(self):
        persona = {"name": "Casey", "role": "Staff", "title": "Outreach Worker"}
        result = format_persona_for_prompt(persona)
        self.assertNotIn("PERSONA-SPECIFIC SCORING RULE", result)


class TestParseTaskOutcome(TestCase):
    """_parse_evaluation_response should extract task_outcome fields."""

    def test_parse_with_task_outcome(self):
        from .llm_evaluator import _parse_evaluation_response

        data = {
            "dimension_scores": {
                "clarity": {"score": 4, "reasoning": "Clear"},
            },
            "criteria_scores": {},
            "overall_satisfaction": 4.0,
            "one_line_summary": "Good",
            "improvement_suggestions": [],
            "task_outcome": "independent",
            "task_outcome_reasoning": "Simple form, clear confirmation",
        }
        step = {"id": 1, "actor": "DS1"}
        result = _parse_evaluation_response(data, step)
        self.assertEqual(result.task_outcome, "independent")
        self.assertEqual(result.task_outcome_reasoning, "Simple form, clear confirmation")

    def test_parse_without_task_outcome(self):
        from .llm_evaluator import _parse_evaluation_response

        data = {
            "dimension_scores": {},
            "criteria_scores": {},
            "overall_satisfaction": 3.0,
            "one_line_summary": "OK",
            "improvement_suggestions": [],
        }
        step = {"id": 1, "actor": "DS1"}
        result = _parse_evaluation_response(data, step)
        self.assertIsNone(result.task_outcome)
