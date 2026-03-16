"""Tests for the plans app — signals and achievement status behaviour (REQ-G4).

Covers the post_save signal on PlanTarget that auto-updates achievement_status
when a goal's lifecycle status changes.
"""
import datetime

from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

import konote.encryption as enc_module
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.plans.models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
)
from apps.programs.models import Program, UserProgramRole
from apps.auth_app.constants import ROLE_STAFF


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


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricValueFormPlausibilityCleanTest(TestCase):
    """Tests for server-side plausibility validation in MetricValueForm.clean()."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def _make_metric_def(self):
        return MetricDefinition.objects.create(
            name="Test Plausibility",
            definition="For plausibility tests",
            category="custom",
            metric_type="scale",
            min_value=None,
            max_value=None,
            warn_min=10,
            warn_max=500,
            very_unlikely_min=-1000,
            very_unlikely_max=150000,
        )

    def test_tier2_value_rejected_without_confirmation(self):
        """Value outside tier-2 bounds should fail without plausibility_confirmed."""
        from apps.notes.forms import MetricValueForm

        md = self._make_metric_def()
        form = MetricValueForm(
            data={"metric_def_id": md.pk, "value": "-5000"},
            metric_def=md,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("extremely unlikely", str(form.errors["value"]))

    def test_tier1_value_rejected_without_confirmation(self):
        """Value outside tier-1 bounds should fail without plausibility_confirmed."""
        from apps.notes.forms import MetricValueForm

        md = self._make_metric_def()
        form = MetricValueForm(
            data={"metric_def_id": md.pk, "value": "5"},
            metric_def=md,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("outside the expected range", str(form.errors["value"]))

    def test_tier2_value_accepted_with_confirmation(self):
        """Value outside tier-2 bounds should pass with plausibility_confirmed=True."""
        from apps.notes.forms import MetricValueForm

        md = self._make_metric_def()
        form = MetricValueForm(
            data={"metric_def_id": md.pk, "value": "-5000", "plausibility_confirmed": "True"},
            metric_def=md,
        )
        self.assertTrue(form.is_valid())

    def test_tier1_value_accepted_with_confirmation(self):
        """Value outside tier-1 bounds should pass with plausibility_confirmed=True."""
        from apps.notes.forms import MetricValueForm

        md = self._make_metric_def()
        form = MetricValueForm(
            data={"metric_def_id": md.pk, "value": "5", "plausibility_confirmed": "True"},
            metric_def=md,
        )
        self.assertTrue(form.is_valid())

    def test_in_range_value_accepted_without_confirmation(self):
        """Value within all bounds should pass without confirmation."""
        from apps.notes.forms import MetricValueForm

        md = self._make_metric_def()
        form = MetricValueForm(
            data={"metric_def_id": md.pk, "value": "100"},
            metric_def=md,
        )
        self.assertTrue(form.is_valid())


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


# ── 90-day metric relevance review (METRIC-REVIEW1) ──────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TestMetricReview(TestCase):
    """Tests for METRIC-REVIEW1: 90-day metric relevance check."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.program = Program.objects.create(name="Review Program")
        self.user = User.objects.create_user(
            username="revtest", password="testpass123", is_admin=True,
        )
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role=ROLE_STAFF, status="active",
        )

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

        self.metric = MetricDefinition.objects.create(
            name="Review Metric",
            definition="Test metric for review",
            metric_type="scale",
            min_value=1,
            max_value=10,
        )

        self.section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Test Section",
            program=self.program,
        )
        self.target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        self.target.name = "Test Target"
        self.target.save()

        self.ptm = PlanTargetMetric.objects.create(
            plan_target=self.target,
            metric_def=self.metric,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_new_metric_no_review_banner(self):
        """Metric assigned today (< 90 days) should not show review banner."""
        from apps.notes.views import _build_target_forms
        forms = _build_target_forms(self.client_file)
        # Find the metric form for our PTM
        mf = forms[0]["metric_forms"][0]
        self.assertFalse(mf.review_due)

    def test_old_metric_shows_review_banner(self):
        """Metric assigned 91+ days ago should show review banner."""
        self.ptm.assigned_date = datetime.date.today() - datetime.timedelta(days=91)
        self.ptm.save(update_fields=["assigned_date"])

        from apps.notes.views import _build_target_forms
        forms = _build_target_forms(self.client_file)
        mf = forms[0]["metric_forms"][0]
        self.assertTrue(mf.review_due)

    def test_reviewed_metric_no_banner(self):
        """Metric reviewed 10 days ago should not show banner even if assigned 91+ days ago."""
        self.ptm.assigned_date = datetime.date.today() - datetime.timedelta(days=100)
        self.ptm.last_reviewed_date = datetime.date.today() - datetime.timedelta(days=10)
        self.ptm.save(update_fields=["assigned_date", "last_reviewed_date"])

        from apps.notes.views import _build_target_forms
        forms = _build_target_forms(self.client_file)
        mf = forms[0]["metric_forms"][0]
        self.assertFalse(mf.review_due)

    def test_confirm_review_endpoint(self):
        """POST to confirm-review updates last_reviewed_date."""
        http_client = Client()
        http_client.login(username="revtest", password="testpass123")
        from django.urls import reverse
        url = reverse("plans:confirm_metric_review", kwargs={"ptm_id": self.ptm.pk})
        response = http_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.ptm.refresh_from_db()
        self.assertEqual(self.ptm.last_reviewed_date, datetime.date.today())

    def test_confirm_review_creates_audit_log(self):
        """Confirming metric review creates an audit trail entry."""
        from apps.audit.models import AuditLog
        http_client = Client()
        http_client.login(username="revtest", password="testpass123")
        from django.urls import reverse
        url = reverse("plans:confirm_metric_review", kwargs={"ptm_id": self.ptm.pk})
        http_client.post(url)
        log = AuditLog.objects.using("audit").filter(
            action="confirm_metric_review",
            resource_type="plan_target_metric",
            resource_id=self.ptm.pk,
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user_id, self.user.pk)

    def test_confirm_review_requires_csrf(self):
        """POST without CSRF token is rejected (Django middleware enforces)."""
        from django.test import Client as DjangoClient
        from django.urls import reverse
        http_client = DjangoClient(enforce_csrf_checks=True)
        http_client.login(username="revtest", password="testpass123")
        url = reverse("plans:confirm_metric_review", kwargs={"ptm_id": self.ptm.pk})
        response = http_client.post(url)
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# Rationale log, severity bands, and assessment-due detection
# ---------------------------------------------------------------------------


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricRationaleLogTest(TestCase):
    """Tests for the MetricDefinition rationale_log append-only changelog."""

    def setUp(self):
        self.metric = MetricDefinition.objects.create(
            name="Test Metric",
            definition="A test metric",
            category="wellbeing",
            metric_type="scale",
        )

    def test_append_rationale_creates_entry(self):
        self.metric.append_rationale(note="Initial setup", author="System")
        self.metric.save()
        self.metric.refresh_from_db()
        self.assertEqual(len(self.metric.rationale_log), 1)
        self.assertEqual(self.metric.rationale_log[0]["note"], "Initial setup")
        self.assertEqual(self.metric.rationale_log[0]["author"], "System")

    def test_append_rationale_preserves_history(self):
        self.metric.append_rationale(note="First note", author="System")
        self.metric.append_rationale(note="Second note", author="Admin")
        self.metric.save()
        self.metric.refresh_from_db()
        self.assertEqual(len(self.metric.rationale_log), 2)
        self.assertEqual(self.metric.rationale_log[0]["note"], "First note")
        self.assertEqual(self.metric.rationale_log[1]["note"], "Second note")

    def test_current_rationale_returns_most_recent(self):
        self.metric.append_rationale(note="Old", author="System")
        self.metric.append_rationale(note="Current", author="Admin")
        self.assertEqual(self.metric.current_rationale, "Current")

    def test_current_rationale_empty_when_no_log(self):
        self.assertEqual(self.metric.current_rationale, "")

    def test_append_rationale_includes_date(self):
        self.metric.append_rationale(note="Test")
        entry = self.metric.rationale_log[0]
        self.assertIn("date", entry)
        self.assertEqual(entry["date"], datetime.date.today().isoformat())

    def test_append_rationale_with_french(self):
        self.metric.append_rationale(note="English", note_fr="Français", author="System")
        entry = self.metric.rationale_log[0]
        self.assertEqual(entry["note_fr"], "Français")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricSeverityBandTest(TestCase):
    """Tests for MetricDefinition.get_severity_band() display-only lookup."""

    def setUp(self):
        self.metric = MetricDefinition.objects.create(
            name="PHQ-9 Test",
            category="wellbeing",
            metric_type="scale",
            scoring_bands=[
                {"label": "Minimal", "min": 0, "max": 4},
                {"label": "Mild", "min": 5, "max": 9},
                {"label": "Moderate", "min": 10, "max": 14},
                {"label": "Moderately Severe", "min": 15, "max": 19},
                {"label": "Severe", "min": 20, "max": 27},
            ],
        )

    def test_exact_lower_bound(self):
        self.assertEqual(self.metric.get_severity_band(0), "Minimal")

    def test_exact_upper_bound(self):
        self.assertEqual(self.metric.get_severity_band(4), "Minimal")

    def test_mid_range(self):
        self.assertEqual(self.metric.get_severity_band(12), "Moderate")

    def test_severe_band(self):
        self.assertEqual(self.metric.get_severity_band(22), "Severe")

    def test_out_of_range_returns_none(self):
        self.assertIsNone(self.metric.get_severity_band(30))

    def test_no_scoring_bands_returns_none(self):
        m = MetricDefinition.objects.create(
            name="No Bands", category="wellbeing", metric_type="scale",
        )
        self.assertIsNone(m.get_severity_band(5))

    def test_invalid_score_returns_none(self):
        self.assertIsNone(self.metric.get_severity_band("not a number"))

    def test_float_score(self):
        self.assertEqual(self.metric.get_severity_band(7.5), "Mild")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AssessmentDueDetectionTest(TestCase):
    """Tests for get_assessments_due() assessment scheduling logic."""

    def setUp(self):
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget

        self.user = User.objects.create_user(
            username="assesstest", password="testpass123", is_admin=True,
        )
        self.program = Program.objects.create(name="Test Program", status="active")
        self.client_file = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="ASSESS-001", status="active",
        )

        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="active",
        )
        section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Health",
            program=self.program,
        )
        self.target = PlanTarget.objects.create(
            client_file=self.client_file,
            plan_section=section,
            status="default",
        )
        self.target.name = "Reduce depression"
        self.target.save()

        self.phq9 = MetricDefinition.objects.create(
            name="PHQ-9",
            category="wellbeing",
            metric_type="scale",
            is_standardized_instrument=True,
            assessment_at_intake=True,
            assessment_interval_days=90,
        )
        PlanTargetMetric.objects.create(
            plan_target=self.target,
            metric_def=self.phq9,
        )

    def test_intake_due_when_no_values(self):
        from apps.plans.assessment import get_assessments_due

        results = get_assessments_due(self.client_file)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["reason"], "intake")
        self.assertIsNone(results[0]["last_date"])

    def test_no_assessments_due_for_non_standardized(self):
        from apps.plans.assessment import get_assessments_due

        self.phq9.is_standardized_instrument = False
        self.phq9.save()
        results = get_assessments_due(self.client_file)
        self.assertEqual(len(results), 0)

    def test_periodic_due_when_overdue(self):
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
        from apps.plans.assessment import get_assessments_due

        # Record a value 100 days ago (overdue for 90-day interval)
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            author=self.user,
            note_type="full",
        )
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note,
            plan_target=self.target,
        )
        mv = MetricValue.objects.create(
            progress_note_target=pnt,
            metric_def=self.phq9,
            value=12,
        )
        # Backdate the created_at
        from django.utils import timezone as tz
        old_date = tz.now() - datetime.timedelta(days=100)
        MetricValue.objects.filter(pk=mv.pk).update(created_at=old_date)

        results = get_assessments_due(self.client_file)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["reason"], "periodic")
        self.assertGreater(results[0]["days_overdue"], 0)

    def test_not_due_when_recently_administered(self):
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
        from apps.plans.assessment import get_assessments_due

        note = ProgressNote.objects.create(
            client_file=self.client_file,
            author=self.user,
            note_type="assessment",
        )
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note,
            plan_target=self.target,
        )
        MetricValue.objects.create(
            progress_note_target=pnt,
            metric_def=self.phq9,
            value=8,
        )

        results = get_assessments_due(self.client_file)
        self.assertEqual(len(results), 0)


# ---------------------------------------------------------------------------
# HTTP-level view tests for rationale and assessment endpoints
# ---------------------------------------------------------------------------


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricRationaleViewTest(TestCase):
    """HTTP-level tests for rationale add/generate HTMX endpoints."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="rationale_admin", password="testpass123", is_admin=True,
        )
        self.metric = MetricDefinition.objects.create(
            name="Rationale Test Metric",
            definition="A test metric",
            category="wellbeing",
            metric_type="scale",
        )
        self.http_client = self.client
        self.http_client.login(username="rationale_admin", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def test_rationale_add_requires_post(self):
        """GET to rationale/add/ should return 405."""
        from django.urls import reverse
        url = reverse("metrics:metric_rationale_add", kwargs={"metric_id": self.metric.pk})
        response = self.http_client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_rationale_add_appends_entry(self):
        """POST with note text appends to rationale_log."""
        from django.urls import reverse
        url = reverse("metrics:metric_rationale_add", kwargs={"metric_id": self.metric.pk})
        response = self.http_client.post(url, {"note": "Test rationale note"})
        self.assertEqual(response.status_code, 200)
        self.metric.refresh_from_db()
        self.assertEqual(len(self.metric.rationale_log), 1)
        self.assertEqual(self.metric.rationale_log[0]["note"], "Test rationale note")

    def test_rationale_add_creates_audit_log(self):
        """Rationale add should create an audit log entry."""
        from django.urls import reverse
        from apps.audit.models import AuditLog
        url = reverse("metrics:metric_rationale_add", kwargs={"metric_id": self.metric.pk})
        self.http_client.post(url, {"note": "Audited note"})
        log = AuditLog.objects.using("audit").filter(
            resource_type="MetricDefinition",
            resource_id=str(self.metric.pk),
            action="update",
        ).last()
        self.assertIsNotNone(log)
        self.assertIn("rationale", log.metadata.get("detail", ""))

    def test_rationale_add_audit_log_uses_forwarded_ip(self):
        """Metric rationale audit logs should use the forwarded client IP."""
        from django.urls import reverse
        from apps.audit.models import AuditLog

        url = reverse("metrics:metric_rationale_add", kwargs={"metric_id": self.metric.pk})
        self.http_client.post(
            url,
            {"note": "Audited note"},
            HTTP_X_FORWARDED_FOR="192.0.2.77, 10.0.0.3",
            REMOTE_ADDR="127.0.0.1",
        )
        log = AuditLog.objects.using("audit").filter(
            resource_type="MetricDefinition",
            resource_id=str(self.metric.pk),
            action="update",
        ).last()
        self.assertEqual(log.ip_address, "192.0.2.77")

    def test_rationale_add_ignores_empty_note(self):
        """POST with empty note should not append."""
        from django.urls import reverse
        url = reverse("metrics:metric_rationale_add", kwargs={"metric_id": self.metric.pk})
        self.http_client.post(url, {"note": "  "})
        self.metric.refresh_from_db()
        self.assertEqual(len(self.metric.rationale_log), 0)

    def test_rationale_generate_requires_post(self):
        """GET to rationale/generate/ should return 405."""
        from django.urls import reverse
        url = reverse("metrics:metric_rationale_generate", kwargs={"metric_id": self.metric.pk})
        response = self.http_client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_rationale_generate_creates_entry(self):
        """POST to generate uses template fallback (no AI in test) and appends entry."""
        from django.urls import reverse
        url = reverse("metrics:metric_rationale_generate", kwargs={"metric_id": self.metric.pk})
        response = self.http_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.metric.refresh_from_db()
        self.assertEqual(len(self.metric.rationale_log), 1)
        self.assertEqual(self.metric.rationale_log[0]["author"], "AI")
        self.assertIn("initial configuration", self.metric.rationale_log[0]["note"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AssessmentDueBannerViewTest(TestCase):
    """HTTP-level test for assessment-due banner HTMX partial."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="banner_user", password="testpass123", is_admin=True,
        )
        self.program = Program.objects.create(name="Banner Program", status="active")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role=ROLE_STAFF, status="active",
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Banner"
        self.client_file.last_name = "Test"
        self.client_file.status = "active"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="active",
        )
        self.http_client = self.client
        self.http_client.login(username="banner_user", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def test_banner_renders_empty_when_no_instruments(self):
        """Banner partial returns 200 with no content when no standardized instruments assigned."""
        from django.urls import reverse
        url = reverse("clients:assessment_due_banner", kwargs={"client_id": self.client_file.pk})
        response = self.http_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Assessment due")

    def test_banner_shows_intake_due(self):
        """Banner shows assessment-due when PHQ-9 assigned with assessment_at_intake."""
        from django.urls import reverse
        phq9 = MetricDefinition.objects.create(
            name="PHQ-9", category="wellbeing", metric_type="scale",
            is_standardized_instrument=True, assessment_at_intake=True,
        )
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Health", program=self.program,
        )
        target = PlanTarget(plan_section=section, client_file=self.client_file)
        target.name = "Mental health"
        target.save()
        PlanTargetMetric.objects.create(plan_target=target, metric_def=phq9)

        url = reverse("clients:assessment_due_banner", kwargs={"client_id": self.client_file.pk})
        response = self.http_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assessment due")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricCSVImportTest(TestCase):
    """Tests for the CSV metric import parser (_parse_metric_csv)."""

    def _make_csv(self, content):
        """Create an in-memory CSV file from string content."""
        import io
        return io.BytesIO(content.encode("utf-8"))

    def test_parse_csv_with_metric_type_column(self):
        """CSV with metric_type column parses scale, achievement, and open_text."""
        from apps.plans.views import _parse_metric_csv

        csv_content = (
            "name,definition,category,metric_type,min_value,max_value,unit\n"
            "Test Scale,A scale metric,general,scale,1,10,score\n"
            "Test Open,An open text metric,client_experience,open_text,,,\n"
            "Test Achievement,An achievement,employment,achievement,,,\n"
        )
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["metric_type"], "scale")
        self.assertEqual(rows[0]["min_value"], 1.0)
        self.assertEqual(rows[0]["max_value"], 10.0)
        self.assertEqual(rows[1]["metric_type"], "open_text")
        self.assertIsNone(rows[1]["min_value"])
        self.assertIsNone(rows[1]["max_value"])
        self.assertEqual(rows[2]["metric_type"], "achievement")

    def test_parse_csv_invalid_metric_type(self):
        """CSV with invalid metric_type produces a row error."""
        from apps.plans.views import _parse_metric_csv

        csv_content = (
            "name,definition,category,metric_type\n"
            "Bad Metric,Something,general,bogus\n"
        )
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(len(rows), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("metric_type", errors[0])

    def test_parse_csv_defaults_to_scale(self):
        """CSV without metric_type column defaults to scale."""
        from apps.plans.views import _parse_metric_csv

        csv_content = (
            "name,definition,category,min_value,max_value\n"
            "Simple Metric,A metric,general,1,5\n"
        )
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["metric_type"], "scale")

    def test_parse_csv_client_experience_category(self):
        """CSV with client_experience category is valid."""
        from apps.plans.views import _parse_metric_csv

        csv_content = (
            "name,definition,category,metric_type\n"
            "How was our service?,Feedback question,client_experience,open_text\n"
        )
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["category"], "client_experience")


# ================================================================== #
# Instrument Grouping Tests                                          #
# ================================================================== #


class InstrumentNameFieldTest(TestCase):
    """Tests for the instrument_name field on MetricDefinition."""

    databases = {"default", "audit"}

    def test_instrument_name_saves_and_retrieves(self):
        """instrument_name can be saved and retrieved correctly."""
        metric = MetricDefinition.objects.create(
            name="Test Inclusivity Item",
            definition="Test definition",
            category="client_experience",
            instrument_name="LogicalOutcomes Inclusivity Battery",
        )
        metric.refresh_from_db()
        self.assertEqual(metric.instrument_name, "LogicalOutcomes Inclusivity Battery")

    def test_instrument_name_defaults_to_empty(self):
        """instrument_name defaults to empty string."""
        metric = MetricDefinition.objects.create(
            name="Standalone Metric",
            definition="No instrument",
            category="general",
        )
        metric.refresh_from_db()
        self.assertEqual(metric.instrument_name, "")

    def test_metrics_grouped_by_instrument_name(self):
        """Metrics with the same instrument_name can be queried together."""
        battery_name = "LogicalOutcomes Inclusivity Battery"
        MetricDefinition.objects.create(
            name="Item 1", definition="First item",
            category="client_experience", instrument_name=battery_name,
        )
        MetricDefinition.objects.create(
            name="Item 2", definition="Second item",
            category="client_experience", instrument_name=battery_name,
        )
        MetricDefinition.objects.create(
            name="Unrelated", definition="Not in a battery",
            category="general",
        )

        grouped = MetricDefinition.objects.filter(instrument_name=battery_name)
        self.assertEqual(grouped.count(), 2)

    def test_instrument_name_in_seed_data(self):
        """Verify seed JSON has instrument_name on the expected metrics."""
        import json
        from pathlib import Path

        seed_file = Path(__file__).resolve().parent.parent / "seeds" / "metric_library.json"
        with open(seed_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        # Check PHQ-9 has instrument_name
        phq9 = next(m for m in metrics if m["name"] == "PHQ-9 (Depression)")
        self.assertEqual(phq9["instrument_name"], "PHQ-9")

        # Check GAD-7
        gad7 = next(m for m in metrics if m["name"] == "GAD-7 (Anxiety)")
        self.assertEqual(gad7["instrument_name"], "GAD-7")

        # Check K10
        k10 = next(m for m in metrics if m["name"] == "K10 (Psychological Distress)")
        self.assertEqual(k10["instrument_name"], "K10")

        # Check all 5 inclusivity items
        inclusivity_names = [
            "Everyone is made to feel welcome",
            "Everyone is valued equally",
            "I am treated with respect",
            "People help each other",
            "I get help when I need it",
        ]
        for name in inclusivity_names:
            item = next(m for m in metrics if m["name"] == name)
            self.assertEqual(
                item["instrument_name"],
                "LogicalOutcomes Inclusivity Battery",
                f"{name} should have instrument_name set",
            )

    def test_metrics_without_instrument_name_not_in_filter(self):
        """Metrics without instrument_name are not returned by instrument filter."""
        MetricDefinition.objects.create(
            name="PHQ-9 Test", definition="Test",
            category="mental_health", instrument_name="PHQ-9",
        )
        MetricDefinition.objects.create(
            name="Standalone", definition="Test",
            category="general", instrument_name="",
        )

        with_instrument = MetricDefinition.objects.filter(instrument_name__gt="")
        self.assertEqual(with_instrument.count(), 1)
        self.assertEqual(with_instrument.first().name, "PHQ-9 Test")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GoalSaveFromSuggestionTest(TestCase):
    """Tests for the goal_create_from_suggestion HTMX endpoint."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.program = Program.objects.create(name="Suggestion Program", status="active")
        self.user = User.objects.create_user(
            username="suggestuser", password="testpass123", is_admin=False, is_active=True,
        )
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role=ROLE_STAFF, status="active",
        )

        self.client_file = ClientFile()
        self.client_file.first_name = "Suggest"
        self.client_file.last_name = "Client"
        self.client_file.status = "active"
        self.client_file.save()

        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="active",
        )

        self.metric = MetricDefinition.objects.create(
            name="Goal Progress",
            definition="How close to the goal",
            category="general",
            metric_type="scale",
            min_value=0,
            max_value=10,
            is_enabled=True,
            status="active",
        )

        self.suggestion = {
            "name": "Improve confidence",
            "description": "Build self-confidence through weekly exercises",
            "client_goal": "I want to feel more confident",
            "suggested_section": "Personal Growth",
            "metrics": [
                {"metric_id": self.metric.pk, "name": "Goal Progress"},
            ],
        }

        self.url = reverse("plans:goal_save_suggestion", kwargs={"client_id": self.client_file.pk})

    def tearDown(self):
        enc_module._fernet = None

    def _store_suggestion_in_session(self, key="goal_suggestion_test_abc12345"):
        """Store a suggestion in the session and return the key."""
        self.client.force_login(self.user)
        # Access session to initialise it
        session = self.client.session
        session[key] = self.suggestion
        session.save()
        return key

    def test_goal_save_suggestion_happy_path(self):
        """POST with valid suggestion_key returns 204 with HX-Redirect, creates goal + section + metric."""
        key = self._store_suggestion_in_session()
        response = self.client.post(self.url, {"suggestion_key": key})

        self.assertEqual(response.status_code, 204)
        self.assertIn("HX-Redirect", response)

        # Goal created
        target = PlanTarget.objects.filter(client_file=self.client_file).first()
        self.assertIsNotNone(target)
        self.assertEqual(target.name, "Improve confidence")

        # Section created with suggested name
        section = PlanSection.objects.filter(
            client_file=self.client_file, name="Personal Growth",
        ).first()
        self.assertIsNotNone(section)
        self.assertEqual(target.plan_section, section)

        # Metric assigned
        ptm = PlanTargetMetric.objects.filter(plan_target=target, metric_def=self.metric)
        self.assertTrue(ptm.exists())

    def test_goal_save_suggestion_expired_key(self):
        """POST with bad key returns 200 with error HTML."""
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"suggestion_key": "bad_key_xyz"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired")

    def test_goal_save_suggestion_auto_section_match_existing(self):
        """Existing section on participant is reused (not duplicated)."""
        # Create existing section matching the suggestion
        existing = PlanSection.objects.create(
            client_file=self.client_file,
            name="Personal Growth",
            program=self.program,
        )

        key = self._store_suggestion_in_session()
        response = self.client.post(self.url, {"suggestion_key": key})

        self.assertEqual(response.status_code, 204)
        target = PlanTarget.objects.filter(client_file=self.client_file).first()
        self.assertEqual(target.plan_section, existing)

        # Should NOT have created a duplicate section
        count = PlanSection.objects.filter(
            client_file=self.client_file, name__iexact="Personal Growth",
        ).count()
        self.assertEqual(count, 1)

    def test_goal_save_suggestion_auto_section_match_program(self):
        """Section exists on other participant in same program — creates section with that name."""
        # Create another client with a section in the same program
        other_client = ClientFile()
        other_client.first_name = "Other"
        other_client.last_name = "Person"
        other_client.status = "active"
        other_client.save()

        PlanSection.objects.create(
            client_file=other_client,
            name="Personal Growth",
            program=self.program,
        )

        key = self._store_suggestion_in_session()
        response = self.client.post(self.url, {"suggestion_key": key})

        self.assertEqual(response.status_code, 204)

        # A new section should be created for this client with the program's canonical name
        section = PlanSection.objects.filter(
            client_file=self.client_file, name="Personal Growth",
        ).first()
        self.assertIsNotNone(section)

    def test_goal_save_suggestion_auto_section_fallback(self):
        """No section suggestion -> 'General' created."""
        self.suggestion["suggested_section"] = ""
        key = self._store_suggestion_in_session()
        response = self.client.post(self.url, {"suggestion_key": key})

        self.assertEqual(response.status_code, 204)
        section = PlanSection.objects.filter(
            client_file=self.client_file, name="General",
        ).first()
        self.assertIsNotNone(section)

    def test_goal_save_suggestion_custom_metric(self):
        """custom_metric in suggestion creates MetricDefinition with category='custom'."""
        self.suggestion["custom_metric"] = {
            "name": "Weekly confidence check-in",
            "definition": "Rate your confidence this week",
            "min_value": 1,
            "max_value": 5,
            "unit": "score",
        }
        key = self._store_suggestion_in_session()
        response = self.client.post(self.url, {"suggestion_key": key})

        self.assertEqual(response.status_code, 204)
        custom = MetricDefinition.objects.filter(
            name="Weekly confidence check-in", category="custom",
        ).first()
        self.assertIsNotNone(custom)
        self.assertFalse(custom.is_library)
        self.assertEqual(custom.owning_program, self.program)

    def test_goal_save_suggestion_permission_denied(self):
        """User without program role gets 403."""
        other_user = User.objects.create_user(
            username="noaccess", password="testpass123", is_admin=False, is_active=True,
        )
        self.client.force_login(other_user)
        # Store suggestion in session for other_user
        session = self.client.session
        session["goal_suggestion_test_perm"] = self.suggestion
        session.save()

        response = self.client.post(self.url, {"suggestion_key": "goal_suggestion_test_perm"})
        self.assertEqual(response.status_code, 403)

    def test_create_goal_empty_name_raises(self):
        """_create_goal raises ValueError when name is empty or whitespace."""
        from apps.plans.views import _create_goal

        section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Test Section",
            program=self.program,
        )

        for empty_name in ["", "   ", None]:
            with self.assertRaises(ValueError, msg=f"Should raise for name={empty_name!r}"):
                _create_goal(
                    client_file=self.client_file,
                    user=self.user,
                    name=empty_name,
                    section=section,
                )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FHIRGoalMetadataTest(TestCase):
    """Tests for FHIR-informed metadata auto-population on PlanTarget."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        self.section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Test Section",
            program=self.program,
        )

    def test_goal_source_joint_when_both_fields(self):
        """Goal source = joint when both description and client_goal populated."""
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Find housing"
        target.description = "Worker notes about housing plan"
        target.client_goal = "I want a safe place to live"
        target.save()
        self.assertEqual(target.goal_source, "joint")
        self.assertEqual(target.metadata_sources.get("goal_source"), "heuristic")

    def test_goal_source_participant_when_only_client_goal(self):
        """Goal source = participant when only client_goal is populated."""
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Find housing"
        target.client_goal = "I want a safe place to live"
        target.save()
        self.assertEqual(target.goal_source, "participant")

    def test_goal_source_worker_when_only_description(self):
        """Goal source = worker when only description is populated."""
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Improve coping skills"
        target.description = "Build resilience strategies"
        target.save()
        self.assertEqual(target.goal_source, "worker")

    def test_goal_source_empty_when_neither_populated(self):
        """Goal source left empty when neither description nor client_goal set."""
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Generic goal"
        target.save()
        self.assertEqual(target.goal_source, "")

    def test_target_date_from_program_default(self):
        """Target date auto-set from program.default_goal_review_days."""
        self.program.default_goal_review_days = 90
        self.program.save()
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test goal"
        target.save()
        self.assertIsNotNone(target.target_date)
        self.assertEqual(target.metadata_sources.get("target_date"), "program_default")

    def test_no_target_date_without_program_default(self):
        """No target date when program has no default_goal_review_days."""
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test goal"
        target.save()
        self.assertIsNone(target.target_date)

    def test_on_hold_status_valid(self):
        """PlanTarget can be set to on_hold status."""
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test goal"
        target.save()
        target.status = "on_hold"
        target.save()
        target.refresh_from_db()
        self.assertEqual(target.status, "on_hold")

    def test_goal_source_not_overwritten_on_update(self):
        """Goal source preserved on subsequent saves (only set on creation)."""
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test goal"
        target.description = "Worker description"
        target.save()
        self.assertEqual(target.goal_source, "worker")
        # Add client_goal and resave — should NOT change goal_source
        target.client_goal = "My own words"
        target.save()
        self.assertEqual(target.goal_source, "worker")

    def test_is_auto_inferred_helper(self):
        """is_auto_inferred returns True for heuristic/ai_inferred sources."""
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test"
        target.description = "Desc"
        target.save()
        self.assertTrue(target.is_auto_inferred("goal_source"))
        self.assertFalse(target.is_auto_inferred("continuous"))

    def test_plan_section_period_fields_nullable(self):
        """PlanSection period fields are nullable by default."""
        self.assertIsNone(self.section.period_start)
        self.assertIsNone(self.section.period_end)

