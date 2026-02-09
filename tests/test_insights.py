"""Tests for Outcome Insights — data collection, views, and AI validation."""
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

import konote.encryption as enc_module
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import ProgressNote, ProgressNoteTarget
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
from apps.programs.models import Program
from apps.reports.insights import (
    MIN_PARTICIPANTS_FOR_QUOTES,
    collect_quotes,
    get_structured_insights,
)
from konote.ai import validate_insights_response

User = get_user_model()

# Use the same test encryption key as other tests
TEST_KEY = "dGVzdGtleWZvcmVuY3J5cHRpb24xMjM0NTY3ODk="


class ValidateInsightsResponseTest(SimpleTestCase):
    """Test AI response validation logic."""

    def _sample_quotes(self):
        return [
            {"text": "I finally feel like I have a plan for my future", "note_id": 1, "target_name": "Employment"},
            {"text": "The housing support has made a real difference in my life", "note_id": 2, "target_name": "Housing"},
            {"text": "I am more confident about looking for work now", "note_id": 3, "target_name": "Employment"},
        ]

    def test_valid_response_passes(self):
        response = {
            "summary": "During this period, participants showed positive progress across multiple areas.",
            "themes": ["employment readiness", "housing stability"],
            "cited_quotes": [
                {"text": "I finally feel like I have a plan for my future", "note_id": 1, "context": "employment goal"},
            ],
            "recommendations": "Staff may want to focus on employment support.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNotNone(result)
        self.assertEqual(len(result["cited_quotes"]), 1)

    def test_missing_key_returns_none(self):
        response = {
            "summary": "Some text here.",
            "themes": [],
            # Missing cited_quotes and recommendations
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNone(result)

    def test_short_summary_returns_none(self):
        response = {
            "summary": "Too short.",
            "themes": [],
            "cited_quotes": [],
            "recommendations": "Something.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNone(result)

    def test_non_verbatim_quotes_are_removed(self):
        response = {
            "summary": "Participants showed improvement across the board during this period.",
            "themes": ["progress"],
            "cited_quotes": [
                # This is verbatim from the original
                {"text": "I finally feel like I have a plan for my future", "note_id": 1, "context": "employment"},
                # This is NOT in the original quotes — AI fabricated it
                {"text": "Everything is going great and I love my life now", "note_id": 99, "context": "general"},
            ],
            "recommendations": "Continue current approach.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNotNone(result)
        # The fabricated quote should be removed
        self.assertEqual(len(result["cited_quotes"]), 1)
        self.assertEqual(result["cited_quotes"][0]["note_id"], 1)

    def test_partial_quote_match_passes(self):
        """A substring of an original quote should pass verbatim check."""
        response = {
            "summary": "Participants expressed growing confidence in their ability to plan ahead.",
            "themes": ["confidence"],
            "cited_quotes": [
                # This is a substring of "I finally feel like I have a plan for my future"
                {"text": "I have a plan for my future", "note_id": 1, "context": "employment"},
            ],
            "recommendations": "Keep it up.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNotNone(result)
        self.assertEqual(len(result["cited_quotes"]), 1)

    def test_not_a_dict_returns_none(self):
        result = validate_insights_response("just a string", self._sample_quotes())
        self.assertIsNone(result)

    def test_themes_not_list_gets_fixed(self):
        response = {
            "summary": "Participants showed improvement across the board during this period.",
            "themes": "employment",  # String instead of list
            "cited_quotes": [],
            "recommendations": "Continue.",
        }
        result = validate_insights_response(response, self._sample_quotes())
        self.assertIsNotNone(result)
        self.assertEqual(result["themes"], [])


class DataTierTest(SimpleTestCase):
    """Test data volume threshold logic."""

    def test_sparse(self):
        from apps.reports.insights_views import _get_data_tier
        self.assertEqual(_get_data_tier(5, 1), "sparse")
        self.assertEqual(_get_data_tier(19, 2), "sparse")

    def test_limited(self):
        from apps.reports.insights_views import _get_data_tier
        self.assertEqual(_get_data_tier(25, 3), "limited")
        self.assertEqual(_get_data_tier(49, 4), "limited")
        self.assertEqual(_get_data_tier(60, 2), "limited")  # <3 months

    def test_full(self):
        from apps.reports.insights_views import _get_data_tier
        self.assertEqual(_get_data_tier(50, 3), "full")
        self.assertEqual(_get_data_tier(500, 12), "full")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EffectiveDateInsightsTest(TestCase):
    """Test that insights use backdate (effective date) instead of created_at."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")
        self.client_file = ClientFile.objects.create(record_id="TEST-INSIGHT-001")
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="enrolled",
        )
        self.section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Test Section",
            program=self.program,
        )
        self.target = PlanTarget.objects.create(
            plan_section=self.section,
            client_file=self.client_file,
            name="Test Target",
        )

    def _create_backdated_note(self, days_ago, descriptor="shifting"):
        """Create a note with backdate set to days_ago."""
        backdate = timezone.now() - timedelta(days=days_ago)
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="full",
            author=self.user,
            author_program=self.program,
            backdate=backdate,
            engagement_observation="engaged",
        )
        ProgressNoteTarget.objects.create(
            progress_note=note,
            plan_target=self.target,
            progress_descriptor=descriptor,
            client_words="This is a long enough quote for the test to pass the word filter easily",
        )
        return note

    def test_backdated_notes_appear_in_correct_date_range(self):
        """Notes with backdate should be found when filtering by the backdate range."""
        # Create notes backdated to 90 days ago
        for _ in range(5):
            self._create_backdated_note(days_ago=90)

        # Query for the date range around 90 days ago
        date_from = (date.today() - timedelta(days=120))
        date_to = (date.today() - timedelta(days=60))

        result = get_structured_insights(
            program=self.program,
            date_from=date_from,
            date_to=date_to,
        )
        self.assertEqual(result["note_count"], 5)

    def test_backdated_notes_excluded_from_wrong_date_range(self):
        """Notes backdated to 90 days ago should NOT appear in last-30-days range."""
        for _ in range(5):
            self._create_backdated_note(days_ago=90)

        date_from = (date.today() - timedelta(days=30))
        date_to = date.today()

        result = get_structured_insights(
            program=self.program,
            date_from=date_from,
            date_to=date_to,
        )
        self.assertEqual(result["note_count"], 0)

    def test_descriptor_trend_uses_backdate_month(self):
        """Descriptor trend should group by backdate month, not created_at."""
        # Create notes backdated to 3 different months
        for _ in range(3):
            self._create_backdated_note(days_ago=30, descriptor="good_place")
        for _ in range(3):
            self._create_backdated_note(days_ago=60, descriptor="shifting")
        for _ in range(3):
            self._create_backdated_note(days_ago=90, descriptor="harder")

        date_from = (date.today() - timedelta(days=120))
        date_to = date.today()

        result = get_structured_insights(
            program=self.program,
            date_from=date_from,
            date_to=date_to,
        )
        # Should have data spread across months, not all in one month
        self.assertGreaterEqual(len(result["descriptor_trend"]), 2)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=True)
class DemoModeQuotesTest(TestCase):
    """Test that DEMO_MODE bypasses the privacy gate for quotes."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Demo Program", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")

        # Create fewer than MIN_PARTICIPANTS_FOR_QUOTES participants
        self.clients = []
        for i in range(3):
            client = ClientFile.objects.create(record_id=f"DEMO-QUOTE-{i:03d}")
            ClientProgramEnrolment.objects.create(
                client_file=client,
                program=self.program,
                status="enrolled",
            )
            self.clients.append(client)

        # Create plan structure for first client
        section = PlanSection.objects.create(
            client_file=self.clients[0],
            name="Test Section",
            program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section,
            client_file=self.clients[0],
            name="Test Target",
        )

        # Create a note with a long-enough client_words quote
        note = ProgressNote.objects.create(
            client_file=self.clients[0],
            note_type="full",
            author=self.user,
            author_program=self.program,
            engagement_observation="engaged",
        )
        ProgressNoteTarget.objects.create(
            progress_note=note,
            plan_target=target,
            progress_descriptor="shifting",
            client_words="I think the biggest thing I'm learning is that it's okay to ask for help when I need it",
        )

    def test_quotes_returned_in_demo_mode_despite_low_participant_count(self):
        """In DEMO_MODE, quotes should be returned even with < 15 participants."""
        self.assertLess(len(self.clients), MIN_PARTICIPANTS_FOR_QUOTES)
        quotes = collect_quotes(program=self.program)
        self.assertGreater(len(quotes), 0)

    @override_settings(DEMO_MODE=False)
    def test_quotes_blocked_without_demo_mode(self):
        """Without DEMO_MODE, quotes should be blocked with < 15 participants."""
        self.assertLess(len(self.clients), MIN_PARTICIPANTS_FOR_QUOTES)
        quotes = collect_quotes(program=self.program)
        self.assertEqual(len(quotes), 0)


class ClientWordsSamplesTest(SimpleTestCase):
    """Verify demo data CLIENT_WORDS_SAMPLES meet the minimum word count."""

    def test_all_samples_have_at_least_10_words(self):
        from apps.admin_settings.management.commands.seed_demo_data import CLIENT_WORDS_SAMPLES
        for sample in CLIENT_WORDS_SAMPLES:
            word_count = len(sample.split())
            self.assertGreaterEqual(
                word_count, 10,
                f"Sample too short ({word_count} words): '{sample}'",
            )
