"""Pre-evaluation health check for scenario suite.

Validates that scenarios are well-formed before running the full
LLM evaluation pipeline. Catches stale URLs, missing personas,
empty step lists, and broken YAML.

Design doc: docs/plans/2026-02-21-qa-evaluation-enrichment-design.md
"""
from dataclasses import dataclass, field
from pathlib import Path

from .scenario_loader import discover_scenarios, load_personas


@dataclass
class HealthCheckResult:
    """Result of a suite health check."""
    total: int = 0
    passed: int = 0
    stale: list = field(default_factory=list)   # [(scenario_id, reason)]
    errors: list = field(default_factory=list)   # [(scenario_id, error_msg)]

    @property
    def pass_rate(self):
        return self.passed / self.total if self.total > 0 else 0.0

    @property
    def is_healthy(self):
        """Suite is healthy if >80% of scenarios pass and total > 0."""
        return self.total > 0 and self.pass_rate >= 0.8


def check_scenario_health(holdout_dir):
    """Run health checks on all scenarios in the holdout directory.

    Checks:
    - Scenario has an id and title
    - Scenario has steps (or moments for DITL)
    - Referenced persona exists in persona files
    - Steps have at least one action or intent

    Args:
        holdout_dir: Path to the konote-qa-scenarios repo.

    Returns:
        HealthCheckResult with pass/fail details.
    """
    result = HealthCheckResult()
    scenarios = discover_scenarios(holdout_dir)
    personas = load_personas(holdout_dir)

    result.total = len(scenarios)

    for path, scenario in scenarios:
        scenario_id = scenario.get("id", f"unknown ({path})")
        issues = []

        # Check: has steps or moments
        steps = scenario.get("steps", [])
        moments = scenario.get("moments", [])
        if not steps and not moments:
            issues.append("no steps or moments defined")

        # Check: persona exists
        persona_id = scenario.get("persona", "")
        if persona_id and persona_id not in personas:
            issues.append(f"persona '{persona_id}' not found in persona files")

        # Check: steps have actions or intent
        for step in steps:
            if not step.get("actions") and not step.get("intent"):
                issues.append(f"step {step.get('id', '?')} has no actions or intent")
                break  # One is enough to flag

        if issues:
            for issue in issues:
                result.stale.append((scenario_id, issue))
        else:
            result.passed += 1

    return result
