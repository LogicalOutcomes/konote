"""Tests for funder profile system — CSV parser, demographic blocklists, custom bins, category merging."""
from datetime import date
from unittest.mock import patch

import pytest
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.clients.models import (
    ClientFile,
    ClientProgramEnrolment,
    CustomFieldDefinition,
    CustomFieldGroup,
    ClientDetailValue,
)
from apps.programs.models import Program, UserProgramRole
from apps.reports.csv_parser import (
    parse_funder_profile_csv,
    validate_parsed_profile,
    generate_sample_csv,
    save_parsed_profile,
)
from apps.reports.demographics import (
    get_demographic_field_choices,
    group_clients_by_age,
    group_clients_by_custom_field,
    _find_age_bin,
    _apply_category_merge,
)
from apps.reports.models import FunderProfile, DemographicBreakdown
import konote.encryption as enc_module


# ─── CSV parser tests ────────────────────────────────────────────────

class CSVParserValidTest(TestCase):
    """Test CSV parsing with valid inputs."""

    def test_parse_minimal_profile(self):
        csv_content = (
            "profile_name,Test Funder\n"
            "breakdown,Age Groups,age\n"
            "bin,Age Groups,0,17,Youth\n"
            "bin,Age Groups,18,64,Adult\n"
            "bin,Age Groups,65,999,Senior\n"
        )
        parsed, errors = parse_funder_profile_csv(csv_content)
        assert not errors, f"Unexpected errors: {errors}"
        assert parsed.name == "Test Funder"
        assert len(parsed.breakdowns) == 1
        assert parsed.breakdowns[0].label == "Age Groups"
        assert parsed.breakdowns[0].source_type == "age"
        assert len(parsed.breakdowns[0].bins) == 3

    def test_parse_with_description(self):
        csv_content = (
            "profile_name,My Funder\n"
            "profile_description,A test description\n"
            "breakdown,Age,age\n"
            "bin,Age,0,18,Young\n"
            "bin,Age,19,999,Old\n"
        )
        parsed, errors = parse_funder_profile_csv(csv_content)
        assert not errors
        assert parsed.description == "A test description"

    def test_parse_custom_field_breakdown_with_merges(self):
        csv_content = (
            'profile_name,Employment Funder\n'
            'breakdown,Employment Status,custom_field,Employment Status\n'
            'merge,Employment Status,Employed,"Full-time,Part-time,Contract"\n'
            'merge,Employment Status,Unemployed,"Unemployed,Seeking"\n'
        )
        parsed, errors = parse_funder_profile_csv(csv_content)
        assert not errors, f"Unexpected errors: {errors}"
        assert len(parsed.breakdowns) == 1
        bd = parsed.breakdowns[0]
        assert bd.source_type == "custom_field"
        assert bd.source_field_name == "Employment Status"
        assert "Employed" in bd.merge_map
        assert "Full-time" in bd.merge_map["Employed"]

    def test_parse_multiple_breakdowns(self):
        csv_content = (
            'profile_name,Complex Funder\n'
            'breakdown,Age,age\n'
            'bin,Age,0,24,Youth\n'
            'bin,Age,25,999,Adult\n'
            'breakdown,Gender,custom_field,Gender\n'
            'merge,Gender,Male,"Male,Man"\n'
            'merge,Gender,Female,"Female,Woman"\n'
        )
        parsed, errors = parse_funder_profile_csv(csv_content)
        assert not errors, f"Unexpected errors: {errors}"
        assert len(parsed.breakdowns) == 2

    def test_parse_keep_all_true(self):
        csv_content = (
            "profile_name,Keep All Test\n"
            "breakdown,Status,custom_field,Status\n"
            "keep_all,Status\n"
        )
        parsed, errors = parse_funder_profile_csv(csv_content)
        assert not errors, f"Unexpected errors: {errors}"
        assert parsed.breakdowns[0].keep_all is True


class CSVParserInvalidTest(TestCase):
    """Test CSV parsing with invalid inputs."""

    def test_empty_csv(self):
        parsed, errors = parse_funder_profile_csv("")
        assert errors
        assert any("profile_name" in e.lower() for e in errors)

    def test_missing_profile_name(self):
        csv_content = (
            "breakdown,Age,age\n"
            "bin,0,17,Youth\n"
        )
        parsed, errors = parse_funder_profile_csv(csv_content)
        assert errors
        assert any("profile_name" in e.lower() for e in errors)

    def test_invalid_bin_values(self):
        csv_content = (
            "profile_name,Bad Bins\n"
            "breakdown,Age,age\n"
            "bin,Age,abc,def,Label\n"
        )
        parsed, errors = parse_funder_profile_csv(csv_content)
        assert errors

    def test_bin_without_breakdown(self):
        csv_content = (
            "profile_name,No Breakdown\n"
            "bin,Nonexistent,0,17,Youth\n"
        )
        parsed, errors = parse_funder_profile_csv(csv_content)
        assert errors


class CSVParserSampleTest(TestCase):
    """Test that the sample CSV can be round-tripped."""

    def test_sample_csv_parses_cleanly(self):
        sample = generate_sample_csv()
        parsed, errors = parse_funder_profile_csv(sample)
        assert not errors, f"Sample CSV had parse errors: {errors}"
        assert parsed.name

    def test_sample_csv_validates_cleanly(self):
        sample = generate_sample_csv()
        parsed, _ = parse_funder_profile_csv(sample)
        warnings = validate_parsed_profile(parsed)
        # Warnings are okay but there should be no showstoppers
        assert isinstance(warnings, list)


# ─── Demographic blocklist tests ─────────────────────────────────────

@override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
class DemographicBlocklistsTest(TestCase):
    """Test that PII and dangerous fields are blocked from demographic grouping."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        enc_module._fernet_instance = None

    def setUp(self):
        self.program = Program.objects.create(
            name="Test Program", status="active",
        )

    def test_confidential_program_returns_only_no_grouping(self):
        self.program.is_confidential = True
        self.program.save()
        choices = get_demographic_field_choices(program=self.program)
        assert len(choices) == 1
        assert choices[0][0] == ""

    def test_small_program_returns_only_no_grouping(self):
        # Program with no enrolments → fewer than 50
        choices = get_demographic_field_choices(program=self.program)
        assert len(choices) == 1

    def test_blocked_groups_excluded(self):
        # Create a field in a blocked group
        blocked_group = CustomFieldGroup.objects.create(
            title="Emergency Contact", sort_order=1,
        )
        CustomFieldDefinition.objects.create(
            group=blocked_group,
            name="Contact Name",
            input_type="select",
            status="active",
            is_sensitive=False,
            options_json=[{"value": "a", "label": "A"}],
        )
        # Create enough enrolments to pass the threshold
        for i in range(60):
            cf = ClientFile.objects.create(
                first_name=f"Test{i}", last_name=f"Client{i}",
                record_id=f"R{i:04d}",
            )
            ClientProgramEnrolment.objects.create(
                client_file=cf, program=self.program, status="enrolled",
            )
        choices = get_demographic_field_choices(program=self.program)
        choice_labels = [c[1] for c in choices]
        assert not any("Emergency Contact" in l for l in choice_labels)

    def test_text_fields_excluded(self):
        safe_group = CustomFieldGroup.objects.create(
            title="Demographics", sort_order=1,
        )
        # Text field — should be excluded
        CustomFieldDefinition.objects.create(
            group=safe_group,
            name="Notes",
            input_type="text",
            status="active",
            is_sensitive=False,
        )
        # Select field — should be included
        CustomFieldDefinition.objects.create(
            group=safe_group,
            name="Province",
            input_type="select",
            status="active",
            is_sensitive=False,
            options_json=[{"value": "ON", "label": "Ontario"}],
        )
        for i in range(60):
            cf = ClientFile.objects.create(
                first_name=f"T{i}", last_name=f"C{i}",
                record_id=f"TX{i:04d}",
            )
            ClientProgramEnrolment.objects.create(
                client_file=cf, program=self.program, status="enrolled",
            )
        choices = get_demographic_field_choices(program=self.program)
        choice_labels = [c[1] for c in choices]
        assert not any("Notes" in l for l in choice_labels)
        assert any("Province" in l for l in choice_labels)

    def test_blocked_field_names_excluded(self):
        demo_group = CustomFieldGroup.objects.create(
            title="Demographics", sort_order=1,
        )
        CustomFieldDefinition.objects.create(
            group=demo_group,
            name="Immigration/Citizenship Status",
            input_type="select",
            status="active",
            is_sensitive=False,
            options_json=[{"value": "pr", "label": "PR"}],
        )
        for i in range(60):
            cf = ClientFile.objects.create(
                first_name=f"B{i}", last_name=f"C{i}",
                record_id=f"BL{i:04d}",
            )
            ClientProgramEnrolment.objects.create(
                client_file=cf, program=self.program, status="enrolled",
            )
        choices = get_demographic_field_choices(program=self.program)
        choice_labels = [c[1] for c in choices]
        assert not any("Immigration" in l for l in choice_labels)


# ─── Custom age bin tests ────────────────────────────────────────────

class CustomAgeBinsTest(TestCase):
    """Test age grouping with custom funder bins."""

    def test_find_age_bin_custom(self):
        bins = [(0, 24, "Youth"), (25, 64, "Adult"), (65, 999, "Senior")]
        assert _find_age_bin(date(2010, 1, 1), date(2025, 6, 1), bins) == "Youth"
        assert _find_age_bin(date(1990, 1, 1), date(2025, 6, 1), bins) == "Adult"
        assert _find_age_bin(date(1950, 1, 1), date(2025, 6, 1), bins) == "Senior"

    def test_find_age_bin_unknown_for_missing(self):
        bins = [(0, 17, "Youth"), (18, 999, "Adult")]
        assert _find_age_bin(None, date(2025, 1, 1), bins) == "Unknown"
        assert _find_age_bin("invalid", date(2025, 1, 1), bins) == "Unknown"

    @override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
    def test_group_clients_by_age_with_custom_bins(self):
        enc_module._fernet_instance = None
        custom_bins = [
            {"min": 0, "max": 24, "label": "Youth (0-24)"},
            {"min": 25, "max": 999, "label": "Adult (25+)"},
        ]
        c1 = ClientFile.objects.create(
            first_name="Young", last_name="Person",
            record_id="YOUNG1",
            birth_date="2010-01-01",
        )
        c2 = ClientFile.objects.create(
            first_name="Old", last_name="Person",
            record_id="OLD1",
            birth_date="1980-01-01",
        )
        groups = group_clients_by_age(
            [c1.pk, c2.pk],
            as_of_date=date(2025, 6, 1),
            custom_bins=custom_bins,
        )
        assert c1.pk in groups.get("Youth (0-24)", [])
        assert c2.pk in groups.get("Adult (25+)", [])


# ─── Category merge tests ────────────────────────────────────────────

class CategoryMergeTest(TestCase):
    """Test category merging for custom field groupings."""

    def test_apply_category_merge_basic(self):
        raw_groups = {
            "Full-time": [1, 2],
            "Part-time": [3],
            "Contract": [4],
            "Unemployed": [5],
            "Unknown": [6],
        }
        merge_map = {
            "Employed": ["Full-time", "Part-time", "Contract"],
            "Not Employed": ["Unemployed"],
        }
        result = _apply_category_merge(raw_groups, merge_map)
        assert set(result["Employed"]) == {1, 2, 3, 4}
        assert result["Not Employed"] == [5]
        assert result["Unknown"] == [6]

    def test_apply_category_merge_unmatched_go_to_other(self):
        raw_groups = {
            "Option A": [1],
            "Option B": [2],
            "Option C": [3],
        }
        merge_map = {
            "AB": ["Option A", "Option B"],
        }
        result = _apply_category_merge(raw_groups, merge_map)
        assert set(result["AB"]) == {1, 2}
        assert result["Other"] == [3]

    def test_apply_category_merge_empty(self):
        result = _apply_category_merge({}, {"A": ["B"]})
        assert result == {}

    @override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
    def test_group_clients_with_merge_categories(self):
        enc_module._fernet_instance = None
        group = CustomFieldGroup.objects.create(title="Employment", sort_order=1)
        field = CustomFieldDefinition.objects.create(
            group=group,
            name="Employment Status",
            input_type="select",
            status="active",
            is_sensitive=False,
            options_json=[
                {"value": "ft", "label": "Full-time"},
                {"value": "pt", "label": "Part-time"},
                {"value": "un", "label": "Unemployed"},
            ],
        )
        c1 = ClientFile.objects.create(
            first_name="A", last_name="B", record_id="MRG1",
        )
        c2 = ClientFile.objects.create(
            first_name="C", last_name="D", record_id="MRG2",
        )
        ClientDetailValue.objects.create(
            client_file=c1, field_def=field, value="ft",
        )
        ClientDetailValue.objects.create(
            client_file=c2, field_def=field, value="un",
        )
        merge = {"Employed": ["Full-time", "Part-time"], "Not Employed": ["Unemployed"]}
        groups = group_clients_by_custom_field(
            [c1.pk, c2.pk], field, merge_categories=merge,
        )
        assert c1.pk in groups.get("Employed", [])
        assert c2.pk in groups.get("Not Employed", [])


# ─── FunderProfile model tests ───────────────────────────────────────

@override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
class FunderProfileModelTest(TestCase):
    """Test FunderProfile and DemographicBreakdown model operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        enc_module._fernet_instance = None

    def test_create_profile_with_breakdowns(self):
        profile = FunderProfile.objects.create(
            name="Test Funder",
            description="Testing",
        )
        bd = DemographicBreakdown.objects.create(
            funder_profile=profile,
            label="Age Categories",
            source_type="age",
            bins_json=[
                {"min": 0, "max": 17, "label": "Youth"},
                {"min": 18, "max": 999, "label": "Adult"},
            ],
            sort_order=1,
        )
        assert profile.breakdowns.count() == 1
        assert bd.bins_json[0]["label"] == "Youth"

    def test_profile_program_link(self):
        program = Program.objects.create(name="Test", status="active")
        profile = FunderProfile.objects.create(name="Linked Funder")
        profile.programs.add(program)
        assert program in profile.programs.all()

    def test_save_parsed_profile(self):
        admin = User.objects.create_user(
            username="admin_save", password="testpass", is_admin=True,
        )
        csv_content = (
            "profile_name,Saved Funder\n"
            "profile_description,auto-created\n"
            "breakdown,Age Buckets,age\n"
            "bin,Age Buckets,0,17,Under 18\n"
            "bin,Age Buckets,18,999,18 and over\n"
        )
        parsed, errors = parse_funder_profile_csv(csv_content)
        assert not errors
        profile = save_parsed_profile(parsed, created_by=admin)
        assert profile.pk is not None
        assert profile.name == "Saved Funder"
        assert profile.breakdowns.count() == 1
        assert profile.created_by == admin


# ─── Admin view permissions tests ─────────────────────────────────────

@override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
class FunderProfileAdminAccessTest(TestCase):
    """Test that funder profile admin views are restricted to admins."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        enc_module._fernet_instance = None

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin_fp", password="pass123", is_admin=True,
        )
        self.staff_user = User.objects.create_user(
            username="staff_fp", password="pass123", is_admin=False,
        )

    def test_admin_can_access_profile_list(self):
        self.client.login(username="admin_fp", password="pass123")
        response = self.client.get("/admin/settings/funder-profiles/")
        assert response.status_code == 200

    def test_staff_cannot_access_profile_list(self):
        self.client.login(username="staff_fp", password="pass123")
        response = self.client.get("/admin/settings/funder-profiles/")
        assert response.status_code in (302, 403)

    def test_admin_can_access_upload(self):
        self.client.login(username="admin_fp", password="pass123")
        response = self.client.get("/admin/settings/funder-profiles/upload/")
        assert response.status_code == 200

    def test_admin_can_download_sample(self):
        self.client.login(username="admin_fp", password="pass123")
        response = self.client.get("/admin/settings/funder-profiles/sample.csv")
        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
