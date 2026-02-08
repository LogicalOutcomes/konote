"""Tests for Outcome Insights — data collection, views, and AI validation."""
from datetime import date, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from konote.ai import validate_insights_response

# Use the same test encryption key as other tests
TEST_KEY = "dGVzdGtleWZvcmVuY3J5cHRpb24xMjM0NTY3ODk="


class ValidateInsightsResponseTest(SimpleTestCase):
    """Test AI response validation logic."""

    def _sample_quotes(self):
        return [
            {"text": "I finally feel like I have a plan for my future", "note_id": 1, "target_name": "Employment"},
            {"text": "The housing support has made a real difference in my life", "note_id": 2, "target_name": "Housing"},
            {"text": "I am more confident about looking for work now", "note_id": 3, "target_name": "Employment"},
        ]

    def test_valid_response_passes(self):
        response = {
            "summary": "During this period, participants showed positive progress across multiple areas.",
            "themes": ["employment readiness", "housing stability"],
            "cited_quotes": [
                {"text": "I finally feel like I have a plan for my future", "note_id": 1, "context": "employment goal"},
            ],
            "recommendations": "Staff may want to focus on employment support.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNotNone(result)
        self.assertEqual(len(result["cited_quotes"]), 1)

    def test_missing_key_returns_none(self):
        response = {
            "summary": "Some text here.",
            "themes": [],
            # Missing cited_quotes and recommendations
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNone(result)

    def test_short_summary_returns_none(self):
        response = {
            "summary": "Too short.",
            "themes": [],
            "cited_quotes": [],
            "recommendations": "Something.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNone(result)

    def test_non_verbatim_quotes_are_removed(self):
        response = {
            "summary": "Participants showed improvement across the board during this period.",
            "themes": ["progress"],
            "cited_quotes": [
                # This is verbatim from the original
                {"text": "I finally feel like I have a plan for my future", "note_id": 1, "context": "employment"},
                # This is NOT in the original quotes — AI fabricated it
                {"text": "Everything is going great and I love my life now", "note_id": 99, "context": "general"},
            ],
            "recommendations": "Continue current approach.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNotNone(result)
        # The fabricated quote should be removed
        self.assertEqual(len(result["cited_quotes"]), 1)
        self.assertEqual(result["cited_quotes"][0]["note_id"], 1)

    def test_partial_quote_match_passes(self):
        """A substring of an original quote should pass verbatim check."""
        response = {
            "summary": "Participants expressed growing confidence in their ability to plan ahead.",
            "themes": ["confidence"],
            "cited_quotes": [
                # This is a substring of "I finally feel like I have a plan for my future"
                {"text": "I have a plan for my future", "note_id": 1, "context": "employment"},
            ],
            "recommendations": "Keep it up.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNotNone(result)
        self.assertEqual(len(result["cited_quotes"]), 1)

    def test_not_a_dict_returns_none(self):
        result = validate_insights_response("just a string", self._sample_quotes())
        self.assertIsNone(result)

    def test_themes_not_list_gets_fixed(self):
        response = {
            "summary": "Participants showed improvement across the board during this period.",
            "themes": "employment",  # String instead of list
            "cited_quotes": [],
            "recommendations": "Continue.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNotNone(result)
        self.assertEqual(result["themes"], [])


class DataTierTest(SimpleTestCase):
    """Test data volume threshold logic."""

    def test_sparse(self):
        from apps.reports.insights_views import _get_data_tier
        self.assertEqual(_get_data_tier(5, 1), "sparse")
        self.assertEqual(_get_data_tier(19, 2), "sparse")

    def test_limited(self):
        from apps.reports.insights_views import _get_data_tier
        self.assertEqual(_get_data_tier(25, 3), "limited")
        self.assertEqual(_get_data_tier(49, 4), "limited")
        self.assertEqual(_get_data_tier(60, 2), "limited")  # <3 months

    def test_full(self):
        from apps.reports.insights_views import _get_data_tier
        self.assertEqual(_get_data_tier(50, 3), "full")
        self.assertEqual(_get_data_tier(500, 12), "full")
