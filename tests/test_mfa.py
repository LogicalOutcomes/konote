"""Tests for MFA (TOTP) views — setup, verify, disable, and security fixes."""
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from apps.auth_app.models import User
from apps.auth_app.views import MFA_PENDING_EXPIRY_SECONDS
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class MFASecretEncryptionTest(TestCase):
    """Test that MFA secrets are Fernet-encrypted at rest (Fix 3)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="mfauser", password="testpass123", display_name="MFA User"
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_mfa_secret_stored_encrypted(self):
        self.user.mfa_secret = "JBSWY3DPEHPK3PXP"
        self.user.save(update_fields=["_mfa_secret_encrypted"])
        self.user.refresh_from_db()
        # The raw DB field should be non-empty binary (Fernet ciphertext)
        self.assertTrue(len(self.user._mfa_secret_encrypted) > 0)
        # The property should decrypt back to the original
        self.assertEqual(self.user.mfa_secret, "JBSWY3DPEHPK3PXP")

    def test_empty_mfa_secret_returns_empty_string(self):
        self.user.mfa_secret = ""
        self.user.save(update_fields=["_mfa_secret_encrypted"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.mfa_secret, "")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class MFABackupCodeHashTest(TestCase):
    """Test that backup codes are stored as SHA-256 hashes (Fix 4)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="mfauser", password="testpass123", display_name="MFA User"
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_set_backup_codes_stores_hashes(self):
        codes = ["abc12345", "def67890"]
        self.user.set_backup_codes(codes)
        # Stored values should be hex strings (SHA-256 = 64 chars), not plaintext
        for stored in self.user.mfa_backup_codes:
            self.assertEqual(len(stored), 64)
            self.assertNotIn(stored, codes)

    def test_check_backup_code_valid(self):
        codes = ["abc12345", "def67890"]
        self.user.set_backup_codes(codes)
        self.user.save()
        self.assertTrue(self.user.check_backup_code("abc12345"))
        # Code should be consumed
        self.assertEqual(len(self.user.mfa_backup_codes), 1)

    def test_check_backup_code_invalid(self):
        codes = ["abc12345"]
        self.user.set_backup_codes(codes)
        self.user.save()
        self.assertFalse(self.user.check_backup_code("wrong_code"))
        # No codes consumed
        self.assertEqual(len(self.user.mfa_backup_codes), 1)

    def test_check_backup_code_not_reusable(self):
        codes = ["abc12345"]
        self.user.set_backup_codes(codes)
        self.user.save()
        self.assertTrue(self.user.check_backup_code("abc12345"))
        self.assertFalse(self.user.check_backup_code("abc12345"))


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class MFAVerifyViewTest(TestCase):
    """Test the MFA verification view (Fixes 1, 6, 8, 9)."""

    databases = {"default", "audit"}

    def setUp(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()
        self.http = Client()
        self.user = User.objects.create_user(
            username="mfauser", password="testpass123", display_name="MFA User"
        )
        self.user.mfa_enabled = True
        self.user.mfa_secret = "JBSWY3DPEHPK3PXP"
        self.user.save(update_fields=["mfa_enabled", "_mfa_secret_encrypted"])

    def tearDown(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()

    def _start_mfa_session(self, expired=False):
        """Set up MFA pending session state."""
        session = self.http.session
        self.http.get("/auth/login/")  # Initialize session
        session = self.http.session
        session["_mfa_pending_user_id"] = self.user.pk
        if expired:
            session["_mfa_pending_at"] = timezone.now().timestamp() - MFA_PENDING_EXPIRY_SECONDS - 60
        else:
            session["_mfa_pending_at"] = timezone.now().timestamp()
        session.save()

    def test_no_pending_session_redirects_to_login(self):
        resp = self.http.get("/auth/mfa/verify/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_verify_page_renders_with_pending_session(self):
        self._start_mfa_session()
        resp = self.http.get("/auth/mfa/verify/")
        self.assertEqual(resp.status_code, 200)

    def test_expired_session_redirects_to_login(self):
        """MFA session older than 5 minutes should be rejected (Fix 6)."""
        self._start_mfa_session(expired=True)
        resp = self.http.get("/auth/mfa/verify/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_invalid_code_shows_translated_error(self):
        """Error message should be translated (Fix 8)."""
        self._start_mfa_session()
        resp = self.http.post("/auth/mfa/verify/", {"code": "000000"})
        self.assertEqual(resp.status_code, 200)
        # Should contain the error text (in English for default language)
        self.assertContains(resp, "Invalid verification code")

    @patch("apps.auth_app.views._verify_totp", return_value=True)
    def test_valid_totp_logs_in(self, mock_totp):
        """Valid TOTP code should complete login (Fix 9 helper)."""
        self._start_mfa_session()
        resp = self.http.post("/auth/mfa/verify/", {"code": "123456"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class MFASetupViewTest(TestCase):
    """Test MFA setup flow."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.user = User.objects.create_user(
            username="mfauser", password="testpass123", display_name="MFA User"
        )
        self.http.login(username="mfauser", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def test_setup_page_renders(self):
        resp = self.http.get("/auth/mfa/setup/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "secret")

    def test_already_enabled_redirects(self):
        self.user.mfa_enabled = True
        self.user.mfa_secret = "JBSWY3DPEHPK3PXP"
        self.user.save(update_fields=["mfa_enabled", "_mfa_secret_encrypted"])
        resp = self.http.get("/auth/mfa/setup/")
        self.assertEqual(resp.status_code, 302)

    @patch("apps.auth_app.views._verify_totp", return_value=True)
    def test_valid_code_enables_mfa(self, mock_totp):
        # First visit to generate a secret
        self.http.get("/auth/mfa/setup/")
        resp = self.http.post("/auth/mfa/setup/", {"code": "123456"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "backup")
        self.user.refresh_from_db()
        self.assertTrue(self.user.mfa_enabled)
        # Backup codes should be hashed (64-char hex strings)
        for stored in self.user.mfa_backup_codes:
            self.assertEqual(len(stored), 64)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class MFADisableViewTest(TestCase):
    """Test MFA disable flow."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.user = User.objects.create_user(
            username="mfauser", password="testpass123", display_name="MFA User"
        )
        self.user.mfa_enabled = True
        self.user.mfa_secret = "JBSWY3DPEHPK3PXP"
        self.user.set_backup_codes(["backup01"])
        self.user.save(update_fields=["mfa_enabled", "_mfa_secret_encrypted", "mfa_backup_codes"])
        self.http.login(username="mfauser", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def test_disable_page_renders(self):
        resp = self.http.get("/auth/mfa/disable/")
        self.assertEqual(resp.status_code, 200)

    @patch("apps.auth_app.views._verify_totp", return_value=True)
    def test_valid_code_disables_mfa(self, mock_totp):
        resp = self.http.post("/auth/mfa/disable/", {"code": "123456"})
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.mfa_enabled)
        self.assertEqual(self.user.mfa_secret, "")

    def test_invalid_code_shows_translated_error(self):
        resp = self.http.post("/auth/mfa/disable/", {"code": "000000"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid code")
