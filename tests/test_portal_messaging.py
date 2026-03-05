"""Tests for the portal participant messaging feature.

Run with:
    pytest tests/test_portal_messaging.py -v
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.portal.models import ParticipantUser
from apps.programs.models import Program
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PortalMessageWorkerNamesTests(TestCase):
    """Test that the message page shows assigned worker names."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.worker_a = User.objects.create_user(
            username="worker_a", password="testpass123",
            display_name="Alice Worker",
        )
        self.worker_b = User.objects.create_user(
            username="worker_b", password="testpass123",
            display_name="Bob Worker",
        )

        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")

        self.client_file = ClientFile.objects.create(
            record_id="MSG-001", status="active",
        )
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Participant"
        self.client_file.save()

        # Active episode with worker in program A
        self.episode_a = ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program_a,
            status="active",
            primary_worker=self.worker_a,
        )

        self.participant = ParticipantUser.objects.create_participant(
            email="msg@example.com",
            client_file=self.client_file,
            display_name="Msg P",
            password="testpass123",
        )

        FeatureToggle.objects.update_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def _portal_login(self):
        """Set up portal session for the test client."""
        self.client.get("/my/login/")
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.pk)
        session.save()

    def test_worker_names_in_context(self):
        """GET /my/message/ includes assigned worker names in context."""
        self._portal_login()
        response = self.client.get("/my/message/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("worker_names", response.context)
        self.assertEqual(response.context["worker_names"], ["Alice Worker"])

    def test_multiple_workers_across_programs(self):
        """Worker names from multiple active episodes are all shown."""
        # Add second active episode with different worker
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program_b,
            status="active",
            primary_worker=self.worker_b,
        )
        self._portal_login()
        response = self.client.get("/my/message/")
        names = sorted(response.context["worker_names"])
        self.assertEqual(names, ["Alice Worker", "Bob Worker"])

    def test_inactive_episode_workers_excluded(self):
        """Workers from closed/inactive episodes are not shown."""
        # Close episode A, add inactive episode with worker B
        self.episode_a.status = "closed"
        self.episode_a.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program_b,
            status="closed",
            primary_worker=self.worker_b,
        )
        self._portal_login()
        response = self.client.get("/my/message/")
        self.assertEqual(response.context["worker_names"], [])

    def test_no_worker_assigned(self):
        """If no worker is assigned, worker_names is empty."""
        self.episode_a.primary_worker = None
        self.episode_a.save()
        self._portal_login()
        response = self.client.get("/my/message/")
        self.assertEqual(response.context["worker_names"], [])

    def test_worker_name_displayed_in_template(self):
        """The worker name appears in the rendered HTML."""
        self._portal_login()
        response = self.client.get("/my/message/")
        self.assertContains(response, "Alice Worker")
        self.assertContains(response, "To:")
