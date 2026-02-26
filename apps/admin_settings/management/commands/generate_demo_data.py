"""
Generate configuration-aware demo data for KoNote.

Creates demo users, clients, plans, notes, events, and other data that matches
the instance's actual configuration (programs, metrics, plan templates).

Usage:
  python manage.py generate_demo_data
  python manage.py generate_demo_data --profile seeds/demo_profile.json
  python manage.py generate_demo_data --clients-per-program 5 --days 365
  python manage.py generate_demo_data --force  # regenerate from scratch
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.admin_settings.demo_engine import DemoDataEngine


class Command(BaseCommand):
    help = (
        "Generate demo data matching the instance's current configuration. "
        "Creates demo users, clients, plans, notes, and events that reflect "
        "the actual programs, metrics, and templates configured in this instance."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            type=str,
            default="",
            help="Path to a demo data profile JSON for richer, program-specific content.",
        )
        parser.add_argument(
            "--clients-per-program",
            type=int,
            default=3,
            help="Number of demo clients to create per program (default: 3).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=180,
            help="Number of days of historical data to generate (default: 180).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing demo data and regenerate from scratch.",
        )
        parser.add_argument(
            "--demo-mode",
            action="store_true",
            help="Enable demo mode for this run (alternative to DEMO_MODE=1 env var).",
        )

    def handle(self, *args, **options):
        if not settings.DEMO_MODE and not options["demo_mode"]:
            self.stdout.write(self.style.WARNING(
                "DEMO_MODE is not enabled. Use --demo-mode flag or set DEMO_MODE=1 env var."
            ))
            return

        engine = DemoDataEngine(stdout=self.stdout, stderr=self.stderr)

        success = engine.run(
            clients_per_program=options["clients_per_program"],
            days_span=options["days"],
            profile_path=options["profile"] or None,
            force=options["force"],
        )

        if success:
            self.stdout.write(self.style.SUCCESS(
                "Configuration-aware demo data generated successfully."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "Demo data generation did not complete. Check messages above."
            ))
