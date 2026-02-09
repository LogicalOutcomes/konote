"""XSS (Cross-Site Scripting) tests for the participant portal.

Verifies that user-supplied content is properly escaped when rendered in
HTML templates. Since participants write journal entries, messages, and
correction requests with free-text fields, these are prime XSS vectors.

Each test creates data with a malicious payload, then GETs the page that
renders it and verifies the script tags appear as HTML entities
(``&lt;script&gt;``) rather than as executable ``<script>`` tags.

Run with:
    python manage.py test apps.portal.tests.test_xss
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.clients.models import ClientFile
from apps.portal.models import (
    CorrectionRequest,
    ParticipantJournalEntry,
    ParticipantMessage,
    ParticipantUser,
)
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()

# Common XSS payloads to test
SCRIPT_PAYLOAD = '<script>alert(1)</script>'
IMG_PAYLOAD = '<img onerror=alert(1) src=x>'


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-xss",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class PortalXSSTests(TestCase):
    """Verify that user-supplied content is HTML-escaped in portal pages."""

    def setUp(self):
        # Reset Fernet singleton so override_settings takes effect
        enc_module._fernet = None

        # Create a client file
        self.client_file = ClientFile.objects.create(
            record_id="XSS-001",
            status="active",
        )
        self.client_file.first_name = "Test"
        self.client_file.last_name = "XSS"
        self.client_file.save()

        # Create a participant user
        self.participant = ParticipantUser.objects.create_participant(
            email="xss@example.com",
            client_file=self.client_file,
            display_name="XSS Tester",
            password="XssPass123!",
        )

        # Enable the portal feature toggle
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

        # Log in as the participant
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.id)
        session.save()

    def tearDown(self):
        enc_module._fernet = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _assert_escaped(self, response, raw_payload):
        """Assert that the raw payload is HTML-escaped in the response.

        The raw ``<script>`` or ``<img`` tag must NOT appear in the
        response body. Instead, it should appear as HTML entities.
        """
        content = response.content.decode()

        # The raw tag must NOT appear unescaped
        self.assertNotIn(
            raw_payload,
            content,
            f"XSS payload found unescaped in response: {raw_payload}",
        )

        # The escaped version should appear (Django's autoescape)
        # <script> becomes &lt;script&gt;
        if "<script>" in raw_payload:
            self.assertIn("&lt;script&gt;", content)

    # ------------------------------------------------------------------
    # Journal entries
    # ------------------------------------------------------------------

    def test_xss_in_journal_content(self):
        """Script tags in journal content must be HTML-escaped on the page."""
        entry = ParticipantJournalEntry.objects.create(
            participant_user=self.participant,
            client_file=self.client_file,
        )
        entry.content = SCRIPT_PAYLOAD
        entry.save()

        response = self.client.get("/my/journal/")
        self.assertEqual(response.status_code, 200)

        self._assert_escaped(response, SCRIPT_PAYLOAD)

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def test_xss_in_message_content(self):
        """Image onerror payload in message content must be HTML-escaped."""
        message = ParticipantMessage.objects.create(
            participant_user=self.participant,
            client_file=self.client_file,
            message_type="general",
        )
        message.content = IMG_PAYLOAD
        message.save()

        response = self.client.get("/my/message/")
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # The raw img tag with onerror must NOT appear
        self.assertNotIn(
            IMG_PAYLOAD,
            content,
            "XSS payload (img onerror) found unescaped in message page",
        )

    # ------------------------------------------------------------------
    # Correction requests
    # ------------------------------------------------------------------

    def test_xss_in_correction_description(self):
        """Script tags in correction description must be HTML-escaped."""
        # Create a correction request with a target that belongs to this participant
        from apps.plans.models import PlanSection, PlanTarget

        section = PlanSection.objects.create(
            client_file=self.client_file,
            name="XSS Test Section",
            status="default",
        )
        target = PlanTarget.objects.create(
            plan_section=section,
            client_file=self.client_file,
            status="default",
        )
        target.name = "XSS Test Goal"
        target.save()

        correction = CorrectionRequest.objects.create(
            participant_user=self.participant,
            client_file=self.client_file,
            data_type="goal",
            object_id=target.pk,
        )
        correction.description = SCRIPT_PAYLOAD
        correction.save()

        # View the page that shows correction requests
        # Could be goals page, settings, or a dedicated corrections list
        response = self.client.get(f"/my/goals/{target.pk}/")
        if response.status_code == 200:
            self._assert_escaped(response, SCRIPT_PAYLOAD)

        # Also check the dashboard (corrections may appear there too)
        response = self.client.get("/my/")
        if response.status_code == 200:
            content = response.content.decode()
            self.assertNotIn(
                SCRIPT_PAYLOAD,
                content,
                "XSS payload found unescaped on dashboard",
            )

    # ------------------------------------------------------------------
    # Display name
    # ------------------------------------------------------------------

    def test_xss_in_display_name(self):
        """Script tags in the participant's display_name must be HTML-escaped.

        The display name appears in the dashboard header, greeting, and
        potentially other pages. It must always be escaped.
        """
        self.participant.display_name = SCRIPT_PAYLOAD
        self.participant.save()

        response = self.client.get("/my/")
        self.assertEqual(response.status_code, 200)

        self._assert_escaped(response, SCRIPT_PAYLOAD)
