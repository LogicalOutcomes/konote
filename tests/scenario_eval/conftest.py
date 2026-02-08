"""Pytest configuration for scenario evaluation tests."""
import os
from datetime import datetime

import pytest


def pytest_addoption(parser):
    """Add --no-llm flag to skip LLM evaluation (dry-run mode)."""
    parser.addoption(
        "--no-llm",
        action="store_true",
        default=False,
        help="Run scenarios without LLM evaluation (capture only)",
    )


def pytest_configure(config):
    """Set SCENARIO_NO_LLM env var if --no-llm flag was passed."""
    if config.getoption("--no-llm", default=False):
        os.environ["SCENARIO_NO_LLM"] = "1"


def pytest_collection_modifyitems(config, items):
    """Add 'scenario_eval' marker to all tests in this directory."""
    for item in items:
        if "scenario_eval" in str(item.fspath):
            item.add_marker(pytest.mark.scenario_eval)


# Collect results across tests for the final report
_all_results = []


def get_all_results():
    """Return the shared results list (test classes append to this)."""
    return _all_results


@pytest.fixture(scope="session")
def holdout_dir():
    """Return the holdout directory path, or skip if not configured."""
    path = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
    if not path or not os.path.isdir(path):
        pytest.skip(
            "SCENARIO_HOLDOUT_DIR not set or not a valid directory. "
            "Set it to your konote-qa-scenarios repo path."
        )
    return path


def pytest_sessionfinish(session, exitstatus):
    """Generate a satisfaction report after all tests complete."""
    if not _all_results:
        return

    # Lazy import to avoid circular issues at collection time
    from .report_generator import generate_report

    holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
    if holdout:
        report_dir = os.path.join(holdout, "reports")
        os.makedirs(report_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        report_path = os.path.join(
            report_dir, f"{date_str}-satisfaction-report.md"
        )
        generate_report(_all_results, output_path=report_path)
        print(f"\n\nSatisfaction report written to: {report_path}")
    else:
        report_text = generate_report(_all_results)
        print("\n\n" + report_text)
