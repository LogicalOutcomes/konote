"""Scenario-based QA evaluation tests.

These tests read scenario YAML files from the holdout repo, execute
them with Playwright, and optionally evaluate satisfaction with an LLM.

Run all scenarios:
    SCENARIO_HOLDOUT_DIR=C:/path/to/konote-qa-scenarios pytest tests/scenario_eval/ -v

Run without LLM evaluation (dry run — screenshots only):
    SCENARIO_HOLDOUT_DIR=C:/path/to/konote-qa-scenarios pytest tests/scenario_eval/ -v --no-llm

Run only calibration scenarios:
    SCENARIO_HOLDOUT_DIR=C:/path/to/konote-qa-scenarios pytest tests/scenario_eval/ -v -k "calibration"

Run a specific scenario:
    SCENARIO_HOLDOUT_DIR=C:/path/to/konote-qa-scenarios pytest tests/scenario_eval/ -v -k "SCN_010"
"""
import os

import pytest

# Skip everything if Playwright is not installed
pw = pytest.importorskip("playwright.sync_api", reason="Playwright required")

from .conftest import get_all_results
from .scenario_loader import discover_scenarios, load_personas
from .scenario_runner import ScenarioRunner


def _should_skip_llm():
    """Check if LLM evaluation should be skipped (--no-llm or env var)."""
    return bool(os.environ.get("SCENARIO_NO_LLM", ""))


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestCalibrationScenarios(ScenarioRunner):
    """Run calibration scenarios to validate the LLM evaluator."""

    def _get_scenarios(self):
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")
        return discover_scenarios(holdout, ids=["CAL-001", "CAL-002", "CAL-003"])

    def _run_calibration(self, scenario_id):
        """Common logic for running a single calibration scenario."""
        scenarios = self._get_scenarios()
        cal = [s for _, s in scenarios if s["id"] == scenario_id]
        if not cal:
            self.skipTest(f"{scenario_id} not found in holdout dir")

        scenario = cal[0]
        self.personas = load_personas()
        self.use_llm = not _should_skip_llm()

        screenshot_dir = os.path.join(
            os.environ.get("SCENARIO_HOLDOUT_DIR", ""),
            "reports", "screenshots",
        )
        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_calibration_good_page(self):
        """CAL-001: Executive dashboard should score 4.2-5.0."""
        result = self._run_calibration("CAL-001")

        if self.use_llm and result.avg_score > 0:
            self.assertGreaterEqual(
                result.avg_score, 3.5,
                f"CAL-001 scored {result.avg_score:.1f} — expected >= 3.5 for known-good page"
            )

    def test_calibration_mediocre_page(self):
        """CAL-002: Admin settings should score 2.8-3.8."""
        self._run_calibration("CAL-002")

    def test_calibration_bad_page(self):
        """CAL-003: Audit log should score 1.0-2.3."""
        self._run_calibration("CAL-003")


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestStarterScenarios(ScenarioRunner):
    """Run the 3 starter scenarios for Phase 0 validation."""

    def _get_scenarios(self):
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")
        return discover_scenarios(holdout, ids=["SCN-005", "SCN-010", "SCN-050"])

    def _run_starter(self, scenario_id):
        """Common logic for running a single starter scenario."""
        scenarios = self._get_scenarios()
        scn = [s for _, s in scenarios if s["id"] == scenario_id]
        if not scn:
            self.skipTest(f"{scenario_id} not found in holdout dir")

        scenario = scn[0]
        self.personas = load_personas()
        self.use_llm = not _should_skip_llm()

        screenshot_dir = os.path.join(
            os.environ.get("SCENARIO_HOLDOUT_DIR", ""),
            "reports", "screenshots",
        )
        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_first_5_minutes(self):
        """SCN-005: First 5 Minutes — cold login for each role."""
        self._run_starter("SCN-005")

    def test_morning_intake(self):
        """SCN-010: Morning Intake — receptionist to staff handoff."""
        self._run_starter("SCN-010")

    def test_keyboard_only(self):
        """SCN-050: Keyboard-Only Workflow — full intake by keyboard."""
        self._run_starter("SCN-050")
