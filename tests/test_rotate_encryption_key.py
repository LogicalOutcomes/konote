"""Tests for the rotate_encryption_key management command."""
from cryptography.fernet import Fernet
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

import konote.encryption as enc_module


# Generate distinct keys for old/new rotation scenarios.
TEST_KEY = Fernet.generate_key().decode()
OLD_KEY = Fernet.generate_key().decode()
NEW_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=OLD_KEY)
class RotateEncryptionKeySuccessTest(TestCase):
    """Encrypt data with old key, rotate, verify it decrypts with new key."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_successful_rotation(self):
        """Data encrypted with old key is re-encrypted and readable with new key."""
        from apps.auth_app.models import User

        # Create a user whose email is encrypted with OLD_KEY.
        user = User.objects.create_user(
            username="rotate_test",
            display_name="Rotate Test",
        )
        user.email = "rotate@example.com"
        user.save(update_fields=["_email_encrypted"])

        # Grab the ciphertext produced by OLD_KEY.
        old_ciphertext = User.objects.get(pk=user.pk)._email_encrypted

        # Run the rotation command (old -> new).
        call_command(
            "rotate_encryption_key",
            old_key=OLD_KEY,
            new_key=NEW_KEY,
        )

        # Reload from DB — the raw ciphertext should have changed.
        user.refresh_from_db()
        new_ciphertext = user._email_encrypted
        # Convert memoryview to bytes for comparison if needed.
        if isinstance(old_ciphertext, memoryview):
            old_ciphertext = bytes(old_ciphertext)
        if isinstance(new_ciphertext, memoryview):
            new_ciphertext = bytes(new_ciphertext)
        self.assertNotEqual(old_ciphertext, new_ciphertext)

        # Decrypt with NEW_KEY to verify the plaintext is intact.
        new_fernet = Fernet(NEW_KEY.encode())
        raw = new_ciphertext
        if isinstance(raw, memoryview):
            raw = bytes(raw)
        plaintext = new_fernet.decrypt(raw).decode("utf-8")
        self.assertEqual(plaintext, "rotate@example.com")


@override_settings(FIELD_ENCRYPTION_KEY=OLD_KEY)
class RotateEncryptionKeyDryRunTest(TestCase):
    """Dry run mode should not modify any data."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_dry_run_does_not_change_data(self):
        """With --dry-run, encrypted data stays unchanged."""
        from apps.auth_app.models import User

        user = User.objects.create_user(
            username="dryrun_test",
            display_name="Dry Run",
        )
        user.email = "dryrun@example.com"
        user.save(update_fields=["_email_encrypted"])

        # Record the original ciphertext.
        original = User.objects.get(pk=user.pk)._email_encrypted
        if isinstance(original, memoryview):
            original = bytes(original)

        # Run with --dry-run.
        call_command(
            "rotate_encryption_key",
            old_key=OLD_KEY,
            new_key=NEW_KEY,
            dry_run=True,
        )

        # Ciphertext should be unchanged.
        after = User.objects.get(pk=user.pk)._email_encrypted
        if isinstance(after, memoryview):
            after = bytes(after)
        self.assertEqual(original, after)

        # Verify it still decrypts with the old key (nothing changed).
        enc_module._fernet = None
        self.assertEqual(
            enc_module.decrypt_field(after),
            "dryrun@example.com",
        )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RotateEncryptionKeySameKeyTest(TestCase):
    """Passing identical old and new keys should raise CommandError."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_same_key_raises_error(self):
        same_key = Fernet.generate_key().decode()
        with self.assertRaises(CommandError) as ctx:
            call_command(
                "rotate_encryption_key",
                old_key=same_key,
                new_key=same_key,
            )
        self.assertIn("same", str(ctx.exception).lower())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RotateEncryptionKeyInvalidKeyTest(TestCase):
    """Passing an invalid Fernet key string should raise CommandError."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_invalid_old_key_raises_error(self):
        valid_key = Fernet.generate_key().decode()
        with self.assertRaises(CommandError) as ctx:
            call_command(
                "rotate_encryption_key",
                old_key="not-a-valid-fernet-key",
                new_key=valid_key,
            )
        self.assertIn("invalid", str(ctx.exception).lower())

    def test_invalid_new_key_raises_error(self):
        valid_key = Fernet.generate_key().decode()
        with self.assertRaises(CommandError) as ctx:
            call_command(
                "rotate_encryption_key",
                old_key=valid_key,
                new_key="also-not-valid!!!",
            )
        self.assertIn("invalid", str(ctx.exception).lower())


@override_settings(FIELD_ENCRYPTION_KEY=OLD_KEY)
class RotateEncryptionKeyEmptyFieldsTest(TestCase):
    """Empty/null encrypted fields are skipped gracefully."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_empty_email_skipped(self):
        """A user with no email (empty bytes) should not cause an error."""
        from apps.auth_app.models import User

        # Create a user without setting an email — _email_encrypted stays b"".
        user = User.objects.create_user(
            username="no_email",
            display_name="No Email",
        )

        # Rotation should complete without error.
        call_command(
            "rotate_encryption_key",
            old_key=OLD_KEY,
            new_key=NEW_KEY,
        )

        # The empty field should still be empty after rotation.
        user.refresh_from_db()
        raw = user._email_encrypted
        if isinstance(raw, memoryview):
            raw = bytes(raw)
        self.assertIn(raw, (b"", None))

    def test_mix_of_empty_and_populated_fields(self):
        """Users with and without email are both handled correctly."""
        from apps.auth_app.models import User

        # User with email.
        user_with = User.objects.create_user(
            username="has_email",
            display_name="Has Email",
        )
        user_with.email = "present@example.com"
        user_with.save(update_fields=["_email_encrypted"])

        # User without email.
        User.objects.create_user(
            username="no_email_mix",
            display_name="No Email Mix",
        )

        # Rotation should succeed for both.
        call_command(
            "rotate_encryption_key",
            old_key=OLD_KEY,
            new_key=NEW_KEY,
        )

        # Verify the populated one was re-encrypted correctly.
        user_with.refresh_from_db()
        raw = user_with._email_encrypted
        if isinstance(raw, memoryview):
            raw = bytes(raw)
        new_fernet = Fernet(NEW_KEY.encode())
        plaintext = new_fernet.decrypt(raw).decode("utf-8")
        self.assertEqual(plaintext, "present@example.com")


@override_settings(FIELD_ENCRYPTION_KEY=OLD_KEY)
class RotateEncryptionKeyInvalidTokenTest(TestCase):
    """If a field can't be decrypted with the old key, report error but continue."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_invalid_token_reports_error_and_continues(self):
        """A field encrypted with a different key reports an error but doesn't crash."""
        from apps.auth_app.models import User

        # Create two users: one with valid data, one with garbage ciphertext.
        good_user = User.objects.create_user(
            username="good_user",
            display_name="Good User",
        )
        good_user.email = "good@example.com"
        good_user.save(update_fields=["_email_encrypted"])

        bad_user = User.objects.create_user(
            username="bad_user",
            display_name="Bad User",
        )
        # Write ciphertext encrypted with a completely different key.
        rogue_key = Fernet.generate_key()
        rogue_fernet = Fernet(rogue_key)
        bad_ciphertext = rogue_fernet.encrypt(b"rogue data")
        bad_user._email_encrypted = bad_ciphertext
        bad_user.save(update_fields=["_email_encrypted"])

        # Rotation should complete (not raise) even though one record is bad.
        call_command(
            "rotate_encryption_key",
            old_key=OLD_KEY,
            new_key=NEW_KEY,
        )

        # The good user's data should be re-encrypted correctly.
        good_user.refresh_from_db()
        raw = good_user._email_encrypted
        if isinstance(raw, memoryview):
            raw = bytes(raw)
        new_fernet = Fernet(NEW_KEY.encode())
        plaintext = new_fernet.decrypt(raw).decode("utf-8")
        self.assertEqual(plaintext, "good@example.com")

        # The bad user's ciphertext should be unchanged (not re-encrypted).
        bad_user.refresh_from_db()
        bad_raw = bad_user._email_encrypted
        if isinstance(bad_raw, memoryview):
            bad_raw = bytes(bad_raw)
        self.assertEqual(bad_raw, bad_ciphertext)
