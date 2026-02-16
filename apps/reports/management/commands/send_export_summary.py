"""
Management command to email admins a weekly summary of data export activity.

Usage:
    python manage.py send_export_summary              # Send email to admins
    python manage.py send_export_summary --dry-run     # Preview without sending
    python manage.py send_export_summary --days 14     # Custom lookback window

Intended to run as a weekly scheduled task (cron, Railway cron, etc.).
Stateless and idempotent — safe to run multiple times.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Email admins a summary of recent data export activity."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show the summary without actually emailing.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days to look back (default: 7).",
        )

    def handle(self, *args, **options):
        from apps.admin_settings.models import InstanceSetting
        from apps.auth_app.models import User
        from apps.reports.models import SecureExportLink

        dry_run = options["dry_run"]
        days = options["days"]

        now = timezone.now()
        cutoff = now - timedelta(days=days)

        # ── Query exports in the period ──────────────────────────────
        exports = SecureExportLink.objects.filter(created_at__gte=cutoff)
        total_count = exports.count()

        # Breakdown by type
        by_type = list(
            exports
            .values("export_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Add display labels for each type
        type_display = dict(SecureExportLink.EXPORT_TYPE_CHOICES)
        for item in by_type:
            item["label"] = str(type_display.get(item["export_type"], item["export_type"]))

        elevated_count = exports.filter(is_elevated=True).count()
        downloaded_count = exports.filter(download_count__gt=0).count()
        pending_count = exports.filter(download_count=0, revoked=False).count()
        revoked_count = exports.filter(revoked=True).count()

        # Top 5 exporters (by display_name since email is encrypted)
        top_exporters = list(
            exports
            .values("created_by__display_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # ── Console output ───────────────────────────────────────────
        period_start = cutoff.strftime("%Y-%m-%d")
        period_end = now.strftime("%Y-%m-%d")

        self.stdout.write(f"Export summary for {period_start} to {period_end}:")
        self.stdout.write(f"  Total exports: {total_count}")
        for item in by_type:
            self.stdout.write(f"  - {item['label']}: {item['count']}")
        self.stdout.write(f"  Elevated: {elevated_count}")
        self.stdout.write(f"  Downloaded: {downloaded_count}")
        self.stdout.write(f"  Pending: {pending_count}")
        self.stdout.write(f"  Revoked: {revoked_count}")
        if top_exporters:
            self.stdout.write("  Top exporters:")
            for exp in top_exporters:
                self.stdout.write(
                    f"    - {exp['created_by__display_name']}: {exp['count']}"
                )

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN — no email sent."))
            return

        # ── Get admin email addresses ────────────────────────────────
        admin_emails = getattr(settings, "EXPORT_NOTIFICATION_EMAILS", None)
        if not admin_emails:
            admins = User.objects.filter(is_admin=True, is_active=True, is_demo=False)
            admin_emails = [u.email for u in admins if u.email]

        if not admin_emails:
            self.stdout.write(self.style.WARNING(
                "No admin email addresses found. Cannot send summary."
            ))
            return

        # ── Build and send the email ─────────────────────────────────
        product_name = InstanceSetting.get("product_name", "KoNote")

        context = {
            "period_start": period_start,
            "period_end": period_end,
            "days": days,
            "total_count": total_count,
            "by_type": by_type,
            "elevated_count": elevated_count,
            "downloaded_count": downloaded_count,
            "pending_count": pending_count,
            "revoked_count": revoked_count,
            "top_exporters": top_exporters,
            "product_name": product_name,
        }

        subject = f"{product_name} — Export Activity Summary ({period_start} to {period_end})"
        text_body = render_to_string("reports/email/weekly_export_summary.txt", context)
        html_body = render_to_string("reports/email/weekly_export_summary.html", context)

        try:
            send_mail(
                subject=subject,
                message=text_body,
                html_message=html_body,
                from_email=None,  # Uses DEFAULT_FROM_EMAIL
                recipient_list=admin_emails,
            )
            self.stdout.write(self.style.SUCCESS(
                f"Summary sent to {len(admin_emails)} admin(s)."
            ))
        except Exception:
            logger.warning(
                "Failed to send export summary email",
                exc_info=True,
            )
            self.stdout.write(self.style.ERROR(
                "Failed to send email. Check email configuration and logs."
            ))
