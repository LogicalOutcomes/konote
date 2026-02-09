"""Session isolation tests for the participant portal.

Staff and participant sessions must be completely independent. A staff
login must not grant portal access, and a portal login must not grant
staff access. The two authentication systems use different session keys:

  - Staff: Django's built-in ``auth.login()`` / ``_auth_user_id``
  - Portal: ``_portal_participant_id`` (a UUID stored in the session)

Run with:
    python manage.py test apps.portal.tests.test_session_isolation
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile
from apps.portal.models import ParticipantUser
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-session-isolation",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class SessionIsolationTests(TestCase):
    """Verify that staff and portal sessions are fully isolated."""

    def setUp(self):
        # Reset Fernet singleton so override_settings takes effect
        enc_module._fernet = None

        # Create a staff user
        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="StaffPass123!",
            display_name="Staff User",
        )

        # Create a client file and participant user
        self.client_file = ClientFile.objects.create(
            record_id="ISO-001",
            status="active",
        )
        self.client_file.first_name = "Portal"
        self.client_file.last_name = "User"
        self.client_file.save()

        self.participant = ParticipantUser.objects.create_participant(
            email="participant@test.com",
            client_file=self.client_file,
            display_name="Portal User",
            password="PartPass123!",
        )

        # Enable the portal feature toggle
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def tearDown(self):
        enc_module._fernet = None

    # ------------------------------------------------------------------
    # Cross-boundary access
    # ------------------------------------------------------------------

    def test_staff_login_no_portal_access(self):
        """A staff login should NOT grant access to the portal dashboard.

        Logging in through the staff auth system sets ``_auth_user_id``
        in the session but should NOT set ``_portal_participant_id``.
        Accessing ``/my/`` should redirect to portal login (not dashboard).
        """
        # Log in as staff
        logged_in = self.client.login(username="staffuser", password="StaffPass123!")
        self.assertTrue(logged_in, "Staff login should succeed")

        # Try to access the portal dashboard
        response = self.client.get("/my/")

        # Should redirect to portal login (not show dashboard content)
        self.assertIn(response.status_code, [302, 303])
        self.assertIn("/my/login/", response.url)

        # Session should NOT contain portal participant ID
        self.assertNotIn("_portal_participant_id", self.client.session)

    def test_portal_login_no_staff_access(self):
        """A portal login should NOT grant access to staff-only pages.

        Setting ``_portal_participant_id`` in the session should NOT
        let the user access staff pages like ``/clients/``.
        """
        # Log in as participant (via session key)
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.id)
        session.save()

        # Try to access a staff-only page
        response = self.client.get("/clients/")

        # Should be denied access (redirect to staff login or 403)
        self.assertIn(
            response.status_code,
            [302, 303, 403],
            "Portal user should not have access to staff pages",
        )

        # If redirected, should go to staff login, NOT portal dashboard
        if response.status_code in [302, 303]:
            self.assertNotIn("/my/", response.url)

    def test_dual_login_separate_sessions(self):
        """Staff and portal sessions should coexist independently.

        When both a staff user and a portal participant are logged in
        within the same browser session (different session keys), each
        should only have access to their respective system.
        """
        # Log in as staff
        self.client.login(username="staffuser", password="StaffPass123!")

        # Also set the portal session key
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.id)
        session.save()

        # Staff user should still have staff access
        response = self.client.get("/clients/")
        # Staff access should work (200 for list, or whatever the normal response is)
        self.assertNotEqual(
            response.status_code,
            403,
            "Staff user should retain staff access when portal is also logged in",
        )

        # Portal participant should have portal access
        response = self.client.get("/my/")
        self.assertEqual(
            response.status_code,
            200,
            "Portal participant should have portal access when staff is also logged in",
        )

    def test_portal_session_key_different(self):
        """Portal uses ``_portal_participant_id``, not Django's ``_auth_user_id``.

        This is a fundamental design requirement. The portal session key
        must be distinct from Django's built-in auth session key to
        prevent any confusion between the two authentication systems.
        """
        from django.contrib.auth import SESSION_KEY as DJANGO_SESSION_KEY

        # The portal session key must be different from Django's
        portal_session_key = "_portal_participant_id"
        self.assertNotEqual(
            portal_session_key,
            DJANGO_SESSION_KEY,
            "Portal session key must differ from Django's auth session key",
        )

        # Log in as participant
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.id)
        session.save()

        # Verify the portal key is set but Django's auth key is NOT
        self.assertIn("_portal_participant_id", self.client.session)
        self.assertNotIn(
            DJANGO_SESSION_KEY,
            self.client.session,
            "Portal login should not set Django's auth session key",
        )
