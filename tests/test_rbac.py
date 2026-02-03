"""Tests for RBAC middleware (program-scoped access control)."""
from django.test import TestCase, RequestFactory, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import ClientFile, ClientProgramEnrolment
from konote.middleware.program_access import ProgramAccessMiddleware
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


def dummy_response(request):
    """Simple view stand-in that returns 200."""
    from django.http import HttpResponse
    return HttpResponse("OK")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminOnlyRoutesTest(TestCase):
    """Admin-only URLs (/admin/*) should be blocked for non-admin users."""

    def setUp(self):
        enc_module._fernet = None
        self.factory = RequestFactory()
        self.middleware = ProgramAccessMiddleware(dummy_response)

        self.admin_user = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin_user.is_admin = True
        self.admin_user.save()

        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_can_access_admin_routes(self):
        request = self.factory.get("/admin/settings/")
        request.user = self.admin_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_non_admin_blocked_from_admin_routes(self):
        request = self.factory.get("/admin/settings/")
        request.user = self.staff_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_passes_through(self):
        """Unauthenticated requests are not checked (login page handles redirect)."""
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get("/admin/settings/")
        request.user = AnonymousUser()
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ClientAccessTest(TestCase):
    """Client URLs should enforce program-scoped access."""

    def setUp(self):
        enc_module._fernet = None
        self.factory = RequestFactory()
        self.middleware = ProgramAccessMiddleware(dummy_response)

        # Create users
        self.admin_user = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin_user.is_admin = True
        self.admin_user.save()

        self.staff_a = User.objects.create_user(
            username="staff_a", password="testpass123", display_name="Staff A"
        )
        self.staff_b = User.objects.create_user(
            username="staff_b", password="testpass123", display_name="Staff B"
        )

        # Create programs
        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")

        # Assign staff to programs
        UserProgramRole.objects.create(user=self.staff_a, program=self.program_a, role="staff")
        UserProgramRole.objects.create(user=self.staff_b, program=self.program_b, role="staff")

        # Create a client enrolled in Program A only
        self.client = ClientFile.objects.create()
        self.client.first_name = "Test"
        self.client.last_name = "Client"
        self.client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client, program=self.program_a
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_staff_with_matching_program_can_access_client(self):
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.staff_a
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_staff_without_matching_program_blocked(self):
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.staff_b
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_admin_without_program_role_blocked_from_client(self):
        """Admins without program roles cannot access client data."""
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.admin_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_admin_with_program_role_can_access_client(self):
        """Admins who also have a program role can access client data."""
        UserProgramRole.objects.create(
            user=self.admin_user, program=self.program_a, role="program_manager"
        )
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.admin_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_non_client_url_passes_through(self):
        """URLs that don't match client patterns should pass through."""
        request = self.factory.get("/programs/")
        request.user = self.staff_a
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
