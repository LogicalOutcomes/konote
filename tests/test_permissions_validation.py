"""Tests for permissions matrix completeness and demo user role validation.

These tests ensure that:
1. The permissions matrix is internally consistent (all roles have all keys).
2. Every permission key in the code maps to a valid level.
3. Demo users have exactly the expected role assignments.
4. The validate_permissions management command works correctly.

Run with:
    pytest tests/test_permissions_validation.py
"""
from io import StringIO

from cryptography.fernet import Fernet
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.auth_app.permissions import (
    ALLOW,
    DENY,
    GATED,
    PERMISSIONS,
    PER_FIELD,
    PROGRAM,
    validate_permissions,
)
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()

# Valid permission levels ΓÇö anything else is a bug
VALID_LEVELS = {ALLOW, DENY, PROGRAM, GATED, PER_FIELD}

# The four roles that must exist
EXPECTED_ROLES = {"receptionist", "staff", "program_manager", "executive"}


class PermissionsMatrixCompletenessTest(TestCase):
    """Validate the permissions matrix is internally consistent."""

    def test_all_roles_present(self):
        """All four roles must be defined in the PERMISSIONS dict."""
        for role in EXPECTED_ROLES:
            self.assertIn(role, PERMISSIONS, f"Role '{role}' missing from PERMISSIONS")

    def test_all_roles_have_same_keys(self):
        """Every role must define exactly the same set of permission keys."""
        all_keys = set()
        for role_perms in PERMISSIONS.values():
            all_keys.update(role_perms.keys())

        for role in EXPECTED_ROLES:
            role_keys = set(PERMISSIONS[role].keys())
            missing = all_keys - role_keys
            extra = role_keys - all_keys
            self.assertEqual(
                missing, set(),
                f"Role '{role}' is missing keys: {sorted(missing)}"
            )
            self.assertEqual(
                extra, set(),
                f"Role '{role}' has extra keys not in other roles: {sorted(extra)}"
            )

    def test_all_values_are_valid_levels(self):
        """Every permission value must be one of the defined levels."""
        for role, perms in PERMISSIONS.items():
            for key, level in perms.items():
                self.assertIn(
                    level, VALID_LEVELS,
                    f"Invalid level '{level}' for {role}.{key}"
                )

    def test_validate_permissions_function_passes(self):
        """The validate_permissions() function should report success."""
        is_valid, errors = validate_permissions()
        self.assertTrue(is_valid, f"Validation failed: {errors}")

    def test_no_unexpected_roles(self):
        """No extra roles beyond the expected four."""
        extra = set(PERMISSIONS.keys()) - EXPECTED_ROLES
        self.assertEqual(
            extra, set(),
            f"Unexpected roles in PERMISSIONS: {extra}"
        )


class PermissionsDesignRulesTest(TestCase):
    """Validate design rules that should hold across the matrix."""

    def test_executive_has_no_client_data_access(self):
        """Executives must DENY all individual client data permissions."""
        client_keys = [
            "client.view_name", "client.view_contact", "client.view_safety",
            "client.view_medications", "client.view_clinical",
            "client.edit", "client.create", "client.edit_contact",
            "client.transfer",
            "note.view", "note.create", "note.edit",
            "plan.view", "plan.edit",
            "event.view", "event.create",
            "circle.view", "circle.create", "circle.edit",
        ]
        exec_perms = PERMISSIONS["executive"]
        for key in client_keys:
            self.assertEqual(
                exec_perms.get(key), DENY,
                f"Executive should DENY '{key}' but has '{exec_perms.get(key)}'"
            )

    def test_receptionist_denies_clinical(self):
        """Front desk must DENY all clinical data access."""
        clinical_keys = [
            "client.view_medications", "client.view_clinical",
            "note.view", "note.create", "note.edit",
            "plan.view", "plan.edit",
            "circle.view", "circle.create", "circle.edit",
            "group.view_roster", "group.view_detail",
        ]
        fd_perms = PERMISSIONS["receptionist"]
        for key in clinical_keys:
            self.assertEqual(
                fd_perms.get(key), DENY,
                f"Receptionist should DENY '{key}' but has '{fd_perms.get(key)}'"
            )

    def test_receptionist_allows_safety_info(self):
        """Front desk MUST see names, contact, and safety info (life-critical)."""
        safety_keys = [
            "client.view_name", "client.view_contact", "client.view_safety",
        ]
        fd_perms = PERMISSIONS["receptionist"]
        for key in safety_keys:
            self.assertEqual(
                fd_perms.get(key), ALLOW,
                f"Receptionist MUST ALLOW '{key}' (safety critical)"
            )

    def test_all_destructive_actions_denied(self):
        """Delete permissions should be DENY for all roles."""
        destructive_keys = ["note.delete", "client.delete", "plan.delete"]
        for role in EXPECTED_ROLES:
            for key in destructive_keys:
                self.assertEqual(
                    PERMISSIONS[role].get(key), DENY,
                    f"{role} should DENY '{key}'"
                )

    def test_staff_cannot_manage_suggestion_themes(self):
        """Staff can view suggestion themes but not create/edit/link them."""
        self.assertNotEqual(
            PERMISSIONS["staff"]["suggestion_theme.view"], DENY,
            "Staff should be able to view suggestion themes"
        )
        self.assertEqual(
            PERMISSIONS["staff"]["suggestion_theme.manage"], DENY,
            "Staff should not manage suggestion themes"
        )

    def test_pm_clinical_data_is_gated(self):
        """PM access to clinical data, notes, and plans must be GATED."""
        gated_keys = [
            "client.view_clinical", "note.view", "plan.view",
        ]
        pm_perms = PERMISSIONS["program_manager"]
        for key in gated_keys:
            self.assertEqual(
                pm_perms.get(key), GATED,
                f"PM '{key}' should be GATED (clinical safeguards) "
                f"but is '{pm_perms.get(key)}'"
            )

    def test_alert_two_person_rule(self):
        """Staff can recommend cancel but not cancel; PM can cancel but not recommend."""
        staff = PERMISSIONS["staff"]
        pm = PERMISSIONS["program_manager"]

        self.assertEqual(staff["alert.cancel"], DENY)
        self.assertNotEqual(staff["alert.recommend_cancel"], DENY)
        self.assertNotEqual(pm["alert.cancel"], DENY)
        self.assertEqual(pm["alert.recommend_cancel"], DENY)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DemoUserRoleValidationTest(TestCase):
    """Validate demo user role assignments match the expected configuration.

    This test seeds the demo database and then checks that the
    EXPECTED_DEMO_ROLES dictionary in the validate_permissions command
    matches what seed.py actually creates.
    """

    databases = {"default", "audit"}

    @classmethod
    def setUpClass(cls):
        """Seed demo data once for all tests in this class."""
        super().setUpClass()
        enc_module._fernet = None

    def setUp(self):
        enc_module._fernet = None
        from django.conf import settings
        # Only run seed in DEMO_MODE
        self._original_demo = getattr(settings, "DEMO_MODE", False)
        settings.DEMO_MODE = True

    def tearDown(self):
        from django.conf import settings
        settings.DEMO_MODE = self._original_demo
        enc_module._fernet = None

    def test_demo_seed_and_validate(self):
        """Seed demo data and run --demo validation without errors."""
        # Seed
        out = StringIO()
        call_command("seed", stdout=out, stderr=StringIO())

        # Validate
        out = StringIO()
        result = call_command("validate_permissions", "--demo", stdout=out, stderr=StringIO())
        output = out.getvalue()

        # Should report all correct
        self.assertNotIn("MISSING", output, f"Missing roles found:\n{output}")
        self.assertNotIn("UNEXPECTED", output, f"Unexpected roles found:\n{output}")
        self.assertNotIn("NOT FOUND", output, f"Users not found:\n{output}")


class ValidatePermissionsCommandTest(TestCase):
    """Test the management command runs without errors."""

    def test_matrix_validation_passes(self):
        """The command should succeed for matrix-only validation."""
        out = StringIO()
        result = call_command("validate_permissions", stdout=out)
        self.assertEqual(result, 0)
        self.assertIn("[OK]", out.getvalue())

    @override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
    def test_user_flag_shows_permissions(self):
        """--user should show permissions for an existing user."""
        from apps.auth_app.models import User
        from apps.programs.models import Program, UserProgramRole

        enc_module._fernet = None
        user = User.objects.create_user(
            username="test-perm-user", password="test1234",
            display_name="Test User",
        )
        prog = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(user=user, program=prog, role="staff")

        out = StringIO()
        call_command("validate_permissions", "--user", "test-perm-user", stdout=out)
        output = out.getvalue()

        self.assertIn("Test User", output)
        self.assertIn("Test Program", output)
        self.assertIn("Direct Service", output)

    def test_user_flag_handles_missing_user(self):
        """--user should handle a non-existent username gracefully."""
        out = StringIO()
        call_command("validate_permissions", "--user", "nonexistent-user", stdout=out)
        self.assertIn("not found", out.getvalue())
