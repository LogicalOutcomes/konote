"""Tests for the automated theme engine (Tier 1 auto-link + Tier 2 AI processing)."""
from cryptography.fernet import Fernet

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

import konote.encryption as enc_module
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import (
    ProgressNote, SuggestionLink, SuggestionTheme, recalculate_theme_priority,
)
from apps.notes.theme_engine import (
    _extract_content_words,
    _find_note_id,
    process_ai_themes,
    try_auto_link_suggestion,
)
from apps.programs.models import Program, UserProgramRole

User = get_user_model()

TEST_KEY = Fernet.generate_key().decode()


def _create_participants(program, count):
    """Create enrolled participants to pass the privacy gate."""
    for i in range(count):
        cf = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
        )
        ClientProgramEnrolment.objects.create(
            client_file=cf, program=program, status="enrolled",
        )


# ── Tier 1: Auto-Link Tests ────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=True)
class Tier1AutoLinkTests(TestCase):
    """Test try_auto_link_suggestion() keyword matching."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        self.user = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(
            user=self.user, program=self.program,
            role="staff", status="active",
        )

        # Create a theme with keywords
        self.theme = SuggestionTheme.objects.create(
            program=self.program,
            name="Evening availability",
            description="Participants want evening sessions",
            keywords="evening, sessions, hours, schedule",
            source="ai_generated",
        )

    def _make_note(self, suggestion, priority="noted"):
        return ProgressNote.objects.create(
            client_file=ClientFile.objects.create(
                _first_name_encrypted=b"", _last_name_encrypted=b"",
            ),
            note_type="full",
            author=self.user,
            author_program=self.program,
            participant_suggestion=suggestion,
            suggestion_priority=priority,
        )

    def test_auto_link_matches_by_keywords(self):
        note = self._make_note("I wish there were evening sessions available")
        linked = try_auto_link_suggestion(note)
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0].pk, self.theme.pk)
        self.assertTrue(
            SuggestionLink.objects.filter(theme=self.theme, progress_note=note).exists()
        )

    def test_auto_link_requires_2_word_overlap(self):
        note = self._make_note("The evening was nice")
        linked = try_auto_link_suggestion(note)
        # "evening" overlaps but only 1 content word — should NOT link
        self.assertEqual(len(linked), 0)

    def test_auto_link_skips_addressed_themes(self):
        self.theme.status = "addressed"
        self.theme.save()
        note = self._make_note("More evening sessions please")
        linked = try_auto_link_suggestion(note)
        self.assertEqual(len(linked), 0)

    def test_auto_link_no_duplicates(self):
        note = self._make_note("Evening sessions would be great for my schedule")
        try_auto_link_suggestion(note)
        try_auto_link_suggestion(note)
        self.assertEqual(
            SuggestionLink.objects.filter(theme=self.theme, progress_note=note).count(),
            1,
        )

    def test_auto_link_recalculates_priority(self):
        self.assertEqual(self.theme.priority, "noted")
        note = self._make_note("Evening sessions urgently needed", priority="urgent")
        try_auto_link_suggestion(note)
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.priority, "urgent")

    def test_auto_link_skips_empty_suggestion(self):
        note = self._make_note("", priority="")
        linked = try_auto_link_suggestion(note)
        self.assertEqual(len(linked), 0)

    def test_auto_link_skips_no_program(self):
        note = ProgressNote.objects.create(
            client_file=ClientFile.objects.create(
                _first_name_encrypted=b"", _last_name_encrypted=b"",
            ),
            note_type="full",
            author=self.user,
            author_program=None,
            participant_suggestion="Evening sessions",
            suggestion_priority="noted",
        )
        linked = try_auto_link_suggestion(note)
        self.assertEqual(len(linked), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=False)
class Tier1PrivacyGateTests(TestCase):
    """Test that the 15-participant privacy gate works for auto-linking."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Small Program")
        self.user = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(
            user=self.user, program=self.program,
            role="staff", status="active",
        )
        self.theme = SuggestionTheme.objects.create(
            program=self.program,
            name="Evening availability",
            keywords="evening, sessions, hours",
            source="ai_generated",
        )

    def test_privacy_gate_blocks_small_programs(self):
        # Only 5 participants — below threshold
        _create_participants(self.program, 5)
        note = ProgressNote.objects.create(
            client_file=ClientFile.objects.create(
                _first_name_encrypted=b"", _last_name_encrypted=b"",
            ),
            note_type="full",
            author=self.user,
            author_program=self.program,
            participant_suggestion="Evening sessions would help",
            suggestion_priority="noted",
        )
        linked = try_auto_link_suggestion(note)
        self.assertEqual(len(linked), 0)

    def test_privacy_gate_allows_large_programs(self):
        _create_participants(self.program, 16)
        note = ProgressNote.objects.create(
            client_file=ClientFile.objects.create(
                _first_name_encrypted=b"", _last_name_encrypted=b"",
            ),
            note_type="full",
            author=self.user,
            author_program=self.program,
            participant_suggestion="Evening sessions would help with schedule",
            suggestion_priority="noted",
        )
        linked = try_auto_link_suggestion(note)
        self.assertEqual(len(linked), 1)


# ── Tier 2: AI Theme Processing Tests ──────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=True)
class Tier2ProcessAiThemesTests(TestCase):
    """Test process_ai_themes() creates/updates themes from AI response."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        self.user = User.objects.create_user(username="staff", password="pass")

        # Create notes with suggestions
        self.cf = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
        )
        self.note1 = ProgressNote.objects.create(
            client_file=self.cf, note_type="full", author=self.user,
            author_program=self.program,
            participant_suggestion="We need evening sessions",
            suggestion_priority="important",
        )
        self.note2 = ProgressNote.objects.create(
            client_file=self.cf, note_type="full", author=self.user,
            author_program=self.program,
            participant_suggestion="Transportation is a real barrier",
            suggestion_priority="urgent",
        )

        # Ephemeral quote source map (simulates what outcome_insights_view builds)
        self.quote_source_map = {
            "We need evening sessions": self.note1.pk,
            "Transportation is a real barrier": self.note2.pk,
        }

    def test_creates_new_theme(self):
        ai_themes = [{
            "name": "Evening availability",
            "description": "Participants want evening sessions",
            "category": "program_design",
            "keywords": ["evening", "sessions", "schedule"],
            "supporting_quotes": ["We need evening sessions"],
        }]
        process_ai_themes(ai_themes, self.quote_source_map, self.program)

        theme = SuggestionTheme.objects.get(name="Evening availability")
        self.assertEqual(theme.source, "ai_generated")
        self.assertIsNone(theme.created_by)
        self.assertEqual(theme.program, self.program)

    def test_reuses_existing_theme_case_insensitive(self):
        existing = SuggestionTheme.objects.create(
            program=self.program, name="Evening availability",
            source="ai_generated",
        )
        ai_themes = [{
            "name": "evening availability",
            "description": "Same theme, different case",
            "category": "program_design",
            "keywords": ["evening"],
            "supporting_quotes": ["We need evening sessions"],
        }]
        process_ai_themes(ai_themes, self.quote_source_map, self.program)

        # Should NOT create a second theme
        self.assertEqual(
            SuggestionTheme.objects.filter(program=self.program, name__iexact="evening availability").count(),
            1,
        )
        # Should link the note to the existing theme
        self.assertTrue(
            SuggestionLink.objects.filter(theme=existing, progress_note=self.note1).exists()
        )

    def test_links_quotes_via_source_map(self):
        ai_themes = [{
            "name": "Transport barriers",
            "description": "Getting to the program is hard",
            "category": "program_design",
            "keywords": ["transportation", "barrier", "access"],
            "supporting_quotes": ["Transportation is a real barrier"],
        }]
        process_ai_themes(ai_themes, self.quote_source_map, self.program)

        theme = SuggestionTheme.objects.get(name="Transport barriers")
        link = SuggestionLink.objects.get(theme=theme)
        self.assertEqual(link.progress_note_id, self.note2.pk)
        self.assertTrue(link.auto_linked)
        self.assertIsNone(link.linked_by)

    def test_skips_operational_themes(self):
        ai_themes = [{
            "name": "Broken coffee machine",
            "description": "Coffee machine needs repair",
            "category": "operational",
            "keywords": ["coffee", "machine"],
            "supporting_quotes": [],
        }]
        process_ai_themes(ai_themes, self.quote_source_map, self.program)
        self.assertFalse(
            SuggestionTheme.objects.filter(name="Broken coffee machine").exists()
        )

    def test_sets_keywords_on_new_theme(self):
        ai_themes = [{
            "name": "Scheduling flexibility",
            "description": "Flexible scheduling needed",
            "category": "program_design",
            "keywords": ["scheduling", "flexible", "times"],
            "supporting_quotes": [],
        }]
        process_ai_themes(ai_themes, self.quote_source_map, self.program)

        theme = SuggestionTheme.objects.get(name="Scheduling flexibility")
        self.assertIn("scheduling", theme.keywords)
        self.assertIn("flexible", theme.keywords)

    def test_updates_keywords_on_existing_theme_if_empty(self):
        existing = SuggestionTheme.objects.create(
            program=self.program, name="Evening availability",
            keywords="",  # No keywords yet
            source="ai_generated",
        )
        ai_themes = [{
            "name": "Evening availability",
            "description": "Updated",
            "category": "program_design",
            "keywords": ["evening", "late", "hours"],
            "supporting_quotes": [],
        }]
        process_ai_themes(ai_themes, self.quote_source_map, self.program)
        existing.refresh_from_db()
        self.assertIn("evening", existing.keywords)

    def test_does_not_overwrite_existing_keywords(self):
        existing = SuggestionTheme.objects.create(
            program=self.program, name="Evening availability",
            keywords="evening, sessions",
            source="ai_generated",
        )
        ai_themes = [{
            "name": "Evening availability",
            "description": "Updated",
            "category": "program_design",
            "keywords": ["late", "night"],
            "supporting_quotes": [],
        }]
        process_ai_themes(ai_themes, self.quote_source_map, self.program)
        existing.refresh_from_db()
        self.assertEqual(existing.keywords, "evening, sessions")


# ── Helper Function Tests ───────────────────────────────────────────


class ExtractContentWordsTests(TestCase):
    """Test _extract_content_words helper."""

    def test_removes_stopwords(self):
        words = _extract_content_words("I want to have more evening sessions")
        self.assertNotIn("want", words)
        self.assertNotIn("more", words)
        self.assertIn("evening", words)
        self.assertIn("sessions", words)

    def test_removes_short_words(self):
        words = _extract_content_words("I am ok in it")
        self.assertEqual(len(words), 0)

    def test_lowercases(self):
        words = _extract_content_words("Evening Sessions Available")
        self.assertIn("evening", words)
        self.assertIn("sessions", words)
        self.assertIn("available", words)


class FindNoteIdTests(TestCase):
    """Test _find_note_id helper for quote-to-note matching."""

    def test_exact_match(self):
        qsm = {"exact text here": 42}
        self.assertEqual(_find_note_id("exact text here", qsm), 42)

    def test_substring_match_ai_truncated(self):
        qsm = {"This is a long quote about evening sessions": 42}
        self.assertEqual(_find_note_id("evening sessions", qsm), 42)

    def test_substring_match_original_in_ai(self):
        qsm = {"evening sessions": 42}
        self.assertEqual(
            _find_note_id("I said evening sessions to the staff", qsm), 42,
        )

    def test_no_match_returns_none(self):
        qsm = {"something else entirely": 42}
        self.assertIsNone(_find_note_id("no match", qsm))
