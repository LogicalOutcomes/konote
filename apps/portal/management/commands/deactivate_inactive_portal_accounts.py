"""Deactivate participant portal accounts inactive for 90+ days.

Usage:
    python manage.py deactivate_inactive_portal_accounts
    python manage.py deactivate_inactive_portal_accounts --dry-run
    python manage.py deactivate_inactive_portal_accounts --days 60

Intended to run as a scheduled task (cron, Railway cron).
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

INACTIVITY_DAYS = 90


class Command(BaseCommand):
    help = "Deactivate portal accounts that have been inactive for 90+ days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deactivated without making changes.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=INACTIVITY_DAYS,
            help=f"Days of inactivity before deactivation (default: {INACTIVITY_DAYS}).",
        )

    def handle(self, *args, **options):
        from apps.portal.models import ParticipantUser

        dry_run = options["dry_run"]
        days = options["days"]

        if days < 1:
            self.stderr.write("--days must be a positive integer.")
            return

        cutoff = timezone.now() - timedelta(days=days)

        # Find accounts that are:
        # 1. Active
        # 2. Either: last_login before cutoff, OR never logged in and created before cutoff
        inactive = ParticipantUser.objects.filter(
            is_active=True,
        ).filter(
            Q(last_login__lt=cutoff)
            | Q(last_login__isnull=True, created_at__lt=cutoff)
        )

        count = inactive.count()

        if dry_run:
            self.stdout.write(f"Would deactivate {count} account(s) inactive for {days}+ days.")
            for account in inactive[:20]:
                self.stdout.write(f"  - {account.display_name} (last login: {account.last_login})")
            if count > 20:
                self.stdout.write(f"  (showing first 20 of {count})")
            return

        if count == 0:
            self.stdout.write("0 accounts to deactivate.")
            return

        # Capture account IDs for audit trail before bulk update
        account_ids = list(inactive.values_list("pk", flat=True)[:500])

        # Write audit log BEFORE deactivation (fail-safe: unaudited deactivation is worse)
        try:
            from apps.audit.models import AuditLog

            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=None,
                user_display="[system]",
                action="update",
                resource_type="portal_account",
                metadata={
                    "operation": "inactivity_deactivation",
                    "accounts_deactivated": count,
                    "inactivity_days": days,
                    "account_ids": [str(pk) for pk in account_ids],
                },
            )
        except Exception:
            logger.exception("Failed to write inactivity deactivation audit log")

        # Deactivate in bulk
        inactive.update(is_active=False)

        self.stdout.write(f"Deactivated {count} account(s) inactive for {days}+ days.")
