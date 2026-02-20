"""Tests for home dashboard permissions — Front Desk, Staff, PM, Executive."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Alert
from apps.notes.models import ProgressNote
from apps.programs.models import Program, UserProgramRole

User = get_user_model()


class HomeDashboardPermissionsTest(TestCase):
    """Verify Front Desk cannot see clinical data on home dashboard."""

    def setUp(self):
        # Create program
        self.program = Program.objects.create(name="Test Program", status="active")

        # Create users with different roles
        self.receptionist = User.objects.create_user(
            username="frontdesk", password="testpass123", is_demo=False
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_demo=False
        )

        # Assign roles
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program, role="receptionist"
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff"
        )

        # Create a client
        self.client_file = ClientFile.objects.create(
            first_name="Jane",
            last_name="Doe",
            birth_date="1990-01-01",
            status="active",
            is_demo=False,
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled"
        )

        # Create clinical data
        self.alert = Alert.objects.create(
            client_file=self.client_file,
            content="Test alert",
            status="default",
        )
        self.note = ProgressNote.objects.create(
            client_file=self.client_file,
            author=self.staff,
            notes_text="Test note",
            status="default",
        )

    def test_receptionist_cannot_see_clinical_metrics(self):
        """Front Desk should not see alerts, notes, or follow-ups on home dashboard."""
        self.client.login(username="frontdesk", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_receptionist"])

        # Verify clinical data is empty for receptionist
        self.assertEqual(response.context["alert_count"], 0)
        self.assertEqual(response.context["notes_today_count"], 0)
        self.assertEqual(response.context["follow_up_count"], 0)
        self.assertEqual(response.context["needs_attention_count"], 0)
        self.assertEqual(len(response.context["active_alerts"]), 0)
        self.assertEqual(len(response.context["pending_follow_ups"]), 0)
        self.assertEqual(len(response.context["needs_attention"]), 0)

        # Stats are not shown to Front Desk — counts are zeroed out
        self.assertEqual(response.context["active_count"], 0)
        self.assertEqual(response.context["total_count"], 0)

    def test_staff_can_see_clinical_metrics(self):
        """Clinical staff should see full dashboard with alerts, notes, follow-ups."""
        self.client.login(username="staff", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_receptionist"])

        # Verify clinical data is present for staff
        self.assertEqual(response.context["alert_count"], 1)
        self.assertGreaterEqual(
            len(response.context["active_alerts"]), 1
        )  # Alert should be visible

        # Verify basic client counts
        self.assertEqual(response.context["active_count"], 1)
        self.assertEqual(response.context["total_count"], 1)

    def test_receptionist_dashboard_html_hides_clinical_sections(self):
        """Front Desk dashboard should not render clinical data sections in HTML."""
        self.client.login(username="frontdesk", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # These sections should NOT appear for Front Desk
        self.assertNotIn("Active Alerts", content)
        self.assertNotIn("Notes Today", content)
        self.assertNotIn("Follow-ups Due", content)
        self.assertNotIn("Needs Attention", content)
        self.assertNotIn("Priority Items", content)

        # Stats row should NOT appear for Front Desk either
        self.assertNotIn("Active Participants", content)

        # Basic sections should still appear
        self.assertIn("Recently Viewed", content)

    def test_staff_dashboard_html_shows_clinical_sections(self):
        """Clinical staff dashboard should render all sections including clinical data."""
        self.client.login(username="staff", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # These sections SHOULD appear for staff
        self.assertIn("Active Alerts", content)
        self.assertIn("Notes Today", content)
        self.assertIn("Follow-ups Due", content)
        self.assertIn("Needs Attention", content)
        self.assertIn("Priority Items", content)


class HomeDashboardRoleBasedTest(TestCase):
    """Verify PM and executive role-based dashboard sections (DASH-ROLES1)."""

    def setUp(self):
        self.program_a = Program.objects.create(name="Program A", status="active")
        self.program_b = Program.objects.create(name="Program B", status="active")

        # PM user — program_manager on program A only
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_demo=False
        )
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role="program_manager"
        )

        # Executive user — executive on program A
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_demo=False
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role="executive"
        )

        # Executive-only user — executive on program B, no other roles
        self.exec_only_user = User.objects.create_user(
            username="exec_only", password="testpass123", is_demo=False
        )
        UserProgramRole.objects.create(
            user=self.exec_only_user, program=self.program_b, role="executive"
        )

        # Staff user
        self.staff_user = User.objects.create_user(
            username="staff2", password="testpass123", is_demo=False
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role="staff"
        )

        # Receptionist user
        self.receptionist_user = User.objects.create_user(
            username="frontdesk2", password="testpass123", is_demo=False
        )
        UserProgramRole.objects.create(
            user=self.receptionist_user, program=self.program_a, role="receptionist"
        )

        # Create a client enrolled in program A
        self.client_file = ClientFile.objects.create(
            first_name="Alex",
            last_name="Smith",
            birth_date="1985-06-15",
            status="active",
            is_demo=False,
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program_a, status="enrolled"
        )

    def test_pm_sees_program_summary(self):
        """PM gets is_pm=True in context and sees program health section."""
        self.client.login(username="pm", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_pm"])
        self.assertFalse(response.context["is_executive"])
        self.assertIsNotNone(response.context["pm_program_stats"])
        self.assertGreaterEqual(len(response.context["pm_program_stats"]), 1)

        content = response.content.decode()
        self.assertIn("Program Health", content)

    def test_executive_sees_aggregate_metrics(self):
        """Executive gets is_executive=True and sees de-identified summary."""
        self.client.login(username="exec", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_executive"])
        self.assertFalse(response.context["is_pm"])
        self.assertIsNotNone(response.context["executive_data"])

        content = response.content.decode()
        self.assertIn("Executive Overview", content)
        # Executive should NOT see staff-specific priority items
        self.assertNotIn("Priority Items", content)

    def test_pm_gets_only_assigned_programs(self):
        """PM only sees stats for programs they manage, not all programs."""
        self.client.login(username="pm", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        pm_stats = response.context["pm_program_stats"]

        # PM is assigned to program_a only — should not see program_b
        program_ids = {s["program"].pk for s in pm_stats}
        self.assertIn(self.program_a.pk, program_ids)
        self.assertNotIn(self.program_b.pk, program_ids)

    def test_executive_only_user_detected(self):
        """User with only executive role (no staff/PM) is correctly identified."""
        self.client.login(username="exec_only", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_executive"])
        self.assertFalse(response.context["is_pm"])
        self.assertIsNotNone(response.context["executive_data"])

    def test_staff_does_not_see_pm_section(self):
        """Staff user does not get PM or executive content."""
        self.client.login(username="staff2", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_pm"])
        self.assertFalse(response.context["is_executive"])
        self.assertIsNone(response.context["pm_program_stats"])
        self.assertIsNone(response.context["executive_data"])

        content = response.content.decode()
        self.assertNotIn("Program Health", content)
        self.assertNotIn("Executive Overview", content)

    def test_receptionist_unchanged(self):
        """Receptionist still sees limited view with no PM/executive sections."""
        self.client.login(username="frontdesk2", password="testpass123")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_receptionist"])
        self.assertFalse(response.context["is_pm"])
        self.assertFalse(response.context["is_executive"])

        content = response.content.decode()
        self.assertNotIn("Program Health", content)
        self.assertNotIn("Executive Overview", content)
        self.assertNotIn("Priority Items", content)
        self.assertIn("Recently Viewed", content)
