"""Tests for CIDS metadata fields and OrganizationProfile (Session 1)."""
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.admin_settings.models import OrganizationProfile
from apps.auth_app.models import User
from apps.plans.models import MetricDefinition, PlanTarget, PlanSection
from apps.programs.models import Program
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
