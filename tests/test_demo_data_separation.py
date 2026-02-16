"""Tests for demo/real data separation security.

These tests verify the critical security requirement that:
- Demo users can ONLY see demo clients
- Real users can ONLY see real clients
- Impersonation is ONLY allowed for demo users
"""
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import ClientFile, ClientProgramEnrolment
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DemoDataManagerTest(TestCase):
    """Test ClientFile.objects.real() and .demo() manager methods."""

    def setUp(self):
        enc_module._fernet = None

    def _create_client(self, first="Test", last="User", is_demo=False, record_id=""):
        cf = ClientFile(is_demo=is_demo, record_id=record_id)
        cf.first_name = first
        cf.last_name = last
        cf.save()
        return cf

    def test_real_manager_excludes_demo_clients(self):
        real_client = self._create_client("Real", "User", is_demo=False)
        demo_client = self._create_client("Demo", "User", is_demo=True, record_id="DEMO-001")

        real_clients = list(ClientFile.objects.real())
        self.assertIn(real_client, real_clients)
        self.assertNotIn(demo_client, real_clients)

    def test_demo_manager_excludes_real_clients(self):
        real_client = self._create_client("Real", "User", is_demo=False)
        demo_client = self._create_client("Demo", "User", is_demo=True, record_id="DEMO-001")

        demo_clients = list(ClientFile.objects.demo())
        self.assertNotIn(real_client, demo_clients)
        self.assertIn(demo_client, demo_clients)

    def test_real_and_demo_are_mutually_exclusive(self):
        self._create_client("Real", "One", is_demo=False)
        self._create_client("Real", "Two", is_demo=False)
        self._create_client("Demo", "One", is_demo=True)
        self._create_client("Demo", "Two", is_demo=True)

        real_pks = set(ClientFile.objects.real().values_list("pk", flat=True))
        demo_pks = set(ClientFile.objects.demo().values_list("pk", flat=True))

        # No overlap between real and demo
        self.assertEqual(len(real_pks & demo_pks), 0)
        # Together they equal all clients
        self.assertEqual(len(real_pks | demo_pks), 4)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DemoDataVisibilityTest(TestCase):
    """Test that demo users see demo data and real users see real data."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()
        self.prog = Program.objects.create(name="Test Program", colour_hex="#10B981")

        # Create real users and clients
        self.real_admin = User.objects.create_user(
            username="real-admin", password="testpass123", is_admin=True, is_demo=False
        )
        self.real_staff = User.objects.create_user(
            username="real-staff", password="testpass123", is_admin=False, is_demo=False
        )
        UserProgramRole.objects.create(user=self.real_staff, program=self.prog, role="staff")

        # Create demo users
        self.demo_admin = User.objects.create_user(
            username="demo-admin", password="testpass123", is_admin=True, is_demo=True
        )
        self.demo_staff = User.objects.create_user(
            username="demo-staff", password="testpass123", is_admin=False, is_demo=True
        )
        UserProgramRole.objects.create(user=self.demo_staff, program=self.prog, role="staff")

        # Create clients
        self.real_client = self._create_client("Real", "Client", is_demo=False)
        self.demo_client = self._create_client("Demo", "Client", is_demo=True, record_id="DEMO-001")
        ClientProgramEnrolment.objects.create(client_file=self.real_client, program=self.prog)
        ClientProgramEnrolment.objects.create(client_file=self.demo_client, program=self.prog)

    def _create_client(self, first, last, is_demo, record_id=""):
        cf = ClientFile(is_demo=is_demo, record_id=record_id)
        cf.first_name = first
        cf.last_name = last
        cf.save()
        return cf

    def test_real_user_sees_only_real_clients(self):
        self.http_client.login(username="real-staff", password="testpass123")
        resp = self.http_client.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Real")
        self.assertNotContains(resp, "Demo")

    def test_demo_user_sees_only_demo_clients(self):
        self.http_client.login(username="demo-staff", password="testpass123")
        resp = self.http_client.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Demo")
        self.assertNotContains(resp, "Real Client")

    def test_real_user_cannot_access_demo_client_detail(self):
        self.http_client.login(username="real-admin", password="testpass123")
        resp = self.http_client.get(f"/participants/{self.demo_client.pk}/")
        # Should get 403 or redirect, not 200
        self.assertIn(resp.status_code, [403, 404, 302])

    def test_demo_user_cannot_access_real_client_detail(self):
        self.http_client.login(username="demo-admin", password="testpass123")
        resp = self.http_client.get(f"/participants/{self.real_client.pk}/")
        # Should get 403 or redirect, not 200
        self.assertIn(resp.status_code, [403, 404, 302])

    def test_search_respects_demo_status(self):
        self.http_client.login(username="real-staff", password="testpass123")
        resp = self.http_client.get("/participants/search/?q=Client")
        self.assertContains(resp, "Real")
        self.assertNotContains(resp, "DEMO-001")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ImpersonationGuardTest(TestCase):
    """Test that impersonation is only allowed for demo users."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        # Admin who will attempt impersonation
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, is_demo=False
        )

        # Demo user (can be impersonated)
        self.demo_user = User.objects.create_user(
            username="demo-staff", password="testpass123", is_admin=False, is_demo=True
        )

        # Real user (CANNOT be impersonated - this is the critical security test)
        self.real_user = User.objects.create_user(
            username="real-staff", password="testpass123", is_admin=False, is_demo=False
        )

    def test_admin_can_impersonate_demo_user(self):
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(f"/admin/users/{self.demo_user.pk}/impersonate/")
        # Should redirect to home after successful impersonation
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")

    def test_admin_cannot_impersonate_real_user(self):
        """CRITICAL SECURITY TEST: Admin must NOT be able to impersonate real users."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(f"/admin/users/{self.real_user.pk}/impersonate/")
        # Should redirect back to user list with error, not to home
        self.assertEqual(resp.status_code, 302)
        self.assertNotEqual(resp.url, "/")

        # Follow redirect and check for error message
        resp = self.http_client.get(resp.url)
        self.assertContains(resp, "Cannot impersonate real users")

    def test_impersonation_requires_admin(self):
        """Non-admin users cannot use impersonation."""
        self.http_client.login(username="real-staff", password="testpass123")
        resp = self.http_client.post(f"/admin/users/{self.demo_user.pk}/impersonate/")
        self.assertEqual(resp.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class IsDemoImmutableTest(TestCase):
    """Test that is_demo field cannot be changed after creation."""

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, is_staff=True
        )

    def test_is_demo_not_in_user_edit_form_fields(self):
        """is_demo should not be editable via user edit form."""
        target = User.objects.create_user(
            username="target", password="testpass123", is_demo=False
        )
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(f"/admin/users/{target.pk}/")
        # The form should not include is_demo as an editable field
        # (it may be displayed but readonly)
        content = resp.content.decode()
        # Check there's no input field named is_demo
        self.assertNotIn('name="is_demo"', content)
