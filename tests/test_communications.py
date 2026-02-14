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
    """Test the quick_log HTMX endpoint."""

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

    def test_get_no_channel_returns_buttons(self):
        """GET without ?channel returns the quick-log buttons partial."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/quick-log/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Record a Call")

    def test_get_with_channel_returns_form(self):
        """GET with ?channel=phone returns the mini form."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/quick-log/?channel=phone"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notes (optional)")

    def test_post_creates_communication(self):
        """POST with valid data creates a Communication and returns buttons."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/quick-log/"
        response = self.client.post(url, {
            "channel": "phone",
            "direction": "outbound",
            "notes": "Called to confirm appointment",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Communication.objects.count(), 1)
        comm = Communication.objects.first()
        self.assertEqual(comm.channel, "phone")
        self.assertEqual(comm.direction, "outbound")
        self.assertEqual(comm.logged_by, self.staff)

    def test_post_with_outcome_saves_outcome(self):
        """POST with outcome saves it on the Communication record."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/quick-log/"
        response = self.client.post(url, {
            "channel": "phone",
            "direction": "outbound",
            "notes": "Left voicemail",
            "outcome": "voicemail",
        })
        self.assertEqual(response.status_code, 200)
        comm = Communication.objects.first()
        self.assertEqual(comm.outcome, "voicemail")

    def test_post_invalid_form_returns_form(self):
        """POST with invalid channel returns the form with errors."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/quick-log/"
        response = self.client.post(url, {
            "channel": "bad_channel",
            "direction": "outbound",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Communication.objects.count(), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CommunicationLogViewTest(TestCase):
    """Test the full communication_log form view."""

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

    def test_get_returns_form(self):
        """GET returns the full communication log form."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/log/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Record a Contact")

    def test_post_creates_communication_and_redirects(self):
        """POST with valid data creates a Communication and redirects to events."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/log/"
        response = self.client.post(url, {
            "direction": "outbound",
            "channel": "email",
            "subject": "Follow-up",
            "content": "Discussed next steps.",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Communication.objects.count(), 1)
        comm = Communication.objects.first()
        self.assertEqual(comm.channel, "email")
        self.assertEqual(comm.subject, "Follow-up")


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

    def test_receptionist_blocked_from_quick_log(self):
        """Receptionist should get 403 on quick_log."""
        self.client.login(username="test_receptionist", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/quick-log/"
        response = self.client.get(url)
        self.assertIn(response.status_code, (403, 302))

    def test_receptionist_blocked_from_full_log(self):
        """Receptionist should get 403 on communication_log."""
        self.client.login(username="test_receptionist", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/log/"
        response = self.client.get(url)
        self.assertIn(response.status_code, (403, 302))

    def test_staff_can_access_quick_log(self):
        """Staff should access quick_log without 403."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/quick-log/"
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 403)

    def test_staff_can_access_full_log(self):
        """Staff should access communication_log without 403."""
        self.client.login(username="test_staff", password="testpass123")
        url = f"/communications/client/{self.client_file.pk}/log/"
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 403)
