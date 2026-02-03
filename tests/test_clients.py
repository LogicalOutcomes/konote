"""Tests for client CRUD views and search."""
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import (
    ClientFile, ClientProgramEnrolment, CustomFieldGroup,
    CustomFieldDefinition, ClientDetailValue,
)
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ClientViewsTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        # Admin with program manager role — admins need a program role to access clients
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)
        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6")
        UserProgramRole.objects.create(user=self.staff, program=self.prog_a, role="staff")
        # Give admin access to both programs so they can see all clients
        UserProgramRole.objects.create(user=self.admin, program=self.prog_a, role="program_manager")
        UserProgramRole.objects.create(user=self.admin, program=self.prog_b, role="program_manager")

    def _create_client(self, first="Jane", last="Doe", programs=None):
        cf = ClientFile()
        cf.first_name = first
        cf.last_name = last
        cf.status = "active"
        cf.save()
        if programs:
            for p in programs:
                ClientProgramEnrolment.objects.create(client_file=cf, program=p)
        return cf

    def test_admin_sees_all_clients(self):
        self._create_client("Alice", "Smith", [self.prog_a])
        self._create_client("Bob", "Jones", [self.prog_b])
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/clients/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertContains(resp, "Bob")

    def test_staff_sees_only_own_program_clients(self):
        self._create_client("Alice", "Smith", [self.prog_a])
        self._create_client("Bob", "Jones", [self.prog_b])
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/clients/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertNotContains(resp, "Bob")

    def test_create_client(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/clients/create/", {
            "first_name": "Test",
            "last_name": "User",
            "middle_name": "",
            "birth_date": "",
            "record_id": "R001",
            "status": "active",
            "programs": [self.prog_a.pk],
        })
        self.assertEqual(resp.status_code, 302)
        cf = ClientFile.objects.last()
        self.assertEqual(cf.first_name, "Test")
        self.assertEqual(cf.last_name, "User")
        self.assertTrue(ClientProgramEnrolment.objects.filter(client_file=cf, program=self.prog_a).exists())

    def test_edit_client(self):
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post(f"/clients/{cf.pk}/edit/", {
            "first_name": "Janet",
            "last_name": "Doe",
            "middle_name": "",
            "birth_date": "",
            "record_id": "",
            "status": "active",
            "programs": [self.prog_a.pk],
        })
        self.assertEqual(resp.status_code, 302)
        cf.refresh_from_db()
        self.assertEqual(cf.first_name, "Janet")

    def test_client_detail(self):
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/clients/{cf.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jane")

    def test_search_finds_client(self):
        self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/clients/search/?q=jane")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jane")

    def test_search_respects_program_scope(self):
        self._create_client("Alice", "Smith", [self.prog_a])
        self._create_client("Bob", "Jones", [self.prog_b])
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/clients/search/?q=")
        self.assertNotContains(resp, "Bob")

    def test_search_empty_query(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/clients/search/?q=")
        self.assertEqual(resp.status_code, 200)

    def test_filter_by_status(self):
        """Filter clients by status (active/discharged)."""
        active = self._create_client("Active", "Client", [self.prog_a])
        discharged = self._create_client("Discharged", "Client", [self.prog_a])
        discharged.status = "discharged"
        discharged.save()

        self.client.login(username="staff", password="testpass123")

        # Filter to active only
        resp = self.client.get("/clients/?status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Active Client")
        self.assertNotContains(resp, "Discharged Client")

        # Filter to discharged only
        resp = self.client.get("/clients/?status=discharged")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Discharged Client")
        self.assertNotContains(resp, "Active Client")

    def test_filter_by_program(self):
        """Filter clients by program enrolment."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role="staff")
        alice = self._create_client("Alice", "Alpha", [self.prog_a])
        bob = self._create_client("Bob", "Beta", [self.prog_b])

        self.client.login(username="staff", password="testpass123")

        # Filter to Program A
        resp = self.client.get(f"/clients/?program={self.prog_a.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice Alpha")
        self.assertNotContains(resp, "Bob Beta")

        # Filter to Program B
        resp = self.client.get(f"/clients/?program={self.prog_b.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bob Beta")
        self.assertNotContains(resp, "Alice Alpha")

    def test_filter_combined_status_and_program(self):
        """Filter clients by both status and program."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role="staff")
        alice_active = self._create_client("Alice", "Active", [self.prog_a])
        alice_discharged = self._create_client("Alice", "Discharged", [self.prog_a])
        alice_discharged.status = "discharged"
        alice_discharged.save()
        bob = self._create_client("Bob", "Beta", [self.prog_b])

        self.client.login(username="staff", password="testpass123")

        # Filter to Program A + Active
        resp = self.client.get(f"/clients/?program={self.prog_a.pk}&status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice Active")
        self.assertNotContains(resp, "Alice Discharged")
        self.assertNotContains(resp, "Bob Beta")

    def test_htmx_filter_returns_partial(self):
        """HTMX requests should return only the table partial."""
        self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/clients/?status=active", HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        # Should NOT contain page structure elements (no extends base.html)
        self.assertNotContains(resp, "<!DOCTYPE")
        # Should contain table content
        self.assertContains(resp, "Jane Doe")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CustomFieldTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        # Admin needs a program role to access client data
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.admin, program=self.program, role="program_manager")

    def test_custom_field_admin_requires_admin(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/clients/admin/fields/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_view_custom_field_admin(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/clients/admin/fields/")
        self.assertEqual(resp.status_code, 200)

    def test_save_custom_field_value(self):
        self.client.login(username="admin", password="testpass123")
        group = CustomFieldGroup.objects.create(title="Demographics")
        field_def = CustomFieldDefinition.objects.create(
            group=group, name="Pronoun", input_type="text"
        )
        cf = ClientFile()
        cf.first_name = "Jane"
        cf.last_name = "Doe"
        cf.save()
        # Enrol client in program so admin has access
        ClientProgramEnrolment.objects.create(client_file=cf, program=self.program)
        resp = self.client.post(f"/clients/{cf.pk}/custom-fields/", {
            f"custom_{field_def.pk}": "she/her",
        })
        self.assertEqual(resp.status_code, 302)
        cdv = ClientDetailValue.objects.get(client_file=cf, field_def=field_def)
        self.assertEqual(cdv.get_value(), "she/her")

    def test_save_sensitive_custom_field_encrypted(self):
        self.client.login(username="admin", password="testpass123")
        group = CustomFieldGroup.objects.create(title="Contact")
        field_def = CustomFieldDefinition.objects.create(
            group=group, name="Phone", input_type="text", is_sensitive=True
        )
        cf = ClientFile()
        cf.first_name = "Jane"
        cf.last_name = "Doe"
        cf.save()
        # Enrol client in program so admin has access
        ClientProgramEnrolment.objects.create(client_file=cf, program=self.program)
        resp = self.client.post(f"/clients/{cf.pk}/custom-fields/", {
            f"custom_{field_def.pk}": "555-0100",
        })
        self.assertEqual(resp.status_code, 302)
        cdv = ClientDetailValue.objects.get(client_file=cf, field_def=field_def)
        # Value should be retrievable via get_value() (decrypted)
        self.assertEqual(cdv.get_value(), "555-0100")
        # Plain value field should be empty (stored encrypted instead)
        self.assertEqual(cdv.value, "")
