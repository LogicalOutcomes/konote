"""Tests for results_serializer task_outcome support."""
from unittest import TestCase

from .results_serializer import serialize_results
from .score_models import ScenarioResult, StepEvaluation


class TestSerializeTaskOutcome(TestCase):
    """Serialized JSON should include task_outcome fields."""

    def test_step_includes_task_outcome(self):
        r = ScenarioResult(scenario_id="SCN-001", title="Test")
        r.step_evaluations = [
            StepEvaluation(
                scenario_id="SCN-001", step_id=1, persona_id="DS1",
                task_outcome="independent",
                task_outcome_reasoning="Simple form",
            ),
        ]
        data = serialize_results([r])
        step = data["scenarios"][0]["steps"][0]
        self.assertEqual(step["task_outcome"], "independent")
        self.assertEqual(step["task_outcome_reasoning"], "Simple form")

    def test_summary_includes_task_outcome_counts(self):
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
        ]
        data = serialize_results([r])
        self.assertIn("task_outcome_counts", data["summary"])
        self.assertEqual(data["summary"]["task_outcome_counts"]["independent"], 1)

    def test_missing_task_outcome_serializes_as_none(self):
        r = ScenarioResult(scenario_id="SCN-001", title="Test")
        r.step_evaluations = [
            StepEvaluation(scenario_id="SCN-001", step_id=1, persona_id="DS1"),
        ]
        data = serialize_results([r])
        step = data["scenarios"][0]["steps"][0]
        self.assertIsNone(step["task_outcome"])
