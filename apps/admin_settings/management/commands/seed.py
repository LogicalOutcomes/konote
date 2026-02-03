"""
Django management command to seed the database with default data.

Run with: python manage.py seed
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed database with metric library, default terminology, and feature toggles."

    def handle(self, *args, **options):
        self._seed_metrics()
        self._seed_feature_toggles()
        self._seed_instance_settings()
        self._seed_event_types()
        if settings.DEMO_MODE:
            self._seed_demo_data()
        self.stdout.write(self.style.SUCCESS("Seed data loaded successfully."))

    def _seed_event_types(self):
        """Delegate to the seed_event_types command so all seeding runs in one place."""
        from django.core.management import call_command

        call_command("seed_event_types", stdout=self.stdout)

    def _seed_metrics(self):
        from apps.plans.models import MetricDefinition

        seed_file = Path(__file__).resolve().parent.parent.parent.parent.parent / "seeds" / "metric_library.json"
        with open(seed_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        created = 0
        for m in metrics:
            _, was_created = MetricDefinition.objects.get_or_create(
                name=m["name"],
                defaults={
                    "definition": m["definition"],
                    "category": m["category"],
                    "is_library": True,
                    "is_enabled": True,
                    "min_value": m.get("min_value"),
                    "max_value": m.get("max_value"),
                    "unit": m.get("unit", ""),
                },
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Metrics: {created} created, {len(metrics) - created} already existed.")

    def _seed_feature_toggles(self):
        from apps.admin_settings.models import FeatureToggle

        defaults = [
            ("shift_summaries", False),
            ("client_avatar", False),
            ("programs", True),
            ("plan_export_to_word", False),
            ("events", True),
            ("alerts", True),
            ("quick_notes", True),
            ("analysis_charts", True),
            ("ai_assist", False),
        ]
        created = 0
        for key, enabled in defaults:
            _, was_created = FeatureToggle.objects.get_or_create(
                feature_key=key, defaults={"is_enabled": enabled}
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Feature toggles: {created} created.")

    def _seed_instance_settings(self):
        from apps.admin_settings.models import InstanceSetting

        defaults = {
            "product_name": "KoNote",
            "logo_url": "",
            "date_format": "YYYY-MM-DD",
            "time_format": "h:mma",
            "timestamp_format": "MMM D, YYYY - h:mma",
            "session_timeout_minutes": "30",
            "print_header": "",
            "print_footer": "CONFIDENTIAL",
            "default_client_tab": "notes",
        }
        created = 0
        for key, value in defaults.items():
            _, was_created = InstanceSetting.objects.get_or_create(
                setting_key=key, defaults={"setting_value": value}
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Instance settings: {created} created.")

    def _seed_demo_data(self):
        """Create demo users, a demo program, and sample clients when DEMO_MODE is on."""
        from apps.auth_app.models import User
        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.programs.models import Program, UserProgramRole

        # Create demo program
        program, _ = Program.objects.get_or_create(
            name="Demo Program",
            defaults={"description": "A sample program for exploring KoNote.", "colour_hex": "#6366F1"},
        )

        # Demo users: (username, display_name, role, is_admin)
        demo_users = [
            ("demo-receptionist", "Dana Receptionist", "receptionist", False),
            ("demo-counsellor", "Casey Counsellor", "staff", False),
            ("demo-manager", "Morgan Manager", "program_manager", False),
            ("demo-admin", "Alex Admin", None, True),
        ]

        for username, display_name, role, is_admin in demo_users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "display_name": display_name,
                    "is_admin": is_admin,
                },
            )
            if created:
                user.set_password("demo1234")
                user.save()
            # Assign program role (non-admin users)
            if role:
                UserProgramRole.objects.get_or_create(
                    user=user, program=program,
                    defaults={"role": role},
                )

        # Create sample clients
        sample_clients = [
            ("Jordan", "Rivera", "2000-03-15", "DEMO-001"),
            ("Taylor", "Chen", "1995-07-22", "DEMO-002"),
            ("Avery", "Johnson", "1988-11-03", "DEMO-003"),
            ("Riley", "Patel", "2001-01-09", "DEMO-004"),
            ("Sam", "Williams", "1992-06-18", "DEMO-005"),
        ]

        for first, last, dob, record_id in sample_clients:
            existing = ClientFile.objects.filter(record_id=record_id).first()
            if not existing:
                client = ClientFile()
                client.first_name = first
                client.last_name = last
                client.birth_date = dob
                client.record_id = record_id
                client.status = "active"
                client.save()
                ClientProgramEnrolment.objects.create(
                    client_file=client, program=program, status="enrolled",
                )

        self.stdout.write("  Demo data: users, program, and sample clients created.")
