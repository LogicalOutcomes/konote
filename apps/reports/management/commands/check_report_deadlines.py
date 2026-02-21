"""
Management command to check report schedule deadlines and send reminders.

Usage:
    python manage.py check_report_deadlines              # Process deadlines
    python manage.py check_report_deadlines --dry-run     # Preview without changes

Intended to run as a daily scheduled task (cron, Railway cron, etc.).
Stateless and idempotent — safe to run multiple times per day.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check report schedule deadlines and send email reminders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without making changes.",
        )

    def handle(self, *args, **options):
        from apps.admin_settings.models import InstanceSetting
        from apps.reports.models import ReportSchedule

        dry_run = options["dry_run"]
        now = timezone.now()
        today = now.date()

        active_schedules = ReportSchedule.objects.filter(is_active=True)

        if not active_schedules.exists():
            self.stdout.write("No active report schedules found.")
            return

        banner_count = 0
        email_count = 0

        for schedule in active_schedules:
            days_until = (schedule.due_date - today).days

            # Set banner_shown_at when within reminder window
            if days_until <= schedule.reminder_days_before:
                if schedule.banner_shown_at is None:
                    if dry_run:
                        self.stdout.write(
                            f"  [DRY RUN] Would set banner for: {schedule.name} "
                            f"(due {schedule.due_date}, {days_until} days)"
                        )
                    else:
                        schedule.banner_shown_at = now
                        schedule.save(update_fields=["banner_shown_at", "updated_at"])
                    banner_count += 1

            # Send email when within reminder window and not yet sent
            if days_until <= schedule.reminder_days_before:
                if schedule.email_sent_at is None:
                    product_name = InstanceSetting.get("product_name", "KoNote")
                    # Email field is encrypted — must use property, not values_list
                    recipients = [
                        u.email for u in schedule.notify_users.filter(is_active=True)
                        if u.email
                    ]

                    if not recipients:
                        # Fall back to admin emails
                        from apps.auth_app.models import User
                        recipients = [
                            u.email for u in User.objects.filter(
                                is_admin=True, is_active=True, is_demo=False,
                            ) if u.email
                        ]

                    if recipients:
                        if dry_run:
                            self.stdout.write(
                                f"  [DRY RUN] Would email {len(recipients)} recipient(s) "
                                f"for: {schedule.name} (due {schedule.due_date})"
                            )
                        else:
                            self._send_reminder(schedule, recipients, product_name)
                            schedule.email_sent_at = now
                            schedule.save(update_fields=["email_sent_at", "updated_at"])
                        email_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"  No email recipients for: {schedule.name}"
                        ))

        self.stdout.write(
            f"Processed {active_schedules.count()} schedule(s): "
            f"{banner_count} banner(s), {email_count} email(s)"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes made."))

    def _send_reminder(self, schedule, recipients, product_name):
        """Send a deadline reminder email for a schedule."""
        context = {
            "schedule": schedule,
            "product_name": product_name,
        }

        subject = f"{product_name} — Report due: {schedule.name}"
        text_body = render_to_string(
            "reports/email/report_deadline_reminder.txt", context,
        )
        html_body = render_to_string(
            "reports/email/report_deadline_reminder.html", context,
        )

        try:
            send_mail(
                subject=subject,
                message=text_body,
                html_message=html_body,
                from_email=None,  # Uses DEFAULT_FROM_EMAIL
                recipient_list=recipients,
            )
            self.stdout.write(self.style.SUCCESS(
                f"  Reminder sent for: {schedule.name} to {len(recipients)} recipient(s)"
            ))
        except Exception:
            logger.warning(
                "Failed to send report deadline reminder for %s",
                schedule.name,
                exc_info=True,
            )
            self.stdout.write(self.style.ERROR(
                f"  Failed to send reminder for: {schedule.name}"
            ))
