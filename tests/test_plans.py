"""Tests for the plans app — signals and achievement status behaviour (REQ-G4).

Covers the post_save signal on PlanTarget that auto-updates achievement_status
when a goal's lifecycle status changes.
"""
import datetime

from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.test import TestCase, Client, override_settings
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
            user=self.user, program=self.program, role="staff", status="active",
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

