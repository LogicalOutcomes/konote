"""Aggregate published reports into consortium rollups.

Reads PublishedReport records from all active tenant schemas and
creates ConsortiumRollup snapshots in the shared schema.

Usage:
    python manage.py aggregate_consortium --consortium-id 1 \
        --period-start 2025-04-01 --period-end 2025-06-30
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.tenants.models import Consortium
from apps.tenants.rollup import aggregate_consortium


class Command(BaseCommand):
    help = "Aggregate published reports into a consortium rollup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--consortium-id", type=int, required=True,
            help="PK of the Consortium to aggregate.",
        )
        parser.add_argument(
            "--period-start", type=str, required=True,
            help="Start date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--period-end", type=str, required=True,
            help="End date (YYYY-MM-DD).",
        )

    def handle(self, *args, **options):
        consortium_id = options["consortium_id"]
        try:
            Consortium.objects.get(pk=consortium_id)
        except Consortium.DoesNotExist:
            raise CommandError(f"Consortium with id={consortium_id} does not exist.")

        try:
            period_start = date.fromisoformat(options["period_start"])
            period_end = date.fromisoformat(options["period_end"])
        except ValueError as e:
            raise CommandError(f"Invalid date format: {e}")

        self.stdout.write(
            f"Aggregating consortium #{consortium_id} "
            f"for {period_start} to {period_end}..."
        )

        rollup = aggregate_consortium(consortium_id, period_start, period_end)

        if rollup:
            self.stdout.write(self.style.SUCCESS(
                f"Rollup created: {rollup.agency_count} agencies, "
                f"{rollup.participant_count} participants."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "No published reports found for this consortium and period."
            ))
