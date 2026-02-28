"""Tests for last contact date display and sorting (UXP-CONTACT)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client as TestClient, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.clients.views import _get_last_contact_dates
from apps.communications.models import Communication
from apps.events.models import Event, Meeting
from apps.notes.models import ProgressNote, ProgressNoteTemplate
from apps.programs.models import Program, UserProgramRole

User = get_user_model()


class LastContactHelperTests(TestCase):
    """Test the _get_last_contact_dates batch helper."""

    databases = ["default", "audit"]

    def setUp(self):
        self.program = Program.objects.create(name="Test")
        self.staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(user=self.staff, program=self.program, role="staff", status="active")

        self.client1 = ClientFile.objects.create(first_name="Alice", last_name="A")
        self.client2 = ClientFile.objects.create(first_name="Bob", last_name="B")
        self.client3 = ClientFile.objects.create(first_name="Carol", last_name="C")
        for c in [self.client1, self.client2, self.client3]:
            ClientProgramEnrolment.objects.create(client_file=c, program=self.program, status="active")

        self.template = ProgressNoteTemplate.objects.create(name="T", owning_program=self.program)

    def test_empty_input(self):
        result = _get_last_contact_dates([])
        self.assertEqual(result, {})

    def test_no_contact_returns_none(self):
        result = _get_last_contact_dates([self.client1.pk])
        self.assertIsNone(result[self.client1.pk])

    def test_picks_up_note_date(self):
        note = ProgressNote(
            client_file=self.client1, template=self.template,
            author=self.staff, author_program=self.program,
            interaction_type="session", status="default",
        )
        note.notes_text = "Test"
        note.save()

        result = _get_last_contact_dates([self.client1.pk])
        self.assertIsNotNone(result[self.client1.pk])

    def test_picks_up_comm_date(self):
        comm = Communication(
            client_file=self.client2, direction="outbound", channel="phone",
            logged_by=self.staff, author_program=self.program,
        )
        comm.content = "Call"
        comm.save()

        result = _get_last_contact_dates([self.client2.pk])
        self.assertIsNotNone(result[self.client2.pk])

    def test_picks_up_meeting_date(self):
        event = Event.objects.create(
            client_file=self.client3,
            title="Test",
            start_timestamp=timezone.now(),
            author_program=self.program,
        )
        meeting = Meeting.objects.create(event=event, status="completed")
        meeting.attendees.add(self.staff)

        result = _get_last_contact_dates([self.client3.pk])
        self.assertIsNotNone(result[self.client3.pk])

    def test_picks_most_recent_across_types(self):
        # Old note (10 days ago)
        note = ProgressNote(
            client_file=self.client1, template=self.template,
            author=self.staff, author_program=self.program,
            interaction_type="session", status="default",
        )
        note.notes_text = "Old"
        note.save()
        ProgressNote.objects.filter(pk=note.pk).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        # Recent comm (1 day ago)
        comm = Communication(
            client_file=self.client1, direction="outbound", channel="phone",
            logged_by=self.staff, author_program=self.program,
        )
        comm.content = "Recent"
        comm.save()
        Communication.objects.filter(pk=comm.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        result = _get_last_contact_dates([self.client1.pk])
        last = result[self.client1.pk]
        self.assertIsNotNone(last)
        # Should be ~1 day ago (the comm), not 10 days ago (the note)
        self.assertTrue(last > timezone.now() - timedelta(days=2))

    def test_batch_multiple_clients(self):
        # Note for client1
        note = ProgressNote(
            client_file=self.client1, template=self.template,
            author=self.staff, author_program=self.program,
            interaction_type="session", status="default",
        )
        note.notes_text = "Test"
        note.save()

        result = _get_last_contact_dates([self.client1.pk, self.client2.pk, self.client3.pk])
        self.assertIsNotNone(result[self.client1.pk])
        self.assertIsNone(result[self.client2.pk])
        self.assertIsNone(result[self.client3.pk])


class ClientListLastContactTests(TestCase):
    """Test last contact column in client list view."""

    databases = ["default", "audit"]

    def setUp(self):
        self.program = Program.objects.create(name="Test")
        self.staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(user=self.staff, program=self.program, role="staff", status="active")

        self.client1 = ClientFile.objects.create(first_name="Alice", last_name="A")
        self.client2 = ClientFile.objects.create(first_name="Bob", last_name="B")
        for c in [self.client1, self.client2]:
            ClientProgramEnrolment.objects.create(client_file=c, program=self.program, status="active")

        self.template = ProgressNoteTemplate.objects.create(name="T", owning_program=self.program)
        self.test_client = TestClient()

    def test_last_contact_column_appears(self):
        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(reverse("clients:client_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Last Contact")

    def test_never_shown_for_no_contact(self):
        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(reverse("clients:client_list"))
        self.assertContains(response, "Never")

    def test_date_shown_for_contact(self):
        note = ProgressNote(
            client_file=self.client1, template=self.template,
            author=self.staff, author_program=self.program,
            interaction_type="session", status="default",
        )
        note.notes_text = "Test"
        note.save()

        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(reverse("clients:client_list"))
        self.assertContains(response, "ago")

    def test_sort_by_last_contact(self):
        # Client1: recent note
        note1 = ProgressNote(
            client_file=self.client1, template=self.template,
            author=self.staff, author_program=self.program,
            interaction_type="session", status="default",
        )
        note1.notes_text = "Recent"
        note1.save()

        # Client2: old note
        note2 = ProgressNote(
            client_file=self.client2, template=self.template,
            author=self.staff, author_program=self.program,
            interaction_type="session", status="default",
        )
        note2.notes_text = "Old"
        note2.save()
        ProgressNote.objects.filter(pk=note2.pk).update(
            created_at=timezone.now() - timedelta(days=30)
        )

        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(reverse("clients:client_list"), {"sort": "last_contact"})
        content = response.content.decode()
        # Alice (recent) should appear before Bob (old)
        alice_pos = content.find("Alice")
        bob_pos = content.find("Bob")
        self.assertTrue(alice_pos < bob_pos, "Most recently contacted should appear first")

    def test_sort_by_name_default(self):
        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(reverse("clients:client_list"))
        content = response.content.decode()
        alice_pos = content.find("Alice")
        bob_pos = content.find("Bob")
        self.assertTrue(alice_pos < bob_pos, "Default sort should be alphabetical")

    def test_sort_preserves_filters(self):
        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(
            reverse("clients:client_list"),
            {"sort": "last_contact", "status": "active"},
        )
        self.assertEqual(response.status_code, 200)
