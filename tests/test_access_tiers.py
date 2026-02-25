"""Tests for access tier system (PERM-TIER1)."""
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.admin_settings.models import (
    ACCESS_TIER_CHOICES, InstanceSetting, get_access_tier,
)
from apps.auth_app.models import User
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GetAccessTierTest(TestCase):
    """Tests for the get_access_tier() helper function."""

    def setUp(self):
        enc_module._fernet = None

    def test_default_tier_is_1(self):
        """When no access_tier setting exists, default is Tier 1."""
        self.assertEqual(get_access_tier(), 1)

    def test_returns_stored_tier(self):
        """Returns the stored access tier as an integer."""
        InstanceSetting.objects.create(setting_key="access_tier", setting_value="2")
        self.assertEqual(get_access_tier(), 2)

    def test_tier_3(self):
        """Tier 3 (Clinical Safeguards) is returned correctly."""
        InstanceSetting.objects.create(setting_key="access_tier", setting_value="3")
        self.assertEqual(get_access_tier(), 3)

    def test_tier_choices_has_three_options(self):
        """ACCESS_TIER_CHOICES has exactly three tiers."""
        self.assertEqual(len(ACCESS_TIER_CHOICES), 3)
        values = [v for v, _ in ACCESS_TIER_CHOICES]
        self.assertEqual(values, ["1", "2", "3"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AccessTierAdminUITest(TestCase):
    """Tests for changing access tier through the instance settings page."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False,
        )

    def _post_settings(self, **overrides):
        """POST to instance settings with required fields + overrides."""
        data = {
            "access_tier": "1",
            "product_name": "TestApp",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
        }
        data.update(overrides)
        return self.client.post("/admin/settings/instance/", data)

    def test_instance_settings_page_shows_tier_radios(self):
        """The instance settings page renders access tier radio buttons."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/instance/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Access Tier")
        self.assertContains(resp, "Open Access")
        self.assertContains(resp, "Role-Based")
        self.assertContains(resp, "Clinical Safeguards")

    def test_admin_can_set_tier_2(self):
        """Admin can change access tier to Role-Based (Tier 2)."""
        self.client.login(username="admin", password="testpass123")
        resp = self._post_settings(access_tier="2")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(get_access_tier(), 2)

    def test_admin_can_set_tier_3(self):
        """Admin can change access tier to Clinical Safeguards (Tier 3)."""
        self.client.login(username="admin", password="testpass123")
        resp = self._post_settings(access_tier="3")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(get_access_tier(), 3)

    def test_admin_can_set_tier_1(self):
        """Admin can set access tier to Open Access (Tier 1)."""
        InstanceSetting.objects.create(setting_key="access_tier", setting_value="3")
        self.client.login(username="admin", password="testpass123")
        resp = self._post_settings(access_tier="1")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(get_access_tier(), 1)

    def test_staff_cannot_access_instance_settings(self):
        """Non-admin staff cannot view or change instance settings."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/admin/settings/instance/")
        self.assertEqual(resp.status_code, 403)

    def test_tier_persists_after_save(self):
        """Access tier value persists as an InstanceSetting record."""
        self.client.login(username="admin", password="testpass123")
        self._post_settings(access_tier="2")
        self.assertEqual(
            InstanceSetting.objects.get(setting_key="access_tier").setting_value,
            "2",
        )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AccessTierWizardTest(TestCase):
    """Tests for access tier in the setup wizard."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )

    def test_wizard_step1_shows_tier_options(self):
        """Setup wizard step 1 renders access tier radio buttons."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/setup-wizard/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Access Tier")
        self.assertContains(resp, "Open Access")
        self.assertContains(resp, "Clinical Safeguards")

    def test_wizard_stores_tier_in_session(self):
        """Posting step 1 stores access_tier in wizard session data."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/setup-wizard/", {
            "product_name": "TestOrg",
            "support_email": "help@test.ca",
            "date_format": "YYYY-MM-DD",
            "access_tier": "3",
        })
        self.assertEqual(resp.status_code, 302)
        # Check session data
        wizard_data = self.client.session.get("setup_wizard", {})
        self.assertEqual(wizard_data.get("instance_settings", {}).get("access_tier"), "3")

    def test_wizard_defaults_tier_to_1(self):
        """When no tier is selected, wizard defaults to Tier 1."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/setup-wizard/", {
            "product_name": "TestOrg",
        })
        self.assertEqual(resp.status_code, 302)
        wizard_data = self.client.session.get("setup_wizard", {})
        self.assertEqual(wizard_data.get("instance_settings", {}).get("access_tier"), "1")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AccessTierContextProcessorTest(TestCase):
    """Tests that access tier is available in template context."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )

    def test_site_context_includes_access_tier(self):
        """The site context variable includes access_tier."""
        InstanceSetting.objects.create(setting_key="access_tier", setting_value="2")
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/")
        # The context processor adds site.access_tier — check it's in the context
        self.assertEqual(resp.context["site"]["access_tier"], "2")

    def test_site_context_default_access_tier(self):
        """Without a stored tier, site context has no access_tier key (or empty)."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/")
        # access_tier is not in site dict when not set
        site = resp.context["site"]
        self.assertIn(site.get("access_tier", ""), ["", None])
