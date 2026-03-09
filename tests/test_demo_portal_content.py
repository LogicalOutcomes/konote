"""Integration test for demo portal content generation.

Runs the DemoDataEngine and verifies that each portal participant
has journal entries, staff notes, messages, surveys (one completed,
one pending), and resource links.
"""
from django.test import TestCase, override_settings
from cryptography.fernet import Fernet

from apps.admin_settings.demo_engine import DemoDataEngine
from apps.programs.models import Program
from apps.plans.models import MetricDefinition, PlanTemplate, PlanTemplateSection
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DemoPortalContentTest(TestCase):
    """Verify DemoDataEngine creates complete portal content."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        # Create a minimal program with a plan template and metric
        self.program = Program.objects.create(
            name="Test Coaching Program", colour_hex="#10B981", status="active",
        )
        template = PlanTemplate.objects.create(
            name="Test Template", owning_program=self.program,
        )
        PlanTemplateSection.objects.create(
            plan_template=template, name="Goals", sort_order=0,
        )
        MetricDefinition.objects.create(
            name="Progress", min_value=0, max_value=10,
        )

    def test_portal_content_created_for_all_participants(self):
        """Run demo engine and verify portal content exists."""
        from apps.portal.models import (
            ParticipantJournalEntry, ParticipantMessage,
            ParticipantUser, PortalResourceLink, StaffPortalNote,
        )
        from apps.surveys.models import SurveyAssignment

        engine = DemoDataEngine()
        result = engine.run(clients_per_program=3, days_span=90)
        self.assertTrue(result)

        participants = ParticipantUser.objects.filter(
            client_file__is_demo=True, is_active=True,
        )
        self.assertGreater(participants.count(), 0, "No portal participants created")

        for pu in participants:
            with self.subTest(participant=str(pu)):
                # Journal entries
                journals = ParticipantJournalEntry.objects.filter(
                    participant_user=pu,
                )
                self.assertGreater(
                    journals.count(), 0,
                    f"{pu} has no journal entries",
                )

                # Staff notes
                notes = StaffPortalNote.objects.filter(client_file=pu.client_file)
                self.assertGreater(
                    notes.count(), 0,
                    f"{pu} has no staff notes",
                )

                # Messages
                msgs = ParticipantMessage.objects.filter(participant_user=pu)
                self.assertGreater(
                    msgs.count(), 0,
                    f"{pu} has no messages",
                )

                # Survey assignments — at least one pending and one completed
                assignments = SurveyAssignment.objects.filter(
                    participant_user=pu,
                )
                statuses = set(assignments.values_list("status", flat=True))
                self.assertIn(
                    "pending", statuses,
                    f"{pu} has no pending survey",
                )
                self.assertIn(
                    "completed", statuses,
                    f"{pu} has no completed survey",
                )

        # Program-level resource links
        resources = PortalResourceLink.objects.filter(
            created_by__is_demo=True,
        )
        self.assertGreater(
            resources.count(), 0,
            "No portal resource links created",
        )

    def test_cleanup_removes_all_portal_content(self):
        """Verify cleanup removes surveys, portal content, and resources."""
        from apps.portal.models import (
            ParticipantJournalEntry, PortalResourceLink,
        )
        from apps.surveys.models import Survey

        engine = DemoDataEngine()
        engine.run(clients_per_program=2, days_span=60)

        # Verify data exists
        self.assertGreater(
            ParticipantJournalEntry.objects.filter(
                client_file__is_demo=True
            ).count(), 0,
        )
        self.assertGreater(
            Survey.objects.filter(created_by__is_demo=True).count(), 0,
        )

        # Run cleanup
        engine.cleanup_demo_data()

        # Verify everything is gone
        self.assertEqual(
            ParticipantJournalEntry.objects.filter(
                client_file__is_demo=True
            ).count(), 0,
            "Journal entries not cleaned up",
        )
        self.assertEqual(
            Survey.objects.filter(created_by__is_demo=True).count(), 0,
            "Surveys not cleaned up",
        )
        self.assertEqual(
            PortalResourceLink.objects.filter(
                created_by__is_demo=True
            ).count(), 0,
            "Portal resources not cleaned up",
        )

    def test_force_regeneration_no_duplicates(self):
        """Running with --force twice should not create duplicate surveys."""
        from apps.surveys.models import Survey

        engine = DemoDataEngine()
        engine.run(clients_per_program=2, days_span=60)
        survey_count_1 = Survey.objects.filter(
            created_by__is_demo=True
        ).count()

        # Run again with force
        engine.run(clients_per_program=2, days_span=60, force=True)
        survey_count_2 = Survey.objects.filter(
            created_by__is_demo=True
        ).count()

        self.assertEqual(
            survey_count_1, survey_count_2,
            f"Survey count changed from {survey_count_1} to {survey_count_2} "
            f"after force regeneration — duplicates created",
        )

    def test_profile_key_validation_warns_on_typo(self):
        """Unknown profile keys should produce warnings."""
        import io
        stderr = io.StringIO()
        engine = DemoDataEngine(stderr=stderr)
        engine._validate_profile_keys({
            "description": "test",
            "programs": {},
            "portal": {
                "journal_pools": {},
                "jornal_pool": {},  # typo
            },
            "portl": {},  # typo
        })
        warnings = stderr.getvalue()
        self.assertIn("portl", warnings)
        self.assertIn("jornal_pool", warnings)
