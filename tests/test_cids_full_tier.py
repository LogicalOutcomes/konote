"""Tests for CIDS Full Tier JSON-LD export assembly."""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import (
    EvaluationComponent,
    EvaluationFramework,
    Program,
)
from apps.reports.cids_full_tier import (
    build_full_tier_jsonld,
    get_agency_cids_summary,
    get_program_cids_coverage,
)

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _create_admin():
    return User.objects.create_user(
        username="admin_ft", email="admin_ft@test.com",
        password="testpass123", is_admin=True,
    )


def _create_program(**kwargs):
    defaults = {
        "name": "Housing Program",
        "description": "Supports housing stability for youth.",
        "population_served_codes": ["youth"],
    }
    defaults.update(kwargs)
    return Program.objects.create(**defaults)


def _create_full_framework(program, user=None):
    """Create a framework with all required Full Tier component types."""
    fw = EvaluationFramework.objects.create(
        name=f"{program.name} framework",
        program=program,
        status="active",
        summary="Theory of change for housing stability.",
        output_summary="Housing placements and referrals.",
        outcome_chain_summary="Stable housing leads to improved wellbeing.",
        risk_summary="Participant disengagement.",
        counterfactual_summary="Without intervention, homelessness persists.",
        created_by=user,
    )
    components = [
        ("participant_group", "Youth aged 16-24"),
        ("service", "Individual counselling"),
        ("activity", "Weekly check-ins"),
        ("output", "Housing referrals completed"),
        ("outcome", "Sustained housing stability"),
        ("risk", "Participant drops out"),
        ("counterfactual", "No intervention comparison"),
    ]
    for comp_type, name in components:
        EvaluationComponent.objects.create(
            framework=fw, component_type=comp_type, name=name,
        )
    return fw


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FullTierExportTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.program = _create_program()
        self.admin = _create_admin()
        self.fw = _create_full_framework(self.program, self.admin)

    def test_basic_export_produces_document(self):
        doc = build_full_tier_jsonld([self.program])
        self.assertIn("@context", doc)
        self.assertIn("@graph", doc)
        self.assertIn("cids:complianceTier", doc)

    def test_full_tier_with_all_components(self):
        doc = build_full_tier_jsonld([self.program])
        graph = doc["@graph"]
        types = {n["@type"] for n in graph if "@type" in n}
        self.assertIn("cids:Service", types)
        self.assertIn("cids:Activity", types)
        self.assertIn("cids:Counterfactual", types)
        self.assertEqual(doc["cids:complianceTier"], "FullTier")

    def test_class_count_matches(self):
        doc = build_full_tier_jsonld([self.program])
        graph = doc["@graph"]
        types = {n["@type"] for n in graph if "@type" in n}
        self.assertEqual(doc["cids:classCount"], len(types))

    def test_attestation_included_when_attested(self):
        self.fw.evaluator_attestation_by = self.admin
        self.fw.evaluator_attestation_at = timezone.now()
        self.fw.evaluator_attestation_scope = ["impact_model"]
        self.fw.save()

        doc = build_full_tier_jsonld([self.program])
        self.assertIn("cids:evaluatorAttestations", doc)
        self.assertEqual(len(doc["cids:evaluatorAttestations"]), 1)

    def test_no_framework_still_produces_basic_tier(self):
        program2 = _create_program(name="Empty Program", description="No framework.")
        doc = build_full_tier_jsonld([program2])
        self.assertIn("@graph", doc)
        # Without framework, should be Essential (has stubs) not Full
        self.assertNotEqual(doc["cids:complianceTier"], "FullTier")

    def test_impact_model_from_framework(self):
        doc = build_full_tier_jsonld([self.program])
        graph = doc["@graph"]
        impact_models = [n for n in graph if n.get("@type") == "cids:ImpactModel"]
        self.assertTrue(len(impact_models) >= 1)
        im = impact_models[0]
        self.assertIn("hasName", im)
        self.assertIn("hasDescription", im)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CoverageHelperTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.program = _create_program()

    def test_empty_coverage(self):
        coverage = get_program_cids_coverage(self.program)
        present = [c for c in coverage if c["status"] == "present"]
        # Should have basic tier + stubs (description + population_served_codes)
        self.assertTrue(len(present) >= 6)

    def test_full_coverage_with_framework(self):
        _create_full_framework(self.program)
        coverage = get_program_cids_coverage(self.program)
        present = [c for c in coverage if c["status"] == "present"]
        self.assertTrue(len(present) >= 12)

    def test_agency_summary(self):
        _create_full_framework(self.program)
        summaries = get_agency_cids_summary()
        self.assertEqual(len(summaries), 1)
        self.assertTrue(summaries[0]["has_framework"])
        self.assertTrue(summaries[0]["pct"] >= 80)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CidsViewsTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = _create_program()
        self.admin = _create_admin()
        self.client = Client()
        self.client.login(username="admin_ft", password="testpass123")

    def test_dashboard_accessible(self):
        resp = self.client.get(reverse("reports:cids_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "CIDS Compliance Dashboard")

    def test_export_status_page(self):
        resp = self.client.get(
            reverse("reports:cids_export_status", kwargs={"program_id": self.program.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.program.name)

    def test_full_tier_export_json(self):
        _create_full_framework(self.program, self.admin)
        resp = self.client.get(reverse("reports:cids_full_tier_export"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("@context", data)
        self.assertIn("cids:complianceTier", data)

    def test_full_tier_export_download(self):
        resp = self.client.get(
            reverse("reports:cids_full_tier_export") + "?format=download"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/ld+json")
        self.assertIn("attachment", resp["Content-Disposition"])

    def test_dashboard_requires_admin(self):
        self.client.logout()
        staff = User.objects.create_user(
            username="staff_ft", email="staff_ft@test.com",
            password="testpass123", is_admin=False,
        )
        self.client.login(username="staff_ft", password="testpass123")
        resp = self.client.get(reverse("reports:cids_dashboard"))
        self.assertEqual(resp.status_code, 403)
