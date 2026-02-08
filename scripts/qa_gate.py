"""QA gate check — read scenario evaluation results and fail on blockers.

Reads the most recent *-results.json file from a report directory and
checks whether any scenarios were flagged as blockers (red band).

Exit codes:
    0 — No blockers found (or no results file found — graceful skip).
    1 — One or more blocker scenarios detected.

Usage:
    python scripts/qa_gate.py [report_dir] [--summary-only]

Arguments:
    report_dir      Path to the directory containing *-results.json files.
                    Defaults to the current directory.
    --summary-only  Print the summary but always exit 0, even if blockers exist.

This script uses only the Python standard library (no Django, no pip packages).
"""

import glob
import json
import os
import sys
from pathlib import Path


def find_latest_results(report_dir):
    """Find the most recent *-results.json file in report_dir.

    Files are sorted by name (which includes a date prefix like
    2026-02-08-results.json), so the last one alphabetically is the
    most recent.

    Returns:
        Path to the most recent results file, or None if none found.
    """
    pattern = os.path.join(report_dir, "*-results.json")
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    return files[-1]


def print_summary(data, results_path):
    """Print a human-readable summary of the evaluation results."""
    summary = data.get("summary", {})
    total = summary.get("total_scenarios", 0)
    avg_score = summary.get("avg_score", 0)
    worst_gap = summary.get("worst_gap", 0)
    blockers = summary.get("blockers", [])
    has_blocker = summary.get("has_blocker", False)

    print(f"QA Scenario Results  ({Path(results_path).name})")
    print(f"  Scenarios evaluated : {total}")
    print(f"  Average score       : {avg_score:.2f} / 5.00")
    print(f"  Worst gap           : {worst_gap:.2f}")

    if has_blocker:
        print(f"  Blockers            : {', '.join(blockers)}")
    else:
        print("  Blockers            : none")

    return has_blocker, blockers


def main():
    # Parse arguments
    args = sys.argv[1:]
    summary_only = "--summary-only" in args
    if summary_only:
        args.remove("--summary-only")

    report_dir = args[0] if args else "."

    # Validate directory
    if not os.path.isdir(report_dir):
        print(f"WARNING: Report directory does not exist: {report_dir}")
        print("Skipping QA gate check (no results to evaluate).")
        sys.exit(0)

    # Find latest results file
    results_path = find_latest_results(report_dir)
    if results_path is None:
        print(f"WARNING: No *-results.json files found in {report_dir}")
        print("Skipping QA gate check (no results to evaluate).")
        sys.exit(0)

    # Read and parse
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Could not read results file: {exc}")
        sys.exit(1)

    # Print summary
    has_blocker, blockers = print_summary(data, results_path)

    # Gate decision
    if summary_only:
        print("\n--summary-only mode: exiting 0 regardless of blockers.")
        sys.exit(0)

    if has_blocker:
        print(f"\nFAILED: {len(blockers)} blocker(s) detected — {', '.join(blockers)}")
        print("Fix these scenarios before merging.")
        sys.exit(1)
    else:
        print("\nPASSED: No blocker scenarios. Good to merge.")
        sys.exit(0)


if __name__ == "__main__":
    main()
