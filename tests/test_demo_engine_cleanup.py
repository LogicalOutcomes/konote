"""Tests that demo data cleanup restores configuration to pre-demo state.

Verifies that _ensure_portal_visible_metrics() stores original values
and cleanup_demo_data() restores them, and that the method is skipped
when DEMO_MODE is not enabled.
"""
from django.test import TestCase, override_settings
from django.conf import settings
from cryptography.fernet import Fernet

from apps.admin_settings.demo_engine import DemoDataEngine
from apps.plans.models import MetricDefinition
from apps.programs.models import Program
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricVisibilityRestorationTest(TestCase):
    """Test that demo engine restores metric portal_visibility after cleanup."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Test Program", status="active",
        )
        self.metric_hidden = MetricDefinition.objects.create(
            name="Hidden Metric",
            unit="score",
            min_value=1,
            max_value=5,
            is_universal=True,
            is_enabled=True,
            portal_visibility="no",
        )
        self.metric_visible = MetricDefinition.objects.create(
            name="Already Visible",
            unit="score",
            min_value=1,
            max_value=5,
            is_universal=True,
            is_enabled=True,
            portal_visibility="yes",
        )
        self.metric_program = MetricDefinition.objects.create(
            name="Program Metric",
            unit="score",
            min_value=1,
            max_value=5,
            owning_program=self.program,
            is_enabled=True,
            portal_visibility="no",
        )

    @override_settings(DEMO_MODE=True)
    def test_ensure_visibility_stores_originals(self):
        engine = DemoDataEngine()
        engine._ensure_portal_visible_metrics([self.program])

        # Hidden metrics should now be visible
        self.metric_hidden.refresh_from_db()
        self.assertEqual(self.metric_hidden.portal_visibility, "yes")

        # Already-visible metric should be unchanged
        self.metric_visible.refresh_from_db()
        self.assertEqual(self.metric_visible.portal_visibility, "yes")

        # Program metric should now be visible
        self.metric_program.refresh_from_db()
        self.assertEqual(self.metric_program.portal_visibility, "yes")

        # Originals should be stored
        self.assertIn(self.metric_hidden.pk, engine._metric_visibility_originals)
        self.assertEqual(
            engine._metric_visibility_originals[self.metric_hidden.pk], "no",
        )
        # Already-visible metric should NOT be in originals
        self.assertNotIn(self.metric_visible.pk, engine._metric_visibility_originals)

    @override_settings(DEMO_MODE=True)
    def test_cleanup_restores_original_visibility(self):
        engine = DemoDataEngine()
        engine._ensure_portal_visible_metrics([self.program])

        # Verify they changed
        self.metric_hidden.refresh_from_db()
        self.assertEqual(self.metric_hidden.portal_visibility, "yes")

        # Run cleanup
        engine.cleanup_demo_data()

        # Should be restored to original
        self.metric_hidden.refresh_from_db()
        self.assertEqual(self.metric_hidden.portal_visibility, "no")

        self.metric_program.refresh_from_db()
        self.assertEqual(self.metric_program.portal_visibility, "no")

        # Already-visible should still be visible
        self.metric_visible.refresh_from_db()
        self.assertEqual(self.metric_visible.portal_visibility, "yes")

    @override_settings(DEMO_MODE=False)
    def test_skips_when_demo_mode_disabled(self):
        engine = DemoDataEngine()
        engine._ensure_portal_visible_metrics([self.program])

        # Should not have changed anything
        self.metric_hidden.refresh_from_db()
        self.assertEqual(self.metric_hidden.portal_visibility, "no")

        self.metric_program.refresh_from_db()
        self.assertEqual(self.metric_program.portal_visibility, "no")

    def test_skips_when_demo_mode_not_set(self):
        """DEMO_MODE not in settings at all — should skip safely."""
        engine = DemoDataEngine()
        had_demo_mode = hasattr(settings, "DEMO_MODE")
        original_demo_mode = getattr(settings, "DEMO_MODE", None)
        if had_demo_mode:
            delattr(settings, "DEMO_MODE")

        try:
            engine._ensure_portal_visible_metrics([self.program])
        finally:
            if had_demo_mode:
                setattr(settings, "DEMO_MODE", original_demo_mode)

        self.metric_hidden.refresh_from_db()
        self.assertEqual(self.metric_hidden.portal_visibility, "no")
