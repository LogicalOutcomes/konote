"""Report generator — writes the UX walkthrough report as Markdown."""
import os
import re
from datetime import datetime

from .checker import Severity, UxIssue


class ReportGenerator:
    """Collects walkthrough results and writes a Markdown report."""

    def __init__(self):
        self.issues: list[UxIssue] = []
        self.pages_visited: int = 0
        self.steps_by_role: dict[str, list[dict]] = {}
        self.scenarios: dict[str, list[dict]] = {}
        self.browser_findings: dict[str, list[dict]] = {}

    def record_step(
        self,
        role: str,
        step: str,
        url: str,
        status_code: int,
        issues: list[UxIssue],
    ):
        """Record the outcome of a single walkthrough step."""
        self.pages_visited += 1
        self.issues.extend(issues)
        if role not in self.steps_by_role:
            self.steps_by_role[role] = []
        self.steps_by_role[role].append({
            "step": step,
            "url": url,
            "status_code": status_code,
            "issues": issues,
        })

    def record_scenario_step(
        self,
        scenario: str,
        role: str,
        step: str,
        url: str,
        status_code: int,
        issues: list[UxIssue],
    ):
        """Record a step belonging to a named scenario.

        Scenario steps appear in the 'Scenario Walkthroughs' section of
        the report, grouped by scenario name with acts listed in order.
        """
        self.pages_visited += 1
        self.issues.extend(issues)
        if scenario not in self.scenarios:
            self.scenarios[scenario] = []
        self.scenarios[scenario].append({
            "role": role,
            "step": step,
            "url": url,
            "status_code": status_code,
            "issues": issues,
        })

    def record_browser_finding(
        self,
        category: str,
        severity: str,
        url: str,
        description: str,
        detail: str = "",
    ):
        """Record a finding from a browser-based test (Playwright).

        Findings are grouped by category (e.g. "Colour Contrast",
        "Focus Management", "Responsive Layout") and also added to
        the main issues list for summary counts.
        """
        if category not in self.browser_findings:
            self.browser_findings[category] = []
        self.browser_findings[category].append({
            "severity": severity,
            "url": url,
            "description": description,
            "detail": detail,
        })
        # Add to main issues list so summary counts include browser findings
        self.issues.append(UxIssue(
            severity=Severity(severity),
            url=url,
            role="Browser",
            step=category,
            description=description,
            detail=detail,
        ))

    def _read_previous_counts(self, filepath: str) -> dict:
        """Read issue counts from a previous report file, if it exists."""
        counts = {"pages": 0, "critical": 0, "warning": 0, "info": 0}
        if not os.path.exists(filepath):
            return counts
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            # Parse the summary table
            for line in content.split("\n"):
                if "Pages visited" in line:
                    m = re.search(r"\|\s*(\d+)", line.split("Pages visited")[1])
                    if m:
                        counts["pages"] = int(m.group(1))
                elif "Critical issues" in line:
                    m = re.search(r"\|\s*(\d+)", line.split("Critical issues")[1])
                    if m:
                        counts["critical"] = int(m.group(1))
                elif "Warnings" in line:
                    m = re.search(r"\|\s*(\d+)", line.split("Warnings")[1])
                    if m:
                        counts["warning"] = int(m.group(1))
                elif "Info items" in line:
                    m = re.search(r"\|\s*(\d+)", line.split("Info items")[1])
                    if m:
                        counts["info"] = int(m.group(1))
        except Exception:
            pass  # If we can't read the previous report, that's fine
        return counts

    def _delta_str(self, current: int, previous: int) -> str:
        """Format a comparison string like '3 (down 1)' or '5 (up 2)'."""
        if previous == 0:
            return str(current)
        diff = current - previous
        if diff > 0:
            return f"{current} | {previous} (up {diff})"
        elif diff < 0:
            return f"{current} | {previous} (down {abs(diff)})"
        else:
            return f"{current} | {previous} (same)"

    def write_report(self, filepath: str):
        """Generate the Markdown report file."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        critical = [i for i in self.issues if i.severity == Severity.CRITICAL]
        warnings = [i for i in self.issues if i.severity == Severity.WARNING]
        info = [i for i in self.issues if i.severity == Severity.INFO]

        # Read previous counts before overwriting
        prev = self._read_previous_counts(filepath)

        lines = [
            "# KoNote UX Walkthrough Report\n",
            f"**Generated:** {now}  ",
            "**Command:** `pytest tests/ux_walkthrough/ -v`\n",
            "## Summary\n",
            "| Metric | This Run | Previous |",
            "|--------|----------|----------|",
            f"| Pages visited | {self._delta_str(self.pages_visited, prev['pages'])} |",
            f"| Critical issues | {self._delta_str(len(critical), prev['critical'])} |",
            f"| Warnings | {self._delta_str(len(warnings), prev['warning'])} |",
            f"| Info items | {self._delta_str(len(info), prev['info'])} |",
            "",
        ]

        # Issues by severity
        for severity_name, issue_list in [
            ("Critical", critical),
            ("Warning", warnings),
            ("Info", info),
        ]:
            lines.append(f"## {severity_name} Issues\n")
            if not issue_list:
                lines.append(f"_No {severity_name.lower()} issues found._\n")
            else:
                for issue in issue_list:
                    lines.append(
                        f"- **[{issue.role}] {issue.step}** `{issue.url}`"
                    )
                    lines.append(f"  {issue.description}")
                    if issue.detail:
                        lines.append(f"  _{issue.detail}_")
                    lines.append("")

        # Known limitations
        lines.append("## Known Limitations\n")
        if self.browser_findings:
            lines.append("- Colour contrast, focus management, and responsive "
                         "layout are tested via Playwright browser tests")
            lines.append("- Colour contrast checks depend on CDN "
                         "(axe-core) — require internet")
        else:
            lines.append("- Colour contrast not tested (requires browser rendering)")
            lines.append("- Focus management after HTMX swaps not tested")
            lines.append("- Visual layout / responsive behaviour not tested")
        lines.append("")

        # Per-role walkthrough table
        lines.append("## Per-Role Walkthrough Results\n")
        for role_name, steps in self.steps_by_role.items():
            lines.append(f"### {role_name}\n")
            lines.append("| Step | URL | Status | Issues |")
            lines.append("|------|-----|--------|--------|")
            for s in steps:
                issue_count = len(s["issues"])
                issue_summary = (
                    "None" if issue_count == 0 else f"{issue_count} issue(s)"
                )
                lines.append(
                    f"| {s['step']} | `{s['url']}` | "
                    f"{s['status_code']} | {issue_summary} |"
                )
            lines.append("")

        # Scenario walkthroughs (if any)
        if self.scenarios:
            lines.append("## Scenario Walkthroughs\n")
            for scenario_name, steps in self.scenarios.items():
                lines.append(f"### {scenario_name}\n")
                lines.append("| Role | Step | URL | Status | Issues |")
                lines.append("|------|------|-----|--------|--------|")
                for s in steps:
                    issue_count = len(s["issues"])
                    issue_summary = (
                        "None" if issue_count == 0
                        else f"{issue_count} issue(s)"
                    )
                    lines.append(
                        f"| {s['role']} | {s['step']} | `{s['url']}` | "
                        f"{s['status_code']} | {issue_summary} |"
                    )
                lines.append("")

        # Browser-based findings (Playwright)
        if self.browser_findings:
            lines.append("## Browser-Based Findings\n")
            lines.append("_Tested with Playwright (headless Chromium) + axe-core._\n")
            for category, findings in self.browser_findings.items():
                lines.append(f"### {category}\n")
                if not findings:
                    lines.append("_No issues found._\n")
                else:
                    for f in findings:
                        sev_label = {
                            "critical": "CRITICAL",
                            "warning": "WARNING",
                            "info": "INFO",
                        }.get(f["severity"], f["severity"].upper())
                        lines.append(
                            f"- **[{sev_label}]** `{f['url']}` "
                            f"— {f['description']}"
                        )
                        if f.get("detail"):
                            lines.append(f"  _{f['detail']}_")
                        lines.append("")

        # Recommendations
        lines.append("## Recommendations\n")
        if critical:
            lines.append("### Immediate (Critical)\n")
            for issue in critical:
                lines.append(f"1. Fix: {issue.description} on `{issue.url}`")
            lines.append("")
        if warnings:
            lines.append("### Short-term (Warnings)\n")
            label_issues = [
                i for i in warnings if "label" in i.description.lower()
            ]
            heading_issues = [
                i for i in warnings if "heading" in i.description.lower()
            ]
            other_warnings = [
                i
                for i in warnings
                if i not in label_issues and i not in heading_issues
            ]
            if label_issues:
                lines.append(
                    f"- **Form labels:** {len(label_issues)} inputs missing "
                    "labels. Add `<label for=\"...\">` or `aria-label`."
                )
            if heading_issues:
                lines.append(
                    f"- **Heading structure:** {len(heading_issues)} pages "
                    "with heading issues."
                )
            for issue in other_warnings:
                lines.append(f"- {issue.description} (`{issue.url}`)")
            lines.append("")

        lines.append("---\n")
        lines.append(
            "_Generated by `tests/ux_walkthrough/` — automated UX walkthrough_\n"
        )

        # Write to file
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
