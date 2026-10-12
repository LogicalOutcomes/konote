"""
Django system checks for translation completeness and demo data health.

These run automatically with every manage.py command (runserver, migrate, etc.).
They catch issues early — especially useful when Claude Code or other AI tools
are the primary developer and will see the warnings.

Check IDs:
    KoNote.W010 — Translation gap detected (Warning)
    KoNote.W011 — .mo file missing or stale (Warning)
    KoNote.W012 — Demo data below report suppression threshold (Warning)

Run checks manually:
    python manage.py check
"""

import re
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError
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


@register()
def check_demo_data_health(app_configs, **kwargs):
    """W012: Warn if demo data exists but is below the report suppression threshold.

    Only runs when DEMO_MODE is enabled.  Catches degraded demo data that
    would cause reports to show "< 5" or empty results — whether from
    low client counts, manual deletions, or migration side-effects.
    """
    warnings = []

    if not getattr(settings, "DEMO_MODE", False):
        return warnings

    try:
        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.programs.models import Program
        from apps.reports.suppression import SMALL_CELL_THRESHOLD
    except Exception:
        return warnings  # App not ready yet (e.g. during initial migrate)

    # System checks run before migrations, so on a fresh database these tables
    # do not exist yet. Treat any database error as "nothing to check".
    low_programs = []
    try:
        # Only check if demo data exists at all
        if not ClientFile.objects.filter(is_demo=True).exists():
            return warnings

        programs = Program.objects.filter(status="active")

        for prog in programs:
            count = ClientProgramEnrolment.objects.filter(
                program=prog, client_file__is_demo=True, status="active",
            ).count()
            if 0 < count < SMALL_CELL_THRESHOLD:
                low_programs.append(f"{prog.name} ({count})")
    except DatabaseError:
        return warnings

    if low_programs:
        warnings.append(
            Warning(
                f"Demo data below suppression threshold in: "
                f"{', '.join(low_programs)}. "
                f"Reports will show '< {SMALL_CELL_THRESHOLD}' instead of "
                f"actual counts.",
                hint=(
                    "Regenerate demo data: "
                    "python manage.py generate_demo_data --force"
                ),
                id="KoNote.W012",
            )
        )

    return warnings
