"""Load persona and scenario YAML files from the holdout directory.

Caches parsed YAML in module-level dicts so files are only read once
per test session (scenarios and personas don't change during a run).
"""
import os
from pathlib import Path

import yaml

# Module-level caches — populated on first call, reused for the session.
_personas_cache = {}      # holdout_dir_str -> personas dict
_all_scenarios_cache = {}  # holdout_dir_str -> [(path, scenario_dict), ...]


def get_holdout_dir():
    """Return the holdout directory path from env or settings."""
    holdout = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
    if not holdout:
        from django.conf import settings
        default = str(settings.BASE_DIR.parent / "konote-qa-scenarios")
        holdout = getattr(settings, "SCENARIO_HOLDOUT_DIR", default)
    if not holdout:
        return None
    p = Path(holdout)
    return p if p.is_dir() else None


def load_personas(holdout_dir=None):
    """Load all persona definitions from the holdout directory.

    Returns a dict mapping persona ID (e.g., 'DS1') to its full definition.
    Results are cached per holdout directory for the session.
    """
    holdout = holdout_dir or get_holdout_dir()
    if not holdout:
        return {}

    cache_key = str(holdout)
    if cache_key in _personas_cache:
        return _personas_cache[cache_key]

    personas_dir = Path(holdout) / "personas"
    if not personas_dir.is_dir():
        _personas_cache[cache_key] = {}
        return {}

    all_personas = {}
    for yaml_file in sorted(personas_dir.glob("*.yaml")):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data and "personas" in data:
            all_personas.update(data["personas"])

    _personas_cache[cache_key] = all_personas
    return all_personas


def load_scenario(scenario_path):
    """Load a single scenario YAML file.

    Returns the parsed scenario dict.
    """
    with open(scenario_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_all_scenarios(holdout_dir):
    """Load and cache ALL scenarios from the holdout directory.

    Called once per session; discover_scenarios() filters from this cache.
    """
    cache_key = str(holdout_dir)
    if cache_key in _all_scenarios_cache:
        return _all_scenarios_cache[cache_key]

    scenarios_dir = Path(holdout_dir) / "scenarios"
    if not scenarios_dir.is_dir():
        _all_scenarios_cache[cache_key] = []
        return []

    search_dirs = [scenarios_dir]
    ditl_dir = Path(holdout_dir) / "day-in-the-life"
    if ditl_dir.is_dir():
        search_dirs.append(ditl_dir)

    results = []
    for search_dir in search_dirs:
        for yaml_file in sorted(search_dir.rglob("*.yaml")):
            scenario = load_scenario(yaml_file)
            if not scenario or "id" not in scenario:
                continue
            results.append((yaml_file, scenario))

    results.sort(key=lambda x: x[1]["id"])
    _all_scenarios_cache[cache_key] = results
    return results


def discover_scenarios(holdout_dir=None, tags=None, ids=None):
    """Discover scenario YAML files in the holdout directory.

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

    all_scenarios = _load_all_scenarios(holdout)

    # No filters — return everything
    if not tags and not ids:
        return list(all_scenarios)

    results = []
    ids_set = set(ids) if ids else None
    for path, scenario in all_scenarios:
        if ids_set and scenario["id"] not in ids_set:
            continue
        if tags:
            scenario_tags = scenario.get("tags", [])
            if not any(t in scenario_tags for t in tags):
                continue
        results.append((path, scenario))

    return results
