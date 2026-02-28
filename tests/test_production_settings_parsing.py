import unittest

from konote.settings.production import (
    _normalize_host_entry,
    _normalize_origin_entry,
)


class ProductionSettingsParsingTests(unittest.TestCase):
    def test_allowed_hosts_normalizes_url_and_wildcard(self):
        self.assertEqual(_normalize_host_entry("https://konote.llewelyn.ca/"), "konote.llewelyn.ca")
        self.assertEqual(_normalize_host_entry("*.railway.app"), ".railway.app")
        self.assertEqual(_normalize_host_entry(".up.railway.app"), ".up.railway.app")

    def test_allowed_hosts_strips_path_and_trailing_dot(self):
        self.assertEqual(_normalize_host_entry("konote-dev.llewelyn.ca/path"), "konote-dev.llewelyn.ca")
        self.assertEqual(_normalize_host_entry("konote.llewelyn.ca."), "konote.llewelyn.ca")

    def test_csrf_origins_accepts_bare_hosts(self):
        self.assertEqual(
            _normalize_origin_entry("konote.llewelyn.ca"),
            "https://konote.llewelyn.ca",
        )
        self.assertEqual(
            _normalize_origin_entry("konote-dev.llewelyn.ca"),
            "https://konote-dev.llewelyn.ca",
        )

    def test_csrf_origins_keeps_valid_origin_and_removes_path(self):
        self.assertEqual(
            _normalize_origin_entry("https://konote.llewelyn.ca/admin/login/"),
            "https://konote.llewelyn.ca",
        )
        self.assertEqual(
            _normalize_origin_entry("https://konote.llewelyn.ca:8443/path"),
            "https://konote.llewelyn.ca:8443",
        )

    def test_csrf_origins_converts_leading_dot_to_wildcard(self):
        self.assertEqual(
            _normalize_origin_entry(".railway.app"),
            "https://*.railway.app",
        )


if __name__ == "__main__":
    unittest.main()