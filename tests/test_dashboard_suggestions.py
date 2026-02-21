"""Tests for suggestion counts and theme display on the executive dashboard."""
from cryptography.fernet import Fernet

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

import konote.encryption as enc_module
from apps.clients.dashboard_views import _batch_suggestion_counts, _batch_top_themes
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import ProgressNote, SuggestionLink, SuggestionTheme
from apps.programs.models import Program, UserProgramRole

User = get_user_model()

TEST_KEY = Fernet.generate_key().decode()


class BatchSuggestionCountsUnitTest(SimpleTestCase):
    """Test edge cases without hitting the database."""

    def test_empty_program_list(self):
        result = _batch_suggestion_counts([])
        self.assertEqual(result, {})


class BatchTopThemesUnitTest(SimpleTestCase):
    """Test edge cases without hitting the database."""

    def test_empty_program_list(self):
        counts, themes = _batch_top_themes([])
        self.assertEqual(counts, {})
        self.assertEqual(themes, {})


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
class BatchTopThemesTest(TestCase):
    """Test _batch_top_themes with real database data."""

    def setUp(self):
        enc_module._fernet = None

        self.program = Program.objects.create(name="Housing", status="active")
        self.user = User.objects.create_user(username="worker", password="testpass123")

    def _create_theme(self, name, priority="noted", status="open"):
        return SuggestionTheme.objects.create(
            program=self.program,
            name=name,
            priority=priority,
            status=status,
            created_by=self.user,
        )

    def test_returns_up_to_3_themes_per_program(self):
        for i in range(5):
            self._create_theme(f"Theme {i}")

        counts, themes = _batch_top_themes([self.program.pk])
        self.assertEqual(len(themes[self.program.pk]), 3)
        self.assertEqual(counts[self.program.pk]["total"], 5)

    def test_urgent_themes_first(self):
        self._create_theme("Low priority", priority="noted")
        self._create_theme("Critical", priority="urgent")
        self._create_theme("Medium", priority="important")

        _, themes = _batch_top_themes([self.program.pk])
        names = [t["name"] for t in themes[self.program.pk]]
        self.assertEqual(names[0], "Critical")
        self.assertEqual(names[1], "Medium")
        self.assertEqual(names[2], "Low priority")

    def test_addressed_themes_excluded(self):
        self._create_theme("Active theme", status="open")
        self._create_theme("Done theme", status="addressed")
        self._create_theme("Skipped theme", status="wont_do")

        counts, themes = _batch_top_themes([self.program.pk])
        self.assertEqual(counts[self.program.pk]["total"], 1)
        self.assertEqual(len(themes[self.program.pk]), 1)
        self.assertEqual(themes[self.program.pk][0]["name"], "Active theme")

    def test_counts_include_open_and_in_progress(self):
        self._create_theme("Open one", status="open")
        self._create_theme("Open two", status="open")
        self._create_theme("Working on it", status="in_progress")

        counts, _ = _batch_top_themes([self.program.pk])
        c = counts[self.program.pk]
        self.assertEqual(c["total"], 3)
        self.assertEqual(c["open"], 2)
        self.assertEqual(c["in_progress"], 1)

    def test_exactly_3_themes_no_overflow(self):
        """Boundary: exactly 3 themes should return all 3, no extras."""
        for i in range(3):
            self._create_theme(f"Theme {i}")

        counts, themes = _batch_top_themes([self.program.pk])
        self.assertEqual(len(themes[self.program.pk]), 3)
        self.assertEqual(counts[self.program.pk]["total"], 3)

    def test_no_themes_returns_empty(self):
        counts, themes = _batch_top_themes([self.program.pk])
        self.assertEqual(counts, {})
        self.assertEqual(themes, {})

    def test_duplicate_names_are_merged(self):
        """deduplicate_themes merges same-name themes, summing link counts."""
        from apps.notes.models import deduplicate_themes
        from django.utils import timezone

        now = timezone.now()
        theme_dicts = [
            {
                "pk": 1, "name": "Recipe variety", "status": "open",
                "priority": "important", "program_id": self.program.pk,
                "updated_at": now, "link_count": 1,
            },
            {
                "pk": 2, "name": "Recipe variety", "status": "open",
                "priority": "noted", "program_id": self.program.pk,
                "updated_at": now, "link_count": 1,
            },
        ]
        result = deduplicate_themes(theme_dicts)

        # Should be merged into one
        self.assertEqual(len(result), 1)
        merged = result[0]
        self.assertEqual(merged["name"], "Recipe variety")
        self.assertEqual(merged["link_count"], 2)
        self.assertEqual(merged["priority"], "important")

    def test_duplicate_names_case_insensitive(self):
        """deduplicate_themes merges themes with different casing."""
        from apps.notes.models import deduplicate_themes
        from django.utils import timezone

        now = timezone.now()
        theme_dicts = [
            {
                "pk": 1, "name": "Take-home portions", "status": "open",
                "priority": "noted", "program_id": self.program.pk,
                "updated_at": now, "link_count": 0,
            },
            {
                "pk": 2, "name": "take-home portions", "status": "open",
                "priority": "important", "program_id": self.program.pk,
                "updated_at": now, "link_count": 0,
            },
        ]
        result = deduplicate_themes(theme_dicts)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["priority"], "important")


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

    def test_dashboard_shows_theme_names(self):
        SuggestionTheme.objects.create(
            program=self.program,
            name="Longer evening hours",
            priority="important",
            status="open",
            created_by=self.user,
        )
        self.client.login(username="exec", password="testpass123")
        response = self.client.get("/participants/executive/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Longer evening hours")
        self.assertContains(response, "Suggestion Themes")

    def test_dashboard_shows_urgent_badge(self):
        SuggestionTheme.objects.create(
            program=self.program,
            name="Safety concern",
            priority="urgent",
            status="open",
            created_by=self.user,
        )
        self.client.login(username="exec", password="testpass123")
        response = self.client.get("/participants/executive/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Safety concern")
        self.assertContains(response, "Urgent")

    def test_dashboard_shows_more_count(self):
        for i in range(5):
            SuggestionTheme.objects.create(
                program=self.program,
                name=f"Theme number {i}",
                priority="noted",
                status="open",
                created_by=self.user,
            )
        self.client.login(username="exec", password="testpass123")
        response = self.client.get("/participants/executive/")
        self.assertEqual(response.status_code, 200)
        # 5 themes, showing 3, so "+2 more" should appear
        self.assertContains(response, "+2")
        self.assertContains(response, "more")

    def test_dashboard_falls_back_to_count_without_themes(self):
        """When no themes exist but suggestions do, show count fallback."""
        ProgressNote.objects.create(
            client_file=self.client_file,
            author=self.user,
            author_program=self.program,
            note_type="progress",
            suggestion_priority="noted",
        )
        self.client.login(username="exec", password="testpass123")
        response = self.client.get("/participants/executive/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suggestions")
        self.assertNotContains(response, "Suggestion Themes")
