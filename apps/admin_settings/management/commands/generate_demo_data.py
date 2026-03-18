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
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.admin_settings.demo_engine import DemoDataEngine


class Command(BaseCommand):
    DEFAULT_PROFILE_PATH = Path("seeds/prosper_canada_demo_profile.json")

    help = (
        "Generate demo data matching the instance's current configuration. "
        "Creates demo users, clients, plans, notes, and events that reflect "
        "the actual programs, metrics, and templates configured in this instance."
    )

    def _resolve_profile_path(self, explicit_profile):
        """Return the explicit profile, a known default profile, or None."""
        if explicit_profile:
            return explicit_profile

        default_profile = Path(settings.BASE_DIR) / self.DEFAULT_PROFILE_PATH
        if default_profile.exists():
            resolved = self.DEFAULT_PROFILE_PATH.as_posix()
            self.stdout.write(f"Using default demo profile: {resolved}")
            return resolved

        return None

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
            default=20,
            help="Number of demo clients to create per program (default: 20).",
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

        profile_path = self._resolve_profile_path(options["profile"])

        success = engine.run(
            clients_per_program=options["clients_per_program"],
            days_span=options["days"],
            profile_path=profile_path,
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
