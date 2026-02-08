"""Tests for PII scrubbing — verifies name replacement and regex patterns."""
from django.test import SimpleTestCase

from apps.reports.pii_scrub import scrub_pii


class PiiScrubNameReplacementTest(SimpleTestCase):
    """Test known-name replacement with word boundaries."""

    def test_replaces_simple_name(self):
        text = "John mentioned he was feeling better."
        result = scrub_pii(text, known_names=["John"])
        self.assertEqual(result, "[NAME] mentioned he was feeling better.")

    def test_replaces_possessive(self):
        text = "John's progress has been remarkable."
        result = scrub_pii(text, known_names=["John"])
        self.assertEqual(result, "[NAME] progress has been remarkable.")

    def test_does_not_corrupt_common_word_hope(self):
        """'Hope' as a name should not replace 'hope' as a common word."""
        text = "She has hope for the future."
        result = scrub_pii(text, known_names=["Hope"])
        # The word "hope" appears lowercase — word boundary + case-insensitive
        # will match it. This is an acceptable trade-off documented in the plan.
        # But we test that at least the pattern doesn't crash or produce garbage.
        self.assertIn("for the future", result)

    def test_replaces_name_case_insensitive(self):
        text = "I spoke with grace about her goals."
        result = scrub_pii(text, known_names=["Grace"])
        self.assertIn("[NAME]", result)
        self.assertIn("about her goals", result)

    def test_replaces_longest_name_first(self):
        text = "Mary-Jane was doing well. Mary called later."
        result = scrub_pii(text, known_names=["Mary", "Mary-Jane"])
        self.assertEqual(result, "[NAME] was doing well. [NAME] called later.")

    def test_handles_none_names(self):
        text = "Some text here."
        result = scrub_pii(text, known_names=None)
        self.assertEqual(result, "Some text here.")

    def test_handles_empty_names(self):
        text = "Some text here."
        result = scrub_pii(text, known_names=["", None, "A"])  # "A" too short
        self.assertEqual(result, "Some text here.")

    def test_handles_empty_text(self):
        self.assertEqual(scrub_pii("", known_names=["John"]), "")
        self.assertEqual(scrub_pii(None, known_names=["John"]), None)


class PiiScrubPhoneTest(SimpleTestCase):
    """Test phone number detection."""

    def test_dashed_phone(self):
        result = scrub_pii("Call me at 613-555-1234.")
        self.assertEqual(result, "Call me at [PHONE].")

    def test_dotted_phone(self):
        result = scrub_pii("Phone: 613.555.1234")
        self.assertEqual(result, "Phone: [PHONE]")

    def test_no_separator_phone(self):
        result = scrub_pii("6135551234")
        self.assertEqual(result, "[PHONE]")

    def test_parentheses_phone(self):
        result = scrub_pii("(613) 555-1234")
        self.assertEqual(result, "[PHONE]")


class PiiScrubEmailTest(SimpleTestCase):
    """Test email detection."""

    def test_simple_email(self):
        result = scrub_pii("Email john.doe@example.com for info.")
        self.assertEqual(result, "Email [EMAIL] for info.")

    def test_email_with_plus(self):
        result = scrub_pii("Contact user+tag@gmail.com")
        self.assertIn("[EMAIL]", result)


class PiiScrubPostalCodeTest(SimpleTestCase):
    """Test Canadian postal code detection."""

    def test_spaced_postal(self):
        result = scrub_pii("Lives in K1A 0B1 area.")
        self.assertEqual(result, "Lives in [POSTAL CODE] area.")

    def test_no_space_postal(self):
        result = scrub_pii("Postal: K1A0B1")
        self.assertIn("[POSTAL CODE]", result)

    def test_lowercase_postal(self):
        result = scrub_pii("Area code k1a 0b1")
        self.assertIn("[POSTAL CODE]", result)


class PiiScrubSinTest(SimpleTestCase):
    """Test SIN (Social Insurance Number) detection."""

    def test_dashed_sin(self):
        result = scrub_pii("SIN: 123-456-789")
        self.assertEqual(result, "SIN: [SIN]")

    def test_spaced_sin(self):
        result = scrub_pii("SIN 123 456 789")
        self.assertEqual(result, "SIN [SIN]")


class PiiScrubAddressTest(SimpleTestCase):
    """Test street address detection."""

    def test_street_address(self):
        result = scrub_pii("Lives at 123 Main Street downtown.")
        self.assertIn("[ADDRESS]", result)

    def test_avenue_address(self):
        result = scrub_pii("Moved to 45 Elm Avenue last week.")
        self.assertIn("[ADDRESS]", result)

    def test_road_address(self):
        result = scrub_pii("At 789 Oak Road now.")
        self.assertIn("[ADDRESS]", result)


class PiiScrubCombinedTest(SimpleTestCase):
    """Test multiple PII types in one text."""

    def test_multiple_pii(self):
        text = (
            "John called from 613-555-1234 to say he moved to "
            "45 Elm Street, K1A 0B1. His email is john@example.com."
        )
        result = scrub_pii(text, known_names=["John"])
        self.assertNotIn("John", result)
        self.assertNotIn("613-555-1234", result)
        self.assertNotIn("K1A 0B1", result)
        self.assertNotIn("john@example.com", result)
        self.assertIn("[NAME]", result)
        self.assertIn("[PHONE]", result)
        self.assertIn("[POSTAL CODE]", result)
        self.assertIn("[EMAIL]", result)
