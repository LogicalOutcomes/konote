"""Track satisfaction gap scores over time.

Reads the most recent QA scenario evaluation results JSON, extracts
key metrics (average score, worst gap, per-persona and per-scenario
breakdowns), and appends a summary entry to a history file.

This builds a longitudinal record so we can see whether satisfaction
gaps between personas are narrowing over time.

Usage:
    python scripts/track_satisfaction.py
    python scripts/track_satisfaction.py --report-dir reports/
    python scripts/track_satisfaction.py --history-file qa/satisfaction-history.json

No Django dependencies -- stdlib only.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date


GAP_TARGET = 1.0  # Worst gap must be below this to pass


def find_latest_results(report_dir):
    """Find the most recent *-results.json file in the report directory.

    Args:
        report_dir: Directory to search for results files.

    Returns:
        Path to the most recent results file, or None if not found.
    """
    pattern = os.path.join(report_dir, "*-results.json")
    files = glob.glob(pattern)
    if not files:
        return None
    # Sort by modification time, most recent last
    files.sort(key=os.path.getmtime)
    return files[-1]


def get_git_commit():
    """Get the current git commit hash (short form).

    Returns:
        Short commit hash string, or 'unknown' if git is not available.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()[:7]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def get_git_branch():
    """Get the current git branch name.

    Returns:
        Branch name string, or 'unknown' if git is not available.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def aggregate_per_persona(scenarios):
    """Average each persona's scores across all scenarios.

    Args:
        scenarios: List of scenario dicts from the results JSON.

    Returns:
        Dict mapping persona ID to their average score across scenarios.
    """
    # Collect all scores per persona
    persona_scores = defaultdict(list)
    for scenario in scenarios:
        for persona_id, score in scenario.get("per_persona_scores", {}).items():
            persona_scores[persona_id].append(score)

    # Average them
    return {
        pid: round(sum(scores) / len(scores), 2)
        for pid, scores in sorted(persona_scores.items())
        if scores
    }


def build_per_scenario(scenarios):
    """Extract per-scenario summary data.

    Args:
        scenarios: List of scenario dicts from the results JSON.

    Returns:
        Dict mapping scenario ID to its score, band, and gap.
    """
    result = {}
    for scenario in scenarios:
        result[scenario["scenario_id"]] = {
            "score": scenario["avg_score"],
            "band": scenario["band"],
            "gap": scenario["satisfaction_gap"],
        }
    return result


def build_history_entry(results_data):
    """Build a history entry from results data and current git state.

    Args:
        results_data: Parsed JSON from a results file.

    Returns:
        Dict representing one history entry.
    """
    scenarios = results_data.get("scenarios", [])
    summary = results_data.get("summary", {})

    worst_gap = summary.get("worst_gap", 0)
    avg_score = summary.get("avg_score", 0)
    blockers = summary.get("blockers", [])

    return {
        "date": date.today().isoformat(),
        "commit": get_git_commit(),
        "branch": get_git_branch(),
        "avg_score": avg_score,
        "worst_gap": worst_gap,
        "gap_target_met": worst_gap < GAP_TARGET,
        "per_persona": aggregate_per_persona(scenarios),
        "per_scenario": build_per_scenario(scenarios),
        "blockers": blockers,
    }


def load_history(history_file):
    """Load existing history from the JSON file.

    Creates the file with an empty list if it does not exist.

    Args:
        history_file: Path to the history JSON file.

    Returns:
        List of history entries.
    """
    if not os.path.exists(history_file):
        # Create parent directories if needed
        parent = os.path.dirname(history_file)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []

    with open(history_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history, history_file):
    """Write history entries back to the JSON file.

    Args:
        history: List of history entry dicts.
        history_file: Path to the history JSON file.
    """
    parent = os.path.dirname(history_file)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    """Main entry point: parse args, read results, update history."""
    parser = argparse.ArgumentParser(
        description="Track satisfaction gap scores over time."
    )
    parser.add_argument(
        "--report-dir",
        default=".",
        help="Directory containing *-results.json files (default: current directory)",
    )
    parser.add_argument(
        "--history-file",
        default="qa/satisfaction-history.json",
        help="Path to the history JSON file (default: qa/satisfaction-history.json)",
    )
    args = parser.parse_args()

    # Find the latest results file
    results_path = find_latest_results(args.report_dir)
    if not results_path:
        print(f"No *-results.json files found in {args.report_dir}")
        sys.exit(1)

    print(f"Reading results from: {results_path}")

    # Parse the results
    with open(results_path, "r", encoding="utf-8") as f:
        results_data = json.load(f)

    # Build the new history entry
    entry = build_history_entry(results_data)

    # Load existing history
    history = load_history(args.history_file)

    # Deduplicate by commit hash -- don't add the same commit twice
    existing_commits = {h["commit"] for h in history}
    if entry["commit"] in existing_commits:
        print(f"Commit {entry['commit']} already recorded. Skipping.")
        sys.exit(0)

    # Append and save
    history.append(entry)
    save_history(history, args.history_file)

    # Report
    print(f"Recorded: commit {entry['commit']} on {entry['branch']}")
    print(f"  Average score: {entry['avg_score']}")
    print(f"  Worst gap:     {entry['worst_gap']}")
    if entry["gap_target_met"]:
        print(f"  Gap target (<{GAP_TARGET}): MET")
    else:
        print(f"  Gap target (<{GAP_TARGET}): NOT MET")
    if entry["blockers"]:
        print(f"  Blockers:      {', '.join(entry['blockers'])}")
    else:
        print("  Blockers:      none")


if __name__ == "__main__":
    main()
