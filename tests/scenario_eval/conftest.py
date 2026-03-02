"""Pytest configuration for scenario evaluation tests."""
import glob
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _resolve_holdout_dir():
    """Resolve the holdout directory, using a sensible default if env var not set.

    Checks SCENARIO_HOLDOUT_DIR env var first, then falls back to the
    sibling directory ../konote-qa-scenarios relative to the project root.
    In git worktrees, the project root differs from the main repo location,
    so we also check the main repo's sibling directory via git.
    """
    path = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
    if path and os.path.isdir(path):
        return path

    def _set_and_return(d):
        os.environ["SCENARIO_HOLDOUT_DIR"] = d
        return d

    # Default: sibling repo next to konote-app
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    default = os.path.join(os.path.dirname(project_root), "konote-qa-scenarios")
    if os.path.isdir(default):
        return _set_and_return(default)

    # Worktree fallback: resolve from the main repo, not the worktree copy
    try:
        git_common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=project_root, text=True, stderr=subprocess.DEVNULL,
            timeout=5,
        ).strip()
        # --git-common-dir returns the main repo's .git dir (absolute or relative)
        main_repo = os.path.dirname(os.path.normpath(
            os.path.join(project_root, git_common)
        ))
        if main_repo != project_root:
            fallback = os.path.join(
                os.path.dirname(main_repo), "konote-qa-scenarios"
            )
            if os.path.isdir(fallback):
                return _set_and_return(fallback)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


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


def pytest_addoption(parser):
    """Add --no-llm flag to skip LLM evaluation (dry-run mode)."""
    parser.addoption(
        "--no-llm",
        action="store_true",
        default=False,
        help="Run scenarios without LLM evaluation (capture only)",
    )


def pytest_configure(config):
    """Configure environment for scenario evaluation tests.

    - Sets SCENARIO_NO_LLM if --no-llm flag was passed
    - Auto-resolves SCENARIO_HOLDOUT_DIR if not set (uses sibling repo)
    """
    if config.getoption("--no-llm", default=False):
        os.environ["SCENARIO_NO_LLM"] = "1"

    # Auto-resolve holdout dir early so it's available during collection
    _resolve_holdout_dir()


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
    """Return the holdout directory path, or skip if not found."""
    path = _resolve_holdout_dir()
    if not path:
        pytest.skip(
            "Holdout repo not found. Either set SCENARIO_HOLDOUT_DIR or "
            "clone konote-qa-scenarios next to konote-app."
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


def _collect_run_files(screenshot_dir, scenario_ids):
    """Return screenshot filenames belonging to the given scenario IDs.

    Matches by filename prefix (e.g. "SCN-010_step1_..." belongs to
    scenario "SCN-010"). This identifies which files THIS run produced
    without needing cross-module state.
    """
    dirpath = Path(screenshot_dir)
    if not dirpath.is_dir():
        return []
    files = []
    for png in sorted(dirpath.glob("*.png")):
        for sid in scenario_ids:
            if png.name.startswith(f"{sid}_"):
                files.append(png.name)
                break
    return files


def _build_run_manifest(holdout, results):
    """Build a .run-manifest.json summarising the scenario run.

    Includes per-scenario metadata, screenshot validation results,
    a files_written list (for downstream tools to scope evaluation),
    and aggregate statistics for downstream tools (qa_gate.py, etc.).
    """
    from .state_capture import validate_screenshot_dir

    screenshot_dir = os.path.join(holdout, "reports", "screenshots")

    # Collect files belonging to THIS run's scenarios
    run_scenario_ids = {r.scenario_id for r in results}
    files_written = _collect_run_files(screenshot_dir, run_scenario_ids)

    # Validate only this run's files (not the entire historical folder)
    validation = validate_screenshot_dir(screenshot_dir, only_files=files_written)

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
        "version": 2,
        "scenarios_run": len(results),
        "personas_tested": sorted(all_personas),
        "total_steps": sum(s["steps"] for s in scenarios),
        "files_written": files_written,
        "screenshots": {
            "total": validation["total"],
            "valid": validation["valid"],
            "blank": validation["blank"],
            "duplicates": validation["duplicates"],
            "issues": validation["issues"],
        },
        "scenarios": scenarios,
    }


def _merge_manifests(existing, new_manifest, screenshot_dir=None):
    """Merge a partial re-run manifest into an existing full-run manifest.

    Keeps scenario data from the previous run for scenarios not re-run,
    and replaces data for scenarios that were re-run. Merges
    files_written so the combined list covers all runs.

    If screenshot_dir is provided, re-validates screenshots for the merged
    file set (gives accurate combined stats). Otherwise falls back to
    new_manifest's screenshot stats (useful for unit tests without disk).
    """
    new_ids = {s["scenario_id"] for s in new_manifest["scenarios"]}

    # Keep existing scenarios that weren't re-run
    merged_scenarios = [
        s for s in existing.get("scenarios", [])
        if s["scenario_id"] not in new_ids
    ]
    merged_scenarios.extend(new_manifest["scenarios"])
    merged_scenarios.sort(key=lambda s: s["scenario_id"])

    # Merge files_written: remove old files for re-run scenarios, add new
    existing_files = set(existing.get("files_written", []))
    for fname in list(existing_files):
        for sid in new_ids:
            if fname.startswith(f"{sid}_"):
                existing_files.discard(fname)
                break
    merged_files = sorted(existing_files | set(new_manifest.get("files_written", [])))

    # Merge personas
    all_personas = set(existing.get("personas_tested", []))
    all_personas.update(new_manifest.get("personas_tested", []))

    # Re-validate screenshots for the merged file set when possible
    if screenshot_dir:
        from .state_capture import validate_screenshot_dir
        validation = validate_screenshot_dir(screenshot_dir, only_files=merged_files)
        screenshots = {
            "total": validation["total"],
            "valid": validation["valid"],
            "blank": validation["blank"],
            "duplicates": validation["duplicates"],
            "issues": validation["issues"],
        }
    else:
        screenshots = new_manifest.get("screenshots", {})

    return {
        "generated_at": new_manifest["generated_at"],
        "version": 2,
        "scenarios_run": len(merged_scenarios),
        "personas_tested": sorted(all_personas),
        "total_steps": sum(s["steps"] for s in merged_scenarios),
        "files_written": merged_files,
        "screenshots": screenshots,
        "scenarios": merged_scenarios,
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

            # Merge with existing manifest if this is a partial re-run
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    existing = json.load(f)
                if existing.get("scenarios_run", 0) > manifest["scenarios_run"]:
                    print(
                        f"  Partial re-run ({manifest['scenarios_run']} scenarios) "
                        f"— merging with existing manifest "
                        f"({existing['scenarios_run']} scenarios)"
                    )
                    manifest = _merge_manifests(existing, manifest, screenshot_dir=screenshot_dir)
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass  # No existing manifest or unreadable — write fresh

            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, default=str)
            print(f"Run manifest written to: {manifest_path}")

            # Print screenshot validation summary
            ss = manifest["screenshots"]
            print(
                f"  {len(manifest.get('files_written', []))} files from this run, "
                f"{ss['total']} validated "
                f"({ss['blank']} blank, {ss['duplicates']} duplicates)"
            )
        except Exception as exc:
            print(f"WARNING: Could not write run manifest: {exc}")
    else:
        report_text = generate_report(_all_results)
        print("\n\n" + report_text)
