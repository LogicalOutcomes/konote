"""Tests for program CRUD views."""
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramViewsTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)

    def test_admin_can_list_programs(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/programs/")
        self.assertEqual(resp.status_code, 200)

    def test_nonadmin_can_list_assigned_programs(self):
        """Non-admin users can view the programs list (filtered to their assignments)."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/programs/")
        self.assertEqual(resp.status_code, 200)

    def test_nonadmin_sees_all_programs_in_list(self):
        """Non-admin users see all programs in the list (access controlled at detail level)."""
        prog1 = Program.objects.create(name="Assigned Program")
        prog2 = Program.objects.create(name="Other Program")
        UserProgramRole.objects.create(user=self.staff, program=prog1, role="staff", status="active")
        # staff is NOT assigned to prog2

        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/programs/")
        self.assertEqual(resp.status_code, 200)
        # Non-admins now see ALL programs in the list
        self.assertContains(resp, "Assigned Program")
        self.assertContains(resp, "Other Program")

    def test_admin_can_create_program(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/programs/create/", {
            "name": "Housing",
            "description": "Housing support",
            "colour_hex": "#10B981",
            "service_model": "individual",
            "status": "active",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Program.objects.filter(name="Housing").exists())

    def test_nonadmin_cannot_create_program(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post("/programs/create/", {
            "name": "Housing",
            "description": "Housing support",
            "colour_hex": "#10B981",
            "status": "active",
        })
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_edit_program(self):
        self.client.login(username="admin", password="testpass123")
        prog = Program.objects.create(name="Youth", colour_hex="#3B82F6")
        resp = self.client.post(f"/programs/{prog.pk}/edit/", {
            "name": "Youth Services",
            "description": "",
            "colour_hex": "#3B82F6",
            "service_model": "both",
            "status": "active",
        })
        self.assertEqual(resp.status_code, 302)
        prog.refresh_from_db()
        self.assertEqual(prog.name, "Youth Services")

    def test_admin_can_view_program_detail(self):
        self.client.login(username="admin", password="testpass123")
        prog = Program.objects.create(name="Employment")
        resp = self.client.get(f"/programs/{prog.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_add_role(self):
        self.client.login(username="admin", password="testpass123")
        prog = Program.objects.create(name="Housing")
        resp = self.client.post(f"/programs/{prog.pk}/roles/add/", {
            "user": self.staff.pk,
            "role": "staff",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(UserProgramRole.objects.filter(user=self.staff, program=prog, status="active").exists())

    def test_admin_can_remove_role(self):
        self.client.login(username="admin", password="testpass123")
        prog = Program.objects.create(name="Housing")
        role = UserProgramRole.objects.create(user=self.staff, program=prog, role="staff")
        resp = self.client.post(f"/programs/{prog.pk}/roles/{role.pk}/remove/")
        self.assertEqual(resp.status_code, 200)
        role.refresh_from_db()
        self.assertEqual(role.status, "removed")

    def test_nonadmin_can_view_assigned_program_detail(self):
        """Non-admin users can view detail of programs they're assigned to."""
        prog = Program.objects.create(name="Assigned Program")
        UserProgramRole.objects.create(user=self.staff, program=prog, role="staff", status="active")
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/programs/{prog.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Assigned Program")

    def test_nonadmin_sees_friendly_message_for_unassigned_program(self):
        """Non-admin users see a friendly permission message for programs they're not assigned to."""
        prog = Program.objects.create(name="Other Program")
        # staff is NOT assigned to this program
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/programs/{prog.pk}/")
        self.assertEqual(resp.status_code, 200)  # Not 403 - shows friendly page
        self.assertContains(resp, "don't have permission")

    def test_program_list_shows_all_programs_to_nonadmin(self):
        """Non-admin users see all programs in the list (not just their assigned ones)."""
        prog1 = Program.objects.create(name="Assigned Program")
        prog2 = Program.objects.create(name="Other Program")
        UserProgramRole.objects.create(user=self.staff, program=prog1, role="staff", status="active")
        # staff is NOT assigned to prog2
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/programs/")
        self.assertEqual(resp.status_code, 200)
        # Should see both programs
        self.assertContains(resp, "Assigned Program")
        self.assertContains(resp, "Other Program")

    def test_program_list_shows_manager_name(self):
        """Program list displays the manager name for each program."""
        prog = Program.objects.create(name="Test Program")
        manager = User.objects.create_user(username="manager", password="testpass123", is_admin=False)
        manager.display_name = "Jane Manager"
        manager.save()
        UserProgramRole.objects.create(user=manager, program=prog, role="program_manager", status="active")
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/programs/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jane Manager")
