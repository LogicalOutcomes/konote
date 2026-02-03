"""Seed default event types."""
from django.core.management.base import BaseCommand

from apps.events.models import EventType


DEFAULTS = [
    {"name": "Intake", "description": "Client intake or admission", "colour_hex": "#22C55E"},
    {"name": "Discharge", "description": "Client discharge or exit", "colour_hex": "#6B7280"},
    {"name": "Crisis", "description": "Crisis event requiring immediate response", "colour_hex": "#EF4444"},
    {"name": "Referral", "description": "Referral to or from another service", "colour_hex": "#3B82F6"},
    {"name": "Follow-up", "description": "Scheduled follow-up contact", "colour_hex": "#14B8A6"},
]


class Command(BaseCommand):
    help = "Create default event types (Intake, Discharge, Crisis, Referral, Follow-up)."

    def handle(self, *args, **options):
        created_count = 0
        for item in DEFAULTS:
            obj, created = EventType.objects.get_or_create(
                name=item["name"],
                defaults={
                    "description": item["description"],
                    "colour_hex": item["colour_hex"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {obj.name}")
            else:
                self.stdout.write(f"  Already exists: {obj.name}")
        self.stdout.write(self.style.SUCCESS(f"Done. {created_count} event type(s) created."))
