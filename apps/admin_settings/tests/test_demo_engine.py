"""Regression tests for the demo data engine."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.admin_settings.demo_engine import DEMO_ATTENDANCE_GROUP_MARKER, DemoDataEngine, SeedAssignment
from apps.clients.models import ClientFile
from apps.groups.models import Group, GroupMembership
from apps.programs.models import Program

User = get_user_model()


class DemoAttendanceSeedingTests(TestCase):
    """Protect attendance demo rosters from stale Unknown members."""

    databases = {"default"}

    def _make_client(self, first_name, last_name, record_id):
        client = ClientFile(record_id=record_id, status="active", is_demo=True)
        client.first_name = first_name
        client.last_name = last_name
        client.save()
        return client

    def test_seed_group_memberships_prunes_blank_orphan_rows(self):
        """Reseeding should remove invalid placeholder memberships before adding clients."""
        program = Program.objects.create(name="Family Outreach", colour_hex="#123456", service_model="group")
        worker = User.objects.create_user(username="demo-worker", password="pass")
        existing_client = self._make_client("Jordan", "Rivera", "DEMO-001")
        new_client = self._make_client("Alex", "Rivera", "DEMO-002")
        group = Group.objects.create(
            name="Family Outreach - North Site",
            group_type="group",
            program=program,
            description=(
                f"{DEMO_ATTENDANCE_GROUP_MARKER} "
                "Seeded attendance roster for Family Outreach at North Site."
            ),
            status="active",
        )

        GroupMembership.objects.create(group=group, client_file=existing_client, role="member", status="active")
        GroupMembership.objects.create(group=group, member_name="", role="member", status="active")

        engine = DemoDataEngine()
        created_count = engine._seed_group_memberships(
            group,
            [
                SeedAssignment(client=existing_client, program=program, trend="stable", worker=worker),
                SeedAssignment(client=new_client, program=program, trend="stable", worker=worker),
            ],
            {},
        )

        self.assertEqual(created_count, 1)
        self.assertFalse(
            GroupMembership.objects.filter(
                group=group,
                client_file__isnull=True,
                member_name="",
            ).exists()
        )
        self.assertEqual(
            list(
                GroupMembership.objects.filter(group=group)
                .order_by("client_file_id")
                .values_list("client_file_id", flat=True)
            ),
            [existing_client.pk, new_client.pk],
        )

    def test_get_or_create_demo_attendance_group_reuses_legacy_demo_marker(self):
        """Legacy bracketed demo-attendance markers should still be treated as demo groups."""
        program = Program.objects.create(name="Family Outreach", colour_hex="#123456", service_model="group")
        legacy_group = Group.objects.create(
            name="Family Outreach - North Site",
            group_type="group",
            program=program,
            description="[Agency Demo Attendance] Seeded attendance roster for Family Outreach at North Site.",
            status="active",
        )

        engine = DemoDataEngine()
        group, created = engine._get_or_create_demo_attendance_group(
            program,
            "North Site",
            {},
        )

        self.assertFalse(created)
        self.assertEqual(group.pk, legacy_group.pk)
        legacy_group.refresh_from_db()
        self.assertIn(DEMO_ATTENDANCE_GROUP_MARKER, legacy_group.description)
