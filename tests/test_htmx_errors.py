"""Tests for HTMX error handling and response content.

These tests verify that error responses contain meaningful content
that the frontend JavaScript can display to users.
"""
from django.test import TestCase, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import ClientFile, ClientProgramEnrolment
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class Error403ResponseTest(TestCase):
    """403 Forbidden responses should contain meaningful error messages."""

    def setUp(self):
        enc_module._fernet = None

        # Create users with different roles
        self.receptionist = User.objects.create_user(
            username="receptionist", password="testpass123", display_name="Front Desk"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )
        self.other_staff = User.objects.create_user(
            username="other_staff", password="testpass123", display_name="Other Staff"
        )

        # Create programs
        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")

        # Assign users to programs
        UserProgramRole.objects.create(user=self.receptionist, program=self.program_a, role="receptionist")
        UserProgramRole.objects.create(user=self.staff_user, program=self.program_a, role="staff")
        UserProgramRole.objects.create(user=self.other_staff, program=self.program_b, role="staff")

        # Create client in Program A only
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.program_a)

    def tearDown(self):
        enc_module._fernet = None

    def test_403_contains_access_denied_message(self):
        """403 responses should contain friendly access message."""
        # Receptionist has client.create ALLOW but client.edit DENY
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/clients/{self.client_file.pk}/edit/")
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "have access to this page", status_code=403)

    def test_403_contains_helpful_instructions(self):
        """403 responses should contain helpful next steps."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/clients/{self.client_file.pk}/edit/")
        self.assertEqual(response.status_code, 403)
        # Should contain suggestions for what user can do
        self.assertContains(response, "What you can do", status_code=403)

    def test_403_for_wrong_program_contains_message(self):
        """403 for accessing client in wrong program should have error content."""
        # other_staff is in Program B, client is in Program A
        self.client.force_login(self.other_staff)
        response = self.client.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "have access to this page", status_code=403)

    def test_403_htmx_request_returns_error_content(self):
        """HTMX requests should still get meaningful error content."""
        self.client.force_login(self.receptionist)
        response = self.client.get(
            f"/clients/{self.client_file.pk}/edit/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 403)
        # Even HTMX requests should get some error content
        self.assertTrue(len(response.content) > 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FormValidationErrorTest(TestCase):
    """Form validation errors should be returned with the form re-rendered."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(user=self.staff_user, program=self.program, role="staff")

        # Create client for testing
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.program)

    def tearDown(self):
        enc_module._fernet = None

    def test_client_create_missing_required_fields_shows_form(self):
        """Submitting client form without required fields should re-render form with errors."""
        self.client.force_login(self.staff_user)
        response = self.client.post("/clients/create/", {
            # Missing first_name and last_name (required)
            "status": "active",
        })
        # Should return 200 with form (not redirect)
        self.assertEqual(response.status_code, 200)
        # Should contain form elements
        self.assertContains(response, "form")
        # Should indicate required field error
        self.assertContains(response, "required")

    def test_client_create_valid_data_redirects(self):
        """Submitting valid client form should redirect (success)."""
        self.client.force_login(self.staff_user)
        response = self.client.post("/clients/create/", {
            "first_name": "New",
            "last_name": "Client",
            "status": "active",
            "preferred_language": "en",
            "programs": [self.program.pk],
        })
        # Should redirect to client detail
        self.assertEqual(response.status_code, 302)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class HTMXPartialResponseTest(TestCase):
    """HTMX requests should receive appropriate partial responses."""

    def setUp(self):
        enc_module._fernet = None

        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(user=self.staff_user, program=self.program, role="staff")

        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.program)

    def tearDown(self):
        enc_module._fernet = None

    def test_client_list_htmx_returns_partial(self):
        """Client list HTMX request should return table partial, not full page."""
        self.client.force_login(self.staff_user)
        response = self.client.get(
            "/clients/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        # Should NOT contain full page structure
        self.assertNotContains(response, "<!DOCTYPE html>")
        self.assertNotContains(response, "<html")

    def test_client_list_normal_returns_full_page(self):
        """Normal client list request should return full page."""
        self.client.force_login(self.staff_user)
        response = self.client.get("/clients/")
        self.assertEqual(response.status_code, 200)
        # Should contain full page structure
        self.assertContains(response, "<!DOCTYPE html>")

    def test_client_detail_htmx_returns_partial(self):
        """Client detail HTMX request should return tab partial."""
        self.client.force_login(self.staff_user)
        response = self.client.get(
            f"/clients/{self.client_file.pk}/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        # Should NOT contain full page structure
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_client_search_htmx_returns_results(self):
        """Client search HTMX request should return search results partial."""
        self.client.force_login(self.staff_user)
        response = self.client.get(
            "/clients/search/?q=Test",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        # Should contain the client name
        self.assertContains(response, "Test")

    def test_plan_view_htmx_returns_partial(self):
        """Plan view HTMX request should return plan tab partial."""
        self.client.force_login(self.staff_user)
        response = self.client.get(
            f"/plans/client/{self.client_file.pk}/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        # Should NOT contain full page structure
        self.assertNotContains(response, "<!DOCTYPE html>")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CustomFieldEditHTMXTest(TestCase):
    """Custom field editing via HTMX should handle errors gracefully."""

    def setUp(self):
        enc_module._fernet = None

        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )
        self.receptionist = User.objects.create_user(
            username="receptionist", password="testpass123", display_name="Front Desk"
        )

        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(user=self.staff_user, program=self.program, role="staff")
        UserProgramRole.objects.create(user=self.receptionist, program=self.program, role="receptionist")

        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.program)

        # Create custom fields
        from apps.clients.models import CustomFieldGroup, CustomFieldDefinition

        self.group = CustomFieldGroup.objects.create(title="Contact", sort_order=1)
        self.editable_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Phone", input_type="text",
            front_desk_access="edit", sort_order=1,
        )
        self.hidden_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Notes", input_type="textarea",
            front_desk_access="none", sort_order=2,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_receptionist_edit_mode_blocked_for_no_editable_fields(self):
        """Front desk staff with no editable fields should get 403 on edit mode."""
        # Remove the editable field, leaving only hidden
        self.editable_field.delete()

        self.client.force_login(self.receptionist)
        response = self.client.get(
            f"/clients/{self.client_file.pk}/custom-fields/edit/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_enter_edit_mode(self):
        """Staff can always enter edit mode for custom fields."""
        self.client.force_login(self.staff_user)
        response = self.client.get(
            f"/clients/{self.client_file.pk}/custom-fields/edit/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

    def test_custom_fields_save_htmx_returns_display_partial(self):
        """Saving custom fields via HTMX should return the display partial."""
        self.client.force_login(self.staff_user)
        response = self.client.post(
            f"/clients/{self.client_file.pk}/custom-fields/",
            {f"custom_{self.editable_field.pk}": "6135551234"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        # Should return the display partial (not redirect)
        # Phone validation normalises to (XXX) XXX-XXXX format
        self.assertContains(response, "(613) 555-1234")
        self.assertNotContains(response, "<!DOCTYPE html>")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminRouteErrorTest(TestCase):
    """Admin routes should return proper 403 for non-admin users."""

    def setUp(self):
        enc_module._fernet = None

        self.admin_user = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin_user.is_admin = True
        self.admin_user.save()

        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(user=self.staff_user, program=self.program, role="staff")

    def tearDown(self):
        enc_module._fernet = None

    def test_non_admin_gets_403_on_admin_routes(self):
        """Non-admin users should get 403 with error message on admin routes."""
        self.client.force_login(self.staff_user)
        response = self.client.get("/admin/settings/")
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "have access to this page", status_code=403)

    def test_admin_can_access_admin_routes(self):
        """Admin users should be able to access admin routes."""
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/settings/")
        self.assertEqual(response.status_code, 200)

    def test_non_admin_htmx_gets_403(self):
        """Non-admin HTMX requests should also get 403."""
        self.client.force_login(self.staff_user)
        response = self.client.get(
            "/admin/settings/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 403)
