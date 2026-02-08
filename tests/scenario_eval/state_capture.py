"""Capture page state at each scenario step for LLM evaluation."""
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class StepCapture:
    """All captured state from a single scenario step."""

    scenario_id: str
    step_id: int
    actor_persona: str
    url: str = ""
    status_code: int = 0
    page_title: str = ""
    page_html: str = ""
    visible_text: str = ""
    screenshot_path: str = ""
    console_errors: list = field(default_factory=list)
    axe_violations: list = field(default_factory=list)
    axe_violation_count: int = 0
    load_time_ms: int = 0
    heading_hierarchy: list = field(default_factory=list)
    aria_live_regions: list = field(default_factory=list)
    interactive_element_count: int = 0
    focus_element: str = ""

    # Browser console output (QA-W2)
    console_log: list = field(default_factory=list)

    # Duplicate screenshot detection (QA-W3)
    is_duplicate: bool = False

    # Round 3: extra captures for mobile, a11y tree, and bilingual scenarios
    accessibility_tree: dict = field(default_factory=dict)
    has_horizontal_scroll: bool = False
    document_lang: str = ""
    viewport_width: int = 0


def _url_to_slug(url, max_length=60):
    """Convert a URL into a short, filesystem-safe slug for screenshot filenames.

    Examples:
        http://localhost:8000/clients/          → 'clients'
        http://localhost:8000/clients/executive/ → 'clients-executive'
        http://localhost:8000/clients/42/notes/  → 'clients-42-notes'
        http://localhost:8000/admin/settings/    → 'admin-settings'
        http://localhost:8000/                   → 'home'
    """
    path = urlparse(url).path.strip("/")
    if not path:
        return "home"
    # Replace path separators with hyphens
    slug = path.replace("/", "-")
    # Remove anything that isn't alphanumeric, hyphen, or underscore
    slug = re.sub(r"[^a-zA-Z0-9_-]", "", slug)
    # Collapse multiple hyphens
    slug = re.sub(r"-{2,}", "-", slug)
    # Truncate to keep filenames reasonable
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "home"


def capture_step_state(page, scenario_id, step_id, actor_persona,
                       screenshot_dir=None, run_axe_fn=None,
                       previous_screenshot_path=None):
    """Capture the full state of the page after a step executes.

    Args:
        page: Playwright page object.
        scenario_id: ID of the scenario (e.g., 'SCN-010').
        step_id: Step number within the scenario.
        actor_persona: Persona ID (e.g., 'DS1').
        screenshot_dir: Directory to save screenshots (optional).
        run_axe_fn: Callable that runs axe-core and returns results (optional).
        previous_screenshot_path: Path to the previous step's screenshot for
            duplicate detection (optional). If provided and the new screenshot
            is byte-identical, sets is_duplicate=True and renames the file.

    Returns:
        StepCapture dataclass with all captured data.
    """
    capture = StepCapture(
        scenario_id=scenario_id,
        step_id=step_id,
        actor_persona=actor_persona,
    )

    # Basic page info
    capture.url = page.url
    capture.page_title = page.title()

    # Page HTML (trimmed — remove scripts and styles for LLM)
    capture.page_html = page.evaluate("""() => {
        const clone = document.documentElement.cloneNode(true);
        clone.querySelectorAll('script, style, link[rel="stylesheet"]')
             .forEach(el => el.remove());
        return clone.outerHTML.substring(0, 50000);
    }""")

    # Visible text only (what a user would read)
    capture.visible_text = page.evaluate("""() => {
        const main = document.querySelector('main') || document.body;
        return main.innerText.substring(0, 10000);
    }""")

    # Heading hierarchy
    capture.heading_hierarchy = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'))
             .map(h => ({
                 level: parseInt(h.tagName[1]),
                 text: h.textContent.trim().substring(0, 100)
             }));
    }""")

    # ARIA live regions
    capture.aria_live_regions = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('[aria-live]'))
             .map(el => ({
                 politeness: el.getAttribute('aria-live'),
                 text: el.textContent.trim().substring(0, 200),
                 id: el.id || null
             }));
    }""")

    # Interactive element count
    capture.interactive_element_count = page.evaluate("""() => {
        return document.querySelectorAll(
            'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
        ).length;
    }""")

    # Current focus element
    capture.focus_element = page.evaluate("""() => {
        const el = document.activeElement;
        if (!el || el === document.body) return 'body';
        const tag = el.tagName.toLowerCase();
        const id = el.id ? '#' + el.id : '';
        const label = el.getAttribute('aria-label') || '';
        return `${tag}${id} ${label}`.trim();
    }""")

    # Horizontal scroll detection (for mobile viewport scenarios)
    capture.has_horizontal_scroll = page.evaluate("""() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    }""")

    # Document language attribute (for bilingual scenarios)
    capture.document_lang = page.evaluate(
        "() => document.documentElement.lang || ''"
    )

    # Viewport width (for responsive scenarios)
    capture.viewport_width = page.evaluate(
        "() => window.innerWidth"
    )

    # Accessibility tree snapshot (for screen reader scenarios)
    try:
        capture.accessibility_tree = page.accessibility.snapshot() or {}
    except Exception:
        pass  # Some pages may not support accessibility snapshots

    # Screenshot — filename includes URL slug for route traceability (QA-T20)
    if screenshot_dir:
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
        slug = _url_to_slug(capture.url)
        filename = f"{scenario_id}_step{step_id}_{actor_persona}_{slug}.png"
        capture.screenshot_path = os.path.join(screenshot_dir, filename)
        page.screenshot(path=capture.screenshot_path, full_page=True)

        # Duplicate screenshot detection (QA-W3)
        if previous_screenshot_path and Path(previous_screenshot_path).is_file():
            try:
                current_bytes = Path(capture.screenshot_path).read_bytes()
                previous_bytes = Path(previous_screenshot_path).read_bytes()
                if current_bytes == previous_bytes:
                    capture.is_duplicate = True
                    print(
                        f"WARNING: {scenario_id} step {step_id} screenshot "
                        f"identical to previous step — action may not have "
                        f"executed"
                    )
                    # Rename to flag the duplicate visually in the output dir
                    dup_filename = (
                        f"{scenario_id}_step{step_id}_{actor_persona}"
                        f"_{slug}_DUPLICATE.png"
                    )
                    dup_path = os.path.join(screenshot_dir, dup_filename)
                    Path(capture.screenshot_path).rename(dup_path)
                    capture.screenshot_path = dup_path
            except OSError:
                pass  # If file read fails, skip detection silently

    # Axe-core accessibility check
    if run_axe_fn:
        try:
            axe_results = run_axe_fn()
            violations = axe_results.get("violations", [])
            capture.axe_violations = [
                {
                    "id": v["id"],
                    "impact": v.get("impact", "unknown"),
                    "description": v.get("description", ""),
                    "nodes_count": len(v.get("nodes", [])),
                }
                for v in violations
            ]
            capture.axe_violation_count = len(violations)
        except Exception:
            pass  # Axe injection can fail on some pages

    return capture


def capture_to_evaluation_context(capture, persona_description=""):
    """Format a StepCapture into a text block for LLM evaluation.

    Returns a string suitable for including in the evaluation prompt.
    """
    headings_str = "\n".join(
        f"  {'  ' * (h['level'] - 1)}h{h['level']}: {h['text']}"
        for h in capture.heading_hierarchy
    )

    live_regions_str = "\n".join(
        f"  [{r['politeness']}] {r['text'][:100]}"
        for r in capture.aria_live_regions
    ) or "  (none)"

    axe_str = "\n".join(
        f"  [{v['impact']}] {v['description']} ({v['nodes_count']} nodes)"
        for v in capture.axe_violations
    ) or "  (none)"

    # Accessibility tree summary (for screen reader scenarios)
    a11y_tree_str = ""
    if capture.accessibility_tree:
        a11y_tree_str = _format_a11y_tree(capture.accessibility_tree, depth=0)

    # Extra metadata for mobile and bilingual scenarios
    extra_meta = ""
    if capture.viewport_width:
        extra_meta += f"Viewport width: {capture.viewport_width}px\n"
    if capture.has_horizontal_scroll:
        extra_meta += "Horizontal scroll: YES (content overflows viewport)\n"
    if capture.document_lang:
        extra_meta += f"Document language: {capture.document_lang}\n"

    # Browser console output (QA-W2)
    console_str = ""
    if capture.console_log:
        console_lines = capture.console_log[:50]  # Cap at 50 lines for LLM
        console_str = "\n".join(f"  {line}" for line in console_lines)
        if len(capture.console_log) > 50:
            console_str += f"\n  ... ({len(capture.console_log) - 50} more lines)"

    # Duplicate screenshot warning (QA-W3)
    duplicate_warning = ""
    if capture.is_duplicate:
        duplicate_warning = (
            "\n**DUPLICATE: This screenshot is identical to the previous "
            "step — the action may not have executed.**\n"
        )

    return f"""## Page State After Step {capture.step_id}
{duplicate_warning}
URL: {capture.url}
Page title: {capture.page_title}
Interactive elements on page: {capture.interactive_element_count}
Current focus: {capture.focus_element}
Axe-core violations: {capture.axe_violation_count}
{extra_meta}
### Heading Hierarchy
{headings_str or '  (no headings found)'}

### ARIA Live Regions
{live_regions_str}

### Accessibility Violations
{axe_str}
{"" if not a11y_tree_str else f'''
### Accessibility Tree (Screen Reader View)
{a11y_tree_str}
'''}{"" if not console_str else f'''### Browser Console Output
{console_str}

'''}### Visible Text Content
{capture.visible_text[:5000]}
"""


def _format_a11y_tree(node, depth=0):
    """Format a Playwright accessibility tree snapshot into readable text.

    Shows the tree structure that a screen reader like JAWS would navigate:
    roles, names, and states. Truncated to keep LLM context manageable.
    """
    if not node:
        return ""

    indent = "  " * depth
    role = node.get("role", "")
    name = node.get("name", "")
    value = node.get("value", "")

    parts = [role]
    if name:
        parts.append(f'"{name}"')
    if value:
        parts.append(f'[value: {value}]')

    lines = [f"{indent}{' '.join(parts)}"]

    # Recurse into children (limit depth to keep output manageable)
    if depth < 4:
        for child in node.get("children", []):
            lines.append(_format_a11y_tree(child, depth + 1))

    # Truncate total output to avoid overwhelming the LLM
    result = "\n".join(lines)
    if len(result) > 5000:
        result = result[:5000] + "\n  ... (truncated)"
    return result
