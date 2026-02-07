"""Tests for Phase 2 group tracking features.

Covers:
- Program detail shows groups section for group/both service models
- Individual note/plan buttons hidden for group-only programs
- Attendance report view and CSV export
- Group detail template bug fixes (session counts)
"""
from datetime import date, timedelta

from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.groups.models import (
    Group,
    GroupMembership,
    GroupSession,
    GroupSessionAttendance,
)
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramDetailGroupsSectionTest(TestCase):
    """Test that program detail page shows groups for group/both programs."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_group_program_shows_groups_section(self):
        """Program detail page shows groups section for group service model."""
        program = Program.objects.create(
            name="Youth Group", service_model="group",
        )
        Group.objects.create(
            name="Monday Group", program=program, group_type="service_group",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/programs/{program.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Monday Group")
        self.assertContains(resp, "Groups")

    def test_both_program_shows_groups_section(self):
        """Program detail page shows groups section for 'both' service model."""
        program = Program.objects.create(
            name="Youth Centre", service_model="both",
        )
        Group.objects.create(
            name="Art Workshop", program=program, group_type="service_group",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/programs/{program.pk}/")
        self.assertContains(resp, "Art Workshop")

    def test_individual_program_hides_groups_section(self):
        """Program detail page does NOT show groups section for individual service model."""
        program = Program.objects.create(
            name="Counselling", service_model="individual",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/programs/{program.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "groups-heading")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AttendanceReportTest(TestCase):
    """Test attendance report view and CSV export."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False,
        )
        self.program = Program.objects.create(
            name="Youth Group", service_model="group",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff", status="active",
        )
        self.group = Group.objects.create(
            name="Monday Group", program=self.program, group_type="service_group",
        )
        # Create a member (non-client for simplicity)
        self.member = GroupMembership.objects.create(
            group=self.group, member_name="Jane Doe", role="member",
        )
        # Create a session with attendance
        self.session = GroupSession(
            group=self.group,
            session_date=date.today(),
            facilitator=self.staff,
            group_vibe="solid",
        )
        self.session.notes = "Test session"
        self.session.save()
        GroupSessionAttendance.objects.create(
            group_session=self.session,
            membership=self.member,
            present=True,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_attendance_report_renders(self):
        """Attendance report page loads with attendance data."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/groups/{self.group.pk}/attendance/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jane Doe")
        self.assertContains(resp, "Attendance Report")

    def test_attendance_report_csv_export(self):
        """CSV export returns a CSV file with attendance data."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(
            f"/groups/{self.group.pk}/attendance/?format=csv"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("attachment", resp["Content-Disposition"])
        content = resp.content.decode("utf-8")
        self.assertIn("Jane Doe", content)

    def test_attendance_report_date_filter(self):
        """Date filter excludes sessions outside range."""
        self.client.login(username="staff", password="testpass123")
        # Filter to a date range that excludes today's session
        future = date.today() + timedelta(days=30)
        resp = self.client.get(
            f"/groups/{self.group.pk}/attendance/"
            f"?date_from={future}&date_to={future}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No attendance data")

    def test_attendance_report_access_control(self):
        """Users without program access cannot view attendance report."""
        other_user = User.objects.create_user(
            username="other", password="testpass123", is_admin=False,
        )
        self.client.login(username="other", password="testpass123")
        resp = self.client.get(f"/groups/{self.group.pk}/attendance/")
        self.assertEqual(resp.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GroupDetailSessionCountsTest(TestCase):
    """Test that group detail correctly shows present/total counts."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False,
        )
        self.program = Program.objects.create(
            name="Test Program", service_model="group",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff", status="active",
        )
        self.group = Group.objects.create(
            name="Test Group", program=self.program, group_type="service_group",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_group_detail_loads(self):
        """Group detail page loads successfully."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/groups/{self.group.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test Group")

    def test_group_detail_shows_session_counts(self):
        """Session cards show present/total member counts."""
        m1 = GroupMembership.objects.create(
            group=self.group, member_name="Alice", role="member",
        )
        m2 = GroupMembership.objects.create(
            group=self.group, member_name="Bob", role="member",
        )
        session = GroupSession(
            group=self.group,
            session_date=date.today(),
            facilitator=self.staff,
            group_vibe="solid",
        )
        session.notes = ""
        session.save()
        GroupSessionAttendance.objects.create(
            group_session=session, membership=m1, present=True,
        )
        GroupSessionAttendance.objects.create(
            group_session=session, membership=m2, present=False,
        )

        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/groups/{self.group.pk}/")
        self.assertEqual(resp.status_code, 200)
        # Should show "1/2 present"
        self.assertContains(resp, "1/2")
