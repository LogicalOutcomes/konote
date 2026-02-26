"""
Application-level PII encryption using Fernet (AES-128-CBC + HMAC-SHA256).

Supports key rotation via MultiFernet. Set FIELD_ENCRYPTION_KEY to a
comma-separated list of keys — the first key encrypts new data, all keys
can decrypt existing data.

    # Single key (normal operation):
    FIELD_ENCRYPTION_KEY="tFE8M4TjWq..."

    # Key rotation (new key first, old key second):
    FIELD_ENCRYPTION_KEY="newKeyABC...,oldKeyXYZ..."

Usage in models:
    from konote.encryption import encrypt_field, decrypt_field

    class MyModel(models.Model):
        _name_encrypted = models.BinaryField()

        @property
        def name(self):
            return decrypt_field(self._name_encrypted)

        @name.setter
        def name(self, value):
            self._name_encrypted = encrypt_field(value)
"""
import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.checks import Error, register

logger = logging.getLogger(__name__)

_fernet = None


class DecryptionError(Exception):
    """Raised when a field cannot be decrypted.

    This typically means the encryption key has changed (key rotation without
    re-encryption) or the stored ciphertext is corrupted. Silent failure is
    NOT acceptable — callers must handle this explicitly.
    """


def _get_fernet():
    """Lazy-initialise the Fernet cipher from the configured key(s).

    Supports comma-separated keys for rotation. The first key is used
    for encryption; all keys are tried for decryption.
    """
    global _fernet
    if _fernet is None:
        key_string = settings.FIELD_ENCRYPTION_KEY
        if not key_string:
            raise ValueError(
                "FIELD_ENCRYPTION_KEY is not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        keys = [k.strip() for k in key_string.split(",") if k.strip()]
        fernet_instances = [
            Fernet(k.encode() if isinstance(k, str) else k) for k in keys
        ]
        if len(fernet_instances) == 1:
            _fernet = fernet_instances[0]
        else:
            _fernet = MultiFernet(fernet_instances)
    return _fernet


def encrypt_field(plaintext):
    """Encrypt a string value. Returns bytes for storage in BinaryField."""
    if plaintext is None or plaintext == "":
        return b""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_field(ciphertext):
    """Decrypt a BinaryField value back to string."""
    if not ciphertext:
        return ""
    f = _get_fernet()
    try:
        if isinstance(ciphertext, memoryview):
            ciphertext = bytes(ciphertext)
        return f.decrypt(ciphertext).decode("utf-8")
    except InvalidToken:
        logger.error("Decryption failed — possible key mismatch or data corruption")
        raise DecryptionError(
            "Decryption failed — possible key mismatch or data corruption"
        )


def generate_key():
    """Generate a new Fernet key for initial setup."""
    return Fernet.generate_key().decode()


@register()
def check_encryption_key(app_configs, **kwargs):
    """Django system check: verify the encryption key round-trips correctly.

    Runs on every `./manage.py check` (and on startup). Fails loudly if the
    key is misconfigured, so operators discover the problem at boot time rather
    than when a staff member opens a client record.
    """
    errors = []
    try:
        # Reset the cached fernet so we pick up the current settings value
        global _fernet
        _fernet = None
        test_plaintext = "konote-encryption-selftest"
        ciphertext = encrypt_field(test_plaintext)
        result = decrypt_field(ciphertext)
        if result != test_plaintext:
            errors.append(
                Error(
                    "FIELD_ENCRYPTION_KEY round-trip check failed: "
                    "encrypt then decrypt did not return the original value.",
                    hint="Check that FIELD_ENCRYPTION_KEY is a valid Fernet key.",
                    id="konote.E001",
                )
            )
    except Exception as exc:
        errors.append(
            Error(
                f"FIELD_ENCRYPTION_KEY is invalid or missing: {exc}",
                hint=(
                    "Generate a key with: "
                    "python -c \"from cryptography.fernet import Fernet; "
                    "print(Fernet.generate_key().decode())\""
                ),
                id="konote.E001",
            )
        )
    finally:
        # Leave the cache clean so the first real use re-initialises normally
        _fernet = None
    return errors
