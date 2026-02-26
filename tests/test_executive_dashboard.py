"""Tests for the executive dashboard view and metric helpers."""
from datetime import date, timedelta

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Alert, Event, Meeting
from apps.groups.models import Group, GroupMembership, GroupSession, GroupSessionAttendance
from apps.notes.models import (
    MetricValue, ProgressNote, ProgressNoteTarget, SuggestionTheme,
)
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
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
class ProgramLearningCardTest(TestCase):
    """Tests for the Program Learning section on executive dashboard cards.

    Covers: achievement headline, scale fallback, theme counts, privacy
    suppression, data completeness, trend direction, link correctness,
    and anti-pattern verification (no band counts on executive cards).
    """
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.user = User.objects.create_user(username="exec", password="testpass123")
        self.program = Program.objects.create(
            name="Youth Employment", colour_hex="#10B981", status="active",
        )
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="executive",
        )
        self.date_from = date.today() - timedelta(days=90)
        self.date_to = date.today()

    def _create_enrolled_client(self, record_id="C001"):
        """Create an active client enrolled in self.program."""
        cf = ClientFile.objects.create(record_id=record_id, status="active")
        ClientProgramEnrolment.objects.create(
            client_file=cf, program=self.program, status="enrolled",
        )
        return cf

    def _create_achievement_metric(self, name="Employment", target_rate=70):
        """Create an achievement metric with success values."""
        return MetricDefinition.objects.create(
            name=name, category="custom", metric_type="achievement",
            achievement_options=["Employed", "In training", "Unemployed"],
            achievement_success_values=["Employed"],
            target_rate=target_rate,
        )

    def _create_scale_metric(self, name="Goal Progress", is_universal=True):
        """Create a universal scale metric."""
        return MetricDefinition.objects.create(
            name=name, category="general", metric_type="scale",
            is_universal=is_universal, min_value=1, max_value=5,
            threshold_low=2, threshold_high=4, higher_is_better=True,
        )

    def _record_achievement(self, client, metric, value="Employed"):
        """Record one achievement metric value for a client."""
        section = PlanSection.objects.filter(
            client_file=client, program=self.program,
        ).first()
        if not section:
            section = PlanSection.objects.create(
                client_file=client, name="Section", program=self.program,
            )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)
        note = ProgressNote.objects.create(
            client_file=client, note_type="full",
            author=self.user, author_program=self.program,
            backdate=timezone.now() - timedelta(days=1),
        )
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note, plan_target=target,
        )
        MetricValue.objects.create(
            progress_note_target=pnt, metric_def=metric, value=value,
        )

    def _record_scale_scores(self, client, metric, scores):
        """Record multiple scale metric scores for a client."""
        section = PlanSection.objects.filter(
            client_file=client, program=self.program,
        ).first()
        if not section:
            section = PlanSection.objects.create(
                client_file=client, name="Section", program=self.program,
            )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=client, name="Goal",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)
        for i, score in enumerate(scores):
            note = ProgressNote.objects.create(
                client_file=client, note_type="full",
                author=self.user, author_program=self.program,
                backdate=timezone.now() - timedelta(days=i + 1),
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note, plan_target=target,
            )
            MetricValue.objects.create(
                progress_note_target=pnt, metric_def=metric, value=str(score),
            )

    def _get_dashboard_response(self):
        """Log in and fetch the executive dashboard."""
        self.http.login(username="exec", password="testpass123")
        return self.http.get("/participants/executive/")

    # ── Test 1: Achievement metric headline ──

    def test_achievement_headline_shown(self):
        """Programs with achievement metrics show the achievement rate."""
        metric = self._create_achievement_metric(target_rate=70)
        # Create 10+ participants with achievement data (meet n >= 10 threshold)
        for i in range(12):
            client = self._create_enrolled_client(f"ACH-{i:03d}")
            value = "Employed" if i < 8 else "Unemployed"
            self._record_achievement(client, metric, value)

        resp = self._get_dashboard_response()
        stat = resp.context["program_stats"][0]
        learning = stat["learning"]

        self.assertEqual(learning["headline_type"], "achievement")
        self.assertEqual(learning["headline_label"], "Employment")
        self.assertIsNotNone(learning["headline_pct"])
        self.assertEqual(learning["target_rate"], 70)

    # ── Test 2: Scale metric fallback (no achievements) ──

    def test_scale_fallback_when_no_achievements(self):
        """Programs without achievement metrics show scale 'goals within reach' %."""
        metric = self._create_scale_metric()
        # Create 10+ participants with scale data
        for i in range(12):
            client = self._create_enrolled_client(f"SCALE-{i:03d}")
            self._record_scale_scores(client, metric, [4, 5])  # high band

        resp = self._get_dashboard_response()
        stat = resp.context["program_stats"][0]
        learning = stat["learning"]

        self.assertEqual(learning["headline_type"], "scale")
        self.assertEqual(learning["headline_label"], "Goal Progress")
        self.assertIsNotNone(learning["headline_pct"])

    # ── Test 3: Suggestion theme counts ──

    def test_theme_open_count(self):
        """Open feedback theme count is correct on the learning card."""
        # Create some open themes
        SuggestionTheme.objects.create(
            name="More group activities",
            program=self.program, status="open", priority="noted",
        )
        SuggestionTheme.objects.create(
            name="Transportation barriers",
            program=self.program, status="open", priority="urgent",
        )
        SuggestionTheme.objects.create(
            name="Resolved issue",
            program=self.program, status="addressed", priority="noted",
        )
        # Create a client so the program card appears
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        stat = resp.context["program_stats"][0]
        learning = stat["learning"]

        self.assertEqual(learning["theme_open_count"], 2)
        self.assertTrue(learning["has_urgent_theme"])

    def test_theme_count_excludes_addressed(self):
        """Addressed themes are not counted in open theme count."""
        SuggestionTheme.objects.create(
            name="Old theme",
            program=self.program, status="addressed", priority="noted",
        )
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        stat = resp.context["program_stats"][0]
        learning = stat["learning"]

        self.assertEqual(learning["theme_open_count"], 0)
        self.assertFalse(learning["has_urgent_theme"])

    # ── Test 4: Privacy suppression (n < 5) ──

    def test_privacy_suppression_below_threshold(self):
        """With < 5 participants with data, headline is None and no percentage shown.

        The metric insight functions themselves require n >= 10, so with only
        3 participants the functions return empty results. The learning card
        correctly shows "No outcome data recorded" rather than any percentages,
        which protects privacy.
        """
        metric = self._create_achievement_metric()
        # Only 3 participants with data (below SMALL_PROGRAM_THRESHOLD=5)
        for i in range(3):
            client = self._create_enrolled_client(f"SMALL-{i:03d}")
            self._record_achievement(client, metric)

        resp = self._get_dashboard_response()
        stat = resp.context["program_stats"][0]
        learning = stat["learning"]

        # No percentage should be shown (either suppressed or no data returned)
        self.assertIsNone(learning["headline_pct"])
        # The HTML should not contain any achievement percentage
        content = resp.content.decode()
        self.assertNotIn("% Employment", content)

    # ── Test 5: Band counts do NOT appear on executive cards ──

    def test_no_band_counts_in_rendered_html(self):
        """Anti-pattern: band_low_count must NOT appear in executive dashboard HTML."""
        metric = self._create_scale_metric()
        for i in range(12):
            client = self._create_enrolled_client(f"BAND-{i:03d}")
            self._record_scale_scores(client, metric, [3, 3])

        resp = self._get_dashboard_response()
        content = resp.content.decode()

        self.assertNotIn("band_low_count", content)
        self.assertNotIn("band_mid_count", content)
        self.assertNotIn("band_high_count", content)
        # Also verify "More support needed" (band label) does not appear
        # on the executive dashboard cards — per DRR anti-pattern
        self.assertNotIn("More support needed", content)

    # ── Test 6: Link to insights page with program pre-selected ──

    def test_learning_link_to_insights_page(self):
        """The 'View program learning' link includes program pre-selection."""
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        content = resp.content.decode()

        expected_link = f"/reports/insights/?program={self.program.pk}"
        self.assertIn(expected_link, content)
        self.assertIn("View program learning", content)

    # ── Test 7: Data completeness indicators ──

    def test_data_completeness_full(self):
        """Programs with >80% data completeness show 'full' level."""
        metric = self._create_scale_metric()
        # 10 enrolled, all with scores → 100% completeness
        for i in range(10):
            client = self._create_enrolled_client(f"FULL-{i:03d}")
            self._record_scale_scores(client, metric, [4, 4])

        resp = self._get_dashboard_response()
        stat = resp.context["program_stats"][0]
        learning = stat["learning"]

        self.assertEqual(learning["completeness_level"], "full")
        self.assertEqual(learning["completeness_enrolled"], 10)
        self.assertEqual(learning["completeness_with_data"], 10)

    def test_data_completeness_partial(self):
        """Programs with 50-80% data completeness show 'partial' level."""
        metric = self._create_scale_metric()
        # 10 enrolled, 6 with scores → 60% completeness
        for i in range(10):
            client = self._create_enrolled_client(f"PART-{i:03d}")
            if i < 6:
                self._record_scale_scores(client, metric, [3, 3])

        resp = self._get_dashboard_response()
        stat = resp.context["program_stats"][0]
        learning = stat["learning"]

        self.assertEqual(learning["completeness_level"], "partial")

    def test_data_completeness_low(self):
        """Programs with <50% data completeness show 'low' level."""
        metric = self._create_scale_metric()
        # 10 enrolled, 3 with scores → 30% completeness
        for i in range(10):
            client = self._create_enrolled_client(f"LOW-{i:03d}")
            if i < 3:
                self._record_scale_scores(client, metric, [3, 3])

        resp = self._get_dashboard_response()
        stat = resp.context["program_stats"][0]
        learning = stat["learning"]

        self.assertEqual(learning["completeness_level"], "low")

    # ── Test 8: Data completeness text alternatives (accessibility) ──

    def test_completeness_text_alternatives_in_html(self):
        """Completeness indicators have text alternatives for screen readers."""
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        content = resp.content.decode()

        # At least one of the text alternatives must appear
        has_text_alt = (
            "Full data" in content
            or "Partial data" in content
            or "Low data" in content
        )
        self.assertTrue(has_text_alt, "No completeness text alternative found in HTML")

    # ── Test 9: Trend direction calculation ──

    def test_trend_direction_shows_in_learning(self):
        """Learning card includes trend direction when descriptor data exists."""
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        stat = resp.context["program_stats"][0]
        learning = stat["learning"]

        # trend_direction should be a string (possibly empty if no data)
        self.assertIn("trend_direction", learning)
        self.assertIsInstance(learning["trend_direction"], str)

    # ── Test 10: Caution accent for urgent themes ──

    def test_caution_accent_for_urgent_theme(self):
        """Cards with urgent themes get the program-card-caution CSS class."""
        SuggestionTheme.objects.create(
            name="Safety concern",
            program=self.program, status="open", priority="urgent",
        )
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        content = resp.content.decode()

        self.assertIn("program-card-caution", content)

    def test_no_caution_accent_without_urgent(self):
        """Cards without urgent themes or declining trends have no caution accent.

        Note: The CSS class name 'program-card-caution' appears in the <style>
        block. We check specifically that the <article> element does not have
        this class applied.
        """
        SuggestionTheme.objects.create(
            name="Minor suggestion",
            program=self.program, status="open", priority="noted",
        )
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        content = resp.content.decode()

        # The <article> should use "program-card" but NOT "program-card-caution"
        self.assertIn('class="program-card"', content)
        self.assertNotIn('class="program-card program-card-caution"', content)

    # ── Test 11: No outcome data scenario ──

    def test_no_outcome_data_message(self):
        """Programs with no metrics show 'No outcome data recorded' message."""
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        content = resp.content.decode()

        self.assertIn("No outcome data recorded", content)

    # ── Test 12: Program Learning heading present ──

    def test_program_learning_section_present(self):
        """The Program Learning section heading is present in the HTML."""
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        content = resp.content.decode()

        self.assertIn("Program Learning", content)

    # ── Test 13: Anti-pattern - no "performance" framing ──

    def test_no_performance_framing(self):
        """The executive dashboard must not use 'performance' framing."""
        metric = self._create_scale_metric()
        for i in range(12):
            client = self._create_enrolled_client(f"PERF-{i:03d}")
            self._record_scale_scores(client, metric, [4, 4])

        resp = self._get_dashboard_response()
        content = resp.content.decode().lower()

        # "performance" should not appear as a framing label
        # (it may appear in other technical contexts but not as a heading)
        self.assertNotIn("program performance", content)

    # ── Test 14: Anti-pattern - no "struggling" or "thriving" language ──

    def test_no_deficit_language(self):
        """Dashboard must not use 'struggling' or 'thriving' language."""
        self._create_enrolled_client()

        resp = self._get_dashboard_response()
        content = resp.content.decode().lower()

        self.assertNotIn("struggling", content)
        self.assertNotIn("thriving", content)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExecutiveDashboardMetricInsightsTest(TestCase):
    """Tests that the executive dashboard includes metric insight indicators."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.exec_user = User.objects.create_user(
            username="exec_insights", password="testpass123"
        )
        self.prog = Program.objects.create(name="Insights Program", colour_hex="#10B981")
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.prog, role="executive"
        )

    def _create_client(self, status="active"):
        cf = ClientFile()
        cf.first_name = "Test"
        cf.last_name = "Client"
        cf.status = status
        cf.save()
        ClientProgramEnrolment.objects.create(client_file=cf, program=self.prog)
        return cf

    def test_program_stats_include_metric_insight_fields(self):
        """Dashboard context includes trend, completeness, and urgent theme fields."""
        self._create_client("active")
        self.http.login(username="exec_insights", password="testpass123")
        resp = self.http.get("/participants/executive/")
        self.assertEqual(resp.status_code, 200)

        program_stats = resp.context["program_stats"]
        self.assertEqual(len(program_stats), 1)
        stat = program_stats[0]

        # All three metric insight fields must be present
        self.assertIn("trend_direction", stat)
        self.assertIn("data_completeness_level", stat)
        self.assertIn("data_completeness_pct", stat)
        self.assertIn("urgent_theme_count", stat)

        # Completeness level must be one of the expected values
        self.assertIn(stat["data_completeness_level"], ("full", "partial", "low"))

    def test_urgent_theme_count_reflects_urgent_themes(self):
        """Dashboard counts urgent suggestion themes per program."""
        from apps.notes.models import SuggestionTheme

        self._create_client("active")

        # Create two urgent themes and one non-urgent theme
        SuggestionTheme.objects.create(
            name="Accessibility barriers",
            program=self.prog,
            status="open",
            priority="urgent",
        )
        SuggestionTheme.objects.create(
            name="Transportation issues",
            program=self.prog,
            status="open",
            priority="urgent",
        )
        SuggestionTheme.objects.create(
            name="Scheduling flexibility",
            program=self.prog,
            status="open",
            priority="noted",
        )

        self.http.login(username="exec_insights", password="testpass123")
        resp = self.http.get("/participants/executive/")
        self.assertEqual(resp.status_code, 200)

        stat = resp.context["program_stats"][0]
        self.assertEqual(stat["urgent_theme_count"], 2)
