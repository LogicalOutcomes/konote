"""Generate satisfaction reports from scenario evaluation results.

Reports follow the gap-first format: headlines are about experience
gaps between personas, not average scores.

QA-T10: Reports now show objective scores alongside LLM scores,
flagging divergences where they disagree.
"""
from datetime import datetime

from .score_models import DIMENSIONS, ScenarioResult, band_emoji, score_to_band


def _overall_traffic_light(results):
    """Determine overall traffic-light colour from results."""
    if not results:
        return "RED"
    scores = [r.avg_score for r in results if r.avg_score > 0]
    if not scores:
        return "RED"
    avg = sum(scores) / len(scores)
    # Any blocker = RED, any orange = YELLOW at best
    has_blocker = any(r.band == "red" for r in results)
    has_fix = any(r.band == "orange" for r in results)
    if has_blocker:
        return "RED"
    if has_fix or avg < 4.0:
        return "YELLOW"
    return "GREEN"


def _generate_traffic_light_summary(results):
    """Generate the traffic-light summary section for the top of the report."""
    from .score_models import TASK_OUTCOMES

    lines = []
    now = datetime.now().strftime("%Y-%m-%d")
    colour = _overall_traffic_light(results)

    lines.append(f"## EVALUATION SUMMARY — {now} — {colour}")
    lines.append("")

    total = len(results)
    scored = [r for r in results if r.avg_score > 0]
    blocked = [r for r in results if any(
        e.is_blocked for e in r.step_evaluations
    )]
    lines.append(f"Scenarios scored: {len(scored)}/{total}")
    if blocked:
        lines.append(f"Blocked (skipped): {len(blocked)}")
    lines.append("")

    # Task outcome counts (using ScenarioResult.task_outcome_counts)
    outcome_counts = {}
    for r in results:
        for outcome, count in r.task_outcome_counts.items():
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + count
    total_outcomes = sum(outcome_counts.values())

    if outcome_counts:
        lines.append("TASK OUTCOMES:")
        for outcome in TASK_OUTCOMES:
            count = outcome_counts.get(outcome, 0)
            pct = f" ({count * 100 // total_outcomes}%)" if total_outcomes else ""
            label = outcome.replace("_", " ").title()
            lines.append(f"  {label}: {count} scenarios{pct}")
        lines.append("")

    # Top concerns (abandoned + error_unnoticed scenarios)
    concerns = []
    for r in results:
        for e in r.step_evaluations:
            if e.task_outcome in ("abandoned", "error_unnoticed"):
                concerns.append((r.title, e.persona_id, e.task_outcome, e.task_outcome_reasoning))
    if concerns:
        lines.append("TOP CONCERNS:")
        for title, persona, outcome, reason in concerns[:5]:
            lines.append(f"  - {title} — {persona} would {outcome.replace('_', ' ')} ({reason})")
        lines.append("")

    return lines


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

    # --- Traffic-light summary (QA enrichment) ---
    lines.extend(_generate_traffic_light_summary(results))
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

    # --- Section 3: Objective Scoring Summary (QA-T10) ---
    lines.append("## Objective Scores")
    lines.append("")
    lines.append("Dimensions scored by measurement (not LLM): accessibility")
    lines.append("(axe-core), efficiency (action count), language (doc lang).")
    lines.append("")

    has_objective = False
    for r in results:
        for e in r.step_evaluations:
            if e.objective_scores:
                has_objective = True
                break
        if has_objective:
            break

    if has_objective:
        lines.append("| Scenario | Step | Dimension | Objective | LLM | Divergence |")
        lines.append("|----------|------|-----------|-----------|-----|------------|")
        for r in results:
            for e in r.step_evaluations:
                for dim_name, obj_score in e.objective_scores.items():
                    if obj_score.score is None:
                        continue
                    llm_score = e.dimension_scores.get(dim_name)
                    llm_val = f"{llm_score.score:.0f}" if llm_score and llm_score.score is not None else "—"
                    obj_val = f"{obj_score.score:.0f}"
                    # Flag significant divergence (>= 2 points)
                    divergence = ""
                    if llm_score and llm_score.score is not None:
                        diff = abs(obj_score.score - llm_score.score)
                        if diff >= 2.0:
                            divergence = f"**{diff:.0f}pt gap**"
                        elif diff >= 1.0:
                            divergence = f"{diff:.0f}pt"
                    lines.append(
                        f"| {r.scenario_id} | {e.step_id} | {dim_name} "
                        f"| {obj_val} | {llm_val} | {divergence} |"
                    )
        lines.append("")
    else:
        lines.append("*No objective scores recorded (axe-core may not have run).*")
        lines.append("")

    # --- Section 4: Calibration Check ---
    calibration = [r for r in results if r.scenario_id.startswith("CAL-")]
    if calibration:
        lines.append("## Calibration Check")
        lines.append("")
        for r in calibration:
            lines.append(f"**{r.scenario_id}: {r.title}** — Score: {r.avg_score:.1f} {band_emoji(r.band)}")
            for e in r.step_evaluations:
                lines.append(f"  - {e.persona_id}: {e.one_line_summary}")
        lines.append("")

    # --- Section 5: Step-by-Step Details ---
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
            if e.task_outcome:
                lines.append(f"  Task outcome: **{e.task_outcome}** — {e.task_outcome_reasoning}")

            # Show effective dimension scores (objective overrides LLM)
            for dim_name, dim_score in e.effective_dimension_scores.items():
                if dim_score.score is None:
                    continue
                # Mark objective-sourced scores
                source = ""
                if dim_name in e.objective_scores:
                    obj = e.objective_scores[dim_name]
                    if obj.score is not None:
                        source = " [objective]"
                lines.append(f"  - {dim_name}: {dim_score.score:.0f}/5{source} — {dim_score.reasoning}")

            # Show improvement suggestions
            if e.improvement_suggestions:
                lines.append("  **Improvements:**")
                for suggestion in e.improvement_suggestions:
                    lines.append(f"  - {suggestion}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # --- Section 6: Improvement Backlog ---
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
