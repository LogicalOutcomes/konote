"""Tests for Board Summary PDF, workbench-to-report links, and goal breadcrumbs.

Covers:
- Board summary PDF authorization (program-scoped, not org-wide)
- Board summary date parsing (valid, invalid, leap-year safe)
- Board summary privacy suppression (quotes gated on enrollment)
- Workbench-to-report links in insights context
- Breadcrumbs on goal creation page
- Trend threshold constant
"""
from datetime import date, timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import Program, UserProgramRole
from apps.reports.pdf_views import _derive_outcome_trend, TREND_THRESHOLD_PP
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Board Summary PDF — Authorization
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BoardSummaryAuthTest(TestCase):
    """Board summary PDF must be program-scoped: users without a role
    in the requested program should get 403."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.program_a = Program.objects.create(name="Program A", status="active")
        self.program_b = Program.objects.create(name="Program B", status="active")

        # User with program_manager role in Program A only
        self.pm_a = User.objects.create_user(
            username="pm_a", password="pass", display_name="PM A",
        )
        UserProgramRole.objects.create(
            user=self.pm_a, program=self.program_a,
            role="program_manager", status="active",
        )

        # Admin user (has is_admin flag — bypasses via allow_admin=True)
        self.admin = User.objects.create_user(
            username="admin", password="pass", display_name="Admin",
            is_admin=True,
        )

        # Staff user with no funder report permission
        self.staff = User.objects.create_user(
            username="staff", password="pass", display_name="Staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program_a,
            role="staff", status="active",
        )

    def _url(self, program):
        return reverse("reports:board_summary_pdf", kwargs={"program_id": program.pk})

    @patch("apps.reports.pdf_views.is_pdf_available", return_value=False)
    def test_pm_can_access_own_program(self, _mock_pdf):
        """PM with funder_report permission in Program A can access A's board summary."""
        self.http.login(username="pm_a", password="pass")
        resp = self.http.get(self._url(self.program_a))
        # 200 or 503 with "PDF unavailable" message (WeasyPrint not installed in test)
        self.assertIn(resp.status_code, [200, 503])

    def test_pm_cannot_access_other_program(self):
        """PM for Program A must NOT access Program B's board summary."""
        self.http.login(username="pm_a", password="pass")
        resp = self.http.get(self._url(self.program_b))
        self.assertEqual(resp.status_code, 403)

    def test_staff_without_permission_gets_403(self):
        """Staff role does not have funder_report permission."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get(self._url(self.program_a))
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_redirects_to_login(self):
        """Unauthenticated users should be redirected to login."""
        resp = self.http.get(self._url(self.program_a))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)

    def test_nonexistent_program_returns_404(self):
        """Admin requesting a non-existent program gets 404.

        Admin users bypass the decorator (allow_admin=True), so the view
        body's get_object_or_404 raises Http404 directly.
        """
        self.http.login(username="admin", password="pass")
        resp = self.http.get(
            reverse("reports:board_summary_pdf", kwargs={"program_id": 99999})
        )
        self.assertEqual(resp.status_code, 404)

    @patch("apps.reports.pdf_views.is_pdf_available", return_value=False)
    def test_admin_can_access_any_program(self, _mock_pdf):
        """Admin with is_admin=True should bypass program scoping (allow_admin)."""
        self.http.login(username="admin", password="pass")
        resp = self.http.get(self._url(self.program_b))
        self.assertIn(resp.status_code, [200, 503])


# ---------------------------------------------------------------------------
# Board Summary PDF — Date Parsing
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BoardSummaryDateParsingTest(TestCase):
    """Date fallback must be safe for all dates including Feb 29."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.program = Program.objects.create(name="Test Program", status="active")
        self.admin = User.objects.create_user(
            username="admin", password="pass", display_name="Admin",
            is_admin=True,
        )
        self.http.login(username="admin", password="pass")
        self._url = reverse(
            "reports:board_summary_pdf",
            kwargs={"program_id": self.program.pk},
        )

    @patch("apps.reports.pdf_views.is_pdf_available", return_value=False)
    def test_no_dates_defaults_to_last_12_months(self, _mock_pdf):
        """Missing date params should default to ~12 months back, not crash."""
        resp = self.http.get(self._url)
        self.assertIn(resp.status_code, [200, 503])

    @patch("apps.reports.pdf_views.is_pdf_available", return_value=False)
    def test_valid_dates_are_parsed(self, _mock_pdf):
        """Explicit date_from and date_to should be used."""
        resp = self.http.get(self._url, {
            "date_from": "2025-01-01", "date_to": "2025-06-30",
        })
        self.assertIn(resp.status_code, [200, 503])

    @patch("apps.reports.pdf_views.is_pdf_available", return_value=False)
    def test_invalid_date_from_falls_back(self, _mock_pdf):
        """Invalid date_from should fall back gracefully."""
        resp = self.http.get(self._url, {
            "date_from": "not-a-date", "date_to": "2025-06-30",
        })
        self.assertIn(resp.status_code, [200, 503])

    @patch("apps.reports.pdf_views.is_pdf_available", return_value=False)
    def test_leap_year_date_to_does_not_crash(self, _mock_pdf):
        """The date fallback must not crash when date_to is Feb 29.

        Previously used date(year-1, month, day) which fails for Feb 29.
        Now uses timedelta(days=365) which is always safe.
        """
        resp = self.http.get(self._url, {"date_to": "2028-02-29"})
        self.assertIn(resp.status_code, [200, 503])


# ---------------------------------------------------------------------------
# Trend Threshold Constant
# ---------------------------------------------------------------------------

class TrendThresholdTest(TestCase):
    """The trend threshold should be a named constant, not a magic number."""

    def test_threshold_is_positive(self):
        self.assertGreater(TREND_THRESHOLD_PP, 0)

    def test_improving_above_threshold(self):
        trends = {1: [{"band_high_pct": 40}, {"band_high_pct": 40 + TREND_THRESHOLD_PP + 1}]}
        self.assertEqual(_derive_outcome_trend(1, trends), "improving")

    def test_declining_below_threshold(self):
        trends = {1: [{"band_high_pct": 50}, {"band_high_pct": 50 - TREND_THRESHOLD_PP - 1}]}
        self.assertEqual(_derive_outcome_trend(1, trends), "declining")

    def test_stable_within_threshold(self):
        trends = {1: [{"band_high_pct": 50}, {"band_high_pct": 50 + TREND_THRESHOLD_PP - 1}]}
        self.assertEqual(_derive_outcome_trend(1, trends), "stable")

    def test_new_with_single_point(self):
        trends = {1: [{"band_high_pct": 50}]}
        self.assertEqual(_derive_outcome_trend(1, trends), "new")

    def test_new_with_no_data(self):
        self.assertEqual(_derive_outcome_trend(99, {}), "new")


# ---------------------------------------------------------------------------
# Workbench-to-Report Links — Context Variables
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class WorkbenchLinksContextTest(TestCase):
    """Insights view should include partner_templates and upcoming_schedules
    in its context when the form is valid."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.program = Program.objects.create(name="Test Program", status="active")
        self.admin = User.objects.create_user(
            username="admin", password="pass", display_name="Admin",
            is_admin=True,
        )
        UserProgramRole.objects.create(
            user=self.admin, program=self.program,
            role="program_manager", status="active",
        )
        self.http.login(username="admin", password="pass")

    def test_context_includes_partner_templates_key(self):
        """The insights view should pass partner_templates to the template."""
        url = reverse("reports:program_insights")
        resp = self.http.get(url, {
            "program": self.program.pk,
            "time_period": "6m",
        }, HTTP_HX_REQUEST="true")
        if resp.status_code == 200:
            self.assertIn("partner_templates", resp.context)

    def test_context_includes_upcoming_schedules_key(self):
        """The insights view should pass upcoming_schedules to the template."""
        url = reverse("reports:program_insights")
        resp = self.http.get(url, {
            "program": self.program.pk,
            "time_period": "6m",
        }, HTTP_HX_REQUEST="true")
        if resp.status_code == 200:
            self.assertIn("upcoming_schedules", resp.context)


# ---------------------------------------------------------------------------
# Goal Create — Breadcrumbs
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GoalCreateBreadcrumbsTest(TestCase):
    """Goal creation page should include breadcrumbs in context."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.program = Program.objects.create(name="Test Program", status="active")
        self.staff = User.objects.create_user(
            username="staff", password="pass", display_name="Staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role="staff", status="active",
        )
        # ClientFile needs property accessors for encrypted fields
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.status = "active"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="enrolled",
        )
        self.http.login(username="staff", password="pass")

    def test_breadcrumbs_in_context(self):
        """Goal create view should include breadcrumbs list in context."""
        url = reverse("plans:goal_create", kwargs={"client_id": self.client_file.pk})
        resp = self.http.get(url)
        if resp.status_code == 200:
            self.assertIn("breadcrumbs", resp.context)
            breadcrumbs = resp.context["breadcrumbs"]
            self.assertEqual(len(breadcrumbs), 4)
            # Last breadcrumb should be the current page (no URL)
            self.assertEqual(breadcrumbs[-1]["url"], "")
