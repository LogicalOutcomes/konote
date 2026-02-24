"""Tests for the executive dashboard view and metric helpers."""
from datetime import timedelta

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Alert, Event, Meeting
from apps.groups.models import Group, GroupMembership, GroupSession, GroupSessionAttendance
from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget
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
        resp = self.http.get("/participants/executive/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Executive Overview")

    def test_dashboard_requires_login(self):
        resp = self.http.get("/participants/executive/")
        self.assertEqual(resp.status_code, 302)

    def test_no_programs_returns_403(self):
        """Users with no programme assignments get a 403, not an empty page."""
        no_prog_user = User.objects.create_user(
            username="noprog", password="testpass123"
        )
        self.http.login(username="noprog", password="testpass123")
        resp = self.http.get("/participants/executive/")
        self.assertEqual(resp.status_code, 403)

    def test_active_count(self):
        self._create_client("active", [self.prog_a])
        self._create_client("active", [self.prog_a])
        self._create_client("inactive", [self.prog_a])

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get("/participants/executive/")
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
        resp = self.http.get("/participants/executive/")
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
        resp = self.http.get("/participants/executive/")
        self.assertEqual(resp.context["overdue_followups"], 1)

    def test_program_filter_valid(self):
        self._create_client("active", [self.prog_a])
        self._create_client("active", [self.prog_b])

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get(f"/participants/executive/?program={self.prog_a.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_active"], 1)
        self.assertEqual(resp.context["selected_program_id"], self.prog_a.pk)
        self.assertEqual(len(resp.context["program_stats"]), 1)

    def test_program_filter_invalid_ignored(self):
        self._create_client("active", [self.prog_a])

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get("/participants/executive/?program=abc")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["selected_program_id"])

    def test_program_filter_unauthorized_ignored(self):
        """User cannot filter to a program they don't have access to."""
        other_prog = Program.objects.create(name="Secret Program", colour_hex="#FF0000")

        self.http.login(username="exec", password="testpass123")
        resp = self.http.get(f"/participants/executive/?program={other_prog.pk}")
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


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExecutiveDashboardOutcomeCardsTest(TestCase):
    """Tests for the Outcome Learning section on executive dashboard cards."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.exec_user = User.objects.create_user(
            username="exec_outcome", password="testpass123"
        )
        self.program = Program.objects.create(name="Outcome Program", colour_hex="#10B981")
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program, role="executive"
        )
        self.now = timezone.now()

    def _create_enrolled_client(self):
        """Create an active client enrolled in self.program."""
        cf = ClientFile()
        cf.first_name = "Test"
        cf.last_name = "Client"
        cf.status = "active"
        cf.save()
        ClientProgramEnrolment.objects.create(
            client_file=cf, program=self.program, status="enrolled"
        )
        return cf

    def _create_metric_value(self, client_file, metric_def, value, backdate=None):
        """Create a MetricValue through the full relationship chain."""
        section = PlanSection.objects.create(
            client_file=client_file, name="Goals", program=self.program
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client_file, status="default"
        )
        note = ProgressNote.objects.create(
            client_file=client_file,
            author=self.exec_user,
            author_program=self.program,
            backdate=backdate,
        )
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note, plan_target=target
        )
        MetricValue.objects.create(
            progress_note_target=pnt,
            metric_def=metric_def,
            value=str(value),
        )
        return note

    def _create_achievement_metric(self, name="Employment", target_rate=None):
        """Create an achievement-type MetricDefinition."""
        return MetricDefinition.objects.create(
            name=name,
            definition="Test achievement metric",
            metric_type="achievement",
            achievement_options=["Employed", "In training", "Unemployed"],
            achievement_success_values=["Employed"],
            target_rate=target_rate,
            owning_program=self.program,
        )

    def _create_scale_metric(self, name="Wellbeing", target_band_high_pct=None):
        """Create a scale-type MetricDefinition."""
        return MetricDefinition.objects.create(
            name=name,
            definition="Test scale metric",
            metric_type="scale",
            min_value=1,
            max_value=5,
            higher_is_better=True,
            target_band_high_pct=target_band_high_pct,
            owning_program=self.program,
        )

    def _populate_achievement_data(self, metric_def, n=12):
        """Create n participants with achievement metric values (n >= 10).

        Returns (achieved_count, total).
        Each participant gets 2 values (to avoid being skipped as "new").
        The latest value determines achieved/not: first 65% get "Employed".
        Dates are within current month to fall inside the dashboard date range.
        """
        achieved = 0
        # Use a date early in the current month (always within month_start filter)
        earlier_this_month = self.now - timedelta(days=min(self.now.day - 1, 7))
        for i in range(n):
            cf = self._create_enrolled_client()
            # First value (earlier this month)
            self._create_metric_value(
                cf, metric_def, "Unemployed",
                backdate=earlier_this_month,
            )
            # Latest value determines achievement
            latest_val = "Employed" if i < int(n * 0.65) else "Unemployed"
            if latest_val == "Employed":
                achieved += 1
            self._create_metric_value(cf, metric_def, latest_val)
        return achieved, n

    def _populate_scale_data(self, metric_def, n=12, high_pct=0.72):
        """Create n participants with scale metric values (n >= 10).

        Each participant gets 2 values to avoid being skipped as "new".
        high_pct fraction score in the high band (>= 3.67 for 1-5 scale).
        Dates are within current month to fall inside the dashboard date range.
        """
        earlier_this_month = self.now - timedelta(days=min(self.now.day - 1, 7))
        for i in range(n):
            cf = self._create_enrolled_client()
            if i < int(n * high_pct):
                val = 4.5  # high band
            else:
                val = 2.0  # low band
            # Two values per participant (not "new")
            self._create_metric_value(
                cf, metric_def, val,
                backdate=earlier_this_month,
            )
            self._create_metric_value(cf, metric_def, val)

    def _get_program_stat(self, resp):
        """Extract the stat dict for self.program from response context."""
        for ps in resp.context["program_stats"]:
            if ps["program"].pk == self.program.pk:
                return ps
        return None

    def test_achievement_metric_shows_lead_outcome(self):
        """Program with achievement metrics shows lead outcome rate."""
        metric = self._create_achievement_metric(name="Employment", target_rate=70)
        achieved, total = self._populate_achievement_data(metric, n=12)

        self.http.login(username="exec_outcome", password="testpass123")
        resp = self.http.get("/participants/executive/")
        self.assertEqual(resp.status_code, 200)

        stat = self._get_program_stat(resp)
        self.assertIsNotNone(stat)
        self.assertIsNotNone(stat["lead_outcome"])
        self.assertEqual(stat["lead_outcome_type"], "achievement")
        self.assertEqual(stat["lead_outcome_name"], "Employment")
        self.assertEqual(stat["lead_outcome_target"], 70)
        # Verify rendered HTML contains the outcome name
        self.assertContains(resp, "Employment:")

    def test_scale_metric_fallback_when_no_achievement(self):
        """Program without achievement metrics falls back to scale metric signal."""
        metric = self._create_scale_metric(name="Wellbeing", target_band_high_pct=75)
        self._populate_scale_data(metric, n=12, high_pct=0.72)

        self.http.login(username="exec_outcome", password="testpass123")
        resp = self.http.get("/participants/executive/")
        stat = self._get_program_stat(resp)

        self.assertIsNotNone(stat["lead_outcome"])
        self.assertEqual(stat["lead_outcome_type"], "scale")
        self.assertEqual(stat["lead_outcome_name"], "Wellbeing")
        # Template shows "in high band"
        self.assertContains(resp, "in high band")

    def test_band_counts_not_in_rendered_html(self):
        """Band counts (band_low_count, band_mid_count, band_high_count) must NOT appear in HTML."""
        metric = self._create_scale_metric(name="Wellbeing")
        self._populate_scale_data(metric, n=12)

        self.http.login(username="exec_outcome", password="testpass123")
        resp = self.http.get("/participants/executive/")
        content = resp.content.decode()

        # These raw keys should not be rendered
        self.assertNotIn("band_low_count", content)
        self.assertNotIn("band_mid_count", content)
        self.assertNotIn("band_high_count", content)

    def test_data_completeness_indicator(self):
        """Data completeness indicator matches the completeness level."""
        metric = self._create_scale_metric(name="Scores")
        earlier_this_month = self.now - timedelta(days=min(self.now.day - 1, 7))

        # Create 20 enrolled clients, give metric data to 12 (enough for
        # lead_outcome to render) and leave 8 without scores.
        # 12/20 = 60% → "partial" completeness level.
        for i in range(20):
            cf = self._create_enrolled_client()
            if i < 12:
                self._create_metric_value(
                    cf, metric, 4.0,
                    backdate=earlier_this_month,
                )
                self._create_metric_value(cf, metric, 4.0)

        self.http.login(username="exec_outcome", password="testpass123")
        resp = self.http.get("/participants/executive/")
        stat = self._get_program_stat(resp)

        completeness = stat["data_completeness"]
        self.assertEqual(completeness["enrolled_count"], 20)
        self.assertEqual(completeness["completeness_level"], "partial")
        # Template renders the circle and counts
        self.assertContains(resp, "enrolled have scores")

    def test_trend_direction_calculated(self):
        """Trend direction field is correctly calculated from monthly data.

        With data in the current month only, trend_direction should be None
        (need >= 2 months). The field must always be present.
        """
        metric = self._create_scale_metric(name="Progress")
        earlier_this_month = self.now - timedelta(days=min(self.now.day - 1, 7))

        # All data within current month — only one month of data
        for i in range(12):
            cf = self._create_enrolled_client()
            self._create_metric_value(
                cf, metric, 2.0,
                backdate=earlier_this_month,
            )
            self._create_metric_value(cf, metric, 4.5)

        self.http.login(username="exec_outcome", password="testpass123")
        resp = self.http.get("/participants/executive/")
        stat = self._get_program_stat(resp)

        # trend_direction field must always be present
        self.assertIn("trend_direction", stat)
        # With only one month of data, trend should be None
        self.assertIsNone(stat["trend_direction"])

    def test_insights_link_present(self):
        """Cards with outcome data link to the insights page with correct program param."""
        metric = self._create_achievement_metric(name="Employment")
        self._populate_achievement_data(metric, n=12)

        self.http.login(username="exec_outcome", password="testpass123")
        resp = self.http.get("/participants/executive/")

        expected_link = f"/reports/insights/?program={self.program.pk}"
        self.assertContains(resp, expected_link)
        self.assertContains(resp, "View program learning")

    def test_privacy_no_outcome_section_when_n_below_10(self):
        """Programs with n < 10 do not show the outcome section."""
        metric = self._create_achievement_metric(name="Employment")
        # Only create 5 participants (below MIN_N_FOR_DISTRIBUTION = 10)
        for i in range(5):
            cf = self._create_enrolled_client()
            self._create_metric_value(cf, metric, "Employed")

        self.http.login(username="exec_outcome", password="testpass123")
        resp = self.http.get("/participants/executive/")
        stat = self._get_program_stat(resp)

        # lead_outcome should be None (insufficient data)
        self.assertIsNone(stat["lead_outcome"])
        # Outcome section should not be rendered
        self.assertNotContains(resp, "Outcome Learning")
