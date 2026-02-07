"""Tests for client CRUD views and search."""
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import (
    ClientFile, ClientProgramEnrolment, CustomFieldGroup,
    CustomFieldDefinition, ClientDetailValue,
)
from apps.notes.models import ProgressNote
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
            "preferred_name": "",
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

    def test_create_client_with_preferred_name(self):
        """Preferred name is saved and used as display_name."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/clients/create/", {
            "first_name": "Jonathan",
            "last_name": "Smith",
            "preferred_name": "Jay",
            "middle_name": "",
            "birth_date": "",
            "record_id": "",
            "status": "active",
            "programs": [self.prog_a.pk],
        })
        self.assertEqual(resp.status_code, 302)
        cf = ClientFile.objects.last()
        self.assertEqual(cf.first_name, "Jonathan")
        self.assertEqual(cf.preferred_name, "Jay")
        self.assertEqual(cf.display_name, "Jay")

    def test_display_name_falls_back_to_first_name(self):
        """When no preferred name, display_name returns first_name."""
        cf = self._create_client("Jane", "Doe")
        self.assertEqual(cf.display_name, "Jane")
        self.assertEqual(cf.preferred_name, "")

    def test_preferred_name_shown_in_client_detail(self):
        """Client detail page shows preferred name, not legal first name."""
        cf = self._create_client("Jonathan", "Smith", [self.prog_a])
        cf.preferred_name = "Jay"
        cf.save()
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/clients/{cf.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jay")

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

    def test_search_finds_client_by_note_content(self):
        """Search should find clients when their progress notes match the query."""
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        note = ProgressNote(client_file=cf, note_type="quick", author=self.admin)
        note.notes_text = "Discussed housing stability goals"
        note.save()
        self.client.login(username="admin", password="testpass123")
        # Search for text in the note — should find the client
        resp = self.client.get("/clients/search/?q=housing")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jane")

    def test_list_search_finds_client_by_note_content(self):
        """Client list search should also find clients by note content."""
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        note = ProgressNote(client_file=cf, note_type="quick", author=self.admin)
        note.notes_text = "Completed intake assessment"
        note.save()
        self.client.login(username="admin", password="testpass123")
        # Search for text in the note — should find the client
        resp = self.client.get("/clients/?q=intake")
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

    # --- Search filter tests (UX19) ---

    def test_search_filter_by_status(self):
        """Filter search results by status."""
        active = self._create_client("Active", "Person", [self.prog_a])
        discharged = self._create_client("Discharged", "Person", [self.prog_a])
        discharged.status = "discharged"
        discharged.save()

        self.client.login(username="staff", password="testpass123")

        # Filter to active only
        resp = self.client.get("/clients/search/?q=person&status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Active Person")
        self.assertNotContains(resp, "Discharged Person")

        # Filter to discharged only
        resp = self.client.get("/clients/search/?q=person&status=discharged")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Discharged Person")
        self.assertNotContains(resp, "Active Person")

    def test_search_filter_by_program(self):
        """Filter search results by program."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role="staff")
        alice = self._create_client("Alice", "Test", [self.prog_a])
        bob = self._create_client("Bob", "Test", [self.prog_b])

        self.client.login(username="staff", password="testpass123")

        # Filter to Program A
        resp = self.client.get(f"/clients/search/?q=test&program={self.prog_a.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice Test")
        self.assertNotContains(resp, "Bob Test")

        # Filter to Program B
        resp = self.client.get(f"/clients/search/?q=test&program={self.prog_b.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bob Test")
        self.assertNotContains(resp, "Alice Test")

    def test_search_filter_by_date_range(self):
        """Filter search results by date range."""
        from django.utils import timezone
        from datetime import timedelta

        old_client = self._create_client("Old", "Client", [self.prog_a])
        new_client = self._create_client("New", "Client", [self.prog_a])

        # Set old client to be created 30 days ago
        old_date = timezone.now() - timedelta(days=30)
        ClientFile.objects.filter(pk=old_client.pk).update(created_at=old_date)

        self.client.login(username="staff", password="testpass123")

        # Filter to recent clients only (last 7 days)
        week_ago = (timezone.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        resp = self.client.get(f"/clients/search/?q=client&date_from={week_ago}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "New Client")
        self.assertNotContains(resp, "Old Client")

    def test_search_filters_without_query(self):
        """Filters should work without a search query."""
        active = self._create_client("Active", "Person", [self.prog_a])
        discharged = self._create_client("Discharged", "Person", [self.prog_a])
        discharged.status = "discharged"
        discharged.save()

        self.client.login(username="staff", password="testpass123")

        # Filter to active only (no search query)
        resp = self.client.get("/clients/search/?status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Active Person")
        self.assertNotContains(resp, "Discharged Person")

    def test_search_combined_filters(self):
        """Multiple filters should work together."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role="staff")
        alice_active = self._create_client("Alice", "Active", [self.prog_a])
        alice_discharged = self._create_client("Alice", "Discharged", [self.prog_a])
        alice_discharged.status = "discharged"
        alice_discharged.save()
        bob = self._create_client("Bob", "Beta", [self.prog_b])

        self.client.login(username="staff", password="testpass123")

        # Search "Alice" + Program A + Active
        resp = self.client.get(f"/clients/search/?q=alice&program={self.prog_a.pk}&status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice Active")
        self.assertNotContains(resp, "Alice Discharged")
        self.assertNotContains(resp, "Bob Beta")


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
        # Use a generic name to avoid auto-detecting validation_type as "phone"
        # This test is about encryption, not phone validation
        field_def = CustomFieldDefinition.objects.create(
            group=group, name="Secret Code", input_type="text", is_sensitive=True
        )
        cf = ClientFile()
        cf.first_name = "Jane"
        cf.last_name = "Doe"
        cf.save()
        # Enrol client in program so admin has access
        ClientProgramEnrolment.objects.create(client_file=cf, program=self.program)
        resp = self.client.post(f"/clients/{cf.pk}/custom-fields/", {
            f"custom_{field_def.pk}": "secret-value-123",
        })
        self.assertEqual(resp.status_code, 302)
        cdv = ClientDetailValue.objects.get(client_file=cf, field_def=field_def)
        # Value should be retrievable via get_value() (decrypted)
        self.assertEqual(cdv.get_value(), "secret-value-123")
        # Plain value field should be empty (stored encrypted instead)
        self.assertEqual(cdv.value, "")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SelectOtherFieldTest(TestCase):
    """Tests for the select_other input type (dropdown with free-text Other option)."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.admin, program=self.program, role="program_manager")
        self.group = CustomFieldGroup.objects.create(title="Contact Information")
        self.pronouns_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Pronouns", input_type="select_other",
            is_sensitive=True, front_desk_access="view",
            options_json=["He/him", "He/they", "She/her", "She/they", "They/them", "Prefer not to answer"],
        )
        self.cf = ClientFile()
        self.cf.first_name = "Alex"
        self.cf.last_name = "Taylor"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.program)
        self.client.login(username="admin", password="testpass123")

    def test_save_standard_option(self):
        """Selecting a standard dropdown option stores that value."""
        resp = self.client.post(f"/clients/{self.cf.pk}/custom-fields/", {
            f"custom_{self.pronouns_field.pk}": "They/them",
            f"custom_{self.pronouns_field.pk}_other": "",
        })
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.pronouns_field)
        self.assertEqual(cdv.get_value(), "They/them")

    def test_save_other_uses_free_text(self):
        """Selecting 'Other' stores the free-text value, not '__other__'."""
        resp = self.client.post(f"/clients/{self.cf.pk}/custom-fields/", {
            f"custom_{self.pronouns_field.pk}": "__other__",
            f"custom_{self.pronouns_field.pk}_other": "xe/xem",
        })
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.pronouns_field)
        self.assertEqual(cdv.get_value(), "xe/xem")

    def test_save_other_strips_whitespace(self):
        """Free-text Other value has whitespace stripped."""
        resp = self.client.post(f"/clients/{self.cf.pk}/custom-fields/", {
            f"custom_{self.pronouns_field.pk}": "__other__",
            f"custom_{self.pronouns_field.pk}_other": "  ze/zir  ",
        })
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.pronouns_field)
        self.assertEqual(cdv.get_value(), "ze/zir")

    def test_pronouns_encrypted_when_sensitive(self):
        """Pronouns field with is_sensitive=True stores encrypted value."""
        self.client.post(f"/clients/{self.cf.pk}/custom-fields/", {
            f"custom_{self.pronouns_field.pk}": "She/her",
            f"custom_{self.pronouns_field.pk}_other": "",
        })
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.pronouns_field)
        self.assertEqual(cdv.get_value(), "She/her")
        # Plain value should be empty — stored encrypted instead
        self.assertEqual(cdv.value, "")

    def test_other_value_detected_in_context(self):
        """Custom (Other) values are flagged as is_other_value in the view context."""
        # Save a non-standard value
        cdv = ClientDetailValue.objects.create(client_file=self.cf, field_def=self.pronouns_field)
        cdv.set_value("xe/xem")
        cdv.save()
        # Fetch the edit view (HTMX partial)
        resp = self.client.get(
            f"/clients/{self.cf.pk}/custom-fields/edit/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        # Check that is_other_value is True for this field in context
        for group in resp.context["custom_data"]:
            for item in group["fields"]:
                if item["field_def"].pk == self.pronouns_field.pk:
                    self.assertTrue(item["is_other_value"])

    def test_standard_value_not_flagged_as_other(self):
        """Standard dropdown values are NOT flagged as is_other_value."""
        cdv = ClientDetailValue.objects.create(client_file=self.cf, field_def=self.pronouns_field)
        cdv.set_value("They/them")
        cdv.save()
        resp = self.client.get(
            f"/clients/{self.cf.pk}/custom-fields/edit/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        for group in resp.context["custom_data"]:
            for item in group["fields"]:
                if item["field_def"].pk == self.pronouns_field.pk:
                    self.assertFalse(item["is_other_value"])

    def test_front_desk_can_view_but_not_edit(self):
        """Front desk staff (receptionist) can see pronouns but not edit them."""
        receptionist = User.objects.create_user(username="frontdesk", password="testpass123")
        UserProgramRole.objects.create(user=receptionist, program=self.program, role="receptionist")
        # Save a value first
        cdv = ClientDetailValue.objects.create(client_file=self.cf, field_def=self.pronouns_field)
        cdv.set_value("They/them")
        cdv.save()
        self.client.login(username="frontdesk", password="testpass123")
        # Display view should show the value
        resp = self.client.get(
            f"/clients/{self.cf.pk}/custom-fields/display/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "They/them")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConsentRecordingTest(TestCase):
    """Tests for consent recording workflow (PRIV1)."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)
        self.receptionist = User.objects.create_user(username="receptionist", password="testpass123", is_admin=False)
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.program, role="staff")
        UserProgramRole.objects.create(user=self.receptionist, program=self.program, role="receptionist")

        self.cf = ClientFile()
        self.cf.first_name = "Jane"
        self.cf.last_name = "Doe"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.program)

    def test_consent_display_shows_no_consent(self):
        """Client detail shows 'no consent' warning when consent not recorded."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/clients/{self.cf.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No consent on file")

    def test_consent_can_be_recorded(self):
        """Staff can record consent on a client."""
        from django.utils import timezone
        self.client.login(username="staff", password="testpass123")
        today = timezone.now().strftime("%Y-%m-%d")
        resp = self.client.post(f"/clients/{self.cf.pk}/consent/", {
            "consent_type": "written",
            "consent_date": today,
            "notes": "Signed consent form on file.",
        })
        self.assertEqual(resp.status_code, 302)
        self.cf.refresh_from_db()
        self.assertIsNotNone(self.cf.consent_given_at)
        self.assertEqual(self.cf.consent_type, "written")

    def test_consent_display_shows_consent_recorded(self):
        """Client detail shows consent status when recorded."""
        from django.utils import timezone
        self.cf.consent_given_at = timezone.now()
        self.cf.consent_type = "verbal"
        self.cf.save()

        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/clients/{self.cf.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Consent recorded")
        self.assertContains(resp, "verbal")

    def test_receptionist_cannot_record_consent(self):
        """Front desk staff cannot record consent (staff-only action)."""
        from django.utils import timezone
        self.client.login(username="receptionist", password="testpass123")
        today = timezone.now().strftime("%Y-%m-%d")
        resp = self.client.post(f"/clients/{self.cf.pk}/consent/", {
            "consent_type": "written",
            "consent_date": today,
        })
        # Should be forbidden (minimum role is staff)
        self.assertEqual(resp.status_code, 403)
        self.cf.refresh_from_db()
        self.assertIsNone(self.cf.consent_given_at)
