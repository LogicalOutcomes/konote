"""Seed a default report template with standard Canadian nonprofit age groups.

Creates a single "Standard Canadian Nonprofit" profile that matches
the hardcoded DEFAULT_AGE_GROUPS that were previously baked into
funder_report.py. This ensures existing behaviour is preserved when
transitioning to the report template system.

Usage:
    python manage.py seed_default_funder_profile
"""
from django.core.management.base import BaseCommand

from apps.reports.models import DemographicBreakdown, ReportTemplate


DEFAULT_PROFILE_NAME = "Standard Canadian Nonprofit"

DEFAULT_AGE_BINS = [
    {"min": 0, "max": 12, "label": "Child (0-12)"},
    {"min": 13, "max": 17, "label": "Youth (13-17)"},
    {"min": 18, "max": 24, "label": "Young Adult (18-24)"},
    {"min": 25, "max": 64, "label": "Adult (25-64)"},
    {"min": 65, "max": 999, "label": "Senior (65+)"},
]


class Command(BaseCommand):
    help = "Create a default report template with standard Canadian nonprofit age categories."

    def handle(self, *args, **options):
        profile, created = ReportTemplate.objects.get_or_create(
            name=DEFAULT_PROFILE_NAME,
            defaults={
                "description": (
                    "Default age group categories commonly used in Canadian "
                    "nonprofit funder reports. Adjust bins or create additional "
                    "templates for funders with different requirements."
                ),
            },
        )

        if not created:
            self.stdout.write(
                self.style.WARNING(
                    f"Profile '{DEFAULT_PROFILE_NAME}' already exists (pk={profile.pk}). Skipping."
                )
            )
            return

        DemographicBreakdown.objects.create(
            report_template=profile,
            label="Age Group",
            source_type="age",
            bins_json=DEFAULT_AGE_BINS,
            sort_order=0,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created default report template '{DEFAULT_PROFILE_NAME}' "
                f"with {len(DEFAULT_AGE_BINS)} age bins."
            )
        )
