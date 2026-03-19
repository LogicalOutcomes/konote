"""Tests for the optional split Profile/Programs client-detail layout."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client as TestClient, TestCase
from django.urls import reverse

from apps.auth_app.constants import ROLE_STAFF
from apps.admin_settings.models import FeatureToggle
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import Program, UserProgramRole

User = get_user_model()


class ClientDetailProgramsTabTests(TestCase):
    """Behaviour checks for the opt-in Programs tab."""

    databases = ["default", "audit"]

    def setUp(self):
        self.program = Program.objects.create(name="Housing Support", colour_hex="#3366FF")
        self.staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(
            user=self.staff,
            program=self.program,
            role=ROLE_STAFF,
            status="active",
        )
        self.client_file = ClientFile.objects.create(first_name="Alice", last_name="Ng")
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="active",
        )
        self.client = TestClient()
        self.client.login(username="staff", password="pass")
        cache.clear()

    def test_client_detail_keeps_stock_info_tab_when_feature_off(self):
        response = self.client.get(reverse("clients:client_detail", kwargs={"client_id": self.client_file.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Info"')
        self.assertNotContains(
            response,
            reverse("clients:client_programs", kwargs={"client_id": self.client_file.pk}),
        )

    def test_programs_tab_appears_when_feature_enabled(self):
        FeatureToggle.objects.update_or_create(feature_key="programs", defaults={"is_enabled": True})
        FeatureToggle.objects.update_or_create(feature_key="client_programs_tab", defaults={"is_enabled": True})
        cache.clear()

        response = self.client.get(reverse("clients:client_detail", kwargs={"client_id": self.client_file.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Profile"')
        self.assertContains(
            response,
            reverse("clients:client_programs", kwargs={"client_id": self.client_file.pk}),
        )

    def test_client_programs_route_requires_feature_flag(self):
        response = self.client.get(reverse("clients:client_programs", kwargs={"client_id": self.client_file.pk}))
        self.assertEqual(response.status_code, 404)

    def test_client_programs_route_renders_visible_enrolments(self):
        FeatureToggle.objects.update_or_create(feature_key="programs", defaults={"is_enabled": True})
        FeatureToggle.objects.update_or_create(feature_key="client_programs_tab", defaults={"is_enabled": True})
        cache.clear()

        response = self.client.get(reverse("clients:client_programs", kwargs={"client_id": self.client_file.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Housing Support")
        self.assertContains(response, "Service Started")
        self.assertContains(response, "Episode Type")

    def test_client_programs_hx_request_returns_partial(self):
        FeatureToggle.objects.update_or_create(feature_key="programs", defaults={"is_enabled": True})
        FeatureToggle.objects.update_or_create(feature_key="client_programs_tab", defaults={"is_enabled": True})
        cache.clear()

        response = self.client.get(
            reverse("clients:client_programs", kwargs={"client_id": self.client_file.pk}),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Housing Support")
        self.assertNotContains(response, "Participant tabs")