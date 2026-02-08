"""Generate a markdown trend table from satisfaction gap history.

Reads the satisfaction history JSON file and produces a markdown
document showing how scores and gaps have changed over time. This
makes it easy to see at a glance whether the satisfaction gap between
personas is narrowing.

Usage:
    python scripts/chart_satisfaction.py
    python scripts/chart_satisfaction.py --history-file qa/satisfaction-history.json
    python scripts/chart_satisfaction.py --output qa/satisfaction-trend.md

No Django dependencies -- stdlib only.
"""

import argparse
import json
import os
import sys


def load_history(history_file):
    """Load history entries from the JSON file.

    Args:
        history_file: Path to the history JSON file.

    Returns:
        List of history entry dicts.
    """
    if not os.path.exists(history_file):
        return []
    with open(history_file, "r", encoding="utf-8") as f:
        return json.load(f)


def format_target_met(met):
    """Format the gap_target_met boolean for display.

    Args:
        met: Boolean indicating whether the target was met.

    Returns:
        'Yes' or 'No' string.
    """
    return "Yes" if met else "No"


def build_trend_line(history):
    """Build a trend summary comparing first and latest entries.

    Args:
        history: List of history entries (must have 2+ entries).

    Returns:
        Trend description string, or None if fewer than 2 entries.
    """
    if len(history) < 2:
        return None

    first = history[0]
    latest = history[-1]

    score_diff = latest["avg_score"] - first["avg_score"]
    gap_diff = latest["worst_gap"] - first["worst_gap"]

    # Describe score direction
    if score_diff > 0:
        score_desc = f"improving (+{score_diff:.1f})"
    elif score_diff < 0:
        score_desc = f"declining ({score_diff:.1f})"
    else:
        score_desc = "stable"

    # Describe gap direction (negative means narrowing, which is good)
    if gap_diff < 0:
        gap_desc = f"narrowing ({gap_diff:.1f})"
    elif gap_diff > 0:
        gap_desc = f"widening (+{gap_diff:.1f})"
    else:
        gap_desc = "stable"

    return f"Trend: Scores {score_desc}, gap {gap_desc}"


def generate_markdown(history):
    """Generate the full markdown document from history data.

    Args:
        history: List of history entry dicts.

    Returns:
        Markdown string ready to write to a file.
    """
    lines = []
    lines.append("# Satisfaction Gap Trend")
    lines.append("")
    lines.append(
        "Target: worst satisfaction gap < 1.0 points between personas."
    )
    lines.append("")

    if not history:
        lines.append("No data recorded yet.")
        lines.append("")
        return "\n".join(lines)

    # Table header
    lines.append(
        "| Date | Commit | Avg Score | Worst Gap | Target Met | Blockers |"
    )
    lines.append(
        "|------|--------|-----------|-----------|------------|----------|"
    )

    # Table rows
    for entry in history:
        date_str = entry.get("date", "?")
        commit = entry.get("commit", "?")
        avg_score = entry.get("avg_score", 0)
        worst_gap = entry.get("worst_gap", 0)
        target_met = format_target_met(entry.get("gap_target_met", False))
        blocker_count = len(entry.get("blockers", []))
        lines.append(
            f"| {date_str} | {commit} | {avg_score} | {worst_gap} "
            f"| {target_met} | {blocker_count} |"
        )

    lines.append("")

    # Latest summary
    latest = history[-1]
    avg = latest.get("avg_score", 0)
    gap = latest.get("worst_gap", 0)
    met_str = "met" if latest.get("gap_target_met", False) else "not yet met"
    lines.append(f"**Latest:** Avg score {avg}, worst gap {gap}. Target {met_str}.")
    lines.append("")

    # Trend line (only if 2+ entries)
    trend = build_trend_line(history)
    if trend:
        lines.append(trend)
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point: parse args, load history, write markdown."""
    parser = argparse.ArgumentParser(
        description="Generate a markdown satisfaction gap trend table."
    )
    parser.add_argument(
        "--history-file",
        default="qa/satisfaction-history.json",
        help="Path to the history JSON file (default: qa/satisfaction-history.json)",
    )
    parser.add_argument(
        "--output",
        default="qa/satisfaction-trend.md",
        help="Path to write the markdown output (default: qa/satisfaction-trend.md)",
    )
    args = parser.parse_args()

    # Load history
    history = load_history(args.history_file)
    if not history:
        print(f"No history data in {args.history_file}")
        print("Run track_satisfaction.py first to record some entries.")

    # Generate markdown
    markdown = generate_markdown(history)

    # Write output
    parent = os.path.dirname(args.output)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Wrote satisfaction trend to {args.output}")
    if history:
        latest = history[-1]
        print(
            f"  {len(history)} entries, latest: "
            f"avg {latest['avg_score']}, gap {latest['worst_gap']}"
        )
        trend = build_trend_line(history)
        if trend:
            print(f"  {trend}")


if __name__ == "__main__":
    main()
