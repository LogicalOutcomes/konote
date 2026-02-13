"""Pytest configuration for scenario evaluation tests."""
import glob
import json
import os
from datetime import datetime, timezone

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


def _get_next_sequence(report_dir, date_str):
    """Return a sequence suffix so multiple runs on the same day get unique filenames.

    First run of the day: "" (no suffix)
    Second run: "a"
    Third run: "b"
    ...and so on through the alphabet.
    """
    # Check for existing report files matching this date
    pattern = os.path.join(report_dir, f"{date_str}*-satisfaction-report.md")
    existing = glob.glob(pattern)
    if not existing:
        return ""

    # Find the highest sequence letter already used
    # Filenames look like: 2026-02-08-satisfaction-report.md (no letter)
    #                   or: 2026-02-08a-satisfaction-report.md (letter "a")
    max_letter = None
    for filepath in existing:
        basename = os.path.basename(filepath)
        # Strip the date prefix and the "-satisfaction-report.md" suffix
        after_date = basename[len(date_str):]  # e.g. "-satisfaction-report.md" or "a-satisfaction-report.md"
        if after_date.startswith("-satisfaction-report.md"):
            # This is the original (no-letter) file
            if max_letter is None:
                max_letter = ""  # Marks that the no-suffix file exists
        elif len(after_date) > 1 and after_date[0].isalpha() and after_date[1] == "-":
            letter = after_date[0]
            if max_letter is None or max_letter == "" or letter > max_letter:
                max_letter = letter

    if max_letter is None:
        # Shouldn't happen since existing is non-empty, but be safe
        return ""
    elif max_letter == "":
        # Only the no-suffix file exists — next is "a"
        return "a"
    else:
        # Advance to the next letter (cap at 'z' to avoid non-alpha chars)
        if max_letter >= "z":
            return "z"
        return chr(ord(max_letter) + 1)


def _build_run_manifest(holdout, results):
    """Build a .run-manifest.json summarising the scenario run.

    Includes per-scenario metadata, screenshot validation results,
    and aggregate statistics for downstream tools (qa_gate.py, etc.).
    """
    from .state_capture import validate_screenshot_dir

    screenshot_dir = os.path.join(holdout, "reports", "screenshots")
    validation = validate_screenshot_dir(screenshot_dir)

    scenarios = []
    all_personas = set()
    for result in results:
        persona_ids = list(result.per_persona_scores().keys())
        all_personas.update(persona_ids)
        scenarios.append({
            "scenario_id": result.scenario_id,
            "title": result.title,
            "steps": len(result.step_evaluations),
            "personas": persona_ids,
            "avg_score": round(result.avg_score, 2),
            "band": result.band,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": 1,
        "scenarios_run": len(results),
        "personas_tested": sorted(all_personas),
        "total_steps": sum(s["steps"] for s in scenarios),
        "screenshots": {
            "total": validation["total"],
            "valid": validation["valid"],
            "blank": validation["blank"],
            "duplicates": validation["duplicates"],
            "issues": validation["issues"],
        },
        "scenarios": scenarios,
    }


def pytest_sessionfinish(session, exitstatus):
    """Generate a satisfaction report and run manifest after all tests complete."""
    if not _all_results:
        return

    # Lazy import to avoid circular issues at collection time
    from .report_generator import generate_report

    holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
    if holdout:
        report_dir = os.path.join(holdout, "reports")
        os.makedirs(report_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        seq = _get_next_sequence(report_dir, date_str)
        date_prefix = f"{date_str}{seq}"

        report_path = os.path.join(
            report_dir, f"{date_prefix}-satisfaction-report.md"
        )
        generate_report(_all_results, output_path=report_path)
        if seq:
            print(f"\n\nRun sequence: {date_str} run '{seq}' (multiple runs today)")
        print(f"\n\nSatisfaction report written to: {report_path}")

        # Also write machine-readable JSON for qa_gate.py and track_satisfaction.py
        try:
            from .results_serializer import write_results_json

            json_path = os.path.join(report_dir, f"{date_prefix}-results.json")
            write_results_json(_all_results, json_path)
            print(f"JSON results written to: {json_path}")
        except Exception as exc:
            print(f"WARNING: Could not write JSON results: {exc}")

        # Write .run-manifest.json with screenshot validation (QA-W6)
        try:
            screenshot_dir = os.path.join(holdout, "reports", "screenshots")
            manifest = _build_run_manifest(holdout, _all_results)
            manifest_path = os.path.join(screenshot_dir, ".run-manifest.json")
            os.makedirs(screenshot_dir, exist_ok=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, default=str)
            print(f"Run manifest written to: {manifest_path}")

            # Print screenshot validation summary
            ss = manifest["screenshots"]
            if ss["blank"] or ss["duplicates"]:
                print(
                    f"  Screenshot issues: {ss['blank']} blank, "
                    f"{ss['duplicates']} duplicates "
                    f"(out of {ss['total']} total)"
                )
            else:
                print(
                    f"  All {ss['total']} screenshots valid "
                    f"(no blanks or duplicates)"
                )
        except Exception as exc:
            print(f"WARNING: Could not write run manifest: {exc}")
    else:
        report_text = generate_report(_all_results)
        print("\n\n" + report_text)
