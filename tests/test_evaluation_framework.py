"""Tests for evaluation planning models, views, and CIDS Full Tier mapping."""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import (
    EvaluationComponent,
    EvaluationEvidenceLink,
    EvaluationFramework,
    Program,
    UserProgramRole,
)

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _create_admin():
    user = User.objects.create_user(
        username="admin_eval",
        email="admin_eval@test.com",
        password="testpass123",
        is_admin=True,
    )
    return user


def _create_staff():
    user = User.objects.create_user(
        username="staff_eval",
        email="staff_eval@test.com",
        password="testpass123",
        is_admin=False,
    )
    return user


def _create_program(**kwargs):
    defaults = {"name": "Test Program", "description": "A test program"}
    defaults.update(kwargs)
    return Program.objects.create(**defaults)


# ── Model tests ────────────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationFrameworkModelTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.program = _create_program()

    def test_create_framework(self):
        fw = EvaluationFramework.objects.create(
            name="Test Framework",
            program=self.program,
            summary="Test summary",
        )
        self.assertEqual(fw.status, "draft")
        self.assertEqual(fw.planning_quality_state, "manual")
        self.assertFalse(fw.is_attested)
        self.assertEqual(str(fw), "Test Framework (Test Program)")

    def test_cids_class_coverage_empty(self):
        fw = EvaluationFramework.objects.create(
            name="Empty Framework", program=self.program,
        )
        self.assertEqual(fw.cids_class_coverage, set())

    def test_cids_class_coverage_with_components(self):
        fw = EvaluationFramework.objects.create(
            name="Full Framework", program=self.program,
        )
        EvaluationComponent.objects.create(
            framework=fw, component_type="service", name="Counselling",
        )
        EvaluationComponent.objects.create(
            framework=fw, component_type="activity", name="Group sessions",
        )
        EvaluationComponent.objects.create(
            framework=fw, component_type="output", name="Sessions delivered",
        )
        coverage = fw.cids_class_coverage
        self.assertIn("cids:Service", coverage)
        self.assertIn("cids:Activity", coverage)
        self.assertIn("cids:Output", coverage)
        self.assertEqual(len(coverage), 3)

    def test_attestation(self):
        user = _create_admin()
        fw = EvaluationFramework.objects.create(
            name="Attested Framework", program=self.program,
        )
        fw.evaluator_attestation_by = user
        fw.evaluator_attestation_at = timezone.now()
        fw.evaluator_attestation_scope = ["impact_model", "risk_assessment"]
        fw.save()
        fw.refresh_from_db()
        self.assertTrue(fw.is_attested)
        self.assertEqual(len(fw.evaluator_attestation_scope), 2)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationComponentModelTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.program = _create_program()
        self.fw = EvaluationFramework.objects.create(
            name="Test Framework", program=self.program,
        )

    def test_auto_populate_cids_class(self):
        comp = EvaluationComponent.objects.create(
            framework=self.fw, component_type="service", name="Counselling",
        )
        self.assertEqual(comp.cids_class, "cids:Service")

    def test_all_cids_class_mappings(self):
        mappings = {
            "participant_group": "cids:Stakeholder",
            "service": "cids:Service",
            "activity": "cids:Activity",
            "output": "cids:Output",
            "outcome": "cids:StakeholderOutcome",
            "risk": "cids:ImpactRisk",
            "counterfactual": "cids:Counterfactual",
            "input": "cids:Input",
        }
        for comp_type, expected_class in mappings.items():
            comp = EvaluationComponent.objects.create(
                framework=self.fw, component_type=comp_type, name=f"Test {comp_type}",
            )
            self.assertEqual(comp.cids_class, expected_class, f"Failed for {comp_type}")

    def test_self_referential_parent(self):
        parent = EvaluationComponent.objects.create(
            framework=self.fw, component_type="service", name="Parent Service",
        )
        child = EvaluationComponent.objects.create(
            framework=self.fw, component_type="activity", name="Child Activity",
            parent=parent,
        )
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

    def test_deactivated_component_excluded_from_coverage(self):
        comp = EvaluationComponent.objects.create(
            framework=self.fw, component_type="service", name="Inactive Service",
            is_active=False,
        )
        self.assertNotIn("cids:Service", self.fw.cids_class_coverage)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationEvidenceLinkModelTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.program = _create_program()
        self.fw = EvaluationFramework.objects.create(
            name="Test Framework", program=self.program,
        )

    def test_create_evidence_link(self):
        link = EvaluationEvidenceLink.objects.create(
            framework=self.fw,
            title="Logic Model v2",
            source_type="logic_model",
            excerpt_text="Key outcomes include housing stability.",
        )
        self.assertEqual(str(link), "Logic Model v2")
        self.assertFalse(link.contains_pii)
        self.assertFalse(link.used_for_ai)


# ── View tests ─────────────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FrameworkViewAccessTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.program = _create_program()
        self.admin = _create_admin()
        self.staff = _create_staff()
        self.client = Client()

    def test_list_requires_admin(self):
        self.client.login(username="staff_eval", password="testpass123")
        resp = self.client.get(reverse("programs:framework_list"))
        self.assertEqual(resp.status_code, 403)

    def test_list_accessible_by_admin(self):
        self.client.login(username="admin_eval", password="testpass123")
        resp = self.client.get(reverse("programs:framework_list"))
        self.assertEqual(resp.status_code, 200)

    def test_create_requires_admin(self):
        self.client.login(username="staff_eval", password="testpass123")
        resp = self.client.get(
            reverse("programs:framework_create", kwargs={"program_id": self.program.pk})
        )
        self.assertEqual(resp.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FrameworkCRUDTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.program = _create_program()
        self.admin = _create_admin()
        self.client = Client()
        self.client.login(username="admin_eval", password="testpass123")

    def test_create_framework(self):
        resp = self.client.post(
            reverse("programs:framework_create", kwargs={"program_id": self.program.pk}),
            {"name": "New Framework", "status": "draft", "summary": "Test"},
        )
        self.assertEqual(resp.status_code, 302)
        fw = EvaluationFramework.objects.get(name="New Framework")
        self.assertEqual(fw.program, self.program)
        self.assertEqual(fw.created_by, self.admin)

    def test_edit_framework(self):
        fw = EvaluationFramework.objects.create(
            name="Original", program=self.program, created_by=self.admin,
        )
        resp = self.client.post(
            reverse("programs:framework_edit", kwargs={"framework_id": fw.pk}),
            {"name": "Updated", "status": "active", "summary": "Updated summary"},
        )
        self.assertEqual(resp.status_code, 302)
        fw.refresh_from_db()
        self.assertEqual(fw.name, "Updated")
        self.assertEqual(fw.status, "active")

    def test_detail_view(self):
        fw = EvaluationFramework.objects.create(
            name="Detail Test", program=self.program,
        )
        resp = self.client.get(
            reverse("programs:framework_detail", kwargs={"framework_id": fw.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Detail Test")

    def test_add_component(self):
        fw = EvaluationFramework.objects.create(
            name="Component Test", program=self.program,
        )
        resp = self.client.post(
            reverse("programs:component_add", kwargs={"framework_id": fw.pk}),
            {"component_type": "service", "name": "Counselling", "description": "1:1 sessions", "sequence_order": "1"},
        )
        self.assertEqual(resp.status_code, 302)
        comp = EvaluationComponent.objects.get(framework=fw, name="Counselling")
        self.assertEqual(comp.cids_class, "cids:Service")

    def test_deactivate_component(self):
        fw = EvaluationFramework.objects.create(
            name="Deactivate Test", program=self.program,
        )
        comp = EvaluationComponent.objects.create(
            framework=fw, component_type="activity", name="To Remove",
        )
        resp = self.client.post(
            reverse("programs:component_deactivate", kwargs={
                "framework_id": fw.pk, "component_id": comp.pk,
            })
        )
        self.assertEqual(resp.status_code, 302)
        comp.refresh_from_db()
        self.assertFalse(comp.is_active)

    def test_add_evidence(self):
        fw = EvaluationFramework.objects.create(
            name="Evidence Test", program=self.program,
        )
        resp = self.client.post(
            reverse("programs:evidence_add", kwargs={"framework_id": fw.pk}),
            {"title": "Grant Proposal", "source_type": "proposal", "excerpt_text": "Key goals..."},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(EvaluationEvidenceLink.objects.filter(framework=fw).exists())

    def test_attestation(self):
        fw = EvaluationFramework.objects.create(
            name="Attest Test", program=self.program,
        )
        resp = self.client.post(
            reverse("programs:framework_attest", kwargs={"framework_id": fw.pk}),
            {"scope": ["impact_model", "outcome_measurement"], "attestation_text": "Reviewed and confirmed."},
        )
        self.assertEqual(resp.status_code, 302)
        fw.refresh_from_db()
        self.assertTrue(fw.is_attested)
        self.assertEqual(fw.evaluator_attestation_by, self.admin)
        self.assertIn("impact_model", fw.evaluator_attestation_scope)
