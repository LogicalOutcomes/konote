"""Regression tests for the admin config generator view under CSP."""

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings

from apps.auth_app.models import User
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConfigGeneratorViewTest(TestCase):
    """Ensure the admin config generator renders with a CSP-safe script tag."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_admin=True,
            display_name="Admin",
        )
        self.staff = User.objects.create_user(
            username="staff",
            password="testpass123",
            is_admin=False,
            display_name="Staff",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_view_injects_nonce_into_script_tag(self):
        self.client.login(username="admin", password="testpass123")

        response = self.client.get("/admin/settings/config-generator/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "KoNote Configuration Generator")
        self.assertIn(b'<script nonce="', response.content)
        self.assertIn("Content-Security-Policy", response.headers)
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("script-src 'self' https://unpkg.com https://cdn.jsdelivr.net", csp)
        self.assertNotIn("script-src-attr", csp)

    def test_non_admin_cannot_access_generator(self):
        self.client.login(username="staff", password="testpass123")

        response = self.client.get("/admin/settings/config-generator/")

        self.assertEqual(response.status_code, 403)