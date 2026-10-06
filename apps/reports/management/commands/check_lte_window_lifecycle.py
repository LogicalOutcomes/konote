"""Daily management command — refresh LTE request lifecycle state.

Evaluates every in-window or active LTE request, applying any
transitions that are due:

- submitted → active  (if 5 business days elapsed with no flags)
- submitted → auto_cancelled  (if population dropped below floor)
- submitted → invalidated_by_withdrawal  (if a participant withdrew)
- active    → expired  (if the 24-hour download window lapsed)

Run from cron or a scheduled task once per day (weekdays only is fine;
the view-time refresh picks up anything missed between runs).

Usage:
    python manage.py check_lte_window_lifecycle
    python manage.py check_lte_window_lifecycle --dry-run
"""

from django.core.management.base import BaseCommand

from apps.reports.lte_lifecycle import refresh_pending_requests
from apps.reports.models import LTEExportRequest


class Command(BaseCommand):
    help = "Refresh LTE request lifecycle state (activate, expire, cancel as due)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count changes without applying them.",
        )

    def handle(self, *args, **options):
        pending = LTEExportRequest.objects.filter(
            status__in=[
                LTEExportRequest.STATUS_SUBMITTED,
                LTEExportRequest.STATUS_ACTIVE,
            ],
        )
        count = pending.count()
        self.stdout.write(f"LTE: {count} pending requests to evaluate")

        if options["dry_run"]:
            for req in pending:
                self.stdout.write(
                    f"  [dry-run] #{req.pk} status={req.status} "
                    f"activates={req.effective_window_activates_at}"
                )
            return

        changed = refresh_pending_requests(requests=pending)
        self.stdout.write(self.style.SUCCESS(
            f"LTE: {changed} request(s) transitioned state"
        ))
