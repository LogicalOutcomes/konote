"""Tests for CIDS metadata fields, code lists, taxonomy, and reports."""
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.admin_settings.models import (
    CidsCodeList, OrganizationProfile, TaxonomyMapping,
)
from apps.auth_app.models import User
from apps.notes.models import ProgressNote, ProgressNoteTarget, MetricValue
from apps.plans.models import MetricDefinition, PlanTarget, PlanSection, PlanTargetMetric
from apps.plans.achievement import compute_achievement_status, update_achievement_status
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


# ── MetricDefinition CIDS fields ──────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricDefinitionCidsFieldsTest(TestCase):
    def setUp(self):
        enc_module._fernet = None

    def test_cids_fields_default_to_blank(self):
        metric = MetricDefinition.objects.create(
            name="Test Metric",
            definition="Test definition",
        )
        self.assertEqual(metric.cids_indicator_uri, "")
        self.assertEqual(metric.iris_metric_code, "")
        self.assertEqual(metric.sdg_goals, [])
        self.assertEqual(metric.cids_unit_description, "")
        self.assertEqual(metric.cids_defined_by, "")
        self.assertEqual(metric.cids_has_baseline, "")
        self.assertEqual(metric.cids_theme_override, "")

    def test_cids_fields_can_be_set(self):
        metric = MetricDefinition.objects.create(
            name="Housing Stability",
            definition="Measures housing stability",
            cids_indicator_uri="urn:cids:indicator:housing-stability",
            iris_metric_code="PI2061",
            sdg_goals=[1, 11],
            cids_unit_description="score",
            cids_defined_by="https://iris.thegiin.org",
            cids_has_baseline="Average score 3.2 at intake",
            cids_theme_override="housing",
        )
        metric.refresh_from_db()
        self.assertEqual(metric.cids_indicator_uri, "urn:cids:indicator:housing-stability")
        self.assertEqual(metric.iris_metric_code, "PI2061")
        self.assertEqual(metric.sdg_goals, [1, 11])
        self.assertEqual(metric.cids_unit_description, "score")
        self.assertEqual(metric.cids_defined_by, "https://iris.thegiin.org")
        self.assertEqual(metric.cids_has_baseline, "Average score 3.2 at intake")
        self.assertEqual(metric.cids_theme_override, "housing")

    def test_sdg_goals_json_serialisation(self):
        metric = MetricDefinition.objects.create(
            name="SDG Test",
            definition="SDG test",
            sdg_goals=[1, 3, 5, 10, 17],
        )
        metric.refresh_from_db()
        self.assertEqual(metric.sdg_goals, [1, 3, 5, 10, 17])
        self.assertIsInstance(metric.sdg_goals, list)

    def test_category_field_unchanged(self):
        """MetricDefinition.category should still work with its 7 original values."""
        for code, _label in MetricDefinition.CATEGORY_CHOICES:
            metric = MetricDefinition.objects.create(
                name=f"Test {code}",
                definition=f"Test {code}",
                category=code,
            )
            self.assertEqual(metric.category, code)

    def test_cids_has_baseline_is_charfield_not_boolean(self):
        """cids_has_baseline stores human-readable text, not True/False."""
        metric = MetricDefinition.objects.create(
            name="Baseline Test",
            definition="Test",
            cids_has_baseline="Median score 4.5 at programme entry",
        )
        metric.refresh_from_db()
        self.assertEqual(metric.cids_has_baseline, "Median score 4.5 at programme entry")


# ── PlanTarget CIDS fields ────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PlanTargetCidsFieldsTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        from apps.clients.models import ClientFile
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Test Section"
        )

    def test_cids_outcome_uri_defaults_to_blank(self):
        target = PlanTarget.objects.create(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test Target"
        target.save()
        self.assertEqual(target.cids_outcome_uri, "")

    def test_cids_outcome_uri_can_be_set(self):
        target = PlanTarget.objects.create(
            plan_section=self.section,
            client_file=self.client_file,
            cids_outcome_uri="urn:cids:outcome:housing-stable",
        )
        target.name = "Housing Stable"
        target.save()
        target.refresh_from_db()
        self.assertEqual(target.cids_outcome_uri, "urn:cids:outcome:housing-stable")


# ── Program CIDS fields ──────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramCidsFieldsTest(TestCase):
    def setUp(self):
        enc_module._fernet = None

    def test_cids_fields_default_to_blank(self):
        program = Program.objects.create(name="Test Program")
        self.assertEqual(program.cids_sector_code, "")
        self.assertEqual(program.population_served_codes, [])
        self.assertEqual(program.description_fr, "")
        self.assertEqual(program.funder_program_code, "")

    def test_cids_fields_can_be_set(self):
        program = Program.objects.create(
            name="Housing First",
            cids_sector_code="ICNPO-7",
            population_served_codes=["youth", "indigenous"],
            description_fr="Programme de logement d'abord",
            funder_program_code="HF-2026-001",
        )
        program.refresh_from_db()
        self.assertEqual(program.cids_sector_code, "ICNPO-7")
        self.assertEqual(program.population_served_codes, ["youth", "indigenous"])
        self.assertEqual(program.description_fr, "Programme de logement d'abord")
        self.assertEqual(program.funder_program_code, "HF-2026-001")

    def test_population_served_codes_json_serialisation(self):
        program = Program.objects.create(
            name="Test",
            population_served_codes=["youth", "seniors", "newcomers"],
        )
        program.refresh_from_db()
        self.assertEqual(program.population_served_codes, ["youth", "seniors", "newcomers"])
        self.assertIsInstance(program.population_served_codes, list)


# ── OrganizationProfile singleton ─────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class OrganizationProfileTest(TestCase):
    def setUp(self):
        enc_module._fernet = None

    def test_get_solo_creates_if_missing(self):
        self.assertEqual(OrganizationProfile.objects.count(), 0)
        profile = OrganizationProfile.get_solo()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.pk, 1)
        self.assertEqual(OrganizationProfile.objects.count(), 1)

    def test_get_solo_returns_existing(self):
        OrganizationProfile.objects.create(pk=1, legal_name="Test Org")
        profile = OrganizationProfile.get_solo()
        self.assertEqual(profile.legal_name, "Test Org")
        self.assertEqual(OrganizationProfile.objects.count(), 1)

    def test_singleton_enforced_on_save(self):
        """Saving with any pk should always use pk=1."""
        profile = OrganizationProfile(pk=99, legal_name="Wrong PK")
        profile.save()
        self.assertEqual(profile.pk, 1)
        self.assertEqual(OrganizationProfile.objects.count(), 1)

    def test_all_fields_default_to_blank(self):
        profile = OrganizationProfile.get_solo()
        self.assertEqual(profile.legal_name, "")
        self.assertEqual(profile.operating_name, "")
        self.assertEqual(profile.description, "")
        self.assertEqual(profile.description_fr, "")
        self.assertEqual(profile.legal_status, "")
        self.assertEqual(profile.sector_codes, [])
        self.assertEqual(profile.street_address, "")
        self.assertEqual(profile.city, "")
        self.assertEqual(profile.province, "")
        self.assertEqual(profile.postal_code, "")
        self.assertEqual(profile.country, "CA")
        self.assertEqual(profile.website, "")

    def test_fields_can_be_set(self):
        profile = OrganizationProfile.get_solo()
        profile.legal_name = "Example Community Services Inc."
        profile.operating_name = "Example Community Services"
        profile.description = "Helping people in need."
        profile.description_fr = "Aider les personnes dans le besoin."
        profile.legal_status = "Registered charity"
        profile.sector_codes = ["ICNPO-7", "ICNPO-4"]
        profile.street_address = "123 Main St"
        profile.city = "Ottawa"
        profile.province = "ON"
        profile.postal_code = "K1A 0A6"
        profile.country = "CA"
        profile.website = "https://example.ca"
        profile.save()

        profile.refresh_from_db()
        self.assertEqual(profile.legal_name, "Example Community Services Inc.")
        self.assertEqual(profile.operating_name, "Example Community Services")
        self.assertEqual(profile.sector_codes, ["ICNPO-7", "ICNPO-4"])
        self.assertEqual(profile.province, "ON")
        self.assertEqual(profile.website, "https://example.ca")

    def test_delete_is_noop(self):
        profile = OrganizationProfile.get_solo()
        profile.delete()
        self.assertEqual(OrganizationProfile.objects.count(), 1)

    def test_str_uses_operating_name(self):
        profile = OrganizationProfile.get_solo()
        profile.operating_name = "My Org"
        profile.save()
        self.assertEqual(str(profile), "My Org")

    def test_str_falls_back_to_legal_name(self):
        profile = OrganizationProfile.get_solo()
        profile.legal_name = "My Legal Org"
        profile.save()
        self.assertEqual(str(profile), "My Legal Org")


# ── OrganizationProfile admin view ────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class OrganizationProfileViewTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False
        )

    def test_admin_can_view_org_profile(self):
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/admin/settings/organization/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Organisation Profile")

    def test_staff_cannot_view_org_profile(self):
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get("/admin/settings/organization/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_save_org_profile(self):
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post("/admin/settings/organization/", {
            "legal_name": "Test Org Inc.",
            "operating_name": "Test Org",
            "description": "Test mission",
            "description_fr": "Mission de test",
            "legal_status": "Nonprofit",
            "sector_codes": "[]",
            "street_address": "123 Main St",
            "city": "Ottawa",
            "province": "ON",
            "postal_code": "K1A 0A6",
            "country": "CA",
            "website": "https://test.ca",
        })
        self.assertEqual(resp.status_code, 302)
        profile = OrganizationProfile.get_solo()
        self.assertEqual(profile.legal_name, "Test Org Inc.")
        self.assertEqual(profile.operating_name, "Test Org")

    def test_anonymous_redirected_to_login(self):
        resp = self.http_client.get("/admin/settings/organization/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)


# ══════════════════════════════════════════════════════════════════════
# Session 2 Tests
# ══════════════════════════════════════════════════════════════════════


# ── CidsCodeList model ───────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CidsCodeListTest(TestCase):
    def setUp(self):
        enc_module._fernet = None

    def test_create_code_list_entry(self):
        entry = CidsCodeList.objects.create(
            list_name="ICNPOsector",
            code="ICNPO-7",
            label="Health",
        )
        self.assertEqual(entry.list_name, "ICNPOsector")
        self.assertEqual(entry.code, "ICNPO-7")
        self.assertEqual(entry.label, "Health")

    def test_unique_together_constraint(self):
        CidsCodeList.objects.create(
            list_name="ICNPOsector", code="ICNPO-7", label="Health",
        )
        with self.assertRaises(Exception):
            CidsCodeList.objects.create(
                list_name="ICNPOsector", code="ICNPO-7", label="Duplicate",
            )

    def test_same_code_different_list_allowed(self):
        CidsCodeList.objects.create(
            list_name="ICNPOsector", code="1", label="Sector 1",
        )
        entry2 = CidsCodeList.objects.create(
            list_name="SDGImpacts", code="1", label="No Poverty",
        )
        self.assertEqual(CidsCodeList.objects.count(), 2)
        self.assertEqual(entry2.label, "No Poverty")

    def test_optional_fields_default_blank(self):
        entry = CidsCodeList.objects.create(
            list_name="Test", code="T1", label="Test",
        )
        self.assertEqual(entry.label_fr, "")
        self.assertEqual(entry.description, "")
        self.assertEqual(entry.specification_uri, "")
        self.assertEqual(entry.defined_by_name, "")
        self.assertEqual(entry.defined_by_uri, "")
        self.assertEqual(entry.source_url, "")
        self.assertIsNone(entry.version_date)

    def test_str_representation(self):
        entry = CidsCodeList.objects.create(
            list_name="SDGImpacts", code="1", label="No Poverty",
        )
        self.assertEqual(str(entry), "SDGImpacts: 1 — No Poverty")

    def test_bilingual_labels(self):
        entry = CidsCodeList.objects.create(
            list_name="ICNPOsector", code="ICNPO-7",
            label="Health", label_fr="Santé",
        )
        entry.refresh_from_db()
        self.assertEqual(entry.label, "Health")
        self.assertEqual(entry.label_fr, "Santé")


# ── TaxonomyMapping model ───────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TaxonomyMappingTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.metric = MetricDefinition.objects.create(
            name="Test Metric", definition="Test",
        )
        self.program = Program.objects.create(name="Test Program")

    def test_create_metric_mapping(self):
        mapping = TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="cids_iris",
            taxonomy_code="PI2061",
            taxonomy_label="Housing Stability",
        )
        self.assertEqual(mapping.taxonomy_system, "cids_iris")
        self.assertEqual(mapping.taxonomy_code, "PI2061")
        self.assertEqual(mapping.metric_definition, self.metric)

    def test_create_program_mapping(self):
        mapping = TaxonomyMapping.objects.create(
            program=self.program,
            taxonomy_system="united_way",
            taxonomy_code="UW-HOUSING",
        )
        self.assertEqual(mapping.program, self.program)

    def test_clean_rejects_no_fk(self):
        mapping = TaxonomyMapping(
            taxonomy_system="cids_iris",
            taxonomy_code="PI2061",
        )
        with self.assertRaises(ValidationError):
            mapping.clean()

    def test_clean_rejects_multiple_fks(self):
        mapping = TaxonomyMapping(
            metric_definition=self.metric,
            program=self.program,
            taxonomy_system="cids_iris",
            taxonomy_code="PI2061",
        )
        with self.assertRaises(ValidationError):
            mapping.clean()

    def test_clean_accepts_single_fk(self):
        mapping = TaxonomyMapping(
            metric_definition=self.metric,
            taxonomy_system="cids_iris",
            taxonomy_code="PI2061",
        )
        mapping.clean()  # Should not raise

    def test_multiple_mappings_per_metric(self):
        TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="cids_iris",
            taxonomy_code="PI2061",
        )
        TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="united_way",
            taxonomy_code="UW-HST",
        )
        self.assertEqual(self.metric.taxonomy_mappings.count(), 2)

    def test_funder_context_scoping(self):
        TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="provincial",
            taxonomy_code="ON-HST",
            funder_context="Ontario MOHLTC",
        )
        TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="provincial",
            taxonomy_code="QC-HAB",
            funder_context="Quebec MSSS",
        )
        on_mapping = self.metric.taxonomy_mappings.filter(
            funder_context="Ontario MOHLTC",
        ).first()
        self.assertEqual(on_mapping.taxonomy_code, "ON-HST")

    def test_str_representation(self):
        mapping = TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="cids_iris",
            taxonomy_code="PI2061",
        )
        self.assertIn("cids_iris:PI2061", str(mapping))


# ── import_cids_codelists management command ─────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ImportCidsCodelistsTest(TestCase):
    def setUp(self):
        enc_module._fernet = None

    @patch("apps.admin_settings.management.commands.import_cids_codelists.fetch_code_list")
    def test_import_creates_entries(self, mock_fetch):
        mock_fetch.return_value = (
            [
                {"code": "1", "label": "No Poverty", "label_fr": "Pas de pauvreté", "description": ""},
                {"code": "2", "label": "Zero Hunger", "label_fr": "Faim zéro", "description": ""},
            ],
            "2026-01-15",
            "https://example.com/spec",
        )
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command(
            "import_cids_codelists",
            "--lists", "SDGImpacts",
            stdout=out,
        )
        self.assertEqual(CidsCodeList.objects.filter(list_name="SDGImpacts").count(), 2)
        entry = CidsCodeList.objects.get(list_name="SDGImpacts", code="1")
        self.assertEqual(entry.label, "No Poverty")
        self.assertEqual(entry.label_fr, "Pas de pauvreté")

    @patch("apps.admin_settings.management.commands.import_cids_codelists.fetch_code_list")
    def test_import_upserts_existing(self, mock_fetch):
        CidsCodeList.objects.create(
            list_name="SDGImpacts", code="1", label="Old Label",
        )
        mock_fetch.return_value = (
            [{"code": "1", "label": "No Poverty", "label_fr": "", "description": ""}],
            None,
            "",
        )
        from django.core.management import call_command
        from io import StringIO
        call_command(
            "import_cids_codelists",
            "--lists", "SDGImpacts",
            "--force",
            stdout=StringIO(),
        )
        entry = CidsCodeList.objects.get(list_name="SDGImpacts", code="1")
        self.assertEqual(entry.label, "No Poverty")

    @patch("apps.admin_settings.management.commands.import_cids_codelists.fetch_code_list")
    def test_dry_run_does_not_write(self, mock_fetch):
        mock_fetch.return_value = (
            [{"code": "1", "label": "Test", "label_fr": "", "description": ""}],
            None,
            "",
        )
        from django.core.management import call_command
        from io import StringIO
        call_command(
            "import_cids_codelists",
            "--lists", "SDGImpacts",
            "--dry-run",
            stdout=StringIO(),
        )
        self.assertEqual(CidsCodeList.objects.count(), 0)

    @patch("apps.admin_settings.management.commands.import_cids_codelists.fetch_code_list")
    def test_connection_error_handled(self, mock_fetch):
        mock_fetch.side_effect = ConnectionError("Network error")
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        err = StringIO()
        call_command(
            "import_cids_codelists",
            "--lists", "SDGImpacts",
            stdout=out,
            stderr=err,
        )
        self.assertIn("FAILED", err.getvalue())


# ── CIDS theme derivation ────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CidsThemeDerivationTest(TestCase):
    def setUp(self):
        enc_module._fernet = None

    def test_admin_override_takes_precedence(self):
        from apps.reports.cids_enrichment import derive_cids_theme
        metric = MetricDefinition.objects.create(
            name="Test", definition="Test",
            iris_metric_code="PI2061",
            cids_theme_override="housing",
        )
        theme, source = derive_cids_theme(metric)
        self.assertEqual(theme, "housing")
        self.assertEqual(source, "override")

    def test_iris_lookup_works(self):
        from apps.reports.cids_enrichment import derive_cids_theme
        CidsCodeList.objects.create(
            list_name="IRISImpactTheme",
            code="PI2061",
            label="Basic Needs",
        )
        metric = MetricDefinition.objects.create(
            name="Housing", definition="Test",
            iris_metric_code="PI2061",
        )
        theme, source = derive_cids_theme(metric)
        self.assertEqual(theme, "Basic Needs")
        self.assertEqual(source, "iris_lookup")

    def test_no_theme_when_no_data(self):
        from apps.reports.cids_enrichment import derive_cids_theme
        metric = MetricDefinition.objects.create(
            name="Plain", definition="Test",
        )
        theme, source = derive_cids_theme(metric)
        self.assertIsNone(theme)
        self.assertIsNone(source)


# ── Standards alignment data ─────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StandardsAlignmentDataTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Housing First",
            cids_sector_code="ICNPO-7",
            funder_program_code="HF-2026",
        )

    def test_alignment_data_structure(self):
        from apps.reports.cids_enrichment import get_standards_alignment_data
        metrics = MetricDefinition.objects.filter(pk__in=[])  # empty queryset
        data = get_standards_alignment_data(self.program, metric_definitions=metrics)
        self.assertEqual(data["cids_version"], "3.2.0")
        self.assertEqual(data["program_cids"]["sector_code"], "ICNPO-7")
        self.assertEqual(data["program_cids"]["funder_code"], "HF-2026")
        self.assertEqual(data["metrics"], [])
        self.assertEqual(data["mapped_count"], 0)
        self.assertEqual(data["total_count"], 0)

    def test_alignment_counts_mapped_metrics(self):
        from apps.reports.cids_enrichment import get_standards_alignment_data
        MetricDefinition.objects.create(
            name="Mapped", definition="Test",
            iris_metric_code="PI2061", sdg_goals=[1, 11],
        )
        MetricDefinition.objects.create(
            name="Unmapped", definition="Test",
        )
        metrics = MetricDefinition.objects.all()
        data = get_standards_alignment_data(self.program, metric_definitions=metrics)
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["mapped_count"], 1)
        self.assertEqual(data["sdg_summary"], {1: 1, 11: 1})


# ══════════════════════════════════════════════════════════════════════
# Session 3: ServiceEpisode tests
# ══════════════════════════════════════════════════════════════════════

from apps.clients.models import (
    ClientFile, ClientProgramEnrolment, ServiceEpisode,
    ServiceEpisodeStatusChange,
)


# ── ServiceEpisode model tests ────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ServiceEpisodeModelTest(TestCase):
    """Test ServiceEpisode model (renamed from ClientProgramEnrolment)."""

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "User"
        self.client_file.save()
        self.program = Program.objects.create(name="Test Program")
        self.program2 = Program.objects.create(name="Other Program")

    def test_alias_still_works(self):
        """ClientProgramEnrolment alias refers to the same class."""
        self.assertIs(ClientProgramEnrolment, ServiceEpisode)

    def test_new_status_choices(self):
        """Status field accepts all new choices."""
        for status_val in ("planned", "waitlist", "active", "on_hold", "finished", "cancelled"):
            ep = ServiceEpisode.objects.create(
                client_file=self.client_file,
                program=self.program,
                status=status_val,
            )
            ep.refresh_from_db()
            self.assertEqual(ep.status, status_val)
            ep.delete()

    def test_default_status_is_active(self):
        ep = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        self.assertEqual(ep.status, "active")

    def test_episode_type_auto_derives_new_intake(self):
        """First episode for client × program auto-derives as new_intake."""
        ep = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        self.assertEqual(ep.episode_type, "new_intake")

    def test_episode_type_auto_derives_re_enrolment(self):
        """Second episode after a finished one auto-derives as re_enrolment."""
        ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="finished",
        )
        ep2 = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        self.assertEqual(ep2.episode_type, "re_enrolment")

    def test_episode_type_auto_derives_transfer_in(self):
        """Episode after a transferred one from another program."""
        ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="finished",
            end_reason="transferred",
        )
        ep2 = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program2,
        )
        self.assertEqual(ep2.episode_type, "transfer_in")

    def test_episode_type_preserves_admin_set(self):
        """Crisis and short_term are not overridden by auto-derivation."""
        ep = ServiceEpisode(
            client_file=self.client_file,
            program=self.program,
            episode_type="crisis",
        )
        derived = ep.derive_episode_type()
        self.assertEqual(derived, "crisis")

    def test_new_fields_nullable(self):
        """All new fields default to blank/null."""
        ep = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        self.assertEqual(ep.status_reason, "")
        self.assertEqual(ep.referral_source, "")
        self.assertEqual(ep.end_reason, "")
        self.assertIsNone(ep.primary_worker)
        self.assertIsNone(ep.ended_at)

    def test_started_at_auto_set(self):
        """started_at auto-sets on create."""
        ep = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        self.assertIsNotNone(ep.started_at)

    def test_db_table_unchanged(self):
        """Table name stays as client_program_enrolments."""
        self.assertEqual(ServiceEpisode._meta.db_table, "client_program_enrolments")

    def test_str_representation(self):
        ep = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        self.assertIn("→", str(ep))


# ── ServiceEpisodeStatusChange tests ───────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StatusChangeTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "User"
        self.client_file.save()
        self.program = Program.objects.create(name="Test Program")
        self.user = User.objects.create_user(
            username="worker", password="test123",
        )

    def test_create_status_change(self):
        ep = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        sc = ServiceEpisodeStatusChange.objects.create(
            episode=ep,
            status="on_hold",
            reason="Summer break",
            changed_by=self.user,
        )
        self.assertEqual(sc.status, "on_hold")
        self.assertEqual(sc.reason, "Summer break")
        self.assertEqual(sc.changed_by, self.user)

    def test_cascade_delete(self):
        """Deleting episode cascades to status changes."""
        ep = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        ServiceEpisodeStatusChange.objects.create(
            episode=ep, status="active",
        )
        ServiceEpisodeStatusChange.objects.create(
            episode=ep, status="on_hold",
        )
        self.assertEqual(ServiceEpisodeStatusChange.objects.count(), 2)
        ep.delete()
        self.assertEqual(ServiceEpisodeStatusChange.objects.count(), 0)

    def test_ordering(self):
        """Status changes are ordered by changed_at."""
        ep = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        sc1 = ServiceEpisodeStatusChange.objects.create(
            episode=ep, status="active",
        )
        sc2 = ServiceEpisodeStatusChange.objects.create(
            episode=ep, status="on_hold",
        )
        changes = list(ep.status_changes.values_list("status", flat=True))
        self.assertEqual(changes, ["active", "on_hold"])

    def test_str_representation(self):
        ep = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        sc = ServiceEpisodeStatusChange.objects.create(
            episode=ep, status="finished",
        )
        self.assertIn("finished", str(sc))


# ── Discharge / On-hold / Resume view tests ───────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DischargeViewTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="pm", password="test123",
        )
        self.program = Program.objects.create(name="Test Program")
        from apps.programs.models import UserProgramRole
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="program_manager",
        )
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "User"
        self.client_file.save()
        self.episode = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="active",
        )
        self.http_client = Client()
        self.http_client.force_login(self.user)

    def test_discharge_sets_finished(self):
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/discharge/",
            {"program_id": self.program.pk, "end_reason": "goals_met"},
        )
        self.assertEqual(resp.status_code, 302)
        self.episode.refresh_from_db()
        self.assertEqual(self.episode.status, "finished")
        self.assertEqual(self.episode.end_reason, "goals_met")
        self.assertIsNotNone(self.episode.ended_at)

    def test_discharge_creates_status_change(self):
        self.http_client.post(
            f"/participants/{self.client_file.pk}/discharge/",
            {"program_id": self.program.pk, "end_reason": "withdrew", "status_reason": "Personal reasons"},
        )
        sc = ServiceEpisodeStatusChange.objects.filter(
            episode=self.episode, status="finished",
        ).first()
        self.assertIsNotNone(sc)
        self.assertIn("Withdrew", sc.reason)

    def test_discharge_requires_end_reason(self):
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/discharge/",
            {"program_id": self.program.pk},
        )
        # Should re-render form (200), not redirect (302)
        self.assertEqual(resp.status_code, 200)
        self.episode.refresh_from_db()
        self.assertEqual(self.episode.status, "active")  # unchanged


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class OnHoldResumeViewTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="pm", password="test123",
        )
        self.program = Program.objects.create(name="Test Program")
        from apps.programs.models import UserProgramRole
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="program_manager",
        )
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "User"
        self.client_file.save()
        self.episode = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="active",
        )
        self.http_client = Client()
        self.http_client.force_login(self.user)

    def test_on_hold(self):
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/on-hold/",
            {"program_id": self.program.pk, "status_reason": "Summer break"},
        )
        self.assertEqual(resp.status_code, 302)
        self.episode.refresh_from_db()
        self.assertEqual(self.episode.status, "on_hold")
        self.assertEqual(self.episode.status_reason, "Summer break")

    def test_resume(self):
        self.episode.status = "on_hold"
        self.episode.save()
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/resume/",
            {"program_id": self.program.pk},
        )
        self.assertEqual(resp.status_code, 302)
        self.episode.refresh_from_db()
        self.assertEqual(self.episode.status, "active")

    def test_on_hold_creates_status_change(self):
        self.http_client.post(
            f"/participants/{self.client_file.pk}/on-hold/",
            {"program_id": self.program.pk, "status_reason": "Vacation"},
        )
        sc = ServiceEpisodeStatusChange.objects.filter(
            episode=self.episode, status="on_hold",
        ).first()
        self.assertIsNotNone(sc)
        self.assertEqual(sc.reason, "Vacation")

    def test_resume_creates_status_change(self):
        self.episode.status = "on_hold"
        self.episode.save()
        self.http_client.post(
            f"/participants/{self.client_file.pk}/resume/",
            {"program_id": self.program.pk},
        )
        sc = ServiceEpisodeStatusChange.objects.filter(
            episode=self.episode, status="active",
        ).first()
        self.assertIsNotNone(sc)


# ── Data migration test ──────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DataMigrationLogicTest(TestCase):
    """Test the migration logic that converts enrolled→active."""

    def setUp(self):
        enc_module._fernet = None

    def test_new_episodes_use_active_not_enrolled(self):
        """After migration, new episodes default to 'active'."""
        cf = ClientFile.objects.create()
        cf.first_name = "Test"
        cf.last_name = "User"
        cf.save()
        program = Program.objects.create(name="Test")
        ep = ServiceEpisode.objects.create(
            client_file=cf, program=program,
        )
        self.assertEqual(ep.status, "active")
        self.assertNotEqual(ep.status, "enrolled")


# ── Session 4: Achievement Status Tests ─────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AchievementStatusQuantitativeTest(TestCase):
    """Test quantitative achievement derivation from MetricValues."""

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "User"
        self.client_file.save()
        self.program = Program.objects.create(name="Test Program")
        self.section = PlanSection.objects.create(
            client_file=self.client_file, program=self.program,
        )
        self.metric = MetricDefinition.objects.create(
            name="Wellbeing Score", definition="1-10 scale",
            higher_is_better=True, max_value=8.0,
        )
        self.target = PlanTarget(
            plan_section=self.section, client_file=self.client_file,
        )
        self.target.name = "Improve wellbeing"
        self.target.save()
        PlanTargetMetric.objects.create(
            plan_target=self.target, metric_def=self.metric, sort_order=0,
        )
        self.user = User.objects.create_user(username="worker", password="test123")

    def _create_note_with_value(self, value):
        """Helper to create a ProgressNote with a MetricValue."""
        note = ProgressNote(
            client_file=self.client_file,
            note_type="quick",
            author=self.user,
        )
        note.notes_text = "Session note"
        note.save()
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note, plan_target=self.target,
        )
        MetricValue.objects.create(
            progress_note_target=pnt, metric_def=self.metric, value=str(value),
        )
        return note

    def test_zero_data_points_in_progress(self):
        status, source = compute_achievement_status(self.target)
        self.assertEqual(status, "in_progress")
        self.assertEqual(source, "auto_computed")

    def test_one_data_point_in_progress(self):
        self._create_note_with_value(5)
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "in_progress")

    def test_one_data_point_meets_target_achieved(self):
        self._create_note_with_value(9)  # Above max_value=8 — signal computes
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "achieved")

    def test_two_points_improving(self):
        self._create_note_with_value(3)
        self._create_note_with_value(6)
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "improving")

    def test_two_points_worsening(self):
        self._create_note_with_value(6)
        self._create_note_with_value(3)
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "worsening")

    def test_three_points_improving(self):
        self._create_note_with_value(2)
        self._create_note_with_value(4)
        self._create_note_with_value(6)
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "improving")

    def test_three_points_worsening(self):
        self._create_note_with_value(6)
        self._create_note_with_value(4)
        self._create_note_with_value(2)
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "worsening")

    def test_three_points_no_change(self):
        self._create_note_with_value(5)
        self._create_note_with_value(6)
        self._create_note_with_value(5)  # Mixed: 1 up, 1 down
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "no_change")

    def test_achieved_sets_first_achieved_at(self):
        self._create_note_with_value(9)  # Meets target — signal auto-computes
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "achieved")
        self.assertIsNotNone(self.target.first_achieved_at)

    def test_sustaining_after_achieved(self):
        # First achieve — signal sets first_achieved_at
        self._create_note_with_value(9)
        self.target.refresh_from_db()
        first_achieved = self.target.first_achieved_at
        self.assertIsNotNone(first_achieved)

        # Another note still meeting target — signal updates to sustaining
        self._create_note_with_value(8.5)
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "sustaining")
        # first_achieved_at never cleared
        self.assertEqual(self.target.first_achieved_at, first_achieved)

    def test_worsening_after_achieved(self):
        self._create_note_with_value(9)  # Signal sets achieved + first_achieved_at
        self.target.refresh_from_db()
        self.assertIsNotNone(self.target.first_achieved_at)

        # Drop below target — signal updates to worsening
        self._create_note_with_value(3)
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "worsening")
        # first_achieved_at is preserved
        self.assertIsNotNone(self.target.first_achieved_at)

    def test_higher_is_better_false(self):
        """Lower-is-better metrics (e.g. PHQ-9)."""
        self.metric.higher_is_better = False
        self.metric.max_value = 5.0  # Target: score <= 5
        self.metric.save()

        self._create_note_with_value(12)
        self._create_note_with_value(8)
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "improving")

    def test_higher_is_better_false_achieved(self):
        self.metric.higher_is_better = False
        self.metric.max_value = 5.0
        self.metric.save()

        self._create_note_with_value(4)  # Below threshold = achieved
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "achieved")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AchievementStatusQualitativeTest(TestCase):
    """Test qualitative achievement derivation from progress_descriptor."""

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "User"
        self.client_file.save()
        self.program = Program.objects.create(name="Test Program")
        self.section = PlanSection.objects.create(
            client_file=self.client_file, program=self.program,
        )
        self.target = PlanTarget(
            plan_section=self.section, client_file=self.client_file,
        )
        self.target.name = "Qualitative goal"
        self.target.save()
        # No metrics linked — qualitative path
        self.user = User.objects.create_user(username="worker2", password="test123")

    def _create_note_with_descriptor(self, descriptor):
        note = ProgressNote(
            client_file=self.client_file,
            note_type="quick",
            author=self.user,
        )
        note.notes_text = "Note"
        note.save()
        ProgressNoteTarget.objects.create(
            progress_note=note,
            plan_target=self.target,
            progress_descriptor=descriptor,
        )
        return note

    def test_harder_maps_to_worsening(self):
        self._create_note_with_descriptor("harder")
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "worsening")

    def test_holding_maps_to_no_change(self):
        self._create_note_with_descriptor("holding")
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "no_change")

    def test_shifting_maps_to_improving(self):
        self._create_note_with_descriptor("shifting")
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "improving")

    def test_good_place_maps_to_achieved(self):
        self._create_note_with_descriptor("good_place")
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "achieved")

    def test_good_place_sustaining_after_achieved(self):
        # First achieve — signal sets it
        self._create_note_with_descriptor("good_place")
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "achieved")

        # Second good_place → sustaining
        self._create_note_with_descriptor("good_place")
        self.target.refresh_from_db()
        self.assertEqual(self.target.achievement_status, "sustaining")

    def test_no_descriptor_in_progress(self):
        """No progress entries → in_progress."""
        status, _ = compute_achievement_status(self.target)
        self.assertEqual(status, "in_progress")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AchievementWorkerOverrideTest(TestCase):
    """Test worker override and not_attainable rules."""

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "User"
        self.client_file.save()
        self.program = Program.objects.create(name="Test Program")
        self.section = PlanSection.objects.create(
            client_file=self.client_file, program=self.program,
        )
        self.target = PlanTarget(
            plan_section=self.section, client_file=self.client_file,
        )
        self.target.name = "Worker override test"
        self.target.save()

    def test_worker_override_preserved_through_auto_computation(self):
        """Auto-computation does NOT overwrite worker_assessed status."""
        self.target.achievement_status = "not_attainable"
        self.target.achievement_status_source = "worker_assessed"
        self.target.save()

        # Try auto-computation
        update_achievement_status(self.target)
        self.target.refresh_from_db()
        # Worker assessment preserved
        self.assertEqual(self.target.achievement_status, "not_attainable")
        self.assertEqual(self.target.achievement_status_source, "worker_assessed")

    def test_not_attainable_never_auto_set(self):
        """compute_achievement_status never returns not_attainable."""
        status, _ = compute_achievement_status(self.target)
        self.assertNotEqual(status, "not_attainable")

    def test_first_achieved_at_never_cleared(self):
        """Once first_achieved_at is set, it persists even on status change."""
        now = timezone.now()
        self.target.first_achieved_at = now
        self.target.achievement_status = "achieved"
        self.target.achievement_status_source = "auto_computed"
        self.target.save()

        # Recompute — status changes but first_achieved_at stays
        update_achievement_status(self.target)
        self.target.refresh_from_db()
        self.assertEqual(self.target.first_achieved_at, now)


# ── Session 4: Author Role Tests ────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AuthorRoleAutoFillTest(TestCase):
    """Test author_role auto-fill on ProgressNote creation."""

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(username="staff", password="test123")
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="staff",
        )
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "User"
        self.client_file.save()

    def test_auto_fill_on_creation(self):
        note = ProgressNote(
            client_file=self.client_file,
            note_type="quick",
            author=self.user,
            author_program=self.program,
        )
        note.notes_text = "Test"
        note.save()
        self.assertEqual(note.author_role, "staff")

    def test_correct_role_lookup(self):
        """Uses the role from the specific program, not just any role."""
        other_program = Program.objects.create(name="Other Program")
        UserProgramRole.objects.create(
            user=self.user, program=other_program, role="program_manager",
        )
        note = ProgressNote(
            client_file=self.client_file,
            note_type="quick",
            author=self.user,
            author_program=other_program,
        )
        note.notes_text = "Test"
        note.save()
        self.assertEqual(note.author_role, "program_manager")

    def test_missing_role_handled_gracefully(self):
        """No UserProgramRole → author_role stays blank."""
        other_user = User.objects.create_user(
            username="norole", password="test123",
        )
        note = ProgressNote(
            client_file=self.client_file,
            note_type="quick",
            author=other_user,
            author_program=self.program,
        )
        note.notes_text = "Test"
        note.save()
        self.assertEqual(note.author_role, "")

    def test_no_author_program_stays_blank(self):
        """No author_program → author_role stays blank."""
        note = ProgressNote(
            client_file=self.client_file,
            note_type="quick",
            author=self.user,
        )
        note.notes_text = "Test"
        note.save()
        self.assertEqual(note.author_role, "")
