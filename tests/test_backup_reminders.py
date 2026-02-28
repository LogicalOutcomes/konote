"""Tests for backup reminder feature (SEC3-REMIND1)."""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from apps.admin_settings.forms import BackupReminderForm
from apps.admin_settings.models import OrganizationProfile


@pytest.fixture
def profile(db):
    """Return the OrganizationProfile singleton with backup reminders configured."""
    p = OrganizationProfile.get_solo()
    p.operating_name = "Test Agency"
    p.backup_reminder_enabled = True
    p.backup_reminder_frequency_days = 90
    p.backup_reminder_contact_email = "admin@testagency.ca"
    p.backup_reminder_last_sent_at = None
    p.backup_last_exported_at = None
    p.save()
    return p


def _call_command(*args, **kwargs):
    """Helper to call send_backup_reminders and capture stdout."""
    out = StringIO()
    call_command("send_backup_reminders", *args, stdout=out, **kwargs)
    return out.getvalue()


@pytest.mark.django_db
class SendBackupRemindersCommandTest:
    """Tests for the send_backup_reminders management command."""

    def test_sends_email_when_due(self, profile):
        """Command sends email when reminder is due (never sent before)."""
        output = _call_command()
        assert "Backup reminder sent" in output
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["admin@testagency.ca"]

    def test_skips_when_recently_sent(self, profile):
        """Command skips when reminder was recently sent."""
        profile.backup_reminder_last_sent_at = timezone.now() - timedelta(days=10)
        profile.save()

        output = _call_command()
        assert "Not due yet" in output
        assert len(mail.outbox) == 0

    def test_skips_when_disabled(self, profile):
        """Command skips when reminders are disabled."""
        profile.backup_reminder_enabled = False
        profile.save()

        output = _call_command()
        assert "disabled" in output.lower()
        assert len(mail.outbox) == 0

    def test_dry_run_no_email_no_timestamp(self, profile):
        """--dry-run does not send email or update timestamp."""
        output = _call_command("--dry-run")
        assert "DRY RUN" in output
        assert len(mail.outbox) == 0

        profile.refresh_from_db()
        assert profile.backup_reminder_last_sent_at is None

    def test_email_contains_agency_name(self, profile):
        """Email body contains the agency name."""
        _call_command()
        assert len(mail.outbox) == 1
        assert "Test Agency" in mail.outbox[0].subject
        assert "Test Agency" in mail.outbox[0].body

    def test_skips_when_recent_export(self, profile):
        """Command skips when a recent export exists within the frequency window."""
        profile.backup_last_exported_at = timezone.now() - timedelta(days=30)
        profile.save()

        output = _call_command()
        assert "Not due yet" in output
        assert len(mail.outbox) == 0

    def test_sends_when_export_is_old(self, profile):
        """Command sends when export is older than the frequency window."""
        profile.backup_last_exported_at = timezone.now() - timedelta(days=100)
        profile.save()

        output = _call_command()
        assert "Backup reminder sent" in output
        assert len(mail.outbox) == 1

    def test_updates_last_sent_timestamp(self, profile):
        """Command updates backup_reminder_last_sent_at after sending."""
        assert profile.backup_reminder_last_sent_at is None
        _call_command()
        profile.refresh_from_db()
        assert profile.backup_reminder_last_sent_at is not None

    def test_skips_when_no_contact_email(self, profile):
        """Command warns and skips when no contact email is set."""
        profile.backup_reminder_contact_email = ""
        profile.save()

        output = _call_command()
        assert "no contact email" in output.lower()
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class BackupReminderFormTest:
    """Tests for the BackupReminderForm."""

    def test_valid_form(self, db):
        form = BackupReminderForm(data={
            "backup_reminder_enabled": True,
            "backup_reminder_frequency_days": 90,
            "backup_reminder_contact_email": "admin@example.ca",
        })
        assert form.is_valid(), form.errors

    def test_saves_correctly(self, db):
        profile = OrganizationProfile.get_solo()
        form = BackupReminderForm(data={
            "backup_reminder_enabled": True,
            "backup_reminder_frequency_days": 90,
            "backup_reminder_contact_email": "admin@example.ca",
        }, instance=profile)
        assert form.is_valid(), form.errors
        form.save()

        profile.refresh_from_db()
        assert profile.backup_reminder_enabled is True
        assert profile.backup_reminder_frequency_days == 90
        assert profile.backup_reminder_contact_email == "admin@example.ca"

    def test_invalid_email(self, db):
        form = BackupReminderForm(data={
            "backup_reminder_enabled": True,
            "backup_reminder_frequency_days": 90,
            "backup_reminder_contact_email": "not-an-email",
        })
        assert not form.is_valid()
        assert "backup_reminder_contact_email" in form.errors

    def test_frequency_must_be_valid_choice(self, db):
        form = BackupReminderForm(data={
            "backup_reminder_enabled": True,
            "backup_reminder_frequency_days": 999,
            "backup_reminder_contact_email": "admin@example.ca",
        })
        assert not form.is_valid()
        assert "backup_reminder_frequency_days" in form.errors
