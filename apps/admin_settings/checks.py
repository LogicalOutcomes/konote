"""
Django system checks for French translation completeness.

These run automatically with every manage.py command (runserver, migrate, etc.).
They catch missing translations early — especially useful when Claude Code or
other AI tools are the primary developer and will see the warnings.

Check IDs:
    KoNote.W010 — Translation gap detected (Warning)
    KoNote.W011 — .mo file missing or stale (Warning)

Run checks manually:
    python manage.py check
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.checks import Warning, register


@register()
def check_translation_coverage(app_configs, **kwargs):
    """W010: Warn if templates have more translatable items than the .po file."""
    warnings = []

    base_dir = getattr(settings, "BASE_DIR", None)
    if not base_dir:
        return warnings

    template_dir = Path(base_dir) / "templates"
    if not template_dir.exists():
        return warnings

    # Count {% trans %} strings and {% blocktrans %} blocks in templates
    trans_pattern = re.compile(r"""\{%[-\s]*trans\s+['"](.+?)['"]\s*[-]?%\}""")
    blocktrans_pattern = re.compile(r"""\{%[-\s]*blocktrans[\s%]""")

    trans_strings = set()
    blocktrans_count = 0

    for html_file in template_dir.rglob("*.html"):
        try:
            content = html_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        trans_strings.update(trans_pattern.findall(content))
        blocktrans_count += len(blocktrans_pattern.findall(content))

    template_count = len(trans_strings) + blocktrans_count

    # Count .po entries
    po_path = _find_po_file(base_dir)
    if po_path is None:
        return warnings

    po_entry_count = _count_po_entries(po_path)

    gap = template_count - po_entry_count
    if gap > 5:
        warnings.append(
            Warning(
                f"French translation gap: templates have ~{template_count} "
                f"translatable items but django.po has {po_entry_count} "
                f"entries (gap: {gap}).",
                hint="Run: python manage.py translate_strings",
                id="KoNote.W010",
            )
        )

    return warnings


@register()
def check_mo_file_health(app_configs, **kwargs):
    """W011: Warn if the French .mo file is missing or older than .po."""
    warnings = []

    base_dir = getattr(settings, "BASE_DIR", None)
    if not base_dir:
        return warnings

    po_path = _find_po_file(base_dir)
    if po_path is None:
        return warnings

    mo_path = po_path.with_suffix(".mo")

    if not mo_path.exists():
        warnings.append(
            Warning(
                "French translation file (django.mo) is missing.",
                hint="Run: python manage.py translate_strings",
                id="KoNote.W011",
            )
        )
    elif po_path.stat().st_mtime > mo_path.stat().st_mtime:
        warnings.append(
            Warning(
                "French translation file (django.mo) is older than "
                "django.po — translations may be stale.",
                hint="Run: python manage.py translate_strings",
                id="KoNote.W011",
            )
        )

    return warnings


def _find_po_file(base_dir):
    """Find the French .po file."""
    for locale_dir in getattr(settings, "LOCALE_PATHS", []):
        po_path = Path(locale_dir) / "fr" / "LC_MESSAGES" / "django.po"
        if po_path.exists():
            return po_path

    po_path = Path(base_dir) / "locale" / "fr" / "LC_MESSAGES" / "django.po"
    if po_path.exists():
        return po_path

    return None


def _count_po_entries(po_path):
    """Fast count of non-header msgid entries in a .po file.

    Handles both single-line (msgid "text") and multi-line msgids
    (msgid "" followed by "continuation" lines). Skips the header
    entry (first msgid "").
    """
    count = 0
    seen_header = False
    with open(po_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith('msgid "'):
            if stripped == 'msgid ""':
                # Could be header or multi-line msgid
                # Check if next line is a string continuation
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('"'):
                    if not seen_header:
                        # First msgid "" is the header — skip it
                        seen_header = True
                    else:
                        # Multi-line msgid — count it
                        count += 1
                elif not seen_header:
                    seen_header = True
            else:
                # Single-line msgid "some text"
                count += 1
        i += 1

    return count
