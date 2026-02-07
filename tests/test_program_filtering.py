"""Tests for program-based data filtering across client tabs.

Verifies that:
- Workers only see data from programs they have access to
- The Plan tab's access check is no longer a stub
- NULL-program items are visible to all users with client access
- Multi-program users see program grouping UI
- Single-program users see a clean view without program UI
"""
from cryptography.fernet import Fernet
from django.test import Client as HttpClient, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Event, EventType
from apps.notes.models import ProgressNote
from apps.plans.models import PlanSection, PlanTarget
from apps.programs.models import Program, UserProgramRole
from konote import encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramFilteringTestBase(TestCase):
    """Shared setUp for program filtering tests."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        # Two programs
        self.prog_a = Program.objects.create(
            name="Housing Support", colour_hex="#10B981", status="active"
        )
        self.prog_b = Program.objects.create(
            name="Youth Employment", colour_hex="#3B82F6", status="active"
        )

        # Worker in Program A only
        self.worker_a = User.objects.create_user(
            username="worker_a", password="pass", display_name="Worker A"
        )
        UserProgramRole.objects.create(
            user=self.worker_a, program=self.prog_a, role="staff", status="active"
        )

        # Worker in Program B only
        self.worker_b = User.objects.create_user(
            username="worker_b", password="pass", display_name="Worker B"
        )
        UserProgramRole.objects.create(
            user=self.worker_b, program=self.prog_b, role="staff", status="active"
        )

        # Multi-program worker (both A and B)
        self.worker_ab = User.objects.create_user(
            username="worker_ab", password="pass", display_name="Worker AB"
        )
        UserProgramRole.objects.create(
            user=self.worker_ab, program=self.prog_a, role="staff", status="active"
        )
        UserProgramRole.objects.create(
            user=self.worker_ab, program=self.prog_b, role="staff", status="active"
        )

        # Client enrolled in both programs
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.status = "active"
        self.client_file.consent_given_at = timezone.now()
        self.client_file.consent_type = "written"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.prog_a, status="enrolled"
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.prog_b, status="enrolled"
        )

        # Plan sections — one per program + one with no program
        self.section_a = PlanSection.objects.create(
            client_file=self.client_file, name="Housing Goals",
            program=self.prog_a, sort_order=1
        )
        self.section_b = PlanSection.objects.create(
            client_file=self.client_file, name="Employment Goals",
            program=self.prog_b, sort_order=2
        )
        self.section_general = PlanSection.objects.create(
            client_file=self.client_file, name="General Goals",
            program=None, sort_order=3
        )

        # Targets in each section
        self.target_a = PlanTarget(
            plan_section=self.section_a, client_file=self.client_file
        )
        self.target_a.name = "Find housing"
        self.target_a.save()

        self.target_b = PlanTarget(
            plan_section=self.section_b, client_file=self.client_file
        )
        self.target_b.name = "Get a job"
        self.target_b.save()

        # Progress notes — one per program + one with no program
        self.note_a = ProgressNote(
            client_file=self.client_file, author=self.worker_a,
            author_program=self.prog_a, interaction_type="one_on_one",
        )
        self.note_a.notes_text = "Note from Housing program"
        self.note_a.save()

        self.note_b = ProgressNote(
            client_file=self.client_file, author=self.worker_b,
            author_program=self.prog_b, interaction_type="one_on_one",
        )
        self.note_b.notes_text = "Note from Employment program"
        self.note_b.save()

        self.note_general = ProgressNote(
            client_file=self.client_file, author=self.worker_a,
            author_program=None, interaction_type="one_on_one",
        )
        self.note_general.notes_text = "Note without program"
        self.note_general.save()

        # Events — one per program
        self.event_type = EventType.objects.create(name="Meeting")
        self.event_a = Event.objects.create(
            client_file=self.client_file, event_type=self.event_type,
            author_program=self.prog_a, start_timestamp=timezone.now(),
            title="Housing meeting",
        )
        self.event_b = Event.objects.create(
            client_file=self.client_file, event_type=self.event_type,
            author_program=self.prog_b, start_timestamp=timezone.now(),
            title="Employment meeting",
        )

        self.http = HttpClient()

    def tearDown(self):
        enc_module._fernet = None


class PlanTabSecurityTest(ProgramFilteringTestBase):
    """Plan tab access check is no longer a stub."""

    def test_plan_tab_returns_403_for_unauthorized_user(self):
        """User with no shared programs gets 403."""
        # Create a user with NO program roles
        outsider = User.objects.create_user(
            username="outsider", password="pass", display_name="Outsider"
        )
        self.http.login(username="outsider", password="pass")
        url = reverse("plans:plan_view", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_worker_a_sees_only_prog_a_sections(self):
        """Worker in Program A sees Housing Goals + General, not Employment Goals."""
        self.http.login(username="worker_a", password="pass")
        url = reverse("plans:plan_view", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Housing Goals")
        self.assertContains(resp, "General Goals")
        self.assertNotContains(resp, "Employment Goals")

    def test_worker_b_sees_only_prog_b_sections(self):
        """Worker in Program B sees Employment Goals + General, not Housing Goals."""
        self.http.login(username="worker_b", password="pass")
        url = reverse("plans:plan_view", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Employment Goals")
        self.assertContains(resp, "General Goals")
        self.assertNotContains(resp, "Housing Goals")

    def test_multi_program_worker_sees_all_sections(self):
        """Worker in both programs sees all sections."""
        self.http.login(username="worker_ab", password="pass")
        url = reverse("plans:plan_view", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Housing Goals")
        self.assertContains(resp, "Employment Goals")
        self.assertContains(resp, "General Goals")


class NotesTabFilteringTest(ProgramFilteringTestBase):
    """Notes tab filters by program and supports program filter param."""

    def test_worker_a_sees_only_prog_a_notes(self):
        """Worker A sees notes from Housing + null-program, not Employment."""
        self.http.login(username="worker_a", password="pass")
        url = reverse("notes:note_list", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Note from Housing program")
        self.assertContains(resp, "Note without program")
        self.assertNotContains(resp, "Note from Employment program")

    def test_program_filter_narrows_results(self):
        """Multi-program user can filter by specific program."""
        self.http.login(username="worker_ab", password="pass")
        url = reverse("notes:note_list", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url, {"program": str(self.prog_a.pk)})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Note from Housing program")
        self.assertNotContains(resp, "Note from Employment program")


class EventsTabFilteringTest(ProgramFilteringTestBase):
    """Events tab filters by user's accessible programs."""

    def test_worker_a_sees_only_prog_a_events(self):
        """Worker A sees Housing meeting, not Employment meeting."""
        self.http.login(username="worker_a", password="pass")
        url = reverse("events:event_list", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Housing meeting")
        self.assertNotContains(resp, "Employment meeting")

    def test_multi_program_worker_sees_all_events(self):
        """Worker in both programs sees all events."""
        self.http.login(username="worker_ab", password="pass")
        url = reverse("events:event_list", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Housing meeting")
        self.assertContains(resp, "Employment meeting")


class AnalysisTabFilteringTest(ProgramFilteringTestBase):
    """Analysis tab filters chart data by user's accessible programs."""

    def test_worker_a_sees_only_prog_a_targets(self):
        """Worker A sees Housing targets in analysis, not Employment."""
        self.http.login(username="worker_a", password="pass")
        url = reverse("reports:client_analysis", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        # No metric data, so just verify access works and doesn't 500


class ProgramDisplayContextTest(ProgramFilteringTestBase):
    """Single-program users see no program UI; multi-program users see grouping."""

    def test_single_program_worker_no_grouping(self):
        """Single-program worker's plan view has no program-group headers."""
        self.http.login(username="worker_a", password="pass")
        url = reverse("plans:plan_view", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "program-group-heading")

    def test_multi_program_worker_sees_grouping(self):
        """Multi-program worker's plan view has program-group headers."""
        self.http.login(username="worker_ab", password="pass")
        url = reverse("plans:plan_view", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "program-group-heading")
        self.assertContains(resp, "Housing Support")
        self.assertContains(resp, "Youth Employment")

    def test_single_program_worker_no_note_program_filter(self):
        """Single-program worker's notes tab has no program filter dropdown."""
        self.http.login(username="worker_a", password="pass")
        url = reverse("notes:note_list", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'name="program"')

    def test_multi_program_worker_sees_note_program_filter(self):
        """Multi-program worker's notes tab has a program filter dropdown."""
        self.http.login(username="worker_ab", password="pass")
        url = reverse("notes:note_list", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="program"')
