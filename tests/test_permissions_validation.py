"""Tests for permission documentation drift check (W022)."""

import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from apps.auth_app.checks import check_docs_permission_row_count


class TestW022DocsRowCount(TestCase):
    """W022: permissions-matrix.md row count vs ALL_PERMISSION_KEYS."""

    def test_w022_passes_with_current_docs(self):
        """The live docs file should have at least as many rows as matrix keys."""
        result = check_docs_permission_row_count(app_configs=None)
        self.assertEqual(result, [], f"W022 unexpectedly fired: {result}")

    @override_settings(BASE_DIR="/nonexistent/path")
    def test_w022_skips_on_missing_file(self):
        """Missing docs file should be silently skipped (no warnings)."""
        result = check_docs_permission_row_count(app_configs=None)
        self.assertEqual(result, [])

    def test_w022_warns_when_rows_fewer_than_keys(self):
        """W022 should fire when doc has fewer data rows than matrix keys."""
        # Build a minimal table with only 2 data rows (far fewer than 68 keys)
        md = (
            "## Quick Summary\n"
            "| Capability | Front Desk | Direct Service |\n"
            "|---|:---:|:---:|\n"
            "| **Clients** | | |\n"
            "| Check clients in | Yes | Scoped |\n"
            "| See client names | Yes | Yes |\n"
            "\n"
            "**Legend:**\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs"
            docs_dir.mkdir()
            (docs_dir / "permissions-matrix.md").write_text(md, encoding="utf-8")
            with self.settings(BASE_DIR=tmp):
                result = check_docs_permission_row_count(app_configs=None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "KoNote.W022")
        self.assertIn("data rows", result[0].msg)

    def test_w022_warns_on_malformed_markdown(self):
        """W022 should warn if the Quick Summary table can't be parsed."""
        md = "# Some Other Heading\n\nNo table here.\n"
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs"
            docs_dir.mkdir()
            (docs_dir / "permissions-matrix.md").write_text(md, encoding="utf-8")
            with self.settings(BASE_DIR=tmp):
                result = check_docs_permission_row_count(app_configs=None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "KoNote.W022")
        self.assertIn("Manual review", result[0].msg)
