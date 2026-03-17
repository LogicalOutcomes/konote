"""Tests for FHIR-metadata computation functions (insights_fhir.py)."""
from datetime import timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

import konote.encryption as enc_module
from apps.clients.models import ClientFile, ServiceEpisode
from apps.notes.models import ProgressNote
from apps.plans.models import PlanSection, PlanTarget
from apps.programs.models import Program
from apps.reports.insights_fhir import (
    MIN_GOALS_FOR_SOURCE_DIST,
    MIN_PER_CATEGORY_FOR_CROSSTAB,
    SMALL_PROGRAM_THRESHOLD,
    build_funder_stats,
    build_program_summary,
    get_cohort_comparison,
    get_goal_source_distribution,
    get_goal_source_vs_achievement,
    get_practice_health,
)

User = get_user_model()
TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GoalSourceDistributionTest(TestCase):
    """Tests for get_goal_source_distribution (Feature A)."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")

    def _create_targets(self, source_counts):
        """Create PlanTargets with given goal_source counts.

        Args:
            source_counts: dict of {goal_source: count}
        """
        targets = []
        idx = 0
        for source, count in source_counts.items():
            for i in range(count):
                client = ClientFile.objects.create(record_id=f"CF-{idx}")
                section = PlanSection.objects.create(
                    client_file=client, name="Section", program=self.program,
                )
                target = PlanTarget.objects.create(
                    plan_section=section,
                    client_file=client,
                    name=f"Goal {idx}",
                    goal_source=source,
                    status="default",
                )
                targets.append(target)
                idx += 1
        return targets

    def test_goal_source_distribution_basic(self):
        """3 sources with correct counts and percentages."""
        self._create_targets({
            "joint": 10,
            "worker": 8,
            "participant": 5,
        })
        result = get_goal_source_distribution(self.program)

        self.assertEqual(result["total"], 23)
        self.assertTrue(result["sufficient"])

        sources_by_key = {s["source"]: s for s in result["sources"]}
        self.assertEqual(sources_by_key["joint"]["count"], 10)
        self.assertEqual(sources_by_key["worker"]["count"], 8)
        self.assertEqual(sources_by_key["participant"]["count"], 5)
        # Percentages should add up roughly to 100
        total_pct = sum(
            s["pct"] for s in result["sources"] if not s["suppressed"]
        )
        self.assertGreaterEqual(total_pct, 95)
        self.assertLessEqual(total_pct, 105)

    def test_goal_source_distribution_suppression(self):
        """Category with < 5 entries shows suppressed."""
        self._create_targets({
            "joint": 15,
            "worker": 8,
            "participant": 3,  # Below SMALL_PROGRAM_THRESHOLD
        })
        result = get_goal_source_distribution(self.program)

        sources_by_key = {s["source"]: s for s in result["sources"]}
        self.assertTrue(sources_by_key["participant"]["suppressed"])
        self.assertIsNone(sources_by_key["participant"]["count"])
        self.assertIsNone(sources_by_key["participant"]["pct"])
        # Non-suppressed should be fine
        self.assertFalse(sources_by_key["joint"]["suppressed"])
        self.assertEqual(sources_by_key["joint"]["count"], 15)

    def test_goal_source_distribution_insufficient(self):
        """< 20 goals returns sufficient=False."""
        self._create_targets({"joint": 5, "worker": 5})
        result = get_goal_source_distribution(self.program)

        self.assertFalse(result["sufficient"])
        self.assertEqual(result["total"], 10)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GoalSourceVsAchievementTest(TestCase):
    """Tests for get_goal_source_vs_achievement (Feature B)."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")

    def _create_targets_with_achievement(self, source, count, achieved_count):
        """Create targets with achievement statuses."""
        targets = []
        for i in range(count):
            client = ClientFile.objects.create(
                record_id=f"CF-{source}-{i}",
            )
            section = PlanSection.objects.create(
                client_file=client, name="Section", program=self.program,
            )
            status = "achieved" if i < achieved_count else "in_progress"
            target = PlanTarget.objects.create(
                plan_section=section,
                client_file=client,
                name=f"Goal {source} {i}",
                goal_source=source,
                achievement_status=status,
                status="default",
            )
            targets.append(target)
        return targets

    def test_crosstab_comparison_sentence(self):
        """Joint rate > worker rate by 10+ generates correct sentence."""
        # Joint: 15 total, 12 achieved = 80%
        self._create_targets_with_achievement("joint", 15, 12)
        # Worker: 12 total, 5 achieved = ~42%
        self._create_targets_with_achievement("worker", 12, 5)

        result = get_goal_source_vs_achievement(self.program)

        self.assertTrue(result["sufficient"])
        self.assertIn("percentage-point higher rate", result["comparison_sentence"])

    def test_crosstab_insufficient(self):
        """< 2 qualifying categories returns sufficient=False."""
        # Only one source with enough data
        self._create_targets_with_achievement("joint", 12, 8)
        # Worker has < MIN_PER_CATEGORY (< 10 total)
        self._create_targets_with_achievement("worker", 8, 4)

        result = get_goal_source_vs_achievement(self.program)

        self.assertFalse(result["sufficient"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PracticeHealthTest(TestCase):
    """Tests for get_practice_health (Feature C)."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")

    def _create_program_data(self, participant_count=10, notes_per=3):
        """Create a fully populated program for practice health testing."""
        clients = []
        for i in range(participant_count):
            client = ClientFile.objects.create(record_id=f"CF-{i}")
            ServiceEpisode.objects.create(
                client_file=client,
                program=self.program,
                status="active",
                episode_type="new_intake",
            )
            section = PlanSection.objects.create(
                client_file=client, name="Section", program=self.program,
            )
            PlanTarget.objects.create(
                plan_section=section,
                client_file=client,
                name=f"Goal {i}",
                goal_source="joint",
                status="default",
            )
            for j in range(notes_per):
                ProgressNote.objects.create(
                    client_file=client,
                    note_type="full",
                    author=self.user,
                    author_program=self.program,
                )
            clients.append(client)
        return clients

    @patch("apps.reports.insights_fhir.get_data_completeness")
    def test_practice_health_indicators(self, mock_completeness):
        """All 4 indicators computed when data is sufficient."""
        mock_completeness.return_value = {
            "enrolled_count": 10,
            "with_scores_count": 8,
            "completeness_pct": 80,
            "completeness_level": "full",
        }
        self._create_program_data(participant_count=10, notes_per=2)

        result = get_practice_health(self.program)

        # Jointly developed indicator
        self.assertTrue(result["jointly_developed"]["show"])
        self.assertEqual(result["jointly_developed"]["level"], "good")

        # Data completeness indicator
        self.assertTrue(result["data_completeness"]["show"])

        # Participant voice — notes created without encrypted data
        # so voice will be 0% but indicator should show if >=10 notes
        self.assertTrue(result["participant_voice"]["show"])

        # Sessions per participant
        self.assertTrue(result["sessions_per_participant"]["show"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CohortComparisonTest(TestCase):
    """Tests for get_cohort_comparison (Feature E)."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")

    def _create_cohort(self, episode_type, count, achieved_pct=50):
        """Create a cohort of participants with episodes, goals, notes."""
        for i in range(count):
            client = ClientFile.objects.create(
                record_id=f"CF-{episode_type}-{i}",
            )
            ServiceEpisode.objects.create(
                client_file=client,
                program=self.program,
                status="active",
                episode_type=episode_type,
            )
            section = PlanSection.objects.create(
                client_file=client, name="Section", program=self.program,
            )
            # Create 2 goals per participant
            for g in range(2):
                ach_status = (
                    "achieved"
                    if (i * 2 + g) < (count * 2 * achieved_pct // 100)
                    else "in_progress"
                )
                PlanTarget.objects.create(
                    plan_section=section,
                    client_file=client,
                    name=f"Goal {i}-{g}",
                    goal_source="joint",
                    achievement_status=ach_status,
                    status="default",
                )
            ProgressNote.objects.create(
                client_file=client,
                note_type="full",
                author=self.user,
                author_program=self.program,
            )

    def test_cohort_comparison_basic(self):
        """New vs returning with different achievement rates."""
        self._create_cohort("new_intake", 12, achieved_pct=70)
        self._create_cohort("re_enrolment", 12, achieved_pct=40)

        result = get_cohort_comparison(self.program)

        self.assertTrue(result["sufficient"])
        self.assertEqual(len(result["cohorts"]), 2)

        new_cohort = next(
            c for c in result["cohorts"] if c["type"] == "new_intake"
        )
        re_cohort = next(
            c for c in result["cohorts"] if c["type"] == "re_enrolment"
        )
        self.assertEqual(new_cohort["participants"], 12)
        self.assertEqual(re_cohort["participants"], 12)
        self.assertTrue(new_cohort["sufficient"])
        self.assertTrue(re_cohort["sufficient"])

    def test_cohort_comparison_insufficient_returning(self):
        """< 10 re-enrolments returns sufficient=False."""
        self._create_cohort("new_intake", 12)
        self._create_cohort("re_enrolment", 5)  # Below threshold

        result = get_cohort_comparison(self.program)

        self.assertFalse(result["sufficient"])
        re_cohort = next(
            c for c in result["cohorts"] if c["type"] == "re_enrolment"
        )
        self.assertFalse(re_cohort["sufficient"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramSummaryTest(TestCase):
    """Tests for build_program_summary (Feature D)."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Youth Empowerment", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")

    def _create_full_program(self, active_count=10):
        """Create a program with enough data for the full summary template."""
        for i in range(active_count):
            client = ClientFile.objects.create(record_id=f"CF-{i}")
            ep_type = "new_intake" if i < active_count // 2 else "re_enrolment"
            ServiceEpisode.objects.create(
                client_file=client,
                program=self.program,
                status="active",
                episode_type=ep_type,
            )
            section = PlanSection.objects.create(
                client_file=client, name="Section", program=self.program,
            )
            PlanTarget.objects.create(
                plan_section=section,
                client_file=client,
                name=f"Goal {i}",
                goal_source="joint" if i % 2 == 0 else "worker",
                achievement_status="achieved" if i < 8 else "in_progress",
                status="default",
            )
            ProgressNote.objects.create(
                client_file=client,
                note_type="full",
                author=self.user,
                author_program=self.program,
            )

    def test_program_summary_sufficient_data(self):
        """Full template rendered when achievement data is available."""
        self._create_full_program(active_count=12)
        enrolment_stats = {"active": 12, "total": 12}

        result = build_program_summary(self.program, enrolment_stats)

        self.assertIn("Youth Empowerment", result)
        self.assertIn("12 participants", result)
        self.assertIn("improvement or achievement", result)

    def test_program_summary_small_program(self):
        """< 5 active participants shows privacy message."""
        enrolment_stats = {"active": 3, "total": 3}

        result = build_program_summary(self.program, enrolment_stats)

        self.assertIn("3 active participants", result)
        self.assertIn("protect privacy", result)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FunderStatsTest(TestCase):
    """Tests for build_funder_stats (Feature F)."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")

    def _create_funder_data(self, participant_count=15, goals_per=2):
        """Create data for funder stat tests."""
        for i in range(participant_count):
            client = ClientFile.objects.create(record_id=f"CF-{i}")
            ep_type = "new_intake" if i < 10 else "re_enrolment"
            ServiceEpisode.objects.create(
                client_file=client,
                program=self.program,
                status="active",
                episode_type=ep_type,
            )
            section = PlanSection.objects.create(
                client_file=client, name="Section", program=self.program,
            )
            for g in range(goals_per):
                ach = "achieved" if (i * goals_per + g) < 12 else "in_progress"
                PlanTarget.objects.create(
                    plan_section=section,
                    client_file=client,
                    name=f"Goal {i}-{g}",
                    goal_source="joint" if g == 0 else "worker",
                    achievement_status=ach,
                    status="default",
                )
            ProgressNote.objects.create(
                client_file=client,
                note_type="full",
                author=self.user,
                author_program=self.program,
            )

    def test_funder_stats_confidence_levels(self):
        """Stats include reliable, partial, and insufficient confidence."""
        self._create_funder_data(participant_count=15, goals_per=2)

        result = build_funder_stats(self.program)

        # Should have 5 stat cards
        self.assertEqual(len(result), 5)

        labels = [s["label"] for s in result]
        self.assertIn("Served", labels)
        self.assertIn("Sessions", labels)
        self.assertIn("Goals", labels)
        self.assertIn("Improving", labels)
        self.assertIn("Completed", labels)

        # Served and Sessions are always reliable
        served = next(s for s in result if s["label"] == "Served")
        self.assertEqual(served["confidence"], "reliable")

        sessions = next(s for s in result if s["label"] == "Sessions")
        self.assertEqual(sessions["confidence"], "reliable")

        # Completed should be insufficient (no finished episodes)
        completed = next(s for s in result if s["label"] == "Completed")
        self.assertEqual(completed["confidence"], "insufficient")
