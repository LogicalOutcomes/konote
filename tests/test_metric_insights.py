"""Tests for metric distribution aggregation, achievement rates, and data completeness."""
from datetime import date, timedelta

from cryptography.fernet import Fernet

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

import konote.encryption as enc_module
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
from apps.programs.models import Program
from apps.reports.metric_insights import (
    MIN_BAND_COUNT,
    MIN_N_FOR_DISTRIBUTION,
    get_achievement_rates,
    get_data_completeness,
    get_metric_distributions,
    get_metric_trends,
    get_two_lenses,
)

User = get_user_model()
TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricDistributionTest(TestCase):
    """Test per-participant band distribution aggregation."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")
        self.metric = MetricDefinition.objects.create(
            name="Goal Progress", category="general",
            is_universal=True, metric_type="scale",
            min_value=1, max_value=5,
            threshold_low=2, threshold_high=4,
            higher_is_better=True,
        )
        self.date_from = date.today() - timedelta(days=90)
        self.date_to = date.today()

    def _create_participant_with_scores(self, record_id, scores):
        """Create a participant enrolled in the program with metric scores.

        Each score creates a separate note (so the participant has multiple assessments).
        """
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Section", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)

        for i, score in enumerate(scores):
            note = ProgressNote.objects.create(
                client_file=client, note_type="full",
                author=self.user, author_program=self.program,
                backdate=timezone.now() - timedelta(days=i + 1),
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

    def test_per_participant_aggregation_not_per_target(self):
        """Multi-goal participants should not be over-counted."""
        client = ClientFile.objects.create(record_id="MULTI-GOAL-001")
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Section", program=self.program,
        )
        # Two targets for the same client
        target1 = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal 1",
        )
        target2 = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal 2",
        )
        PlanTargetMetric.objects.create(plan_target=target1, metric_def=self.metric)
        PlanTargetMetric.objects.create(plan_target=target2, metric_def=self.metric)

        # Create 2 notes per target (so the participant has >1 assessment)
        for target in [target1, target2]:
            for i in range(2):
                note = ProgressNote.objects.create(
                    client_file=client, note_type="full",
                    author=self.user, author_program=self.program,
                    backdate=timezone.now() - timedelta(days=i + 1),
                )
                pnt = ProgressNoteTarget.objects.create(
                    progress_note=note, plan_target=target,
                )
                MetricValue.objects.create(
                    progress_note_target=pnt, metric_def=self.metric, value="4",
                )

        # Add 9 more participants to meet n>=10 threshold
        for i in range(9):
            self._create_participant_with_scores(f"FILL-{i:03d}", [4, 4])

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        # Total should be 10 (not 11 or higher from double-counting)
        dist = result.get(self.metric.pk)
        self.assertIsNotNone(dist)
        self.assertEqual(dist["total"], 10)

    def test_higher_is_better_false_flips_bands(self):
        """When higher_is_better=False, low score = band_high (good)."""
        phq = MetricDefinition.objects.create(
            name="PHQ-9", category="mental_health",
            metric_type="scale", min_value=0, max_value=27,
            threshold_low=5, threshold_high=15,
            higher_is_better=False,
        )
        for i in range(12):
            client = ClientFile.objects.create(record_id=f"PHQ-{i:03d}")
            ClientProgramEnrolment.objects.create(
                client_file=client, program=self.program, status="enrolled",
            )
            section = PlanSection.objects.create(
                client_file=client, name="Section", program=self.program,
            )
            target = PlanTarget.objects.create(
                plan_section=section, client_file=client, name="Goal",
            )
            PlanTargetMetric.objects.create(plan_target=target, metric_def=phq)
            # Score = 3 (below threshold_low=5, so "good" when lower is better)
            for j in range(2):
                note = ProgressNote.objects.create(
                    client_file=client, note_type="full",
                    author=self.user, author_program=self.program,
                    backdate=timezone.now() - timedelta(days=j + 1),
                )
                pnt = ProgressNoteTarget.objects.create(
                    progress_note=note, plan_target=target,
                )
                MetricValue.objects.create(
                    progress_note_target=pnt, metric_def=phq, value="3",
                )

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        dist = result.get(phq.pk)
        self.assertIsNotNone(dist)
        # Low score (3 < 5) with higher_is_better=False → band_high
        self.assertEqual(dist["band_high_pct"], 100.0)
        self.assertFalse(dist["higher_is_better"])

    def test_n_less_than_5_band_suppression(self):
        """Band counts below 5 should be suppressed to '< 5'."""
        # Create 10 participants: 3 in low band, 7 in high band
        for i in range(3):
            self._create_participant_with_scores(f"LOW-{i:03d}", [1, 1])
        for i in range(7):
            self._create_participant_with_scores(f"HIGH-{i:03d}", [5, 5])

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        dist = result.get(self.metric.pk)
        self.assertIsNotNone(dist)
        # 3 in low band → suppressed
        self.assertEqual(dist["band_low_count"], "< 5")
        # 0 in mid band → suppressed
        self.assertEqual(dist["band_mid_count"], "< 5")
        # 7 in high band → shown
        self.assertEqual(dist["band_high_count"], 7)

    def test_n_less_than_10_metric_excluded(self):
        """Metrics with fewer than 10 participants should be excluded."""
        for i in range(5):
            self._create_participant_with_scores(f"FEW-{i:03d}", [3, 3])

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        self.assertNotIn(self.metric.pk, result)

    def test_new_participants_excluded(self):
        """Participants with only 1 assessment should be flagged as new."""
        # 10 participants with 2+ assessments
        for i in range(10):
            self._create_participant_with_scores(f"REG-{i:03d}", [4, 4])
        # 3 participants with only 1 assessment
        for i in range(3):
            self._create_participant_with_scores(f"NEW-{i:03d}", [4])

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        dist = result.get(self.metric.pk)
        self.assertIsNotNone(dist)
        self.assertEqual(dist["total"], 10)  # Only multi-assessment participants
        self.assertEqual(dist["n_new_participants"], 3)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AchievementRateTest(TestCase):
    """Test achievement rate calculation."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")
        self.metric = MetricDefinition.objects.create(
            name="Employment", category="employment",
            metric_type="achievement",
            achievement_options=["Employed", "In training", "Unemployed"],
            achievement_success_values=["Employed"],
            target_rate=70,
        )
        self.date_from = date.today() - timedelta(days=90)
        self.date_to = date.today()

    def _create_participant_with_achievement(self, record_id, value):
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Section", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)
        note = ProgressNote.objects.create(
            client_file=client, note_type="full",
            author=self.user, author_program=self.program,
        )
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note, plan_target=target,
        )
        MetricValue.objects.create(
            progress_note_target=pnt, metric_def=self.metric, value=value,
        )
        return client

    def test_achievement_rate_calculation(self):
        """Achievement rate should count success values correctly."""
        for i in range(7):
            self._create_participant_with_achievement(f"EMP-{i:03d}", "Employed")
        for i in range(3):
            self._create_participant_with_achievement(f"UNEMP-{i:03d}", "Unemployed")

        result = get_achievement_rates(self.program, self.date_from, self.date_to)
        ach = result.get(self.metric.pk)
        self.assertIsNotNone(ach)
        self.assertEqual(ach["achieved_count"], 7)
        self.assertEqual(ach["total"], 10)
        self.assertEqual(ach["achieved_pct"], 70.0)
        self.assertEqual(ach["target_rate"], 70)

    def test_achievement_n_less_than_10_excluded(self):
        """Achievement metrics with <10 participants should be excluded."""
        for i in range(5):
            self._create_participant_with_achievement(f"FEW-{i:03d}", "Employed")

        result = get_achievement_rates(self.program, self.date_from, self.date_to)
        self.assertNotIn(self.metric.pk, result)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DataCompletenessTest(TestCase):
    """Test data completeness calculation."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")
        self.metric = MetricDefinition.objects.create(
            name="Goal Progress", category="general", metric_type="scale",
            min_value=1, max_value=5,
        )
        self.date_from = date.today() - timedelta(days=90)
        self.date_to = date.today()

    def _enrol_participant(self, record_id, with_score=False):
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        if with_score:
            section = PlanSection.objects.create(
                client_file=client, name="Section", program=self.program,
            )
            target = PlanTarget.objects.create(
                plan_section=section, client_file=client, name="Goal",
            )
            note = ProgressNote.objects.create(
                client_file=client, note_type="full",
                author=self.user, author_program=self.program,
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note, plan_target=target,
            )
            MetricValue.objects.create(
                progress_note_target=pnt, metric_def=self.metric, value="3",
            )
        return client

    def test_full_completeness(self):
        """Over 80% → full."""
        for i in range(10):
            self._enrol_participant(f"FULL-{i:03d}", with_score=True)

        result = get_data_completeness(self.program, self.date_from, self.date_to)
        self.assertEqual(result["completeness_level"], "full")
        self.assertEqual(result["enrolled_count"], 10)
        self.assertEqual(result["with_scores_count"], 10)
        self.assertEqual(result["completeness_pct"], 100.0)

    def test_partial_completeness(self):
        """50-80% → partial."""
        for i in range(7):
            self._enrol_participant(f"SCORED-{i:03d}", with_score=True)
        for i in range(3):
            self._enrol_participant(f"NOSCORE-{i:03d}", with_score=False)

        result = get_data_completeness(self.program, self.date_from, self.date_to)
        # 7/10 = 70% → partial
        self.assertEqual(result["completeness_level"], "partial")

    def test_low_completeness(self):
        """Under 50% → low."""
        for i in range(3):
            self._enrol_participant(f"SCORED-{i:03d}", with_score=True)
        for i in range(7):
            self._enrol_participant(f"NOSCORE-{i:03d}", with_score=False)

        result = get_data_completeness(self.program, self.date_from, self.date_to)
        self.assertEqual(result["completeness_level"], "low")
        self.assertEqual(result["completeness_pct"], 30.0)

    def test_no_enrolled(self):
        """Zero enrolled → low with zero counts."""
        result = get_data_completeness(self.program, self.date_from, self.date_to)
        self.assertEqual(result["completeness_level"], "low")
        self.assertEqual(result["enrolled_count"], 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TwoLensesTest(TestCase):
    """Test Two Lenses gap calculation."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")
        self.self_efficacy = MetricDefinition.objects.create(
            name="Self-Efficacy", category="general",
            is_universal=True, metric_type="scale",
            min_value=1, max_value=5,
            threshold_low=2, threshold_high=4,
            higher_is_better=True,
        )
        self.date_from = date.today() - timedelta(days=90)
        self.date_to = date.today()

    def test_insufficient_data_returns_none(self):
        """With fewer than 10 participants, returns None."""
        result = get_two_lenses(self.program, self.date_from, self.date_to)
        self.assertIsNone(result)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AutoExpandLogicTest(TestCase):
    """Test the auto-expand logic for progressive disclosure sections."""

    def test_participant_voice_opens_by_default(self):
        from apps.reports.insights_views import _compute_auto_expand
        flags = _compute_auto_expand(
            active_themes=[{"priority": "noted"}],
            metric_distributions={},
            achievement_rates={},
            structured={"suggestion_total": 5},
            data_tier="full",
        )
        self.assertTrue(flags["expand_participant_voice"])

    def test_urgent_theme_opens_participant_voice(self):
        from apps.reports.insights_views import _compute_auto_expand
        flags = _compute_auto_expand(
            active_themes=[{"priority": "urgent"}],
            metric_distributions={},
            achievement_rates={},
            structured={"suggestion_total": 1},
            data_tier="full",
        )
        self.assertTrue(flags["expand_participant_voice"])

    def test_quantitative_data_also_opens_participant_voice(self):
        """If only quantitative sections would open, Participant Voice also opens."""
        from apps.reports.insights_views import _compute_auto_expand
        flags = _compute_auto_expand(
            active_themes=[],
            metric_distributions={"1": {"total": 10}},
            achievement_rates={},
            structured={"suggestion_total": 0, "descriptor_trend": []},
            data_tier="full",
        )
        self.assertTrue(flags["expand_participant_voice"])
        self.assertTrue(flags["expand_distributions"])

    def test_sparse_data_tier_no_expand(self):
        from apps.reports.insights_views import _compute_auto_expand
        flags = _compute_auto_expand(
            active_themes=[],
            metric_distributions={},
            achievement_rates={},
            structured={},
            data_tier="sparse",
        )
        self.assertFalse(flags["expand_participant_voice"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricDefinitionValidationTest(TestCase):
    """Test MetricDefinition model validation."""

    def test_threshold_low_must_be_less_than_high(self):
        metric = MetricDefinition(
            name="Test Metric", category="general",
            threshold_low=5, threshold_high=2,
        )
        with self.assertRaises(ValidationError):
            metric.clean()

    def test_equal_thresholds_rejected(self):
        metric = MetricDefinition(
            name="Test Metric", category="general",
            threshold_low=3, threshold_high=3,
        )
        with self.assertRaises(ValidationError):
            metric.clean()

    def test_valid_thresholds_pass(self):
        metric = MetricDefinition(
            name="Test Metric", category="general",
            threshold_low=2, threshold_high=4,
        )
        metric.clean()  # Should not raise

    def test_null_thresholds_pass(self):
        metric = MetricDefinition(
            name="Test Metric", category="general",
            threshold_low=None, threshold_high=None,
        )
        metric.clean()  # Should not raise

    def test_metric_type_default_is_scale(self):
        metric = MetricDefinition.objects.create(
            name="Default Type", category="general",
        )
        self.assertEqual(metric.metric_type, "scale")
        self.assertTrue(metric.higher_is_better)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricTrendsTest(TestCase):
    """Test monthly band trend calculation."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")
        self.metric = MetricDefinition.objects.create(
            name="Goal Progress", category="general",
            is_universal=True, metric_type="scale",
            min_value=1, max_value=5,
            threshold_low=2, threshold_high=4,
            higher_is_better=True,
        )
        self.date_from = date.today() - timedelta(days=180)
        self.date_to = date.today()

    def _create_participant_with_monthly_scores(self, record_id, monthly_scores):
        """Create a participant with scores in specific months.

        monthly_scores: list of (month_offset_days, score) tuples
        """
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client, name="Section", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)

        for offset_days, score in monthly_scores:
            note = ProgressNote.objects.create(
                client_file=client, note_type="full",
                author=self.user, author_program=self.program,
                backdate=timezone.now() - timedelta(days=offset_days),
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note, plan_target=target,
            )
            MetricValue.objects.create(
                progress_note_target=pnt, metric_def=self.metric,
                value=str(score),
            )
        return client

    def test_monthly_bucketing(self):
        """Trends should produce monthly data points."""
        # Create 12 participants with scores in 2 different months
        for i in range(12):
            self._create_participant_with_monthly_scores(
                f"TREND-{i:03d}",
                [(60, 4), (10, 4)],  # Two months apart, 2 assessments each
            )

        result = get_metric_trends(self.program, self.date_from, self.date_to)
        trend = result.get(self.metric.pk)
        self.assertIsNotNone(trend)
        self.assertGreaterEqual(len(trend), 1)
        # Each point has the expected keys
        for point in trend:
            self.assertIn("month", point)
            self.assertIn("band_low_pct", point)
            self.assertIn("band_high_pct", point)
            self.assertIn("total", point)

    def test_new_participants_excluded_from_trends(self):
        """Participants with only 1 assessment total should be excluded."""
        # 10 participants with 2 assessments (included)
        for i in range(10):
            self._create_participant_with_monthly_scores(
                f"MULTI-{i:03d}", [(60, 4), (10, 4)],
            )
        # 5 participants with only 1 assessment (excluded)
        for i in range(5):
            self._create_participant_with_monthly_scores(
                f"NEW-{i:03d}", [(10, 4)],
            )

        result = get_metric_trends(self.program, self.date_from, self.date_to)
        trend = result.get(self.metric.pk)
        self.assertIsNotNone(trend)
        # Each month's total should not include new participants
        for point in trend:
            self.assertLessEqual(point["total"], 10)

    def test_month_below_n_threshold_excluded(self):
        """Months with fewer than 10 included participants should be excluded."""
        # Only 5 participants — no month should meet the n>=10 threshold
        for i in range(5):
            self._create_participant_with_monthly_scores(
                f"FEW-{i:03d}", [(60, 4), (10, 4)],
            )

        result = get_metric_trends(self.program, self.date_from, self.date_to)
        # Should have no trend data (or metric not in results)
        self.assertNotIn(self.metric.pk, result)


class TrendDirectionTest(TestCase):
    """Test _compute_trend_direction helper."""

    def test_improving_trend(self):
        from apps.reports.insights_views import _compute_trend_direction
        trend_data = [
            {"good_place": 20, "shifting": 10},
            {"good_place": 30, "shifting": 15},
        ]
        result = _compute_trend_direction(trend_data)
        self.assertIn("improving", result.lower() if hasattr(result, 'lower') else str(result))

    def test_declining_trend(self):
        from apps.reports.insights_views import _compute_trend_direction
        trend_data = [
            {"good_place": 40, "shifting": 20},
            {"good_place": 25, "shifting": 10},
        ]
        result = _compute_trend_direction(trend_data)
        self.assertIn("declining", result.lower() if hasattr(result, 'lower') else str(result))

    def test_stable_trend(self):
        from apps.reports.insights_views import _compute_trend_direction
        trend_data = [
            {"good_place": 30, "shifting": 20},
            {"good_place": 31, "shifting": 21},
        ]
        result = _compute_trend_direction(trend_data)
        self.assertIn("stable", result.lower() if hasattr(result, 'lower') else str(result))

    def test_single_data_point_returns_empty(self):
        from apps.reports.insights_views import _compute_trend_direction
        result = _compute_trend_direction([{"good_place": 30, "shifting": 20}])
        self.assertEqual(result, "")

    def test_empty_data_returns_empty(self):
        from apps.reports.insights_views import _compute_trend_direction
        self.assertEqual(_compute_trend_direction([]), "")
        self.assertEqual(_compute_trend_direction(None), "")


class SummaryBuildersTest(TestCase):
    """Test _build_distributions_summary and _build_outcomes_summary."""

    def test_distributions_summary_empty(self):
        from apps.reports.insights_views import _build_distributions_summary
        self.assertEqual(_build_distributions_summary({}), "")
        self.assertEqual(_build_distributions_summary(None), "")

    def test_distributions_summary_with_data(self):
        from apps.reports.insights_views import _build_distributions_summary
        distributions = {
            1: {"total": 20, "band_low_pct": 25.0},
            2: {"total": 10, "band_low_pct": 10.0},
        }
        result = _build_distributions_summary(distributions)
        self.assertIn("30", result)  # total_scored = 20 + 10

    def test_outcomes_summary_empty(self):
        from apps.reports.insights_views import _build_outcomes_summary
        self.assertEqual(_build_outcomes_summary({}), "")
        self.assertEqual(_build_outcomes_summary(None), "")

    def test_outcomes_summary_with_data(self):
        from apps.reports.insights_views import _build_outcomes_summary
        achievements = {
            1: {"achieved_pct": 70.0, "name": "Employment", "target_rate": 80},
        }
        result = _build_outcomes_summary(achievements)
        self.assertIn("70.0%", result)
        self.assertIn("Employment", result)
        self.assertIn("target: 80%", result)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ReEnrolmentDuplicateTest(TestCase):
    """Test that re-enrolled participants are not double-counted."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")
        self.metric = MetricDefinition.objects.create(
            name="Goal Progress", category="general",
            is_universal=True, metric_type="scale",
            min_value=1, max_value=5,
            threshold_low=2, threshold_high=4,
            higher_is_better=True,
        )
        self.date_from = date.today() - timedelta(days=90)
        self.date_to = date.today()

    def test_dual_enrolment_no_value_inflation(self):
        """A participant with two active enrolments should not have inflated values."""
        client = ClientFile.objects.create(record_id="DUAL-ENROL-001")
        # Two active enrolments for the same program (data quality issue)
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program, status="enrolled",
        )

        section = PlanSection.objects.create(
            client_file=client, name="Section", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric)

        # Two notes with scores
        for i in range(2):
            note = ProgressNote.objects.create(
                client_file=client, note_type="full",
                author=self.user, author_program=self.program,
                backdate=timezone.now() - timedelta(days=i + 1),
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note, plan_target=target,
            )
            MetricValue.objects.create(
                progress_note_target=pnt, metric_def=self.metric,
                value="4",
            )

        # Add 9 more normal participants to meet threshold
        for i in range(9):
            c = ClientFile.objects.create(record_id=f"NORMAL-{i:03d}")
            ClientProgramEnrolment.objects.create(
                client_file=c, program=self.program, status="enrolled",
            )
            s = PlanSection.objects.create(
                client_file=c, name="Section", program=self.program,
            )
            t = PlanTarget.objects.create(
                plan_section=s, client_file=c, name="Goal",
            )
            PlanTargetMetric.objects.create(plan_target=t, metric_def=self.metric)
            for j in range(2):
                note = ProgressNote.objects.create(
                    client_file=c, note_type="full",
                    author=self.user, author_program=self.program,
                    backdate=timezone.now() - timedelta(days=j + 1),
                )
                pnt = ProgressNoteTarget.objects.create(
                    progress_note=note, plan_target=t,
                )
                MetricValue.objects.create(
                    progress_note_target=pnt, metric_def=self.metric,
                    value="4",
                )

        result = get_metric_distributions(self.program, self.date_from, self.date_to)
        dist = result.get(self.metric.pk)
        self.assertIsNotNone(dist)
        # The dual-enrolled participant should be counted once, total = 10
        self.assertEqual(dist["total"], 10)
