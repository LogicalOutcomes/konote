"""Tests for report_generator enrichments (traffic-light summary + task outcomes)."""
from unittest import TestCase

from .report_generator import generate_report
from .score_models import DimensionScore, ScenarioResult, StepEvaluation


def _make_result(scenario_id, title, score, task_outcome="independent"):
    """Helper: create a ScenarioResult with one step at the given score."""
    r = ScenarioResult(scenario_id=scenario_id, title=title)
    r.step_evaluations = [
        StepEvaluation(
            scenario_id=scenario_id,
            step_id=1,
            persona_id="DS1",
            overall_satisfaction=score,
            task_outcome=task_outcome,
            task_outcome_reasoning=f"Reason for {task_outcome}",
            dimension_scores={
                "clarity": DimensionScore("clarity", score, "test"),
            },
        ),
    ]
    return r


class TestTrafficLightSummary(TestCase):
    """Report should start with a traffic-light summary section."""

    def test_summary_at_top(self):
        results = [_make_result("SCN-001", "Login", 4.5)]
        report = generate_report(results)
        # Summary should appear before the Satisfaction Gaps section
        summary_pos = report.find("EVALUATION SUMMARY")
        gaps_pos = report.find("## Satisfaction Gaps")
        self.assertGreater(summary_pos, -1, "Summary section missing")
        self.assertLess(summary_pos, gaps_pos, "Summary should be before Gaps")

    def test_summary_includes_overall_colour(self):
        results = [
            _make_result("SCN-001", "Login", 4.5),
            _make_result("SCN-002", "Note", 2.5, "abandoned"),
        ]
        report = generate_report(results)
        # Should show YELLOW (mixed scores)
        self.assertIn("YELLOW", report[:500])

    def test_summary_includes_task_outcome_counts(self):
        results = [
            _make_result("SCN-001", "Login", 4.5, "independent"),
            _make_result("SCN-002", "Note", 3.0, "assisted"),
            _make_result("SCN-003", "Survey", 2.0, "abandoned"),
        ]
        report = generate_report(results)
        self.assertIn("Independent", report)
        self.assertIn("Assisted", report)
        self.assertIn("Abandoned", report)


class TestTaskOutcomeInDetails(TestCase):
    """Step details should show task_outcome."""

    def test_step_shows_task_outcome(self):
        results = [_make_result("SCN-001", "Login", 4.0, "independent")]
        report = generate_report(results)
        self.assertIn("independent", report)
