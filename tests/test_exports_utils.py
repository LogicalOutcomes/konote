import unittest
from apps.exports.utils import sanitize_for_csv

class CSVInjectionTests(unittest.TestCase):
    """Tests for CSV injection protection in apps.exports.utils."""

    def test_sanitize_equals(self):
        """Values starting with = should be prefixed with a single quote."""
        self.assertEqual(sanitize_for_csv("=SUM(A1:A10)"), "'=SUM(A1:A10)")

    def test_sanitize_plus(self):
        """Values starting with + should be prefixed with a single quote."""
        self.assertEqual(sanitize_for_csv("+1+1"), "'+1+1")

    def test_sanitize_minus(self):
        """Values starting with - should be prefixed with a single quote."""
        self.assertEqual(sanitize_for_csv("-123"), "'-123")

    def test_sanitize_at(self):
        """Values starting with @ should be prefixed with a single quote."""
        self.assertEqual(sanitize_for_csv("@execute"), "'@execute")

    def test_safe_string(self):
        """Safe strings should pass through unchanged."""
        self.assertEqual(sanitize_for_csv("Hello World"), "Hello World")
        self.assertEqual(sanitize_for_csv("John Doe"), "John Doe")

    def test_empty_string(self):
        """Empty strings should pass through unchanged."""
        self.assertEqual(sanitize_for_csv(""), "")

    def test_none_value(self):
        """None values should pass through unchanged."""
        self.assertIsNone(sanitize_for_csv(None))

    def test_non_string_values(self):
        """Non-string values should pass through unchanged."""
        self.assertEqual(sanitize_for_csv(42), 42)
        self.assertEqual(sanitize_for_csv(3.14), 3.14)
        self.assertEqual(sanitize_for_csv(True), True)

    def test_internal_dangerous_characters(self):
        """Dangerous characters not at the start should not trigger sanitization."""
        self.assertEqual(sanitize_for_csv("Price: -100"), "Price: -100")
        self.assertEqual(sanitize_for_csv("1+1=2"), "1+1=2")
        self.assertEqual(sanitize_for_csv("email@example.com"), "email@example.com")

if __name__ == '__main__':
    unittest.main()
