"""Tests for the Safety Oversight MVP feature.

Covers:
- Enhanced dashboard alert card helpers
- Oversight report generation service (compute_oversight_metrics, determine_status)
- Oversight report views (list, generate, detail, approve)
- Report schedule model (advance_due_date, is_due_soon, is_overdue)
- Management command (check_report_deadlines)
- Dashboard banner context processor
"""
from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import Client as HttpClient, TestCase, override_settings
from django.utils import timezone

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Alert, AlertCancellationRecommendation
from apps.programs.models import Program, UserProgramRole
from apps.reports.models import OversightReportSnapshot, ReportSchedule
from apps.reports.oversight import (
    compute_oversight_metrics,
    determine_status,
    get_oversight_context,
    quarter_dates,
)
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Enhanced Dashboard Alert Card
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EnhancedAlertCardTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = HttpClient()
        self.admin = User.objects.create_user(
            username="admin_oversight", password="testpass123", is_admin=True,
        )
        self.exec_user = User.objects.create_user(
            username="exec_alert", password="testpass123",
        )
        self.prog = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.prog, role="executive",
        )

    def _create_client(self, status="active"):
        cf = ClientFile()
        cf.first_name = "Test"
        cf.last_name = "Client"
        cf.status = status
        cf.save()
        ClientProgramEnrolment.objects.create(client_file=cf, program=self.prog)
        return cf

    def test_alert_oversight_data(self):
        """_get_alert_oversight_data returns active, aging, pending counts."""
        from apps.clients.dashboard_views import _get_alert_oversight_data

        cf = self._create_client()

        # Create a recent alert
        Alert.objects.create(
            client_file=cf, author=self.exec_user, author_program=self.prog,
            content="Recent alert",
        )

        # Create an aging alert (>14 days old)
        old_alert = Alert.objects.create(
            client_file=cf, author=self.exec_user, author_program=self.prog,
            content="Old alert",
        )
        Alert.objects.filter(pk=old_alert.pk).update(
            created_at=timezone.now() - timedelta(days=20),
        )

        data = _get_alert_oversight_data([cf.pk])
        self.assertEqual(data["active"], 2)
        self.assertEqual(data["aging"], 1)
        self.assertEqual(data["pending_cancellation"], 0)

    def test_alert_oversight_with_pending_cancellation(self):
        """Pending cancellation reviews are counted correctly."""
        from apps.clients.dashboard_views import _get_alert_oversight_data

        cf = self._create_client()
        alert = Alert.objects.create(
            client_file=cf, author=self.exec_user, author_program=self.prog,
            content="Alert with recommendation",
        )
        AlertCancellationRecommendation.objects.create(
            alert=alert, recommended_by=self.exec_user,
            assessment="Test assessment", status="pending",
        )

        data = _get_alert_oversight_data([cf.pk])
        self.assertEqual(data["pending_cancellation"], 1)

    def test_alert_overview_page_loads(self):
        """Alert overview by program page loads for executive users."""
        self.http.login(username="exec_alert", password="testpass123")
        resp = self.http.get("/participants/executive/alerts/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test Program")

    def test_alert_overview_requires_login(self):
        resp = self.http.get("/participants/executive/alerts/")
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# Oversight Report Generation Service
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class OversightReportServiceTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="gen_user", password="testpass123", is_admin=True,
        )
        self.prog = Program.objects.create(name="Service Prog", colour_hex="#3B82F6")

    def test_quarter_dates_parsing(self):
        """quarter_dates correctly parses 'Q1 2026' format."""
        start, end = quarter_dates("Q1 2026")
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 3, 31))

    def test_quarter_dates_q4(self):
        start, end = quarter_dates("Q4 2025")
        self.assertEqual(start, date(2025, 10, 1))
        self.assertEqual(end, date(2025, 12, 31))

    def test_determine_status_routine(self):
        """No triggers → ROUTINE status."""
        metrics = {
            "aging_alerts": 0,
            "pending_reviews": 0,
            "alerts_raised": 2,
            "program_breakdown": [],
            "prev_notes_recorded": 100,
            "notes_recorded": 90,
        }
        status, triggers = determine_status(metrics)
        self.assertEqual(status, "ROUTINE")
        self.assertEqual(triggers, [])

    def test_determine_status_notable_aging(self):
        """Aging alerts trigger NOTABLE status."""
        metrics = {
            "aging_alerts": 3,
            "pending_reviews": 0,
            "alerts_raised": 3,
            "program_breakdown": [],
            "prev_notes_recorded": 100,
            "notes_recorded": 90,
        }
        status, triggers = determine_status(metrics)
        self.assertEqual(status, "NOTABLE")
        self.assertIn("14 days", triggers[0])

    def test_determine_status_notable_activity_drop(self):
        """Notes dropping >30% triggers NOTABLE."""
        metrics = {
            "aging_alerts": 0,
            "pending_reviews": 0,
            "alerts_raised": 0,
            "program_breakdown": [],
            "prev_notes_recorded": 100,
            "notes_recorded": 50,
        }
        status, triggers = determine_status(metrics)
        self.assertEqual(status, "NOTABLE")
        self.assertTrue(any("dropped" in t for t in triggers))

    def test_external_suppression(self):
        """get_oversight_context suppresses counts <5 for external view."""
        snapshot = OversightReportSnapshot.objects.create(
            period_label="Q1 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            metrics_json={
                "alerts_raised": 10,
                "alerts_resolved": 5,
                "median_resolution_days": 3.0,
                "active_at_quarter_end": 3,
                "notes_recorded": 100,
                "active_participants": 50,
                "active_staff": 10,
                "aging_alerts": 0,
                "pending_reviews": 0,
                "program_breakdown": [
                    {"program_name": "Prog A", "alerts_raised": 3, "active_at_end": 2},
                ],
                "prev_alerts_raised": 8,
                "prev_notes_recorded": 90,
            },
            overall_status="ROUTINE",
            generated_by=self.user,
        )

        context = get_oversight_context(snapshot, is_external=True)
        # Program with 3 alerts (< 5) should be suppressed to "<5"
        prog = context["program_breakdown"][0]
        self.assertEqual(prog["alerts_raised"], "<5")
        self.assertEqual(prog["active_at_end"], "<5")

    def test_internal_no_suppression(self):
        """Internal view does not suppress small counts."""
        snapshot = OversightReportSnapshot.objects.create(
            period_label="Q1 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            metrics_json={
                "alerts_raised": 10,
                "alerts_resolved": 5,
                "median_resolution_days": None,
                "active_at_quarter_end": 3,
                "notes_recorded": 100,
                "active_participants": 50,
                "active_staff": 10,
                "aging_alerts": 0,
                "pending_reviews": 0,
                "program_breakdown": [
                    {"program_name": "Prog A", "alerts_raised": 3, "active_at_end": 2},
                ],
                "prev_alerts_raised": 8,
                "prev_notes_recorded": 90,
            },
            overall_status="ROUTINE",
            generated_by=self.user,
        )

        context = get_oversight_context(snapshot, is_external=False)
        prog = context["program_breakdown"][0]
        self.assertEqual(prog["alerts_raised"], 3)
        self.assertEqual(prog["active_at_end"], 2)


# ---------------------------------------------------------------------------
# Oversight Report Views
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class OversightReportViewTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = HttpClient()
        self.admin = User.objects.create_user(
            username="admin_view", password="testpass123", is_admin=True,
        )
        self.non_admin = User.objects.create_user(
            username="worker_view", password="testpass123",
        )

    def test_oversight_list_requires_admin(self):
        """Non-admin users cannot access oversight report list."""
        self.http.login(username="worker_view", password="testpass123")
        resp = self.http.get("/reports/oversight/")
        self.assertIn(resp.status_code, [302, 403])

    def test_oversight_list_loads_for_admin(self):
        self.http.login(username="admin_view", password="testpass123")
        resp = self.http.get("/reports/oversight/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Safety Oversight Reports")

    def test_generate_page_loads(self):
        self.http.login(username="admin_view", password="testpass123")
        resp = self.http.get("/reports/oversight/generate/")
        self.assertEqual(resp.status_code, 200)

    def test_detail_page_loads(self):
        snapshot = OversightReportSnapshot.objects.create(
            period_label="Q1 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            metrics_json={
                "alerts_raised": 0, "alerts_resolved": 0,
                "median_resolution_days": None,
                "active_at_quarter_end": 0,
                "notes_recorded": 0, "active_participants": 0,
                "active_staff": 0, "aging_alerts": 0,
                "pending_reviews": 0, "program_breakdown": [],
                "prev_alerts_raised": 0, "prev_notes_recorded": 0,
            },
            overall_status="ROUTINE",
            generated_by=self.admin,
        )
        self.http.login(username="admin_view", password="testpass123")
        resp = self.http.get(f"/reports/oversight/{snapshot.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ROUTINE")

    def test_approve_sets_attestation(self):
        snapshot = OversightReportSnapshot.objects.create(
            period_label="Q1 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            metrics_json={
                "alerts_raised": 0, "alerts_resolved": 0,
                "median_resolution_days": None,
                "active_at_quarter_end": 0,
                "notes_recorded": 0, "active_participants": 0,
                "active_staff": 0, "aging_alerts": 0,
                "pending_reviews": 0, "program_breakdown": [],
                "prev_alerts_raised": 0, "prev_notes_recorded": 0,
            },
            overall_status="ROUTINE",
            generated_by=self.admin,
        )
        self.http.login(username="admin_view", password="testpass123")
        resp = self.http.post(
            f"/reports/oversight/{snapshot.pk}/approve/",
            {"narrative": "All good", "confirm": True},
        )
        self.assertEqual(resp.status_code, 302)

        snapshot.refresh_from_db()
        self.assertEqual(snapshot.narrative, "All good")
        self.assertIsNotNone(snapshot.approved_by)
        self.assertIsNotNone(snapshot.approved_at)

    def test_schedule_list_loads(self):
        self.http.login(username="admin_view", password="testpass123")
        resp = self.http.get("/reports/schedules/")
        self.assertEqual(resp.status_code, 200)

    def test_schedule_create_and_list(self):
        self.http.login(username="admin_view", password="testpass123")
        resp = self.http.post("/reports/schedules/create/", {
            "name": "Q Safety Report",
            "report_type": "oversight",
            "frequency": "quarterly",
            "due_date": "2026-03-31",
            "reminder_days_before": 14,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(ReportSchedule.objects.filter(name="Q Safety Report").exists())


# ---------------------------------------------------------------------------
# Report Schedule Model
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ReportScheduleModelTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="sched_user", password="testpass123", is_admin=True,
        )

    def _create_schedule(self, due_date=None, frequency="quarterly"):
        return ReportSchedule.objects.create(
            name="Test Schedule",
            report_type="oversight",
            frequency=frequency,
            due_date=due_date or date(2026, 3, 31),
            reminder_days_before=14,
            created_by=self.user,
        )

    def test_advance_due_date_quarterly(self):
        schedule = self._create_schedule(date(2026, 3, 31), "quarterly")
        schedule.advance_due_date()
        schedule.refresh_from_db()
        self.assertEqual(schedule.due_date, date(2026, 6, 30))

    def test_advance_due_date_monthly(self):
        schedule = self._create_schedule(date(2026, 1, 31), "monthly")
        schedule.advance_due_date()
        schedule.refresh_from_db()
        # Feb has 28 days — should clamp
        self.assertEqual(schedule.due_date, date(2026, 2, 28))

    def test_advance_due_date_annually(self):
        schedule = self._create_schedule(date(2026, 3, 31), "annually")
        schedule.advance_due_date()
        schedule.refresh_from_db()
        self.assertEqual(schedule.due_date, date(2027, 3, 31))

    def test_advance_due_date_year_overflow(self):
        """Quarterly from Nov should roll into next year."""
        schedule = self._create_schedule(date(2026, 11, 30), "quarterly")
        schedule.advance_due_date()
        schedule.refresh_from_db()
        self.assertEqual(schedule.due_date, date(2027, 2, 28))

    def test_advance_resets_notification_state(self):
        schedule = self._create_schedule()
        schedule.banner_shown_at = timezone.now()
        schedule.email_sent_at = timezone.now()
        schedule.save()
        schedule.advance_due_date()
        schedule.refresh_from_db()
        self.assertIsNone(schedule.banner_shown_at)
        self.assertIsNone(schedule.email_sent_at)

    @patch("django.utils.timezone.now")
    def test_is_due_soon(self, mock_now):
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 3, 20, 12, 0)
        )
        schedule = self._create_schedule(date(2026, 3, 31))
        # 11 days until due, reminder is 14 days → should be due soon
        self.assertTrue(schedule.is_due_soon)

    @patch("django.utils.timezone.now")
    def test_is_not_due_soon(self, mock_now):
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 3, 1, 12, 0)
        )
        schedule = self._create_schedule(date(2026, 3, 31))
        # 30 days until due, reminder is 14 days → not due soon
        self.assertFalse(schedule.is_due_soon)

    @patch("django.utils.timezone.now")
    def test_is_overdue(self, mock_now):
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 4, 2, 12, 0)
        )
        schedule = self._create_schedule(date(2026, 3, 31))
        self.assertTrue(schedule.is_overdue)

    @patch("django.utils.timezone.now")
    def test_not_overdue_after_generation(self, mock_now):
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 4, 2, 12, 0)
        )
        schedule = self._create_schedule(date(2026, 3, 31))
        schedule.last_generated_at = timezone.make_aware(
            timezone.datetime(2026, 3, 31, 10, 0)
        )
        schedule.save()
        self.assertFalse(schedule.is_overdue)


# ---------------------------------------------------------------------------
# Management Command
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CheckReportDeadlinesTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="cmd_user", password="testpass123", is_admin=True,
        )

    @patch("django.utils.timezone.now")
    def test_dry_run_no_changes(self, mock_now):
        """--dry-run should not modify schedule state."""
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 3, 25, 12, 0)
        )
        schedule = ReportSchedule.objects.create(
            name="Dry Run Test",
            report_type="oversight",
            frequency="quarterly",
            due_date=date(2026, 3, 31),
            reminder_days_before=14,
            created_by=self.user,
        )

        from django.core.management import call_command
        out = StringIO()
        call_command("check_report_deadlines", "--dry-run", stdout=out)

        schedule.refresh_from_db()
        self.assertIsNone(schedule.banner_shown_at)
        self.assertIsNone(schedule.email_sent_at)
        self.assertIn("DRY RUN", out.getvalue())

    @patch("django.utils.timezone.now")
    def test_sets_banner_when_due_soon(self, mock_now):
        """Command sets banner_shown_at when schedule is within reminder window."""
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 3, 25, 12, 0)
        )
        schedule = ReportSchedule.objects.create(
            name="Banner Test",
            report_type="oversight",
            frequency="quarterly",
            due_date=date(2026, 3, 31),
            reminder_days_before=14,
            created_by=self.user,
        )

        from django.core.management import call_command
        call_command("check_report_deadlines", stdout=StringIO())

        schedule.refresh_from_db()
        self.assertIsNotNone(schedule.banner_shown_at)


# ---------------------------------------------------------------------------
# Context Processor
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class UpcomingReportsContextTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="ctx_admin", password="testpass123", is_admin=True,
        )

    @patch("django.utils.timezone.now")
    def test_overdue_in_context(self, mock_now):
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 4, 2, 12, 0)
        )
        ReportSchedule.objects.create(
            name="Overdue Schedule",
            report_type="oversight",
            frequency="quarterly",
            due_date=date(2026, 3, 31),
            reminder_days_before=14,
            created_by=self.admin,
        )

        from django.core.cache import cache
        cache.delete("upcoming_report_schedules")

        from konote.context_processors import upcoming_reports
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.admin

        result = upcoming_reports(request)
        self.assertEqual(len(result["overdue_reports"]), 1)
        self.assertEqual(result["overdue_reports"][0].name, "Overdue Schedule")

    @patch("django.utils.timezone.now")
    def test_upcoming_in_context(self, mock_now):
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 3, 25, 12, 0)
        )
        ReportSchedule.objects.create(
            name="Soon Schedule",
            report_type="oversight",
            frequency="quarterly",
            due_date=date(2026, 3, 31),
            reminder_days_before=14,
            created_by=self.admin,
        )

        from django.core.cache import cache
        cache.delete("upcoming_report_schedules")

        from konote.context_processors import upcoming_reports
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.admin

        result = upcoming_reports(request)
        self.assertEqual(len(result["upcoming_reports"]), 1)

    def test_non_admin_gets_empty(self):
        """Non-admin users get no report schedule context."""
        non_admin = User.objects.create_user(
            username="ctx_worker", password="testpass123",
        )

        from konote.context_processors import upcoming_reports
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.user = non_admin

        result = upcoming_reports(request)
        self.assertEqual(result, {})
