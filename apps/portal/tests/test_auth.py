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
)
class PortalAuthTests(TestCase):
    """Test portal authentication flows."""

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

        # Create a participant user
        self.participant = ParticipantUser.objects.create_participant(
            email="test@example.com",
            client_file=self.client_file,
            display_name="Test Participant",
            password="TestPass123!",
        )

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

        # Session should contain the portal participant ID
        self.assertIn("_portal_participant_id", self.client.session)

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

        response = self.client.get("/my/logout/")

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
