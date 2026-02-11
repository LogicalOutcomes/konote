"""Tests for the expanded role system, invite registration, and demo mode."""
import uuid
from datetime import timedelta

from cryptography.fernet import Fernet
from django.test import TestCase, RequestFactory, override_settings
from django.utils import timezone

from apps.auth_app.decorators import minimum_role
from apps.auth_app.models import Invite, User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import Program, UserProgramRole
from konote.middleware.program_access import ProgramAccessMiddleware
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


def dummy_response(request):
    from django.http import HttpResponse
    return HttpResponse("OK")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RoleHierarchyTest(TestCase):
    """Test that the middleware assigns the correct role and the decorator enforces minimums."""

    def setUp(self):
        enc_module._fernet = None
        self.factory = RequestFactory()
        self.middleware = ProgramAccessMiddleware(dummy_response)
        self.program = Program.objects.create(name="Test Program")

        # Create users with different roles
        self.receptionist = User.objects.create_user(
            username="receptionist", password="testpass123", display_name="Front Desk"
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program, role="receptionist"
        )
        self.counsellor = User.objects.create_user(
            username="counsellor", password="testpass123", display_name="Direct Service"
        )
        UserProgramRole.objects.create(
            user=self.counsellor, program=self.program, role="staff"
        )
        self.manager = User.objects.create_user(
            username="manager", password="testpass123", display_name="Manager"
        )
        UserProgramRole.objects.create(
            user=self.manager, program=self.program, role="program_manager"
        )

        # Create client in program
        self.client = ClientFile.objects.create()
        self.client.first_name = "Test"
        self.client.last_name = "Client"
        self.client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client, program=self.program
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_receptionist_can_access_client(self):
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.receptionist
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_program_role, "receptionist")

    def test_counsellor_gets_staff_role(self):
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.counsellor
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_program_role, "staff")

    def test_manager_gets_program_manager_role(self):
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.manager
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_program_role, "program_manager")

    def test_minimum_role_blocks_receptionist_from_staff_view(self):
        """minimum_role('staff') should block front desk staff."""
        @minimum_role("staff")
        def staff_view(request):
            from django.http import HttpResponse
            return HttpResponse("OK")

        request = self.factory.get("/test/")
        request.user_program_role = "receptionist"
        response = staff_view(request)
        self.assertEqual(response.status_code, 403)

    def test_minimum_role_allows_staff(self):
        @minimum_role("staff")
        def staff_view(request):
            from django.http import HttpResponse
            return HttpResponse("OK")

        request = self.factory.get("/test/")
        request.user_program_role = "staff"
        response = staff_view(request)
        self.assertEqual(response.status_code, 200)

    def test_minimum_role_allows_manager_for_staff_view(self):
        @minimum_role("staff")
        def staff_view(request):
            from django.http import HttpResponse
            return HttpResponse("OK")

        request = self.factory.get("/test/")
        request.user_program_role = "program_manager"
        response = staff_view(request)
        self.assertEqual(response.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class InviteModelTest(TestCase):
    """Test Invite model properties."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin", is_admin=True,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_valid_invite(self):
        invite = Invite.objects.create(
            role="staff",
            created_by=self.admin,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.assertTrue(invite.is_valid)
        self.assertFalse(invite.is_expired)
        self.assertFalse(invite.is_used)

    def test_expired_invite(self):
        invite = Invite.objects.create(
            role="staff",
            created_by=self.admin,
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(invite.is_valid)
        self.assertTrue(invite.is_expired)

    def test_used_invite(self):
        user = User.objects.create_user(
            username="newuser", password="testpass123", display_name="New User"
        )
        invite = Invite.objects.create(
            role="staff",
            created_by=self.admin,
            expires_at=timezone.now() + timedelta(days=7),
            used_by=user,
            used_at=timezone.now(),
        )
        self.assertFalse(invite.is_valid)
        self.assertTrue(invite.is_used)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class InviteAcceptViewTest(TestCase):
    """Test the invite accept (registration) flow."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin", is_admin=True,
        )
        self.program = Program.objects.create(name="Test Program")
        self.invite = Invite.objects.create(
            role="staff",
            created_by=self.admin,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.invite.programs.add(self.program)

    def tearDown(self):
        enc_module._fernet = None

    def test_accept_creates_user_with_role(self):
        response = self.client.post(f"/auth/join/{self.invite.code}/", {
            "username": "newcounsellor",
            "display_name": "New Direct Service",
            "password": "securepass123",
            "password_confirm": "securepass123",
        })
        self.assertEqual(response.status_code, 302)  # Redirect to home

        user = User.objects.get(username="newcounsellor")
        self.assertEqual(user.display_name, "New Direct Service")
        self.assertFalse(user.is_admin)

        # Check program role
        role = UserProgramRole.objects.get(user=user)
        self.assertEqual(role.role, "staff")
        self.assertEqual(role.program, self.program)

        # Check invite is marked used
        self.invite.refresh_from_db()
        self.assertEqual(self.invite.used_by, user)
        self.assertIsNotNone(self.invite.used_at)

    def test_accept_expired_invite_shows_error(self):
        self.invite.expires_at = timezone.now() - timedelta(days=1)
        self.invite.save()

        response = self.client.get(f"/auth/join/{self.invite.code}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired")

    def test_accept_used_invite_shows_error(self):
        user = User.objects.create_user(
            username="existing", password="testpass123", display_name="Existing"
        )
        self.invite.used_by = user
        self.invite.used_at = timezone.now()
        self.invite.save()

        response = self.client.get(f"/auth/join/{self.invite.code}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already been used")

    def test_accept_admin_invite_creates_admin(self):
        admin_invite = Invite.objects.create(
            role="admin",
            created_by=self.admin,
            expires_at=timezone.now() + timedelta(days=7),
        )
        response = self.client.post(f"/auth/join/{admin_invite.code}/", {
            "username": "newadmin",
            "display_name": "New Admin",
            "password": "securepass123",
            "password_confirm": "securepass123",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newadmin")
        self.assertTrue(user.is_admin)

    def test_duplicate_username_rejected(self):
        User.objects.create_user(
            username="taken", password="testpass123", display_name="Taken"
        )
        response = self.client.post(f"/auth/join/{self.invite.code}/", {
            "username": "taken",
            "display_name": "New User",
            "password": "securepass123",
            "password_confirm": "securepass123",
        })
        self.assertEqual(response.status_code, 200)  # Re-renders form
        self.assertContains(response, "already taken")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=True)
class DemoLoginTest(TestCase):
    """Test demo login functionality."""

    def setUp(self):
        enc_module._fernet = None
        self.demo_user = User.objects.create_user(
            username="demo-worker-1", password="demo1234", display_name="Casey Worker"
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_demo_login_works_when_enabled(self):
        response = self.client.get("/auth/demo-login/worker-1/")
        self.assertEqual(response.status_code, 302)  # Redirect to home

    def test_demo_login_invalid_role_404(self):
        response = self.client.get("/auth/demo-login/superuser/")
        self.assertEqual(response.status_code, 404)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=False)
class DemoLoginDisabledTest(TestCase):
    """Demo login should 404 when DEMO_MODE is off."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_demo_login_404_when_disabled(self):
        response = self.client.get("/auth/demo-login/worker-1/")
        self.assertEqual(response.status_code, 404)
