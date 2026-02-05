"""
One-off command to populate custom field values for demo clients.

This updates existing demo data without needing to reset the database:
1. Archives youth/recreation field groups (if they exist)
2. Populates contact, emergency, and referral info for demo clients

Run with: python manage.py update_demo_client_fields
Only runs when DEMO_MODE is enabled.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.clients.models import ClientDetailValue, ClientFile, CustomFieldDefinition, CustomFieldGroup


# Field groups to archive (youth/recreation — not needed for most agencies)
GROUPS_TO_ARCHIVE = [
    "Parent/Guardian Information",
    "Health & Safety",
    "Program Consents",
]

# Custom field values for demo clients
CLIENT_CUSTOM_FIELDS = {
    "DEMO-001": {
        "Preferred Name": "Jordan",
        "Primary Phone": "(416) 555-0123",
        "Email": "jordan.rivera@example.com",
        "Preferred Contact Method": "Text message",
        "Best Time to Contact": "Afternoon (12pm-5pm)",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "Maria Rivera",
        "Emergency Contact Relationship": "Parent/Guardian",
        "Emergency Contact Phone": "(416) 555-0124",
        "Referral Source": "Community agency",
        "Referring Agency Name": "Downtown Community Health Centre",
    },
    "DEMO-002": {
        "Preferred Name": "Taylor",
        "Primary Phone": "(647) 555-0234",
        "Preferred Contact Method": "Phone call",
        "Best Time to Contact": "Morning (9am-12pm)",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "Alex Chen",
        "Emergency Contact Relationship": "Friend",
        "Emergency Contact Phone": "(647) 555-0235",
        "Referral Source": "Shelter/Housing provider",
        "Referring Agency Name": "Covenant House",
        "Accommodation Needs": "Prefers written appointment reminders",
    },
    "DEMO-003": {
        "Preferred Name": "Avery",
        "Primary Phone": "(905) 555-0345",
        "Email": "avery.j@example.com",
        "Preferred Contact Method": "Email",
        "Best Time to Contact": "Any time",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "Jamie Johnson",
        "Emergency Contact Relationship": "Sibling",
        "Emergency Contact Phone": "(905) 555-0346",
        "Referral Source": "Hospital/Health provider",
        "Referring Agency Name": "CAMH",
    },
    "DEMO-004": {
        "Primary Phone": "(416) 555-0456",
        "Preferred Contact Method": "Text message",
        "Best Time to Contact": "Evening (5pm-8pm)",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "Priya Patel",
        "Emergency Contact Relationship": "Parent/Guardian",
        "Emergency Contact Phone": "(416) 555-0457",
        "Referral Source": "School/Education",
        "Referring Agency Name": "Toronto District School Board",
    },
    "DEMO-005": {
        "Preferred Name": "Sam",
        "Primary Phone": "(647) 555-0567",
        "Email": "sam.williams@example.com",
        "Preferred Contact Method": "Email",
        "Best Time to Contact": "Any time",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "Drew Williams",
        "Emergency Contact Relationship": "Spouse/Partner",
        "Emergency Contact Phone": "(647) 555-0568",
        "Referral Source": "Self-referral",
    },
    "DEMO-006": {
        "Primary Phone": "(416) 555-0678",
        "Preferred Contact Method": "Text message",
        "Best Time to Contact": "Afternoon (12pm-5pm)",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "Rosa Martinez",
        "Emergency Contact Relationship": "Parent/Guardian",
        "Emergency Contact Phone": "(416) 555-0679",
        "Referral Source": "School/Education",
    },
    "DEMO-007": {
        "Preferred Name": "Maya",
        "Primary Phone": "(905) 555-0789",
        "Preferred Contact Method": "Phone call",
        "Best Time to Contact": "Morning (9am-12pm)",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "David Thompson",
        "Emergency Contact Relationship": "Parent/Guardian",
        "Emergency Contact Phone": "(905) 555-0790",
        "Referral Source": "Hospital/Health provider",
        "Accommodation Needs": "Needs quiet space for meetings; social anxiety",
    },
    "DEMO-008": {
        "Primary Phone": "(647) 555-0890",
        "Preferred Contact Method": "Text message",
        "Best Time to Contact": "Evening (5pm-8pm)",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "Lisa Nguyen",
        "Emergency Contact Relationship": "Parent/Guardian",
        "Emergency Contact Phone": "(647) 555-0891",
        "Referral Source": "Social services (OW/ODSP)",
    },
    "DEMO-009": {
        "Preferred Name": "Zara",
        "Primary Phone": "(416) 555-0901",
        "Email": "zara.a@example.com",
        "Preferred Contact Method": "Email",
        "Best Time to Contact": "Afternoon (12pm-5pm)",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "Fatima Ahmed",
        "Emergency Contact Relationship": "Parent/Guardian",
        "Emergency Contact Phone": "(416) 555-0902",
        "Referral Source": "Self-referral",
    },
    "DEMO-010": {
        "Preferred Name": "Liam",
        "Primary Phone": "(905) 555-1012",
        "Email": "liam.oconnor@example.com",
        "Preferred Contact Method": "Phone call",
        "Best Time to Contact": "Any time",
        "Preferred Language of Service": "English",
        "Emergency Contact Name": "Patrick O'Connor",
        "Emergency Contact Relationship": "Parent/Guardian",
        "Emergency Contact Phone": "(905) 555-1013",
        "Referral Source": "Community agency",
        "Referring Agency Name": "Youth Employment Services",
    },
}


class Command(BaseCommand):
    help = "Populate custom field values for demo clients (one-off migration)."

    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            self.stdout.write(self.style.WARNING("DEMO_MODE is not enabled. Skipping."))
            return

        # 1. Archive youth/recreation field groups
        archived_count = CustomFieldGroup.objects.filter(
            title__in=GROUPS_TO_ARCHIVE,
            status="active",
        ).update(status="archived")
        if archived_count:
            self.stdout.write(f"  Archived {archived_count} youth/recreation field group(s).")

        # 2. Populate custom field values for demo clients
        fields_updated = 0
        for record_id, field_values in CLIENT_CUSTOM_FIELDS.items():
            client = ClientFile.objects.filter(record_id=record_id).first()
            if not client:
                continue

            for field_name, value in field_values.items():
                try:
                    field_def = CustomFieldDefinition.objects.get(name=field_name)
                    cdv, _ = ClientDetailValue.objects.get_or_create(
                        client_file=client,
                        field_def=field_def,
                    )
                    cdv.set_value(value)
                    cdv.save()
                    fields_updated += 1
                except CustomFieldDefinition.DoesNotExist:
                    pass

        self.stdout.write(self.style.SUCCESS(f"  Updated {fields_updated} custom field values for demo clients."))
