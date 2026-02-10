"""
Management command to alert admins about clients past their data retention date.

Usage:
    python manage.py alert_expired_retention            # Send email to admins
    python manage.py alert_expired_retention --dry-run   # Preview without sending

Intended to run as a daily scheduled task (cron, Railway cron, etc.).
Only alerts for clients whose retention has expired AND who have NOT
already been through the erasure process.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Email admins about clients past their data retention date (PIPEDA compliance)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be sent without actually emailing.",
        )

    def handle(self, *args, **options):
        from apps.auth_app.models import User
        from apps.clients.models import ClientFile

        dry_run = options["dry_run"]
        today = timezone.now().date()

        # Find clients past retention with no completed erasure
        expired = (
            ClientFile.objects
            .filter(retention_expires__lt=today, erasure_completed_at__isnull=True)
            .exclude(erasure_requested=True)
            .order_by("retention_expires")
        )

        count = expired.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No clients past retention date. Nothing to do."))
            return

        # Build summary for the email
        expired_list = []
        for client in expired:
            days_overdue = (today - client.retention_expires).days
            expired_list.append({
                "record_id": client.record_id,
                "retention_expires": client.retention_expires.isoformat(),
                "days_overdue": days_overdue,
            })

        self.stdout.write(f"Found {count} client(s) past retention date:")
        for item in expired_list:
            self.stdout.write(
                f"  - {item['record_id']} — expired {item['retention_expires']} "
                f"({item['days_overdue']} days ago)"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN — no email sent."))
            return

        # Get admin email addresses
        admins = User.objects.filter(is_admin=True, is_active=True, is_demo=False)
        admin_emails = [u.email for u in admins if u.email]

        if not admin_emails:
            self.stdout.write(self.style.WARNING(
                "No admin email addresses found. Cannot send notification."
            ))
            return

        # Get privacy officer info if configured
        from apps.admin_settings.models import InstanceSetting
        privacy_officer_name = InstanceSetting.get("privacy_officer_name", "")
        privacy_officer_email = InstanceSetting.get("privacy_officer_email", "")
        product_name = InstanceSetting.get("product_name", "KoNote")

        context = {
            "expired_list": expired_list,
            "count": count,
            "today": today.isoformat(),
            "product_name": product_name,
            "privacy_officer_name": privacy_officer_name,
            "privacy_officer_email": privacy_officer_email,
        }

        subject = f"{product_name} — {count} client(s) past data retention date"
        text_body = render_to_string("clients/email/expired_retention_alert.txt", context)
        html_body = render_to_string("clients/email/expired_retention_alert.html", context)

        try:
            send_mail(
                subject=subject,
                message=text_body,
                html_message=html_body,
                from_email=None,  # Uses DEFAULT_FROM_EMAIL
                recipient_list=admin_emails,
            )
            self.stdout.write(self.style.SUCCESS(
                f"Notification sent to {len(admin_emails)} admin(s)."
            ))
        except Exception:
            logger.warning(
                "Failed to send retention expiry notification",
                exc_info=True,
            )
            self.stdout.write(self.style.ERROR(
                "Failed to send email. Check email configuration and logs."
            ))
