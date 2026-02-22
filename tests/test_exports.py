"""Tests for report export CSV generation and insights data.

Covers BUG-EXP1: format_number() and generate_funder_report_csv_rows()
must handle string values produced by small-cell suppression for
confidential programs (e.g. "< 10", "suppressed").

Covers BUG-AI2: get_structured_insights() must return JSON-serializable
dicts (no gettext_lazy proxies as keys).

Covers CHART-TIME1: client_analysis timeframe filter.
"""
import json
from datetime import date, timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import Client as HttpClient, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.reports.funder_report import (
    format_number,
    generate_funder_report_csv_rows,
    generate_funder_report_data,
)


class FormatNumberTests(SimpleTestCase):
    """format_number() must handle int, float, None, and suppressed strings."""

    def test_integer(self):
        self.assertEqual(format_number(42), "42")

    def test_integer_with_thousands(self):
        self.assertEqual(format_number(1234), "1,234")

    def test_float(self):
        self.assertEqual(format_number(3.14159), "3.1")

    def test_none(self):
        self.assertEqual(format_number(None), "N/A")

    def test_zero(self):
        self.assertEqual(format_number(0), "0")

    def test_suppressed_string(self):
        """Suppressed values like '< 10' should pass through unchanged."""
        self.assertEqual(format_number("< 10"), "< 10")

    def test_suppressed_total_string(self):
        """The word 'suppressed' should pass through unchanged."""
        self.assertEqual(format_number("suppressed"), "suppressed")


def _minimal_report_data(**overrides):
    """Build a minimal report_data dict for generate_funder_report_csv_rows."""
    data = {
        "generated_at": timezone.now(),
        "reporting_period": "2025-2026",
        "date_from": date(2025, 4, 1),
        "date_to": date(2026, 3, 31),
        "organisation_name": "Test Org",
        "program_name": "Test Program",
        "program_description": "",
        "total_individuals_served": 50,
        "new_clients_this_period": 10,
        "total_contacts": 100,
        "contact_breakdown": {"successful_contacts": 80, "contact_attempts": 20},
        "age_demographics": {"18-24": 15, "25-34": 20, "35-44": 15},
        "age_demographics_total": 50,
        "custom_demographic_sections": [],
        "report_template_name": None,
        "primary_outcome": None,
        "secondary_outcomes": [],
        "achievement_summary": {
            "total_clients": 0,
            "clients_met_any_target": 0,
            "overall_rate": 0,
            "metrics": [],
        },
        "active_client_count": 50,
        "enrolled_client_count": 55,
    }
    data.update(overrides)
    return data


class FunderReportCSVSuppressedAgeTests(SimpleTestCase):
    """CSV generation must not crash when age demographics contain suppressed values."""

    def test_suppressed_age_counts_produce_star_percentage(self):
        """When an age group count is suppressed (string), percentage should be '*'."""
        report_data = _minimal_report_data(
            age_demographics={"18-24": "< 10", "25-34": 20, "35-44": "< 10"},
            age_demographics_total=50,
        )
        rows = generate_funder_report_csv_rows(report_data)

        # Find the age demographics rows (match translated section header)
        age_rows = []
        in_age_section = False
        for row in rows:
            if len(row) == 1 and "AGE" in str(row[0]).upper():
                in_age_section = True
                continue
            if in_age_section and len(row) == 3 and row[0] not in ("Age Group", _("Age Group")):
                age_rows.append(row)
                if row[0] in ("Total", _("Total")):
                    break

        # Suppressed counts should have '*' percentage
        self.assertEqual(age_rows[0][0], "18-24")
        self.assertEqual(age_rows[0][1], "< 10")  # format_number passes through
        self.assertEqual(age_rows[0][2], "*")

        # Non-suppressed count should have normal percentage
        self.assertEqual(age_rows[1][0], "25-34")
        self.assertEqual(age_rows[1][1], "20")
        self.assertIn("%", age_rows[1][2])

    def test_no_crash_on_all_suppressed_age_counts(self):
        """Should not crash even if all age counts are suppressed."""
        report_data = _minimal_report_data(
            age_demographics={"18-24": "< 10", "25-34": "< 10"},
            age_demographics_total=50,
        )
        # Should not raise
        rows = generate_funder_report_csv_rows(report_data)
        self.assertIsInstance(rows, list)


class FunderReportCSVSuppressedCustomDemoTests(SimpleTestCase):
    """CSV generation must not crash when custom demographics contain suppressed values."""

    def test_suppressed_custom_demo_with_suppressed_total(self):
        """When section total is 'suppressed', all percentages should be '*'."""
        report_data = _minimal_report_data(
            custom_demographic_sections=[{
                "label": "Gender Identity",
                "data": {"Female": "< 10", "Male": 25, "Non-binary": "< 10"},
                "total": "suppressed",
            }],
        )
        rows = generate_funder_report_csv_rows(report_data)

        # Find the custom section rows (match uppercased label)
        custom_rows = []
        in_section = False
        for row in rows:
            if len(row) == 1 and "GENDER" in str(row[0]).upper():
                in_section = True
                continue
            if in_section and len(row) == 3 and row[0] not in ("Category", _("Category")):
                custom_rows.append(row)
                if row[0] in ("Total", _("Total")):
                    break

        # All percentages should be '*' when total is suppressed
        for cr in custom_rows:
            if cr[0] not in ("Total", _("Total")):
                self.assertEqual(cr[2], "*", f"Expected '*' for {cr[0]}, got {cr[2]}")

        # Total row should show suppressed value with '*' percentage
        total_row = custom_rows[-1]
        self.assertIn(total_row[0], ("Total", _("Total")))
        self.assertEqual(total_row[1], "suppressed")
        self.assertEqual(total_row[2], "*")

    def test_mixed_suppressed_custom_demo(self):
        """Some counts suppressed, total is numeric — percentages should be '*' for strings."""
        report_data = _minimal_report_data(
            custom_demographic_sections=[{
                "label": "Ethnicity",
                "data": {"Group A": "< 10", "Group B": 30},
                "total": 40,
            }],
        )
        rows = generate_funder_report_csv_rows(report_data)

        # Find the section rows (match uppercased label)
        section_rows = []
        in_section = False
        for row in rows:
            if len(row) == 1 and "ETHNICITY" in str(row[0]).upper():
                in_section = True
                continue
            if in_section and len(row) == 3 and row[0] not in ("Category", _("Category")):
                section_rows.append(row)
                if row[0] in ("Total", _("Total")):
                    break

        # Suppressed count should have '*'
        self.assertEqual(section_rows[0][1], "< 10")
        self.assertEqual(section_rows[0][2], "*")

        # Non-suppressed count should have normal percentage
        self.assertEqual(section_rows[1][1], "30")
        self.assertIn("%", section_rows[1][2])


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StructuredInsightsJSONTest(TestCase):
    """Regression for BUG-AI2: get_structured_insights() must be JSON-serializable."""

    databases = {"default", "audit"}

    def setUp(self):
        import konote.encryption as enc_module
        enc_module._fernet = None

        from apps.auth_app.models import User
        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.notes.models import ProgressNote
        from apps.programs.models import Program, UserProgramRole

        self.user = User.objects.create_user(
            username="reporter", password="pass", display_name="Reporter"
        )
        self.program = Program.objects.create(name="Housing")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="staff", status="active"
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled"
        )
        # Create a note with an engagement observation to trigger label lookup
        ProgressNote.objects.create(
            client_file=self.client_file,
            author=self.user,
            engagement_observation="engaged",
        )

    def tearDown(self):
        import konote.encryption as enc_module
        enc_module._fernet = None

    def test_insights_dict_is_json_serializable(self):
        """All dict keys must be plain str, not gettext_lazy proxies."""
        from apps.reports.insights import get_structured_insights

        result = get_structured_insights(program=self.program)
        # This will raise TypeError if any keys are lazy proxies
        serialized = json.dumps(result)
        self.assertIsInstance(serialized, str)
        self.assertGreater(result["note_count"], 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AnalysisChartTimeframeTest(TestCase):
    """CHART-TIME1: Analysis chart timeframe filter tests."""

    databases = {"default", "audit"}

    def setUp(self):
        import konote.encryption as enc_module
        enc_module._fernet = None

        from apps.auth_app.models import User
        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
        from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
        from apps.programs.models import Program, UserProgramRole

        self.http = HttpClient()
        self.user = User.objects.create_user(
            username="analyst", password="pass", display_name="Analyst"
        )
        self.program = Program.objects.create(name="Coaching")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="staff", status="active"
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Chart"
        self.client_file.last_name = "Test"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled"
        )

        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.program,
        )
        self.target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Confidence",
        )
        self.metric = MetricDefinition.objects.create(
            name="Score", min_value=0, max_value=10, unit="pts",
            definition="Test metric", category="general",
        )
        PlanTargetMetric.objects.create(plan_target=self.target, metric_def=self.metric)

        # Create an old note (90 days ago) and a recent note (5 days ago).
        # Use backdate since created_at is auto_now_add and can't be overridden.
        old_note = ProgressNote.objects.create(
            client_file=self.client_file, author=self.user,
            backdate=timezone.now() - timedelta(days=90),
        )
        old_pnt = ProgressNoteTarget.objects.create(
            progress_note=old_note, plan_target=self.target,
        )
        MetricValue.objects.create(
            metric_def=self.metric, progress_note_target=old_pnt, value="3",
        )

        recent_note = ProgressNote.objects.create(
            client_file=self.client_file, author=self.user,
            backdate=timezone.now() - timedelta(days=5),
        )
        recent_pnt = ProgressNoteTarget.objects.create(
            progress_note=recent_note, plan_target=self.target,
        )
        MetricValue.objects.create(
            metric_def=self.metric, progress_note_target=recent_pnt, value="7",
        )

    def tearDown(self):
        import konote.encryption as enc_module
        enc_module._fernet = None

    def test_analysis_no_filter_returns_all_data(self):
        """Default (no filter) returns both old and recent data points."""
        self.http.login(username="analyst", password="pass")
        resp = self.http.get(
            f"/reports/participant/{self.client_file.pk}/analysis/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "chart-data")
        # Both data points should be in the chart data
        content = resp.content.decode()
        self.assertIn('"value": 3.0', content)
        self.assertIn('"value": 7.0', content)

    def test_analysis_30d_filter_excludes_old_data(self):
        """30-day filter only shows recent data, not old."""
        self.http.login(username="analyst", password="pass")
        resp = self.http.get(
            f"/reports/participant/{self.client_file.pk}/analysis/?timeframe=30d"
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('"value": 7.0', content)
        self.assertNotIn('"value": 3.0', content)

    def test_analysis_all_time_returns_everything(self):
        """Explicit 'all' timeframe returns all data."""
        self.http.login(username="analyst", password="pass")
        resp = self.http.get(
            f"/reports/participant/{self.client_file.pk}/analysis/?timeframe=all"
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('"value": 3.0', content)
        self.assertIn('"value": 7.0', content)

    def test_analysis_manual_date_range(self):
        """Manual date_from/date_to filters data by date range."""
        self.http.login(username="analyst", password="pass")
        # Only include the last 10 days
        date_from = (timezone.now() - timedelta(days=10)).date().isoformat()
        resp = self.http.get(
            f"/reports/participant/{self.client_file.pk}/analysis/?date_from={date_from}"
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('"value": 7.0', content)
        self.assertNotIn('"value": 3.0', content)

    def test_analysis_3m_filter_excludes_old_data(self):
        """3-month filter should exclude data older than 90 days."""
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget

        # Create a metric value backdated > 90 days ago
        old_note = ProgressNote.objects.create(
            client_file=self.client_file, author=self.user,
            backdate=timezone.now() - timedelta(days=120),
        )
        old_pnt = ProgressNoteTarget.objects.create(
            progress_note=old_note, plan_target=self.target,
        )
        MetricValue.objects.create(
            metric_def=self.metric, progress_note_target=old_pnt, value="1",
        )

        self.http.login(username="analyst", password="pass")
        resp = self.http.get(
            f"/reports/participant/{self.client_file.pk}/analysis/?timeframe=3m"
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # The 120-day-old value=1.0 should be excluded
        self.assertNotIn('"value": 1.0', content)
        # The 5-day-old value=7.0 should still be present
        self.assertIn('"value": 7.0', content)

    def test_analysis_6m_filter_excludes_old_data(self):
        """6-month filter should exclude data older than 180 days."""
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget

        # Create a metric value backdated > 180 days ago
        old_note = ProgressNote.objects.create(
            client_file=self.client_file, author=self.user,
            backdate=timezone.now() - timedelta(days=200),
        )
        old_pnt = ProgressNoteTarget.objects.create(
            progress_note=old_note, plan_target=self.target,
        )
        MetricValue.objects.create(
            metric_def=self.metric, progress_note_target=old_pnt, value="2",
        )

        self.http.login(username="analyst", password="pass")
        resp = self.http.get(
            f"/reports/participant/{self.client_file.pk}/analysis/?timeframe=6m"
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # The 200-day-old value=2.0 should be excluded
        self.assertNotIn('"value": 2.0', content)
        # The 5-day-old value=7.0 should still be present
        self.assertIn('"value": 7.0', content)

    def test_analysis_invalid_timeframe_returns_all(self):
        """Invalid timeframe value should return all data (no crash)."""
        self.http.login(username="analyst", password="pass")
        resp = self.http.get(
            f"/reports/participant/{self.client_file.pk}/analysis/?timeframe=invalid"
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # Both data points should still be present
        self.assertIn('"value": 3.0', content)
        self.assertIn('"value": 7.0', content)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FunderReportTemplateMetricFilterTest(TestCase):
    """Template-defined metrics should filter funder report achievement data."""

    databases = {"default", "audit"}

    def setUp(self):
        import konote.encryption as enc_module
        enc_module._fernet = None

        from apps.auth_app.models import User
        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
        from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
        from apps.programs.models import Program, UserProgramRole
        from apps.reports.models import Partner, ReportMetric, ReportTemplate

        self.user = User.objects.create_user(
            username="exec", password="pass", display_name="Exec"
        )
        self.program = Program.objects.create(name="Coaching")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="executive", status="active"
        )

        self.client_file = ClientFile()
        self.client_file.first_name = "Template"
        self.client_file.last_name = "Test"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled"
        )

        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Goal 1",
        )

        # Two metrics: "Score A" and "Score B"
        self.metric_a = MetricDefinition.objects.create(
            name="Score A", min_value=0, max_value=10, unit="pts",
            definition="Metric A", category="general",
        )
        self.metric_b = MetricDefinition.objects.create(
            name="Score B", min_value=0, max_value=10, unit="pts",
            definition="Metric B", category="general",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric_a)
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric_b)

        # Create a note with values for both metrics
        note = ProgressNote.objects.create(
            client_file=self.client_file, author=self.user,
        )
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note, plan_target=target,
        )
        MetricValue.objects.create(
            metric_def=self.metric_a, progress_note_target=pnt, value="8",
        )
        MetricValue.objects.create(
            metric_def=self.metric_b, progress_note_target=pnt, value="6",
        )

        # Create a template with only metric A
        partner = Partner.objects.create(name="Test Funder", partner_type="funder")
        self.template = ReportTemplate.objects.create(
            partner=partner, name="Quarterly Report",
        )
        ReportMetric.objects.create(
            report_template=self.template,
            metric_definition=self.metric_a,
            aggregation="threshold_percentage",
            display_label="Custom Score Label",
            sort_order=1,
        )

        # Also create an empty template (no ReportMetric entries)
        self.empty_template = ReportTemplate.objects.create(
            partner=partner, name="Empty Template",
        )

    def tearDown(self):
        import konote.encryption as enc_module
        enc_module._fernet = None

    def test_template_with_metrics_filters_to_those_metrics(self):
        """When template has ReportMetric entries, only those metrics appear."""
        data = generate_funder_report_data(
            self.program,
            date_from=date(2025, 4, 1),
            date_to=date(2026, 3, 31),
            user=self.user,
            report_template=self.template,
        )
        metric_ids = [
            m["metric_id"] for m in data["achievement_summary"]["by_metric"]
        ]
        self.assertIn(self.metric_a.pk, metric_ids)
        self.assertNotIn(self.metric_b.pk, metric_ids)
        self.assertEqual(len(metric_ids), 1)

    def test_template_without_metrics_includes_all(self):
        """When template has zero ReportMetric entries, all metrics appear (fallback)."""
        data = generate_funder_report_data(
            self.program,
            date_from=date(2025, 4, 1),
            date_to=date(2026, 3, 31),
            user=self.user,
            report_template=self.empty_template,
        )
        metric_names = [
            m["metric_name"] for m in data["achievement_summary"]["by_metric"]
        ]
        self.assertIn("Score A", metric_names)
        self.assertIn("Score B", metric_names)

    def test_no_template_includes_all(self):
        """Without a template, all metrics with data appear."""
        data = generate_funder_report_data(
            self.program,
            date_from=date(2025, 4, 1),
            date_to=date(2026, 3, 31),
            user=self.user,
            report_template=None,
        )
        metric_names = [
            m["metric_name"] for m in data["achievement_summary"]["by_metric"]
        ]
        self.assertIn("Score A", metric_names)
        self.assertIn("Score B", metric_names)

    def test_template_display_label_overrides_metric_name(self):
        """ReportMetric.display_label should override metric_name in results."""
        data = generate_funder_report_data(
            self.program,
            date_from=date(2025, 4, 1),
            date_to=date(2026, 3, 31),
            user=self.user,
            report_template=self.template,
        )
        metric_names = [
            m["metric_name"] for m in data["achievement_summary"]["by_metric"]
        ]
        self.assertIn("Custom Score Label", metric_names)
        self.assertNotIn("Score A", metric_names)


# ---------------------------------------------------------------------------
# Aggregation engine tests (Fix #7)
# ---------------------------------------------------------------------------

class ComputeMetricAggregationTests(SimpleTestCase):
    """Tests for compute_metric_aggregation() — all 7 aggregation types."""

    def _make_values(self, data):
        """Helper: convert {client_id: [(date_str, value), ...]} to proper format."""
        from datetime import datetime
        result = {}
        for cid, pairs in data.items():
            result[cid] = [
                (datetime.fromisoformat(d), float(v)) for d, v in pairs
            ]
        return result

    def test_count(self):
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({
            1: [("2025-06-01", 5)],
            2: [("2025-06-01", 3)],
            3: [("2025-06-01", 7)],
        })
        result = compute_metric_aggregation(values, "count")
        self.assertEqual(result["value"], 3)
        self.assertEqual(result["n"], 3)

    def test_average(self):
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({
            1: [("2025-06-01", 4)],
            2: [("2025-06-01", 6)],
        })
        result = compute_metric_aggregation(values, "average")
        self.assertEqual(result["value"], 5.0)
        self.assertEqual(result["n"], 2)

    def test_sum(self):
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({
            1: [("2025-06-01", 10)],
            2: [("2025-06-01", 20)],
            3: [("2025-06-01", 30)],
        })
        result = compute_metric_aggregation(values, "sum")
        self.assertEqual(result["value"], 60.0)
        self.assertEqual(result["n"], 3)

    def test_average_change(self):
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({
            1: [("2025-01-01", 3), ("2025-06-01", 7)],  # change = +4
            2: [("2025-01-01", 5), ("2025-06-01", 8)],  # change = +3
        })
        result = compute_metric_aggregation(values, "average_change")
        self.assertEqual(result["value"], 3.5)  # avg of 4 and 3
        self.assertEqual(result["n"], 2)

    def test_average_change_excludes_single_value_clients(self):
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({
            1: [("2025-01-01", 3), ("2025-06-01", 7)],  # change = +4
            2: [("2025-06-01", 5)],  # only 1 value — excluded
        })
        result = compute_metric_aggregation(values, "average_change")
        self.assertEqual(result["value"], 4.0)
        self.assertEqual(result["n"], 1)  # only client 1 contributes

    def test_threshold_count(self):
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({
            1: [("2025-06-01", 8)],
            2: [("2025-06-01", 3)],
            3: [("2025-06-01", 7)],
        })
        result = compute_metric_aggregation(values, "threshold_count", threshold_value=7)
        self.assertEqual(result["value"], 2)  # clients 1 and 3 meet threshold
        self.assertEqual(result["n"], 3)

    def test_threshold_percentage(self):
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({
            1: [("2025-06-01", 8)],
            2: [("2025-06-01", 3)],
            3: [("2025-06-01", 7)],
            4: [("2025-06-01", 9)],
        })
        result = compute_metric_aggregation(values, "threshold_percentage", threshold_value=7)
        self.assertEqual(result["value"], 75.0)  # 3 of 4
        self.assertEqual(result["n"], 4)

    def test_percentage_alias(self):
        """'percentage' should behave identically to 'threshold_percentage'."""
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({
            1: [("2025-06-01", 10)],
            2: [("2025-06-01", 2)],
        })
        result = compute_metric_aggregation(values, "percentage", threshold_value=5)
        self.assertEqual(result["value"], 50.0)  # 1 of 2
        self.assertEqual(result["n"], 2)

    def test_empty_values_returns_zero(self):
        from apps.reports.aggregation import compute_metric_aggregation
        result = compute_metric_aggregation({}, "count")
        self.assertEqual(result["value"], 0)
        self.assertEqual(result["n"], 0)

    def test_unknown_aggregation_raises_valueerror(self):
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({1: [("2025-06-01", 5)]})
        with self.assertRaises(ValueError) as ctx:
            compute_metric_aggregation(values, "nonexistent_type")
        self.assertIn("nonexistent_type", str(ctx.exception))

    def test_uses_latest_value_per_client(self):
        """Average should use the latest (by date) value per client."""
        from apps.reports.aggregation import compute_metric_aggregation
        values = self._make_values({
            1: [("2025-01-01", 2), ("2025-06-01", 8)],  # latest = 8
        })
        result = compute_metric_aggregation(values, "average")
        self.assertEqual(result["value"], 8.0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConsortiumMetricLockingTest(TestCase):
    """Tests for consortium-required metric locking in MetricExportForm."""

    databases = {"default", "audit"}

    def setUp(self):
        import konote.encryption as enc_module
        enc_module._fernet = None

        from apps.auth_app.models import User
        from apps.plans.models import MetricDefinition
        from apps.programs.models import Program, UserProgramRole
        from apps.reports.models import Partner, ReportMetric, ReportTemplate

        self.user = User.objects.create_user(
            username="pm_user", password="pass", display_name="PM"
        )
        self.program = Program.objects.create(name="Coaching")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="staff", status="active"
        )

        self.metric_a = MetricDefinition.objects.create(
            name="Metric A", min_value=0, max_value=10, unit="pts",
            definition="Test", category="general",
        )
        self.metric_b = MetricDefinition.objects.create(
            name="Metric B", min_value=0, max_value=10, unit="pts",
            definition="Test", category="general",
        )

        partner = Partner.objects.create(name="Consortium Funder", partner_type="funder")
        partner.programs.add(self.program)
        self.template = ReportTemplate.objects.create(
            partner=partner, name="Consortium Report",
        )
        # Metric A is consortium-required; Metric B is not
        ReportMetric.objects.create(
            report_template=self.template,
            metric_definition=self.metric_a,
            aggregation="count",
            is_consortium_required=True,
            sort_order=1,
        )
        ReportMetric.objects.create(
            report_template=self.template,
            metric_definition=self.metric_b,
            aggregation="average",
            is_consortium_required=False,
            sort_order=2,
        )

    def tearDown(self):
        import konote.encryption as enc_module
        enc_module._fernet = None

    def test_consortium_locked_metrics_populated_from_template(self):
        """When template is selected, consortium_locked_metrics includes required metric IDs."""
        from apps.reports.forms import MetricExportForm

        form = MetricExportForm(
            data={"report_template": str(self.template.pk)},
            user=self.user,
        )
        self.assertIn(self.metric_a.pk, form.consortium_locked_metrics)
        self.assertNotIn(self.metric_b.pk, form.consortium_locked_metrics)

    def test_consortium_partner_name_set(self):
        """The consortium partner name should be set when locked metrics exist."""
        from apps.reports.forms import MetricExportForm

        form = MetricExportForm(
            data={"report_template": str(self.template.pk)},
            user=self.user,
        )
        self.assertEqual(form.consortium_partner_name, "Consortium Funder")

    def test_no_template_means_no_locks(self):
        """Without a template selection, no metrics should be locked."""
        from apps.reports.forms import MetricExportForm

        form = MetricExportForm(data={}, user=self.user)
        self.assertEqual(form.consortium_locked_metrics, set())
        self.assertEqual(form.consortium_partner_name, "")
