"""Batch-expire stale PortalAllianceRequest records past their expiry date.

Run periodically (e.g. daily via cron) to clean up requests that participants
never visited:

    python manage.py expire_alliance_requests
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Expire pending portal alliance requests that have passed their expiry date."

    def handle(self, *args, **options):
        from apps.portal.models import PortalAllianceRequest

        expired_count = PortalAllianceRequest.objects.filter(
            status="pending",
            expires_at__lt=timezone.now(),
        ).update(status="expired")

        self.stdout.write(
            self.style.SUCCESS(f"Expired {expired_count} stale alliance request(s).")
        )
