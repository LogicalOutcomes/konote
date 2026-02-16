"""
Management command to send automated appointment reminders.

Usage:
    python manage.py send_reminders              # Send reminders for meetings in next 36h
    python manage.py send_reminders --dry-run    # Preview without sending
    python manage.py send_reminders --hours 24   # Custom lookahead window

Intended to run as a scheduled task (e.g., hourly cron via Railway, Azure, etc.).
Finds meetings in the next N hours that haven't had a reminder sent yet,
sends via the client's preferred channel (SMS or email), and logs results.
Failed reminders are retried on subsequent runs.
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.communications.services import check_and_send_health_alert, send_reminder
from apps.events.models import Meeting

logger = logging.getLogger(__name__)

# Default lookahead window in hours.
DEFAULT_HOURS = 36


class Command(BaseCommand):
    help = (
        "Send appointment reminders for upcoming meetings. "
        "Finds scheduled meetings in the next 36 hours (configurable) "
        "that haven't been reminded yet and sends via SMS or email."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show which meetings would get reminders without actually sending.",
        )
        parser.add_argument(
            "--hours",
            type=int,
            default=DEFAULT_HOURS,
            help=f"Lookahead window in hours (default: {DEFAULT_HOURS}).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        hours = options["hours"]
        now = timezone.now()
        cutoff = now + timedelta(hours=hours)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no reminders will be sent.\n"))

        # Find meetings that need reminders:
        # - Scheduled (not cancelled/completed/no-show)
        # - In the future but within the lookahead window
        # - Not already successfully reminded
        # - Failed reminders are retried (reminder_sent=False includes failed)
        meetings = (
            Meeting.objects
            .filter(
                status="scheduled",
                reminder_sent=False,
                event__start_timestamp__gt=now,
                event__start_timestamp__lte=cutoff,
            )
            .select_related("event", "event__client_file")
            .order_by("event__start_timestamp")
        )

        total = meetings.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                f"No meetings need reminders in the next {hours} hours."
            ))
            return

        self.stdout.write(f"Found {total} meeting(s) needing reminders.\n")

        sent = 0
        failed = 0
        skipped = 0

        for meeting in meetings:
            client_file = meeting.event.client_file
            start = meeting.event.start_timestamp
            label = f"Meeting on {start.strftime('%b %d at %I:%M %p')} (ID {meeting.pk})"

            if dry_run:
                channel = getattr(client_file, "preferred_contact_method", "none")
                self.stdout.write(f"  Would remind: {label} — channel: {channel}")
                skipped += 1
                continue

            try:
                success, reason = send_reminder(meeting)
            except Exception:
                logger.exception("Unexpected error sending reminder for meeting %s", meeting.pk)
                success = False
                reason = "Unexpected error"

            if success:
                sent += 1
                self.stdout.write(f"  Sent: {label}")
            elif "consent" in reason.lower() or "no phone" in reason.lower() or "no email" in reason.lower():
                # Client-side issue — won't change on retry, don't count as failure
                skipped += 1
                self.stdout.write(f"  Skipped: {label} — {reason}")
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(f"  Failed: {label} — {reason}"))

        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"DRY RUN complete: {skipped} meeting(s) would be processed."
            ))
            return

        summary_parts = []
        if sent:
            summary_parts.append(f"{sent} sent")
        if skipped:
            summary_parts.append(f"{skipped} skipped (no consent/contact)")
        if failed:
            summary_parts.append(f"{failed} failed (will retry next run)")

        self.stdout.write(self.style.SUCCESS(
            f"Done: {', '.join(summary_parts)}."
        ))

        # Check system health and send admin alerts if channels are failing
        try:
            check_and_send_health_alert()
        except Exception:
            logger.exception("Error checking system health after reminder batch")
