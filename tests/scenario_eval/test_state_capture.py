"""Tests for state_capture module — screenshot naming (QA-T20) and validation (QA-W6).

Fast unit tests — no browser needed.
"""
import os
import tempfile
from pathlib import Path
from unittest import TestCase

from .state_capture import _url_to_slug, validate_screenshot_dir


class TestUrlToSlug(TestCase):
    """Test URL-to-slug conversion for screenshot filenames."""

    def test_simple_path(self):
        self.assertEqual(_url_to_slug("http://localhost:8000/clients/"), "clients")

    def test_nested_path(self):
        self.assertEqual(
            _url_to_slug("http://localhost:8000/clients/executive/"),
            "clients-executive",
        )

    def test_path_with_id(self):
        self.assertEqual(
            _url_to_slug("http://localhost:8000/clients/42/notes/"),
            "clients-42-notes",
        )

    def test_admin_settings(self):
        self.assertEqual(
            _url_to_slug("http://localhost:8000/admin/settings/"),
            "admin-settings",
        )

    def test_root_path(self):
        self.assertEqual(_url_to_slug("http://localhost:8000/"), "home")

    def test_empty_url(self):
        self.assertEqual(_url_to_slug(""), "home")

    def test_no_trailing_slash(self):
        self.assertEqual(
            _url_to_slug("http://localhost:8000/clients"),
            "clients",
        )

    def test_deep_path(self):
        self.assertEqual(
            _url_to_slug("http://localhost:8000/clients/42/plans/5/edit/"),
            "clients-42-plans-5-edit",
        )

    def test_query_params_ignored(self):
        self.assertEqual(
            _url_to_slug("http://localhost:8000/clients/?search=jane&page=2"),
            "clients",
        )

    def test_fragment_ignored(self):
        self.assertEqual(
            _url_to_slug("http://localhost:8000/clients/#section"),
            "clients",
        )

    def test_special_characters_removed(self):
        self.assertEqual(
            _url_to_slug("http://localhost:8000/clients/some%20path/"),
            "clients-some20path",
        )

    def test_truncation_at_max_length(self):
        long_url = "http://localhost:8000/" + "/".join(f"segment{i}" for i in range(20))
        slug = _url_to_slug(long_url, max_length=30)
        self.assertLessEqual(len(slug), 30)
        self.assertFalse(slug.endswith("-"))

    def test_truncation_does_not_end_with_hyphen(self):
        # Build a URL whose slug at exactly max_length would end with a hyphen
        slug = _url_to_slug("http://localhost:8000/abcdefghij/klmnopqrst/", max_length=11)
        self.assertLessEqual(len(slug), 11)
        self.assertFalse(slug.endswith("-"))

    def test_default_max_length_is_60(self):
        # 60 characters should be enough for most routes
        normal_url = "http://localhost:8000/clients/executive/"
        slug = _url_to_slug(normal_url)
        self.assertEqual(slug, "clients-executive")
        self.assertLessEqual(len(slug), 60)


class TestValidateScreenshotDir(TestCase):
    """Test screenshot directory validation (QA-W6)."""

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_screenshot_dir(tmpdir)
            self.assertEqual(result["total"], 0)
            self.assertEqual(result["valid"], 0)
            self.assertEqual(result["issues"], [])

    def test_nonexistent_dir(self):
        result = validate_screenshot_dir("/nonexistent/path")
        self.assertEqual(result["total"], 0)

    def test_valid_screenshots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two distinct PNG files (> 5 KB each)
            for name in ["shot1.png", "shot2.png"]:
                path = Path(tmpdir) / name
                path.write_bytes(b"\x89PNG" + os.urandom(6000))

            result = validate_screenshot_dir(tmpdir)
            self.assertEqual(result["total"], 2)
            self.assertEqual(result["valid"], 2)
            self.assertEqual(result["blank"], 0)
            self.assertEqual(result["duplicates"], 0)

    def test_blank_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a tiny PNG (< 5 KB — likely blank)
            path = Path(tmpdir) / "blank.png"
            path.write_bytes(b"\x89PNG" + b"\x00" * 100)

            result = validate_screenshot_dir(tmpdir)
            self.assertEqual(result["blank"], 1)
            self.assertEqual(result["issues"][0]["problem"], "blank")

    def test_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = b"\x89PNG" + os.urandom(6000)
            # Write identical content to two files (sorted: a_first, b_second)
            (Path(tmpdir) / "a_first.png").write_bytes(content)
            (Path(tmpdir) / "b_second.png").write_bytes(content)

            result = validate_screenshot_dir(tmpdir)
            self.assertEqual(result["duplicates"], 1)
            dup_issues = [i for i in result["issues"] if i["problem"] == "duplicate_of"]
            self.assertEqual(len(dup_issues), 1)
            self.assertEqual(dup_issues[0]["file"], "b_second.png")
            self.assertEqual(dup_issues[0]["duplicate_of"], "a_first.png")
