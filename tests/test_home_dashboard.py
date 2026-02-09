"""Tests for home dashboard permissions — Front Desk vs Clinical Staff."""
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

        # Verify basic client counts are still visible
        self.assertEqual(response.context["active_count"], 1)
        self.assertEqual(response.context["total_count"], 1)

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

        # Basic sections should still appear
        self.assertIn("Active Participants", content)  # or "Active clients"
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
