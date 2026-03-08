"""Tests for taxonomy classification review workflow."""
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings

from apps.admin_settings.models import CidsCodeList, TaxonomyMapping
from apps.auth_app.models import User
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget
from apps.programs.models import Program
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TaxonomyReviewWorkflowTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin-review",
            password="testpass123",
            is_admin=True,
        )
        self.staff = User.objects.create_user(
            username="staff-review",
            password="testpass123",
            is_admin=False,
        )
        self.program = Program.objects.create(
            name="Housing Support",
            description="Helps people secure and maintain housing.",
        )
        self.metric = MetricDefinition.objects.create(
            name="Housing Stability Score",
            definition="Measures whether the participant is staying housed over time.",
            unit="score",
        )
        from apps.clients.models import ClientFile

        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Taylor"
        self.client_file.last_name = "Client"
        self.client_file.save()
        self.section = PlanSection.objects.create(
            client_file=self.client_file,
            program=self.program,
            name="Housing",
        )
        self.target = PlanTarget.objects.create(
            plan_section=self.section,
            client_file=self.client_file,
        )
        self.target.name = "Keep stable housing"
        self.target.description = "Maintain safe housing for the next six months."
        self.target.client_goal = "I want to keep my apartment."
        self.target.save()

        CidsCodeList.objects.create(
            list_name="IrisMetric53",
            code="PI4060",
            label="Housing stability score",
            description="Metric about sustained housing stability.",
        )
        CidsCodeList.objects.create(
            list_name="IrisMetric53",
            code="OI1111",
            label="Employment income change",
            description="Metric about earnings and work income.",
        )
        CidsCodeList.objects.create(
            list_name="SDGImpacts",
            code="11",
            label="Sustainable Cities and Communities",
            description="Housing, communities, and urban inclusion.",
        )
        CidsCodeList.objects.create(
            list_name="SDGImpacts",
            code="8",
            label="Decent Work and Economic Growth",
            description="Employment, work, and economic opportunity.",
        )

    def test_queue_requires_admin(self):
        self.client.login(username="staff-review", password="testpass123")
        response = self.client.get("/admin/settings/classification/")
        self.assertEqual(response.status_code, 403)

    def test_generate_metric_draft_suggestions(self):
        self.client.login(username="admin-review", password="testpass123")
        response = self.client.post(
            "/admin/settings/classification/generate/",
            {
                "subject_type": "metric",
                "taxonomy_list_name": "IrisMetric53",
                "max_items": 10,
                "max_suggestions": 2,
                "only_unmapped": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        drafts = TaxonomyMapping.objects.filter(
            metric_definition=self.metric,
            taxonomy_list_name="IrisMetric53",
            mapping_status="draft",
        )
        self.assertTrue(drafts.exists())
        self.assertEqual(drafts.first().taxonomy_system, "iris_plus")

    def test_generate_target_draft_suggestions(self):
        self.client.login(username="admin-review", password="testpass123")
        response = self.client.post(
            "/admin/settings/classification/generate/",
            {
                "subject_type": "target",
                "taxonomy_list_name": "SDGImpacts",
                "max_items": 10,
                "max_suggestions": 2,
                "only_unmapped": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            TaxonomyMapping.objects.filter(
                plan_target=self.target,
                taxonomy_list_name="SDGImpacts",
                mapping_status="draft",
            ).exists()
        )

    def test_approve_mapping_supersedes_sibling_drafts(self):
        approved_candidate = TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="iris_plus",
            taxonomy_list_name="IrisMetric53",
            taxonomy_code="PI4060",
            taxonomy_label="Housing stability score",
            mapping_status="draft",
            mapping_source="system_suggested",
        )
        sibling = TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="iris_plus",
            taxonomy_list_name="IrisMetric53",
            taxonomy_code="OI1111",
            taxonomy_label="Employment income change",
            mapping_status="draft",
            mapping_source="system_suggested",
        )
        self.client.login(username="admin-review", password="testpass123")
        response = self.client.post(f"/admin/settings/classification/{approved_candidate.pk}/approve/")
        self.assertEqual(response.status_code, 302)
        approved_candidate.refresh_from_db()
        sibling.refresh_from_db()
        self.assertEqual(approved_candidate.mapping_status, "approved")
        self.assertEqual(approved_candidate.reviewed_by, self.admin)
        self.assertEqual(sibling.mapping_status, "superseded")

    def test_reject_mapping_sets_review_metadata(self):
        mapping = TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="iris_plus",
            taxonomy_list_name="IrisMetric53",
            taxonomy_code="OI1111",
            taxonomy_label="Employment income change",
            mapping_status="draft",
            mapping_source="system_suggested",
        )
        self.client.login(username="admin-review", password="testpass123")
        response = self.client.post(f"/admin/settings/classification/{mapping.pk}/reject/")
        self.assertEqual(response.status_code, 302)
        mapping.refresh_from_db()
        self.assertEqual(mapping.mapping_status, "rejected")
        self.assertEqual(mapping.reviewed_by, self.admin)
        self.assertIsNotNone(mapping.reviewed_at)

    def test_reclassify_with_different_list_creates_new_drafts(self):
        mapping = TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="iris_plus",
            taxonomy_list_name="IrisMetric53",
            taxonomy_code="PI4060",
            taxonomy_label="Housing stability score",
            mapping_status="draft",
            mapping_source="system_suggested",
        )
        self.client.login(username="admin-review", password="testpass123")
        response = self.client.post(
            f"/admin/settings/classification/{mapping.pk}/reclassify/",
            {
                "taxonomy_list_name": "SDGImpacts",
                "max_suggestions": 2,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            TaxonomyMapping.objects.filter(
                metric_definition=self.metric,
                taxonomy_list_name="SDGImpacts",
                mapping_status="draft",
            ).exists()
        )

    def test_bulk_approve_updates_selected_drafts(self):
        other_metric = MetricDefinition.objects.create(
            name="Housing Retention",
            definition="Measures retained housing over six months.",
            unit="count",
        )
        first = TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="iris_plus",
            taxonomy_list_name="IrisMetric53",
            taxonomy_code="PI4060",
            taxonomy_label="Housing stability score",
            mapping_status="draft",
            mapping_source="system_suggested",
        )
        second = TaxonomyMapping.objects.create(
            metric_definition=other_metric,
            taxonomy_system="iris_plus",
            taxonomy_list_name="IrisMetric53",
            taxonomy_code="OI1111",
            taxonomy_label="Employment income change",
            mapping_status="draft",
            mapping_source="system_suggested",
        )
        self.client.login(username="admin-review", password="testpass123")
        response = self.client.post(
            "/admin/settings/classification/bulk-action/",
            {"action": "approve", "mapping_ids": f"{first.pk},{second.pk}"},
        )
        self.assertEqual(response.status_code, 302)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.mapping_status, "approved")
        self.assertEqual(second.mapping_status, "approved")

    def test_manual_pick_creates_approved_manual_mapping(self):
        mapping = TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="iris_plus",
            taxonomy_list_name="IrisMetric53",
            taxonomy_code="PI4060",
            taxonomy_label="Housing stability score",
            mapping_status="draft",
            mapping_source="system_suggested",
        )
        self.client.login(username="admin-review", password="testpass123")
        response = self.client.post(
            f"/admin/settings/classification/{mapping.pk}/manual-pick/",
            {"code": "OI1111"},
        )
        self.assertEqual(response.status_code, 302)
        manual_mapping = TaxonomyMapping.objects.get(
            metric_definition=self.metric,
            taxonomy_system="iris_plus",
            taxonomy_code="OI1111",
        )
        mapping.refresh_from_db()
        self.assertEqual(manual_mapping.mapping_status, "approved")
        self.assertEqual(manual_mapping.mapping_source, "manual")
        self.assertEqual(mapping.mapping_status, "superseded")

    @patch("apps.admin_settings.classification_views.answer_taxonomy_question")
    def test_detail_question_flow_records_conversation(self, mock_answer):
        mock_answer.return_value = "This fit was chosen because the wording centres on housing stability."
        mapping = TaxonomyMapping.objects.create(
            metric_definition=self.metric,
            taxonomy_system="iris_plus",
            taxonomy_list_name="IrisMetric53",
            taxonomy_code="PI4060",
            taxonomy_label="Housing stability score",
            mapping_status="draft",
            mapping_source="system_suggested",
        )
        self.client.login(username="admin-review", password="testpass123")
        response = self.client.post(
            f"/admin/settings/classification/{mapping.pk}/ask/",
            {"question": "Why not the employment code?"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Why not the employment code?")
        self.assertContains(response, "wording centres on housing stability")