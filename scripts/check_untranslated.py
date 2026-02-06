#!/usr/bin/env python
"""
Check for user-facing strings that are NOT wrapped in translation functions.

Catches the root cause: strings that never make it to .po files because
the developer forgot to use _() or gettext_lazy().

Priority levels:
  HIGH (exit code 1) — forms.py labels, placeholders, help_text, empty_label;
       views.py messages; ValidationError messages; model choice labels
  LOW  (informational) — model field help_text (only visible in Django admin)

Run:  python scripts/check_untranslated.py
      python scripts/check_untranslated.py --app plans    (check one app)
      python scripts/check_untranslated.py --all           (include LOW priority)

Exit code 1 if HIGH-priority issues found, 0 if clean.
"""

import ast
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
APPS_DIR = PROJECT_ROOT / "apps"

TRANSLATION_FUNCS = {
    "_", "gettext", "gettext_lazy",
    "ngettext", "ngettext_lazy",
    "pgettext", "pgettext_lazy",
}

# Strings that are never user-facing
SKIP_VALUES = {
    "utf-8", "utf8", "POST", "GET", "PUT", "PATCH", "DELETE",
    "active", "default", "completed", "deactivated", "archived",
    "pending", "approved", "rejected",
}


class UnwrappedStringFinder(ast.NodeVisitor):
    """AST visitor that finds user-facing strings not wrapped in _()."""

    def __init__(self, filepath, source_type):
        self.filepath = filepath
        self.source_type = source_type  # "forms", "models", "views"
        self.high = []
        self.low = []

    def _is_bare_string(self, node):
        return isinstance(node, ast.Constant) and isinstance(node.value, str)

    def _should_skip(self, value):
        if len(value) < 3:
            return True
        if value.lower() in SKIP_VALUES:
            return True
        if value.startswith("/") or value.startswith("http"):
            return True
        if re.match(r"^[a-z_]+$", value):
            return True
        if re.match(r"^[a-z\-]+$", value):
            return True
        return False

    def _record(self, priority, lineno, context, value):
        if self._should_skip(value):
            return
        entry = {
            "file": str(self.filepath),
            "line": lineno,
            "context": context,
            "string": value,
        }
        if priority == "HIGH":
            self.high.append(entry)
        else:
            self.low.append(entry)

    def _check_keyword_arg(self, keyword, parent_context=""):
        """Check keyword arguments for untranslated strings."""
        # HIGH priority: form-facing strings
        high_kwargs = {"label", "empty_label", "title"}
        # Context-dependent: help_text and placeholder
        form_kwargs = {"help_text", "placeholder"}

        if keyword.arg in high_kwargs and self._is_bare_string(keyword.value):
            ctx = f"{parent_context}{keyword.arg}="
            self._record("HIGH", keyword.value.lineno, ctx, keyword.value.value)

        elif keyword.arg in form_kwargs and self._is_bare_string(keyword.value):
            ctx = f"{parent_context}{keyword.arg}="
            # In forms.py, these are always user-facing. In models.py, only admin.
            priority = "HIGH" if self.source_type == "forms" else "LOW"
            self._record(priority, keyword.value.lineno, ctx, keyword.value.value)

        # Check placeholder inside attrs dict: attrs={"placeholder": "..."}
        if keyword.arg == "attrs" and isinstance(keyword.value, ast.Dict):
            for key, val in zip(keyword.value.keys, keyword.value.values):
                if (isinstance(key, ast.Constant) and key.value == "placeholder"
                        and self._is_bare_string(val)):
                    ctx = f'{parent_context}attrs["placeholder"]='
                    self._record("HIGH", val.lineno, ctx, val.value)

    def visit_Call(self, node):
        for kw in node.keywords:
            self._check_keyword_arg(kw)

        # messages.success/error/warning/info
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "success", "error", "warning", "info"
        }:
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "messages":
                if len(node.args) >= 2 and self._is_bare_string(node.args[1]):
                    self._record(
                        "HIGH", node.args[1].lineno,
                        f"messages.{node.func.attr}()",
                        node.args[1].value,
                    )

        # ValidationError
        func_name = ""
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id
        if func_name == "ValidationError":
            if node.args and self._is_bare_string(node.args[0]):
                self._record("HIGH", node.args[0].lineno, "ValidationError()", node.args[0].value)

        self.generic_visit(node)

    def visit_Assign(self, node):
        """Check CHOICES = [("key", "Label"), ...] assignments."""
        for target in node.targets:
            name = ""
            if isinstance(target, ast.Name):
                name = target.id
            elif isinstance(target, ast.Attribute):
                name = target.attr

            if "CHOICES" in name.upper() or name == "choices":
                if isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Tuple) and len(elt.elts) >= 2:
                            label = elt.elts[1]
                            if self._is_bare_string(label):
                                self._record("HIGH", label.lineno, f"{name} label", label.value)

        self.generic_visit(node)


def check_file(filepath):
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return [], []

    name = filepath.stem
    source_type = "forms" if name == "forms" else ("models" if name == "models" else "views")
    finder = UnwrappedStringFinder(filepath.relative_to(PROJECT_ROOT), source_type)
    finder.visit(tree)
    return finder.high, finder.low


def main():
    show_all = "--all" in sys.argv
    app_filter = None
    if "--app" in sys.argv:
        idx = sys.argv.index("--app")
        if idx + 1 < len(sys.argv):
            app_filter = sys.argv[idx + 1]

    scan_names = {"forms.py", "models.py", "views.py"}
    all_high = []
    all_low = []

    for app_dir in sorted(APPS_DIR.iterdir()):
        if not app_dir.is_dir():
            continue
        if app_filter and app_dir.name != app_filter:
            continue
        for py_file in sorted(app_dir.glob("*.py")):
            if py_file.name in scan_names:
                high, low = check_file(py_file)
                all_high.extend(high)
                all_low.extend(low)

    if all_high:
        print(f"FAIL: {len(all_high)} untranslated user-facing string(s):\n")
        for issue in all_high:
            print(f"  {issue['file']}:{issue['line']}")
            print(f"    {issue['context']} \"{issue['string']}\"")
            print()
        print("FIX: Wrap these with _() and add French translations to django.po")
        print("     Import: from django.utils.translation import gettext_lazy as _")

    if show_all and all_low:
        print(f"\nINFO: {len(all_low)} low-priority string(s) (admin-only help_text):\n")
        for issue in all_low:
            print(f"  {issue['file']}:{issue['line']}")
            print(f"    {issue['context']} \"{issue['string']}\"")
            print()

    if not all_high:
        scope = f"apps/{app_filter}" if app_filter else "all apps"
        count = f" ({len(all_low)} low-priority skipped)" if all_low and not show_all else ""
        print(f"OK: No untranslated user-facing strings in {scope}.{count}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
