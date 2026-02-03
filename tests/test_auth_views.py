"""Tests for authentication views — login, logout, invite acceptance, permission checks."""
from datetime import timedelta

from cryptography.fernet import Fernet
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from apps.auth_app.models import Invite, User
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local")
class LoginViewTest(TestCase):
    """Test local username/password login."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.user = User.objects.create_user(
            username="testuser", password="goodpass123", display_name="Test User"
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_login_page_renders(self):
        resp = self.http.get("/auth/login/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "username")

    def test_valid_login_redirects_to_home(self):
        resp = self.http.post("/auth/login/", {
            "username": "testuser",
            "password": "goodpass123",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")

    def test_invalid_password_shows_error(self):
        resp = self.http.post("/auth/login/", {
            "username": "testuser",
            "password": "wrongpass",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid username or password")

    def test_nonexistent_user_shows_error(self):
        resp = self.http.post("/auth/login/", {
            "username": "nobody",
            "password": "whatever",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid username or password")

    def test_empty_fields_shows_error(self):
        resp = self.http.post("/auth/login/", {
            "username": "",
            "password": "",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please enter both username and password")

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        resp = self.http.post("/auth/login/", {
            "username": "testuser",
            "password": "goodpass123",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid username or password")

    def test_authenticated_user_redirected_from_login_page(self):
        self.http.login(username="testuser", password="goodpass123")
        resp = self.http.get("/auth/login/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")

    def test_login_updates_last_login_at(self):
        self.http.post("/auth/login/", {
            "username": "testuser",
            "password": "goodpass123",
        })
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login_at)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LogoutViewTest(TestCase):
    """Test logout functionality."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.user = User.objects.create_user(
            username="testuser", password="goodpass123", display_name="Test User"
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_logout_redirects_to_login(self):
        self.http.login(username="testuser", password="goodpass123")
        resp = self.http.get("/auth/logout/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_logout_clears_session(self):
        self.http.login(username="testuser", password="goodpass123")
        self.http.get("/auth/logout/")
        # Accessing a protected page should redirect to login
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)

    def test_unauthenticated_logout_redirects_to_login(self):
        resp = self.http.get("/auth/logout/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class InviteAcceptViewTest(TestCase):
    """Test invite-based registration flow."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
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

    def test_valid_invite_renders_form(self):
        resp = self.http.get(f"/auth/join/{self.invite.code}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "username")

    def test_accept_creates_user_and_assigns_role(self):
        resp = self.http.post(f"/auth/join/{self.invite.code}/", {
            "username": "newuser",
            "display_name": "New User",
            "password": "securepass123",
            "password_confirm": "securepass123",
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="newuser")
        self.assertFalse(user.is_admin)
        role = UserProgramRole.objects.get(user=user)
        self.assertEqual(role.role, "staff")
        self.assertEqual(role.program, self.program)

    def test_expired_invite_shows_error(self):
        self.invite.expires_at = timezone.now() - timedelta(days=1)
        self.invite.save()
        resp = self.http.get(f"/auth/join/{self.invite.code}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "expired")

    def test_used_invite_shows_error(self):
        user = User.objects.create_user(
            username="existing", password="testpass123", display_name="Existing"
        )
        self.invite.used_by = user
        self.invite.used_at = timezone.now()
        self.invite.save()
        resp = self.http.get(f"/auth/join/{self.invite.code}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "already been used")

    def test_password_mismatch_rejected(self):
        resp = self.http.post(f"/auth/join/{self.invite.code}/", {
            "username": "newuser",
            "display_name": "New User",
            "password": "securepass123",
            "password_confirm": "differentpass",
        })
        self.assertEqual(resp.status_code, 200)  # Re-renders form
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_duplicate_username_rejected(self):
        User.objects.create_user(
            username="taken", password="testpass123", display_name="Taken"
        )
        resp = self.http.post(f"/auth/join/{self.invite.code}/", {
            "username": "taken",
            "display_name": "New User",
            "password": "securepass123",
            "password_confirm": "securepass123",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "already taken")

    def test_admin_invite_creates_admin_user(self):
        admin_invite = Invite.objects.create(
            role="admin",
            created_by=self.admin,
            expires_at=timezone.now() + timedelta(days=7),
        )
        resp = self.http.post(f"/auth/join/{admin_invite.code}/", {
            "username": "newadmin",
            "display_name": "New Admin",
            "password": "securepass123",
            "password_confirm": "securepass123",
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="newadmin")
        self.assertTrue(user.is_admin)

    def test_invalid_invite_code_404(self):
        import uuid
        resp = self.http.get(f"/auth/join/{uuid.uuid4()}/")
        self.assertIn(resp.status_code, [404, 200])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminRoutePermissionTest(TestCase):
    """Test that admin-only routes block non-admin users."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.admin = User.objects.create_user(
            username="admin", password="pass", display_name="Admin", is_admin=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="pass", display_name="Staff"
        )
        self.program = Program.objects.create(name="Test")
        UserProgramRole.objects.create(user=self.staff, program=self.program, role="staff")

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_can_access_user_list(self):
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/auth/users/")
        self.assertEqual(resp.status_code, 200)

    def test_staff_cannot_access_user_list(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/auth/users/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_invite_list(self):
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/auth/invites/")
        self.assertEqual(resp.status_code, 200)

    def test_staff_cannot_access_invite_list(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/auth/invites/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_settings(self):
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/admin/settings/")
        self.assertEqual(resp.status_code, 200)

    def test_staff_blocked_from_admin_settings(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/admin/settings/")
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_redirected_from_admin_routes(self):
        resp = self.http.get("/auth/users/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)
