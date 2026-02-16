"""Tests for the send_reminders management command.

Covers:
- Dry run shows pending meetings without sending
- Sends reminders for meetings in the lookahead window
- Skips meetings already reminded (reminder_sent=True)
- Skips cancelled/completed meetings
- Skips meetings outside the lookahead window
- Retries previously failed reminders
- Custom --hours flag
- Calls check_and_send_health_alert after batch
"""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.admin_settings.models import FeatureToggle, InstanceSetting
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Event, EventType, Meeting
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _setup_fixtures(tc):
    """Create shared test data: program, staff, client with consent, event type."""
    tc.program = Program.objects.create(name="Reminder Program")
    tc.staff = User.objects.create_user(
        username="reminder_staff",
        password="testpass123",
        display_name="Staff User",
    )
    UserProgramRole.objects.create(
        user=tc.staff, program=tc.program, role="staff", status="active",
    )
    tc.client_file = ClientFile()
    tc.client_file.first_name = "Reminder"
    tc.client_file.last_name = "Client"
    tc.client_file.phone = "+15559876543"
    tc.client_file.sms_consent = True
    tc.client_file.sms_consent_date = timezone.now().date()
    tc.client_file.email_consent = True
    tc.client_file.email_consent_date = timezone.now().date()
    tc.client_file.consent_type = "express"
    tc.client_file.preferred_contact_method = "sms"
    tc.client_file.preferred_language = "en"
    tc.client_file.save()
    ClientProgramEnrolment.objects.create(
        client_file=tc.client_file, program=tc.program,
    )
    tc.event_type = EventType.objects.create(
        name="Meeting", description="Standard meeting",
    )

    # Enable messaging so can_send() passes
    InstanceSetting.objects.update_or_create(
        setting_key="messaging_profile",
        defaults={"setting_value": "staff_sent"},
    )
    FeatureToggle.objects.update_or_create(
        feature_key="messaging_sms",
        defaults={"is_enabled": True},
    )


def _create_meeting(tc, hours_from_now=24, **kwargs):
    """Create an Event + Meeting at the given offset."""
    start = timezone.now() + timedelta(hours=hours_from_now)
    event = Event.objects.create(
        client_file=tc.client_file,
        event_type=tc.event_type,
        start_timestamp=start,
    )
    meeting = Meeting.objects.create(event=event, location="Office", **kwargs)
    meeting.attendees.add(tc.staff)
    return meeting


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, SMS_ENABLED=True)
class SendRemindersCommandTests(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        _setup_fixtures(self)

    def tearDown(self):
        enc_module._fernet = None

    def test_dry_run_does_not_send(self):
        """--dry-run shows meetings but doesn't call send_reminder."""
        _create_meeting(self, hours_from_now=12)
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            call_command("send_reminders", "--dry-run", stdout=out)
            mock_send.assert_not_called()

        output = out.getvalue()
        self.assertIn("DRY RUN", output)
        self.assertIn("Would remind", output)

    def test_sends_for_upcoming_meeting(self):
        """Sends a reminder for a scheduled meeting within the window."""
        meeting = _create_meeting(self, hours_from_now=12)
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            mock_send.return_value = (True, "Sent")
            with patch("apps.communications.management.commands.send_reminders.check_and_send_health_alert"):
                call_command("send_reminders", stdout=out)

            mock_send.assert_called_once_with(meeting)

        output = out.getvalue()
        self.assertIn("1 sent", output)

    def test_skips_already_reminded(self):
        """Meetings with reminder_sent=True are not processed."""
        _create_meeting(self, hours_from_now=12, reminder_sent=True, reminder_status="sent")
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            call_command("send_reminders", stdout=out)
            mock_send.assert_not_called()

        self.assertIn("No meetings need reminders", out.getvalue())

    def test_skips_cancelled_meetings(self):
        """Cancelled meetings are not reminded."""
        _create_meeting(self, hours_from_now=12, status="cancelled")
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            call_command("send_reminders", stdout=out)
            mock_send.assert_not_called()

    def test_skips_meetings_outside_window(self):
        """Meetings beyond the lookahead window are not reminded."""
        _create_meeting(self, hours_from_now=48)  # Default window is 36h
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            call_command("send_reminders", stdout=out)
            mock_send.assert_not_called()

    def test_custom_hours_flag(self):
        """--hours flag changes the lookahead window."""
        meeting = _create_meeting(self, hours_from_now=48)
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            mock_send.return_value = (True, "Sent")
            with patch("apps.communications.management.commands.send_reminders.check_and_send_health_alert"):
                call_command("send_reminders", "--hours", "72", stdout=out)

            mock_send.assert_called_once_with(meeting)

    def test_retries_failed_reminders(self):
        """Meetings with reminder_status='failed' (but reminder_sent=False) are retried."""
        meeting = _create_meeting(self, hours_from_now=12, reminder_status="failed")
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            mock_send.return_value = (True, "Sent")
            with patch("apps.communications.management.commands.send_reminders.check_and_send_health_alert"):
                call_command("send_reminders", stdout=out)

            mock_send.assert_called_once_with(meeting)

    def test_counts_consent_skip_separately(self):
        """Meetings where send_reminder returns a consent reason are counted as skipped."""
        _create_meeting(self, hours_from_now=12)
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            mock_send.return_value = (False, "Client has not consented to reminders")
            with patch("apps.communications.management.commands.send_reminders.check_and_send_health_alert"):
                call_command("send_reminders", stdout=out)

        output = out.getvalue()
        self.assertIn("skipped", output)
        self.assertNotIn("failed", output.lower().split("done:")[-1].split("skip")[0])

    def test_calls_health_check_after_batch(self):
        """check_and_send_health_alert is called after processing."""
        _create_meeting(self, hours_from_now=12)

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            mock_send.return_value = (True, "Sent")
            with patch("apps.communications.management.commands.send_reminders.check_and_send_health_alert") as mock_health:
                call_command("send_reminders", stdout=StringIO())
                mock_health.assert_called_once()

    def test_skips_past_meetings(self):
        """Meetings in the past are not reminded."""
        start = timezone.now() - timedelta(hours=1)
        event = Event.objects.create(
            client_file=self.client_file,
            event_type=self.event_type,
            start_timestamp=start,
        )
        Meeting.objects.create(event=event, location="Office")
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            call_command("send_reminders", stdout=out)
            mock_send.assert_not_called()

    def test_no_meetings_message(self):
        """When there are no meetings to process, shows a helpful message."""
        out = StringIO()
        call_command("send_reminders", stdout=out)
        self.assertIn("No meetings need reminders", out.getvalue())

    def test_handles_send_exception_gracefully(self):
        """Unexpected exceptions in send_reminder don't crash the batch."""
        _create_meeting(self, hours_from_now=12)
        out = StringIO()

        with patch("apps.communications.management.commands.send_reminders.send_reminder") as mock_send:
            mock_send.side_effect = RuntimeError("Unexpected error")
            with patch("apps.communications.management.commands.send_reminders.check_and_send_health_alert"):
                call_command("send_reminders", stdout=out)

        output = out.getvalue()
        self.assertIn("failed", output.lower())
