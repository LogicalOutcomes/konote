"""Tests for the on-screen report preview feature (REP-PREVIEW1).

Covers:
1. Preview renders HTML (not a file download)
2. Preview respects permissions (PM, admin, executive aggregate-only)
3. Preview data matches what the download would contain
4. Download buttons on the preview page point to the correct endpoints
5. GET requests to preview URLs redirect to the form
"""
from datetime import date, datetime, time, timedelta

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
from apps.programs.models import Program, UserProgramRole
from apps.reports.models import Partner, ReportTemplate
from apps.reports.preview_views import _querydict_to_pairs
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _create_test_data():
    """Create minimal test data for report preview tests.

    Returns a dict with all created objects.
    """
    program = Program.objects.create(name="Youth Services", status="active")
    metric = MetricDefinition.objects.create(
        name="Engagement Score",
        definition="How engaged is the participant?",
        category="custom",
        is_enabled=True,
        status="active",
    )
    partner = Partner.objects.create(
        name="United Way",
        partner_type="funder",
        is_active=True,
    )
    partner.programs.add(program)

    template = ReportTemplate.objects.create(
        name="Quarterly Outcome Report",
        partner=partner,
        is_active=True,
        period_type="custom",
        output_format="mixed",
    )

    # Create a client with a note and metric value
    client_file = ClientFile.objects.create(
        record_id="TEST-001",
        status="active",
    )
    ClientProgramEnrolment.objects.create(
        client_file=client_file,
        program=program,
        status="enrolled",
    )
    plan_section = PlanSection.objects.create(
        client_file=client_file,
        name="Goals",
    )
    plan_target = PlanTarget.objects.create(
        plan_section=plan_section,
        client_file=client_file,
        name="Improve engagement",
    )
    PlanTargetMetric.objects.create(
        plan_target=plan_target,
        metric_def=metric,
    )

    return {
        "program": program,
        "metric": metric,
        "partner": partner,
        "template": template,
        "client_file": client_file,
        "plan_section": plan_section,
        "plan_target": plan_target,
    }


def _create_note_with_metric(user, client_file, plan_target, metric, value="4.0"):
    """Create a progress note with a metric value."""
    note = ProgressNote.objects.create(
        client_file=client_file,
        author=user,
        status="default",
        backdate=timezone.make_aware(datetime.combine(date(2025, 10, 15), time.min)),
    )
    pnt = ProgressNoteTarget.objects.create(
        progress_note=note,
        plan_target=plan_target,
    )
    MetricValue.objects.create(
        progress_note_target=pnt,
        metric_def=metric,
        value=value,
    )
    return note


# =========================================================================
# Helper tests
# =========================================================================

class QueryDictToPairsTest(TestCase):
    """Test the _querydict_to_pairs helper for multi-value field handling."""

    def test_single_value_fields(self):
        """Single-value fields produce one pair each."""
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd["program"] = "1"
        qd["date_from"] = "2025-04-01"
        pairs = _querydict_to_pairs(qd)
        self.assertIn(("program", "1"), pairs)
        self.assertIn(("date_from", "2025-04-01"), pairs)

    def test_multi_value_fields(self):
        """Multi-value fields (like metrics) produce one pair per value."""
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd.setlist("metrics", ["1", "2", "3"])
        pairs = _querydict_to_pairs(qd)
        metric_pairs = [(k, v) for k, v in pairs if k == "metrics"]
        self.assertEqual(len(metric_pairs), 3)
        self.assertIn(("metrics", "1"), pairs)
        self.assertIn(("metrics", "2"), pairs)
        self.assertIn(("metrics", "3"), pairs)

    def test_excludes_csrf_and_preview_and_format(self):
        """csrfmiddlewaretoken, preview, and format are excluded."""
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd["csrfmiddlewaretoken"] = "abc123"
        qd["preview"] = "1"
        qd["format"] = "csv"
        qd["program"] = "1"
        pairs = _querydict_to_pairs(qd)
        keys = [k for k, v in pairs]
        self.assertNotIn("csrfmiddlewaretoken", keys)
        self.assertNotIn("preview", keys)
        self.assertNotIn("format", keys)
        self.assertIn("program", keys)

    def test_excludes_empty_values(self):
        """Empty and whitespace-only values are excluded."""
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd["program"] = "1"
        qd["group_by"] = ""
        qd["fiscal_year"] = "  "
        pairs = _querydict_to_pairs(qd)
        keys = [k for k, v in pairs]
        self.assertIn("program", keys)
        self.assertNotIn("group_by", keys)
        self.assertNotIn("fiscal_year", keys)


# =========================================================================
# Template-driven report preview tests
# =========================================================================

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TemplateReportPreviewTest(TestCase):
    """Test the template-driven report preview view."""

    databases = ("default", "audit")

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        # Users
        self.admin = User.objects.create_user(
            username="admin", password="testpass123",
            is_admin=True, display_name="Admin User",
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123",
            is_admin=False, display_name="Staff User",
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123",
            is_admin=False, display_name="PM User",
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123",
            is_admin=False, display_name="Exec User",
        )

        # Test data
        data = _create_test_data()
        self.program = data["program"]
        self.metric = data["metric"]
        self.partner = data["partner"]
        self.template = data["template"]
        self.client_file = data["client_file"]
        self.plan_target = data["plan_target"]

        # Roles
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program, role="program_manager",
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program, role="executive",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff",
        )

        # Create metric data
        _create_note_with_metric(
            self.pm_user, self.client_file, self.plan_target, self.metric, "4.0"
        )

    def _preview_post_data(self, **overrides):
        """Build POST data for template-driven preview."""
        data = {
            "report_template": str(self.template.pk),
            "date_from": "2025-04-01",
            "date_to": "2026-03-31",
            "format": "csv",
            "recipient": "Board of Directors",
            "recipient_reason": "Quarterly update",
            "preview": "1",
        }
        data.update(overrides)
        return data

    def test_preview_renders_html_not_file(self):
        """Preview should return an HTML page, not a file download."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Report Preview")
        self.assertNotIn("Content-Disposition", resp.headers)

    def test_preview_contains_report_metadata(self):
        """Preview page should display report metadata."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "United Way")
        self.assertContains(resp, "Quarterly Outcome Report")
        self.assertContains(resp, "Youth Services")

    def test_preview_contains_service_statistics(self):
        """Preview page should display service statistics section."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Service Statistics")
        self.assertContains(resp, "Total Individuals Served")

    def test_preview_contains_download_buttons(self):
        """Preview page should have Download PDF and Download CSV buttons."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Download PDF")
        self.assertContains(resp, "Download CSV")

    def test_preview_contains_print_button(self):
        """Preview page should have a Print button."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Print")
        self.assertContains(resp, "window.print()")

    def test_preview_admin_access(self):
        """Admin users should be able to access the preview."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)

    def test_preview_pm_access(self):
        """Program managers should be able to access the preview."""
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)

    def test_preview_exec_access(self):
        """Executives should be able to access the preview."""
        self.http_client.login(username="exec", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)

    def test_preview_staff_denied(self):
        """Staff without report permission should be denied (403)."""
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 403)

    def test_preview_unauthenticated_redirects(self):
        """Unauthenticated users should be redirected to login."""
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_get_request_redirects_to_form(self):
        """GET request to preview URL should redirect to the generate form."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/generate/preview/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/reports/generate/", resp.url)

    def test_preview_invalid_form_shows_errors(self):
        """Invalid form data should re-render the form with errors."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            {
                "preview": "1",
                "format": "csv",
                # Missing required fields
            },
        )
        self.assertEqual(resp.status_code, 200)
        # Should show the form page (not the preview page)
        self.assertNotContains(resp, "Report Preview")

    def test_preview_back_link(self):
        """Preview page should have a back link to the generate form."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/generate/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Back to Generate Report")
        self.assertContains(resp, "/reports/generate/")


# =========================================================================
# Ad-hoc export preview tests
# =========================================================================

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdhocReportPreviewTest(TestCase):
    """Test the ad-hoc export preview view."""

    databases = ("default", "audit")

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        # Users
        self.admin = User.objects.create_user(
            username="admin", password="testpass123",
            is_admin=True, display_name="Admin User",
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123",
            is_admin=False, display_name="PM User",
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123",
            is_admin=False, display_name="Exec User",
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123",
            is_admin=False, display_name="Staff User",
        )

        # Test data
        data = _create_test_data()
        self.program = data["program"]
        self.metric = data["metric"]
        self.client_file = data["client_file"]
        self.plan_target = data["plan_target"]

        # Roles
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program, role="program_manager",
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program, role="executive",
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program, role="staff",
        )

        # Create metric data
        _create_note_with_metric(
            self.pm_user, self.client_file, self.plan_target, self.metric, "3.5"
        )

    def _preview_post_data(self, **overrides):
        """Build POST data for ad-hoc preview."""
        data = {
            "program": str(self.program.pk),
            "metrics": [str(self.metric.pk)],
            "fiscal_year": "",
            "date_from": "2025-04-01",
            "date_to": "2026-03-31",
            "format": "csv",
            "recipient": "Internal team",
            "recipient_reason": "Program review",
            "preview": "1",
        }
        data.update(overrides)
        return data

    def test_preview_renders_html_not_file(self):
        """Preview should return an HTML page, not a file download."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Report Preview")
        self.assertNotIn("Content-Disposition", resp.headers)

    def test_preview_contains_aggregate_data(self):
        """Preview should display aggregate summary statistics."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Summary Statistics")
        self.assertContains(resp, "Engagement Score")

    def test_preview_shows_program_name(self):
        """Preview metadata should include the program name."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Youth Services")

    def test_preview_download_buttons(self):
        """Preview should include Download PDF and CSV buttons."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Download PDF")
        self.assertContains(resp, "Download CSV")

    def test_preview_admin_sees_aggregate_only(self):
        """Admin without PM role sees aggregate-only data in preview.

        Admins without a PM role are aggregate-only users per the
        export permission model (apps/reports/utils.py).
        """
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Aggregate summary only")
        # Should NOT show individual data table
        self.assertNotContains(resp, "Individual Data")

    def test_preview_exec_sees_aggregate_only(self):
        """Executive users should only see aggregate data in preview."""
        self.http_client.login(username="exec", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Aggregate summary only")
        self.assertNotContains(resp, "Individual Data")

    def test_preview_pm_sees_individual_data(self):
        """Program managers should see individual data rows in preview."""
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        # PM is not aggregate-only, so should see individual data
        self.assertContains(resp, "Individual Data")
        self.assertContains(resp, "TEST-001")

    def test_preview_staff_denied(self):
        """Staff without export permission should be denied (403)."""
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 403)

    def test_preview_unauthenticated_redirects(self):
        """Unauthenticated users should be redirected to login."""
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_get_request_redirects_to_form(self):
        """GET request to preview URL should redirect to export form."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export/preview/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/reports/export/", resp.url)

    def test_preview_no_data_shows_form(self):
        """When no matching data exists, preview should re-show the form."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(
                date_from="2020-01-01",
                date_to="2020-01-31",
            ),
        )
        self.assertEqual(resp.status_code, 200)
        # Should show the "no data" message on the form page
        self.assertContains(resp, "No data found")

    def test_preview_back_link_to_export(self):
        """Preview page should have a back link to the export form."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Back to Custom Export")
        self.assertContains(resp, "/reports/export/")

    def test_download_buttons_include_form_fields(self):
        """Download buttons should include hidden form fields from original submission."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            "/reports/export/",
            self._preview_post_data(),
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        # The hidden fields should include the program ID and metric ID
        self.assertIn(f'value="{self.program.pk}"', content)
        self.assertIn(f'value="{self.metric.pk}"', content)

    def test_without_preview_flag_proceeds_normally(self):
        """POST without preview=1 should proceed to normal export flow."""
        self.http_client.login(username="admin", password="testpass123")
        post_data = self._preview_post_data()
        del post_data["preview"]
        resp = self.http_client.post(
            "/reports/export/",
            post_data,
        )
        self.assertEqual(resp.status_code, 200)
        # Should show the export link page, not the preview
        self.assertNotContains(resp, "Report Preview")


# =========================================================================
# Form button tests
# =========================================================================

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PreviewButtonOnFormsTest(TestCase):
    """Test that the Preview on Screen button appears on both report forms."""

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123",
            is_admin=True, display_name="Admin",
        )
        self.program = Program.objects.create(name="Test Program", status="active")
        self.metric = MetricDefinition.objects.create(
            name="Test Metric",
            definition="A test metric",
            category="custom",
            is_enabled=True,
            status="active",
        )
        # Template-driven form requires at least one active report template
        self.partner = Partner.objects.create(
            name="Test Partner", partner_type="funder", is_active=True,
        )
        self.partner.programs.add(self.program)
        self.template = ReportTemplate.objects.create(
            name="Test Report",
            partner=self.partner,
            is_active=True,
            period_type="custom",
            output_format="mixed",
        )

    def test_template_form_has_preview_button(self):
        """Template-driven form should have a Preview on Screen button."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/generate/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Preview on Screen")
        self.assertContains(resp, 'id="btn-preview"')
        self.assertContains(resp, 'id="id_preview"')

    def test_adhoc_form_has_preview_button(self):
        """Ad-hoc export form should have a Preview on Screen button."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Preview on Screen")
        self.assertContains(resp, 'id="btn-preview"')
        self.assertContains(resp, 'id="id_preview"')
