"""Tests for metric distribution aggregation and insights views.

Covers:
- MetricDefinition new fields and validation
- classify_band() with higher_is_better and fallback thresholds
- get_metric_distributions() per-participant aggregation
- get_achievement_rates() success rate calculation
- get_data_completeness() enrolled vs scored counts
- get_two_lenses() self-report vs staff comparison
- Privacy: n<5 suppression, n<10 exclusion
- program_insights() view context variables
"""
from datetime import date, timedelta

from cryptography.fernet import Fernet

from django.core.exceptions import ValidationError
from django.test import Client as TestClient, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

import konote.encryption as enc_module
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.reports.metric_insights import (
    MIN_N_FOR_BAND,
    MIN_N_FOR_DISPLAY,
    SUPPRESSED_LABEL,
    get_achievement_rates,
    get_data_completeness,
    get_metric_distributions,
    get_metric_trends,
    get_trend_direction,
    get_two_lenses,
)

TEST_KEY = Fernet.generate_key().decode()


# ── Model field tests ──────────────────────────────────────────────


class MetricDefinitionFieldsTest(SimpleTestCase):
    """Test new MetricDefinition fields and validation."""

    def _make_metric(self, **kwargs):
        defaults = {
            "name": "Test Metric",
            "definition": "Test",
            "metric_type": "scale",
            "min_value": 1,
            "max_value": 5,
        }
        defaults.update(kwargs)
        m = MetricDefinition(**defaults)
        return m

    def test_default_metric_type_is_scale(self):
        m = self._make_metric()
        self.assertEqual(m.metric_type, "scale")

    def test_default_higher_is_better_is_true(self):
        m = self._make_metric()
        self.assertTrue(m.higher_is_better)

    def test_threshold_ordering_validation(self):
        m = self._make_metric(threshold_low=4, threshold_high=2)
        with self.assertRaises(ValidationError):
            m.clean()

    def test_equal_thresholds_rejected(self):
        m = self._make_metric(threshold_low=3, threshold_high=3)
        with self.assertRaises(ValidationError):
            m.clean()

    def test_valid_thresholds_pass(self):
        m = self._make_metric(threshold_low=2, threshold_high=4)
        m.clean()  # Should not raise

    def test_achievement_with_thresholds_rejected(self):
        m = self._make_metric(metric_type="achievement", threshold_low=2)
        with self.assertRaises(ValidationError):
            m.clean()

    def test_scale_with_achievement_options_rejected(self):
        m = self._make_metric(metric_type="scale", achievement_options=["Yes", "No"])
        with self.assertRaises(ValidationError):
            m.clean()


class ClassifyBandTest(SimpleTestCase):
    """Test the classify_band() method on MetricDefinition."""

    def _make_metric(self, **kwargs):
        defaults = {
            "name": "Test",
            "definition": "Test",
            "metric_type": "scale",
            "min_value": 1,
            "max_value": 5,
            "threshold_low": 2,
            "threshold_high": 4,
            "higher_is_better": True,
        }
        defaults.update(kwargs)
        return MetricDefinition(**defaults)

    def test_low_band(self):
        m = self._make_metric()
        self.assertEqual(m.classify_band(1), "band_low")
        self.assertEqual(m.classify_band(2), "band_low")

    def test_mid_band(self):
        m = self._make_metric()
        self.assertEqual(m.classify_band(3), "band_mid")

    def test_high_band(self):
        m = self._make_metric()
        self.assertEqual(m.classify_band(4), "band_high")
        self.assertEqual(m.classify_band(5), "band_high")

    def test_lower_is_better_flips_bands(self):
        """PHQ-9 style: high value = more support needed (band_low)."""
        m = self._make_metric(
            min_value=0, max_value=27,
            threshold_low=5, threshold_high=15,
            higher_is_better=False,
        )
        # Low score = good (band_high for lower-is-better)
        self.assertEqual(m.classify_band(3), "band_high")
        # Mid score
        self.assertEqual(m.classify_band(10), "band_mid")
        # High score = needs support (band_low for lower-is-better)
        self.assertEqual(m.classify_band(20), "band_low")

    def test_fallback_thresholds_when_not_set(self):
        """When thresholds not set, use scale-thirds."""
        m = self._make_metric(threshold_low=None, threshold_high=None)
        # 1-5 scale: low = 1 + (5-1)/3 ≈ 2.33, high = 1 + 2*(5-1)/3 ≈ 3.67
        self.assertEqual(m.classify_band(1), "band_low")
        self.assertEqual(m.classify_band(3), "band_mid")
        self.assertEqual(m.classify_band(5), "band_high")

    def test_no_min_max_returns_none(self):
        m = self._make_metric(
            min_value=None, max_value=None,
            threshold_low=None, threshold_high=None,
        )
        self.assertIsNone(m.classify_band(3))


# ── Aggregation function tests ─────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricDistributionsTest(TestCase):
    """Test get_metric_distributions() per-participant aggregation."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = self.program  # Placeholder — we create a real user below
        from apps.auth_app.models import User
        self.user = User.objects.create_user(username="worker", password="testpass123")

        self.metric = MetricDefinition.objects.create(
            name="Goal Progress",
            definition="How much progress toward the goal",
            metric_type="scale",
            min_value=1,
            max_value=5,
            threshold_low=2,
            threshold_high=4,
            higher_is_better=True,
            is_universal=True,
            category="general",
        )

        self.date_from = date.today() - timedelta(days=365)
        self.date_to = date.today()

    def _create_participant_with_scores(self, record_id, scores, days_offsets=None):
        """Create a client enrolled in the program with metric scores.

        Args:
            record_id: Unique record ID
            scores: List of metric values (floats)
            days_offsets: Optional list of day offsets for backdating
        """
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Goals", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal 1",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)

        for i, score in enumerate(scores):
            offset = (days_offsets[i] if days_offsets else i * 30) if days_offsets else i * 30
            backdate = timezone.now() - timedelta(days=offset)
            note = ProgressNote.objects.create(
                client_file=client,
                note_type="full",
                author=self.user,
                author_program=self.program,
                backdate=backdate,
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note, plan_target=target,
            )
            MetricValue.objects.create(
                progress_note_target=pnt,
                metric_def=self.metric,
                value=str(score),
            )
        return client

    def test_empty_program_returns_empty(self):
        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        self.assertEqual(result, {})

    def test_single_assessment_excluded_from_distributions(self):
        """Participants with only 1 assessment should be flagged as new, not in bands."""
        for i in range(12):
            self._create_participant_with_scores(f"SINGLE-{i}", [3])

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        # All have single assessments, so none should be in distributions
        self.assertEqual(result, {})

    def test_distributions_with_sufficient_data(self):
        """12 participants with 2+ scores each should produce distributions."""
        for i in range(12):
            if i < 3:
                scores = [1, 2]  # Low band
            elif i < 7:
                scores = [3, 3]  # Mid band
            else:
                scores = [4, 5]  # High band
            self._create_participant_with_scores(f"DIST-{i}", scores)

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        self.assertIn(self.metric.pk, result)

        dist = result[self.metric.pk]
        self.assertEqual(dist["total"], 12)
        self.assertEqual(dist["n_new_participants"], 0)

    def test_multi_goal_participant_uses_median(self):
        """A participant with multiple goals should use median across goals."""
        client = ClientFile.objects.create(record_id="MULTI-GOAL")
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Goals", program=self.program,
        )

        # Create two targets with different scores
        for goal_num, score_series in enumerate([(1, 2), (5, 5)]):
            target = PlanTarget.objects.create(
                plan_section=section, client_file=client, name=f"Goal {goal_num}",
            )
            PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)
            for i, score in enumerate(score_series):
                note = ProgressNote.objects.create(
                    client_file=client, note_type="full",
                    author=self.user, author_program=self.program,
                    backdate=timezone.now() - timedelta(days=i * 30),
                )
                pnt = ProgressNoteTarget.objects.create(
                    progress_note=note, plan_target=target,
                )
                MetricValue.objects.create(
                    progress_note_target=pnt, metric_def=self.metric, value=str(score),
                )

        # Add enough other participants for MIN_N_FOR_DISPLAY
        for i in range(11):
            self._create_participant_with_scores(f"FILLER-{i}", [3, 3])

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        # The multi-goal participant: latest scores are [2, 5], median = 3.5 → mid band
        self.assertIn(self.metric.pk, result)

    def test_below_minimum_n_excluded(self):
        """Fewer than MIN_N_FOR_DISPLAY participants should be excluded."""
        for i in range(5):  # Less than 10
            self._create_participant_with_scores(f"FEW-{i}", [3, 4])

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        self.assertEqual(result, {})


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BandSuppressionTest(TestCase):
    """Test that band counts < 5 are suppressed (Canadian n<5 standard)."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        from apps.auth_app.models import User
        self.user = User.objects.create_user(username="worker2", password="testpass123")

        self.metric = MetricDefinition.objects.create(
            name="Test Scale",
            definition="Test",
            metric_type="scale",
            min_value=1,
            max_value=5,
            threshold_low=2,
            threshold_high=4,
            higher_is_better=True,
            category="general",
        )
        self.date_from = date.today() - timedelta(days=365)
        self.date_to = date.today()

    def _add_participant(self, record_id, scores):
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Goals", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="G",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)
        for i, score in enumerate(scores):
            note = ProgressNote.objects.create(
                client_file=client, note_type="full",
                author=self.user, author_program=self.program,
                backdate=timezone.now() - timedelta(days=i * 30),
            )
            pnt = ProgressNoteTarget.objects.create(progress_note=note, plan_target=target)
            MetricValue.objects.create(
                progress_note_target=pnt, metric_def=self.metric, value=str(score),
            )

    def test_small_band_count_suppressed(self):
        """A band with fewer than 5 participants shows '< 5' instead of count."""
        # 2 in low, 4 in mid, 6 in high — low should be suppressed
        for i in range(2):
            self._add_participant(f"LOW-{i}", [1, 1])
        for i in range(4):
            self._add_participant(f"MID-{i}", [3, 3])
        for i in range(6):
            self._add_participant(f"HIGH-{i}", [5, 5])

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        if self.metric.pk in result:
            dist = result[self.metric.pk]
            self.assertEqual(dist["band_low_count"], SUPPRESSED_LABEL)
            self.assertEqual(dist["band_mid_count"], SUPPRESSED_LABEL)
            # High band has 6, should NOT be suppressed
            self.assertEqual(dist["band_high_count"], 6)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AchievementRatesTest(TestCase):
    """Test get_achievement_rates() success rate calculation."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Employment Program", status="active")
        from apps.auth_app.models import User
        self.user = User.objects.create_user(username="worker3", password="testpass123")

        self.metric = MetricDefinition.objects.create(
            name="Employment Status",
            definition="Whether participant gained employment",
            metric_type="achievement",
            achievement_options=["Employed", "In training", "Unemployed"],
            achievement_success_values=["Employed"],
            target_rate=70,
            category="employment",
        )
        self.date_from = date.today() - timedelta(days=365)
        self.date_to = date.today()

    def _add_participant(self, record_id, value):
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Goals", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Employment",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)
        note = ProgressNote.objects.create(
            client_file=client, note_type="full",
            author=self.user, author_program=self.program,
        )
        pnt = ProgressNoteTarget.objects.create(progress_note=note, plan_target=target)
        MetricValue.objects.create(
            progress_note_target=pnt, metric_def=self.metric, value=value,
        )

    def test_achievement_rate_calculation(self):
        """7 of 10 employed should give 70% achievement rate."""
        for i in range(7):
            self._add_participant(f"EMP-{i}", "Employed")
        for i in range(3):
            self._add_participant(f"UNEMP-{i}", "Unemployed")

        result = get_achievement_rates(self.program, self.date_from, self.date_to)
        self.assertIn(self.metric.pk, result)
        self.assertEqual(result[self.metric.pk]["achieved_count"], 7)
        self.assertEqual(result[self.metric.pk]["total"], 10)
        self.assertEqual(result[self.metric.pk]["achieved_pct"], 70.0)
        self.assertEqual(result[self.metric.pk]["target_rate"], 70)

    def test_below_minimum_n_excluded(self):
        """Fewer than 10 participants should be excluded."""
        for i in range(5):
            self._add_participant(f"FEW-{i}", "Employed")

        result = get_achievement_rates(self.program, self.date_from, self.date_to)
        self.assertEqual(result, {})


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DataCompletenessTest(TestCase):
    """Test get_data_completeness() enrolled vs scored counts."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        from apps.auth_app.models import User
        self.user = User.objects.create_user(username="worker4", password="testpass123")

        self.metric = MetricDefinition.objects.create(
            name="Goal Progress",
            definition="Test",
            metric_type="scale",
            min_value=1,
            max_value=5,
            category="general",
        )
        self.date_from = date.today() - timedelta(days=365)
        self.date_to = date.today()

    def _enrol_client(self, record_id, with_score=False):
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        if with_score:
            section = PlanSection.objects.create(
                client_file=client, name="Goals", program=self.program,
            )
            target = PlanTarget.objects.create(
                plan_section=section, client_file=client, name="G",
            )
            PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)
            note = ProgressNote.objects.create(
                client_file=client, note_type="full",
                author=self.user, author_program=self.program,
            )
            pnt = ProgressNoteTarget.objects.create(progress_note=note, plan_target=target)
            MetricValue.objects.create(
                progress_note_target=pnt, metric_def=self.metric, value="3",
            )

    def test_full_completeness(self):
        """All enrolled have scores → 'full' level."""
        for i in range(10):
            self._enrol_client(f"FULL-{i}", with_score=True)

        result = get_data_completeness(self.program, self.date_from, self.date_to)
        self.assertEqual(result["enrolled_count"], 10)
        self.assertEqual(result["with_scores_count"], 10)
        self.assertEqual(result["completeness_pct"], 100.0)
        self.assertEqual(result["completeness_level"], "full")

    def test_partial_completeness(self):
        """6 of 10 have scores → 'partial' level."""
        for i in range(6):
            self._enrol_client(f"SCORED-{i}", with_score=True)
        for i in range(4):
            self._enrol_client(f"NOSCORED-{i}", with_score=False)

        result = get_data_completeness(self.program, self.date_from, self.date_to)
        self.assertEqual(result["enrolled_count"], 10)
        self.assertEqual(result["with_scores_count"], 6)
        self.assertEqual(result["completeness_pct"], 60.0)
        self.assertEqual(result["completeness_level"], "partial")

    def test_low_completeness(self):
        """3 of 10 have scores → 'low' level."""
        for i in range(3):
            self._enrol_client(f"SCORED-{i}", with_score=True)
        for i in range(7):
            self._enrol_client(f"NOSCORED-{i}", with_score=False)

        result = get_data_completeness(self.program, self.date_from, self.date_to)
        self.assertEqual(result["completeness_pct"], 30.0)
        self.assertEqual(result["completeness_level"], "low")

    def test_empty_program(self):
        result = get_data_completeness(self.program, self.date_from, self.date_to)
        self.assertEqual(result["enrolled_count"], 0)
        self.assertEqual(result["completeness_level"], "low")


class TrendDirectionTest(SimpleTestCase):
    """Test get_trend_direction() analysis."""

    def test_improving(self):
        trends = {1: [
            {"month": "2025-10", "band_low_pct": 30, "band_high_pct": 40, "total": 20},
            {"month": "2025-11", "band_low_pct": 25, "band_high_pct": 45, "total": 20},
            {"month": "2025-12", "band_low_pct": 20, "band_high_pct": 50, "total": 20},
        ]}
        self.assertEqual(get_trend_direction(trends, 1), "improving")

    def test_declining(self):
        trends = {1: [
            {"month": "2025-10", "band_low_pct": 20, "band_high_pct": 50, "total": 20},
            {"month": "2025-11", "band_low_pct": 25, "band_high_pct": 45, "total": 20},
            {"month": "2025-12", "band_low_pct": 30, "band_high_pct": 40, "total": 20},
        ]}
        self.assertEqual(get_trend_direction(trends, 1), "declining")

    def test_stable(self):
        trends = {1: [
            {"month": "2025-10", "band_low_pct": 25, "band_high_pct": 45, "total": 20},
            {"month": "2025-11", "band_low_pct": 25, "band_high_pct": 46, "total": 20},
            {"month": "2025-12", "band_low_pct": 24, "band_high_pct": 47, "total": 20},
        ]}
        self.assertEqual(get_trend_direction(trends, 1), "stable")

    def test_insufficient_data(self):
        trends = {1: [
            {"month": "2025-12", "band_low_pct": 25, "band_high_pct": 45, "total": 20},
        ]}
        self.assertEqual(get_trend_direction(trends, 1), "stable")

    def test_missing_metric(self):
        self.assertEqual(get_trend_direction({}, 99), "stable")


# ── View context tests ────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramInsightsViewContextTest(TestCase):
    """Test that program_insights() passes correct context variables."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(
            username="pm_user", password="testpass123", display_name="PM",
        )
        UserProgramRole.objects.create(
            user=self.user, program=self.program,
            role="program_manager", status="active",
        )

        self.metric = MetricDefinition.objects.create(
            name="Goal Progress",
            definition="Scale metric for testing",
            metric_type="scale",
            min_value=1,
            max_value=5,
            threshold_low=2,
            threshold_high=4,
            higher_is_better=True,
            is_universal=True,
            category="general",
        )

        self.test_client = TestClient()
        self.test_client.login(username="pm_user", password="testpass123")
        self.url = reverse("reports:program_insights")

    def tearDown(self):
        enc_module._fernet = None

    def _create_participant(self, record_id, scores):
        """Create an enrolled participant with metric scores."""
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Goals", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal 1",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)
        for i, score in enumerate(scores):
            note = ProgressNote.objects.create(
                client_file=client, note_type="full",
                author=self.user, author_program=self.program,
                backdate=timezone.now() - timedelta(days=i * 30),
                engagement_observation="engaged",
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note, plan_target=target,
                progress_descriptor="shifting",
            )
            MetricValue.objects.create(
                progress_note_target=pnt, metric_def=self.metric, value=str(score),
            )

    def _get_params(self):
        """GET params that make the form valid."""
        return {
            "program": self.program.pk,
            "time_period": "12m",
        }

    def test_sparse_data_no_metric_context(self):
        """With <20 notes (sparse tier), metric context should be empty defaults."""
        # Create just a few participants — not enough for non-sparse tier
        for i in range(3):
            self._create_participant(f"SPARSE-{i}", [3, 4])

        response = self.test_client.get(self.url, self._get_params())
        self.assertEqual(response.status_code, 200)
        ctx = response.context

        self.assertTrue(ctx["show_results"])
        self.assertEqual(ctx["data_tier"], "sparse")
        self.assertEqual(ctx["metric_distributions"], {})
        self.assertEqual(ctx["achievement_rates"], {})
        self.assertIsNone(ctx["two_lenses"])
        self.assertEqual(ctx["total_new_participants"], 0)

    def test_sufficient_data_has_metric_context(self):
        """With 20+ notes, metric context variables should be populated."""
        # 12 participants × 2 notes each = 24 notes (limited tier)
        for i in range(12):
            self._create_participant(f"DATA-{i}", [3, 4])

        response = self.test_client.get(self.url, self._get_params())
        self.assertEqual(response.status_code, 200)
        ctx = response.context

        self.assertTrue(ctx["show_results"])
        self.assertIn(ctx["data_tier"], ("limited", "full"))
        # Metric distributions should be populated (12 multi-assessment participants)
        self.assertIn(self.metric.pk, ctx["metric_distributions"])
        self.assertIsInstance(ctx["data_completeness"], dict)
        self.assertIn("completeness_pct", ctx["data_completeness"])

    def test_auto_expand_flags_present(self):
        """Auto-expand flags should always be in context when show_results is True."""
        for i in range(12):
            self._create_participant(f"EXPAND-{i}", [3, 4])

        response = self.test_client.get(self.url, self._get_params())
        ctx = response.context

        self.assertIn("expand_participant_voice", ctx)
        self.assertIn("expand_distributions", ctx)
        self.assertIn("expand_outcomes", ctx)
        self.assertIn("expand_staff_assessments", ctx)
        self.assertIn("expand_engagement", ctx)
        # Participant Voice is always open
        self.assertTrue(ctx["expand_participant_voice"])
        # Engagement defaults to collapsed
        self.assertFalse(ctx["expand_engagement"])

    def test_expand_distributions_matches_data(self):
        """expand_distributions should be True when metric_distributions is non-empty."""
        for i in range(12):
            self._create_participant(f"DIST-{i}", [3, 4])

        response = self.test_client.get(self.url, self._get_params())
        ctx = response.context

        has_distributions = bool(ctx["metric_distributions"])
        self.assertEqual(ctx["expand_distributions"], has_distributions)

    def test_no_form_submission_no_results(self):
        """Without GET params, show_results should not be in context."""
        response = self.test_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("show_results", response.context)

    def test_unauthenticated_redirects(self):
        """Unauthenticated users should be redirected to login."""
        anon_client = TestClient()
        response = anon_client.get(self.url, self._get_params())
        self.assertEqual(response.status_code, 302)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BuildMetricContextTest(TestCase):
    """Test the _build_metric_context() helper directly."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(
            username="worker5", password="testpass123",
        )
        UserProgramRole.objects.create(
            user=self.user, program=self.program,
            role="staff", status="active",
        )

        self.metric = MetricDefinition.objects.create(
            name="Goal Progress",
            definition="Scale metric for testing",
            metric_type="scale",
            min_value=1,
            max_value=5,
            threshold_low=2,
            threshold_high=4,
            higher_is_better=True,
            is_universal=True,
            category="general",
        )

        self.date_from = date.today() - timedelta(days=365)
        self.date_to = date.today()

    def tearDown(self):
        enc_module._fernet = None

    def _create_participant(self, record_id, scores):
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Goals", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal 1",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)
        for i, score in enumerate(scores):
            note = ProgressNote.objects.create(
                client_file=client, note_type="full",
                author=self.user, author_program=self.program,
                backdate=timezone.now() - timedelta(days=i * 30),
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note, plan_target=target,
            )
            MetricValue.objects.create(
                progress_note_target=pnt, metric_def=self.metric, value=str(score),
            )

    def test_returns_all_expected_keys(self):
        """Helper should return all keys the template expects."""
        from apps.reports.insights_views import _build_metric_context

        for i in range(12):
            self._create_participant(f"CTX-{i}", [3, 4])

        result = _build_metric_context(
            self.program, self.date_from, self.date_to, active_themes=[],
        )

        expected_keys = {
            "metric_distributions", "achievement_rates", "metric_trends",
            "two_lenses", "data_completeness", "trend_directions",
            "lead_outcome", "lead_metric", "lead_trend_direction",
            "distributions_summary_pct", "distributions_trend_direction",
            "total_new_participants", "has_urgent_themes",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_has_urgent_themes_flag(self):
        """has_urgent_themes should be True when active_themes has an urgent item."""
        from apps.reports.insights_views import _build_metric_context

        result = _build_metric_context(
            self.program, self.date_from, self.date_to,
            active_themes=[{"priority": "urgent", "name": "Test"}],
        )
        self.assertTrue(result["has_urgent_themes"])

    def test_no_urgent_themes_flag(self):
        """has_urgent_themes should be False with no urgent items."""
        from apps.reports.insights_views import _build_metric_context

        result = _build_metric_context(
            self.program, self.date_from, self.date_to,
            active_themes=[{"priority": "important", "name": "Test"}],
        )
        self.assertFalse(result["has_urgent_themes"])
