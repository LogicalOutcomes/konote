"""Tests for staff message functionality (UXP-RECEP)."""
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import Program, UserProgramRole
from apps.communications.models import StaffMessage

User = get_user_model()


class StaffMessageModelTests(TestCase):
    """Test StaffMessage model."""

    databases = ["default", "audit"]

    def test_content_encryption(self):
        program = Program.objects.create(name="Test")
        client = ClientFile.objects.create(first_name="Test", last_name="Client")
        user = User.objects.create_user(username="test", password="pass")

        msg = StaffMessage(client_file=client, left_by=user)
        msg.content = "Sarah called about appointment"
        msg.save()

        # Reload from DB
        msg.refresh_from_db()
        self.assertEqual(msg.content, "Sarah called about appointment")
        # Raw field should be encrypted (not plain text)
        self.assertNotEqual(msg._content_encrypted, b"Sarah called about appointment")


class StaffMessagePermissionTests(TestCase):
    """Test permission enforcement for staff messages."""

    databases = ["default", "audit"]

    def setUp(self):
        self.program = Program.objects.create(name="Test Program")
        self.client_file = ClientFile.objects.create(first_name="Test", last_name="Client")
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="active"
        )

        # Receptionist
        self.receptionist = User.objects.create_user(username="recep", password="pass", display_name="Front Desk")
        UserProgramRole.objects.create(user=self.receptionist, program=self.program, role="receptionist", status="active")

        # Staff
        self.staff = User.objects.create_user(username="staff", password="pass", display_name="Case Worker")
        UserProgramRole.objects.create(user=self.staff, program=self.program, role="staff", status="active")

        # PM
        self.pm = User.objects.create_user(username="pm", password="pass", display_name="Program Manager")
        UserProgramRole.objects.create(user=self.pm, program=self.program, role="program_manager", status="active")

        self.test_client = TestClient()

    def test_receptionist_can_leave_message(self):
        self.test_client.login(username="recep", password="pass")
        response = self.test_client.post(
            reverse("communications:leave_message", args=[self.client_file.pk]),
            {"message": "Client called to reschedule", "for_user": self.staff.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StaffMessage.objects.count(), 1)
        msg = StaffMessage.objects.first()
        self.assertEqual(msg.content, "Client called to reschedule")
        self.assertEqual(msg.left_by, self.receptionist)
        self.assertEqual(msg.for_user, self.staff)

    def test_receptionist_cannot_view_messages(self):
        self.test_client.login(username="recep", password="pass")
        response = self.test_client.get(
            reverse("communications:client_messages", args=[self.client_file.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_messages(self):
        msg = StaffMessage(client_file=self.client_file, left_by=self.receptionist, for_user=self.staff, author_program=self.program)
        msg.content = "Test message"
        msg.save()

        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(
            reverse("communications:client_messages", args=[self.client_file.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test message")

    def test_staff_can_mark_read(self):
        msg = StaffMessage(client_file=self.client_file, left_by=self.receptionist, for_user=self.staff, author_program=self.program)
        msg.content = "Test"
        msg.save()

        self.test_client.login(username="staff", password="pass")
        response = self.test_client.post(
            reverse("communications:mark_message_read", args=[self.client_file.pk, msg.pk])
        )
        msg.refresh_from_db()
        self.assertEqual(msg.status, "read")
        self.assertIsNotNone(msg.read_at)

    def test_leave_message_without_for_user(self):
        self.test_client.login(username="recep", password="pass")
        response = self.test_client.post(
            reverse("communications:leave_message", args=[self.client_file.pk]),
            {"message": "Documents dropped off at front desk"},
        )
        self.assertEqual(response.status_code, 302)
        msg = StaffMessage.objects.first()
        self.assertIsNone(msg.for_user)

    def test_pm_can_view_messages(self):
        msg = StaffMessage(client_file=self.client_file, left_by=self.receptionist, author_program=self.program)
        msg.content = "PM should see this"
        msg.save()

        self.test_client.login(username="pm", password="pass")
        response = self.test_client.get(
            reverse("communications:client_messages", args=[self.client_file.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PM should see this")

    def test_my_messages_page(self):
        msg = StaffMessage(client_file=self.client_file, left_by=self.receptionist, for_user=self.staff, author_program=self.program)
        msg.content = "Check inbox"
        msg.save()

        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(reverse("communications:my_messages"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check inbox")
