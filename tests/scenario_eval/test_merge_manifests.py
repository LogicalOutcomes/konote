"""Unit tests for _merge_manifests in conftest.py."""

import pytest
from tests.scenario_eval.conftest import _merge_manifests


def _make_manifest(scenario_ids, personas=None, screenshots=None, files=None):
    """Helper to build a minimal manifest dict for testing."""
    scenarios = [
        {"scenario_id": sid, "title": f"Test {sid}", "steps": 3,
         "personas": personas or ["P1"], "avg_score": 4.0, "band": "good"}
        for sid in scenario_ids
    ]
    return {
        "generated_at": "2026-03-01T12:00:00+00:00",
        "version": 2,
        "scenarios_run": len(scenarios),
        "personas_tested": sorted(set(p for s in scenarios for p in s["personas"])),
        "total_steps": sum(s["steps"] for s in scenarios),
        "files_written": files or [f"{sid}_step1.png" for sid in scenario_ids],
        "screenshots": screenshots or {
            "total": len(scenario_ids), "valid": len(scenario_ids),
            "blank": 0, "duplicates": 0, "issues": [],
        },
        "scenarios": scenarios,
    }


class MergeManifestsTest:
    """Tests for _merge_manifests without filesystem (screenshot_dir=None)."""

    def test_partial_rerun_keeps_old_scenarios(self):
        """Scenarios not re-run should be preserved from the existing manifest."""
        existing = _make_manifest(["SC01", "SC02", "SC03"])
        partial = _make_manifest(["SC02"])

        merged = _merge_manifests(existing, partial)

        ids = [s["scenario_id"] for s in merged["scenarios"]]
        assert sorted(ids) == ["SC01", "SC02", "SC03"]
        assert merged["scenarios_run"] == 3

    def test_partial_rerun_replaces_rerun_scenario_data(self):
        """Re-run scenarios should use data from the new manifest."""
        existing = _make_manifest(["SC01", "SC02"])
        # Give SC02 a different score in the new run
        partial = _make_manifest(["SC02"])
        partial["scenarios"][0]["avg_score"] = 5.0

        merged = _merge_manifests(existing, partial)

        sc02 = next(s for s in merged["scenarios"] if s["scenario_id"] == "SC02")
        assert sc02["avg_score"] == 5.0

    def test_files_written_merges_correctly(self):
        """Old files for re-run scenarios should be replaced; others kept."""
        existing = _make_manifest(
            ["SC01", "SC02"],
            files=["SC01_step1.png", "SC01_step2.png", "SC02_step1.png"],
        )
        partial = _make_manifest(
            ["SC02"],
            files=["SC02_step1.png", "SC02_step2.png"],
        )

        merged = _merge_manifests(existing, partial)

        assert sorted(merged["files_written"]) == [
            "SC01_step1.png", "SC01_step2.png",
            "SC02_step1.png", "SC02_step2.png",
        ]

    def test_personas_merged(self):
        """Personas from both runs should be combined."""
        existing = _make_manifest(["SC01"], personas=["P1", "P2"])
        partial = _make_manifest(["SC02"], personas=["P2", "P3"])

        merged = _merge_manifests(existing, partial)

        assert merged["personas_tested"] == ["P1", "P2", "P3"]

    def test_total_steps_summed_from_merged_scenarios(self):
        """total_steps should reflect all merged scenarios, not just the new run."""
        existing = _make_manifest(["SC01", "SC02", "SC03"])  # 3 steps each = 9
        partial = _make_manifest(["SC02"])  # 3 steps

        merged = _merge_manifests(existing, partial)

        assert merged["total_steps"] == 9  # 3 scenarios × 3 steps

    def test_without_screenshot_dir_uses_new_manifest_screenshots(self):
        """Without screenshot_dir, screenshots fall back to new_manifest's stats."""
        existing = _make_manifest(
            ["SC01", "SC02"],
            screenshots={"total": 10, "valid": 9, "blank": 1, "duplicates": 0, "issues": []},
        )
        partial = _make_manifest(
            ["SC02"],
            screenshots={"total": 2, "valid": 2, "blank": 0, "duplicates": 0, "issues": []},
        )

        merged = _merge_manifests(existing, partial)

        # Without screenshot_dir, falls back to new_manifest's stats
        assert merged["screenshots"]["total"] == 2

    def test_version_and_timestamp_from_new_manifest(self):
        """Version and generated_at should come from the new manifest."""
        existing = _make_manifest(["SC01"])
        existing["generated_at"] = "2026-02-28T12:00:00+00:00"
        partial = _make_manifest(["SC01"])
        partial["generated_at"] = "2026-03-01T14:00:00+00:00"

        merged = _merge_manifests(existing, partial)

        assert merged["generated_at"] == "2026-03-01T14:00:00+00:00"
        assert merged["version"] == 2

    def test_scenarios_sorted_by_id(self):
        """Merged scenarios should be sorted by scenario_id."""
        existing = _make_manifest(["SC03", "SC01"])
        partial = _make_manifest(["SC02"])

        merged = _merge_manifests(existing, partial)

        ids = [s["scenario_id"] for s in merged["scenarios"]]
        assert ids == ["SC01", "SC02", "SC03"]
