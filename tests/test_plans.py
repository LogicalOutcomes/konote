"""Tests for the plans app — signals and achievement status behaviour (REQ-G4).

Covers the post_save signal on PlanTarget that auto-updates achievement_status
when a goal's lifecycle status changes.
"""
import pytest
from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

import konote.encryption as enc_module
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.plans.models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
)
from apps.programs.models import Program


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PlanTargetSignalTest(TestCase):
    """Tests for the post_save signal on PlanTarget (REQ-G4).

    The signal should:
    - Set achievement_status = "achieved" when status → "completed"
    - Set achievement_status = "not_achieved" when status → "deactivated"
    - Do nothing when status does not change
    - Not error when there are no linked PlanTargetMetric rows
    """

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.program = Program.objects.create(name="Test Program")

        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.status = "active"
        self.client_file.save()

        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="active",
        )

        self.section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Test Section",
            program=self.program,
        )

    def tearDown(self):
        enc_module._fernet = None

    def _make_target(self, name="Test Goal"):
        """Create a PlanTarget in the default (active) status."""
        t = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        t.name = name
        t.save()
        return t

    # ------------------------------------------------------------------ #
    # completed → achieved
    # ------------------------------------------------------------------ #

    def test_status_completed_sets_achievement_achieved(self):
        """Changing status to 'completed' should set achievement_status to 'achieved'."""
        target = self._make_target()
        self.assertEqual(target.achievement_status, "")

        target.status = "completed"
        target.save()

        target.refresh_from_db()
        self.assertEqual(target.achievement_status, "achieved")
        self.assertEqual(target.achievement_status_source, "worker_assessed")
        self.assertIsNotNone(target.achievement_status_updated_at)

    def test_status_completed_sets_first_achieved_at_when_unset(self):
        """Completing a goal for the first time should record first_achieved_at."""
        target = self._make_target()
        self.assertIsNone(target.first_achieved_at)

        target.status = "completed"
        target.save()

        target.refresh_from_db()
        self.assertIsNotNone(target.first_achieved_at)

    def test_status_completed_does_not_clear_existing_first_achieved_at(self):
        """If first_achieved_at was already set, completing again must not change it."""
        earlier = timezone.now() - timezone.timedelta(days=30)

        target = self._make_target()
        target.first_achieved_at = earlier
        target.save(update_fields=["first_achieved_at"])

        target.status = "completed"
        target.save()

        target.refresh_from_db()
        # first_achieved_at should not be overwritten — still the earlier timestamp
        self.assertEqual(
            target.first_achieved_at.replace(microsecond=0),
            earlier.replace(microsecond=0),
        )

    # ------------------------------------------------------------------ #
    # deactivated → not_achieved
    # ------------------------------------------------------------------ #

    def test_status_deactivated_sets_achievement_not_achieved(self):
        """Changing status to 'deactivated' should set achievement_status to 'not_achieved'."""
        target = self._make_target()
        self.assertEqual(target.achievement_status, "")

        target.status = "deactivated"
        target.save()

        target.refresh_from_db()
        self.assertEqual(target.achievement_status, "not_achieved")
        self.assertEqual(target.achievement_status_source, "worker_assessed")
        self.assertIsNotNone(target.achievement_status_updated_at)

    def test_status_deactivated_does_not_set_first_achieved_at(self):
        """Deactivating a goal should never set first_achieved_at."""
        target = self._make_target()
        target.status = "deactivated"
        target.save()

        target.refresh_from_db()
        self.assertIsNone(target.first_achieved_at)

    # ------------------------------------------------------------------ #
    # No status change — signal must not fire
    # ------------------------------------------------------------------ #

    def test_save_without_status_change_does_not_update_achievement(self):
        """Saving a PlanTarget without changing status must NOT alter achievement_status."""
        target = self._make_target()
        # Pre-populate a known achievement_status
        PlanTarget.objects.filter(pk=target.pk).update(
            achievement_status="improving",
            achievement_status_source="auto_computed",
        )

        # Now save target (status stays "default") — simulate a name-only edit
        target.refresh_from_db()
        target.name = "Updated Goal Name"
        target.save()

        target.refresh_from_db()
        # achievement_status must still be "improving" — signal should not have changed it
        self.assertEqual(target.achievement_status, "improving")
        self.assertEqual(target.achievement_status_source, "auto_computed")

    def test_creation_does_not_set_achievement_status(self):
        """Creating a new PlanTarget must not set achievement_status."""
        target = self._make_target()
        target.refresh_from_db()
        self.assertEqual(target.achievement_status, "")

    # ------------------------------------------------------------------ #
    # Targets without linked PlanTargetMetric rows
    # ------------------------------------------------------------------ #

    def test_target_without_metrics_does_not_error_on_completed(self):
        """Completing a target with no linked metrics must not raise any exception."""
        target = self._make_target()
        # No PlanTargetMetric rows — goal has no associated metric

        try:
            target.status = "completed"
            target.save()
        except Exception as exc:
            self.fail(f"Signal raised an unexpected exception: {exc}")

        target.refresh_from_db()
        self.assertEqual(target.achievement_status, "achieved")

    def test_target_without_metrics_does_not_error_on_deactivated(self):
        """Deactivating a target with no linked metrics must not raise any exception."""
        target = self._make_target()

        try:
            target.status = "deactivated"
            target.save()
        except Exception as exc:
            self.fail(f"Signal raised an unexpected exception: {exc}")

        target.refresh_from_db()
        self.assertEqual(target.achievement_status, "not_achieved")

    # ------------------------------------------------------------------ #
    # Targets WITH linked PlanTargetMetric rows
    # ------------------------------------------------------------------ #

    def test_target_with_metrics_updates_correctly_on_completed(self):
        """A target with linked metrics should still update achievement_status correctly."""
        metric = MetricDefinition.objects.create(
            name="Goal Progress",
            definition="How close to the goal",
            category="general",
            metric_type="scale",
            min_value=0,
            max_value=10,
        )
        target = self._make_target()
        PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)

        target.status = "completed"
        target.save()

        target.refresh_from_db()
        self.assertEqual(target.achievement_status, "achieved")

    # ------------------------------------------------------------------ #
    # Multiple status transitions
    # ------------------------------------------------------------------ #

    def test_multiple_transitions(self):
        """Status can move through multiple states; each transition updates correctly."""
        target = self._make_target()

        # Active → completed → default (re-opened) → deactivated
        target.status = "completed"
        target.save()
        target.refresh_from_db()
        self.assertEqual(target.achievement_status, "achieved")

        # Re-open the goal — signal should not clear achievement_status
        target.status = "default"
        target.save()
        target.refresh_from_db()
        # Achievement status is left alone on re-activation (recalculated by note saves)
        self.assertEqual(target.achievement_status, "achieved")

        # Deactivate
        target.status = "deactivated"
        target.save()
        target.refresh_from_db()
        self.assertEqual(target.achievement_status, "not_achieved")


# ────────────────────────────────────────────────────────────────────
# DQ1-TIER2: Very unlikely plausibility threshold tests
# ────────────────────────────────────────────────────────────────────


class MetricDefinitionTier2ValidationTest(TestCase):
    """Tests for very_unlikely_min/max validation on MetricDefinition."""

    def _make_metric(self, **kwargs):
        defaults = {
            "name": "Test Metric",
            "definition": "Test definition",
            "category": "general",
            "metric_type": "scale",
        }
        defaults.update(kwargs)
        return MetricDefinition(**defaults)

    def test_very_unlikely_min_must_be_less_than_very_unlikely_max(self):
        """very_unlikely_min >= very_unlikely_max should raise ValidationError."""
        m = self._make_metric(very_unlikely_min=100, very_unlikely_max=50)
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("Very unlikely minimum must be less than very unlikely maximum", str(ctx.exception))

    def test_very_unlikely_min_equal_to_very_unlikely_max_is_invalid(self):
        """very_unlikely_min == very_unlikely_max should raise ValidationError."""
        m = self._make_metric(very_unlikely_min=50, very_unlikely_max=50)
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("Very unlikely minimum must be less than very unlikely maximum", str(ctx.exception))

    def test_very_unlikely_min_must_be_at_or_above_min_value(self):
        """very_unlikely_min < min_value should raise ValidationError."""
        m = self._make_metric(min_value=0, very_unlikely_min=-10)
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("Very unlikely minimum cannot be below the hard minimum", str(ctx.exception))

    def test_very_unlikely_max_must_be_at_or_below_max_value(self):
        """very_unlikely_max > max_value should raise ValidationError."""
        m = self._make_metric(max_value=100, very_unlikely_max=200)
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("Very unlikely maximum cannot exceed the hard maximum", str(ctx.exception))

    def test_very_unlikely_min_must_be_at_or_below_warn_min(self):
        """very_unlikely_min > warn_min should raise ValidationError."""
        m = self._make_metric(warn_min=10, very_unlikely_min=20)
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("Very unlikely minimum must be at or below the warning minimum", str(ctx.exception))

    def test_very_unlikely_max_must_be_at_or_above_warn_max(self):
        """very_unlikely_max < warn_max should raise ValidationError."""
        m = self._make_metric(warn_max=90, very_unlikely_max=80)
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("Very unlikely maximum must be at or above the warning maximum", str(ctx.exception))

    def test_very_unlikely_min_less_than_very_unlikely_max_is_valid(self):
        """very_unlikely_min < very_unlikely_max should pass validation."""
        m = self._make_metric(very_unlikely_min=10, very_unlikely_max=200)
        m.clean()  # Should not raise

    def test_very_unlikely_min_equal_to_min_value_is_valid(self):
        """very_unlikely_min == min_value should pass validation."""
        m = self._make_metric(min_value=0, very_unlikely_min=0)
        m.clean()  # Should not raise

    def test_very_unlikely_max_equal_to_max_value_is_valid(self):
        """very_unlikely_max == max_value should pass validation."""
        m = self._make_metric(max_value=100, very_unlikely_max=100)
        m.clean()  # Should not raise

    def test_very_unlikely_min_equal_to_warn_min_is_valid(self):
        """very_unlikely_min == warn_min should pass validation."""
        m = self._make_metric(warn_min=10, very_unlikely_min=10)
        m.clean()  # Should not raise

    def test_very_unlikely_max_equal_to_warn_max_is_valid(self):
        """very_unlikely_max == warn_max should pass validation."""
        m = self._make_metric(warn_max=90, very_unlikely_max=90)
        m.clean()  # Should not raise

    def test_full_ordering_valid(self):
        """min_value <= very_unlikely_min <= warn_min <= warn_max <= very_unlikely_max <= max_value."""
        m = self._make_metric(
            min_value=0,
            very_unlikely_min=5,
            warn_min=20,
            warn_max=80,
            very_unlikely_max=95,
            max_value=100,
        )
        m.clean()  # Should not raise

    def test_full_ordering_with_equal_boundaries_valid(self):
        """All equal boundaries should pass validation."""
        m = self._make_metric(
            min_value=0,
            very_unlikely_min=0,
            warn_min=0,
            warn_max=100,
            very_unlikely_max=100,
            max_value=100,
        )
        m.clean()  # Should not raise

    def test_none_fields_do_not_trigger_validation(self):
        """When tier-2 fields are None, no tier-2 validation should fire."""
        m = self._make_metric(
            min_value=0,
            max_value=100,
            warn_min=10,
            warn_max=90,
            very_unlikely_min=None,
            very_unlikely_max=None,
        )
        m.clean()  # Should not raise


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricValueFormTier2Test(TestCase):
    """Tests that MetricValueForm renders tier-2 data attributes."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_form_renders_very_unlikely_data_attributes(self):
        """Number input should have data-very-unlikely-min and data-very-unlikely-max."""
        from apps.notes.forms import MetricValueForm

        metric_def = MetricDefinition.objects.create(
            name="Test Financial",
            definition="Financial metric",
            category="custom",
            metric_type="scale",
            min_value=None,
            max_value=None,
            warn_min=0,
            warn_max=15000,
            very_unlikely_min=-1000,
            very_unlikely_max=150000,
        )
        form = MetricValueForm(metric_def=metric_def)
        html = str(form["value"])
        self.assertIn("data-very-unlikely-min", html)
        self.assertIn("data-very-unlikely-max", html)

    def test_form_renders_plausibility_confirmed_with_tier2_only(self):
        """plausibility_confirmed should appear even if only tier-2 thresholds are set."""
        from apps.notes.forms import MetricValueForm

        metric_def = MetricDefinition.objects.create(
            name="Test Tier2 Only",
            definition="Tier 2 only metric",
            category="custom",
            metric_type="scale",
            warn_min=None,
            warn_max=None,
            very_unlikely_min=-1000,
            very_unlikely_max=150000,
        )
        form = MetricValueForm(metric_def=metric_def)
        self.assertIn("plausibility_confirmed", form.fields)

    def test_form_does_not_render_tier2_attrs_when_not_set(self):
        """No tier-2 data attrs when very_unlikely fields are None."""
        from apps.notes.forms import MetricValueForm

        metric_def = MetricDefinition.objects.create(
            name="Test No Tier2",
            definition="No tier 2",
            category="custom",
            metric_type="scale",
            min_value=0,
            max_value=100,
            warn_min=10,
            warn_max=90,
            very_unlikely_min=None,
            very_unlikely_max=None,
        )
        form = MetricValueForm(metric_def=metric_def)
        html = str(form["value"])
        self.assertNotIn("data-very-unlikely-min", html)
        self.assertNotIn("data-very-unlikely-max", html)


class Tier2DataMigrationTest(TestCase):
    """Test that the data migration constants are correctly defined."""

    def test_financial_tier2_thresholds_are_wider_than_tier1(self):
        """Tier-2 thresholds should be wider than tier-1 thresholds."""
        import importlib
        mod18 = importlib.import_module("apps.plans.migrations.0018_set_financial_warn_thresholds")
        FINANCIAL_THRESHOLDS = mod18.FINANCIAL_THRESHOLDS
        mod20 = importlib.import_module("apps.plans.migrations.0020_set_financial_tier2_thresholds")
        FINANCIAL_TIER2_THRESHOLDS = mod20.FINANCIAL_TIER2_THRESHOLDS

        for name in FINANCIAL_THRESHOLDS:
            self.assertIn(name, FINANCIAL_TIER2_THRESHOLDS)
            t1 = FINANCIAL_THRESHOLDS[name]
            t2 = FINANCIAL_TIER2_THRESHOLDS[name]
            self.assertLessEqual(
                t2["very_unlikely_min"], t1["warn_min"],
            )
            self.assertGreaterEqual(
                t2["very_unlikely_max"], t1["warn_max"],
            )

