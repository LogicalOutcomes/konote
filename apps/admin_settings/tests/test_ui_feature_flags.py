"""Tests for config-gated UI feature flags.

These tests protect the shared-product default behavior so new UI flags do not
change existing tenant navigation or group pages unless explicitly enabled.
"""
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase

from apps.admin_settings.views import DEFAULT_FEATURES, FEATURES_DEFAULT_ENABLED
from konote.context_processors import features as feature_context, nav_active


class UiFeatureFlagSafetyTests(SimpleTestCase):
    """Safety checks for opt-in UI flags."""

    def setUp(self):
        cache.clear()

    def test_new_ui_flags_are_disabled_by_default(self):
        """Shared UI flags should not affect existing tenants unless enabled."""
        self.assertIn("client_programs_tab", DEFAULT_FEATURES)
        self.assertIn("group_relationship_column", DEFAULT_FEATURES)
        self.assertIn("attendance_navigation", DEFAULT_FEATURES)
        self.assertNotIn("client_programs_tab", FEATURES_DEFAULT_ENABLED)
        self.assertNotIn("group_relationship_column", FEATURES_DEFAULT_ENABLED)
        self.assertNotIn("attendance_navigation", FEATURES_DEFAULT_ENABLED)

    @patch("apps.admin_settings.models.FeatureToggle.get_all_flags", return_value={})
    def test_feature_context_keeps_new_ui_flags_off_by_default(self, _mock_flags):
        """The template feature context should default the new UI flags to False."""
        request = SimpleNamespace()
        context = feature_context(request)

        self.assertFalse(context["features"]["client_programs_tab"])
        self.assertFalse(context["features"]["group_relationship_column"])
        self.assertFalse(context["features"]["attendance_navigation"])

    @patch("apps.admin_settings.models.FeatureToggle.get_all_flags", return_value={})
    def test_session_log_nav_stays_groups_when_attendance_flag_off(self, _mock_flags):
        """Existing tenants should keep the Groups nav active for session pages."""
        request = SimpleNamespace(
            path="/groups/12/session/",
            resolver_match=SimpleNamespace(url_name="session_log"),
        )

        context = nav_active(request)
        self.assertEqual(context["nav_active"], "groups")

    @patch(
        "apps.admin_settings.models.FeatureToggle.get_all_flags",
        return_value={"attendance_navigation": True},
    )
    def test_session_log_nav_switches_to_attendance_when_flag_enabled(self, _mock_flags):
        """Attendance pages should highlight the Attendance nav only when enabled."""
        request = SimpleNamespace(
            path="/groups/12/session/",
            resolver_match=SimpleNamespace(url_name="session_log"),
        )

        context = nav_active(request)
        self.assertEqual(context["nav_active"], "attendance")
