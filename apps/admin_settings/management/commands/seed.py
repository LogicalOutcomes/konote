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
        self._seed_note_templates()
        self._seed_intake_fields()
        if settings.DEMO_MODE:
            self._create_demo_users_and_clients()
            self._update_demo_client_fields()
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _seed_event_types(self):
        """Delegate to the seed_event_types command so all seeding runs in one place."""
        from django.core.management import call_command

        call_command("seed_event_types", stdout=self.stdout)

    def _seed_intake_fields(self):
        """Seed default custom fields for client intake forms."""
        from django.core.management import call_command

        call_command("seed_intake_fields", stdout=self.stdout)

    def _seed_note_templates(self):
        """Seed default note templates (Standard session, Brief check-in, etc.)."""
        from django.core.management import call_command

        call_command("seed_note_templates", stdout=self.stdout)

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
            ("groups", True),
            ("participant_portal", False),
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
            "product_name": "KoNote2",
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

    def _cleanup_old_demo_data(self):
        """Remove old demo data so it can be re-seeded cleanly.

        Safe: only deletes objects marked is_demo=True or linked to DEMO- clients.
        """
        from apps.auth_app.models import User
        from apps.clients.models import ClientDetailValue, ClientFile, ClientProgramEnrolment
        from apps.events.models import Alert, Event
        from apps.notes.models import ProgressNote
        from apps.plans.models import PlanSection, PlanTarget
        from apps.programs.models import Program, UserProgramRole

        demo_clients = ClientFile.objects.filter(
            record_id__startswith="DEMO-", is_demo=True
        )
        if not demo_clients.exists():
            return

        self.stdout.write("  Cleaning up old demo data...")
        count = demo_clients.count()

        # Delete rich data (cascades handle MetricValue, ProgressNoteTarget, etc.)
        ProgressNote.objects.filter(client_file__in=demo_clients).delete()
        PlanTarget.objects.filter(client_file__in=demo_clients).delete()
        PlanSection.objects.filter(client_file__in=demo_clients).delete()
        Event.objects.filter(client_file__in=demo_clients).delete()
        Alert.objects.filter(client_file__in=demo_clients).delete()
        ClientDetailValue.objects.filter(client_file__in=demo_clients).delete()
        ClientProgramEnrolment.objects.filter(client_file__in=demo_clients).delete()
        demo_clients.delete()

        # Remove old demo user roles and the old single-worker user
        demo_users = User.objects.filter(is_demo=True)
        UserProgramRole.objects.filter(user__in=demo_users).delete()
        # Remove old demo-worker (replaced by demo-worker-1 and demo-worker-2)
        User.objects.filter(username="demo-worker", is_demo=True).delete()

        # Remove old program names that no longer exist
        for old_name in ("Demo Program", "Youth Services"):
            Program.objects.filter(name=old_name).exclude(
                client_enrolments__isnull=False  # keep if real clients enrolled
            ).delete()

        self.stdout.write(f"  Removed {count} old demo clients and related data.")

    def _create_demo_users_and_clients(self):
        """Create demo users, 5 programs, and 15 sample clients for DEMO_MODE."""
        from apps.auth_app.models import User
        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.programs.models import Program, UserProgramRole

        # Clean up any old demo data first
        self._cleanup_old_demo_data()

        # --- 5 Programs ---
        employment, _ = Program.objects.get_or_create(
            name="Supported Employment",
            defaults={
                "description": "One-on-one job coaching, resume building, and interview preparation for adults seeking stable employment.",
                "colour_hex": "#3B82F6",
                "service_model": "individual",
                "name_fr": "Emploi accompagn\u00e9",
            },
        )
        housing, _ = Program.objects.get_or_create(
            name="Housing Stability",
            defaults={
                "description": "Case management to help adults find and maintain stable housing, including landlord mediation and referrals.",
                "colour_hex": "#F59E0B",
                "service_model": "individual",
                "name_fr": "Stabilit\u00e9 du logement",
            },
        )
        youth, _ = Program.objects.get_or_create(
            name="Youth Drop-In",
            defaults={
                "description": "Group activities, homework help, and mentorship for youth aged 13-18.",
                "colour_hex": "#10B981",
                "service_model": "both",
                "name_fr": "Centre jeunesse sans rendez-vous",
            },
        )
        newcomer, _ = Program.objects.get_or_create(
            name="Newcomer Connections",
            defaults={
                "description": "Settlement support for newcomers including service navigation, English conversation circles, and community orientation.",
                "colour_hex": "#8B5CF6",
                "service_model": "individual",
                "name_fr": "Connexions nouveaux arrivants",
            },
        )
        kitchen, _ = Program.objects.get_or_create(
            name="Community Kitchen",
            defaults={
                "description": "Weekly cooking sessions focused on affordable, healthy meals. Open to participants from any program.",
                "colour_hex": "#14B8A6",
                "service_model": "group",
                "name_fr": "Cuisine communautaire",
            },
        )

        # Ensure service_model is set on existing programs (idempotent update)
        _service_models = {
            "Supported Employment": "individual",
            "Housing Stability": "individual",
            "Youth Drop-In": "both",
            "Newcomer Connections": "individual",
            "Community Kitchen": "group",
        }
        for prog in [employment, housing, youth, newcomer, kitchen]:
            expected = _service_models.get(prog.name)
            if expected and prog.service_model != expected:
                prog.service_model = expected
                prog.save(update_fields=["service_model"])

        # Ensure French names are set on existing programs (idempotent update)
        _french_names = {
            "Supported Employment": "Emploi accompagn\u00e9",
            "Housing Stability": "Stabilit\u00e9 du logement",
            "Youth Drop-In": "Centre jeunesse sans rendez-vous",
            "Newcomer Connections": "Connexions nouveaux arrivants",
            "Community Kitchen": "Cuisine communautaire",
        }
        for prog in [employment, housing, youth, newcomer, kitchen]:
            expected_fr = _french_names.get(prog.name)
            if expected_fr and prog.name_fr != expected_fr:
                prog.name_fr = expected_fr
                prog.save(update_fields=["name_fr"])
        all_programs = [employment, housing, youth, newcomer, kitchen]

        # --- Demo Users ---
        demo_users = [
            ("demo-frontdesk", "Dana Front Desk", False),
            ("demo-worker-1", "Casey Worker", False),
            ("demo-worker-2", "Noor Worker", False),
            ("demo-manager", "Morgan Manager", False),
            ("demo-executive", "Eva Executive", False),
            ("demo-admin", "Alex Admin", True),
        ]
        for username, display_name, is_admin in demo_users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "display_name": display_name,
                    "is_admin": is_admin,
                    "is_demo": True,
                },
            )
            if created:
                user.set_password("demo1234")
                user.save()

        front_desk = User.objects.get(username="demo-frontdesk")
        worker1 = User.objects.get(username="demo-worker-1")
        worker2 = User.objects.get(username="demo-worker-2")
        manager = User.objects.get(username="demo-manager")
        executive = User.objects.get(username="demo-executive")

        # --- Program Roles ---
        # Front Desk: receptionist on all 5 programs
        for prog in all_programs:
            UserProgramRole.objects.get_or_create(
                user=front_desk, program=prog,
                defaults={"role": "receptionist"},
            )

        # Casey (worker-1): program_manager for Employment, staff for Housing + Kitchen
        # Mixed roles demonstrate how the same person sees different things per program
        UserProgramRole.objects.get_or_create(
            user=worker1, program=employment,
            defaults={"role": "program_manager"},
        )
        for prog in (housing, kitchen):
            UserProgramRole.objects.get_or_create(
                user=worker1, program=prog,
                defaults={"role": "staff"},
            )

        # Noor (worker-2): group programs + shared Kitchen
        for prog in (youth, newcomer, kitchen):
            UserProgramRole.objects.get_or_create(
                user=worker2, program=prog,
                defaults={"role": "staff"},
            )

        # Manager: program_manager on Employment, Housing, Kitchen (not all 5)
        # Shows that even managers have program boundaries
        for prog in (employment, housing, kitchen):
            UserProgramRole.objects.get_or_create(
                user=manager, program=prog,
                defaults={"role": "program_manager"},
            )

        # Executive: executive on all 5 (dashboard only)
        for prog in all_programs:
            UserProgramRole.objects.get_or_create(
                user=executive, program=prog,
                defaults={"role": "executive"},
            )

        # --- 15 Demo Clients ---
        # (first_name, last_name, dob, record_id, program, extra_programs)
        demo_clients = [
            # Supported Employment (Casey)
            ("Jordan", "Rivera", "2000-03-15", "DEMO-001", employment, [kitchen]),
            ("Taylor", "Chen", "1995-07-22", "DEMO-002", employment, []),
            ("Avery", "Osei", "1988-11-03", "DEMO-003", employment, []),
            # Housing Stability (Casey)
            ("Sam", "Williams", "1992-06-18", "DEMO-004", housing, [kitchen]),
            ("Kai", "Dubois", "1990-04-25", "DEMO-005", housing, []),
            ("Jesse", "Morales", "1985-08-14", "DEMO-006", housing, []),
            # Youth Drop-In (Noor)
            ("Jayden", "Martinez", "2009-05-12", "DEMO-007", youth, []),
            ("Maya", "Thompson", "2008-09-28", "DEMO-008", youth, []),
            ("Zara", "Ahmed", "2009-11-03", "DEMO-009", youth, []),
            # Newcomer Connections (Noor)
            ("Amara", "Diallo", "1993-02-18", "DEMO-010", newcomer, [kitchen]),
            ("Fatima", "Hassan", "1996-03-22", "DEMO-011", newcomer, []),
            ("Carlos", "Reyes", "1991-10-05", "DEMO-012", newcomer, []),
            # Community Kitchen (Both workers)
            ("Priya", "Sharma", "1987-05-15", "DEMO-013", kitchen, []),
            ("Liam", "O'Connor", "1994-08-22", "DEMO-014", kitchen, []),
            ("Nadia", "Kovac", "1999-01-30", "DEMO-015", kitchen, []),
        ]

        for first, last, dob, record_id, primary_program, extra_programs in demo_clients:
            existing = ClientFile.objects.filter(record_id=record_id).first()
            if not existing:
                client = ClientFile()
                client.first_name = first
                client.last_name = last
                client.birth_date = dob
                client.record_id = record_id
                client.status = "active"
                client.is_demo = True
                client.save()
                # Primary program enrolment
                ClientProgramEnrolment.objects.create(
                    client_file=client, program=primary_program, status="enrolled",
                )
                # Cross-enrolments (e.g., also in Community Kitchen)
                for extra in extra_programs:
                    ClientProgramEnrolment.objects.create(
                        client_file=client, program=extra, status="enrolled",
                    )

        self.stdout.write("  Demo data: 6 users, 5 programs, 15 clients created.")
        self.stdout.write("    - Casey Worker: program_manager(Employment) + staff(Housing, Kitchen)")
        self.stdout.write("    - Noor Worker:  staff(Youth Drop-In, Newcomer, Kitchen)")
        self.stdout.write("    - Morgan Manager: program_manager(Employment, Housing, Kitchen only)")
        self.stdout.write("    - Community Kitchen is shared — both workers see Kitchen clients")
        self.stdout.write("    - 3 clients cross-enrolled in Kitchen from other programs")

        # Populate demo clients with rich data for charts and reports
        from django.core.management import call_command

        call_command("seed_demo_data", stdout=self.stdout)

    def _update_demo_client_fields(self):
        """Populate custom field values and consent for demo clients."""
        from django.core.management import call_command

        call_command("update_demo_client_fields", stdout=self.stdout)
