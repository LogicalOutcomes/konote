"""One-time migration: copy phone numbers from custom fields to ClientFile.phone.

Run after deploying the phone field migration:
    python manage.py migrate_phone_field

Safe to run multiple times — skips clients that already have a phone value.
"""
from django.core.management.base import BaseCommand

from apps.clients.models import ClientDetailValue, ClientFile
from apps.clients.validators import normalize_phone_number


class Command(BaseCommand):
    help = "Copy 'Primary Phone' custom field values into ClientFile.phone"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Find custom field definitions that look like phone fields
        phone_values = ClientDetailValue.objects.filter(
            field_def__name__icontains="phone",
            field_def__status="active",
        ).select_related("client_file", "field_def")

        migrated = 0
        skipped = 0
        errors = 0

        for cdv in phone_values:
            client = cdv.client_file
            raw_value = cdv.get_value()

            if not raw_value:
                skipped += 1
                continue

            # Skip if client already has a phone value
            if client.phone:
                skipped += 1
                continue

            try:
                normalised = normalize_phone_number(raw_value)
                if not normalised:
                    self.stderr.write(
                        f"  SKIP: Client {client.pk} — could not normalise '{raw_value}'"
                    )
                    skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f"  DRY RUN: Client {client.pk} — would set phone to '{normalised}'"
                    )
                else:
                    client.phone = normalised
                    client.save(update_fields=["_phone_encrypted"])

                migrated += 1

            except Exception as e:
                self.stderr.write(
                    f"  ERROR: Client {client.pk} — {e}"
                )
                errors += 1

        prefix = "DRY RUN — " if dry_run else ""
        self.stdout.write(
            f"\n{prefix}Phone migration complete: "
            f"{migrated} migrated, {skipped} skipped, {errors} errors."
        )
