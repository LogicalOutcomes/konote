"""Tests for score_models enrichments (task_outcome)."""
from unittest import TestCase

from .score_models import (
    TASK_OUTCOMES,
    DimensionScore,
    ScenarioResult,
    StepEvaluation,
    task_outcome_colour,
)


class TestTaskOutcomeField(TestCase):
    """StepEvaluation should carry task_outcome and reasoning."""

    def test_default_task_outcome_is_none(self):
        e = StepEvaluation(scenario_id="SCN-001", step_id=1, persona_id="DS1")
        self.assertIsNone(e.task_outcome)
        self.assertEqual(e.task_outcome_reasoning, "")

    def test_task_outcome_can_be_set(self):
        e = StepEvaluation(
            scenario_id="SCN-001", step_id=1, persona_id="DS1",
            task_outcome="independent",
            task_outcome_reasoning="Form is simple and clear",
        )
        self.assertEqual(e.task_outcome, "independent")
        self.assertEqual(e.task_outcome_reasoning, "Form is simple and clear")


class TestTaskOutcomeConstants(TestCase):
    """TASK_OUTCOMES list and colour mapping."""

    def test_four_outcomes_defined(self):
        self.assertEqual(len(TASK_OUTCOMES), 4)
        self.assertIn("independent", TASK_OUTCOMES)
        self.assertIn("assisted", TASK_OUTCOMES)
        self.assertIn("abandoned", TASK_OUTCOMES)
        self.assertIn("error_unnoticed", TASK_OUTCOMES)

    def test_colour_mapping(self):
        self.assertEqual(task_outcome_colour("independent"), "green")
        self.assertEqual(task_outcome_colour("assisted"), "yellow")
        self.assertEqual(task_outcome_colour("abandoned"), "orange")
        self.assertEqual(task_outcome_colour("error_unnoticed"), "red")
        self.assertEqual(task_outcome_colour("unknown"), "grey")


class TestScenarioResultTaskOutcomes(TestCase):
    """ScenarioResult should aggregate task outcomes across steps."""

    def test_task_outcome_counts(self):
        r = ScenarioResult(scenario_id="SCN-001", title="Test")
        r.step_evaluations = [
            StepEvaluation(
                scenario_id="SCN-001", step_id=1, persona_id="DS1",
                task_outcome="independent",
            ),
            StepEvaluation(
                scenario_id="SCN-001", step_id=2, persona_id="DS1",
                task_outcome="assisted",
            ),
            StepEvaluation(
                scenario_id="SCN-001", step_id=3, persona_id="DS1",
                task_outcome="independent",
            ),
        ]
        counts = r.task_outcome_counts
        self.assertEqual(counts["independent"], 2)
        self.assertEqual(counts["assisted"], 1)
        self.assertEqual(counts.get("abandoned", 0), 0)
