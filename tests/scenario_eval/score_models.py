"""Score dataclasses and aggregation for satisfaction evaluation."""
from dataclasses import dataclass, field
from statistics import mean, stdev


# The 7 satisfaction dimensions
DIMENSIONS = [
    "clarity",
    "efficiency",
    "feedback",
    "error_recovery",
    "accessibility",
    "language",
    "confidence",
]

# Score bands — report these, not raw decimals
BANDS = {
    "green": (4.0, 5.0, "No action needed"),
    "yellow": (3.0, 3.99, "Review recommended"),
    "orange": (2.0, 2.99, "Priority fix"),
    "red": (1.0, 1.99, "Blocker"),
}


@dataclass
class DimensionScore:
    """Score for a single dimension at a single step."""
    dimension: str
    score: float  # 1.0-5.0
    reasoning: str = ""


@dataclass
class StepEvaluation:
    """Full evaluation of a single scenario step."""
    scenario_id: str
    step_id: int
    persona_id: str
    dimension_scores: dict = field(default_factory=dict)  # dimension -> DimensionScore
    criteria_scores: dict = field(default_factory=dict)  # criterion text -> score
    overall_satisfaction: float = 0.0
    one_line_summary: str = ""
    improvement_suggestions: list = field(default_factory=list)

    @property
    def avg_dimension_score(self):
        """Average across all scored dimensions (skip None/N/A)."""
        scores = [
            ds.score for ds in self.dimension_scores.values()
            if ds.score is not None
        ]
        return mean(scores) if scores else 0.0

    @property
    def avg_criteria_score(self):
        """Average across custom satisfaction criteria."""
        scores = [s for s in self.criteria_scores.values() if s is not None]
        return mean(scores) if scores else 0.0


@dataclass
class ScenarioResult:
    """Aggregated result for an entire scenario."""
    scenario_id: str
    title: str
    step_evaluations: list = field(default_factory=list)  # list of StepEvaluation

    @property
    def avg_score(self):
        """Average score across all steps."""
        scores = [e.avg_dimension_score for e in self.step_evaluations if e.avg_dimension_score > 0]
        return mean(scores) if scores else 0.0

    @property
    def band(self):
        """Score band (green/yellow/orange/red)."""
        return score_to_band(self.avg_score)

    @property
    def all_suggestions(self):
        """All improvement suggestions across all steps."""
        suggestions = []
        for e in self.step_evaluations:
            suggestions.extend(e.improvement_suggestions)
        return suggestions

    def per_persona_scores(self):
        """Scores grouped by persona ID."""
        by_persona = {}
        for e in self.step_evaluations:
            if e.persona_id not in by_persona:
                by_persona[e.persona_id] = []
            by_persona[e.persona_id].append(e.avg_dimension_score)
        return {pid: mean(scores) for pid, scores in by_persona.items() if scores}

    @property
    def satisfaction_gap(self):
        """Max score difference between personas on this scenario."""
        scores = self.per_persona_scores()
        if len(scores) < 2:
            return 0.0
        vals = list(scores.values())
        return max(vals) - min(vals)


def score_to_band(score):
    """Convert a numeric score to a colour band."""
    if score >= 4.0:
        return "green"
    elif score >= 3.0:
        return "yellow"
    elif score >= 2.0:
        return "orange"
    else:
        return "red"


def band_emoji(band):
    """Return a text marker for the band (no actual emojis)."""
    return {
        "green": "[OK]",
        "yellow": "[REVIEW]",
        "orange": "[FIX]",
        "red": "[BLOCKER]",
    }.get(band, "[?]")


def check_stability(scores_across_runs):
    """Check if scores are stable across multiple runs.

    Args:
        scores_across_runs: list of float scores from repeated runs.

    Returns:
        (mean, stdev, is_stable) where is_stable means stdev < 0.5
    """
    if len(scores_across_runs) < 2:
        return scores_across_runs[0] if scores_across_runs else 0, 0, True
    m = mean(scores_across_runs)
    s = stdev(scores_across_runs)
    return m, s, s < 0.5
