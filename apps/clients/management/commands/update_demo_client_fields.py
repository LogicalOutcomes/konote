"""
Command to populate custom field values and consent for demo clients.

This updates existing demo data without needing to reset the database:
1. Archives youth/recreation field groups (if they exist)
2. Populates contact, emergency, and referral info for demo clients
3. Sets consent for demo clients that don't have it yet

Run with: python manage.py update_demo_client_fields
Only runs when DEMO_MODE is enabled.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clients.models import ClientDetailValue, ClientFile, CustomFieldDefinition, CustomFieldGroup
from seeds.demo_client_fields import CLIENT_CUSTOM_FIELDS


# Field groups to archive (youth/recreation — not needed for most agencies)
GROUPS_TO_ARCHIVE = [
    "Parent/Guardian Information",
    "Health & Safety",
    "Program Consents",
]


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
        fields_skipped = 0
        clients_missing = 0
        for record_id, field_values in CLIENT_CUSTOM_FIELDS.items():
            client = ClientFile.objects.filter(record_id=record_id).first()
            if not client:
                clients_missing += 1
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
                    fields_skipped += 1

        self.stdout.write(self.style.SUCCESS(f"  Updated {fields_updated} custom field values for demo clients."))
        if clients_missing:
            self.stdout.write(self.style.WARNING(
                f"  {clients_missing} demo client(s) not found in database. "
                "Run 'python manage.py seed' to create them."
            ))
        if fields_skipped:
            self.stdout.write(self.style.WARNING(
                f"  {fields_skipped} field(s) skipped — definitions not found. "
                "Run 'python manage.py seed' to create them."
            ))

        # 3. Set consent for demo clients that don't have it yet
        consent_updated = 0
        demo_clients = ClientFile.objects.filter(is_demo=True, consent_given_at__isnull=True)
        for client in demo_clients:
            client.consent_given_at = timezone.now()
            client.consent_type = "verbal"
            client.save(update_fields=["consent_given_at", "consent_type"])
            consent_updated += 1
        if consent_updated:
            self.stdout.write(f"  Set consent for {consent_updated} demo client(s).")

        # 4. Populate core phone/email fields and messaging consent (CASL)
        # The custom fields store "Primary Phone" and "Email" as EAV values,
        # but the ClientFile model has its own encrypted phone/email fields
        # that the messaging system uses. Set those + CASL consent flags.
        messaging_updated = 0
        today = timezone.now().date()
        for record_id, field_values in CLIENT_CUSTOM_FIELDS.items():
            client = ClientFile.objects.filter(record_id=record_id).first()
            if not client:
                continue

            changed = False
            phone = field_values.get("Primary Phone")
            email = field_values.get("Email")

            if phone and not client.phone:
                client.phone = phone
                client.sms_consent = True
                client.sms_consent_date = today
                client.consent_messaging_type = "express"
                client.preferred_contact_method = "sms"
                changed = True

            if email and not client.email:
                client.email = email
                client.email_consent = True
                client.email_consent_date = today
                changed = True
                # If both phone and email, prefer "both"
                if client.sms_consent:
                    client.preferred_contact_method = "both"
                else:
                    client.preferred_contact_method = "email"

            # Clients without email but with phone — set sms preference
            if phone and not email and not client.preferred_contact_method:
                client.preferred_contact_method = "sms"
                changed = True

            if changed:
                client.save()
                messaging_updated += 1

        if messaging_updated:
            self.stdout.write(f"  Messaging: set phone/email and consent for {messaging_updated} demo client(s).")
