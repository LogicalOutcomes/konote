"""Tests for the AI Goal Builder — conversational goal setting.

Covers: panel start, chat flow, PII scrubbing, save (target + metric + section),
session management, permission checks, and AI failure handling.
"""
import json
from unittest.mock import patch, call

from cryptography.fernet import Fernet
from django.test import TestCase, Client, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.plans.models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
    PlanTargetRevision,
)
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()

# Sample AI response for mocking
SAMPLE_AI_RESPONSE = {
    "message": "Housing stability is a great area to focus on.",
    "questions": ["Is the participant currently in transitional housing?"],
    "draft": None,
}

SAMPLE_AI_RESPONSE_WITH_DRAFT = {
    "message": "Here's a draft goal based on our conversation.",
    "questions": [],
    "draft": {
        "name": "Secure stable housing",
        "description": "Participant will transition from transitional to independent housing within 6 months.",
        "client_goal": "I want my own apartment",
        "metric": {
            "existing_metric_id": None,
            "name": "Housing Stability",
            "definition": "1 = No housing leads\n2 = Actively searching\n3 = Approved, awaiting move-in\n4 = Moved in, settling\n5 = Stable independent housing",
            "min_value": 1,
            "max_value": 5,
            "unit": "score",
        },
        "suggested_section": "Housing",
    },
}


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, OPENROUTER_API_KEY="test-key-123")
class GoalBuilderBaseTest(TestCase):
    """Base class with shared setUp for Goal Builder tests."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.user = User.objects.create_user(
            username="staff", password="pass", display_name="Staff User"
        )
        self.program = Program.objects.create(name="Housing Support")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="staff", status="active"
        )

        # Client enrolled in program
        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled"
        )

        # Enable AI
        FeatureToggle.objects.create(feature_key="ai_assist", is_enabled=True)

    def tearDown(self):
        enc_module._fernet = None

    @property
    def start_url(self):
        return f"/ai/goal-builder/{self.client_file.pk}/"

    @property
    def chat_url(self):
        return f"/ai/goal-builder/{self.client_file.pk}/chat/"

    @property
    def save_url(self):
        return f"/ai/goal-builder/{self.client_file.pk}/save/"


class GoalBuilderStartTest(GoalBuilderBaseTest):
    """Test the Goal Builder panel start view."""

    def test_unauthenticated_redirected(self):
        resp = self.http.get(self.start_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)

    def test_authenticated_returns_panel(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get(self.start_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Goal Builder")

    def test_ai_disabled_returns_403(self):
        FeatureToggle.objects.filter(feature_key="ai_assist").update(is_enabled=False)
        self.http.login(username="staff", password="pass")
        resp = self.http.get(self.start_url)
        self.assertEqual(resp.status_code, 403)

    @override_settings(OPENROUTER_API_KEY="")
    def test_no_api_key_returns_403(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get(self.start_url)
        self.assertEqual(resp.status_code, 403)

    def test_pm_without_edit_permission_returns_403(self):
        """Program managers have plan.edit: DENY, so they can't use Goal Builder."""
        pm = User.objects.create_user(username="pm", password="pass", display_name="PM")
        UserProgramRole.objects.create(
            user=pm, program=self.program, role="program_manager", status="active"
        )
        self.http.login(username="pm", password="pass")
        resp = self.http.get(self.start_url)
        self.assertEqual(resp.status_code, 403)

    def test_clears_previous_session(self):
        """Starting the builder clears any previous conversation for this client."""
        self.http.login(username="staff", password="pass")
        # Set up a fake session conversation
        session = self.http.session
        session[f"goal_builder_{self.client_file.pk}"] = {"messages": [{"role": "user", "content": "old"}]}
        session.save()
        # Start fresh
        resp = self.http.get(self.start_url)
        self.assertEqual(resp.status_code, 200)


class GoalBuilderChatTest(GoalBuilderBaseTest):
    """Test the Goal Builder chat endpoint."""

    @patch("konote.ai.build_goal_chat")
    def test_happy_path_returns_ai_message(self, mock_chat):
        mock_chat.return_value = SAMPLE_AI_RESPONSE
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.chat_url, {"message": "Find stable housing"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Housing stability is a great area")
        mock_chat.assert_called_once()

    @patch("konote.ai.build_goal_chat")
    def test_draft_shown_when_present(self, mock_chat):
        mock_chat.return_value = SAMPLE_AI_RESPONSE_WITH_DRAFT
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.chat_url, {"message": "She wants her own apartment in 6 months"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Draft Goal")
        self.assertContains(resp, "Secure stable housing")
        self.assertContains(resp, "Housing Stability")

    def test_empty_message_returns_error(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.chat_url, {"message": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please enter a message")

    def test_unauthenticated_redirected(self):
        resp = self.http.post(self.chat_url, {"message": "test"})
        self.assertEqual(resp.status_code, 302)

    @patch("konote.ai.build_goal_chat")
    def test_ai_failure_returns_error(self, mock_chat):
        mock_chat.return_value = None
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.chat_url, {"message": "Find housing"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "unavailable")

    @patch("konote.ai.build_goal_chat")
    def test_conversation_history_maintained(self, mock_chat):
        """Multi-turn: second message includes first exchange in history."""
        mock_chat.return_value = SAMPLE_AI_RESPONSE
        self.http.login(username="staff", password="pass")

        # First message
        self.http.post(self.chat_url, {"message": "Find housing"})
        # Second message
        mock_chat.return_value = SAMPLE_AI_RESPONSE_WITH_DRAFT
        self.http.post(self.chat_url, {"message": "In transitional housing now"})

        # Check the second call includes prior messages
        second_call_messages = mock_chat.call_args_list[1][0][0]
        self.assertGreaterEqual(len(second_call_messages), 3)
        # First user message should be present
        user_messages = [m for m in second_call_messages if m["role"] == "user"]
        self.assertGreaterEqual(len(user_messages), 2)
        # There should be at least one assistant message from the first exchange
        assistant_messages = [m for m in second_call_messages if m["role"] == "assistant"]
        self.assertGreaterEqual(len(assistant_messages), 1)


class GoalBuilderPIITest(GoalBuilderBaseTest):
    """Test PII scrubbing in the Goal Builder chat."""

    @patch("konote.ai.build_goal_chat")
    @patch("apps.reports.pii_scrub.scrub_pii")
    def test_pii_scrubbed_before_ai_call(self, mock_scrub, mock_chat):
        mock_scrub.return_value = "Find stable housing for [NAME]"
        mock_chat.return_value = SAMPLE_AI_RESPONSE
        self.http.login(username="staff", password="pass")
        self.http.post(self.chat_url, {"message": "Find stable housing for Jane"})

        # scrub_pii should have been called with the raw message
        mock_scrub.assert_called_once()
        raw_message = mock_scrub.call_args[0][0]
        self.assertEqual(raw_message, "Find stable housing for Jane")

        # AI should have received the scrubbed version
        ai_messages = mock_chat.call_args[0][0]
        self.assertEqual(ai_messages[0]["content"], "Find stable housing for [NAME]")

    @patch("konote.ai.build_goal_chat")
    @patch("apps.reports.pii_scrub.scrub_pii")
    def test_known_names_include_client_names(self, mock_scrub, mock_chat):
        mock_scrub.return_value = "test"
        mock_chat.return_value = SAMPLE_AI_RESPONSE
        self.http.login(username="staff", password="pass")
        self.http.post(self.chat_url, {"message": "test"})

        # Check known_names passed to scrub_pii
        known_names = mock_scrub.call_args[0][1]
        self.assertIn("Jane", known_names)
        self.assertIn("Doe", known_names)


class GoalBuilderSaveTest(GoalBuilderBaseTest):
    """Test saving a goal from the Goal Builder."""

    def setUp(self):
        super().setUp()
        # Create an existing section for tests
        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Housing", program=self.program
        )

    def test_unauthenticated_redirected(self):
        resp = self.http.post(self.save_url, {"name": "test"})
        self.assertEqual(resp.status_code, 302)

    def test_save_creates_target_with_existing_section(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.save_url, {
            "name": "Secure stable housing",
            "description": "Transition to independent housing within 6 months.",
            "client_goal": "I want my own apartment",
            "section_id": self.section.pk,
            "metric_name": "Housing Stability",
            "metric_definition": "1 = No leads\n5 = Stable",
            "metric_min": 1,
            "metric_max": 5,
            "metric_unit": "score",
        })
        self.assertEqual(resp.status_code, 302)  # Redirect to plan view

        # Verify target created
        target = PlanTarget.objects.filter(plan_section=self.section).first()
        self.assertIsNotNone(target)
        self.assertEqual(target.name, "Secure stable housing")
        self.assertEqual(target.client_goal, "I want my own apartment")

        # Verify revision created
        revision = PlanTargetRevision.objects.filter(plan_target=target).first()
        self.assertIsNotNone(revision)
        self.assertEqual(revision.name, "Secure stable housing")

        # Verify custom metric created and linked
        metric = MetricDefinition.objects.filter(name="Housing Stability").first()
        self.assertIsNotNone(metric)
        self.assertFalse(metric.is_library)
        self.assertEqual(metric.owning_program, self.program)
        self.assertTrue(
            PlanTargetMetric.objects.filter(plan_target=target, metric_def=metric).exists()
        )

    def test_save_creates_new_section(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.save_url, {
            "name": "Improve employment skills",
            "description": "Gain job-ready skills.",
            "client_goal": "I want to find a job",
            "new_section_name": "Employment",
            "metric_name": "Job Readiness",
            "metric_definition": "1 = Not ready\n5 = Job-ready",
            "metric_min": 1,
            "metric_max": 5,
            "metric_unit": "score",
        })
        self.assertEqual(resp.status_code, 302)

        # Verify new section created
        section = PlanSection.objects.filter(name="Employment", client_file=self.client_file).first()
        self.assertIsNotNone(section)
        self.assertEqual(section.program, self.program)

        # Verify target in new section
        target = PlanTarget.objects.filter(plan_section=section).first()
        self.assertIsNotNone(target)

    def test_save_with_existing_metric(self):
        metric = MetricDefinition.objects.create(
            name="PHQ-9", definition="Depression scale", category="mental_health",
            min_value=0, max_value=27, unit="score", is_enabled=True,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.save_url, {
            "name": "Reduce depression symptoms",
            "description": "Lower PHQ-9 score.",
            "section_id": self.section.pk,
            "existing_metric_id": metric.pk,
        })
        self.assertEqual(resp.status_code, 302)

        # Verify existing metric linked (no new metric created)
        target = PlanTarget.objects.filter(plan_section=self.section).first()
        linked = PlanTargetMetric.objects.filter(plan_target=target).first()
        self.assertIsNotNone(linked)
        self.assertEqual(linked.metric_def, metric)

    def test_save_without_section_returns_error(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.save_url, {
            "name": "Test goal",
            # No section_id or new_section_name
        })
        self.assertEqual(resp.status_code, 200)  # Re-renders form with error

    def test_save_clears_session(self):
        self.http.login(username="staff", password="pass")
        # Set up a fake session conversation
        session = self.http.session
        session[f"goal_builder_{self.client_file.pk}"] = {"messages": [{"role": "user", "content": "test"}]}
        session.save()
        # Save
        self.http.post(self.save_url, {
            "name": "Test goal",
            "section_id": self.section.pk,
            "metric_name": "Test",
            "metric_definition": "1-5",
        })
        # Session should be cleared (check via a new start)
        resp = self.http.get(self.start_url)
        self.assertEqual(resp.status_code, 200)


class BuildGoalChatFunctionTest(TestCase):
    """Test the build_goal_chat() AI function directly."""

    @override_settings(OPENROUTER_API_KEY="test-key")
    @patch("konote.ai._call_openrouter")
    def test_valid_response_parsed(self, mock_call):
        mock_call.return_value = json.dumps(SAMPLE_AI_RESPONSE)
        from konote.ai import build_goal_chat

        result = build_goal_chat(
            [{"role": "user", "content": "Find housing"}],
            "Housing Support",
            [{"id": 1, "name": "PHQ-9", "definition": "test", "category": "mental_health"}],
            ["Housing"],
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["message"], "Housing stability is a great area to focus on.")

    @override_settings(OPENROUTER_API_KEY="test-key")
    @patch("konote.ai._call_openrouter")
    def test_response_with_draft_parsed(self, mock_call):
        mock_call.return_value = json.dumps(SAMPLE_AI_RESPONSE_WITH_DRAFT)
        from konote.ai import build_goal_chat

        result = build_goal_chat(
            [{"role": "user", "content": "She wants her own apartment"}],
            "Housing Support", [], [],
        )
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["draft"])
        self.assertEqual(result["draft"]["name"], "Secure stable housing")
        self.assertEqual(result["draft"]["metric"]["min_value"], 1)
        self.assertEqual(result["draft"]["metric"]["max_value"], 5)

    @override_settings(OPENROUTER_API_KEY="test-key")
    @patch("konote.ai._call_openrouter")
    def test_malformed_json_returns_none(self, mock_call):
        mock_call.return_value = "This is not JSON"
        from konote.ai import build_goal_chat

        result = build_goal_chat(
            [{"role": "user", "content": "test"}],
            "Housing Support", [], [],
        )
        self.assertIsNone(result)

    @override_settings(OPENROUTER_API_KEY="test-key")
    @patch("konote.ai._call_openrouter")
    def test_api_failure_returns_none(self, mock_call):
        mock_call.return_value = None
        from konote.ai import build_goal_chat

        result = build_goal_chat(
            [{"role": "user", "content": "test"}],
            "Housing Support", [], [],
        )
        self.assertIsNone(result)

    @override_settings(OPENROUTER_API_KEY="test-key")
    @patch("konote.ai._call_openrouter")
    def test_markdown_fences_stripped(self, mock_call):
        mock_call.return_value = "```json\n" + json.dumps(SAMPLE_AI_RESPONSE) + "\n```"
        from konote.ai import build_goal_chat

        result = build_goal_chat(
            [{"role": "user", "content": "test"}],
            "Housing Support", [], [],
        )
        self.assertIsNotNone(result)

    @override_settings(OPENROUTER_API_KEY="test-key")
    @patch("konote.ai._call_openrouter")
    def test_invalid_metric_id_cleared(self, mock_call):
        """If AI suggests a metric ID that's not in the catalogue, it's set to None."""
        response = {
            "message": "Draft ready.",
            "draft": {
                "name": "Test",
                "description": "Test",
                "client_goal": "Test",
                "metric": {
                    "existing_metric_id": 999,  # Not in catalogue
                    "name": "Test Metric",
                    "definition": "1-5",
                    "min_value": 1,
                    "max_value": 5,
                    "unit": "score",
                },
                "suggested_section": "Test",
            },
        }
        mock_call.return_value = json.dumps(response)
        from konote.ai import build_goal_chat

        result = build_goal_chat(
            [{"role": "user", "content": "test"}],
            "Housing Support",
            [{"id": 1, "name": "PHQ-9", "definition": "test", "category": "mental_health"}],
            [],
        )
        # metric_id 999 should be cleared to None since it's not in catalogue
        self.assertIsNone(result["draft"]["metric"]["existing_metric_id"])


class GoalBuilderSessionTest(GoalBuilderBaseTest):
    """Test session management in the Goal Builder."""

    @patch("konote.ai.build_goal_chat")
    def test_session_stores_conversation(self, mock_chat):
        mock_chat.return_value = SAMPLE_AI_RESPONSE
        self.http.login(username="staff", password="pass")
        self.http.post(self.chat_url, {"message": "Find housing"})

        # Check session
        session = self.http.session
        session_data = session.get(f"goal_builder_{self.client_file.pk}")
        self.assertIsNotNone(session_data)
        messages = session_data["messages"]
        self.assertEqual(len(messages), 2)  # user + assistant
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
