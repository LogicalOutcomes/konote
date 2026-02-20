"""Lifecycle tests for participant portal accounts.

Verifies automatic deactivation on discharge and other lifecycle events.
"""
from datetime import timedelta
from io import StringIO

from cryptography.fernet import Fernet
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.erasure import build_data_summary, _anonymise_client_pii, _purge_narrative_content
from apps.clients.merge import execute_merge
from apps.clients.models import ClientFile
from apps.portal.models import (
    CorrectionRequest,
    ParticipantJournalEntry,
    ParticipantMessage,
    ParticipantUser,
    StaffPortalNote,
)
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


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-lifecycle",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class ClientMergePortalTests(TestCase):
    """D3: Portal account transfer during client merge."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.kept = ClientFile.objects.create(record_id="MERGE-KEPT", status="active")
        self.archived = ClientFile.objects.create(record_id="MERGE-ARCH", status="active")
        self.staff_user = User.objects.create_user(
            username="mergestaff", password="pass", display_name="Staff",
        )
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_merge_transfers_portal_account(self):
        """Portal account on archived client should transfer to kept client."""
        participant = ParticipantUser.objects.create_participant(
            email="archived@example.com",
            client_file=self.archived,
            display_name="Archived User",
            password="TestPass123!",
        )
        execute_merge(self.kept, self.archived, {}, {}, self.staff_user, "127.0.0.1")
        participant.refresh_from_db()
        self.assertEqual(participant.client_file_id, self.kept.pk)

    def test_merge_deactivates_duplicate_portal_account(self):
        """If both clients have portal accounts, archived's should be deactivated."""
        kept_user = ParticipantUser.objects.create_participant(
            email="kept@example.com",
            client_file=self.kept,
            display_name="Kept User",
            password="TestPass123!",
        )
        arch_user = ParticipantUser.objects.create_participant(
            email="archived2@example.com",
            client_file=self.archived,
            display_name="Archived User",
            password="TestPass123!",
        )
        execute_merge(self.kept, self.archived, {}, {}, self.staff_user, "127.0.0.1")
        kept_user.refresh_from_db()
        arch_user.refresh_from_db()
        self.assertTrue(kept_user.is_active)
        self.assertFalse(arch_user.is_active)

    def test_merge_transfers_journal_entries(self):
        """Journal entries on archived client should transfer to kept."""
        participant = ParticipantUser.objects.create_participant(
            email="journal@example.com",
            client_file=self.archived,
            display_name="Journal User",
            password="TestPass123!",
        )
        entry = ParticipantJournalEntry(
            participant_user=participant,
            client_file=self.archived,
        )
        entry.content = "My journal"
        entry.save()

        execute_merge(self.kept, self.archived, {}, {}, self.staff_user, "127.0.0.1")
        entry.refresh_from_db()
        self.assertEqual(entry.client_file_id, self.kept.pk)

    def test_merge_transfers_messages(self):
        """Portal messages should transfer to kept client."""
        participant = ParticipantUser.objects.create_participant(
            email="msg@example.com",
            client_file=self.archived,
            display_name="Message User",
            password="TestPass123!",
        )
        msg = ParticipantMessage(
            participant_user=participant,
            client_file=self.archived,
            message_type="general",
        )
        msg.content = "Hello"
        msg.save()

        execute_merge(self.kept, self.archived, {}, {}, self.staff_user, "127.0.0.1")
        msg.refresh_from_db()
        self.assertEqual(msg.client_file_id, self.kept.pk)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-lifecycle",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class ErasurePortalTests(TestCase):
    """D4: Portal data included in erasure workflow."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create(
            record_id="ERASE-001", status="active",
        )
        self.participant = ParticipantUser.objects.create_participant(
            email="erase@example.com",
            client_file=self.client_file,
            display_name="Erase Test",
            password="TestPass123!",
        )
        # Create portal content
        entry = ParticipantJournalEntry(
            participant_user=self.participant,
            client_file=self.client_file,
        )
        entry.content = "Secret journal entry"
        entry.save()

        msg = ParticipantMessage(
            participant_user=self.participant,
            client_file=self.client_file,
            message_type="general",
        )
        msg.content = "Secret message"
        msg.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_data_summary_includes_portal_counts(self):
        """build_data_summary should count portal journal entries and messages."""
        summary = build_data_summary(self.client_file)
        self.assertEqual(summary["portal_journal_entries"], 1)
        self.assertEqual(summary["portal_messages"], 1)

    def test_purge_blanks_portal_content(self):
        """_purge_narrative_content should blank portal encrypted content."""
        _purge_narrative_content(self.client_file)
        entry = ParticipantJournalEntry.objects.get(client_file=self.client_file)
        self.assertEqual(entry._content_encrypted, b"")
        msg = ParticipantMessage.objects.get(client_file=self.client_file)
        self.assertEqual(msg._content_encrypted, b"")

    def test_anonymise_deactivates_portal_account(self):
        """_anonymise_client_pii should deactivate and scrub the portal account."""
        _anonymise_client_pii(self.client_file, "ER-TEST-001")
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)
        self.assertEqual(self.participant._email_encrypted, b"")
        self.assertEqual(self.participant._totp_secret_encrypted, b"")
        self.assertEqual(self.participant.display_name, "[Anonymised]")
        self.assertTrue(self.participant.email_hash.startswith("anonymised-"))
        self.assertEqual(self.participant.password, "")
        self.assertEqual(self.participant.password_reset_token_hash, "")

    def test_anonymise_two_accounts_no_unique_clash(self):
        """Anonymising two clients with portal accounts should not raise IntegrityError."""
        client2 = ClientFile.objects.create(record_id="ERASE-002", status="active")
        ParticipantUser.objects.create_participant(
            email="erase2@example.com",
            client_file=client2,
            display_name="Erase Test 2",
            password="TestPass123!",
        )
        _anonymise_client_pii(self.client_file, "ER-TEST-001")
        _anonymise_client_pii(client2, "ER-TEST-002")  # Should not raise


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-lifecycle",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class InactivityDeactivationTests(TestCase):
    """D1: Deactivate portal accounts inactive for 90+ days."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create(
            record_id="INACT-001", status="active",
        )
        self.participant = ParticipantUser.objects.create_participant(
            email="inactive@example.com",
            client_file=self.client_file,
            display_name="Inactive User",
            password="TestPass123!",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_deactivates_inactive_accounts(self):
        """Accounts with last_login > 90 days ago should be deactivated."""
        self.participant.last_login = timezone.now() - timedelta(days=91)
        self.participant.save(update_fields=["last_login"])

        out = StringIO()
        call_command("deactivate_inactive_portal_accounts", stdout=out)
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)
        self.assertIn("1", out.getvalue())

    def test_leaves_active_accounts(self):
        """Accounts with recent login should not be deactivated."""
        self.participant.last_login = timezone.now() - timedelta(days=30)
        self.participant.save(update_fields=["last_login"])

        call_command("deactivate_inactive_portal_accounts", stdout=StringIO())
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.is_active)

    def test_deactivates_never_logged_in_old_accounts(self):
        """Accounts created > 90 days ago that never logged in should be deactivated."""
        self.participant.last_login = None
        self.participant.save(update_fields=["last_login"])
        # Backdate created_at
        ParticipantUser.objects.filter(pk=self.participant.pk).update(
            created_at=timezone.now() - timedelta(days=91),
        )

        call_command("deactivate_inactive_portal_accounts", stdout=StringIO())
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)

    def test_dry_run_does_not_deactivate(self):
        """--dry-run should report but not deactivate."""
        self.participant.last_login = timezone.now() - timedelta(days=91)
        self.participant.save(update_fields=["last_login"])

        call_command("deactivate_inactive_portal_accounts", "--dry-run", stdout=StringIO())
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.is_active)
