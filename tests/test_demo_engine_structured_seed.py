"""Tests for structured attendance demo seeding in DemoDataEngine."""

import json
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.admin_settings.demo_engine import (
    DEMO_ATTENDANCE_GROUP_MARKER,
    HOUSEHOLD_RELATIONSHIP_CHILD,
    HOUSEHOLD_RELATIONSHIP_PARENT,
    HOUSEHOLD_RELATIONSHIP_PARTNER,
    DemoDataEngine,
)
from apps.circles.models import CircleMembership
from apps.field_collection.models import ProgramFieldConfig
from apps.groups.models import Group, GroupSession, GroupSessionAttendance
from apps.programs.models import Program
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=True)
class DemoEngineStructuredAttendanceSeedTest(TestCase):
    """Verify attendance groups, sessions, relationships, and pilots are seeded."""

    def setUp(self):
        enc_module._fernet = None
        for name in ("Family Program", "Caregiver Pilot", "Support Hub"):
            Program.objects.create(name=name, status="active")

    def tearDown(self):
        enc_module._fernet = None

    def _write_profile(self, profile_data):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        profile_path = Path(temp_dir.name) / "structured_profile.json"
        profile_path.write_text(json.dumps(profile_data), encoding="utf-8")
        return str(profile_path)

    def _base_profile(self):
        return {
            "description": "Test structured profile for attendance demo seeding.",
            "demo_group": "structured-test",
            "feature_toggles": {"circles": True},
            "defaults": {"days_span": 30, "note_count_range": [1, 1]},
            "locations": {
                "all_active": ["North Hub"],
                "family_locations": ["North Hub"],
            },
            "circles": {
                "generated_family_target": 1,
                "circle_seed_pool": [
                    {
                        "circle_name": "Harper Family Circle",
                        "home_location": "North Hub",
                        "active_programs": ["Family Program", "Caregiver Pilot", "Support Hub"],
                        "members": [
                            "Dana Harper (caregiver)",
                            "Chris Harper (partner)",
                            "Mason Harper (age 8)",
                            "Nora Harper (age 1)"
                        ],
                        "seed_focus": "Family attendance and caregiver pilot demo."
                    }
                ]
            },
            "attendance_seed": {
                "enabled": True,
                "programs": [
                    {
                        "program_name": "Family Program",
                        "locations_key": "family_locations",
                        "include_member_types": ["adult", "child"],
                        "primary_contact_only_for_adults": True,
                        "max_child_age": 12,
                        "sessions_per_group": 2,
                        "days_between_sessions": 7,
                        "attendance_probability": {"adult": 1.0, "child": 1.0, "default": 1.0},
                        "session_note_pool": ["Family program seeded attendance session."]
                    },
                    {
                        "program_name": "Caregiver Pilot",
                        "locations": ["North Hub"],
                        "include_member_types": ["adult"],
                        "primary_contact_only_for_adults": True,
                        "sessions_per_group": 1,
                        "days_between_sessions": 14,
                        "attendance_probability": {"adult": 1.0, "default": 1.0},
                        "session_note_pool": ["Caregiver pilot seeded attendance session."]
                    }
                ],
                "field_collection_pilots": [
                    {"program_name": "Family Program", "enabled": True, "data_tier": "standard", "profile": "group"},
                    {"program_name": "Caregiver Pilot", "enabled": True, "data_tier": "standard", "profile": "circle"}
                ]
            },
            "single_clients": []
        }

    def test_structured_seed_creates_attendance_groups_history_and_pilots(self):
        profile_path = self._write_profile(self._base_profile())
        engine = DemoDataEngine()

        success = engine.run(profile_path=profile_path, force=False)

        self.assertTrue(success)
        self.assertTrue(Group.objects.filter(name="Family Program - North Hub").exists())
        self.assertTrue(Group.objects.filter(name="Caregiver Pilot - North Hub").exists())

        family_group = Group.objects.get(name="Family Program - North Hub")
        caregiver_group = Group.objects.get(name="Caregiver Pilot - North Hub")
        self.assertIn(DEMO_ATTENDANCE_GROUP_MARKER, family_group.description)
        self.assertEqual(family_group.memberships.filter(status="active").count(), 3)
        self.assertEqual(caregiver_group.memberships.filter(status="active").count(), 1)

        self.assertEqual(GroupSession.objects.filter(group=family_group).count(), 2)
        self.assertEqual(GroupSession.objects.filter(group=caregiver_group).count(), 1)
        self.assertEqual(
            GroupSessionAttendance.objects.filter(group_session__group=family_group).count(),
            6,
        )
        self.assertEqual(
            GroupSessionAttendance.objects.filter(group_session__group=caregiver_group).count(),
            1,
        )

        family_config = ProgramFieldConfig.objects.get(program__name="Family Program")
        caregiver_config = ProgramFieldConfig.objects.get(program__name="Caregiver Pilot")
        self.assertTrue(family_config.enabled)
        self.assertEqual(family_config.profile, "group")
        self.assertEqual(caregiver_config.profile, "circle")

        relationship_labels = set(
            CircleMembership.objects.filter(client_file__is_demo=True)
            .values_list("relationship_label", flat=True)
        )
        self.assertIn(HOUSEHOLD_RELATIONSHIP_PARENT, relationship_labels)
        self.assertIn(HOUSEHOLD_RELATIONSHIP_PARTNER, relationship_labels)
        self.assertIn(HOUSEHOLD_RELATIONSHIP_CHILD, relationship_labels)
        self.assertNotIn("caregiver", relationship_labels)
        self.assertNotIn("member", relationship_labels)

    def test_cleanup_removes_seeded_groups_but_preserves_manual_groups(self):
        profile_path = self._write_profile(self._base_profile())
        engine = DemoDataEngine()
        engine.run(profile_path=profile_path, force=False)

        manual_group = Group.objects.create(
            name="Manual Group",
            group_type="group",
            program=Program.objects.get(name="Support Hub"),
            description="Real group that should not be deleted.",
        )

        engine.cleanup_demo_data()

        self.assertTrue(Group.objects.filter(pk=manual_group.pk).exists())
        self.assertFalse(
            Group.objects.filter(description__contains=DEMO_ATTENDANCE_GROUP_MARKER).exists()
        )

    def test_existing_field_collection_config_is_not_overwritten(self):
        ProgramFieldConfig.objects.create(
            program=Program.objects.get(name="Family Program"),
            enabled=False,
            data_tier="field_contact",
            profile="circle",
        )
        profile_path = self._write_profile(self._base_profile())
        engine = DemoDataEngine()

        engine.run(profile_path=profile_path, force=False)

        config = ProgramFieldConfig.objects.get(program__name="Family Program")
        self.assertFalse(config.enabled)
        self.assertEqual(config.data_tier, "field_contact")
        self.assertEqual(config.profile, "circle")