"""Tests for the reports app — fiscal year functionality, metric export, demographics, and achievements."""
from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.clients.models import (
    ClientFile,
    ClientProgramEnrolment,
    CustomFieldDefinition,
    CustomFieldGroup,
    ClientDetailValue,
)
from apps.notes.models import (
    MetricValue,
    ProgressNote,
    ProgressNoteTarget,
)
from apps.plans.models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
)
from apps.programs.models import Program, UserProgramRole
from apps.reports.achievements import (
    calculate_achievement_status,
    get_client_achievement_rate,
    get_program_achievement_rate,
    get_achievement_summary,
    format_achievement_summary,
)
from apps.reports.demographics import (
    get_age_range,
    group_clients_by_age,
    group_clients_by_custom_field,
    get_demographic_field_choices,
    parse_grouping_choice,
)
from apps.reports.utils import (
    get_fiscal_year_range,
    get_current_fiscal_year,
    get_fiscal_year_choices,
)
from apps.reports.forms import MetricExportForm
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


class FiscalYearUtilsTest(TestCase):
    """Test fiscal year utility functions."""

    def test_get_fiscal_year_range_returns_correct_dates(self):
        """Fiscal year 2025-26 should return April 1, 2025 to March 31, 2026."""
        date_from, date_to = get_fiscal_year_range(2025)
        self.assertEqual(date_from, date(2025, 4, 1))
        self.assertEqual(date_to, date(2026, 3, 31))

    def test_get_fiscal_year_range_different_year(self):
        """Fiscal year 2023-24 should return April 1, 2023 to March 31, 2024."""
        date_from, date_to = get_fiscal_year_range(2023)
        self.assertEqual(date_from, date(2023, 4, 1))
        self.assertEqual(date_to, date(2024, 3, 31))

    @patch("apps.reports.utils.date")
    def test_get_current_fiscal_year_in_may(self, mock_date):
        """In May 2025, current fiscal year should be 2025 (FY 2025-26)."""
        mock_date.today.return_value = date(2025, 5, 15)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        result = get_current_fiscal_year()
        self.assertEqual(result, 2025)

    @patch("apps.reports.utils.date")
    def test_get_current_fiscal_year_in_january(self, mock_date):
        """In January 2026, current fiscal year should be 2025 (FY 2025-26)."""
        mock_date.today.return_value = date(2026, 1, 15)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        result = get_current_fiscal_year()
        self.assertEqual(result, 2025)

    @patch("apps.reports.utils.date")
    def test_get_current_fiscal_year_in_march(self, mock_date):
        """In March 2026, current fiscal year should be 2025 (FY 2025-26)."""
        mock_date.today.return_value = date(2026, 3, 31)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        result = get_current_fiscal_year()
        self.assertEqual(result, 2025)

    @patch("apps.reports.utils.date")
    def test_get_current_fiscal_year_in_april(self, mock_date):
        """In April 2026, current fiscal year should be 2026 (FY 2026-27)."""
        mock_date.today.return_value = date(2026, 4, 1)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        result = get_current_fiscal_year()
        self.assertEqual(result, 2026)

    @patch("apps.reports.utils.date")
    def test_get_fiscal_year_choices_returns_five_years(self, mock_date):
        """Default should return 5 fiscal year choices."""
        mock_date.today.return_value = date(2025, 6, 15)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        choices = get_fiscal_year_choices()
        self.assertEqual(len(choices), 5)
        # First choice should be current FY
        self.assertEqual(choices[0], ("2025", "FY 2025-26"))
        # Last choice should be 4 years ago
        self.assertEqual(choices[4], ("2021", "FY 2021-22"))

    @patch("apps.reports.utils.date")
    def test_get_fiscal_year_choices_custom_count(self, mock_date):
        """Can request different number of years."""
        mock_date.today.return_value = date(2025, 6, 15)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        choices = get_fiscal_year_choices(num_years=3)
        self.assertEqual(len(choices), 3)

    def test_fiscal_year_label_format(self):
        """Fiscal year labels should use short format (e.g., FY 2025-26)."""
        # Test that end year is properly shortened
        date_from, date_to = get_fiscal_year_range(2025)
        self.assertEqual(date_to.year, 2026)
        # The label format is tested in get_fiscal_year_choices
        # but we verify the underlying date calculation is correct


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricExportFormTest(TestCase):
    """Test the MetricExportForm with fiscal year field."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.metric = MetricDefinition.objects.create(
            name="Test Metric",
            definition="A test metric",
            category="custom",
            is_enabled=True,
            status="active",
        )

    def test_form_has_fiscal_year_field(self):
        """Form should include fiscal_year field."""
        form = MetricExportForm()
        self.assertIn("fiscal_year", form.fields)

    def test_form_fiscal_year_choices_include_blank(self):
        """Fiscal year choices should include a blank option."""
        form = MetricExportForm()
        choices = form.fields["fiscal_year"].choices
        # First choice should be blank
        self.assertEqual(choices[0][0], "")
        self.assertEqual(choices[0][1], "— Custom date range —")

    def test_form_valid_with_fiscal_year(self):
        """Form should be valid when fiscal year is selected (no manual dates)."""
        form = MetricExportForm(data={
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "2025",
            "format": "csv",
        })
        self.assertTrue(form.is_valid(), form.errors)
        # Dates should be populated from fiscal year
        self.assertEqual(form.cleaned_data["date_from"], date(2025, 4, 1))
        self.assertEqual(form.cleaned_data["date_to"], date(2026, 3, 31))

    def test_form_valid_with_manual_dates(self):
        """Form should be valid with manual date range (no fiscal year)."""
        form = MetricExportForm(data={
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "",
            "date_from": "2025-01-01",
            "date_to": "2025-06-30",
            "format": "csv",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["date_from"], date(2025, 1, 1))
        self.assertEqual(form.cleaned_data["date_to"], date(2025, 6, 30))

    def test_form_invalid_without_dates_or_fiscal_year(self):
        """Form should be invalid if neither fiscal year nor dates provided."""
        form = MetricExportForm(data={
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "",
            "format": "csv",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("date_from", form.errors)
        self.assertIn("date_to", form.errors)

    def test_form_fiscal_year_overrides_manual_dates(self):
        """When fiscal year is selected, it should override any manual dates."""
        form = MetricExportForm(data={
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "2024",
            "date_from": "2025-01-01",  # These should be ignored
            "date_to": "2025-06-30",
            "format": "csv",
        })
        self.assertTrue(form.is_valid(), form.errors)
        # Dates should come from fiscal year, not manual entry
        self.assertEqual(form.cleaned_data["date_from"], date(2024, 4, 1))
        self.assertEqual(form.cleaned_data["date_to"], date(2025, 3, 31))

    def test_form_rejects_invalid_date_range(self):
        """Form should reject date_from after date_to."""
        form = MetricExportForm(data={
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "",
            "date_from": "2025-06-30",
            "date_to": "2025-01-01",
            "format": "csv",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("'Date from' must be before 'Date to'", str(form.errors))


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExportFormViewTest(TestCase):
    """Test the export form view with fiscal year selection."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False
        )
        self.program = Program.objects.create(name="Test Program", status="active")
        self.metric = MetricDefinition.objects.create(
            name="Test Metric",
            definition="A test metric",
            category="custom",
            is_enabled=True,
            status="active",
        )

    def test_admin_can_access_export_form(self):
        """Admin users should be able to access the export form."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fiscal Year")

    def test_nonadmin_cannot_access_export_form(self):
        """Non-admin users should not be able to access the export form."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/reports/export/")
        self.assertEqual(resp.status_code, 403)

    def test_export_form_displays_fiscal_year_dropdown(self):
        """Export form should display the fiscal year dropdown."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fiscal Year (April-March)")
        self.assertContains(resp, "Custom date range")

    def test_export_form_has_achievement_rate_checkbox(self):
        """Export form should include the achievement rate checkbox."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Include achievement rate")


class CalculateAchievementStatusTest(TestCase):
    """Test the calculate_achievement_status function."""

    def test_gte_comparison_meets_target(self):
        """Value >= target should return True for gte comparison."""
        self.assertTrue(calculate_achievement_status(10.0, 8.0, "gte"))
        self.assertTrue(calculate_achievement_status(8.0, 8.0, "gte"))

    def test_gte_comparison_misses_target(self):
        """Value < target should return False for gte comparison."""
        self.assertFalse(calculate_achievement_status(7.0, 8.0, "gte"))

    def test_lte_comparison_meets_target(self):
        """Value <= target should return True for lte comparison."""
        self.assertTrue(calculate_achievement_status(5.0, 8.0, "lte"))
        self.assertTrue(calculate_achievement_status(8.0, 8.0, "lte"))

    def test_lte_comparison_misses_target(self):
        """Value > target should return False for lte comparison."""
        self.assertFalse(calculate_achievement_status(10.0, 8.0, "lte"))

    def test_eq_comparison_meets_target(self):
        """Value == target should return True for eq comparison."""
        self.assertTrue(calculate_achievement_status(8.0, 8.0, "eq"))

    def test_eq_comparison_misses_target(self):
        """Value != target should return False for eq comparison."""
        self.assertFalse(calculate_achievement_status(7.0, 8.0, "eq"))
        self.assertFalse(calculate_achievement_status(9.0, 8.0, "eq"))

    def test_range_comparison_within_range(self):
        """Value within min-max should return True for range comparison."""
        self.assertTrue(calculate_achievement_status(5.0, 0.0, "range", min_value=0.0, max_value=10.0))
        self.assertTrue(calculate_achievement_status(0.0, 0.0, "range", min_value=0.0, max_value=10.0))
        self.assertTrue(calculate_achievement_status(10.0, 0.0, "range", min_value=0.0, max_value=10.0))

    def test_range_comparison_outside_range(self):
        """Value outside min-max should return False for range comparison."""
        self.assertFalse(calculate_achievement_status(-1.0, 0.0, "range", min_value=0.0, max_value=10.0))
        self.assertFalse(calculate_achievement_status(11.0, 0.0, "range", min_value=0.0, max_value=10.0))

    def test_range_comparison_without_bounds_returns_false(self):
        """Range comparison without min/max values should return False."""
        self.assertFalse(calculate_achievement_status(5.0, 0.0, "range"))
        self.assertFalse(calculate_achievement_status(5.0, 0.0, "range", min_value=0.0))
        self.assertFalse(calculate_achievement_status(5.0, 0.0, "range", max_value=10.0))


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GetClientAchievementRateTest(TestCase):
    """Test the get_client_achievement_rate function."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.metric = MetricDefinition.objects.create(
            name="Housing Stability Score",
            definition="Score from 0-10",
            category="housing",
            is_enabled=True,
            status="active",
            min_value=0.0,
            max_value=10.0,
        )
        self.user = User.objects.create_user(
            username="worker", password="testpass123"
        )
        self.client_file = ClientFile.objects.create(
            record_id="TEST-001",
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="enrolled",
        )
        # Create plan structure
        self.section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Housing Goals",
            status="default",
        )
        self.target = PlanTarget.objects.create(
            plan_section=self.section,
            client_file=self.client_file,
            name="Stable Housing",
            status="default",
        )
        PlanTargetMetric.objects.create(
            plan_target=self.target,
            metric_def=self.metric,
        )

    def _create_metric_value(self, value, days_ago=0):
        """Helper to create a metric value with a specific date."""
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="full",
            author=self.user,
            created_at=timezone.now() - timedelta(days=days_ago),
        )
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note,
            plan_target=self.target,
        )
        return MetricValue.objects.create(
            progress_note_target=pnt,
            metric_def=self.metric,
            value=str(value),
        )

    def test_no_data_returns_zero_rate(self):
        """Client with no metric data should return 0% achievement rate."""
        result = get_client_achievement_rate(
            self.client_file, self.metric, 8.0
        )
        self.assertEqual(result["total_measurements"], 0)
        self.assertEqual(result["measurements_met_target"], 0)
        self.assertEqual(result["achievement_rate"], 0.0)
        self.assertIsNone(result["latest_value"])

    def test_all_measurements_meet_target(self):
        """When all measurements meet target, rate should be 100%."""
        self._create_metric_value(9.0, days_ago=10)
        self._create_metric_value(8.0, days_ago=5)
        self._create_metric_value(10.0, days_ago=0)

        result = get_client_achievement_rate(
            self.client_file, self.metric, 8.0, comparison="gte"
        )
        self.assertEqual(result["total_measurements"], 3)
        self.assertEqual(result["measurements_met_target"], 3)
        self.assertEqual(result["achievement_rate"], 100.0)
        self.assertEqual(result["latest_value"], 10.0)
        self.assertTrue(result["latest_met_target"])

    def test_some_measurements_meet_target(self):
        """Rate should reflect proportion of measurements meeting target."""
        self._create_metric_value(5.0, days_ago=10)  # miss
        self._create_metric_value(8.0, days_ago=5)   # meet
        self._create_metric_value(6.0, days_ago=0)   # miss

        result = get_client_achievement_rate(
            self.client_file, self.metric, 8.0, comparison="gte"
        )
        self.assertEqual(result["total_measurements"], 3)
        self.assertEqual(result["measurements_met_target"], 1)
        self.assertAlmostEqual(result["achievement_rate"], 33.3, places=1)
        self.assertEqual(result["latest_value"], 6.0)
        self.assertFalse(result["latest_met_target"])

    def test_date_range_filtering(self):
        """Should only count measurements within date range."""
        self._create_metric_value(9.0, days_ago=30)  # outside range
        self._create_metric_value(8.0, days_ago=5)   # inside range

        date_from = date.today() - timedelta(days=10)
        date_to = date.today()

        result = get_client_achievement_rate(
            self.client_file, self.metric, 8.0,
            date_from=date_from, date_to=date_to, comparison="gte"
        )
        self.assertEqual(result["total_measurements"], 1)
        self.assertEqual(result["measurements_met_target"], 1)
        self.assertEqual(result["achievement_rate"], 100.0)

    def test_non_numeric_values_ignored(self):
        """Non-numeric values should be excluded from calculations."""
        self._create_metric_value(8.0, days_ago=5)
        self._create_metric_value("N/A", days_ago=0)

        result = get_client_achievement_rate(
            self.client_file, self.metric, 8.0, comparison="gte"
        )
        self.assertEqual(result["total_measurements"], 1)
        self.assertEqual(result["measurements_met_target"], 1)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GetProgramAchievementRateTest(TestCase):
    """Test the get_program_achievement_rate function."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.metric = MetricDefinition.objects.create(
            name="PHQ-9 Score",
            definition="Depression screening score",
            category="mental_health",
            is_enabled=True,
            status="active",
            min_value=0.0,
            max_value=27.0,
        )
        self.user = User.objects.create_user(
            username="worker", password="testpass123"
        )

    def _create_client_with_values(self, record_id, values):
        """Helper to create a client with metric values."""
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client,
            program=self.program,
            status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client,
            name="Mental Health",
            status="default",
        )
        target = PlanTarget.objects.create(
            plan_section=section,
            client_file=client,
            name="Reduce Depression",
            status="default",
        )
        PlanTargetMetric.objects.create(
            plan_target=target,
            metric_def=self.metric,
        )
        for i, value in enumerate(values):
            note = ProgressNote.objects.create(
                client_file=client,
                note_type="full",
                author=self.user,
                created_at=timezone.now() - timedelta(days=len(values) - i),
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note,
                plan_target=target,
            )
            MetricValue.objects.create(
                progress_note_target=pnt,
                metric_def=self.metric,
                value=str(value),
            )
        return client

    def test_no_clients_returns_zero(self):
        """Programme with no client data should return 0% achievement."""
        result = get_program_achievement_rate(
            self.program, self.metric, 10.0
        )
        self.assertEqual(result["total_clients"], 0)
        self.assertEqual(result["clients_met_target"], 0)
        self.assertEqual(result["achievement_rate"], 0.0)

    def test_all_clients_meet_target(self):
        """When all clients meet target, rate should be 100%."""
        # PHQ-9 is a reduction metric — lower is better
        self._create_client_with_values("CLIENT-001", [15, 12, 8])  # meets <=10
        self._create_client_with_values("CLIENT-002", [20, 15, 5])  # meets <=10

        result = get_program_achievement_rate(
            self.program, self.metric, 10.0, comparison="lte", use_latest=True
        )
        self.assertEqual(result["total_clients"], 2)
        self.assertEqual(result["clients_met_target"], 2)
        self.assertEqual(result["achievement_rate"], 100.0)

    def test_some_clients_meet_target(self):
        """Rate should reflect proportion of clients meeting target."""
        self._create_client_with_values("CLIENT-001", [15, 12, 8])   # latest=8, meets
        self._create_client_with_values("CLIENT-002", [20, 15, 12])  # latest=12, misses
        self._create_client_with_values("CLIENT-003", [18, 14, 10])  # latest=10, meets
        self._create_client_with_values("CLIENT-004", [22, 18, 15])  # latest=15, misses

        result = get_program_achievement_rate(
            self.program, self.metric, 10.0, comparison="lte", use_latest=True
        )
        self.assertEqual(result["total_clients"], 4)
        self.assertEqual(result["clients_met_target"], 2)
        self.assertEqual(result["achievement_rate"], 50.0)

    def test_use_average_instead_of_latest(self):
        """Should use average when use_latest=False."""
        # Client with average = 10 (8+10+12)/3 = 10
        self._create_client_with_values("CLIENT-001", [8, 10, 12])

        # Using latest (12) would miss the target of <=10
        result_latest = get_program_achievement_rate(
            self.program, self.metric, 10.0, comparison="lte", use_latest=True
        )
        self.assertEqual(result_latest["clients_met_target"], 0)

        # Using average (10) would meet the target of <=10
        result_avg = get_program_achievement_rate(
            self.program, self.metric, 10.0, comparison="lte", use_latest=False
        )
        self.assertEqual(result_avg["clients_met_target"], 1)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GetAchievementSummaryTest(TestCase):
    """Test the get_achievement_summary function."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.metric1 = MetricDefinition.objects.create(
            name="Housing Score",
            definition="Housing stability score",
            category="housing",
            is_enabled=True,
            status="active",
            min_value=0.0,
            max_value=10.0,  # Target threshold
        )
        self.metric2 = MetricDefinition.objects.create(
            name="Employment Rate",
            definition="Percent employed",
            category="employment",
            is_enabled=True,
            status="active",
            min_value=0.0,
            max_value=100.0,  # Target threshold
        )
        self.metric_no_target = MetricDefinition.objects.create(
            name="Engagement Score",
            definition="Subjective engagement",
            category="general",
            is_enabled=True,
            status="active",
            # No max_value = no target
        )
        self.user = User.objects.create_user(
            username="worker", password="testpass123"
        )

    def _create_client_with_metrics(self, record_id, metric_values):
        """Helper to create a client with multiple metric values."""
        client = ClientFile.objects.create(record_id=record_id)
        ClientProgramEnrolment.objects.create(
            client_file=client,
            program=self.program,
            status="enrolled",
        )
        section = PlanSection.objects.create(
            client_file=client,
            name="Goals",
            status="default",
        )

        for metric_def, values in metric_values.items():
            target = PlanTarget.objects.create(
                plan_section=section,
                client_file=client,
                name=f"Target for {metric_def.name}",
                status="default",
            )
            PlanTargetMetric.objects.create(
                plan_target=target,
                metric_def=metric_def,
            )
            for i, value in enumerate(values):
                note = ProgressNote.objects.create(
                    client_file=client,
                    note_type="full",
                    author=self.user,
                    created_at=timezone.now() - timedelta(days=len(values) - i),
                )
                pnt = ProgressNoteTarget.objects.create(
                    progress_note=note,
                    plan_target=target,
                )
                MetricValue.objects.create(
                    progress_note_target=pnt,
                    metric_def=metric_def,
                    value=str(value),
                )
        return client

    def test_empty_program_returns_zeros(self):
        """Programme with no data should return zero counts."""
        result = get_achievement_summary(self.program)
        self.assertEqual(result["total_clients"], 0)
        self.assertEqual(result["clients_met_any_target"], 0)
        self.assertEqual(result["overall_rate"], 0.0)
        self.assertEqual(result["by_metric"], [])

    def test_summary_includes_all_metrics(self):
        """Summary should include breakdown for each metric with data."""
        self._create_client_with_metrics("CLIENT-001", {
            self.metric1: [8, 9, 10],   # meets target (10)
            self.metric2: [50, 80, 100],  # meets target (100)
        })

        result = get_achievement_summary(
            self.program,
            metric_defs=[self.metric1, self.metric2],
        )
        self.assertEqual(result["total_clients"], 1)
        self.assertEqual(len(result["by_metric"]), 2)

        # Find metric1 in results
        m1_result = next(m for m in result["by_metric"] if m["metric_id"] == self.metric1.pk)
        self.assertEqual(m1_result["metric_name"], "Housing Score")
        self.assertEqual(m1_result["target_value"], 10.0)
        self.assertTrue(m1_result["has_target"])
        self.assertEqual(m1_result["clients_met_target"], 1)
        self.assertEqual(m1_result["achievement_rate"], 100.0)

    def test_metrics_without_target_handled_gracefully(self):
        """Metrics without max_value should be marked as having no target."""
        self._create_client_with_metrics("CLIENT-001", {
            self.metric_no_target: [5, 6, 7],
        })

        result = get_achievement_summary(
            self.program,
            metric_defs=[self.metric_no_target],
        )
        self.assertEqual(result["total_clients"], 1)
        m_result = result["by_metric"][0]
        self.assertFalse(m_result["has_target"])
        self.assertIsNone(m_result["clients_met_target"])
        self.assertIsNone(m_result["achievement_rate"])


class FormatAchievementSummaryTest(TestCase):
    """Test the format_achievement_summary function."""

    def test_format_with_data(self):
        """Should format summary as readable text."""
        summary = {
            "total_clients": 20,
            "clients_met_any_target": 15,
            "overall_rate": 75.0,
            "by_metric": [
                {
                    "metric_id": 1,
                    "metric_name": "Housing Score",
                    "target_value": 10.0,
                    "has_target": True,
                    "total_clients": 20,
                    "clients_met_target": 16,
                    "achievement_rate": 80.0,
                },
                {
                    "metric_id": 2,
                    "metric_name": "Engagement",
                    "target_value": None,
                    "has_target": False,
                    "total_clients": 15,
                    "clients_met_target": None,
                    "achievement_rate": None,
                },
            ],
        }
        result = format_achievement_summary(summary)
        self.assertIn("15 of 20 clients (75.0%)", result)
        self.assertIn("Housing Score: 16 of 20 clients (80.0%) met target of 10.0", result)
        self.assertIn("Engagement: 15 clients (no target defined)", result)

    def test_format_with_no_data(self):
        """Should handle empty summary gracefully."""
        summary = {
            "total_clients": 0,
            "clients_met_any_target": 0,
            "overall_rate": 0.0,
            "by_metric": [],
        }
        result = format_achievement_summary(summary)
        self.assertIn("No client data available", result)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AchievementRateFormTest(TestCase):
    """Test the achievement rate checkbox in the export form."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.metric = MetricDefinition.objects.create(
            name="Test Metric",
            definition="A test metric",
            is_enabled=True,
            status="active",
        )

    def test_form_has_achievement_rate_field(self):
        """Form should include include_achievement_rate field."""
        form = MetricExportForm()
        self.assertIn("include_achievement_rate", form.fields)

    def test_form_valid_with_achievement_rate(self):
        """Form should be valid with achievement rate checkbox checked."""
        form = MetricExportForm(data={
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "2025",
            "format": "csv",
            "include_achievement_rate": True,
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["include_achievement_rate"])

    def test_form_valid_without_achievement_rate(self):
        """Form should be valid with achievement rate checkbox unchecked."""
        form = MetricExportForm(data={
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "2025",
            "format": "csv",
            "include_achievement_rate": False,
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["include_achievement_rate"])


# =============================================================================
# Demographic Grouping Tests (RPT4)
# =============================================================================


class AgeRangeTests(TestCase):
    """Tests for the get_age_range function."""

    def test_age_range_child(self):
        """Birth date resulting in age 10 should return '0-17'."""
        as_of = date(2025, 6, 15)
        birth_date = date(2015, 1, 1)
        result = get_age_range(birth_date, as_of)
        self.assertEqual(result, "0-17")

    def test_age_range_young_adult(self):
        """Birth date resulting in age 22 should return '18-24'."""
        as_of = date(2025, 6, 15)
        birth_date = date(2003, 1, 1)
        result = get_age_range(birth_date, as_of)
        self.assertEqual(result, "18-24")

    def test_age_range_adult_25_34(self):
        """Birth date resulting in age 30 should return '25-34'."""
        as_of = date(2025, 6, 15)
        birth_date = date(1995, 1, 1)
        result = get_age_range(birth_date, as_of)
        self.assertEqual(result, "25-34")

    def test_age_range_adult_35_44(self):
        """Birth date resulting in age 40 should return '35-44'."""
        as_of = date(2025, 6, 15)
        birth_date = date(1985, 1, 1)
        result = get_age_range(birth_date, as_of)
        self.assertEqual(result, "35-44")

    def test_age_range_adult_45_54(self):
        """Birth date resulting in age 50 should return '45-54'."""
        as_of = date(2025, 6, 15)
        birth_date = date(1975, 1, 1)
        result = get_age_range(birth_date, as_of)
        self.assertEqual(result, "45-54")

    def test_age_range_adult_55_64(self):
        """Birth date resulting in age 60 should return '55-64'."""
        as_of = date(2025, 6, 15)
        birth_date = date(1965, 1, 1)
        result = get_age_range(birth_date, as_of)
        self.assertEqual(result, "55-64")

    def test_age_range_senior(self):
        """Birth date resulting in age 70 should return '65+'."""
        as_of = date(2025, 6, 15)
        birth_date = date(1955, 1, 1)
        result = get_age_range(birth_date, as_of)
        self.assertEqual(result, "65+")

    def test_age_range_boundary_17_to_18(self):
        """Person turning 18 today should be in '18-24'."""
        as_of = date(2025, 6, 15)
        birth_date = date(2007, 6, 15)  # Exactly 18 today
        result = get_age_range(birth_date, as_of)
        self.assertEqual(result, "18-24")

    def test_age_range_boundary_still_17(self):
        """Person turning 18 tomorrow should still be in '0-17'."""
        as_of = date(2025, 6, 15)
        birth_date = date(2007, 6, 16)  # Turns 18 tomorrow
        result = get_age_range(birth_date, as_of)
        self.assertEqual(result, "0-17")

    def test_age_range_none_birth_date(self):
        """None birth date should return 'Unknown'."""
        result = get_age_range(None)
        self.assertEqual(result, "Unknown")

    def test_age_range_empty_string(self):
        """Empty string birth date should return 'Unknown'."""
        result = get_age_range("")
        self.assertEqual(result, "Unknown")

    def test_age_range_string_date(self):
        """String date format should be handled correctly."""
        as_of = date(2025, 6, 15)
        result = get_age_range("1990-01-15", as_of)
        self.assertEqual(result, "35-44")

    def test_age_range_invalid_string(self):
        """Invalid string should return 'Unknown'."""
        result = get_age_range("not-a-date")
        self.assertEqual(result, "Unknown")

    def test_age_range_uses_today_by_default(self):
        """When as_of_date is None, should use today's date."""
        birth_date = date(2000, 1, 1)
        result = get_age_range(birth_date)
        # Should return some valid range, not Unknown
        self.assertIn(result, ["18-24", "25-34", "35-44"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GroupClientsByAgeTests(TestCase):
    """Tests for the group_clients_by_age function."""

    def setUp(self):
        enc_module._fernet = None
        # Create clients with different ages
        self.client1 = ClientFile.objects.create()
        self.client1.first_name = "Child"
        self.client1.last_name = "One"
        self.client1.birth_date = date(2015, 1, 1)  # Age 10
        self.client1.save()

        self.client2 = ClientFile.objects.create()
        self.client2.first_name = "Adult"
        self.client2.last_name = "Two"
        self.client2.birth_date = date(1990, 1, 1)  # Age 35
        self.client2.save()

        self.client3 = ClientFile.objects.create()
        self.client3.first_name = "Senior"
        self.client3.last_name = "Three"
        self.client3.birth_date = date(1950, 1, 1)  # Age 75
        self.client3.save()

        self.client4 = ClientFile.objects.create()
        self.client4.first_name = "No"
        self.client4.last_name = "Birthday"
        # No birth date set
        self.client4.save()

    def test_group_clients_by_age(self):
        """Should group clients into correct age ranges."""
        client_ids = [self.client1.pk, self.client2.pk, self.client3.pk, self.client4.pk]
        as_of = date(2025, 6, 15)

        groups = group_clients_by_age(client_ids, as_of)

        self.assertIn("0-17", groups)
        self.assertIn(self.client1.pk, groups["0-17"])

        self.assertIn("35-44", groups)
        self.assertIn(self.client2.pk, groups["35-44"])

        self.assertIn("65+", groups)
        self.assertIn(self.client3.pk, groups["65+"])

        self.assertIn("Unknown", groups)
        self.assertIn(self.client4.pk, groups["Unknown"])

    def test_group_clients_empty_list(self):
        """Empty client list should return empty dict."""
        groups = group_clients_by_age([])
        self.assertEqual(groups, {})


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GroupClientsByCustomFieldTests(TestCase):
    """Tests for the group_clients_by_custom_field function."""

    def setUp(self):
        enc_module._fernet = None
        # Create custom field group and definition
        self.field_group = CustomFieldGroup.objects.create(
            title="Demographics",
            sort_order=0,
        )
        self.gender_field = CustomFieldDefinition.objects.create(
            group=self.field_group,
            name="Gender",
            input_type="select",
            options_json=[
                {"value": "M", "label": "Male"},
                {"value": "F", "label": "Female"},
                {"value": "O", "label": "Other"},
            ],
        )
        self.text_field = CustomFieldDefinition.objects.create(
            group=self.field_group,
            name="Region",
            input_type="text",
        )

        # Create clients
        self.client1 = ClientFile.objects.create()
        self.client1.first_name = "John"
        self.client1.last_name = "Doe"
        self.client1.save()

        self.client2 = ClientFile.objects.create()
        self.client2.first_name = "Jane"
        self.client2.last_name = "Doe"
        self.client2.save()

        self.client3 = ClientFile.objects.create()
        self.client3.first_name = "No"
        self.client3.last_name = "Value"
        self.client3.save()

        # Set custom field values
        ClientDetailValue.objects.create(
            client_file=self.client1,
            field_def=self.gender_field,
            value="M",
        )
        ClientDetailValue.objects.create(
            client_file=self.client2,
            field_def=self.gender_field,
            value="F",
        )

    def test_group_by_dropdown_field_uses_labels(self):
        """Grouping by dropdown should use option labels, not raw values."""
        client_ids = [self.client1.pk, self.client2.pk, self.client3.pk]

        groups = group_clients_by_custom_field(client_ids, self.gender_field)

        # Should use labels "Male" and "Female", not "M" and "F"
        self.assertIn("Male", groups)
        self.assertIn(self.client1.pk, groups["Male"])

        self.assertIn("Female", groups)
        self.assertIn(self.client2.pk, groups["Female"])

        # Client without value should be "Unknown"
        self.assertIn("Unknown", groups)
        self.assertIn(self.client3.pk, groups["Unknown"])

    def test_group_by_text_field(self):
        """Grouping by text field should use raw values."""
        # Add text field values
        ClientDetailValue.objects.create(
            client_file=self.client1,
            field_def=self.text_field,
            value="Toronto",
        )
        ClientDetailValue.objects.create(
            client_file=self.client2,
            field_def=self.text_field,
            value="Ottawa",
        )

        client_ids = [self.client1.pk, self.client2.pk, self.client3.pk]

        groups = group_clients_by_custom_field(client_ids, self.text_field)

        self.assertIn("Toronto", groups)
        self.assertIn(self.client1.pk, groups["Toronto"])

        self.assertIn("Ottawa", groups)
        self.assertIn(self.client2.pk, groups["Ottawa"])

        self.assertIn("Unknown", groups)
        self.assertIn(self.client3.pk, groups["Unknown"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DemographicFieldChoicesTests(TestCase):
    """Tests for the get_demographic_field_choices function."""

    def setUp(self):
        enc_module._fernet = None
        self.field_group = CustomFieldGroup.objects.create(
            title="Demographics",
            sort_order=0,
        )

    def test_choices_include_no_grouping_and_age_range(self):
        """Choices should always include 'No grouping' and 'Age Range'."""
        choices = get_demographic_field_choices()

        values = [c[0] for c in choices]
        labels = [c[1] for c in choices]

        self.assertIn("", values)
        self.assertIn("age_range", values)
        self.assertIn("No grouping", labels)
        self.assertIn("Age Range", labels)

    def test_choices_include_suitable_custom_fields(self):
        """Choices should include active, non-sensitive select and text fields."""
        # Create suitable fields
        gender_field = CustomFieldDefinition.objects.create(
            group=self.field_group,
            name="Gender",
            input_type="select",
            status="active",
            is_sensitive=False,
        )
        region_field = CustomFieldDefinition.objects.create(
            group=self.field_group,
            name="Region",
            input_type="text",
            status="active",
            is_sensitive=False,
        )

        choices = get_demographic_field_choices()

        values = [c[0] for c in choices]
        labels = [c[1] for c in choices]

        self.assertIn(f"custom_{gender_field.pk}", values)
        self.assertIn(f"custom_{region_field.pk}", values)
        self.assertIn("Demographics: Gender", labels)
        self.assertIn("Demographics: Region", labels)

    def test_choices_exclude_sensitive_fields(self):
        """Choices should not include sensitive fields."""
        sensitive_field = CustomFieldDefinition.objects.create(
            group=self.field_group,
            name="SIN",
            input_type="text",
            status="active",
            is_sensitive=True,  # Sensitive!
        )

        choices = get_demographic_field_choices()

        values = [c[0] for c in choices]
        self.assertNotIn(f"custom_{sensitive_field.pk}", values)

    def test_choices_exclude_date_and_number_fields(self):
        """Choices should not include date or number fields."""
        date_field = CustomFieldDefinition.objects.create(
            group=self.field_group,
            name="Start Date",
            input_type="date",
            status="active",
        )
        number_field = CustomFieldDefinition.objects.create(
            group=self.field_group,
            name="Income",
            input_type="number",
            status="active",
        )

        choices = get_demographic_field_choices()

        values = [c[0] for c in choices]
        self.assertNotIn(f"custom_{date_field.pk}", values)
        self.assertNotIn(f"custom_{number_field.pk}", values)

    def test_choices_exclude_archived_fields(self):
        """Choices should not include archived fields."""
        archived_field = CustomFieldDefinition.objects.create(
            group=self.field_group,
            name="Old Field",
            input_type="select",
            status="archived",  # Archived!
        )

        choices = get_demographic_field_choices()

        values = [c[0] for c in choices]
        self.assertNotIn(f"custom_{archived_field.pk}", values)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ParseGroupingChoiceTests(TestCase):
    """Tests for the parse_grouping_choice function."""

    def setUp(self):
        enc_module._fernet = None
        self.field_group = CustomFieldGroup.objects.create(
            title="Demographics",
            sort_order=0,
        )
        self.gender_field = CustomFieldDefinition.objects.create(
            group=self.field_group,
            name="Gender",
            input_type="select",
            status="active",
        )

    def test_parse_empty_string(self):
        """Empty string should return 'none' type."""
        grouping_type, field = parse_grouping_choice("")
        self.assertEqual(grouping_type, "none")
        self.assertIsNone(field)

    def test_parse_age_range(self):
        """'age_range' should return correct type."""
        grouping_type, field = parse_grouping_choice("age_range")
        self.assertEqual(grouping_type, "age_range")
        self.assertIsNone(field)

    def test_parse_custom_field(self):
        """'custom_123' should return field definition."""
        grouping_type, field = parse_grouping_choice(f"custom_{self.gender_field.pk}")
        self.assertEqual(grouping_type, "custom_field")
        self.assertEqual(field.pk, self.gender_field.pk)

    def test_parse_invalid_custom_field(self):
        """Invalid custom field ID should return 'none'."""
        grouping_type, field = parse_grouping_choice("custom_99999")
        self.assertEqual(grouping_type, "none")
        self.assertIsNone(field)

    def test_parse_invalid_format(self):
        """Invalid format should return 'none'."""
        grouping_type, field = parse_grouping_choice("invalid_value")
        self.assertEqual(grouping_type, "none")
        self.assertIsNone(field)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricExportFormGroupByTests(TestCase):
    """Tests for the group_by field in MetricExportForm."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")
        self.metric = MetricDefinition.objects.create(
            name="Test Metric",
            definition="A test metric",
            category="custom",
            is_enabled=True,
            status="active",
        )

    def test_form_has_group_by_field(self):
        """Form should include group_by field."""
        form = MetricExportForm()
        self.assertIn("group_by", form.fields)

    def test_form_group_by_choices_include_age_range(self):
        """Group by choices should include Age Range option."""
        form = MetricExportForm()
        choices = form.fields["group_by"].choices

        values = [c[0] for c in choices]
        labels = [c[1] for c in choices]

        self.assertIn("age_range", values)
        self.assertIn("Age Range", labels)

    def test_form_valid_with_group_by(self):
        """Form should be valid when group_by is selected."""
        form = MetricExportForm(data={
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "2025",
            "format": "csv",
            "group_by": "age_range",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["group_by"], "age_range")

    def test_form_valid_without_group_by(self):
        """Form should be valid when group_by is empty (no grouping)."""
        form = MetricExportForm(data={
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "2025",
            "format": "csv",
            "group_by": "",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["group_by"], "")


# =============================================================================
# Funder Report Template Tests (RPT6)
# =============================================================================


class CMTAgeGroupTests(TestCase):
    """Tests for CMT-specific age group calculations."""

    def test_cmt_age_group_child(self):
        """Birth date resulting in age 8 should return 'Child (0-12)'."""
        from apps.reports.cmt_export import get_cmt_age_group
        as_of = date(2025, 6, 15)
        birth_date = date(2017, 1, 1)  # Age 8
        result = get_cmt_age_group(birth_date, as_of)
        self.assertEqual(result, "Child (0-12)")

    def test_cmt_age_group_youth(self):
        """Birth date resulting in age 15 should return 'Youth (13-17)'."""
        from apps.reports.cmt_export import get_cmt_age_group
        as_of = date(2025, 6, 15)
        birth_date = date(2010, 1, 1)  # Age 15
        result = get_cmt_age_group(birth_date, as_of)
        self.assertEqual(result, "Youth (13-17)")

    def test_cmt_age_group_young_adult(self):
        """Birth date resulting in age 22 should return 'Young Adult (18-24)'."""
        from apps.reports.cmt_export import get_cmt_age_group
        as_of = date(2025, 6, 15)
        birth_date = date(2003, 1, 1)  # Age 22
        result = get_cmt_age_group(birth_date, as_of)
        self.assertEqual(result, "Young Adult (18-24)")

    def test_cmt_age_group_adult(self):
        """Birth date resulting in age 40 should return 'Adult (25-64)'."""
        from apps.reports.cmt_export import get_cmt_age_group
        as_of = date(2025, 6, 15)
        birth_date = date(1985, 1, 1)  # Age 40
        result = get_cmt_age_group(birth_date, as_of)
        self.assertEqual(result, "Adult (25-64)")

    def test_cmt_age_group_senior(self):
        """Birth date resulting in age 70 should return 'Senior (65+)'."""
        from apps.reports.cmt_export import get_cmt_age_group
        as_of = date(2025, 6, 15)
        birth_date = date(1955, 1, 1)  # Age 70
        result = get_cmt_age_group(birth_date, as_of)
        self.assertEqual(result, "Senior (65+)")

    def test_cmt_age_group_unknown_for_none(self):
        """None birth date should return 'Unknown'."""
        from apps.reports.cmt_export import get_cmt_age_group
        result = get_cmt_age_group(None)
        self.assertEqual(result, "Unknown")

    def test_cmt_age_group_boundary_12_to_13(self):
        """Person turning 13 today should be in 'Youth (13-17)'."""
        from apps.reports.cmt_export import get_cmt_age_group
        as_of = date(2025, 6, 15)
        birth_date = date(2012, 6, 15)  # Exactly 13 today
        result = get_cmt_age_group(birth_date, as_of)
        self.assertEqual(result, "Youth (13-17)")

    def test_cmt_age_group_string_date(self):
        """String date format should be handled correctly."""
        from apps.reports.cmt_export import get_cmt_age_group
        as_of = date(2025, 6, 15)
        result = get_cmt_age_group("1990-01-15", as_of)  # Age 35
        self.assertEqual(result, "Adult (25-64)")


class FormatFiscalYearLabelTests(TestCase):
    """Tests for fiscal year label formatting."""

    def test_format_fiscal_year_label_2025(self):
        """FY 2025 should format as 'FY 2025-26'."""
        from apps.reports.cmt_export import format_fiscal_year_label
        result = format_fiscal_year_label(2025)
        self.assertEqual(result, "FY 2025-26")

    def test_format_fiscal_year_label_2023(self):
        """FY 2023 should format as 'FY 2023-24'."""
        from apps.reports.cmt_export import format_fiscal_year_label
        result = format_fiscal_year_label(2023)
        self.assertEqual(result, "FY 2023-24")

    def test_format_fiscal_year_label_century_boundary(self):
        """FY 2099 should format as 'FY 2099-00'."""
        from apps.reports.cmt_export import format_fiscal_year_label
        result = format_fiscal_year_label(2099)
        self.assertEqual(result, "FY 2099-00")


class FormatNumberTests(TestCase):
    """Tests for number formatting with thousand separators."""

    def test_format_number_integer(self):
        """Integer should format with thousand separators."""
        from apps.reports.cmt_export import format_number
        self.assertEqual(format_number(1234), "1,234")
        self.assertEqual(format_number(1234567), "1,234,567")
        self.assertEqual(format_number(0), "0")

    def test_format_number_float(self):
        """Float should format with one decimal place."""
        from apps.reports.cmt_export import format_number
        self.assertEqual(format_number(1234.5), "1,234.5")
        self.assertEqual(format_number(1234.56), "1,234.6")  # Rounds

    def test_format_number_none(self):
        """None should return 'N/A'."""
        from apps.reports.cmt_export import format_number
        self.assertEqual(format_number(None), "N/A")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CMTExportFormTests(TestCase):
    """Tests for the CMTExportForm class."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", status="active")

    def test_form_has_required_fields(self):
        """CMT form should have program, fiscal_year, and format fields."""
        from apps.reports.forms import CMTExportForm
        form = CMTExportForm()
        self.assertIn("program", form.fields)
        self.assertIn("fiscal_year", form.fields)
        self.assertIn("format", form.fields)

    def test_form_fiscal_year_is_required(self):
        """CMT form should require fiscal year (unlike regular export form)."""
        from apps.reports.forms import CMTExportForm
        form = CMTExportForm(data={
            "program": self.program.pk,
            "format": "csv",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("fiscal_year", form.errors)

    def test_form_valid_with_all_fields(self):
        """CMT form should be valid with program and fiscal year."""
        from apps.reports.forms import CMTExportForm
        form = CMTExportForm(data={
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_populates_date_range_from_fiscal_year(self):
        """CMT form should populate date_from and date_to from fiscal year."""
        from apps.reports.forms import CMTExportForm
        form = CMTExportForm(data={
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["date_from"], date(2025, 4, 1))
        self.assertEqual(form.cleaned_data["date_to"], date(2026, 3, 31))

    def test_form_generates_fiscal_year_label(self):
        """CMT form should generate fiscal year label."""
        from apps.reports.forms import CMTExportForm
        form = CMTExportForm(data={
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["fiscal_year_label"], "FY 2025-26")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GenerateCMTDataTests(TestCase):
    """Tests for the generate_cmt_data function."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Test Program",
            description="A test programme for CMT export",
            status="active",
        )
        self.metric = MetricDefinition.objects.create(
            name="Housing Score",
            definition="Housing stability score",
            is_enabled=True,
            status="active",
            min_value=0.0,
            max_value=10.0,  # Target
        )
        self.user = User.objects.create_user(
            username="worker", password="testpass123"
        )

    def test_empty_program_returns_zeros(self):
        """Programme with no data should return zero counts."""
        from apps.reports.cmt_export import generate_cmt_data
        cmt_data = generate_cmt_data(
            self.program,
            date_from=date(2025, 4, 1),
            date_to=date(2026, 3, 31),
            fiscal_year_label="FY 2025-26",
        )

        self.assertEqual(cmt_data["total_individuals_served"], 0)
        self.assertEqual(cmt_data["new_clients_this_period"], 0)
        self.assertEqual(cmt_data["total_contacts"], 0)
        self.assertEqual(cmt_data["programme_name"], "Test Program")
        self.assertEqual(cmt_data["reporting_period"], "FY 2025-26")

    def test_cmt_data_includes_all_age_groups(self):
        """CMT data should include all standard age groups."""
        from apps.reports.cmt_export import generate_cmt_data, CMT_AGE_GROUPS
        cmt_data = generate_cmt_data(
            self.program,
            date_from=date(2025, 4, 1),
            date_to=date(2026, 3, 31),
        )

        # Should have all CMT age groups (plus Unknown)
        expected_groups = [label for _, _, label in CMT_AGE_GROUPS] + ["Unknown"]
        for group in expected_groups:
            self.assertIn(group, cmt_data["age_demographics"])

    def test_cmt_data_counts_clients_with_activity(self):
        """CMT should count clients who have notes in the period."""
        from apps.reports.cmt_export import generate_cmt_data

        # Create a client with a note in the period
        client = ClientFile.objects.create()
        client.first_name = "Test"
        client.last_name = "Client"
        client.birth_date = date(1990, 1, 1)  # Adult
        client.save()

        ClientProgramEnrolment.objects.create(
            client_file=client,
            program=self.program,
            status="enrolled",
        )

        # Create a progress note in the fiscal year
        note = ProgressNote.objects.create(
            client_file=client,
            note_type="quick",
            author=self.user,
            created_at=timezone.make_aware(datetime(2025, 6, 15, 10, 0)),
        )

        cmt_data = generate_cmt_data(
            self.program,
            date_from=date(2025, 4, 1),
            date_to=date(2026, 3, 31),
        )

        self.assertEqual(cmt_data["total_individuals_served"], 1)
        self.assertEqual(cmt_data["total_contacts"], 1)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GenerateCMTCSVRowsTests(TestCase):
    """Tests for the generate_cmt_csv_rows function."""

    def setUp(self):
        enc_module._fernet = None

    def test_csv_rows_include_header_sections(self):
        """CSV output should include standard CMT sections."""
        from apps.reports.cmt_export import generate_cmt_csv_rows

        cmt_data = {
            "generated_at": timezone.now(),
            "organisation_name": "Test Org",
            "programme_name": "Test Program",
            "programme_description": "",
            "reporting_period": "FY 2025-26",
            "total_individuals_served": 50,
            "new_clients_this_period": 10,
            "total_contacts": 200,
            "age_demographics": {
                "Child (0-12)": 5,
                "Youth (13-17)": 10,
                "Young Adult (18-24)": 15,
                "Adult (25-64)": 18,
                "Senior (65+)": 2,
                "Unknown": 0,
            },
            "age_demographics_total": 50,
            "primary_outcome": {
                "name": "Housing Score",
                "target_value": 10.0,
                "clients_measured": 40,
                "clients_achieved": 30,
                "achievement_rate": 75.0,
            },
            "secondary_outcomes": [],
            "achievement_summary": {
                "total_clients": 40,
                "clients_met_any_target": 30,
                "overall_rate": 75.0,
            },
        }

        rows = generate_cmt_csv_rows(cmt_data)

        # Flatten rows to a single string for easier searching
        flat_text = " ".join(" ".join(str(cell) for cell in row) for row in rows)

        self.assertIn("FUNDER REPORT TEMPLATE", flat_text)
        self.assertIn("ORGANISATION INFORMATION", flat_text)
        self.assertIn("SERVICE STATISTICS", flat_text)
        self.assertIn("AGE DEMOGRAPHICS", flat_text)
        self.assertIn("OUTCOME INDICATORS", flat_text)
        self.assertIn("Test Org", flat_text)
        self.assertIn("Test Program", flat_text)
        self.assertIn("75.0%", flat_text)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CMTExportViewTests(TestCase):
    """Tests for the CMT export view."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False
        )
        self.program = Program.objects.create(name="Test Program", status="active")

    def test_admin_can_access_cmt_export_form(self):
        """Admin users should be able to access the CMT export form."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/reports/cmt-export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Funder Report Template")

    def test_nonadmin_cannot_access_cmt_export(self):
        """Non-admin users should not be able to access CMT export."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/reports/cmt-export/")
        self.assertEqual(resp.status_code, 403)

    def test_cmt_export_form_displays_program_dropdown(self):
        """CMT export form should display programme dropdown."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/reports/cmt-export/")
        self.assertContains(resp, "Programme")
        self.assertContains(resp, "Test Program")

    def test_cmt_export_form_displays_fiscal_year_dropdown(self):
        """CMT export form should display fiscal year dropdown."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/reports/cmt-export/")
        self.assertContains(resp, "Fiscal Year")

    def test_cmt_export_csv_download(self):
        """CMT export should return CSV when csv format selected."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/reports/cmt-export/", {
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("CMT_Report", resp["Content-Disposition"])
        self.assertIn("FY_2025-26", resp["Content-Disposition"])

    def test_cmt_export_csv_content(self):
        """CMT CSV export should contain expected sections."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/reports/cmt-export/", {
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
        })
        content = resp.content.decode("utf-8")
        self.assertIn("FUNDER REPORT TEMPLATE", content)
        self.assertIn("Test Program", content)
        self.assertIn("SERVICE STATISTICS", content)
        self.assertIn("AGE DEMOGRAPHICS", content)
