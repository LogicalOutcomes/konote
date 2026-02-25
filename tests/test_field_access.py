"""Tests for field access configuration (WP1 — PERM-P8)."""
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.admin_settings.models import InstanceSetting
from apps.auth_app.models import User
from apps.clients.models import (
    ClientFile,
    ClientProgramEnrolment,
    CustomFieldDefinition,
    CustomFieldGroup,
    FieldAccessConfig,
)
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FieldAccessConfigGetAccessTest(TestCase):
    """Tests for FieldAccessConfig.get_access() class method."""

    def setUp(self):
        enc_module._fernet = None

    def test_returns_safe_default_for_phone(self):
        """Phone defaults to 'edit' when no config row exists."""
        self.assertEqual(FieldAccessConfig.get_access("phone"), "edit")

    def test_returns_safe_default_for_email(self):
        """Email defaults to 'edit' when no config row exists."""
        self.assertEqual(FieldAccessConfig.get_access("email"), "edit")

    def test_returns_safe_default_for_birth_date(self):
        """Birth date defaults to 'none' (hidden) when no config row exists."""
        self.assertEqual(FieldAccessConfig.get_access("birth_date"), "none")

    def test_returns_safe_default_for_preferred_name(self):
        """Preferred name defaults to 'view' when no config row exists."""
        self.assertEqual(FieldAccessConfig.get_access("preferred_name"), "view")

    def test_returns_none_for_unknown_field(self):
        """Unknown fields default to 'none' (hidden)."""
        self.assertEqual(FieldAccessConfig.get_access("unknown_field"), "none")

    def test_returns_stored_config(self):
        """Returns the stored access level when a config row exists."""
        FieldAccessConfig.objects.create(field_name="phone", front_desk_access="view")
        self.assertEqual(FieldAccessConfig.get_access("phone"), "view")

    def test_stored_config_overrides_default(self):
        """Stored config takes precedence over safe defaults."""
        FieldAccessConfig.objects.create(field_name="birth_date", front_desk_access="edit")
        self.assertEqual(FieldAccessConfig.get_access("birth_date"), "edit")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FieldAccessConfigGetAllAccessTest(TestCase):
    """Tests for FieldAccessConfig.get_all_access() class method."""

    def setUp(self):
        enc_module._fernet = None

    def test_returns_safe_defaults_when_empty(self):
        """Returns SAFE_DEFAULTS when no config rows exist."""
        result = FieldAccessConfig.get_all_access()
        self.assertEqual(result, FieldAccessConfig.SAFE_DEFAULTS)

    def test_stored_config_merges_with_defaults(self):
        """Stored config values override defaults; unset fields keep defaults."""
        FieldAccessConfig.objects.create(field_name="phone", front_desk_access="none")
        result = FieldAccessConfig.get_all_access()
        self.assertEqual(result["phone"], "none")
        # Other defaults preserved
        self.assertEqual(result["email"], "edit")
        self.assertEqual(result["birth_date"], "none")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GetVisibleFieldsTest(TestCase):
    """Tests for ClientFile.get_visible_fields() with FieldAccessConfig."""

    def setUp(self):
        enc_module._fernet = None
        self.cf = ClientFile()
        self.cf.first_name = "Jane"
        self.cf.last_name = "Doe"
        self.cf.save()

    def test_receptionist_sees_always_visible_fields(self):
        """Receptionist always sees identity fields regardless of config."""
        visible = self.cf.get_visible_fields("receptionist")
        for field in FieldAccessConfig.ALWAYS_VISIBLE:
            self.assertTrue(visible.get(field), f"{field} should be visible")

    def test_receptionist_sees_phone_by_default(self):
        """Receptionist sees phone (safe default is 'edit')."""
        visible = self.cf.get_visible_fields("receptionist")
        self.assertTrue(visible.get("phone"))
        self.assertTrue(visible.get("phone_editable"))

    def test_receptionist_birth_date_hidden_by_default(self):
        """Receptionist cannot see birth_date by default (safe default is 'none')."""
        visible = self.cf.get_visible_fields("receptionist")
        self.assertFalse(visible.get("birth_date"))

    def test_receptionist_sees_birth_date_when_configured(self):
        """Receptionist sees birth_date when config is set to 'view'."""
        FieldAccessConfig.objects.create(field_name="birth_date", front_desk_access="view")
        visible = self.cf.get_visible_fields("receptionist")
        self.assertTrue(visible.get("birth_date"))
        self.assertFalse(visible.get("birth_date_editable"))

    def test_staff_sees_all_fields(self):
        """Staff role sees all fields as visible and editable."""
        visible = self.cf.get_visible_fields("staff")
        for field in ("first_name", "last_name", "phone", "email"):
            self.assertTrue(visible.get(field), f"{field} should be visible for staff")
            self.assertTrue(visible.get(f"{field}_editable"), f"{field} should be editable for staff")

    def test_program_manager_sees_all_fields(self):
        """Program manager sees all fields as visible and editable."""
        visible = self.cf.get_visible_fields("program_manager")
        self.assertTrue(visible.get("phone"))
        self.assertTrue(visible.get("email"))


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FieldAccessAdminViewTest(TestCase):
    """Tests for the field access admin page."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False,
        )
        self.prog = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.admin, program=self.prog, role="program_manager")
        UserProgramRole.objects.create(user=self.staff_user, program=self.prog, role="staff")

        # Set tier to 2 so the page is accessible
        InstanceSetting.objects.create(setting_key="access_tier", setting_value="2")

    def test_admin_can_view_field_access_page(self):
        """Admin at Tier 2 can view the field access page."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/field-access/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Field Access for Front Desk")
        self.assertContains(resp, "Phone Number")

    def test_admin_can_save_field_access(self):
        """Admin can save core field access changes."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/field-access/", {
            "core_phone": "view",
            "core_email": "none",
            "core_preferred_name": "edit",
            "core_birth_date": "view",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(FieldAccessConfig.get_access("phone"), "view")
        self.assertEqual(FieldAccessConfig.get_access("email"), "none")
        self.assertEqual(FieldAccessConfig.get_access("preferred_name"), "edit")
        self.assertEqual(FieldAccessConfig.get_access("birth_date"), "view")

    def test_admin_can_save_custom_field_access(self):
        """Admin can save custom field access changes."""
        group = CustomFieldGroup.objects.create(title="Demographics")
        cf = CustomFieldDefinition.objects.create(
            group=group, name="Pronouns", input_type="text",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/field-access/", {
            "core_phone": "edit",
            "core_email": "edit",
            "core_preferred_name": "view",
            "core_birth_date": "none",
            f"custom_{cf.pk}": "view",
        })
        self.assertEqual(resp.status_code, 302)
        cf.refresh_from_db()
        self.assertEqual(cf.front_desk_access, "view")

    def test_field_access_hidden_at_tier_1(self):
        """Field access page redirects at Tier 1."""
        InstanceSetting.objects.filter(setting_key="access_tier").update(setting_value="1")
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/field-access/")
        self.assertEqual(resp.status_code, 302)

    def test_non_admin_cannot_access(self):
        """Non-admin users get 403."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/admin/settings/field-access/")
        self.assertEqual(resp.status_code, 403)

    def test_dashboard_shows_field_access_card_at_tier_2(self):
        """Dashboard shows the field access card when tier is 2+."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Field Access for Front Desk")

    def test_dashboard_hides_field_access_card_at_tier_1(self):
        """Dashboard hides the field access card when tier is 1."""
        InstanceSetting.objects.filter(setting_key="access_tier").update(setting_value="1")
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Field Access for Front Desk")
