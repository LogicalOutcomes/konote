"""Tests for the plans app — signals and achievement status behaviour (REQ-G4).

Covers the post_save signal on PlanTarget that auto-updates achievement_status
when a goal's lifecycle status changes.
"""
import pytest
from cryptography.fernet import Fernet
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
