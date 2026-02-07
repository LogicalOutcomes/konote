"""Tests for CONF9 program context switcher (multi-tier staff).

When a user has roles in both Standard and Confidential programs,
the system forces them to select an active program context. This
filters client lists to show only clients from the active program.
"""
from django.test import Client, TestCase, override_settings

from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.context import (
    SESSION_KEY,
    clear_active_program,
    get_active_program_ids,
    get_switcher_options,
    get_user_program_tiers,
    needs_program_selection,
    needs_program_selector,
    set_active_program,
)
from apps.programs.models import Program, UserProgramRole

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramContextHelpersTest(TestCase):
    """Test the pure helper functions in apps/programs/context.py."""

    def setUp(self):
        enc_module._fernet = None

        # Users
        self.single_standard_user = User.objects.create_user(
            username="single_std", password="testpass123",
        )
        self.multi_standard_user = User.objects.create_user(
            username="multi_std", password="testpass123",
        )
        self.single_confidential_user = User.objects.create_user(
            username="single_conf", password="testpass123",
        )
        self.mixed_user = User.objects.create_user(
            username="mixed", password="testpass123",
        )
        self.multi_conf_user = User.objects.create_user(
            username="multi_conf", password="testpass123",
        )

        # Programs
        self.employment = Program.objects.create(name="Employment", colour_hex="#10B981")
        self.housing = Program.objects.create(name="Housing", colour_hex="#3B82F6")
        self.counselling = Program.objects.create(
            name="Counselling", colour_hex="#EF4444", is_confidential=True,
        )
        self.dv_support = Program.objects.create(
            name="Community Support", colour_hex="#F59E0B", is_confidential=True,
        )

        # Roles
        UserProgramRole.objects.create(
            user=self.single_standard_user, program=self.employment, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.multi_standard_user, program=self.employment, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.multi_standard_user, program=self.housing, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.single_confidential_user, program=self.counselling, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.employment, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.counselling, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.multi_conf_user, program=self.counselling, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.multi_conf_user, program=self.dv_support, role="program_manager",
        )

    def tearDown(self):
        enc_module._fernet = None

    # --- get_user_program_tiers ---

    def test_tiers_standard_only(self):
        tiers = get_user_program_tiers(self.multi_standard_user)
        self.assertEqual(len(tiers["standard"]), 2)
        self.assertEqual(len(tiers["confidential"]), 0)

    def test_tiers_mixed(self):
        tiers = get_user_program_tiers(self.mixed_user)
        self.assertEqual(len(tiers["standard"]), 1)
        self.assertEqual(len(tiers["confidential"]), 1)
        self.assertEqual(tiers["standard"][0]["name"], "Employment")
        self.assertEqual(tiers["confidential"][0]["name"], "Counselling")

    def test_tiers_multi_confidential(self):
        tiers = get_user_program_tiers(self.multi_conf_user)
        self.assertEqual(len(tiers["confidential"]), 2)

    # --- needs_program_selector ---

    def test_single_standard_no_selector(self):
        self.assertFalse(needs_program_selector(self.single_standard_user))

    def test_multi_standard_no_selector(self):
        self.assertFalse(needs_program_selector(self.multi_standard_user))

    def test_single_confidential_no_selector(self):
        self.assertFalse(needs_program_selector(self.single_confidential_user))

    def test_mixed_needs_selector(self):
        self.assertTrue(needs_program_selector(self.mixed_user))

    def test_multi_confidential_needs_selector(self):
        self.assertTrue(needs_program_selector(self.multi_conf_user))

    # --- needs_program_selection ---

    def test_no_selection_needed_for_standard_only(self):
        session = {}
        self.assertFalse(needs_program_selection(self.multi_standard_user, session))

    def test_selection_needed_for_mixed_no_session(self):
        session = {}
        self.assertTrue(needs_program_selection(self.mixed_user, session))

    def test_selection_not_needed_after_valid_choice(self):
        session = {SESSION_KEY: self.employment.pk}
        self.assertFalse(needs_program_selection(self.mixed_user, session))

    def test_selection_needed_if_session_has_invalid_program(self):
        session = {SESSION_KEY: 99999}
        self.assertTrue(needs_program_selection(self.mixed_user, session))

    # --- get_active_program_ids ---

    def test_standard_only_returns_all(self):
        session = {}
        ids = get_active_program_ids(self.multi_standard_user, session)
        self.assertEqual(ids, {self.employment.pk, self.housing.pk})

    def test_mixed_no_session_returns_empty(self):
        session = {}
        ids = get_active_program_ids(self.mixed_user, session)
        self.assertEqual(ids, set())

    def test_mixed_single_program_selected(self):
        session = {SESSION_KEY: self.counselling.pk}
        ids = get_active_program_ids(self.mixed_user, session)
        self.assertEqual(ids, {self.counselling.pk})

    def test_all_standard_option(self):
        # Give mixed user a second standard program
        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.housing, role="staff",
        )
        session = {SESSION_KEY: "all_standard"}
        ids = get_active_program_ids(self.mixed_user, session)
        self.assertEqual(ids, {self.employment.pk, self.housing.pk})

    def test_invalid_session_value_returns_empty(self):
        session = {SESSION_KEY: "garbage"}
        ids = get_active_program_ids(self.mixed_user, session)
        self.assertEqual(ids, set())

    # --- set/clear ---

    def test_set_and_clear(self):
        session = {}
        set_active_program(session, self.employment.pk)
        self.assertEqual(session[SESSION_KEY], self.employment.pk)
        clear_active_program(session)
        self.assertNotIn(SESSION_KEY, session)

    # --- get_switcher_options ---

    def test_switcher_options_mixed_user(self):
        options = get_switcher_options(self.mixed_user)
        values = [o["value"] for o in options]
        # 1 standard + 1 confidential = 2 options (no "all_standard" with only 1 standard)
        self.assertEqual(len(options), 2)
        self.assertIn(str(self.employment.pk), values)
        self.assertIn(str(self.counselling.pk), values)
        # No "all_standard" because only 1 standard program
        self.assertNotIn("all_standard", values)

    def test_switcher_options_all_standard_appears_with_2_plus(self):
        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.housing, role="staff",
        )
        options = get_switcher_options(self.mixed_user)
        values = [o["value"] for o in options]
        self.assertIn("all_standard", values)

    def test_switcher_never_has_all_confidential(self):
        options = get_switcher_options(self.multi_conf_user)
        values = [o["value"] for o in options]
        self.assertNotIn("all_confidential", values)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramSwitcherViewTest(TestCase):
    """Test the switch_program and select_program views."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.mixed_user = User.objects.create_user(
            username="mixed", password="testpass123",
        )
        self.standard_user = User.objects.create_user(
            username="std_only", password="testpass123",
        )

        self.employment = Program.objects.create(name="Employment", colour_hex="#10B981")
        self.counselling = Program.objects.create(
            name="Counselling", colour_hex="#EF4444", is_confidential=True,
        )
        self.housing = Program.objects.create(name="Housing", colour_hex="#3B82F6")

        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.employment, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.counselling, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.standard_user, program=self.employment, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.standard_user, program=self.housing, role="staff",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_select_program_page_renders(self):
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.get("/programs/select/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Employment")
        self.assertContains(resp, "Counselling")

    def test_switch_program_sets_session(self):
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.post("/programs/switch/", {
            "program": str(self.employment.pk),
            "next": "/",
        })
        self.assertEqual(resp.status_code, 302)
        # Session should now have the program
        session = self.http.session
        self.assertEqual(session[SESSION_KEY], self.employment.pk)

    def test_switch_to_unassigned_program_rejected(self):
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.post("/programs/switch/", {
            "program": str(self.housing.pk),  # mixed_user has no role here
            "next": "/",
        })
        self.assertEqual(resp.status_code, 403)

    def test_switch_to_all_standard(self):
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.post("/programs/switch/", {
            "program": "all_standard",
            "next": "/",
        })
        self.assertEqual(resp.status_code, 302)
        session = self.http.session
        self.assertEqual(session[SESSION_KEY], "all_standard")

    def test_switch_program_get_not_allowed(self):
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.get("/programs/switch/")
        self.assertEqual(resp.status_code, 405)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ForcedSelectionRedirectTest(TestCase):
    """Test that mixed-tier users are redirected to select a program."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.mixed_user = User.objects.create_user(
            username="mixed", password="testpass123",
        )
        self.standard_user = User.objects.create_user(
            username="std_only", password="testpass123",
        )

        self.employment = Program.objects.create(name="Employment", colour_hex="#10B981")
        self.counselling = Program.objects.create(
            name="Counselling", colour_hex="#EF4444", is_confidential=True,
        )

        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.employment, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.counselling, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.standard_user, program=self.employment, role="staff",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_mixed_user_redirected_to_select(self):
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/programs/select/", resp.url)

    def test_standard_user_not_redirected(self):
        self.http.login(username="std_only", password="testpass123")
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_select_page_not_redirected(self):
        """The select page itself must not redirect (would be infinite loop)."""
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.get("/programs/select/")
        self.assertEqual(resp.status_code, 200)

    def test_switch_url_not_redirected(self):
        """The switch endpoint must not be blocked by the redirect."""
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.post("/programs/switch/", {
            "program": str(self.employment.pk),
            "next": "/",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("/programs/select/", resp.url)

    def test_auth_urls_not_redirected(self):
        """Logout and other auth URLs must still work."""
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.get("/auth/logout/")
        self.assertNotEqual(resp.status_code, 403)

    def test_merge_url_not_blocked(self):
        """MATCH4: Merge tool must not be blocked by program selection."""
        self.http.login(username="mixed", password="testpass123")
        resp = self.http.get("/merge/")
        # May 404 if merge tool not built yet, but should NOT redirect to /programs/select/
        if resp.status_code == 302:
            self.assertNotIn("/programs/select/", resp.url)

    def test_after_selection_no_redirect(self):
        """After selecting a program, user should access home normally."""
        self.http.login(username="mixed", password="testpass123")
        # Select a program
        self.http.post("/programs/switch/", {
            "program": str(self.employment.pk),
            "next": "/",
        })
        # Now home should work
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ClientFilteringByActiveProgram(TestCase):
    """Test that client lists respect the active program context."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.mixed_user = User.objects.create_user(
            username="mixed", password="testpass123",
        )

        self.employment = Program.objects.create(name="Employment", colour_hex="#10B981")
        self.counselling = Program.objects.create(
            name="Counselling", colour_hex="#EF4444", is_confidential=True,
        )

        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.employment, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.mixed_user, program=self.counselling, role="staff",
        )

        # Client in standard program
        self.std_client = ClientFile()
        self.std_client.first_name = "Alice"
        self.std_client.last_name = "Standard"
        self.std_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.std_client, program=self.employment,
        )

        # Client in confidential program
        self.conf_client = ClientFile()
        self.conf_client.first_name = "Bob"
        self.conf_client.last_name = "Confidential"
        self.conf_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.conf_client, program=self.counselling,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_standard_context_shows_only_standard_clients(self):
        self.http.login(username="mixed", password="testpass123")
        self.http.post("/programs/switch/", {
            "program": str(self.employment.pk), "next": "/",
        })
        resp = self.http.get("/clients/")
        self.assertContains(resp, "Alice")
        self.assertNotContains(resp, "Bob")

    def test_confidential_context_shows_only_confidential_clients(self):
        self.http.login(username="mixed", password="testpass123")
        self.http.post("/programs/switch/", {
            "program": str(self.counselling.pk), "next": "/",
        })
        resp = self.http.get("/clients/")
        self.assertContains(resp, "Bob")
        self.assertNotContains(resp, "Alice")

    def test_all_standard_excludes_confidential(self):
        self.http.login(username="mixed", password="testpass123")
        self.http.post("/programs/switch/", {
            "program": "all_standard", "next": "/",
        })
        resp = self.http.get("/clients/")
        self.assertContains(resp, "Alice")
        self.assertNotContains(resp, "Bob")

    def test_client_detail_accessible_regardless_of_context(self):
        """Direct URL to a client the user has legitimate access to should work."""
        self.http.login(username="mixed", password="testpass123")
        # Select standard context
        self.http.post("/programs/switch/", {
            "program": str(self.employment.pk), "next": "/",
        })
        # Should still access confidential client by direct URL
        # (middleware checks all programs, not just active)
        resp = self.http.get(f"/clients/{self.conf_client.pk}/")
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RoleRemovedClearsSessionTest(TestCase):
    """Test that stale session values are handled gracefully."""

    def setUp(self):
        enc_module._fernet = None

        self.user = User.objects.create_user(
            username="mixed", password="testpass123",
        )
        self.employment = Program.objects.create(name="Employment", colour_hex="#10B981")
        self.counselling = Program.objects.create(
            name="Counselling", colour_hex="#EF4444", is_confidential=True,
        )

        self.std_role = UserProgramRole.objects.create(
            user=self.user, program=self.employment, role="staff",
        )
        self.conf_role = UserProgramRole.objects.create(
            user=self.user, program=self.counselling, role="staff",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_removed_role_invalidates_session(self):
        session = {SESSION_KEY: self.counselling.pk}
        self.assertFalse(needs_program_selection(self.user, session))

        # Admin removes the role
        self.conf_role.status = "removed"
        self.conf_role.save()

        # User no longer needs selector (only 1 active program)
        self.assertFalse(needs_program_selector(self.user))

    def test_archived_program_invalidates_session(self):
        session = {SESSION_KEY: self.counselling.pk}
        self.assertFalse(needs_program_selection(self.user, session))

        # Program archived
        self.counselling.status = "archived"
        self.counselling.save()

        # Now user only has 1 active program — no selector needed
        self.assertFalse(needs_program_selector(self.user))
