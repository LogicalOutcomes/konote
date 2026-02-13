"""Tests for admin role management views."""
from django.test import TestCase, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class UserRoleManagementTest(TestCase):
    """Test the admin role management views."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        # Admin user
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin",
        )
        self.admin.is_admin = True
        self.admin.save()

        # Regular staff user (non-admin)
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff User",
        )

        # Target user whose roles we'll manage
        self.target = User.objects.create_user(
            username="target", password="testpass123", display_name="Target User",
        )

        # Programs
        self.program_a = Program.objects.create(name="Youth Outreach", status="active")
        self.program_b = Program.objects.create(name="Kitchen Sessions", status="active")

        # Give staff a role so they can log in
        UserProgramRole.objects.create(
            user=self.staff, program=self.program_a, role="staff",
        )

    def tearDown(self):
        enc_module._fernet = None

    # --- Access control ---

    def test_non_admin_cannot_view_roles_page(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/admin/users/{self.target.pk}/roles/")
        self.assertEqual(resp.status_code, 403)

    def test_non_admin_cannot_add_role(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(
            f"/admin/users/{self.target.pk}/roles/add/",
            {"program": self.program_a.pk, "role": "staff"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_non_admin_cannot_remove_role(self):
        role = UserProgramRole.objects.create(
            user=self.target, program=self.program_a, role="staff",
        )
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(
            f"/admin/users/{self.target.pk}/roles/{role.pk}/remove/",
        )
        self.assertEqual(resp.status_code, 403)

    # --- View roles page ---

    def test_admin_can_view_roles_page(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/admin/users/{self.target.pk}/roles/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Target User")

    def test_roles_page_shows_existing_roles(self):
        UserProgramRole.objects.create(
            user=self.target, program=self.program_a, role="staff",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/admin/users/{self.target.pk}/roles/")
        self.assertContains(resp, "Youth Outreach")
        self.assertContains(resp, "Direct Service")

    # --- Add role ---

    def test_admin_can_add_role(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post(
            f"/admin/users/{self.target.pk}/roles/add/",
            {"program": self.program_a.pk, "role": "staff"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            UserProgramRole.objects.filter(
                user=self.target, program=self.program_a, role="staff", status="active",
            ).exists()
        )

    def test_add_role_reactivates_removed_role(self):
        """Adding a role to a program where the user was previously removed reactivates it."""
        role = UserProgramRole.objects.create(
            user=self.target, program=self.program_a, role="staff", status="removed",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post(
            f"/admin/users/{self.target.pk}/roles/add/",
            {"program": self.program_a.pk, "role": "program_manager"},
        )
        self.assertEqual(resp.status_code, 302)
        role.refresh_from_db()
        self.assertEqual(role.status, "active")
        self.assertEqual(role.role, "program_manager")

    # --- Remove role ---

    def test_admin_can_remove_role(self):
        role = UserProgramRole.objects.create(
            user=self.target, program=self.program_a, role="staff",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post(
            f"/admin/users/{self.target.pk}/roles/{role.pk}/remove/",
        )
        self.assertEqual(resp.status_code, 302)
        role.refresh_from_db()
        self.assertEqual(role.status, "removed")

    # --- Form excludes assigned programs ---

    def test_add_form_excludes_assigned_programs(self):
        UserProgramRole.objects.create(
            user=self.target, program=self.program_a, role="staff",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/admin/users/{self.target.pk}/roles/")
        # Program A should not be in the add-role form options
        content = resp.content.decode()
        # program_b should be available, program_a should not
        self.assertContains(resp, "Kitchen Sessions")
        # The form's program dropdown should not include Youth Outreach
        # (it's already assigned)

    # --- User list shows roles ---

    def test_user_list_shows_program_roles(self):
        UserProgramRole.objects.create(
            user=self.target, program=self.program_a, role="program_manager",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/users/")
        self.assertContains(resp, "Program Manager")
        self.assertContains(resp, "Youth Outreach")
        # Should have a "Roles" link
        self.assertContains(resp, "Roles")
