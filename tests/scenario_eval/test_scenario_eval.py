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
import yaml

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

    def test_french_intake(self):
        """SCN-026: French Intake — R2-FR receptionist intakes a French-speaking client."""
        self._run_daily("SCN-026")

    def test_quick_log_phone_call(self):
        """SCN-080: Quick Log Phone Call — staff logs a phone call via quick-log buttons."""
        self._run_daily("SCN-080")

    def test_schedule_meeting_reminder(self):
        """SCN-081: Schedule Meeting + Send Reminder — staff creates meeting and sends text reminder."""
        self._run_daily("SCN-081")

    def test_calendar_feed_setup(self):
        """SCN-083: Calendar Feed Setup — staff generates iCal feed URL."""
        self._run_daily("SCN-083")


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

    def test_pm_program_config(self):
        """SCN-036: PM Program Config — program manager configures program settings."""
        self._run_periodic("SCN-036")

    def test_pm_staff_management(self):
        """SCN-037: PM Staff Management — program manager manages staff."""
        self._run_periodic("SCN-037")

    def test_meeting_dashboard_review(self):
        """SCN-082: PM Meeting Dashboard — programme manager reviews meetings and updates status."""
        self._run_periodic("SCN-082")

    def test_funder_report_suppression(self):
        """SCN-086: Funder Report Suppression — funder profile with small-cell suppression."""
        self._run_periodic("SCN-086")


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

    def test_alert_recommendation_workflow(self):
        """SCN-075: Alert Recommendation — staff recommends, PM reviews alert cancellation."""
        self._run_cross_role("SCN-075")

    def test_group_management_permissions(self):
        """SCN-076: Group Management Permissions — role-based group access."""
        self._run_cross_role("SCN-076")

    def test_messaging_consent_blocks(self):
        """SCN-084: Messaging Consent Blocks — reminders blocked by missing consent, logging still works."""
        self._run_cross_role("SCN-084")

    def test_front_desk_messaging_denied(self):
        """SCN-085: Front Desk Denied — permission enforcement on messaging/meeting/calendar pages."""
        self._run_cross_role("SCN-085")


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

    def test_alt_text_images(self):
        """SCN-063: Alt Text for Images — meaningful alt text on all images."""
        self._run_a11y("SCN-063")

    def test_page_titles(self):
        """SCN-064: Page Titles — unique, descriptive page titles."""
        self._run_a11y("SCN-064")

    def test_focus_not_obscured(self):
        """SCN-065: Focus Not Obscured — focused element visible, not hidden by sticky elements."""
        self._run_a11y("SCN-065")


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestSmokeTest(ScenarioRunner):
    """Smoke test subset — minimal 6 scenarios for quick health checks.

    Loads scenarios from tasks/smoke-test-subset.yaml and runs each one.
    This is the entry point for the QA repo's smoke test evaluation.
    """

    def _get_smoke_scenario_ids(self):
        """Load smoke test scenario IDs from smoke-test-subset.yaml."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")

        smoke_subset_path = os.path.join(holdout, "tasks", "smoke-test-subset.yaml")
        if not os.path.exists(smoke_subset_path):
            self.skipTest(f"Smoke test subset not found: {smoke_subset_path}")

        with open(smoke_subset_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        scenarios = data.get("smoke_test_scenarios", [])
        return [s["id"] for s in scenarios if "id" in s]

    def _run_smoke_scenario(self, scenario_id):
        """Common logic for running a smoke test scenario."""
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

        # Seed bulk clients for executive scenarios
        if scenario_id in ["CAL-001", "SCN-030"]:
            self._seed_bulk_clients(150)

        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        get_all_results().append(result)
        return result

    def test_smoke_cal_001_executive_dashboard(self):
        """CAL-001: Executive dashboard — smoke test for E1 persona."""
        self._run_smoke_scenario("CAL-001")

    def test_smoke_scn_010_morning_intake(self):
        """SCN-010: Morning intake — smoke test for R1 persona."""
        self._run_smoke_scenario("SCN-010")

    def test_smoke_scn_015_catchup_friday(self):
        """SCN-015: Catchup Friday — smoke test for DS1 persona."""
        self._run_smoke_scenario("SCN-015")

    def test_smoke_scn_040_bilingual_intake(self):
        """SCN-040: Bilingual intake — smoke test for DS2 persona."""
        self._run_smoke_scenario("SCN-040")

    def test_smoke_scn_051_login_focus(self):
        """SCN-051: Login focus — smoke test for DS3 persona."""
        self._run_smoke_scenario("SCN-051")

    def test_smoke_scn_035_funder_reporting(self):
        """SCN-035: Funder reporting — smoke test for PM1 persona."""
        self._run_smoke_scenario("SCN-035")


def _compute_icc(scores_matrix):
    """Compute ICC(2,1) — two-way random, single measures.

    Args:
        scores_matrix: List of lists. Each inner list is one rater/variant's
                       scores across all subjects/scenarios.
                       Shape: [n_raters][n_subjects]

    Returns:
        ICC value (float), or None if computation fails.
    """
    n_raters = len(scores_matrix)
    if n_raters < 2:
        return None
    n_subjects = len(scores_matrix[0])
    if n_subjects < 2:
        return None

    # Grand mean
    all_scores = [s for rater in scores_matrix for s in rater]
    grand_mean = sum(all_scores) / len(all_scores)

    # Row means (per subject, averaged across raters)
    row_means = []
    for j in range(n_subjects):
        row_means.append(sum(scores_matrix[i][j] for i in range(n_raters)) / n_raters)

    # Column means (per rater, averaged across subjects)
    col_means = []
    for i in range(n_raters):
        col_means.append(sum(scores_matrix[i]) / n_subjects)

    # Mean squares
    # MSR = mean square for rows (between subjects)
    msr = n_raters * sum((rm - grand_mean) ** 2 for rm in row_means) / (n_subjects - 1)
    # MSC = mean square for columns (between raters)
    msc = n_subjects * sum((cm - grand_mean) ** 2 for cm in col_means) / (n_raters - 1)
    # MSE = mean square error (residual)
    ss_total = sum((scores_matrix[i][j] - grand_mean) ** 2
                   for i in range(n_raters) for j in range(n_subjects))
    ss_rows = n_raters * sum((rm - grand_mean) ** 2 for rm in row_means)
    ss_cols = n_subjects * sum((cm - grand_mean) ** 2 for cm in col_means)
    ss_error = ss_total - ss_rows - ss_cols
    df_error = (n_raters - 1) * (n_subjects - 1)
    if df_error == 0:
        return None
    mse = ss_error / df_error

    # ICC(2,1) formula
    denominator = msr + (n_raters - 1) * mse + n_raters * (msc - mse) / n_subjects
    if abs(denominator) < 1e-10:
        return None
    icc = (msr - mse) / denominator

    # Clamp to [-1, 1] range (can be slightly outside due to floating point)
    return max(-1.0, min(1.0, icc))


def _compute_agreement_pct(scores_matrix, tolerance=1.0):
    """Compute percentage of score pairs within tolerance.

    For each subject, checks all rater pairs. Returns the percentage
    where the absolute difference is <= tolerance.
    """
    n_raters = len(scores_matrix)
    n_subjects = len(scores_matrix[0])
    total_pairs = 0
    agree_pairs = 0

    for j in range(n_subjects):
        for i1 in range(n_raters):
            for i2 in range(i1 + 1, n_raters):
                total_pairs += 1
                if abs(scores_matrix[i1][j] - scores_matrix[i2][j]) <= tolerance:
                    agree_pairs += 1

    if total_pairs == 0:
        return 0.0
    return (agree_pairs / total_pairs) * 100.0


# Default variant configurations for IRR testing
_DEFAULT_IRR_VARIANTS = [
    {"name": "default", "model": "claude-haiku-4-5-20251001", "temperature": 0.3},
    {"name": "higher-temp", "model": "claude-haiku-4-5-20251001", "temperature": 0.8},
    {"name": "low-temp", "model": "claude-haiku-4-5-20251001", "temperature": 0.1},
]

_CALIBRATION_IDS = ["CAL-001", "CAL-002", "CAL-003", "CAL-004", "CAL-005"]


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestInterRaterReliability(ScenarioRunner):
    """CAL-006: Inter-rater reliability across evaluator variants.

    Runs CAL-001 through CAL-005 with different model/temperature
    configurations. Computes ICC(2,1) and agreement metrics to validate
    that the LLM evaluator produces consistent scores.

    This is a slow, expensive test — run sparingly after evaluator changes.
    """

    def _load_variants(self):
        """Load variant configurations from CAL-006 YAML or use defaults."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            return _DEFAULT_IRR_VARIANTS, {"min_icc": 0.60, "min_agreement_pct": 70}

        scenarios = discover_scenarios(holdout, ids=["CAL-006"])
        cal6 = [s for _, s in scenarios if s["id"] == "CAL-006"]
        if not cal6:
            return _DEFAULT_IRR_VARIANTS, {"min_icc": 0.60, "min_agreement_pct": 70}

        scenario = cal6[0]
        variants = scenario.get("variants", _DEFAULT_IRR_VARIANTS)
        pass_criteria = scenario.get("pass_criteria", {
            "min_icc": 0.60, "min_agreement_pct": 70,
        })
        return variants, pass_criteria

    def _run_calibration_with_variant(self, scenario_id, variant):
        """Run a single calibration scenario with a specific variant config."""
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        scenarios = discover_scenarios(holdout, ids=[scenario_id])
        scn = [s for _, s in scenarios if s["id"] == scenario_id]
        if not scn:
            return None

        scenario = scn[0]
        self.personas = load_personas()
        self.use_llm = True
        self.eval_model = variant.get("model")
        self.eval_temperature = variant.get("temperature")

        screenshot_dir = os.path.join(holdout, "reports", "screenshots")
        result = self.run_scenario(scenario, screenshot_dir=screenshot_dir)
        return result

    def test_inter_rater_reliability(self):
        """CAL-006: ICC and agreement across evaluator variants.

        Runs all calibration scenarios with each variant configuration,
        then computes ICC(2,1) and pairwise agreement percentage.
        """
        holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
        if not holdout or not os.path.isdir(holdout):
            self.skipTest("SCENARIO_HOLDOUT_DIR not set")

        if _should_skip_llm():
            self.skipTest("IRR requires LLM evaluation (no --no-llm)")

        variants, pass_criteria = self._load_variants()
        min_icc = pass_criteria.get("min_icc", 0.60)
        min_agreement = pass_criteria.get("min_agreement_pct", 70)

        # Collect scores: variants x scenarios
        # scores_matrix[variant_idx][scenario_idx] = avg_score
        scores_matrix = []
        variant_names = []

        for variant in variants:
            variant_name = variant.get("name", "unnamed")
            variant_names.append(variant_name)
            variant_scores = []

            for scenario_id in _CALIBRATION_IDS:
                result = self._run_calibration_with_variant(scenario_id, variant)
                if result and result.avg_score > 0:
                    variant_scores.append(result.avg_score)
                    get_all_results().append(result)
                else:
                    variant_scores.append(0.0)

            scores_matrix.append(variant_scores)

        # Reset eval config
        self.eval_model = None
        self.eval_temperature = None

        # Compute ICC
        icc = _compute_icc(scores_matrix)
        agreement = _compute_agreement_pct(scores_matrix)

        # Build report
        report_lines = [
            "=" * 60,
            "INTER-RATER RELIABILITY REPORT (CAL-006)",
            "=" * 60,
            "",
            f"Variants tested: {len(variants)}",
            f"Scenarios: {', '.join(_CALIBRATION_IDS)}",
            "",
            "Scores by variant:",
        ]
        for i, name in enumerate(variant_names):
            scores_str = ", ".join(f"{s:.2f}" for s in scores_matrix[i])
            report_lines.append(f"  {name}: [{scores_str}]")

        report_lines.extend([
            "",
            f"ICC(2,1): {icc:.3f}" if icc is not None else "ICC(2,1): N/A",
            f"Agreement (within 1.0): {agreement:.1f}%",
            "",
            f"Pass criteria: ICC >= {min_icc}, Agreement >= {min_agreement}%",
        ])

        # Write report to file
        report_path = os.path.join(holdout, "reports", "irr-report.txt")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            f.write("\n".join(report_lines))

        # Print to test output
        print("\n" + "\n".join(report_lines))

        # Assertions
        if icc is not None:
            self.assertGreaterEqual(
                icc, min_icc,
                f"ICC(2,1) = {icc:.3f} — below threshold {min_icc}"
            )
        self.assertGreaterEqual(
            agreement, min_agreement,
            f"Agreement = {agreement:.1f}% — below threshold {min_agreement}%"
        )
