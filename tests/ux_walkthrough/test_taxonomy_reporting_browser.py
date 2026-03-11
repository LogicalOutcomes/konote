"""Browser walkthrough for taxonomy review and reporting lens flows."""
import unittest

import pytest
from django.utils import timezone

from .browser_base import BrowserTestBase


HAS_PLAYWRIGHT = False
try:
    import playwright  # noqa: F401
    HAS_PLAYWRIGHT = True
except ImportError:
    pass


@unittest.skipUnless(HAS_PLAYWRIGHT, "Playwright not installed")
@pytest.mark.browser
class TaxonomyReportingBrowserTest(BrowserTestBase):
    """Exercise the new admin classification and reporting-lens UI."""

    def _create_test_data(self):
        super()._create_test_data()

        from apps.admin_settings.models import CidsCodeList, TaxonomyMapping
        from apps.notes.models import MetricValue, ProgressNoteTarget
        from apps.plans.models import MetricDefinition, PlanTargetMetric
        from apps.reports.models import Partner, ReportMetric, ReportTemplate

        self.client_a.birth_date = "1990-01-01"
        self.client_a.save()

        self.metric_b = MetricDefinition.objects.create(
            name="Sessions Attended",
            definition="Counts completed support sessions.",
            category="general",
            unit="sessions",
            is_enabled=True,
        )
        self.metric_c = MetricDefinition.objects.create(
            name="Housing Stability Index",
            definition="Tracks whether the participant remains housed.",
            category="housing",
            unit="score",
            is_enabled=True,
        )
        PlanTargetMetric.objects.create(plan_target=self.plan_target, metric_def=self.metric_b)
        PlanTargetMetric.objects.create(plan_target=self.plan_target, metric_def=self.metric_c)

        self.note_target = ProgressNoteTarget.objects.create(
            progress_note=self.note,
            plan_target=self.plan_target,
        )
        MetricValue.objects.create(
            progress_note_target=self.note_target,
            metric_def=self.metric_a,
            value="8",
        )

        CidsCodeList.objects.create(
            list_name="SDGImpacts",
            code="3",
            label="Good Health and Well-Being",
            description="Ensure healthy lives and promote well-being for all.",
        )
        CidsCodeList.objects.create(
            list_name="SDGImpacts",
            code="8",
            label="Decent Work and Economic Growth",
            description="Promote sustained, inclusive economic growth.",
        )
        CidsCodeList.objects.create(
            list_name="SDGImpacts",
            code="11",
            label="Sustainable Cities and Communities",
            description="Make cities and human settlements inclusive and safe.",
        )

        self.primary_mapping = TaxonomyMapping.objects.create(
            metric_definition=self.metric_a,
            taxonomy_system="sdg",
            taxonomy_list_name="SDGImpacts",
            taxonomy_code="11",
            taxonomy_label="Sustainable Cities and Communities",
            mapping_status="draft",
            mapping_source="system_suggested",
            confidence_score=0.71,
            rationale="Broad housing and community match based on the metric wording.",
        )
        self.bulk_mapping_1 = TaxonomyMapping.objects.create(
            metric_definition=self.metric_b,
            taxonomy_system="sdg",
            taxonomy_list_name="SDGImpacts",
            taxonomy_code="8",
            taxonomy_label="Decent Work and Economic Growth",
            mapping_status="draft",
            mapping_source="system_suggested",
            confidence_score=0.66,
            rationale="Session attendance can support economic participation reporting.",
        )
        self.bulk_mapping_2 = TaxonomyMapping.objects.create(
            metric_definition=self.metric_c,
            taxonomy_system="sdg",
            taxonomy_list_name="SDGImpacts",
            taxonomy_code="11",
            taxonomy_label="Sustainable Cities and Communities",
            mapping_status="draft",
            mapping_source="system_suggested",
            confidence_score=0.89,
            rationale="Direct housing stability alignment.",
        )

        self.partner = Partner.objects.create(
            name="City Funder",
            partner_type="funder",
        )
        self.partner.programs.add(self.program_a)
        self.report_template = ReportTemplate.objects.create(
            partner=self.partner,
            name="Quarterly Outcomes Report",
            description="Template for partner-ready outcomes reporting.",
            created_by=self.admin_user,
            period_type="quarterly",
            period_alignment="fiscal",
            output_format="mixed",
            taxonomy_system="sdg",
        )
        ReportMetric.objects.create(
            report_template=self.report_template,
            metric_definition=self.metric_a,
            aggregation="average",
            display_label="PHQ-9 Score",
            sort_order=1,
        )

    def test_taxonomy_review_and_reporting_lens_walkthrough(self):
        self.login_via_browser("admin")

        self.page.goto(self.live_url("/admin/settings/classification/"))
        self.page.wait_for_load_state("networkidle")
        self.assertTrue(self.page.get_by_role("heading", name="Classification Review").is_visible())

        self.page.locator("tr", has_text="Sessions Attended").locator(".bulk-mapping-checkbox").check()
        self.page.locator("tr", has_text="Housing Stability Index").locator(".bulk-mapping-checkbox").check()
        self.page.select_option("#bulk-review-form select[name='action']", "approve")
        self.page.get_by_role("button", name="Apply to Selected").click()
        self.page.wait_for_load_state("networkidle")
        self.assertIn("2 mapping(s) approved.", self.page.locator("body").inner_text())

        self.page.get_by_role("link", name="PHQ-9 Score").click()
        self.page.wait_for_load_state("networkidle")
        self.assertTrue(self.page.get_by_role("heading", name="Review Mapping").is_visible())

        self.page.fill("input[name='query']", "good health")
        self.page.get_by_role("button", name="Search This Code List").click()
        self.page.wait_for_load_state("networkidle")
        self.assertIn("Good Health and Well-Being", self.page.locator("body").inner_text())
        self.page.locator("tr", has_text="Good Health and Well-Being").get_by_role("button", name="Use This Code").click()
        self.page.wait_for_load_state("networkidle")
        body_text = self.page.locator("body").inner_text()
        self.assertIn("Manual code selection saved and approved.", body_text)
        self.assertIn("Code: 3", body_text)

        self.page.goto(self.live_url("/reports/funder-report/"))
        self.page.wait_for_load_state("networkidle")
        self.page.select_option("#id_program", str(self.program_a.pk))
        self.page.select_option("#id_report_template", str(self.report_template.pk))
        fiscal_year = self.page.locator("#id_fiscal_year option").nth(1).get_attribute("value")
        self.page.select_option("#id_fiscal_year", fiscal_year)

        self.page.check("input[name='format'][value='html']")
        self.page.fill("#id_recipient", "Jordan Lee, City Funder")
        self.page.fill("#id_recipient_reason", "Quarterly partner reporting")
        self.page.get_by_role("button", name="Generate Preview").click()
        self.page.wait_for_load_state("networkidle")
        preview_text = self.page.locator("body").inner_text()
        self.assertIn("Review Report Before Approving", preview_text)
        self.assertIn("Standards Lens", preview_text)
        self.assertIn("SDG", preview_text)

        self.page.goto(self.live_url("/reports/generate/"))
        self.page.wait_for_load_state("networkidle")
        self.page.select_option("#id_report_template", str(self.report_template.pk))
        self.wait_for_htmx()
        period_value = self.page.locator("#id_period option").nth(0).get_attribute("value")
        self.page.select_option("#id_period", period_value)

        self.page.fill("#id_recipient", "Jordan Lee, City Funder")
        self.page.fill("#id_recipient_reason", "Quarterly partner reporting")
        self.page.get_by_role("button", name="Preview on Screen").click()
        self.page.wait_for_load_state("networkidle")
        report_text = self.page.locator("body").inner_text()
        self.assertIn("Reporting Lens:", report_text)
        self.assertIn("SDG", report_text)
        self.assertIn("Good Health and Well-Being", report_text)
        self.assertIn("Selected Code", report_text)