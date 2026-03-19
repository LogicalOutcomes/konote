"""Tests for the opt-in relationship column on group rosters."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client as TestClient, TestCase
from django.urls import reverse

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.constants import ROLE_STAFF
from apps.circles.models import Circle, CircleMembership
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.groups.models import Group, GroupMembership
from apps.groups.views import _get_visible_circle_relationships
from apps.programs.models import Program, UserProgramRole

User = get_user_model()


class VisibleCircleRelationshipsTests(TestCase):
    """Unit tests for _get_visible_circle_relationships helper."""

    databases = ["default", "audit"]

    def setUp(self):
        self.program = Program.objects.create(
            name="Support", service_model="group", colour_hex="#3366FF",
        )
        self.staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role=ROLE_STAFF, status="active",
        )
        self.alice = ClientFile.objects.create(first_name="Alice", last_name="A")
        self.bob = ClientFile.objects.create(first_name="Bob", last_name="B")
        # Enrol clients so they're accessible to the staff user via program role
        ClientProgramEnrolment.objects.create(
            client_file=self.alice, program=self.program, status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.bob, program=self.program, status="active",
        )
        self.circle = Circle.objects.create(name="Family A", status="active")
        CircleMembership.objects.create(
            circle=self.circle, client_file=self.alice,
            relationship_label="Parent", status="active",
        )
        CircleMembership.objects.create(
            circle=self.circle, client_file=self.bob,
            relationship_label="Child", status="active",
        )
        cache.clear()

    def _enable_relationship_column(self):
        FeatureToggle.objects.update_or_create(
            feature_key="circles", defaults={"is_enabled": True},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="group_relationship_column", defaults={"is_enabled": True},
        )
        cache.clear()

    def test_returns_empty_when_flag_off(self):
        """No relationship data should leak when the feature flag is off."""
        from django.test import RequestFactory
        request = RequestFactory().get("/")
        request.user = self.staff

        result = _get_visible_circle_relationships(request, [self.alice.pk])
        self.assertEqual(result, {})

    def test_returns_relationships_from_visible_circles_when_flag_on(self):
        self._enable_relationship_column()
        from django.test import RequestFactory
        request = RequestFactory().get("/")
        request.user = self.staff

        result = _get_visible_circle_relationships(
            request, [self.alice.pk, self.bob.pk],
        )

        self.assertEqual(result[self.alice.pk], "Parent")
        self.assertEqual(result[self.bob.pk], "Child")

    def test_excludes_inactive_memberships(self):
        self._enable_relationship_column()
        CircleMembership.objects.filter(client_file=self.bob).update(status="inactive")

        from django.test import RequestFactory
        request = RequestFactory().get("/")
        request.user = self.staff

        result = _get_visible_circle_relationships(
            request, [self.alice.pk, self.bob.pk],
        )

        self.assertIn(self.alice.pk, result)
        self.assertNotIn(self.bob.pk, result)

    def test_returns_empty_for_empty_client_list(self):
        self._enable_relationship_column()
        from django.test import RequestFactory
        request = RequestFactory().get("/")
        request.user = self.staff

        result = _get_visible_circle_relationships(request, [])
        self.assertEqual(result, {})


class GroupDetailRelationshipColumnTests(TestCase):
    """Integration tests for relationship column visibility on group detail."""

    databases = ["default", "audit"]

    def setUp(self):
        self.program = Program.objects.create(
            name="Support", service_model="group", colour_hex="#3366FF",
        )
        self.staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role=ROLE_STAFF, status="active",
        )
        self.group = Group.objects.create(
            name="Monday", program=self.program, group_type="group",
        )
        self.alice = ClientFile.objects.create(first_name="Alice", last_name="A")
        GroupMembership.objects.create(
            group=self.group, client_file=self.alice, status="active",
        )
        self.client = TestClient()
        self.client.login(username="staff", password="pass")
        cache.clear()

    def test_relationship_column_hidden_when_flag_off(self):
        response = self.client.get(
            reverse("groups:group_detail", kwargs={"group_id": self.group.pk}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Relationship")

    def test_relationship_column_shown_when_flag_on(self):
        FeatureToggle.objects.update_or_create(
            feature_key="circles", defaults={"is_enabled": True},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="group_relationship_column", defaults={"is_enabled": True},
        )
        cache.clear()

        response = self.client.get(
            reverse("groups:group_detail", kwargs={"group_id": self.group.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Relationship")
