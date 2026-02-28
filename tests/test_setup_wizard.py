"""Tests for the setup wizard UI."""
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SetupWizardAccessTest(TestCase):
    """Test that only admins can access the setup wizard."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False
        )

    def test_admin_can_access_wizard(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/setup-wizard/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Setup Wizard")

    def test_staff_cannot_access_wizard(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/admin/settings/setup-wizard/")
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get("/admin/settings/setup-wizard/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SetupWizardNavigationTest(TestCase):
    """Test wizard step navigation."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.client.login(username="admin", password="testpass123")

    def test_default_step_is_instance_settings(self):
        resp = self.client.get("/admin/settings/setup-wizard/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Step 1")
        self.assertContains(resp, "Instance Settings")

    def test_can_access_each_step(self):
        steps = [
            ("instance_settings", "Step 1"),
            ("terminology", "Step 2"),
            ("features", "Step 3"),
            ("programs", "Step 4"),
            ("metrics", "Step 5"),
            ("plan_templates", "Step 6"),
            ("custom_fields", "Step 7"),
            ("review", "Step 8"),
        ]
        for step_name, step_label in steps:
            resp = self.client.get(f"/admin/settings/setup-wizard/{step_name}/")
            self.assertEqual(resp.status_code, 200, f"Step {step_name} failed")
            self.assertContains(resp, step_label)

    def test_invalid_step_redirects(self):
        resp = self.client.get("/admin/settings/setup-wizard/nonexistent/")
        self.assertEqual(resp.status_code, 302)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SetupWizardFormTest(TestCase):
    """Test wizard form submissions and session storage."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.client.login(username="admin", password="testpass123")

    def test_instance_settings_post_redirects_to_terminology(self):
        resp = self.client.post("/admin/settings/setup-wizard/instance_settings/", {
            "product_name": "TestNote",
            "support_email": "test@example.ca",
            "logo_url": "",
            "date_format": "YYYY-MM-DD",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("terminology", resp.url)

    def test_instance_settings_stored_in_session(self):
        self.client.post("/admin/settings/setup-wizard/instance_settings/", {
            "product_name": "TestNote",
            "support_email": "test@example.ca",
            "logo_url": "",
            "date_format": "YYYY-MM-DD",
        })
        session = self.client.session
        wizard_data = session.get("setup_wizard", {})
        self.assertIn("instance_settings", wizard_data)
        self.assertEqual(wizard_data["instance_settings"]["product_name"], "TestNote")

    def test_features_post_redirects_to_programs(self):
        resp = self.client.post("/admin/settings/setup-wizard/features/", {
            "feature_programs": "on",
            "feature_custom_fields": "on",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("programs", resp.url)

    def test_programs_post_collects_data(self):
        resp = self.client.post("/admin/settings/setup-wizard/programs/", {
            "program_name": ["Youth Housing", "Mental Health"],
            "program_description": ["Housing program", "MH program"],
            "program_colour": ["#3B82F6", "#EF4444"],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("metrics", resp.url)
        wizard_data = self.client.session.get("setup_wizard", {})
        self.assertEqual(len(wizard_data.get("programs", [])), 2)

    def test_plan_templates_post_redirects(self):
        resp = self.client.post("/admin/settings/setup-wizard/plan_templates/", {
            "template_name": ["Basic Plan"],
            "template_description": ["A basic plan template"],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("custom_fields", resp.url)

    def test_custom_fields_post_redirects(self):
        resp = self.client.post("/admin/settings/setup-wizard/custom_fields/", {
            "group_title": ["Demographics"],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("review", resp.url)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SetupWizardResetTest(TestCase):
    """Test wizard reset functionality."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.client.login(username="admin", password="testpass123")

    def test_reset_clears_session_data(self):
        # First, store some wizard data
        self.client.post("/admin/settings/setup-wizard/instance_settings/", {
            "product_name": "TestNote",
            "support_email": "",
            "logo_url": "",
            "date_format": "YYYY-MM-DD",
        })
        # Verify data is stored
        self.assertIn("setup_wizard", self.client.session)

        # Reset
        resp = self.client.get("/admin/settings/setup-wizard/reset/")
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("setup_wizard", self.client.session)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SetupWizardApplyTest(TestCase):
    """Test the review step applies configuration."""
    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.client.login(username="admin", password="testpass123")

    def test_review_get_shows_preview(self):
        # Store some wizard data first
        session = self.client.session
        session["setup_wizard"] = {
            "instance_settings": {
                "product_name": "TestNote",
                "support_email": "test@example.ca",
            },
            "terminology": {"client": "Participant"},
            "features": {"programs": True},
        }
        session.save()

        resp = self.client.get("/admin/settings/setup-wizard/review/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Review")

    def test_review_post_applies_and_redirects(self):
        from apps.admin_settings.models import InstanceSetting

        # Store wizard data
        session = self.client.session
        session["setup_wizard"] = {
            "instance_settings": {
                "product_name": "TestNote",
                "support_email": "test@example.ca",
            },
        }
        session.save()

        resp = self.client.post("/admin/settings/setup-wizard/review/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("complete", resp.url)

        # Verify settings were applied
        setting = InstanceSetting.objects.get(setting_key="product_name")
        self.assertEqual(setting.setting_value, "TestNote")

    def test_complete_page_loads(self):
        session = self.client.session
        session["setup_wizard_summary"] = {"Instance settings": "2 configured"}
        session.save()

        resp = self.client.get("/admin/settings/setup-wizard/complete/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Setup Complete")

