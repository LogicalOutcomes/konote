"""Tests for focused theme analysis and graduated privacy threshold."""
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, Client, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import ProgressNote
from apps.notes.theme_engine import _check_privacy_gate, get_participant_count
from apps.programs.models import Program, UserProgramRole
from apps.reports.insights import (
    MIN_PARTICIPANTS_FOR_QUOTES,
    MIN_PARTICIPANTS_FOR_THEME_PROCESSING,
)
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()
FOCUSED_URL = "/manage/suggestions/themes/focused-analysis/"


def _create_participants(program, count):
    """Create N active participant enrolments for a program."""
    for i in range(count):
        cf = ClientFile.objects.create()
        ClientProgramEnrolment.objects.create(
            client_file=cf, program=program, status="active",
        )


# ── Privacy gate tests ──────────────────────────────────────────────

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PrivacyGateGraduatedThresholdTest(TestCase):
    """Test _check_privacy_gate with graduated N=5/15 thresholds."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")

    def tearDown(self):
        enc_module._fernet = None

    @override_settings(INSIGHTS_API_BASE="http://localhost:11434/v1")
    def test_self_hosted_4_participants_denied(self):
        _create_participants(self.program, 4)
        self.assertFalse(_check_privacy_gate(self.program))

    @override_settings(INSIGHTS_API_BASE="http://localhost:11434/v1")
    def test_self_hosted_5_participants_allowed(self):
        _create_participants(self.program, 5)
        self.assertTrue(_check_privacy_gate(self.program))

    @override_settings(INSIGHTS_API_BASE="http://localhost:11434/v1")
    def test_self_hosted_14_participants_allowed(self):
        _create_participants(self.program, 14)
        self.assertTrue(_check_privacy_gate(self.program))

    @override_settings(INSIGHTS_API_BASE="")
    def test_external_14_participants_denied(self):
        _create_participants(self.program, 14)
        self.assertFalse(_check_privacy_gate(self.program))

    @override_settings(INSIGHTS_API_BASE="")
    def test_external_15_participants_allowed(self):
        _create_participants(self.program, 15)
        self.assertTrue(_check_privacy_gate(self.program))

    @override_settings(DEMO_MODE=True, INSIGHTS_API_BASE="")
    def test_demo_mode_bypasses_gate(self):
        _create_participants(self.program, 2)
        self.assertTrue(_check_privacy_gate(self.program))

    def test_constants_are_correct(self):
        self.assertEqual(MIN_PARTICIPANTS_FOR_THEME_PROCESSING, 5)
        self.assertEqual(MIN_PARTICIPANTS_FOR_QUOTES, 15)


# ── Focused analysis view tests ─────────────────────────────────────

@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    OPENROUTER_API_KEY="test-key",
    INSIGHTS_API_BASE="http://localhost:11434/v1",
)
class FocusedAnalysisViewTest(TestCase):
    """Test the focused analysis HTMX endpoint."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.user = User.objects.create_user(
            username="pm", password="pass", display_name="PM User"
        )
        self.program = Program.objects.create(name="Housing")
        UserProgramRole.objects.create(
            user=self.user, program=self.program,
            role="program_manager", status="active",
        )

        # Enable feature toggles
        FeatureToggle.objects.create(
            feature_key="ai_assist_tools_only", is_enabled=True,
        )
        FeatureToggle.objects.create(
            feature_key="ai_assist_participant_data", is_enabled=True,
        )

        # Create 10 participants (above N=5 self-hosted threshold)
        _create_participants(self.program, 10)

        # Create some suggestions
        for i in range(5):
            cf = ClientFile.objects.create()
            ClientProgramEnrolment.objects.create(
                client_file=cf, program=self.program, status="active",
            )
            ProgressNote.objects.create(
                client_file=cf,
                author=self.user,
                author_program=self.program,
                participant_suggestion=f"I wish there were evening sessions available {i}",
                suggestion_priority="important",
            )

    def tearDown(self):
        enc_module._fernet = None

    def test_unauthenticated_redirected(self):
        resp = self.http.post(FOCUSED_URL, {
            "question": "Any themes about hours?",
            "program_id": self.program.pk,
        })
        self.assertEqual(resp.status_code, 302)

    def test_get_not_allowed(self):
        self.http.login(username="pm", password="pass")
        resp = self.http.get(FOCUSED_URL)
        self.assertEqual(resp.status_code, 405)

    def test_feature_toggle_disabled(self):
        FeatureToggle.objects.filter(
            feature_key="ai_assist_participant_data",
        ).update(is_enabled=False)
        self.http.login(username="pm", password="pass")
        resp = self.http.post(FOCUSED_URL, {
            "question": "test",
            "program_id": self.program.pk,
        })
        self.assertEqual(resp.status_code, 403)

    def test_empty_question_returns_error(self):
        self.http.login(username="pm", password="pass")
        resp = self.http.post(FOCUSED_URL, {
            "question": "",
            "program_id": self.program.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please enter a question")

    @override_settings(INSIGHTS_API_BASE="http://localhost:11434/v1")
    def test_privacy_gate_blocks_small_programs(self):
        small_program = Program.objects.create(name="Small")
        UserProgramRole.objects.create(
            user=self.user, program=small_program,
            role="program_manager", status="active",
        )
        _create_participants(small_program, 3)

        self.http.login(username="pm", password="pass")
        resp = self.http.post(FOCUSED_URL, {
            "question": "test",
            "program_id": small_program.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "minimum of 5")

    @patch("apps.notes.suggestion_views.generate_focused_analysis")
    def test_happy_path_returns_results(self, mock_ai):
        mock_ai.return_value = {
            "relevant_count": 3,
            "total_count": 5,
            "summary": "Participants want evening sessions.",
            "sub_themes": [
                {"name": "Evening Hours", "description": "Want evening sessions", "count": 3},
            ],
            "suggestion": "Schedule Flexibility",
        }
        self.http.login(username="pm", password="pass")
        resp = self.http.post(FOCUSED_URL, {
            "question": "Any themes about scheduling?",
            "program_id": self.program.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Analysis Results")
        self.assertContains(resp, "evening sessions")
        self.assertContains(resp, "Schedule Flexibility")
        self.assertContains(resp, "Create Theme from This")

    @patch("apps.notes.suggestion_views.generate_focused_analysis")
    def test_ai_failure_returns_error(self, mock_ai):
        mock_ai.return_value = None
        self.http.login(username="pm", password="pass")
        resp = self.http.post(FOCUSED_URL, {
            "question": "test question",
            "program_id": self.program.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "could not be completed")

    @patch("apps.notes.suggestion_views.generate_focused_analysis")
    def test_rate_limit_enforced(self, mock_ai):
        mock_ai.return_value = {
            "relevant_count": 0,
            "total_count": 0,
            "summary": "Nothing found.",
            "sub_themes": [],
            "suggestion": "",
        }
        self.http.login(username="pm", password="pass")

        # Exhaust the rate limit
        from django.core.cache import cache
        cache.set(f"focused_analysis:{self.user.pk}", 10, 3600)

        resp = self.http.post(FOCUSED_URL, {
            "question": "test",
            "program_id": self.program.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Rate limit")

    @patch("apps.notes.suggestion_views.generate_focused_analysis")
    def test_audit_log_created(self, mock_ai):
        mock_ai.return_value = {
            "relevant_count": 0,
            "total_count": 0,
            "summary": "Nothing found.",
            "sub_themes": [],
            "suggestion": "",
        }
        self.http.login(username="pm", password="pass")
        self.http.post(FOCUSED_URL, {
            "question": "opening hours",
            "program_id": self.program.pk,
        })

        from apps.audit.models import AuditLog
        log = AuditLog.objects.using("audit").filter(
            action="focused_analysis",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_values["question"], "opening hours")
        self.assertEqual(log.program_id, self.program.pk)

    def test_inaccessible_program_returns_403(self):
        other_program = Program.objects.create(name="Secret")
        self.http.login(username="pm", password="pass")
        resp = self.http.post(FOCUSED_URL, {
            "question": "test",
            "program_id": other_program.pk,
        })
        self.assertEqual(resp.status_code, 403)


# ── AI response validation tests ────────────────────────────────────

class FocusedAnalysisValidationTest(TestCase):
    """Test _validate_focused_analysis."""

    def test_valid_response(self):
        from konote.ai import _validate_focused_analysis
        resp = {
            "relevant_count": 3,
            "total_count": 10,
            "summary": "Participants mentioned scheduling concerns.",
            "sub_themes": [
                {"name": "Timing", "description": "About timing", "count": 2},
            ],
            "suggestion": "Scheduling",
        }
        result = _validate_focused_analysis(resp, 10)
        self.assertIsNotNone(result)
        self.assertEqual(result["total_count"], 10)
        self.assertEqual(result["relevant_count"], 3)

    def test_missing_summary_returns_none(self):
        from konote.ai import _validate_focused_analysis
        resp = {"relevant_count": 0, "total_count": 0}
        result = _validate_focused_analysis(resp, 0)
        self.assertIsNone(result)

    def test_relevant_count_capped(self):
        from konote.ai import _validate_focused_analysis
        resp = {
            "relevant_count": 999,
            "total_count": 5,
            "summary": "Test summary.",
            "sub_themes": [],
            "suggestion": "",
        }
        result = _validate_focused_analysis(resp, 5)
        self.assertEqual(result["relevant_count"], 5)

    def test_non_dict_returns_none(self):
        from konote.ai import _validate_focused_analysis
        result = _validate_focused_analysis("not a dict", 5)
        self.assertIsNone(result)
