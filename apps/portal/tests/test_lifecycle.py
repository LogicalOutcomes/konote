"""Lifecycle tests for participant portal accounts.

Verifies automatic deactivation on discharge and other lifecycle events.
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
    EMAIL_HASH_KEY="test-hash-key-for-lifecycle",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class DischargeDeactivationTests(TestCase):
    """D2: Portal account deactivation on client discharge."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create(
            record_id="LIFE-001", status="active",
        )
        self.participant = ParticipantUser.objects.create_participant(
            email="discharge@example.com",
            client_file=self.client_file,
            display_name="Discharge Test",
            password="TestPass123!",
        )
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_discharge_deactivates_portal_account(self):
        """Changing client status to 'discharged' should deactivate portal account."""
        self.assertTrue(self.participant.is_active)
        self.client_file.status = "discharged"
        self.client_file.save()
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)

    def test_inactive_status_deactivates_portal_account(self):
        """Changing client status to 'inactive' should also deactivate portal account."""
        self.client_file.status = "inactive"
        self.client_file.save()
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)

    def test_active_status_does_not_deactivate(self):
        """Client remaining active should not affect portal account."""
        self.client_file.status = "active"
        self.client_file.save()
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.is_active)

    def test_discharge_without_portal_account_no_error(self):
        """Discharging a client without a portal account should not raise errors."""
        other_client = ClientFile.objects.create(
            record_id="LIFE-002", status="active",
        )
        other_client.status = "discharged"
        other_client.save()  # Should not raise
