"""Serialize ScenarioResult objects to JSON-friendly dicts.

Used by conftest.py to write machine-readable results alongside the
markdown report. Scripts like qa_gate.py and track_satisfaction.py
read this JSON instead of parsing markdown.
"""
import json
from datetime import datetime

from .score_models import score_to_band


def _serialize_dimension_score(ds):
    """Convert a DimensionScore to a dict."""
    return {
        "score": ds.score,
        "reasoning": ds.reasoning,
    }


def _serialize_step(step_eval):
    """Convert a StepEvaluation to a dict."""
    return {
        "step_id": step_eval.step_id,
        "persona_id": step_eval.persona_id,
        "scenario_id": step_eval.scenario_id,
        "avg_dimension_score": round(step_eval.avg_dimension_score, 2),
        "overall_satisfaction": step_eval.overall_satisfaction,
        "one_line_summary": step_eval.one_line_summary,
        "improvement_suggestions": list(step_eval.improvement_suggestions),
        "dimension_scores": {
            dim: _serialize_dimension_score(ds)
            for dim, ds in step_eval.dimension_scores.items()
        },
        "objective_scores": {
            dim: _serialize_dimension_score(ds)
            for dim, ds in step_eval.objective_scores.items()
        },
        "effective_scores": {
            dim: _serialize_dimension_score(ds)
            for dim, ds in step_eval.effective_dimension_scores.items()
        },
    }


def _serialize_scenario(result):
    """Convert a ScenarioResult to a dict."""
    return {
        "scenario_id": result.scenario_id,
        "title": result.title,
        "avg_score": round(result.avg_score, 2),
        "band": result.band,
        "satisfaction_gap": round(result.satisfaction_gap, 2),
        "per_persona_scores": {
            pid: round(score, 2)
            for pid, score in result.per_persona_scores().items()
        },
        "steps": [_serialize_step(e) for e in result.step_evaluations],
    }


def serialize_results(results):
    """Convert a list of ScenarioResult objects to a JSON-serializable dict.

    Args:
        results: List of ScenarioResult objects.

    Returns:
        Dict ready for json.dump().
    """
    scenarios = [_serialize_scenario(r) for r in results]

    # Build summary
    blockers = [s["scenario_id"] for s in scenarios if s["band"] == "red"]
    all_scores = [s["avg_score"] for s in scenarios if s["avg_score"] > 0]
    all_gaps = [s["satisfaction_gap"] for s in scenarios]

    summary = {
        "total_scenarios": len(scenarios),
        "has_blocker": len(blockers) > 0,
        "blockers": blockers,
        "avg_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0,
        "worst_gap": round(max(all_gaps), 2) if all_gaps else 0,
    }

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "version": 1,
        "scenarios": scenarios,
        "summary": summary,
    }


def write_results_json(results, output_path):
    """Serialize results and write to a JSON file.

    Args:
        results: List of ScenarioResult objects.
        output_path: Path to write the JSON file.
    """
    data = serialize_results(results)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
