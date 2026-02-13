"""Tests for Wave 3 messaging features.

Covers:
- can_send() comprehensive pre-send checks
- render_message_template() with defaults and custom templates
- generate_unsubscribe_url() token generation
- email_unsubscribe view (GET confirmation, POST consent withdrawal)
- send_reminder_preview view (GET preview, POST send)
- SystemHealthCheck model (record_success, record_failure)
- Health banners on meeting dashboard
- MessagingSettingsForm validation and save
- messaging_settings view (admin only)
"""
from datetime import date, timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.core import signing
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.admin_settings.models import FeatureToggle, InstanceSetting
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.communications.models import Communication, SystemHealthCheck
from apps.communications.services import (
    can_send,
    check_and_send_health_alert,
    generate_unsubscribe_url,
    render_message_template,
)
from apps.events.models import Event, EventType, Meeting
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _create_test_fixtures(test_case):
    """Shared helper to create program, user, client, event type."""
    test_case.program = Program.objects.create(name="Test Program")
    test_case.staff = User.objects.create_user(
        username="wave3_staff",
        password="testpass123",
        display_name="Test Staff",
    )
    UserProgramRole.objects.create(
        user=test_case.staff,
        program=test_case.program,
        role="staff",
        status="active",
    )
    test_case.admin_user = User.objects.create_user(
        username="wave3_admin",
        password="testpass123",
        display_name="Admin User",
        is_admin=True,
    )
    UserProgramRole.objects.create(
        user=test_case.admin_user,
        program=test_case.program,
        role="staff",
        status="active",
    )
    test_case.client_file = ClientFile()
    test_case.client_file.first_name = "Maria"
    test_case.client_file.last_name = "Doe"
    test_case.client_file.phone = "+15551234567"
    test_case.client_file.sms_consent = True
    test_case.client_file.sms_consent_date = date.today()
    test_case.client_file.email_consent = True
    test_case.client_file.email_consent_date = date.today()
    test_case.client_file.consent_type = "express"
    test_case.client_file.preferred_contact_method = "sms"
    test_case.client_file.preferred_language = "en"
    test_case.client_file.save()
    ClientProgramEnrolment.objects.create(
        client_file=test_case.client_file,
        program=test_case.program,
    )
    test_case.event_type = EventType.objects.create(
        name="Meeting",
        description="Standard meeting",
    )


def _create_meeting(test_case, **kwargs):
    """Create an Event + Meeting for testing."""
    defaults = {
        "start_timestamp": timezone.now() + timedelta(hours=24),
    }
    defaults.update(kwargs)
    event = Event.objects.create(
        client_file=test_case.client_file,
        event_type=test_case.event_type,
        start_timestamp=defaults["start_timestamp"],
    )
    meeting = Meeting.objects.create(event=event, location="Office")
    meeting.attendees.add(test_case.staff)
    return meeting


# -----------------------------------------------------------------------
# can_send() tests
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CanSendTests(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        _create_test_fixtures(self)

    def tearDown(self):
        enc_module._fernet = None

    def test_happy_path_sms(self):
        """All checks pass — can_send returns True."""
        InstanceSetting.objects.update_or_create(
            setting_key="messaging_profile",
            defaults={"setting_value": "staff_sent"},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="messaging_sms",
            defaults={"is_enabled": True},
        )
        allowed, reason = can_send(self.client_file, "sms")
        self.assertTrue(allowed)
        self.assertEqual(reason, "OK")

    def test_happy_path_email(self):
        InstanceSetting.objects.update_or_create(
            setting_key="messaging_profile",
            defaults={"setting_value": "staff_sent"},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="messaging_email",
            defaults={"is_enabled": True},
        )
        self.client_file.email = "test@example.com"
        self.client_file.save()
        allowed, reason = can_send(self.client_file, "email")
        self.assertTrue(allowed)

    def test_safety_first_blocks_all(self):
        InstanceSetting.objects.update_or_create(
            setting_key="safety_first_mode",
            defaults={"setting_value": "true"},
        )
        allowed, reason = can_send(self.client_file, "sms")
        self.assertFalse(allowed)
        self.assertIn("Safety-First", reason)

    def test_record_keeping_blocks_all(self):
        InstanceSetting.objects.update_or_create(
            setting_key="messaging_profile",
            defaults={"setting_value": "record_keeping"},
        )
        allowed, reason = can_send(self.client_file, "sms")
        self.assertFalse(allowed)
        self.assertIn("record-keeping", reason)

    def test_sms_toggle_disabled_blocks(self):
        InstanceSetting.objects.update_or_create(
            setting_key="messaging_profile",
            defaults={"setting_value": "staff_sent"},
        )
        # No FeatureToggle for messaging_sms
        allowed, reason = can_send(self.client_file, "sms")
        self.assertFalse(allowed)
        self.assertIn("not set up", reason)

    def test_no_consent_blocks(self):
        InstanceSetting.objects.update_or_create(
            setting_key="messaging_profile",
            defaults={"setting_value": "staff_sent"},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="messaging_sms",
            defaults={"is_enabled": True},
        )
        self.client_file.sms_consent = False
        self.client_file.save()
        allowed, reason = can_send(self.client_file, "sms")
        self.assertFalse(allowed)
        self.assertIn("not consented", reason)

    def test_expired_implied_consent_blocks(self):
        InstanceSetting.objects.update_or_create(
            setting_key="messaging_profile",
            defaults={"setting_value": "staff_sent"},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="messaging_sms",
            defaults={"is_enabled": True},
        )
        self.client_file.consent_type = "implied"
        self.client_file.sms_consent_date = date.today() - timedelta(days=731)
        self.client_file.save()
        allowed, reason = can_send(self.client_file, "sms")
        self.assertFalse(allowed)
        self.assertIn("expired", reason)

    def test_no_phone_blocks_sms(self):
        InstanceSetting.objects.update_or_create(
            setting_key="messaging_profile",
            defaults={"setting_value": "staff_sent"},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="messaging_sms",
            defaults={"is_enabled": True},
        )
        self.client_file.phone = ""
        self.client_file.save()
        allowed, reason = can_send(self.client_file, "sms")
        self.assertFalse(allowed)
        self.assertIn("phone", reason.lower())


# -----------------------------------------------------------------------
# Message template tests
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MessageTemplateTests(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        _create_test_fixtures(self)
        self.meeting = _create_meeting(self)

    def tearDown(self):
        enc_module._fernet = None

    def test_default_template_renders(self):
        text = render_message_template("reminder_sms", self.client_file, self.meeting)
        self.assertIn("Reminder", text)
        self.assertIn("appointment", text)
        self.assertIn("STOP", text)

    def test_french_template_for_francophone_client(self):
        self.client_file.preferred_language = "fr"
        self.client_file.save()
        text = render_message_template("reminder_sms", self.client_file, self.meeting)
        self.assertIn("Rappel", text)
        self.assertIn("STOP", text)

    def test_custom_template_from_instance_setting(self):
        InstanceSetting.objects.create(
            setting_key="reminder_sms_en",
            setting_value="Hey! Appointment on {date} at {time}. Call {org_phone}.",
        )
        text = render_message_template("reminder_sms", self.client_file, self.meeting)
        self.assertIn("Hey!", text)

    def test_personal_note_appended(self):
        text = render_message_template(
            "reminder_sms", self.client_file, self.meeting,
            personal_note="Looking forward to seeing you!"
        )
        self.assertIn("Looking forward", text)


# -----------------------------------------------------------------------
# Unsubscribe tests
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class UnsubscribeTests(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        _create_test_fixtures(self)

    def tearDown(self):
        enc_module._fernet = None

    def test_valid_token_shows_confirmation(self):
        url = generate_unsubscribe_url(self.client_file, "email")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unsubscribe")

    def test_post_withdraws_email_consent(self):
        url = generate_unsubscribe_url(self.client_file, "email")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.client_file.refresh_from_db()
        self.assertFalse(self.client_file.email_consent)
        self.assertEqual(self.client_file.email_consent_withdrawn_date, date.today())

    def test_post_withdraws_sms_consent(self):
        url = generate_unsubscribe_url(self.client_file, "sms")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.client_file.refresh_from_db()
        self.assertFalse(self.client_file.sms_consent)

    def test_creates_audit_log(self):
        from apps.audit.models import AuditLog
        url = generate_unsubscribe_url(self.client_file, "email")
        self.client.post(url)
        audit = AuditLog.objects.using("audit").filter(
            resource_type="clients",
            action="update",
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata["method"], "email_unsubscribe_link")

    def test_expired_token_shows_error(self):
        token = signing.dumps(
            {"client_id": self.client_file.pk, "channel": "email"},
            salt="unsubscribe",
        )
        # Simulate expired token by using max_age=0
        with patch("apps.communications.views.signing.loads") as mock_loads:
            mock_loads.side_effect = signing.BadSignature("expired")
            response = self.client.get(f"/communications/unsubscribe/{token}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired")

    def test_invalid_token_shows_error(self):
        response = self.client.get("/communications/unsubscribe/invalid-garbage-token/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired")


# -----------------------------------------------------------------------
# Send Reminder Preview tests
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SendReminderPreviewTests(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        _create_test_fixtures(self)
        self.meeting = _create_meeting(self)
        self.client.login(username="wave3_staff", password="testpass123")
        # Enable messaging
        InstanceSetting.objects.update_or_create(
            setting_key="messaging_profile",
            defaults={"setting_value": "staff_sent"},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="messaging_sms",
            defaults={"is_enabled": True},
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_get_returns_preview(self):
        url = f"/communications/client/{self.client_file.pk}/meeting/{self.meeting.event_id}/send-reminder/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reminder")

    def test_get_shows_blocked_reason_when_not_allowed(self):
        self.client_file.sms_consent = False
        self.client_file.save()
        url = f"/communications/client/{self.client_file.pk}/meeting/{self.meeting.event_id}/send-reminder/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot send")

    @patch("apps.communications.services.send_sms")
    def test_post_sends_reminder(self, mock_sms):
        mock_sms.return_value = (True, "SM123")
        url = f"/communications/client/{self.client_file.pk}/meeting/{self.meeting.event_id}/send-reminder/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.meeting.refresh_from_db()
        self.assertTrue(self.meeting.reminder_sent)
        self.assertEqual(self.meeting.reminder_status, "sent")

    def test_unauthenticated_redirects(self):
        self.client.logout()
        url = f"/communications/client/{self.client_file.pk}/meeting/{self.meeting.event_id}/send-reminder/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


# -----------------------------------------------------------------------
# SystemHealthCheck model tests
# -----------------------------------------------------------------------

class SystemHealthCheckTests(TestCase):
    def test_record_success_resets_failures(self):
        SystemHealthCheck.record_failure("sms", "test error")
        SystemHealthCheck.record_failure("sms", "test error 2")
        SystemHealthCheck.record_success("sms")
        health = SystemHealthCheck.objects.get(channel="sms")
        self.assertEqual(health.consecutive_failures, 0)
        self.assertIsNotNone(health.last_success_at)

    def test_record_failure_increments(self):
        SystemHealthCheck.record_failure("email", "SMTP error")
        SystemHealthCheck.record_failure("email", "SMTP error 2")
        health = SystemHealthCheck.objects.get(channel="email")
        self.assertEqual(health.consecutive_failures, 2)
        self.assertEqual(health.last_failure_reason, "SMTP error 2")

    def test_record_success_creates_entry(self):
        SystemHealthCheck.record_success("sms")
        self.assertTrue(SystemHealthCheck.objects.filter(channel="sms").exists())


# -----------------------------------------------------------------------
# Health banner tests
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class HealthBannerTests(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        _create_test_fixtures(self)
        self.client.login(username="wave3_staff", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def test_no_banner_when_healthy(self):
        response = self.client.get("/events/meetings/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "health-banner")

    def test_warning_banner_on_recent_failures(self):
        FeatureToggle.objects.update_or_create(
            feature_key="messaging_sms",
            defaults={"is_enabled": True},
        )
        SystemHealthCheck.record_failure("sms", "Phone unreachable")
        response = self.client.get("/events/meetings/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "health-banner")

    def test_danger_banner_on_sustained_failures(self):
        FeatureToggle.objects.update_or_create(
            feature_key="messaging_sms",
            defaults={"is_enabled": True},
        )
        for _ in range(4):
            SystemHealthCheck.record_failure("sms", "Twilio down")
        response = self.client.get("/events/meetings/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "health-banner-danger")


# -----------------------------------------------------------------------
# Health alert email tests
# -----------------------------------------------------------------------

class HealthAlertTests(TestCase):
    databases = {"default", "audit"}

    @patch("apps.communications.services.send_email_message")
    def test_alert_sent_after_sustained_failures(self, mock_email):
        mock_email.return_value = (True, None)
        InstanceSetting.objects.create(
            setting_key="support_email",
            setting_value="admin@org.ca",
        )
        # Create health check with 5 failures starting now
        health = SystemHealthCheck.objects.create(
            channel="sms",
            consecutive_failures=5,
            last_failure_at=timezone.now(),
            last_failure_reason="Twilio suspended",
        )
        check_and_send_health_alert()
        mock_email.assert_called_once()
        health.refresh_from_db()
        self.assertIsNotNone(health.alert_email_sent_at)

    @patch("apps.communications.services.send_email_message")
    def test_alert_not_resent_within_24h(self, mock_email):
        mock_email.return_value = (True, None)
        InstanceSetting.objects.create(
            setting_key="support_email",
            setting_value="admin@org.ca",
        )
        SystemHealthCheck.objects.create(
            channel="sms",
            consecutive_failures=5,
            last_failure_at=timezone.now(),
            last_failure_reason="Twilio down",
            alert_email_sent_at=timezone.now() - timedelta(hours=12),
        )
        check_and_send_health_alert()
        mock_email.assert_not_called()

    def test_no_alert_without_support_email(self):
        SystemHealthCheck.objects.create(
            channel="sms",
            consecutive_failures=10,
            last_failure_at=timezone.now(),
        )
        # Should not raise — just returns silently
        check_and_send_health_alert()


# -----------------------------------------------------------------------
# Feature toggle tests
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MessagingFeatureToggleTests(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        cache.clear()
        enc_module._fernet = None
        _create_test_fixtures(self)
        self.meeting = _create_meeting(self)
        self.client.login(username="wave3_staff", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None
        cache.clear()

    def test_send_reminder_button_hidden_when_toggles_off(self):
        response = self.client.get("/events/meetings/")
        self.assertNotContains(response, "Send Reminder")

    def test_send_reminder_button_visible_when_toggle_on(self):
        FeatureToggle.objects.update_or_create(
            feature_key="messaging_sms",
            defaults={"is_enabled": True},
        )
        response = self.client.get("/events/meetings/")
        self.assertContains(response, "Send Reminder")


# -----------------------------------------------------------------------
# Messaging settings page tests
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MessagingSettingsTests(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        _create_test_fixtures(self)

    def tearDown(self):
        enc_module._fernet = None

    def test_non_admin_gets_403(self):
        self.client.login(username="wave3_staff", password="testpass123")
        response = self.client.get("/admin/settings/messaging/")
        # Non-admin should be forbidden (redirected or 403)
        self.assertIn(response.status_code, [302, 403])

    def test_admin_sees_page(self):
        self.client.login(username="wave3_admin", password="testpass123")
        response = self.client.get("/admin/settings/messaging/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Messaging Settings")

    def test_post_saves_profile(self):
        self.client.login(username="wave3_admin", password="testpass123")
        response = self.client.post("/admin/settings/messaging/", {
            "messaging_profile": "staff_sent",
            "reminder_window_hours": "24",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            InstanceSetting.get("messaging_profile"),
            "staff_sent",
        )

    def test_safety_first_toggle_saves(self):
        self.client.login(username="wave3_admin", password="testpass123")
        self.client.post("/admin/settings/messaging/", {
            "messaging_profile": "record_keeping",
            "safety_first_mode": "on",
            "reminder_window_hours": "24",
        })
        self.assertEqual(
            InstanceSetting.get("safety_first_mode"),
            "true",
        )

    def test_template_updates_save(self):
        self.client.login(username="wave3_admin", password="testpass123")
        self.client.post("/admin/settings/messaging/", {
            "messaging_profile": "staff_sent",
            "reminder_window_hours": "24",
            "reminder_sms_en": "Custom reminder: {date} at {time}",
        })
        self.assertEqual(
            InstanceSetting.get("reminder_sms_en"),
            "Custom reminder: {date} at {time}",
        )

    def test_messaging_card_on_dashboard(self):
        self.client.login(username="wave3_admin", password="testpass123")
        response = self.client.get("/admin/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Messaging")
        self.assertContains(response, "Messaging Settings")
