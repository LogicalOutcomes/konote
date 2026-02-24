"""Execute Tier 3 erasures that have passed their 24-hour safety window."""
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clients.erasure import execute_scheduled_tier3
from apps.clients.models import ErasureRequest

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Execute Tier 3 erasures that have passed their 24-hour scheduled execution time."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be executed without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        now = timezone.now()

        pending = ErasureRequest.objects.filter(
            status="scheduled",
            scheduled_execution_at__lte=now,
        ).select_related("client_file")

        count = 0
        for er in pending:
            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would execute {er.erasure_code} "
                    f"(scheduled for {er.scheduled_execution_at})"
                )
                count += 1
                continue

            try:
                execute_scheduled_tier3(er)
                logger.info("Erasure %s executed successfully.", er.erasure_code)
                count += 1
            except Exception:
                logger.exception("Failed to execute erasure %s", er.erasure_code)

        action = "Would execute" if dry_run else "Executed"
        self.stdout.write(self.style.SUCCESS(f"{action} {count} pending erasure(s)."))
