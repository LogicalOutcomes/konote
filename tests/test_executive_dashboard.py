"""Tests for the executive dashboard view and metric helpers."""
from datetime import timedelta

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Alert, Event, Meeting
from apps.groups.models import Group, GroupMembership, GroupSession, GroupSessionAttendance
from apps.notes.models import ProgressNote
from apps.plans.models import PlanSection, PlanTarget
from apps.programs.models import Program, UserProgramRole
from apps.registration.models import RegistrationLink, RegistrationSubmission
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExecutiveDashboardViewTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123"
        )
        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6")
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.prog_a, role="executive"
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.prog_b, role="executive"
        )

    def _create_client(self, status="active", programs=None):
        cf = ClientFile()
        cf.first_name = "Test"
        cf.last_name = "Client"
        cf.status = status
        cf.save()
        if programs:
            for p in programs:
                ClientProgramEnrolment.objects.create(client_file=cf, program=p)
        return cf

    def test_dashboard_loads(self):
        self.http.login(username="exec", password="testpass123")
        resp = self.http.get("/clients/executive/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Executive Overview")

    def test_dashboard_requires_login(self):
        resp = self.http.get("/clients/executive/")
        self.assertEqual(resp.status_code, 302)

    def test_no_programs_shows_empty_state(self):
        no_prog_user = User.objects.create_user(
            username="noprog", password="testpass123"
        )
        self.http.login(username="noprog", password="testpass123")
        resp = self.http.get("/clients/executive/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No programs assigned")

    def test_active_count(self):
        self._create_client("active", [self.prog_a])
        self._create_client("active", [self.prog_a])
        self._create_client("inactive", [self.prog_a])

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get("/clients/executive/")
        self.assertEqual(resp.context["total_active"], 2)

    def test_without_notes_count(self):
        cf1 = self._create_client("active", [self.prog_a])
        cf2 = self._create_client("active", [self.prog_a])

        # cf1 has a note this month, cf2 does not
        ProgressNote.objects.create(
            client_file=cf1,
            author=self.exec_user,
            author_program=self.prog_a,
        )

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get("/clients/executive/")
        self.assertEqual(resp.context["without_notes"], 1)

    def test_overdue_followups(self):
        cf = self._create_client("active", [self.prog_a])
        yesterday = timezone.now().date() - timedelta(days=1)

        # Overdue follow-up
        ProgressNote.objects.create(
            client_file=cf,
            author=self.exec_user,
            author_program=self.prog_a,
            follow_up_date=yesterday,
        )
        # Completed follow-up (should not count)
        ProgressNote.objects.create(
            client_file=cf,
            author=self.exec_user,
            author_program=self.prog_a,
            follow_up_date=yesterday,
            follow_up_completed_at=timezone.now(),
        )

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get("/clients/executive/")
        self.assertEqual(resp.context["overdue_followups"], 1)

    def test_program_filter_valid(self):
        self._create_client("active", [self.prog_a])
        self._create_client("active", [self.prog_b])

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get(f"/clients/executive/?program={self.prog_a.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_active"], 1)
        self.assertEqual(resp.context["selected_program_id"], self.prog_a.pk)
        self.assertEqual(len(resp.context["program_stats"]), 1)

    def test_program_filter_invalid_ignored(self):
        self._create_client("active", [self.prog_a])

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get("/clients/executive/?program=abc")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["selected_program_id"])

    def test_program_filter_unauthorized_ignored(self):
        """User cannot filter to a program they don't have access to."""
        other_prog = Program.objects.create(name="Secret Program", colour_hex="#FF0000")

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get(f"/clients/executive/?program={other_prog.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["selected_program_id"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExecutiveDashboardHelperTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(username="worker", password="testpass123")
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        self.now = timezone.now()
        self.month_start = self.now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _create_client(self, status="active"):
        cf = ClientFile()
        cf.first_name = "Test"
        cf.last_name = "Client"
        cf.status = status
        cf.save()
        ClientProgramEnrolment.objects.create(client_file=cf, program=self.program)
        return cf

    def test_engagement_quality(self):
        from apps.clients.dashboard_views import _calc_engagement_quality

        cf = self._create_client()
        # 2 engaged, 1 guarded = 67%
        for obs in ["engaged", "valuing", "guarded"]:
            ProgressNote.objects.create(
                client_file=cf,
                author=self.user,
                author_program=self.program,
                engagement_observation=obs,
            )
        result = _calc_engagement_quality(self.program, self.month_start)
        self.assertEqual(result, 67)

    def test_engagement_quality_excludes_blank(self):
        from apps.clients.dashboard_views import _calc_engagement_quality

        cf = self._create_client()
        ProgressNote.objects.create(
            client_file=cf,
            author=self.user,
            author_program=self.program,
            engagement_observation="",
        )
        ProgressNote.objects.create(
            client_file=cf,
            author=self.user,
            author_program=self.program,
            engagement_observation="engaged",
        )
        result = _calc_engagement_quality(self.program, self.month_start)
        self.assertEqual(result, 100)

    def test_engagement_quality_no_data(self):
        from apps.clients.dashboard_views import _calc_engagement_quality

        result = _calc_engagement_quality(self.program, self.month_start)
        self.assertIsNone(result)

    def test_goal_completion(self):
        from apps.clients.dashboard_views import _calc_goal_completion

        cf = self._create_client()
        section = PlanSection.objects.create(
            client_file=cf, name="Goals", program=self.program
        )
        PlanTarget.objects.create(plan_section=section, client_file=cf, status="completed")
        PlanTarget.objects.create(plan_section=section, client_file=cf, status="default")
        result = _calc_goal_completion(self.program)
        self.assertEqual(result, 50)

    def test_goal_completion_no_targets(self):
        from apps.clients.dashboard_views import _calc_goal_completion

        result = _calc_goal_completion(self.program)
        self.assertIsNone(result)

    def test_no_show_rate(self):
        from apps.clients.dashboard_views import _calc_no_show_rate

        cf = self._create_client()
        for status in ["completed", "completed", "no_show"]:
            event = Event.objects.create(
                client_file=cf,
                author_program=self.program,
                start_timestamp=self.now,
            )
            Meeting.objects.create(event=event, status=status)
        result = _calc_no_show_rate(self.program, self.month_start)
        self.assertEqual(result, 33)

    def test_no_show_rate_no_meetings(self):
        from apps.clients.dashboard_views import _calc_no_show_rate

        result = _calc_no_show_rate(self.program, self.month_start)
        self.assertIsNone(result)

    def test_intake_pending(self):
        from apps.clients.dashboard_views import _count_intake_pending

        link = RegistrationLink.objects.create(
            program=self.program,
            title="Apply",
            created_by=self.user,
        )
        RegistrationSubmission.objects.create(
            registration_link=link, status="pending"
        )
        RegistrationSubmission.objects.create(
            registration_link=link, status="approved"
        )
        result = _count_intake_pending(self.program)
        self.assertEqual(result, 1)

    def test_group_attendance(self):
        from apps.clients.dashboard_views import _calc_group_attendance

        cf = self._create_client()
        group = Group.objects.create(
            name="Test Group", program=self.program, status="active"
        )
        member = GroupMembership.objects.create(group=group, client_file=cf)
        session = GroupSession.objects.create(
            group=group,
            session_date=self.now.date(),
            facilitator=self.user,
        )
        GroupSessionAttendance.objects.create(
            group_session=session, membership=member, present=True
        )
        # Add a second member who was absent
        cf2 = self._create_client()
        member2 = GroupMembership.objects.create(group=group, client_file=cf2)
        GroupSessionAttendance.objects.create(
            group_session=session, membership=member2, present=False
        )
        result = _calc_group_attendance(self.program, self.month_start)
        self.assertEqual(result, 50)

    def test_active_alerts(self):
        from apps.clients.dashboard_views import _count_active_alerts

        cf = self._create_client()
        Alert.objects.create(
            client_file=cf, status="default", author_program=self.program
        )
        Alert.objects.create(
            client_file=cf, status="cancelled", author_program=self.program
        )
        result = _count_active_alerts({cf.pk})
        self.assertEqual(result, 1)
