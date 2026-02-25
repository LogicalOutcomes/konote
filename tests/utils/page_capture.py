"""
Shared utilities for page state capture (QA page audit).

Captures screenshots of every KoNote page for every authorized persona
at multiple breakpoints. Screenshots feed into the /run-page-audit skill
in the konote-qa-scenarios repo.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Paths — relative to this file's location
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent  # konote-web/
QA_REPO = _PROJECT_ROOT.parent / "konote-qa-scenarios"
PAGE_INVENTORY_PATH = QA_REPO / "pages" / "page-inventory.yaml"
SCREENSHOT_DIR = QA_REPO / "reports" / "screenshots" / "pages"
MANIFEST_PATH = SCREENSHOT_DIR / ".pages-manifest.json"
AXE_REPORT_PATH = SCREENSHOT_DIR / "axe-a11y-report.json"

# ---------------------------------------------------------------------------
# Persona → test username mapping
# ---------------------------------------------------------------------------
# Source: qa-scenarios persona YAMLs + scenario_runner.py _create_test_data()

PERSONA_MAP = {
    "R1": "frontdesk",
    "R2": "frontdesk2",
    "R2-FR": "frontdesk_fr",
    "DS1": "staff",
    "DS1b": "staff_new",
    "DS1c": "staff_adhd",
    "DS2": "staff_fr",
    "DS3": "staff_a11y",
    "DS4": "staff_voice",
    "E1": "executive",
    "E2": "admin2",
    "PM1": "manager",
    "admin": "admin",
}

# States that Phase 1 can capture (just navigation, no form interaction)
PHASE1_STATES = {"default", "populated"}


# ---------------------------------------------------------------------------
# Page inventory
# ---------------------------------------------------------------------------

def load_page_inventory():
    """Load page-inventory.yaml from the qa-scenarios repo.

    Returns:
        list[dict]: List of page entries from the YAML.
    """
    with open(PAGE_INVENTORY_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("pages", [])


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------

# Matches Django-style URL placeholders like <int:client_id> or <slug:slug>
_PLACEHOLDER_RE = re.compile(r"<(?:int|slug):(\w+)>")


def resolve_url_pattern(pattern, test_data):
    """Replace <int:xxx> / <slug:xxx> placeholders with real values.

    Args:
        pattern: URL pattern, e.g. "/participants/<int:client_id>/edit/"
        test_data: dict mapping placeholder names to values,
                   e.g. {"client_id": 42, "note_id": 7, "slug": "intake"}

    Returns:
        Resolved URL string, or None if a placeholder can't be resolved.
    """
    def _replace(match):
        name = match.group(1)
        value = test_data.get(name)
        if value is None:
            raise KeyError(name)
        return str(value)

    try:
        return _PLACEHOLDER_RE.sub(_replace, pattern)
    except KeyError:
        return None


# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------

_BREAKPOINTS = {
    "1366x768": (1366, 768),
    "1920x1080": (1920, 1080),
    "375x667": (375, 667),
}


def capture_page_screenshot(page, filepath, breakpoint_str):
    """Set viewport and capture a full-page screenshot.

    Args:
        page: Playwright Page object.
        filepath: Full path to save the PNG.
        breakpoint_str: Size string like "1366x768".
    """
    width, height = _BREAKPOINTS[breakpoint_str]
    page.set_viewport_size({"width": width, "height": height})

    # Let HTMX requests and animations settle
    page.wait_for_timeout(500)

    # Full-page screenshot with timeout fallback
    try:
        page.screenshot(path=str(filepath), full_page=True, timeout=10000)
    except Exception:
        # Fall back to viewport-only if full-page hangs (HTMX polling, etc.)
        page.screenshot(path=str(filepath), full_page=False, timeout=10000)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def write_manifest(manifest_data):
    """Write the .pages-manifest.json file.

    Args:
        manifest_data: dict to serialise as JSON.
    """
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, default=str)


def new_manifest():
    """Return a fresh manifest dict with default structure."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pages_captured": 0,
        "personas_tested": [],
        "states_captured": [],
        "breakpoints": list(_BREAKPOINTS.keys()),
        "total_screenshots": 0,
        "axe_total_scans": 0,
        "axe_pages_with_violations": 0,
        "axe_total_violations": 0,
        "skipped": [],
        "missing_screenshots": [],
        "pages": [],
    }


# ---------------------------------------------------------------------------
# Expand special persona tokens
# ---------------------------------------------------------------------------

def expand_personas(authorized_personas):
    """Expand special persona tokens to concrete persona IDs.

    "all_authenticated" → all personas in PERSONA_MAP
    "all" → all personas in PERSONA_MAP
    "unauthenticated" → kept as-is (handled by caller)

    Returns:
        list[str] of persona IDs.
    """
    expanded = []
    for p in authorized_personas:
        if p in ("all_authenticated", "all"):
            expanded.extend(PERSONA_MAP.keys())
        else:
            expanded.append(p)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for p in expanded:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Axe-core accessibility scanning
# ---------------------------------------------------------------------------

def run_axe_for_page(run_axe_fn):
    """Run axe-core on the current page and return compact results.

    Args:
        run_axe_fn: Callable that injects axe (if needed) and returns
                    the raw axe results dict (e.g. BrowserTestBase.run_axe).

    Returns:
        dict with keys: violation_count (int), violations (list of dicts),
        and optionally error (str) if axe failed.
    """
    try:
        raw = run_axe_fn()
        violations = raw.get("violations", [])
        compact = [
            {
                "id": v["id"],
                "impact": v.get("impact", "unknown"),
                "description": v.get("description", ""),
                "help_url": v.get("helpUrl", ""),
                "nodes_count": len(v.get("nodes", [])),
            }
            for v in violations
        ]
        return {"violation_count": len(compact), "violations": compact}
    except Exception as exc:
        return {"violation_count": 0, "violations": [], "error": str(exc)}


def write_axe_report(scan_results, timestamp):
    """Write the standalone axe-a11y-report.json file.

    Groups violations by rule type across all pages, sorted by severity.
    Written alongside the manifest in the screenshots directory.

    Args:
        scan_results: list of dicts, each with keys:
            page_id, persona, state, violation_count, violations,
            error (optional).
        timestamp: ISO timestamp string.
    """
    by_rule = {}
    clean_pages = set()
    error_pages = []
    pages_with_violations = set()

    for scan in scan_results:
        if scan.get("error"):
            error_pages.append({
                "page_id": scan["page_id"],
                "persona": scan["persona"],
                "state": scan["state"],
                "error": scan["error"],
            })
            continue

        if scan["violation_count"] == 0:
            clean_pages.add(scan["page_id"])
        else:
            pages_with_violations.add(scan["page_id"])

        for v in scan["violations"]:
            rule_id = v["id"]
            if rule_id not in by_rule:
                by_rule[rule_id] = {
                    "rule_id": rule_id,
                    "impact": v["impact"],
                    "description": v["description"],
                    "help_url": v.get("help_url", ""),
                    "affected_pages": [],
                    "total_nodes": 0,
                }
            by_rule[rule_id]["affected_pages"].append({
                "page_id": scan["page_id"],
                "persona": scan["persona"],
                "state": scan["state"],
                "nodes_count": v["nodes_count"],
            })
            by_rule[rule_id]["total_nodes"] += v["nodes_count"]

    # Sort by impact severity, then by total affected nodes descending
    impact_order = {
        "critical": 0, "serious": 1, "moderate": 2, "minor": 3, "unknown": 4,
    }
    summary = sorted(
        by_rule.values(),
        key=lambda r: (impact_order.get(r["impact"], 4), -r["total_nodes"]),
    )
    for entry in summary:
        entry["total_affected_pages"] = len(entry["affected_pages"])

    # Pages clean across ALL scans (no violations in any persona/state)
    truly_clean = clean_pages - pages_with_violations

    report = {
        "timestamp": timestamp,
        "total_scans": len(scan_results),
        "total_pages_scanned": len({s["page_id"] for s in scan_results}),
        "pages_with_violations": len(pages_with_violations),
        "violation_summary": summary,
        "clean_pages": sorted(truly_clean),
        "scan_errors": error_pages,
    }

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with open(AXE_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
