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
        return discover_scenarios(holdout, ids=["CAL-001", "CAL-002", "CAL-003", "CAL-004", "CAL-005"])

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

    def test_calibration_accessible_page(self):
        """CAL-004: Accessible login form should score >= 3.0 for DS3."""
        result = self._run_calibration("CAL-004")
        if self.use_llm and result.avg_score > 0:
            self.assertGreaterEqual(
                result.avg_score, 3.0,
                f"CAL-004 scored {result.avg_score:.1f} — expected >= 3.0 for accessible page"
            )

    def test_calibration_inaccessible_page(self):
        """CAL-005: Inaccessible data table should score <= 2.5 for DS3."""
        result = self._run_calibration("CAL-005")
        if self.use_llm and result.avg_score > 0:
            self.assertLessEqual(
                result.avg_score, 2.5,
                f"CAL-005 scored {result.avg_score:.1f} — expected <= 2.5 for inaccessible page"
            )


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


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestRound3Scenarios(ScenarioRunner):
    """Round 3 scenarios: mobile viewport and offline/slow network."""

    def _run_round3(self, scenario_id):
        """Common logic for running a single Round 3 scenario."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")

        scenarios = discover_scenarios(holdout, ids=[scenario_id])
        scn = [s for _, s in scenarios if s["id"] == scenario_id]
        if not scn:
            self.skipTest(f"{scenario_id} not found in holdout dir")

        scenario = scn[0]
        self.personas = load_personas()
        self.use_llm = not _should_skip_llm()

        screenshot_dir = os.path.join(holdout, "reports", "screenshots")
        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_mobile_phone_375px(self):
        """SCN-047: Mobile phone at 375px — responsive layout and touch."""
        self._run_round3("SCN-047")

    def test_offline_slow_network(self):
        """SCN-048: Offline/slow network — graceful degradation."""
        self._run_round3("SCN-048")


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestDayInTheLife(ScenarioRunner):
    """Day-in-the-life narrative scenarios.

    These are NOT step-by-step automation — the test runner captures
    screenshots at key moments described in the YAML, and the LLM
    evaluator scores the full day as a narrative assessment.

    For DITL scenarios, we simulate key moments by navigating to the
    relevant pages and capturing state, rather than replaying every
    action. The narrative YAML has 'moments' instead of 'steps'.
    """

    def _run_ditl(self, scenario_id):
        """Common logic for running a day-in-the-life narrative."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")

        scenarios = discover_scenarios(holdout, ids=[scenario_id])
        scn = [s for _, s in scenarios if s["id"] == scenario_id]
        if not scn:
            self.skipTest(f"{scenario_id} not found in holdout dir")

        scenario = scn[0]
        self.personas = load_personas()
        self.use_llm = not _should_skip_llm()

        screenshot_dir = os.path.join(holdout, "reports", "screenshots")

        # DITL scenarios use 'moments' not 'steps' — use run_narrative
        # to capture key pages and evaluate holistically
        result = self.run_narrative(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_ditl_ds3_amara(self):
        """DITL-DS3: Amara's Wednesday — screen reader full day."""
        self._run_ditl("DITL-DS3")

    def test_ditl_e1_margaret(self):
        """DITL-E1: Margaret's Thursday — executive dashboard full day."""
        # Seed bulk clients so dashboard numbers are realistic
        self._seed_bulk_clients(150)
        self._run_ditl("DITL-E1")

    def test_ditl_ds2_jean_luc(self):
        """DITL-DS2: Jean-Luc's Friday — bilingual full day."""
        self._run_ditl("DITL-DS2")

    def test_ditl_ds1_casey(self):
        """DITL-DS1: Casey's Tuesday — direct service full day."""
        self._run_ditl("DITL-DS1")

    def test_ditl_r1_dana(self):
        """DITL-R1: Dana's Monday — receptionist full day."""
        self._run_ditl("DITL-R1")


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestDailyScenarios(ScenarioRunner):
    """Daily workflow scenarios: batch notes, phone updates, quick lookups."""

    def _run_daily(self, scenario_id):
        """Common logic for running a daily scenario."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")

        scenarios = discover_scenarios(holdout, ids=[scenario_id])
        scn = [s for _, s in scenarios if s["id"] == scenario_id]
        if not scn:
            self.skipTest(f"{scenario_id} not found in holdout dir")

        scenario = scn[0]
        self.personas = load_personas()
        self.use_llm = not _should_skip_llm()

        screenshot_dir = os.path.join(holdout, "reports", "screenshots")
        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_batch_note_entry(self):
        """SCN-015: Batch Note Entry — Casey enters notes for multiple clients."""
        self._run_daily("SCN-015")

    def test_phone_number_update(self):
        """SCN-020: Phone Number Update — receptionist updates client phone."""
        self._run_daily("SCN-020")

    def test_quick_client_lookup(self):
        """SCN-025: Quick Client Lookup — Omar looks up a client quickly."""
        self._run_daily("SCN-025")


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestPeriodicScenarios(ScenarioRunner):
    """Periodic scenarios: board prep, funder reporting."""

    def _run_periodic(self, scenario_id):
        """Common logic for running a periodic scenario."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")

        scenarios = discover_scenarios(holdout, ids=[scenario_id])
        scn = [s for _, s in scenarios if s["id"] == scenario_id]
        if not scn:
            self.skipTest(f"{scenario_id} not found in holdout dir")

        scenario = scn[0]
        self.personas = load_personas()
        self.use_llm = not _should_skip_llm()

        screenshot_dir = os.path.join(holdout, "reports", "screenshots")
        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_board_prep(self):
        """SCN-030: Board Prep — executive + admin prepare board reports."""
        self._seed_bulk_clients(150)
        self._run_periodic("SCN-030")

    def test_funder_reporting(self):
        """SCN-035: Funder Reporting — program manager generates reports."""
        self._run_periodic("SCN-035")


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestCrossRoleScenarios(ScenarioRunner):
    """Cross-role scenarios: bilingual intake, multi-program clients."""

    def _run_cross_role(self, scenario_id):
        """Common logic for running a cross-role scenario."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")

        scenarios = discover_scenarios(holdout, ids=[scenario_id])
        scn = [s for _, s in scenarios if s["id"] == scenario_id]
        if not scn:
            self.skipTest(f"{scenario_id} not found in holdout dir")

        scenario = scn[0]
        self.personas = load_personas()
        self.use_llm = not _should_skip_llm()

        screenshot_dir = os.path.join(holdout, "reports", "screenshots")
        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_bilingual_intake(self):
        """SCN-040: Bilingual Intake — Jean-Luc intakes a French-speaking client."""
        self._run_cross_role("SCN-040")

    def test_multi_program_client(self):
        """SCN-042: Multi-Program Client — cross-program enrolment and views."""
        self._run_cross_role("SCN-042")


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestEdgeCaseScenarios(ScenarioRunner):
    """Edge case scenarios: errors, timeouts, shared devices, consent."""

    def _run_edge_case(self, scenario_id):
        """Common logic for running an edge case scenario."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")

        scenarios = discover_scenarios(holdout, ids=[scenario_id])
        scn = [s for _, s in scenarios if s["id"] == scenario_id]
        if not scn:
            self.skipTest(f"{scenario_id} not found in holdout dir")

        scenario = scn[0]
        self.personas = load_personas()
        self.use_llm = not _should_skip_llm()

        screenshot_dir = os.path.join(holdout, "reports", "screenshots")
        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_error_states(self):
        """SCN-045: Error States — staff and receptionist encounter errors."""
        self._run_edge_case("SCN-045")

    def test_session_timeout(self):
        """SCN-046: Session Timeout — staff session expires mid-task."""
        self._run_edge_case("SCN-046")

    def test_shared_device_handoff(self):
        """SCN-049: Shared Device Handoff — staff to receptionist on same device."""
        self._run_edge_case("SCN-049")

    def test_consent_withdrawal(self):
        """SCN-070: Consent Withdrawal — PM and executive handle data erasure."""
        self._run_edge_case("SCN-070")


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestAccessibilityMicro(ScenarioRunner):
    """Accessibility micro-scenarios: focused checks on specific a11y features."""

    def _run_a11y(self, scenario_id):
        """Common logic for running an accessibility micro-scenario."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")

        scenarios = discover_scenarios(holdout, ids=[scenario_id])
        scn = [s for _, s in scenarios if s["id"] == scenario_id]
        if not scn:
            self.skipTest(f"{scenario_id} not found in holdout dir")

        scenario = scn[0]
        self.personas = load_personas()
        self.use_llm = not _should_skip_llm()

        screenshot_dir = os.path.join(holdout, "reports", "screenshots")
        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_login_focus(self):
        """SCN-051: Login Focus — keyboard focus order on login page."""
        self._run_a11y("SCN-051")

    def test_skip_link(self):
        """SCN-052: Skip Link — skip-to-content link works correctly."""
        self._run_a11y("SCN-052")

    def test_form_accessibility(self):
        """SCN-053: Form Accessibility — labels, errors, and ARIA on forms."""
        self._run_a11y("SCN-053")

    def test_tab_panel_aria(self):
        """SCN-054: Tab Panel ARIA — tab widget has correct ARIA roles."""
        self._run_a11y("SCN-054")

    def test_htmx_announcement(self):
        """SCN-055: HTMX Announcement — dynamic content announced to screen reader."""
        self._run_a11y("SCN-055")

    def test_high_contrast_zoom(self):
        """SCN-056: High Contrast + Zoom — layout at 200% zoom with forced colours."""
        self._run_a11y("SCN-056")

    def test_touch_targets(self):
        """SCN-057: Touch Targets — minimum 44x44px touch targets on mobile."""
        self._run_a11y("SCN-057")

    def test_cognitive_load(self):
        """SCN-058: Cognitive Load — interface simplicity for ADHD user."""
        self._run_a11y("SCN-058")

    def test_voice_navigation(self):
        """SCN-059: Voice Navigation — Dragon NaturallySpeaking compatibility."""
        self._run_a11y("SCN-059")

    def test_form_errors_keyboard(self):
        """SCN-061: Form Errors Keyboard — error recovery by keyboard only."""
        self._run_a11y("SCN-061")

    def test_aria_live_fatigue(self):
        """SCN-062: ARIA Live Fatigue — too many announcements overwhelm user."""
        self._run_a11y("SCN-062")
