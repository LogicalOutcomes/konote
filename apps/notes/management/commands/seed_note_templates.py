"""Seed default note templates for progress notes."""
from django.core.management.base import BaseCommand

from apps.notes.models import ProgressNoteTemplate, ProgressNoteTemplateSection


# Default templates with their sections
# Section types: "basic" = free text, "plan" = plan targets with metrics
DEFAULTS = [
    {
        "name": "Standard session",
        "sections": [
            {"name": "Session summary", "section_type": "basic", "sort_order": 1},
            {"name": "Plan progress", "section_type": "plan", "sort_order": 2},
            {"name": "Next steps", "section_type": "basic", "sort_order": 3},
        ],
    },
    {
        "name": "Brief check-in",
        "sections": [
            {"name": "Update", "section_type": "basic", "sort_order": 1},
            {"name": "Plan progress", "section_type": "plan", "sort_order": 2},
        ],
    },
    {
        "name": "Phone/text contact",
        "sections": [
            {"name": "Contact summary", "section_type": "basic", "sort_order": 1},
            {"name": "Plan progress", "section_type": "plan", "sort_order": 2},
            {"name": "Follow-up needed", "section_type": "basic", "sort_order": 3},
        ],
    },
    {
        "name": "Crisis intervention",
        "sections": [
            {"name": "Safety assessment", "section_type": "basic", "sort_order": 1},
            {"name": "Immediate actions", "section_type": "basic", "sort_order": 2},
            {"name": "Follow-up plan", "section_type": "basic", "sort_order": 3},
        ],
    },
    {
        "name": "Intake assessment",
        "sections": [
            {"name": "Background", "section_type": "basic", "sort_order": 1},
            {"name": "Initial goals discussion", "section_type": "basic", "sort_order": 2},
            {"name": "Service plan overview", "section_type": "basic", "sort_order": 3},
        ],
    },
    {
        "name": "Case closing",
        "sections": [
            {"name": "Services provided summary", "section_type": "basic", "sort_order": 1},
            {"name": "Outcomes achieved", "section_type": "plan", "sort_order": 2},
            {"name": "Referrals made", "section_type": "basic", "sort_order": 3},
            {"name": "Closure reason", "section_type": "basic", "sort_order": 4},
        ],
    },
]


class Command(BaseCommand):
    help = "Create default note templates (Standard session, Brief check-in, etc.)."

    def handle(self, *args, **options):
        created_count = 0
        for item in DEFAULTS:
            template, created = ProgressNoteTemplate.objects.get_or_create(
                name=item["name"],
                defaults={"status": "active"},
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created template: {template.name}")
                # Create sections for new templates
                for section_data in item["sections"]:
                    ProgressNoteTemplateSection.objects.create(
                        template=template,
                        name=section_data["name"],
                        section_type=section_data["section_type"],
                        sort_order=section_data["sort_order"],
                    )
                    self.stdout.write(f"    - {section_data['name']}")
            else:
                self.stdout.write(f"  Already exists: {template.name}")
        self.stdout.write(
            self.style.SUCCESS(f"Done. {created_count} note template(s) created.")
        )
