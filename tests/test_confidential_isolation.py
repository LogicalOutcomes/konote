"""Tests for confidential program isolation and duplicate matching.

Security contract: confidential program clients must NEVER appear in any
query, search, match, view, or export accessible to users without explicit
confidential program access. This test file blocks deployment if any test fails.
"""
from django.contrib.admin.sites import AdminSite
from django.test import Client, RequestFactory, TestCase, override_settings

from cryptography.fernet import Fernet

from apps.audit.models import AuditLog
from apps.auth_app.models import User
from apps.clients.admin import ClientDetailValueAdmin, ClientFileAdmin, ClientProgramEnrolmentAdmin
from apps.clients.models import ClientDetailValue, ClientFile, ClientProgramEnrolment, CustomFieldDefinition, CustomFieldGroup
from apps.programs.models import Program, UserProgramRole
from apps.reports.suppression import suppress_small_cell

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConfidentialIsolationTest(TestCase):
    """Test that confidential programs are invisible to non-members."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        # Users
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.standard_staff = User.objects.create_user(
            username="standard_staff", password="testpass123",
        )
        self.confidential_staff = User.objects.create_user(
            username="conf_staff", password="testpass123",
        )

        # Programs
        self.standard_prog = Program.objects.create(
            name="Employment Services", colour_hex="#10B981",
        )
        self.confidential_prog = Program.objects.create(
            name="Counselling Services", colour_hex="#EF4444",
            is_confidential=True,
        )

        # Roles
        UserProgramRole.objects.create(
            user=self.standard_staff, program=self.standard_prog, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.confidential_staff, program=self.confidential_prog, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.admin, program=self.standard_prog, role="program_manager",
        )

        # Client in standard program only
        self.standard_client = ClientFile()
        self.standard_client.first_name = "Alice"
        self.standard_client.last_name = "Standard"
        self.standard_client.phone = "(613) 555-1111"
        self.standard_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.standard_client, program=self.standard_prog,
        )

        # Client in confidential program only
        self.confidential_client = ClientFile()
        self.confidential_client.first_name = "Bob"
        self.confidential_client.last_name = "Confidential"
        self.confidential_client.phone = "(613) 555-2222"
        self.confidential_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.confidential_client, program=self.confidential_prog,
        )

        # Client in BOTH programs (dual-enrolled)
        self.dual_client = ClientFile()
        self.dual_client.first_name = "Carol"
        self.dual_client.last_name = "Dual"
        self.dual_client.phone = "(613) 555-3333"
        self.dual_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.dual_client, program=self.standard_prog,
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.dual_client, program=self.confidential_prog,
        )

    # ---- Client list ----

    def test_standard_staff_sees_standard_client(self):
        self.http.login(username="standard_staff", password="testpass123")
        resp = self.http.get("/clients/")
        self.assertContains(resp, "Alice")

    def test_standard_staff_does_not_see_confidential_only_client(self):
        self.http.login(username="standard_staff", password="testpass123")
        resp = self.http.get("/clients/")
        self.assertNotContains(resp, "Bob")

    def test_standard_staff_sees_dual_enrolled_client(self):
        """Dual-enrolled clients are visible if user has access to ANY of their programs."""
        self.http.login(username="standard_staff", password="testpass123")
        resp = self.http.get("/clients/")
        self.assertContains(resp, "Carol")

    def test_standard_staff_does_not_see_confidential_program_name(self):
        """The confidential program name must never appear for standard staff."""
        self.http.login(username="standard_staff", password="testpass123")
        resp = self.http.get("/clients/")
        self.assertNotContains(resp, "Counselling Services")

    def test_confidential_staff_sees_their_clients(self):
        self.http.login(username="conf_staff", password="testpass123")
        resp = self.http.get("/clients/")
        self.assertContains(resp, "Bob")

    # ---- Client detail ----

    def test_standard_staff_cannot_access_confidential_client_detail(self):
        self.http.login(username="standard_staff", password="testpass123")
        resp = self.http.get(f"/clients/{self.confidential_client.pk}/")
        self.assertIn(resp.status_code, [403, 404])

    def test_dual_client_detail_hides_confidential_enrolment(self):
        """When standard staff views a dual-enrolled client, the confidential
        program enrolment must not be shown."""
        self.http.login(username="standard_staff", password="testpass123")
        resp = self.http.get(f"/clients/{self.dual_client.pk}/")
        self.assertNotContains(resp, "Counselling Services")
        self.assertContains(resp, "Employment Services")

    # ---- Edit form unenrolment bug ----

    def test_edit_preserves_confidential_enrolment(self):
        """CRITICAL: Saving the edit form must NOT remove the client from
        programs the user can't see (the silent unenrolment bug)."""
        self.http.login(username="standard_staff", password="testpass123")

        # Submit edit form with only the standard program checked
        resp = self.http.post(
            f"/clients/{self.dual_client.pk}/edit/",
            {
                "first_name": "Carol",
                "last_name": "Dual",
                "status": "active",
                "programs": [self.standard_prog.pk],
            },
        )
        self.assertIn(resp.status_code, [200, 302])

        # The confidential enrolment must still be active
        conf_enrolment = ClientProgramEnrolment.objects.get(
            client_file=self.dual_client, program=self.confidential_prog,
        )
        self.assertEqual(conf_enrolment.status, "enrolled")

    # ---- is_confidential one-way rule ----

    def test_new_program_defaults_to_standard(self):
        prog = Program.objects.create(name="Sports", colour_hex="#3B82F6")
        self.assertFalse(prog.is_confidential)

    def test_confidential_cannot_be_reverted_via_form(self):
        """The form clean method must reject unsetting is_confidential."""
        from apps.programs.forms import ProgramForm
        form = ProgramForm(
            data={
                "name": "Counselling Services",
                "colour_hex": "#EF4444",
                "status": "active",
                "is_confidential": False,
            },
            instance=self.confidential_prog,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("is_confidential", form.errors)

    # ---- Search ----

    def test_search_does_not_reveal_confidential_clients(self):
        self.http.login(username="standard_staff", password="testpass123")
        resp = self.http.get("/clients/search/?q=Bob")
        self.assertNotContains(resp, "Bob")

    def test_search_no_hint_about_hidden_data(self):
        """UI must never say 'some programs may not be included' or similar."""
        self.http.login(username="standard_staff", password="testpass123")
        resp = self.http.get("/clients/search/?q=nonexistent")
        content = resp.content.decode()
        self.assertNotIn("may not be included", content)
        self.assertNotIn("hidden clients", content.lower())
        self.assertNotIn("hidden records", content.lower())
        self.assertNotIn("confidential", content.lower())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DuplicateMatchingTest(TestCase):
    """Test phone-based and name+DOB duplicate detection."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        # Staff user
        self.staff = User.objects.create_user(
            username="staff", password="testpass123",
        )

        # Programs
        self.standard_prog = Program.objects.create(
            name="Employment", colour_hex="#10B981",
        )
        self.confidential_prog = Program.objects.create(
            name="DV Support", colour_hex="#EF4444",
            is_confidential=True,
        )

        UserProgramRole.objects.create(
            user=self.staff, program=self.standard_prog, role="staff",
        )

        # Existing client in standard program with phone and DOB
        self.existing = ClientFile()
        self.existing.first_name = "Jane"
        self.existing.last_name = "Doe"
        self.existing.phone = "(613) 555-9999"
        self.existing.birth_date = "2001-03-15"
        self.existing.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.existing, program=self.standard_prog,
        )

        # Existing client in confidential program with phone and DOB
        self.conf_client = ClientFile()
        self.conf_client.first_name = "Secret"
        self.conf_client.last_name = "Person"
        self.conf_client.phone = "(613) 555-8888"
        self.conf_client.birth_date = "1990-06-20"
        self.conf_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.conf_client, program=self.confidential_prog,
        )

    def test_phone_match_found(self):
        """HTMX endpoint returns banner when phone matches standard client."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"phone": "(613) 555-9999"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jane")
        self.assertContains(resp, "Doe")

    def test_phone_match_returns_empty_for_no_match(self):
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"phone": "(613) 555-0000"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "duplicate")

    def test_confidential_client_excluded_from_matching(self):
        """CRITICAL: Clients in confidential programs must never appear
        in duplicate matching results."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"phone": "(613) 555-8888"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Secret")
        self.assertNotContains(resp, "DV Support")

    def test_empty_phone_returns_empty(self):
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"phone": ""},
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode().strip()
        self.assertNotIn("duplicate", content.lower())

    def test_matching_respects_demo_separation(self):
        """Demo staff should not match against real clients."""
        demo_staff = User.objects.create_user(
            username="demo_staff", password="testpass123", is_demo=True,
        )
        UserProgramRole.objects.create(
            user=demo_staff, program=self.standard_prog, role="staff",
        )
        self.http.login(username="demo_staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"phone": "(613) 555-9999"},
        )
        self.assertEqual(resp.status_code, 200)
        # Real client should not match for demo user
        self.assertNotContains(resp, "Jane")

    # ---- Name + DOB matching (MATCH3) ----

    def test_name_dob_match_found(self):
        """First 3 chars of first name + exact DOB returns banner."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"first_name": "Jan", "birth_date": "2001-03-15"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "similar name and date of birth")
        self.assertContains(resp, "Check existing records")
        self.assertContains(resp, f"/clients/{self.existing.pk}/")

    def test_name_dob_case_insensitive(self):
        """Name matching must be case-insensitive."""
        self.http.login(username="staff", password="testpass123")
        for name in ["jan", "JAN", "Jan", "jAn"]:
            resp = self.http.get(
                "/clients/check-duplicate/",
                {"first_name": name, "birth_date": "2001-03-15"},
            )
            self.assertContains(
                resp, "similar name and date of birth",
                msg_prefix=f"Failed for '{name}'",
            )

    def test_name_dob_confidential_excluded(self):
        """CRITICAL: Confidential clients must never appear in name+DOB matching."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"first_name": "Sec", "birth_date": "1990-06-20"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Secret")
        self.assertNotContains(resp, "DV Support")

    def test_phone_takes_priority_over_name_dob(self):
        """When phone matches, show phone banner even if name+DOB also matches."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {
                "phone": "(613) 555-9999",
                "first_name": "Jan",
                "birth_date": "2001-03-15",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "phone number")
        self.assertNotContains(resp, "similar name")

    def test_phone_no_match_falls_back_to_name_dob(self):
        """When phone is provided but doesn't match, fall back to name+DOB."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {
                "phone": "(613) 555-0000",
                "first_name": "Jan",
                "birth_date": "2001-03-15",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "similar name and date of birth")
        self.assertContains(resp, f"/clients/{self.existing.pk}/")

    def test_partial_data_first_name_only_returns_empty(self):
        """First name alone (no DOB) must not trigger matching."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"first_name": "Jan"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Jane")

    def test_partial_data_birth_date_only_returns_empty(self):
        """DOB alone (no first name) must not trigger matching."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"birth_date": "2001-03-15"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Jane")

    def test_short_name_ignored(self):
        """First name with fewer than 3 chars must not trigger matching."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"first_name": "Ja", "birth_date": "2001-03-15"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Jane")

    def test_self_exclusion_on_edit_with_name_dob(self):
        """Editing a client must not match against themselves via name+DOB."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {
                "first_name": "Jan",
                "birth_date": "2001-03-15",
                "exclude": str(self.existing.pk),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Jane")

    def test_name_dob_demo_separation(self):
        """Demo staff must not match against real clients via name+DOB."""
        demo_staff = User.objects.create_user(
            username="demo_staff2", password="testpass123", is_demo=True,
        )
        UserProgramRole.objects.create(
            user=demo_staff, program=self.standard_prog, role="staff",
        )
        self.http.login(username="demo_staff2", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"first_name": "Jan", "birth_date": "2001-03-15"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Jane")

    def test_wrong_dob_does_not_match(self):
        """Same name prefix but different DOB must not match."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(
            "/clients/check-duplicate/",
            {"first_name": "Jan", "birth_date": "2001-03-16"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Jane")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RegistrationLinkConfidentialTest(TestCase):
    """Test that registration links cannot be created for confidential programs."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )

        self.confidential_prog = Program.objects.create(
            name="DV Support", colour_hex="#EF4444",
            is_confidential=True,
        )
        self.standard_prog = Program.objects.create(
            name="Sports", colour_hex="#10B981",
        )

        UserProgramRole.objects.create(
            user=self.admin, program=self.standard_prog, role="program_manager",
        )

    def test_confidential_program_excluded_from_registration_form(self):
        """The registration link form should not offer confidential programs."""
        from apps.registration.forms import RegistrationLinkForm
        form = RegistrationLinkForm()
        program_qs = form.fields["program"].queryset
        self.assertNotIn(self.confidential_prog, program_qs)
        self.assertIn(self.standard_prog, program_qs)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GroupAccessTest(TestCase):
    """Test that group views respect program-based access control."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.staff_a = User.objects.create_user(
            username="staff_a", password="testpass123",
        )
        self.staff_b = User.objects.create_user(
            username="staff_b", password="testpass123",
        )

        self.prog_a = Program.objects.create(name="Sports", colour_hex="#10B981")
        self.prog_b = Program.objects.create(
            name="Counselling", colour_hex="#EF4444", is_confidential=True,
        )

        UserProgramRole.objects.create(
            user=self.staff_a, program=self.prog_a, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.staff_b, program=self.prog_b, role="staff",
        )

        # Create groups
        from apps.groups.models import Group
        self.group_a = Group.objects.create(
            name="Basketball", program=self.prog_a,
        )
        self.group_b = Group.objects.create(
            name="Therapy Group", program=self.prog_b,
        )

    def test_group_list_filters_by_program_access(self):
        """Staff should only see groups in their assigned programs."""
        self.http.login(username="staff_a", password="testpass123")
        resp = self.http.get("/groups/")
        self.assertContains(resp, "Basketball")
        self.assertNotContains(resp, "Therapy Group")

    def test_group_detail_blocked_for_wrong_program(self):
        """Staff cannot view details of groups in other programs."""
        self.http.login(username="staff_a", password="testpass123")
        resp = self.http.get(f"/groups/{self.group_b.pk}/")
        self.assertEqual(resp.status_code, 403)

    def test_group_detail_allowed_for_correct_program(self):
        self.http.login(username="staff_a", password="testpass123")
        resp = self.http.get(f"/groups/{self.group_a.pk}/")
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PhoneFieldTest(TestCase):
    """Test the first-class phone field on ClientFile."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.staff = User.objects.create_user(
            username="staff", password="testpass123",
        )
        self.prog = Program.objects.create(name="Sports", colour_hex="#10B981")
        UserProgramRole.objects.create(
            user=self.staff, program=self.prog, role="staff",
        )

    def test_phone_saved_and_retrieved_encrypted(self):
        cf = ClientFile()
        cf.first_name = "Test"
        cf.last_name = "User"
        cf.phone = "(613) 555-1234"
        cf.save()

        cf.refresh_from_db()
        self.assertEqual(cf.phone, "(613) 555-1234")
        # Ensure it's actually encrypted in the database
        self.assertNotEqual(cf._phone_encrypted, b"")

    def test_phone_normalised_on_form_clean(self):
        from apps.clients.forms import ClientFileForm
        form = ClientFileForm(data={
            "first_name": "Test",
            "last_name": "User",
            "status": "active",
            "phone": "6135551234",
        })
        form.fields["programs"].queryset = Program.objects.all()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["phone"], "(613) 555-1234")

    def test_create_client_with_phone(self):
        self.http.login(username="staff", password="testpass123")
        resp = self.http.post("/clients/create/", {
            "first_name": "New",
            "last_name": "Client",
            "status": "active",
            "phone": "6135551234",
            "programs": [self.prog.pk],
        })
        self.assertIn(resp.status_code, [200, 302])

        # Check client was created with phone
        cf = ClientFile.objects.order_by("-pk").first()
        if cf:
            self.assertEqual(cf.phone, "(613) 555-1234")


# =====================================================================
# CONF4: Django admin confidential filtering
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DjangoAdminConfidentialTest(TestCase):
    """Test Django admin respects confidential program boundaries.

    Expert panel finding #1: get_queryset() AND object-level permissions
    must both be checked (direct URL bypass prevention).
    """

    def setUp(self):
        enc_module._fernet = None
        self.factory = RequestFactory()
        self.site = AdminSite()

        # Users — none get automatic access via superuser status
        self.admin_no_roles = User.objects.create_user(
            username="admin_noroles", password="testpass123", is_admin=True,
        )
        self.admin_standard = User.objects.create_user(
            username="admin_std", password="testpass123", is_admin=True,
        )
        self.admin_confidential = User.objects.create_user(
            username="admin_conf", password="testpass123", is_admin=True,
        )

        # Programs
        self.standard_prog = Program.objects.create(
            name="Employment", colour_hex="#10B981",
        )
        self.confidential_prog = Program.objects.create(
            name="DV Support", colour_hex="#EF4444", is_confidential=True,
        )

        # Roles
        UserProgramRole.objects.create(
            user=self.admin_standard, program=self.standard_prog,
            role="program_manager",
        )
        UserProgramRole.objects.create(
            user=self.admin_confidential, program=self.confidential_prog,
            role="program_manager",
        )

        # Clients
        self.standard_client = ClientFile()
        self.standard_client.first_name = "Standard"
        self.standard_client.last_name = "Client"
        self.standard_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.standard_client, program=self.standard_prog,
        )

        self.confidential_client = ClientFile()
        self.confidential_client.first_name = "Confidential"
        self.confidential_client.last_name = "Client"
        self.confidential_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.confidential_client, program=self.confidential_prog,
        )

        self.dual_client = ClientFile()
        self.dual_client.first_name = "Dual"
        self.dual_client.last_name = "Client"
        self.dual_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.dual_client, program=self.standard_prog,
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.dual_client, program=self.confidential_prog,
        )

    def _make_request(self, user):
        request = self.factory.get("/django-admin/clients/clientfile/")
        request.user = user
        return request

    # ---- ClientFileAdmin list filtering ----

    def test_admin_no_roles_sees_no_clients(self):
        admin_cls = ClientFileAdmin(ClientFile, self.site)
        qs = admin_cls.get_queryset(self._make_request(self.admin_no_roles))
        self.assertEqual(qs.count(), 0)

    def test_admin_standard_sees_standard_and_dual(self):
        admin_cls = ClientFileAdmin(ClientFile, self.site)
        qs = admin_cls.get_queryset(self._make_request(self.admin_standard))
        ids = set(qs.values_list("pk", flat=True))
        self.assertIn(self.standard_client.pk, ids)
        self.assertIn(self.dual_client.pk, ids)
        self.assertNotIn(self.confidential_client.pk, ids)

    def test_admin_confidential_sees_confidential_and_dual(self):
        admin_cls = ClientFileAdmin(ClientFile, self.site)
        qs = admin_cls.get_queryset(self._make_request(self.admin_confidential))
        ids = set(qs.values_list("pk", flat=True))
        self.assertIn(self.confidential_client.pk, ids)
        self.assertIn(self.dual_client.pk, ids)
        self.assertNotIn(self.standard_client.pk, ids)

    # ---- Object-level permission checks (expert finding #1) ----

    def test_direct_access_blocked_for_confidential_client(self):
        """Direct URL access to a confidential client must be denied."""
        admin_cls = ClientFileAdmin(ClientFile, self.site)
        request = self._make_request(self.admin_standard)
        self.assertFalse(
            admin_cls.has_view_permission(request, self.confidential_client)
        )
        self.assertFalse(
            admin_cls.has_change_permission(request, self.confidential_client)
        )
        self.assertFalse(
            admin_cls.has_delete_permission(request, self.confidential_client)
        )

    def test_direct_access_allowed_for_accessible_client(self):
        admin_cls = ClientFileAdmin(ClientFile, self.site)
        request = self._make_request(self.admin_standard)
        self.assertTrue(
            admin_cls.has_view_permission(request, self.standard_client)
        )

    # ---- Enrolment admin filtering (expert finding #5) ----

    def test_enrolment_admin_filters_by_program(self):
        """Enrolment admin must filter by program access, not just client."""
        admin_cls = ClientProgramEnrolmentAdmin(ClientProgramEnrolment, self.site)
        qs = admin_cls.get_queryset(self._make_request(self.admin_standard))
        program_ids = set(qs.values_list("program_id", flat=True))
        self.assertIn(self.standard_prog.pk, program_ids)
        self.assertNotIn(self.confidential_prog.pk, program_ids)

    def test_enrolment_direct_access_blocked(self):
        """Direct access to confidential program enrolment must be denied."""
        admin_cls = ClientProgramEnrolmentAdmin(ClientProgramEnrolment, self.site)
        request = self._make_request(self.admin_standard)
        conf_enrolment = ClientProgramEnrolment.objects.get(
            client_file=self.confidential_client, program=self.confidential_prog,
        )
        self.assertFalse(
            admin_cls.has_view_permission(request, conf_enrolment)
        )

    # ---- ClientDetailValue admin filtering ----

    def test_detail_value_admin_filtered(self):
        """Custom field values for confidential clients must be hidden."""
        group = CustomFieldGroup.objects.create(title="Demographics")
        field = CustomFieldDefinition.objects.create(
            group=group, name="Test Field", input_type="text",
        )
        val_std = ClientDetailValue.objects.create(
            client_file=self.standard_client, field_def=field,
        )
        val_conf = ClientDetailValue.objects.create(
            client_file=self.confidential_client, field_def=field,
        )

        admin_cls = ClientDetailValueAdmin(ClientDetailValue, self.site)
        qs = admin_cls.get_queryset(self._make_request(self.admin_standard))
        client_ids = set(qs.values_list("client_file_id", flat=True))
        self.assertIn(self.standard_client.pk, client_ids)
        self.assertNotIn(self.confidential_client.pk, client_ids)


# =====================================================================
# CONF5: Audit logging for confidential access
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AuditConfidentialTaggingTest(TestCase):
    """Test audit logging tags confidential access correctly."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.staff = User.objects.create_user(
            username="audit_staff", password="testpass123",
        )

        self.standard_prog = Program.objects.create(
            name="Sports", colour_hex="#10B981",
        )
        self.conf_prog = Program.objects.create(
            name="DV Support", colour_hex="#EF4444", is_confidential=True,
        )

        UserProgramRole.objects.create(
            user=self.staff, program=self.standard_prog, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.conf_prog, role="staff",
        )

        self.standard_client = ClientFile()
        self.standard_client.first_name = "Standard"
        self.standard_client.last_name = "AuditTest"
        self.standard_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.standard_client, program=self.standard_prog,
        )

        self.conf_client = ClientFile()
        self.conf_client.first_name = "Confidential"
        self.conf_client.last_name = "AuditTest"
        self.conf_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.conf_client, program=self.conf_prog,
        )

    def test_standard_client_view_not_tagged_confidential(self):
        self.http.login(username="audit_staff", password="testpass123")
        self.http.get(f"/clients/{self.standard_client.pk}/")

        log = AuditLog.objects.using("audit").filter(
            resource_id=self.standard_client.pk, action="view",
        ).first()
        self.assertIsNotNone(log)
        self.assertFalse(log.is_confidential_context)

    def test_confidential_client_view_tagged(self):
        self.http.login(username="audit_staff", password="testpass123")
        self.http.get(f"/clients/{self.conf_client.pk}/")

        log = AuditLog.objects.using("audit").filter(
            resource_id=self.conf_client.pk, action="view",
        ).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.is_confidential_context)
        self.assertEqual(log.program_id, self.conf_prog.pk)

    def test_failed_access_logged_as_access_denied(self):
        """403 on a client record must be logged (expert finding #14)."""
        # Create a user WITHOUT access to the confidential program
        outsider = User.objects.create_user(
            username="outsider", password="testpass123",
        )
        UserProgramRole.objects.create(
            user=outsider, program=self.standard_prog, role="staff",
        )
        self.http.login(username="outsider", password="testpass123")
        resp = self.http.get(f"/clients/{self.conf_client.pk}/")
        self.assertIn(resp.status_code, [403, 404])

        log = AuditLog.objects.using("audit").filter(
            resource_id=self.conf_client.pk, action="access_denied",
        ).first()
        # Log should exist if a 403 was returned
        if resp.status_code == 403:
            self.assertIsNotNone(log, "403 on confidential client must be audit-logged")

    def test_program_manager_can_view_audit_log(self):
        pm = User.objects.create_user(
            username="pm_audit", password="testpass123",
        )
        UserProgramRole.objects.create(
            user=pm, program=self.conf_prog, role="program_manager",
        )
        self.http.login(username="pm_audit", password="testpass123")
        resp = self.http.get(f"/audit/program/{self.conf_prog.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_non_pm_cannot_view_program_audit_log(self):
        self.http.login(username="audit_staff", password="testpass123")
        resp = self.http.get(f"/audit/program/{self.conf_prog.pk}/")
        self.assertEqual(resp.status_code, 403)


# =====================================================================
# CONF6: Small-cell suppression
# =====================================================================


class SmallCellSuppressionTest(TestCase):
    """Test suppress_small_cell utility function."""

    def setUp(self):
        self.standard_prog = Program.objects.create(
            name="Sports", colour_hex="#10B981",
        )
        self.conf_prog = Program.objects.create(
            name="DV Support", colour_hex="#EF4444", is_confidential=True,
        )

    def test_standard_program_not_suppressed(self):
        """Standard programs show exact counts regardless of size."""
        self.assertEqual(suppress_small_cell(3, self.standard_prog), 3)
        self.assertEqual(suppress_small_cell(0, self.standard_prog), 0)

    def test_confidential_small_count_suppressed(self):
        """Confidential program with < 10 clients shows '< 10'."""
        self.assertEqual(suppress_small_cell(7, self.conf_prog), "< 10")
        self.assertEqual(suppress_small_cell(1, self.conf_prog), "< 10")
        self.assertEqual(suppress_small_cell(0, self.conf_prog), "< 10")

    def test_confidential_large_count_not_suppressed(self):
        """Confidential program with >= 10 clients shows exact count."""
        self.assertEqual(suppress_small_cell(10, self.conf_prog), 10)
        self.assertEqual(suppress_small_cell(25, self.conf_prog), 25)

    def test_custom_threshold(self):
        self.assertEqual(suppress_small_cell(4, self.conf_prog, threshold=5), "< 5")
        self.assertEqual(suppress_small_cell(5, self.conf_prog, threshold=5), 5)
