"""Tests for RBAC middleware (program-scoped access control)."""
from django.test import TestCase, RequestFactory, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import ClientFile, ClientProgramEnrolment
from konote.middleware.program_access import ProgramAccessMiddleware
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


def dummy_response(request):
    """Simple view stand-in that returns 200."""
    from django.http import HttpResponse
    return HttpResponse("OK")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminOnlyRoutesTest(TestCase):
    """Admin-only URLs (/admin/*) should be blocked for non-admin users."""

    def setUp(self):
        enc_module._fernet = None
        self.factory = RequestFactory()
        self.middleware = ProgramAccessMiddleware(dummy_response)

        self.admin_user = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin_user.is_admin = True
        self.admin_user.save()

        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_can_access_admin_routes(self):
        request = self.factory.get("/admin/settings/")
        request.user = self.admin_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_non_admin_blocked_from_admin_routes(self):
        request = self.factory.get("/admin/settings/")
        request.user = self.staff_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_passes_through(self):
        """Unauthenticated requests are not checked (login page handles redirect)."""
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get("/admin/settings/")
        request.user = AnonymousUser()
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ClientAccessTest(TestCase):
    """Client URLs should enforce program-scoped access."""

    def setUp(self):
        enc_module._fernet = None
        self.factory = RequestFactory()
        self.middleware = ProgramAccessMiddleware(dummy_response)

        # Create users
        self.admin_user = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin_user.is_admin = True
        self.admin_user.save()

        self.staff_a = User.objects.create_user(
            username="staff_a", password="testpass123", display_name="Staff A"
        )
        self.staff_b = User.objects.create_user(
            username="staff_b", password="testpass123", display_name="Staff B"
        )

        # Create programs
        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")

        # Assign staff to programs
        UserProgramRole.objects.create(user=self.staff_a, program=self.program_a, role="staff")
        UserProgramRole.objects.create(user=self.staff_b, program=self.program_b, role="staff")

        # Create a client enrolled in Program A only
        self.client = ClientFile.objects.create()
        self.client.first_name = "Test"
        self.client.last_name = "Client"
        self.client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client, program=self.program_a
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_staff_with_matching_program_can_access_client(self):
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.staff_a
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_staff_without_matching_program_blocked(self):
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.staff_b
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_admin_without_program_role_blocked_from_client(self):
        """Admins without program roles cannot access client data."""
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.admin_user
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_admin_with_program_role_can_access_client(self):
        """Admins who also have a program role can access client data."""
        UserProgramRole.objects.create(
            user=self.admin_user, program=self.program_a, role="program_manager"
        )
        request = self.factory.get(f"/clients/{self.client.pk}/")
        request.user = self.admin_user
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_non_client_url_passes_through(self):
        """URLs that don't match client patterns should pass through."""
        request = self.factory.get("/programs/")
        request.user = self.staff_a
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ReceptionistFieldAccessTest(TestCase):
    """Front desk staff should only see/edit fields based on front_desk_access setting."""

    def setUp(self):
        enc_module._fernet = None

        # Create users
        self.receptionist = User.objects.create_user(
            username="receptionist", password="testpass123", display_name="Front Desk"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )

        # Create program and assign users
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(user=self.receptionist, program=self.program, role="receptionist")
        UserProgramRole.objects.create(user=self.staff_user, program=self.program, role="staff")

        # Create client
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.program)

        # Create custom field group
        from apps.clients.models import CustomFieldGroup, CustomFieldDefinition, ClientDetailValue

        self.group = CustomFieldGroup.objects.create(title="Contact Info", sort_order=1)

        # Phone field - front desk can edit
        self.phone_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Phone", input_type="text",
            front_desk_access="edit", sort_order=1,
        )
        ClientDetailValue.objects.create(
            client_file=self.client_file, field_def=self.phone_field, value="555-1234"
        )

        # Address field - front desk can view only
        self.address_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Address", input_type="text",
            front_desk_access="view", sort_order=2,
        )
        ClientDetailValue.objects.create(
            client_file=self.client_file, field_def=self.address_field, value="123 Main St"
        )

        # Case notes field - hidden from front desk
        self.notes_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Case Notes", input_type="textarea",
            front_desk_access="none", sort_order=3,
        )
        ClientDetailValue.objects.create(
            client_file=self.client_file, field_def=self.notes_field, value="Sensitive info here"
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_receptionist_sees_view_and_edit_fields(self):
        """Front desk staff see fields with access='view' or 'edit', not 'none'."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should see phone (edit access)
        self.assertContains(response, "555-1234")
        # Should see address (view access)
        self.assertContains(response, "123 Main St")
        # Should NOT see case notes (none access)
        self.assertNotContains(response, "Sensitive info here")
        self.assertNotContains(response, "Case Notes")

    def test_staff_sees_all_fields(self):
        """Staff should see all custom fields regardless of front_desk_access."""
        self.client.force_login(self.staff_user)
        response = self.client.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should see all fields
        self.assertContains(response, "555-1234")
        self.assertContains(response, "123 Main St")
        self.assertContains(response, "Sensitive info here")
        self.assertContains(response, "Case Notes")

    def test_receptionist_cannot_edit_client_basic_info(self):
        """Front desk staff should not see the Edit button for basic client info."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should NOT have edit link for basic info
        self.assertNotContains(response, f"/clients/{self.client_file.pk}/edit/")

    def test_staff_can_see_edit_button(self):
        """Staff should see the Edit button."""
        self.client.force_login(self.staff_user)
        response = self.client.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should have edit link
        self.assertContains(response, f"/clients/{self.client_file.pk}/edit/")

    def test_receptionist_blocked_from_edit_endpoint(self):
        """Front desk staff should get 403 when accessing edit endpoint directly."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/clients/{self.client_file.pk}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_receptionist_can_save_editable_fields(self):
        """Front desk staff can save fields with front_desk_access='edit'."""
        self.client.force_login(self.receptionist)
        response = self.client.post(
            f"/clients/{self.client_file.pk}/custom-fields/",
            {f"custom_{self.phone_field.pk}": "6135559999"},
        )
        # Should redirect (success), not 403
        self.assertEqual(response.status_code, 302)

        # Verify value was saved (phone validation normalises to (XXX) XXX-XXXX)
        from apps.clients.models import ClientDetailValue
        cdv = ClientDetailValue.objects.get(client_file=self.client_file, field_def=self.phone_field)
        self.assertEqual(cdv.value, "(613) 555-9999")

    def test_receptionist_cannot_save_view_only_fields(self):
        """Front desk staff cannot modify fields with front_desk_access='view'."""
        self.client.force_login(self.receptionist)
        # Try to save the address field (view-only for front desk)
        response = self.client.post(
            f"/clients/{self.client_file.pk}/custom-fields/",
            {f"custom_{self.address_field.pk}": "456 New St"},
        )
        # Should redirect but NOT save (field not in editable list)
        self.assertEqual(response.status_code, 302)

        # Verify value was NOT changed
        from apps.clients.models import ClientDetailValue
        cdv = ClientDetailValue.objects.get(client_file=self.client_file, field_def=self.address_field)
        self.assertEqual(cdv.value, "123 Main St")

    def test_receptionist_cannot_save_none_access_fields(self):
        """Front desk staff cannot modify fields with front_desk_access='none' even if they POST them."""
        self.client.force_login(self.receptionist)
        # Try to save the case notes field (hidden from front desk)
        response = self.client.post(
            f"/clients/{self.client_file.pk}/custom-fields/",
            {f"custom_{self.notes_field.pk}": "Trying to inject data"},
        )
        # Should redirect but NOT save (field not in editable list)
        self.assertEqual(response.status_code, 302)

        # Verify value was NOT changed
        from apps.clients.models import ClientDetailValue
        cdv = ClientDetailValue.objects.get(client_file=self.client_file, field_def=self.notes_field)
        self.assertEqual(cdv.value, "Sensitive info here")

    def test_receptionist_can_create_client(self):
        """Receptionist has client.create: ALLOW per permissions matrix — front desk does intake."""
        self.client.force_login(self.receptionist)
        response = self.client.get("/clients/create/")
        self.assertEqual(response.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ReceptionistNotesAccessTest(TestCase):
    """Front desk staff should be blocked from creating, editing, or cancelling notes."""

    def setUp(self):
        enc_module._fernet = None

        # Create users
        self.receptionist = User.objects.create_user(
            username="receptionist", password="testpass123", display_name="Front Desk"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )

        # Create program and assign users
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(user=self.receptionist, program=self.program, role="receptionist")
        UserProgramRole.objects.create(user=self.staff_user, program=self.program, role="staff")

        # Create client
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.program)

    def tearDown(self):
        enc_module._fernet = None

    def test_receptionist_blocked_from_note_list(self):
        """Front desk staff cannot access the notes list (requires staff role)."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/notes/client/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_note_list(self):
        """Staff can access the notes list."""
        self.client.force_login(self.staff_user)
        response = self.client.get(f"/notes/client/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_receptionist_blocked_from_quick_note_create(self):
        """Front desk staff cannot create quick notes."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/notes/client/{self.client_file.pk}/quick/")
        self.assertEqual(response.status_code, 403)

        # Also test POST
        response = self.client.post(f"/notes/client/{self.client_file.pk}/quick/", {
            "notes_text": "Test note",
        })
        self.assertEqual(response.status_code, 403)

    def test_receptionist_blocked_from_full_note_create(self):
        """Front desk staff cannot create full notes."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/notes/client/{self.client_file.pk}/new/")
        self.assertEqual(response.status_code, 403)

    def test_receptionist_blocked_from_note_cancel(self):
        """Front desk staff cannot cancel notes."""
        # First create a note as staff
        from apps.notes.models import ProgressNote
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            author=self.staff_user,
            author_program=self.program,
            note_type="quick",
            notes_text="A test note",
        )

        # Front desk tries to cancel
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/notes/{note.pk}/cancel/")
        self.assertEqual(response.status_code, 403)

        # Also test POST
        response = self.client.post(f"/notes/{note.pk}/cancel/", {
            "cancel_reason": "Testing",
        })
        self.assertEqual(response.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ReceptionistPlansAccessTest(TestCase):
    """Plan access tests: staff has plan.edit: SCOPED, all other roles have plan.edit: DENY.

    Receptionist also has plan.view: DENY, so cannot even view plans.
    Program manager has plan.view: ALLOW but plan.edit: DENY.
    """

    def setUp(self):
        enc_module._fernet = None

        # Create users
        self.receptionist = User.objects.create_user(
            username="receptionist", password="testpass123", display_name="Front Desk"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )
        self.manager = User.objects.create_user(
            username="manager", password="testpass123", display_name="Manager"
        )

        # Create program and assign users
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(user=self.receptionist, program=self.program, role="receptionist")
        UserProgramRole.objects.create(user=self.staff_user, program=self.program, role="staff")
        UserProgramRole.objects.create(user=self.manager, program=self.program, role="program_manager")

        # Create client
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.program)

    def tearDown(self):
        enc_module._fernet = None

    def test_receptionist_blocked_from_plan_view(self):
        """Receptionist has plan.view: DENY per permissions matrix — cannot view plans."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/plans/client/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 403)

    def test_receptionist_blocked_from_section_create(self):
        """Receptionist has plan.edit: DENY per permissions matrix."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/plans/client/{self.client_file.pk}/sections/create/")
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_section(self):
        """Staff has plan.edit: SCOPED per permissions matrix — can create sections."""
        self.client.force_login(self.staff_user)
        response = self.client.get(f"/plans/client/{self.client_file.pk}/sections/create/")
        self.assertEqual(response.status_code, 200)

    def test_manager_blocked_from_section_create(self):
        """Program manager has plan.edit: DENY per permissions matrix — cannot create sections."""
        self.client.force_login(self.manager)
        response = self.client.get(f"/plans/client/{self.client_file.pk}/sections/create/")
        self.assertEqual(response.status_code, 403)

    def test_receptionist_blocked_from_target_create(self):
        """Receptionist has plan.edit: DENY per permissions matrix — cannot create targets."""
        from apps.plans.models import PlanSection
        section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Test Section",
            program=self.program,
        )

        self.client.force_login(self.receptionist)
        response = self.client.get(f"/plans/sections/{section.pk}/targets/create/")
        self.assertEqual(response.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SensitiveFieldReceptionistAccessTest(TestCase):
    """Sensitive (encrypted) custom fields should work correctly with front desk access levels."""

    def setUp(self):
        enc_module._fernet = None

        # Create users
        self.receptionist = User.objects.create_user(
            username="receptionist", password="testpass123", display_name="Front Desk"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )

        # Create program and assign users
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(user=self.receptionist, program=self.program, role="receptionist")
        UserProgramRole.objects.create(user=self.staff_user, program=self.program, role="staff")

        # Create client
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.program)

        # Create custom field group
        from apps.clients.models import CustomFieldGroup, CustomFieldDefinition, ClientDetailValue

        self.group = CustomFieldGroup.objects.create(title="Sensitive Info", sort_order=1)

        # Sensitive field with front desk edit access (e.g., emergency contact)
        self.emergency_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Emergency Contact", input_type="text",
            front_desk_access="edit", is_sensitive=True, sort_order=1,
        )
        cdv = ClientDetailValue.objects.create(
            client_file=self.client_file, field_def=self.emergency_field,
        )
        cdv.set_value("Mom: 555-1234")
        cdv.save()

        # Sensitive field hidden from front desk (e.g., clinical assessment)
        self.assessment_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Clinical Assessment", input_type="textarea",
            front_desk_access="none", is_sensitive=True, sort_order=2,
        )
        cdv2 = ClientDetailValue.objects.create(
            client_file=self.client_file, field_def=self.assessment_field,
        )
        cdv2.set_value("Patient shows signs of improvement")
        cdv2.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_receptionist_sees_sensitive_field_with_edit_access(self):
        """Front desk staff can see sensitive fields if front_desk_access='edit'."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should see the emergency contact (decrypted)
        self.assertContains(response, "Mom: 555-1234")
        self.assertContains(response, "Emergency Contact")

    def test_receptionist_cannot_see_sensitive_field_with_none_access(self):
        """Front desk staff cannot see sensitive fields if front_desk_access='none'."""
        self.client.force_login(self.receptionist)
        response = self.client.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should NOT see the clinical assessment
        self.assertNotContains(response, "Patient shows signs of improvement")
        self.assertNotContains(response, "Clinical Assessment")

    def test_staff_sees_all_sensitive_fields(self):
        """Staff can see all sensitive fields regardless of front_desk_access."""
        self.client.force_login(self.staff_user)
        response = self.client.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should see both fields
        self.assertContains(response, "Mom: 555-1234")
        self.assertContains(response, "Patient shows signs of improvement")

    def test_receptionist_can_edit_sensitive_field_with_edit_access(self):
        """Front desk staff can edit sensitive fields if front_desk_access='edit'."""
        self.client.force_login(self.receptionist)
        response = self.client.post(
            f"/clients/{self.client_file.pk}/custom-fields/",
            {f"custom_{self.emergency_field.pk}": "Dad: 555-9999"},
        )
        self.assertEqual(response.status_code, 302)

        # Verify value was saved (and still encrypted)
        from apps.clients.models import ClientDetailValue
        cdv = ClientDetailValue.objects.get(client_file=self.client_file, field_def=self.emergency_field)
        self.assertEqual(cdv.get_value(), "Dad: 555-9999")
        # Verify it's actually encrypted (not stored in plain 'value' field)
        self.assertEqual(cdv.value, "")
        self.assertNotEqual(cdv._value_encrypted, b"")

    def test_receptionist_cannot_edit_sensitive_field_with_none_access(self):
        """Front desk staff cannot edit sensitive fields if front_desk_access='none'."""
        self.client.force_login(self.receptionist)
        response = self.client.post(
            f"/clients/{self.client_file.pk}/custom-fields/",
            {f"custom_{self.assessment_field.pk}": "Trying to modify clinical data"},
        )
        self.assertEqual(response.status_code, 302)

        # Verify value was NOT changed
        from apps.clients.models import ClientDetailValue
        cdv = ClientDetailValue.objects.get(client_file=self.client_file, field_def=self.assessment_field)
        self.assertEqual(cdv.get_value(), "Patient shows signs of improvement")
