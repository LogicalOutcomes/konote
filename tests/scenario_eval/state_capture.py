"""Capture page state at each scenario step for LLM evaluation."""
import os
import time
from dataclasses import dataclass, field
from pathlib import Path


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


def capture_step_state(page, scenario_id, step_id, actor_persona,
                       screenshot_dir=None, run_axe_fn=None):
    """Capture the full state of the page after a step executes.

    Args:
        page: Playwright page object.
        scenario_id: ID of the scenario (e.g., 'SCN-010').
        step_id: Step number within the scenario.
        actor_persona: Persona ID (e.g., 'DS1').
        screenshot_dir: Directory to save screenshots (optional).
        run_axe_fn: Callable that runs axe-core and returns results (optional).

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

    # Screenshot
    if screenshot_dir:
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
        filename = f"{scenario_id}_step{step_id}_{actor_persona}.png"
        capture.screenshot_path = os.path.join(screenshot_dir, filename)
        page.screenshot(path=capture.screenshot_path, full_page=True)

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

    return f"""## Page State After Step {capture.step_id}

URL: {capture.url}
Page title: {capture.page_title}
Interactive elements on page: {capture.interactive_element_count}
Current focus: {capture.focus_element}
Axe-core violations: {capture.axe_violation_count}

### Heading Hierarchy
{headings_str or '  (no headings found)'}

### ARIA Live Regions
{live_regions_str}

### Accessibility Violations
{axe_str}

### Visible Text Content
{capture.visible_text[:5000]}
"""
