"""
Management command to send backup export reminders.

Usage:
    python manage.py send_backup_reminders              # Send if due
    python manage.py send_backup_reminders --dry-run    # Preview without sending

Intended to run as a daily scheduled task (cron, Railway cron, etc.).
Checks whether a backup reminder is due based on the configured frequency
and sends an email to the designated contact. Idempotent — safe to run
multiple times per day.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Send a backup export reminder email if one is due. "
        "Checks the configured frequency and last-sent timestamp."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without sending email or updating timestamps.",
        )

    def handle(self, *args, **options):
        from apps.admin_settings.models import InstanceSetting, OrganizationProfile

        dry_run = options["dry_run"]
        now = timezone.now()

        profile = OrganizationProfile.get_solo()

        # 1. Check if reminders are enabled
        if not profile.backup_reminder_enabled:
            self.stdout.write("Backup reminders are disabled. Nothing to do.")
            return

        # 2. Check contact email
        contact_email = profile.backup_reminder_contact_email
        if not contact_email:
            self.stdout.write(self.style.WARNING(
                "Backup reminders are enabled but no contact email is set. Skipping."
            ))
            return

        # 3. Check if enough time has passed since last reminder
        frequency_days = profile.backup_reminder_frequency_days or 90
        if profile.backup_reminder_last_sent_at:
            days_since_reminder = (now - profile.backup_reminder_last_sent_at).days
            if days_since_reminder < frequency_days:
                self.stdout.write(
                    f"Last reminder sent {days_since_reminder} day(s) ago "
                    f"(frequency: every {frequency_days} days). Not due yet."
                )
                return

        # 4. Check if enough time has passed since last export
        if profile.backup_last_exported_at:
            days_since_export = (now - profile.backup_last_exported_at).days
            if days_since_export < frequency_days:
                self.stdout.write(
                    f"Last export was {days_since_export} day(s) ago "
                    f"(frequency: every {frequency_days} days). Not due yet."
                )
                return

        # 5. Reminder is due — send it
        product_name = InstanceSetting.get("product_name", "KoNote")
        agency_name = profile.operating_name or profile.legal_name or product_name
        is_self_hosted = getattr(settings, "SELF_HOSTED", False)

        context = {
            "product_name": product_name,
            "agency_name": agency_name,
            "is_self_hosted": is_self_hosted,
        }

        subject = f"{product_name} — Backup reminder for {agency_name}"
        text_body = render_to_string("emails/backup_reminder.txt", context)
        html_body = render_to_string("emails/backup_reminder.html", context)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no email sent.\n"))
            self.stdout.write(f"  Would send to: {contact_email}")
            self.stdout.write(f"  Subject: {subject}")
            self.stdout.write(f"  Agency: {agency_name}")
            return

        try:
            send_mail(
                subject=subject,
                message=text_body,
                html_message=html_body,
                from_email=None,  # Uses DEFAULT_FROM_EMAIL
                recipient_list=[contact_email],
            )
        except Exception:
            logger.exception("Failed to send backup reminder email to %s", contact_email)
            self.stdout.write(self.style.ERROR(
                f"Failed to send backup reminder to {contact_email}. Check logs."
            ))
            return

        # 6. Update last-sent timestamp
        profile.backup_reminder_last_sent_at = now
        profile.save(update_fields=["backup_reminder_last_sent_at"])

        self.stdout.write(self.style.SUCCESS(
            f"Backup reminder sent to {contact_email}."
        ))
