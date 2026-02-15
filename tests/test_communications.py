"""Tests for communication views and services (Wave 2).

Covers:
- QuickLogForm validation (channel, direction)
- CommunicationLogForm validation
- quick_log view — GET (buttons), GET with channel (form), POST (log + return buttons)
- communication_log view — GET (form), POST (log + redirect)
- log_communication service — creates Communication + AuditLog
- Permission enforcement — receptionist blocked, staff/PM allowed
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.communications.forms import CommunicationLogForm, QuickLogForm
from apps.communications.models import Communication
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


# -----------------------------------------------------------------------
# Form tests
# -----------------------------------------------------------------------

class QuickLogFormTest(TestCase):
    """Validate QuickLogForm field validation."""

    def test_valid_minimal(self):
        form = QuickLogForm(data={
            "channel": "phone",
            "direction": "outbound",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_with_notes(self):
        form = QuickLogForm(data={
            "channel": "sms",
            "direction": "inbound",
            "notes": "Client confirmed appointment",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_channel_rejected(self):
        form = QuickLogForm(data={
            "channel": "carrier_pigeon",
            "direction": "outbound",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("channel", form.errors)

    def test_invalid_direction_rejected(self):
        form = QuickLogForm(data={
            "channel": "email",
            "direction": "sideways",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("direction", form.errors)

    def test_channel_required(self):
        form = QuickLogForm(data={"direction": "outbound"})
        self.assertFalse(form.is_valid())
        self.assertIn("channel", form.errors)

    def test_valid_with_outcome(self):
        form = QuickLogForm(data={
            "channel": "phone",
            "direction": "outbound",
            "outcome": "reached",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_outcome_optional(self):
        form = QuickLogForm(data={
            "channel": "phone",
            "direction": "outbound",
            "outcome": "",
        })
        self.assertTrue(form.is_valid(), form.errors)


class CommunicationLogFormTest(TestCase):
    """Validate CommunicationLogForm field validation."""

    def test_valid_minimal(self):
        form = CommunicationLogForm(data={
            "direction": "outbound",
            "channel": "phone",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_with_all_fields(self):
        form = CommunicationLogForm(data={
            "direction": "inbound",
            "channel": "email",
            "subject": "Follow-up",
            "content": "Discussed safety plan next steps.",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_direction(self):
        form = CommunicationLogForm(data={
            "direction": "both",
            "channel": "phone",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("direction", form.errors)

    def test_valid_with_outcome(self):
        form = CommunicationLogForm(data={
            "direction": "outbound",
            "channel": "phone",
            "outcome": "voicemail",
        })
        self.assertTrue(form.is_valid(), form.errors)


# -----------------------------------------------------------------------
# View tests
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class QuickLogViewTest(TestCase):
    """Test the quick_log endpoint (deprecated — now redirects to Quick Notes)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Test Program", colour_hex="#10B981",
        )
        self.staff = User.objects.create_user(
            username="test_staff", password="testpass123",
            display_name="Test Staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role="staff", status="active",
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_get_redirects_to_timeline(self):
        """GET redirects to event list (deprecated view)."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/quick-log/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_post_redirects_to_timeline(self):
        """POST redirects to event list (deprecated view)."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/quick-log/"
        response = self.client.post(url, {
            "channel": "phone",
            "direction": "outbound",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Communication.objects.count(), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CommunicationLogViewTest(TestCase):
    """Test the communication_log view (deprecated — now redirects to Quick Notes)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Test Program", colour_hex="#10B981",
        )
        self.staff = User.objects.create_user(
            username="test_staff", password="testpass123",
            display_name="Test Staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role="staff", status="active",
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_get_redirects_to_quick_notes(self):
        """GET redirects to quick notes (deprecated view)."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/log/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


# -----------------------------------------------------------------------
# Service tests
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LogCommunicationServiceTest(TestCase):
    """Test the log_communication service function."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Test Program", colour_hex="#10B981",
        )
        self.staff = User.objects.create_user(
            username="test_staff", password="testpass123",
            display_name="Test Staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role="staff", status="active",
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_creates_communication_record(self):
        from apps.communications.services import log_communication
        comm = log_communication(
            client_file=self.client_file,
            direction="outbound",
            channel="phone",
            logged_by=self.staff,
            content="Called about intake.",
            author_program=self.program,
        )
        self.assertEqual(comm.channel, "phone")
        self.assertEqual(comm.direction, "outbound")
        self.assertEqual(comm.method, "manual_log")
        self.assertEqual(comm.delivery_status, "sent")
        self.assertEqual(comm.content, "Called about intake.")

    def test_creates_audit_log(self):
        from apps.audit.models import AuditLog
        from apps.communications.services import log_communication
        log_communication(
            client_file=self.client_file,
            direction="inbound",
            channel="sms",
            logged_by=self.staff,
        )
        audit = AuditLog.objects.using("audit").filter(
            resource_type="communication",
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.action, "create")
        self.assertEqual(audit.metadata["channel"], "sms")

    def test_outcome_saved(self):
        from apps.communications.services import log_communication
        comm = log_communication(
            client_file=self.client_file,
            direction="outbound",
            channel="phone",
            logged_by=self.staff,
            outcome="reached",
        )
        self.assertEqual(comm.outcome, "reached")

    def test_no_content_leaves_encrypted_field_empty(self):
        from apps.communications.services import log_communication
        comm = log_communication(
            client_file=self.client_file,
            direction="outbound",
            channel="in_person",
            logged_by=self.staff,
        )
        self.assertFalse(comm.content)


# -----------------------------------------------------------------------
# Permission enforcement
# -----------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CommunicationPermissionTest(TestCase):
    """Verify permission enforcement on communication views."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Test Program", colour_hex="#10B981",
        )
        # Receptionist — should be DENIED communication.log
        self.receptionist = User.objects.create_user(
            username="test_receptionist", password="testpass123",
            display_name="Test Receptionist",
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program,
            role="receptionist", status="active",
        )
        # Staff — should be ALLOWED communication.log
        self.staff = User.objects.create_user(
            username="test_staff", password="testpass123",
            display_name="Test Staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role="staff", status="active",
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_receptionist_blocked_from_compose_email(self):
        """Receptionist should get 403 on compose_email."""
        self.client.login(username="test_receptionist", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.get(url)
        self.assertIn(response.status_code, (403, 302))

    def test_staff_can_access_compose_email(self):
        """Staff should access compose_email without 403."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 403)


# -----------------------------------------------------------------------
# Compose Email view tests
# -----------------------------------------------------------------------

def _enable_messaging():
    """Enable messaging feature toggles and profile for tests."""
    from apps.admin_settings.models import FeatureToggle, InstanceSetting
    InstanceSetting.objects.update_or_create(
        setting_key="messaging_profile",
        defaults={"setting_value": "staff_sent"},
    )
    FeatureToggle.objects.update_or_create(
        feature_key="messaging_email",
        defaults={"is_enabled": True},
    )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ComposeEmailViewTest(TestCase):
    """Test the compose_email view for sending free-form emails."""

    databases = {"default", "audit"}

    def setUp(self):
        from datetime import date
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Test Program", colour_hex="#10B981",
        )
        self.staff = User.objects.create_user(
            username="test_staff", password="testpass123",
            display_name="Test Staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role="staff", status="active",
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.email = "test@example.com"
        self.client_file.email_consent = True
        self.client_file.email_consent_date = date.today()
        self.client_file.consent_messaging_type = "express"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )
        _enable_messaging()

    def tearDown(self):
        enc_module._fernet = None

    def test_get_returns_compose_form(self):
        """GET returns 200 with compose form when email is allowed."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Send Email to")
        self.assertContains(response, "Subject")
        self.assertContains(response, "Message")

    def test_get_shows_masked_email(self):
        """Response contains masked email, not the full address."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.get(url)
        content = response.content.decode()
        self.assertIn("te***@example.com", content)
        self.assertNotIn("test@example.com", content)

    def test_get_blocked_no_consent(self):
        """GET shows reason when consent is missing."""
        self.client_file.email_consent = False
        self.client_file.save()
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email cannot be sent")
        self.assertContains(response, "consent")

    def test_get_blocked_no_email(self):
        """GET shows reason when no email on file."""
        self.client_file.email = ""
        self.client_file.save()
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email cannot be sent")

    def test_post_preview_shows_preview(self):
        """POST with action=preview shows preview content."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.post(url, {
            "action": "preview",
            "subject": "Follow-up",
            "message": "Hope you are doing well.",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Follow-up")
        self.assertContains(response, "Hope you are doing well.")
        self.assertContains(response, "Send Email")
        self.assertContains(response, "unsubscribe")

    def test_post_preview_invalid_shows_errors(self):
        """POST with action=preview and missing subject shows errors."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.post(url, {
            "action": "preview",
            "subject": "",
            "message": "Body text",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "correct the errors")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_post_send_creates_communication(self):
        """POST with action=send creates Communication with method=staff_sent."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.post(url, {
            "action": "send",
            "subject": "Check-in",
            "message": "Just checking in.",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Communication.objects.count(), 1)
        comm = Communication.objects.first()
        self.assertEqual(comm.method, "staff_sent")
        self.assertEqual(comm.direction, "outbound")
        self.assertEqual(comm.channel, "email")
        self.assertEqual(comm.subject, "Check-in")
        self.assertEqual(comm.delivery_status, "sent")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_post_send_creates_audit_log(self):
        """POST with action=send creates an audit log entry."""
        from apps.audit.models import AuditLog
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        self.client.post(url, {
            "action": "send",
            "subject": "Test",
            "message": "Test body.",
        })
        audit = AuditLog.objects.using("audit").filter(
            resource_type="communication",
        ).last()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata["method"], "staff_sent")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_post_send_redirects_to_client_detail(self):
        """POST with action=send redirects to client detail on success."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.post(url, {
            "action": "send",
            "subject": "Redirect test",
            "message": "Body.",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/clients/{self.client_file.pk}/", response.url)

    def test_receptionist_blocked(self):
        """Receptionist should get 403 on compose_email."""
        receptionist = User.objects.create_user(
            username="test_receptionist", password="testpass123",
            display_name="Test Receptionist",
        )
        UserProgramRole.objects.create(
            user=receptionist, program=self.program,
            role="receptionist", status="active",
        )
        self.client.login(username="test_receptionist", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.get(url)
        self.assertIn(response.status_code, (403, 302))

    def test_unauthenticated_redirects_to_login(self):
        """Unauthenticated user gets redirect to login."""
        url = f"/communications/client/{self.client_file.pk}/compose-email/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
