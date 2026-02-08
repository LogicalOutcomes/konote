"""Load persona and scenario YAML files from the holdout directory."""
import os
from pathlib import Path

import yaml


def get_holdout_dir():
    """Return the holdout directory path from env or settings."""
    holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
    if not holdout:
        from django.conf import settings
        holdout = getattr(settings, "SCENARIO_HOLDOUT_DIR", "")
    if not holdout:
        return None
    p = Path(holdout)
    return p if p.is_dir() else None


def load_personas(holdout_dir=None):
    """Load all persona definitions from the holdout directory.

    Returns a dict mapping persona ID (e.g., 'DS1') to its full definition.
    """
    holdout = holdout_dir or get_holdout_dir()
    if not holdout:
        return {}
    personas_dir = Path(holdout) / "personas"
    if not personas_dir.is_dir():
        return {}

    all_personas = {}
    for yaml_file in sorted(personas_dir.glob("*.yaml")):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data and "personas" in data:
            all_personas.update(data["personas"])
    return all_personas


def load_scenario(scenario_path):
    """Load a single scenario YAML file.

    Returns the parsed scenario dict.
    """
    with open(scenario_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def discover_scenarios(holdout_dir=None, tags=None, ids=None):
    """Discover all scenario YAML files in the holdout directory.

    Args:
        holdout_dir: Path to the holdout repo (uses env if not given).
        tags: Optional list of tags to filter by.
        ids: Optional list of scenario IDs to filter by (e.g., ['CAL-001']).

    Returns:
        List of (path, scenario_dict) tuples, sorted by ID.
    """
    holdout = holdout_dir or get_holdout_dir()
    if not holdout:
        return []
    scenarios_dir = Path(holdout) / "scenarios"
    if not scenarios_dir.is_dir():
        return []

    # Search scenarios/ and day-in-the-life/ directories
    search_dirs = [scenarios_dir]
    ditl_dir = Path(holdout) / "day-in-the-life"
    if ditl_dir.is_dir():
        search_dirs.append(ditl_dir)

    results = []
    for search_dir in search_dirs:
        for yaml_file in sorted(search_dir.rglob("*.yaml")):
            scenario = load_scenario(yaml_file)
            if not scenario or "id" not in scenario:
                continue

            # Filter by ID
            if ids and scenario["id"] not in ids:
                continue

            # Filter by tags
            if tags:
                scenario_tags = scenario.get("tags", [])
                if not any(t in scenario_tags for t in tags):
                    continue

            results.append((yaml_file, scenario))

    return sorted(results, key=lambda x: x[1]["id"])
