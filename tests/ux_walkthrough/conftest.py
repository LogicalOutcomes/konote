"""Session-scoped fixture for collecting and writing the UX report."""
import os

import pytest

from .report import ReportGenerator

# Module-level report collector shared across all walkthrough tests
_report = ReportGenerator()


@pytest.fixture(scope="session", autouse=True)
def ux_report():
    """Provide the shared report collector and write the report at session end."""
    yield _report
    # Finalizer: write the report after all tests finish
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "tasks",
        "ux-review-latest.md",
    )
    if _report.pages_visited > 0 or _report.browser_findings:
        _report.write_report(report_path)


def get_report() -> ReportGenerator:
    """Get the module-level report instance (for use in test classes)."""
    return _report
