"""Tests for plain-language chart interpretation functions."""
from django.test import SimpleTestCase

from apps.reports.interpretations import (
    interpret_client_trend,
    interpret_descriptor_snapshot,
    interpret_engagement,
    interpret_progress_trend,
    interpret_suggestions,
)


class InterpretProgressTrendTest(SimpleTestCase):
    """Tests for interpret_progress_trend()."""

    def test_empty_data(self):
        self.assertEqual(interpret_progress_trend([]), "")

    def test_single_month(self):
        trend = [{"month": "2026-01", "harder": 20, "holding": 30, "shifting": 25, "good_place": 25}]
        result = interpret_progress_trend(trend)
        self.assertIn("too early", result.lower())

    def test_rising_good_place(self):
        trend = [
            {"month": "2026-01", "harder": 25, "holding": 30, "shifting": 20, "good_place": 25},
            {"month": "2026-02", "harder": 20, "holding": 25, "shifting": 20, "good_place": 35},
            {"month": "2026-03", "harder": 15, "holding": 20, "shifting": 20, "good_place": 45},
        ]
        result = interpret_progress_trend(trend)
        self.assertIn("good place", result.lower())
        self.assertIn("rose", result.lower())
        self.assertIn("25", result)  # start value
        self.assertIn("45", result)  # end value

    def test_declining_good_place(self):
        trend = [
            {"month": "2026-01", "harder": 15, "holding": 20, "shifting": 20, "good_place": 45},
            {"month": "2026-03", "harder": 25, "holding": 25, "shifting": 20, "good_place": 30},
        ]
        result = interpret_progress_trend(trend)
        self.assertIn("good place", result.lower())
        self.assertIn("dropped", result.lower())

    def test_rising_harder(self):
        trend = [
            {"month": "2026-01", "harder": 10, "holding": 30, "shifting": 30, "good_place": 30},
            {"month": "2026-03", "harder": 25, "holding": 30, "shifting": 25, "good_place": 20},
        ]
        result = interpret_progress_trend(trend)
        self.assertIn("harder", result.lower())
        self.assertIn("rose", result.lower())

    def test_dropping_harder(self):
        trend = [
            {"month": "2026-01", "harder": 30, "holding": 30, "shifting": 20, "good_place": 20},
            {"month": "2026-03", "harder": 15, "holding": 30, "shifting": 25, "good_place": 30},
        ]
        result = interpret_progress_trend(trend)
        self.assertIn("harder", result.lower())
        self.assertIn("dropped", result.lower())

    def test_stable_returns_stable_message(self):
        trend = [
            {"month": "2026-01", "harder": 20, "holding": 30, "shifting": 25, "good_place": 25},
            {"month": "2026-03", "harder": 21, "holding": 29, "shifting": 26, "good_place": 24},
        ]
        result = interpret_progress_trend(trend)
        self.assertIn("stable", result.lower())

    def test_both_good_and_harder_change(self):
        trend = [
            {"month": "2026-01", "harder": 30, "holding": 30, "shifting": 20, "good_place": 20},
            {"month": "2026-03", "harder": 15, "holding": 20, "shifting": 25, "good_place": 40},
        ]
        result = interpret_progress_trend(trend)
        # Should mention both changes
        self.assertIn("good place", result.lower())
        self.assertIn("harder", result.lower())


class InterpretEngagementTest(SimpleTestCase):
    """Tests for interpret_engagement()."""

    def test_empty_data(self):
        self.assertEqual(interpret_engagement({}), "")

    def test_high_engagement(self):
        raw = {"engaged": 45, "valuing": 25, "guarded": 20, "motions": 10}
        result = interpret_engagement(raw)
        self.assertIn("70%", result)
        self.assertIn("actively engaged", result.lower())

    def test_moderate_engagement(self):
        raw = {"engaged": 30, "valuing": 15, "guarded": 30, "motions": 25}
        result = interpret_engagement(raw)
        self.assertIn("45%", result)
        self.assertIn("room", result.lower())

    def test_low_engagement(self):
        raw = {"engaged": 15, "valuing": 10, "guarded": 35, "motions": 40}
        result = interpret_engagement(raw)
        self.assertIn("25%", result)
        self.assertIn("barriers", result.lower())


class InterpretDescriptorSnapshotTest(SimpleTestCase):
    """Tests for interpret_descriptor_snapshot()."""

    def test_empty_data(self):
        self.assertEqual(interpret_descriptor_snapshot([]), "")

    def test_dominant_good_place(self):
        trend = [{"month": "2026-01", "harder": 10, "holding": 20, "shifting": 25, "good_place": 45}]
        result = interpret_descriptor_snapshot(trend)
        self.assertIn("45", result)
        self.assertIn("good place", result.lower())

    def test_dominant_holding(self):
        trend = [{"month": "2026-01", "harder": 10, "holding": 50, "shifting": 20, "good_place": 20}]
        result = interpret_descriptor_snapshot(trend)
        self.assertIn("50", result)
        self.assertIn("holding steady", result.lower())

    def test_no_dominant_group(self):
        """When all values are very low, return empty."""
        trend = [{"month": "2026-01", "harder": 2, "holding": 3, "shifting": 3, "good_place": 2}]
        result = interpret_descriptor_snapshot(trend)
        self.assertEqual(result, "")


class InterpretSuggestionsTest(SimpleTestCase):
    """Tests for interpret_suggestions()."""

    def test_zero_suggestions(self):
        self.assertEqual(interpret_suggestions(0, 0), "")

    def test_with_important(self):
        result = interpret_suggestions(18, 5)
        self.assertIn("18", result)
        self.assertIn("5", result)
        self.assertIn("important", result.lower())

    def test_without_important(self):
        result = interpret_suggestions(10, 0)
        self.assertIn("10", result)
        self.assertNotIn("important", result.lower())


class InterpretClientTrendTest(SimpleTestCase):
    """Tests for interpret_client_trend()."""

    def test_empty_data(self):
        self.assertEqual(interpret_client_trend([]), "")

    def test_single_month(self):
        trend = [{"month": "2026-01", "harder": 20, "holding": 30, "shifting": 25, "good_place": 25}]
        result = interpret_client_trend(trend)
        self.assertIn("too early", result.lower())

    def test_improving_trend(self):
        trend = [
            {"month": "2026-01", "harder": 30, "holding": 30, "shifting": 20, "good_place": 20},
            {"month": "2026-03", "harder": 15, "holding": 20, "shifting": 25, "good_place": 40},
        ]
        result = interpret_client_trend(trend)
        self.assertIn("good place", result.lower())
        self.assertIn("their", result.lower())

    def test_worsening_trend(self):
        trend = [
            {"month": "2026-01", "harder": 10, "holding": 30, "shifting": 30, "good_place": 30},
            {"month": "2026-03", "harder": 25, "holding": 30, "shifting": 25, "good_place": 20},
        ]
        result = interpret_client_trend(trend)
        self.assertIn("harder", result.lower())
        self.assertIn("their", result.lower())

    def test_stable_trend(self):
        trend = [
            {"month": "2026-01", "harder": 25, "holding": 25, "shifting": 25, "good_place": 25},
            {"month": "2026-03", "harder": 24, "holding": 26, "shifting": 24, "good_place": 26},
        ]
        result = interpret_client_trend(trend)
        self.assertIn("steady", result.lower())
