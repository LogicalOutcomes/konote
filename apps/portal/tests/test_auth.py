"""Authentication tests for the participant portal.

Verifies login, logout, lockout, feature-toggle gating, and
unauthenticated redirect behaviour. These tests exercise the
portal-specific session key (``_portal_participant_id``), which is
entirely separate from Django's built-in ``auth.login()`` mechanism.

Run with:
    python manage.py test apps.portal.tests.test_auth
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.clients.models import ClientFile
from apps.portal.models import ParticipantUser
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-portal-auth",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PortalAuthTests(TestCase):
    """Test portal authentication flows."""

    databases = {"default", "audit"}

    def setUp(self):
        # Reset Fernet singleton so override_settings takes effect
        enc_module._fernet = None

        # Create a client file for the participant
        self.client_file = ClientFile.objects.create(
            record_id="TEST-001",
            status="active",
        )
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Participant"
        self.client_file.save()

        # Create a participant user (MFA exempt for login tests)
        self.participant = ParticipantUser.objects.create_participant(
            email="test@example.com",
            client_file=self.client_file,
            display_name="Test Participant",
            password="TestPass123!",
        )
        self.participant.mfa_method = "exempt"
        self.participant.save()

        # Enable the portal feature toggle
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def tearDown(self):
        enc_module._fernet = None

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def test_login_success(self):
        """Valid credentials should log the participant in and redirect to dashboard."""
        response = self.client.post("/my/login/", {
            "email": "test@example.com",
            "password": "TestPass123!",
        })

        # Should redirect to the dashboard
        self.assertIn(response.status_code, [302, 303])
        self.assertIn("/my/", response.url)

        # Follow the redirect manually so the test client picks up
        # the new session cookie (login calls session.cycle_key)
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)

        # Verify the participant is actually logged in by confirming
        # the dashboard rendered (only visible to authenticated users)
        self.assertContains(response, "Hi,")

    def test_login_wrong_password(self):
        """Wrong password should not log in and should increment failed_login_count."""
        response = self.client.post("/my/login/", {
            "email": "test@example.com",
            "password": "WrongPassword!",
        })

        # Should stay on login page (200) or redirect back to login
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertIn("login", response.url)

        # Session should NOT contain the portal participant ID
        self.assertNotIn("_portal_participant_id", self.client.session)

        # Failed login count should be incremented
        self.participant.refresh_from_db()
        self.assertGreaterEqual(self.participant.failed_login_count, 1)

    def test_login_inactive_account(self):
        """Inactive account should be denied login."""
        self.participant.is_active = False
        self.participant.save()

        response = self.client.post("/my/login/", {
            "email": "test@example.com",
            "password": "TestPass123!",
        })

        # Should not redirect to dashboard
        self.assertNotIn("_portal_participant_id", self.client.session)

    def test_account_lockout(self):
        """Five failed attempts should lock the account; correct password is then denied."""
        for i in range(5):
            self.client.post("/my/login/", {
                "email": "test@example.com",
                "password": f"WrongPassword{i}",
            })

        # Refresh and verify lockout
        self.participant.refresh_from_db()
        self.assertGreaterEqual(self.participant.failed_login_count, 5)

        # Now try with the correct password -- should still be denied
        response = self.client.post("/my/login/", {
            "email": "test@example.com",
            "password": "TestPass123!",
        })

        self.assertNotIn("_portal_participant_id", self.client.session)

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def test_logout(self):
        """Logout should clear the session and redirect to login."""
        # Log in first
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.id)
        session.save()

        # Logout requires POST (enforced by @require_POST)
        response = self.client.post("/my/logout/")

        # Should redirect to login
        self.assertIn(response.status_code, [302, 303])

        # Session should no longer contain participant ID
        self.assertNotIn("_portal_participant_id", self.client.session)

    def test_emergency_logout(self):
        """Emergency logout should return 204 and clear the session immediately."""
        # Log in first
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.id)
        session.save()

        response = self.client.post("/my/emergency-logout/")

        # Should return 204 No Content (no redirect, no page to see)
        self.assertEqual(response.status_code, 204)

        # Session should be cleared
        self.assertNotIn("_portal_participant_id", self.client.session)

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------

    def test_unauthenticated_redirect(self):
        """Unauthenticated access to dashboard should redirect to login."""
        response = self.client.get("/my/")

        self.assertIn(response.status_code, [302, 303])
        self.assertIn("/my/login/", response.url)

    def test_feature_toggle_disabled(self):
        """When the portal feature is disabled, login page should return 404."""
        toggle = FeatureToggle.objects.get(feature_key="participant_portal")
        toggle.is_enabled = False
        toggle.save()

        response = self.client.get("/my/login/")

        self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    def test_password_reset_request_sends_code(self):
        """POST to reset request should store hashed token and return submitted=True."""
        response = self.client.post("/my/password/reset/", {
            "email": "test@example.com",
        })
        self.assertEqual(response.status_code, 200)
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.password_reset_token_hash)
        self.assertIsNotNone(self.participant.password_reset_expires)

    def test_password_reset_request_unknown_email_no_leak(self):
        """Unknown email should show same success page (no enumeration)."""
        response = self.client.post("/my/password/reset/", {
            "email": "nonexistent@example.com",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "code")  # Shows "we sent a code" message

    def test_password_reset_confirm_valid_code(self):
        """Valid reset code should allow setting a new password."""
        # First request a reset to generate a token
        self.client.post("/my/password/reset/", {"email": "test@example.com"})
        self.participant.refresh_from_db()
        # Retrieve the plaintext code from the test mail outbox
        from django.core import mail
        self.assertEqual(len(mail.outbox), 1)
        # Extract the 6-digit code from the email body
        import re
        code_match = re.search(r"\b(\d{6})\b", mail.outbox[0].body)
        self.assertIsNotNone(code_match)
        code = code_match.group(1)

        response = self.client.post("/my/password/reset/confirm/", {
            "email": "test@example.com",
            "code": code,
            "new_password": "NewSecurePass456!",
            "confirm_password": "NewSecurePass456!",
        })
        self.assertEqual(response.status_code, 200)
        # Verify new password works
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.check_password("NewSecurePass456!"))

    def test_password_reset_expired_code(self):
        """Expired reset code should fail."""
        self.client.post("/my/password/reset/", {"email": "test@example.com"})
        self.participant.refresh_from_db()
        # Expire the token manually
        from django.utils import timezone
        from datetime import timedelta
        self.participant.password_reset_expires = timezone.now() - timedelta(minutes=1)
        self.participant.save(update_fields=["password_reset_expires"])
        response = self.client.post("/my/password/reset/confirm/", {
            "email": "test@example.com",
            "code": "123456",
            "new_password": "NewSecurePass456!",
            "confirm_password": "NewSecurePass456!",
        })
        self.assertContains(response, "expired")

    def test_password_reset_rate_limit(self):
        """More than 3 reset requests in an hour should be rejected."""
        for _ in range(3):
            self.client.post("/my/password/reset/", {"email": "test@example.com"})
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.password_reset_request_count, 3)
        response = self.client.post("/my/password/reset/", {"email": "test@example.com"})
        self.assertEqual(response.status_code, 200)
        # Should still show "success" but NOT send a 4th email
        from django.core import mail
        self.assertEqual(len(mail.outbox), 3)
