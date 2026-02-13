"""Session-scoped fixture for collecting and writing the UX report."""
import os
import re

import pytest

from .report import ReportGenerator

# Module-level report collector shared across all walkthrough tests
_report = ReportGenerator()


def pytest_addoption(parser):
    """Add --force-overwrite option for UX walkthrough reports."""
    parser.addoption(
        "--force-overwrite",
        action="store_true",
        default=False,
        help="Overwrite UX report even if previous report had more pages",
    )


@pytest.fixture(scope="session", autouse=True)
def ux_report(request):
    """Provide the shared report collector and write the report at session end."""
    yield _report
    # Finalizer: write the report after all tests finish
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "tasks",
        "ux-review-latest.md",
    )
    if _report.pages_visited > 0 or _report.browser_findings:
        # Overwrite protection: refuse to replace a bigger report
        # unless --force-overwrite is passed
        force = request.config.getoption("--force-overwrite", default=False)
        prev_pages = _read_previous_page_count(report_path)
        if prev_pages > 0 and _report.pages_visited < prev_pages and not force:
            print(
                f"\n⚠️  UX report NOT overwritten: this run visited "
                f"{_report.pages_visited} pages but the existing report "
                f"has {prev_pages}. Use --force-overwrite to replace it."
            )
            return
        _report.write_report(report_path)


def _read_previous_page_count(filepath: str) -> int:
    """Read page count from the existing report file."""
    if not os.path.exists(filepath):
        return 0
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if "Pages visited" in line:
                    m = re.search(r"\|\s*(\d+)", line.split("Pages visited")[1])
                    if m:
                        return int(m.group(1))
    except Exception:
        pass
    return 0


def get_report() -> ReportGenerator:
    """Get the module-level report instance (for use in test classes)."""
    return _report
