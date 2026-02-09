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
    GroupSessionHighlight,
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
            name="Monday Group", program=program, group_type="group",
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
            name="Art Workshop", program=program, group_type="group",
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
            name="Monday Group", program=self.program, group_type="group",
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
            name="Test Group", program=self.program, group_type="group",
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


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SessionLogHappyPathTest(TestCase):
    """Test the session_log view: session creation, attendance, highlights, redirects, access."""

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
            name="Monday Group", program=self.program, group_type="group",
        )
        self.member1 = GroupMembership.objects.create(
            group=self.group, member_name="Alice", role="member",
        )
        self.member2 = GroupMembership.objects.create(
            group=self.group, member_name="Bob", role="member",
        )

    def tearDown(self):
        enc_module._fernet = None

    def _session_url(self):
        return f"/groups/{self.group.pk}/session/"

    def _valid_post_data(self, **overrides):
        """Return default valid POST data; override individual keys as needed."""
        data = {
            "session_date": "2026-02-07",
            "group_vibe": "great",
            "notes": "Great session",
            f"present_{self.member1.pk}": "on",
            f"present_{self.member2.pk}": "on",
            f"highlight_{self.member1.pk}": "Good progress",
            f"highlight_{self.member2.pk}": "",
        }
        data.update(overrides)
        return data

    def test_session_log_happy_path_creates_session(self):
        """POST with valid data creates a GroupSession with correct fields."""
        self.client.login(username="staff", password="testpass123")
        data = self._valid_post_data()
        self.client.post(self._session_url(), data)
        self.assertEqual(GroupSession.objects.count(), 1)
        session = GroupSession.objects.first()
        self.assertEqual(str(session.session_date), "2026-02-07")
        self.assertEqual(session.group_vibe, "great")
        self.assertEqual(session.notes, "Great session")
        self.assertEqual(session.group, self.group)

    def test_session_log_creates_attendance_records(self):
        """POST creates attendance records — checked members present, unchecked absent."""
        self.client.login(username="staff", password="testpass123")
        # member1 checked, member2 NOT checked (omitted from POST data)
        data = self._valid_post_data()
        del data[f"present_{self.member2.pk}"]
        self.client.post(self._session_url(), data)
        self.assertEqual(GroupSessionAttendance.objects.count(), 2)
        att1 = GroupSessionAttendance.objects.get(membership=self.member1)
        att2 = GroupSessionAttendance.objects.get(membership=self.member2)
        self.assertTrue(att1.present)
        self.assertFalse(att2.present)

    def test_session_log_saves_highlights(self):
        """POST with non-empty highlight text creates a GroupSessionHighlight."""
        self.client.login(username="staff", password="testpass123")
        data = self._valid_post_data()
        self.client.post(self._session_url(), data)
        self.assertEqual(GroupSessionHighlight.objects.count(), 1)
        highlight = GroupSessionHighlight.objects.first()
        self.assertEqual(highlight.membership, self.member1)
        self.assertEqual(highlight.notes, "Good progress")

    def test_session_log_empty_highlight_not_saved(self):
        """POST with empty highlight text does NOT create a GroupSessionHighlight."""
        self.client.login(username="staff", password="testpass123")
        # Both highlights empty
        data = self._valid_post_data()
        data[f"highlight_{self.member1.pk}"] = ""
        self.client.post(self._session_url(), data)
        self.assertEqual(GroupSessionHighlight.objects.count(), 0)

    def test_session_log_redirects_to_group_detail(self):
        """POST with valid data redirects (302) to the group detail page."""
        self.client.login(username="staff", password="testpass123")
        data = self._valid_post_data()
        resp = self.client.post(self._session_url(), data)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(str(self.group.pk), resp.url)

    def test_session_log_get_renders_form(self):
        """GET returns 200 and the page contains 'Session Date'."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(self._session_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Session Date")

    def test_session_log_access_denied_for_other_program(self):
        """User with a role in a different program gets 403."""
        other_program = Program.objects.create(
            name="Other Program", service_model="group",
        )
        other_user = User.objects.create_user(
            username="other", password="testpass123", is_admin=False,
        )
        UserProgramRole.objects.create(
            user=other_user, program=other_program, role="staff", status="active",
        )
        self.client.login(username="other", password="testpass123")
        data = self._valid_post_data()
        resp = self.client.post(self._session_url(), data)
        self.assertEqual(resp.status_code, 403)


# ======================================================================
# Group form validation tests (TEST-9)
# ======================================================================

from apps.groups.forms import (
    GroupForm,
    MembershipAddForm,
    ProjectOutcomeForm,
    SessionLogForm,
)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GroupFormValidationTest(TestCase):
    """Validate group-related form classes: membership, session log, outcome, and group form."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    # ------------------------------------------------------------------
    # MembershipAddForm
    # ------------------------------------------------------------------

    def test_membership_form_requires_one_of_client_or_name(self):
        """MembershipAddForm with neither client_file nor member_name is invalid."""
        form = MembershipAddForm(data={"role": "member"})
        self.assertFalse(form.is_valid())
        # Error should be a non-field error (raised via ValidationError in clean)
        self.assertTrue(form.non_field_errors())

    def test_membership_form_rejects_both_client_and_name(self):
        """MembershipAddForm with both client_file and member_name is invalid."""
        form = MembershipAddForm(data={
            "client_file": 1,
            "member_name": "Alice",
            "role": "member",
        })
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_membership_form_valid_with_name_only(self):
        """MembershipAddForm with just member_name is valid."""
        form = MembershipAddForm(data={
            "member_name": "Alice",
            "role": "member",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_membership_form_valid_with_client_only(self):
        """MembershipAddForm with just client_file is valid."""
        form = MembershipAddForm(data={
            "client_file": 1,
            "role": "member",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_membership_form_strips_whitespace_name(self):
        """MembershipAddForm with whitespace-only member_name (no client) is invalid."""
        form = MembershipAddForm(data={
            "member_name": "   ",
            "role": "member",
        })
        self.assertFalse(form.is_valid())

    # ------------------------------------------------------------------
    # GroupForm
    # ------------------------------------------------------------------

    def test_group_form_program_queryset_filtered(self):
        """GroupForm program queryset contains only group/both programs, not individual."""
        group_prog = Program.objects.create(
            name="Youth Group", service_model="group", status="active",
        )
        individual_prog = Program.objects.create(
            name="Counselling", service_model="individual", status="active",
        )
        form = GroupForm()
        qs = form.fields["program"].queryset
        self.assertIn(group_prog, qs)
        self.assertNotIn(individual_prog, qs)

    # ------------------------------------------------------------------
    # SessionLogForm
    # ------------------------------------------------------------------

    def test_session_log_form_valid_with_minimal_data(self):
        """SessionLogForm with just session_date is valid."""
        form = SessionLogForm(data={"session_date": "2026-03-01"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_session_log_form_missing_date_invalid(self):
        """SessionLogForm without session_date is invalid."""
        form = SessionLogForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("session_date", form.errors)

    # ------------------------------------------------------------------
    # ProjectOutcomeForm
    # ------------------------------------------------------------------

    def test_project_outcome_form_requires_description(self):
        """ProjectOutcomeForm without description is invalid."""
        form = ProjectOutcomeForm(data={
            "outcome_date": "2026-03-01",
            "description": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)
