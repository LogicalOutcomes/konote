"""Seed the Prosper Canada / Resilient Futures partner and report templates.

Creates:
- Partner: "Prosper Canada — Resilient Futures" (funder type)
- ReportTemplate: "Prosper Canada Quarterly Report" with metrics and demographics
- ReportTemplate: "RF Semi-Annual Demographic Report" with 10 RF identity constructs

Usage:
    python manage.py seed_prosper_canada_report_template
"""
from datetime import date

from django.core.management.base import BaseCommand

from apps.clients.models import CustomFieldDefinition
from apps.plans.models import MetricDefinition
from apps.reports.models import (
    DemographicBreakdown,
    Partner,
    ReportMetric,
    ReportSection,
    ReportTemplate,
)


# RF Social Identity age bins (ESDC reporting)
RF_AGE_BINS = [
    {"min": 18, "max": 24, "label": "18-24"},
    {"min": 25, "max": 34, "label": "25-34"},
    {"min": 35, "max": 44, "label": "35-44"},
    {"min": 45, "max": 54, "label": "45-54"},
    {"min": 55, "max": 64, "label": "55-64"},
    {"min": 65, "max": 120, "label": "65+"},
]

# Metrics for quarterly report (name must match MetricDefinition.name)
QUARTERLY_METRICS = [
    ("CFPB Financial Wellbeing Scale", "average_change", "Average change in CFPB score from intake to most recent"),
    ("Total Debt", "average_change", "Average change in total debt"),
    ("Monthly Income", "average_change", "Average change in monthly income"),
    ("Credit Score Change", "average", "Average credit score change"),
    ("Monthly Savings", "average", "Average monthly savings"),
    ("Savings Rate", "average", "Average savings rate"),
    ("Housing Stability Index", "average_change", "Average change in housing stability"),
]

# Demographic breakdowns (label, custom_field_name, keep_all, merge_categories)
DEMOGRAPHIC_BREAKDOWNS = [
    ("Gender Identity", "Gender Identity", True, {}),
    ("Racial Identity", "Racial Identity", True, {}),
    ("Indigenous Identity", "Indigenous Identity", True, {}),
    ("Born in Canada", "Born in Canada", True, {}),
    ("2SLGBTQIA+ Identity", "2SLGBTQIA+ Identity", True, {}),
    ("Disability", "Disability", True, {}),
    ("Caregiver Status", "Caregiver Status", True, {}),
    ("Primary Language", "Primary Language", True, {}),
    ("Employment Status at Intake", "Employment Status at Intake", False, {
        "Employed": ["Employed full-time", "Employed part-time", "Self-employed"],
        "Unemployed": ["Unemployed - seeking", "Unemployed - not seeking"],
        "Other": ["Student", "Retired", "On disability"],
    }),
    ("Household Income Bracket", "Household Income Bracket", True, {}),
]


class Command(BaseCommand):
    help = "Create Prosper Canada partner and report templates with RF demographics."

    def handle(self, *args, **options):
        partner = self._create_partner()
        self._create_quarterly_template(partner)
        self._create_demographic_template(partner)
        self.stdout.write(self.style.SUCCESS("Prosper Canada report templates seeded."))

    def _create_partner(self):
        partner, created = Partner.objects.get_or_create(
            name="Prosper Canada — Resilient Futures",
            defaults={
                "name_fr": "Prospérité Canada — Avenirs résilients",
                "partner_type": "funder",
                "contact_name": "",
                "grant_period_start": date(2025, 4, 1),
                "grant_period_end": date(2028, 3, 31),
                "notes": "ESDC Resilient Futures grant. Semi-annual demographic reporting + quarterly outcomes.",
            },
        )
        action = "Created" if created else "Found existing"
        self.stdout.write(f"  {action} partner: {partner.name} (pk={partner.pk})")
        return partner

    def _create_quarterly_template(self, partner):
        template, created = ReportTemplate.objects.get_or_create(
            partner=partner,
            name="Prosper Canada Quarterly Report",
            defaults={
                "description": (
                    "Standard quarterly outcome report for Prosper Canada partner agencies. "
                    "Covers financial outcomes (CFPB, debt, savings, credit), service statistics, "
                    "and participant demographics."
                ),
                "period_type": "quarterly",
                "period_alignment": "fiscal",
                "fiscal_year_start_month": 4,
                "output_format": "mixed",
                "language": "en",
                "suppression_threshold": 5,
            },
        )
        if not created:
            self.stdout.write(f"  Quarterly template already exists (pk={template.pk}). Skipping.")
            return

        self.stdout.write(f"  Created quarterly template (pk={template.pk})")

        # Sections
        svc_section = ReportSection.objects.create(
            report_template=template, title="Service Statistics",
            section_type="service_stats", sort_order=0,
        )
        metrics_section = ReportSection.objects.create(
            report_template=template, title="Outcome Metrics",
            section_type="metrics_table", sort_order=10,
        )
        demo_section = ReportSection.objects.create(
            report_template=template, title="Participant Demographics",
            section_type="demographic_summary", sort_order=20,
        )

        # Metrics
        for i, (name, agg, desc) in enumerate(QUARTERLY_METRICS):
            md = MetricDefinition.objects.filter(name=name, is_enabled=True).first()
            if md:
                ReportMetric.objects.create(
                    report_template=template, metric_definition=md,
                    section=metrics_section, aggregation=agg,
                    display_label=desc, sort_order=i * 10,
                    is_consortium_required=True,
                )
                self.stdout.write(f"    + Metric: {name} ({agg})")
            else:
                self.stdout.write(self.style.WARNING(f"    ! Metric not found: {name}"))

        # Age breakdown
        DemographicBreakdown.objects.create(
            report_template=template, label="Age Group",
            source_type="age", bins_json=RF_AGE_BINS, sort_order=0,
        )
        self.stdout.write("    + Age Group breakdown (6 bins)")

        # Custom field breakdowns
        self._add_demographic_breakdowns(template, start_sort=10)

    def _create_demographic_template(self, partner):
        template, created = ReportTemplate.objects.get_or_create(
            partner=partner,
            name="RF Semi-Annual Demographic Report",
            defaults={
                "description": (
                    "Semi-annual demographic report for ESDC Resilient Futures. "
                    "Covers 10 RF Social Identity constructs required for all partners."
                ),
                "period_type": "semi_annual",
                "period_alignment": "fiscal",
                "fiscal_year_start_month": 4,
                "output_format": "tabular",
                "language": "en",
                "suppression_threshold": 5,
            },
        )
        if not created:
            self.stdout.write(f"  Semi-annual template already exists (pk={template.pk}). Skipping.")
            return

        self.stdout.write(f"  Created semi-annual demographic template (pk={template.pk})")

        ReportSection.objects.create(
            report_template=template, title="RF Social Identity Demographics",
            section_type="demographic_summary", sort_order=0,
        )

        # Age breakdown
        DemographicBreakdown.objects.create(
            report_template=template, label="Age Group",
            source_type="age", bins_json=RF_AGE_BINS, sort_order=0,
        )

        # All 10 RF constructs
        self._add_demographic_breakdowns(template, start_sort=10)

    def _add_demographic_breakdowns(self, template, start_sort=0):
        for i, (label, field_name, keep_all, merge_cats) in enumerate(DEMOGRAPHIC_BREAKDOWNS):
            cf = CustomFieldDefinition.objects.filter(name=field_name).first()
            if cf:
                DemographicBreakdown.objects.create(
                    report_template=template,
                    label=label,
                    source_type="custom_field",
                    custom_field=cf,
                    keep_all_categories=keep_all,
                    merge_categories_json=merge_cats,
                    sort_order=start_sort + i * 10,
                )
                self.stdout.write(f"    + Demographic: {label}")
            else:
                self.stdout.write(self.style.WARNING(f"    ! Custom field not found: {field_name}"))
