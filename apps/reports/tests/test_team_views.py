"""Tests for team meeting view (UXP-TEAM)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client as TestClient, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.communications.models import Communication
from apps.notes.models import ProgressNote, ProgressNoteTemplate
from apps.programs.models import Program, UserProgramRole

User = get_user_model()


class TeamMeetingViewPermissionTests(TestCase):
    """Test access control for team meeting view."""

    databases = ["default", "audit"]

    def setUp(self):
        self.program = Program.objects.create(name="Test Program")
        self.test_client = TestClient()

    def test_pm_can_access(self):
        pm = User.objects.create_user(username="pm", password="pass")
        UserProgramRole.objects.create(user=pm, program=self.program, role="program_manager", status="active")
        self.test_client.login(username="pm", password="pass")
        response = self.test_client.get(reverse("reports:team_meeting_view"))
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_access(self):
        staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(user=staff, program=self.program, role="staff", status="active")
        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(reverse("reports:team_meeting_view"))
        self.assertEqual(response.status_code, 403)

    def test_receptionist_cannot_access(self):
        recep = User.objects.create_user(username="recep", password="pass")
        UserProgramRole.objects.create(user=recep, program=self.program, role="receptionist", status="active")
        self.test_client.login(username="recep", password="pass")
        response = self.test_client.get(reverse("reports:team_meeting_view"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access(self):
        admin = User.objects.create_user(username="admin", password="pass")
        admin.is_admin = True
        admin.save()
        UserProgramRole.objects.create(user=admin, program=self.program, role="staff", status="active")
        self.test_client.login(username="admin", password="pass")
        response = self.test_client.get(reverse("reports:team_meeting_view"))
        self.assertEqual(response.status_code, 200)


class TeamMeetingViewContentTests(TestCase):
    """Test content display in team meeting view."""

    databases = ["default", "audit"]

    def setUp(self):
        self.program = Program.objects.create(name="Youth Services")
        self.pm = User.objects.create_user(username="pm", password="pass", display_name="Program Manager")
        UserProgramRole.objects.create(user=self.pm, program=self.program, role="program_manager", status="active")

        self.staff1 = User.objects.create_user(username="staff1", password="pass", display_name="Alice Smith")
        UserProgramRole.objects.create(user=self.staff1, program=self.program, role="staff", status="active")

        self.staff2 = User.objects.create_user(username="staff2", password="pass", display_name="Bob Jones")
        UserProgramRole.objects.create(user=self.staff2, program=self.program, role="staff", status="active")

        self.client_file = ClientFile.objects.create(first_name="Test", last_name="Client")
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.program, status="enrolled")

        self.template = ProgressNoteTemplate.objects.create(name="Test Template", owning_program=self.program)

        self.test_client = TestClient()
        self.test_client.login(username="pm", password="pass")

    def test_shows_staff_members(self):
        response = self.test_client.get(reverse("reports:team_meeting_view"))
        self.assertContains(response, "Alice")
        self.assertContains(response, "Bob")

    def test_counts_notes(self):
        note = ProgressNote(
            client_file=self.client_file,
            template=self.template,
            author=self.staff1,
            author_program=self.program,
            note_type="full",
            interaction_type="session",
            status="default",
        )
        note.notes_text = "Test"
        note.save()

        response = self.test_client.get(reverse("reports:team_meeting_view"))
        self.assertEqual(response.status_code, 200)
        # Alice should have 1 note
        self.assertContains(response, "<strong>1</strong>")

    def test_counts_communications(self):
        comm = Communication(
            client_file=self.client_file,
            direction="outbound",
            channel="phone",
            logged_by=self.staff1,
            author_program=self.program,
        )
        comm.content = "Test call"
        comm.save()

        response = self.test_client.get(reverse("reports:team_meeting_view"))
        self.assertEqual(response.status_code, 200)

    def test_date_filter_7_days(self):
        """Notes older than 7 days don't show in default view."""
        old_note = ProgressNote(
            client_file=self.client_file,
            template=self.template,
            author=self.staff1,
            author_program=self.program,
            note_type="full",
            interaction_type="session",
            status="default",
        )
        old_note.notes_text = "Old"
        old_note.save()
        # Backdate
        ProgressNote.objects.filter(pk=old_note.pk).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        response = self.test_client.get(reverse("reports:team_meeting_view"), {"days": "7"})
        self.assertEqual(response.status_code, 200)

    def test_date_filter_30_days(self):
        """Notes within 30 days show with 30-day filter."""
        note = ProgressNote(
            client_file=self.client_file,
            template=self.template,
            author=self.staff1,
            author_program=self.program,
            note_type="full",
            interaction_type="session",
            status="default",
        )
        note.notes_text = "Recent-ish"
        note.save()
        # Backdate to 15 days ago
        ProgressNote.objects.filter(pk=note.pk).update(
            created_at=timezone.now() - timedelta(days=15)
        )

        response = self.test_client.get(reverse("reports:team_meeting_view"), {"days": "30"})
        self.assertEqual(response.status_code, 200)

    def test_program_filter(self):
        """Program filter limits to selected program."""
        other_program = Program.objects.create(name="Other Program")
        other_staff = User.objects.create_user(username="other", password="pass", display_name="Other Staff")
        UserProgramRole.objects.create(user=other_staff, program=other_program, role="staff", status="active")
        # PM also has access to other program
        UserProgramRole.objects.create(user=self.pm, program=other_program, role="program_manager", status="active")

        # Filter to main program only
        response = self.test_client.get(
            reverse("reports:team_meeting_view"),
            {"program": str(self.program.pk)}
        )
        self.assertContains(response, "Alice")
        self.assertNotContains(response, "Other")
