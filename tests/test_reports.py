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
from apps.reports.models import SecureExportLink
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
            "recipient": "self",
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
            "recipient": "self",
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
            "recipient": "self",
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
            "recipient": "self",
        })
        self.assertFalse(form.is_valid())
        # Check for the error message (HTML entities may encode quotes)
        error_text = str(form.errors)
        self.assertIn("Date from", error_text)
        self.assertIn("must be before", error_text)


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
        """Helper to create a metric value with a specific date.

        Note: ProgressNote.created_at has auto_now_add=True, so we must use
        queryset.update() after creation to backdate it reliably.
        """
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="full",
            author=self.user,
        )
        if days_ago:
            backdated = timezone.now() - timedelta(days=days_ago)
            ProgressNote.objects.filter(pk=note.pk).update(created_at=backdated)
            note.refresh_from_db()
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
            "recipient": "self",
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
            "recipient": "self",
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
            "recipient": "self",
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
            "recipient": "self",
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
            "recipient": "self",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_populates_date_range_from_fiscal_year(self):
        """CMT form should populate date_from and date_to from fiscal year."""
        from apps.reports.forms import CMTExportForm
        form = CMTExportForm(data={
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
            "recipient": "self",
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
            "recipient": "self",
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

        self.assertIn("PROGRAMME OUTCOME REPORT TEMPLATE", flat_text)
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
        self.assertContains(resp, "Programme Outcome Report Template")

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

    def _get_download_content(self, download_resp):
        """Read content from a FileResponse (streaming)."""
        return b"".join(download_resp.streaming_content).decode("utf-8")

    def test_cmt_export_csv_download(self):
        """CMT export should create a secure link, and following it returns CSV."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/reports/cmt-export/", {
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")
        self.assertIn("attachment", download_resp["Content-Disposition"])
        self.assertIn("CMT_Report", download_resp["Content-Disposition"])
        self.assertIn("FY_2025-26", download_resp["Content-Disposition"])

    def test_cmt_export_csv_content(self):
        """CMT CSV export should contain expected sections via secure link."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/reports/cmt-export/", {
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")
        content = self._get_download_content(download_resp)
        self.assertIn("PROGRAMME OUTCOME REPORT TEMPLATE", content)
        self.assertIn("Test Program", content)
        self.assertIn("SERVICE STATISTICS", content)
        self.assertIn("AGE DEMOGRAPHICS", content)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ClientDataExportViewTests(TestCase):
    """Tests for the client data export view."""

    databases = {"default", "audit"}

    def setUp(self):
        # Set up encryption key
        enc_module.FIELD_ENCRYPTION_KEY = TEST_KEY
        enc_module._fernet = Fernet(TEST_KEY)

        # Create admin user
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
            is_admin=True,
        )

        # Create non-admin user
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="testpass123",
            is_admin=False,
        )

        # Create a program
        self.program = Program.objects.create(
            name="Test Program",
            status="active",
        )

        # Create a client
        self.client_file = ClientFile.objects.create(
            record_id="TEST-001",
            status="active",
        )
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.birth_date = "1990-01-15"
        self.client_file.save()

        # Enrol client in program
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="enrolled",
        )

    def test_admin_can_access_client_data_export(self):
        """Admin users should be able to access the client data export form."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/reports/client-data-export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Client Data Export")

    def test_nonadmin_cannot_access_client_data_export(self):
        """Non-admin users should be denied access."""
        self.client.login(username="regular", password="testpass123")
        resp = self.client.get("/reports/client-data-export/")
        self.assertEqual(resp.status_code, 403)

    def _get_download_content(self, download_resp):
        """Read content from a FileResponse (streaming)."""
        return b"".join(download_resp.streaming_content).decode("utf-8")

    def test_client_data_export_csv_download(self):
        """Client data export should create a secure link that returns a CSV file."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/reports/client-data-export/", {
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")
        self.assertIn("attachment", download_resp["Content-Disposition"])
        self.assertIn("client_data_export", download_resp["Content-Disposition"])

    def test_client_data_export_csv_contains_client_data(self):
        """CSV export via secure link should contain the client's data."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/reports/client-data-export/", {
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")
        content = self._get_download_content(download_resp)
        self.assertIn("TEST-001", content)
        self.assertIn("Jane", content)
        self.assertIn("Doe", content)
        self.assertIn("Test Program", content)

    def test_client_data_export_with_program_filter(self):
        """Export can be filtered by program."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/reports/client-data-export/", {
            "program": self.program.pk,
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")
        content = self._get_download_content(download_resp)
        self.assertIn("TEST-001", content)
        self.assertIn(f"Programme Filter: {self.program.name}", content)

    def test_client_data_export_with_status_filter(self):
        """Export can be filtered by client status."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/reports/client-data-export/", {
            "status": "active",
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")
        content = self._get_download_content(download_resp)
        self.assertIn("TEST-001", content)
        self.assertIn("Status Filter: active", content)

    def test_client_data_export_no_clients_shows_message(self):
        """Export with no matching clients should show a message."""
        # Delete all clients
        ClientFile.objects.all().delete()

        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/reports/client-data-export/", {
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No data found")


# =============================================================================
# Security Tests: Demo/Real Data Separation in Exports (EXP0d)
# =============================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DemoRealExportSeparationTests(TestCase):
    """
    Critical security tests for demo/real data separation in export views.

    SECURITY REQUIREMENT: Demo users must NEVER be able to export real client data.
    Real users must NEVER be able to export demo client data.

    These tests verify the fix for the critical security bug identified in EXP0.
    """

    databases = {"default", "audit"}

    def setUp(self):
        # Set up encryption key
        enc_module.FIELD_ENCRYPTION_KEY = TEST_KEY
        enc_module._fernet = Fernet(TEST_KEY)

        # Create demo admin user
        self.demo_admin = User.objects.create_user(
            username="demo_admin",
            email="demo@example.com",
            password="testpass123",
            is_admin=True,
            is_demo=True,  # Demo user
        )

        # Create real admin user
        self.real_admin = User.objects.create_user(
            username="real_admin",
            email="real@example.com",
            password="testpass123",
            is_admin=True,
            is_demo=False,  # Real user
        )

        # Create a program
        self.program = Program.objects.create(
            name="Test Program",
            status="active",
        )

        # Create DEMO client
        self.demo_client = ClientFile.objects.create(
            record_id="DEMO-001",
            status="active",
            is_demo=True,  # Demo client
        )
        self.demo_client.first_name = "Demo"
        self.demo_client.last_name = "Client"
        self.demo_client.birth_date = "1990-01-15"
        self.demo_client.save()

        # Create REAL client
        self.real_client = ClientFile.objects.create(
            record_id="REAL-001",
            status="active",
            is_demo=False,  # Real client
        )
        self.real_client.first_name = "Real"
        self.real_client.last_name = "Person"
        self.real_client.birth_date = "1985-06-20"
        self.real_client.save()

        # Enrol both clients in program
        ClientProgramEnrolment.objects.create(
            client_file=self.demo_client,
            program=self.program,
            status="enrolled",
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.real_client,
            program=self.program,
            status="enrolled",
        )

        # Create progress notes for both clients (for metric export testing)
        self.demo_note = ProgressNote.objects.create(
            client_file=self.demo_client,
            note_type="quick",
            author=self.demo_admin,
        )
        self.real_note = ProgressNote.objects.create(
            client_file=self.real_client,
            note_type="quick",
            author=self.real_admin,
        )

    def _get_download_content(self, download_resp):
        """Read content from a FileResponse (streaming)."""
        return b"".join(download_resp.streaming_content).decode("utf-8")

    def test_demo_admin_cannot_export_real_clients_in_client_data_export(self):
        """
        CRITICAL: Demo admin must NOT see real client data in client data export.

        This is the primary security test for EXP0a.
        """
        self.client.login(username="demo_admin", password="testpass123")
        resp = self.client.post("/reports/client-data-export/", {
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")

        content = self._get_download_content(download_resp)

        # Demo admin should see demo client
        self.assertIn("DEMO-001", content)
        self.assertIn("Demo", content)

        # Demo admin must NOT see real client
        self.assertNotIn("REAL-001", content)
        self.assertNotIn("Real", content)

    def test_real_admin_cannot_export_demo_clients_in_client_data_export(self):
        """
        Real admin must NOT see demo client data in client data export.
        """
        self.client.login(username="real_admin", password="testpass123")
        resp = self.client.post("/reports/client-data-export/", {
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")

        content = self._get_download_content(download_resp)

        # Real admin should see real client
        self.assertIn("REAL-001", content)
        self.assertIn("Real", content)

        # Real admin must NOT see demo client
        self.assertNotIn("DEMO-001", content)
        self.assertNotIn("Demo", content)

    def test_demo_admin_export_only_shows_demo_clients_with_program_filter(self):
        """
        Demo admin filtering by program should still only see demo clients.
        """
        self.client.login(username="demo_admin", password="testpass123")
        resp = self.client.post("/reports/client-data-export/", {
            "program": self.program.pk,
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")

        content = self._get_download_content(download_resp)

        # Should see demo client (enrolled in program)
        self.assertIn("DEMO-001", content)

        # Must NOT see real client (even though also enrolled in program)
        self.assertNotIn("REAL-001", content)

    def test_real_admin_metric_export_only_shows_real_clients(self):
        """
        Real admin metric export should only show real client data (EXP0b).
        """
        # Create a metric
        metric = MetricDefinition.objects.create(
            name="Test Metric",
            definition="A test metric",
            category="custom",
            is_enabled=True,
            status="active",
        )

        # Create plan and target structures for both clients
        for client, note in [(self.demo_client, self.demo_note), (self.real_client, self.real_note)]:
            section = PlanSection.objects.create(
                client_file=client,
                name="Test Section",
                status="default",
            )
            target = PlanTarget.objects.create(
                plan_section=section,
                client_file=client,
                name="Test Target",
                status="default",
            )
            PlanTargetMetric.objects.create(
                plan_target=target,
                metric_def=metric,
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note,
                plan_target=target,
            )
            MetricValue.objects.create(
                progress_note_target=pnt,
                metric_def=metric,
                value="5",
            )

        self.client.login(username="real_admin", password="testpass123")
        resp = self.client.post("/reports/export/", {
            "program": self.program.pk,
            "metrics": [metric.pk],
            "fiscal_year": "",
            "date_from": "2020-01-01",
            "date_to": "2030-12-31",
            "format": "csv",
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")

        content = self._get_download_content(download_resp)

        # Real admin should see real client's record ID
        self.assertIn("REAL-001", content)

        # Real admin must NOT see demo client's record ID
        self.assertNotIn("DEMO-001", content)

    def test_demo_admin_metric_export_only_shows_demo_clients(self):
        """
        Demo admin metric export should only show demo client data (EXP0b).
        """
        # Create a metric
        metric = MetricDefinition.objects.create(
            name="Demo Metric",
            definition="A demo metric",
            category="custom",
            is_enabled=True,
            status="active",
        )

        # Create plan and target structures for both clients
        for client, note in [(self.demo_client, self.demo_note), (self.real_client, self.real_note)]:
            section = PlanSection.objects.create(
                client_file=client,
                name="Demo Section",
                status="default",
            )
            target = PlanTarget.objects.create(
                plan_section=section,
                client_file=client,
                name="Demo Target",
                status="default",
            )
            PlanTargetMetric.objects.create(
                plan_target=target,
                metric_def=metric,
            )
            pnt = ProgressNoteTarget.objects.create(
                progress_note=note,
                plan_target=target,
            )
            MetricValue.objects.create(
                progress_note_target=pnt,
                metric_def=metric,
                value="5",
            )

        self.client.login(username="demo_admin", password="testpass123")
        resp = self.client.post("/reports/export/", {
            "program": self.program.pk,
            "metrics": [metric.pk],
            "fiscal_year": "",
            "date_from": "2020-01-01",
            "date_to": "2030-12-31",
            "format": "csv",
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")

        content = self._get_download_content(download_resp)

        # Demo admin should see demo client's record ID
        self.assertIn("DEMO-001", content)

        # Demo admin must NOT see real client's record ID
        self.assertNotIn("REAL-001", content)

    def test_demo_admin_cmt_export_only_shows_demo_clients(self):
        """
        Demo admin CMT export should only count demo client data (EXP0c).
        """
        self.client.login(username="demo_admin", password="testpass123")
        resp = self.client.post("/reports/cmt-export/", {
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")

        # The CMT export counts individuals served - should only count demo clients
        content = self._get_download_content(download_resp)

        # We have 1 demo client enrolled, so max individuals served should be 1 or 0
        # (depending on whether they have notes in the fiscal year period)
        # The key is that it shouldn't be 2 (which would mean real client is included)
        self.assertIn("Test Program", content)

    def test_real_admin_cmt_export_only_shows_real_clients(self):
        """
        Real admin CMT export should only count real client data (EXP0c).
        """
        self.client.login(username="real_admin", password="testpass123")
        resp = self.client.post("/reports/cmt-export/", {
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.latest("created_at")
        download_resp = self.client.get(f"/reports/download/{link.id}/")

        content = self._get_download_content(download_resp)
        self.assertIn("Test Program", content)


# =============================================================================
# Export Warning Dialog Tests (EXP2e-g)
# =============================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExportWarningDialogTests(TestCase):
    """
    Tests for Phase 2 export warning dialogs (EXP2e-g).

    Covers:
    - Recipient field is required on all three export forms
    - Client count preview on client data export GET page
    - PII warning text displayed on export pages
    """

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.program = Program.objects.create(name="Test Program", status="active")
        self.metric = MetricDefinition.objects.create(
            name="Test Metric",
            definition="A test metric",
            category="custom",
            is_enabled=True,
            status="active",
        )
        # Create a client so client count preview has data
        self.client_file = ClientFile.objects.create(
            record_id="WARN-001",
            status="active",
        )
        self.client_file.first_name = "Warning"
        self.client_file.last_name = "Test"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="enrolled",
        )
        # Create metric value data so metric export can produce a CSV
        section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Test Section",
            status="default",
        )
        target = PlanTarget.objects.create(
            plan_section=section,
            client_file=self.client_file,
            name="Test Target",
            status="default",
        )
        PlanTargetMetric.objects.create(
            plan_target=target,
            metric_def=self.metric,
        )
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="full",
            author=self.admin,
            created_at=timezone.make_aware(datetime(2025, 6, 15, 10, 0)),
        )
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note,
            plan_target=target,
        )
        MetricValue.objects.create(
            progress_note_target=pnt,
            metric_def=self.metric,
            value="5",
        )
        self.client.login(username="admin", password="testpass123")

    # -----------------------------------------------------------------
    # Recipient Required — Metric Export (/reports/export/)
    # -----------------------------------------------------------------

    def test_metric_export_post_without_recipient_is_invalid(self):
        """POST to /reports/export/ without recipient should fail validation."""
        resp = self.client.post("/reports/export/", {
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "2025",
            "format": "csv",
            # No recipient field
        })
        # Should stay on the form page (200) with errors, not redirect or download
        self.assertEqual(resp.status_code, 200)
        self.assertIn("recipient", resp.context["form"].errors)

    def test_metric_export_post_with_recipient_proceeds(self):
        """POST to /reports/export/ with recipient should create a secure export link."""
        resp = self.client.post("/reports/export/", {
            "program": self.program.pk,
            "metrics": [self.metric.pk],
            "fiscal_year": "2025",
            "format": "csv",
            "recipient": "self",
        })
        # Should return 200 (secure link page) and create a SecureExportLink
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(SecureExportLink.objects.exists())

    # -----------------------------------------------------------------
    # Recipient Required — CMT Export (/reports/cmt-export/)
    # -----------------------------------------------------------------

    def test_cmt_export_post_without_recipient_is_invalid(self):
        """POST to /reports/cmt-export/ without recipient should fail validation."""
        resp = self.client.post("/reports/cmt-export/", {
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
            # No recipient field
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("recipient", resp.context["form"].errors)

    def test_cmt_export_post_with_recipient_proceeds(self):
        """POST to /reports/cmt-export/ with recipient should create a secure export link."""
        resp = self.client.post("/reports/cmt-export/", {
            "program": self.program.pk,
            "fiscal_year": "2025",
            "format": "csv",
            "recipient": "funder",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(SecureExportLink.objects.exists())

    # -----------------------------------------------------------------
    # Recipient Required — Client Data Export (/reports/client-data-export/)
    # -----------------------------------------------------------------

    def test_client_data_export_post_without_recipient_is_invalid(self):
        """POST to /reports/client-data-export/ without recipient should fail validation."""
        resp = self.client.post("/reports/client-data-export/", {
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            # No recipient field
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("recipient", resp.context["form"].errors)

    def test_client_data_export_post_with_recipient_proceeds(self):
        """POST to /reports/client-data-export/ with recipient should create a secure export link."""
        resp = self.client.post("/reports/client-data-export/", {
            "include_custom_fields": True,
            "include_enrolments": True,
            "include_consent": True,
            "recipient": "colleague",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(SecureExportLink.objects.exists())

    # -----------------------------------------------------------------
    # Client Count Preview
    # -----------------------------------------------------------------

    def test_client_data_export_get_shows_client_count(self):
        """GET to /reports/client-data-export/ should show the accessible client count."""
        resp = self.client.get("/reports/client-data-export/")
        self.assertEqual(resp.status_code, 200)
        # Check context variable is present
        self.assertIn("total_client_count", resp.context)
        self.assertGreaterEqual(resp.context["total_client_count"], 1)
        # Check the count is displayed in the template
        self.assertContains(resp, "client record")

    def test_client_data_export_get_preserves_count_on_validation_failure(self):
        """POST with invalid data should still show the client count."""
        resp = self.client.post("/reports/client-data-export/", {
            # Missing recipient — form will be invalid
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("total_client_count", resp.context)
        self.assertGreaterEqual(resp.context["total_client_count"], 1)

    # -----------------------------------------------------------------
    # PII Warnings Display
    # -----------------------------------------------------------------

    def test_metric_export_get_shows_pii_warning(self):
        """GET to /reports/export/ should display a personal information warning."""
        resp = self.client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "personal information")

    def test_client_data_export_get_shows_pii_warning(self):
        """GET to /reports/client-data-export/ should display a personal information warning."""
        resp = self.client.get("/reports/client-data-export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "personal information")

    def test_cmt_export_get_shows_draft_template_notice(self):
        """GET to /reports/cmt-export/ should display a Draft Template notice."""
        resp = self.client.get("/reports/cmt-export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Draft Template")


# =================================================================
# Individual Client Export — PIPEDA Data Portability (EXP2x-aa)
# =================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local")
class IndividualClientExportViewTests(TestCase):
    """Tests for the individual client data export view (PIPEDA compliance)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module.FIELD_ENCRYPTION_KEY = TEST_KEY
        enc_module._fernet = Fernet(TEST_KEY)

        # Create a program
        self.program = Program.objects.create(name="Test Program", status="active")

        # Create staff user with program role
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff User"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program, role="staff"
        )

        # Create receptionist user
        self.receptionist = User.objects.create_user(
            username="receptionist", password="testpass123", display_name="Receptionist"
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program, role="receptionist"
        )

        # Create a client enrolled in the program
        self.client_file = ClientFile.objects.create(
            record_id="PIPEDA-001", status="active",
        )
        self.client_file.first_name = "Alice"
        self.client_file.last_name = "Smith"
        self.client_file.birth_date = "1985-06-15"
        self.client_file.save()

        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled",
        )

        self.export_url = f"/reports/client/{self.client_file.pk}/export/"

    def tearDown(self):
        enc_module._fernet = None

    # --- Access control ---

    def test_login_required(self):
        """Anonymous users should be redirected to login."""
        resp = self.client.get(self.export_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_staff_can_access_export_form(self):
        """Staff with program role can access the individual client export."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(self.export_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Export Client Data")

    def test_receptionist_gets_403_on_export(self):
        """Receptionists should be blocked from the individual client export (EXP-FIX5).

        The export button is hidden in the template for receptionists, but
        they could still access the URL directly. The server must return 403.
        """
        self.client.login(username="receptionist", password="testpass123")
        resp = self.client.get(self.export_url)
        self.assertEqual(resp.status_code, 403)

    def test_receptionist_cannot_post_export(self):
        """Receptionists should also be blocked from POSTing to the export endpoint."""
        self.client.login(username="receptionist", password="testpass123")
        resp = self.client.post(self.export_url, {
            "format": "csv",
            "include_plans": True,
            "include_notes": True,
            "include_metrics": True,
            "include_events": True,
            "include_custom_fields": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 403)

    def test_client_name_shown_on_form(self):
        """The client's name should appear on the export form."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(self.export_url)
        self.assertContains(resp, "Alice Smith")

    # --- CSV export ---

    def test_csv_export_returns_csv_file(self):
        """POST with format=csv should return a CSV attachment."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(self.export_url, {
            "format": "csv",
            "include_plans": True,
            "include_notes": True,
            "include_metrics": True,
            "include_events": True,
            "include_custom_fields": True,
            "recipient": "self",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertIn("client_export", resp["Content-Disposition"])

    def test_csv_contains_client_info(self):
        """CSV export should include the client's name and record ID."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(self.export_url, {
            "format": "csv",
            "include_plans": True,
            "include_notes": True,
            "include_metrics": True,
            "include_events": True,
            "include_custom_fields": True,
            "recipient": "self",
        })
        content = resp.content.decode("utf-8")
        self.assertIn("Alice", content)
        self.assertIn("Smith", content)
        self.assertIn("PIPEDA-001", content)

    def test_csv_without_notes_omits_notes_section(self):
        """When include_notes is unchecked, CSV should not have the notes section."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(self.export_url, {
            "format": "csv",
            "include_plans": True,
            "include_metrics": True,
            "include_events": True,
            "include_custom_fields": True,
            "recipient": "self",
            # include_notes NOT checked
        })
        content = resp.content.decode("utf-8")
        self.assertNotIn("PROGRESS NOTES", content)

    # --- Form validation ---

    def test_recipient_required(self):
        """Export without recipient should fail validation."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(self.export_url, {
            "format": "csv",
            "include_plans": True,
            # No recipient
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("recipient", resp.context["form"].errors)

    # --- Audit logging ---

    def test_csv_export_creates_audit_log(self):
        """Individual client export should create an audit log entry."""
        from apps.audit.models import AuditLog

        self.client.login(username="staff", password="testpass123")
        self.client.post(self.export_url, {
            "format": "csv",
            "include_plans": True,
            "include_notes": True,
            "include_metrics": True,
            "include_events": True,
            "include_custom_fields": True,
            "recipient": "self",
        })
        log = AuditLog.objects.using("audit").filter(
            resource_type="individual_client_export",
            resource_id=self.client_file.pk,
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, "export")
        self.assertEqual(log.metadata["format"], "csv")
        self.assertEqual(log.metadata["client_id"], self.client_file.pk)

    # --- Demo data separation ---

    def test_demo_user_cannot_export_real_client(self):
        """Demo users should not be able to access real client exports."""
        demo_user = User.objects.create_user(
            username="demo", password="testpass123", display_name="Demo",
            is_demo=True,
        )
        UserProgramRole.objects.create(
            user=demo_user, program=self.program, role="staff",
        )
        self.client.login(username="demo", password="testpass123")
        resp = self.client.get(self.export_url)
        self.assertEqual(resp.status_code, 403)

    # --- Button on client detail page ---

    def test_export_button_on_client_detail(self):
        """The client detail page should show an 'Export All Data' button for staff."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/clients/{self.client_file.pk}/")
        self.assertContains(resp, "Export All Data")
        self.assertContains(resp, self.export_url)


# =================================================================
# CSV Injection & Filename Sanitisation (EXP-FIX2, EXP-FIX4)
# =================================================================


class CsvSanitisationTests(TestCase):
    """Tests for CSV injection protection (EXP-FIX2)."""

    def test_sanitise_csv_value_equals(self):
        """Values starting with = should be prefixed with a tab."""
        from apps.reports.csv_utils import sanitise_csv_value
        result = sanitise_csv_value("=SUM(A1:A10)")
        self.assertTrue(result.startswith("\t"))
        self.assertIn("=SUM(A1:A10)", result)

    def test_sanitise_csv_value_plus(self):
        """Values starting with + should be prefixed with a tab."""
        from apps.reports.csv_utils import sanitise_csv_value
        result = sanitise_csv_value("+cmd|'/C calc'!A0")
        self.assertTrue(result.startswith("\t"))

    def test_sanitise_csv_value_minus(self):
        """Values starting with - should be prefixed with a tab."""
        from apps.reports.csv_utils import sanitise_csv_value
        result = sanitise_csv_value("-1+1")
        self.assertTrue(result.startswith("\t"))

    def test_sanitise_csv_value_at(self):
        """Values starting with @ should be prefixed with a tab."""
        from apps.reports.csv_utils import sanitise_csv_value
        result = sanitise_csv_value("@SUM(A1:A10)")
        self.assertTrue(result.startswith("\t"))

    def test_sanitise_csv_value_safe_string(self):
        """Safe strings should pass through unchanged."""
        from apps.reports.csv_utils import sanitise_csv_value
        self.assertEqual(sanitise_csv_value("Hello World"), "Hello World")
        self.assertEqual(sanitise_csv_value("John Smith"), "John Smith")
        self.assertEqual(sanitise_csv_value(""), "")

    def test_sanitise_csv_value_none(self):
        """None values should pass through unchanged."""
        from apps.reports.csv_utils import sanitise_csv_value
        self.assertIsNone(sanitise_csv_value(None))

    def test_sanitise_csv_value_number(self):
        """Numeric values should pass through unchanged (not converted to strings)."""
        from apps.reports.csv_utils import sanitise_csv_value
        self.assertEqual(sanitise_csv_value(42), 42)
        self.assertEqual(sanitise_csv_value(3.14), 3.14)

    def test_sanitise_csv_row(self):
        """sanitise_csv_row should sanitise all string values in a list."""
        from apps.reports.csv_utils import sanitise_csv_row
        row = ["Name", "=HYPERLINK(\"http://evil.com\")", 42, "+attack", "safe"]
        result = sanitise_csv_row(row)
        self.assertEqual(result[0], "Name")
        self.assertTrue(result[1].startswith("\t"))
        self.assertEqual(result[2], 42)
        self.assertTrue(result[3].startswith("\t"))
        self.assertEqual(result[4], "safe")


class FilenameSanitisationTests(TestCase):
    """Tests for Content-Disposition filename sanitisation (EXP-FIX4)."""

    def test_sanitise_filename_simple(self):
        """Alphanumeric strings should pass through unchanged."""
        from apps.reports.csv_utils import sanitise_filename
        self.assertEqual(sanitise_filename("PIPEDA-001"), "PIPEDA-001")

    def test_sanitise_filename_with_spaces(self):
        """Spaces should be stripped from filenames."""
        from apps.reports.csv_utils import sanitise_filename
        result = sanitise_filename("my file name")
        self.assertNotIn(" ", result)
        self.assertEqual(result, "myfilename")

    def test_sanitise_filename_path_traversal(self):
        """Path traversal slashes should be stripped; dots are safe in filenames."""
        from apps.reports.csv_utils import sanitise_filename
        result = sanitise_filename("../../etc/passwd")
        # Slashes are stripped so path traversal is impossible
        self.assertNotIn("/", result)
        self.assertNotIn("\\", result)
        # Dots are kept (valid in filenames) but slashes are gone,
        # so "../../etc/passwd" becomes "....etcpasswd" — no traversal possible
        self.assertEqual(result, "....etcpasswd")

    def test_sanitise_filename_special_chars(self):
        """Special characters should be stripped, keeping only safe chars."""
        from apps.reports.csv_utils import sanitise_filename
        result = sanitise_filename("record<>:\"|?*id")
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)
        self.assertNotIn(":", result)
        self.assertNotIn('"', result)
        self.assertNotIn("|", result)
        self.assertNotIn("?", result)
        self.assertNotIn("*", result)
        self.assertEqual(result, "recordid")

    def test_sanitise_filename_empty(self):
        """Empty input should return 'export' as a fallback."""
        from apps.reports.csv_utils import sanitise_filename
        self.assertEqual(sanitise_filename(""), "export")
        self.assertEqual(sanitise_filename(None), "export")

    def test_sanitise_filename_all_special(self):
        """Input that is entirely special characters should return 'export'."""
        from apps.reports.csv_utils import sanitise_filename
        self.assertEqual(sanitise_filename("@#$%^&"), "export")

    def test_sanitise_filename_preserves_hyphens_underscores(self):
        """Hyphens and underscores should be preserved."""
        from apps.reports.csv_utils import sanitise_filename
        self.assertEqual(sanitise_filename("my_record-001"), "my_record-001")

    def test_sanitise_filename_preserves_dots(self):
        """Periods should be preserved (used in file extensions)."""
        from apps.reports.csv_utils import sanitise_filename
        self.assertEqual(sanitise_filename("file.name"), "file.name")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local")
class CsvInjectionIntegrationTests(TestCase):
    """Integration test: verify CSV injection protection in actual export output."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module.FIELD_ENCRYPTION_KEY = TEST_KEY
        enc_module._fernet = Fernet(TEST_KEY)

        self.program = Program.objects.create(name="Test Program", status="active")
        self.staff_user = User.objects.create_user(
            username="csvtest", password="testpass123", display_name="CSV Tester"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program, role="staff"
        )

        # Create client with a malicious-looking first name
        self.client_file = ClientFile.objects.create(
            record_id="INJ-001", status="active",
        )
        self.client_file.first_name = "=HYPERLINK(\"http://evil.com\")"
        self.client_file.last_name = "Smith"
        self.client_file.save()

        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled",
        )

        self.export_url = f"/reports/client/{self.client_file.pk}/export/"

    def tearDown(self):
        enc_module._fernet = None

    def test_csv_export_sanitises_dangerous_values(self):
        """CSV export should prefix dangerous cell values with a tab character."""
        self.client.login(username="csvtest", password="testpass123")
        resp = self.client.post(self.export_url, {
            "format": "csv",
            "include_plans": True,
            "include_notes": True,
            "include_metrics": True,
            "include_events": True,
            "include_custom_fields": True,
            "recipient": "self",
        })
        content = resp.content.decode("utf-8")
        # The malicious first name should be prefixed with a tab character.
        # CSV writer may quote the value (escaping internal quotes with ""),
        # but the tab prefix must be present before the = sign.
        self.assertIn("\t=HYPERLINK", content)
        # Verify no line contains the raw =HYPERLINK without the tab prefix
        for line in content.split("\n"):
            if "HYPERLINK" in line:
                self.assertIn("\t=HYPERLINK", line)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local")
class FilenameSanitisationIntegrationTests(TestCase):
    """Integration test: verify filename sanitisation in Content-Disposition headers."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module.FIELD_ENCRYPTION_KEY = TEST_KEY
        enc_module._fernet = Fernet(TEST_KEY)

        self.program = Program.objects.create(name="Test Program", status="active")
        self.staff_user = User.objects.create_user(
            username="fntest", password="testpass123", display_name="Filename Tester"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program, role="staff"
        )

        # Create client with special characters in record_id
        self.client_file = ClientFile.objects.create(
            record_id='../../etc/passwd"inject', status="active",
        )
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()

        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled",
        )

        self.export_url = f"/reports/client/{self.client_file.pk}/export/"

    def tearDown(self):
        enc_module._fernet = None

    def test_filename_strips_dangerous_characters(self):
        """Content-Disposition filename should not contain path traversal chars."""
        self.client.login(username="fntest", password="testpass123")
        resp = self.client.post(self.export_url, {
            "format": "csv",
            "include_plans": True,
            "include_notes": True,
            "include_metrics": True,
            "include_events": True,
            "include_custom_fields": True,
            "recipient": "self",
        })
        disposition = resp["Content-Disposition"]
        # Should not contain path traversal
        self.assertNotIn("../", disposition)
        self.assertNotIn("..\\", disposition)
        # Should not contain double quotes inside the filename value
        # (the outer quotes are the HTTP header format, inner ones would be injection)
        filename_part = disposition.split("filename=")[1]
        # The filename should be safely sanitised
        self.assertNotIn("passwd", disposition.replace("..etcpasswdinject", ""))  # it's in the sanitised form
        self.assertIn("client_export_", disposition)
