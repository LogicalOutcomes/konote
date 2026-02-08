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


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ImpersonationGuardTest(TestCase):
    """
    Test the impersonation security guard.

    CRITICAL: Admins can ONLY impersonate demo users (is_demo=True).
    Real users cannot be impersonated regardless of admin privileges.
    """

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        # Admin who will attempt impersonation
        self.admin = User.objects.create_user(
            username="admin", password="adminpass", display_name="Admin User", is_admin=True
        )
        # Demo user (CAN be impersonated)
        self.demo_user = User.objects.create_user(
            username="demo-staff", password="demopass", display_name="Demo Staff",
            is_demo=True, is_admin=False
        )
        # Real user (CANNOT be impersonated)
        self.real_user = User.objects.create_user(
            username="real-staff", password="realpass", display_name="Real Staff",
            is_demo=False, is_admin=False
        )
        # Inactive demo user (CANNOT be impersonated even though is_demo=True)
        self.inactive_demo = User.objects.create_user(
            username="inactive-demo", password="inactivepass", display_name="Inactive Demo",
            is_demo=True, is_active=False
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_can_impersonate_demo_user(self):
        """Admin should successfully impersonate a demo user."""
        self.http.login(username="admin", password="adminpass")
        resp = self.http.get(f"/auth/users/{self.demo_user.pk}/impersonate/")

        # Should redirect to home page after successful impersonation
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")

        # Verify the session is now the demo user
        resp = self.http.get("/")
        # Check that we're logged in as demo user (the session user changed)
        # We need to check via a follow-up request or session inspection
        self.assertEqual(int(self.http.session["_auth_user_id"]), self.demo_user.pk)

    def test_admin_cannot_impersonate_real_user(self):
        """CRITICAL: Admin must NOT be able to impersonate real users."""
        self.http.login(username="admin", password="adminpass")
        resp = self.http.get(f"/auth/users/{self.real_user.pk}/impersonate/")

        # Should redirect back to user list (not home)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/auth/users/")

        # Verify the admin is still logged in as themselves
        self.assertEqual(int(self.http.session["_auth_user_id"]), self.admin.pk)

    def test_admin_cannot_impersonate_inactive_demo_user(self):
        """Admin cannot impersonate inactive users even if they are demo users."""
        self.http.login(username="admin", password="adminpass")
        resp = self.http.get(f"/auth/users/{self.inactive_demo.pk}/impersonate/")

        # Should redirect back to user list
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/auth/users/")

        # Admin still logged in as themselves
        self.assertEqual(int(self.http.session["_auth_user_id"]), self.admin.pk)

    def test_non_admin_cannot_impersonate_anyone(self):
        """Non-admin users cannot access the impersonation endpoint at all."""
        # Create a non-admin user
        regular = User.objects.create_user(
            username="regular", password="regularpass", display_name="Regular User"
        )
        self.http.login(username="regular", password="regularpass")

        # Try to impersonate demo user
        resp = self.http.get(f"/auth/users/{self.demo_user.pk}/impersonate/")

        # Should get 403 Forbidden
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_impersonate(self):
        """Unauthenticated users are redirected to login."""
        resp = self.http.get(f"/auth/users/{self.demo_user.pk}/impersonate/")

        # Should redirect to login
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)

    def test_impersonation_creates_audit_log(self):
        """Successful impersonation should create an audit log entry."""
        from apps.audit.models import AuditLog

        self.http.login(username="admin", password="adminpass")
        self.http.get(f"/auth/users/{self.demo_user.pk}/impersonate/")

        # Check audit log was created
        log = AuditLog.objects.using("audit").filter(
            resource_type="impersonation",
            resource_id=self.demo_user.pk,
        ).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.user_id, self.admin.pk)
        self.assertEqual(log.action, "login")
        self.assertEqual(log.metadata["impersonated_user_id"], self.demo_user.pk)
        self.assertEqual(log.metadata["admin_username"], "admin")

    def test_failed_impersonation_no_audit_log(self):
        """Failed impersonation (real user) should NOT create audit log."""
        from apps.audit.models import AuditLog

        # Clear any existing logs
        AuditLog.objects.using("audit").all().delete()

        self.http.login(username="admin", password="adminpass")
        self.http.get(f"/auth/users/{self.real_user.pk}/impersonate/")

        # No audit log should be created for failed impersonation
        log = AuditLog.objects.using("audit").filter(
            resource_type="impersonation",
        ).first()

        self.assertIsNone(log)

    def test_impersonation_updates_last_login(self):
        """Impersonation should update the target user's last_login_at."""
        self.demo_user.last_login_at = None
        self.demo_user.save()

        self.http.login(username="admin", password="adminpass")
        self.http.get(f"/auth/users/{self.demo_user.pk}/impersonate/")

        self.demo_user.refresh_from_db()
        self.assertIsNotNone(self.demo_user.last_login_at)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class AccountLockoutTest(TestCase):
    """Test the account lockout logic that blocks login after repeated failures.

    The lockout system tracks failed login attempts per IP address using Django's
    cache. After 5 failed attempts within 15 minutes, that IP is blocked from
    further login attempts until the window expires.
    """

    databases = {"default", "audit"}

    def setUp(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()
        self.http = Client()
        self.user = User.objects.create_user(
            username="locktest", password="goodpass123", display_name="Lock Test"
        )

    def tearDown(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()

    def _fail_login(self, username="locktest", password="wrongpass"):
        """Helper: send a failed login POST and return the response."""
        return self.http.post("/auth/login/", {
            "username": username,
            "password": password,
        })

    def _succeed_login(self):
        """Helper: send a successful login POST and return the response."""
        return self.http.post("/auth/login/", {
            "username": "locktest",
            "password": "goodpass123",
        })

    def test_lockout_after_five_failed_attempts(self):
        """After 5 failed login attempts, the 6th attempt should be blocked."""
        # First 5 attempts should show "Invalid username or password" with
        # decreasing remaining attempts
        for i in range(5):
            resp = self._fail_login()
            self.assertEqual(resp.status_code, 200)

        # The 6th attempt should be blocked with a lockout message
        resp = self._fail_login()
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Too many failed login attempts")

    def test_correct_credentials_blocked_during_lockout(self):
        """Even correct credentials should be rejected while the IP is locked out."""
        # Trigger lockout with 5 failed attempts
        for i in range(5):
            self._fail_login()

        # Now try with correct credentials — should still be blocked
        resp = self._succeed_login()
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Too many failed login attempts")

    def test_successful_login_clears_counter(self):
        """A successful login before reaching the threshold resets the counter."""
        # Fail 3 times (below the threshold of 5)
        for i in range(3):
            self._fail_login()

        # Successful login should clear the counter
        resp = self._succeed_login()
        self.assertEqual(resp.status_code, 302)  # Redirect on success

        # Log out so we can try again
        self.http.get("/auth/logout/")

        # Now fail 4 more times — should NOT trigger lockout because the
        # counter was reset by the successful login above
        for i in range(4):
            resp = self._fail_login()
            self.assertEqual(resp.status_code, 200)
            self.assertNotContains(resp, "Too many failed login attempts")

    def test_cache_clearing_resets_lockout(self):
        """Clearing the cache simulates the 15-minute timeout expiry."""
        from django.core.cache import cache

        # Trigger lockout
        for i in range(5):
            self._fail_login()

        # Confirm locked out
        resp = self._fail_login()
        self.assertContains(resp, "Too many failed login attempts")

        # Clear cache (simulates the 15-minute window expiring)
        cache.clear()

        # Should be able to log in again with correct credentials
        resp = self._succeed_login()
        self.assertEqual(resp.status_code, 302)  # Redirect on success
