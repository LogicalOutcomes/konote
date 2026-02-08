"""Generate satisfaction reports from scenario evaluation results.

Reports follow the gap-first format: headlines are about experience
gaps between personas, not average scores.
"""
from datetime import datetime

from .score_models import DIMENSIONS, ScenarioResult, band_emoji, score_to_band


def generate_report(results, output_path=None):
    """Generate a Markdown satisfaction report.

    Args:
        results: List of ScenarioResult objects.
        output_path: Path to write the report (optional — also returns string).

    Returns:
        The report as a Markdown string.
    """
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append(f"# Satisfaction Report — {now}")
    lines.append("")

    # --- Section 1: Satisfaction Gaps (headline metric) ---
    lines.append("## Satisfaction Gaps")
    lines.append("")
    lines.append("These are the scenarios where different personas had the most")
    lines.append("divergent experiences. **Gaps > 2.0 are critical.**")
    lines.append("")

    gap_results = sorted(results, key=lambda r: r.satisfaction_gap, reverse=True)
    lines.append("| Scenario | Gap | Personas | Band |")
    lines.append("|----------|-----|----------|------|")
    for r in gap_results:
        gap = r.satisfaction_gap
        if gap < 0.1:
            continue  # Skip scenarios with only one persona
        persona_scores = r.per_persona_scores()
        persona_str = ", ".join(
            f"{pid}: {score:.1f}" for pid, score in persona_scores.items()
        )
        gap_label = "CRITICAL" if gap > 2.0 else "significant" if gap > 1.0 else "acceptable"
        lines.append(f"| {r.title} | {gap:.1f} ({gap_label}) | {persona_str} | {band_emoji(r.band)} |")
    lines.append("")

    # --- Section 2: Scenario Scores ---
    lines.append("## Scenario Scores")
    lines.append("")
    lines.append("| ID | Title | Score | Band |")
    lines.append("|----|-------|-------|------|")
    for r in sorted(results, key=lambda r: r.avg_score):
        lines.append(
            f"| {r.scenario_id} | {r.title} | {r.avg_score:.1f} | {band_emoji(r.band)} |"
        )
    lines.append("")

    # --- Section 3: Calibration Check ---
    calibration = [r for r in results if r.scenario_id.startswith("CAL-")]
    if calibration:
        lines.append("## Calibration Check")
        lines.append("")
        for r in calibration:
            lines.append(f"**{r.scenario_id}: {r.title}** — Score: {r.avg_score:.1f} {band_emoji(r.band)}")
            for e in r.step_evaluations:
                lines.append(f"  - {e.persona_id}: {e.one_line_summary}")
        lines.append("")

    # --- Section 4: Step-by-Step Details ---
    lines.append("## Step-by-Step Details")
    lines.append("")
    for r in results:
        if r.scenario_id.startswith("CAL-"):
            continue  # Already shown above
        lines.append(f"### {r.scenario_id}: {r.title}")
        lines.append(f"Overall: {r.avg_score:.1f} {band_emoji(r.band)}")
        lines.append("")

        for e in r.step_evaluations:
            step_band = score_to_band(e.avg_dimension_score)
            lines.append(f"**Step {e.step_id}** ({e.persona_id}) — {e.avg_dimension_score:.1f} {band_emoji(step_band)}")
            lines.append(f"  {e.one_line_summary}")

            # Show dimension scores
            for dim_name, dim_score in e.dimension_scores.items():
                if dim_score.score is not None:
                    lines.append(f"  - {dim_name}: {dim_score.score:.0f}/5 — {dim_score.reasoning}")

            # Show improvement suggestions
            if e.improvement_suggestions:
                lines.append("  **Improvements:**")
                for suggestion in e.improvement_suggestions:
                    lines.append(f"  - {suggestion}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # --- Section 5: Improvement Backlog ---
    lines.append("## Improvement Backlog")
    lines.append("")
    lines.append("All suggestions from the evaluator, grouped by frequency:")
    lines.append("")

    all_suggestions = []
    for r in results:
        all_suggestions.extend(r.all_suggestions)

    # Deduplicate by counting similar suggestions
    suggestion_counts = {}
    for s in all_suggestions:
        # Simple dedup — lowercase first 50 chars
        key = s.lower()[:50]
        if key not in suggestion_counts:
            suggestion_counts[key] = {"text": s, "count": 0}
        suggestion_counts[key]["count"] += 1

    for item in sorted(suggestion_counts.values(), key=lambda x: -x["count"]):
        count_str = f" (x{item['count']})" if item["count"] > 1 else ""
        lines.append(f"- {item['text']}{count_str}")
    lines.append("")

    report_text = "\n".join(lines)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)

    return report_text
