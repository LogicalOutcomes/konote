"""Tests for scenario health check (pre-evaluation validation)."""
import os
import tempfile
from pathlib import Path
from unittest import TestCase

import yaml

from .health_check import check_scenario_health, HealthCheckResult


class TestHealthCheckResult(TestCase):
    """HealthCheckResult data structure."""

    def test_pass_rate(self):
        r = HealthCheckResult(total=10, passed=8, stale=[("SCN-X", "bad URL")], errors=[])
        self.assertEqual(r.pass_rate, 0.8)

    def test_is_healthy_above_threshold(self):
        r = HealthCheckResult(total=10, passed=9, stale=[], errors=[])
        self.assertTrue(r.is_healthy)

    def test_is_unhealthy_below_threshold(self):
        r = HealthCheckResult(total=10, passed=7, stale=[("a","b"),("c","d"),("e","f")], errors=[])
        self.assertFalse(r.is_healthy)  # 70% < 80% threshold

    def test_empty_suite_is_unhealthy(self):
        r = HealthCheckResult(total=0, passed=0, stale=[], errors=[])
        self.assertFalse(r.is_healthy)


class TestCheckScenarioHealth(TestCase):
    """check_scenario_health validates scenarios from a holdout dir."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create a minimal scenario directory
        scenarios_dir = Path(self.tmpdir) / "scenarios" / "daily"
        scenarios_dir.mkdir(parents=True)

        self.good_scenario = {
            "id": "SCN-001",
            "title": "Good scenario",
            "persona": "DS1",
            "steps": [{"id": 1, "intent": "Login", "actions": [{"goto": "/"}]}],
        }
        with open(scenarios_dir / "SCN-001.yaml", "w") as f:
            yaml.dump(self.good_scenario, f)

        self.no_steps_scenario = {
            "id": "SCN-002",
            "title": "Broken scenario",
            "persona": "DS1",
            # No steps — stale/broken
        }
        with open(scenarios_dir / "SCN-002.yaml", "w") as f:
            yaml.dump(self.no_steps_scenario, f)

        # Create persona file
        personas_dir = Path(self.tmpdir) / "personas"
        personas_dir.mkdir()
        with open(personas_dir / "staff.yaml", "w") as f:
            yaml.dump({"personas": {"DS1": {"name": "Casey", "role": "Staff"}}}, f)

    def test_detects_stale_scenarios(self):
        result = check_scenario_health(self.tmpdir)
        self.assertEqual(result.total, 2)
        # SCN-002 has no steps, should be flagged
        stale_ids = [s[0] for s in result.stale]
        self.assertIn("SCN-002", stale_ids)

    def test_passes_valid_scenarios(self):
        result = check_scenario_health(self.tmpdir)
        self.assertGreaterEqual(result.passed, 1)  # SCN-001 should pass
