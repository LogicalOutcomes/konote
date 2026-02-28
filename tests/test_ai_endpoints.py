"""Tests for AI HTMX endpoints — form validation, permission checks, mocked AI calls."""
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import SimpleTestCase, TestCase, Client, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, OPENROUTER_API_KEY="test-key-123")
class AIEndpointBaseTest(TestCase):
    """Base class with shared setUp for AI endpoint tests."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.user = User.objects.create_user(
            username="staff", password="pass", display_name="Staff"
        )
        self.program = Program.objects.create(name="Housing")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="staff", status="active"
        )

        # Enable the AI feature toggle
        FeatureToggle.objects.create(feature_key="ai_assist", is_enabled=True)

    def tearDown(self):
        enc_module._fernet = None


class SuggestMetricsViewTest(AIEndpointBaseTest):
    """Test the suggest-metrics AI endpoint."""

    def setUp(self):
        super().setUp()
        self.metric = MetricDefinition.objects.create(
            name="PHQ-9", definition="Depression scale", category="mental_health",
            min_value=0, max_value=27, unit="score",
        )
        self.url = "/ai/suggest-metrics/"

    def test_unauthenticated_redirected(self):
        resp = self.http.post(self.url, {"target_description": "test"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)

    def test_missing_target_description_returns_error(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please enter a target description")

    def test_ai_disabled_returns_403(self):
        FeatureToggle.objects.filter(feature_key="ai_assist").update(is_enabled=False)
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"target_description": "Find housing"})
        self.assertEqual(resp.status_code, 403)

    @override_settings(OPENROUTER_API_KEY="")
    def test_no_api_key_returns_403(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"target_description": "Find housing"})
        self.assertEqual(resp.status_code, 403)

    @patch("konote.ai.suggest_metrics")
    def test_happy_path_returns_suggestions(self, mock_suggest):
        mock_suggest.return_value = [
            {"metric_id": self.metric.pk, "name": "PHQ-9", "reason": "Relevant for mental health"}
        ]
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"target_description": "Improve mental health"})
        self.assertEqual(resp.status_code, 200)
        mock_suggest.assert_called_once()
        # The target_description should be passed to the AI function
        call_args = mock_suggest.call_args
        self.assertEqual(call_args[0][0], "Improve mental health")

    @patch("konote.ai.suggest_metrics")
    def test_ai_failure_returns_error_message(self, mock_suggest):
        mock_suggest.return_value = None
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"target_description": "Find housing"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "unavailable")


class ImproveOutcomeViewTest(AIEndpointBaseTest):
    """Test the improve-outcome AI endpoint."""

    def setUp(self):
        super().setUp()
        self.url = "/ai/improve-outcome/"

    def test_missing_draft_text_returns_error(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please enter a draft outcome")

    def test_ai_disabled_returns_403(self):
        FeatureToggle.objects.filter(feature_key="ai_assist").update(is_enabled=False)
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"draft_text": "Get better at stuff"})
        self.assertEqual(resp.status_code, 403)

    @patch("konote.ai.improve_outcome")
    def test_happy_path_returns_improved_text(self, mock_improve):
        mock_improve.return_value = "Client will achieve stable housing within 3 months."
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"draft_text": "Get housing"})
        self.assertEqual(resp.status_code, 200)
        mock_improve.assert_called_once_with("Get housing")

    @patch("konote.ai.improve_outcome")
    def test_ai_failure_returns_error_message(self, mock_improve):
        mock_improve.return_value = None
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"draft_text": "Get housing"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "unavailable")


class GenerateNarrativeViewTest(AIEndpointBaseTest):
    """Test the generate-narrative AI endpoint."""

    def setUp(self):
        super().setUp()
        self.url = "/ai/generate-narrative/"

    def test_missing_fields_returns_error(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please select a program")

    def test_missing_date_range_returns_error(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"program_id": self.program.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please select a program")

    def test_invalid_program_returns_400(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "program_id": 99999,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        })
        self.assertEqual(resp.status_code, 400)

    @patch("konote.ai.generate_narrative")
    def test_no_metric_data_returns_error(self, mock_narrative):
        """When there are no metric values for the period, show an error."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "program_id": self.program.pk,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No metric data found")
        mock_narrative.assert_not_called()

    def test_ai_disabled_returns_403(self):
        FeatureToggle.objects.filter(feature_key="ai_assist").update(is_enabled=False)
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "program_id": self.program.pk,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        })
        self.assertEqual(resp.status_code, 403)


class SuggestNoteStructureViewTest(AIEndpointBaseTest):
    """Test the suggest-note-structure AI endpoint."""

    def setUp(self):
        super().setUp()
        self.url = "/ai/suggest-note-structure/"

        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="active"
        )

        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.program,
        )
        self.target = PlanTarget.objects.create(
            plan_section=self.section, client_file=self.client_file,
            name="Find Housing", description="Stable housing within 3 months",
        )
        self.metric = MetricDefinition.objects.create(
            name="Housing Score", definition="Stability score", category="housing",
            min_value=0, max_value=10, unit="score",
        )
        PlanTargetMetric.objects.create(plan_target=self.target, metric_def=self.metric)

    def test_missing_target_id_returns_error(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No target selected")

    def test_invalid_target_id_returns_400(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"target_id": 99999})
        self.assertEqual(resp.status_code, 400)

    def test_ai_disabled_returns_403(self):
        FeatureToggle.objects.filter(feature_key="ai_assist").update(is_enabled=False)
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"target_id": self.target.pk})
        self.assertEqual(resp.status_code, 403)

    @patch("konote.ai.suggest_note_structure")
    def test_happy_path_returns_structure(self, mock_suggest):
        mock_suggest.return_value = [
            {"section": "Observation", "prompt": "Describe what you observed."},
            {"section": "Progress", "prompt": "Note any progress on metrics."},
        ]
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"target_id": self.target.pk})
        self.assertEqual(resp.status_code, 200)
        mock_suggest.assert_called_once()
        call_args = mock_suggest.call_args[0]
        self.assertEqual(call_args[0], "Find Housing")
        self.assertEqual(call_args[1], "Stable housing within 3 months")

    @patch("konote.ai.suggest_note_structure")
    def test_ai_failure_returns_error_message(self, mock_suggest):
        mock_suggest.return_value = None
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"target_id": self.target.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "unavailable")

    def test_unauthenticated_redirected(self):
        resp = self.http.post(self.url, {"target_id": self.target.pk})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)


class SuggestTargetViewTest(AIEndpointBaseTest):
    """Test the suggest-target AI endpoint."""

    def setUp(self):
        super().setUp()
        self.url = "/ai/suggest-target/"

        self.client_file = ClientFile()
        self.client_file.first_name = "Jayden"
        self.client_file.last_name = "Martinez"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="active"
        )

        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Social Goals", program=self.program,
        )
        self.metric = MetricDefinition.objects.create(
            name="Progress", definition="1-5 progress scale", category="general",
            min_value=1, max_value=5, unit="score",
        )

    def test_unauthenticated_redirected(self):
        resp = self.http.post(self.url, {
            "participant_words": "I want to make a friend",
            "client_id": self.client_file.pk,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)

    def test_missing_words_returns_error(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"client_id": self.client_file.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "describe what the participant")

    def test_missing_client_id_returns_error(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {"participant_words": "I want a friend"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "describe what the participant")

    def test_ai_disabled_returns_403(self):
        FeatureToggle.objects.filter(feature_key="ai_assist").update(is_enabled=False)
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "participant_words": "I want a friend",
            "client_id": self.client_file.pk,
        })
        self.assertEqual(resp.status_code, 403)

    @override_settings(OPENROUTER_API_KEY="")
    def test_no_api_key_returns_403(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "participant_words": "I want a friend",
            "client_id": self.client_file.pk,
        })
        self.assertEqual(resp.status_code, 403)

    def test_invalid_client_id_returns_404(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "participant_words": "I want a friend",
            "client_id": 99999,
        })
        self.assertEqual(resp.status_code, 404)

    @patch("konote.ai.suggest_target")
    def test_happy_path_returns_suggestion_card(self, mock_suggest):
        mock_suggest.return_value = {
            "name": "Build social connections",
            "description": "Jayden will identify and reach out to one person outside the group for a social activity within 3 months.",
            "client_goal": "I want to make a friend that I can go out with",
            "suggested_section": "Social Goals",
            "metrics": [
                {"metric_id": self.metric.pk, "name": "Progress", "reason": "Tracks steps toward goal"},
            ],
        }
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "participant_words": "I want to make a friend that I can go out with",
            "client_id": self.client_file.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Build social connections")
        self.assertContains(resp, "btn-use-suggestion")
        self.assertContains(resp, "btn-edit-suggestion")
        self.assertContains(resp, "btn-start-over")
        mock_suggest.assert_called_once()

    @patch("konote.ai.suggest_target")
    def test_ai_failure_returns_error_partial(self, mock_suggest):
        mock_suggest.return_value = None
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "participant_words": "I want a friend",
            "client_id": self.client_file.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "couldn't be generated")
        self.assertContains(resp, "btn-show-manual-form")

    @patch("konote.ai.suggest_target")
    def test_section_pk_resolved_for_matching_section(self, mock_suggest):
        mock_suggest.return_value = {
            "name": "Build social connections",
            "description": "SMART description",
            "client_goal": "Make a friend",
            "suggested_section": "Social Goals",
            "metrics": [],
        }
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "participant_words": "Make a friend",
            "client_id": self.client_file.pk,
        })
        self.assertEqual(resp.status_code, 200)
        # The matched_section_pk should be set in the template context
        self.assertContains(resp, str(self.section.pk))

    @patch("konote.ai.suggest_target")
    def test_pii_scrubbed_before_ai_call(self, mock_suggest):
        """Participant's name should be scrubbed from the words sent to AI."""
        mock_suggest.return_value = {
            "name": "Build social connections",
            "description": "SMART description",
            "client_goal": "Make a friend",
            "suggested_section": "Social Goals",
            "metrics": [],
        }
        self.http.login(username="staff", password="pass")
        resp = self.http.post(self.url, {
            "participant_words": "Jayden wants to make a friend",
            "client_id": self.client_file.pk,
        })
        self.assertEqual(resp.status_code, 200)
        # The AI function should have been called with scrubbed text
        call_args = mock_suggest.call_args[0]
        scrubbed_words = call_args[0]
        self.assertNotIn("Jayden", scrubbed_words)


class ValidateSuggestTargetResponseTest(SimpleTestCase):
    """Unit tests for _validate_suggest_target_response — no DB needed."""

    def test_metric_catalogue_uses_metric_id_key(self):
        """Regression for BUG-AI1: catalogue dicts use 'metric_id', not 'id'."""
        from konote.ai import _validate_suggest_target_response

        catalogue = [
            {"metric_id": 1, "name": "PHQ-9", "definition": "Depression scale", "category": "mental_health"},
            {"metric_id": 2, "name": "GAD-7", "definition": "Anxiety scale", "category": "mental_health"},
        ]
        response = {
            "name": "Improve wellbeing",
            "description": "SMART description here",
            "client_goal": "Feel better",
            "suggested_section": "Health",
            "metrics": [
                {"metric_id": 1, "name": "PHQ-9", "reason": "Tracks depression"},
                {"metric_id": 999, "name": "Invalid", "reason": "Not in catalogue"},
            ],
        }
        result = _validate_suggest_target_response(response, catalogue)
        self.assertIsNotNone(result)
        # Valid metric kept, invalid metric filtered out
        self.assertEqual(len(result["metrics"]), 1)
        self.assertEqual(result["metrics"][0]["metric_id"], 1)
