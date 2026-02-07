"""Tests for Django system checks and helpers in admin_settings.checks.

Covers the translation gap detection (W010), .mo health check (W011),
and the _count_po_entries helper that must handle multi-line msgids.
"""

import os
import tempfile
import time
from pathlib import Path
from django.test import SimpleTestCase, override_settings

from apps.admin_settings.checks import (
    _count_po_entries,
    _find_po_file,
    check_mo_file_health,
    check_translation_coverage,
)


# ─────────────────────────────────────────────────────────────────────────
# _count_po_entries — the .po parser
# ─────────────────────────────────────────────────────────────────────────


class CountPoEntriesTest(SimpleTestCase):
    """Test the .po entry counter handles all msgid formats."""

    def _write_po(self, content):
        """Write content to a temp .po file and return the path."""
        fd, path = tempfile.mkstemp(suffix=".po")
        os.close(fd)
        Path(path).write_text(content, encoding="utf-8")
        self.addCleanup(lambda: os.unlink(path))
        return Path(path)

    def test_single_line_msgids(self):
        po = self._write_po(
            'msgid ""\n'
            'msgstr ""\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            "\n"
            'msgid "Hello"\n'
            'msgstr "Bonjour"\n'
            "\n"
            'msgid "Goodbye"\n'
            'msgstr "Au revoir"\n'
        )
        self.assertEqual(_count_po_entries(po), 2)

    def test_multi_line_msgids(self):
        po = self._write_po(
            'msgid ""\n'
            'msgstr ""\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            "\n"
            'msgid "Simple"\n'
            'msgstr "Simple"\n'
            "\n"
            'msgid ""\n'
            '"This is a long "\n'
            '"multi-line string"\n'
            'msgstr ""\n'
            '"Ceci est une longue "\n'
            '"chaîne multi-ligne"\n'
        )
        self.assertEqual(_count_po_entries(po), 2)

    def test_header_only(self):
        po = self._write_po(
            'msgid ""\n'
            'msgstr ""\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        )
        self.assertEqual(_count_po_entries(po), 0)

    def test_empty_file(self):
        po = self._write_po("")
        self.assertEqual(_count_po_entries(po), 0)

    def test_mixed_single_and_multi_line(self):
        """Regression test: 145 multi-line entries were undercounted before fix."""
        po = self._write_po(
            'msgid ""\n'
            'msgstr ""\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            "\n"
            'msgid "One"\n'
            'msgstr "Un"\n'
            "\n"
            'msgid ""\n'
            '"Two "\n'
            '"words"\n'
            'msgstr ""\n'
            '"Deux "\n'
            '"mots"\n'
            "\n"
            'msgid "Three"\n'
            'msgstr "Trois"\n'
            "\n"
            'msgid ""\n'
            '"Four "\n'
            '"parts here"\n'
            'msgstr ""\n'
            '"Quatre "\n'
            '"parties ici"\n'
        )
        self.assertEqual(_count_po_entries(po), 4)

    def test_matches_real_po_file(self):
        """Verify count against the actual project .po file using polib."""
        from django.conf import settings

        po_path = _find_po_file(settings.BASE_DIR)
        if po_path is None:
            self.skipTest("No .po file found")

        import polib

        po = polib.pofile(str(po_path))
        polib_count = len([e for e in po if not e.obsolete])
        our_count = _count_po_entries(po_path)
        self.assertEqual(
            our_count,
            polib_count,
            f"_count_po_entries ({our_count}) disagrees with "
            f"polib ({polib_count}) on real .po file",
        )


# ─────────────────────────────────────────────────────────────────────────
# System check: W010 — translation gap
# ─────────────────────────────────────────────────────────────────────────


class TranslationCoverageCheckTest(SimpleTestCase):
    """Test the W010 system check for translation gap detection."""

    def test_no_warnings_when_translations_complete(self):
        """Current project state: all translations present, no gap."""
        warnings = check_translation_coverage(None)
        self.assertEqual(
            len(warnings),
            0,
            f"Expected no W010 warnings but got: {warnings}",
        )

    @override_settings(BASE_DIR=None)
    def test_no_crash_when_base_dir_missing(self):
        warnings = check_translation_coverage(None)
        self.assertEqual(warnings, [])

    def test_no_crash_when_templates_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(BASE_DIR=tmp, LOCALE_PATHS=[]):
                warnings = check_translation_coverage(None)
                self.assertEqual(warnings, [])


# ─────────────────────────────────────────────────────────────────────────
# System check: W011 — .mo file health
# ─────────────────────────────────────────────────────────────────────────


class MoFileHealthCheckTest(SimpleTestCase):
    """Test the W011 system check for .mo freshness."""

    def test_no_warnings_when_mo_is_fresh(self):
        """Current project state: .mo is newer than .po."""
        warnings = check_mo_file_health(None)
        self.assertEqual(
            len(warnings),
            0,
            f"Expected no W011 warnings but got: {warnings}",
        )

    def test_warns_when_mo_missing(self):
        """W011 fires if .mo file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            locale_dir = Path(tmp) / "locale" / "fr" / "LC_MESSAGES"
            locale_dir.mkdir(parents=True)
            po_path = locale_dir / "django.po"
            po_path.write_text(
                'msgid ""\nmsgstr ""\n\nmsgid "Test"\nmsgstr "Test"\n',
                encoding="utf-8",
            )
            with override_settings(BASE_DIR=tmp, LOCALE_PATHS=[]):
                warnings = check_mo_file_health(None)
                self.assertEqual(len(warnings), 1)
                self.assertEqual(warnings[0].id, "KoNote2.W011")
                self.assertIn("missing", warnings[0].msg.lower())

    def test_warns_when_mo_is_stale(self):
        """W011 fires if .mo is older than .po."""
        with tempfile.TemporaryDirectory() as tmp:
            locale_dir = Path(tmp) / "locale" / "fr" / "LC_MESSAGES"
            locale_dir.mkdir(parents=True)

            mo_path = locale_dir / "django.mo"
            mo_path.write_bytes(b"")
            # Ensure .po is written after .mo so mtime is newer
            time.sleep(0.05)

            po_path = locale_dir / "django.po"
            po_path.write_text(
                'msgid ""\nmsgstr ""\n\nmsgid "Test"\nmsgstr "Test"\n',
                encoding="utf-8",
            )

            with override_settings(BASE_DIR=tmp, LOCALE_PATHS=[]):
                warnings = check_mo_file_health(None)
                self.assertEqual(len(warnings), 1)
                self.assertEqual(warnings[0].id, "KoNote2.W011")
                self.assertIn("stale", warnings[0].msg.lower())

    @override_settings(BASE_DIR=None)
    def test_no_crash_when_base_dir_missing(self):
        warnings = check_mo_file_health(None)
        self.assertEqual(warnings, [])

    def test_no_crash_when_no_po_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(BASE_DIR=tmp, LOCALE_PATHS=[]):
                warnings = check_mo_file_health(None)
                self.assertEqual(warnings, [])
