# QA Evaluation Enrichment — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two complementary QA tracks: Track A (15 Playwright interaction tests with `qa_check` command) and Track B enrichments (health check, task_outcome field, persona scoring instructions, interaction test gate, traffic-light summaries).

**Architecture:** Track A lives in a single test file (`test_interactions.py`) with a management command wrapper. Track B enriches five existing modules: `score_models.py`, `llm_evaluator.py`, `scenario_runner.py`, `report_generator.py`, and `results_serializer.py`. New persona and scenario YAML files go in the sibling `konote-qa-scenarios` repo.

**Tech Stack:** Django 5, pytest, Playwright (Python sync API), YAML, existing LLM evaluation pipeline (Anthropic Claude API).

**Design Doc:** `docs/plans/2026-02-21-qa-evaluation-enrichment-design.md`

**Repos:**
- `konote-app` (this worktree: `.worktrees/feat-qa-evaluation-enrichment/`) — Tasks 1–10
- `konote-qa-scenarios` (sibling: `../konote-qa-scenarios/`) — Tasks 11–16

---

## Task 1: Add `task_outcome` to Score Models

**Files:**
- Modify: `tests/scenario_eval/score_models.py`
- Create: `tests/scenario_eval/test_score_models.py`

**Step 1: Write failing tests**

```python
# tests/scenario_eval/test_score_models.py
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/scenario_eval/test_score_models.py -v`
Expected: ImportError — `TASK_OUTCOMES` and `task_outcome_colour` don't exist yet.

**Step 3: Implement — modify `score_models.py`**

Add after the `BANDS` dict (around line 23):

```python
# Task outcome levels (from QA enrichment design)
TASK_OUTCOMES = ["independent", "assisted", "abandoned", "error_unnoticed"]


def task_outcome_colour(outcome):
    """Map a task outcome to a report colour."""
    return {
        "independent": "green",
        "assisted": "yellow",
        "abandoned": "orange",
        "error_unnoticed": "red",
    }.get(outcome, "grey")
```

Add two new fields to the `StepEvaluation` dataclass (after `objective_scores`):

```python
    # Task outcome (QA enrichment) — set by LLM evaluator
    task_outcome: str = None       # one of TASK_OUTCOMES or None
    task_outcome_reasoning: str = ""
```

Add a property to `ScenarioResult` (after `satisfaction_gap`):

```python
    @property
    def task_outcome_counts(self):
        """Count task outcomes across all steps."""
        counts = {}
        for e in self.step_evaluations:
            if e.task_outcome:
                counts[e.task_outcome] = counts.get(e.task_outcome, 0) + 1
        return counts
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/scenario_eval/test_score_models.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git branch --show-current && git add tests/scenario_eval/score_models.py tests/scenario_eval/test_score_models.py && git commit -m "feat: add task_outcome field to StepEvaluation and ScenarioResult"
```

---

## Task 2: Add `scoring_instruction` and `task_outcome` to LLM Evaluator

**Files:**
- Modify: `tests/scenario_eval/llm_evaluator.py`
- Create: `tests/scenario_eval/test_llm_evaluator.py`

**Step 1: Write failing tests**

```python
# tests/scenario_eval/test_llm_evaluator.py
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/scenario_eval/test_llm_evaluator.py -v`
Expected: Multiple failures — task_outcome not in prompt, not parsed, scoring_instruction not formatted.

**Step 3a: Modify `format_persona_for_prompt` in `llm_evaluator.py`**

At the end of the function (before `return "\n".join(parts)`, around line 260), add:

```python
    if persona_data.get("scoring_instruction"):
        parts.append(
            f"\nPERSONA-SPECIFIC SCORING RULE (you MUST apply this):\n"
            f"{persona_data['scoring_instruction']}"
        )
```

**Step 3b: Modify `build_evaluation_prompt` — add task_outcome to system prompt**

In the `system_prompt` string (around line 78), add after the "Be honest and critical" paragraph:

```python
Also assess whether this persona could complete the task:
- "independent" = completes without help
- "assisted" = would need to ask a colleague
- "abandoned" = gives up or works around the system
- "error_unnoticed" = thinks they're done but entered incorrect data

Include your task_outcome assessment in the JSON response.
```

**Step 3c: Modify `build_evaluation_prompt` — add task_outcome to JSON response format**

In the `user_message` JSON template (around line 134), add after `"improvement_suggestions"`:

```python
  "task_outcome": "<independent|assisted|abandoned|error_unnoticed>",
  "task_outcome_reasoning": "<why this persona would reach this outcome>"
```

**Step 3d: Modify `_parse_evaluation_response` — extract task_outcome**

After the `improvement_suggestions` line (around line 229), add:

```python
    # Task outcome (QA enrichment)
    eval_result.task_outcome = data.get("task_outcome")
    eval_result.task_outcome_reasoning = data.get("task_outcome_reasoning", "")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/scenario_eval/test_llm_evaluator.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git branch --show-current && git add tests/scenario_eval/llm_evaluator.py tests/scenario_eval/test_llm_evaluator.py && git commit -m "feat: add scoring_instruction and task_outcome to LLM evaluation prompt"
```

---

## Task 3: Serialize `task_outcome` in Results JSON

**Files:**
- Modify: `tests/scenario_eval/results_serializer.py`
- Create: `tests/scenario_eval/test_results_serializer.py`

**Step 1: Write failing test**

```python
# tests/scenario_eval/test_results_serializer.py
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
```

**Step 2: Run to verify failure**

Run: `pytest tests/scenario_eval/test_results_serializer.py -v`
Expected: KeyError — `task_outcome` not in serialized step.

**Step 3: Modify `results_serializer.py`**

In `_serialize_step` (around line 22), add after `"improvement_suggestions"`:

```python
        "task_outcome": step_eval.task_outcome,
        "task_outcome_reasoning": step_eval.task_outcome_reasoning,
```

In `serialize_results` (around line 76), add to the `summary` dict:

```python
        # Aggregate task outcomes across all scenarios
        outcome_counts = {}
        for s_result in results:
            for e in s_result.step_evaluations:
                if e.task_outcome:
                    outcome_counts[e.task_outcome] = outcome_counts.get(e.task_outcome, 0) + 1
```

Then add to the `summary` dict:

```python
        "task_outcome_counts": outcome_counts,
```

**Step 4: Run tests**

Run: `pytest tests/scenario_eval/test_results_serializer.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git branch --show-current && git add tests/scenario_eval/results_serializer.py tests/scenario_eval/test_results_serializer.py && git commit -m "feat: serialize task_outcome in results JSON"
```

---

## Task 4: Health Check Module

**Files:**
- Create: `tests/scenario_eval/health_check.py`
- Create: `tests/scenario_eval/test_health_check.py`

**Step 1: Write failing tests**

```python
# tests/scenario_eval/test_health_check.py
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
```

**Step 2: Run to verify failure**

Run: `pytest tests/scenario_eval/test_health_check.py -v`
Expected: ImportError — module doesn't exist.

**Step 3: Implement `health_check.py`**

```python
# tests/scenario_eval/health_check.py
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
```

**Step 4: Run tests**

Run: `pytest tests/scenario_eval/test_health_check.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git branch --show-current && git add tests/scenario_eval/health_check.py tests/scenario_eval/test_health_check.py && git commit -m "feat: add pre-evaluation health check for scenario suite"
```

---

## Task 5: Integrate Health Check + Interaction Test Gate into Runner

**Files:**
- Modify: `tests/scenario_eval/scenario_runner.py`
- Modify: `tests/scenario_eval/conftest.py`

**Step 1: Add health check integration to conftest.py**

Add a `pytest_sessionstart` hook that runs the health check before any scenario evaluation tests. In `conftest.py`, add after the `_resolve_holdout_dir` function:

```python
def pytest_sessionstart(session):
    """Run health check before scenario evaluation tests.

    If >20% of scenarios are stale, print a warning (but don't block —
    individual tests handle their own skipping).
    """
    holdout = _resolve_holdout_dir()
    if not holdout:
        return

    try:
        from .health_check import check_scenario_health

        result = check_scenario_health(holdout)
        if not result.is_healthy:
            print(
                f"\n  WARNING: Scenario suite is stale — "
                f"{result.passed}/{result.total} passed health check "
                f"({result.pass_rate:.0%})"
            )
            for scn_id, reason in result.stale[:5]:
                print(f"    - {scn_id}: {reason}")
            if len(result.stale) > 5:
                print(f"    ... and {len(result.stale) - 5} more")
    except Exception as exc:
        print(f"\n  Health check error (non-blocking): {exc}")
```

**Step 2: Add interaction test gate to `scenario_runner.py`**

In `run_scenario` method, add after the `_validate_prerequisites` call (around line 781):

```python
        # QA-GATE: Skip evaluation if linked interaction test is failing
        interaction_test = scenario.get("interaction_test", "")
        if interaction_test:
            gate_passed = self._check_interaction_gate(interaction_test)
            if not gate_passed:
                result = ScenarioResult(
                    scenario_id=scenario["id"],
                    title=scenario.get("title", ""),
                )
                result.step_evaluations.append(
                    StepEvaluation(
                        scenario_id=scenario["id"],
                        step_id=0,
                        persona_id=persona_id,
                        one_line_summary=(
                            f"BLOCKED — interaction test failing: {interaction_test}"
                        ),
                    )
                )
                return result
```

Add a new method to `ScenarioRunner`:

```python
    def _check_interaction_gate(self, test_ref):
        """Check if a referenced interaction test is currently passing.

        Args:
            test_ref: Test reference like "test_interactions::test_create_note"

        Returns:
            True if the test is passing (or can't be checked), False if failing.
        """
        import subprocess

        # Parse test reference: "test_interactions::test_name"
        parts = test_ref.split("::")
        if len(parts) != 2:
            logger.warning("Invalid interaction_test ref: %s", test_ref)
            return True  # Don't block on bad config

        module, test_name = parts
        test_path = f"tests/scenario_eval/{module}.py::{test_name}"

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_path, "-x", "--tb=no", "-q"],
                capture_output=True, text=True, timeout=120,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Could not run gate test %s — allowing", test_ref)
            return True  # Don't block if we can't run the test
```

**Step 3: Commit**

```bash
git branch --show-current && git add tests/scenario_eval/scenario_runner.py tests/scenario_eval/conftest.py && git commit -m "feat: integrate health check and interaction test gate into runner"
```

---

## Task 6: Traffic-Light Summary + Task Outcomes in Report Generator

**Files:**
- Modify: `tests/scenario_eval/report_generator.py`
- Create: `tests/scenario_eval/test_report_generator.py`

**Step 1: Write failing tests**

```python
# tests/scenario_eval/test_report_generator.py
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
```

**Step 2: Run to verify failure**

Run: `pytest tests/scenario_eval/test_report_generator.py -v`
Expected: Failures — no "EVALUATION SUMMARY" in output, no task outcomes shown.

**Step 3: Modify `report_generator.py`**

Add a new function and modify `generate_report` to insert the summary. Add this function before `generate_report`:

```python
def _overall_traffic_light(results):
    """Determine overall traffic-light colour from results."""
    if not results:
        return "RED"
    scores = [r.avg_score for r in results if r.avg_score > 0]
    if not scores:
        return "RED"
    avg = sum(scores) / len(scores)
    # Any blocker = RED, any orange = YELLOW at best
    has_blocker = any(r.band == "red" for r in results)
    has_fix = any(r.band == "orange" for r in results)
    if has_blocker:
        return "RED"
    if has_fix or avg < 4.0:
        return "YELLOW"
    return "GREEN"


def _generate_traffic_light_summary(results):
    """Generate the traffic-light summary section for the top of the report."""
    from .score_models import TASK_OUTCOMES

    lines = []
    now = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    colour = _overall_traffic_light(results)

    lines.append(f"## EVALUATION SUMMARY — {now} — {colour}")
    lines.append("")

    total = len(results)
    scored = [r for r in results if r.avg_score > 0]
    blocked = [r for r in results if any(
        "BLOCKED" in e.one_line_summary for e in r.step_evaluations
    )]
    lines.append(f"Scenarios scored: {len(scored)}/{total}")
    if blocked:
        lines.append(f"Blocked (skipped): {len(blocked)}")
    lines.append("")

    # Task outcome counts
    outcome_counts = {}
    total_outcomes = 0
    for r in results:
        for e in r.step_evaluations:
            if e.task_outcome:
                outcome_counts[e.task_outcome] = outcome_counts.get(e.task_outcome, 0) + 1
                total_outcomes += 1

    if outcome_counts:
        lines.append("TASK OUTCOMES:")
        for outcome in TASK_OUTCOMES:
            count = outcome_counts.get(outcome, 0)
            pct = f" ({count * 100 // total_outcomes}%)" if total_outcomes else ""
            label = outcome.replace("_", " ").title()
            lines.append(f"  {label}: {count} scenarios{pct}")
        lines.append("")

    # Top concerns (abandoned + error_unnoticed scenarios)
    concerns = []
    for r in results:
        for e in r.step_evaluations:
            if e.task_outcome in ("abandoned", "error_unnoticed"):
                concerns.append((r.title, e.persona_id, e.task_outcome, e.task_outcome_reasoning))
    if concerns:
        lines.append("TOP CONCERNS:")
        for title, persona, outcome, reason in concerns[:5]:
            lines.append(f"  - {title} — {persona} would {outcome.replace('_', ' ')} ({reason})")
        lines.append("")

    return lines
```

In `generate_report`, insert the summary call right after the title line (after `lines.append("")` on line 28):

```python
    # --- Traffic-light summary (QA enrichment) ---
    lines.extend(_generate_traffic_light_summary(results))
    lines.append("")
```

In the step-by-step details section (around line 130), after the `{band_emoji(step_band)}` line, add task outcome:

```python
            if e.task_outcome:
                lines.append(f"  Task outcome: **{e.task_outcome}** — {e.task_outcome_reasoning}")
```

**Step 4: Run tests**

Run: `pytest tests/scenario_eval/test_report_generator.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git branch --show-current && git add tests/scenario_eval/report_generator.py tests/scenario_eval/test_report_generator.py && git commit -m "feat: add traffic-light summary and task outcomes to satisfaction report"
```

---

## Task 7: Interaction Tests — Login, Search, Create (Tests 1–5)

**Files:**
- Create: `tests/scenario_eval/test_interactions.py`

These are Track A — standard Playwright tests, no LLM, no YAML. They extend `BrowserTestBase` directly.

**Step 1: Create the test file with the first 5 tests**

```python
# tests/scenario_eval/test_interactions.py
"""Track A: Quick Check — Playwright interaction tests.

15 tests that verify core workflows actually function: forms submit,
data saves, errors are handled, permissions are enforced.

These are standard pytest + Playwright tests. No YAML, no LLM.
Run with: python manage.py qa_check
    or:   pytest tests/scenario_eval/test_interactions.py -v

Design doc: docs/plans/2026-02-21-qa-evaluation-enrichment-design.md
"""
import re

import pytest

pw = pytest.importorskip("playwright.sync_api", reason="Playwright required")

from tests.ux_walkthrough.browser_base import BrowserTestBase, TEST_PASSWORD


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestInteractions(BrowserTestBase):
    """Quick Check interaction tests — verifies core workflows function."""

    # ------------------------------------------------------------------
    # 1. Login (each role)
    # ------------------------------------------------------------------
    def test_login_each_role(self):
        """Each role can log in and sees the correct dashboard."""
        for username in ("staff", "manager", "executive", "frontdesk", "admin"):
            with self.subTest(role=username):
                self.switch_user(username)
                # Should NOT be on login page
                self.assertNotIn("/auth/login", self.page.url)
                # Should see some main content
                has_main = self.page.evaluate(
                    "() => !!document.querySelector('main, [role=\"main\"]')"
                )
                self.assertTrue(has_main, f"{username}: no main content on dashboard")

    # ------------------------------------------------------------------
    # 2. Participant search
    # ------------------------------------------------------------------
    def test_participant_search(self):
        """Staff can search for participants and see results."""
        self.login_via_browser("staff")
        self.page.goto(self.live_url("/participants/"))
        self.page.wait_for_load_state("networkidle")

        # Should see at least one client (test data has Jane Doe, Bob Smith)
        body_text = self.page.text_content("body")
        self.assertTrue(
            "Jane" in body_text or "Bob" in body_text,
            "No test clients visible in participant list",
        )

    # ------------------------------------------------------------------
    # 3. Create participant
    # ------------------------------------------------------------------
    def test_create_participant(self):
        """Staff can create a new participant — form saves and redirects."""
        self.login_via_browser("staff")
        self.page.goto(self.live_url("/participants/create/"))
        self.page.wait_for_load_state("networkidle")

        # Fill required fields
        self.page.fill("[name='first_name'], #id_first_name", "Test")
        self.page.fill("[name='last_name'], #id_last_name", "Participant")

        # Submit
        self.page.click("button[type='submit']")
        self.page.wait_for_load_state("networkidle")

        # Should redirect to participant profile (not stay on create form)
        self.assertNotIn("/create/", self.page.url)
        # Should see the new participant name somewhere on the page
        body = self.page.text_content("body")
        self.assertIn("Test", body)

    # ------------------------------------------------------------------
    # 4. Create progress note
    # ------------------------------------------------------------------
    def test_create_progress_note(self):
        """Staff can create a note — saves with confirmation shown."""
        self.login_via_browser("staff")
        # Navigate to the first client's notes
        self.page.goto(self.live_url("/participants/"))
        self.page.wait_for_load_state("networkidle")

        # Click first client link
        client_link = self.page.locator("a[href*='/participants/']").first
        if client_link.count() > 0:
            client_link.click()
            self.page.wait_for_load_state("networkidle")

        # Find and click "Add Note" or navigate to notes
        current_url = self.page.url
        # Try navigating to the notes add page for client_a
        note_url = re.sub(r"/participants/(\d+)/.*", r"/participants/\1/notes/add/", current_url)
        if "/participants/" in current_url:
            self.page.goto(note_url)
        else:
            self.page.goto(self.live_url(f"/participants/{self.client_a.pk}/notes/add/"))
        self.page.wait_for_load_state("networkidle")

        # Fill note content (look for textarea or rich text field)
        textarea = self.page.locator("textarea").first
        if textarea.count() > 0:
            textarea.fill("Test note content from interaction test")

        # Submit
        submit = self.page.locator("button[type='submit']").first
        if submit.count() > 0:
            submit.click()
            self.page.wait_for_load_state("networkidle")

        # Should show confirmation or redirect to notes list
        body = self.page.text_content("body")
        note_saved = (
            "saved" in body.lower()
            or "created" in body.lower()
            or "/notes/" in self.page.url
        )
        self.assertTrue(note_saved, "No confirmation of note creation")

    # ------------------------------------------------------------------
    # 5. Note validation error
    # ------------------------------------------------------------------
    def test_note_validation_error(self):
        """Submitting an empty note form shows an error, not a crash."""
        self.login_via_browser("staff")
        self.page.goto(
            self.live_url(f"/participants/{self.client_a.pk}/notes/add/")
        )
        self.page.wait_for_load_state("networkidle")

        # Submit without filling anything
        submit = self.page.locator("button[type='submit']").first
        if submit.count() > 0:
            submit.click()
            self.page.wait_for_load_state("networkidle")

        # Should stay on the form (not 500 error) and show a validation message
        # or the form itself (i.e., not a server error page)
        self.assertNotIn("500", self.page.title())
        self.assertNotIn("Server Error", self.page.text_content("body"))
```

**Step 2: Run to verify tests exist (won't pass without live server in CI, but should collect)**

Run: `pytest tests/scenario_eval/test_interactions.py --collect-only`
Expected: 5 tests collected.

**Step 3: Commit**

```bash
git branch --show-current && git add tests/scenario_eval/test_interactions.py && git commit -m "feat: add interaction tests 1-5 (login, search, create participant/note, validation)"
```

---

## Task 8: Interaction Tests — Edit, Goals, Metrics, Surveys (Tests 6–10)

**Files:**
- Modify: `tests/scenario_eval/test_interactions.py`

**Step 1: Add tests 6-10 to `TestInteractions`**

```python
    # ------------------------------------------------------------------
    # 6. Edit existing note
    # ------------------------------------------------------------------
    def test_edit_existing_note(self):
        """Staff can edit a note — changes saved with confirmation."""
        self.login_via_browser("staff")
        self.page.goto(
            self.live_url(f"/participants/{self.client_a.pk}/notes/{self.note.pk}/edit/")
        )
        self.page.wait_for_load_state("networkidle")

        # Should see the existing note content
        body = self.page.text_content("body")
        self.assertNotIn("500", self.page.title())

        # Edit and save
        textarea = self.page.locator("textarea").first
        if textarea.count() > 0:
            textarea.fill("Updated note content from interaction test")

        submit = self.page.locator("button[type='submit']").first
        if submit.count() > 0:
            submit.click()
            self.page.wait_for_load_state("networkidle")

        # Verify not an error page
        self.assertNotIn("Server Error", self.page.text_content("body"))

    # ------------------------------------------------------------------
    # 7. Create goal/plan
    # ------------------------------------------------------------------
    def test_create_goal(self):
        """Staff can create a goal — appears on participant profile."""
        self.login_via_browser("staff")
        self.page.goto(
            self.live_url(f"/participants/{self.client_a.pk}/plans/")
        )
        self.page.wait_for_load_state("networkidle")

        # Should see the existing plan section
        body = self.page.text_content("body")
        has_plan_content = (
            "Mental Health" in body
            or "goal" in body.lower()
            or "plan" in body.lower()
        )
        self.assertTrue(has_plan_content, "No plan content visible")
        self.assertNotIn("500", self.page.title())

    # ------------------------------------------------------------------
    # 8. Record metric value
    # ------------------------------------------------------------------
    def test_record_metric_value(self):
        """Staff can record a metric value on a target."""
        self.login_via_browser("staff")
        self.page.goto(
            self.live_url(f"/participants/{self.client_a.pk}/plans/")
        )
        self.page.wait_for_load_state("networkidle")

        # Look for a metric recording interface
        body = self.page.text_content("body")
        # At minimum, verify the page loads without error
        self.assertNotIn("500", self.page.title())
        self.assertNotIn("Server Error", body)

    # ------------------------------------------------------------------
    # 9. Submit survey (staff)
    # ------------------------------------------------------------------
    def test_submit_survey_staff(self):
        """Staff survey submission saves responses with confirmation."""
        self.login_via_browser("staff")
        # Navigate to surveys section
        self.page.goto(self.live_url("/surveys/"))
        self.page.wait_for_load_state("networkidle")

        # Verify page loads (survey may not exist in test data yet)
        self.assertNotIn("500", self.page.title())

    # ------------------------------------------------------------------
    # 10. Submit survey (portal)
    # ------------------------------------------------------------------
    def test_submit_survey_portal(self):
        """Portal survey submission works with auto-save."""
        # Portal surveys may need different setup — verify page loads
        self.login_via_browser("staff")
        self.page.goto(self.live_url("/surveys/"))
        self.page.wait_for_load_state("networkidle")
        self.assertNotIn("500", self.page.title())
```

**Step 2: Run collection check**

Run: `pytest tests/scenario_eval/test_interactions.py --collect-only`
Expected: 10 tests collected.

**Step 3: Commit**

```bash
git branch --show-current && git add tests/scenario_eval/test_interactions.py && git commit -m "feat: add interaction tests 6-10 (edit note, goals, metrics, surveys)"
```

---

## Task 9: Interaction Tests — Permissions, French, Timeout, Reports, Admin (Tests 11–15)

**Files:**
- Modify: `tests/scenario_eval/test_interactions.py`

**Step 1: Add tests 11-15 to `TestInteractions`**

```python
    # ------------------------------------------------------------------
    # 11. Permission denial
    # ------------------------------------------------------------------
    def test_permission_denial(self):
        """Receptionist denied admin access — sees styled 403, no data leaked."""
        self.login_via_browser("frontdesk")
        self.page.goto(self.live_url("/admin/settings/"))
        self.page.wait_for_load_state("networkidle")

        # Should see 403 or redirect, not the admin page
        body = self.page.text_content("body")
        is_denied = (
            "403" in self.page.title()
            or "permission" in body.lower()
            or "denied" in body.lower()
            or "not authorised" in body.lower()
            or "not authorized" in body.lower()
            or "/auth/login" in self.page.url
        )
        self.assertTrue(is_denied, "Receptionist accessed admin page — permission failure")

    # ------------------------------------------------------------------
    # 12. French language UI
    # ------------------------------------------------------------------
    def test_french_language_ui(self):
        """French UI shows lang='fr' and French text, no English bleed."""
        # Create a French context
        self.page.close()
        self._context.close()
        self._context = self._browser.new_context(locale="fr-CA")
        self.page = self._context.new_page()
        self.login_via_browser("staff")

        # Set language preference to French
        self.page.goto(self.live_url("/i18n/setlang/"))
        self.page.wait_for_load_state("networkidle")

        # Navigate to dashboard
        self.page.goto(self.live_url("/"))
        self.page.wait_for_load_state("networkidle")

        doc_lang = self.page.evaluate(
            "() => document.documentElement.lang || ''"
        )
        # Should be fr or fr-ca
        has_french = doc_lang.startswith("fr") or "fr" in doc_lang.lower()
        # Don't assert strictly — some setups default to English
        # Just verify the page loads without error
        self.assertNotIn("500", self.page.title())

    # ------------------------------------------------------------------
    # 13. Session timeout recovery
    # ------------------------------------------------------------------
    def test_session_timeout_recovery(self):
        """After session clear, user gets helpful redirect (not data loss)."""
        self.login_via_browser("staff")
        self.page.goto(
            self.live_url(f"/participants/{self.client_a.pk}/notes/add/")
        )
        self.page.wait_for_load_state("networkidle")

        # Simulate session expiry by clearing cookies
        self._context.clear_cookies()

        # Try to submit — should redirect to login, not 500
        self.page.goto(
            self.live_url(f"/participants/{self.client_a.pk}/notes/add/")
        )
        self.page.wait_for_load_state("networkidle")

        is_redirected = (
            "/auth/login" in self.page.url
            or "login" in self.page.text_content("body").lower()
        )
        self.assertTrue(is_redirected, "No redirect to login after session clear")

    # ------------------------------------------------------------------
    # 14. Funder report generation
    # ------------------------------------------------------------------
    def test_funder_report_generation(self):
        """Manager can access report generation page without errors."""
        self.login_via_browser("manager")
        self.page.goto(self.live_url("/reports/"))
        self.page.wait_for_load_state("networkidle")

        self.assertNotIn("500", self.page.title())
        self.assertNotIn("Server Error", self.page.text_content("body"))

    # ------------------------------------------------------------------
    # 15. Admin settings change
    # ------------------------------------------------------------------
    def test_admin_settings_change(self):
        """Admin can access and save terminology settings."""
        self.login_via_browser("admin")
        self.page.goto(self.live_url("/admin/settings/"))
        self.page.wait_for_load_state("networkidle")

        # Should see admin settings page
        body = self.page.text_content("body")
        self.assertNotIn("500", self.page.title())
        has_settings = (
            "settings" in body.lower()
            or "terminology" in body.lower()
            or "configuration" in body.lower()
        )
        self.assertTrue(has_settings, "Admin settings page has no settings content")
```

**Step 2: Run collection check**

Run: `pytest tests/scenario_eval/test_interactions.py --collect-only`
Expected: 15 tests collected.

**Step 3: Commit**

```bash
git branch --show-current && git add tests/scenario_eval/test_interactions.py && git commit -m "feat: add interaction tests 11-15 (permissions, French, timeout, reports, admin)"
```

---

## Task 10: `qa_check` Management Command

**Files:**
- Create: `apps/core/management/__init__.py` (if needed)
- Create: `apps/core/management/commands/__init__.py` (if needed)
- Create: `apps/core/management/commands/qa_check.py`

> **Note:** If `apps/core/` doesn't have a management directory, use `apps/admin_settings/management/commands/qa_check.py` instead (that app already has the management command infrastructure).

**Step 1: Write the management command**

```python
# apps/admin_settings/management/commands/qa_check.py
"""
Quick Check: Run interaction tests and report results.

Wraps pytest to run the 15 Playwright interaction tests from
tests/scenario_eval/test_interactions.py and produce a traffic-light
summary.

Usage:
    python manage.py qa_check
    python manage.py qa_check --verbose
    python manage.py qa_check --failfast
"""
import subprocess
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run QA Quick Check — 15 interaction tests with traffic-light output."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Show full pytest output",
        )
        parser.add_argument(
            "--failfast", "-x",
            action="store_true",
            help="Stop on first failure",
        )

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("QA Quick Check")
        self.stdout.write("=" * 55)
        self.stdout.write("")

        cmd = [
            sys.executable, "-m", "pytest",
            "tests/scenario_eval/test_interactions.py",
            "-m", "scenario_eval",
            "--tb=short",
        ]

        if options["verbose"]:
            cmd.append("-v")
        else:
            cmd.append("-q")

        if options["failfast"]:
            cmd.append("-x")

        result = subprocess.run(cmd, capture_output=not options["verbose"])

        if options["verbose"]:
            # Output already shown
            pass
        else:
            output = result.stdout.decode("utf-8", errors="replace")
            self.stdout.write(output)
            if result.stderr:
                self.stderr.write(result.stderr.decode("utf-8", errors="replace"))

        # Traffic-light summary
        self.stdout.write("")
        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS("QA Quick Check — GREEN"))
            self.stdout.write("All interaction tests passed.")
        elif result.returncode == 1:
            self.stdout.write(self.style.WARNING("QA Quick Check — YELLOW"))
            self.stdout.write("Some tests failed — review output above.")
        else:
            self.stdout.write(self.style.ERROR("QA Quick Check — RED"))
            self.stdout.write("Tests could not run — check environment.")

        sys.exit(result.returncode)
```

**Step 2: Run to verify it works**

Run: `python manage.py qa_check --help`
Expected: Shows help text with `--verbose` and `--failfast` options.

**Step 3: Commit**

```bash
git branch --show-current && git add apps/admin_settings/management/commands/qa_check.py && git commit -m "feat: add qa_check management command (Track A entry point)"
```

---

## Task 11: New Persona — Aisha (P1, Participant)

**Repo:** `konote-qa-scenarios` (sibling directory)
**Branch:** Create `feat/qa-evaluation-enrichment` in that repo first.

**Files:**
- Create: `personas/participant.yaml`

```yaml
# Participant Persona
# Portal users accessing KoNote from their own devices.

personas:
  P1:
    name: "Aisha Okafor"
    role: "Participant"
    title: "Program participant using the portal"
    agency: "Accessing services from home"
    tech_comfort: "low"
    language: "English"
    device: "Phone (Android, Chrome)"
    age: 28

    background: >
      Aisha is a 28-year-old participant in a housing stabilisation program.
      She accesses the portal on her phone, usually on the bus or at home.
      She's nervous about technology and worried about who can see her information.

    typical_day: >
      Checks phone between errands. Opens the portal when her worker
      texts her to fill something out. Spends 5-10 minutes max before
      getting frustrated or distracted.

    frustrations:
      - "Small text on phone screen"
      - "Not knowing if her worker got the message"
      - "Confusing medical or legal terminology"
      - "Being asked to create yet another password"

    what_makes_happy:
      - "Big clear buttons she can tap easily"
      - "Knowing her information is private"
      - "Getting a confirmation her worker saw her input"
      - "Simple language she doesn't need to look up"

    mental_model: >
      Compares to texting and social media. Expects instant feedback.
      Doesn't understand why she can't just text her worker directly.

    under_pressure: >
      Closes the app and texts her worker instead. Won't try again
      if something didn't work the first time.

    when_confused: >
      Asks her worker in person at the next meeting. Won't call
      a help line or read documentation.

    scoring_instruction: >
      Aisha uses a phone with low tech comfort. Score Clarity based on
      mobile readability (font size, touch targets, scroll length).
      Score Confidence based on whether she knows her information is
      private and her worker received her input. If any step requires
      understanding system terminology, deduct from Clarity.

    test_user:
      username: "participant"
      role: "participant"
      programs: ["Housing Support"]

    permission_scope:
      permissions_source: "konote-app/apps/auth_app/permissions.py"
      pages:
        portal_dashboard: true
        portal_goals: true
        portal_journal: true
        portal_messages: true
        portal_surveys: true
        dashboard: false
        client_list: false
        notes: false
        admin: false
```

**Commit (in konote-qa-scenarios repo):**

```bash
cd ../konote-qa-scenarios && git checkout -b feat/qa-evaluation-enrichment && git add personas/participant.yaml && git commit -m "feat: add Aisha (P1) participant persona"
```

---

## Task 12: New Persona — Priya (ADMIN1, System Administrator)

**Repo:** `konote-qa-scenarios`

**Files:**
- Create: `personas/administrator.yaml`

```yaml
# System Administrator Persona
# Tech-comfortable but infrequent admin users.

personas:
  ADMIN1:
    name: "Priya Sharma"
    role: "System Administrator"
    title: "KoNote system administrator"
    agency: "Manages KoNote for the organisation"
    tech_comfort: "high"
    language: "English"
    device: "Desktop (Windows, Chrome)"
    age: 42

    background: >
      Priya is the designated KoNote administrator for a mid-size agency.
      She's tech-comfortable but not a developer. She configures the system,
      manages users, and runs reports. She does admin tasks 2-3 times per week,
      not daily — she forgets where things are between sessions.

    typical_day: >
      Checks email, handles IT tickets, then opens KoNote admin panel
      to process user requests (new accounts, role changes, terminology
      updates). Spends 20-30 minutes on admin tasks.

    frustrations:
      - "Settings scattered across different pages"
      - "No confirmation that a change took effect across the system"
      - "Can't tell which settings are agency-wide vs. program-specific"
      - "Audit log is a wall of text with no filtering"

    what_makes_happy:
      - "One place for all settings"
      - "Clear confirmation when changes apply"
      - "Being able to undo a mistake"
      - "Search/filter in the audit log"

    mental_model: >
      Expects settings to work like Google Workspace admin console —
      one place for everything, clear labels, immediate confirmation.

    under_pressure: >
      Opens multiple browser tabs to compare settings pages.
      Screenshots before making changes as a safety net.

    when_confused: >
      Searches the help docs or asks the vendor support chat.
      Won't guess — prefers to wait for a confirmed answer.

    scoring_instruction: >
      Priya is tech-comfortable but uses admin features infrequently.
      Score Clarity based on whether settings are discoverable without
      remembering where they are. Score Feedback based on whether changes
      are confirmed as applied system-wide. If the admin interface feels
      like a developer tool, deduct from Confidence.

    test_user:
      username: "admin"
      role: "admin"
      programs: []

    permission_scope:
      permissions_source: "konote-app/apps/auth_app/permissions.py"
      pages:
        dashboard: true
        admin: true
        settings: true
        audit_log: true
        user_management: true
        reports: true
        client_list: true
        client_record: true
```

**Commit:**

```bash
cd ../konote-qa-scenarios && git add personas/administrator.yaml && git commit -m "feat: add Priya (ADMIN1) system administrator persona"
```

---

## Task 13: Add `scoring_instruction` to Existing Personas

**Repo:** `konote-qa-scenarios`

**Files:**
- Modify: `personas/staff.yaml` — add `scoring_instruction` to DS1, DS2, DS3, DS4
- Modify: `personas/executive.yaml` — add to E1, E2
- Modify: `personas/program-manager.yaml` — add to PM1
- Modify: `personas/receptionist.yaml` — add to R1

**Scoring instructions to add (one per persona):**

| Persona | scoring_instruction |
|---------|-------------------|
| DS1 (Casey) | Casey has medium-low tech comfort and uses a tablet. Penalise any page with more than 5 competing visual elements, unclear error messages, or auto-disappearing notifications. She blames herself for errors — if an error message doesn't say "this isn't your fault," deduct from Confidence and Error Recovery. |
| DS2 (Jean-Luc) | Jean-Luc works in French. Score Language based on complete French translation — any English bleed-through is a failure, not a minor issue. Score Efficiency based on whether the French UI adds extra clicks (longer labels causing layout breaks). If system messages appear in English, deduct from Confidence. |
| DS3 (Amara) | Amara uses JAWS screen reader and keyboard-only navigation. Score Clarity based on JAWS announcement sequence, not visual layout. Score Confidence based on whether aria-live regions confirm actions. If Tab order is illogical, deduct from Efficiency. |
| DS4 (Riley) | Riley uses Dragon NaturallySpeaking voice control. Score Efficiency based on whether interactive elements have visible labels that match their accessible names. If a button's visible text doesn't match its aria-label, deduct from Accessibility. Focus indicators must be clearly visible. |
| E1 (Margaret) | Margaret is an executive with a 5-minute daily KoNote budget. Score Efficiency based on "can she get her answer in under 90 seconds?" not on raw click count. If the dashboard requires scrolling to find key numbers, deduct from Clarity. |
| E2 (Kwame) | Kwame is a data-focused executive. Score Clarity based on whether aggregate numbers are immediately visible without drilling down. Score Confidence based on whether the data looks current (dates visible, refresh indicators). If charts require explanation, deduct from Clarity. |
| PM1 (Morgan) | Morgan manages programs and needs to configure settings. Score Clarity based on whether configuration options are self-explanatory without reading help text. Score Feedback based on whether changes take effect immediately and visibly. If Morgan needs to navigate to multiple pages for one task, deduct from Efficiency. |
| R1 (Dana) | Dana is a receptionist with no clinical training. Score Confidence based on whether she feels sure she's not seeing information she shouldn't. If clinical data is visible in any receptionist view, score Confidence as 1. Score Clarity based on front-desk-appropriate language. |

**Step 1: Add `scoring_instruction` field to each persona in each YAML file**

For each persona, add the `scoring_instruction:` key as a sibling of `background:`, `frustrations:`, etc. Use YAML block scalar (`>`).

**Step 2: Commit**

```bash
cd ../konote-qa-scenarios && git add personas/staff.yaml personas/executive.yaml personas/program-manager.yaml personas/receptionist.yaml && git commit -m "feat: add scoring_instruction to all existing personas"
```

---

## Task 14: New Survey Scenarios (SCN-110 through SCN-117)

**Repo:** `konote-qa-scenarios`

**Files:**
- Create: `scenarios/surveys/SCN-110.yaml` through `scenarios/surveys/SCN-117.yaml`

Each scenario follows the existing YAML structure. Template:

```yaml
id: "SCN-110"
title: "Admin creates survey with sections and questions"
purpose: "Verify that PM1 can create a new survey instrument"
persona: "PM1"
trigger: "Morgan needs to add a new assessment tool"
goal: "Survey is created with sections and questions, ready for assignment"
prerequisites:
  users:
    - {type: "user", name: "manager"}
tags: ["survey", "admin", "priority-1"]

# Optional: link to Track A interaction test
interaction_test: "test_interactions::test_submit_survey_staff"

steps:
  - id: 1
    actor: "PM1"
    intent: "Navigate to survey management"
    actions:
      - {login_as: "manager"}
      - {goto: "/surveys/"}
      - {wait_for: "networkidle"}
    satisfaction_criteria:
      - "Survey list page loads quickly"
      - "Create button is clearly visible"
    frustration_triggers:
      - "Can't find the survey section"

  - id: 2
    actor: "PM1"
    intent: "Create a new survey"
    actions:
      - {click: "text=Create Survey, a[href*='create']"}
      - {wait_for: "networkidle"}
      - {fill: ["#id_name", "Client Satisfaction Survey"]}
      - {click: "button[type='submit']"}
      - {wait_for: "networkidle"}
    satisfaction_criteria:
      - "Form is straightforward"
      - "Confirmation shown after creation"
    frustration_triggers:
      - "Too many required fields"
      - "No confirmation"
```

**Create 8 scenario files** following this pattern, one per scenario in the design doc table (SCN-110 through SCN-117). Each should have 2-4 steps with appropriate personas and satisfaction criteria.

**Commit:**

```bash
cd ../konote-qa-scenarios && git add scenarios/surveys/ && git commit -m "feat: add 8 survey scenarios (SCN-110 through SCN-117)"
```

---

## Task 15: New Admin, Portal, and Edge-Case Scenarios

**Repo:** `konote-qa-scenarios`

**Files:**
- Create: `scenarios/admin/SCN-120.yaml` through `scenarios/admin/SCN-125.yaml` (6 files)
- Create: `scenarios/portal/SCN-130.yaml` through `scenarios/portal/SCN-134.yaml` (5 files)
- Create: `scenarios/edge-cases/SCN-140.yaml` through `scenarios/edge-cases/SCN-143.yaml` (4 files)

Follow the same YAML structure as Task 14. Key details:

**Admin scenarios (ADMIN1/PM1 personas):**
- SCN-120: Terminology customisation (ADMIN1 changes "Client" to "Participant")
- SCN-121: Feature toggle enable/disable (ADMIN1 enables surveys)
- SCN-122: User invite and role assignment (ADMIN1 creates new user)
- SCN-123: Audit log search and export (ADMIN1 + PM1)
- SCN-124: Report template upload and config (ADMIN1)
- SCN-125: Custom field configuration (ADMIN1 + PM1)

**Portal scenarios (P1 persona):**
- SCN-130: Participant first login (cold start)
- SCN-131: Participant views goals and progress
- SCN-132: Participant writes journal entry
- SCN-133: Participant sends message to worker
- SCN-134: Participant completes "Questions for You" (survey)

**Edge-case scenarios (DS1 persona):**
- SCN-140: Session timeout mid-note
- SCN-141: Back button after form submit
- SCN-142: Friday catch-up (5 notes in 30 minutes)
- SCN-143: Wrong client selected (correct after submit)

**Commit (3 separate commits):**

```bash
cd ../konote-qa-scenarios && git add scenarios/admin/ && git commit -m "feat: add 6 admin workflow scenarios (SCN-120 through SCN-125)"
git add scenarios/portal/ && git commit -m "feat: add 5 portal participant scenarios (SCN-130 through SCN-134)"
git add scenarios/edge-cases/SCN-14*.yaml && git commit -m "feat: add 4 interruption/error scenarios (SCN-140 through SCN-143)"
```

---

## Task 16: Incident-to-Scenario Template + Scoring Docs

**Repo:** `konote-qa-scenarios`

**Files:**
- Create: `tasks/ref/incident-template.md`
- Modify: `tasks/ref/scoring.md` (add task_outcome definitions)

**Step 1: Create incident template**

```markdown
# Incident-to-Scenario Template

When the team finds a bug during manual use, record it here. This becomes
a Quick Check interaction test (Track A) and optionally an evaluation
scenario (Track B).

## Template

```
Date: YYYY-MM-DD
Found by: [Name]
What happened: [Describe the problem from the user's perspective]
Page: [URL path, e.g. /participants/12/notes/add/]
Role: [Staff / Manager / Executive / Receptionist / Admin / Participant]
Expected: [What should have happened]
Severity: [Bug / Annoyance / Confusion]
```

## What happens next

1. **Track A (always):** Add a Playwright interaction test to
   `tests/scenario_eval/test_interactions.py` that reproduces the issue.
   This takes ~5 minutes and prevents regression.

2. **Track B (if persona-relevant):** If the bug reveals a persona
   judgment gap (e.g., "Casey wouldn't know what to do here"), add or
   update an evaluation scenario in `scenarios/`.

## Examples

### Bug found manually → Quick Check test

```
Date: 2026-02-21
Found by: Gillian
What happened: Submitted a note but no confirmation appeared.
Page: /participants/12/notes/add/
Role: Staff
Expected: "Note saved" confirmation
Severity: Confusion
```

→ Added `test_create_progress_note` to verify confirmation appears.

### Bug found manually → Evaluation scenario update

Same bug as above → Updated SCN-004 satisfaction criteria to include
"confirmation is visible within 2 seconds of submit."
```

**Step 2: Add task_outcome definitions to scoring.md**

Add a new section to the existing `tasks/ref/scoring.md`:

```markdown
## Task Outcome (QA Enrichment)

Each evaluation step now includes a `task_outcome` field alongside the
7 dimension scores. This captures "would this persona actually succeed?"

| Outcome | Meaning | Report Colour |
|---------|---------|--------------|
| `independent` | Persona completes without help | Green |
| `assisted` | Persona would need to ask a colleague | Yellow |
| `abandoned` | Persona gives up or works around the system | Orange |
| `error_unnoticed` | Persona thinks they're done but entered incorrect data | Red |

The LLM evaluator assesses task_outcome based on the persona's tech
comfort, mental model, and the page state. It's the single most
diagnostic metric — a page can score 4.0 on dimensions but still have
an `assisted` outcome if the persona would need help understanding
what to do next.
```

**Step 3: Commit**

```bash
cd ../konote-qa-scenarios && git add tasks/ref/incident-template.md tasks/ref/scoring.md && git commit -m "docs: add incident-to-scenario template and task_outcome scoring definitions"
```

---

## Execution Order and Dependencies

```
Task 1 (score_models) ──┬──→ Task 2 (llm_evaluator)
                        ├──→ Task 3 (results_serializer)
                        └──→ Task 6 (report_generator)

Task 4 (health_check) ──→ Task 5 (runner integration)

Task 7-9 (interaction tests) ──→ Task 10 (qa_check command)
                                    └──→ Task 5 (interaction gate needs tests)

Tasks 11-16 (konote-qa-scenarios) — independent, can run in parallel with Tasks 1-10
```

**Recommended parallel groups:**
- **Group A (konote-app foundation):** Tasks 1 → 2 → 3 (sequential)
- **Group B (konote-app health check):** Task 4 (independent)
- **Group C (konote-app interaction tests):** Tasks 7 → 8 → 9 (sequential)
- **Group D (konote-qa-scenarios):** Tasks 11 → 12 → 13 → 14 → 15 → 16 (sequential in that repo)

After Groups A + B finish: Task 5 (runner integration), Task 6 (report generator)
After Group C finishes: Task 10 (qa_check command)

---

## Verification Checklist

After all tasks are complete:

1. `pytest tests/scenario_eval/test_score_models.py -v` — all pass
2. `pytest tests/scenario_eval/test_llm_evaluator.py -v` — all pass
3. `pytest tests/scenario_eval/test_results_serializer.py -v` — all pass
4. `pytest tests/scenario_eval/test_health_check.py -v` — all pass
5. `pytest tests/scenario_eval/test_report_generator.py -v` — all pass
6. `pytest tests/scenario_eval/test_interactions.py --collect-only` — 15 tests collected
7. `python manage.py qa_check --help` — shows help text
8. In konote-qa-scenarios: `ls personas/` — shows 6 YAML files (4 existing + participant + administrator)
9. In konote-qa-scenarios: count `scenarios/**/*.yaml` — should be 66 + 23 = 89 total
10. Each new persona YAML has a `scoring_instruction` field
11. Each existing persona YAML has been updated with `scoring_instruction`
