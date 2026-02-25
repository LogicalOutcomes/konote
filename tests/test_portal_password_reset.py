"""Tests for portal password reset flow (OPS3).

Covers: request code, confirm code, expired codes, rate limiting,
invalid email, account enumeration prevention, duplicate sends.

Run with:
    pytest tests/test_portal_password_reset.py -v
"""
from datetime import timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile
from apps.portal.models import ParticipantUser
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _enable_portal():
    FeatureToggle.objects.update_or_create(
        feature_key="participant_portal",
        defaults={"is_enabled": True},
    )


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-pwreset",
)
class PasswordResetRequestTests(TestCase):
    """Test POST /my/password/reset/ — requesting a reset code."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        _enable_portal()
        self.cf = ClientFile.objects.create(record_id="RST-001", status="active")
        self.cf.first_name = "Reset"
        self.cf.last_name = "Tester"
        self.cf.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="reset@example.com",
            client_file=self.cf,
            display_name="Reset P",
            password="oldpass123",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_get_shows_form(self):
        resp = self.client.get("/my/password/reset/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "email")

    @patch("django.core.mail.send_mail")
    def test_valid_email_sends_code(self, mock_send):
        resp = self.client.post("/my/password/reset/", {"email": "reset@example.com"})
        self.assertEqual(resp.status_code, 200)
        mock_send.assert_called_once()
        # Email should contain a 6-digit code
        body = mock_send.call_args[1].get("message") or mock_send.call_args[0][1]
        self.assertRegex(body, r"\d{6}")

    @patch("django.core.mail.send_mail")
    def test_code_stored_hashed(self, mock_send):
        self.client.post("/my/password/reset/", {"email": "reset@example.com"})
        self.participant.refresh_from_db()
        # Token hash should be set (not empty, not plaintext 6 digits)
        self.assertTrue(self.participant.password_reset_token_hash)
        self.assertFalse(self.participant.password_reset_token_hash.isdigit())

    @patch("django.core.mail.send_mail")
    def test_expiry_set_to_10_minutes(self, mock_send):
        before = timezone.now()
        self.client.post("/my/password/reset/", {"email": "reset@example.com"})
        self.participant.refresh_from_db()
        self.assertIsNotNone(self.participant.password_reset_expires)
        # Should be ~10 minutes from now
        delta = self.participant.password_reset_expires - before
        self.assertGreater(delta.total_seconds(), 9 * 60)
        self.assertLess(delta.total_seconds(), 11 * 60)

    @patch("django.core.mail.send_mail")
    def test_unknown_email_still_shows_success(self, mock_send):
        """Prevent account enumeration — always show success page."""
        resp = self.client.post("/my/password/reset/", {"email": "nobody@example.com"})
        self.assertEqual(resp.status_code, 200)
        # No email sent for unknown address
        mock_send.assert_not_called()

    @patch("django.core.mail.send_mail")
    def test_rate_limit_blocks_after_3_requests(self, mock_send):
        """Max 3 requests per hour."""
        self.participant.password_reset_request_count = 3
        self.participant.password_reset_last_request = timezone.now()
        self.participant.save(update_fields=[
            "password_reset_request_count",
            "password_reset_last_request",
        ])
        resp = self.client.post("/my/password/reset/", {"email": "reset@example.com"})
        self.assertEqual(resp.status_code, 200)
        # No email sent — rate limited
        mock_send.assert_not_called()

    def test_portal_disabled_returns_404(self):
        FeatureToggle.objects.filter(feature_key="participant_portal").update(is_enabled=False)
        resp = self.client.get("/my/password/reset/")
        self.assertEqual(resp.status_code, 404)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-pwconfirm",
)
class PasswordResetConfirmTests(TestCase):
    """Test POST /my/password/reset/confirm/ — entering code + new password."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        _enable_portal()
        self.cf = ClientFile.objects.create(record_id="CFM-001", status="active")
        self.cf.first_name = "Confirm"
        self.cf.last_name = "Tester"
        self.cf.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="confirm@example.com",
            client_file=self.cf,
            display_name="Confirm P",
            password="oldpass123",
        )

    def tearDown(self):
        enc_module._fernet = None

    def _request_code(self):
        """Helper: request a reset code and return the plaintext code."""
        with patch("django.core.mail.send_mail") as mock_send:
            self.client.post("/my/password/reset/", {"email": "confirm@example.com"})
            body = mock_send.call_args[1].get("message") or mock_send.call_args[0][1]
        import re
        match = re.search(r"(\d{6})", body)
        return match.group(1) if match else None

    def test_get_shows_form(self):
        resp = self.client.get("/my/password/reset/confirm/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "code")

    def test_valid_code_resets_password(self):
        code = self._request_code()
        self.assertIsNotNone(code)
        resp = self.client.post("/my/password/reset/confirm/", {
            "email": "confirm@example.com",
            "code": code,
            "new_password": "newSecure99!",
            "confirm_password": "newSecure99!",
        })
        self.assertEqual(resp.status_code, 200)
        # Password should now be the new one
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.check_password("newSecure99!"))
        self.assertFalse(self.participant.check_password("oldpass123"))

    def test_reset_clears_token(self):
        code = self._request_code()
        self.client.post("/my/password/reset/confirm/", {
            "email": "confirm@example.com",
            "code": code,
            "new_password": "newSecure99!",
            "confirm_password": "newSecure99!",
        })
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.password_reset_token_hash, "")
        self.assertIsNone(self.participant.password_reset_expires)
        self.assertEqual(self.participant.password_reset_request_count, 0)

    def test_expired_code_rejected(self):
        code = self._request_code()
        # Expire the code
        self.participant.refresh_from_db()
        self.participant.password_reset_expires = timezone.now() - timedelta(minutes=1)
        self.participant.save(update_fields=["password_reset_expires"])

        resp = self.client.post("/my/password/reset/confirm/", {
            "email": "confirm@example.com",
            "code": code,
            "new_password": "newSecure99!",
            "confirm_password": "newSecure99!",
        })
        self.assertEqual(resp.status_code, 200)
        # Password should NOT have changed
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.check_password("oldpass123"))

    def test_wrong_code_rejected(self):
        self._request_code()
        resp = self.client.post("/my/password/reset/confirm/", {
            "email": "confirm@example.com",
            "code": "000000",
            "new_password": "newSecure99!",
            "confirm_password": "newSecure99!",
        })
        self.assertEqual(resp.status_code, 200)
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.check_password("oldpass123"))

    def test_wrong_email_rejected(self):
        code = self._request_code()
        resp = self.client.post("/my/password/reset/confirm/", {
            "email": "wrong@example.com",
            "code": code,
            "new_password": "newSecure99!",
            "confirm_password": "newSecure99!",
        })
        self.assertEqual(resp.status_code, 200)
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.check_password("oldpass123"))

    def test_password_mismatch_rejected(self):
        code = self._request_code()
        resp = self.client.post("/my/password/reset/confirm/", {
            "email": "confirm@example.com",
            "code": code,
            "new_password": "newSecure99!",
            "confirm_password": "differentPass!",
        })
        self.assertEqual(resp.status_code, 200)
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.check_password("oldpass123"))

    def test_code_cannot_be_reused(self):
        """Once a code is used, the token is cleared — second attempt fails."""
        code = self._request_code()
        # First: succeed
        self.client.post("/my/password/reset/confirm/", {
            "email": "confirm@example.com",
            "code": code,
            "new_password": "newSecure99!",
            "confirm_password": "newSecure99!",
        })
        # Second: should fail
        resp = self.client.post("/my/password/reset/confirm/", {
            "email": "confirm@example.com",
            "code": code,
            "new_password": "anotherPass1!",
            "confirm_password": "anotherPass1!",
        })
        self.assertEqual(resp.status_code, 200)
        self.participant.refresh_from_db()
        # Password should still be from first reset, not second
        self.assertTrue(self.participant.check_password("newSecure99!"))

    def test_inactive_account_rejected(self):
        code = self._request_code()
        self.participant.is_active = False
        self.participant.save(update_fields=["is_active"])

        resp = self.client.post("/my/password/reset/confirm/", {
            "email": "confirm@example.com",
            "code": code,
            "new_password": "newSecure99!",
            "confirm_password": "newSecure99!",
        })
        self.assertEqual(resp.status_code, 200)
        self.participant.refresh_from_db()
        # Should still have old password (code valid but account inactive)
        # The view queries is_active=True, so it won't find the user
        self.assertFalse(self.participant.check_password("newSecure99!"))

    def test_audit_log_created_on_success(self):
        from apps.audit.models import AuditLog
        code = self._request_code()
        self.client.post("/my/password/reset/confirm/", {
            "email": "confirm@example.com",
            "code": code,
            "new_password": "newSecure99!",
            "confirm_password": "newSecure99!",
        })
        audit = AuditLog.objects.using("audit").filter(
            action="portal_password_reset_completed",
        ).first()
        self.assertIsNotNone(audit)
