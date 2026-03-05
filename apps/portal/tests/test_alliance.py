"""Tests for portal alliance rating (PORTAL-ALLIANCE1).

Run with:
    pytest apps/portal/tests/test_alliance.py -v
"""
from datetime import timedelta

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile
from apps.notes.models import ProgressNote
from apps.portal.models import ParticipantUser, PortalAllianceRequest
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-alliance",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class TestPortalAllianceRating(TestCase):
    """Tests for the portal alliance rating flow."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.staff_user = User.objects.create_user(
            username="alliancestaff",
            password="staffpass123",
            display_name="Staff User",
        )

        self.client_file = ClientFile.objects.create(
            record_id="ALLIANCE-001", status="active",
        )
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Participant"
        self.client_file.save()

        self.participant = ParticipantUser.objects.create_participant(
            email="alliance@example.com",
            client_file=self.client_file,
            display_name="Test P",
            password="TestPass123!",
        )
        self.participant.mfa_method = "exempt"
        self.participant.save()

        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

        # Create a progress note without alliance rating
        self.note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="full",
            author=self.staff_user,
            interaction_type="session",
        )

        # Create a pending alliance request
        self.alliance_req = PortalAllianceRequest.objects.create(
            progress_note=self.note,
            client_file=self.client_file,
            prompt_index=0,
            expires_at=timezone.now() + timedelta(days=7),
        )

    def _login_portal(self):
        """Log in to the portal session."""
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.pk)
        session.save()

    def test_alliance_form_renders(self):
        """GET the alliance rating page shows the form."""
        self._login_portal()
        url = f"/my/alliance/{self.alliance_req.pk}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How well are we working together?")

    def test_submit_rating(self):
        """POST a valid rating completes the request."""
        self._login_portal()
        url = f"/my/alliance/{self.alliance_req.pk}/"
        response = self.client.post(url, {"rating": "4"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thank you")

        self.alliance_req.refresh_from_db()
        self.assertEqual(self.alliance_req.status, "completed")
        self.assertEqual(self.alliance_req.rating, 4)
        self.assertIsNotNone(self.alliance_req.completed_at)

        # Rating should also be saved on the note
        self.note.refresh_from_db()
        self.assertEqual(self.note.alliance_rating, 4)
        self.assertEqual(self.note.alliance_rater, "client")

    def test_expired_request_shows_expired_page(self):
        """Expired requests show a friendly message."""
        self._login_portal()
        self.alliance_req.expires_at = timezone.now() - timedelta(hours=1)
        self.alliance_req.save(update_fields=["expires_at"])

        url = f"/my/alliance/{self.alliance_req.pk}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired")

    def test_already_completed_shows_thank_you(self):
        """Already completed requests show thank you."""
        self._login_portal()
        self.alliance_req.status = "completed"
        self.alliance_req.rating = 3
        self.alliance_req.completed_at = timezone.now()
        self.alliance_req.save()

        url = f"/my/alliance/{self.alliance_req.pk}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thank you")

    def test_other_participant_cannot_access(self):
        """A different participant cannot access another's alliance request."""
        other_client = ClientFile.objects.create(
            record_id="ALLIANCE-002", status="active",
        )
        other_client.first_name = "Other"
        other_client.last_name = "Person"
        other_client.save()
        other_participant = ParticipantUser.objects.create_participant(
            email="other@example.com",
            client_file=other_client,
            display_name="Other P",
            password="TestPass123!",
        )
        other_participant.mfa_method = "exempt"
        other_participant.save()

        session = self.client.session
        session["_portal_participant_id"] = str(other_participant.pk)
        session.save()

        url = f"/my/alliance/{self.alliance_req.pk}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_note_with_existing_rating_not_overwritten(self):
        """If note already has alliance_rating, portal rating doesn't overwrite."""
        self._login_portal()
        self.note.alliance_rating = 5
        self.note.alliance_rater = "worker_observed"
        self.note.save()

        url = f"/my/alliance/{self.alliance_req.pk}/"
        self.client.post(url, {"rating": "2"})

        self.note.refresh_from_db()
        # The existing rating should be preserved
        self.assertEqual(self.note.alliance_rating, 5)
        self.assertEqual(self.note.alliance_rater, "worker_observed")
