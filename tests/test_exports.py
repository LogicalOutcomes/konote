"""Tests for report export CSV generation — suppressed value handling.

Covers BUG-EXP1: format_number() and generate_funder_report_csv_rows()
must handle string values produced by small-cell suppression for
confidential programs (e.g. "< 10", "suppressed").
"""
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from apps.reports.funder_report import format_number, generate_funder_report_csv_rows


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

        # Find the age demographics rows
        age_rows = []
        in_age_section = False
        for row in rows:
            if row == ["AGE DEMOGRAPHICS"]:
                in_age_section = True
                continue
            if in_age_section and len(row) == 3 and row[0] != "Age Group":
                age_rows.append(row)
                if row[0] == "Total":
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

        # Find the custom section rows
        custom_rows = []
        in_section = False
        for row in rows:
            if row == ["GENDER IDENTITY"]:
                in_section = True
                continue
            if in_section and len(row) == 3 and row[0] != "Category":
                custom_rows.append(row)
                if row[0] == "Total":
                    break

        # All percentages should be '*' when total is suppressed
        for cr in custom_rows:
            if cr[0] != "Total":
                self.assertEqual(cr[2], "*", f"Expected '*' for {cr[0]}, got {cr[2]}")

        # Total row should show suppressed value with '*' percentage
        total_row = custom_rows[-1]
        self.assertEqual(total_row[0], "Total")
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

        # Find the section rows
        section_rows = []
        in_section = False
        for row in rows:
            if row == ["ETHNICITY"]:
                in_section = True
                continue
            if in_section and len(row) == 3 and row[0] != "Category":
                section_rows.append(row)
                if row[0] == "Total":
                    break

        # Suppressed count should have '*'
        self.assertEqual(section_rows[0][1], "< 10")
        self.assertEqual(section_rows[0][2], "*")

        # Non-suppressed count should have normal percentage
        self.assertEqual(section_rows[1][1], "30")
        self.assertIn("%", section_rows[1][2])
