"""Tests for PIPEDA data access request views — authorization and POST-only fixes."""
from datetime import date, timedelta

from cryptography.fernet import Fernet
from django.test import TestCase, Client, override_settings

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment, DataAccessRequest
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class DataAccessAuthorizationTest(TestCase):
    """Test that data access views enforce client authorization (Fix 2)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        # Two programs
        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6")

        # Staff user assigned to Program A only
        self.staff = User.objects.create_user(
            username="staffuser", password="testpass123", display_name="Staff"
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.prog_a, role="staff"
        )

        # Client enrolled in Program B only (not accessible to staff)
        self.client_b = ClientFile()
        self.client_b.first_name = "Private"
        self.client_b.last_name = "Client"
        self.client_b.record_id = "REC-002"
        self.client_b.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_b, program=self.prog_b
        )

        # Client enrolled in Program A (accessible)
        self.client_a = ClientFile()
        self.client_a.first_name = "Accessible"
        self.client_a.last_name = "Client"
        self.client_a.record_id = "REC-001"
        self.client_a.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_a, program=self.prog_a
        )

        # Data access request for client in B
        self.dar_b = DataAccessRequest.objects.create(
            client_file=self.client_b,
            requested_at=date.today(),
            request_method="written",
            deadline=date.today() + timedelta(days=30),
            created_by=self.staff,
        )

        # Data access request for client in A
        self.dar_a = DataAccessRequest.objects.create(
            client_file=self.client_a,
            requested_at=date.today(),
            request_method="written",
            deadline=date.today() + timedelta(days=30),
            created_by=self.staff,
        )

        self.http.login(username="staffuser", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def test_checklist_forbidden_for_unassigned_client(self):
        """Staff cannot view checklist for client in another program."""
        resp = self.http.get(f"/data-access/{self.dar_b.pk}/")
        self.assertEqual(resp.status_code, 403)

    def test_checklist_accessible_for_assigned_client(self):
        """Staff can view checklist for client in their program."""
        resp = self.http.get(f"/data-access/{self.dar_a.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_complete_forbidden_for_unassigned_client(self):
        """Staff cannot complete a request for client in another program."""
        resp = self.http.post(f"/data-access/{self.dar_b.pk}/complete/", {
            "completed_at": str(date.today()),
            "delivery_method": "in_person",
        })
        self.assertEqual(resp.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class DataAccessCompletePostOnlyTest(TestCase):
    """Test that data_access_complete is POST-only (Fix 5)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.staff = User.objects.create_user(
            username="staffuser", password="testpass123", display_name="Staff"
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.prog, role="staff"
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.record_id = "REC-001"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.prog
        )
        self.dar = DataAccessRequest.objects.create(
            client_file=self.client_file,
            requested_at=date.today(),
            request_method="written",
            deadline=date.today() + timedelta(days=30),
            created_by=self.staff,
        )
        self.http.login(username="staffuser", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def test_get_redirects_to_checklist(self):
        """GET to complete endpoint should redirect to checklist (Fix 5)."""
        resp = self.http.get(f"/data-access/{self.dar.pk}/complete/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/data-access/{self.dar.pk}/", resp.url)

    def test_post_completes_request(self):
        """POST with valid data should mark request complete."""
        resp = self.http.post(f"/data-access/{self.dar.pk}/complete/", {
            "completed_at": str(date.today()),
            "delivery_method": "in_person",
        })
        self.assertEqual(resp.status_code, 302)
        self.dar.refresh_from_db()
        self.assertIsNotNone(self.dar.completed_at)

    def test_already_completed_redirects(self):
        """Re-completing an already-completed request should redirect with info."""
        self.dar.completed_at = date.today()
        self.dar.save(update_fields=["completed_at"])
        resp = self.http.post(f"/data-access/{self.dar.pk}/complete/", {
            "completed_at": str(date.today()),
            "delivery_method": "in_person",
        })
        self.assertEqual(resp.status_code, 302)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class DataAccessURLNamespaceTest(TestCase):
    """Test that data access URL namespace works (Fix 11)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_namespaced_url_resolves(self):
        from django.urls import reverse
        url = reverse("data_access:data_access_checklist", kwargs={"pk": 1})
        self.assertEqual(url, "/data-access/1/")

    def test_complete_url_resolves(self):
        from django.urls import reverse
        url = reverse("data_access:data_access_complete", kwargs={"pk": 1})
        self.assertEqual(url, "/data-access/1/complete/")
