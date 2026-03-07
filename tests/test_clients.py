"""Tests for client CRUD views and search."""
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.constants import (
    ROLE_EXECUTIVE,
    ROLE_PROGRAM_MANAGER,
    ROLE_RECEPTIONIST,
    ROLE_STAFF,
)
from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import (
    ClientFile, ClientProgramEnrolment, ConsentEvent, CustomFieldGroup,
    CustomFieldDefinition, ClientDetailValue,
)
from apps.notes.models import ProgressNote
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ClientViewsTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        # Admin with program manager role — admins need a program role to access clients
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)
        self.pm = User.objects.create_user(username="pm", password="testpass123", is_admin=False)
        self.receptionist = User.objects.create_user(username="receptionist", password="testpass123", is_admin=False)
        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6")
        UserProgramRole.objects.create(user=self.staff, program=self.prog_a, role=ROLE_STAFF)
        UserProgramRole.objects.create(user=self.pm, program=self.prog_a, role=ROLE_PROGRAM_MANAGER)
        UserProgramRole.objects.create(user=self.receptionist, program=self.prog_a, role=ROLE_RECEPTIONIST)
        # Give admin access to both programs so they can see all clients
        UserProgramRole.objects.create(user=self.admin, program=self.prog_a, role=ROLE_PROGRAM_MANAGER)
        UserProgramRole.objects.create(user=self.admin, program=self.prog_b, role=ROLE_PROGRAM_MANAGER)

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
        resp = self.client.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertContains(resp, "Bob")

    def test_staff_sees_only_own_program_clients(self):
        self._create_client("Alice", "Smith", [self.prog_a])
        self._create_client("Bob", "Jones", [self.prog_b])
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertNotContains(resp, "Bob")

    def test_create_client(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/participants/create/", {
            "first_name": "Test",
            "last_name": "User",
            "preferred_name": "",
            "middle_name": "",
            "birth_date": "",
            "record_id": "R001",
            "status": "active",
            "preferred_language": "en",
            "programs": [self.prog_a.pk],
        })
        self.assertEqual(resp.status_code, 302)
        cf = ClientFile.objects.last()
        self.assertEqual(cf.first_name, "Test")
        self.assertEqual(cf.last_name, "User")
        self.assertTrue(ClientProgramEnrolment.objects.filter(client_file=cf, program=self.prog_a).exists())

    def test_create_client_redirect_to_profile(self):
        """After creating a participant, redirect to profile with success message (QA-W7/W8)."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/participants/create/", {
            "first_name": "Test",
            "last_name": "Redirect",
            "preferred_name": "",
            "middle_name": "",
            "birth_date": "",
            "record_id": "R002",
            "status": "active",
            "preferred_language": "en",
            "programs": [self.prog_a.pk],
        }, follow=True)
        # Should redirect to profile page (not 404)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test")
        self.assertContains(resp, "Redirect")
        # Should include personalised success message with participant name
        messages_list = list(resp.context["messages"])
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Test Redirect", str(messages_list[0]))
        self.assertIn("created successfully", str(messages_list[0]))
        # Should be added to recently-viewed session
        cf = ClientFile.objects.last()
        session = self.client.session
        self.assertIn(cf.pk, session.get("recent_clients", []))

    def test_create_client_redirect_staff_user(self):
        """BUG-7 reproduction: staff user creating a participant should redirect to profile, not 404."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post("/participants/create/", {
            "first_name": "Staff",
            "last_name": "Created",
            "preferred_name": "",
            "middle_name": "",
            "birth_date": "",
            "record_id": "R-STAFF",
            "status": "active",
            "preferred_language": "en",
            "programs": [self.prog_a.pk],
        }, follow=True)
        self.assertEqual(resp.status_code, 200, f"Expected 200 but got {resp.status_code}")
        self.assertContains(resp, "Staff")
        self.assertContains(resp, "Created")

    def test_create_client_with_preferred_name(self):
        """Preferred name is saved and used as display_name."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/participants/create/", {
            "first_name": "Jonathan",
            "last_name": "Smith",
            "preferred_name": "Jay",
            "middle_name": "",
            "birth_date": "",
            "record_id": "",
            "status": "active",
            "preferred_language": "en",
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
        resp = self.client.get(f"/participants/{cf.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jay")

    def test_edit_client(self):
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        # Staff role has client.edit PROGRAM (same as program_manager)
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(f"/participants/{cf.pk}/edit/", {
            "first_name": "Janet",
            "last_name": "Doe",
            "middle_name": "",
            "birth_date": "",
            "record_id": "",
            "status": "active",
            "preferred_language": "en",
        })
        self.assertEqual(resp.status_code, 302)
        cf.refresh_from_db()
        self.assertEqual(cf.first_name, "Janet")

    def test_pm_can_edit_client(self):
        """Program managers have client.edit PROGRAM — can edit clients in their program."""
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/participants/{cf.pk}/edit/", {
            "first_name": "Janet",
            "last_name": "Doe",
            "middle_name": "",
            "birth_date": "",
            "record_id": "",
            "status": "active",
            "preferred_language": "en",
        })
        self.assertEqual(resp.status_code, 302)
        cf.refresh_from_db()
        self.assertEqual(cf.first_name, "Janet")

    def test_pm_cannot_edit_contact(self):
        """Program managers have client.edit_contact DENY — cannot edit contact info."""
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get(f"/participants/{cf.pk}/edit-contact/")
        self.assertEqual(resp.status_code, 403)

    def test_receptionist_cannot_edit_client(self):
        """Receptionists have client.edit DENY — cannot edit client records."""
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="receptionist", password="testpass123")
        resp = self.client.get(f"/participants/{cf.pk}/edit/")
        self.assertEqual(resp.status_code, 403)

    # --- Transfer tests ---

    def test_staff_can_transfer_client(self):
        """Staff have client.transfer PROGRAM — can add a program."""
        # Give staff access to both programs
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role=ROLE_STAFF)
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(f"/participants/{cf.pk}/transfer/", {
            "programs": [self.prog_a.pk, self.prog_b.pk],
        })
        self.assertEqual(resp.status_code, 302)
        # Verify new enrollment created
        self.assertTrue(
            ClientProgramEnrolment.objects.filter(
                client_file=cf, program=self.prog_b, status="active",
            ).exists()
        )

    def test_staff_transfer_removes_program(self):
        """Staff can unenrol a client from a program via transfer."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role=ROLE_STAFF)
        cf = self._create_client("Jane", "Doe", [self.prog_a, self.prog_b])
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(f"/participants/{cf.pk}/transfer/", {
            "programs": [self.prog_a.pk],  # Removing prog_b
        })
        self.assertEqual(resp.status_code, 302)
        enrolment = ClientProgramEnrolment.objects.get(
            client_file=cf, program=self.prog_b,
        )
        self.assertEqual(enrolment.status, "finished")

    def test_receptionist_cannot_transfer(self):
        """Receptionists have client.transfer DENY — get 403."""
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="receptionist", password="testpass123")
        resp = self.client.get(f"/participants/{cf.pk}/transfer/")
        self.assertEqual(resp.status_code, 403)

    def test_transfer_creates_audit_log(self):
        """Transfer creates an audit log entry with program change details."""
        from apps.audit.models import AuditLog
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role=ROLE_STAFF)
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="staff", password="testpass123")
        self.client.post(f"/participants/{cf.pk}/transfer/", {
            "programs": [self.prog_a.pk, self.prog_b.pk],
            "transfer_reason": "Client needs housing support",
        })
        log = AuditLog.objects.using("audit").filter(
            resource_type="enrolment", resource_id=cf.pk,
        ).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.metadata["transfer"])
        self.assertIn(self.prog_b.pk, log.metadata["programs_added"])
        self.assertEqual(log.metadata["reason"], "Client needs housing support")

    def test_transfer_preserves_confidential_enrollments(self):
        """Confidential program enrolments are not touched by transfer."""
        conf_prog = Program.objects.create(
            name="Confidential", colour_hex="#EF4444", is_confidential=True,
        )
        cf = self._create_client("Jane", "Doe", [self.prog_a, conf_prog])
        self.client.login(username="staff", password="testpass123")
        # Staff only sees prog_a, not conf_prog
        resp = self.client.post(f"/participants/{cf.pk}/transfer/", {
            "programs": [self.prog_a.pk],
        })
        self.assertEqual(resp.status_code, 302)
        # Confidential enrollment should still be enrolled
        self.assertTrue(
            ClientProgramEnrolment.objects.filter(
                client_file=cf, program=conf_prog, status="active",
            ).exists()
        )

    def test_edit_no_longer_changes_programs(self):
        """Edit form POST does not affect program enrolments (use transfer instead)."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role=ROLE_STAFF)
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="staff", password="testpass123")
        # POST to edit — programs field is no longer on the edit form
        resp = self.client.post(f"/participants/{cf.pk}/edit/", {
            "first_name": "Janet",
            "last_name": "Doe",
            "middle_name": "",
            "birth_date": "",
            "record_id": "",
            "status": "active",
            "preferred_language": "en",
        })
        self.assertEqual(resp.status_code, 302)
        # Should still only be enrolled in prog_a — edit doesn't touch enrolments
        self.assertFalse(
            ClientProgramEnrolment.objects.filter(
                client_file=cf, program=self.prog_b, status="active",
            ).exists()
        )

    def test_pm_can_transfer_client(self):
        """PMs have client.transfer PROGRAM — can transfer clients."""
        UserProgramRole.objects.create(user=self.pm, program=self.prog_b, role=ROLE_PROGRAM_MANAGER)
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/participants/{cf.pk}/transfer/", {
            "programs": [self.prog_a.pk, self.prog_b.pk],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            ClientProgramEnrolment.objects.filter(
                client_file=cf, program=self.prog_b, status="active",
            ).exists()
        )

    # --- End transfer tests ---

    def test_client_detail(self):
        cf = self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/participants/{cf.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jane")

    def test_search_finds_client(self):
        self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/participants/search/?q=jane")
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
        resp = self.client.get("/participants/search/?q=housing")
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
        resp = self.client.get("/participants/?q=intake")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jane")

    def test_search_respects_program_scope(self):
        self._create_client("Alice", "Smith", [self.prog_a])
        self._create_client("Bob", "Jones", [self.prog_b])
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/participants/search/?q=")
        self.assertNotContains(resp, "Bob")

    def test_search_empty_query(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/participants/search/?q=")
        self.assertEqual(resp.status_code, 200)

    def test_filter_by_status(self):
        """Filter clients by status (active/discharged)."""
        active = self._create_client("Active", "Client", [self.prog_a])
        discharged = self._create_client("Discharged", "Client", [self.prog_a])
        discharged.status = "discharged"
        discharged.save()

        self.client.login(username="staff", password="testpass123")

        # Filter to active only
        resp = self.client.get("/participants/?status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Active Client")
        self.assertNotContains(resp, "Discharged Client")

        # Filter to discharged only
        resp = self.client.get("/participants/?status=discharged")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Discharged Client")
        self.assertNotContains(resp, "Active Client")

    def test_on_hold_client_visible_in_list(self):
        """On-hold clients must remain visible in client list (regression)."""
        active = self._create_client("Active", "Client", [self.prog_a])
        on_hold = self._create_client("OnHold", "Client", [self.prog_a])
        # Put the enrolment on hold
        ep = ClientProgramEnrolment.objects.get(
            client_file=on_hold, program=self.prog_a,
        )
        ep.status = "on_hold"
        ep.save()

        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Active Client")
        self.assertContains(resp, "OnHold Client")

    def test_filter_by_program(self):
        """Filter clients by program enrolment."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role=ROLE_STAFF)
        alice = self._create_client("Alice", "Alpha", [self.prog_a])
        bob = self._create_client("Bob", "Beta", [self.prog_b])

        self.client.login(username="staff", password="testpass123")

        # Filter to Program A
        resp = self.client.get(f"/participants/?program={self.prog_a.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice Alpha")
        self.assertNotContains(resp, "Bob Beta")

        # Filter to Program B
        resp = self.client.get(f"/participants/?program={self.prog_b.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bob Beta")
        self.assertNotContains(resp, "Alice Alpha")

    def test_filter_combined_status_and_program(self):
        """Filter clients by both status and program."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role=ROLE_STAFF)
        alice_active = self._create_client("Alice", "Active", [self.prog_a])
        alice_discharged = self._create_client("Alice", "Discharged", [self.prog_a])
        alice_discharged.status = "discharged"
        alice_discharged.save()
        bob = self._create_client("Bob", "Beta", [self.prog_b])

        self.client.login(username="staff", password="testpass123")

        # Filter to Program A + Active
        resp = self.client.get(f"/participants/?program={self.prog_a.pk}&status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice Active")
        self.assertNotContains(resp, "Alice Discharged")
        self.assertNotContains(resp, "Bob Beta")

    def test_htmx_filter_returns_partial(self):
        """HTMX requests should return only the table partial."""
        self._create_client("Jane", "Doe", [self.prog_a])
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/participants/?status=active", HTTP_HX_REQUEST="true")
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
        resp = self.client.get("/participants/search/?q=person&status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Active Person")
        self.assertNotContains(resp, "Discharged Person")

        # Filter to discharged only
        resp = self.client.get("/participants/search/?q=person&status=discharged")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Discharged Person")
        self.assertNotContains(resp, "Active Person")

    def test_search_filter_by_program(self):
        """Filter search results by program."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role=ROLE_STAFF)
        alice = self._create_client("Alice", "Test", [self.prog_a])
        bob = self._create_client("Bob", "Test", [self.prog_b])

        self.client.login(username="staff", password="testpass123")

        # Filter to Program A
        resp = self.client.get(f"/participants/search/?q=test&program={self.prog_a.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice Test")
        self.assertNotContains(resp, "Bob Test")

        # Filter to Program B
        resp = self.client.get(f"/participants/search/?q=test&program={self.prog_b.pk}")
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
        resp = self.client.get(f"/participants/search/?q=client&date_from={week_ago}")
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
        resp = self.client.get("/participants/search/?status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Active Person")
        self.assertNotContains(resp, "Discharged Person")

    def test_search_combined_filters(self):
        """Multiple filters should work together."""
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role=ROLE_STAFF)
        alice_active = self._create_client("Alice", "Active", [self.prog_a])
        alice_discharged = self._create_client("Alice", "Discharged", [self.prog_a])
        alice_discharged.status = "discharged"
        alice_discharged.save()
        bob = self._create_client("Bob", "Beta", [self.prog_b])

        self.client.login(username="staff", password="testpass123")

        # Search "Alice" + Program A + Active
        resp = self.client.get(f"/participants/search/?q=alice&program={self.prog_a.pk}&status=active")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice Active")
        self.assertNotContains(resp, "Alice Discharged")
        self.assertNotContains(resp, "Bob Beta")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CustomFieldTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        # Admin needs a program role to access client data
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.admin, program=self.program, role=ROLE_PROGRAM_MANAGER)

    def test_custom_field_admin_requires_admin(self):
        staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/participants/admin/fields/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_view_custom_field_admin(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/participants/admin/fields/")
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
        resp = self.client.post(f"/participants/{cf.pk}/custom-fields/", {
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
        resp = self.client.post(f"/participants/{cf.pk}/custom-fields/", {
            f"custom_{field_def.pk}": "secret-value-123",
        })
        self.assertEqual(resp.status_code, 302)
        cdv = ClientDetailValue.objects.get(client_file=cf, field_def=field_def)
        # Value should be retrievable via get_value() (decrypted)
        self.assertEqual(cdv.get_value(), "secret-value-123")
        # Plain value field should be empty (stored encrypted instead)
        self.assertEqual(cdv.value, "")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ShowOnCreateFieldTest(TestCase):
    """Tests for custom fields with show_on_create=True on the New Participant form."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.receptionist = User.objects.create_user(username="recep", password="testpass123", is_admin=False)
        self.prog = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.admin, program=self.prog, role=ROLE_PROGRAM_MANAGER)
        UserProgramRole.objects.create(user=self.receptionist, program=self.prog, role=ROLE_RECEPTIONIST)
        self.group = CustomFieldGroup.objects.create(title="Identity", sort_order=10)
        self.pronouns = CustomFieldDefinition.objects.create(
            group=self.group, name="Pronouns", input_type="select_other",
            is_required=False, show_on_create=True, front_desk_access="edit",
            options_json=["He/him", "She/her", "They/them"],
        )

    def _base_post_data(self, **extra):
        data = {
            "first_name": "Test", "last_name": "User",
            "preferred_name": "", "middle_name": "",
            "birth_date": "", "record_id": "", "status": "active",
            "preferred_language": "en", "programs": [self.prog.pk],
        }
        data.update(extra)
        return data

    def test_create_renders_show_on_create_field(self):
        """GET create page includes custom fields marked show_on_create."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/participants/create/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pronouns")
        self.assertContains(resp, "He/him")

    def test_create_saves_custom_field_value(self):
        """POST with a custom field value saves a ClientDetailValue."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/participants/create/", self._base_post_data(
            **{f"custom_{self.pronouns.pk}": "They/them"},
        ))
        self.assertEqual(resp.status_code, 302)
        cf = ClientFile.objects.last()
        cdv = ClientDetailValue.objects.get(client_file=cf, field_def=self.pronouns)
        self.assertEqual(cdv.get_value(), "They/them")

    def test_create_skips_empty_custom_field(self):
        """Empty custom field values don't create ClientDetailValue records."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/participants/create/", self._base_post_data(
            **{f"custom_{self.pronouns.pk}": ""},
        ))
        self.assertEqual(resp.status_code, 302)
        cf = ClientFile.objects.last()
        self.assertFalse(ClientDetailValue.objects.filter(client_file=cf).exists())

    def test_create_receptionist_sees_edit_fields_only(self):
        """Receptionist sees show_on_create fields with front_desk_access='edit' only."""
        hidden_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Secret Field", input_type="text",
            show_on_create=True, front_desk_access="none",
        )
        self.client.login(username="recep", password="testpass123")
        resp = self.client.get("/participants/create/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pronouns")
        self.assertNotContains(resp, "Secret Field")

    def test_create_does_not_show_non_flagged_fields(self):
        """Fields with show_on_create=False don't appear on the create form."""
        hidden = CustomFieldDefinition.objects.create(
            group=self.group, name="Hidden Field", input_type="text",
            show_on_create=False, front_desk_access="edit",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/participants/create/")
        self.assertNotContains(resp, "Hidden Field")

    def test_create_sensitive_field_encrypted(self):
        """Sensitive custom field values are stored encrypted."""
        sensitive = CustomFieldDefinition.objects.create(
            group=self.group, name="SIN", input_type="text",
            is_required=False, is_sensitive=True,
            show_on_create=True, front_desk_access="edit",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/participants/create/", self._base_post_data(
            **{f"custom_{sensitive.pk}": "123-456-789"},
        ))
        self.assertEqual(resp.status_code, 302)
        cf = ClientFile.objects.last()
        cdv = ClientDetailValue.objects.get(client_file=cf, field_def=sensitive)
        self.assertEqual(cdv.get_value(), "123-456-789")
        self.assertEqual(cdv.value, "")  # Plain text field empty
        self.assertTrue(cdv._value_encrypted)  # Encrypted field populated


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SelectOtherFieldTest(TestCase):
    """Tests for the select_other input type (dropdown with free-text Other option)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.admin, program=self.program, role=ROLE_PROGRAM_MANAGER)
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
        resp = self.client.post(f"/participants/{self.cf.pk}/custom-fields/", {
            f"custom_{self.pronouns_field.pk}": "They/them",
            f"custom_{self.pronouns_field.pk}_other": "",
        })
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.pronouns_field)
        self.assertEqual(cdv.get_value(), "They/them")

    def test_save_other_uses_free_text(self):
        """Selecting 'Other' stores the free-text value, not '__other__'."""
        resp = self.client.post(f"/participants/{self.cf.pk}/custom-fields/", {
            f"custom_{self.pronouns_field.pk}": "__other__",
            f"custom_{self.pronouns_field.pk}_other": "xe/xem",
        })
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.pronouns_field)
        self.assertEqual(cdv.get_value(), "xe/xem")

    def test_save_other_strips_whitespace(self):
        """Free-text Other value has whitespace stripped."""
        resp = self.client.post(f"/participants/{self.cf.pk}/custom-fields/", {
            f"custom_{self.pronouns_field.pk}": "__other__",
            f"custom_{self.pronouns_field.pk}_other": "  ze/zir  ",
        })
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.pronouns_field)
        self.assertEqual(cdv.get_value(), "ze/zir")

    def test_pronouns_encrypted_when_sensitive(self):
        """Pronouns field with is_sensitive=True stores encrypted value."""
        self.client.post(f"/participants/{self.cf.pk}/custom-fields/", {
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
            f"/participants/{self.cf.pk}/custom-fields/edit/",
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
            f"/participants/{self.cf.pk}/custom-fields/edit/",
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
        UserProgramRole.objects.create(user=receptionist, program=self.program, role=ROLE_RECEPTIONIST)
        # Save a value first
        cdv = ClientDetailValue.objects.create(client_file=self.cf, field_def=self.pronouns_field)
        cdv.set_value("They/them")
        cdv.save()
        self.client.login(username="frontdesk", password="testpass123")
        # Display view should show the value
        resp = self.client.get(
            f"/participants/{self.cf.pk}/custom-fields/display/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "They/them")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MultiSelectFieldTest(TestCase):
    """Tests for multi_select and multi_select_other custom field types."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.admin, program=self.program, role=ROLE_PROGRAM_MANAGER)
        self.group = CustomFieldGroup.objects.create(title="Demographics")
        self.racial_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Racial Identity", input_type="multi_select",
            options_json=["White", "Black", "South Asian", "East Asian", "Latin American"],
        )
        self.identity_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Identity", input_type="multi_select_other",
            options_json=["Option A", "Option B", "Option C"],
        )
        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.program)
        self.client.login(username="admin", password="testpass123")

    def test_multi_select_saves_json_array(self):
        """Selecting multiple checkboxes stores a JSON array."""
        resp = self.client.post(f"/participants/{self.cf.pk}/custom-fields/", {
            f"custom_{self.racial_field.pk}": ["Black", "South Asian"],
        })
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.racial_field)
        self.assertEqual(cdv.get_value(), '["Black", "South Asian"]')

    def test_multi_select_empty_saves_blank(self):
        """No selections stores empty string, not '[]'."""
        resp = self.client.post(f"/participants/{self.cf.pk}/custom-fields/", {
            # No value for the multi_select field — Django sends nothing for unchecked boxes
        })
        self.assertIn(resp.status_code, [200, 302])
        qs = ClientDetailValue.objects.filter(client_file=self.cf, field_def=self.racial_field)
        if qs.exists():
            self.assertIn(qs.first().get_value(), ["", "[]"])

    def test_multi_select_roundtrip_shows_checked(self):
        """Saved multi_select values appear as checked in the edit view context."""
        import json
        cdv = ClientDetailValue.objects.create(client_file=self.cf, field_def=self.racial_field)
        cdv.value = json.dumps(["Black", "South Asian"])
        cdv.save()
        resp = self.client.get(
            f"/participants/{self.cf.pk}/custom-fields/edit/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        for group in resp.context["custom_data"]:
            for item in group["fields"]:
                if item["field_def"].pk == self.racial_field.pk:
                    self.assertIn("Black", item["selected_values"])
                    self.assertIn("South Asian", item["selected_values"])
                    self.assertEqual(item["display_value"], "Black, South Asian")

    def test_multi_select_other_merges_custom_text(self):
        """'Other' free-text is appended to the JSON array."""
        resp = self.client.post(f"/participants/{self.cf.pk}/custom-fields/", {
            f"custom_{self.identity_field.pk}": ["Option A"],
            f"custom_{self.identity_field.pk}_other": "Custom Value",
        })
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.identity_field)
        import json
        stored = json.loads(cdv.get_value())
        self.assertIn("Option A", stored)
        self.assertIn("Custom Value", stored)

    def test_multi_select_display_comma_separated(self):
        """Display view shows multi_select as comma-separated text."""
        import json
        cdv = ClientDetailValue.objects.create(client_file=self.cf, field_def=self.racial_field)
        cdv.value = json.dumps(["Black", "South Asian"])
        cdv.save()
        resp = self.client.get(
            f"/participants/{self.cf.pk}/custom-fields/display/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Black, South Asian")

    def test_collapsed_group_renders_without_open(self):
        """Groups with collapsed_by_default=True render <details> without open attribute."""
        self.group.collapsed_by_default = True
        self.group.save()
        cdv = ClientDetailValue.objects.create(
            client_file=self.cf, field_def=self.racial_field, value="White"
        )
        resp = self.client.get(
            f"/participants/{self.cf.pk}/custom-fields/display/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # Collapsed group should have <details> without open
        self.assertIn("<details>", content)
        self.assertNotIn("<details open>", content)

    def test_open_group_renders_with_open(self):
        """Groups with collapsed_by_default=False render <details open>."""
        self.group.collapsed_by_default = False
        self.group.save()
        cdv = ClientDetailValue.objects.create(
            client_file=self.cf, field_def=self.racial_field, value="White"
        )
        resp = self.client.get(
            f"/participants/{self.cf.pk}/custom-fields/display/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<details open>")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConsentRecordingTest(TestCase):
    """Tests for consent recording workflow (PRIV1)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)
        self.receptionist = User.objects.create_user(username="receptionist", password="testpass123", is_admin=False)
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.program, role=ROLE_STAFF)
        UserProgramRole.objects.create(user=self.receptionist, program=self.program, role=ROLE_RECEPTIONIST)

        self.cf = ClientFile()
        self.cf.first_name = "Jane"
        self.cf.last_name = "Doe"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.program)

    def test_consent_display_shows_no_consent(self):
        """Client detail shows 'no consent' warning when consent not recorded."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/participants/{self.cf.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No consent on file")

    def test_consent_can_be_recorded(self):
        """Staff can record consent on a client."""
        from django.utils import timezone
        self.client.login(username="staff", password="testpass123")
        today = timezone.now().strftime("%Y-%m-%d")
        resp = self.client.post(f"/participants/{self.cf.pk}/consent/", {
            "consent_type": "written",
            "consent_date": today,
            "notes": "Signed consent form on file.",
        })
        self.assertEqual(resp.status_code, 302)
        self.cf.refresh_from_db()
        self.assertIsNotNone(self.cf.consent_given_at)
        self.assertEqual(self.cf.consent_type, "written")

    def test_consent_audit_log_uses_forwarded_ip(self):
        """Consent grant audit logs should use the forwarded client IP."""
        from apps.audit.models import AuditLog
        from django.utils import timezone

        self.client.login(username="staff", password="testpass123")
        today = timezone.now().strftime("%Y-%m-%d")
        self.client.post(
            f"/participants/{self.cf.pk}/consent/",
            {
                "consent_type": "written",
                "consent_date": today,
                "notes": "Signed consent form on file.",
            },
            HTTP_X_FORWARDED_FOR="203.0.113.11, 10.0.0.5",
            REMOTE_ADDR="127.0.0.1",
        )

        log = AuditLog.objects.using("audit").filter(
            resource_type="consent",
            resource_id=self.cf.pk,
            action="create",
        ).latest("event_timestamp")
        self.assertEqual(log.ip_address, "203.0.113.11")

    def test_consent_display_shows_consent_recorded(self):
        """Client detail shows consent status when recorded."""
        from django.utils import timezone
        self.cf.consent_given_at = timezone.now()
        self.cf.consent_type = "verbal"
        self.cf.save()

        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/participants/{self.cf.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Consent on file")
        self.assertContains(resp, "verbal")

    def test_receptionist_cannot_record_consent(self):
        """Front desk staff cannot record consent (staff-only action)."""
        from django.utils import timezone
        self.client.login(username="receptionist", password="testpass123")
        today = timezone.now().strftime("%Y-%m-%d")
        resp = self.client.post(f"/participants/{self.cf.pk}/consent/", {
            "consent_type": "written",
            "consent_date": today,
        })
        # Should be forbidden (minimum role is staff)
        self.assertEqual(resp.status_code, 403)
        self.cf.refresh_from_db()
        self.assertIsNone(self.cf.consent_given_at)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConsentWithdrawalTest(TestCase):
    """Tests for consent withdrawal workflow (QA-R7-PRIVACY2)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)
        self.pm = User.objects.create_user(username="pm", password="testpass123", is_admin=False)
        self.receptionist = User.objects.create_user(username="receptionist", password="testpass123", is_admin=False)
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.program, role=ROLE_STAFF)
        UserProgramRole.objects.create(user=self.pm, program=self.program, role=ROLE_PROGRAM_MANAGER)
        UserProgramRole.objects.create(user=self.receptionist, program=self.program, role=ROLE_RECEPTIONIST)

        self.cf = ClientFile()
        self.cf.first_name = "Jane"
        self.cf.last_name = "Doe"
        self.cf.consent_given_at = timezone.now()
        self.cf.consent_type = "written"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.program)

    def test_withdraw_form_visible_for_pm(self):
        """PM sees the Withdraw button on consent display."""
        self.http.login(username="pm", password="testpass123")
        resp = self.http.get(f"/participants/{self.cf.pk}/consent/display/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Withdraw")

    def test_withdraw_form_not_visible_for_receptionist(self):
        """Receptionist does not see the Withdraw button."""
        self.http.login(username="receptionist", password="testpass123")
        resp = self.http.get(f"/participants/{self.cf.pk}/consent/display/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Withdraw")

    def test_withdrawal_saves_correctly(self):
        """POST to withdraw clears consent_given_at, sets retention_expires, creates ConsentEvent."""
        self.http.login(username="pm", password="testpass123")
        today = timezone.now().strftime("%Y-%m-%d")
        resp = self.http.post(f"/participants/{self.cf.pk}/consent/withdraw/save/", {
            "withdrawal_date": today,
            "withdrawal_reason": "participant_requested",
            "request_received_via": "written",
            "notes": "Participant called to withdraw.",
            "confirm": "on",
        })
        self.assertIn(resp.status_code, [200, 302])
        self.cf.refresh_from_db()
        self.assertIsNone(self.cf.consent_given_at)
        self.assertEqual(self.cf.consent_type, "")
        self.assertIsNotNone(self.cf.retention_expires)

        # Verify ConsentEvent created
        event = ConsentEvent.objects.filter(client_file=self.cf, event_type="withdrawn").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.withdrawal_reason, "participant_requested")
        self.assertEqual(event.recorded_by, self.pm)

    def test_withdrawal_audit_log_uses_forwarded_ip(self):
        """Consent withdrawal audit logs should use the forwarded client IP."""
        from apps.audit.models import AuditLog

        self.http.login(username="pm", password="testpass123")
        today = timezone.now().strftime("%Y-%m-%d")
        self.http.post(
            f"/participants/{self.cf.pk}/consent/withdraw/save/",
            {
                "withdrawal_date": today,
                "withdrawal_reason": "participant_requested",
                "request_received_via": "written",
                "confirm": "on",
            },
            HTTP_X_FORWARDED_FOR="198.51.100.40, 10.0.0.9",
            REMOTE_ADDR="127.0.0.1",
        )

        log = AuditLog.objects.using("audit").filter(
            resource_type="consent",
            resource_id=self.cf.pk,
            action="update",
        ).latest("event_timestamp")
        self.assertEqual(log.ip_address, "198.51.100.40")

    def test_withdrawal_blocks_note_creation(self):
        """After withdrawal, note creation returns consent-required page."""
        # Withdraw consent
        self.cf.consent_given_at = None
        self.cf.retention_expires = timezone.now().date()
        self.cf.save()

        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(f"/notes/participant/{self.cf.pk}/new/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "consent")

    def test_withdrawal_blocks_client_edit(self):
        """After withdrawal, client edit redirects with error message."""
        self.cf.consent_given_at = None
        self.cf.retention_expires = timezone.now().date()
        self.cf.save()

        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(f"/participants/{self.cf.pk}/edit/")
        self.assertEqual(resp.status_code, 302)

    def test_re_grant_after_withdrawal(self):
        """Re-recording consent sets consent_given_at, clears retention_expires."""
        # First withdraw
        self.cf.consent_given_at = None
        self.cf.retention_expires = timezone.now().date()
        self.cf.consent_type = ""
        self.cf.save()

        self.http.login(username="staff", password="testpass123")
        today = timezone.now().strftime("%Y-%m-%d")
        resp = self.http.post(f"/participants/{self.cf.pk}/consent/", {
            "consent_type": "written",
            "consent_date": today,
        })
        self.assertIn(resp.status_code, [200, 302])
        self.cf.refresh_from_db()
        self.assertIsNotNone(self.cf.consent_given_at)
        self.assertIsNone(self.cf.retention_expires)

        # Verify ConsentEvent for grant
        event = ConsentEvent.objects.filter(client_file=self.cf, event_type="granted").first()
        self.assertIsNotNone(event)

    def test_cannot_withdraw_when_no_consent(self):
        """Attempting to withdraw with no active consent fails gracefully."""
        self.cf.consent_given_at = None
        self.cf.save()

        self.http.login(username="pm", password="testpass123")
        resp = self.http.get(f"/participants/{self.cf.pk}/consent/withdraw/")
        self.assertIn(resp.status_code, [200, 302])

    def test_receptionist_cannot_withdraw(self):
        """Receptionist cannot access the withdrawal endpoint."""
        self.http.login(username="receptionist", password="testpass123")
        resp = self.http.post(f"/participants/{self.cf.pk}/consent/withdraw/save/", {
            "withdrawal_date": timezone.now().strftime("%Y-%m-%d"),
            "withdrawal_reason": "participant_requested",
            "request_received_via": "written",
            "confirm": "on",
        })
        self.assertEqual(resp.status_code, 403)

    def test_withdrawal_sets_retention_period(self):
        """Retention date is calculated correctly (default 3650 days)."""
        from datetime import date, timedelta
        self.http.login(username="pm", password="testpass123")
        today = date.today()
        resp = self.http.post(f"/participants/{self.cf.pk}/consent/withdraw/save/", {
            "withdrawal_date": today.isoformat(),
            "withdrawal_reason": "service_ended",
            "request_received_via": "verbal",
            "confirm": "on",
        })
        self.assertIn(resp.status_code, [200, 302])
        self.cf.refresh_from_db()
        expected = today + timedelta(days=3650)
        self.assertEqual(self.cf.retention_expires, expected)

    def test_consent_history_records_all_events(self):
        """Multiple grant/withdraw cycles create correct ConsentEvent chain."""
        self.http.login(username="pm", password="testpass123")
        today = timezone.now().strftime("%Y-%m-%d")

        # Withdraw
        self.http.post(f"/participants/{self.cf.pk}/consent/withdraw/save/", {
            "withdrawal_date": today,
            "withdrawal_reason": "participant_requested",
            "request_received_via": "written",
            "confirm": "on",
        })
        # Re-grant
        self.http.post(f"/participants/{self.cf.pk}/consent/", {
            "consent_type": "verbal",
            "consent_date": today,
        })

        events = ConsentEvent.objects.filter(client_file=self.cf).order_by("recorded_at")
        self.assertEqual(events.count(), 2)
        self.assertEqual(events[0].event_type, "withdrawn")
        self.assertEqual(events[1].event_type, "granted")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExecutiveDashboardExportTest(TestCase):
    """Tests for executive dashboard CSV export (BUG-9/10 review fixes)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981")

        # Executive user
        self.executive = User.objects.create_user(
            username="exec", password="pass", is_admin=False,
        )
        UserProgramRole.objects.create(
            user=self.executive, program=self.prog, role=ROLE_EXECUTIVE,
        )

        # PM user
        self.pm = User.objects.create_user(
            username="pm", password="pass", is_admin=False,
        )
        UserProgramRole.objects.create(
            user=self.pm, program=self.prog, role=ROLE_PROGRAM_MANAGER,
        )

        # Frontline staff (should be blocked)
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_admin=False,
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.prog, role=ROLE_STAFF,
        )

        # Admin user
        self.admin = User.objects.create_user(
            username="admin", password="pass", is_admin=True,
        )
        UserProgramRole.objects.create(
            user=self.admin, program=self.prog, role=ROLE_PROGRAM_MANAGER,
        )

        # Create some clients
        for i in range(6):
            cf = ClientFile()
            cf.first_name = f"Client{i}"
            cf.last_name = "Test"
            cf.status = "active"
            cf.save()
            ClientProgramEnrolment.objects.create(
                client_file=cf, program=self.prog,
            )

    def tearDown(self):
        enc_module._fernet = None

    def test_executive_can_export(self):
        """Executive role can download CSV export."""
        self.http.login(username="exec", password="pass")
        resp = self.http.get("/participants/executive/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("executive-dashboard.csv", resp["Content-Disposition"])

    def test_pm_can_export(self):
        """Program manager role can download CSV export."""
        self.http.login(username="pm", password="pass")
        resp = self.http.get("/participants/executive/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")

    def test_admin_can_export(self):
        """Admin can download CSV export."""
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/participants/executive/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")

    def test_staff_blocked_from_export(self):
        """Frontline staff cannot download CSV export."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/participants/executive/export/")
        self.assertEqual(resp.status_code, 403)

    def test_export_creates_audit_log(self):
        """CSV export creates an audit log entry."""
        from apps.audit.models import AuditLog
        self.http.login(username="exec", password="pass")
        self.http.get("/participants/executive/export/")
        log = AuditLog.objects.using("audit").filter(
            action="export", resource_type="executive_dashboard",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user_id, self.executive.pk)

    def test_export_with_start_date(self):
        """CSV export respects start_date query param."""
        self.http.login(username="exec", password="pass")
        resp = self.http.get("/participants/executive/export/", {"start_date": "2026-01-01"})
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("Prog A", content)

    def test_anonymous_user_redirected_export(self):
        """Unauthenticated users are redirected to login on export."""
        resp = self.http.get("/participants/executive/export/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)

    def test_anonymous_user_redirected_dashboard(self):
        """Unauthenticated users are redirected to login on dashboard."""
        resp = self.http.get("/participants/executive/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)


class ExecutiveDashboardPdfExportTest(TestCase):
    """Tests for executive dashboard PDF export."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981")

        # Executive user
        self.executive = User.objects.create_user(
            username="exec", password="pass", is_admin=False,
        )
        UserProgramRole.objects.create(
            user=self.executive, program=self.prog, role=ROLE_EXECUTIVE,
        )

        # PM user
        self.pm = User.objects.create_user(
            username="pm", password="pass", is_admin=False,
        )
        UserProgramRole.objects.create(
            user=self.pm, program=self.prog, role=ROLE_PROGRAM_MANAGER,
        )

        # Frontline staff (should be blocked)
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_admin=False,
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.prog, role=ROLE_STAFF,
        )

        # Admin user
        self.admin = User.objects.create_user(
            username="admin", password="pass", is_admin=True,
        )
        UserProgramRole.objects.create(
            user=self.admin, program=self.prog, role=ROLE_PROGRAM_MANAGER,
        )

        # Create some clients
        for i in range(6):
            cf = ClientFile()
            cf.first_name = f"Client{i}"
            cf.last_name = "Test"
            cf.status = "active"
            cf.save()
            ClientProgramEnrolment.objects.create(
                client_file=cf, program=self.prog,
            )

    def tearDown(self):
        enc_module._fernet = None

    def test_executive_dashboard_pdf_permission(self):
        """Frontline staff cannot access the PDF export."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/participants/executive/pdf/")
        self.assertEqual(resp.status_code, 403)

    def test_executive_dashboard_pdf_success(self):
        """Executive/PM user can download the PDF export."""
        self.http.login(username="exec", password="pass")
        resp = self.http.get("/participants/executive/pdf/")
        self.assertEqual(resp.status_code, 200)
        # WeasyPrint may not be installed in the test environment, so the
        # view falls back to HTML.  Accept either content type.
        self.assertIn(
            resp["Content-Type"],
            ("application/pdf", "text/html"),
        )
        self.assertIn("Content-Disposition", resp)
        self.assertIn("executive-dashboard", resp["Content-Disposition"])

    def test_executive_dashboard_pdf_with_program_filter(self):
        """PDF export accepts a program query parameter."""
        self.http.login(username="exec", password="pass")
        resp = self.http.get(
            "/participants/executive/pdf/",
            {"program": self.prog.pk},
        )
        self.assertEqual(resp.status_code, 200)

    def test_executive_dashboard_pdf_with_start_date(self):
        """PDF export accepts a start_date query parameter."""
        self.http.login(username="exec", password="pass")
        resp = self.http.get(
            "/participants/executive/pdf/",
            {"start_date": "2025-01-01"},
        )
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StatisticalDisclosureGuardTest(TestCase):
    """Tests for small-program percentage suppression."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.small_prog = Program.objects.create(
            name="Small Prog", colour_hex="#FF0000", status="active",
        )
        self.large_prog = Program.objects.create(
            name="Large Prog", colour_hex="#00FF00", status="active",
        )

        # Small program: 3 active clients (below threshold of 5)
        for i in range(3):
            cf = ClientFile()
            cf.first_name = f"Small{i}"
            cf.last_name = "Test"
            cf.status = "active"
            cf.save()
            ClientProgramEnrolment.objects.create(
                client_file=cf, program=self.small_prog,
            )

        # Large program: 10 active clients (above threshold)
        for i in range(10):
            cf = ClientFile()
            cf.first_name = f"Large{i}"
            cf.last_name = "Test"
            cf.status = "active"
            cf.save()
            ClientProgramEnrolment.objects.create(
                client_file=cf, program=self.large_prog,
            )

    def tearDown(self):
        enc_module._fernet = None

    def test_small_program_suppresses_percentages(self):
        """Programs below SMALL_PROGRAM_THRESHOLD suppress percentage metrics."""
        from apps.clients.dashboard_views import (
            SMALL_PROGRAM_THRESHOLD,
            _batch_enrolment_stats,
        )
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        all_client_ids = set(ClientFile.objects.values_list("pk", flat=True))
        small_ids = [self.small_prog.pk]
        stats = _batch_enrolment_stats(small_ids, all_client_ids, month_start)
        active = stats[self.small_prog.pk]["active"]
        self.assertLess(active, SMALL_PROGRAM_THRESHOLD)

    def test_large_program_shows_percentages(self):
        """Programs above SMALL_PROGRAM_THRESHOLD show percentage metrics."""
        from apps.clients.dashboard_views import (
            SMALL_PROGRAM_THRESHOLD,
            _batch_enrolment_stats,
        )
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        all_client_ids = set(ClientFile.objects.values_list("pk", flat=True))
        large_ids = [self.large_prog.pk]
        stats = _batch_enrolment_stats(large_ids, all_client_ids, month_start)
        active = stats[self.large_prog.pk]["active"]
        self.assertGreaterEqual(active, SMALL_PROGRAM_THRESHOLD)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AccentedCharacterEncryptionTest(TestCase):
    """QA-R7-BUG13: Verify accented characters survive Fernet encrypt/decrypt cycle."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_accented_first_name_preserved(self):
        """French accented characters round-trip through encrypt -> save -> load -> decrypt."""
        client = ClientFile()
        client.first_name = "H\u00e9l\u00e8ne"
        client.last_name = "B\u00e9h\u00e9rer"
        client.save()

        loaded = ClientFile.objects.get(pk=client.pk)
        self.assertEqual(loaded.first_name, "H\u00e9l\u00e8ne")
        self.assertEqual(loaded.last_name, "B\u00e9h\u00e9rer")

    def test_full_accent_set_preserved(self):
        """All common French/Canadian accented characters survive the cycle."""
        accented_names = [
            ("Ren\u00e9", "L\u00e9vesque"),
            ("Fran\u00e7ois", "L\u00e9gar\u00e9"),
            ("No\u00ebl", "C\u00f4t\u00e9"),
            ("Andr\u00e9e", "B\u00e9land"),
        ]
        for first, last in accented_names:
            client = ClientFile()
            client.first_name = first
            client.last_name = last
            client.save()

            loaded = ClientFile.objects.get(pk=client.pk)
            self.assertEqual(loaded.first_name, first, f"First name failed for {first}")
            self.assertEqual(loaded.last_name, last, f"Last name failed for {last}")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FormDataPreservationTest(TestCase):
    """QA-R7-BUG21: Verify create-participant form preserves data after validation error."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.admin, program=self.program, role=ROLE_PROGRAM_MANAGER)

    def test_form_data_preserved_on_validation_error(self):
        """When a required field is missing, entered data should be in the response."""
        self.http_client.login(username="admin", password="testpass123")
        # Submit without selecting a program (required) to trigger a validation error
        resp = self.http_client.post("/participants/create/", {
            "first_name": "Marie-Claire",
            "last_name": "Tremblay",
            "preferred_name": "",
            "middle_name": "",
            "phone": "",
            "record_id": "",
            "status": "active",
            "preferred_language": "fr",
            # Deliberately omit "programs" to trigger validation error
        })
        self.assertEqual(resp.status_code, 200)  # Re-renders the form (not redirect)
        content = resp.content.decode("utf-8")
        # The form should contain the entered first name and last name
        self.assertIn("Marie-Claire", content)
        self.assertIn("Tremblay", content)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CrossProgramSearchTest(TestCase):
    """Regression test for cross-program search (PR #207)."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6")

    def test_cross_program_search_finds_client_ux3(self):
        """QA-R8-UX3: User in Program B can search for client created in Program A."""
        user_b = User.objects.create_user(
            username="staff_b", password="testpass123", is_admin=False
        )
        UserProgramRole.objects.create(user=user_b, program=self.prog_b, role=ROLE_STAFF)
        UserProgramRole.objects.create(user=user_b, program=self.prog_a, role=ROLE_STAFF)

        cf = ClientFile()
        cf.first_name = "Unique"
        cf.last_name = "Testname"
        cf.status = "active"
        cf.save()
        ClientProgramEnrolment.objects.create(client_file=cf, program=self.prog_a)

        self.client.login(username="staff_b", password="testpass123")
        resp = self.client.get("/participants/?q=Unique")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unique")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RoleBasedGroupingTest(TestCase):
    """Tests for the mixed-role participant list grouping (caseload vs oversight)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.prog_kitchen = Program.objects.create(name="Community Kitchen", colour_hex="#10B981")
        self.prog_housing = Program.objects.create(name="Housing Stability", colour_hex="#F59E0B")

        # Morgan: staff in Kitchen, PM in Housing — dual role
        self.morgan = User.objects.create_user(username="morgan", password="testpass123")
        UserProgramRole.objects.create(user=self.morgan, program=self.prog_kitchen, role=ROLE_STAFF)
        UserProgramRole.objects.create(user=self.morgan, program=self.prog_housing, role=ROLE_PROGRAM_MANAGER)

        # Single-role staff user
        self.single_staff = User.objects.create_user(username="single_staff", password="testpass123")
        UserProgramRole.objects.create(user=self.single_staff, program=self.prog_kitchen, role=ROLE_STAFF)

        # Single-role PM user
        self.single_pm = User.objects.create_user(username="single_pm", password="testpass123")
        UserProgramRole.objects.create(user=self.single_pm, program=self.prog_housing, role=ROLE_PROGRAM_MANAGER)

    def _create_client(self, first, last, programs):
        from apps.clients.models import ClientFile, ClientProgramEnrolment
        cf = ClientFile()
        cf.first_name = first
        cf.last_name = last
        cf.status = "active"
        cf.save()
        for p in programs:
            ClientProgramEnrolment.objects.create(client_file=cf, program=p)
        return cf

    def test_staff_only_user_sees_flat_list(self):
        """Single-role staff user gets no section split."""
        self._create_client("Alice", "A", [self.prog_kitchen])
        self.client.login(username="single_staff", password="testpass123")
        resp = self.client.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Your caseload")
        self.assertNotContains(resp, "Programs you manage")
        self.assertContains(resp, "Alice")

    def test_pm_only_user_sees_flat_list(self):
        """Single-role PM user gets no section split."""
        self._create_client("Bob", "B", [self.prog_housing])
        self.client.login(username="single_pm", password="testpass123")
        resp = self.client.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Your caseload")
        self.assertNotContains(resp, "Programs you manage")
        self.assertContains(resp, "Bob")

    def test_mixed_role_user_sees_two_sections(self):
        """Dual-role user sees caseload and oversight sections."""
        self._create_client("Caseload", "Client", [self.prog_kitchen])
        self._create_client("Oversight", "Client", [self.prog_housing])
        self.client.login(username="morgan", password="testpass123")
        resp = self.client.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Your caseload")
        self.assertContains(resp, "Programs you manage")
        self.assertContains(resp, "Caseload")
        self.assertContains(resp, "Oversight")

    def test_participant_in_both_programs_goes_to_caseload(self):
        """A participant in both a staff and PM program appears in caseload only."""
        self._create_client("Both", "Programs", [self.prog_kitchen, self.prog_housing])
        self._create_client("Only", "Housing", [self.prog_housing])
        self.client.login(username="morgan", password="testpass123")
        resp = self.client.get("/participants/")
        content = resp.content.decode()
        # "Both Programs" should be in caseload section (before oversight heading)
        caseload_pos = content.find("caseload-heading")
        oversight_pos = content.find("oversight-heading")
        both_pos = content.find("Both")
        self.assertGreater(both_pos, caseload_pos)
        self.assertLess(both_pos, oversight_pos)

    def test_htmx_returns_sections_for_mixed_role(self):
        """HTMX request returns sections template for mixed-role user."""
        self._create_client("Test", "Client", [self.prog_kitchen])
        self.client.login(username="morgan", password="testpass123")
        resp = self.client.get("/participants/", HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "caseload-heading")
        self.assertContains(resp, "oversight-heading")

    def test_htmx_returns_flat_table_for_single_role(self):
        """HTMX request returns flat table for single-role user."""
        self._create_client("Test", "Client", [self.prog_kitchen])
        self.client.login(username="single_staff", password="testpass123")
        resp = self.client.get("/participants/", HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "caseload-heading")

    def test_role_subtitle_shows_program_names(self):
        """Mixed-role user sees role subtitle with program names."""
        self._create_client("Test", "Client", [self.prog_kitchen])
        self.client.login(username="morgan", password="testpass123")
        resp = self.client.get("/participants/")
        self.assertContains(resp, "Community Kitchen")
        self.assertContains(resp, "Housing Stability")
        # Subtitle contains role labels
        self.assertContains(resp, "Staff in")
        self.assertContains(resp, "Manager for")
