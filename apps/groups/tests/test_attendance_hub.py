"""Tests for the opt-in Attendance Hub and related UI flags."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client as TestClient, TestCase
from django.urls import reverse

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.constants import ROLE_STAFF
from apps.groups.models import Group, GroupMembership
from apps.clients.models import ClientFile
from apps.programs.models import Program, UserProgramRole

User = get_user_model()


class AttendanceHubTests(TestCase):
    """Behaviour checks for the opt-in Attendance Hub."""

    databases = ["default", "audit"]

    def setUp(self):
        self.program = Program.objects.create(
            name="Youth Group", service_model="group", colour_hex="#3366FF",
        )
        self.staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role=ROLE_STAFF, status="active",
        )
        self.group = Group.objects.create(
            name="Monday Session", program=self.program, group_type="group",
        )
        self.client_file = ClientFile.objects.create(first_name="Bo", last_name="Lee")
        GroupMembership.objects.create(
            group=self.group, client_file=self.client_file, status="active",
        )
        self.client = TestClient()
        self.client.login(username="staff", password="pass")
        cache.clear()

    # ------------------------------------------------------------------
    # Feature flag gating
    # ------------------------------------------------------------------

    def test_attendance_hub_returns_404_when_flag_off(self):
        """Existing tenants should not see the attendance hub."""
        response = self.client.get(reverse("groups:attendance_hub"))
        self.assertEqual(response.status_code, 404)

    def test_attendance_hub_returns_404_when_groups_disabled(self):
        """Attendance flag without the groups parent flag still 404s."""
        FeatureToggle.objects.update_or_create(
            feature_key="attendance_navigation", defaults={"is_enabled": True},
        )
        # groups flag defaults to off
        cache.clear()

        response = self.client.get(reverse("groups:attendance_hub"))
        self.assertEqual(response.status_code, 404)

    def test_attendance_hub_renders_when_both_flags_enabled(self):
        FeatureToggle.objects.update_or_create(
            feature_key="groups", defaults={"is_enabled": True},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="attendance_navigation", defaults={"is_enabled": True},
        )
        cache.clear()

        response = self.client.get(reverse("groups:attendance_hub"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monday Session")
        self.assertContains(response, "Log Session")
        self.assertContains(response, "Attendance Report")

    def test_attendance_hub_only_shows_accessible_groups(self):
        """Groups from programs the user has no role in should not appear."""
        other_program = Program.objects.create(
            name="Other Program", service_model="group", colour_hex="#FF0000",
        )
        Group.objects.create(
            name="Secret Group", program=other_program, group_type="group",
        )
        FeatureToggle.objects.update_or_create(
            feature_key="groups", defaults={"is_enabled": True},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="attendance_navigation", defaults={"is_enabled": True},
        )
        cache.clear()

        response = self.client.get(reverse("groups:attendance_hub"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monday Session")
        self.assertNotContains(response, "Secret Group")

    # ------------------------------------------------------------------
    # Breadcrumb fallback
    # ------------------------------------------------------------------

    def test_session_log_breadcrumbs_use_groups_when_attendance_flag_off(self):
        """When attendance_navigation is off, session log breadcrumbs point to Groups."""
        FeatureToggle.objects.update_or_create(
            feature_key="groups", defaults={"is_enabled": True},
        )
        cache.clear()

        response = self.client.get(
            reverse("groups:session_log", kwargs={"group_id": self.group.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("groups:group_list"))

    def test_session_log_breadcrumbs_use_attendance_when_flag_on(self):
        """When attendance_navigation is on, session log breadcrumbs point to Attendance Hub."""
        FeatureToggle.objects.update_or_create(
            feature_key="groups", defaults={"is_enabled": True},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="attendance_navigation", defaults={"is_enabled": True},
        )
        cache.clear()

        response = self.client.get(
            reverse("groups:session_log", kwargs={"group_id": self.group.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("groups:attendance_hub"))
