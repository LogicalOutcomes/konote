"""Tests for state_capture module — screenshot naming (QA-T20).

Fast unit tests — no browser needed.
"""
from unittest import TestCase

from .state_capture import _url_to_slug


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
