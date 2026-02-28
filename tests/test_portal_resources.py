"""Tests for the portal resources feature.

Run with:
    pytest tests/test_portal_resources.py -v
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.portal.models import ClientResourceLink, ParticipantUser, PortalResourceLink
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PortalResourcesViewTests(TestCase):
    """Test the participant-facing resources page."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="res_staff", password="testpass123",
            display_name="Res Staff",
        )
        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")

        self.client_file = ClientFile.objects.create(
            record_id="RES-001", status="active",
        )
        self.client_file.first_name = "Res"
        self.client_file.last_name = "Test"
        self.client_file.save()

        # Enrol in program A only
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program_a,
            status="active",
        )

        self.participant = ParticipantUser.objects.create_participant(
            email="res@example.com",
            client_file=self.client_file,
            display_name="Res P",
            password="testpass123",
        )

        # Enable portal features
        FeatureToggle.objects.update_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="portal_resources",
            defaults={"is_enabled": True},
        )

        # Create program resources
        self.resource_a = PortalResourceLink.objects.create(
            program=self.program_a,
            title="Crisis Line",
            title_fr="Ligne de crise",
            url="https://crisis.example.com",
            description="24/7 support",
            display_order=1,
            created_by=self.staff,
        )
        self.resource_b = PortalResourceLink.objects.create(
            program=self.program_b,
            title="Program B Link",
            url="https://progb.example.com",
            display_order=1,
            created_by=self.staff,
        )

        # Create client-specific resource
        self.client_resource = ClientResourceLink.objects.create(
            client_file=self.client_file,
            title="Housing Help",
            url="https://housing.example.com",
            description="Local housing directory",
            created_by=self.staff,
        )

    def _portal_login(self):
        """Set up portal session for the test client."""
        self.client.get("/my/login/")
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.pk)
        session.save()

    def test_resources_page_shows_enrolled_program_resources(self):
        """Participant sees resources from programs they're enrolled in."""
        self._portal_login()
        response = self.client.get("/my/resources/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crisis Line")
        self.assertContains(response, "https://crisis.example.com")

    def test_resources_page_hides_other_program_resources(self):
        """Participant does NOT see resources from programs they're not in."""
        self._portal_login()
        response = self.client.get("/my/resources/")
        self.assertNotContains(response, "Program B Link")

    def test_resources_page_shows_client_resources(self):
        """Participant sees their client-specific resources."""
        self._portal_login()
        response = self.client.get("/my/resources/")
        self.assertContains(response, "Housing Help")
        self.assertContains(response, "https://housing.example.com")

    def test_resources_page_hides_inactive_resources(self):
        """Inactive resources are not shown."""
        self.resource_a.is_active = False
        self.resource_a.save()
        self._portal_login()
        response = self.client.get("/my/resources/")
        self.assertNotContains(response, "Crisis Line")

    def test_resources_page_empty_state(self):
        """Empty state shown when no resources exist."""
        PortalResourceLink.objects.all().delete()
        ClientResourceLink.objects.all().delete()
        self._portal_login()
        response = self.client.get("/my/resources/")
        self.assertEqual(response.status_code, 200)

    def test_feature_toggle_disabled_returns_404(self):
        """Resources page returns 404 when portal_resources is disabled."""
        FeatureToggle.objects.update_or_create(
            feature_key="portal_resources",
            defaults={"is_enabled": False},
        )
        self._portal_login()
        response = self.client.get("/my/resources/")
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_redirects_to_login(self):
        """Unauthenticated request redirects to portal login."""
        response = self.client.get("/my/resources/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/my/login/", response.url)

    def test_french_titles_used_for_french_participant(self):
        """French resource title shown when participant prefers French."""
        self.participant.preferred_language = "fr"
        self.participant.save()
        self._portal_login()
        response = self.client.get("/my/resources/")
        self.assertContains(response, "Ligne de crise")

    def test_english_fallback_when_french_empty(self):
        """English title used as fallback when French title is empty."""
        self.resource_a.title_fr = ""
        self.resource_a.save()
        self.participant.preferred_language = "fr"
        self.participant.save()
        self._portal_login()
        response = self.client.get("/my/resources/")
        self.assertContains(response, "Crisis Line")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StaffProgramResourceTests(TestCase):
    """Test staff views for managing program resource links."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="res_admin", password="testpass123",
            display_name="Res Admin", is_admin=True,
        )
        self.worker = User.objects.create_user(
            username="res_worker", password="testpass123",
            display_name="Res Worker",
        )
        self.program = Program.objects.create(name="Test Program")

        FeatureToggle.objects.update_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def test_admin_can_view_program_resources(self):
        """Admin can access the program resources management page."""
        self.client.login(username="res_admin", password="testpass123")
        response = self.client.get(f"/programs/{self.program.pk}/resources/")
        self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_view_program_resources(self):
        """Non-admin staff get redirected (no permission)."""
        self.client.login(username="res_worker", password="testpass123")
        response = self.client.get(f"/programs/{self.program.pk}/resources/")
        # Should redirect to login or return 403
        self.assertIn(response.status_code, [302, 403])

    def test_admin_can_create_program_resource(self):
        """Admin can create a program resource link."""
        self.client.login(username="res_admin", password="testpass123")
        response = self.client.post(
            f"/programs/{self.program.pk}/resources/",
            {
                "title": "Mental Health Info",
                "url": "https://mentalhealth.example.com",
                "description": "Information about services",
                "display_order": 1,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            PortalResourceLink.objects.filter(
                program=self.program, title="Mental Health Info",
            ).exists()
        )

    def test_admin_can_edit_program_resource(self):
        """Admin can edit an existing program resource link."""
        resource = PortalResourceLink.objects.create(
            program=self.program,
            title="Old Title",
            url="https://old.example.com",
            display_order=1,
            created_by=self.admin,
        )
        self.client.login(username="res_admin", password="testpass123")
        response = self.client.post(
            f"/programs/{self.program.pk}/resources/{resource.pk}/edit/",
            {
                "title": "New Title",
                "url": "https://new.example.com",
                "description": "",
                "display_order": 2,
            },
        )
        self.assertEqual(response.status_code, 302)
        resource.refresh_from_db()
        self.assertEqual(resource.title, "New Title")
        self.assertEqual(resource.url, "https://new.example.com")

    def test_admin_can_deactivate_program_resource(self):
        """Admin can soft-delete a program resource link."""
        resource = PortalResourceLink.objects.create(
            program=self.program,
            title="To Remove",
            url="https://remove.example.com",
            display_order=1,
            created_by=self.admin,
        )
        self.client.login(username="res_admin", password="testpass123")
        response = self.client.post(
            f"/programs/{self.program.pk}/resources/{resource.pk}/deactivate/",
        )
        self.assertEqual(response.status_code, 302)
        resource.refresh_from_db()
        self.assertFalse(resource.is_active)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StaffClientResourceTests(TestCase):
    """Test staff views for managing client resource links."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        from apps.programs.models import UserProgramRole

        self.staff = User.objects.create_user(
            username="cli_staff", password="testpass123",
            display_name="CLI Staff", is_admin=True,
        )
        self.program = Program.objects.create(name="Client Prog")
        # Admin needs a program role to pass @requires_permission("note.create")
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role="program_manager", status="active",
        )
        self.client_file = ClientFile.objects.create(
            record_id="CLI-001", status="active",
        )
        self.client_file.first_name = "Cli"
        self.client_file.last_name = "Test"
        self.client_file.save()

        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="active",
        )

        FeatureToggle.objects.update_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def test_staff_can_view_client_resources(self):
        """Staff can access the client resources management page."""
        self.client.login(username="cli_staff", password="testpass123")
        response = self.client.get(f"/participants/{self.client_file.pk}/resources/")
        self.assertEqual(response.status_code, 200)

    def test_staff_can_create_client_resource(self):
        """Staff can create a client resource link."""
        self.client.login(username="cli_staff", password="testpass123")
        response = self.client.post(
            f"/participants/{self.client_file.pk}/resources/",
            {
                "title": "Local Food Bank",
                "url": "https://foodbank.example.com",
                "description": "Weekly pickup available",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ClientResourceLink.objects.filter(
                client_file=self.client_file, title="Local Food Bank",
            ).exists()
        )

    def test_staff_can_deactivate_client_resource(self):
        """Staff can soft-delete a client resource link."""
        resource = ClientResourceLink.objects.create(
            client_file=self.client_file,
            title="To Remove",
            url="https://remove.example.com",
            created_by=self.staff,
        )
        self.client.login(username="cli_staff", password="testpass123")
        response = self.client.post(
            f"/participants/{self.client_file.pk}/resources/{resource.pk}/deactivate/",
        )
        self.assertEqual(response.status_code, 302)
        resource.refresh_from_db()
        self.assertFalse(resource.is_active)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PortalResourceModelTests(TestCase):
    """Test model methods on resource link models."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Model Prog")
        self.staff = User.objects.create_user(
            username="mod_staff", password="testpass123",
            display_name="Mod Staff",
        )

    def test_get_title_english(self):
        """get_title returns English title for English language."""
        resource = PortalResourceLink.objects.create(
            program=self.program,
            title="English Title",
            title_fr="Titre français",
            url="https://example.com",
            created_by=self.staff,
        )
        self.assertEqual(resource.get_title("en"), "English Title")

    def test_get_title_french(self):
        """get_title returns French title when available."""
        resource = PortalResourceLink.objects.create(
            program=self.program,
            title="English Title",
            title_fr="Titre français",
            url="https://example.com",
            created_by=self.staff,
        )
        self.assertEqual(resource.get_title("fr"), "Titre français")

    def test_get_title_french_fallback(self):
        """get_title falls back to English when French is empty."""
        resource = PortalResourceLink.objects.create(
            program=self.program,
            title="English Title",
            title_fr="",
            url="https://example.com",
            created_by=self.staff,
        )
        self.assertEqual(resource.get_title("fr"), "English Title")

    def test_get_description_french(self):
        """get_description returns French description when available."""
        resource = PortalResourceLink.objects.create(
            program=self.program,
            title="Test",
            url="https://example.com",
            description="English desc",
            description_fr="Description française",
            created_by=self.staff,
        )
        self.assertEqual(resource.get_description("fr"), "Description française")

    def test_str_portal_resource(self):
        """PortalResourceLink __str__ includes title and program."""
        resource = PortalResourceLink.objects.create(
            program=self.program,
            title="Test Link",
            url="https://example.com",
            created_by=self.staff,
        )
        self.assertIn("Test Link", str(resource))

    def test_str_client_resource(self):
        """ClientResourceLink __str__ includes title."""
        client_file = ClientFile.objects.create(
            record_id="STR-001", status="active",
        )
        resource = ClientResourceLink.objects.create(
            client_file=client_file,
            title="Client Link",
            url="https://example.com",
            created_by=self.staff,
        )
        self.assertIn("Client Link", str(resource))
