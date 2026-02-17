"""Tests for suggestion counts on the executive dashboard."""
from cryptography.fernet import Fernet

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

import konote.encryption as enc_module
from apps.clients.dashboard_views import _batch_suggestion_counts
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import ProgressNote
from apps.programs.models import Program, UserProgramRole

User = get_user_model()

TEST_KEY = Fernet.generate_key().decode()


class BatchSuggestionCountsUnitTest(SimpleTestCase):
    """Test edge cases without hitting the database."""

    def test_empty_program_list(self):
        result = _batch_suggestion_counts([])
        self.assertEqual(result, {})


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BatchSuggestionCountsTest(TestCase):
    """Test _batch_suggestion_counts with real database data."""

    def setUp(self):
        enc_module._fernet = None

        self.program1 = Program.objects.create(name="Housing", status="active")
        self.program2 = Program.objects.create(name="Employment", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")

        self.client1 = ClientFile.objects.create(record_id="SUGG-001")
        ClientProgramEnrolment.objects.create(
            client_file=self.client1, program=self.program1, status="enrolled",
        )
        self.client2 = ClientFile.objects.create(record_id="SUGG-002")
        ClientProgramEnrolment.objects.create(
            client_file=self.client2, program=self.program2, status="enrolled",
        )

    def _create_note(self, client, program, priority):
        return ProgressNote.objects.create(
            client_file=client,
            author=self.user,
            author_program=program,
            note_type="progress",
            suggestion_priority=priority,
        )

    def test_counts_by_priority(self):
        self._create_note(self.client1, self.program1, "noted")
        self._create_note(self.client1, self.program1, "important")
        self._create_note(self.client1, self.program1, "important")
        self._create_note(self.client1, self.program1, "urgent")

        result = _batch_suggestion_counts([self.program1.pk])
        p1 = result[self.program1.pk]
        self.assertEqual(p1["total"], 4)
        self.assertEqual(p1["important"], 2)
        self.assertEqual(p1["urgent"], 1)

    def test_multiple_programs(self):
        self._create_note(self.client1, self.program1, "important")
        self._create_note(self.client2, self.program2, "noted")
        self._create_note(self.client2, self.program2, "urgent")

        result = _batch_suggestion_counts([self.program1.pk, self.program2.pk])
        self.assertEqual(result[self.program1.pk]["total"], 1)
        self.assertEqual(result[self.program2.pk]["total"], 2)
        self.assertEqual(result[self.program2.pk]["urgent"], 1)

    def test_no_suggestions_returns_empty(self):
        # Create a note without suggestion_priority
        ProgressNote.objects.create(
            client_file=self.client1,
            author=self.user,
            author_program=self.program1,
            note_type="progress",
        )
        result = _batch_suggestion_counts([self.program1.pk])
        self.assertEqual(result, {})

    def test_deleted_notes_excluded(self):
        note = self._create_note(self.client1, self.program1, "important")
        note.status = "deleted"
        note.save()

        result = _batch_suggestion_counts([self.program1.pk])
        self.assertEqual(result, {})


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExecutiveDashboardSuggestionViewTest(TestCase):
    """Integration test: verify suggestion card renders on dashboard."""

    def setUp(self):
        enc_module._fernet = None

        self.program = Program.objects.create(name="Housing", status="active")
        self.user = User.objects.create_user(username="exec", password="testpass123")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="executive", status="active",
        )

        self.client_file = ClientFile.objects.create(record_id="EXEC-001")
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled",
        )

    def test_dashboard_shows_suggestion_card_when_important(self):
        ProgressNote.objects.create(
            client_file=self.client_file,
            author=self.user,
            author_program=self.program,
            note_type="progress",
            suggestion_priority="important",
        )
        self.client.login(username="exec", password="testpass123")
        response = self.client.get("/participants/executive/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Important Suggestions")

    def test_dashboard_no_card_when_no_suggestions(self):
        self.client.login(username="exec", password="testpass123")
        response = self.client.get("/participants/executive/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Important Suggestions")

    def test_per_program_suggestion_count_shown(self):
        ProgressNote.objects.create(
            client_file=self.client_file,
            author=self.user,
            author_program=self.program,
            note_type="progress",
            suggestion_priority="noted",
        )
        ProgressNote.objects.create(
            client_file=self.client_file,
            author=self.user,
            author_program=self.program,
            note_type="progress",
            suggestion_priority="important",
        )
        self.client.login(username="exec", password="testpass123")
        response = self.client.get("/participants/executive/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suggestions")
        self.assertContains(response, "Outcome Insights")
