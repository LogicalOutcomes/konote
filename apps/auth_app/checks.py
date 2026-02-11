"""Django system checks for permission enforcement wiring.

These run automatically with every manage.py command (runserver, migrate, etc.).
They catch permission enforcement drift — especially useful during the migration
from hardcoded role decorators to the permission matrix.

Check IDs:
    KoNote.W020 — Hardcoded role decorator found (should migrate to @requires_permission)
    KoNote.E020 — Unknown permission key in @requires_permission (typo / deleted key)
    KoNote.W021 — Matrix key not referenced by any @requires_permission (dead key)

Run checks manually:
    python manage.py check
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning, register

from apps.auth_app.permissions import ALL_PERMISSION_KEYS


# Patterns to detect hardcoded role decorators in Python files
_HARDCODED_PATTERNS = [
    (re.compile(r"@minimum_role\("), "@minimum_role"),
    (re.compile(r"@program_role_required\("), "@program_role_required"),
]

# Pattern to extract permission keys from @requires_permission("key") calls.
# Only matches keys containing a dot (e.g. "note.view") to avoid false
# positives from placeholder text like "key" in docstrings and comments.
_REQUIRES_PERM_PATTERN = re.compile(
    r"""@requires_permission(?:_global)?\(\s*["']([a-z_]+\.[a-z_]+)["']"""
)


def _scan_view_files():
    """Find all Python files under apps/ that are likely view files."""
    base_dir = Path(getattr(settings, "BASE_DIR", "."))
    apps_dir = base_dir / "apps"
    if not apps_dir.exists():
        return []

    view_files = []
    for py_file in apps_dir.rglob("*.py"):
        name = py_file.name
        # Include files named *views*.py or views/ directory contents
        if "views" in name or "views" in str(py_file.parent.name):
            view_files.append(py_file)
    return view_files


@register()
def check_hardcoded_role_decorators(app_configs, **kwargs):
    """W020: Warn on any remaining @minimum_role or @program_role_required usage."""
    warnings = []

    for py_file in _scan_view_files():
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for pattern, decorator_name in _HARDCODED_PATTERNS:
            matches = list(pattern.finditer(content))
            if matches:
                # Count occurrences
                count = len(matches)
                # Find line numbers for the first few
                lines = content[:matches[0].start()].count("\n") + 1
                rel_path = py_file.relative_to(Path(settings.BASE_DIR))
                warnings.append(
                    Warning(
                        f"{rel_path} has {count} {decorator_name}() "
                        f"call(s) (first at line {lines}). "
                        f"Migrate to @requires_permission.",
                        hint=(
                            f"Replace {decorator_name} with "
                            f"@requires_permission(\"<key>\") reading from "
                            f"the permissions matrix."
                        ),
                        id="KoNote.W020",
                    )
                )

    return warnings


@register()
def check_permission_key_validity(app_configs, **kwargs):
    """E020: Error if @requires_permission uses a key not in the matrix."""
    errors = []
    base_dir = Path(getattr(settings, "BASE_DIR", "."))
    apps_dir = base_dir / "apps"
    if not apps_dir.exists():
        return errors

    for py_file in apps_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for match in _REQUIRES_PERM_PATTERN.finditer(content):
            key = match.group(1)
            if key not in ALL_PERMISSION_KEYS:
                line_no = content[:match.start()].count("\n") + 1
                rel_path = py_file.relative_to(base_dir)
                errors.append(
                    Error(
                        f"{rel_path}:{line_no} uses unknown permission key "
                        f"'{key}' in @requires_permission.",
                        hint=(
                            f"Check for typos. Valid keys: "
                            f"{', '.join(sorted(ALL_PERMISSION_KEYS)[:5])}..."
                        ),
                        id="KoNote.E020",
                    )
                )

    return errors


@register()
def check_dead_permission_keys(app_configs, **kwargs):
    """W021: Warn if a matrix key is not referenced by any @requires_permission."""
    warnings = []
    base_dir = Path(getattr(settings, "BASE_DIR", "."))
    apps_dir = base_dir / "apps"
    if not apps_dir.exists():
        return warnings

    # Collect all permission keys used in decorators across the codebase
    used_keys = set()
    for py_file in apps_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in _REQUIRES_PERM_PATTERN.finditer(content):
            used_keys.add(match.group(1))

    # Also scan template files for {% has_permission "key" %} usage
    template_dir = base_dir / "templates"
    template_perm_pattern = re.compile(r"""\{%\s*has_permission\s+["']([^"']+)["']""")
    if template_dir.exists():
        for html_file in template_dir.rglob("*.html"):
            try:
                content = html_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for match in template_perm_pattern.finditer(content):
                used_keys.add(match.group(1))

    # Keys that are admin-only (enforced by @admin_required, not the matrix)
    # These are expected to not have @requires_permission references
    admin_keys = {"user.manage", "settings.manage", "program.manage", "audit.view"}

    # Keys with known alternative enforcement (not decorator-driven)
    alternative_enforcement_keys = {
        "attendance.check_in",      # View-level check
        "attendance.view_report",   # View-level check
        "custom_field.view",        # PER_FIELD — field-level config
        "custom_field.edit",        # PER_FIELD — field-level config
        "client.view_name",         # get_visible_fields() via can_access()
        "client.view_contact",      # get_visible_fields() via can_access()
        "client.view_safety",       # get_visible_fields() via can_access()
        "client.view_medications",  # get_visible_fields() via can_access()
        "client.view_clinical",     # get_visible_fields() via can_access()
        "metric.view_individual",   # View-level / report logic
        "metric.view_aggregate",    # View-level / report logic
        "report.program_report",    # is_aggregate_only_user() + export logic
        "report.data_extract",      # Export logic
        "note.delete",              # Admin-only destructive action
        "client.delete",            # Admin erasure workflow
        "plan.delete",              # Admin-only destructive action
    }

    unreferenced = ALL_PERMISSION_KEYS - used_keys - admin_keys - alternative_enforcement_keys
    if unreferenced:
        warnings.append(
            Warning(
                f"{len(unreferenced)} permission key(s) in the matrix are not "
                f"referenced by @requires_permission or {{% has_permission %}}: "
                f"{', '.join(sorted(unreferenced))}",
                hint=(
                    "Either wire these keys to a decorator/template tag, "
                    "or add them to the alternative_enforcement_keys set in "
                    "checks.py if they use a different enforcement mechanism."
                ),
                id="KoNote.W021",
            )
        )

    return warnings
