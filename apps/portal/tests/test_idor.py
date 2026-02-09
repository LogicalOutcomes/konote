"""IDOR (Insecure Direct Object Reference) tests for the participant portal.

This is the most critical security test suite. Every test verifies that
Participant A cannot access, view, or modify Participant B's data --
even by manipulating URLs or form parameters.

The portal MUST NEVER accept a ``client_id`` parameter in URLs or POST
data. The authenticated participant's identity determines which data is
returned, and attempts to reference another participant's objects MUST
return 404 (not 403, to avoid information disclosure).

Run with:
    python manage.py test apps.portal.tests.test_idor
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.clients.models import ClientFile
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget
from apps.portal.models import (
    CorrectionRequest,
    ParticipantJournalEntry,
    ParticipantMessage,
    ParticipantUser,
)
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-idor",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class PortalIDORTests(TestCase):
    """Verify that one participant cannot access another's data."""

    def setUp(self):
        # Reset Fernet singleton so override_settings takes effect
        enc_module._fernet = None

        # --- Client A ---
        self.client_a = ClientFile.objects.create(
            record_id="IDOR-A",
            status="active",
        )
        self.client_a.first_name = "Alice"
        self.client_a.last_name = "Alpha"
        self.client_a.save()

        self.participant_a = ParticipantUser.objects.create_participant(
            email="alice@example.com",
            client_file=self.client_a,
            display_name="Alice",
            password="AlicePass123!",
        )

        # Plans for Client A
        self.section_a = PlanSection.objects.create(
            client_file=self.client_a,
            name="Section A",
            status="default",
        )
        self.target_a = PlanTarget.objects.create(
            plan_section=self.section_a,
            client_file=self.client_a,
            status="default",
        )
        self.target_a.name = "Goal A"
        self.target_a.client_goal = "My own goal"
        self.target_a.save()

        # --- Client B ---
        self.client_b = ClientFile.objects.create(
            record_id="IDOR-B",
            status="active",
        )
        self.client_b.first_name = "Bob"
        self.client_b.last_name = "Beta"
        self.client_b.save()

        self.participant_b = ParticipantUser.objects.create_participant(
            email="bob@example.com",
            client_file=self.client_b,
            display_name="Bob",
            password="BobPass123!",
        )

        # Plans for Client B
        self.section_b = PlanSection.objects.create(
            client_file=self.client_b,
            name="Section B",
            status="default",
        )
        self.target_b = PlanTarget.objects.create(
            plan_section=self.section_b,
            client_file=self.client_b,
            status="default",
        )
        self.target_b.name = "Goal B"
        self.target_b.client_goal = "Bob's private goal"
        self.target_b.save()

        # Journal entries for both
        self.journal_a = ParticipantJournalEntry.objects.create(
            participant_user=self.participant_a,
            client_file=self.client_a,
        )
        self.journal_a.content = "Alice's private journal"
        self.journal_a.save()

        self.journal_b = ParticipantJournalEntry.objects.create(
            participant_user=self.participant_b,
            client_file=self.client_b,
        )
        self.journal_b.content = "Bob's private journal"
        self.journal_b.save()

        # Messages for both
        self.message_a = ParticipantMessage.objects.create(
            participant_user=self.participant_a,
            client_file=self.client_a,
            message_type="general",
        )
        self.message_a.content = "Alice's message"
        self.message_a.save()

        self.message_b = ParticipantMessage.objects.create(
            participant_user=self.participant_b,
            client_file=self.client_b,
            message_type="general",
        )
        self.message_b.content = "Bob's message"
        self.message_b.save()

        # Enable the portal feature toggle
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

        # Log in as Participant A for all tests
        self._login_as_participant(self.participant_a)

    def tearDown(self):
        enc_module._fernet = None

    def _login_as_participant(self, participant):
        """Set the portal session key to simulate a logged-in participant."""
        session = self.client.session
        session["_portal_participant_id"] = str(participant.id)
        session.save()

    # ------------------------------------------------------------------
    # Goal / target access
    # ------------------------------------------------------------------

    def test_idor_goal_detail(self):
        """Participant A cannot view Participant B's goal detail.

        The response MUST be 404 (not 200 or 403) to avoid disclosing
        whether the object exists at all.
        """
        response = self.client.get(f"/my/goals/{self.target_b.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_idor_goals_only_own(self):
        """The goals list should only show Participant A's targets."""
        response = self.client.get("/my/goals/")
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Alice's goal should be visible
        self.assertIn("Goal A", content)

        # Bob's goal must NOT be visible
        self.assertNotIn("Goal B", content)
        self.assertNotIn("Bob", content)

    # ------------------------------------------------------------------
    # Progress / metrics
    # ------------------------------------------------------------------

    def test_idor_progress_only_own(self):
        """Progress page should only show Participant A's metrics."""
        response = self.client.get("/my/progress/")
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Bob's data must not appear
        self.assertNotIn("Bob", content)
        self.assertNotIn("Goal B", content)

    # ------------------------------------------------------------------
    # My Words (reflections)
    # ------------------------------------------------------------------

    def test_idor_my_words_only_own(self):
        """My Words page should only show Participant A's reflections."""
        response = self.client.get("/my/my-words/")
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        self.assertNotIn("Bob", content)

    # ------------------------------------------------------------------
    # Correction requests
    # ------------------------------------------------------------------

    def test_idor_correction_other_client(self):
        """Correction request targeting Participant B's object should be rejected.

        The view must verify the referenced object_id belongs to the
        authenticated participant's client file. If not, it should return
        404 or 400 (never process the request).
        """
        response = self.client.post("/my/correction/new/", {
            "data_type": "goal",
            "object_id": self.target_b.pk,
            "description": "I want to change this",
        })

        # Should be rejected (404, 400, or 403 -- not 200 or 302 to success)
        self.assertIn(response.status_code, [400, 403, 404])

        # Verify no correction was created for Bob's target
        self.assertFalse(
            CorrectionRequest.objects.filter(
                object_id=self.target_b.pk,
                participant_user=self.participant_a,
            ).exists(),
            "A correction request for another participant's object must not be created.",
        )

    # ------------------------------------------------------------------
    # Journal entries
    # ------------------------------------------------------------------

    def test_idor_journal_other_participant(self):
        """Participant A should not see Participant B's journal entries."""
        response = self.client.get("/my/journal/")
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        self.assertNotIn("Bob's private journal", content)

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def test_idor_message_other_participant(self):
        """Participant A should not see Participant B's messages."""
        response = self.client.get("/my/message/")
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        self.assertNotIn("Bob's message", content)

    # ------------------------------------------------------------------
    # URL parameter injection
    # ------------------------------------------------------------------

    def test_no_client_id_in_urls(self):
        """No portal URL should accept a client_id parameter.

        The portal determines the client from the authenticated session --
        never from a URL parameter. If client_id is passed as a query
        parameter, it must be ignored (the response should still only
        show Participant A's data) or return an error.
        """
        # Try appending client_id as a query parameter to the dashboard
        response = self.client.get(f"/my/?client_id={self.client_b.pk}")
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        # Bob's name or data must not appear
        self.assertNotIn("Bob", content)
        self.assertNotIn("Beta", content)

        # Try the goals page with client_id
        response = self.client.get(f"/my/goals/?client_id={self.client_b.pk}")
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        self.assertNotIn("Goal B", content)
        self.assertNotIn("Bob", content)
